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
                   "event": {"event": "zone.extraction", "fires": "on_enter", "repeat": "edge"}})
    ev = event_block(a)
    assert ev["fires"] == "on_enter" and ev["repeat"] == "edge" and "audible" not in ev


def test_the_registry_and_the_node_carry_it_and_an_anchor_without_one_has_none():
    with_ev, without = _anchors(
        {"id": "dc:vault", "type": "trigger", "pos": [0, 0, 0], "event": {"event": "alarm.vault_door", "audible": True}},
        {"id": "dc:loot", "type": "loot", "pos": [1, 0, 0]})
    reg = {r["shell_id"].split("/")[-1]: r for r in build_anchor_registry(SPEC, [with_ev, without])["anchors"]}
    assert reg["dc:vault"]["event"]["event"] == "alarm.vault_door" and reg["dc:vault"]["event"]["audible"] is True
    assert "event" not in reg["dc:loot"]


@pytest.mark.parametrize("block", [{"event": "police.arrive"}, {"event": "alarm.x", "fires": "every_frame"},
                                   {"event": "zone.x", "repeat": "always"}])
def test_a_block_a_consumer_could_not_read_is_refused(block):
    a, = _anchors({"id": "dc:bad", "type": "trigger", "pos": [0, 0, 0], "event": block})
    with pytest.raises(ValueError):
        event_block(a)


def test_the_vocabulary_holds_no_behaviour():
    """Edge and once are how often an event is SENT; nothing here says what a game does with it."""
    assert EVENT_FIRES == ("on_touch", "on_enter", "on_exit") and EVENT_REPEAT == ("edge", "once")
