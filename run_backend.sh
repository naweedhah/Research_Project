#!/usr/bin/env bash
# Start the integrated backend (all four components) on http://localhost:8000 — API docs at /docs.
# Usage: ./run_backend.sh            (Ctrl+C to stop)
#        PORT=8001 ./run_backend.sh   C3_DATA_DIR=/other/folder ./run_backend.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8000}"
export C3_DATA_DIR="${C3_DATA_DIR:-$HOME/Downloads/clean_malnutrition_data}"

# First Python environment that has every backend package.
PY=""
for env in "$ROOT/backend/.venv" "$ROOT/components/c3_reliability_maintenance/.venv"; do
  if [ -x "$env/bin/python" ] && "$env/bin/python" -c "import fastapi, uvicorn, sklearn, dice_ml, jwt, pwdlib, reportlab" 2>/dev/null; then
    PY="$env/bin/python"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "No Python environment with the backend packages. Set one up once:"
  echo "  cd $ROOT/backend && python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

if lsof -i ":$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use (another backend, or C1's Docker API without the integrated file)."
  echo "Stop that program or run: PORT=8001 $0"
  exit 1
fi
[ -f "$C3_DATA_DIR/PHM_prediction_2025_to_2026.csv" ] || echo "Note: C3 data not found in $C3_DATA_DIR (C3 endpoints will report not ready)."

echo "Backend: http://localhost:$PORT   API docs: http://localhost:$PORT/docs   (Ctrl+C to stop)"
cd "$ROOT/backend"
exec "$PY" -m uvicorn app.main:app --port "$PORT"
