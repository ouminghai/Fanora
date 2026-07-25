#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying Fanora database migrations"
  /app/.venv/bin/alembic upgrade head
fi

if [ "${1:-}" = "/app/.venv/bin/uvicorn" ]; then
  set -- "$@" --port "${PORT:-8000}"
fi

exec "$@"
