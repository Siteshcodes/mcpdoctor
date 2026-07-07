"""/doctor must NEVER reuse chat sessions (spec §4/§5): lint probes cancel via
asyncio.wait_for, which would cancel requests out from under a live chat. The
proof: give a Chat a spy client, run the doctor from the same spec, and assert
zero traffic crossed the spy — the doctor connected its own fresh sessions."""

import asyncio

from mcpdoctor.chatbot import Chat
from mcpdoctor.doctor.runner import run_doctor_specs


class SpyClient:
    """Records every interaction. Stands in for a chat-owned MCPClient."""

    def __init__(self):
        self.calls: list[str] = []

    def session(self):
        self.calls.append("session")
        return self

    async def list_tools(self):
        self.calls.append("list_tools")
        return []

    async def call_tool(self, *a, **k):
        self.calls.append("call_tool")
        raise AssertionError("doctor must not call tools on a chat session")

    def init_result(self):
        self.calls.append("init_result")
        raise AssertionError("doctor must not read a chat session's init result")


def test_doctor_run_does_not_touch_chat_owned_sessions():
    spy = SpyClient()
    # The chat "owns" this session for the same spec the doctor will lint.
    Chat(llm=None, clients={"badserver": spy}, server_specs=["fixtures/badserver.py"])

    run = asyncio.run(run_doctor_specs(["fixtures/badserver.py"]))

    assert run.results, "doctor should have produced findings from a fresh session"
    assert spy.calls == [], f"lint traffic leaked onto the chat session: {spy.calls}"
