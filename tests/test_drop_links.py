"""A declared drop's off-mesh link reaches the package, from both importers (0.5.3, factory roadmap 173).

Run: python -m pytest tests/test_drop_links.py -q
"""
import json
from types import SimpleNamespace

from dispatch.importers import deli_counter as dc_imp
from dispatch.importers import lot as lot_imp
from dispatch.navgraph import NavGraph

#: The link Deli Counter 0.226.0 files on deli_a01's floor hole, verbatim (building frame, z up).
DROP = {
    "id": "deli_a01_floor_hole_1_8_-4_navlink",
    "start_position": [8.0, -4.0, 3.3],
    "end_position": [8.0, -4.0, 0.0],
    "bidirectional": False,
    "cost": 4.0,
    "agent_types": ["player", "ai_humanoid"],
    "required_capability": "drop",
    "access_state": "open",
    "reservation_state": "free",
    "hole": [[7.25, -4.75], [8.75, -3.25]],
}


def test_the_payload_survives_verbatim_and_is_one_way():
    g = NavGraph()
    g.add_off_mesh_link(dict(DROP), "deli_counter", "z")
    got = g.links[0]
    assert got["id"] == "deli_counter:deli_a01_floor_hole_1_8_-4_navlink"
    assert got["bidirectional"] is False and got["required_capability"] == "drop"
    assert got["hole"] == DROP["hole"]
    assert got["start_position"][1] - got["end_position"][1] == 3.3     # z up became y up: the fall is 3.3 m


def _files(tmp_path, prefix, gp, extra):
    (tmp_path / f"{prefix}.gameplay.json").write_text(json.dumps(gp), encoding="utf-8")
    (tmp_path / f"{prefix}.nav_hints.json").write_text(json.dumps({"up_axis": "z", "nodes": [], "links": []}), encoding="utf-8")
    (tmp_path / f"{prefix}.glb").write_bytes(b"")
    files = {f"{prefix}.gameplay.json": tmp_path / f"{prefix}.gameplay.json",
             f"{prefix}.nav_hints.json": tmp_path / f"{prefix}.nav_hints.json",
             f"{prefix}.glb": tmp_path / f"{prefix}.glb"}
    files.update(extra)
    return files


def test_the_deli_counter_importer_reads_a_drop(tmp_path):
    gp = {"up_axis": "z", "anchors": [], "props": [], "ladders": [],
          "vertical_links": [{"kind": "stair"}, {"kind": "floor_hole", "story": 1, "x": 8.0, "y": -4.0, "nav_link": dict(DROP)}]}
    rt = SimpleNamespace(files=_files(tmp_path, "shell", gp, {}), manifest=gp, schema="deli_counter.gameplay.v1")
    imp = dc_imp.load(rt)
    ids = [l["id"] for l in imp.nav.links]
    assert ids == ["deli_counter:deli_a01_floor_hole_1_8_-4_navlink"], ids


def test_the_lot_importer_reads_a_drop(tmp_path):
    gp = {"up_axis": "z", "anchors": [], "props": [], "interactives": [], "ladders": [],
          "vertical_links": [{"kind": "hatch", "story": 1, "x": -12.0, "y": 8.0, "building": "deli_a01",
                              "nav_link": dict(DROP, id="deli_a01_hatch_1_-12_8_navlink")}]}
    layout = {"up_axis": "z"}
    (tmp_path / "lot.layout.json").write_text(json.dumps(layout), encoding="utf-8")
    files = _files(tmp_path, "lot", gp, {"lot.layout.json": tmp_path / "lot.layout.json"})
    rt = SimpleNamespace(files=files, manifest=layout, schema="lot.layout.v1")
    imp = lot_imp.load(rt)
    ids = [l["id"] for l in imp.nav.links]
    assert ids == ["lot:deli_a01_hatch_1_-12_8_navlink"], ids
    assert imp.nav.links[0]["source"] == "lot"
