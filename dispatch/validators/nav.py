"""AI nav readiness (TDD 13.6): islands, AI spawn/patrol binding."""

from __future__ import annotations

from ..anchors import by_type
from ..authority import node_path_for
from . import Issue

SYSTEM = "ai_nav"


def validate(ctx) -> list:
    issues = []
    if not ctx.nav.nodes:
        return issues  # reachability already reports the blocker

    radius = float(ctx.spec.tuning["anchor_nav_radius"])
    islands = ctx.nav.islands()
    if len(islands) > 1:
        main = set(islands[0])
        orphan_count = sum(len(c) for c in islands[1:])
        issues.append(Issue(
            "moderate", SYSTEM,
            f"Nav graph has {len(islands)} islands; {orphan_count} node(s) are disconnected from the main island.",
            "Add nav links between islands or remove unreachable nav nodes.",
        ))
        for a in ctx.anchors:
            node = ctx.nav.nearest(a.pos, radius)
            if node is not None and node not in main and a.type in ("objective", "extraction", "player_start", "ai_spawn"):
                issues.append(Issue(
                    "major", SYSTEM,
                    f"{a.type} {a.id!r} sits on a disconnected nav island.",
                    "Bridge the island or move the anchor to the main nav island.",
                    node=node_path_for(a),
                ))

    for a in by_type(ctx.anchors, "ai_spawn"):
        if ctx.nav.nearest(a.pos, radius) is None:
            issues.append(Issue(
                "major", SYSTEM,
                f"AI spawn {a.id!r} is outside the nav graph; AI spawned here cannot navigate.",
                "Move the spawn zone onto the navmesh area.",
                node=node_path_for(a),
            ))
    for a in by_type(ctx.anchors, "patrol_point"):
        if ctx.nav.nearest(a.pos, radius) is None:
            issues.append(Issue(
                "moderate", SYSTEM,
                f"Patrol point {a.id!r} is outside the nav graph.",
                "Move the patrol point onto walkable space.",
                node=node_path_for(a),
            ))

    issues.append(Issue(
        "info", SYSTEM,
        "Runtime navmesh is not baked by Dispatch v0.1: bake the NavigationRegion3D in the Godot editor before AI playtest.",
    ))
    return issues
