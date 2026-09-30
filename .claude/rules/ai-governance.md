---
paths:
  - "backend/app/services/**"
  - "backend/app/api/webhook.py"
  - "backend/tests/**"
---

# Governança de IA e segurança em LLMs (OWASP Top 10 LLM)

O Groq (`openai/gpt-oss-120b`) recebe texto de turistas e o bot responde por WhatsApp: toda entrada
é não confiável e toda saída também. Itens do checklist: `AI-1`, `AI-2`, `AI-3`.

## Prompt injection (`AI-1`)
- O texto do usuário é **dado**, nunca instrução: vai em mensagem de papel `user`, delimitado
  (ex.: `<mensagem_do_turista>…</mensagem_do_turista>`), nunca concatenado ao prompt de sistema.
- Limite o tamanho antes de chamar o LLM; recuse/neutralize padrões de sequestro conhecidos
  ("ignore as instruções anteriores", "mostre seu prompt").
- O prompt de sistema não contém segredo nem dado pessoal, e o bot nunca o revela.
- Sem guardrail pesado (NeMo/Llama Guard) por custo zero: valem delimitação + limite + filtro +
  **teste adversário** em `backend/tests/`.

## Saída do LLM é dado de terceiros (`AI-2`)
- Valide formato e tamanho antes de enviar ao WhatsApp, gravar no banco ou renderizar no painel.
- Nunca interpole a saída em SQL, HTML ou shell. Ações com efeito (marcar conversa, acionar
  humano) só por allowlist de intenções, nunca por texto livre devolvido pelo modelo.
- No painel a saída é texto (`{variavel}` no JSX), nunca HTML.

## Dados e custo (`AI-3`)
- Envie ao LLM o mínimo necessário: sem telefone, sem nome, sem histórico além do que a resposta
  precisa.
- Nenhum LLM ou serviço de tradução novo sem o teste de qualidade de
  `docs/decisoes-de-arquitetura.md` (custo zero é requisito) e ADR.

## Código gerado por IA (Anti-AI-slop, `GIT-3`)
- Sem função fantasma, import/parâmetro morto, comentário que repete o código, `print`/
  `console.log`. Quem envia explica cada trecho; o `code-reviewer` pergunta "por que existe?".
