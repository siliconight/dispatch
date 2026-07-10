"""Validation Report (TDD 17): BLUF-first, md + json + html."""

from __future__ import annotations

import html as html_mod
import json
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .validators import SEVERITIES, issues_by_severity

SEVERITY_LABEL = {
    "blocker": "Blocker", "major": "Major", "moderate": "Moderate",
    "minor": "Minor", "info": "Info",
}


def bluf(score: dict, grouped: dict) -> str:
    n_block = len(grouped["blocker"])
    n_major = len(grouped["major"])
    status = score["status"].replace("_", " ")
    if n_block:
        heads = "; ".join(i.message.rstrip(".") for i in grouped["blocker"][:2])
        more = f" (+{n_block - 2} more)" if n_block > 2 else ""
        return (f"Mission is not ready for online playtest. "
                f"{n_block} blocker(s) found: {heads}{more}.")
    if n_major:
        return (f"Mission is {status}. No blockers, but {n_major} major issue(s) "
                f"should be fixed before online playtest.")
    return f"Mission is {status} at readiness {score['mission_readiness']}. No blockers or major issues."


def build_report(ctx, issues: list, score: dict, out_dir: Path) -> dict:
    grouped = issues_by_severity(issues)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    spec = ctx.spec
    data = {
        "schema": "dispatch.report.v0.1",
        "dispatch_version": __version__,
        "generated": now,
        "mission_id": spec.mission_id,
        "title": spec.title,
        "bluf": bluf(score, grouped),
        "readiness": score,
        "online_ready": not any(
            i.severity in ("blocker", "major") and i.system == "online_runtime"
            for i in issues),
        "counts": {s: len(grouped[s]) for s in SEVERITIES},
        "issues": [i.to_json() for i in issues],
        "inputs": {t: rt.schema for t, rt in sorted(ctx.resolved.tools.items())},
        "anchor_counts": {},
        "export_location": str(out_dir),
    }
    for a in ctx.anchors:
        data["anchor_counts"][a.type] = data["anchor_counts"].get(a.type, 0) + 1
    data["anchor_counts"] = dict(sorted(data["anchor_counts"].items()))
    return data


def write_reports(ctx, issues: list, score: dict, out_dir: Path) -> Path:
    vdir = out_dir / "validation"
    vdir.mkdir(parents=True, exist_ok=True)
    data = build_report(ctx, issues, score, out_dir)
    (vdir / "report.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (vdir / "report.md").write_text(_markdown(ctx, data), encoding="utf-8")
    (vdir / "report.html").write_text(_html(data), encoding="utf-8")
    return vdir


def _issue_lines(data, severity):
    return [i for i in data["issues"] if i["severity"] == severity]


def _markdown(ctx, d: dict) -> str:
    L = []
    L.append(f"# Validation Report: {d['title']}")
    L.append("")
    L.append(f"Mission `{d['mission_id']}` — dispatch v{d['dispatch_version']} — {d['generated']}")
    L.append("")
    L.append("## BLUF")
    L.append("")
    L.append(d["bluf"])
    L.append("")
    L.append("## Build Summary")
    L.append("")
    L.append(f"Engine: {ctx.spec.engine}. Mode: {ctx.spec.mode}. "
             f"Players: {ctx.spec.players_min}-{ctx.spec.players_max}. "
             f"Networking: {ctx.spec.net_model}.")
    L.append("")
    anchors = ", ".join(f"{k} x{v}" for k, v in d["anchor_counts"].items()) or "none"
    L.append(f"Anchors: {anchors}.")
    L.append("")
    L.append("## Mission Readiness")
    L.append("")
    r = d["readiness"]
    L.append(f"Readiness **{r['mission_readiness']}** — status `{r['status']}`.")
    L.append("")
    for cat, val in r["scores"].items():
        L.append(f"- {cat}: {val}")
    L.append("")
    L.append("## Online Runtime Readiness")
    L.append("")
    L.append("Online-ready: **yes**." if d["online_ready"]
             else "Online-ready: **no** — see online_runtime issues below.")
    L.append("")
    for sev in SEVERITIES:
        items = _issue_lines(d, sev)
        L.append(f"## {SEVERITY_LABEL[sev]} Issues ({len(items)})")
        L.append("")
        if not items:
            L.append("None.")
        for i in items:
            line = f"- **[{i['system']}]** {i['message']}"
            if i.get("node"):
                line += f" (node: `{i['node']}`)"
            L.append(line)
            if i.get("suggested_fix"):
                L.append(f"  - Suggested fix: {i['suggested_fix']}")
        L.append("")
    L.append("## Inputs")
    L.append("")
    for tool, schema in d["inputs"].items():
        L.append(f"- {tool}: `{schema or 'no schema field'}`")
    L.append("")
    L.append("## Export")
    L.append("")
    L.append(f"Package: `{d['export_location']}`")
    L.append("")
    L.append("Debug overlays: `validation/overlays/` (if generated).")
    L.append("")
    return "\n".join(L)


def _html(d: dict) -> str:
    esc = html_mod.escape
    colors = {"blocker": "#c0392b", "major": "#d35400", "moderate": "#b7950b",
              "minor": "#7f8c8d", "info": "#2e86c1"}
    rows = []
    for i in d["issues"]:
        fix = esc(i.get("suggested_fix", ""))
        node = esc(i.get("node", ""))
        rows.append(
            f"<tr><td style='color:{colors[i['severity']]};font-weight:bold'>{esc(i['severity'])}</td>"
            f"<td>{esc(i['system'])}</td><td>{esc(i['message'])}"
            + (f"<br><small>node: <code>{node}</code></small>" if node else "")
            + (f"<br><small>fix: {fix}</small>" if fix else "")
            + "</td></tr>"
        )
    cats = "".join(f"<li>{esc(k)}: {v}</li>" for k, v in d["readiness"]["scores"].items())
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Dispatch Report: {esc(d['title'])}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 60rem; color: #222; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #ddd; padding: 6px 10px; vertical-align: top; text-align: left; }}
.bluf {{ background: #f4f6f7; border-left: 4px solid #2e86c1; padding: 1rem; }}
.score {{ font-size: 2rem; font-weight: bold; }}
</style></head><body>
<h1>{esc(d['title'])}</h1>
<p>Mission <code>{esc(d['mission_id'])}</code> — dispatch v{esc(d['dispatch_version'])} — {esc(d['generated'])}</p>
<div class="bluf"><strong>BLUF:</strong> {esc(d['bluf'])}</div>
<h2>Readiness</h2>
<p class="score">{d['readiness']['mission_readiness']} <small>({esc(d['readiness']['status'])})</small></p>
<ul>{cats}</ul>
<h2>Online Runtime</h2>
<p>{"Online-ready: yes." if d['online_ready'] else "Online-ready: <strong>no</strong>."}</p>
<h2>Issues ({len(d['issues'])})</h2>
<table><tr><th>Severity</th><th>System</th><th>Detail</th></tr>{''.join(rows)}</table>
<h2>Export</h2>
<p><code>{esc(d['export_location'])}</code></p>
</body></html>
"""
