#!/usr/bin/env bash
# Sobe a API com um SQLite descartável (migrations + catálogo) para os testes de fumaça, o fuzz
# de contrato, o DAST e a carga. Não usa segredo nenhum. Uso, na raiz do repositório:
#   scripts/ci/start_api.sh        # deixa a API em 127.0.0.1:${PORT:-8000}; PID em $WORKDIR/api.pid
set -euo pipefail

port="${PORT:-8000}"
workdir="${WORKDIR:-$(mktemp -d)}"
mkdir -p "$workdir"

export DATABASE_URL="sqlite+aiosqlite:///$workdir/ci.db"
export DASHBOARD_API_TOKEN="${DASHBOARD_API_TOKEN:-ci-dashboard-token}"
export FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-http://localhost:4173}"
python_bin="${PYTHON:-python}"

cd backend
"$python_bin" -m alembic upgrade head
"$python_bin" -m app.seed
nohup "$python_bin" -m uvicorn app.main:app --host 127.0.0.1 --port "$port" \
  >"$workdir/api.log" 2>&1 &
echo $! >"$workdir/api.pid"
cd ..

if [ -n "${GITHUB_ENV:-}" ]; then
  echo "API_WORKDIR=$workdir" >>"$GITHUB_ENV"
  echo "API_URL=http://127.0.0.1:$port" >>"$GITHUB_ENV"
fi
scripts/ci/wait_for_url.sh "http://127.0.0.1:$port/health" 60 || {
  echo "--- log da API ---" >&2
  cat "$workdir/api.log" >&2
  exit 1
}
echo "API em http://127.0.0.1:$port (log: $workdir/api.log)"
