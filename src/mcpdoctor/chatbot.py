"""Minimal CLI chatbot with MCP integration and runtime self-healing.

Evolved from legacy/core/chat.py + tools.py, generalized to arbitrary server
specs (no course-server hardcoding) and with the name->client map built once
per turn instead of re-listing tools on every call.

The flagship behavior: when a tool call errors, heal.heal() asks the LLM to
repair the arguments and retries against the live server (native per-call
timeout, never asyncio.wait_for — a chat session must not be cancelled from
under the user). On success a visible "[self-healed]" line is printed and the
corrected result is fed back to the model.

Demo path (needs OPENAI_API_KEY):
    uv run mcpdoctor chat fixtures/otherserver.py
    > Call fetch_metrics with the date set to the literal text "July 5th"
      (do not convert it to any other format)
fetch_metrics accepts any string but its body rejects a non-ISO date with a
helpful error ("date must be YYYY-MM-DD, got 'July 5th'"); heal reads that,
proposes "2026-07-05", the retry succeeds, and you see "[self-healed] ...".

Use a schema-valid string that the tool body rejects to demonstrate repair.
Model-generated tool arguments still need validation by the MCP server.
"""

import asyncio
import json
from datetime import timedelta

from mcp.types import CallToolResult, TextContent
from openai import OpenAIError

from mcpdoctor import heal
from mcpdoctor.doctor.probes import ProbeConfig
from mcpdoctor.doctor.report import render_text
from mcpdoctor.doctor.runner import run_doctor_specs
from mcpdoctor.llm import OpenAILLM, api_error_hint
from mcpdoctor.mcp_client import ConnectError, MCPClient, split_command

_CALL_TIMEOUT = timedelta(seconds=30)


def _result_text(result: CallToolResult | None) -> str:
    if result is None:
        return ""
    return "\n".join(
        item.text for item in result.content if isinstance(item, TextContent)
    )


def _parse_tool_arguments(raw: str) -> dict:
    """Reject malformed arguments without converting them into an executable call."""
    def reject_constant(value: str):
        raise ValueError(f"{value} is not a valid JSON constant")

    args = json.loads(raw, parse_constant=reject_constant)
    if not isinstance(args, dict):
        raise ValueError("tool arguments must be a JSON object")
    return args


class Chat:
    def __init__(
        self,
        llm: OpenAILLM,
        clients: dict[str, MCPClient],
        server_specs: list[str] | None = None,
    ):
        self.llm = llm
        self.clients = clients
        # The specs this chat launched with — /doctor reconnects fresh from
        # these (never reusing chat sessions) when called with no args.
        self.server_specs = server_specs or []
        self.messages: list = []

    async def _tool_index(self) -> tuple[list[dict], dict[str, tuple[MCPClient, dict]]]:
        """OpenAI-format tool list + a name -> (client, schema) map, built once
        per turn (fixes the legacy re-list-per-call pattern)."""
        tools: list[dict] = []
        index: dict[str, tuple[MCPClient, dict]] = {}
        for client in self.clients.values():
            for tool in await client.list_tools():
                if tool.name in index:
                    continue  # first server wins (T6 territory, not our problem here)
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": tool.inputSchema,
                        },
                    }
                )
                index[tool.name] = (client, tool.inputSchema)
        return tools, index

    async def _run_tool(
        self, client: MCPClient, name: str, schema: dict, args: dict
    ) -> str:
        """Execute one tool call, healing on error. Returns text for the model."""
        result = await client.call_tool(name, args, read_timeout_seconds=_CALL_TIMEOUT)
        if result is not None and not result.isError:
            return _result_text(result)

        # Failed — try to self-heal. The execute callback runs the repaired
        # call for real (the user intended this call) and stashes its result.
        captured: dict = {}

        async def execute(candidate_args: dict) -> tuple[bool, str]:
            res = await client.call_tool(
                name, candidate_args, read_timeout_seconds=_CALL_TIMEOUT
            )
            captured["result"] = res
            ok = res is not None and not res.isError
            return ok, _result_text(res)

        outcome = await heal.heal(execute, _result_text(result), schema, args)
        if outcome.healed:
            print(f"[self-healed] {name} retried with corrected args {outcome.args}")
            return _result_text(captured.get("result"))
        return _result_text(result)  # original error, handed to the model

    async def send(self, user_text: str) -> str:
        # If anything below raises (e.g. the LLM API rate-limiting), roll the
        # history back to this point — a dangling assistant tool_call with no
        # tool result would poison every later turn.
        checkpoint = len(self.messages)
        try:
            return await self._send(user_text)
        except BaseException:
            del self.messages[checkpoint:]
            raise

    async def _send(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        while True:
            tools, index = await self._tool_index()
            message = self.llm.chat(messages=self.messages, tools=tools)
            self.messages.append(message)

            if not message.tool_calls:
                return message.content or ""

            for call in message.tool_calls:
                name = call.function.name
                try:
                    args = _parse_tool_arguments(call.function.arguments)
                except (ValueError, TypeError):
                    args = None

                if args is None:
                    content = json.dumps({
                        "error": f"tool '{name}' arguments must be a valid JSON object; "
                        "tool was not executed. Correct the arguments and try again.",
                    })
                elif name in index:
                    client, schema = index[name]
                    try:
                        content = await self._run_tool(client, name, schema, args)
                    except Exception as e:  # noqa: BLE001 - report, don't crash the chat
                        content = json.dumps({"error": f"tool '{name}' failed: {e}"})
                else:
                    content = json.dumps({"error": f"no such tool: {name}"})

                self.messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": content}
                )

    async def handle_command(self, text: str) -> str:
        """Handle a /command locally (before the LLM sees it). Returns the text
        to print. Currently: /doctor [specs...] [--thorough]."""
        try:
            parts = split_command(text)
        except ValueError as exc:
            return f"invalid command: {exc}"
        if not parts:
            return "enter /doctor to lint the connected servers"
        cmd, args = parts[0], parts[1:]

        if cmd != "/doctor":
            return f"unknown command {cmd}; the only chat command is /doctor"

        if "--unsafe" in args:
            return (
                "/doctor will not probe destructive tools from a chat session. "
                "Run it from the CLI if you really mean to: "
                "mcpdoctor doctor --unsafe <server>"
            )

        thorough = "--thorough" in args
        unknown = [a for a in args if a.startswith("--") and a != "--thorough"]
        if unknown:
            return f"unknown /doctor option: {unknown[0]}; supported option: --thorough"
        specs = [a for a in args if not a.startswith("--")] or self.server_specs
        if not specs:
            return "no server specs to lint (this chat launched without any)"

        # Fresh sessions — NEVER the chat's own (spec §4/§5): lint cancellation
        # must not touch a session the chat owns.
        try:
            run = await run_doctor_specs(specs, ProbeConfig(thorough=thorough))
        except ConnectError as e:
            return f"could not start '{e.spec}': {e.cause}"
        return render_text(run.manifest, run.results, run.notes, run.degraded)

    async def repl(self) -> None:
        print("mcpdoctor chat — /doctor to lint, Ctrl+C to exit")
        while True:
            try:
                user_text = await asyncio.to_thread(input, "> ")
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not user_text.strip():
                continue
            try:
                if user_text.lstrip().startswith("/"):
                    reply = await self.handle_command(user_text.strip())
                else:
                    reply = await self.send(user_text)
            except KeyboardInterrupt:
                print()
                return
            except Exception as e:  # noqa: BLE001 - keep the chat alive
                name = type(e).__name__
                text = api_error_hint(e) if isinstance(e, OpenAIError) else str(e)[:200]
                print(f"\n[chat error] {name}: {text}")
                print()
                continue
            print(f"\n{reply}\n")
