from dispatch.assembler import assemble_scene


def test_scene_hierarchy(ctx):
    scene = assemble_scene(ctx)
    paths = {scene.node_path(n) for n in scene.nodes}
    for expected in (
        ".", "World", "World/LotRoot", "World/BuildingRoot", "World/PropsRoot",
        "World/VisualsRoot", "World/LightingRoot", "World/FXRoot", "World/AudioRoot",
        "Gameplay/PlayerStarts", "Gameplay/AI/SpawnZones", "Gameplay/Navigation/NavMesh",
        "Runtime/MissionController", "Runtime/ReplicationRegistry", "Runtime/DebugOverlay",
        "Gameplay/PlayerStarts/player_start_01",
        "Gameplay/Objectives/cash_register",
        "Gameplay/ExtractionPoints/escape_vehicle",
        "World/VisualsRoot/StyledShell",
    ):
        assert expected in paths, expected


def test_coordinate_conversion(ctx):
    scene = assemble_scene(ctx)
    reg = next(n for n in scene.nodes if n.name == "cash_register")
    # blender (-4, 3.5, 0) -> godot (-4, 0, -3.5)
    assert reg.pos == (-4.0, 0.0, -3.5)


def test_anchor_metadata(ctx):
    scene = assemble_scene(ctx)
    loot = next(n for n in scene.nodes if n.name == "register_loot")
    assert loot.metadata["anchor_type"] == "loot"
    assert loot.metadata["authority"] == "server"
    assert loot.metadata["net_id"] >= 1000
    start = next(n for n in scene.nodes if n.name == "player_start_01")
    assert start.metadata["authority"] == "static"
    assert "net_id" not in start.metadata
