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
    # Single-building missions with no Lot input still ship their state
    # machines; when Lot is present its site-level concatenation wins
    # (see assembler.export_package). Carried verbatim, same as lot.py.
    imp.meta["interactives"] = list(gp.get("interactives", []) or [])
    nav = read_json_file(rt.files["shell.nav_hints.json"], "deli_counter")
    imp.nav = load_nav_hints(nav, "deli_counter", str(nav.get("up_axis", up)))
    # OFF-MESH LINKS, from the gameplay manifest rather than the nav hints:
    # Deli Counter computes one per ladder (`ladder._nav_link`) and files it on
    # the ladder, because that is where its cost, capability and access state
    # live. Without this the package ships a climb MARKER and no edge, so a
    # player can climb a ladder and an AI cannot path up it (roadmap 172).
    _up = str(nav.get("up_axis", up))
    for _lad in gp.get("ladders", []) or []:
        _link = _lad.get("nav_link")
        if _link:
            imp.nav.add_off_mesh_link(_link, "deli_counter", _up)
    if "shell.collision.json" in rt.files:
        imp.meta["collision"] = read_json_file(rt.files["shell.collision.json"], "deli_counter")
    imp.meta["schema"] = rt.schema
    imp.meta["glb"] = rt.files["shell.glb"]
    return imp
