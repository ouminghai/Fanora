#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying Fanora database migrations"
  /app/.venv/bin/alembic upgrade head
fi

exec "$@"

