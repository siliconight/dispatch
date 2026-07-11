"""Import Resolver (TDD 13.1).

Resolves upstream tool outputs relative to each tool's manifest, validates
that required files exist, and produces a build lock file recording versions
and content hashes for repeatable builds (TDD 21).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import DispatchError, __version__
from .spec import MissionSpec

# tool -> (required sibling files, optional sibling files), resolved relative
# to the manifest named in the spec. "*" entries are directories.
TOOL_FILES = {
    "deli_counter": {
        "manifest": "shell.gameplay.json",
        "required": ["shell.glb", "shell.gameplay.json", "shell.nav_hints.json"],
        "optional": ["shell.collision.json"],
    },
    "lot": {
        "manifest": "lot.layout.json",
        "required": ["lot.glb", "lot.layout.json", "lot.gameplay.json", "lot.nav_hints.json"],
        "optional": [],
    },
    "zoo": {
        "manifest": "zoo.catalog.json",
        "required": ["zoo.catalog.json"],
        "optional": ["props"],
    },
    "patina": {
        "manifest": "shell.patina.json",
        "required": ["shell.patina.glb", "shell.patina.json"],
        "optional": ["textures"],
    },
    "lux": {
        "manifest": "lux.profile.json",
        "required": ["lux.profile.json"],
        "optional": ["lux.lighting.json", "lux.volumes.json"],
    },
}

OPTIONAL_TOOLS = ("zoo", "patina", "lux")


@dataclass
class ResolvedTool:
    tool: str
    root: Path                       # directory holding this tool's outputs
    files: dict = field(default_factory=dict)   # name -> Path (present files)
    manifest: dict = field(default_factory=dict)
    schema: str = ""


@dataclass
class ResolvedInputs:
    tools: dict = field(default_factory=dict)   # tool -> ResolvedTool
    warnings: list = field(default_factory=list)

    def has(self, tool: str) -> bool:
        return tool in self.tools


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path, tool: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DispatchError(
            f"{tool} manifest is not valid JSON: {path} ({e})",
            suggested_fix=f"Re-run the {tool} export or fix the file by hand.",
        )


def resolve_inputs(spec: MissionSpec) -> ResolvedInputs:
    out = ResolvedInputs()
    for tool, rel in sorted(spec.inputs.items()):
        info = TOOL_FILES[tool]
        manifest_path = (spec.spec_dir / rel).resolve()
        if not manifest_path.is_file():
            if tool in OPTIONAL_TOOLS:
                out.warnings.append(
                    f"optional input {tool} manifest not found at {manifest_path}; skipping {tool}."
                )
                continue
            raise DispatchError(
                f"required {tool.replace('_', ' ').title()} file {manifest_path.name} is missing.",
                expected=str(manifest_path),
                suggested_fix=f"Run the {tool} export again or update dispatch.mission.json.",
            )
        root = manifest_path.parent
        rt = ResolvedTool(tool=tool, root=root)
        rt.files[manifest_path.name] = manifest_path
        for name in info["required"]:
            p = root / name
            if not p.exists():
                raise DispatchError(
                    f"required {tool.replace('_', ' ').title()} file {name} is missing.",
                    expected=str(p),
                    suggested_fix=f"Run the {tool} export again or update dispatch.mission.json.",
                )
            rt.files[name] = p
        for name in info["optional"]:
            p = root / name
            if p.exists():
                rt.files[name] = p
        rt.manifest = _read_json(manifest_path, tool)
        rt.schema = str(rt.manifest.get("schema", ""))
        out.tools[tool] = rt
    return out


def write_lock_file(spec: MissionSpec, resolved: ResolvedInputs, out_dir: Path,
                    mode: str = "shell-handoff") -> Path:
    """dispatch.build_lock.v0.2 (delta D8): what Dispatch consumed and
    produced — spec hash, per-role input hashes, per-file output hashes,
    contract, mode, timestamp. Level Factory wraps this in its own lock.
    Written LAST: it hashes every package file except itself.
    """
    from datetime import datetime, timezone

    from . import SCHEMA_MISSION

    inputs = [{"role": "mission_spec", "path": str(spec.spec_path),
               "sha256": _sha256(spec.spec_path)}]
    for tool, rt in sorted(resolved.tools.items()):
        for name, path in sorted(rt.files.items()):
            if path.is_dir():
                continue
            inputs.append({"role": f"{tool}:{name}", "path": str(path),
                           "sha256": _sha256(path)})

    outputs = []
    for f in sorted(out_dir.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(out_dir).as_posix()
        if rel == "build.lock.json":
            continue
        outputs.append({"path": rel, "sha256": _sha256(f)})

    lock = {
        "schema": "dispatch.build_lock.v0.2",
        "dispatch_version": __version__,
        "contract": SCHEMA_MISSION,
        "mode": mode,
        "mission_id": spec.mission_id,
        "engine": spec.engine,
        "spec_sha256": _sha256(spec.spec_path),
        "inputs": inputs,
        "outputs": outputs,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "build.lock.json"
    p.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    return p
