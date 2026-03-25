# showrunner-sdk

Make any app ShowRunner-managed in 3 steps.

Replaces Container Control — no adapters, no config.yaml, no framework wrapping your app. Your app stays in control; the SDK is just a library it imports.

## What you get

| Feature | How | Port |
|---------|-----|------|
| **Config injection** | JSON file mounted at `/config/app.json` | — |
| **Live config reload** | ShowRunner sends `SIGHUP` → SDK re-reads the file | — |
| **Prometheus metrics** | Base (CPU, mem, uptime) + your custom metrics | 9090 |
| **Health endpoint** | `/healthz` with status + uptime | 9090 |

## Quick start

### 1. Install

```dockerfile
# In your Dockerfile
RUN pip install showrunner-sdk[full]
```

Or use the base image:
```dockerfile
FROM showrunner-sdk:0.1.0
```

### 2. Integrate (5-10 lines in your app)

```python
from showrunner_sdk import config, metrics, health

# Load config (reads /config/app.json, reloads on SIGHUP)
cfg = config.load()
config.on_reload(lambda c: apply_new_config(c))  # optional

# Register your metrics
rps = metrics.gauge("attack_rps", "Current RPS")
total = metrics.counter("requests_total", "Total requests")

# Start metrics server + set health
metrics.start_server()  # :9090/metrics + :9090/healthz
health.set_status("running")

# Your app runs normally — you own the process
```

### 3. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt  # includes showrunner-sdk

COPY . .
RUN mkdir -p /config

EXPOSE 9090
ENTRYPOINT ["python", "your_app.py"]  # YOUR app is the entrypoint
```

That's it. ShowRunner handles the rest:
- Writes config to the `/config` volume before starting your container
- Sends `SIGHUP` for live config updates
- Scrapes `http://container:9090/metrics` for Prometheus data
- Checks `http://container:9090/healthz` for health

## How ShowRunner manages your container

```
ShowRunner                              Your Container
─────────                              ──────────────
1. Write /config/app.json ──volume──→  config.load() on startup
2. docker start ─────────────────────→ App starts, reads config
3. SIGHUP (config update) ──signal──→  config re-reads file, calls callbacks
4. GET :9090/metrics ────────────────→ Prometheus data
5. GET :9090/healthz ────────────────→ {"status": "running", "uptime": 42.1}
6. docker stop ──────────────────────→ App stops gracefully
```

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SHOWRUNNER_CONFIG_PATH` | `/config/app.json` | Config file location |
| `SHOWRUNNER_METRICS_PORT` | `9090` | Metrics/health server port |

## Custom metrics examples

```python
from showrunner_sdk import metrics

# Gauge — current value
rps = metrics.gauge("attack_rps", "Requests per second")
rps.set(150)

# Counter — cumulative total
errors = metrics.counter("errors_total", "Total errors")
errors.inc()

# Histogram — distribution of values
latency = metrics.histogram(
    "request_duration_seconds",
    "Request latency",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)
latency.observe(0.23)

# Labels
rps_by_method = metrics.gauge("rps_by_method", "RPS by HTTP method", labels=["method"])
rps_by_method.labels(method="GET").set(100)
rps_by_method.labels(method="POST").set(50)

# App info metadata
metrics.set_app_info(name="traffic-generator", version="1.0.7")
```

## Migration from Container Control

**Before (CC):**
- Clone container-control repo in Dockerfile
- Write config.yaml (12+ lines)
- Write adapter class (30-100 lines)
- CC is your entrypoint
- CC owns the process lifecycle

**After (SDK):**
- `pip install showrunner-sdk`
- 5-10 lines in your existing code
- Your app is the entrypoint
- You own your process

### Files to delete
- `config.yaml`
- `*_adapter.py`
- `container_control_core.py` (if copied)
- `git clone` of container-control in Dockerfile
