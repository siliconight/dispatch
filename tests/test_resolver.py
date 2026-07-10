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
    p = write_lock_file(spec, r, tmp_path)
    lock = json.loads(p.read_text())
    dc = lock["inputs"]["deli_counter"]["files"]
    assert dc["shell.glb"]["sha256"]
    assert dc["shell.glb"]["bytes"] > 0
