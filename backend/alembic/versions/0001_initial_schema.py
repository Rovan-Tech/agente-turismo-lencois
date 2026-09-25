"""schema inicial: tours, conversations, messages

Revision ID: 0001
Revises:
Create Date: 2026-09-25

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tours",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("descricao", sa.String(1000), nullable=False),
        sa.Column("dificuldade_fisica", sa.String(10), nullable=False),
        sa.Column("caminhada_areia_minutos", sa.Integer(), nullable=False),
        sa.Column("acessivel_idosos", sa.Boolean(), nullable=False),
        sa.Column("acessivel_cadeirantes", sa.Boolean(), nullable=False),
        sa.Column("acessivel_criancas_pequenas", sa.Boolean(), nullable=False),
        sa.Column("duracao_horas", sa.Float(), nullable=False),
        sa.Column("faixa_etaria_recomendada", sa.String(200), nullable=False),
        sa.Column("preco_reais", sa.Numeric(10, 2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("whatsapp_phone", sa.String(32), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("idioma_detectado", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_whatsapp_phone", "conversations", ["whatsapp_phone"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("idioma", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_whatsapp_phone", table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("tours")
