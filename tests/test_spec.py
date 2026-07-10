import pytest

from dispatch import DispatchError
from dispatch.spec import load_spec, validate_spec
from conftest import edit_json


def test_load_example_spec(world):
    s = load_spec(world / "dispatch.mission.json")
    assert s.mission_id == "gas_station_robbery_001"
    assert s.players_max == 4
    assert s.net_model == "server_authoritative"
    assert s.tuning["anchor_nav_radius"] == 3.0  # defaults merged


def test_missing_file():
    with pytest.raises(DispatchError, match="not found"):
        load_spec("/nonexistent/dispatch.mission.json")


def test_bad_schema(world):
    p = world / "dispatch.mission.json"
    edit_json(p, lambda d: d.update(schema="dispatch.mission.v9"))
    with pytest.raises(DispatchError, match="unsupported mission schema"):
        load_spec(p)


def test_bad_players(world):
    p = world / "dispatch.mission.json"
    edit_json(p, lambda d: d["players"].update(max=6))
    with pytest.raises(DispatchError, match="player counts"):
        load_spec(p)


def test_required_inputs(world):
    p = world / "dispatch.mission.json"
    edit_json(p, lambda d: d["inputs"].pop("lot"))
    with pytest.raises(DispatchError, match="required inputs missing"):
        load_spec(p)


def test_duplicate_flow_step(world):
    p = world / "dispatch.mission.json"
    edit_json(p, lambda d: d["mission_flow"].append({"step": "loot", "objective": "x"}))
    with pytest.raises(DispatchError, match="more than once"):
        load_spec(p)


def test_empty_flow(world):
    p = world / "dispatch.mission.json"
    edit_json(p, lambda d: d.update(mission_flow=[]))
    with pytest.raises(DispatchError, match="mission_flow"):
        load_spec(p)
