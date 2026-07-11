"""Scene Assembler and mission shell package export.

build_context() runs resolve -> import -> normalize (anchors, nav, beat
graph, ownership declarations). assemble_scene() builds the handoff scene
(handoff spec section 9): Functional / Presentation / Handoff, plus
PreviewOnly when preview mode is requested. export_package() writes the
package (section 10).

Dispatch prepares a mission shell for gameplay and server engineering. It
implements no mission authority, RPCs, replication, persistence, late-join
recovery, or objective/combat/AI behavior.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import GENERATED_MARKER, __version__
from .anchors import find_duplicate_ids
from .flow import compile_beats
from .importers import IMPORTERS
from .navgraph import NavGraph, merge
from .anchors import required_authority_for
from .ownership import (ANCHOR_GROUPS, build_anchor_registry,
                        build_ownership_requirements, layer_for,
                        node_path_for)
from .resolver import resolve_inputs
from .spec import MissionSpec
from .tscn import Scene, SceneNode, serialize

GD_DIR = Path(__file__).parent / "gd"

# "playtest" and "preview-playtest" are aliases: shell-handoff plus the
# isolated preview_only/ package (delta D1 resolution — v0.1.0's runtime
# skeleton is not resurrected; AC7 amended accordingly).
MODES = ("shell-handoff", "playtest", "preview-playtest", "runtime-adapter")
DEFAULT_MODE = "shell-handoff"
PREVIEW_MODES = ("playtest", "preview-playtest")

PREVIEW_HEADER = (
    "# DISPATCH PREVIEW ONLY\n"
    "# Not production gameplay or networking code."
)


@dataclass
class BuildContext:
    spec: MissionSpec
    resolved: object
    imports: dict                      # tool -> ToolImport
    mode: str = DEFAULT_MODE
    include_preview: bool = False
    anchors: list = field(default_factory=list)
    nav: NavGraph = None
    beats: object = None
    ownership: dict = field(default_factory=dict)
    registry: dict = field(default_factory=dict)
    duplicate_anchor_ids: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def res_root(self) -> str:
        godot = self.spec.raw.get("godot", {}) or {}
        return str(godot.get("res_root", f"res://missions/{self.spec.mission_id}")).rstrip("/")


def build_context(spec: MissionSpec, mode: str = DEFAULT_MODE,
                  include_preview: bool = False) -> BuildContext:
    if mode not in MODES:
        raise ValueError(f"unknown build mode {mode!r}; expected one of {MODES}")
    include_preview = include_preview or mode in PREVIEW_MODES
    resolved = resolve_inputs(spec)
    imports = {}
    for tool in sorted(resolved.tools):
        imports[tool] = IMPORTERS[tool](resolved.tools[tool])

    anchors = []
    for tool in ("deli_counter", "lot"):
        if tool in imports:
            anchors.extend(imports[tool].anchors)
    anchors.sort(key=lambda a: (a.type, a.id))

    # runtime-adapter mode ships adapter interfaces, so anchors with a known
    # expected adapter become adapter_available; Dispatch never sets
    # integrated / verified_by_game_runtime (handoff spec section 8).
    if mode == "runtime-adapter":
        for a in anchors:
            if a.expected_adapter:
                a.integration_status = "adapter_available"

    graphs = [imports[t].nav for t in ("deli_counter", "lot") if t in imports and imports[t].nav]
    nav = merge(graphs, float(spec.tuning["nav_bridge_radius"])) if graphs else NavGraph()

    beats = compile_beats(spec.mission_flow, anchors, spec.mission_id)

    ctx = BuildContext(
        spec=spec,
        resolved=resolved,
        imports=imports,
        mode=mode,
        include_preview=include_preview,
        anchors=anchors,
        nav=nav,
        beats=beats,
        duplicate_anchor_ids=find_duplicate_ids(anchors),
        warnings=list(resolved.warnings),
    )
    ctx.ownership = build_ownership_requirements(spec, anchors)
    ctx.registry = build_anchor_registry(spec, anchors)
    if spec.legacy_schema:
        ctx.warnings.append(
            "spec uses schema dispatch.mission.v0.1; read for compatibility — "
            "new specs should declare dispatch.mission.v0.2.")
    return ctx


# --- scene ------------------------------------------------------------------


def assemble_scene(ctx: BuildContext) -> Scene:
    spec = ctx.spec
    res = ctx.res_root
    scene = Scene(root_name="MissionRoot")

    ext_ids = {}

    def ext(rtype: str, rel_path: str, key: str) -> str:
        if key not in ext_ids:
            ext_ids[key] = scene.add_ext(rtype, f"{res}/{rel_path}", f"{len(ext_ids) + 1}_{key}")
        return ext_ids[key]

    root = SceneNode(name="MissionRoot", type="Node3D", parent="")
    root.metadata = {
        "dispatch_generated": True,
        "dispatch_marker": GENERATED_MARKER,
        "dispatch_version": __version__,
        "dispatch_mode": ctx.mode,
        "mission_id": spec.mission_id,
        "mission_title": spec.title,
    }
    scene.add(root)

    # -- Functional ------------------------------------------------------------
    scene.add(SceneNode(name="Functional", parent="."))
    for group in ("Geometry", "Collision", "GameplayAnchors", "NavigationHints"):
        scene.add(SceneNode(name=group, parent="Functional",
                            metadata={"dispatch_generated": True}))

    if "lot" in ctx.imports:
        eid = ext("PackedScene", "assets/lot.glb", "lot")
        scene.add(SceneNode(name="LotSite", parent="Functional/Geometry", instance=eid,
                            metadata={"dispatch_generated": True, "source": "lot",
                                      "layer": "functional"}))
    if "deli_counter" in ctx.imports:
        eid = ext("PackedScene", "assets/shell.glb", "shell")
        scene.add(SceneNode(name="Shell", parent="Functional/Geometry", instance=eid,
                            metadata={"dispatch_generated": True, "source": "deli_counter",
                                      "layer": "functional"}))
        if "collision" in ctx.imports["deli_counter"].meta:
            node = SceneNode(name="ShellCollisionInfo", type="Node", parent="Functional/Collision",
                             metadata={"dispatch_generated": True,
                                       "collision_manifest": f"{res}/assets/shell.collision.json"})
            scene.add(node)

    for g in ANCHOR_GROUPS:
        scene.add(SceneNode(name=g, parent="Functional/GameplayAnchors",
                            metadata={"dispatch_generated": True}))
    for a in ctx.anchors:
        path = node_path_for(a)
        parent, name = path.rsplit("/", 1)
        md = {
            "dispatch_generated": True,
            "shell_id": a.qualified_id(spec.mission_id),
            "anchor_type": a.type,
            "source": a.source,
            "layer": layer_for(a),
            "required_authority": required_authority_for(a),
            "integration_status": a.integration_status,
        }
        if a.expected_adapter:
            md["expected_adapter"] = a.expected_adapter
        if a.tags:
            md["tags"] = list(a.tags)
        if a.objective:
            md["objective"] = a.objective
        scene.add(SceneNode(name=name, type="Marker3D", parent=parent,
                            pos=a.pos, rot_y=a.rot_y, metadata=md))

    scene.add(SceneNode(name="NavMesh", type="NavigationRegion3D",
                        parent="Functional/NavigationHints",
                        metadata={"dispatch_generated": True, "bake_required": True,
                                  "navigation_hints_file": f"{res}/navigation_hints.json"}))

    # -- Presentation ------------------------------------------------------------
    scene.add(SceneNode(name="Presentation", parent="."))
    for group in ("Props", "Materials", "Decals", "Lighting", "Atmosphere"):
        scene.add(SceneNode(name=group, parent="Presentation",
                            metadata={"dispatch_generated": True, "layer": "presentation"}))

    if "patina" in ctx.imports:
        eid = ext("PackedScene", "presentation/shell.patina.glb", "patina")
        scene.add(SceneNode(name="StyledShell", parent="Presentation/Materials", instance=eid,
                            metadata={"dispatch_generated": True, "source": "patina",
                                      "layer": "presentation"}))
    if "lux" in ctx.imports:
        profile = ctx.imports["lux"].meta.get("profile", {})
        for n in scene.nodes:
            if n.name == "Lighting" and n.parent == "Presentation":
                n.metadata.update({
                    "lux_profile": str(profile.get("preset", profile.get("name", ""))),
                    "lux_profile_file": f"{res}/presentation/lux/lux.profile.json",
                })
        if "volumes" in ctx.imports["lux"].meta:
            for n in scene.nodes:
                if n.name == "Atmosphere" and n.parent == "Presentation":
                    n.metadata["lux_volumes_file"] = f"{res}/presentation/lux/lux.volumes.json"

    _add_props(ctx, scene, ext)

    # -- Handoff -----------------------------------------------------------------
    scene.add(SceneNode(name="Handoff", parent="."))
    scene.add(SceneNode(name="OwnershipRequirements", type="Node", parent="Handoff",
                        metadata={"dispatch_generated": True,
                                  "file": f"{res}/runtime_ownership_requirements.json"}))
    scene.add(SceneNode(name="ProposedBeatGraph", type="Node", parent="Handoff",
                        metadata={"dispatch_generated": True,
                                  "file": f"{res}/proposed_beat_graph.json"}))
    scene.add(SceneNode(name="ValidationMetadata", type="Node", parent="Handoff",
                        metadata={"dispatch_generated": True,
                                  "dispatch_version": __version__,
                                  "report_file": f"{res}/validation/report.json"}))

    # -- PreviewOnly (playtest modes or --include-preview) -------------------------
    if ctx.include_preview:
        scene.add(SceneNode(name="PreviewOnly", parent="."))
        bid = ext("Script", "preview_only/preview_mission_bridge.gd", "preview")
        node = SceneNode(name="PreviewMissionBridge", type="Node", parent="PreviewOnly",
                         metadata={"dispatch_generated": True, "preview_only": True})
        node.script = bid
        node.props["beat_graph_path"] = f"{res}/proposed_beat_graph.json"
        scene.add(node)

    return scene


def _add_props(ctx: BuildContext, scene: Scene, ext) -> None:
    """Prop placements from DC/Lot against the Zoo catalog -> Presentation/Props.

    Placement is presentation; any gameplay function a prop implies (cover,
    blocking) is declared via gameplay_tags metadata for the runtime to honor.
    """
    from .anchors import blender_to_godot
    zoo = ctx.imports.get("zoo")
    catalog = zoo.meta.get("assets", {}) if zoo else {}
    props_dir = zoo.meta.get("props_dir") if zoo else None
    placements = []
    for tool in ("deli_counter", "lot"):
        if tool in ctx.imports:
            for p in ctx.imports[tool].props:
                placements.append((tool, p))
    counter = {}
    for tool, p in placements:
        aid = str(p.get("asset_id", ""))
        counter[aid] = counter.get(aid, 0) + 1
        name = f"{aid}_{counter[aid]:02d}"
        pos = blender_to_godot(p.get("pos", (0, 0, 0)))
        md = {"dispatch_generated": True, "asset_id": aid, "source": tool,
              "layer": "presentation"}
        meta = catalog.get(aid, {})
        if meta.get("gameplay_tags"):
            md["gameplay_tags"] = list(meta["gameplay_tags"])
        glb = (props_dir / f"{aid}.glb") if props_dir else None
        if glb and glb.is_file():
            eid = ext("PackedScene", f"presentation/props/{aid}.glb", f"prop_{aid}")
            node = SceneNode(name=name, parent="Presentation/Props", instance=eid,
                             pos=pos, rot_y=float(p.get("rot_y", 0.0)), metadata=md)
        else:
            md["missing_asset"] = True
            node = SceneNode(name=name, type="Marker3D", parent="Presentation/Props",
                             pos=pos, rot_y=float(p.get("rot_y", 0.0)), metadata=md)
        scene.add(node)


# --- package export -----------------------------------------------------------


def default_out_dir(spec: MissionSpec) -> Path:
    return spec.spec_dir / "export" / "godot" / "missions" / spec.mission_id


def export_package(ctx: BuildContext, scene: Scene, out_dir: Path) -> dict:
    """Write the mission shell package (handoff spec section 10)."""
    spec = ctx.spec
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "assets").mkdir(exist_ok=True)
    pres = out_dir / "presentation"
    pres.mkdir(exist_ok=True)

    copied = []

    def copy(src: Path, rel: str) -> None:
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied.append(rel)

    # functional assets
    if "deli_counter" in ctx.imports:
        copy(ctx.imports["deli_counter"].meta["glb"], "assets/shell.glb")
        coll = ctx.imports["deli_counter"].files.get("shell.collision.json")
        if coll:
            copy(coll, "assets/shell.collision.json")
    if "lot" in ctx.imports:
        copy(ctx.imports["lot"].meta["glb"], "assets/lot.glb")

    # presentation assets
    if "patina" in ctx.imports:
        copy(ctx.imports["patina"].meta["glb"], "presentation/shell.patina.glb")
        tex = ctx.imports["patina"].files.get("textures")
        if tex and tex.is_dir():
            shutil.copytree(tex, pres / "textures", dirs_exist_ok=True)
            copied.append("presentation/textures/")
    if "lux" in ctx.imports:
        for name, path in sorted(ctx.imports["lux"].files.items()):
            if path.is_file():
                copy(path, f"presentation/lux/{name}")
    zoo = ctx.imports.get("zoo")
    if zoo and zoo.meta.get("props_dir"):
        used = {str(p.get("asset_id")) for t in ("deli_counter", "lot") if t in ctx.imports
                for p in ctx.imports[t].props}
        for aid in sorted(used):
            glb = zoo.meta["props_dir"] / f"{aid}.glb"
            if glb.is_file():
                copy(glb, f"presentation/props/{aid}.glb")

    # scene + handoff data
    (out_dir / "mission.tscn").write_text(serialize(scene), encoding="utf-8")
    (out_dir / "gameplay_anchors.json").write_text(
        json.dumps(ctx.registry, indent=2) + "\n", encoding="utf-8")
    (out_dir / "proposed_beat_graph.json").write_text(
        json.dumps(ctx.beats.to_json(), indent=2) + "\n", encoding="utf-8")
    (out_dir / "runtime_ownership_requirements.json").write_text(
        json.dumps(ctx.ownership, indent=2) + "\n", encoding="utf-8")
    nav = ctx.nav.to_json(bridge_radius=float(spec.tuning["nav_bridge_radius"]))
    (out_dir / "navigation_hints.json").write_text(
        json.dumps(nav, indent=2) + "\n", encoding="utf-8")

    # mode-specific code packages
    files = []
    if ctx.include_preview:
        pdir = out_dir / "preview_only"
        pdir.mkdir(exist_ok=True)
        _write_gd(pdir, "preview_mission_bridge.gd", "preview_mission_bridge.gd.tpl", spec)
        files.append("preview_only/preview_mission_bridge.gd")
    else:
        # handoff scenes must carry no preview code from earlier builds
        shutil.rmtree(out_dir / "preview_only", ignore_errors=True)
    if ctx.mode == "runtime-adapter":
        adir = out_dir / "adapters"
        adir.mkdir(exist_ok=True)
        for name in ("mission_events.gd", "anchor_adapter.gd", "adapter_registry.gd"):
            _write_gd(adir, name, f"{name}.tpl", spec)
            files.append(f"adapters/{name}")
    else:
        shutil.rmtree(out_dir / "adapters", ignore_errors=True)

    manifest = {
        "schema": "dispatch.manifest.v0.2",
        "dispatch_version": __version__,
        "marker": GENERATED_MARKER,
        "mode": ctx.mode,
        "include_preview": ctx.include_preview,
        "mission_id": spec.mission_id,
        "title": spec.title,
        "engine": spec.engine,
        "mode_of_play": spec.mode,
        "players": {"min": spec.players_min, "max": spec.players_max,
                    "preferred": spec.players_preferred},
        "intended_networking": {"model": spec.net_model,
                                "implemented_by": "production game runtime"},
        "res_root": ctx.res_root,
        "inputs": {t: rt.schema for t, rt in sorted(ctx.resolved.tools.items())},
        "anchor_counts": _anchor_counts(ctx),
        "beat_count": len(ctx.beats.beats),
        "files": sorted(copied) + sorted(files) + [
            "mission.tscn", "mission_manifest.json", "gameplay_anchors.json",
            "proposed_beat_graph.json", "runtime_ownership_requirements.json",
            "navigation_hints.json", "build.lock.json", "resource_manifest.json",
            "HANDOFF.md", "LICENSES.md",
        ],
    }
    (out_dir / "mission_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _anchor_counts(ctx: BuildContext) -> dict:
    counts = {}
    for a in ctx.anchors:
        counts[a.type] = counts.get(a.type, 0) + 1
    return dict(sorted(counts.items()))


def _write_gd(out_dir: Path, name: str, tpl: str, spec: MissionSpec) -> None:
    text = (GD_DIR / tpl).read_text(encoding="utf-8")
    text = text.replace("{version}", __version__).replace("{mission_id}", spec.mission_id)
    (out_dir / name).write_text(text, encoding="utf-8")
