# AI Market Intelligence Dashboard — production image
# Multi-stage: build React UI, then run Streamlit + Python backend.

# --- Stage 1: React frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python app ---
FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="AI Market Intelligence Dashboard"
LABEL org.opencontainers.image.description="Streamlit dashboard with Bedrock RAG"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    DEPLOY_ENV=production

WORKDIR /app

# curl for healthcheck; build deps for chromadb wheels if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app.py .
COPY src/ ./src/
COPY .streamlit/ ./.streamlit/
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
COPY --from=frontend-builder /build/frontend/build ./frontend/build/

RUN mkdir -p /app/data && \
    useradd --create-home --uid 10001 appuser && \
    chown -R appuser:appuser /app && \
    chmod +x /docker-entrypoint.sh

USER appuser
VOLUME /app/data
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f "http://127.0.0.1:8501/_stcore/health" || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
