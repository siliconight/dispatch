from dispatch.score import compute
from dispatch.validators import Issue


def test_clean_is_100():
    s = compute([Issue("info", "assembly", "ok")])
    assert s["mission_readiness"] == 100
    assert s["status"] == "ready_for_review"


def test_blocker_caps_below_playtest():
    s = compute([Issue("blocker", "assembly", "boom")])
    assert s["mission_readiness"] <= 59
    assert s["status"] in ("prototype_only", "broken")


def test_majors_degrade():
    issues = [Issue("major", "online_runtime", "x"),
              Issue("major", "objective_reachability", "y")]
    s = compute(issues)
    assert s["scores"]["online_runtime"] == 75
    assert s["scores"]["objective_flow"] == 75
    assert s["status"] == "ready_for_playtest"


def test_category_floor_zero():
    issues = [Issue("blocker", "assembly", "x")] * 3
    s = compute(issues)
    assert s["scores"]["assembly"] == 0
