#!/usr/bin/env bash
# Production-style local start (after venv + frontend build).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Create a venv first: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [[ ! -f frontend/build/index.html ]]; then
  echo "React build missing. Run: ./scripts/build_frontend.sh"
  exit 1
fi

mkdir -p data
export DEPLOY_ENV="${DEPLOY_ENV:-production}"
export PORT="${PORT:-8501}"
export STREAMLIT_SERVER_ADDRESS="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"

echo "Starting on http://localhost:${PORT}"
exec streamlit run app.py \
  --server.port="${PORT}" \
  --server.address="${STREAMLIT_SERVER_ADDRESS}" \
  --server.headless=true \
  --browser.gatherUsageStats=false
