"""otherserver — a minimal, well-behaved fixture whose only job is to expose
a tool named `search`, colliding with badserver's `search` when both are
linted in one doctor run (T6 hard collision → score 0)."""

import re

from pydantic import Field

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP(
    "otherserver",
    log_level="ERROR",
    instructions="Toy search server used by mcpdoctor's test suite. "
    "Exposes a single keyword search tool over a static in-memory corpus.",
)


@mcp.tool(
    name="search",
    description="Search the demo corpus by keyword. Use this when the user "
    "asks to find a document by topic, e.g. 'search for condenser reports'. "
    "Matches titles only, not full text.",
)
def search(
    query: str = Field(description="Keyword to look for, e.g. 'condenser'"),
) -> str:
    return "no results in demo corpus"


# T4 exemplary pole (Phase 3): a read-only tool whose error names the field,
# the expected format, AND the received value — so the heal loop repairs a
# bad call in ONE retry. readOnlyHint=True lets the doctor re-execute the
# repaired call live (spec §4/§5) and confirm the fix actually works → T4 = 2.
@mcp.tool(
    name="fetch_metrics",
    description="Fetch aggregated metrics for a single calendar day. Use this "
    "when the user asks for stats on a specific date, e.g. fetch_metrics with "
    "date 2026-07-06.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
def fetch_metrics(
    date: str = Field(description="ISO date, YYYY-MM-DD, e.g. 2026-07-06"),
) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        # Exemplary error: field + expected format + received value.
        raise ValueError(f"date must be YYYY-MM-DD, got {date!r}")
    return f"metrics for {date}: 42 events, 7 alerts"


# Well-documented template with an instantiable example URI — proves the
# R4 = 2 path (documented + deterministic example read works).
@mcp.resource(
    "demo://item/{n}",
    description="A demo corpus item by number. n is 1-3, e.g. demo://item/1",
    mime_type="text/plain",
)
def item(n: str) -> str:
    return f"demo item {n}"


# Documented prompt with a described, required argument — gives P2 live
# coverage and proves P3 renders with deterministic filler args.
@mcp.prompt(
    name="summarize_hits",
    description="Summarize search hits on a topic for the user.",
)
def summarize_hits(
    topic: str = Field(description="Topic that was searched, e.g. 'condenser'"),
) -> str:
    return f"Summarize the search results about {topic} in two sentences."


if __name__ == "__main__":
    mcp.run(transport="stdio")
