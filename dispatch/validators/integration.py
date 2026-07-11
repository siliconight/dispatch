"""Integration Readiness Validator (handoff spec section 7).

Validates that the mission shell is ready to RECEIVE an authoritative
runtime: every mission-critical anchor has a stable shell ID, a declared
runtime ownership requirement, a declared replication requirement, and a
valid functional-layer placement.

Dispatch cannot and does not validate actual server authority, RPC security,
replication correctness, prediction, reconciliation, late-join recovery,
persistence correctness, gameplay behavior, or shipping online playability.
"""

from __future__ import annotations

from ..anchors import (DISPATCH_SETTABLE_STATUS, RUNTIME_OWNED_TYPES, by_type,
                       runtime_requirements_for)
from ..ownership import PRESENTATION_ROOTS, node_path_for
from . import Issue

SYSTEM = "integration_readiness"


def validate(ctx) -> list:
    issues = []
    spec = ctx.spec

    # Every runtime-owned anchor must carry a complete requirement declaration.
    declared = {r["shell_id"]: r["runtime_requirements"]
                for r in ctx.ownership.get("anchors", [])}
    for a in ctx.anchors:
        if a.type not in RUNTIME_OWNED_TYPES:
            continue
        rr = declared.get(a.qualified_id(spec.mission_id))
        if not rr:
            issues.append(Issue(
                "blocker", SYSTEM,
                f"Anchor {a.shell_id!r} ({a.type}) is missing its runtime ownership requirement declaration.",
                "Re-run the build; if it persists this is a Dispatch bug.",
                node=node_path_for(a),
            ))
            continue
        if "authoritative_owner" not in rr or "replication_required" not in rr:
            issues.append(Issue(
                "blocker", SYSTEM,
                f"Anchor {a.shell_id!r} declaration is incomplete (owner/replication flags missing).",
                "Re-run the build.",
                node=node_path_for(a),
            ))
        # Internal consistency: persistence or late-join without replication
        # is not satisfiable.
        if (rr.get("mission_persistence_required") or rr.get("late_join_state_required")) \
                and not rr.get("replication_required"):
            issues.append(Issue(
                "major", SYSTEM,
                f"Anchor {a.shell_id!r} declares persistence/late-join state without replication.",
                "Declare replication_required for stateful anchors.",
                node=node_path_for(a),
            ))

    # Dispatch may only ever emit unimplemented / adapter_available.
    for a in ctx.anchors:
        if a.integration_status not in DISPATCH_SETTABLE_STATUS:
            issues.append(Issue(
                "blocker", SYSTEM,
                f"Anchor {a.shell_id!r} carries integration status {a.integration_status!r}, "
                "which only the production game pipeline may set.",
                "Statuses 'integrated' and 'verified_by_game_runtime' are set downstream, never by Dispatch.",
                node=node_path_for(a),
            ))

    # No gameplay anchors may live under presentation roots.
    for a in ctx.anchors:
        path = node_path_for(a)
        if a.type in RUNTIME_OWNED_TYPES and any(path.startswith(p) for p in PRESENTATION_ROOTS):
            issues.append(Issue(
                "blocker", SYSTEM,
                f"Gameplay anchor {a.shell_id!r} is placed under a presentation root.",
                "Move it into Functional/GameplayAnchors.",
                node=path,
            ))

    # Player starts must cover the intended player range.
    starts = by_type(ctx.anchors, "player_start")
    if len(starts) < spec.players_max:
        issues.append(Issue(
            "blocker", SYSTEM,
            f"Mission targets up to {spec.players_max} players but only {len(starts)} player start(s) exist.",
            f"Export {spec.players_max - len(starts)} more player_start anchor(s).",
        ))

    # Extraction must exist with a declared server-owned requirement.
    for a in by_type(ctx.anchors, "extraction"):
        rr = runtime_requirements_for(a)
        if rr.get("authoritative_owner") != "server":
            issues.append(Issue(
                "blocker", SYSTEM,
                f"Extraction {a.shell_id!r} does not declare server ownership; extraction completion must be server-decided.",
                "Re-run the build.",
                node=node_path_for(a),
            ))

    # Beats must not depend on debug-only anchors.
    debug_ids = {a.id for a in by_type(ctx.anchors, "camera_debug")}
    for beat in ctx.beats.beats:
        for aid in sorted(debug_ids.intersection(beat.anchor_ids)):
            issues.append(Issue(
                "major", SYSTEM,
                f"Proposed beat {beat.id!r} depends on debug-only anchor {aid!r}.",
                "Bind the beat to a gameplay anchor instead.",
            ))

    # Interactables flagged client_only cannot satisfy their own declaration.
    for a in ctx.anchors:
        if a.type in ("door", "loot", "interaction", "breach_point") and a.extra.get("client_only"):
            issues.append(Issue(
                "major", SYSTEM,
                f"Interactable {a.shell_id!r} is marked client_only, contradicting its server-ownership requirement.",
                "Remove client_only or reclassify the anchor as presentation.",
                node=node_path_for(a),
            ))

    if not issues:
        issues.append(Issue(
            "info", SYSTEM,
            "Every mission-critical anchor has a stable shell ID, a declared runtime ownership "
            "requirement, a declared replication requirement, and a valid functional-layer placement. "
            "Online gameplay itself is NOT verified by Dispatch.",
        ))
    return issues
