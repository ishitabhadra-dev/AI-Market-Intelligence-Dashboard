#!/usr/bin/env bash
# Build and run the dashboard with Docker Compose.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

find_docker() {
  if command -v docker >/dev/null 2>&1; then
    command -v docker
    return 0
  fi
  if [[ -x /Applications/Docker.app/Contents/Resources/bin/docker ]]; then
    echo "/Applications/Docker.app/Contents/Resources/bin/docker"
    return 0
  fi
  if [[ -x /usr/local/bin/docker ]]; then
    echo "/usr/local/bin/docker"
    return 0
  fi
  return 1
}

DOCKER="$(find_docker || true)"
if [[ -z "$DOCKER" ]]; then
  echo "Docker is not installed or not running."
  echo ""
  echo "Install Docker Desktop for Mac:"
  echo "  https://www.docker.com/products/docker-desktop/"
  echo ""
  echo "Or:  brew install --cask docker"
  echo "Then open Docker.app from Applications and wait until it says 'Running'."
  exit 1
fi

if ! "$DOCKER" info >/dev/null 2>&1; then
  echo "Docker is installed but the daemon is not running."
  echo "Open Docker Desktop and wait until the whale icon shows 'Running', then retry."
  exit 1
fi

# Prefer 'docker compose' (v2 plugin)
if "$DOCKER" compose version >/dev/null 2>&1; then
  COMPOSE=("$DOCKER" compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "ERROR: docker compose plugin not found. Update Docker Desktop."
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Creating .env from .env.example — edit it with your AWS/Bedrock settings."
  cp .env.example .env
fi

# Empty AWS_PROFILE breaks boto3 inside containers
if grep -q '^AWS_PROFILE=$' .env 2>/dev/null; then
  sed -i.bak '/^AWS_PROFILE=$/d' .env && rm -f .env.bak
  echo "Removed empty AWS_PROFILE from .env (not needed in Docker)."
fi

echo "==> Building and starting (first build may take 3–5 minutes)..."
"${COMPOSE[@]}" up --build -d

echo ""
echo "==> Dashboard starting at http://localhost:${PORT:-8501}"
echo "    Logs:    ${COMPOSE[*]} logs -f"
echo "    Stop:    ${COMPOSE[*]} down"
echo "    Status:  ${COMPOSE[*]} ps"
