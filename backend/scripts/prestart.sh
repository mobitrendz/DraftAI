#!/bin/bash
set -e

echo "Running migrations..."
uv run alembic upgrade head

echo "Seeding initial data..."
uv run python -m app.db.initial_data

echo "Prestart complete."
