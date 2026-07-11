from dispatch.anchors import (blender_to_godot, find_duplicate_ids,
                              normalize_anchors, runtime_requirements_for)


def test_blender_to_godot():
    assert blender_to_godot((1, 2, 3)) == (1, 3, -2)


def test_normalize_converts():
    a = normalize_anchors([{"id": "x", "type": "cover", "pos": [1, 2, 0]}], "dc")[0]
    assert a.pos == (1, 0, -2)
    assert a.source == "dc"


def test_normalize_y_up_passthrough():
    a = normalize_anchors([{"id": "x", "type": "cover", "pos": [1, 2, 3]}], "dc", up_axis="y")[0]
    assert a.pos == (1, 2, 3)


def test_shell_id_and_adapter():
    a = normalize_anchors([{"id": "vault_door_01", "type": "door", "pos": [0, 0, 0]}], "dc")[0]
    assert a.shell_id == "vault_door_01"
    assert a.expected_adapter == "openable_door"
    assert a.integration_status == "unimplemented"


def test_runtime_requirements_declarations():
    recs = normalize_anchors([
        {"id": "d", "type": "door", "pos": [0, 0, 0]},
        {"id": "o", "type": "objective", "pos": [0, 0, 0]},
        {"id": "s", "type": "player_start", "pos": [0, 0, 0]},
    ], "dc")
    door, obj, start = recs
    assert runtime_requirements_for(door)["replication_required"] is True
    assert runtime_requirements_for(door)["mission_persistence_required"] is False
    assert runtime_requirements_for(obj)["mission_persistence_required"] is True
    assert runtime_requirements_for(start) == {}


def test_duplicates():
    recs = [{"id": "x", "type": "cover", "pos": [0, 0, 0]}] * 2
    assert find_duplicate_ids(normalize_anchors(recs, "dc")) == ["x"]
