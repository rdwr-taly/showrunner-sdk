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
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("showrunner.config")

CONFIG_PATH = os.environ.get("SHOWRUNNER_CONFIG_PATH", "/config/app.json")


class _Config:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
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
        """Load config from JSON file. Returns the parsed dict."""
        p = Path(path or CONFIG_PATH)
        if not p.exists():
            logger.warning("Config file not found: %s — using empty config", p)
            self._data = {}
            return self._data

        with open(p) as f:
            self._data = json.load(f)

        self._reload_count += 1
        logger.info("Config loaded from %s (%d keys)", p, len(self._data))

        for cb in self._callbacks:
            try:
                cb(self._data)
            except Exception:
                logger.exception("Error in config reload callback")

        return self._data

    def on_reload(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a function to be called whenever config is reloaded."""
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
