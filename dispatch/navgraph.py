"""Navigation graph built from upstream nav hints.

Dispatch does not bake geometry navmeshes in v0.1 (heavy geometry work is a
later, optional native layer — TDD 23). It reasons over the nav-hint graphs
that Deli Counter and Lot already export: nodes with positions, links between
them. That is enough for reachability, island detection, and anchor binding,
and it is deterministic.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from .anchors import blender_to_godot


@dataclass
class NavNode:
    id: str
    pos: tuple      # Godot-space
    source: str


@dataclass
class NavGraph:
    nodes: dict = field(default_factory=dict)   # id -> NavNode
    adj: dict = field(default_factory=dict)     # id -> set(id)
    bridges: list = field(default_factory=list)  # auto-added cross-source links

    def add_node(self, node: NavNode) -> None:
        self.nodes[node.id] = node
        self.adj.setdefault(node.id, set())

    def add_link(self, a: str, b: str) -> None:
        if a in self.nodes and b in self.nodes and a != b:
            self.adj[a].add(b)
            self.adj[b].add(a)

    # -- queries ------------------------------------------------------------

    def nearest(self, pos, max_dist: float):
        """Nearest node id within max_dist of pos, else None."""
        best, best_d = None, max_dist
        for n in self.nodes.values():
            d = _dist(pos, n.pos)
            if d <= best_d:
                best, best_d = n.id, d
        return best

    def reachable(self, a: str, b: str) -> bool:
        if a not in self.nodes or b not in self.nodes:
            return False
        if a == b:
            return True
        seen = {a}
        q = deque([a])
        while q:
            cur = q.popleft()
            for nxt in self.adj[cur]:
                if nxt == b:
                    return True
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        return False

    def islands(self) -> list:
        """Connected components, sorted largest first (then by min node id)."""
        seen = set()
        comps = []
        for nid in sorted(self.nodes):
            if nid in seen:
                continue
            comp = []
            q = deque([nid])
            seen.add(nid)
            while q:
                cur = q.popleft()
                comp.append(cur)
                for nxt in self.adj[cur]:
                    if nxt not in seen:
                        seen.add(nxt)
                        q.append(nxt)
            comps.append(sorted(comp))
        comps.sort(key=lambda c: (-len(c), c[0]))
        return comps

    def bounds(self):
        """((min_x, min_z), (max_x, max_z)) over node positions."""
        if not self.nodes:
            return ((0.0, 0.0), (0.0, 0.0))
        xs = [n.pos[0] for n in self.nodes.values()]
        zs = [n.pos[2] for n in self.nodes.values()]
        return ((min(xs), min(zs)), (max(xs), max(zs)))

    def to_json(self, bridge_radius: float = 0.0) -> dict:
        bridged = {tuple(sorted(b)) for b in self.bridges}
        edges = []
        for pair in sorted({tuple(sorted([a, b]))
                            for a in self.adj for b in self.adj[a] if a != b}):
            e = {"nodes": list(pair), "bridged": pair in bridged}
            if e["bridged"] and bridge_radius:
                e["bridge_radius"] = bridge_radius
            edges.append(e)
        return {
            "schema": "dispatch.navigation_hints.v0.2",
            "navmesh": "bake_required",
            "nodes": [
                {"id": n.id, "pos": list(n.pos), "source": n.source}
                for n in sorted(self.nodes.values(), key=lambda n: n.id)
            ],
            "edges": edges,
        }


def _dist(a, b) -> float:
    return math.dist((a[0], a[1], a[2]), (b[0], b[1], b[2]))


def load_nav_hints(data: dict, source: str, up_axis: str = "z") -> NavGraph:
    """Load one tool's nav_hints JSON.

    Expected shape (docs/FORMATS.md):
      {"schema": "...", "nodes": [{"id": "n1", "pos": [x,y,z]}], "links": [["n1","n2"]]}
    Node ids are namespaced with the source to avoid collisions on merge.
    """
    g = NavGraph()
    for rec in data.get("nodes", []):
        raw = rec.get("pos", (0.0, 0.0, 0.0))
        pos = blender_to_godot(raw) if up_axis == "z" else tuple(float(v) for v in raw)
        g.add_node(NavNode(id=f"{source}:{rec['id']}", pos=pos, source=source))
    for a, b in data.get("links", []):
        g.add_link(f"{source}:{a}", f"{source}:{b}")
    return g


def merge(graphs: list, bridge_radius: float) -> NavGraph:
    """Merge graphs; auto-bridge nodes from different sources within
    bridge_radius so DC interiors connect to Lot exteriors at shared thresholds.
    Bridges are recorded so the report can surface them (no hidden assumptions).
    """
    merged = NavGraph()
    for g in graphs:
        for n in g.nodes.values():
            merged.add_node(n)
        for a in g.adj:
            for b in g.adj[a]:
                merged.add_link(a, b)
    nodes = sorted(merged.nodes.values(), key=lambda n: n.id)
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if a.source != b.source and _dist(a.pos, b.pos) <= bridge_radius:
                if b.id not in merged.adj[a.id]:
                    merged.add_link(a.id, b.id)
                    merged.bridges.append([a.id, b.id])
    return merged
