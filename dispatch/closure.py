"""Resource closure and anchor parity (delta D11, AC4, AC5).

Dispatch owns closure for the package IT writes: every resource referenced by
mission.tscn must exist inside the export root; no absolute filesystem paths;
no references into tool repositories or workspaces. These checks run against
the WRITTEN package — validated, not assumed. Level Factory's exporter owns
full portable-godot closure (Lux localization, clean-project instantiation);
Dispatch does neither.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import __version__
from .validators import Issue

SYSTEM = "closure"

_EXT_RES_RE = re.compile(r'\[ext_resource[^\]]*?path="([^"]+)"')
_SHELL_ID_RE = re.compile(r'metadata/shell_id = "([^"]+)"')

# Path fragments that indicate a reference back into an authoring repo or
# workspace rather than the self-contained package.
_REPO_MARKERS = ("/repos/", "\\repos\\", "/workspace/", "\\workspace\\",
                 "/siliconight/", "\\siliconight\\", "/.git/", "\\.git\\",
                 "/addons/dispatch", "user://")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_absolute_ref(ref: str) -> bool:
    if ref.startswith("res://") or ref.startswith("uid://"):
        return False
    if re.match(r"^[A-Za-z]:[/\\]", ref):   # windows drive path
        return True
    return ref.startswith("/") or ref.startswith("\\\\")


def scan_package(out_dir: Path, res_root: str) -> list:
    """Closure checks on the written package. Every violation is a blocker."""
    issues = []
    tscn = out_dir / "mission.tscn"
    if not tscn.is_file():
        issues.append(Issue("blocker", SYSTEM, "mission.tscn is missing from the package.",
                            "Re-run the build."))
        return issues
    text = tscn.read_text(encoding="utf-8")
    root = res_root.rstrip("/")
    for ref in _EXT_RES_RE.findall(text):
        if _is_absolute_ref(ref):
            issues.append(Issue(
                "blocker", SYSTEM,
                f"mission.tscn references an absolute filesystem path: {ref}",
                "All references must be res:// paths inside the export root.",
            ))
            continue
        if any(m in ref for m in _REPO_MARKERS):
            issues.append(Issue(
                "blocker", SYSTEM,
                f"mission.tscn references a tool repository or workspace path: {ref}",
                "The package must be self-contained; re-run the build.",
            ))
            continue
        if ref.startswith("res://"):
            if not ref.startswith(root + "/"):
                issues.append(Issue(
                    "blocker", SYSTEM,
                    f"mission.tscn references a resource outside the export root: {ref}",
                    f"Every referenced resource must live under {root}/.",
                ))
                continue
            rel = ref[len(root) + 1:]
            if not (out_dir / rel).is_file():
                issues.append(Issue(
                    "blocker", SYSTEM,
                    f"mission.tscn references {ref} but {rel} was not emitted into the package.",
                    "Re-run the build; if it persists this is a Dispatch bug.",
                ))
    return issues


def check_anchor_parity(out_dir: Path) -> list:
    """AC4: gameplay_anchors.json must exactly match the Marker3D anchor set
    in the written mission.tscn. Blocking on any mismatch."""
    issues = []
    tscn = out_dir / "mission.tscn"
    reg_path = out_dir / "gameplay_anchors.json"
    if not tscn.is_file() or not reg_path.is_file():
        return issues  # missing files already reported by closure/resolver
    scene_ids = set(_SHELL_ID_RE.findall(tscn.read_text(encoding="utf-8")))
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    registry_ids = {a["shell_id"] for a in reg.get("anchors", [])}
    for missing in sorted(registry_ids - scene_ids):
        issues.append(Issue(
            "blocker", SYSTEM,
            f"Anchor {missing!r} is in gameplay_anchors.json but not in mission.tscn.",
            "Registry and scene must match exactly; re-run the build.",
        ))
    for extra in sorted(scene_ids - registry_ids):
        issues.append(Issue(
            "blocker", SYSTEM,
            f"Anchor {extra!r} is in mission.tscn but not in gameplay_anchors.json.",
            "Registry and scene must match exactly; re-run the build.",
        ))
    return issues


def write_resource_manifest(out_dir: Path) -> Path:
    """dispatch.resource_manifest.v0.2: every file in the package with sha256.

    Excludes itself and build.lock.json (the lock is written afterwards and
    hashes this manifest among the outputs). The package requires no editor
    plugins and no autoloads — it is consumable without Dispatch installed.
    """
    skip = {"resource_manifest.json", "build.lock.json"}
    files = []
    for p in sorted(out_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(out_dir).as_posix()
        if rel in skip:
            continue
        files.append({"path": rel, "sha256": _sha256(p), "bytes": p.stat().st_size})
    manifest = {
        "schema": "dispatch.resource_manifest.v0.2",
        "dispatch_version": __version__,
        "requires_editor_plugins": False,
        "requires_autoloads": False,
        "files": files,
    }
    out = out_dir / "resource_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out
