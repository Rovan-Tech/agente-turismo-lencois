import logging
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from alembic import command
from alembic.config import Config
from app.core.config import get_settings

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def alembic_config(tmp_path, monkeypatch):
    """Alembic apontado para um SQLite descartável (o env.py lê a URL das settings)."""
    database = tmp_path / "migracao.db"
    monkeypatch.setattr(get_settings(), "database_url", f"sqlite+aiosqlite:///{database}")
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    return config, f"sqlite:///{database}"


def _conversation_columns(sync_url: str) -> set[str]:
    engine = create_engine(sync_url)
    try:
        return {column["name"] for column in inspect(engine).get_columns("conversations")}
    finally:
        engine.dispose()


def _tour_columns(sync_url: str) -> set[str]:
    engine = create_engine(sync_url)
    try:
        return {column["name"] for column in inspect(engine).get_columns("tours")}
    finally:
        engine.dispose()


def _table_names(sync_url: str) -> set[str]:
    engine = create_engine(sync_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_suggested_tour_migration_goes_up_down_and_up_again(alembic_config):
    config, sync_url = alembic_config

    command.upgrade(config, "head")
    assert "passeio_sugerido_id" in _conversation_columns(sync_url)

    command.downgrade(config, "0002")
    assert "passeio_sugerido_id" not in _conversation_columns(sync_url)

    command.upgrade(config, "head")
    assert "passeio_sugerido_id" in _conversation_columns(sync_url)


def test_booking_migration_goes_up_down_and_up_again(alembic_config):
    config, sync_url = alembic_config

    command.upgrade(config, "head")
    assert "capacidade_diaria" in _tour_columns(sync_url)
    assert "bookings" in _table_names(sync_url)

    command.downgrade(config, "0003")
    assert "capacidade_diaria" not in _tour_columns(sync_url)
    assert "bookings" not in _table_names(sync_url)

    command.upgrade(config, "head")
    assert "capacidade_diaria" in _tour_columns(sync_url)
    assert "bookings" in _table_names(sync_url)


def test_running_migrations_does_not_silence_the_app_loggers(alembic_config):
    """O `fileConfig` do Alembic desativa loggers já criados e o app perderia os próprios logs."""
    config, _ = alembic_config
    app_logger = logging.getLogger("app.services.message_handler")

    command.upgrade(config, "head")

    assert app_logger.disabled is False
