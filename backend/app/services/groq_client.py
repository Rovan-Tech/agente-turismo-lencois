from __future__ import annotations

import json

import httpx

from app.core.config import Settings
from app.models.tour import Tour

SYSTEM_PROMPT_TEMPLATE = """Você é o assistente virtual da {agency_name}, uma agência de \
turismo em Lençóis Maranhenses (Barreirinhas/MA, Brasil).

Responda SEMPRE no mesmo idioma da pergunta do turista (português, inglês ou espanhol).
Use APENAS os passeios do catálogo estruturado abaixo (JSON) para recomendar. Considere \
explicitamente os atributos de dificuldade física, acessibilidade, duração, faixa etária \
recomendada e preço para decidir qual passeio combina com o perfil do turista. Explique \
brevemente o motivo da recomendação e cite o preço. Seja direto, no máximo 4 frases.

Se nenhum passeio do catálogo atender bem ao pedido, ou se o turista pedir explicitamente \
para falar com uma pessoa, marque "precisa_atencao_humana" como true e explique isso na resposta.

Responda SOMENTE com um objeto JSON válido, sem markdown, no formato exato:
{{"idioma": "pt|en|es", "precisa_atencao_humana": true|false, "resposta": "texto da resposta"}}

CATÁLOGO:
{catalog_json}
"""


class GroqReply:
    def __init__(self, idioma: str, precisa_atencao_humana: bool, resposta: str):
        self.idioma = idioma
        self.precisa_atencao_humana = precisa_atencao_humana
        self.resposta = resposta


def build_system_prompt(agency_name: str, tours: list[Tour]) -> str:
    catalog_json = json.dumps([t.to_catalog_dict() for t in tours], ensure_ascii=False, indent=2)
    return SYSTEM_PROMPT_TEMPLATE.format(agency_name=agency_name, catalog_json=catalog_json)


def parse_reply(raw_content: str) -> GroqReply:
    try:
        data = json.loads(raw_content)
        return GroqReply(
            idioma=data.get("idioma", "pt"),
            precisa_atencao_humana=bool(data.get("precisa_atencao_humana", False)),
            resposta=data.get("resposta", raw_content),
        )
    except (json.JSONDecodeError, AttributeError):
        return GroqReply(idioma="pt", precisa_atencao_humana=True, resposta=raw_content)


async def ask_groq(settings: Settings, system_prompt: str, user_message: str) -> GroqReply:
    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}

    async with httpx.AsyncClient(base_url=settings.groq_base_url, timeout=30) as client:
        response = await client.post("/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    raw_content = data["choices"][0]["message"]["content"]
    return parse_reply(raw_content)
