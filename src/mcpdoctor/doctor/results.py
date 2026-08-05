"""CheckResult contract and scoring model (spec §1, §11).

n/a convention: a check that does not apply (e.g. P2 on a server with no
prompts) emits no CheckResult at all. A category with zero results is n/a,
and its weight is redistributed proportionally across the categories that
do have results — a pure tool server isn't punished for having no resources.
"""

from dataclasses import dataclass


@dataclass
class CheckResult:
    id: str              # "T4"
    name: str            # "Error repairability"
    category: str        # "error_quality"
    target: str          # tool/resource/prompt name, or "server"
    score: int           # 0, 1, or 2
    max_score: int       # always 2
    severity: str        # "info" | "warn" | "fail"
    message: str         # what was found
    fix_hint: str | None = None  # concrete suggestion, shown in report
    server: str | None = None  # owning server; renderers qualify target on
                               # multi-server runs (report.display_target)


CATEGORY_WEIGHTS: dict[str, int] = {
    "error_quality": 30,
    "tool_clarity": 25,
    "safety": 15,
    "resources": 15,
    "protocol_hygiene": 10,
    "spec_extras": 5,
}


def category_scores(results: list[CheckResult]) -> dict[str, float | None]:
    """Percent score per category. None means n/a (no check produced results)."""
    points: dict[str, int] = {c: 0 for c in CATEGORY_WEIGHTS}
    maxes: dict[str, int] = {c: 0 for c in CATEGORY_WEIGHTS}
    for r in results:
        if r.category not in CATEGORY_WEIGHTS:
            raise ValueError(f"check {r.id} reported unknown category {r.category!r}")
        points[r.category] += r.score
        maxes[r.category] += r.max_score
    return {
        c: (100.0 * points[c] / maxes[c]) if maxes[c] else None
        for c in CATEGORY_WEIGHTS
    }


def overall_score(results: list[CheckResult]) -> float:
    """Weighted 0-100 score with n/a categories' weight redistributed."""
    scores = category_scores(results)
    present = {c: w for c, w in CATEGORY_WEIGHTS.items() if scores[c] is not None}
    if not present:
        return 0.0
    total_weight = sum(present.values())
    return sum(scores[c] * w for c, w in present.items()) / total_weight


def letter_grade(score: float) -> str:
    """A >= 90, B >= 75, C >= 60, D >= 45, F below (spec §11)."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    return "F"
