"""
Minimal ShowRunner-managed application.

This is ALL the code you need to make an app work with ShowRunner:
- Reads config from /config/app.json (or SHOWRUNNER_CONFIG_PATH)
- Re-reads config on SIGHUP (sent by ShowRunner for live updates)
- Exposes Prometheus metrics on :9090/metrics
- Exposes health on :9090/healthz

Run:  python minimal_app.py
Test: curl localhost:9090/metrics
      curl localhost:9090/healthz
      kill -HUP <pid>    # triggers config reload
"""

import time
from showrunner_sdk import config, metrics, health

# ── 1. Load config (auto-reads /config/app.json) ──
cfg = config.load()

# Optional: react to config changes
def on_config_change(new_cfg):
    print(f"Config updated: {new_cfg}")

config.on_reload(on_config_change)

# ── 2. Register app-specific metrics ──
rps_gauge = metrics.gauge("attack_rps", "Current requests per second")
requests_total = metrics.counter("requests_total", "Total requests sent")

# Set app metadata (shows up as app_info metric)
metrics.set_app_info(name="my-app", version="1.0.0")

# ── 3. Start metrics server ──
metrics.start_server()  # port 9090 by default
health.set_status("running")

# ── 4. Your app logic ──
print(f"Running with config: {cfg}")
while True:
    rps_gauge.set(100)
    requests_total.inc()
    time.sleep(1)
