"""Mission Readiness Score (TDD 16).

Structural readiness only. This is not a fun score — fun is a feel property
and offline fun-scores are confidently wrong. The score reflects whether the
mission is assembled, connected, network-safe, and inside budget.
"""

from __future__ import annotations

# validator system -> score category
CATEGORY_OF = {
    "assembly": "assembly",
    "objective_reachability": "objective_flow",
    "online_runtime": "online_runtime",
    "ai_nav": "ai_readiness",
    "multiplayer_spawns": "multiplayer",
    "performance": "performance",
}

CATEGORIES = ("assembly", "objective_flow", "online_runtime",
              "ai_readiness", "multiplayer", "performance")

PENALTY = {"blocker": 60, "major": 25, "moderate": 10, "minor": 3, "info": 0}

STATUS_BANDS = (
    (90, "ready_for_review"),
    (75, "ready_for_playtest"),
    (60, "playable_with_major_issues"),
    (40, "prototype_only"),
    (0, "broken"),
)


def compute(issues: list) -> dict:
    scores = {c: 100 for c in CATEGORIES}
    for issue in issues:
        cat = CATEGORY_OF.get(issue.system)
        if cat:
            scores[cat] = max(0, scores[cat] - PENALTY[issue.severity])

    overall = round(sum(scores.values()) / len(scores))
    # Severity caps: averages must not hide critical issues.
    if any(i.severity == "blocker" for i in issues):
        overall = min(overall, 59)   # never playtest-ready with a blocker
    elif any(i.severity == "major" for i in issues):
        overall = min(overall, 89)   # never review-ready with a major issue

    status = "broken"
    for floor, name in STATUS_BANDS:
        if overall >= floor:
            status = name
            break

    return {
        "mission_readiness": overall,
        "status": status,
        "scores": dict(scores),
    }
