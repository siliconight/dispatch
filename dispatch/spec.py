"""Mission spec (dispatch.mission.json) loading and validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import SCHEMA_MISSION, SCHEMA_MISSION_LEGACY, DispatchError

KNOWN_TOOLS = ("deli_counter", "lot", "zoo", "patina", "lux")
REQUIRED_TOOLS = ("deli_counter", "lot")
VALID_MODES = ("online_coop_pve",)
VALID_NET_MODELS = ("server_authoritative",)
_ID_RE = re.compile(r"^[a-z0-9_]+$")

DEFAULT_VALIDATION = {
    "require_online_runtime_readiness": True,
    "require_all_objectives_reachable": True,
    "require_all_players_spawn_valid": True,
    "require_ai_navmesh": True,
    "require_cover_score": False,
    "require_performance_budget": True,
}

DEFAULT_BUDGETS = {
    "max_props": 400,
    "max_lights": 48,
    "max_shadow_lights": 8,
    "max_unique_materials": 96,
    "max_nav_nodes": 4000,
}

DEFAULT_TUNING = {
    # Meters. Anchors farther than this from any nav node are "outside nav".
    "anchor_nav_radius": 3.0,
    # Auto-bridge distance between the DC and Lot nav graphs.
    "nav_bridge_radius": 1.5,
    # Minimum spacing between player starts.
    "spawn_min_spacing": 1.0,
    # Clear radius a player capsule needs.
    "spawn_clear_radius": 0.5,
}


@dataclass
class MissionSpec:
    mission_id: str
    title: str
    engine: str
    mode: str
    players_min: int
    players_max: int
    players_preferred: int
    net_model: str
    theme: str
    inputs: dict            # tool -> manifest path (as written in the spec)
    mission_flow: list      # list of step dicts
    validation: dict
    budgets: dict
    tuning: dict
    spec_path: Path
    legacy_schema: bool = False
    raw: dict = field(repr=False, default_factory=dict)

    @property
    def spec_dir(self) -> Path:
        return self.spec_path.parent


def load_spec(path: str | Path) -> MissionSpec:
    p = Path(path)
    if not p.is_file():
        raise DispatchError(
            f"mission spec not found: {p}",
            expected=str(p),
            suggested_fix="Check the path, or run `dispatch init <mission_id>` to scaffold one.",
        )
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DispatchError(
            f"mission spec is not valid JSON: {p} ({e})",
            suggested_fix="Fix the JSON syntax error at the line/column above.",
        )
    return validate_spec(raw, p)


def validate_spec(raw: dict, spec_path: Path) -> MissionSpec:
    schema = raw.get("schema")
    if schema not in (SCHEMA_MISSION, SCHEMA_MISSION_LEGACY):
        raise DispatchError(
            f"unsupported mission schema {schema!r}",
            expected=f'"schema": "{SCHEMA_MISSION}" (v0.1 is still read for compatibility)',
            suggested_fix="Update the spec schema field or upgrade Dispatch.",
        )

    mission_id = raw.get("mission_id", "")
    if not _ID_RE.match(mission_id or ""):
        raise DispatchError(
            f"mission_id {mission_id!r} is missing or invalid",
            expected="lowercase letters, digits and underscores, e.g. gas_station_robbery_001",
            suggested_fix="Set a valid mission_id in the spec.",
        )

    mode = raw.get("mode", "online_coop_pve")
    if mode not in VALID_MODES:
        raise DispatchError(
            f"unsupported mode {mode!r}",
            expected=f"one of {list(VALID_MODES)}",
            suggested_fix="Dispatch v0.1 targets online co-op PvE only.",
        )

    players = raw.get("players", {}) or {}
    pmin = int(players.get("min", 1))
    pmax = int(players.get("max", 4))
    ppref = int(players.get("preferred", pmax))
    if not (1 <= pmin <= pmax <= 4):
        raise DispatchError(
            f"invalid player counts min={pmin} max={pmax}",
            expected="1 <= min <= max <= 4",
            suggested_fix="Dispatch v0.1 supports 1 to 4 networked players.",
        )

    net = raw.get("networking", {}) or {}
    net_model = net.get("model", "server_authoritative")
    if net_model not in VALID_NET_MODELS:
        raise DispatchError(
            f"unsupported networking model {net_model!r}",
            expected=f"one of {list(VALID_NET_MODELS)}",
            suggested_fix="Dispatch v0.1 assumes server-authoritative mission state.",
        )

    inputs = raw.get("inputs", {}) or {}
    unknown = [k for k in inputs if k not in KNOWN_TOOLS]
    if unknown:
        raise DispatchError(
            f"unknown input tool keys: {unknown}",
            expected=f"keys from {list(KNOWN_TOOLS)}",
            suggested_fix="Remove or rename the unknown input keys in the spec.",
        )
    missing = [k for k in REQUIRED_TOOLS if k not in inputs]
    if missing:
        raise DispatchError(
            f"required inputs missing from spec: {missing}",
            expected='"inputs": { "deli_counter": ..., "lot": ... }',
            suggested_fix="Point the spec at the Deli Counter and Lot build outputs.",
        )

    flow = raw.get("mission_flow", []) or []
    if not isinstance(flow, list) or not flow:
        raise DispatchError(
            "mission_flow is missing or empty",
            expected="a non-empty list of flow steps",
            suggested_fix='Add at least a spawn step and one objective, e.g. [{"step": "spawn", "location_tag": "street_start"}].',
        )
    seen_steps = set()
    for i, step in enumerate(flow):
        if not isinstance(step, dict) or "step" not in step:
            raise DispatchError(
                f"mission_flow[{i}] has no \"step\" name",
                expected='{"step": "loot", "objective": "open_cash_register"}',
                suggested_fix="Give every flow entry a step name.",
            )
        name = step["step"]
        if name in seen_steps:
            raise DispatchError(
                f"mission_flow step {name!r} appears more than once",
                suggested_fix="Step names must be unique; suffix repeated beats (loot_a, loot_b).",
            )
        seen_steps.add(name)

    validation = dict(DEFAULT_VALIDATION)
    validation.update(raw.get("validation", {}) or {})
    budgets = dict(DEFAULT_BUDGETS)
    budgets.update(raw.get("budgets", {}) or {})
    tuning = dict(DEFAULT_TUNING)
    tuning.update(raw.get("tuning", {}) or {})

    return MissionSpec(
        mission_id=mission_id,
        title=raw.get("title", mission_id),
        engine=raw.get("engine", "godot_4_7"),
        mode=mode,
        players_min=pmin,
        players_max=pmax,
        players_preferred=ppref,
        net_model=net_model,
        theme=raw.get("theme", ""),
        inputs=inputs,
        mission_flow=flow,
        validation=validation,
        budgets=budgets,
        tuning=tuning,
        spec_path=spec_path,
        legacy_schema=(schema == SCHEMA_MISSION_LEGACY),
        raw=raw,
    )
