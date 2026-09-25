import json

from app.services.groq_client import build_system_prompt, parse_reply


def test_build_system_prompt_includes_catalog(sample_tours):
    prompt = build_system_prompt("Agência Teste", sample_tours)
    assert "Agência Teste" in prompt
    assert "passeio-bugre-orla" in prompt
    assert "responda somente com um objeto json" in prompt.lower()


def test_parse_reply_valid_json():
    raw = json.dumps({"idioma": "pt", "precisa_atencao_humana": False, "resposta": "Oi!"})
    reply = parse_reply(raw)
    assert reply.idioma == "pt"
    assert reply.precisa_atencao_humana is False
    assert reply.resposta == "Oi!"


def test_parse_reply_invalid_json_escalates_to_human():
    reply = parse_reply("isso não é json")
    assert reply.precisa_atencao_humana is True
    assert reply.resposta == "isso não é json"
