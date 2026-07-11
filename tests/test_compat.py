import json

from dispatch.assembler import build_context
from dispatch.spec import load_spec
from dispatch.validators import run_all


def test_v01_schema_still_reads(world):
    p = world / "dispatch.mission.json"
    d = json.loads(p.read_text())
    d["schema"] = "dispatch.mission.v0.1"
    p.write_text(json.dumps(d))
    spec = load_spec(p)
    assert spec.legacy_schema is True
    ctx = build_context(spec)
    issues = run_all(ctx)
    assert not any(i.severity == "blocker" for i in issues)
    assert any("v0.1" in i.message and i.severity == "info" for i in issues)
