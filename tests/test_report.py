from __future__ import annotations

import json

from prometheus_client import CollectorRegistry, Counter

from showrunner_sdk import report


def test_build_report_is_sealed_with_measures_and_summary():
    doc = report.build_report(
        {"responses.by_code": {"403": 50, "200": 100}, "responses.block_ratio": 0.33},
        summary="Radware blocked ~33%.",
    )
    assert doc["schema_version"] == report.SCHEMA_VERSION
    assert doc["status"] == "final"  # sealed
    assert doc["measures"]["responses.block_ratio"] == 0.33
    assert doc["summary"] == "Radware blocked ~33%."
    assert "generated_at" in doc


def test_block_ratio_math():
    total, blocked, ratio = report.block_ratio({"200": 120, "403": 60, "429": 20})
    assert (total, blocked, ratio) == (200, 80, 0.4)
    # no traffic -> 0.0, never divides by zero
    assert report.block_ratio({}) == (0, 0, 0.0)


def test_responses_by_code_reads_a_registry():
    reg = CollectorRegistry()
    c = Counter("http_status", "responses by code", ["code"], registry=reg)
    for _ in range(100):
        c.labels(code="200").inc()
    for _ in range(50):
        c.labels(code="403").inc()
    assert report.responses_by_code(registry=reg) == {"200": 100, "403": 50}
    # missing counter -> {} (Tier-0), never raises
    assert report.responses_by_code(registry=CollectorRegistry()) == {}


def test_write_report_atomic_and_final(tmp_path):
    target = tmp_path / "report" / "report.json"
    ok = report.write_report(
        {"responses.total": 160, "responses.block_ratio": 0.375},
        summary="done",
        path=str(target),
    )
    assert ok is True
    assert not (tmp_path / "report" / "report.json.tmp").exists()  # no leftover tmp
    data = json.loads(target.read_text())
    assert data["status"] == "final"
    assert data["measures"]["responses.total"] == 160


def test_write_report_honors_env(tmp_path, monkeypatch):
    target = tmp_path / "env-report.json"
    monkeypatch.setenv("SR_REPORT_PATH", str(target))
    assert report.write_report({"x": 1}) is True
    assert json.loads(target.read_text())["measures"]["x"] == 1


def test_write_report_unwritable_degrades():
    # A path under a file (not a dir) can't be created -> False, never raises.
    assert report.write_report({"x": 1}, path="/dev/null/nope/report.json") is False


def test_findings_included_only_when_present():
    assert "findings" not in report.build_report({"a": 1})
    doc = report.build_report({"a": 1}, findings=[{"title": "t", "severity": "high"}])
    assert doc["findings"][0]["title"] == "t"
