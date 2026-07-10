"""Patina importer: styled visual shell. Must not invalidate DC gameplay anchors
(TDD 8.4) — Dispatch keeps DC gameplay data authoritative and only swaps the
visual mesh."""

from __future__ import annotations

from . import ToolImport


def load(rt) -> ToolImport:
    imp = ToolImport(tool="patina", files=dict(rt.files))
    imp.meta["schema"] = rt.schema
    imp.meta["glb"] = rt.files["shell.patina.glb"]
    imp.meta["materials"] = rt.manifest.get("materials", [])
    imp.meta["manifest"] = rt.manifest
    return imp
