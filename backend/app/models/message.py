import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class MessageDirection(str, enum.Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"


class MessageType(str, enum.Enum):
    TEXTO = "texto"
    AUDIO_TRANSCRITO = "audio_transcrito"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    direction: Mapped[MessageDirection] = mapped_column(String(10))
    tipo: Mapped[MessageType] = mapped_column(String(20), default=MessageType.TEXTO)
    conteudo: Mapped[str] = mapped_column(Text)
    idioma: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # `message.id` da Meta em cada mensagem recebida: o índice único barra o reprocessamento quando
    # ela reenvia o webhook. Nulo nas respostas do bot (saída).
    whatsapp_message_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
