"""Minimal CLI chatbot with MCP integration and runtime self-healing.

Evolved from legacy/core/chat.py + tools.py, generalized to arbitrary server
specs (no course-server hardcoding) and with the name->client map built once
per turn instead of re-listing tools on every call.

The flagship behavior: when a tool call errors, heal.heal() asks the LLM to
repair the arguments and retries against the live server (native per-call
timeout, never asyncio.wait_for — a chat session must not be cancelled from
under the user). On success a visible "[self-healed]" line is printed and the
corrected result is fed back to the model.

Demo path (needs GROQ_API_KEY):
    uv run mcpdoctor chat fixtures/otherserver.py
    > Call fetch_metrics with the date set to the literal text "July 5th"
      (do not convert it to any other format)
fetch_metrics accepts any string but its body rejects a non-ISO date with a
helpful error ("date must be YYYY-MM-DD, got 'July 5th'"); heal reads that,
proposes "2026-07-05", the retry succeeds, and you see "[self-healed] ...".

Why not force a wrong TYPE (e.g. an int)? Groq validates tool-call arguments
against the schema server-side and refuses to emit a type-invalid call at all
(tool_use_failed) — the same "validation happens before you can observe the
bad call" lesson the linter is built around. So the runtime heal demo needs a
schema-valid input that the tool BODY rejects.
"""

import asyncio
import json
from datetime import timedelta

from mcp.types import CallToolResult, TextContent

from mcpdoctor import heal
from mcpdoctor.doctor.probes import ProbeConfig
from mcpdoctor.doctor.report import render_text
from mcpdoctor.doctor.runner import run_doctor_specs
from mcpdoctor.llm import GroqLLM
from mcpdoctor.mcp_client import ConnectError, MCPClient

_CALL_TIMEOUT = timedelta(seconds=30)


def _result_text(result: CallToolResult | None) -> str:
    if result is None:
        return ""
    return "\n".join(
        item.text for item in result.content if isinstance(item, TextContent)
    )


class Chat:
    def __init__(
        self,
        llm: GroqLLM,
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
        """Groq-format tool list + a name -> (client, schema) map, built once
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
                            "description": tool.description,
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
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                if name in index:
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
        parts = text.split()
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
                text = str(e)
                print(f"\n[chat error] {name}: {text[:200]}")
                if "RateLimit" in name:
                    print("Groq free-tier limit hit - wait a minute and try again.")
                elif "tool_use_failed" in text:
                    print(
                        "Groq rejected the model's tool call against the schema "
                        "(e.g. a wrong-typed argument). Rephrase so the arguments "
                        "match the tool's declared types."
                    )
                print()
                continue
            print(f"\n{reply}\n")
