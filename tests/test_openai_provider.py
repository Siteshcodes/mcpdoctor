"""Exercise the real OpenAI SDK through a local, non-network HTTP transport."""

import json

import httpx
import openai
import pytest
from mcp.types import CallToolResult, TextContent, Tool
from typer.testing import CliRunner

from mcpdoctor import cli, llm
from mcpdoctor.chatbot import Chat
from mcpdoctor.doctor.runner import degraded_banners


def completion(content=None, tool_calls=None):
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": llm.DEFAULT_MODEL,
        "choices": [{
            "index": 0,
            "finish_reason": "tool_calls" if tool_calls else "stop",
            "message": message,
        }],
    }


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    real_client = openai.OpenAI
    clients = []

    def make(*responses):
        pending = iter(responses)
        requests = []

        def handle(request):
            requests.append(request)
            status, body = next(pending)
            return httpx.Response(status, json=body)

        def client_factory(**kwargs):
            client = real_client(
                http_client=httpx.Client(transport=httpx.MockTransport(handle)),
                **kwargs,
            )
            clients.append(client)
            return client

        monkeypatch.setattr(openai, "OpenAI", client_factory)
        return llm.OpenAILLM(), requests

    llm.reset_degradation()
    yield make
    for client in clients:
        client.close()
    llm.reset_degradation()


def test_model_configuration_does_not_reuse_old_groq_model(monkeypatch):
    monkeypatch.setenv("MODEL", "llama-3.3-70b-versatile")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert llm.OpenAILLM().model == "gpt-5.4-mini"
    monkeypatch.setenv("OPENAI_MODEL", " gpt-5.4-mini-2026-03-17 ")
    assert llm.OpenAILLM().model == "gpt-5.4-mini-2026-03-17"
    assert llm.OpenAILLM(model="explicit-model").model == "explicit-model"
    monkeypatch.setenv("OPENAI_MODEL", " ")
    assert llm.OpenAILLM().model == llm.DEFAULT_MODEL


@pytest.mark.parametrize("key", [None, "", " \t"])
def test_keyless_judges_degrade_and_chat_fails_without_creating_client(monkeypatch, key):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    if key is not None:
        monkeypatch.setenv("OPENAI_API_KEY", key)
    monkeypatch.setenv("GROQ_API_KEY", "old-provider-key")

    def forbidden_client(**kwargs):
        pytest.fail("Keyless calls must not construct an OpenAI client")

    monkeypatch.setattr(openai, "OpenAI", forbidden_client)
    adapter = llm.OpenAILLM()
    assert adapter.json_call("Judge this", default={"score": 1}) == {"score": 1}
    assert "OPENAI_API_KEY not set" in degraded_banners()[0]
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY not set"):
        adapter.chat([{"role": "user", "content": "hello"}])
    assert adapter._client is None


def test_json_judge_uses_openai_auth_format_and_bounded_requests(provider):
    adapter, requests = provider((200, completion('{"score": 2}')))
    assert adapter._client is None
    assert adapter.json_call("Judge this", default={"score": 1}) == {"score": 2}
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://api.openai.com/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer unit-test-key"
    body = json.loads(request.content)
    assert body["model"] == "gpt-5.4-mini"
    assert body["temperature"] == 0
    assert body["response_format"] == {"type": "json_object"}
    assert "JSON" in body["messages"][0]["content"]
    assert body["max_completion_tokens"] == 1024
    assert "max_tokens" not in body
    assert adapter.client.max_retries == 0
    assert adapter.client.timeout == 20.0


def test_chat_without_tools_omits_empty_tools_array(provider):
    adapter, requests = provider((200, completion("hello")))
    assert adapter.chat([{"role": "user", "content": "hi"}], tools=[]).content == "hello"
    body = json.loads(requests[0].content)
    assert "tools" not in body
    assert "response_format" not in body
    assert body["max_completion_tokens"] == 8000


def test_openai_auth_failure_degrades_without_leaking_response_body(provider):
    error = {"error": {"message": "private-request-value", "code": "invalid_api_key"}}
    adapter, requests = provider((401, error), (401, error))
    assert adapter.json_call("Judge this", default={"score": 1}) == {"score": 1}
    assert len(requests) == 2  # no SDK retries beyond the existing application bound
    assert "AuthenticationError" in degraded_banners()[0]
    assert "private-request-value" not in str(llm.degradation_events())


async def test_openai_tool_call_heal_and_followup_serialize_correctly(provider, monkeypatch, capsys):
    tool_call = {
        "id": "call-metrics",
        "type": "function",
        "function": {"name": "fetch_metrics", "arguments": '{"date": "July 5th"}'},
    }
    adapter, requests = provider(
        (200, completion(tool_calls=[tool_call])),
        (200, completion('{"args": {"date": "2026-07-05"}}')),
        (200, completion("Fetched the metrics.")),
    )
    monkeypatch.setattr(llm, "json_call", adapter.json_call)

    class MetricsClient:
        def __init__(self):
            self.calls = []

        async def list_tools(self):
            return [Tool(name="fetch_metrics", inputSchema={
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "required": ["date"],
            })]

        async def call_tool(self, name, args, read_timeout_seconds=None):
            self.calls.append(args)
            ok = args["date"] == "2026-07-05"
            return CallToolResult(
                isError=not ok,
                content=[TextContent(type="text", text="42" if ok else "date must be YYYY-MM-DD")],
            )

    server = MetricsClient()
    chat = Chat(adapter, {"metrics": server})
    assert await chat.send("Fetch metrics for July 5th") == "Fetched the metrics."
    assert server.calls == [{"date": "July 5th"}, {"date": "2026-07-05"}]
    assert "[self-healed]" in capsys.readouterr().out
    assert len(requests) == 3
    first, repair, followup = [json.loads(r.content) for r in requests]
    assert first["tools"][0]["function"]["description"] == ""
    assert repair["response_format"] == {"type": "json_object"}
    assert followup["messages"][1]["tool_calls"] == [tool_call]
    assert followup["messages"][2] == {
        "role": "tool", "tool_call_id": "call-metrics", "content": "42",
    }


@pytest.mark.parametrize("status, code, hint", [
    (401, "invalid_api_key", "Check OPENAI_API_KEY"),
    (429, "insufficient_quota", "billing and usage limits"),
    (429, "rate_limit_exceeded", "Wait before retrying"),
    (404, "model_not_found", "model access"),
    (403, "permission_denied", "key permissions"),
    (400, "invalid_request_error", "Chat Completions"),
])
async def test_chat_provider_errors_are_actionable_and_redacted(provider, monkeypatch, capsys, status, code, hint):
    adapter, requests = provider((status, {"error": {
        "message": "private-request-value", "code": code,
    }}))
    inputs = iter(["hello"])

    def fake_input(_prompt):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr("builtins.input", fake_input)
    chat = Chat(adapter, {})
    await chat.repl()
    output = capsys.readouterr().out
    assert hint in output
    assert "private-request-value" not in output
    assert chat.messages == []
    assert len(requests) == 1


def test_chat_without_key_exits_before_launching_servers(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "old-provider-key")

    async def forbidden_chat(_specs):
        pytest.fail("Chat must check for its key before launching any servers")

    monkeypatch.setattr(cli, "_chat", forbidden_chat)
    result = CliRunner().invoke(cli.app, ["chat", "fixtures/otherserver.py"])
    assert result.exit_code == 1
    assert "OPENAI_API_KEY not set" in result.output
    assert "Traceback" not in result.output
