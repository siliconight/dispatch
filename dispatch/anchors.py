"""Gameplay Anchor Binder (TDD 13.3).

Normalizes upstream anchor records into one anchor list, converts
Blender Z-up coordinates to Godot Y-up, and assigns stable network IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ANCHOR_TYPES = (
    "player_start",
    "ai_spawn",
    "objective",
    "door",
    "loot",
    "cover",
    "patrol_point",
    "extraction",
    "trigger",
    "breach_point",
    "interaction",
    "camera_debug",
)

# Anchor types whose runtime state must be server-authoritative.
SERVER_ANCHOR_TYPES = (
    "objective",
    "door",
    "loot",
    "extraction",
    "trigger",
    "breach_point",
    "interaction",
    "ai_spawn",
)

# Presentation-only anchor types: never replicated.
CLIENT_ANCHOR_TYPES = ("camera_debug",)


@dataclass
class Anchor:
    id: str
    type: str
    pos: tuple            # Godot-space (x, y, z), Y-up, meters
    rot_y: float = 0.0    # degrees around Godot up axis
    tags: tuple = ()
    objective: str = ""   # objective key for objective anchors
    source: str = ""      # which tool provided it
    net_id: int = 0       # stable network id (0 = not replicated)
    extra: dict = field(default_factory=dict)


def blender_to_godot(pos) -> tuple:
    """Blender Z-up -> Godot Y-up: (x, y, z) -> (x, z, -y).

    Matches the pipeline-wide convention used by the Lux light loader.
    """
    x, y, z = float(pos[0]), float(pos[1]), float(pos[2])
    return (x, z, -y)


def normalize_anchors(records: list, source: str, up_axis: str = "z") -> list:
    """Turn raw anchor dicts into Anchor objects.

    up_axis="z" (Blender-style upstream export, the pipeline default)
    converts positions; up_axis="y" passes them through.
    Unknown anchor types are kept (typed as-is) so upstream vocabulary can
    grow, but validators only reason about known types.
    """
    out = []
    for rec in records:
        raw_pos = rec.get("pos", rec.get("position", (0.0, 0.0, 0.0)))
        pos = blender_to_godot(raw_pos) if up_axis == "z" else tuple(float(v) for v in raw_pos)
        out.append(
            Anchor(
                id=str(rec.get("id", "")),
                type=str(rec.get("type", "")),
                pos=pos,
                rot_y=float(rec.get("rot_y", rec.get("rotation_y", 0.0))),
                tags=tuple(rec.get("tags", ())),
                objective=str(rec.get("objective", "")),
                source=source,
                extra={k: v for k, v in rec.items()
                       if k not in ("id", "type", "pos", "position", "rot_y",
                                    "rotation_y", "tags", "objective")},
            )
        )
    return out


def assign_net_ids(anchors: list, start: int = 1000) -> None:
    """Deterministic, stable network IDs for replicated anchors.

    Sorted by (type, id) so a rebuild with unchanged upstream data yields
    identical IDs (TDD 13.5: replicated objects have stable IDs).
    """
    nid = start
    for a in sorted(anchors, key=lambda a: (a.type, a.id)):
        if a.type in SERVER_ANCHOR_TYPES:
            a.net_id = nid
            nid += 1


def by_type(anchors: list, kind: str) -> list:
    return [a for a in anchors if a.type == kind]


def find_duplicate_ids(anchors: list) -> list:
    seen, dupes = set(), []
    for a in anchors:
        key = a.id
        if key in seen:
            dupes.append(key)
        seen.add(key)
    return dupes
