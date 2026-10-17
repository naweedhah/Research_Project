#!/usr/bin/env bash
# Local run without Docker. Requires Homebrew PostgreSQL (already running on this Mac).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

# Local hostnames (compose uses postgres/redis service names)
python3 - <<'PY'
from pathlib import Path
p = Path(".env")
text = p.read_text()
text = text.replace("@postgres:5432", "@localhost:5432").replace("redis://redis:", "redis://localhost:")
p.write_text(text)
PY

export PATH="/opt/homebrew/opt/postgresql@14/bin:/opt/homebrew/opt/postgresql@16/bin:$PATH"
psql -d postgres -v ON_ERROR_STOP=1 -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cnip') THEN CREATE ROLE cnip LOGIN PASSWORD 'cnip_dev_password' SUPERUSER; END IF; END \$\$;"
psql -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'cnip'" | grep -q 1 || createdb -O cnip cnip

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r services/api/requirements.txt
.venv/bin/pip install -q fastapi uvicorn pydantic pydantic-settings numpy pyyaml httpx

cd "$ROOT/services/api"
PYTHONPATH="$ROOT/services/api:$ROOT" "$ROOT/.venv/bin/alembic" upgrade head
PYTHONPATH="$ROOT/services/api:$ROOT" "$ROOT/.venv/bin/python" -m app.seed
cd "$ROOT"

echo "Starting inference :8001, API :8000, web :3000"
echo "Open http://localhost:3000  (doctor@demo.local / DemoPass123!)"
