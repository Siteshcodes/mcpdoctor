"""Self-healing loop — shared by the chatbot (runtime) and the doctor (T4).

A tool call fails; heal asks the LLM to propose corrected arguments from the
error text + schema, then retries via an `execute` callback. That callback is
the policy seam:
- the chatbot passes real execution against the live server (the human
  intended the call, so retries run for real);
- T4 passes an execute that live-runs ONLY provably read-only tools and
  otherwise validates the proposed args locally (spec §4/§5 lint-repair
  safety) — a repaired call is a valid call, and a valid call must never
  mutate someone's data during a lint.

One module, two features — the whole demo hinges on this being literally the
same code path.
"""

import json
from dataclasses import dataclass
from typing import Awaitable, Callable

from mcpdoctor import llm

MAX_ATTEMPTS = 2  # total repair attempts before giving up

# execute(candidate_args) -> (ok, error_text_if_not_ok)
Execute = Callable[[dict], Awaitable[tuple[bool, str]]]

_REPAIR_PROMPT = """An AI agent's MCP tool call failed. Propose corrected arguments.
Tool schema: {schema}
Failed arguments: {args}
Error returned: {error}

Reply with ONLY JSON: {{"args": {{corrected arguments as an object}}}}"""


@dataclass
class HealResult:
    healed: bool
    attempts: int  # repair attempts consumed (1..MAX_ATTEMPTS)
    args: dict | None  # the args that finally worked / validated
    detail: str  # last error, or "ok"


async def repair_args(
    error_text: str, tool_schema: dict, original_args: dict
) -> dict | None:
    """One LLM shot proposing corrected args, or None if it declined."""
    prompt = _REPAIR_PROMPT.format(
        schema=json.dumps(tool_schema),
        args=json.dumps(original_args),
        error=error_text,
    )
    proposed = llm.json_call(prompt, default={}).get("args")
    return proposed if isinstance(proposed, dict) else None


async def heal(
    execute: Execute,
    error_text: str,
    tool_schema: dict,
    original_args: dict,
) -> HealResult:
    """Propose → retry, up to MAX_ATTEMPTS. Each failed retry feeds its own
    error back into the next proposal."""
    current_error, current_args = error_text, original_args
    for attempt in range(1, MAX_ATTEMPTS + 1):
        proposed = await repair_args(current_error, tool_schema, current_args)
        if proposed is None:
            return HealResult(False, attempt, None, "no repair proposed")
        ok, err = await execute(proposed)
        if ok:
            return HealResult(True, attempt, proposed, "ok")
        current_error, current_args = err, proposed
    return HealResult(False, MAX_ATTEMPTS, None, current_error)
