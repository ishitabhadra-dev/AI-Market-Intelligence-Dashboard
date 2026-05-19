#!/usr/bin/env bash
# Foreground Streamlit for launchd/systemd (loads .env, production flags).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

export DEPLOY_ENV="${DEPLOY_ENV:-production}"
export PORT="${PORT:-8501}"

exec "${ROOT}/.venv/bin/streamlit" run app.py \
  --server.port="${PORT}" \
  --server.address="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}" \
  --server.headless=true \
  --browser.gatherUsageStats=false
