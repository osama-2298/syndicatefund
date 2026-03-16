#!/bin/bash

echo "=== Syndicate Starting ==="
echo "PORT: ${PORT:-8000}"

# Create tables + seed founding data (idempotent)
echo "Setting up database..."
python -m syndicate.db.seed 2>&1 || echo "WARNING: DB setup failed — server will start without DB"

# Start the server
echo "Starting Syndicate API server..."
exec python -m syndicate.main --serve
