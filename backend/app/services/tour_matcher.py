from __future__ import annotations

import re

from app.models.tour import Tour

_ELDERLY_KEYWORDS = (
    "idoso",
    "idosa",
    "avô",
    "avó",
    "bengala",
    "elderly",
    "anciano",
    "anciana",
    "mayor",
)
_WHEELCHAIR_KEYWORDS = ("cadeirante", "cadeira de rodas", "wheelchair", "silla de ruedas")
_CHILDREN_KEYWORDS = (
    "criança",
    "crianças",
    "filho pequeno",
    "filhos pequenos",
    "child",
    "kids",
    "niño",
    "niña",
    "niños",
    "hijos pequeños",
)

_PRICE_CEILING_RE = re.compile(
    r"(?:at[ée]|no m[áa]ximo|m[áa]ximo de|up to|hasta)\s*r?\$?\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE
)
_DURATION_CEILING_RE = re.compile(
    r"(?:at[ée]|no m[áa]ximo|m[áa]ximo de|up to|hasta)\s*(\d+(?:[.,]\d+)?)\s*h", re.IGNORECASE
)


def extract_criteria(message: str) -> dict:
    lowered = message.lower()
    criteria: dict = {}

    if any(kw in lowered for kw in _ELDERLY_KEYWORDS):
        criteria["acessivel_idosos"] = True
    if any(kw in lowered for kw in _WHEELCHAIR_KEYWORDS):
        criteria["acessivel_cadeirantes"] = True
    if any(kw in lowered for kw in _CHILDREN_KEYWORDS):
        criteria["acessivel_criancas_pequenas"] = True

    price_match = _PRICE_CEILING_RE.search(lowered)
    if price_match:
        criteria["preco_maximo"] = float(price_match.group(1).replace(",", "."))

    duration_match = _DURATION_CEILING_RE.search(lowered)
    if duration_match:
        criteria["duracao_maxima_horas"] = float(duration_match.group(1).replace(",", "."))

    return criteria


def filter_tours(tours: list[Tour], criteria: dict) -> list[Tour]:
    filtered = [t for t in tours if t.ativo]

    if criteria.get("acessivel_idosos"):
        filtered = [t for t in filtered if t.acessivel_idosos]
    if criteria.get("acessivel_cadeirantes"):
        filtered = [t for t in filtered if t.acessivel_cadeirantes]
    if criteria.get("acessivel_criancas_pequenas"):
        filtered = [t for t in filtered if t.acessivel_criancas_pequenas]
    if "preco_maximo" in criteria:
        filtered = [t for t in filtered if float(t.preco_reais) <= criteria["preco_maximo"]]
    if "duracao_maxima_horas" in criteria:
        filtered = [t for t in filtered if t.duracao_horas <= criteria["duracao_maxima_horas"]]

    return filtered


def select_candidate_tours(tours: list[Tour], message: str) -> list[Tour]:
    criteria = extract_criteria(message)
    if not criteria:
        return [t for t in tours if t.ativo]

    candidates = filter_tours(tours, criteria)
    return candidates if candidates else [t for t in tours if t.ativo]
