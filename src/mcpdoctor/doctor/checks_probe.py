"""Probe engine + probe-driven checks (spec §4-§7, §9).

Safety rules (spec §5) are wired in from the first line:
- destructive tools (DESTRUCTIVE_WORDS in name, or destructiveHint=True) are
  NEVER probe-called unless the run is --unsafe; the skip surfaces as a
  probe-safety note, not a scored result;
- every probe uses invalid inputs designed to be rejected (probes.py);
- every call runs under the configured timeout (default 10s);
- hard budget per server (default 40 calls) across reads, prompt-gets and
  tool probes combined.

The engine runs ONCE per doctor run: the first probe check to execute fills
manifest._probe_run, and every other check reads the same records - one
execution, one budget, no double reads.
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import jsonschema
from mcp import ClientSession, types
from pydantic import AnyUrl

from mcpdoctor.doctor.manifest import Manifest, ServerManifest
from mcpdoctor.doctor.probes import generate_probes
from mcpdoctor.doctor.results import CheckResult
from mcpdoctor.doctor.vocab import DESTRUCTIVE_WORDS, READ_ONLY_WORDS, name_tokens

RESOURCE_SAMPLE = 10  # spec §6: first N in listing order, deterministic


@dataclass
class ProbeRecord:
    kind: str  # "resource_read" | "template_read" | "prompt_get" | "tool_probe"
    server: str
    target: str  # resource uri / template uriTemplate / prompt / tool name
    outcome: str  # "ok" | "error_result" | "protocol_error" | "timeout"
    latency_s: float
    template: str | None = None  # probe template name (tool probes only)
    expect: str | None = None  # "reject" | "tolerate" (tool probes only)
    detail: str = ""  # error text / instantiated URI / probe description
    payload: Any = None  # ReadResourceResult for reads, GetPromptResult for gets
    probe_args: dict | None = None  # the bad args sent (tool probes; T4 seeds heal)


@dataclass
class ProbeRun:
    records: list[ProbeRecord] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # probe-safety notes
    budget_used: dict[str, int] = field(default_factory=dict)


def is_destructive(tool: types.Tool) -> bool:
    """Spec §5 rule 1 - by annotation OR by name."""
    if tool.annotations is not None and tool.annotations.destructiveHint is True:
        return True
    return bool(name_tokens(tool.name) & DESTRUCTIVE_WORDS)


def is_read_only(tool: types.Tool) -> bool:
    """Spec §4/§5 read-only heuristic for lint-time repair execution.

    Destructive signals and explicit readOnlyHint=False override read-like
    names. Otherwise use the annotation or get/list/read/search/fetch/query/show.
    """
    if is_destructive(tool):
        return False
    if tool.annotations is not None and tool.annotations.readOnlyHint is not None:
        return tool.annotations.readOnlyHint is True
    return bool(name_tokens(tool.name) & READ_ONLY_WORDS)


def call_error_text(result: types.CallToolResult | None) -> str:
    """Text content of an errored CallToolResult - the string heal sees."""
    if result is None:
        return ""
    return "\n".join(
        c.text for c in result.content if isinstance(c, types.TextContent)
    )


def local_validation_error(schema: dict, args: dict) -> str | None:
    """None if args satisfy the inputSchema, else a concise error string.
    Used to score repaired args for non-read-only tools WITHOUT executing
    them (spec §4/§5 lint-repair safety)."""
    try:
        validator = jsonschema.Draft202012Validator(schema or {})
        errors = sorted(validator.iter_errors(args), key=str)
    except jsonschema.exceptions.SchemaError:
        return None  # unusable schema - treat as "can't disprove", heal wins
    if not errors:
        return None
    return "; ".join(e.message for e in errors[:3])


_URI_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s'\"()]+")


def example_uri_for(template: types.ResourceTemplate) -> str | None:
    """Deterministic R4 instantiation: a URI in the template's own
    description that matches the template's shape; no LLM call is made."""
    escaped = re.escape(template.uriTemplate)
    pattern = re.sub(r"\\\{\w+\\\}", lambda m: r"[^/\s]+", escaped)
    shape = re.compile(f"^{pattern}$")
    for candidate in _URI_RE.findall(template.description or ""):
        candidate = candidate.rstrip(".,;")
        if shape.match(candidate):
            return candidate
    return None


class _ServerProber:
    """Runs all probe calls for one server under its budget."""

    def __init__(
        self,
        server: ServerManifest,
        session: ClientSession,
        manifest: Manifest,
        run: ProbeRun,
    ):
        self.server = server
        self.session = session
        self.cfg = manifest.probe_config
        self.run = run
        self.used = 0
        self.exhausted = False

    def _take_budget(self) -> bool:
        if self.used >= self.cfg.budget_per_server:
            if not self.exhausted:
                self.exhausted = True
                self.run.notes.append(
                    f"{self.server.name}: probe budget exhausted "
                    f"({self.cfg.budget_per_server} calls) - remaining probes skipped"
                )
            return False
        self.used += 1
        return True

    async def _call(self, kind: str, target: str, coro, **extra) -> ProbeRecord | None:
        if not self._take_budget():
            coro.close()
            return None
        start = time.monotonic()
        try:
            payload = await asyncio.wait_for(coro, timeout=self.cfg.timeout_s)
            outcome, detail = "ok", ""
        except asyncio.TimeoutError:
            payload = None
            outcome, detail = "timeout", f"no response within {self.cfg.timeout_s:.0f}s"
        except Exception as e:
            payload = None
            outcome, detail = "protocol_error", str(e)
        record = ProbeRecord(
            kind=kind,
            server=self.server.name,
            target=target,
            outcome=outcome,
            latency_s=time.monotonic() - start,
            payload=payload,
            detail=extra.pop("detail", detail) if outcome == "ok" else detail,
            **extra,
        )
        self.run.records.append(record)
        return record

    async def probe(self) -> None:
        # 1. Resources - read each (first RESOURCE_SAMPLE, spec §6).
        for resource in self.server.resources[:RESOURCE_SAMPLE]:
            await self._call(
                "resource_read",
                str(resource.uri),
                self.session.read_resource(AnyUrl(str(resource.uri))),
            )

        # 2. Templates - only when a documented example URI is extractable.
        for template in self.server.resource_templates:
            uri = example_uri_for(template)
            if uri is None:
                continue
            await self._call(
                "template_read",
                template.uriTemplate,
                self.session.read_resource(AnyUrl(uri)),
                detail=uri,
            )

        # 3. Prompts - render with deterministic filler args.
        for prompt in self.server.prompts:
            args = {a.name: "example" for a in (prompt.arguments or [])}
            await self._call(
                "prompt_get", prompt.name, self.session.get_prompt(prompt.name, args)
            )

        # 4. Tools - the trap sweep. Safety gate FIRST (spec §5).
        for tool in self.server.tools:
            if is_destructive(tool) and not self.cfg.unsafe:
                self.run.notes.append(
                    f"{self.server.name}/{tool.name}: active probes skipped for safety"
                )
                continue
            plan = generate_probes(tool, thorough=self.cfg.thorough)
            for note in plan.notes:
                self.run.notes.append(f"{self.server.name}/{tool.name}: {note}")
            for probe in plan.probes:
                record = await self._call(
                    "tool_probe",
                    tool.name,
                    self.session.call_tool(tool.name, probe.args),
                    template=probe.template,
                    expect=probe.expect,
                    detail=probe.note,
                    probe_args=probe.args,
                )
                if record is None:  # budget exhausted mid-tool
                    return
                # call_tool resolves with isError=True for in-band failures.
                if record.outcome == "ok" and record.payload is not None:
                    if getattr(record.payload, "isError", False):
                        record.outcome = "error_result"


async def ensure_probe_run(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> ProbeRun:
    """Execute (once) and cache the probe pass for this manifest."""
    if manifest._probe_run is None:
        run = ProbeRun()
        for server in manifest.servers:
            session = sessions.get(server.name)
            if session is None:
                continue
            prober = _ServerProber(server, session, manifest, run)
            await prober.probe()
            run.budget_used[server.name] = prober.used
        manifest._probe_run = run
    return manifest._probe_run


def probe_notes(manifest: Manifest) -> list[str]:
    """Safety/budget notes for the report; empty before any probe check ran."""
    run = manifest._probe_run
    return list(run.notes) if isinstance(run, ProbeRun) else []


def make_repair_executor(
    session: ClientSession | None,
    manifest: Manifest,
    run: ProbeRun,
    server_name: str,
    tool: types.Tool,
    schema: dict,
):
    """Build the heal `execute` callback for T4 (spec §4/§5 lint-repair safety).

    Read-only tools: re-run the repaired call live (recorded as a
    "repair_exec" ProbeRecord, counted against the same per-server budget).
    Everything else: validate the repaired args locally, never executed.
    Returns (execute, executed_live_flag_holder)."""
    cfg = manifest.probe_config
    read_only = is_read_only(tool)
    state = {"executed_live": False}

    async def execute(candidate_args: dict) -> tuple[bool, str]:
        used = run.budget_used.get(server_name, 0)
        if read_only and session is not None and used < cfg.budget_per_server:
            run.budget_used[server_name] = used + 1
            start = time.monotonic()
            outcome, err, result = "ok", "", None
            try:
                result = await asyncio.wait_for(
                    session.call_tool(tool.name, candidate_args),
                    timeout=cfg.timeout_s,
                )
            except asyncio.TimeoutError:
                outcome, err = "timeout", f"no response within {cfg.timeout_s:.0f}s"
            except Exception as e:  # noqa: BLE001 - protocol error, not a crash
                outcome, err = "protocol_error", str(e)
            if result is not None:
                if getattr(result, "isError", False):
                    outcome, err = "error_result", call_error_text(result)
                else:
                    outcome = "ok"
            run.records.append(
                ProbeRecord(
                    kind="repair_exec",
                    server=server_name,
                    target=tool.name,
                    outcome=outcome,
                    latency_s=time.monotonic() - start,
                    detail="repair retry (read-only, live)",
                )
            )
            state["executed_live"] = True
            return outcome == "ok", err

        # Non-read-only, or budget exhausted: validate locally, never execute.
        error = local_validation_error(schema, candidate_args)
        if error is None:
            return True, ""
        return False, error

    return execute, state


def _severity(score: int) -> str:
    return {2: "info", 1: "warn", 0: "fail"}[score]


def _records(run: ProbeRun, server: str, kind: str) -> list[ProbeRecord]:
    return [r for r in run.records if r.server == server and r.kind == kind]


# --- Resources (spec §6) ----------------------------------------------------


async def r1_resource_readability(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """R1 - a listed resource that errors on read is a broken promise."""
    run = await ensure_probe_run(sessions, manifest)
    results = []
    for server in manifest.servers:
        reads = _records(run, server.name, "resource_read")
        if not reads:
            continue  # n/a - no resources
        ok = [r for r in reads if r.outcome == "ok"]
        frac = len(ok) / len(reads)
        score = 2 if frac == 1.0 else 1 if frac >= 0.8 else 0
        message = f"{len(ok)}/{len(reads)} listed resources readable"
        if len(server.resources) > len(reads):
            message += f" (sampled first {len(reads)} of {len(server.resources)})"
        failing = [f"{r.target} ({r.detail})" for r in reads if r.outcome != "ok"]
        if failing:
            message += f"; failing: {'; '.join(failing)}"
        results.append(
            CheckResult(
                id="R1",
                server=server.name,
                name="Resource readability",
                category="resources",
                target=server.name,
                score=score,
                max_score=2,
                severity=_severity(score),
                message=message,
                fix_hint=None
                if score == 2
                else "every listed resource must read successfully - fix or unlist the broken ones",
            )
        )
    return results


def _payload_tokens(payload: types.ReadResourceResult) -> int:
    total = 0
    for content in payload.contents:
        if isinstance(content, types.TextResourceContents):
            total += len(content.text)
        elif isinstance(content, types.BlobResourceContents):
            total += len(content.blob)
    return total // 4


async def r2_context_flooding(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """R2 - need one field, receive a 50k-token dump. Severity warn: the
    report makes the cost visible, big is sometimes legitimate (spec §6)."""
    run = await ensure_probe_run(sessions, manifest)
    results = []
    for server in manifest.servers:
        sizes = [
            (r.target, _payload_tokens(r.payload))
            for r in _records(run, server.name, "resource_read")
            if r.outcome == "ok" and r.payload is not None
        ]
        if not sizes:
            continue  # n/a - nothing readable to measure
        worst_uri, worst = max(sizes, key=lambda pair: pair[1])
        score = 2 if worst <= 2_000 else 1 if worst <= 10_000 else 0
        results.append(
            CheckResult(
                id="R2",
                server=server.name,
                name="Context flooding (size)",
                category="resources",
                target=server.name,
                score=score,
                max_score=2,
                severity="info" if score == 2 else "warn",
                message=f"largest of {len(sizes)} resource(s) is ~{worst} tokens ({worst_uri})",
                fix_hint=None
                if score == 2
                else "split into per-section resources or add a summary resource",
            )
        )
    return results


async def r3_mime_honesty(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """R3 - the model plans how to parse based on mimeType; a lie breaks the plan."""
    run = await ensure_probe_run(sessions, manifest)
    results = []
    for server in manifest.servers:
        reads = {r.target: r for r in _records(run, server.name, "resource_read")}
        for resource in server.resources[:RESOURCE_SAMPLE]:
            uri = str(resource.uri)
            declared = resource.mimeType
            record = reads.get(uri)

            if not declared:
                score, message = 0, "no mimeType declared"
            elif record is None or record.outcome != "ok" or not record.payload.contents:
                score, message = 1, f"declared {declared} but unverifiable (read failed)"
            else:
                content = record.payload.contents[0]
                is_text = isinstance(content, types.TextResourceContents)
                if declared == "application/json" or declared.endswith("+json"):
                    parseable = False
                    if is_text:
                        try:
                            json.loads(content.text)
                            parseable = True
                        except ValueError:
                            parseable = False
                    if parseable:
                        score, message = 2, f"declared {declared}, content parses as JSON"
                    else:
                        score, message = 0, f"declared {declared} but content is not valid JSON"
                elif declared.startswith("text/"):
                    if is_text:
                        score, message = 2, f"declared {declared}, content is text"
                    else:
                        score, message = 0, f"declared {declared} but content is a binary blob"
                else:
                    score, message = 1, f"declared {declared} (not verifiable from content)"

            results.append(
                CheckResult(
                    id="R3",
                    server=server.name,
                    name="MIME declared & matches content",
                    category="resources",
                    target=uri,
                    score=score,
                    max_score=2,
                    severity=_severity(score),
                    message=message,
                    fix_hint=None
                    if score == 2
                    else "declare the mimeType the content actually has - agents parse based on it",
                )
            )
    return results


_TEMPLATE_PARAM_RE = re.compile(r"\{(\w+)\}")


async def r4_template_usability(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """R4 - the model constructs URIs from templates itself; undocumented
    params make that a guessing game."""
    run = await ensure_probe_run(sessions, manifest)
    results = []
    for server in manifest.servers:
        reads = {r.target: r for r in _records(run, server.name, "template_read")}
        for template in server.resource_templates:
            params = _TEMPLATE_PARAM_RE.findall(template.uriTemplate)
            desc = (template.description or "").strip()
            missing = [
                p for p in params if not re.search(rf"\b{re.escape(p)}\b", desc)
            ]
            record = reads.get(template.uriTemplate)

            if not desc or missing:
                score = 0
                message = (
                    "no description at all"
                    if not desc
                    else f"template params undocumented: {', '.join(missing)}"
                )
            elif record is not None and record.outcome == "ok":
                score = 2
                message = f"params documented; example URI {record.detail} reads successfully"
            elif record is not None:
                score = 1
                message = f"params documented but the example URI failed to read ({record.detail})"
            else:
                score = 1
                message = "params documented; no example URI in the description to instantiate"

            results.append(
                CheckResult(
                    id="R4",
                    server=server.name,
                    name="URI template usability",
                    category="resources",
                    target=template.uriTemplate,
                    score=score,
                    max_score=2,
                    severity=_severity(score),
                    message=message,
                    fix_hint=None
                    if score == 2
                    else "describe every template param and include a working example URI in the description",
                )
            )
    return results


# --- Protocol Hygiene (spec §7) ---------------------------------------------


async def p3_prompt_renders(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """P3 - prompts/get with filler args must return non-empty messages."""
    run = await ensure_probe_run(sessions, manifest)
    results = []
    for server in manifest.servers:
        gets = {r.target: r for r in _records(run, server.name, "prompt_get")}
        for prompt in server.prompts:
            record = gets.get(prompt.name)
            rendered = (
                record is not None
                and record.outcome == "ok"
                and record.payload is not None
                and bool(record.payload.messages)
            )
            if rendered:
                score = 2
                message = f"renders {len(record.payload.messages)} message(s) with filler args"
            else:
                score = 0
                detail = record.detail if record is not None else "not attempted (budget)"
                message = f"prompts/get failed: {detail}"
            results.append(
                CheckResult(
                    id="P3",
                    server=server.name,
                    name="Prompt renders with valid args",
                    category="protocol_hygiene",
                    target=prompt.name,
                    score=score,
                    max_score=2,
                    severity="info" if score == 2 else "fail",
                    message=message,
                    fix_hint=None
                    if score == 2
                    else "prompts/get must return non-empty messages for plausible args",
                )
            )
    return results


# --- Error Quality (spec §4) ------------------------------------------------


async def t4_garbage_trap(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """The garbage-acceptance trap (spec §4, step 2): a deliberately invalid
    call that SUCCEEDS is the worst outcome - validation is broken. Automatic
    0 with severity fail.

    NOTE: superseded in step (e) by t4_error_repairability in checks_llm.py,
    which absorbs this trap logic AND adds heal-loop scoring. Kept here only
    so step (d) stays runnable; removed from the registry in step (e)."""
    run = await ensure_probe_run(sessions, manifest)
    results = []
    for server in manifest.servers:
        offenders: dict[str, list[ProbeRecord]] = {}
        for record in _records(run, server.name, "tool_probe"):
            if record.expect == "reject" and record.outcome == "ok":
                offenders.setdefault(record.target, []).append(record)
        for tool_name, records in offenders.items():
            first = records[0]
            message = f"accepted {first.detail} without error - input validation is broken"
            if len(records) > 1:
                message += f" ({len(records)} invalid probes accepted)"
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
                    fix_hint="validate inputs against the declared schema and "
                    "reject bad calls with isError naming the field",
                )
            )
    return results


def s3_score(records: list[ProbeRecord]) -> tuple[int, str]:
    """Pure S3 scoring core: 2 = all <5s, 1 = any 5-10s, 0 = any timeout."""
    timeouts = sum(1 for r in records if r.outcome == "timeout")
    max_latency = max((r.latency_s for r in records), default=0.0)
    if timeouts:
        return 0, f"{timeouts} of {len(records)} probe calls timed out"
    if max_latency >= 5.0:
        return 1, f"slowest of {len(records)} probe calls took {max_latency:.1f}s (5-10s window)"
    return 2, f"{len(records)} probe calls, all under 5s (max {max_latency:.2f}s)"


async def s3_response_time(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """S3 - a tool that hangs forever kills the whole agent loop."""
    run = await ensure_probe_run(sessions, manifest)
    results = []
    for server in manifest.servers:
        records = [r for r in run.records if r.server == server.name]
        if not records:
            continue  # n/a - nothing was probed
        score, message = s3_score(records)
        results.append(
            CheckResult(
                id="S3",
                server=server.name,
                name="Probe response time / hangs",
                category="error_quality",
                target=server.name,
                score=score,
                max_score=2,
                severity=_severity(score),
                message=message,
                fix_hint=None
                if score == 2
                else "enforce server-side time limits and return errors promptly - timeouts are the failure mode nobody handles",
            )
        )
    return results
