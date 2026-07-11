"""Validation framework (TDD 13.5-13.11, 15).

Validators never mutate the mission — they report (TDD 2). Each returns a
list of Issues with severity, system, message, and a suggested fix.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SEVERITIES = ("blocker", "major", "moderate", "minor", "info")


@dataclass
class Issue:
    severity: str
    system: str
    message: str
    suggested_fix: str = ""
    node: str = ""

    def to_json(self) -> dict:
        d = {"severity": self.severity, "system": self.system, "message": self.message}
        if self.suggested_fix:
            d["suggested_fix"] = self.suggested_fix
        if self.node:
            d["node"] = self.node
        return d


def issues_by_severity(issues: list) -> dict:
    out = {s: [] for s in SEVERITIES}
    for i in issues:
        out[i.severity].append(i)
    return out


from . import assembly, integration, nav, performance, reachability, spawns  # noqa: E402

# (system name, validator function, gate flag in spec.validation or None)
VALIDATORS = (
    ("assembly", assembly.validate, None),
    ("integration_readiness", integration.validate, "require_online_runtime_readiness"),
    ("multiplayer_spawns", spawns.validate, "require_all_players_spawn_valid"),
    ("objective_reachability", reachability.validate, "require_all_objectives_reachable"),
    ("ai_nav", nav.validate, "require_ai_navmesh"),
    ("performance", performance.validate, "require_performance_budget"),
)


def run_all(ctx) -> list:
    issues = []
    for _name, fn, gate in VALIDATORS:
        if gate is not None and not ctx.spec.validation.get(gate, True):
            continue
        issues.extend(fn(ctx))
    order = {s: i for i, s in enumerate(SEVERITIES)}
    issues.sort(key=lambda i: (order[i.severity], i.system, i.message))
    return issues
