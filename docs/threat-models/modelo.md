# Threat model: <funcionalidade>

- **Data:** AAAA-MM-DD
- **Escopo:** <o que entra e o que fica de fora>
- **Dados sensíveis:** <telefone, conversas, token…>
- **Fronteiras de confiança:** <ex.: Internet → webhook; painel → API; backend → Groq>

## Diagrama de fluxo (texto)

```
<ator> → <fronteira> → <componente> → <armazenamento / serviço externo>
```

## Ameaças (STRIDE)

| Cat. | Ameaça | Impacto | Mitigação | Teste que prova | Risco residual |
|---|---|---|---|---|---|
| **S**poofing | <ex.: webhook forjado> | | <ex.: HMAC em tempo constante> | `test_security.py::test_…` | |
| **T**ampering | | | | | |
| **R**epudiation | | | | | |
| **I**nformation disclosure | | | | | |
| **D**enial of service | | | | | |
| **E**levation of privilege | | | | | |

## Riscos aceitos

- <risco, motivo, quem aceitou e até quando>
