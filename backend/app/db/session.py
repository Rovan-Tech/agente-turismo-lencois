from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()


def get_connect_args(database_url: str) -> dict:
    # asyncpg não entende sslmode/channel_binding como kwargs (só dentro de uma DSN que ele
    # mesmo faz parse) — Settings já filtra esses parâmetros da URL, então o SSL exigido pelo
    # Neon precisa ser pedido explicitamente aqui.
    if "asyncpg" in make_url(database_url).drivername:
        return {"ssl": True}
    return {}


POOL_RECYCLE_SECONDS = 300


def get_pool_args() -> dict[str, bool | int]:
    """Opções do pool que evitam reutilizar conexão que o Neon já encerrou.

    O Neon (Postgres serverless) fecha conexões ociosas; sem validar antes do uso, a primeira
    requisição depois de uma pausa recebe `connection is closed` e o endpoint devolve 500.
    `pool_pre_ping` testa a conexão ao tirá-la do pool e `pool_recycle` a renova antes do corte.
    """
    return {"pool_pre_ping": True, "pool_recycle": POOL_RECYCLE_SECONDS}


engine = create_async_engine(
    settings.database_url,
    echo=False,
    # O texto de uma exceção do banco inclui os parâmetros do SQL: sem isto, telefone e conversa do
    # turista iriam parar no log de erro.
    hide_parameters=True,
    connect_args=get_connect_args(settings.database_url),
    **get_pool_args(),
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
