#!/bin/sh
set -e

echo "Running migrations..."
alembic upgrade head

echo "Starting FastAPI..."
exec hypercorn app.main:app --bind 0.0.0.0:8000