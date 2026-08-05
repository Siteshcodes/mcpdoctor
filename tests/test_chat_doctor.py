"""/doctor inside the chatbot (spec §4/§5): reconnects fresh from the chat's
own specs, never touching chat-owned sessions, and refuses --unsafe."""

import asyncio

from mcpdoctor.chatbot import Chat


class SilentSpy:
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
        raise AssertionError("/doctor must not reach the chat's own session")


def _chat_with_spec() -> tuple[Chat, SilentSpy]:
    spy = SilentSpy()
    chat = Chat(
        llm=None, clients={"badserver": spy}, server_specs=["fixtures/badserver.py"]
    )
    return chat, spy


def test_doctor_no_args_lints_chats_own_specs():
    chat, spy = _chat_with_spec()
    out = asyncio.run(chat.handle_command("/doctor"))
    assert "Overall:" in out  # a full report came back
    assert spy.calls == []  # ...from fresh sessions, not the chat's


def test_doctor_refuses_unsafe_from_chat():
    chat, _ = _chat_with_spec()
    out = asyncio.run(chat.handle_command("/doctor --unsafe"))
    assert "will not probe destructive" in out
    assert "mcpdoctor doctor --unsafe" in out


def test_unknown_command_hints():
    chat, _ = _chat_with_spec()
    out = asyncio.run(chat.handle_command("/wat"))
    assert "unknown command" in out and "/doctor" in out


def test_doctor_with_no_specs_says_so():
    chat = Chat(llm=None, clients={}, server_specs=[])
    out = asyncio.run(chat.handle_command("/doctor"))
    assert "no server specs" in out


# --- REPL resilience: an LLM API failure must not kill the chat -------------


class BoomLLM:
    def chat(self, messages, tools=None, temperature=1.0):
        raise RuntimeError("RateLimitError: free-tier limit reached")


def test_send_restores_history_on_llm_failure():
    import pytest

    chat = Chat(llm=BoomLLM(), clients={})
    with pytest.raises(RuntimeError):
        asyncio.run(chat.send("hi"))
    # no dangling user/tool_call messages to poison the next turn
    assert chat.messages == []


def test_repl_survives_llm_failure(monkeypatch, capsys):
    chat = Chat(llm=BoomLLM(), clients={})
    prompts = iter(["hello"])

    def fake_input(_prompt=""):
        try:
            return next(prompts)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", fake_input)
    asyncio.run(chat.repl())  # must return cleanly, not raise

    out = capsys.readouterr().out
    assert "[chat error]" in out
    assert "Traceback" not in out
