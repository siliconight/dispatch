from dispatch.navgraph import NavGraph, NavNode, load_nav_hints, merge


def _g(source, nodes, links):
    return load_nav_hints({"nodes": nodes, "links": links, "up_axis": "y"}, source, "y")


def test_reachable_and_islands():
    g = _g("t", [{"id": "a", "pos": [0, 0, 0]}, {"id": "b", "pos": [1, 0, 0]},
                 {"id": "c", "pos": [50, 0, 0]}], [["a", "b"]])
    assert g.reachable("t:a", "t:b")
    assert not g.reachable("t:a", "t:c")
    islands = g.islands()
    assert len(islands) == 2
    assert islands[0] == ["t:a", "t:b"]  # largest first


def test_nearest():
    g = _g("t", [{"id": "a", "pos": [0, 0, 0]}], [])
    assert g.nearest((0.5, 0, 0), 1.0) == "t:a"
    assert g.nearest((5, 0, 0), 1.0) is None


def test_merge_bridges_cross_source_only():
    g1 = _g("dc", [{"id": "a", "pos": [0, 0, 0]}, {"id": "far", "pos": [0, 0, 30]}], [])
    g2 = _g("lot", [{"id": "b", "pos": [1, 0, 0]}], [])
    m = merge([g1, g2], bridge_radius=1.5)
    assert m.reachable("dc:a", "lot:b")
    assert m.bridges == [["dc:a", "lot:b"]]
    assert not m.reachable("dc:a", "dc:far")  # same-source nodes are not auto-bridged


def test_bounds():
    g = NavGraph()
    g.add_node(NavNode("a", (-2, 0, 3), "t"))
    g.add_node(NavNode("b", (5, 0, -1), "t"))
    assert g.bounds() == ((-2, -1), (5, 3))
