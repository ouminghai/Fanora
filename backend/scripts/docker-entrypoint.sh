#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  attempts="${MIGRATION_MAX_ATTEMPTS:-5}"
  delay="${MIGRATION_RETRY_DELAY_SECONDS:-2}"
  current=1

  while [ "$current" -le "$attempts" ]; do
    echo "Applying Fanora database migrations, attempt ${current}/${attempts}"
    if /app/.venv/bin/alembic upgrade head; then
      break
    fi

    if [ "$current" -eq "$attempts" ]; then
      echo "Fanora database migrations failed after ${attempts} attempts"
      exit 1
    fi

    current=$((current + 1))
    sleep "$delay"
  done
fi

if [ "${1:-}" = "/app/.venv/bin/uvicorn" ]; then
  set -- "$@" --port "${PORT:-8000}"
fi

exec "$@"
