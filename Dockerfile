# =============================================================================
# Stage 1: Build frontend
# =============================================================================
FROM node:20-slim AS frontend-builder

WORKDIR /app

COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --quiet

COPY apps/web/src ./src
COPY apps/web/index.html ./
COPY apps/web/vite.config.js ./
COPY apps/web/public ./public
RUN npm run build

# =============================================================================
# Stage 2: Production runtime
# =============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 esg && \
    useradd --uid 1000 --gid esg --shell /bin/bash --create-home esg

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache -e .

COPY --chown=esg:esg src/ ./src/
COPY --from=frontend-builder --chown=esg:esg /app/dist ./static

RUN chown -R esg:esg /app

USER esg

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["gunicorn", "src.api.main:app", "--bind", "0.0.0.0:8000", "--workers", "4"]
