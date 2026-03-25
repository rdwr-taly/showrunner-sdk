"""ShowRunner SDK — near-zero boilerplate to make any app ShowRunner-managed."""

from showrunner_sdk.config import config
from showrunner_sdk.metrics import metrics
from showrunner_sdk.health import health

__version__ = "0.1.0"
__all__ = ["config", "metrics", "health"]
