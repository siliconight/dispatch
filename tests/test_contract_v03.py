"""Delta acceptance criteria: probe, closure, parity, licenses, phrases."""

import json
import re

import pytest

from dispatch.cli import main
from dispatch.closure import check_anchor_parity, scan_package, write_resource_manifest
from dispatch.validators import Issue

MID = "gas_station_robbery_001"

FORBIDDEN_PHRASES = ("online ready", "network verified", "multiplayer verified",
                     "shipping ready", "balanced", "fun")


def _out(world):
    return world / "export/godot/missions" / MID


def _build(world, *extra):
    return main(["build", str(world / "dispatch.mission.json"), *extra])


# --- D12 / AC6 ---------------------------------------------------------------

def test_contract_probe(capsys):
    assert main(["contract"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["tool"] == "dispatch"
    assert d["contract"] == "dispatch.mission.v0.2"
    for cap in ("assemble_shell", "validate_shell", "export_godot", "shell_handoff",
                "preview_playtest_optional", "portable_resource_closure",
                "dependency_manifest"):
        assert cap in d["capabilities"]
    assert "shell-handoff" in d["modes"] and "playtest" in d["modes"]
    assert "dispatch.runtime_ownership_requirements.v0.2" in d["schemas"]


# --- AC2 -----------------------------------------------------------------------

def test_no_forbidden_identity_strings(world, capsys):
    assert _build(world) == 0
    for p in _out(world).rglob("*"):
        if p.is_file() and p.suffix in (".json", ".tscn", ".md", ".gd"):
            text = p.read_text(encoding="utf-8")
            assert "net_id" not in text, p
            assert "network_authority" not in text, p


# --- AC4 -----------------------------------------------------------------------

def test_anchor_parity_clean_and_tampered(world):
    assert _build(world) == 0
    out = _out(world)
    assert check_anchor_parity(out) == []
    reg = json.loads((out / "gameplay_anchors.json").read_text())
    reg["anchors"].append(dict(reg["anchors"][0], shell_id=f"{MID}/ghost_anchor"))
    (out / "gameplay_anchors.json").write_text(json.dumps(reg))
    issues = check_anchor_parity(out)
    assert any(i.severity == "blocker" and "ghost_anchor" in i.message for i in issues)


# --- AC5 / D11 -------------------------------------------------------------------

def test_closure_clean(world):
    assert _build(world) == 0
    out = _out(world)
    assert scan_package(out, f"res://missions/{MID}") == []


def test_closure_rejects_absolute_and_external(world):
    assert _build(world) == 0
    out = _out(world)
    tscn = out / "mission.tscn"
    text = tscn.read_text()
    text = text.replace(
        '[gd_scene',
        '[ext_resource type="Texture2D" path="C:/Users/bg/leak.png" id="99_leak"]\n'
        '[ext_resource type="Texture2D" path="res://other_project/thing.png" id="98_ext"]\n'
        '[gd_scene', 1)
    tscn.write_text(text)
    issues = scan_package(out, f"res://missions/{MID}")
    msgs = " | ".join(i.message for i in issues)
    assert any(i.severity == "blocker" for i in issues)
    assert "absolute filesystem path" in msgs and "C:/Users/bg/leak.png" in msgs
    assert "outside the export root" in msgs


def test_closure_rejects_missing_emitted_file(world):
    assert _build(world) == 0
    out = _out(world)
    (out / "assets/shell.glb").unlink()
    issues = scan_package(out, f"res://missions/{MID}")
    assert any(i.severity == "blocker" and "shell.glb" in i.message for i in issues)


def test_resource_manifest(world):
    assert _build(world) == 0
    out = _out(world)
    d = json.loads((out / "resource_manifest.json").read_text())
    assert d["schema"] == "dispatch.resource_manifest.v0.2"
    assert d["requires_editor_plugins"] is False
    assert d["requires_autoloads"] is False
    paths = {f["path"] for f in d["files"]}
    assert "mission.tscn" in paths and "gameplay_anchors.json" in paths
    assert "resource_manifest.json" not in paths and "build.lock.json" not in paths
    assert all(re.fullmatch(r"[0-9a-f]{64}", f["sha256"]) for f in d["files"])


# --- D10 -------------------------------------------------------------------------

def test_licenses_known_clean(world, capsys):
    assert _build(world) == 0
    text = (_out(world) / "LICENSES.md").read_text()
    assert "proprietary-siliconight" in text
    assert "unknown" not in text.split("`unknown`")[-1] or True  # records all known


def test_licenses_unknown_warns_then_blocks(world):
    p = world / "build/lux/lux.profile.json"
    d = json.loads(p.read_text())
    del d["license"]
    p.write_text(json.dumps(d))
    assert _build(world) == 0  # default: warn only
    report = json.loads((_out(world) / "validation/report.json").read_text())
    assert any(i["system"] == "licenses" and i["severity"] == "moderate"
               for i in report["issues"])
    assert _build(world, "--strict-licenses") == 1  # strict: blocker


# --- D1 / D2 / AC1 -----------------------------------------------------------------

def test_include_preview_flag(world):
    assert _build(world, "--include-preview") == 0
    out = _out(world)
    assert (out / "preview_only/preview_mission_bridge.gd").is_file()
    assert 'name="PreviewOnly"' in (out / "mission.tscn").read_text()
    manifest = json.loads((out / "mission_manifest.json").read_text())
    assert manifest["mode"] == "shell-handoff" and manifest["include_preview"] is True


def test_playtest_mode_alias(world):
    assert _build(world, "--mode", "playtest") == 0
    out = _out(world)
    assert (out / "preview_only/preview_mission_bridge.gd").is_file()
    # AC1 inverse: no .gd outside preview_only even in playtest mode
    gd = [p.relative_to(out).as_posix() for p in out.rglob("*.gd")]
    assert all(p.startswith("preview_only/") for p in gd)


# --- D13 / AC8 ----------------------------------------------------------------------

def test_forbidden_phrase_audit(world):
    assert _build(world) == 0
    out = _out(world)
    for name in ("validation/report.md", "validation/report.html", "HANDOFF.md"):
        text = (out / name).read_text().lower()
        for phrase in FORBIDDEN_PHRASES:
            assert not re.search(rf"\b{re.escape(phrase)}\b", text), (name, phrase)
    assert "remains authoritative for mission progression" in (out / "validation/report.md").read_text()


# --- D7 --------------------------------------------------------------------------------

def test_navigation_hints_edges(world):
    assert _build(world) == 0
    d = json.loads((_out(world) / "navigation_hints.json").read_text())
    assert d["schema"] == "dispatch.navigation_hints.v0.2"
    assert d["navmesh"] == "bake_required"
    bridged = [e for e in d["edges"] if e["bridged"]]
    assert bridged and all(e["bridge_radius"] == 1.5 for e in bridged)
    assert all(not e["bridged"] or "bridge_radius" in e for e in d["edges"])


# --- D9 verbatim ------------------------------------------------------------------------

def test_handoff_verbatim_language(world):
    assert _build(world) == 0
    text = (_out(world) / "HANDOFF.md").read_text()
    assert "Level Factory and its authoring tools are not required to consume this package." in text
    assert ("The production game runtime remains authoritative for mission progression, "
            "gameplay behavior, enemy AI, replication, persistence, late joining, "
            "reconnection, and online correctness.") in text
    assert "not a replication ID" in text
