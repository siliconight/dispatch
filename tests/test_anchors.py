from dispatch.anchors import (assign_net_ids, blender_to_godot,
                              find_duplicate_ids, normalize_anchors)


def test_blender_to_godot():
    assert blender_to_godot((1, 2, 3)) == (1, 3, -2)


def test_normalize_converts():
    a = normalize_anchors([{"id": "x", "type": "cover", "pos": [1, 2, 0]}], "dc")[0]
    assert a.pos == (1, 0, -2)
    assert a.source == "dc"


def test_normalize_y_up_passthrough():
    a = normalize_anchors([{"id": "x", "type": "cover", "pos": [1, 2, 3]}], "dc", up_axis="y")[0]
    assert a.pos == (1, 2, 3)


def test_net_ids_stable_and_server_only():
    recs = [
        {"id": "b_obj", "type": "objective", "pos": [0, 0, 0]},
        {"id": "a_obj", "type": "objective", "pos": [0, 0, 0]},
        {"id": "spawn", "type": "player_start", "pos": [0, 0, 0]},
    ]
    a1 = normalize_anchors(recs, "dc")
    a2 = normalize_anchors(list(reversed(recs)), "dc")
    assign_net_ids(a1)
    assign_net_ids(a2)
    ids1 = {a.id: a.net_id for a in a1}
    ids2 = {a.id: a.net_id for a in a2}
    assert ids1 == ids2                      # input order does not matter
    assert ids1["a_obj"] == 1000
    assert ids1["b_obj"] == 1001
    assert ids1["spawn"] == 0                # not replicated


def test_duplicates():
    recs = [{"id": "x", "type": "cover", "pos": [0, 0, 0]}] * 2
    assert find_duplicate_ids(normalize_anchors(recs, "dc")) == ["x"]
