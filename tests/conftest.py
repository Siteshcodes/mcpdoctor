import asyncio
import json
import re
import sys
from contextlib import AsyncExitStack
from pathlib import Path

import pytest

from mcpdoctor import llm
from mcpdoctor.doctor.manifest import Manifest, gather_manifest
from mcpdoctor.doctor.results import CheckResult
from mcpdoctor.doctor.runner import run_checks
from mcpdoctor.doctor.vocab import name_tokens
from mcpdoctor.mcp_client import MCPClient

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
TRIPWIRE = FIXTURES / ".tripwire"  # written by badserver's delete_everything

_SCHEMA_RE = re.compile(r"Tool schema: (.+)")


def _valid_args_from_schema(schema: dict) -> dict:
    """Deterministic stand-in for what a real repair LLM would return: the
    minimal schema-valid arg set, with date-ish string params filled with a
    real ISO date so exemplary read-only tools (fetch_metrics) heal in 1."""
    props = schema.get("properties", {})
    required = schema.get("required", list(props))
    args: dict = {}
    for name in required:
        spec = props.get(name, {})
        t = spec.get("type")
        if t == "string":
            date_ish = spec.get("format") == "date" or (
                name_tokens(name) & {"date", "time", "when"}
            )
            args[name] = "2026-07-06" if date_ish else "x"
        elif t in ("integer", "number"):
            args[name] = 1
        elif t == "boolean":
            args[name] = False
        elif t == "array":
            args[name] = []
        elif t == "object":
            args[name] = {}
        else:
            args[name] = "x"
    return args


def _fake_json_call(prompt: str, *, default: dict) -> dict:
    """Stands in for OpenAI across the whole suite. Dispatches on the prompt so
    heal, the T4 fix_hint judge, and the T1 judge each get a plausible,
    deterministic reply - the real check code runs unchanged."""
    if "grading an MCP tool description" in prompt:
        return {
            "score": 2,
            "reason": "states what and when",
            "suggested_description": "Search documents by title; use when the "
            "user names a topic. Matches titles only, e.g. 'condenser'.",
        }
    if "what the error message should have said" in prompt:
        return {"fix_hint": "name the field, the expected format, and the received value"}
    if '"args"' in prompt:  # heal repair prompt
        match = _SCHEMA_RE.search(prompt)
        schema = json.loads(match.group(1)) if match else {}
        return {"args": _valid_args_from_schema(schema)}
    return dict(default)


@pytest.fixture(scope="session", autouse=True)
def _mock_openai():
    """No test hits the network. Individual tests may still monkeypatch
    llm.json_call for their own scenarios; this is the default."""
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    mp.setattr(llm, "json_call", _fake_json_call)
    yield
    mp.undo()


def run_doctor(*scripts: str) -> tuple[Manifest, list[CheckResult]]:
    """Spawn fixture servers over stdio, gather the manifest, run all checks.

    Sync on purpose: Phase-1 checks only need the gathered data, so tests can
    stay synchronous and let asyncio.run own the event loop.
    """

    async def _run():
        async with AsyncExitStack() as stack:
            clients: dict[str, MCPClient] = {}
            for script in scripts:
                clients[Path(script).stem] = await stack.enter_async_context(
                    MCPClient(command=sys.executable, args=[str(FIXTURES / script)])
                )
            manifest = await gather_manifest(clients)
            sessions = {key: c.session() for key, c in clients.items()}
            results = await run_checks(sessions, manifest)
        return manifest, results

    return asyncio.run(_run())


@pytest.fixture(scope="session")
def badserver_run() -> tuple[Manifest, list[CheckResult]]:
    TRIPWIRE.unlink(missing_ok=True)  # a stale sentinel must not mask/fake a trip
    return run_doctor("badserver.py")


@pytest.fixture(scope="session")
def otherserver_run() -> tuple[Manifest, list[CheckResult]]:
    return run_doctor("otherserver.py")


@pytest.fixture(scope="session")
def collision_run() -> tuple[Manifest, list[CheckResult]]:
    TRIPWIRE.unlink(missing_ok=True)
    return run_doctor("badserver.py", "otherserver.py")
