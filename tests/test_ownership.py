from dispatch.ownership import (FORBIDDEN_NODE_NAMES, build_anchor_registry,
                                build_ownership_requirements, node_path_for)


MID = "gas_station_robbery_001"


def test_ownership_requirements(ctx):
    o = ctx.ownership
    assert o["schema"] == "dispatch.runtime_ownership_requirements.v0.2"
    assert o["intended_model"] == "server_authoritative"
    assert "Presentation/Lighting" in o["presentation_roots"]
    reqs = {r["shell_id"]: r for r in o["anchors"]}
    # every runtime-owned anchor type is declared (namespaced), statics are not
    assert f"{MID}/cash_register" in reqs and f"{MID}/escape_vehicle" in reqs
    assert f"{MID}/player_start_01" not in reqs and f"{MID}/pump_cover_a" not in reqs
    rec = reqs[f"{MID}/cash_register"]
    rr = rec["runtime_requirements"]
    assert rr["authoritative_owner"] == "server"
    assert rr["replication_required"] is True
    assert rr["mission_persistence_required"] is True
    # AC3: always unimplemented in this file — Dispatch must not guess
    assert all(r["integration_status"] == "unimplemented" for r in o["anchors"])
    # declarations only — no network ids anywhere
    assert not any("net_id" in r for r in o["anchors"])


def test_anchor_registry(ctx):
    reg = ctx.registry
    assert reg["schema"] == "dispatch.gameplay_anchors.v0.2"
    by_id = {a["shell_id"]: a for a in reg["anchors"]}
    door = by_id[f"{MID}/front_door"]
    assert door["runtime_binding"] is None
    assert door["integration_status"] == "unimplemented"
    assert door["expected_adapter"] == "openable_door"
    assert door["required_authority"] == "server"
    assert door["source_tool"] == "deli_counter"
    assert door["transform"]["pos"] == [0.0, 0.0, 1.2]
    start = by_id[f"{MID}/player_start_01"]
    assert start["runtime_requirements"] == {}
    assert start["expected_adapter"] == ""
    assert start["required_authority"] == "none"
    # deterministic diffs: sorted by shell_id
    ids = [a["shell_id"] for a in reg["anchors"]]
    assert ids == sorted(ids)


def test_node_paths(ctx):
    by_id = {a.id: a for a in ctx.anchors}
    assert node_path_for(by_id["player_start_01"]) == "Functional/GameplayAnchors/PlayerStarts/player_start_01"
    assert node_path_for(by_id["clerk_spawn"]) == "Functional/GameplayAnchors/AISpawnZones/clerk_spawn"
    assert node_path_for(by_id["escape_vehicle"]) == "Functional/GameplayAnchors/ExtractionPoints/escape_vehicle"


def test_forbidden_names_constant():
    assert "MissionController" in FORBIDDEN_NODE_NAMES
    assert "Runtime" in FORBIDDEN_NODE_NAMES
