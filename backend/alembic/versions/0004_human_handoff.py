"""atendimento humano: estado da conversa e autoria das mensagens (ADR-0008)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table: o SQLite (desenvolvimento) não altera colunas por ALTER TABLE.
    with op.batch_alter_table("conversations") as batch:
        batch.add_column(
            sa.Column("atendimento", sa.String(10), nullable=False, server_default="ia")
        )
        batch.add_column(sa.Column("humano_sub", sa.String(128), nullable=True))
        batch.add_column(sa.Column("humano_nome", sa.String(40), nullable=True))
        batch.add_column(sa.Column("humano_desde", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("humano_atividade_em", sa.DateTime(timezone=True), nullable=True)
        )
    # O histórico existente: o que entrou é do turista e o que saiu foi da IA (ainda não havia
    # atendente). Só depois a coluna vira obrigatória.
    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("autor", sa.String(10), nullable=True))
        batch.add_column(sa.Column("autor_sub", sa.String(128), nullable=True))
        batch.add_column(sa.Column("client_message_id", sa.String(64), nullable=True))
    op.execute("UPDATE messages SET autor = 'turista' WHERE direction = 'entrada'")
    op.execute("UPDATE messages SET autor = 'ia' WHERE direction <> 'entrada'")
    with op.batch_alter_table("messages") as batch:
        batch.alter_column("autor", existing_type=sa.String(10), nullable=False)
    op.create_index("ix_messages_client_message_id", "messages", ["client_message_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_messages_client_message_id", table_name="messages")
    with op.batch_alter_table("messages") as batch:
        batch.drop_column("client_message_id")
        batch.drop_column("autor_sub")
        batch.drop_column("autor")
    with op.batch_alter_table("conversations") as batch:
        batch.drop_column("humano_atividade_em")
        batch.drop_column("humano_desde")
        batch.drop_column("humano_nome")
        batch.drop_column("humano_sub")
        batch.drop_column("atendimento")
