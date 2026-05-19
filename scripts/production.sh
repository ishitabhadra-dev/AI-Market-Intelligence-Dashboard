#!/usr/bin/env bash
# Production process manager (no Docker): start | stop | restart | status | logs
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PIDFILE="${ROOT}/data/dashboard.pid"
LOGFILE="${ROOT}/logs/dashboard.log"
PORT="${PORT:-8501}"

die() { echo "ERROR: $*" >&2; exit 1; }

ensure_ready() {
  [[ -d .venv ]] || die "Run ./scripts/production_install.sh first"
  [[ -f .venv/bin/streamlit ]] || die "Missing streamlit in .venv"
  mkdir -p data logs
}

start_app() {
  ensure_ready
  if [[ -f "$PIDFILE" ]]; then
    pid=$(cat "$PIDFILE")
    if kill -0 "$pid" 2>/dev/null; then
      echo "Already running (PID $pid) — http://localhost:${PORT}"
      exit 0
    fi
    rm -f "$PIDFILE"
  fi

  export DEPLOY_ENV="${DEPLOY_ENV:-production}"
  export PORT
  export STREAMLIT_SERVER_ADDRESS="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"
  export STREAMLIT_SERVER_PORT="${PORT}"
  export STREAMLIT_SERVER_HEADLESS=true
  export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

  # shellcheck source=/dev/null
  source .venv/bin/activate

  echo "Starting production dashboard on http://localhost:${PORT}"
  nohup streamlit run app.py \
    --server.port="${PORT}" \
    --server.address="${STREAMLIT_SERVER_ADDRESS}" \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    >>"$LOGFILE" 2>&1 &

  echo $! >"$PIDFILE"
  sleep 2
  if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Started (PID $(cat "$PIDFILE")). Logs: $LOGFILE"
  else
    rm -f "$PIDFILE"
    die "Failed to start. Check $LOGFILE"
  fi
}

stop_app() {
  if [[ ! -f "$PIDFILE" ]]; then
    echo "Not running (no pid file)."
    exit 0
  fi
  pid=$(cat "$PIDFILE")
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    sleep 1
    kill -9 "$pid" 2>/dev/null || true
    echo "Stopped (PID $pid)."
  else
    echo "Process $pid not found."
  fi
  rm -f "$PIDFILE"
}

status_app() {
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "running — PID $(cat "$PIDFILE") — http://localhost:${PORT}"
    exit 0
  fi
  echo "stopped"
  exit 1
}

case "${1:-}" in
  start) start_app ;;
  stop) stop_app ;;
  restart) stop_app || true; start_app ;;
  status) status_app ;;
  logs) tail -f "$LOGFILE" ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
