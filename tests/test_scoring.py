"""Unit tests for the scoring math in results.py (spec §11)."""

import pytest

from mcpdoctor.doctor.results import (
    CheckResult,
    category_scores,
    letter_grade,
    overall_score,
)


def make(category: str, score: int, check_id: str = "T2") -> CheckResult:
    return CheckResult(
        id=check_id,
        name="synthetic",
        category=category,
        target="x",
        score=score,
        max_score=2,
        severity="info",
        message="",
    )


def test_category_percent_is_points_over_max():
    results = [make("tool_clarity", 2), make("tool_clarity", 1), make("tool_clarity", 0)]
    assert category_scores(results)["tool_clarity"] == pytest.approx(50.0)


def test_category_without_results_is_na():
    assert category_scores([make("safety", 2)])["resources"] is None


def test_na_categories_redistribute_weight():
    # tool_clarity at 100% (weight 25) + safety at 50% (weight 15);
    # everything else n/a -> overall = (100*25 + 50*15) / (25+15) = 81.25
    results = [make("tool_clarity", 2), make("safety", 1, "T5")]
    assert overall_score(results) == pytest.approx(81.25)


def test_all_categories_present_uses_full_weights():
    results = [
        make("error_quality", 2),
        make("tool_clarity", 2),
        make("safety", 2),
        make("resources", 2),
        make("protocol_hygiene", 2),
        make("spec_extras", 2),
    ]
    assert overall_score(results) == pytest.approx(100.0)


def test_no_results_scores_zero():
    assert overall_score([]) == 0.0


def test_unknown_category_raises():
    with pytest.raises(ValueError, match="unknown category"):
        category_scores([make("made_up_category", 2)])


@pytest.mark.parametrize(
    ("score", "grade"),
    [
        (100, "A"),
        (90, "A"),
        (89.9, "B"),
        (75, "B"),
        (74.9, "C"),
        (60, "C"),
        (59.9, "D"),
        (45, "D"),
        (44.9, "F"),
        (0, "F"),
    ],
)
def test_letter_grade_boundaries(score: float, grade: str):
    assert letter_grade(score) == grade
