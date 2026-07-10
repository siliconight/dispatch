"""Multiplayer Spawn Validator (TDD 13.10)."""

from __future__ import annotations

import math

from ..anchors import by_type
from ..authority import node_path_for
from . import Issue

SYSTEM = "multiplayer_spawns"


def _dist(a, b) -> float:
    return math.dist(a, b)


def validate(ctx) -> list:
    issues = []
    spec = ctx.spec
    starts = by_type(ctx.anchors, "player_start")
    spacing = float(spec.tuning["spawn_min_spacing"])
    nav_radius = float(spec.tuning["anchor_nav_radius"])

    if len(starts) < spec.players_max:
        # Reported as a blocker by online_runtime; skip duplicate noise here.
        pass

    # Overlap / spacing.
    for i, a in enumerate(starts):
        for b in starts[i + 1:]:
            d = _dist(a.pos, b.pos)
            if d < 0.01:
                issues.append(Issue(
                    "blocker", SYSTEM,
                    f"Player starts {a.id!r} and {b.id!r} overlap at the same position.",
                    "Spread the spawn points apart in the upstream export.",
                    node=node_path_for(a),
                ))
            elif d < spacing:
                issues.append(Issue(
                    "major", SYSTEM,
                    f"Player starts {a.id!r} and {b.id!r} are {d:.2f}m apart (min {spacing}m).",
                    "Increase spawn spacing so player capsules do not collide on spawn.",
                    node=node_path_for(a),
                ))

    # Each spawn must sit on (near) the nav graph.
    for a in starts:
        if ctx.nav.nodes and ctx.nav.nearest(a.pos, nav_radius) is None:
            issues.append(Issue(
                "blocker", SYSTEM,
                f"Player start {a.id!r} is more than {nav_radius}m from any nav node; it may be inside collision or outside the level.",
                "Move the spawn onto walkable space or extend nav hints to cover it.",
                node=node_path_for(a),
            ))

    # Spawn exposure: AI spawn within short range of a player start.
    ai = by_type(ctx.anchors, "ai_spawn")
    for a in starts:
        for e in ai:
            d = _dist(a.pos, e.pos)
            if d < 8.0:
                issues.append(Issue(
                    "major", SYSTEM,
                    f"Player start {a.id!r} is {d:.1f}m from AI spawn {e.id!r}; players risk being spawn-killed.",
                    "Move the AI spawn zone away from player starts or gate it behind Dangerous Mode.",
                    node=node_path_for(a),
                ))

    if not issues and starts:
        issues.append(Issue("info", SYSTEM,
                            f"{len(starts)} player start(s) validated for {spec.players_min}-{spec.players_max} players."))
    return issues
