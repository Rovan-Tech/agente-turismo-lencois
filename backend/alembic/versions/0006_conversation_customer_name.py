"""nome do perfil do WhatsApp do turista na conversa (opcional, dado pessoal)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nula nas conversas existentes: o nome só chega quando o WhatsApp o informa.
    with op.batch_alter_table("conversations") as batch:
        batch.add_column(sa.Column("cliente_nome", sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("conversations") as batch:
        batch.drop_column("cliente_nome")
