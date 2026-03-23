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

# Install system deps
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (production - no TensorFlow)
COPY backend/requirements-prod.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend — main.py looks 3 levels up from app/main.py = /frontend/dist
COPY --from=frontend-builder /app/frontend/dist /frontend/dist

# Persistent data directory
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["gunicorn", "app.main:app", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120"]
