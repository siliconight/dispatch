"""Gameplay Anchor Binder.

Normalizes upstream anchor records into one anchor list and converts Blender
Z-up coordinates to Godot Y-up.

Identity model (handoff spec section 5): every anchor carries a stable SHELL
ID — the upstream anchor id, deterministic across rebuilds. Shell IDs are not
network IDs. The production runtime maps a shell ID to whatever network
entity, replicated actor, or save-state record it chooses; Dispatch records
that mapping slot as ``runtime_binding: null``.
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

# Anchor types whose runtime state the production game must own
# server-side. Dispatch declares the requirement; it implements nothing.
RUNTIME_OWNED_TYPES = (
    "objective",
    "door",
    "loot",
    "extraction",
    "trigger",
    "breach_point",
    "interaction",
    "ai_spawn",
)

# Static placement data: consumed by the runtime, never replicated as
# stateful objects by Dispatch's declaration.
STATIC_ANCHOR_TYPES = ("player_start", "cover", "patrol_point")

# Debug-only anchors: never part of the handoff contract.
DEBUG_ANCHOR_TYPES = ("camera_debug",)

# anchor type -> adapter interface name the runtime-adapter mode can stub.
EXPECTED_ADAPTER = {
    "objective": "objective_point",
    "door": "openable_door",
    "loot": "lootable",
    "extraction": "extraction_zone",
    "trigger": "trigger_volume",
    "breach_point": "breachable",
    "interaction": "interactable",
    "ai_spawn": "ai_spawn_point",
}

# Integration status values (handoff spec section 8). Dispatch may set only
# the first two; the production game pipeline owns the rest.
DISPATCH_SETTABLE_STATUS = ("unimplemented", "adapter_available")
GAME_SETTABLE_STATUS = ("integrated", "verified_by_game_runtime")
INTEGRATION_STATUSES = DISPATCH_SETTABLE_STATUS + GAME_SETTABLE_STATUS

# Stateful types that a late-joining peer must receive current state for.
_LATE_JOIN_TYPES = ("objective", "door", "loot", "extraction", "trigger",
                    "breach_point", "interaction", "ai_spawn")
# Types whose outcome must survive into mission persistence.
_PERSISTENCE_TYPES = ("objective", "extraction", "loot", "breach_point")


@dataclass
class Anchor:
    id: str               # stable shell id (NOT a network id)
    type: str
    pos: tuple            # Godot-space (x, y, z), Y-up, meters
    rot_y: float = 0.0    # degrees around Godot up axis
    tags: tuple = ()
    objective: str = ""   # objective key for objective anchors
    source: str = ""      # which tool provided it
    integration_status: str = "unimplemented"
    extra: dict = field(default_factory=dict)

    @property
    def shell_id(self) -> str:
        return self.id

    def qualified_id(self, mission_id: str) -> str:
        """Namespaced shell id (handoff delta D4): two imported missions must
        not collide, so exported ids are '<mission_id>/<anchor_id>'."""
        return f"{mission_id}/{self.id}"

    @property
    def expected_adapter(self) -> str:
        return EXPECTED_ADAPTER.get(self.type, "")


#: GAMEPLAY EVENTS (0.6.0, the factory's roadmap 323). An anchor may carry an EVENT: data a game may ingest or
#: ignore, never behaviour Dispatch runs. The factory's walker: "they could mean nothing, but they could also be
#: ingested/used by the gameplay layer", and of zones a player stands in, "we don't do that, we just have the event
#: that we send (without spamming/rate limiting)". So a block names the event and HOW it fires, and nothing about what
#: follows -- no heat, timer or mission end:
#:   event   a dotted name, `alarm.*`, `score.*` or `zone.*`
#:   fires   `on_touch` (a fixture is used), `on_enter` / `on_exit` (a zone)
#:   repeat  `edge` -- once when the condition becomes true, not again until it has been false (standing in a zone
#:           sends one event, not one a frame) -- or `once`, once per mission
#:   audible a fact about the real alarm, where there is one
EVENT_PREFIXES = ("alarm.", "score.", "zone.")
EVENT_FIRES = ("on_touch", "on_enter", "on_exit")
EVENT_REPEAT = ("edge", "once")


def event_block(anchor) -> dict | None:
    """The anchor's event, normalised -- ``fires`` defaulting to `on_touch` and ``repeat`` to `edge` -- or None when
    it carries none. A block that names an event outside the vocabulary, or a firing rule Dispatch does not know,
    raises ValueError: a consumer could not read it the way it was meant. A `zone.*` event carries its
    ``radius`` (metres in plan, positive): the extent a body enters."""
    raw = anchor.extra.get("event") if hasattr(anchor, "extra") else None
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = {"event": raw}
    name = str(raw.get("event", ""))
    if not name.startswith(EVENT_PREFIXES):
        raise ValueError("anchor %s: event %r is not alarm.*, score.* or zone.*" % (anchor.id, name))
    out = {"event": name, "fires": str(raw.get("fires", "on_touch")), "repeat": str(raw.get("repeat", "edge"))}
    if out["fires"] not in EVENT_FIRES or out["repeat"] not in EVENT_REPEAT:
        raise ValueError("anchor %s: event %r fires %r repeat %r" % (anchor.id, name, out["fires"], out["repeat"]))
    if "audible" in raw:
        out["audible"] = bool(raw["audible"])
    for k in ("fixture", "room"):
        if raw.get(k):
            out[k] = str(raw[k])
    # A zone is a place a body enters, so it has an extent: `radius`, metres in plan around the anchor's position
    # (0.7.0). Without one `on_enter` has nothing to be entered, and a consumer would have to invent a size.
    if "radius" in raw or name.startswith("zone."):
        try:
            r = float(raw.get("radius"))
        except (TypeError, ValueError):
            r = float("nan")
        if not (r > 0.0 and r < float("inf")):
            raise ValueError("anchor %s: event %r needs a positive radius in metres, got %r"
                             % (anchor.id, name, raw.get("radius")))
        out["radius"] = r
    return out


def required_authority_for(anchor: Anchor) -> str:
    """Declared authority REQUIREMENT (not a description of anything built)."""
    if anchor.type in RUNTIME_OWNED_TYPES:
        return "server"
    return "none"


def runtime_requirements_for(anchor: Anchor) -> dict:
    """Declared requirements the production runtime must satisfy for this
    anchor (handoff spec section 4). Declarations only — Dispatch prescribes
    no networking library, RPC names, serialization, or entity IDs.
    """
    if anchor.type not in RUNTIME_OWNED_TYPES:
        return {}
    return {
        "authoritative_owner": "server",
        "replication_required": True,
        "late_join_state_required": anchor.type in _LATE_JOIN_TYPES,
        "mission_persistence_required": anchor.type in _PERSISTENCE_TYPES,
    }


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
