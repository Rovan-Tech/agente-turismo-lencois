"""Reexporta os modelos para que importar `app.models` registre todos no metadata do SQLAlchemy."""

from app.models.booking import Booking, PaymentMethod, PaymentStatus
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageDirection, MessageType
from app.models.tour import DifficultyLevel, Tour

__all__ = [
    "Booking",
    "Conversation",
    "ConversationStatus",
    "DifficultyLevel",
    "Message",
    "MessageDirection",
    "MessageType",
    "PaymentMethod",
    "PaymentStatus",
    "Tour",
]
