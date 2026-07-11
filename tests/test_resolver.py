import json

import pytest

from dispatch import DispatchError
from dispatch.resolver import resolve_inputs, write_lock_file


def test_resolve_all_tools(spec):
    r = resolve_inputs(spec)
    assert set(r.tools) == {"deli_counter", "lot", "zoo", "patina", "lux"}
    assert r.tools["deli_counter"].schema == "dc.gameplay.v1"


def test_missing_required_file(world, spec):
    (world / "build/lot/lot.nav_hints.json").unlink()
    with pytest.raises(DispatchError, match="lot.nav_hints.json is missing"):
        resolve_inputs(spec)


def test_optional_tool_skipped(world, spec):
    (world / "build/lux/lux.profile.json").unlink()
    r = resolve_inputs(spec)
    assert "lux" not in r.tools
    assert any("lux" in w for w in r.warnings)


def test_lock_file(spec, tmp_path):
    r = resolve_inputs(spec)
    (tmp_path / "mission.tscn").write_text("[gd_scene format=3]\n")
    p = write_lock_file(spec, r, tmp_path, mode="shell-handoff")
    lock = json.loads(p.read_text())
    assert lock["schema"] == "dispatch.build_lock.v0.2"
    assert lock["contract"] == "dispatch.mission.v0.2"
    assert lock["mode"] == "shell-handoff"
    assert lock["spec_sha256"]
    assert lock["created_at"]
    roles = {i["role"] for i in lock["inputs"]}
    assert "mission_spec" in roles and "deli_counter:shell.glb" in roles
    assert all(i["sha256"] for i in lock["inputs"])
    outs = {o["path"] for o in lock["outputs"]}
    assert "mission.tscn" in outs and "build.lock.json" not in outs
