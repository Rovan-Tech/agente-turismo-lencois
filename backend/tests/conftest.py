import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.tour import DifficultyLevel, Tour
from app.services import message_handler, whatsapp_client
from app.services.groq_client import GroqReply

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


async def persist(db_session: AsyncSession, *objects: object) -> None:
    """Adiciona um ou mais objetos, na ordem dada, e commita — para preparar o estado de um teste.

    Dá `flush()` depois de cada `add()`: sem `relationship()` entre os modelos, o SQLAlchemy não
    tem como ordenar os INSERTs por dependência de FK sozinho. SQLite não aplica a constraint e
    deixava passar calado; o Postgres recusa se um `Booking` for inserido antes do `Tour` que ele
    referencia. Passar o `Tour` antes do `Booking` nos argumentos garante a ordem certa.
    """
    for obj in objects:
        db_session.add(obj)
        await db_session.flush()
    await db_session.commit()


def default_tour_fields(**overrides: object) -> dict[str, object]:
    """Campos válidos mínimos de um `Tour`, para montar variações em testes sem repetir tudo."""
    fields: dict[str, object] = {
        "id": "passeio-teste",
        "nome": "Passeio de teste",
        "descricao": "Descrição do passeio de teste.",
        "dificuldade_fisica": DifficultyLevel.MEDIA,
        "caminhada_areia_minutos": 10,
        "acessivel_idosos": False,
        "acessivel_cadeirantes": False,
        "acessivel_criancas_pequenas": False,
        "duracao_horas": 2.0,
        "faixa_etaria_recomendada": "todas as idades",
        "preco_reais": 90.0,
        "ativo": True,
    }
    fields.update(overrides)
    return fields


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
