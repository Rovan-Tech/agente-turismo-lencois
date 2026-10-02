"""Modelo de agendamento (pagamento simulado — nenhum gateway real é integrado)."""

import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PaymentMethod(str, enum.Enum):
    """Forma de pagamento simulada escolhida pelo atendente ao registrar o agendamento."""

    PIX = "pix"
    BOLETO = "boleto"
    CARTAO = "cartao"


class PaymentStatus(str, enum.Enum):
    """Status do agendamento. Hoje só ``PAGO`` é produzido (a simulação sempre aprova na hora)."""

    PENDENTE = "pendente"
    PAGO = "pago"


def _as_sql_enum(enum_cls: type[enum.Enum]) -> SQLEnum:
    """Enum armazenado como `VARCHAR` (não o tipo nativo do Postgres), com o valor em minúsculas.

    Sem isso, `Mapped[PaymentMethod]` sobre `mapped_column(String(10))` devolve `str` puro ao
    recarregar de uma sessão nova (só parece um `PaymentMethod` quando o objeto vem do identity
    map) — o `mypy` aceita `booking.forma_pagamento.value` e isso quebra em runtime.
    """
    return SQLEnum(
        enum_cls, native_enum=False, length=10, values_callable=lambda e: [m.value for m in e]
    )


class Booking(Base):
    """Agendamento de um passeio num dia, com pagamento simulado (nunca um gateway real)."""

    __tablename__ = "bookings"
    __table_args__ = (Index("ix_bookings_tour_id_data", "tour_id", "data"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tour_id: Mapped[str] = mapped_column(ForeignKey("tours.id"))
    data: Mapped[date] = mapped_column(Date)
    pessoas: Mapped[int] = mapped_column(Integer)
    forma_pagamento: Mapped[PaymentMethod] = mapped_column(_as_sql_enum(PaymentMethod))
    status_pagamento: Mapped[PaymentStatus] = mapped_column(
        _as_sql_enum(PaymentStatus), default=PaymentStatus.PAGO
    )
    telefone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
