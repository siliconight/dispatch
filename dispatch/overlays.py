"""Debug overlay PNGs (TDD 10): top-down plots of nav, spawns, objectives,
cover. Stdlib-only PNG writer (zlib + struct) — no imaging dependency.

World top-down: image x = Godot +X, image y = Godot +Z.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from .anchors import by_type

BG = (24, 26, 30)
NAV_NODE = (90, 200, 250)
NAV_LINK = (60, 90, 110)
BRIDGE = (250, 200, 90)
COLORS = {
    "player_start": (80, 220, 120),
    "ai_spawn": (235, 80, 80),
    "objective": (250, 210, 60),
    "extraction": (170, 120, 255),
    "cover": (200, 200, 200),
    "patrol_point": (240, 140, 60),
    "loot": (255, 170, 200),
    "door": (120, 170, 220),
    "trigger": (140, 220, 220),
}


class Canvas:
    def __init__(self, w: int, h: int, bg=BG):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * w * h)

    def set(self, x: int, y: int, c) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def disc(self, x: int, y: int, r: int, c) -> None:
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    self.set(x + dx, y + dy, c)

    def line(self, x0: int, y0: int, x1: int, y1: int, c) -> None:
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def png_bytes(self) -> bytes:
        raw = b"".join(
            b"\x00" + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3])
            for y in range(self.h)
        )

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data)))

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


class Projector:
    def __init__(self, ctx, size: int = 1024, pad: int = 48):
        (min_x, min_z), (max_x, max_z) = ctx.nav.bounds()
        xs = [a.pos[0] for a in ctx.anchors] + [min_x, max_x]
        zs = [a.pos[2] for a in ctx.anchors] + [min_z, max_z]
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_z, self.max_z = min(zs), max(zs)
        span = max(self.max_x - self.min_x, self.max_z - self.min_z, 1.0)
        self.scale = (size - 2 * pad) / span
        self.pad = pad
        self.w = int((self.max_x - self.min_x) * self.scale) + 2 * pad
        self.h = int((self.max_z - self.min_z) * self.scale) + 2 * pad

    def to_px(self, pos):
        x = int((pos[0] - self.min_x) * self.scale) + self.pad
        y = int((pos[2] - self.min_z) * self.scale) + self.pad
        return x, y


def _nav_backdrop(ctx, proj: Projector, canvas: Canvas) -> None:
    bridge_pairs = {tuple(sorted(b)) for b in ctx.nav.bridges}
    drawn = set()
    for a in ctx.nav.adj:
        for b in ctx.nav.adj[a]:
            key = tuple(sorted((a, b)))
            if key in drawn:
                continue
            drawn.add(key)
            pa, pb = ctx.nav.nodes[a].pos, ctx.nav.nodes[b].pos
            color = BRIDGE if key in bridge_pairs else NAV_LINK
            canvas.line(*proj.to_px(pa), *proj.to_px(pb), color)
    for n in ctx.nav.nodes.values():
        canvas.disc(*proj.to_px(n.pos), 2, NAV_NODE)


def _plot_anchor_types(ctx, proj, canvas, types, radius=5) -> None:
    for t in types:
        for a in by_type(ctx.anchors, t):
            canvas.disc(*proj.to_px(a.pos), radius, COLORS.get(t, (255, 255, 255)))


def write_overlays(ctx, out_dir: Path) -> list:
    odir = out_dir / "validation" / "overlays"
    odir.mkdir(parents=True, exist_ok=True)
    proj = Projector(ctx)
    written = []

    def emit(name: str, canvas: Canvas) -> None:
        p = odir / name
        p.write_bytes(canvas.png_bytes())
        written.append(p)

    # nav overlay
    c = Canvas(proj.w, proj.h)
    _nav_backdrop(ctx, proj, c)
    emit("nav_overlay.png", c)

    # spawn overlay
    c = Canvas(proj.w, proj.h)
    _nav_backdrop(ctx, proj, c)
    _plot_anchor_types(ctx, proj, c, ("player_start", "ai_spawn"))
    emit("spawn_overlay.png", c)

    # objective flow overlay: numbered beats connected in order
    c = Canvas(proj.w, proj.h)
    _nav_backdrop(ctx, proj, c)
    anchors_by_id = {a.id: a for a in ctx.anchors}
    prev = None
    for step in ctx.flow.steps:
        pts = [anchors_by_id[i] for i in step.anchor_ids if i in anchors_by_id]
        if not pts:
            continue
        cur = proj.to_px(pts[0].pos)
        if prev:
            c.line(*prev, *cur, (250, 210, 60))
        for a in pts:
            color = COLORS.get(a.type, (250, 210, 60))
            c.disc(*proj.to_px(a.pos), 6, color)
        prev = cur
    _plot_anchor_types(ctx, proj, c, ("player_start",), radius=4)
    emit("objective_flow.png", c)

    # cover overlay
    c = Canvas(proj.w, proj.h)
    _nav_backdrop(ctx, proj, c)
    _plot_anchor_types(ctx, proj, c, ("cover",), radius=3)
    _plot_anchor_types(ctx, proj, c, ("ai_spawn", "player_start"), radius=4)
    emit("cover_overlay.png", c)

    return written
