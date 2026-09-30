"""idempotência do webhook: id da mensagem do WhatsApp em messages

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("whatsapp_message_id", sa.String(128), nullable=True))
    op.create_index(
        "ix_messages_whatsapp_message_id", "messages", ["whatsapp_message_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_messages_whatsapp_message_id", table_name="messages")
    op.drop_column("messages", "whatsapp_message_id")
