"""Gameplay events on anchors (0.6.0, the factory's roadmap 323).

An anchor may carry an event a game may ingest or ignore: its name, how it fires, how it repeats. Dispatch carries it
into the anchor registry and the anchor's node metadata, defaults the firing rule, and refuses a block a consumer
could not read the way it was meant. It runs nothing. FAILS ON 0.5.4, which drops every event.
"""
from types import SimpleNamespace

import pytest

from dispatch.anchors import EVENT_FIRES, EVENT_REPEAT, event_block, normalize_anchors
from dispatch.ownership import build_anchor_registry

SPEC = SimpleNamespace(mission_id="bank_block_001")


def _anchors(*records):
    return normalize_anchors(list(records), "deli_counter", up_axis="y")


def test_an_alarm_carries_its_event_with_the_firing_rule_defaulted():
    a, = _anchors({"id": "dc:teller", "type": "trigger", "pos": [0, 1, 0],
                   "event": {"event": "alarm.panic_button", "audible": False, "fixture": "teller_line"}})
    assert event_block(a) == {"event": "alarm.panic_button", "fires": "on_touch", "repeat": "edge",
                              "audible": False, "fixture": "teller_line"}


def test_a_zone_says_it_fires_once_on_entry():
    a, = _anchors({"id": "lot:van", "type": "trigger", "pos": [0, 0, 0],
                   "event": {"event": "zone.extraction", "fires": "on_enter", "repeat": "edge", "radius": 1.75}})
    ev = event_block(a)
    assert ev["fires"] == "on_enter" and ev["repeat"] == "edge" and "audible" not in ev
    assert ev["radius"] == 1.75


@pytest.mark.parametrize("radius", [None, 0, -1.0, "wide", float("nan"), float("inf")])
def test_a_zone_without_a_real_extent_is_refused(radius):
    """0.7.0: on_enter needs something to be entered. FAILS ON 0.6.0, which takes a zone with no size."""
    ev = {"event": "zone.extraction", "fires": "on_enter"}
    if radius is not None:
        ev["radius"] = radius
    a, = _anchors({"id": "lot:van", "type": "trigger", "pos": [0, 0, 0], "event": ev})
    with pytest.raises(ValueError):
        event_block(a)


def test_a_point_event_needs_no_radius_and_the_registry_carries_a_zones():
    point, zone = _anchors(
        {"id": "dc:atm", "type": "trigger", "pos": [0, 0, 0], "event": {"event": "alarm.atm_tampered"}},
        {"id": "lot:van", "type": "extraction", "pos": [5, 0, 0],
         "event": {"event": "zone.extraction", "fires": "on_enter", "radius": 1.75}})
    assert "radius" not in event_block(point)
    reg = {r["shell_id"].split("/")[-1]: r for r in build_anchor_registry(SPEC, [point, zone])["anchors"]}
    assert reg["lot:van"]["event"]["radius"] == 1.75


def test_the_registry_and_the_node_carry_it_and_an_anchor_without_one_has_none():
    with_ev, without = _anchors(
        {"id": "dc:vault", "type": "trigger", "pos": [0, 0, 0], "event": {"event": "alarm.vault_door", "audible": True}},
        {"id": "dc:loot", "type": "loot", "pos": [1, 0, 0]})
    reg = {r["shell_id"].split("/")[-1]: r for r in build_anchor_registry(SPEC, [with_ev, without])["anchors"]}
    assert reg["dc:vault"]["event"]["event"] == "alarm.vault_door" and reg["dc:vault"]["event"]["audible"] is True
    assert "event" not in reg["dc:loot"]


@pytest.mark.parametrize("block", [{"event": "police.arrive"}, {"event": "alarm.x", "fires": "every_frame"},
                                   {"event": "zone.x", "repeat": "always", "radius": 2.0}])
def test_a_block_a_consumer_could_not_read_is_refused(block):
    a, = _anchors({"id": "dc:bad", "type": "trigger", "pos": [0, 0, 0], "event": block})
    with pytest.raises(ValueError):
        event_block(a)


def test_the_vocabulary_holds_no_behaviour():
    """Edge and once are how often an event is SENT; nothing here says what a game does with it."""
    assert EVENT_FIRES == ("on_touch", "on_enter", "on_exit") and EVENT_REPEAT == ("edge", "once")


def test_a_drill_zone_fires_on_entry_and_exit_and_names_its_door():
    """0.8.0: a drill zone is sent as a body enters and as it leaves, so a game times the hold; it names the
    interactive it acts on. FAILS ON 0.7.0, which takes one rule and drops the target."""
    a, = _anchors({"id": "dc:drill", "type": "trigger", "pos": [0, 0, 0],
                   "event": {"event": "zone.drill", "fires": ["on_exit", "on_enter"], "radius": 1.0,
                             "target": "bank_branch_a02:if:5f1e", "fixture": "vault_door"}})
    ev = event_block(a)
    assert ev["fires"] == ["on_enter", "on_exit"] and ev["target"] == "bank_branch_a02:if:5f1e"
    reg = {r["shell_id"].split("/")[-1]: r for r in build_anchor_registry(SPEC, [a])["anchors"]}
    assert reg["dc:drill"]["event"]["fires"] == ["on_enter", "on_exit"]


@pytest.mark.parametrize("fires", [[], ["on_enter", "on_enter"], ["on_enter", "while_inside"], 3])
def test_a_firing_list_a_consumer_could_not_read_is_refused(fires):
    a, = _anchors({"id": "dc:bad", "type": "trigger", "pos": [0, 0, 0],
                   "event": {"event": "zone.drill", "fires": fires, "radius": 1.0}})
    with pytest.raises(ValueError):
        event_block(a)


def test_one_rule_is_still_a_string():
    a, = _anchors({"id": "lot:van", "type": "extraction", "pos": [0, 0, 0],
                   "event": {"event": "zone.extraction", "fires": ["on_enter"], "radius": 1.75}})
    assert event_block(a)["fires"] == "on_enter"
