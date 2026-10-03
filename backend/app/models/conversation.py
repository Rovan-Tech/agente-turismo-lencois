import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import ForeignKey

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.tour import Tour


class ConversationStatus(str, enum.Enum):
    ABERTA = "aberta"
    PRECISA_ATENCAO = "precisa_atencao"
    RESOLVIDA = "resolvida"


class Handling(str, enum.Enum):
    """Quem responde ao turista: o assistente de IA ou uma pessoa da equipe (ADR-0008)."""

    IA = "ia"
    HUMANO = "humano"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    whatsapp_phone: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[ConversationStatus] = mapped_column(
        String(20), default=ConversationStatus.ABERTA
    )
    idioma_detectado: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Nome do perfil do WhatsApp do turista, quando a Meta o informa (dado pessoal, LGPD): só o
    # painel o mostra; nunca vai a log nem a prompt de LLM.
    cliente_nome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Último passeio que o assistente recomendou (validado contra os candidatos enviados ao LLM).
    passeio_sugerido_id: Mapped[str | None] = mapped_column(
        ForeignKey("tours.id"), nullable=True, index=True
    )
    atendimento: Mapped[Handling] = mapped_column(String(10), default=Handling.IA)
    # Quem assumiu (`sub` do login), o primeiro nome mostrado ao turista e quando. Só valem enquanto
    # `atendimento` for `humano`; a última mensagem do atendente renova `humano_atividade_em`.
    humano_sub: Mapped[str | None] = mapped_column(String(128), nullable=True)
    humano_nome: Mapped[str | None] = mapped_column(String(40), nullable=True)
    humano_desde: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    humano_atividade_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    passeio_sugerido: Mapped["Tour | None"] = relationship()
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", order_by="Message.created_at", cascade="all, delete-orphan"
    )
