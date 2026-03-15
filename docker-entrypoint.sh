#!/bin/bash

echo "=== Hivemind Starting ==="
echo "DATABASE_URL: ${DATABASE_URL:-(not set)}"
echo "PORT: ${PORT:-8000}"

# Run database migrations (don't crash if DB not ready)
echo "Running database migrations..."
python -m alembic upgrade head 2>&1 || echo "WARNING: Migration failed — will retry on next deploy"

# Seed founding data (idempotent, don't crash if DB not ready)
echo "Seeding database..."
python -m hivemind.db.seed 2>&1 || echo "WARNING: Seed failed — will retry on next deploy"

# Start the server (this must succeed)
echo "Starting Hivemind API server..."
exec python -m hivemind.main --serve
