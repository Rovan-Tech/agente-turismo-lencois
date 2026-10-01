#!/usr/bin/env bash
# Valida as migrations num PostgreSQL de verdade: sobe tudo, confere que o modelo e o banco
# batem (`alembic check`), desce até a base e sobe de novo (reversibilidade).
# Uso: DATABASE_URL=postgresql+asyncpg://... scripts/ci/check_migrations.sh
set -euo pipefail

: "${DATABASE_URL:?defina DATABASE_URL apontando para um banco VAZIO}"
python_bin="${PYTHON:-python}"

cd backend
echo "== upgrade head"
"$python_bin" -m alembic upgrade head
echo "== check (modelo x banco)"
"$python_bin" -m alembic check
echo "== downgrade base"
"$python_bin" -m alembic downgrade base
echo "== upgrade head de novo"
"$python_bin" -m alembic upgrade head
echo "migrations ok"
