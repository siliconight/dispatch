"""Objective Reachability Validator (TDD 13.9).

BFS over the merged nav-hint graph. Every anchor is bound to its nearest nav
node within anchor_nav_radius; reachability is then graph connectivity.
"""

from __future__ import annotations

from ..anchors import by_type
from ..authority import node_path_for
from . import Issue

SYSTEM = "objective_reachability"


def _bind(ctx, anchor):
    return ctx.nav.nearest(anchor.pos, float(ctx.spec.tuning["anchor_nav_radius"]))


def validate(ctx) -> list:
    issues = []
    if not ctx.nav.nodes:
        issues.append(Issue(
            "blocker", SYSTEM,
            "No nav hint nodes were found in any input; reachability cannot be validated.",
            "Export nav_hints.json from Deli Counter and Lot.",
        ))
        return issues

    starts = by_type(ctx.anchors, "player_start")
    required = [a for a in ctx.anchors if a.type in ("objective", "extraction")]
    radius = float(ctx.spec.tuning["anchor_nav_radius"])

    bound = {}
    for a in starts + required:
        node = _bind(ctx, a)
        if node is None:
            issues.append(Issue(
                "blocker", SYSTEM,
                f"{a.type} {a.id!r} is more than {radius}m from any nav node (inside collision or outside nav bounds).",
                "Move the anchor onto walkable space, or add a nav node/link near it.",
                node=node_path_for(a),
            ))
        else:
            bound[a.id] = node

    # Flow-ordered reachability: every start reaches the first bound step
    # anchor; each consecutive pair of flow steps is connected.
    flow_anchors = []
    for step in ctx.flow.steps:
        ids = [aid for aid in step.anchor_ids if aid in bound]
        if ids:
            flow_anchors.append((step.name, ids))

    if flow_anchors:
        first_name, first_ids = flow_anchors[0]
        for s in starts:
            if s.id not in bound:
                continue
            if not any(ctx.nav.reachable(bound[s.id], bound[t]) for t in first_ids):
                issues.append(Issue(
                    "blocker", SYSTEM,
                    f"Player start {s.id!r} cannot reach the first mission beat ({first_name}).",
                    "Connect the spawn area to the mission space with nav links, or move the spawn.",
                    node=node_path_for(s),
                ))
        for (name_a, ids_a), (name_b, ids_b) in zip(flow_anchors, flow_anchors[1:]):
            ok = any(ctx.nav.reachable(bound[x], bound[y]) for x in ids_a for y in ids_b)
            if not ok:
                issues.append(Issue(
                    "blocker", SYSTEM,
                    f"Mission beat {name_b!r} cannot be reached from beat {name_a!r}.",
                    "Move the anchor to a reachable nav island or add a nav link.",
                ))

    # Extraction must be reachable from at least one objective.
    extractions = [a for a in required if a.type == "extraction" and a.id in bound]
    objectives = [a for a in required if a.type == "objective" and a.id in bound]
    for e in extractions:
        if objectives and not any(ctx.nav.reachable(bound[o.id], bound[e.id]) for o in objectives):
            issues.append(Issue(
                "blocker", SYSTEM,
                f"Extraction point {e.id!r} cannot be reached from any objective.",
                "Move the extraction point to a reachable nav island or add a nav link.",
                node=node_path_for(e),
            ))

    if not issues:
        issues.append(Issue("info", SYSTEM, "All mission beats are reachable in flow order."))
    return issues
