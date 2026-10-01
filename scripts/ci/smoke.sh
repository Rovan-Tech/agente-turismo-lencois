#!/usr/bin/env bash
# Teste de fumaça de uma instância no ar: serve, protege e responde JSON válido.
# Uso: smoke.sh <url-base> [token-do-painel]
#   sem token: confere só o que é público (/health) e que a API fecha sem credencial;
#   com token: confere também uma leitura autenticada.
set -euo pipefail

base="${1:?uso: smoke.sh <url-base> [token]}"
base="${base%/}"
token="${2:-}"
fail=0

check() { # descrição, esperado, obtido
  if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FALHA $1 (esperado $2, obtido $3)" >&2; fail=1; fi
}

# curl devolve 000 e sai com erro quando não consegue conectar: o `|| true` deixa o `check` relatar.
status() { curl --silent --max-time 15 --output /dev/null --write-out '%{http_code}' "$@" || true; }

check "GET /health" 200 "$(status "$base/health")"
body="$(curl --silent --max-time 15 "$base/health" || true)"
check "/health devolve status ok" '{"status":"ok"}' "$(printf '%s' "$body" | tr -d ' \n')"
check "GET /api/tours sem token é negado" 401 "$(status "$base/api/tours")"
check "GET /api/conversations sem token é negado" 401 "$(status "$base/api/conversations")"
invalid_token="token-invalido"
check "GET /api/tours com token inválido é negado" 401 \
  "$(status -H "Authorization: Bearer $invalid_token" "$base/api/tours")"

if [ -n "$token" ]; then
  check "GET /api/tours com token" 200 "$(status -H "Authorization: Bearer $token" "$base/api/tours")"
  tours="$(curl --silent --max-time 15 -H "Authorization: Bearer $token" "$base/api/tours" || true)"
  if printf '%s' "$tours" | python3 -c 'import json,sys; assert isinstance(json.load(sys.stdin), list)' 2>/dev/null; then
    echo "ok   /api/tours devolve uma lista JSON"
  else
    echo "FALHA /api/tours não devolveu uma lista JSON" >&2
    fail=1
  fi
fi

exit "$fail"
