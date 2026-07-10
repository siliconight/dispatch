"""Zoo importer: prop catalog and asset metadata."""

from __future__ import annotations

from . import ToolImport


def load(rt) -> ToolImport:
    imp = ToolImport(tool="zoo", files=dict(rt.files))
    cat = rt.manifest  # zoo.catalog.json
    assets = {}
    for rec in cat.get("assets", []):
        aid = rec.get("asset_id")
        if aid:
            assets[aid] = rec
    imp.meta["schema"] = rt.schema
    imp.meta["assets"] = assets
    props_dir = rt.files.get("props")
    if props_dir:
        imp.meta["props_dir"] = props_dir
    return imp
