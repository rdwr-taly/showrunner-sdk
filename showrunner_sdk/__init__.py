"""ShowRunner SDK — near-zero boilerplate to make any app ShowRunner-managed."""

from showrunner_sdk import report
from showrunner_sdk.config import config
from showrunner_sdk.health import health
from showrunner_sdk.metrics import metrics

__version__ = "0.2.0"
__all__ = ["config", "metrics", "health", "report"]
