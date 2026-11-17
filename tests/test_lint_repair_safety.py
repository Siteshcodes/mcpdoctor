"""SAFETY PROOF (spec §4/§5): a lint-time repair never executes a repaired
call on a non-read-only tool. A repaired call is a VALID call; executing it
against a mutating tool would mutate real data.

These tests use make_repair_executor directly with a spy session that fails
the test if call_tool is ever invoked on a non-read-only tool."""

import pytest
from mcp import types

from mcpdoctor.doctor.checks_probe import (
    ProbeRun,
    is_read_only,
    make_repair_executor,
)
from mcpdoctor.doctor.manifest import Manifest, ServerManifest


def tool(name: str, read_only: bool = False) -> types.Tool:
    return types.Tool(
        name=name,
        description="x",
        inputSchema={
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
        annotations=types.ToolAnnotations(readOnlyHint=True) if read_only else None,
    )


class ExplodingSession:
    """Any call_tool here means the safety rule was violated."""

    async def call_tool(self, *a, **k):
        raise AssertionError("lint executed a repaired call on a non-read-only tool")


def _manifest() -> Manifest:
    return Manifest(
        servers=[ServerManifest("s", "s", capabilities=None, instructions=None)]
    )


async def test_non_read_only_tool_is_validated_not_executed():
    run = ProbeRun()
    t = tool("update_thing", read_only=False)  # not in READ_ONLY_WORDS
    execute, state = make_repair_executor(
        ExplodingSession(), _manifest(), run, "s", t, t.inputSchema
    )
    # A schema-VALID repair: would succeed live, but must be validated locally.
    ok, err = await execute({"target": "x"})
    assert ok and err == ""
    assert state["executed_live"] is False
    assert not any(r.kind == "repair_exec" for r in run.records)


async def test_non_read_only_invalid_repair_fails_validation():
    run = ProbeRun()
    t = tool("write_file", read_only=False)
    execute, state = make_repair_executor(
        ExplodingSession(), _manifest(), run, "s", t, t.inputSchema
    )
    ok, err = await execute({})  # missing required 'target'
    assert not ok
    assert "target" in err
    assert state["executed_live"] is False


async def test_read_only_tool_executes_live_and_records():
    run = ProbeRun()
    calls = []

    class OkSession:
        async def call_tool(self, name, args, **k):
            calls.append((name, args))
            return types.CallToolResult(
                content=[types.TextContent(type="text", text="ok")], isError=False
            )

    t = tool("get_thing", read_only=False)  # read-only by NAME token "get"
    assert is_read_only(t)
    execute, state = make_repair_executor(
        OkSession(), _manifest(), run, "s", t, t.inputSchema
    )
    ok, err = await execute({"target": "x"})
    assert ok
    assert state["executed_live"] is True
    assert calls == [("get_thing", {"target": "x"})]
    assert [r.kind for r in run.records] == ["repair_exec"]


async def test_read_only_repair_counts_against_budget():
    from mcpdoctor.doctor.probes import ProbeConfig

    manifest = _manifest()
    manifest.probe_config = ProbeConfig(budget_per_server=0)  # no budget left
    run = ProbeRun()

    t = tool("read_thing", read_only=True)
    execute, state = make_repair_executor(
        ExplodingSession(), manifest, run, "s", t, t.inputSchema
    )
    # Budget exhausted -> falls back to local validation, never executes.
    ok, err = await execute({"target": "x"})
    assert ok
    assert state["executed_live"] is False


def test_read_only_classification():
    assert is_read_only(tool("get_user"))
    assert is_read_only(tool("search"))
    assert is_read_only(tool("fetch_metrics"))
    assert not is_read_only(tool("process"))
    assert not is_read_only(tool("update_record"))
    assert is_read_only(tool("mutate", read_only=True))  # annotation wins


@pytest.mark.parametrize("name,annotations", [
    ("get_and_delete", types.ToolAnnotations(readOnlyHint=True)),
    ("get_record", types.ToolAnnotations(destructiveHint=True, readOnlyHint=True)),
    ("get_record", types.ToolAnnotations(readOnlyHint=False)),
])
async def test_mutation_signals_override_read_only_names(name, annotations):
    t = tool(name)
    t.annotations = annotations
    assert not is_read_only(t)
    execute, state = make_repair_executor(
        ExplodingSession(), _manifest(), ProbeRun(), "s", t, t.inputSchema
    )
    assert await execute({"target": "x"}) == (True, "")
    assert state["executed_live"] is False
