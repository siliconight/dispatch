"""Deli Counter importer: building shell, gameplay anchors, nav hints."""

from __future__ import annotations

from ..anchors import normalize_anchors
from ..navgraph import load_nav_hints
from . import ToolImport, read_json_file


def load(rt) -> ToolImport:
    imp = ToolImport(tool="deli_counter", files=dict(rt.files))
    gp = rt.manifest  # shell.gameplay.json is the manifest
    up = str(gp.get("up_axis", "z"))
    imp.anchors = normalize_anchors(gp.get("anchors", []), "deli_counter", up)
    imp.props = list(gp.get("props", []))
    nav = read_json_file(rt.files["shell.nav_hints.json"], "deli_counter")
    imp.nav = load_nav_hints(nav, "deli_counter", str(nav.get("up_axis", up)))
    if "shell.collision.json" in rt.files:
        imp.meta["collision"] = read_json_file(rt.files["shell.collision.json"], "deli_counter")
    imp.meta["schema"] = rt.schema
    imp.meta["glb"] = rt.files["shell.glb"]
    return imp
