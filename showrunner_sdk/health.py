"""
Health module — tracks app status, exposed via /healthz on the metrics port.

Usage:
    from showrunner_sdk import health

    health.set_status("running")
    health.set_status("error", reason="connection lost")
"""

import json
import time
import logging

logger = logging.getLogger("showrunner.health")


class _Health:
    def __init__(self) -> None:
        self.status: str = "starting"
        self.reason: str = ""
        self._started_at = time.time()

    def set_status(self, status: str, reason: str = "") -> None:
        """Set current app status. Common values: starting, running, stopped, error."""
        self.status = status
        self.reason = reason
        logger.info("Health status: %s%s", status, f" ({reason})" if reason else "")

    def to_json(self) -> str:
        return json.dumps({
            "status": self.status,
            "reason": self.reason,
            "uptime_seconds": round(time.time() - self._started_at, 1),
        })


health = _Health()
