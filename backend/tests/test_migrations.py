import logging
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

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


def test_suggested_tour_migration_goes_up_down_and_up_again(alembic_config):
    config, sync_url = alembic_config

    command.upgrade(config, "head")
    assert "passeio_sugerido_id" in _conversation_columns(sync_url)

    command.downgrade(config, "0002")
    assert "passeio_sugerido_id" not in _conversation_columns(sync_url)

    command.upgrade(config, "head")
    assert "passeio_sugerido_id" in _conversation_columns(sync_url)


def test_running_migrations_does_not_silence_the_app_loggers(alembic_config):
    """O `fileConfig` do Alembic desativa loggers já criados e o app perderia os próprios logs."""
    config, _ = alembic_config
    app_logger = logging.getLogger("app.services.message_handler")

    command.upgrade(config, "head")

    assert app_logger.disabled is False


def _columns(sync_url: str, table: str) -> set[str]:
    engine = create_engine(sync_url)
    try:
        return {column["name"] for column in inspect(engine).get_columns(table)}
    finally:
        engine.dispose()


def _authors_by_content(sync_url: str) -> dict[str, str]:
    engine = create_engine(sync_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(text("SELECT conteudo, autor FROM messages")).all()
        return {row[0]: row[1] for row in rows}
    finally:
        engine.dispose()


def _seeded_conversation_state(sync_url: str) -> tuple[object, object, set[str | None]]:
    engine = create_engine(sync_url)
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT atendimento, humano_desde FROM conversations WHERE id = 'c1'")
            ).one()
        unique = {i["name"] for i in inspect(engine).get_indexes("messages") if i["unique"]}
        return row[0], row[1], unique
    finally:
        engine.dispose()


def _seed_two_messages(sync_url: str) -> None:
    engine = create_engine(sync_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO conversations (id, whatsapp_phone, status, created_at, updated_at)"
                    " VALUES ('c1', '5598900000001', 'aberta', '2026-10-01', '2026-10-01')"
                )
            )
            for message_id, direction, content in (("m1", "entrada", "oi"), ("m2", "saida", "olá")):
                connection.execute(
                    text(
                        "INSERT INTO messages (id, conversation_id, direction, tipo, conteudo,"
                        " created_at) VALUES (:id, 'c1', :direction, 'texto',"
                        " :content, '2026-10-01')"
                    ),
                    {"id": message_id, "direction": direction, "content": content},
                )
    finally:
        engine.dispose()


def test_human_handoff_migration_backfills_the_author_and_is_reversible(alembic_config):
    config, sync_url = alembic_config
    command.upgrade(config, "0003")
    _seed_two_messages(sync_url)

    command.upgrade(config, "head")
    assert _authors_by_content(sync_url) == {"oi": "turista", "olá": "ia"}
    handling, since, unique_indexes = _seeded_conversation_state(sync_url)
    assert (handling, since) == ("ia", None)
    assert "ix_messages_client_message_id" in unique_indexes
    assert {"atendimento", "humano_sub", "humano_nome"} <= _columns(sync_url, "conversations")
    assert {"autor", "autor_sub", "client_message_id"} <= _columns(sync_url, "messages")

    command.downgrade(config, "0003")
    assert "atendimento" not in _columns(sync_url, "conversations")
    assert "autor" not in _columns(sync_url, "messages")

    command.upgrade(config, "head")
    assert _authors_by_content(sync_url) == {"oi": "turista", "olá": "ia"}
