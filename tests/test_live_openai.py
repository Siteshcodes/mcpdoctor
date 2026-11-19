"""Opt-in OpenAI requests against a local, read-only MCP fixture.

Run: uv run pytest -m live tests/test_live_openai.py -v -s
Requires OPENAI_API_KEY; real requests use API quota. No other servers are used.
"""

import json
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from openai import OpenAIError

from mcpdoctor import chatbot, llm
from mcpdoctor.chatbot import Chat
from mcpdoctor.doctor.results import letter_grade, overall_score
from mcpdoctor.mcp_client import MCPClient

pytestmark = pytest.mark.live
ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "fixtures" / "otherserver.py"


class BoundedOpenAI(llm.OpenAILLM):
    """Limit this test's API usage, including the JSON helper's retries."""

    def __init__(self):
        super().__init__()
        self.requests = 0

    def _count(self):
        if self.requests >= 32:
            raise RuntimeError("Live validation reached its 32-request limit")
        self.requests += 1

    def _complete(self, prompt):
        self._count()
        try:
            return super()._complete(prompt)
        except OpenAIError as error:
            print(llm.api_error_hint(error), flush=True)
            raise RuntimeError("OpenAI live judge request failed") from None

    def chat(self, messages, tools=None, temperature=1.0):
        self._count()
        try:
            return super().chat(messages, tools, temperature)
        except OpenAIError as error:
            raise RuntimeError(llm.api_error_hint(error)) from None


class ObservedClient(MCPClient):
    def __init__(self):
        super().__init__(sys.executable, [str(SERVER)])
        self.traffic = []
        self.calls = []

    async def list_tools(self):
        self.traffic.append("list_tools")
        return await super().list_tools()

    async def call_tool(self, name, args, read_timeout_seconds=None):
        self.traffic.append("call_tool")
        self.calls.append((name, dict(args)))
        return await super().call_tool(name, args, read_timeout_seconds)


@pytest.fixture
def live_openai(monkeypatch):
    load_dotenv(ROOT / ".env")
    if not llm.has_api_key():
        pytest.skip("OPENAI_API_KEY not set")
    adapter = BoundedOpenAI()
    # Replace the suite's offline stand-in only for this explicitly live test.
    monkeypatch.setattr(llm, "json_call", adapter.json_call)
    llm.reset_degradation()
    yield adapter
    if adapter._client is not None:
        adapter._client.close()
    llm.reset_degradation()


async def test_openai_tools_repair_and_doctor_keep_chat_usable(live_openai, monkeypatch):
    runs = []
    run_doctor = chatbot.run_doctor_specs

    async def record_doctor(specs, config):
        run = await run_doctor(specs, config)
        runs.append(run)
        return run

    monkeypatch.setattr(chatbot, "run_doctor_specs", record_doctor)
    async with ObservedClient() as client:
        chat = Chat(live_openai, {"otherserver": client}, [str(SERVER)])
        session = client.session()

        print("Live: asking OpenAI to call fetch_metrics", flush=True)
        reply = await chat.send("Use fetch_metrics to fetch metrics for 2026-07-05.")
        assert ("fetch_metrics", {"date": "2026-07-05"}) in client.calls
        assert reply.strip()
        assert any(
            isinstance(message, dict) and message.get("role") == "tool"
            and "42 events, 7 alerts" in message["content"]
            for message in chat.messages
        )

        print("Live: asking OpenAI to call search", flush=True)
        before = len(client.calls)
        await chat.send("Use search with query condenser, then report its result.")
        assert any(name == "search" for name, _ in client.calls[before:])

        print("Live: injecting a bad date to exercise real OpenAI repair", flush=True)
        tool = next(t for t in await client.list_tools() if t.name == "fetch_metrics")
        before = len(client.calls)
        repaired = await chat._run_tool(
            client, tool.name, tool.inputSchema, {"date": "July 5th, 2026"},
        )
        assert "metrics for 2026-07-05: 42 events, 7 alerts" in repaired
        assert 2 <= len(client.calls) - before <= 3  # initial call + at most two repairs
        assert not llm.degradation_events()

        print("Live: /doctor with fresh sessions and real OpenAI judges", flush=True)
        traffic_before = list(client.traffic)
        history_before = list(chat.messages)
        report = await chat.handle_command("/doctor")
        assert "Overall:" in report
        assert len(runs) == 1
        run = runs[0]
        assert not run.degraded, run.degraded
        assert client.traffic == traffic_before
        assert chat.messages == history_before
        assert client.session() is session
        repairs = [r for r in run.results if r.id == "T4"]
        assert {r.target for r in repairs} == {"fetch_metrics", "search"}
        assert all(r.score == 2 and "(live)" in r.message for r in repairs)
        assert all(
            used <= run.manifest.probe_config.budget_per_server
            for used in run.manifest._probe_run.budget_used.values()
        )

        calls_before = live_openai.requests
        assert "will not probe destructive" in await chat.handle_command("/doctor --unsafe")
        assert live_openai.requests == calls_before
        assert client.traffic == traffic_before

        print("Live: calling a tool again after /doctor", flush=True)
        before = len(client.calls)
        reply = await chat.send("Use fetch_metrics to fetch metrics for 2026-07-06.")
        assert reply.strip()
        assert ("fetch_metrics", {"date": "2026-07-06"}) in client.calls[before:]
        assert client.session() is session
        assert not llm.degradation_events()

        score = overall_score(run.results)
        print(json.dumps({
            "model": live_openai.model,
            "openai_requests": live_openai.requests,
            "score": round(score, 2),
            "grade": letter_grade(score),
            "probe_budget_used": run.manifest._probe_run.budget_used,
            "degraded": run.degraded,
            "chat_session_preserved": True,
        }), flush=True)
