"""Integration for the Phase-2 probe checks (R1-R4, P3, S3) against the
fixtures, plus synthetic-ProbeRun unit tests for the paths a fast local
fixture can't produce live (slow probes, timeouts, budget exhaustion)."""

import asyncio

from mcpdoctor.doctor.checks_probe import (
    ProbeRecord,
    ProbeRun,
    _ServerProber,
    probe_notes,
    s3_response_time,
    s3_score,
)
from mcpdoctor.doctor.manifest import Manifest, ServerManifest
from mcpdoctor.doctor.probes import ProbeConfig
from mcpdoctor.doctor.report import render_text


def by_id(results, check_id):
    return [r for r in results if r.id == check_id]


def one(results, check_id, target):
    matches = [r for r in by_id(results, check_id) if r.target == target]
    assert len(matches) == 1, f"expected one {check_id} result for {target}, got {matches}"
    return matches[0]


# --- live fixture runs ------------------------------------------------------


def test_r1_badserver_resources_all_readable(badserver_run):
    _, results = badserver_run
    assert one(results, "R1", "badserver").score == 2


def test_r2_flags_the_40k_resource(badserver_run):
    _, results = badserver_run
    r = one(results, "R2", "badserver")
    assert r.score == 0
    assert r.severity == "warn"  # spec: big is sometimes legitimate
    assert "big-report" in r.message


def test_r3_catches_the_mime_lie(badserver_run):
    _, results = badserver_run
    lie = one(results, "R3", "data://config")
    assert lie.score == 0
    assert lie.severity == "fail"
    assert "not valid JSON" in lie.message
    assert one(results, "R3", "data://big-report").score == 2


def test_r4_undocumented_template_fails(badserver_run):
    _, results = badserver_run
    assert one(results, "R4", "data://entry/{key}").score == 0


def test_r4_documented_template_with_example_reads(collision_run):
    _, results = collision_run
    r = one(results, "R4", "demo://item/{n}")
    assert r.score == 2
    assert "demo://item/1" in r.message


def test_t4_exemplary_error_heals_to_two(collision_run):
    manifest, results = collision_run
    # fetch_metrics: read-only, exemplary error -> heal repairs in 1 -> 2.
    r = one(results, "T4", "fetch_metrics")
    assert r.score == 2
    assert r.severity == "info"
    # proof it was actually executed live (read-only path), not just validated
    repair = [
        rec
        for rec in manifest._probe_run.records
        if rec.kind == "repair_exec" and rec.target == "fetch_metrics"
    ]
    assert repair, "fetch_metrics should have been re-executed live"


def test_p3_prompt_renders_with_filler_args(collision_run):
    _, results = collision_run
    assert one(results, "P3", "summarize_hits").score == 2


def test_p2_live_documented_prompt(collision_run):
    _, results = collision_run
    assert one(results, "P2", "summarize_hits").score == 2


def test_s3_badserver_is_fast(badserver_run):
    _, results = badserver_run
    assert one(results, "S3", "badserver").score == 2


def test_probe_budget_respected(badserver_run):
    manifest, _ = badserver_run
    assert manifest._probe_run.budget_used["badserver"] <= 40


def test_destructive_skip_produces_safety_note(badserver_run):
    manifest, _ = badserver_run
    notes = probe_notes(manifest)
    assert any(
        "delete_everything" in n and "skipped for safety" in n for n in notes
    )


def test_report_has_no_partial_labels_and_shows_notes(badserver_run):
    manifest, results = badserver_run
    text = render_text(manifest, results, probe_notes(manifest))
    # Phase 3: T4 and T1 landed, so grades are real - no "partial" labels.
    assert "partial (" not in text
    assert "Probe safety:" in text
    assert "active probes skipped for safety" in text


# --- synthetic ProbeRun paths -----------------------------------------------


def _record(latency: float, outcome: str = "ok") -> ProbeRecord:
    return ProbeRecord(
        kind="tool_probe", server="s", target="t", outcome=outcome, latency_s=latency
    )


def test_s3_score_fast():
    score, _ = s3_score([_record(0.1), _record(4.9)])
    assert score == 2


def test_s3_score_slow_window():
    score, message = s3_score([_record(0.1), _record(6.0)])
    assert score == 1
    assert "6.0s" in message


def test_s3_score_timeout():
    score, message = s3_score([_record(0.1), _record(10.0, "timeout")])
    assert score == 0
    assert "timed out" in message


def _synthetic_manifest() -> Manifest:
    server = ServerManifest(
        name="s", server_info_name="s", capabilities=None, instructions=None
    )
    return Manifest(servers=[server])


def test_s3_check_consumes_preseeded_run():
    # Fabricating manifest._probe_run exercises the full check without a
    # live server - the same seam every probe check shares.
    manifest = _synthetic_manifest()
    manifest._probe_run = ProbeRun(records=[_record(0.2), _record(10.0, "timeout")])
    results = asyncio.run(s3_response_time({}, manifest))
    assert len(results) == 1
    assert results[0].score == 0
    assert results[0].severity == "fail"


def test_budget_clamp_stops_calls_and_notes_once():
    manifest = _synthetic_manifest()
    manifest.probe_config = ProbeConfig(budget_per_server=3)
    prober = _ServerProber(manifest.servers[0], None, manifest, ProbeRun())
    grants = [prober._take_budget() for _ in range(5)]
    assert grants == [True, True, True, False, False]
    exhausted = [n for n in prober.run.notes if "budget exhausted" in n]
    assert len(exhausted) == 1


async def test_exhausted_budget_closes_unstarted_coroutine():
    import inspect

    manifest = _synthetic_manifest()
    manifest.probe_config = ProbeConfig(budget_per_server=0)
    prober = _ServerProber(manifest.servers[0], None, manifest, ProbeRun())

    async def must_not_run():
        raise AssertionError("budget-exhausted call was executed")

    coro = must_not_run()
    assert await prober._call("resource_read", "data://test", coro) is None
    assert inspect.getcoroutinestate(coro) == inspect.CORO_CLOSED
