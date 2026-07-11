from dispatch.anchors import normalize_anchors
from dispatch.flow import compile_beats


ANCHORS = normalize_anchors([
    {"id": "start_1", "type": "player_start", "pos": [0, 0, 0], "tags": ["street_start"]},
    {"id": "reg", "type": "objective", "pos": [0, 0, 0], "objective": "open_register"},
    {"id": "exit", "type": "extraction", "pos": [0, 0, 0], "objective": "reach_exit"},
], "dc")


def test_binding_and_types():
    g = compile_beats([
        {"step": "spawn", "location_tag": "street_start"},
        {"step": "loot", "objective": "open_register"},
        {"step": "escape", "objective": "reach_exit"},
    ], ANCHORS, "m1")
    assert g.graph_id == "m1"
    assert [b.anchor_ids for b in g.beats] == [("start_1",), ("reg",), ("exit",)]
    assert [b.type for b in g.beats] == ["location", "objective", "extraction"]
    assert g.connections == [["spawn", "loot"], ["loot", "escape"]]
    assert g.unbound == []


def test_trigger_beat_needs_no_anchor():
    g = compile_beats([{"step": "go_hot", "trigger": "alarm"}], ANCHORS, "m1")
    assert g.unbound == []
    assert g.beats[0].type == "trigger"


def test_unbound_beat_detected():
    g = compile_beats([{"step": "mystery", "objective": "nothing_matches"}], ANCHORS, "m1")
    assert g.unbound == ["mystery"]


def test_explicit_type_wins():
    g = compile_beats([{"step": "haul", "objective": "open_register", "type": "carry"}], ANCHORS, "m1")
    assert g.beats[0].type == "carry"


def test_graph_json_shape():
    g = compile_beats([{"step": "loot", "objective": "open_register"}], ANCHORS, "m1")
    j = g.to_json()
    assert j["schema"] == "dispatch.proposed_beat_graph.v0.2"
    assert j["beats"][0]["id"] == "loot"
    assert j["beats"][0]["status"] == "proposed"
    assert j["beats"][0]["shell_ids"] == ["m1/reg"]  # namespaced (delta D4)
    assert "runtime owns" in j["statement"]
