"""Proposed Beat Graph compiler (handoff spec section 6).

Converts the mission spec's flow list into a proposed beat graph: design
intent, not runtime state. Each beat binds to the shell anchors that express
it; connections record intended sequencing. The production game decides
whether a beat is valid, when it completes, which peer may report it, whether
the server accepts it, how completion replicates, and how reconnecting
players receive state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

BEAT_TYPES = ("location", "objective", "extraction", "trigger", "carry")


@dataclass
class Beat:
    id: str               # step name from the spec
    type: str             # location | objective | extraction | trigger | carry
    objective: str = ""
    location_tag: str = ""
    trigger: str = ""
    anchor_ids: tuple = ()   # shell ids bound to this beat


@dataclass
class BeatGraph:
    graph_id: str = ""
    beats: list = field(default_factory=list)
    connections: list = field(default_factory=list)   # [from_id, to_id]
    unbound: list = field(default_factory=list)        # beat ids with no anchor

    def to_json(self) -> dict:
        return {
            "schema": "dispatch.proposed_beat_graph.v0.2",
            "graph_id": self.graph_id,
            "statement": ("Proposed mission sequencing. Design intent only — "
                          "the production runtime owns beat validity, "
                          "completion, and replication."),
            "beats": [
                {
                    "id": b.id,
                    "type": b.type,
                    "status": "proposed",
                    "objective": b.objective,
                    "location_tag": b.location_tag,
                    "trigger": b.trigger,
                    "shell_ids": [f"{self.graph_id}/{a}" for a in b.anchor_ids],
                }
                for b in self.beats
            ],
            "connections": [list(c) for c in self.connections],
        }


def _binds(beat: Beat, anchor) -> bool:
    if beat.objective and anchor.objective == beat.objective:
        return True
    if beat.objective and beat.objective in anchor.tags:
        return True
    if beat.location_tag and (beat.location_tag in anchor.tags or anchor.id == beat.location_tag):
        return True
    return False


def _beat_type(raw: dict, bound_anchors: list) -> str:
    declared = str(raw.get("type", ""))
    if declared in BEAT_TYPES:
        return declared
    if raw.get("trigger"):
        return "trigger"
    if any(a.type == "extraction" for a in bound_anchors):
        return "extraction"
    if raw.get("objective"):
        return "objective"
    return "location"


def compile_beats(spec_flow: list, anchors: list, graph_id: str) -> BeatGraph:
    graph = BeatGraph(graph_id=graph_id)
    for raw in spec_flow:
        beat = Beat(
            id=str(raw["step"]),
            type="location",
            objective=str(raw.get("objective", "")),
            location_tag=str(raw.get("location_tag", "")),
            trigger=str(raw.get("trigger", "")),
        )
        bound = sorted((a for a in anchors if _binds(beat, a)), key=lambda a: a.id)
        beat.anchor_ids = tuple(a.id for a in bound)
        beat.type = _beat_type(raw, bound)
        # A pure trigger beat (e.g. dangerous_mode) needs no anchor.
        if not beat.anchor_ids and not beat.trigger:
            graph.unbound.append(beat.id)
        graph.beats.append(beat)
    graph.connections = [
        [a.id, b.id] for a, b in zip(graph.beats, graph.beats[1:])
    ]
    return graph
