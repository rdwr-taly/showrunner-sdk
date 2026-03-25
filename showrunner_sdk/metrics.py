"""
Metrics module — Prometheus /metrics endpoint with automatic base metrics.

Usage:
    from showrunner_sdk import metrics

    # App-specific metrics
    rps = metrics.gauge("attack_rps", "Current requests per second")
    rps.set(42)

    total = metrics.counter("requests_total", "Total HTTP requests sent")
    total.inc()

    latency = metrics.histogram("request_duration_seconds", "Request latency")
    latency.observe(0.23)

    # Start the metrics server (call once, usually in main)
    metrics.start_server(port=9090)
"""

import os
import time
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from showrunner_sdk.health import health

logger = logging.getLogger("showrunner.metrics")

METRICS_PORT = int(os.environ.get("SHOWRUNNER_METRICS_PORT", "9090"))


class _Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self._start_time = time.time()
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

        # ── Base metrics (free for every app) ──
        self._uptime = Gauge(
            "app_uptime_seconds",
            "Seconds since process start",
            registry=self.registry,
        )
        self._config_reloads = Counter(
            "config_reloads_total",
            "Number of config reloads (SIGHUP)",
            registry=self.registry,
        )
        self._app_info = Info(
            "app",
            "Application metadata",
            registry=self.registry,
        )

        # CPU/memory collected lazily on scrape via a callback
        self._cpu_gauge = Gauge(
            "process_cpu_percent",
            "Process CPU usage percent",
            registry=self.registry,
        )
        self._memory_gauge = Gauge(
            "process_memory_mb",
            "Process resident memory in MB",
            registry=self.registry,
        )

    # ── Public API: create app-specific metrics ──

    def gauge(self, name: str, description: str, labels: list[str] | None = None) -> Gauge:
        return Gauge(name, description, labelnames=labels or [], registry=self.registry)

    def counter(self, name: str, description: str, labels: list[str] | None = None) -> Counter:
        return Counter(name, description, labelnames=labels or [], registry=self.registry)

    def histogram(
        self,
        name: str,
        description: str,
        buckets: tuple | None = None,
        labels: list[str] | None = None,
    ) -> Histogram:
        kwargs: dict[str, Any] = {"labelnames": labels or [], "registry": self.registry}
        if buckets:
            kwargs["buckets"] = buckets
        return Histogram(name, description, **kwargs)

    def set_app_info(self, **labels: str) -> None:
        """Set app metadata (name, version, etc.)."""
        self._app_info.info(labels)

    # ── Metrics server ──

    def start_server(self, port: int | None = None) -> None:
        """Start the HTTP metrics server in a background thread."""
        port = port or METRICS_PORT
        if self._server is not None:
            logger.warning("Metrics server already running")
            return

        # Wire up config reload counter
        from showrunner_sdk.config import config
        config.on_reload(lambda _: self._config_reloads.inc())

        handler = self._make_handler()
        self._server = HTTPServer(("0.0.0.0", port), handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="showrunner-metrics",
            daemon=True,
        )
        self._thread.start()
        logger.info("Metrics server listening on :%d", port)

    def stop_server(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None

    def _collect_process_metrics(self) -> None:
        """Snapshot CPU/memory — called on each /metrics scrape."""
        self._uptime.set(time.time() - self._start_time)
        try:
            import psutil
            proc = psutil.Process()
            self._cpu_gauge.set(proc.cpu_percent(interval=None))
            self._memory_gauge.set(proc.memory_info().rss / 1024 / 1024)
        except ImportError:
            pass  # psutil optional — base metrics still work

    def _make_handler(self) -> type:
        metrics_ref = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/metrics":
                    metrics_ref._collect_process_metrics()
                    output = generate_latest(metrics_ref.registry)
                    self.send_response(200)
                    self.send_header("Content-Type", CONTENT_TYPE_LATEST)
                    self.end_headers()
                    self.wfile.write(output)
                elif self.path == "/healthz":
                    body = health.to_json().encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format: str, *args: Any) -> None:
                pass  # suppress per-request logs

        return Handler


metrics = _Metrics()
