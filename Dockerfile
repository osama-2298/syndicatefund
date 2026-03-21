# ── Builder stage ──
FROM python:3.11.11-slim AS builder

WORKDIR /app

# System deps for asyncpg and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir poetry==1.8.5

# Copy dependency files first (Docker layer caching)
COPY pyproject.toml poetry.lock* ./

# Install dependencies (no virtualenv in container)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Install the project itself
RUN poetry install --no-interaction --no-ansi --only-root

# ── Runtime stage ──
FROM python:3.11.11-slim

WORKDIR /app

# Runtime deps only (no gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --system syndicate && \
    useradd --system --gid syndicate --create-home syndicate

# Copy installed packages and application from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Startup script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Ensure data dir is writable by syndicate user
RUN mkdir -p /app/data && chown -R syndicate:syndicate /app/data

USER syndicate

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
