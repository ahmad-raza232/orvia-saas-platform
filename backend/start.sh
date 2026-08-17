#!/usr/bin/env sh
set -eu

# Render Free Web Service entrypoint. Local default port stays 8000.
PORT="${PORT:-8000}"

python -m alembic upgrade head
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
