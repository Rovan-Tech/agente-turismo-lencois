#!/usr/bin/env bash
# Imprime a revisão do Cloud Run que atende o tráfego hoje (alvo do rollback automático).
# No primeiro deploy, quando o serviço ainda não existe, não imprime nada e só avisa. Qualquer
# outro erro do gcloud falha o script: sem revisão anterior o rollback não teria para onde voltar.
# Uso: previous_revision.sh <serviço> <região>
set -euo pipefail

service="${1:?uso: previous_revision.sh <serviço> <região>}"
region="${2:?}"
gcloud_bin="${GCLOUD_BIN:-gcloud}"

errors="$(mktemp)"
trap 'rm -f "$errors"' EXIT

# stdout (a revisão) e stderr (avisos e erros do gcloud) ficam separados.
if revision="$("$gcloud_bin" run services describe "$service" --region "$region" \
  --format='value(status.traffic[0].revisionName)' 2>"$errors")"; then
  printf '%s\n' "${revision%%$'\n'*}"
  exit 0
fi

if grep -qiE 'cannot find service|service \[[^]]*\] could not be found' "$errors"; then
  echo "::warning::Serviço $service ainda não existe: primeiro deploy, sem revisão para o rollback." >&2
  exit 0
fi

cat "$errors" >&2
exit 1
