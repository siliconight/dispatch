"""Lux importer: lighting profile. Presentation layer unless gameplay-critical
(TDD 3) — Dispatch records the profile and light data; the Lux addon owns the
runtime look."""

from __future__ import annotations

from . import ToolImport, read_json_file


def load(rt) -> ToolImport:
    imp = ToolImport(tool="lux", files=dict(rt.files))
    imp.meta["schema"] = rt.schema
    imp.meta["profile"] = rt.manifest
    if "lux.lighting.json" in rt.files:
        imp.meta["lighting"] = read_json_file(rt.files["lux.lighting.json"], "lux")
    if "lux.volumes.json" in rt.files:
        imp.meta["volumes"] = read_json_file(rt.files["lux.volumes.json"], "lux")
    return imp
