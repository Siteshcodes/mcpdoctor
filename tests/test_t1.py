"""T1 description quality: static gate + §10 judge. Groq mocked by conftest;
one live-marked test exercises the real judge."""

import shutil

import pytest

from mcpdoctor.doctor.checks_llm import t1_description_quality


def by_id(results, check_id):
    return [r for r in results if r.id == check_id]


def one(results, check_id, target):
    matches = [r for r in by_id(results, check_id) if r.target == target]
    assert len(matches) == 1
    return matches[0]


def test_one_word_descriptions_all_score_zero(badserver_run):
    _, results = badserver_run
    t1 = by_id(results, "T1")
    # every badserver tool has a one-word description -> static gate -> 0
    assert t1 and all(r.score == 0 for r in t1)
    assert all(r.severity == "fail" for r in t1)


def test_gated_tool_still_gets_a_suggested_description(badserver_run):
    _, results = badserver_run
    r = one(results, "T1", "process")
    assert r.message.startswith("static gate:")
    # interpretation on record: gate owns the score, judge writes the suggestion
    assert "suggested:" in (r.fix_hint or "")


def test_well_described_tool_is_judge_scored(collision_run):
    _, results = collision_run
    # Two tools are named 'search' (the T6 collision): badserver's one-word
    # one is gated to 0, otherserver's rich description is judge-scored 2.
    search_scores = {r.score for r in by_id(results, "T1") if r.target == "search"}
    assert search_scores == {0, 2}
    judged = next(
        r for r in by_id(results, "T1") if r.target == "search" and r.score == 2
    )
    assert judged.fix_hint is None


def test_t1_covers_every_tool(badserver_run):
    manifest, results = badserver_run
    tool_names = {t.name for s in manifest.servers for t in s.tools}
    assert {r.target for r in by_id(results, "T1")} == tool_names


@pytest.mark.live
def test_t1_judge_live():
    # Real Groq (requires GROQ_API_KEY). Bypasses the conftest module mock by
    # driving a fresh GroqLLM directly, so the session mock stays intact.
    import os

    if not os.getenv("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY not set")

    from mcpdoctor import llm
    from mcpdoctor.doctor.checks_llm import _T1_JUDGE_PROMPT
    from mcpdoctor.llm import GroqLLM

    llm.reset_degradation()
    judge = GroqLLM()
    good = judge.json_call(
        _T1_JUDGE_PROMPT.format(
            name="search_docs",
            description="Search documents by title keyword. Use this when the "
            "user names a topic to locate; matches titles only, not full text.",
        ),
        default={"score": -1},
    )
    vague = judge.json_call(
        _T1_JUDGE_PROMPT.format(name="process", description="Processes."),
        default={"score": -1},
    )
    # If the provider itself failed (rate limit / outage), that's not a code
    # defect — skip rather than fail a flaky live test on Groq's availability.
    if llm.degradation_events():
        pytest.skip(f"Groq degraded: {llm.degradation_events()[0]}")

    assert good.get("score") in (1, 2)
    assert vague.get("score") in (0, 1)
    assert good.get("suggested_description")  # judge always proposes one
