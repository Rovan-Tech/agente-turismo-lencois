"""Textos fixos que o turista recebe quando uma pessoa assume ou devolve a conversa (ADR-0008).

São modelos, nunca texto digitado: o único dado variável é o primeiro nome, já sanitizado.
"""

from __future__ import annotations

LANGUAGES = ("pt", "en", "es")

# (frase, fecho) por idioma; o nome vem depois dos dois-pontos e, sem nome, a frase fecha sozinha.
_ANNOUNCEMENT = {
    "pt": (
        "Olá! Agora quem está falando com você é uma pessoa da nossa equipe",
        "Pode continuar por aqui.",
    ),
    "en": (
        "Hello! You are now talking to a person from our team",
        "You can keep writing here.",
    ),
    "es": (
        "¡Hola! Ahora te atiende una persona de nuestro equipo",
        "Puedes seguir escribiendo por aquí.",
    ),
}
_GIVE_BACK = {
    "pt": (
        "A partir de agora o nosso assistente virtual volta a ajudar você. "
        "Se quiser falar com uma pessoa, é só pedir."
    ),
    "en": (
        "From now on our virtual assistant will help you again. "
        "If you want to talk to a person, just ask."
    ),
    "es": (
        "A partir de ahora nuestro asistente virtual vuelve a ayudarte. "
        "Si quieres hablar con una persona, solo pídelo."
    ),
}


def _languages(language: str | None) -> tuple[str, ...]:
    """O idioma da conversa; sem idioma detectado (ou desconhecido), os três."""
    return (language,) if language in _ANNOUNCEMENT else LANGUAGES


def announcement_text(language: str | None, first_name: str | None) -> str:
    """Aviso de que agora é uma pessoa falando, no idioma da conversa (ou nos três)."""
    suffix = f": {first_name}" if first_name else ""
    parts = (_ANNOUNCEMENT[code] for code in _languages(language))
    return "\n".join(f"{lead}{suffix}. {tail}" for lead, tail in parts)


def give_back_text(language: str | None) -> str:
    """Aviso curto de que o assistente virtual voltou, no idioma da conversa (ou nos três)."""
    return "\n".join(_GIVE_BACK[code] for code in _languages(language))
