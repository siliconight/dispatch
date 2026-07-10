"""Lot importer: outdoor site, exterior anchors, nav hints."""

from __future__ import annotations

from ..anchors import normalize_anchors
from ..navgraph import load_nav_hints
from . import ToolImport, read_json_file


def load(rt) -> ToolImport:
    imp = ToolImport(tool="lot", files=dict(rt.files))
    layout = rt.manifest  # lot.layout.json is the manifest
    up = str(layout.get("up_axis", "z"))
    gp = read_json_file(rt.files["lot.gameplay.json"], "lot")
    imp.anchors = normalize_anchors(gp.get("anchors", []), "lot", str(gp.get("up_axis", up)))
    imp.props = list(gp.get("props", []))
    nav = read_json_file(rt.files["lot.nav_hints.json"], "lot")
    imp.nav = load_nav_hints(nav, "lot", str(nav.get("up_axis", up)))
    imp.meta["schema"] = rt.schema
    imp.meta["layout"] = layout
    imp.meta["glb"] = rt.files["lot.glb"]
    return imp
