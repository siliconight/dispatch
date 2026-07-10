"""Mission Flow Compiler (TDD 13.4).

Converts the mission spec's flow list into runtime objective logic:
PRE_MISSION -> <steps...> -> COMPLETE, with each step bound to the anchors
that satisfy it. Binding is by objective key first, then by location tag.
Dispatch creates the flow from the spec and binds it to anchors placed by
Deli Counter and Lot (TDD open question 2 — resolved: spec drives flow,
upstream tools place anchors).
"""

from __future__ import annotations

from dataclasses import dataclass, field

TERMINALS = ("PRE_MISSION", "COMPLETE")


@dataclass
class FlowStep:
    name: str            # e.g. "loot"
    state: str           # e.g. "LOOT"
    objective: str = ""  # objective key to satisfy
    location_tag: str = ""
    trigger: str = ""    # event key that advances this step
    anchor_ids: tuple = ()   # anchors bound to this step


@dataclass
class CompiledFlow:
    steps: list = field(default_factory=list)
    unbound: list = field(default_factory=list)   # step names with no anchor

    @property
    def states(self) -> list:
        return ["PRE_MISSION"] + [s.state for s in self.steps] + ["COMPLETE"]

    def to_json(self) -> dict:
        return {
            "schema": "dispatch.flow.v0.1",
            "states": self.states,
            "steps": [
                {
                    "name": s.name,
                    "state": s.state,
                    "objective": s.objective,
                    "location_tag": s.location_tag,
                    "trigger": s.trigger,
                    "anchor_ids": list(s.anchor_ids),
                }
                for s in self.steps
            ],
        }


def _binds(step: FlowStep, anchor) -> bool:
    if step.objective and anchor.objective == step.objective:
        return True
    if step.objective and step.objective in anchor.tags:
        return True
    if step.location_tag and (step.location_tag in anchor.tags or anchor.id == step.location_tag):
        return True
    return False


def compile_flow(spec_flow: list, anchors: list) -> CompiledFlow:
    out = CompiledFlow()
    for raw in spec_flow:
        step = FlowStep(
            name=str(raw["step"]),
            state=str(raw["step"]).upper(),
            objective=str(raw.get("objective", "")),
            location_tag=str(raw.get("location_tag", "")),
            trigger=str(raw.get("trigger", "")),
        )
        bound = sorted(a.id for a in anchors if _binds(step, a))
        step.anchor_ids = tuple(bound)
        # A pure trigger step (e.g. dangerous_mode) needs no anchor.
        if not bound and not step.trigger:
            out.unbound.append(step.name)
        out.steps.append(step)
    return out
