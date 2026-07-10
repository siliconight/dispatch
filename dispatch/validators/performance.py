"""Performance Budget Validator (TDD 13.11).

Identifies risk early from manifest data — no geometry parsing, no guarantee
of final performance (TDD: Dispatch should not guarantee performance).
"""

from __future__ import annotations

from . import Issue

SYSTEM = "performance"


def _warn(issues, count, budget, what, fix):
    if count > budget:
        issues.append(Issue(
            "moderate", SYSTEM,
            f"{what}: {count} exceeds budget {budget}.",
            fix,
        ))


def validate(ctx) -> list:
    issues = []
    b = ctx.spec.budgets

    prop_count = sum(len(ctx.imports[t].props) for t in ("deli_counter", "lot") if t in ctx.imports)
    _warn(issues, prop_count, int(b["max_props"]), "Prop placement count",
          "Reduce prop density or raise max_props in the spec budgets.")

    lux = ctx.imports.get("lux")
    if lux and "lighting" in lux.meta:
        lights = lux.meta["lighting"].get("lights", [])
        _warn(issues, len(lights), int(b["max_lights"]), "Light count",
              "Reduce light rigs or raise max_lights; dense rooms blow out and cost draw time.")
        shadow = [l for l in lights if l.get("shadows")]
        _warn(issues, len(shadow), int(b["max_shadow_lights"]), "Shadow-casting light count",
              "Disable shadows on fill lights.")

    patina = ctx.imports.get("patina")
    if patina:
        mats = patina.meta.get("materials", [])
        _warn(issues, len(mats), int(b["max_unique_materials"]), "Unique material count",
              "Atlas more surfaces or raise max_unique_materials.")

    _warn(issues, len(ctx.nav.nodes), int(b["max_nav_nodes"]), "Nav node count",
          "Simplify nav hints; runtime pathfinding cost scales with graph size.")

    if not issues:
        issues.append(Issue("info", SYSTEM, "All tracked budgets are within limits."))
    return issues
