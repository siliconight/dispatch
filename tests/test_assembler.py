from dispatch.assembler import assemble_scene, build_context
from dispatch.ownership import FORBIDDEN_NODE_NAMES


def test_scene_hierarchy(ctx):
    scene = assemble_scene(ctx)
    paths = {scene.node_path(n) for n in scene.nodes}
    for expected in (
        ".", "Functional", "Functional/Geometry", "Functional/Collision",
        "Functional/GameplayAnchors", "Functional/NavigationHints",
        "Functional/Geometry/Shell", "Functional/Geometry/LotSite",
        "Functional/NavigationHints/NavMesh",
        "Presentation/Props", "Presentation/Materials", "Presentation/Decals",
        "Presentation/Lighting", "Presentation/Atmosphere",
        "Presentation/Materials/StyledShell",
        "Handoff/OwnershipRequirements", "Handoff/ProposedBeatGraph",
        "Handoff/ValidationMetadata",
        "Functional/GameplayAnchors/PlayerStarts/player_start_01",
        "Functional/GameplayAnchors/Objectives/cash_register",
        "Functional/GameplayAnchors/ExtractionPoints/escape_vehicle",
    ):
        assert expected in paths, expected


def test_no_forbidden_runtime_nodes(ctx):
    scene = assemble_scene(ctx)
    names = {n.name for n in scene.nodes}
    assert not names.intersection(FORBIDDEN_NODE_NAMES)
    assert "PreviewOnly" not in names  # shell-handoff carries no preview


def test_coordinate_conversion(ctx):
    scene = assemble_scene(ctx)
    reg = next(n for n in scene.nodes if n.name == "cash_register")
    # blender (-4, 3.5, 0) -> godot (-4, 0, -3.5)
    assert reg.pos == (-4.0, 0.0, -3.5)


def test_anchor_metadata(ctx):
    scene = assemble_scene(ctx)
    loot = next(n for n in scene.nodes if n.name == "register_loot")
    assert loot.metadata["shell_id"] == "gas_station_robbery_001/register_loot"
    assert loot.metadata["anchor_type"] == "loot"
    assert loot.metadata["integration_status"] == "unimplemented"
    assert loot.metadata["expected_adapter"] == "lootable"
    assert loot.metadata["required_authority"] == "server"
    assert "net_id" not in loot.metadata
    assert "authority" not in loot.metadata  # required_authority is the v0.2+ key
    cover = next(n for n in scene.nodes if n.name == "pump_cover_a")
    assert cover.metadata["required_authority"] == "none"


def test_props_are_presentation(ctx):
    scene = assemble_scene(ctx)
    prop = next(n for n in scene.nodes if n.name == "dumpster_01_01")
    assert prop.parent == "Presentation/Props"
    assert prop.metadata["layer"] == "presentation"


def test_preview_mode_adds_bridge(spec):
    ctx = build_context(spec, mode="preview-playtest")
    scene = assemble_scene(ctx)
    paths = {scene.node_path(n) for n in scene.nodes}
    assert "PreviewOnly/PreviewMissionBridge" in paths
    bridge = next(n for n in scene.nodes if n.name == "PreviewMissionBridge")
    assert bridge.props["beat_graph_path"].endswith("proposed_beat_graph.json")
