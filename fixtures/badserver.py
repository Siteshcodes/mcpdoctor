"""badserver — a deliberately terrible MCP server.

Every flaw below is planted on purpose and tagged with the mcpdoctor check ID
that should catch it. This file is both the pytest fixture and the demo star:
run the doctor against it and watch every category light up red.

Safety note: nothing in here touches real data. `delete_everything` deletes
nothing — it exists only so the linter can flag its missing annotations, and
the probe engine must NEVER call it (spec §5).
"""

import os
from pathlib import Path

from pydantic import Field

from mcp.server.fastmcp import FastMCP

# Safety tripwire: if ANYTHING ever invokes delete_everything, this sentinel
# file appears and the test suite fails loudly. Executable proof that the
# probe engine's destructive-skip rule (spec §5) actually held — not just
# absence of a crash.
TRIPWIRE = Path(os.environ.get("MCPDOCTOR_TRIPWIRE", str(Path(__file__).parent / ".tripwire")))

# S2: no `instructions` field — the server gives the LLM zero usage guidance.
# P1: no prompts defined anywhere in this file.
# S1: FastMCP still auto-declares the prompts capability, so the server
#     declares a capability with nothing registered behind it.
# R5: no resources.subscribe / listChanged support declared.
mcp = FastMCP("badserver", log_level="ERROR")


# T1: one-word description says nothing about what/when/constraints.
# T2: `data` param has no description.
# T6: `process` is on the generic-name blocklist.
# T4 (Phase 3): error text is just "400" — unrepairable by an agent.
@mcp.tool(name="process", description="Processes.")
def process(data: str) -> str:
    raise ValueError("400")


# T1 / T2 / T6: same flaws as `process` — vague, undocumented, generic name.
@mcp.tool(name="handle", description="Handles.")
def handle(input: str) -> str:
    raise ValueError("400")


# T2: the classic — `date: string` with no description, format, pattern,
#     enum, or example. ISO? "tomorrow"? The model finds out by erroring.
# T6: near-duplicate of `get_dates` (Levenshtein distance 1).
# T4 (Phase 3): cryptic "400" error.
@mcp.tool(name="get_data", description="Gets data.")
def get_data(date: str) -> str:
    raise ValueError("400")


# T6: near-duplicate of `get_data`.
@mcp.tool(name="get_dates", description="Gets dates.")
def get_dates(date: str) -> str:
    raise ValueError("400")


# T6: exact cross-server collision — fixtures/otherserver.py also exposes
#     `search`. Run both under one doctor session to trigger the hard fail.
# T2: `query` has no description and no format hint.
# T3: no example anywhere on this server — every tool scores 0.
@mcp.tool(name="search", description="Search.")
def search(query: str) -> str:
    raise ValueError("400")


# T4 GARBAGE TRAP (spec §4): declares a date format it never validates.
#     pydantic only enforces `str`, so a bad_format probe ("July 5th")
#     sails through and the call SUCCEEDS — the worst possible outcome:
#     a deliberately invalid call that works means validation is broken.
# T2: `when` also has no description (consistent with the rest).
@mcp.tool(name="log_event", description="Logs.")
def log_event(when: str = Field(json_schema_extra={"format": "date"})) -> str:
    return "logged"


# T5: destructive name with NO annotations — no destructiveHint, nothing.
#     Indistinguishable from a read-only tool by metadata alone → hard fail.
#     Probe safety (spec §5): the doctor must never call this without --unsafe.
@mcp.tool(name="delete_everything", description="Deletes.")
def delete_everything(target: str) -> str:
    # Deletes nothing — but proves it was called by tripping the sentinel.
    TRIPWIRE.write_text("delete_everything was invoked", encoding="utf-8")
    raise ValueError("400")


# R2 (Phase 2): ~40k-token context bomb (~160k chars at the len/4 heuristic).
@mcp.resource("data://big-report", mime_type="text/plain")
def big_report() -> str:
    line = "SECTION 7.3.1 — condenser tower flange torque readings (kNm): "
    return (line + "42.1, 42.3, 41.9, 42.0\n") * 1800


# R3 (Phase 2): declares application/json but returns plain prose — the
#     model plans json.loads and the plan breaks.
@mcp.resource("data://config", mime_type="application/json")
def config() -> str:
    return "config is fine, trust me"


# R4: resource template with an undocumented {key} param — no description
#     at all, so the model must guess how to construct the URI.
@mcp.resource("data://entry/{key}")
def entry(key: str) -> str:
    return "?"


if __name__ == "__main__":
    mcp.run(transport="stdio")
