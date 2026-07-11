"""Structural assembly checks: anchors exist, flow binds, ids are unique."""

from __future__ import annotations

from ..anchors import ANCHOR_TYPES, by_type
from . import Issue


def validate(ctx) -> list:
    issues = []
    if ctx.duplicate_anchor_ids:
        for aid in sorted(set(ctx.duplicate_anchor_ids)):
            issues.append(Issue(
                "blocker", "assembly",
                f"Anchor id {aid!r} appears more than once across upstream inputs.",
                "Rename the anchor in the Deli Counter or Lot export so ids are unique.",
            ))
    for w in ctx.warnings:
        issues.append(Issue("info", "assembly", w))
    for beat in ctx.beats.unbound:
        issues.append(Issue(
            "blocker", "assembly",
            f"Proposed beat {beat!r} binds to no anchor and has no trigger.",
            "Add a matching objective/tag on an upstream anchor, or give the beat a trigger.",
        ))
    if not by_type(ctx.anchors, "player_start"):
        issues.append(Issue(
            "blocker", "assembly",
            "No player_start anchors were found in any input.",
            "Export player starts from Deli Counter or Lot gameplay data.",
        ))
    if not by_type(ctx.anchors, "objective"):
        issues.append(Issue(
            "blocker", "assembly",
            "No objective anchors were found in any input.",
            "Export at least one objective anchor, or the mission has nothing to do.",
        ))
    if not by_type(ctx.anchors, "extraction"):
        issues.append(Issue(
            "major", "assembly",
            "No extraction anchor was found; the mission cannot end at an extraction point.",
            "Add an extraction anchor in Lot (escape vehicle, alley exit).",
        ))
    unknown = sorted({a.type for a in ctx.anchors} - set(ANCHOR_TYPES))
    for t in unknown:
        issues.append(Issue(
            "info", "assembly",
            f"Anchor type {t!r} is not a known Dispatch anchor type; nodes were created but not validated.",
        ))
    if ctx.nav.bridges:
        issues.append(Issue(
            "info", "assembly",
            f"{len(ctx.nav.bridges)} nav bridge link(s) were auto-added between the Deli Counter and Lot nav graphs (within {ctx.spec.tuning['nav_bridge_radius']}m).",
            "Verify thresholds line up; export shared boundary nodes to avoid auto-bridging.",
        ))
    return issues
