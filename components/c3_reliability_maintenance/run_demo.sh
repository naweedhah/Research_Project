#!/usr/bin/env bash
# Start the integrated backend and open the Component 3 model-health dashboard.
# Usage: ./run_demo.sh            (Ctrl+C to stop)
#        PORT=8001 ./run_demo.sh  C3_DATA_DIR=/other/folder ./run_demo.sh
set -euo pipefail

C3_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$C3_DIR/../../backend"
PY="$C3_DIR/.venv/bin/python"
PORT="${PORT:-8000}"
export C3_DATA_DIR="${C3_DATA_DIR:-$HOME/Downloads/clean_malnutrition_data}"
URL="http://localhost:$PORT/maintenance/dashboard"

if [ ! -x "$PY" ]; then
  echo "No .venv found. Set it up once:"
  echo "  cd $C3_DIR && python3.13 -m venv .venv"
  echo "  .venv/bin/pip install -e '.[dev,experiments]' -r ../../backend/requirements.txt"
  exit 1
fi
if [ ! -f "$C3_DATA_DIR/PHM_prediction_2025_to_2026.csv" ]; then
  echo "Data not found: $C3_DATA_DIR/PHM_prediction_2025_to_2026.csv (set C3_DATA_DIR)"
  exit 1
fi
if lsof -i ":$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Stop that program or run: PORT=8001 $0"
  exit 1
fi

cd "$BACKEND_DIR"
"$PY" -m uvicorn app.main:app --port "$PORT" &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT INT TERM

# The first status call trains the stand-in model; do it now, not in front of the panel.
echo "Starting server and preparing the model..."
for _ in $(seq 1 120); do
  if curl -sf "http://localhost:$PORT/maintenance/status" | grep -q '"ready":true'; then
    echo "Ready: $URL"
    open "$URL" 2>/dev/null || true
    wait $SERVER
    exit 0
  fi
  kill -0 $SERVER 2>/dev/null || { echo "Server stopped unexpectedly (see messages above)."; exit 1; }
  sleep 1
done
echo "Model did not become ready within 2 minutes."
exit 1
