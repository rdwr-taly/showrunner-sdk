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
        # Single tuple so status+reason are always consistent when read
        # concurrently.  Tuple reference replacement is atomic in CPython.
        self._state: tuple[str, str] = ("starting", "")
        self._started_at = time.time()

    def set_status(self, status: str, reason: str = "") -> None:
        """Set current app status. Common values: starting, running, stopped, error."""
        self._state = (status, reason)
        logger.info("Health status: %s%s", status, f" ({reason})" if reason else "")

    @property
    def status(self) -> str:
        return self._state[0]

    @property
    def reason(self) -> str:
        return self._state[1]

    def to_json(self) -> str:
        status, reason = self._state
        return json.dumps({
            "status": status,
            "reason": reason,
            "uptime_seconds": round(time.time() - self._started_at, 1),
        })


health = _Health()
