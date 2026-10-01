import json
import os
import uuid

import jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.tour import DifficultyLevel, Tour
from app.services import message_handler, whatsapp_client
from app.services.groq_client import GroqReply
from tests.access_support import AUDIENCE, KID, AccessEnv
from tests.ingest_support import INGEST_BEARER

TEST_DASHBOARD_TOKEN = "test-dashboard-token"


@pytest_asyncio.fixture
async def db_session():
    """Sessão de teste: SQLite em memória; com `TEST_DATABASE_URL`, o mesmo banco da produção.

    O CI roda a suíte também em PostgreSQL (job `backend`): SQLite perdoa coisas que o
    Postgres recusa (tipos, datas com fuso, `FOR UPDATE`, constraints). Sem pool, cada teste abre e
    fecha a própria conexão (o loop de eventos muda a cada teste).
    """
    url = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    is_sqlite = url.startswith("sqlite")
    engine = create_async_engine(url, poolclass=None if is_sqlite else NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    if not is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "dashboard_api_token", TEST_DASHBOARD_TOKEN)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {TEST_DASHBOARD_TOKEN}"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def ingest_token(monkeypatch):
    """Configura o `INGEST_API_TOKEN` do n8n, distinto do token do painel."""
    monkeypatch.setattr(get_settings(), "ingest_api_token", INGEST_BEARER)
    return INGEST_BEARER


@pytest.fixture
def blind_duplicate_check(monkeypatch):
    """Faz a checagem inicial não ver a duplicata, como num reenvio simultâneo em outra conexão."""

    async def never_duplicate(db, whatsapp_message_id):
        return False

    monkeypatch.setattr(message_handler, "is_duplicate_delivery", never_duplicate)


@pytest.fixture
def pipeline_spies(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[object]]:
    """Espiona as fronteiras externas do bot (envio ao WhatsApp, Groq e transcrição)."""
    import app.services.transcription as transcription_module

    calls: dict[str, list[object]] = {"sent": [], "transcribed": [], "asked": []}

    async def fake_send_text_message(settings, to, body):
        calls["sent"].append(body)

    async def fake_ask_groq(settings, system_prompt, user_message):
        calls["asked"].append(user_message)
        return GroqReply(idioma="pt", precisa_atencao_humana=False, resposta="ok")

    monkeypatch.setattr(whatsapp_client, "send_text_message", fake_send_text_message)
    monkeypatch.setattr(message_handler, "ask_groq", fake_ask_groq)
    monkeypatch.setattr(
        transcription_module, "transcribe_audio", lambda *args: calls["transcribed"].append(args)
    )
    return calls


@pytest.fixture
def sample_tours() -> list[Tour]:
    return [
        Tour(
            id="passeio-bugre-orla",
            nome="Passeio de bugre pela orla",
            descricao="Caminhada mínima, acessível a idosos e cadeirantes.",
            dificuldade_fisica=DifficultyLevel.BAIXA,
            caminhada_areia_minutos=5,
            acessivel_idosos=True,
            acessivel_cadeirantes=True,
            acessivel_criancas_pequenas=True,
            duracao_horas=2.5,
            faixa_etaria_recomendada="todas as idades",
            preco_reais=100,
            ativo=True,
        ),
        Tour(
            id="trilha-das-emendas",
            nome="Trilha das Emendas",
            descricao="Trilha longa, alta dificuldade.",
            dificuldade_fisica=DifficultyLevel.ALTA,
            caminhada_areia_minutos=90,
            acessivel_idosos=False,
            acessivel_cadeirantes=False,
            acessivel_criancas_pequenas=False,
            duracao_horas=5,
            faixa_etaria_recomendada="12 a 55 anos",
            preco_reais=130,
            ativo=True,
        ),
        Tour(
            id="rio-preguicas",
            nome="Rio Preguiças (barco)",
            descricao="Passeio de barco, acessível a idosos.",
            dificuldade_fisica=DifficultyLevel.BAIXA,
            caminhada_areia_minutos=8,
            acessivel_idosos=True,
            acessivel_cadeirantes=False,
            acessivel_criancas_pequenas=True,
            duracao_horas=6,
            faixa_etaria_recomendada="todas as idades",
            preco_reais=180,
            ativo=True,
        ),
    ]


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[RSAPrivateKey, RSAPrivateKey]:
    return (
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
    )


def _configure(monkeypatch: pytest.MonkeyPatch, mode: str, issuer: str, audience: str) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "panel_auth_mode", mode)
    monkeypatch.setattr(settings, "access_team_domain", issuer)
    monkeypatch.setattr(settings, "access_aud", audience)


@pytest.fixture
def access(
    monkeypatch: pytest.MonkeyPatch, rsa_keys: tuple[RSAPrivateKey, RSAPrivateKey]
) -> AccessEnv:
    """Modo `access` com um JWKS de teste (sem rede). Cada teste usa uma equipe nova: o cache é
    por endereço, então um teste não enxerga o JWKS do outro."""
    private_key, other_key = rsa_keys
    issuer = f"https://t{uuid.uuid4().hex[:10]}.cloudflareaccess.com"
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk |= {"kid": KID, "use": "sig", "alg": "RS256"}
    fetches: list[int] = []

    def fake_fetch(self: object) -> dict[str, object]:
        fetches.append(1)
        return {"keys": [jwk]}

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fake_fetch)
    _configure(monkeypatch, "access", issuer, AUDIENCE)
    return AccessEnv(issuer, private_key, other_key, fetches)
