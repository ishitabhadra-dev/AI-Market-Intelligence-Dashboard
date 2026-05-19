#!/usr/bin/env bash
# Build React components for Streamlit (requires Node.js 18+).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"

find_npm() {
  if command -v npm >/dev/null 2>&1; then
    command -v npm
    return 0
  fi
  for candidate in \
    /opt/homebrew/bin/npm \
    /usr/local/bin/npm \
    "$HOME/.nvm/versions/node/"*/bin/npm; do
    if [[ -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

NPM="$(find_npm || true)"

if [[ -z "$NPM" ]]; then
  echo "ERROR: npm not found. Install Node.js first, then re-run this script."
  echo ""
  echo "Option A — Homebrew (recommended on Mac):"
  echo "  brew install node"
  echo ""
  echo "Option B — Official installer:"
  echo "  https://nodejs.org/  (download LTS, then restart Terminal)"
  echo ""
  echo "Option C — nvm:"
  echo "  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"
  echo "  # restart Terminal, then:"
  echo "  nvm install --lts"
  echo ""
  echo "Verify:"
  echo "  node -v && npm -v"
  echo ""
  echo "Then run:"
  echo "  ./scripts/build_frontend.sh"
  exit 1
fi

echo "Using npm: $NPM"
"$NPM" install
"$NPM" run build
echo ""
echo "Done. React build is at frontend/build/"
echo "Start the app: streamlit run app.py"
