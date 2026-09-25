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


engine = create_async_engine(
    settings.database_url, echo=False, connect_args=get_connect_args(settings.database_url)
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
