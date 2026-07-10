"""Minimal deterministic Godot 4 .tscn writer.

Only what Dispatch needs: Node3D hierarchies, Marker3D anchors, GLB scene
instances, script attachment, transforms, and metadata properties. Output is
format=3 (Godot 4.x) and byte-stable across rebuilds with unchanged inputs
(TDD 21: repeatable builds).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Raw:
    """Verbatim tscn value, e.g. Raw('ExtResource("2_cfg")')."""
    text: str


@dataclass
class ExtResource:
    rtype: str   # "PackedScene", "Script", ...
    path: str    # res:// path
    id: str      # e.g. "1_shell"


@dataclass
class SceneNode:
    name: str
    type: str = "Node3D"          # ignored when instance is set
    parent: str = ""              # "" = root, "." = child of root, else path
    instance: str = ""            # ExtResource id for instanced scenes
    script: str = ""              # ExtResource id for attached script
    pos: tuple = None             # (x, y, z) Godot space
    rot_y: float = 0.0            # degrees
    props: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass
class Scene:
    root_name: str
    ext_resources: list = field(default_factory=list)
    nodes: list = field(default_factory=list)   # root first, document order

    def add_ext(self, rtype: str, path: str, id_: str) -> str:
        self.ext_resources.append(ExtResource(rtype, path, id_))
        return id_

    def add(self, node: SceneNode) -> SceneNode:
        self.nodes.append(node)
        return node

    def node_path(self, node: SceneNode) -> str:
        if node.parent == "":
            return "."
        if node.parent == ".":
            return node.name
        return f"{node.parent}/{node.name}"


def _gd_value(v) -> str:
    if isinstance(v, Raw):
        return v.text
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return _f(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_gd_value(x) for x in v) + "]"
    if isinstance(v, dict):
        items = ", ".join(f"{_gd_value(str(k))}: {_gd_value(val)}" for k, val in sorted(v.items()))
        return "{" + items + "}"
    raise TypeError(f"cannot serialize {type(v)} to tscn")


def _f(x: float) -> str:
    if abs(x) < 1e-12:
        x = 0.0
    s = f"{x:.6g}"
    return s


def _transform(pos, rot_y_deg: float) -> str:
    """Transform3D from yaw + origin."""
    r = math.radians(rot_y_deg)
    c, s = math.cos(r), math.sin(r)
    basis = [c, 0.0, s, 0.0, 1.0, 0.0, -s, 0.0, c]
    origin = list(pos)
    vals = ", ".join(_f(v) for v in basis + origin)
    return f"Transform3D({vals})"


def serialize(scene: Scene) -> str:
    lines = []
    load_steps = len(scene.ext_resources) + 1
    lines.append(f'[gd_scene load_steps={load_steps} format=3]')
    lines.append("")
    for er in scene.ext_resources:
        lines.append(f'[ext_resource type="{er.rtype}" path="{er.path}" id="{er.id}"]')
    if scene.ext_resources:
        lines.append("")
    for node in scene.nodes:
        head = f'[node name="{node.name}"'
        if node.instance:
            head += f' parent="{node.parent}" instance=ExtResource("{node.instance}")'
        else:
            head += f' type="{node.type}"'
            if node.parent:
                head += f' parent="{node.parent}"'
        head += "]"
        lines.append(head)
        if node.script:
            lines.append(f'script = ExtResource("{node.script}")')
        if node.pos is not None or node.rot_y:
            lines.append(f"transform = {_transform(node.pos or (0, 0, 0), node.rot_y)}")
        for k in sorted(node.props):
            lines.append(f"{k} = {_gd_value(node.props[k])}")
        for k in sorted(node.metadata):
            lines.append(f"metadata/{k} = {_gd_value(node.metadata[k])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
