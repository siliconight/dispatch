"""A ladder's off-mesh link reaches the package, in the nodes' frame.

THE WALKER, 2026-09-23: does the pipeline have navmesh off-mesh links? It does
-- `deli_counter.ladder._nav_link` emits one per ladder with a per-type cost, a
required capability, an access state and a multiplayer reservation state -- and
until this it stopped at the shell's `gameplay.json`. Measured on
`walk_export_club_block_009`, which HAS ladders: 0 files in the shipped package
carried a nav_link, and 0 of its 35 interactives were ladder-related. The climb
MARKER shipped, so a player could climb and an AI had no edge to path along.

Run: python -m pytest tests/test_offmesh_links.py -q
"""
from dispatch.navgraph import NavGraph, merge

#: The real link off `deli_a03`'s `night_deli_ladder_0`, verbatim.
LINK = {
    "id": "night_deli_ladder_0_navlink",
    "start_position": [8.0, -12.0, 0.0],
    "end_position": [8.0, -12.0, 6.6],
    "bidirectional": True,
    "cost": 3.0,
    "agent_types": ["player", "ai_humanoid"],
    "required_capability": "climb",
    "access_state": "open",
    "reservation_state": "free",
}


def test_the_link_is_converted_into_the_nodes_frame():
    """Blender Z-up -> Godot Y-up is (x, y, z) -> (x, z, -y). The ladder climbs
    in Z, so after conversion it must climb in Y -- if this came through
    unconverted the link would run horizontally and a planner would path a body
    sideways through a wall."""
    g = NavGraph()
    g.add_off_mesh_link(LINK, "deli_counter", "z")
    got = g.links[0]
    assert got["start_position"] == [8.0, 0.0, 12.0], got["start_position"]
    assert got["end_position"] == [8.0, 6.6, 12.0], got["end_position"]
    # it CLIMBS: the only axis that moved is Y
    assert got["end_position"][1] - got["start_position"][1] == 6.6


def test_the_id_is_namespaced_like_a_node_id():
    """Two tools may both ship a `ladder_0`. Node ids are namespaced for that
    reason and a link's must be too, or a merge silently collides."""
    g = NavGraph()
    g.add_off_mesh_link(LINK, "deli_counter", "z")
    assert g.links[0]["id"] == "deli_counter:night_deli_ladder_0_navlink"
    assert g.links[0]["source"] == "deli_counter"


def test_the_payload_survives_verbatim():
    """Cost, capability, access and reservation are what a consumer cannot
    re-derive from a marker position. If this pass dropped them it would be
    shipping a worse link than the one it was given."""
    g = NavGraph()
    g.add_off_mesh_link(LINK, "deli_counter", "z")
    got = g.links[0]
    for k in ("bidirectional", "cost", "agent_types", "required_capability",
              "access_state", "reservation_state"):
        assert got[k] == LINK[k], (k, got[k], LINK[k])


def test_links_survive_a_merge_and_reach_to_json():
    a, b = NavGraph(), NavGraph()
    a.add_off_mesh_link(LINK, "deli_counter", "z")
    b.add_off_mesh_link(dict(LINK, id="lot_ladder"), "lot", "z")
    out = merge([a, b], bridge_radius=1.5).to_json()
    assert out["schema"] == "dispatch.navigation_hints.v0.3"
    ids = [l["id"] for l in out["links"]]
    assert ids == sorted(ids), ids
    assert "deli_counter:night_deli_ladder_0_navlink" in ids
    assert "lot:lot_ladder" in ids


def test_a_graph_with_no_ladder_ships_an_empty_list_not_a_missing_key():
    """A consumer branching on the key's presence must not have to guess. An
    absent list and an empty one are different claims."""
    out = NavGraph().to_json()
    assert out["links"] == []


# ---------------------------------------------------------------------------
# the seam, which is what cold run 9075 caught and the unit tests above did not
# ---------------------------------------------------------------------------
LADDER_ON_SITE = {
    "id": "mh01_ladder_0", "building": "b0",
    "role": "roof_access", "ladder_type": "fixed_vertical",
    "lower_anchor": [91.4, 70.0, 0.0], "upper_anchor": [91.4, 70.0, 6.5],
    # the id comes from the LINK, not from the ladder -- the first draft of
    # this test overrode the positions and not the id, and failed asserting an
    # id nothing had ever produced
    "nav_link": dict(LINK, id="mh01_ladder_0_navlink",
                     start_position=[91.4, 70.0, 0.0],
                     end_position=[91.4, 70.0, 6.5]),
}


def test_a_site_ladder_reaches_navigation_hints(world, tmp_path):
    """COLD RUN 9075. Dispatch 0.5.0 taught the DELI COUNTER importer to carry
    these. A site mission runs the LOT importer, whose manifest is
    `lot.gameplay.json`, so the package shipped 23 gb_ladder surfaces and
    `links: []`. Both sides' unit tests passed; nothing tested the seam.

    FAILS BEFORE THE LOT IMPORTER CARRIES LADDERS."""
    import json as _json
    from conftest import edit_json
    from dispatch.assembler import assemble_scene, build_context, export_package
    from dispatch.spec import load_spec

    edit_json(world / "build/lot/lot.gameplay.json",
              lambda d: d.update(ladders=[LADDER_ON_SITE]))
    spec = load_spec(world / "dispatch.mission.json")
    ctx = build_context(spec)
    scene = assemble_scene(ctx)
    out = tmp_path / "pkg"
    export_package(ctx, scene, out)
    nav = _json.loads((out / "navigation_hints.json").read_text(encoding="utf-8"))
    assert nav["schema"] == "dispatch.navigation_hints.v0.3"
    ids = [l["id"] for l in nav["links"]]
    assert "lot:mh01_ladder_0_navlink" in ids, ids
    link = [l for l in nav["links"] if l["id"].endswith("mh01_ladder_0_navlink")][0]
    # the cost and capability are the point -- a bare pair of endpoints is
    # something a consumer could have derived from the marker themselves
    assert link["required_capability"] == "climb"
    assert link["cost"] == 3.0


def test_a_site_with_no_ladders_still_ships_the_key(world, tmp_path):
    """An absent list and an empty one are different claims, and a package with
    no ladders is exactly the case that made the first measurement of this
    prove nothing."""
    import json as _json
    from dispatch.assembler import assemble_scene, build_context, export_package
    from dispatch.spec import load_spec

    spec = load_spec(world / "dispatch.mission.json")
    ctx = build_context(spec)
    out = tmp_path / "pkg"
    export_package(ctx, assemble_scene(ctx), out)
    nav = _json.loads((out / "navigation_hints.json").read_text(encoding="utf-8"))
    assert nav["links"] == []
