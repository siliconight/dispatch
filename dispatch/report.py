"""Validation report and engineering handoff document.

BLUF-first report.md / report.json / report.html, plus HANDOFF.md — the
integration contract for gameplay and server engineers. Validation claims
integration readiness, never implemented authority (handoff spec section 7).
"""

from __future__ import annotations

import html as html_mod
import json
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .anchors import RUNTIME_OWNED_TYPES
from .validators import SEVERITIES, issues_by_severity

SEVERITY_LABEL = {
    "blocker": "Blocker", "major": "Major", "moderate": "Moderate",
    "minor": "Minor", "info": "Info",
}

NON_CLAIMS = (
    "actual server authority", "RPC security", "replication correctness",
    "network prediction or reconciliation", "late-join or reconnect recovery",
    "persistence correctness", "objective/enemy/combat behavior",
    "final gameplay pacing", "matchmaking", "shipping online playability",
)


def bluf(score: dict, grouped: dict) -> str:
    n_block = len(grouped["blocker"])
    n_major = len(grouped["major"])
    status = score["status"].replace("_", " ")
    if n_block:
        heads = "; ".join(i.message.rstrip(".") for i in grouped["blocker"][:2])
        more = f" (+{n_block - 2} more)" if n_block > 2 else ""
        return (f"Mission shell is not ready for handoff. "
                f"{n_block} blocker(s) found: {heads}{more}.")
    if n_major:
        return (f"Mission shell is {status}. No blockers, but {n_major} major issue(s) "
                f"should be fixed before handoff.")
    return (f"Mission shell is {status} at readiness {score['mission_readiness']}. "
            f"No blockers or major issues. Online gameplay is not verified by Dispatch.")


def build_report(ctx, issues: list, score: dict, out_dir: Path) -> dict:
    grouped = issues_by_severity(issues)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    spec = ctx.spec
    data = {
        "schema": "dispatch.report.v0.2",
        "dispatch_version": __version__,
        "generated": now,
        "mode": ctx.mode,
        "mission_id": spec.mission_id,
        "title": spec.title,
        "bluf": bluf(score, grouped),
        "readiness": score,
        "integration_ready": not any(
            i.severity in ("blocker", "major") and i.system in ("integration_readiness", "closure")
            for i in issues),
        "counts": {s: len(grouped[s]) for s in SEVERITIES},
        "issues": [i.to_json() for i in issues],
        "inputs": {t: rt.schema for t, rt in sorted(ctx.resolved.tools.items())},
        "anchor_counts": {},
        "export_location": str(out_dir),
        "not_validated": list(NON_CLAIMS),
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
    L.append(f"Mission shell `{d['mission_id']}` — dispatch v{d['dispatch_version']} "
             f"— mode `{d['mode']}` — {d['generated']}")
    L.append("")
    L.append("## BLUF")
    L.append("")
    L.append(d["bluf"])
    L.append("")
    L.append("## Build Summary")
    L.append("")
    L.append(f"Engine: {ctx.spec.engine}. Mode of play: {ctx.spec.mode}. "
             f"Players: {ctx.spec.players_min}-{ctx.spec.players_max}. "
             f"Intended networking model (to be implemented by the game runtime): {ctx.spec.net_model}.")
    L.append("")
    anchors = ", ".join(f"{k} x{v}" for k, v in d["anchor_counts"].items()) or "none"
    L.append(f"Anchors: {anchors}.")
    L.append("")
    L.append("## Shell Readiness")
    L.append("")
    r = d["readiness"]
    L.append(f"Readiness **{r['mission_readiness']}** — status `{r['status']}`.")
    L.append("")
    for cat, val in r["scores"].items():
        L.append(f"- {cat}: {val}")
    L.append("")
    L.append("## Integration Readiness")
    L.append("")
    L.append("**Shell integration requirements complete.** The shell is ready to receive an authoritative runtime."
             if d["integration_ready"]
             else "Shell integration requirements **incomplete** — see integration_readiness and closure issues below.")
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
    L.append("## Not Validated By Dispatch")
    L.append("")
    L.append("Dispatch validates structural readiness only. It does not validate: "
             + "; ".join(d["not_validated"]) + ".")
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
    L.append("Debug overlays: `validation/overlays/` (if generated). Engineering handoff: `HANDOFF.md`.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("*This report validates structural readiness of a mission shell. Any preview code "
             "lives only in `preview_only/` and claims no gameplay, mission, or network authority. "
             "The production game runtime remains authoritative for mission progression, gameplay "
             "behavior, enemy AI, replication, persistence, late joining, reconnection, and online "
             "correctness.*")
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
.nonclaims {{ color: #666; font-size: 0.9rem; }}
</style></head><body>
<h1>{esc(d['title'])}</h1>
<p>Mission shell <code>{esc(d['mission_id'])}</code> — dispatch v{esc(d['dispatch_version'])} — mode <code>{esc(d['mode'])}</code> — {esc(d['generated'])}</p>
<div class="bluf"><strong>BLUF:</strong> {esc(d['bluf'])}</div>
<h2>Shell Readiness</h2>
<p class="score">{d['readiness']['mission_readiness']} <small>({esc(d['readiness']['status'])})</small></p>
<ul>{cats}</ul>
<h2>Integration Readiness</h2>
<p>{"Shell integration requirements complete — the shell is ready to receive an authoritative runtime." if d['integration_ready'] else "Shell integration requirements <strong>incomplete</strong>."}</p>
<h2>Issues ({len(d['issues'])})</h2>
<table><tr><th>Severity</th><th>System</th><th>Detail</th></tr>{''.join(rows)}</table>
<p class="nonclaims">Not validated by Dispatch: {esc('; '.join(d['not_validated']))}.</p>
<h2>Export</h2>
<p><code>{esc(d['export_location'])}</code></p>
</body></html>
"""


# --- HANDOFF.md ----------------------------------------------------------------


def write_handoff(ctx, out_dir: Path, issues=None, score=None) -> Path:
    """Engineering handoff document (handoff spec sections 2, 10, 12.9)."""
    spec = ctx.spec
    L = []
    L.append(f"# Engineering Handoff: {spec.title}")
    L.append("")
    L.append(f"Mission shell `{spec.mission_id}` — dispatch v{__version__} — mode `{ctx.mode}`.")
    L.append("")
    L.append("> This package contains a self-contained Godot 4.7 mission shell, presentation "
             "resources, gameplay anchors, proposed mission beats, and runtime integration "
             "requirements.")
    L.append(">")
    L.append("> Level Factory and its authoring tools are not required to consume this package.")
    L.append(">")
    L.append("> The production game runtime remains authoritative for mission progression, "
             "gameplay behavior, enemy AI, replication, persistence, late joining, "
             "reconnection, and online correctness.")
    L.append("")
    L.append("## What this package is")
    L.append("")
    L.append("A structurally validated Godot mission shell: functional geometry and anchors, "
             "an isolated presentation layer, a proposed beat graph, declared runtime ownership "
             "requirements, navigation hints, license records, and a hashed resource manifest. "
             "It contains no production gameplay or networking implementation" +
             (", apart from clearly marked preview-only walkthrough tooling under `preview_only/` "
              "— delete that folder before integration."
              if ctx.include_preview else
              " and no hidden runtime code."))
    L.append("")
    L.append("## What the game runtime must implement")
    L.append("")
    L.append("Per `runtime_ownership_requirements.json`: mission authority, all RPCs and "
             "replication, persistence, late-join state recovery, and every objective, combat, "
             "and AI behavior. Dispatch declares the requirements; it implements none of them, "
             "and it does not prescribe networking library, RPC names, replication frequency, "
             "serialization, prediction/reconciliation models, persistence backend, or network "
             "entity IDs. The runtime maps `shell_id` to its own network identities; `shell_id` "
             "is a stable content key namespaced by mission id, not a replication ID — "
             "`runtime_binding` is intentionally null.")
    L.append("")
    L.append("## Integration checklist")
    L.append("")
    owned = [r for r in ctx.ownership.get("requirements", [])]
    L.append(f"{len(owned)} gameplay-critical anchor(s) require runtime ownership:")
    L.append("")
    for r in owned:
        rr = r["runtime_requirements"]
        flags = [k.replace("_required", "") for k, v in rr.items() if v is True]
        status = next((a.integration_status for a in ctx.anchors if a.id == r["shell_id"]),
                      "unimplemented")
        adapter = next((a.expected_adapter for a in ctx.anchors if a.id == r["shell_id"]), "")
        line = (f"- `{r['shell_id']}` ({r['anchor_type']}) — owner: {rr['authoritative_owner']}; "
                f"{', '.join(flags) or 'no state flags'}; status: {status}")
        if adapter:
            line += f"; expected adapter: {adapter}"
        L.append(line)
    L.append("")
    L.append("Integration status values `integrated` and `verified_by_game_runtime` are set by "
             "the production pipeline only — never by Dispatch.")
    L.append("")
    L.append("## Proposed beat graph")
    L.append("")
    beats = ctx.beats.beats
    L.append(" -> ".join(f"{b.id} ({b.type})" for b in beats) if beats else "none")
    L.append("")
    L.append("The graph is design intent. The game decides whether a beat is valid, when it "
             "completes, which peer may report it, whether the server accepts it, how completion "
             "replicates, and how reconnecting players receive state.")
    L.append("")
    L.append("## Validation")
    L.append("")
    if issues is not None and score is not None:
        counts = {}
        for i in issues:
            counts[i.severity] = counts.get(i.severity, 0) + 1
        L.append(f"Shell readiness {score['mission_readiness']} (`{score['status']}`) — "
                 + ", ".join(f"{counts.get(s, 0)} {s}" for s in ("blocker", "major", "moderate", "minor"))
                 + ". Full detail in `validation/report.md`.")
    else:
        L.append("Validation was not run in this build. Run `dispatch validate` for reports.")
    L.append("")
    L.append("Dispatch does NOT validate or claim: " ) 
    L.append("; ".join(NON_CLAIMS) + ".")
    L.append("")
    L.append("## Package contents")
    L.append("")
    L.append("`mission.tscn` (Functional / Presentation / Handoff"
             + (" / PreviewOnly" if ctx.include_preview else "")
             + "), `gameplay_anchors.json`, `proposed_beat_graph.json`, "
             "`runtime_ownership_requirements.json`, `navigation_hints.json`, "
             "`mission_manifest.json`, `resource_manifest.json`, `build.lock.json`, "
             "`LICENSES.md`, `validation/`"
             + (", `preview_only/` (delete before integration)" if ctx.include_preview else "")
             + (", `adapters/` (interface stubs only — no RPCs, replication, or persistence)"
                if ctx.mode == "runtime-adapter" else "")
             + ".")
    L.append("")
    p = out_dir / "HANDOFF.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p
