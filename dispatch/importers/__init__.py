"""Per-tool importers.

Each importer takes a ResolvedTool and returns a ToolImport with a common
shape: anchors, an optional nav graph, prop placements, and metadata.
Dispatch never edits upstream data (TDD 2) — importers read and normalize.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .. import DispatchError


@dataclass
class ToolImport:
    tool: str
    anchors: list = field(default_factory=list)
    nav = None
    props: list = field(default_factory=list)    # placements: asset_id/pos/rot_y
    meta: dict = field(default_factory=dict)
    files: dict = field(default_factory=dict)    # name -> Path


def read_json_file(path: Path, tool: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DispatchError(
            f"{tool} file is not valid JSON: {path} ({e})",
            suggested_fix=f"Re-run the {tool} export.",
        )


from . import deli_counter, lot, lux, patina, zoo  # noqa: E402,F401

IMPORTERS = {
    "deli_counter": deli_counter.load,
    "lot": lot.load,
    "zoo": zoo.load,
    "patina": patina.load,
    "lux": lux.load,
}
