---
name: threat-model
description: Cria o modelo de ameaças STRIDE de uma funcionalidade crítica em docs/threat-models/ e converte cada mitigação em casos de teste de segurança. Use antes de codar endpoint, webhook, autenticação, tratamento de dado pessoal ou chamada a LLM (item GOV-2 do checklist).
argument-hint: "<funcionalidade>"
disable-model-invocation: true
---

# /threat-model

Funcionalidade: **$ARGUMENTS**

1. Leia `docs/threat-models/README.md`, `docs/threat-models/modelo.md`, `.claude/rules/security.md`,
   `.claude/rules/ai-governance.md` e a superfície descrita na skill `security-check`.
2. Mapeie: fluxo de dados, fronteiras de confiança (Internet → webhook, painel → API, backend →
   Groq/WhatsApp/banco) e dados sensíveis (telefone, conversas, token; áudio bruto nunca é
   persistido).
3. Preencha **as seis categorias STRIDE** (Spoofing, Tampering, Repudiation, Information
   disclosure, Denial of service, Elevation of privilege). Para a funcionalidade de LLM inclua
   prompt injection e saída não confiável (OWASP LLM Top 10). Categoria sem ameaça escreve o motivo.
4. Para cada mitigação, escreva o **caso de teste** (nome `test_<unidade>_<cenário>_<resultado>` em
   `backend/tests/test_security.py` ou spec Playwright) e deixe-o na lista de tarefas da
   implementação (TDD: o teste falha antes da mitigação).
5. Salve em `docs/threat-models/AAAA-MM-DD-<funcionalidade>.md` e apresente ao Patrick. Riscos
   aceitos exigem a decisão dele, registrada no próprio arquivo.
