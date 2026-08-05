"""Gather everything the doctor inspects — once, at startup, from all
connected servers (spec §1).

Each list call's outcome is recorded explicitly because S1 grades the
difference between "server doesn't support prompts" (fine), "declares the
capability but nothing is registered" (warn), and "declares it but the list
call errors" (fail).
"""

from dataclasses import dataclass, field
from typing import Awaitable, Callable

from mcp import McpError, types
from mcp.types import METHOD_NOT_FOUND

from mcpdoctor.doctor.probes import ProbeConfig
from mcpdoctor.mcp_client import MCPClient


@dataclass
class ListOutcome:
    status: str  # "ok" | "empty" | "error" | "unsupported"
    error: str | None = None


@dataclass
class ServerManifest:
    name: str  # unique key for this doctor run (also the sessions dict key)
    server_info_name: str | None  # what the server calls itself
    capabilities: types.ServerCapabilities | None
    instructions: str | None
    tools: list[types.Tool] = field(default_factory=list)
    resources: list[types.Resource] = field(default_factory=list)
    resource_templates: list[types.ResourceTemplate] = field(default_factory=list)
    prompts: list[types.Prompt] = field(default_factory=list)
    # keys: "tools", "resources", "resource_templates", "prompts"
    list_outcomes: dict[str, ListOutcome] = field(default_factory=dict)


@dataclass
class Manifest:
    servers: list[ServerManifest]
    # Probe-engine knobs for this run (spec §5); CLI/tests override.
    probe_config: ProbeConfig = field(default_factory=ProbeConfig)
    # Cached ProbeRun, filled by checks_probe on first use so R1/R2/R3/S3
    # share one execution and one budget. Not part of the gathered data.
    _probe_run: object | None = field(default=None, repr=False, compare=False)


async def _gather_list(fetch: Callable[[], Awaitable[list]]) -> tuple[list, ListOutcome]:
    try:
        items = await fetch()
    except McpError as e:
        if e.error.code == METHOD_NOT_FOUND:
            return [], ListOutcome("unsupported", str(e))
        return [], ListOutcome("error", str(e))
    except Exception as e:
        return [], ListOutcome("error", str(e))
    return items, ListOutcome("ok" if items else "empty")


async def gather_server(name: str, client: MCPClient) -> ServerManifest:
    init = client.init_result()
    manifest = ServerManifest(
        name=name,
        server_info_name=init.serverInfo.name if init.serverInfo else None,
        capabilities=init.capabilities,
        instructions=init.instructions,
    )

    fetchers = {
        "tools": client.list_tools,
        "resources": client.list_resources,
        "resource_templates": client.list_resource_templates,
        "prompts": client.list_prompts,
    }
    for kind, fetch in fetchers.items():
        items, outcome = await _gather_list(fetch)
        setattr(manifest, kind, items)
        manifest.list_outcomes[kind] = outcome
    return manifest


async def gather_manifest(clients: dict[str, MCPClient]) -> Manifest:
    return Manifest(
        servers=[
            await gather_server(name, client) for name, client in clients.items()
        ]
    )
