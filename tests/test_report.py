import json

from dispatch.report import bluf, write_reports
from dispatch.score import compute
from dispatch.validators import issues_by_severity, run_all


def test_reports_written(ctx, tmp_path):
    issues = run_all(ctx)
    score = compute(issues)
    vdir = write_reports(ctx, issues, score, tmp_path)
    md = (vdir / "report.md").read_text()
    assert "## BLUF" in md
    assert "Mission Readiness" in md
    assert "Online Runtime Readiness" in md
    data = json.loads((vdir / "report.json").read_text())
    assert data["mission_id"] == "gas_station_robbery_001"
    assert data["online_ready"] is True
    html = (vdir / "report.html").read_text()
    assert "Gas Station Robbery" in html


def test_bluf_mentions_blockers():
    from dispatch.validators import Issue
    grouped = issues_by_severity([Issue("blocker", "x", "Extraction is unreachable.")])
    text = bluf({"status": "broken", "mission_readiness": 10}, grouped)
    assert "not ready" in text
    assert "Extraction is unreachable" in text
