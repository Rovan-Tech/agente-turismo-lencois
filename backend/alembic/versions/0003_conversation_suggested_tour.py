"""passeio sugerido pela IA: conversations.passeio_sugerido_id

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table: o SQLite (desenvolvimento) não cria chave estrangeira por ALTER TABLE.
    with op.batch_alter_table("conversations") as batch:
        batch.add_column(sa.Column("passeio_sugerido_id", sa.String(64), nullable=True))
        batch.create_foreign_key(
            "fk_conversations_passeio_sugerido_id_tours",
            "tours",
            ["passeio_sugerido_id"],
            ["id"],
        )
        batch.create_index("ix_conversations_passeio_sugerido_id", ["passeio_sugerido_id"])


def downgrade() -> None:
    with op.batch_alter_table("conversations") as batch:
        batch.drop_index("ix_conversations_passeio_sugerido_id")
        batch.drop_constraint("fk_conversations_passeio_sugerido_id_tours", type_="foreignkey")
        batch.drop_column("passeio_sugerido_id")
