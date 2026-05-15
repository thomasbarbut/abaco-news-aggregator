# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps needed to compile some wheels (lxml, psycopg2-binary, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libffi-dev \
        libssl-dev \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies into a prefix so we can copy them later
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: final slim image ─────────────────────────────────────────────────
FROM python:3.12-slim AS final

LABEL maintainer="thomas.barbut@abaco.ro"
LABEL description="ABACO News Aggregation Platform – backend API"

WORKDIR /app

# Runtime system libraries (asyncpg needs libssl, playwright needs chromium deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libssl3 \
        libpq5 \
        # Playwright / Chromium dependencies
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpango-1.0-0 \
        libcairo2 \
        libxshmfence1 \
        fonts-liberation \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxext6 \
        wget \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Install Playwright's Chromium browser
RUN playwright install chromium --with-deps 2>/dev/null || \
    (python -m playwright install chromium && python -m playwright install-deps chromium) || true

# Copy application source
COPY . .

# Non-root user for security
RUN useradd -r -u 1001 -g root appuser && chown -R appuser:root /app
USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
