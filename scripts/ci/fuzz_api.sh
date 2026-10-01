#!/usr/bin/env bash
# Fuzz do contrato OpenAPI com o schemathesis contra uma API já no ar.
# Uso: fuzz_api.sh <url-da-api> [token-do-painel]
#
# No PR o portão exige o que protege o serviço: nenhuma resposta 5xx, resposta sempre dentro do
# schema e do content-type declarados, cabeçalhos coerentes e sem recurso fantasma depois de
# apagado. Os checks de documentação do contrato (status não declarado, `Allow`) e de rejeição de
# campo extra rodam todos no noturno (FUZZ_CHECKS=all) e estão em docs/tech-debt.md.
set -euo pipefail

url="${1:?uso: fuzz_api.sh <url-da-api> [token]}"
token="${2:-ci-dashboard-token}"
checks="${FUZZ_CHECKS:-not_a_server_error,content_type_conformance,response_headers_conformance,response_schema_conformance,missing_required_header,use_after_free,ensure_resource_availability}"
examples="${FUZZ_EXAMPLES:-50}"
schemathesis_bin="${SCHEMATHESIS_BIN:-schemathesis}"

exec "$schemathesis_bin" run "$url/openapi.json" --url "$url" \
  -H "Authorization: Bearer $token" \
  --checks "$checks" --max-examples "$examples" --workers 2 --no-color
