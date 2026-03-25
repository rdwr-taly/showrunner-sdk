# Base image for ShowRunner-managed applications.
# Apps can use this as their base: FROM showrunner-sdk:0.1.0
#
# What you get for free:
#   - showrunner-sdk installed (config + metrics + health)
#   - psutil for process metrics
#   - /config/ directory ready for volume mount
#   - Non-root user 'app'
#   - SIGHUP handler for live config reload
#   - Prometheus metrics on port 9090

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -g app -m app

WORKDIR /app

COPY pyproject.toml .
COPY showrunner_sdk/ showrunner_sdk/
RUN pip install --no-cache-dir ".[full]"

RUN mkdir -p /config && chown app:app /config

EXPOSE 9090

USER app
