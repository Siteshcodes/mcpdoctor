"""LLM-backed checks: T4 (error repairability, heal-scored) and T1
(description quality). Judge hygiene per CLAUDE.md is delegated to
llm.json_call — temp=0, JSON-only, fence-strip, one parse retry, safe
default, never raises — so a judge failure can never crash a lint run.

These import engine helpers from checks_probe (ensure_probe_run,
make_repair_executor, ...) but never another *check* function.
"""

import math

from mcp import ClientSession

from mcpdoctor import heal, llm
from mcpdoctor.doctor.checks_probe import (
    ProbeRecord,
    call_error_text,
    ensure_probe_run,
    is_read_only,
    make_repair_executor,
)
from mcpdoctor.doctor.manifest import Manifest
from mcpdoctor.doctor.results import CheckResult

_T1_MIN_WORDS = 10  # spec §3 static gate

# Spec §10, verbatim.
_T1_JUDGE_PROMPT = """You are grading an MCP tool description for AI usability.
Tool name: {name}
Description: {description}

Score 0-2:
2 = an AI agent could decide WHEN to use this tool vs alternatives,
    and knows its constraints
1 = says what the tool does, but not when to use it
0 = vague or content-free

Reply with ONLY JSON: {{"score": <0|1|2>, "reason": "<one sentence>",
"suggested_description": "<improved version, <=40 words>"}}"""

# Spec §10, verbatim.
_T4_FIXHINT_PROMPT = """An AI agent sent this tool call and got this error, and could not
repair the call from the error text alone.
Tool schema: {schema}
Bad call: {args}
Error returned: {error}

Reply with ONLY JSON: {{"fix_hint": "<one sentence telling the server
author what the error message should have said>"}}"""

_T4_STATIC_HINT = (
    "error should name the field, the expected format, and the received value"
)


def _probe_error_text(record: ProbeRecord) -> str:
    if record.payload is not None:
        return call_error_text(record.payload)
    return record.detail


def _t4_fix_hint(schema: dict, record: ProbeRecord) -> str:
    """§10 judge, run only on a failing tool, only to write the fix_hint.
    Falls back to the static hint on any judge trouble."""
    import json

    prompt = _T4_FIXHINT_PROMPT.format(
        schema=json.dumps(schema),
        args=json.dumps(record.probe_args or {}),
        error=_probe_error_text(record),
    )
    result = llm.json_call(prompt, default={"fix_hint": _T4_STATIC_HINT})
    hint = result.get("fix_hint")
    return hint if isinstance(hint, str) and hint.strip() else _T4_STATIC_HINT


def _t1_fix_hint(reason: str, suggestion: str | None) -> str:
    """Carry the judge's suggested_description alongside the reason so Phase-4's
    --fix can re-parse it (interpretation on record)."""
    if suggestion and suggestion.strip():
        return f"{reason} | suggested: {suggestion.strip()}"
    return reason


def _t1_judge(name: str, description: str) -> dict:
    prompt = _T1_JUDGE_PROMPT.format(name=name, description=description)
    # Spec §10 parsing rule: safe default on unparseable.
    return llm.json_call(
        prompt, default={"score": 1, "reason": "judge unparseable"}
    )


async def t1_description_quality(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """T1 (spec §3, §10). Static gate owns the score: missing or < 10 words
    -> 0 without judge influence. The judge is still consulted on gated tools,
    hint-only, to write suggested_description. Well-described tools are judged
    for score and suggestion."""
    results: list[CheckResult] = []
    for server in manifest.servers:
        for tool in server.tools:
            description = (tool.description or "").strip()
            words = len(description.split())

            if words < _T1_MIN_WORDS:
                judged = _t1_judge(tool.name, description)  # suggestion only
                score = 0
                reason = (
                    "no description"
                    if not description
                    else f"only {words} words - says what but not when to use it"
                )
                message = f"static gate: {reason}"
                fix_hint = _t1_fix_hint(reason, judged.get("suggested_description"))
            else:
                judged = _t1_judge(tool.name, description)
                raw = judged.get("score", 1)
                score = raw if isinstance(raw, int) and 0 <= raw <= 2 else 1
                reason = str(judged.get("reason", "judge unparseable"))
                message = reason
                fix_hint = (
                    None
                    if score == 2
                    else _t1_fix_hint(reason, judged.get("suggested_description"))
                )

            results.append(
                CheckResult(
                    id="T1",
                    server=server.name,
                    name="Tool description quality",
                    category="tool_clarity",
                    target=tool.name,
                    score=score,
                    max_score=2,
                    severity="info" if score == 2 else "warn" if score == 1 else "fail",
                    message=message,
                    fix_hint=fix_hint,
                )
            )
    return results


async def t4_error_repairability(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """T4 (spec §4). Per non-destructive tool with reject-probes:
    - any invalid probe that SUCCEEDED -> 0 fail (garbage-acceptance trap);
    - else score each failed reject-probe by the heal loop (repaired in 1
      attempt -> 2, in 2 -> 1, unrepaired -> 0), tool score = floor(mean).
    Destructive-skipped tools have no reject-probes -> naturally n/a.
    The §10 judge writes fix_hints for tools scoring 0 only."""
    run = await ensure_probe_run(sessions, manifest)
    results: list[CheckResult] = []

    for server in manifest.servers:
        session = sessions.get(server.name)
        tools = {t.name: t for t in server.tools}

        by_tool: dict[str, list[ProbeRecord]] = {}
        for record in run.records:
            if (
                record.server == server.name
                and record.kind == "tool_probe"
                and record.expect == "reject"
            ):
                by_tool.setdefault(record.target, []).append(record)

        for tool_name, records in by_tool.items():
            tool = tools.get(tool_name)
            schema = (tool.inputSchema if tool else {}) or {}

            # 1. Garbage-acceptance trap (Phase-2 behavior, message preserved).
            accepted = [r for r in records if r.outcome == "ok"]
            if accepted:
                first = accepted[0]
                message = (
                    f"accepted {first.detail} without error - input validation is broken"
                )
                if len(accepted) > 1:
                    message += f" ({len(accepted)} invalid probes accepted)"
                results.append(
                    CheckResult(
                        id="T4",
                        server=server.name,
                        name="Error repairability",
                        category="error_quality",
                        target=tool_name,
                        score=0,
                        max_score=2,
                        severity="fail",
                        message=message,
                        fix_hint=_t4_fix_hint(schema, first),
                    )
                )
                continue

            # 2. Heal-score each failed reject-probe.
            probe_scores: list[int] = []
            executed_live = False
            for record in records:
                if record.outcome in ("timeout", "protocol_error"):
                    probe_scores.append(0)  # spec §4 step 1: crash/hang -> 0
                    continue
                # error_result -> ask heal to repair from the error text.
                execute, state = make_repair_executor(
                    session, manifest, run, server.name, tool, schema
                )
                outcome = await heal.heal(
                    execute,
                    _probe_error_text(record),
                    schema,
                    record.probe_args or {},
                )
                executed_live = executed_live or state["executed_live"]
                probe_scores.append(
                    2 if outcome.healed and outcome.attempts == 1
                    else 1 if outcome.healed
                    else 0
                )

            score = math.floor(sum(probe_scores) / len(probe_scores)) if probe_scores else 0

            verb = "live" if executed_live else "validated locally (not executed for safety)"
            if score == 2:
                message = f"errors let the heal loop repair every bad call in 1 retry ({verb})"
            elif score == 1:
                message = f"errors repairable but only after 2 retries ({verb})"
            else:
                message = f"errors did not let the heal loop repair the call ({verb})"

            results.append(
                CheckResult(
                    id="T4",
                    server=server.name,
                    name="Error repairability",
                    category="error_quality",
                    target=tool_name,
                    score=score,
                    max_score=2,
                    severity="info" if score == 2 else "warn" if score == 1 else "fail",
                    message=message,
                    fix_hint=_t4_fix_hint(schema, records[0]) if score == 0 else None,
                )
            )
    return results
