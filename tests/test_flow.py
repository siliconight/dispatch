from dispatch.anchors import normalize_anchors
from dispatch.flow import compile_flow


ANCHORS = normalize_anchors([
    {"id": "start_1", "type": "player_start", "pos": [0, 0, 0], "tags": ["street_start"]},
    {"id": "reg", "type": "objective", "pos": [0, 0, 0], "objective": "open_register"},
    {"id": "exit", "type": "extraction", "pos": [0, 0, 0], "objective": "reach_exit"},
], "dc")


def test_binding_by_tag_and_objective():
    flow = compile_flow([
        {"step": "spawn", "location_tag": "street_start"},
        {"step": "loot", "objective": "open_register"},
        {"step": "escape", "objective": "reach_exit"},
    ], ANCHORS)
    assert flow.steps[0].anchor_ids == ("start_1",)
    assert flow.steps[1].anchor_ids == ("reg",)
    assert flow.steps[2].anchor_ids == ("exit",)
    assert flow.unbound == []
    assert flow.states == ["PRE_MISSION", "SPAWN", "LOOT", "ESCAPE", "COMPLETE"]


def test_trigger_step_needs_no_anchor():
    flow = compile_flow([{"step": "go_hot", "trigger": "alarm"}], ANCHORS)
    assert flow.unbound == []


def test_unbound_step_detected():
    flow = compile_flow([{"step": "mystery", "objective": "nothing_matches"}], ANCHORS)
    assert flow.unbound == ["mystery"]
