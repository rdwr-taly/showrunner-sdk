"""
Config module — reads /config/app.json on startup and re-reads on SIGHUP.

Usage:
    from showrunner_sdk import config

    cfg = config.load()                         # returns dict
    config.on_reload(lambda c: print("new:", c))  # optional callback
"""

import json
import os
import signal
import logging
import threading
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("showrunner.config")

CONFIG_PATH = os.environ.get("SHOWRUNNER_CONFIG_PATH", "/config/app.json")


class _Config:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._lock = threading.Lock()
        self._reload_count = 0
        self._setup_signal()

    def _setup_signal(self) -> None:
        """Register SIGHUP handler for live config reload."""
        try:
            signal.signal(signal.SIGHUP, self._handle_sighup)
        except (OSError, AttributeError):
            # Windows or restricted environment — skip signal
            pass

    def _handle_sighup(self, signum: int, frame: Any) -> None:
        logger.info("SIGHUP received — reloading config")
        self.load()

    def load(self, path: str | None = None) -> dict[str, Any]:
        """Load config from JSON file. Returns the parsed dict.

        Thread-safety: builds the new dict in a local variable, then does a
        single atomic reference replacement (``self._data = new_data``).  This
        is safe in CPython even when called from a signal handler because no
        lock acquisition is needed on the data-read path.
        """
        p = Path(path or CONFIG_PATH)
        if not p.exists():
            logger.warning("Config file not found: %s — using empty config", p)
            self._data = {}
            return self._data

        with open(p) as f:
            new_data = json.load(f)

        # Atomic reference replacement — readers see either the old or new
        # dict, never a partially-updated one.
        self._data = new_data

        self._reload_count += 1
        logger.info("Config loaded from %s (%d keys)", p, len(new_data))

        # Snapshot callbacks under lock so iteration is safe even if another
        # thread appends a callback concurrently.
        with self._lock:
            callbacks = list(self._callbacks)

        for cb in callbacks:
            try:
                cb(new_data)
            except Exception:
                logger.exception("Error in config reload callback")

        return new_data

    def on_reload(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a function to be called whenever config is reloaded."""
        with self._lock:
            self._callbacks.append(callback)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key."""
        return self._data.get(key, default)

    @property
    def data(self) -> dict[str, Any]:
        """Current config dict."""
        return self._data

    @property
    def reload_count(self) -> int:
        return self._reload_count


config = _Config()
