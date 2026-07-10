"""Network Authority Model (TDD 12).

Builds network_authority_map.json: which scene paths are server-authoritative,
which are client-side presentation, plus a replication registry with stable
network IDs for every replicated gameplay anchor.
"""

from __future__ import annotations

from .anchors import CLIENT_ANCHOR_TYPES, SERVER_ANCHOR_TYPES

SERVER_ROOTS = (
    "Runtime/MissionController",
    "Runtime/ObjectiveController",
    "Runtime/SpawnController",
    "Runtime/ExtractionController",
    "Runtime/NetworkAuthority",
    "Runtime/ReplicationRegistry",
    "Gameplay/Objectives",
    "Gameplay/Interactables",
    "Gameplay/ExtractionPoints",
    "Gameplay/Triggers",
    "Gameplay/AI",
)

CLIENT_ROOTS = (
    "World/LightingRoot",
    "World/FXRoot",
    "World/AudioRoot",
    "World/VisualsRoot",
    "Runtime/DebugOverlay",
)

# anchor type -> Gameplay subtree it lives under
ANCHOR_PARENT = {
    "player_start": "Gameplay/PlayerStarts",
    "objective": "Gameplay/Objectives",
    "extraction": "Gameplay/ExtractionPoints",
    "door": "Gameplay/Interactables",
    "loot": "Gameplay/Interactables",
    "interaction": "Gameplay/Interactables",
    "breach_point": "Gameplay/Interactables",
    "trigger": "Gameplay/Triggers",
    "ai_spawn": "Gameplay/AI/SpawnZones",
    "patrol_point": "Gameplay/AI/PatrolRoutes",
    "cover": "Gameplay/AI/CoverPoints",
    "camera_debug": "Runtime/DebugOverlay",
}


def node_path_for(anchor) -> str:
    parent = ANCHOR_PARENT.get(anchor.type, "Gameplay/Triggers")
    return f"{parent}/{anchor.id}"


def authority_for(anchor) -> str:
    if anchor.type in SERVER_ANCHOR_TYPES:
        return "server"
    if anchor.type in CLIENT_ANCHOR_TYPES:
        return "client"
    # player_start, cover, patrol_point: static placement data, not replicated
    # runtime state; owned by the server scene but carry no net id.
    return "static"


def build_authority_map(spec, anchors: list) -> dict:
    registry = []
    for a in sorted(anchors, key=lambda a: (a.type, a.id)):
        if a.net_id:
            registry.append(
                {
                    "net_id": a.net_id,
                    "node": node_path_for(a),
                    "anchor_type": a.type,
                    "owner": "server",
                }
            )
    return {
        "schema": "dispatch.authority.v0.1",
        "mission_id": spec.mission_id,
        "model": spec.net_model,
        "server_authoritative": list(SERVER_ROOTS),
        "client_presentation": list(CLIENT_ROOTS),
        "replication_registry": registry,
    }
