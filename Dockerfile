# ── Stage 1: Build React frontend ───────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install --production=false

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + serve frontend ────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (production — no TensorFlow)
COPY backend/requirements-prod.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend — main.py looks at /frontend/dist
COPY --from=frontend-builder /app/frontend/dist /frontend/dist

# Persistent data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/healthz || exit 1

# Single worker: background threads (prediction_tracker daemon, etc.) must
# start inside the worker process. Without --preload the worker imports the
# app fresh after fork, so daemon threads start correctly.
# 300 s timeout accommodates slow first ML predictions on cold starts.
CMD ["sh", "-c", "gunicorn app.main:app \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout 300 \
    --keep-alive 120 \
    --access-logfile - \
    --error-logfile -"]
