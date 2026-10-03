"""Nome do perfil do WhatsApp do turista: limpeza e gravação na conversa.

O nome é dado pessoal (LGPD) e texto escolhido pelo próprio turista, então é dado não confiável:
só vai ao banco e ao painel. Nunca ao log, a mensagem de erro, ao prompt do LLM ou ao n8n.
"""

from __future__ import annotations

import unicodedata

from app.models.conversation import Conversation

# Mesmo tamanho da coluna `conversations.cliente_nome` e do contrato de ingestão.
MAX_LENGTH = 100
# Controle (inclui NUL, que o Postgres recusa) e substitutos soltos (UTF-8 inválido no banco).
_DROPPED_CATEGORIES = frozenset({"Cc", "Cs"})


def clean_profile_name(raw: object) -> str | None:
    """Normaliza o nome do perfil; devolve `None` se não sobrar nada que valha mostrar.

    Args:
        raw: Valor vindo de fora (payload da Meta ou do n8n), de qualquer tipo.

    Returns:
        O nome com espaços colapsados, sem caracteres de controle e com no máximo 100 caracteres,
        ou `None` se o valor não é texto ou ficou vazio.
    """
    if not isinstance(raw, str):
        return None
    # `split` colapsa também quebras de linha e tabulações em um espaço só.
    collapsed = " ".join(raw.split())
    visible = "".join(c for c in collapsed if unicodedata.category(c) not in _DROPPED_CATEGORIES)
    return visible.strip()[:MAX_LENGTH].strip() or None


def apply_profile_name(conversation: Conversation, raw: object) -> None:
    """Guarda o nome na conversa; ausente ou vazio mantém o que já estava (nunca apaga).

    O WhatsApp só manda o nome às vezes, e o turista pode trocá-lo: o mais recente vale.
    """
    name = clean_profile_name(raw)
    if name is not None and name != conversation.cliente_nome:
        conversation.cliente_nome = name
