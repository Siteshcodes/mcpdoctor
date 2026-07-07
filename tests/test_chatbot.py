"""Chatbot heal wiring: a bad tool call recovers and prints [self-healed].

Everything is faked - no MCP server, no Groq. The point is to prove the
runtime path (tool error -> heal -> visible recovery -> corrected result fed
back to the model) is wired correctly."""

import json
from types import SimpleNamespace

from mcp.types import CallToolResult, TextContent, Tool

from mcpdoctor import llm
from mcpdoctor.chatbot import Chat


def _tool_call(name, args):
    return SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def _text_result(text, is_error=False):
    return CallToolResult(content=[TextContent(type="text", text=text)], isError=is_error)


class FakeLLM:
    """Turn 1: call log_event with a wrong-typed arg. Turn 2: final text."""

    def __init__(self):
        self.turn = 0

    def chat(self, messages, tools=None):
        self.turn += 1
        if self.turn == 1:
            return SimpleNamespace(
                tool_calls=[_tool_call("log_event", {"when": 42})], content=None
            )
        return SimpleNamespace(tool_calls=None, content="done")


class FakeClient:
    def __init__(self):
        self.calls = []

    async def list_tools(self):
        return [
            Tool(
                name="log_event",
                description="Logs an event on a date.",
                inputSchema={
                    "type": "object",
                    "properties": {"when": {"type": "string"}},
                    "required": ["when"],
                },
            )
        ]

    async def call_tool(self, name, args, read_timeout_seconds=None):
        self.calls.append(args)
        # First call (the wrong-typed 42) errors; a string retry succeeds.
        if isinstance(args.get("when"), str):
            return _text_result("logged")
        return _text_result("Error: when must be a string", is_error=True)


async def test_chatbot_self_heals_and_reports(monkeypatch, capsys):
    monkeypatch.setattr(
        llm, "json_call", lambda prompt, *, default: {"args": {"when": "2026-07-06"}}
    )
    client = FakeClient()
    chat = Chat(FakeLLM(), {"srv": client})

    reply = await chat.send("log an event")

    assert reply == "done"
    out = capsys.readouterr().out
    assert "[self-healed] log_event" in out
    # the corrected result, not the error, was fed back to the model
    tool_msgs = [m for m in chat.messages if isinstance(m, dict) and m.get("role") == "tool"]
    assert tool_msgs and tool_msgs[-1]["content"] == "logged"
    assert client.calls == [{"when": 42}, {"when": "2026-07-06"}]


async def test_chatbot_reports_unhealable_error(monkeypatch, capsys):
    # LLM proposes nothing repairable -> no [self-healed], error handed back.
    monkeypatch.setattr(llm, "json_call", lambda prompt, *, default: dict(default))
    client = FakeClient()

    class AlwaysError(FakeClient):
        async def call_tool(self, name, args, read_timeout_seconds=None):
            self.calls.append(args)
            return _text_result("Error: 400", is_error=True)

    client = AlwaysError()
    chat = Chat(FakeLLM(), {"srv": client})
    await chat.send("log an event")

    out = capsys.readouterr().out
    assert "[self-healed]" not in out
    tool_msgs = [m for m in chat.messages if isinstance(m, dict) and m.get("role") == "tool"]
    assert tool_msgs[-1]["content"] == "Error: 400"
