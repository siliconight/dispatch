"""Interactives reach the handoff: roadmap item 46, step 2.

Deli Counter declares one replicable state machine per interactive fixture,
Lot concatenates them into the site — and until now the mission shell package
contained zero files mentioning "interactive". Dispatch now ships the
declaration VERBATIM beside gameplay_anchors.json (the gameplay side of the
packaging split): ids are the network handle, so nothing rewrites them, and
Dispatch implements none of it — one replicated node per id is the game's job.
"""
import json

from conftest import edit_json
from dispatch.assembler import assemble_scene, build_context, export_package
from dispatch.spec import load_spec

INTER = [{
    "id": "cr_deli:if:4cd00b22", "kind": "window",
    "slot_ref": "ext_0_S_open1", "building": "cr_deli",
    "transform": {"translation": [3.0, 8.0, 1.1], "rot_y": 0},
    "states": ["intact", "broken"], "default": "intact",
    "transitions": [{"event": "break", "from": "intact", "to": "broken"}],
    "collision_per_state": {"intact": True, "broken": False},
}]


def test_interactives_ship_beside_the_anchors(world, tmp_path):
    edit_json(world / "build/lot/lot.gameplay.json",
              lambda d: d.update(interactives=INTER))
    spec = load_spec(world / "dispatch.mission.json")
    ctx = build_context(spec)
    scene = assemble_scene(ctx)
    paths = {scene.node_path(n) for n in scene.nodes}
    assert "Handoff/Interactives" in paths

    out = tmp_path / "pkg"
    manifest = export_package(ctx, scene, out)
    data = json.loads((out / "interactives.json").read_text(encoding="utf-8"))
    # verbatim: the whole state machine, untouched — id, transitions,
    # advisory hints and all. Dispatch ships, it never edits (TDD 2).
    assert data["interactives"] == INTER
    assert data["schema"] == "dispatch.interactives.v0.1"
    assert manifest["interactive_count"] == 1
    assert "interactives.json" in manifest["files"]
    # and the anchors file is still exactly what it was — siblings, not a merge
    assert (out / "gameplay_anchors.json").is_file()


def test_no_interactives_still_ships_the_empty_declaration(ctx, tmp_path):
    """The file's PRESENCE is the contract: empty means 'this level has
    none', absent would mean 'nobody asked' — the exact ambiguity item 46
    exists to kill."""
    scene = assemble_scene(ctx)
    out = tmp_path / "pkg"
    manifest = export_package(ctx, scene, out)
    data = json.loads((out / "interactives.json").read_text(encoding="utf-8"))
    assert data["interactives"] == []
    assert manifest["interactive_count"] == 0
    assert "interactives.json" in manifest["files"]


def test_deli_counter_carries_when_lot_is_absent(world, tmp_path):
    """Single-building missions: the shell's own declaration ships."""
    edit_json(world / "build" / "deli_counter" / "shell.gameplay.json",
              lambda d: d.update(interactives=INTER))
    spec = load_spec(world / "dispatch.mission.json")
    ctx = build_context(spec)
    # simulate a lot-less mission: drop the lot import after build
    ctx.imports.pop("lot", None)
    scene = assemble_scene(ctx)
    out = tmp_path / "pkg"
    manifest = export_package(ctx, scene, out)
    data = json.loads((out / "interactives.json").read_text(encoding="utf-8"))
    assert data["interactives"] == INTER
    assert manifest["interactive_count"] == 1
