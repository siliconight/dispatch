"""Scene Assembler (TDD 13.2) and mission package export (TDD 10).

build_context() runs resolve -> import -> normalize (anchors, nav, flow,
authority) and returns everything validators and exporters need.
assemble_scene() builds the predictable MissionRoot hierarchy (TDD 11).
export_package() writes the mission folder.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import GENERATED_MARKER, __version__
from .anchors import assign_net_ids, find_duplicate_ids
from .authority import ANCHOR_PARENT, authority_for, build_authority_map, node_path_for
from .flow import compile_flow
from .importers import IMPORTERS
from .navgraph import NavGraph, merge
from .resolver import resolve_inputs, write_lock_file
from .spec import MissionSpec
from .tscn import Raw, Scene, SceneNode, serialize

GD_DIR = Path(__file__).parent / "gd"

WORLD_GROUPS = ("LotRoot", "BuildingRoot", "PropsRoot", "VisualsRoot",
                "LightingRoot", "FXRoot", "AudioRoot")
RUNTIME_NODES = ("MissionController", "ObjectiveController", "SpawnController",
                 "ExtractionController", "NetworkAuthority", "ReplicationRegistry",
                 "DebugOverlay")


@dataclass
class BuildContext:
    spec: MissionSpec
    resolved: object
    imports: dict                      # tool -> ToolImport
    anchors: list = field(default_factory=list)
    nav: NavGraph = None
    flow: object = None
    authority: dict = field(default_factory=dict)
    duplicate_anchor_ids: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def res_root(self) -> str:
        godot = self.spec.raw.get("godot", {}) or {}
        return str(godot.get("res_root", f"res://missions/{self.spec.mission_id}")).rstrip("/")


def build_context(spec: MissionSpec) -> BuildContext:
    resolved = resolve_inputs(spec)
    imports = {}
    for tool in sorted(resolved.tools):
        imports[tool] = IMPORTERS[tool](resolved.tools[tool])

    anchors = []
    for tool in ("deli_counter", "lot"):
        if tool in imports:
            anchors.extend(imports[tool].anchors)
    anchors.sort(key=lambda a: (a.type, a.id))
    assign_net_ids(anchors)

    graphs = [imports[t].nav for t in ("deli_counter", "lot") if t in imports and imports[t].nav]
    nav = merge(graphs, float(spec.tuning["nav_bridge_radius"])) if graphs else NavGraph()

    flow = compile_flow(spec.mission_flow, anchors)
    authority = build_authority_map(spec, anchors)

    ctx = BuildContext(
        spec=spec,
        resolved=resolved,
        imports=imports,
        anchors=anchors,
        nav=nav,
        flow=flow,
        authority=authority,
        duplicate_anchor_ids=find_duplicate_ids(anchors),
        warnings=list(resolved.warnings),
    )
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
        "mission_id": spec.mission_id,
        "mission_title": spec.title,
    }
    scene.add(root)

    # -- World ---------------------------------------------------------------
    scene.add(SceneNode(name="World", parent="."))
    for group in WORLD_GROUPS:
        scene.add(SceneNode(name=group, parent="World",
                            metadata={"dispatch_generated": True}))

    if "lot" in ctx.imports:
        eid = ext("PackedScene", "assets/lot.glb", "lot")
        scene.add(SceneNode(name="LotSite", parent="World/LotRoot", instance=eid,
                            metadata={"dispatch_generated": True, "source": "lot",
                                      "role": "function"}))

    if "deli_counter" in ctx.imports:
        eid = ext("PackedScene", "assets/shell.glb", "shell")
        scene.add(SceneNode(name="Shell", parent="World/BuildingRoot", instance=eid,
                            metadata={"dispatch_generated": True, "source": "deli_counter",
                                      "role": "function"}))

    if "patina" in ctx.imports:
        eid = ext("PackedScene", "assets/shell.patina.glb", "patina")
        scene.add(SceneNode(name="StyledShell", parent="World/VisualsRoot", instance=eid,
                            metadata={"dispatch_generated": True, "source": "patina",
                                      "role": "presentation", "authority": "client"}))

    if "lux" in ctx.imports:
        lighting = scene.nodes  # LightingRoot already added; attach metadata
        for n in lighting:
            if n.name == "LightingRoot":
                profile = ctx.imports["lux"].meta.get("profile", {})
                n.metadata.update({
                    "authority": "client",
                    "lux_profile": str(profile.get("preset", profile.get("name", ""))),
                    "lux_profile_file": f"{res}/assets/lux/lux.profile.json",
                })

    _add_props(ctx, scene, ext)

    # -- Gameplay ------------------------------------------------------------
    scene.add(SceneNode(name="Gameplay", parent="."))
    gameplay_groups = ["PlayerStarts", "Objectives", "ExtractionPoints",
                       "Interactables", "Triggers"]
    for g in gameplay_groups:
        scene.add(SceneNode(name=g, parent="Gameplay",
                            metadata={"dispatch_generated": True}))
    scene.add(SceneNode(name="AI", parent="Gameplay"))
    for g in ("SpawnZones", "PatrolRoutes", "CoverPoints", "DirectorZones"):
        scene.add(SceneNode(name=g, parent="Gameplay/AI",
                            metadata={"dispatch_generated": True}))
    scene.add(SceneNode(name="Navigation", parent="Gameplay"))
    scene.add(SceneNode(name="NavMesh", type="NavigationRegion3D", parent="Gameplay/Navigation",
                        metadata={"dispatch_generated": True, "bake_required": True,
                                  "navgraph_file": f"{res}/nav/navgraph.json"}))
    scene.add(SceneNode(name="NavRegions", parent="Gameplay/Navigation"))
    scene.add(SceneNode(name="NavLinks", parent="Gameplay/Navigation"))

    for a in ctx.anchors:
        path = node_path_for(a)
        parent, name = path.rsplit("/", 1)
        md = {
            "dispatch_generated": True,
            "anchor_type": a.type,
            "source": a.source,
            "authority": authority_for(a),
        }
        if a.net_id:
            md["net_id"] = a.net_id
        if a.tags:
            md["tags"] = list(a.tags)
        if a.objective:
            md["objective"] = a.objective
        scene.add(SceneNode(name=name, type="Marker3D", parent=parent,
                            pos=a.pos, rot_y=a.rot_y, metadata=md))

    # -- Runtime ---------------------------------------------------------------
    scene.add(SceneNode(name="Runtime", parent="."))
    cfg_id = ext("Resource", "mission_config.tres", "cfg")
    run_id = ext("Script", "mission_runtime.gd", "runtime")
    for n in RUNTIME_NODES:
        node = SceneNode(name=n, type="Node", parent="Runtime",
                         metadata={"dispatch_generated": True,
                                   "authority": "client" if n == "DebugOverlay" else "server"})
        if n == "MissionController":
            node.script = run_id
            node.props["mission_config"] = Raw(f'ExtResource("{cfg_id}")')
        if n == "ReplicationRegistry":
            node.metadata["registry_file"] = f"{res}/network_authority_map.json"
        scene.add(node)

    return scene


def _add_props(ctx: BuildContext, scene: Scene, ext) -> None:
    """Instantiate prop placements from DC/Lot against the Zoo catalog."""
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
        from .anchors import blender_to_godot
        raw = p.get("pos", (0, 0, 0))
        pos = blender_to_godot(raw)
        md = {"dispatch_generated": True, "asset_id": aid, "source": tool}
        glb = (props_dir / f"{aid}.glb") if props_dir else None
        if glb and glb.is_file():
            eid = ext("PackedScene", f"assets/props/{aid}.glb", f"prop_{aid}")
            node = SceneNode(name=name, parent="World/PropsRoot", instance=eid,
                             pos=pos, rot_y=float(p.get("rot_y", 0.0)), metadata=md)
        else:
            md["missing_asset"] = True
            node = SceneNode(name=name, type="Marker3D", parent="World/PropsRoot",
                             pos=pos, rot_y=float(p.get("rot_y", 0.0)), metadata=md)
        meta = catalog.get(aid, {})
        if meta.get("gameplay_tags"):
            md["gameplay_tags"] = list(meta["gameplay_tags"])
        scene.add(node)


# --- package export -----------------------------------------------------------


def default_out_dir(spec: MissionSpec) -> Path:
    return spec.spec_dir / "export" / "godot" / "missions" / spec.mission_id


def export_package(ctx: BuildContext, scene: Scene, out_dir: Path) -> dict:
    """Write the mission package. Returns the manifest dict."""
    spec = ctx.spec
    out_dir.mkdir(parents=True, exist_ok=True)
    assets = out_dir / "assets"
    assets.mkdir(exist_ok=True)

    copied = []

    def copy(src: Path, rel: str) -> None:
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied.append(rel)

    if "deli_counter" in ctx.imports:
        copy(ctx.imports["deli_counter"].meta["glb"], "assets/shell.glb")
    if "lot" in ctx.imports:
        copy(ctx.imports["lot"].meta["glb"], "assets/lot.glb")
    if "patina" in ctx.imports:
        copy(ctx.imports["patina"].meta["glb"], "assets/shell.patina.glb")
        tex = ctx.imports["patina"].files.get("textures")
        if tex and tex.is_dir():
            shutil.copytree(tex, assets / "textures", dirs_exist_ok=True)
            copied.append("assets/textures/")
    if "lux" in ctx.imports:
        for name, path in sorted(ctx.imports["lux"].files.items()):
            if path.is_file():
                copy(path, f"assets/lux/{name}")
    zoo = ctx.imports.get("zoo")
    if zoo and zoo.meta.get("props_dir"):
        used = {str(p.get("asset_id")) for t in ("deli_counter", "lot") if t in ctx.imports
                for p in ctx.imports[t].props}
        for aid in sorted(used):
            glb = zoo.meta["props_dir"] / f"{aid}.glb"
            if glb.is_file():
                copy(glb, f"assets/props/{aid}.glb")

    # scene + scripts + config
    (out_dir / "mission.tscn").write_text(serialize(scene), encoding="utf-8")
    _write_gd(out_dir, "mission_runtime.gd", "mission_runtime.gd.tpl", spec)
    _write_gd(out_dir, "mission_config.gd", "mission_config.gd.tpl", spec)
    (out_dir / "mission_config.tres").write_text(_config_tres(ctx), encoding="utf-8")

    # authority + nav data
    (out_dir / "network_authority_map.json").write_text(
        json.dumps(ctx.authority, indent=2) + "\n", encoding="utf-8")
    nav_dir = out_dir / "nav"
    nav_dir.mkdir(exist_ok=True)
    (nav_dir / "navgraph.json").write_text(
        json.dumps(ctx.nav.to_json(), indent=2) + "\n", encoding="utf-8")
    (nav_dir / "cover_points.json").write_text(
        json.dumps(_anchor_dump(ctx, "cover"), indent=2) + "\n", encoding="utf-8")
    (nav_dir / "ai_routes.json").write_text(
        json.dumps(_anchor_dump(ctx, "patrol_point"), indent=2) + "\n", encoding="utf-8")

    write_lock_file(spec, ctx.resolved, out_dir)

    manifest = {
        "schema": "dispatch.manifest.v0.1",
        "dispatch_version": __version__,
        "marker": GENERATED_MARKER,
        "mission_id": spec.mission_id,
        "title": spec.title,
        "engine": spec.engine,
        "mode": spec.mode,
        "players": {"min": spec.players_min, "max": spec.players_max,
                    "preferred": spec.players_preferred},
        "networking": {"model": spec.net_model},
        "res_root": ctx.res_root,
        "inputs": {t: rt.schema for t, rt in sorted(ctx.resolved.tools.items())},
        "flow": ctx.flow.to_json(),
        "anchor_counts": _anchor_counts(ctx),
        "files": sorted(copied) + [
            "mission.tscn", "mission_config.gd", "mission_config.tres",
            "mission_runtime.gd", "network_authority_map.json",
            "nav/navgraph.json", "nav/cover_points.json", "nav/ai_routes.json",
            "build.lock.json",
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


def _anchor_dump(ctx: BuildContext, kind: str) -> dict:
    return {
        "schema": f"dispatch.{kind}.v0.1",
        "items": [
            {"id": a.id, "pos": list(a.pos), "rot_y": a.rot_y,
             "tags": list(a.tags), "source": a.source}
            for a in ctx.anchors if a.type == kind
        ],
    }


def _write_gd(out_dir: Path, name: str, tpl: str, spec: MissionSpec) -> None:
    text = (GD_DIR / tpl).read_text(encoding="utf-8")
    text = text.replace("{version}", __version__).replace("{mission_id}", spec.mission_id)
    text = text.replace("{{}}", "{}")
    (out_dir / name).write_text(text, encoding="utf-8")


def _config_tres(ctx: BuildContext) -> str:
    from .tscn import _gd_value
    spec = ctx.spec
    flow = ctx.flow.to_json()
    steps = [
        {"name": s["name"], "state": s["state"], "objective": s["objective"],
         "trigger": s["trigger"], "anchor_ids": s["anchor_ids"]}
        for s in flow["steps"]
    ]
    lines = [
        "[gd_resource type=\"Resource\" load_steps=2 format=3]",
        "",
        f'[ext_resource type="Script" path="{ctx.res_root}/mission_config.gd" id="1_cfg"]',
        "",
        "[resource]",
        'script = ExtResource("1_cfg")',
        f'mission_id = {_gd_value(spec.mission_id)}',
        f'title = {_gd_value(spec.title)}',
        f'mode = {_gd_value(spec.mode)}',
        f'net_model = {_gd_value(spec.net_model)}',
        f'players_min = {spec.players_min}',
        f'players_max = {spec.players_max}',
        f'states = {_gd_value(flow["states"])}',
        f'steps = {_gd_value(steps)}',
    ]
    return "\n".join(lines) + "\n"
