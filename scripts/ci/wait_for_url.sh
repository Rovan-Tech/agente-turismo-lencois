#!/usr/bin/env bash
# Espera uma URL responder 2xx. Uso: wait_for_url.sh <url> [segundos=60]
set -euo pipefail

url="${1:?uso: wait_for_url.sh <url> [segundos]}"
timeout="${2:-60}"
deadline=$((SECONDS + timeout))

until curl --fail --silent --show-error --max-time 5 --output /dev/null "$url" 2>/dev/null; do
  if ((SECONDS >= deadline)); then
    echo "::error::$url não respondeu em ${timeout}s" >&2
    exit 1
  fi
  sleep 1
done
echo "$url no ar"
