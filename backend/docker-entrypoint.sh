#!/bin/sh
set -e
# Apply schema migrations before serving. Safe to run on every start.
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*' --workers "${WEB_CONCURRENCY:-2}"
