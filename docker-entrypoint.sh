#!/bin/bash
set -e

echo "=== Hivemind Starting ==="

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head 2>/dev/null || echo "Migration skipped (may need initial revision)"

# Seed founding data (idempotent)
echo "Seeding database..."
python -m hivemind.db.seed

# Start the server
echo "Starting Hivemind API server..."
exec python -m hivemind.main --serve
