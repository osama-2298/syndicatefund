#!/bin/bash

echo "=== Hivemind Starting ==="
echo "PORT: ${PORT:-8000}"

# Create tables + seed founding data (idempotent)
echo "Setting up database..."
python -m hivemind.db.seed 2>&1 || echo "WARNING: DB setup failed — server will start without DB"

# Start the server
echo "Starting Hivemind API server..."
exec python -m hivemind.main --serve
