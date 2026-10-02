"""capacidade diária do passeio e tabela de agendamentos (pagamento simulado)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table: o SQLite (desenvolvimento) não altera tabela existente por ALTER TABLE
    # direto. server_default preenche os passeios que já existem (sem isso, NOT NULL falha).
    with op.batch_alter_table("tours") as batch:
        batch.add_column(
            sa.Column("capacidade_diaria", sa.Integer(), nullable=False, server_default="30")
        )

    op.create_table(
        "bookings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tour_id", sa.String(64), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("pessoas", sa.Integer(), nullable=False),
        sa.Column("forma_pagamento", sa.String(10), nullable=False),
        sa.Column("status_pagamento", sa.String(10), nullable=False),
        sa.Column("telefone", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bookings_tour_id_data", "bookings", ["tour_id", "data"])


def downgrade() -> None:
    op.drop_index("ix_bookings_tour_id_data", table_name="bookings")
    op.drop_table("bookings")
    with op.batch_alter_table("tours") as batch:
        batch.drop_column("capacidade_diaria")
