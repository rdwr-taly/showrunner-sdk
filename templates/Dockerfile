# Template Dockerfile for a ShowRunner-managed application.
#
# What you get:
#   - showrunner-sdk installed (config + metrics + health)
#   - Config mount at /config/app.json
#   - Prometheus metrics on :9090
#   - Health check on :9090/healthz
#   - Non-root user

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install your app's dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY . .

# Non-root user
RUN adduser --disabled-login --gecos "" appuser \
 && chown -R appuser:appuser /app

# Config mount point (ShowRunner writes config here before starting)
RUN mkdir -p /config && chown appuser:appuser /config

USER appuser

# SDK metrics + health port
EXPOSE 9090

# Your app is the entrypoint — it owns the process
ENTRYPOINT ["python", "main.py"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD curl -sf http://127.0.0.1:9090/healthz || exit 1
