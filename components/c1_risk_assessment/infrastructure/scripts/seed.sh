#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../services/api"
alembic upgrade head
python -m app.seed
python -m app.enrich_demo
