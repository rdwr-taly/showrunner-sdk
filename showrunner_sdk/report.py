"""SR3 report writer — the shared helper apps use to emit ``/report/report.json``.

ShowRunner v3.0 pulls this file out of the container at window close (Docker
``get_archive``, or an HTTP GET on the SDK port) and projects its typed
``measures`` into the demo report + runbook. An app declares the contract (path,
typed measures, a default runbook) in its ``.showrunner/appspec.json`` ``sdk``
block; this helper just writes a well-formed, SEALED report so ShowRunner never
observes a half-written or untrusted file.

Fully optional and non-fatal: if the path is not writable the run is unaffected
(ShowRunner degrades to Tier-0 = Prometheus metrics + logs). The file is written
atomically (tmp + ``os.replace``) with ``status: "final"``.

Typical use, at shutdown, from the metrics you already track::

    from showrunner_sdk import report

    by_code = report.responses_by_code()                 # from the SDK registry
    total, blocked, ratio = report.block_ratio(by_code)
    report.write_report(
        measures={
            "responses.by_code": by_code,
            "responses.total": total,
            "responses.blocked": blocked,
            "responses.block_ratio": ratio,
        },
        summary=f"Sent {total} request(s); {blocked} blocked ({ratio:.0%}).",
    )

Call ``write_report`` on EVERY exit path (normal completion, SIGTERM/SIGINT,
error) — e.g. from a ``finally`` around your main run coroutine.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("showrunner_sdk.report")

DEFAULT_REPORT_PATH = "/report/report.json"
SCHEMA_VERSION = 1
#: Status codes an HTTP attack/traffic tool typically reads as "mitigated".
BLOCKED_CODES = frozenset({"403", "429", "503"})


def responses_by_code(registry: Any = None, counter_name: str = "http_status") -> dict[str, int]:
    """Per-status-code counts from a Prometheus registry.

    Reads the samples of a ``Counter`` named ``counter_name`` (prometheus_client
    renders it as ``<name>_total`` carrying a ``code`` label). Defaults to the
    SDK's own registry. Never raises — returns ``{}`` if the counter is absent or
    the registry cannot be read.
    """
    counts: dict[str, int] = {}
    try:
        if registry is None:
            from showrunner_sdk import metrics as _sdk_metrics

            registry = _sdk_metrics.registry
        sample_name = f"{counter_name}_total"
        for metric in registry.collect():
            for sample in metric.samples:
                if sample.name == sample_name:
                    code = sample.labels.get("code")
                    if code:
                        counts[code] = counts.get(code, 0) + int(sample.value)
    except Exception:  # pragma: no cover - defensive; never break the run
        LOGGER.debug("responses_by_code: failed to read registry", exc_info=True)
    return counts


def block_ratio(
    by_code: dict[str, int], blocked_codes: Iterable[str] = BLOCKED_CODES
) -> tuple[int, int, float]:
    """Return ``(total, blocked, ratio)`` from a by-code map.

    ``blocked`` sums the counts whose code is in ``blocked_codes``; ``ratio`` is
    ``blocked / total`` rounded to 4 dp (0.0 when no requests were sent).
    """
    blocked_set = set(blocked_codes)
    total = sum(by_code.values())
    blocked = sum(v for code, v in by_code.items() if code in blocked_set)
    return total, blocked, (round(blocked / total, 4) if total else 0.0)


def build_report(
    measures: dict[str, Any],
    *,
    summary: str | None = None,
    findings: list[dict[str, Any]] | None = None,
    status: str = "final",
) -> dict[str, Any]:
    """Build the SR3 report envelope. ``status="final"`` seals it for the portal.

    ``measures`` keys are dotted (e.g. ``"responses.by_code"``); ShowRunner
    unflattens them so a runbook can check ``report.responses.by_code.403``.
    """
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "measures": dict(measures or {}),
    }
    if summary is not None:
        report["summary"] = summary
    if findings:
        report["findings"] = list(findings)
    return report


def write_report(
    measures: dict[str, Any],
    *,
    summary: str | None = None,
    findings: list[dict[str, Any]] | None = None,
    status: str = "final",
    path: str | None = None,
) -> bool:
    """Atomically write the SR3 report. Returns ``True`` on success, never raises.

    Path resolution: explicit ``path`` > env ``SR_REPORT_PATH`` > ``/report/report.json``.
    """
    target = Path(path or os.getenv("SR_REPORT_PATH", DEFAULT_REPORT_PATH))
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        document = build_report(measures, summary=summary, findings=findings, status=status)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps(document, indent=2), encoding="utf-8")
        tmp.replace(target)  # atomic on the same filesystem
        LOGGER.info("SR3 report written to %s", target)
        return True
    except Exception:  # pragma: no cover - degrade to Tier-0, never affect the run
        LOGGER.debug("SR3 report write failed; ShowRunner degrades to Tier-0", exc_info=True)
        return False


__all__ = [
    "build_report",
    "write_report",
    "responses_by_code",
    "block_ratio",
    "DEFAULT_REPORT_PATH",
    "BLOCKED_CODES",
    "SCHEMA_VERSION",
]
