"""Regenerate examples/gas_station_robbery_001 fixture data.

Deterministic. Positions are authored in Blender Z-up space (the pipeline
export convention); Dispatch converts on import. Run from repo root:

    python scripts/make_example.py
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples" / "gas_station_robbery_001"


def minimal_glb() -> bytes:
    """Smallest valid GLB: header + JSON chunk with an empty scene."""
    doc = json.dumps({
        "asset": {"version": "2.0", "generator": "dispatch example fixture"},
        "scenes": [{"nodes": []}],
        "scene": 0,
    }).encode("utf-8")
    pad = (4 - len(doc) % 4) % 4
    doc += b" " * pad
    chunk = struct.pack("<II", len(doc), 0x4E4F534A) + doc  # JSON chunk
    header = struct.pack("<III", 0x46546C67, 2, 12 + len(chunk))
    return header + chunk


def _writer(base: Path):
    def w(rel: str, data) -> None:
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            p.write_bytes(data)
        else:
            p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return w


def main(target: Path = None) -> None:
    base = Path(target) if target else EX
    w = _writer(base)
    glb = minimal_glb()

    # --- Deli Counter: gas station shell -------------------------------------
    w("build/deli_counter/shell.glb", glb)
    w("build/deli_counter/shell.gameplay.json", {
        "schema": "dc.gameplay.v1",
        "license": {"name": "proprietary-siliconight", "source": "deli_counter"},
        "up_axis": "z",
        "anchors": [
            {"id": "store_door", "type": "objective", "pos": [0, -1, 0],
             "objective": "enter_store", "tags": ["entry"]},
            {"id": "front_door", "type": "door", "pos": [0, -1.2, 0], "tags": ["entry"]},
            {"id": "cash_register", "type": "objective", "pos": [-4, 3.5, 0],
             "objective": "open_cash_register", "tags": ["loot_room"]},
            {"id": "register_loot", "type": "loot", "pos": [-4, 3.8, 0]},
            {"id": "clerk_spawn", "type": "ai_spawn", "pos": [4, 5, 0], "tags": ["interior"]},
            {"id": "backroom_guard", "type": "ai_spawn", "pos": [0, 6.5, 0], "tags": ["interior"]},
            {"id": "shelf_cover_a", "type": "cover", "pos": [-2, 2, 0]},
            {"id": "shelf_cover_b", "type": "cover", "pos": [2, 3, 0]},
            {"id": "aisle_patrol_a", "type": "patrol_point", "pos": [0, 2, 0]},
            {"id": "aisle_patrol_b", "type": "patrol_point", "pos": [4, 6, 0]},
        ],
        "props": [
            {"asset_id": "shelf_unit_01", "pos": [-2, 2.2, 0], "rot_y": 0},
            {"asset_id": "shelf_unit_01", "pos": [2, 3.2, 0], "rot_y": 90},
        ],
    })
    w("build/deli_counter/shell.collision.json", {"schema": "dc.collision.v1", "hulls": 24})
    w("build/deli_counter/shell.nav_hints.json", {
        "schema": "dc.nav_hints.v1",
        "up_axis": "z",
        "nodes": [
            {"id": "door", "pos": [0, -1.5, 0]},
            {"id": "sales_floor", "pos": [0, 2, 0]},
            {"id": "register", "pos": [-4, 3, 0]},
            {"id": "aisle_east", "pos": [4, 6, 0]},
            {"id": "backroom", "pos": [0, 6, 0]},
        ],
        "links": [["door", "sales_floor"], ["sales_floor", "register"],
                  ["sales_floor", "aisle_east"], ["aisle_east", "backroom"],
                  ["sales_floor", "backroom"]],
    })

    # --- Lot: corner lot with street approach --------------------------------
    w("build/lot/lot.glb", glb)
    w("build/lot/lot.layout.json", {
        "schema": "lot.layout.v1",
        "license": {"name": "proprietary-siliconight", "source": "lot"},
        "up_axis": "z",
        "site": "delco_corner_lot",
        "bounds": [[-14, -22, 0], [14, 12, 8]],
    })
    w("build/lot/lot.gameplay.json", {
        "schema": "lot.gameplay.v1",
        "up_axis": "z",
        "anchors": [
            {"id": "player_start_01", "type": "player_start", "pos": [-3, -18, 0],
             "rot_y": 0, "tags": ["street_start"]},
            {"id": "player_start_02", "type": "player_start", "pos": [-1, -18, 0],
             "rot_y": 0, "tags": ["street_start"]},
            {"id": "player_start_03", "type": "player_start", "pos": [1, -18, 0],
             "rot_y": 0, "tags": ["street_start"]},
            {"id": "player_start_04", "type": "player_start", "pos": [3, -18, 0],
             "rot_y": 0, "tags": ["street_start"]},
            {"id": "forecourt_marker", "type": "objective", "pos": [0, -6, 0],
             "objective": "reach_gas_station", "tags": ["forecourt"]},
            {"id": "escape_vehicle", "type": "extraction", "pos": [5, -17, 0],
             "objective": "reach_escape_vehicle", "tags": ["street"]},
            {"id": "pump_cover_a", "type": "cover", "pos": [-2.5, -6, 0]},
            {"id": "pump_cover_b", "type": "cover", "pos": [2.5, -6, 0]},
        ],
        "props": [
            {"asset_id": "dumpster_01", "pos": [8, -4, 0], "rot_y": 180},
        ],
    })
    w("build/lot/lot.nav_hints.json", {
        "schema": "lot.nav_hints.v1",
        "up_axis": "z",
        "nodes": [
            {"id": "street_w", "pos": [-3, -18, 0]},
            {"id": "street_c", "pos": [0, -18, 0]},
            {"id": "street_e", "pos": [3, -18, 0]},
            {"id": "curb", "pos": [0, -14, 0]},
            {"id": "lot_edge", "pos": [0, -10, 0]},
            {"id": "forecourt", "pos": [0, -6, 0]},
            {"id": "storefront", "pos": [0, -2.5, 0]},
            {"id": "side_alley", "pos": [8, -4, 0]},
        ],
        "links": [["street_w", "street_c"], ["street_c", "street_e"],
                  ["street_c", "curb"], ["curb", "lot_edge"],
                  ["lot_edge", "forecourt"], ["forecourt", "storefront"],
                  ["forecourt", "side_alley"]],
    })

    # --- Zoo: prop catalog ----------------------------------------------------
    w("build/zoo/zoo.catalog.json", {
        "schema": "zoo.catalog.v1",
        "license": {"name": "proprietary-siliconight", "source": "zoo"},
        "assets": [
            {"asset_id": "dumpster_01", "category": "cover",
             "theme_tags": ["urban", "delco", "gas_station", "1990s"],
             "gameplay_tags": ["medium_cover", "blocks_los"],
             "collision": "simple_static", "nav_behavior": "obstacle",
             "recommended_use": ["alley", "parking_lot", "service_area"]},
            {"asset_id": "shelf_unit_01", "category": "cover",
             "theme_tags": ["retail", "1990s"],
             "gameplay_tags": ["medium_cover"],
             "collision": "simple_static", "nav_behavior": "obstacle",
             "recommended_use": ["sales_floor"]},
        ],
    })
    w("build/zoo/props/dumpster_01.glb", glb)
    w("build/zoo/props/dumpster_01.json", {"asset_id": "dumpster_01"})
    w("build/zoo/props/shelf_unit_01.glb", glb)
    w("build/zoo/props/shelf_unit_01.json", {"asset_id": "shelf_unit_01"})

    # --- Patina: styled shell ---------------------------------------------------
    w("build/patina/shell.patina.glb", glb)
    w("build/patina/shell.patina.json", {
        "schema": "patina.shell.v1",
        "license": {"name": "proprietary-siliconight", "source": "patina"},
        "materials": [f"mat_{i:02d}" for i in range(14)],
    })
    (base / "build/patina/textures").mkdir(parents=True, exist_ok=True)
    (base / "build/patina/textures/README.txt").write_text(
        "placeholder texture dir for the example fixture\n", encoding="utf-8")

    # --- Lux: lighting profile ---------------------------------------------------
    w("build/lux/lux.profile.json", {
        "schema": "lux.profile.v1",
        "license": {"name": "proprietary-siliconight", "source": "lux"},
        "preset": "gas_station_fluorescent",
        "time_of_day": "night",
    })
    w("build/lux/lux.lighting.json", {
        "schema": "lux.lighting.v1",
        "lights": ([{"kind": "fluorescent", "shadows": False}] * 16
                   + [{"kind": "area", "shadows": True}] * 3),
    })
    w("build/lux/lux.volumes.json", {"schema": "lux.volumes.v1", "volumes": []})

    # --- Mission spec (TDD section 9) ------------------------------------------
    w("dispatch.mission.json", {
        "schema": "dispatch.mission.v0.2",
        "mission_id": "gas_station_robbery_001",
        "title": "Gas Station Robbery",
        "engine": "godot_4_7",
        "mode": "online_coop_pve",
        "players": {"min": 1, "max": 4, "preferred": 4},
        "networking": {"model": "server_authoritative", "critical_state_owner": "server"},
        "theme": "delco_1997_gas_station",
        "inputs": {
            "deli_counter": "build/deli_counter/shell.gameplay.json",
            "lot": "build/lot/lot.layout.json",
            "zoo": "build/zoo/zoo.catalog.json",
            "patina": "build/patina/shell.patina.json",
            "lux": "build/lux/lux.profile.json",
        },
        "mission_flow": [
            {"step": "spawn", "location_tag": "street_start"},
            {"step": "approach", "objective": "reach_gas_station"},
            {"step": "civilian_mode", "objective": "enter_store"},
            {"step": "dangerous_mode", "trigger": "weapon_fired_or_alarm_started"},
            {"step": "loot", "objective": "open_cash_register"},
            {"step": "escape", "objective": "reach_escape_vehicle"},
        ],
        "validation": {
            "require_online_runtime_readiness": True,
            "require_all_objectives_reachable": True,
            "require_all_players_spawn_valid": True,
            "require_ai_navmesh": True,
            "require_cover_score": False,
            "require_performance_budget": True,
        },
    })
    print(f"example written to {base}")


if __name__ == "__main__":
    main()
