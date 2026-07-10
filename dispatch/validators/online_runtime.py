"""Online Runtime Validator (TDD 13.5).

Confirms the mission can support server-authoritative online co-op:
authority coverage, stable IDs, no gameplay under presentation roots,
player-start counts, no debug dependencies in the flow.
"""

from __future__ import annotations

from ..anchors import SERVER_ANCHOR_TYPES, by_type
from ..authority import CLIENT_ROOTS, node_path_for
from . import Issue

SYSTEM = "online_runtime"


def validate(ctx) -> list:
    issues = []
    spec = ctx.spec

    # Every mission-critical anchor must be replicated with a stable id.
    for a in ctx.anchors:
        if a.type in SERVER_ANCHOR_TYPES and not a.net_id:
            issues.append(Issue(
                "blocker", SYSTEM,
                f"Server-authoritative anchor {a.id!r} ({a.type}) has no network id.",
                "This is a Dispatch bug — net ids are assigned automatically. Re-run the build.",
                node=node_path_for(a),
            ))

    # Replication registry integrity: unique ids, deterministic order.
    reg = ctx.authority.get("replication_registry", [])
    ids = [r["net_id"] for r in reg]
    if len(ids) != len(set(ids)):
        issues.append(Issue(
            "blocker", SYSTEM,
            "Duplicate network ids in the replication registry.",
            "Re-run the build; if it persists, report upstream duplicate anchor ids.",
        ))

    # No gameplay anchors may live under client-only presentation roots.
    for a in ctx.anchors:
        path = node_path_for(a)
        if a.type in SERVER_ANCHOR_TYPES and any(path.startswith(c) for c in CLIENT_ROOTS):
            issues.append(Issue(
                "blocker", SYSTEM,
                f"Gameplay anchor {a.id!r} is placed under a client-only presentation root.",
                "Move it into the Gameplay subtree.",
                node=path,
            ))

    # Player starts must support the networked player range.
    starts = by_type(ctx.anchors, "player_start")
    if len(starts) < spec.players_max:
        issues.append(Issue(
            "blocker", SYSTEM,
            f"Mission supports up to {spec.players_max} players but only {len(starts)} player start(s) exist.",
            f"Export {spec.players_max - len(starts)} more player_start anchor(s).",
        ))

    # Extraction must exist and be server-owned (completion is server-confirmed).
    for a in by_type(ctx.anchors, "extraction"):
        if not a.net_id:
            issues.append(Issue(
                "blocker", SYSTEM,
                f"Extraction {a.id!r} is not registered for replication; extraction could complete client-only.",
                "Re-run the build.",
                node=node_path_for(a),
            ))

    # Debug anchors must not be bound into the mission flow.
    debug_ids = {a.id for a in by_type(ctx.anchors, "camera_debug")}
    for step in ctx.flow.steps:
        used = debug_ids.intersection(step.anchor_ids)
        for aid in sorted(used):
            issues.append(Issue(
                "major", SYSTEM,
                f"Mission flow step {step.name!r} depends on debug-only anchor {aid!r}.",
                "Bind the step to a gameplay anchor instead.",
            ))

    # Interactables need an interaction contract to be server-arbitrated.
    for a in ctx.anchors:
        if a.type in ("door", "loot", "interaction") and a.extra.get("client_only"):
            issues.append(Issue(
                "major", SYSTEM,
                f"Interactable {a.id!r} is marked client_only; state changes would not replicate.",
                "Remove client_only or reclassify the anchor as presentation.",
                node=node_path_for(a),
            ))

    if not issues:
        issues.append(Issue("info", SYSTEM,
                            "All mission-critical nodes carry authority hints and stable network ids."))
    return issues
