"""Integration: the full pipeline against fixtures/badserver.py.

Every planted flaw must be caught by the check ID tagged next to it in the
fixture. One stdio round-trip per session (see conftest.run_doctor).
"""

from mcpdoctor.doctor.report import render_text
from mcpdoctor.doctor.results import category_scores, letter_grade, overall_score


def by_id(results, check_id):
    return [r for r in results if r.id == check_id]


def one(results, check_id, target):
    matches = [r for r in by_id(results, check_id) if r.target == target]
    assert len(matches) == 1, f"expected one {check_id} result for {target}, got {matches}"
    return matches[0]


def test_t2_catches_undocumented_date(badserver_run):
    _, results = badserver_run
    r = one(results, "T2", "get_data")
    assert r.score == 0
    assert "date" in r.message
    assert "format" in r.fix_hint


def test_t2_flags_all_undocumented_tools(badserver_run):
    _, results = badserver_run
    assert all(r.score == 0 for r in by_id(results, "T2"))


def test_t3_no_examples_anywhere(badserver_run):
    _, results = badserver_run
    t3 = by_id(results, "T3")
    assert t3 and all(r.score == 0 for r in t3)


def test_t5_destructive_mismatch_hard_fails_safety(badserver_run):
    _, results = badserver_run
    r = one(results, "T5", "delete_everything")
    assert r.score == 0
    assert r.severity == "fail"
    assert "destructiveHint" in r.fix_hint
    assert category_scores(results)["safety"] == 0.0


def test_t6_generic_names_and_near_dupes_warn(badserver_run):
    _, results = badserver_run
    r = one(results, "T6", "badserver")
    assert r.score == 1
    assert r.severity == "warn"
    assert "process" in r.message and "handle" in r.message
    assert "get_data/get_dates" in r.message


def test_t7_small_manifest_passes(badserver_run):
    _, results = badserver_run
    assert one(results, "T7", "badserver").score == 2


def test_s1_declared_but_empty_prompts_warns(badserver_run):
    _, results = badserver_run
    r = one(results, "S1", "badserver")
    assert r.score == 1
    assert "framework default" in r.message


def test_s2_missing_instructions(badserver_run):
    _, results = badserver_run
    assert one(results, "S2", "badserver").score == 0


def test_p1_no_prompts(badserver_run):
    _, results = badserver_run
    assert one(results, "P1", "badserver").score == 0


def test_p2_is_na_without_prompts(badserver_run):
    _, results = badserver_run
    assert by_id(results, "P2") == []


def test_r5_no_subscriptions(badserver_run):
    _, results = badserver_run
    assert one(results, "R5", "badserver").score == 0


def test_badserver_flunks_overall(badserver_run):
    _, results = badserver_run
    assert letter_grade(overall_score(results)) == "F"


def test_report_renders_grade_and_findings(badserver_run):
    manifest, results = badserver_run
    text = render_text(manifest, results)
    assert "Overall: F" in text
    assert "T5 delete_everything" in text
    # Since Phase 2 every category has results for badserver - the probe
    # findings must render too ("n/a" display is no longer reachable here).
    assert "R2 badserver" in text
    assert "R3 data://config" in text


def test_garbage_trap_catches_accepting_tool(badserver_run):
    """Spec §4: a deliberately invalid probe that SUCCEEDS is an automatic
    fail. log_event declares format=date but never validates it."""
    _, results = badserver_run
    r = one(results, "T4", "log_event")
    assert r.score == 0
    assert r.severity == "fail"
    assert "accepted" in r.message and "without error" in r.message


def test_garbage_trap_fires_only_on_the_acceptor(badserver_run):
    _, results = badserver_run
    # Since Phase 3, T4 covers every probed tool (heal-scored), but the
    # garbage-trap MESSAGE must attach only to log_event - the tool that
    # accepted invalid input. Other tools reject, so they get heal-scored
    # messages, not "accepted ... without error".
    trap = [r for r in by_id(results, "T4") if "without error" in r.message]
    assert [r.target for r in trap] == ["log_event"]


def test_t4_skips_destructive_tool(badserver_run):
    _, results = badserver_run
    # delete_everything is destructive-skipped: never probed, so no T4 result.
    assert "delete_everything" not in {r.target for r in by_id(results, "T4")}


def test_t4_cryptic_body_tool_scores_zero_with_fix_hint(badserver_run):
    _, results = badserver_run
    # get_data: read-only-named, live-executed; body always raises "400",
    # so no error message lets heal repair it -> 0 with a concrete fix_hint.
    r = one(results, "T4", "get_data")
    assert r.score == 0
    assert r.severity == "fail"
    assert r.fix_hint and "field" in r.fix_hint


def test_no_repair_ever_executed_on_non_read_only_tools(badserver_run):
    # Live-fixture safety audit: process/handle are non-read-only, so T4 must
    # have scored them by LOCAL VALIDATION - zero repair_exec records for them.
    manifest, _ = badserver_run
    repair_targets = {
        r.target for r in manifest._probe_run.records if r.kind == "repair_exec"
    }
    assert "process" not in repair_targets
    assert "handle" not in repair_targets
    assert manifest._probe_run.budget_used["badserver"] <= 40


def test_t6_cross_server_collision_hard_fails(collision_run):
    _, results = collision_run
    badserver = one(results, "T6", "badserver")
    otherserver = one(results, "T6", "otherserver")
    assert badserver.score == 0 and otherserver.score == 0
    assert "'search'" in badserver.message and "otherserver" in badserver.message
