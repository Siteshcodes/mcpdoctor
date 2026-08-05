"""S1 hard-fail paths on synthetic manifests.

Intentional (per review): FastMCP can't easily fake a declared capability
whose list call errors, or an exposed primitive with no declared capability —
it auto-declares everything it registers. The live fixture covers the
declared-but-empty warn; these synthetic manifests cover the fail paths.
"""

import asyncio

from mcp import types

from mcpdoctor.doctor.checks_static import s1_capability_honesty
from mcpdoctor.doctor.manifest import ListOutcome, Manifest, ServerManifest


def run_s1(server: ServerManifest):
    results = asyncio.run(s1_capability_honesty({}, Manifest(servers=[server])))
    assert len(results) == 1
    return results[0]


def _tool() -> types.Tool:
    return types.Tool(name="ping", inputSchema={"type": "object", "properties": {}})


def test_declared_capability_with_erroring_list_fails():
    server = ServerManifest(
        name="synthetic",
        server_info_name="synthetic",
        capabilities=types.ServerCapabilities(
            prompts=types.PromptsCapability(listChanged=False)
        ),
        instructions=None,
        list_outcomes={"prompts": ListOutcome("error", "boom")},
    )
    r = run_s1(server)
    assert r.score == 0
    assert r.severity == "fail"
    assert "prompts capability declared but prompts/list error" in r.message


def test_exposed_tools_without_declared_capability_fails():
    server = ServerManifest(
        name="synthetic",
        server_info_name="synthetic",
        capabilities=types.ServerCapabilities(),  # nothing declared
        instructions=None,
        tools=[_tool()],
        list_outcomes={"tools": ListOutcome("ok")},
    )
    r = run_s1(server)
    assert r.score == 0
    assert "exposes tools without declaring the capability" in r.message


def test_clean_server_scores_two():
    server = ServerManifest(
        name="synthetic",
        server_info_name="synthetic",
        capabilities=types.ServerCapabilities(
            tools=types.ToolsCapability(listChanged=False)
        ),
        instructions="does things",
        tools=[_tool()],
        list_outcomes={"tools": ListOutcome("ok")},
    )
    r = run_s1(server)
    assert r.score == 2
    assert r.severity == "info"
