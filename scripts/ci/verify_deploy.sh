#!/usr/bin/env bash
# Confere a revisão recém-publicada do Cloud Run e, se ela não ficar saudável, devolve o tráfego
# para a revisão anterior (rollback automático). Tolera cold start: tenta algumas vezes.
# Uso: verify_deploy.sh <url> <serviço> <região> <revisão-anterior|""> [token-do-painel]
set -euo pipefail

url="${1:?uso: verify_deploy.sh <url> <serviço> <região> <revisão-anterior> [token]}"
service="${2:?}"
region="${3:?}"
previous="${4:-}"
token="${5:-}"

gcloud_bin="${GCLOUD_BIN:-gcloud}"
smoke="${SMOKE_SCRIPT:-$(dirname "$0")/smoke.sh}"
attempts="${VERIFY_ATTEMPTS:-6}"
delay="${VERIFY_DELAY:-10}"

for attempt in $(seq 1 "$attempts"); do
  if "$smoke" "$url" "$token"; then
    echo "A revisão nova está saudável (tentativa $attempt/$attempts)."
    exit 0
  fi
  echo "Teste de fumaça falhou (tentativa $attempt/$attempts)."
  [ "$attempt" -lt "$attempts" ] && sleep "$delay"
done

echo "::error::A revisão nova reprovou no teste de fumaça."
if [ -n "$previous" ]; then
  "$gcloud_bin" run services update-traffic "$service" --region "$region" --to-revisions "$previous=100"
  echo "Tráfego devolvido para a revisão anterior: $previous."
else
  echo "::warning::Não há revisão anterior registrada; o tráfego não foi alterado (sem revisão anterior para voltar)."
fi
exit 1
