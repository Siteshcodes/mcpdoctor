"""Ruling on record (Phase 3 kickoff): n/a-category rendering must stay
covered by the DEFAULT suite. badserver exercises every category since
Phase 2, so a synthetic pure-tool manifest covers the n/a display path."""

import re

from mcpdoctor.doctor.manifest import Manifest, ServerManifest
from mcpdoctor.doctor.report import (
    display_target,
    render_fixes,
    render_markdown,
    render_rich,
    render_text,
    top_fixes,
)
from mcpdoctor.doctor.results import CheckResult


def _result(category: str, score: int, check_id: str) -> CheckResult:
    return CheckResult(
        id=check_id,
        name="synthetic",
        category=category,
        target="server",
        score=score,
        max_score=2,
        severity="info",
        message="synthetic",
    )


def test_categories_without_results_render_as_na():
    manifest = Manifest(
        servers=[
            ServerManifest(
                name="pure-tools",
                server_info_name="pure-tools",
                capabilities=None,
                instructions=None,
            )
        ]
    )
    results = [_result("tool_clarity", 2, "T2"), _result("safety", 1, "T5")]
    text = render_text(manifest, results)

    assert re.search(r"Resources\s+n/a", text)
    assert re.search(r"Error Quality\s+n/a", text)
    assert re.search(r"Spec Extras\s+n/a", text)
    # present categories show percentages, not n/a
    assert re.search(r"Tool Clarity\s+100%", text)
    assert re.search(r"Safety\s+50%", text)


def test_single_server_targets_stay_unqualified():
    r = _result("safety", 0, "T5")
    r = CheckResult(**{**r.__dict__, "target": "delete_it", "server": "s"})
    assert display_target(r, multi=False) == "delete_it"
    assert display_target(r, multi=True) == "s:delete_it"


def test_collision_run_renders_server_qualified_targets(collision_run):
    manifest, results = collision_run
    text = render_text(manifest, results)
    # both servers expose `search`; the report must disambiguate which is which
    assert "badserver:search" in text
    assert "otherserver:search" in text


def test_server_equal_target_is_not_doubled():
    # server-level findings (target == server.name) must not become "s:s"
    r = CheckResult(
        id="S2", name="x", category="spec_extras", target="s",
        score=0, max_score=2, severity="warn", message="", server="s",
    )
    assert display_target(r, multi=True) == "s"


def test_top_fixes_ranks_by_points_recovered():
    # a Safety fail (weight 15, the only safety result) recovers more than a
    # Spec-Extras fail (weight 5, its only result) when each jumps 0 -> 2.
    results = [
        CheckResult("T5", "x", "safety", "del", 0, 2, "fail", "m", "fix safety", "s"),
        CheckResult("S2", "x", "spec_extras", "s", 0, 2, "warn", "m", "fix extras", "s"),
    ]
    ranked = top_fixes(results)
    assert [r.id for r, _ in ranked] == ["T5", "S2"]
    assert all(delta > 0 for _, delta in ranked)


def test_degraded_banner_renders_at_top():
    manifest = Manifest(
        servers=[
            ServerManifest("s", "s", capabilities=None, instructions=None)
        ]
    )
    text = render_text(
        manifest,
        [_result("tool_clarity", 0, "T1")],
        degraded=["GROQ_API_KEY not set - T1/T4 degraded to safe defaults"],
    )
    assert text.splitlines()[0].startswith("!!")
    assert "degraded to safe defaults" in text


def test_rich_card_has_grade_bars_and_qualified_targets(collision_run):
    manifest, results = collision_run
    text = render_rich(
        manifest, results, degraded=["GROQ_API_KEY not set - degraded"]
    )
    assert "Overall:" in text
    assert "Error Quality" in text and "Spec Extras" in text
    assert "#" in text  # a category bar rendered
    # the rich card shows worst-per-category + top fixes, not every finding;
    # qualification is proven by any server-prefixed target appearing
    assert "badserver:" in text
    assert "degraded run" in text  # the banner panel title
    assert "Top fixes" in text


def test_markdown_export_has_table_and_qualified_targets(collision_run):
    manifest, results = collision_run
    md = render_markdown(
        manifest, results, degraded=["GROQ_API_KEY not set - degraded"]
    )
    assert md.startswith("# mcpdoctor")
    assert "| Category | Score | Bar | Worst finding |" in md  # the table header
    assert "**Overall:" in md
    assert "## Findings" in md
    assert "badserver:search" in md and "otherserver:search" in md  # full list
    assert "> ⚠️" in md  # blockquoted degraded banner


def test_fix_blocks_show_before_and_after(badserver_run):
    manifest, results = badserver_run
    blocks = render_fixes(manifest, results)
    # badserver's one-word tools fail T1; the mocked judge supplies a
    # suggested_description carried through the "| suggested:" convention.
    assert "process" in blocks
    assert '- current:   "Processes."' in blocks
    assert "+ suggested:" in blocks


def test_suggested_convention_not_leaked_into_findings(badserver_run):
    manifest, results = badserver_run
    for text in (
        render_text(manifest, results),
        render_markdown(manifest, results),
        render_rich(manifest, results),
    ):
        # the internal "| suggested:" marker must stay out of the report body;
        # the rewrite text lives in --fix only
        assert "| suggested:" not in text


def test_fix_blocks_empty_without_suggestions():
    manifest = Manifest(
        servers=[ServerManifest("s", "s", capabilities=None, instructions=None)]
    )
    # a T1 pass (no fix_hint) yields no rewrite blocks
    passing = CheckResult(
        "T1", "x", "tool_clarity", "good_tool", 2, 2, "info", "ok", None, "s"
    )
    assert "needs GROQ_API_KEY" in render_fixes(manifest, [passing])
