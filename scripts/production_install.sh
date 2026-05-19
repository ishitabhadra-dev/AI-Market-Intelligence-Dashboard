#!/usr/bin/env bash
# One-time production setup (no Docker required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> AI Market Intelligence — production install"
echo "    Project: $ROOT"

# --- Python venv ---
if [[ ! -d .venv ]]; then
  echo "==> Creating virtualenv (.venv)"
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# --- Environment ---
if [[ ! -f .env ]]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
  echo "    Edit .env with your AWS_REGION and Bedrock model IDs before starting."
fi

# --- React build ---
if [[ -f frontend/build/index.html ]]; then
  echo "==> React build already present (frontend/build/)"
else
  if command -v npm >/dev/null 2>&1; then
    echo "==> Building React frontend"
    ./scripts/build_frontend.sh
  else
    echo "WARN: npm not found — app will use Streamlit fallback widgets."
    echo "      Install Node.js later and run: ./scripts/build_frontend.sh"
  fi
fi

mkdir -p data logs
chmod +x scripts/*.sh 2>/dev/null || true

echo ""
echo "==> Install complete."
echo "    Next: edit .env, then run:  ./scripts/production.sh start"
echo "    URL:  http://localhost:8501"
