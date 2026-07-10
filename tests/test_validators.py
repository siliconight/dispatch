import json
from pathlib import Path

from dispatch.assembler import build_context
from dispatch.spec import load_spec
from dispatch.validators import run_all
from conftest import edit_json


def _issues(world):
    ctx = build_context(load_spec(world / "dispatch.mission.json"))
    return ctx, run_all(ctx)


def _by_sev(issues, sev):
    return [i for i in issues if i.severity == sev]


def test_happy_path_no_blockers(world):
    _ctx, issues = _issues(world)
    assert _by_sev(issues, "blocker") == []
    assert _by_sev(issues, "major") == []


def test_missing_player_starts_blocker(world):
    p = world / "build/lot/lot.gameplay.json"
    edit_json(p, lambda d: d.update(
        anchors=[a for a in d["anchors"] if a["type"] != "player_start"]))
    _ctx, issues = _issues(world)
    msgs = " | ".join(i.message for i in _by_sev(issues, "blocker"))
    assert "No player_start anchors" in msgs


def test_overlapping_spawns_blocker(world):
    p = world / "build/lot/lot.gameplay.json"
    def overlap(d):
        for a in d["anchors"]:
            if a["type"] == "player_start":
                a["pos"] = [0, -18, 0]
    edit_json(p, overlap)
    _ctx, issues = _issues(world)
    assert any("overlap" in i.message for i in _by_sev(issues, "blocker"))


def test_spawn_near_ai_major(world):
    p = world / "build/lot/lot.gameplay.json"
    edit_json(p, lambda d: d["anchors"].append(
        {"id": "ambush", "type": "ai_spawn", "pos": [0, -17, 0]}))
    _ctx, issues = _issues(world)
    assert any("spawn-killed" in i.message for i in _by_sev(issues, "major"))


def test_anchor_off_nav_blocker(world):
    p = world / "build/deli_counter/shell.gameplay.json"
    def strand(d):
        for a in d["anchors"]:
            if a["id"] == "cash_register":
                a["pos"] = [40, 40, 0]
    edit_json(p, strand)
    _ctx, issues = _issues(world)
    assert any("cash_register" in i.message and "nav" in i.message
               for i in _by_sev(issues, "blocker"))


def test_cut_link_breaks_reachability(world):
    p = world / "build/lot/lot.nav_hints.json"
    edit_json(p, lambda d: d.update(
        links=[l for l in d["links"] if l != ["curb", "lot_edge"]]))
    _ctx, issues = _issues(world)
    blockers = _by_sev(issues, "blocker")
    assert any("cannot be reached" in i.message for i in blockers)


def test_nav_island_reported(world):
    p = world / "build/lot/lot.nav_hints.json"
    edit_json(p, lambda d: d["nodes"].append({"id": "orphan", "pos": [90, 90, 0]}))
    _ctx, issues = _issues(world)
    assert any("islands" in i.message for i in _by_sev(issues, "moderate"))


def test_performance_budget(world):
    edit_json(world / "dispatch.mission.json",
              lambda d: d.update(budgets={"max_lights": 5}))
    _ctx, issues = _issues(world)
    assert any(i.system == "performance" and "Light count" in i.message
               for i in _by_sev(issues, "moderate"))


def test_validation_gates_respected(world):
    edit_json(world / "dispatch.mission.json",
              lambda d: d["validation"].update(require_performance_budget=False))
    edit_json(world / "dispatch.mission.json",
              lambda d: d.update(budgets={"max_lights": 1}))
    _ctx, issues = _issues(world)
    assert not any(i.system == "performance" for i in issues)
