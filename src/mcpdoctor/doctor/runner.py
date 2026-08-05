"""Check registry + orchestration (spec §1).

Every check is a small async function (sessions, manifest) -> list[CheckResult],
registered in CHECKS below. Static checks ignore the sessions dict; probe
checks (Phase 2) route their calls through it. No check imports another.
"""

import os
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from mcp import ClientSession

from mcpdoctor import llm

from mcpdoctor.doctor.checks_llm import t1_description_quality, t4_error_repairability
from mcpdoctor.doctor.checks_probe import (
    p3_prompt_renders,
    probe_notes,
    r1_resource_readability,
    r2_context_flooding,
    r3_mime_honesty,
    r4_template_usability,
    s3_response_time,
)
from mcpdoctor.doctor.manifest import gather_manifest
from mcpdoctor.doctor.probes import ProbeConfig
from mcpdoctor.mcp_client import (
    ConnectError,
    MCPClient,
    root_cause,
    spec_to_command,
    unique_key,
)
from mcpdoctor.doctor.checks_static import (
    p1_prompts_exist,
    p2_prompt_arg_docs,
    r5_subscriptions,
    s1_capability_honesty,
    s2_instructions,
    t2_param_docs,
    t3_examples,
    t5_safety_annotations,
    t6_names,
    t7_manifest_bloat,
)
from mcpdoctor.doctor.manifest import Manifest
from mcpdoctor.doctor.results import CheckResult

Check = Callable[[dict[str, ClientSession], Manifest], Awaitable[list[CheckResult]]]

CHECKS: list[Check] = [
    t1_description_quality,
    t2_param_docs,
    t3_examples,
    t5_safety_annotations,
    t6_names,
    t7_manifest_bloat,
    s1_capability_honesty,
    p2_prompt_arg_docs,
    s2_instructions,
    p1_prompts_exist,
    r5_subscriptions,
    # probe checks (Phase 2) - the first one to run fills the shared ProbeRun
    r1_resource_readability,
    r2_context_flooding,
    r3_mime_honesty,
    r4_template_usability,
    p3_prompt_renders,
    # T4 (Phase 3) heals reject-probes; its repair_exec calls add records, so
    # it MUST run before s3_response_time, which scores over all probe records.
    t4_error_repairability,
    s3_response_time,
]


async def run_checks(
    sessions: dict[str, ClientSession],
    manifest: Manifest,
    checks: list[Check] | None = None,
) -> list[CheckResult]:
    """Run every registered check (or an explicit subset) and pool the results."""
    results: list[CheckResult] = []
    for check in CHECKS if checks is None else checks:
        results.extend(await check(sessions, manifest))
    return results


@dataclass
class DoctorRun:
    manifest: Manifest
    results: list[CheckResult]
    notes: list[str] = field(default_factory=list)  # probe-safety notes
    degraded: list[str] = field(default_factory=list)  # degradation banners (r1)


_FLOOR = "; grade is a floor, not a final"


def degraded_banners() -> list[str]:
    """Disclosure banners (spec §11) for a run whose LLM checks degraded to
    safe defaults — either no key up front, or the API failing mid-run."""
    if not os.getenv("GROQ_API_KEY"):
        return [f"GROQ_API_KEY not set - T1/T4 degraded to safe defaults{_FLOOR}"]
    events = list(dict.fromkeys(llm.degradation_events()))  # dedup, keep order
    if events:
        return [f"{events[0]} - T1/T4 degraded to safe defaults{_FLOOR}"]
    return []


async def run_doctor_specs(
    specs: list[str], probe_config: ProbeConfig | None = None
) -> DoctorRun:
    """Connect FRESH sessions from the given specs, lint, and close them.

    This is the single orchestration path for both `mcpdoctor doctor` and the
    chatbot's /doctor. Fresh connections are load-bearing (spec §4/§5): lint
    probes cancel via asyncio.wait_for, which must never touch a session the
    chatbot owns — so /doctor reconnects rather than reusing chat sessions.
    """
    llm.reset_degradation()
    clients: dict[str, MCPClient] = {}
    async with AsyncExitStack() as stack:
        for spec in specs:
            command, args = spec_to_command(spec)
            key = unique_key(spec, set(clients))
            client = MCPClient(command, args)
            try:
                await stack.enter_async_context(client)
            except Exception as e:  # noqa: BLE001 - one friendly line, not a traceback
                raise ConnectError(
                    spec, " ".join([command, *args]), root_cause(e)
                ) from None
            clients[key] = client

        manifest = await gather_manifest(clients)
        if probe_config is not None:
            manifest.probe_config = probe_config
        sessions = {key: client.session() for key, client in clients.items()}
        results = await run_checks(sessions, manifest)
        notes = probe_notes(manifest)
    return DoctorRun(
        manifest=manifest, results=results, notes=notes, degraded=degraded_banners()
    )
