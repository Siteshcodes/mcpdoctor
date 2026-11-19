"""A well-behaved demo server for audits, chat, and resource notifications.

Its `search` name deliberately collides with badserver when audited together.
The catalog can be published internally; neither tool mutates server state.
"""

import re
from contextlib import asynccontextmanager

import anyio
from pydantic import AnyUrl, Field

from mcp.server.fastmcp import FastMCP
from mcp.server.lowlevel import NotificationOptions
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, Resource, ToolAnnotations


class DemoCatalog:
    def __init__(self):
        self.items = {f"demo://item/{n}": f"demo item {n}" for n in range(1, 4)}
        self.subscriptions: dict[ServerSession, set[str]] = {}

    def read(self, uri: AnyUrl | str) -> str:
        try:
            return self.items[str(uri)]
        except KeyError:
            raise McpError(ErrorData(
                code=-32002, message="Resource not found", data={"uri": str(uri)},
            )) from None

    async def publish_item(self, n: int, text: str) -> None:
        """Publish a local catalog change, without exposing a mutating tool."""
        if type(n) is not int or n < 1:
            raise ValueError("item number must be a positive integer")
        uri = f"demo://item/{n}"
        added = uri not in self.items
        if self.items.get(uri) == text:
            return
        self.items[uri] = text
        for session, subscriptions in list(self.subscriptions.items()):
            try:
                if added:
                    await session.send_resource_list_changed()
                elif uri in subscriptions:
                    await session.send_resource_updated(AnyUrl(uri))
            except (anyio.BrokenResourceError, anyio.ClosedResourceError):
                self.subscriptions.pop(session, None)


catalog = DemoCatalog()


@asynccontextmanager
async def resource_lifespan(app):
    state = {"session": None}
    try:
        yield state
    finally:
        catalog.subscriptions.pop(state["session"], None)


mcp = FastMCP(
    "otherserver",
    log_level="ERROR",
    lifespan=resource_lifespan,
    instructions="Use this demo server to test MCP clients, not for production data. "
    "Use search for title keywords; its demo corpus is empty, so it returns no hits. "
    "Use fetch_metrics for one date in YYYY-MM-DD format; counts are fixed demo values. "
    "Both tools are read-only and make no external requests. "
    "List and read demo://item/{n} resources for sample text. Subscribe to an item "
    "for content updates, and refresh the resource list after a list-change notification. "
    "Use summarize_hits to prepare a two-sentence summary prompt for a searched topic.",
)


def resource_session() -> ServerSession:
    context = mcp._mcp_server.request_context
    context.lifespan_context["session"] = context.session
    catalog.subscriptions.setdefault(context.session, set())
    return context.session


# FastMCP has no subscription decorators. Register the official SDK's
# low-level handlers, and enable their capabilities in run_server below.
@mcp._mcp_server.list_resources()
async def list_items() -> list[Resource]:
    resource_session()
    return [Resource(
        uri=AnyUrl(uri), name=f"Demo item {uri.rsplit('/', 1)[-1]}",
        description="Sample text for testing MCP resource reads and subscriptions.",
        mimeType="text/plain",
    ) for uri in catalog.items]


@mcp._mcp_server.read_resource()
async def read_item(uri: AnyUrl) -> list[ReadResourceContents]:
    resource_session()
    return [ReadResourceContents(content=catalog.read(uri), mime_type="text/plain")]


@mcp._mcp_server.subscribe_resource()
async def subscribe_item(uri: AnyUrl) -> None:
    catalog.read(uri)  # Reject unknown URIs before recording the subscription.
    catalog.subscriptions[resource_session()].add(str(uri))


@mcp._mcp_server.unsubscribe_resource()
async def unsubscribe_item(uri: AnyUrl) -> None:
    catalog.subscriptions[resource_session()].discard(str(uri))


@mcp.tool(
    name="search",
    description="Search the demo corpus by keyword. Use this when the user "
    "asks to find a document by topic, e.g. 'search for condenser reports'. "
    "Matches titles only, not full text.",
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False,
    ),
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
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False,
    ),
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
    description="A demo item by number. n is a positive integer from the resource "
    "list (initially 1-3), e.g. demo://item/1",
    mime_type="text/plain",
)
def item(n: str) -> str:
    return catalog.read(f"demo://item/{n}")


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


async def run_server(read_stream, write_stream) -> None:
    server = mcp._mcp_server
    options = server.create_initialization_options(
        notification_options=NotificationOptions(resources_changed=True),
    )
    # This SDK defaults subscribe to False even with handlers registered.
    # Both handlers and the catalog's notification publisher are implemented above.
    options.capabilities.resources.subscribe = True
    await server.run(read_stream, write_stream, options)


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await run_server(read_stream, write_stream)


if __name__ == "__main__":
    anyio.run(main)
