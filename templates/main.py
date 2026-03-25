"""
Template ShowRunner-managed entry point.

Copy this to your project and adapt the YOUR_APP sections.
"""

import signal
import logging
import threading

from showrunner_sdk import config, metrics, health

logger = logging.getLogger("my-app")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── SDK: Load config from /config/app.json ──
cfg = config.load()

# ── SDK: Register app-specific metrics ──
# Replace these with your actual metrics:
rps_gauge = metrics.gauge("my_app_rps", "Current requests per second")
total_counter = metrics.counter("my_app_requests_total", "Total requests processed")
# Optional: set app metadata
metrics.set_app_info(name="my-app", version="1.0.0")

# ── SDK: Start metrics server (:9090/metrics + :9090/healthz) ──
metrics.start_server()

# ──────────────────────────────────────────────
# YOUR APP: Initialize and start your workload
# ──────────────────────────────────────────────

def start_workload(cfg_data):
    """Start your app's main work based on config."""
    health.set_status("running")
    logger.info("Starting workload with config: %s", cfg_data)
    # TODO: your app logic here
    # Example:
    #   generator = MyGenerator(cfg_data)
    #   generator.start()


def stop_workload():
    """Stop your app's work gracefully."""
    health.set_status("stopped")
    logger.info("Workload stopped")
    # TODO: your cleanup here


# ── SDK: React to config changes (SIGHUP) ──
def on_config_reload(new_cfg):
    logger.info("Config reloaded, restarting workload")
    stop_workload()
    start_workload(new_cfg)

config.on_reload(on_config_reload)

# ── Start ──
if cfg:
    start_workload(cfg)
else:
    health.set_status("waiting", reason="no config file")
    logger.info("No config at %s — waiting for SIGHUP", config.CONFIG_PATH)

# ── Keep alive until SIGTERM/SIGINT ──
shutdown = threading.Event()

def handle_shutdown(signum, frame):
    logger.info("Shutdown signal received")
    stop_workload()
    shutdown.set()

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)
shutdown.wait()
