"""License tracking (delta D10).

Each upstream tool manifest may carry a ``license`` record; absent means
unknown. Dispatch aggregates into LICENSES.md. Default: warn on unknown
bundled third-party resources; --strict-licenses turns unknowns into
blockers (Level Factory invokes with strict on).
"""

from __future__ import annotations

from pathlib import Path

from . import __version__
from .validators import Issue

SYSTEM = "licenses"

# Tools whose files are copied INTO the package (bundled). Lux/DC/Lot/Zoo/
# Patina all bundle assets; spec-only inputs would not.
BUNDLING_TOOLS = ("deli_counter", "lot", "zoo", "patina", "lux")


def collect(ctx) -> list:
    """One record per resolved input tool: name, license info or unknown."""
    records = []
    for tool, rt in sorted(ctx.resolved.tools.items()):
        lic = rt.manifest.get("license") if isinstance(rt.manifest, dict) else None
        if isinstance(lic, str):
            lic = {"name": lic}
        records.append({
            "tool": tool,
            "schema": rt.schema,
            "license": (lic or {}).get("name", "unknown"),
            "source": (lic or {}).get("source", ""),
            "notes": (lic or {}).get("notes", ""),
            "bundled": tool in BUNDLING_TOOLS,
        })
    return records


def validate(ctx, strict: bool) -> list:
    issues = []
    for rec in collect(ctx):
        if rec["bundled"] and rec["license"] == "unknown":
            sev = "blocker" if strict else "moderate"
            issues.append(Issue(
                sev, SYSTEM,
                f"Bundled resources from {rec['tool']} carry no license record.",
                f"Add a \"license\" record to the {rec['tool']} manifest "
                "(strict mode blocks the build on unknowns).",
            ))
    if not issues:
        issues.append(Issue("info", SYSTEM, "All bundled inputs carry license records."))
    return issues


def write_licenses_md(ctx, out_dir: Path) -> Path:
    L = []
    L.append(f"# Licenses — {ctx.spec.title}")
    L.append("")
    L.append(f"Aggregated by dispatch v{__version__} from upstream tool manifests. "
             "`unknown` means the upstream manifest carries no license record yet.")
    L.append("")
    for rec in collect(ctx):
        line = f"- **{rec['tool']}** ({rec['schema'] or 'no schema'}): {rec['license']}"
        if rec["source"]:
            line += f" — {rec['source']}"
        if rec["notes"]:
            line += f" ({rec['notes']})"
        if rec["bundled"]:
            line += " [bundled]"
        L.append(line)
    L.append("")
    p = out_dir / "LICENSES.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p
