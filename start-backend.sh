#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BACKEND_DIR="$PROJECT_DIR/backend"

if command -v uv >/dev/null 2>&1; then
  UV_BIN=uv
elif [ -x "$HOME/.local/bin/uv" ]; then
  UV_BIN="$HOME/.local/bin/uv"
else
  echo "uv is not installed. Install it with:"
  echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "Missing backend/.env"
  echo "Create it first with: cp backend/.env.example backend/.env"
  exit 1
fi

cd "$BACKEND_DIR"

echo "Using $("$UV_BIN" --version)"
echo "Synchronizing backend dependencies"
"$UV_BIN" sync --all-extras --group dev

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying database migrations"
  "$UV_BIN" run python -m app.core.migrations
fi

HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}
RELOAD=${RELOAD:-true}

set -- app.main:app --host "$HOST" --port "$PORT"
if [ "$RELOAD" = "true" ]; then
  set -- "$@" --reload
fi

echo "Starting Fanora backend at http://$HOST:$PORT"
exec "$UV_BIN" run uvicorn "$@"
