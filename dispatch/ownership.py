"""Runtime ownership requirements and the gameplay anchor registry.

Dispatch declares what the production runtime must satisfy; it implements
none of it (handoff spec sections 4, 5, 8). Node placement keeps gameplay
anchors in the Functional layer, cleanly separated from Presentation.
"""

from __future__ import annotations

from . import __version__
from .anchors import (DEBUG_ANCHOR_TYPES, RUNTIME_OWNED_TYPES,
                      required_authority_for, runtime_requirements_for)

FUNCTIONAL_ROOTS = (
    "Functional/Geometry",
    "Functional/Collision",
    "Functional/GameplayAnchors",
    "Functional/NavigationHints",
)

PRESENTATION_ROOTS = (
    "Presentation/Props",
    "Presentation/Materials",
    "Presentation/Decals",
    "Presentation/Lighting",
    "Presentation/Atmosphere",
)

# Node names that must never appear in a handoff scene (handoff spec
# section 3) — they would imply Dispatch ships a production runtime.
FORBIDDEN_NODE_NAMES = (
    "Runtime",
    "MissionController",
    "AuthorityController",
    "NetworkController",
    "ReplicationController",
)

# anchor type -> Functional/GameplayAnchors subtree
ANCHOR_PARENT = {
    "player_start": "Functional/GameplayAnchors/PlayerStarts",
    "objective": "Functional/GameplayAnchors/Objectives",
    "extraction": "Functional/GameplayAnchors/ExtractionPoints",
    "door": "Functional/GameplayAnchors/Interactables",
    "loot": "Functional/GameplayAnchors/Interactables",
    "interaction": "Functional/GameplayAnchors/Interactables",
    "breach_point": "Functional/GameplayAnchors/Interactables",
    "trigger": "Functional/GameplayAnchors/Triggers",
    "ai_spawn": "Functional/GameplayAnchors/AISpawnZones",
    "patrol_point": "Functional/GameplayAnchors/PatrolRoutes",
    "cover": "Functional/GameplayAnchors/CoverPoints",
    "camera_debug": "Functional/GameplayAnchors/Debug",
}

ANCHOR_GROUPS = ("PlayerStarts", "Objectives", "ExtractionPoints",
                 "Interactables", "Triggers", "AISpawnZones",
                 "PatrolRoutes", "CoverPoints", "Debug")


def node_path_for(anchor) -> str:
    parent = ANCHOR_PARENT.get(anchor.type, "Functional/GameplayAnchors/Triggers")
    return f"{parent}/{anchor.id}"


def layer_for(anchor) -> str:
    if anchor.type in DEBUG_ANCHOR_TYPES:
        return "debug"
    return "functional"


def build_ownership_requirements(spec, anchors: list) -> dict:
    """runtime_ownership_requirements.json — what the future runtime must
    satisfy (schema dispatch.runtime_ownership_requirements.v0.2, delta D3).
    Requirements, not a map: Dispatch validates these declarations exist and
    are internally consistent; it does not prescribe networking library, RPC
    names, replication frequency, serialization, prediction, reconciliation,
    persistence backend, or final network entity IDs. integration_status is
    always "unimplemented" here — Dispatch has no way to know otherwise and
    must not guess (adapter_available appears only in gameplay_anchors.json
    when runtime-adapter mode ships matching stubs).
    """
    recs = []
    for a in sorted(anchors, key=lambda a: a.qualified_id(spec.mission_id)):
        rr = runtime_requirements_for(a)
        if rr:
            recs.append({
                "shell_id": a.qualified_id(spec.mission_id),
                "anchor_type": a.type,
                "node": node_path_for(a),
                "integration_status": "unimplemented",
                "expected_adapter": a.expected_adapter,
                "runtime_requirements": rr,
            })
    return {
        "schema": "dispatch.runtime_ownership_requirements.v0.2",
        "dispatch_version": __version__,
        "mission_id": spec.mission_id,
        "statement": ("Declared requirements for the production game runtime. "
                      "Dispatch implements no authority, RPCs, replication, "
                      "persistence, or late-join recovery."),
        "intended_model": spec.net_model,
        "functional_roots": list(FUNCTIONAL_ROOTS),
        "presentation_roots": list(PRESENTATION_ROOTS),
        "anchors": recs,
    }


def build_anchor_registry(spec, anchors: list) -> dict:
    """gameplay_anchors.json — the shell-id registry. runtime_binding stays
    null until the production pipeline maps each shell id to its own entity;
    integration_status only ever leaves Dispatch as 'unimplemented' or
    'adapter_available' (handoff spec section 8).
    """
    items = []
    for a in sorted(anchors, key=lambda a: a.qualified_id(spec.mission_id)):
        items.append({
            "shell_id": a.qualified_id(spec.mission_id),
            "anchor_type": a.type,
            "node": node_path_for(a),
            "transform": {"pos": list(a.pos), "rot_y_deg": a.rot_y},
            "tags": list(a.tags),
            "objective": a.objective,
            "source_tool": a.source,
            "source_building": str(a.extra.get("building", "")),
            "layer": layer_for(a),
            "required_authority": required_authority_for(a),
            "expected_adapter": a.expected_adapter,
            "integration_status": a.integration_status,
            "runtime_binding": None,
            "runtime_requirements": runtime_requirements_for(a),
        })
    return {
        "schema": "dispatch.gameplay_anchors.v0.2",
        "dispatch_version": __version__,
        "mission_id": spec.mission_id,
        "anchors": items,
    }
