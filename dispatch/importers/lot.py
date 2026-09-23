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
    # Interactive fixtures: replicable state machines declared upstream
    # (Deli Counter emits them per building; Lot concatenates them into the
    # site — see the factory's INTERACTIVES.md). Carried VERBATIM: their ids
    # are the network handle, their transforms are already site-space, and
    # Dispatch's job is to ship the declaration, not to normalize it into
    # anchors — a state machine is the netcode's input, not a Marker3D.
    imp.meta["interactives"] = list(gp.get("interactives", []) or [])
    nav = read_json_file(rt.files["lot.nav_hints.json"], "lot")
    imp.nav = load_nav_hints(nav, "lot", str(nav.get("up_axis", up)))
    # OFF-MESH LINKS. Deli Counter computes one per ladder and files it on the
    # ladder; Lot concatenates its buildings' ladders into the site with every
    # position moved into site space. THIS is the importer a site mission
    # runs -- the Deli Counter one only loads for a single-building mission --
    # and cold run 9075 shipped a package with 23 gb_ladder surfaces and an
    # empty `links[]` because only that one had been taught to carry them.
    _up = str(nav.get("up_axis", up))
    for _lad in gp.get("ladders", []) or []:
        _link = _lad.get("nav_link")
        if _link:
            imp.nav.add_off_mesh_link(_link, "lot", _up)
    imp.meta["schema"] = rt.schema
    imp.meta["layout"] = layout
    imp.meta["glb"] = rt.files["lot.glb"]
    return imp
