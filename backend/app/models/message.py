import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class MessageDirection(str, enum.Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"


class MessageAuthor(str, enum.Enum):
    """Quem escreveu a mensagem: o turista, o assistente de IA ou uma pessoa da equipe."""

    TURISTA = "turista"
    IA = "ia"
    ATENDENTE = "atendente"


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
    autor: Mapped[MessageAuthor] = mapped_column(String(10))
    # `sub` da pessoa que enviou (só para `atendente`), para saber quem respondeu ao turista.
    autor_sub: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Gerado pelo painel a cada envio: o índice único faz o clique duplo ou a nova tentativa não
    # mandar a mensagem duas vezes ao turista.
    client_message_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


@event.listens_for(Message, "before_insert")
def _fill_author(_mapper: Mapper[Message], _connection: Connection, message: Message) -> None:
    """Sem autor explícito, a direção decide: o que entra é do turista e o que sai é da IA."""
    if message.autor is None:
        is_inbound = message.direction == MessageDirection.ENTRADA
        message.autor = MessageAuthor.TURISTA if is_inbound else MessageAuthor.IA
