import json

from dispatch.cli import main


def _out(world):
    return world / "export/godot/missions/gas_station_robbery_001"


def test_shell_handoff_default_has_no_runtime_code(world):
    assert main(["build", str(world / "dispatch.mission.json")]) == 0
    out = _out(world)
    assert not (out / "preview_only").exists()
    assert not (out / "adapters").exists()
    tscn = (out / "mission.tscn").read_text()
    for forbidden in ("Runtime", "MissionController", "AuthorityController",
                      "NetworkController", "ReplicationController"):
        assert f'name="{forbidden}"' not in tscn
    assert ".gd" not in tscn  # no scripts attached anywhere in handoff scenes
    manifest = json.loads((out / "mission_manifest.json").read_text())
    assert manifest["mode"] == "shell-handoff"


def test_preview_mode_isolated(world):
    assert main(["build", str(world / "dispatch.mission.json"),
                 "--mode", "preview-playtest"]) == 0
    out = _out(world)
    gd = (out / "preview_only/preview_mission_bridge.gd").read_text()
    assert gd.startswith("# DISPATCH PREVIEW ONLY\n# Not production gameplay or networking code.")
    assert "rpc" not in gd.lower()
    tscn = (out / "mission.tscn").read_text()
    assert 'name="PreviewOnly"' in tscn
    assert "preview_only/preview_mission_bridge.gd" in tscn
    # rebuilding in default mode removes the preview package again
    assert main(["build", str(world / "dispatch.mission.json")]) == 0
    assert not (out / "preview_only").exists()
    assert 'name="PreviewOnly"' not in (out / "mission.tscn").read_text()


def test_runtime_adapter_mode(world):
    assert main(["build", str(world / "dispatch.mission.json"),
                 "--mode", "runtime-adapter"]) == 0
    out = _out(world)
    for name in ("mission_events.gd", "anchor_adapter.gd", "adapter_registry.gd"):
        gd = (out / "adapters" / name).read_text()
        assert gd.startswith("# DISPATCH RUNTIME ADAPTER — interface only.")
        assert "@rpc" not in gd
    reg = json.loads((out / "gameplay_anchors.json").read_text())
    statuses = {a["anchor_type"]: a["integration_status"] for a in reg["anchors"]}
    assert statuses["door"] == "adapter_available"
    assert statuses["cover"] == "unimplemented"
    # Dispatch never emits game-pipeline statuses
    assert not any(a["integration_status"] in ("integrated", "verified_by_game_runtime")
                   for a in reg["anchors"])


def test_handoff_document(world):
    assert main(["build", str(world / "dispatch.mission.json")]) == 0
    text = (_out(world) / "HANDOFF.md").read_text()
    assert "does NOT validate" in text
    assert "runtime_binding` is intentionally null" in text
    assert "shipping online playability" in text
    assert "spawn (location) -> approach (objective)" in text
