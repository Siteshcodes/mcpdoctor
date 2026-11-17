"""MCP connection layer, evolved from archive/legacy/mcp_client.py.

Changes from legacy (kept deliberately small):
- connect() keeps the InitializeResult — the doctor reads capabilities,
  instructions, and serverInfo from it (S1, S2).
- list_resources() / list_resource_templates() added for the Manifest.
"""

import json
import os
import shlex
import sys
from datetime import timedelta
from pathlib import Path
from typing import Optional, Any
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl


class ConnectError(Exception):
    """A server failed to start/handshake. Carries enough to print one
    friendly line instead of an anyio traceback."""

    def __init__(self, spec: str, command: str, cause: str):
        self.spec = spec
        self.command = command
        self.cause = cause
        super().__init__(f"could not start MCP server '{spec}': {cause}")


def root_cause(exc: BaseException) -> str:
    """Unwrap ExceptionGroups / __cause__ chains to the most informative leaf."""
    seen = 0
    while seen < 10:
        seen += 1
        group = getattr(exc, "exceptions", None)
        if group:
            exc = group[0]
            continue
        if exc.__cause__ is not None:
            exc = exc.__cause__
            continue
        break
    text = str(exc).strip()
    return text or type(exc).__name__


def split_command(text: str) -> list[str]:
    """Split command arguments without consuming Windows path separators.

    Shell operators and variable expansion are deliberately not evaluated.
    A quoted argument groups spaces on every platform.
    """
    if os.name != "nt":
        return shlex.split(text)
    parts = shlex.split(text, posix=False)
    return [
        p[1:-1] if len(p) >= 2 and p[0] == p[-1] and p[0] in "\"'" else p
        for p in parts
    ]


def spec_to_command(spec: str) -> tuple[str, list[str]]:
    """A bare .py path runs under this interpreter; anything else is a quoted
    command line, e.g. "npx -y @modelcontextprotocol/server-filesystem .".
    Shared by the doctor and the chatbot so both accept identical specs."""
    spec = spec.strip()
    try:
        if not spec:
            raise ValueError("server specification is empty")
        # A real path can contain unquoted spaces. A command ending in .py
        # must still be parsed as a command, not mistaken for a filename.
        if spec.lower().endswith(".py") and Path(spec).is_file():
            return sys.executable, [spec]
        parts = split_command(spec)
        if not parts or not parts[0]:
            raise ValueError("server command is empty")
    except (ValueError, OSError) as exc:
        raise ConnectError(spec, spec, str(exc)) from None
    command, *args = parts
    if command.lower().endswith(".py"):
        return sys.executable, [command, *args]
    return command, args


def unique_key(spec: str, taken: set[str]) -> str:
    """A stable, collision-free session key derived from the spec's basename."""
    command, args = spec_to_command(spec)
    base = Path(args[0] if command == sys.executable and args else command).stem
    key, n = base, 1
    while key in taken:
        n += 1
        key = f"{base}_{n}"
    return key


class MCPClient:
    def __init__(
        self,
        command: str,
        args: list[str],
        env: Optional[dict] = None,
    ):
        self._command = command
        self._args = args
        self._env = env
        self._session: Optional[ClientSession] = None
        self._init_result: Optional[types.InitializeResult] = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()

    async def connect(self):
        server_params = StdioServerParameters(
            command=self._command,
            args=self._args,
            env=self._env,
        )
        try:
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            _stdio, _write = stdio_transport
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(_stdio, _write, read_timeout_seconds=timedelta(seconds=30))
            )
            self._init_result = await self._session.initialize()
        except BaseException:
            # Close whatever partially opened so a failed start doesn't leave a
            # dangling anyio generator (the ugly-traceback gotcha). Callers wrap
            # the re-raised error in ConnectError for a friendly message.
            await self._exit_stack.aclose()
            raise

    def session(self) -> ClientSession:
        if self._session is None:
            raise ConnectionError(
                "Client session not initialized or cache not populated. Call connect_to_server first."
            )
        return self._session

    def init_result(self) -> types.InitializeResult:
        if self._init_result is None:
            raise ConnectionError(
                "Client session not initialized. Call connect first."
            )
        return self._init_result

    async def _list_all(self, method: str, field: str) -> list:
        """Collect every page; reject looping cursors instead of hanging."""
        fetch = getattr(self.session(), method)
        items, seen = [], set()
        result = await fetch()
        while True:
            items.extend(getattr(result, field))
            cursor = result.nextCursor
            if cursor is None:
                return items
            if cursor in seen:
                raise ValueError(f"{method} returned a repeated pagination cursor")
            seen.add(cursor)
            result = await fetch(cursor=cursor)

    async def list_tools(self) -> list[types.Tool]:
        return await self._list_all("list_tools", "tools")

    async def call_tool(
        self,
        tool_name: str,
        tool_input: dict,
        read_timeout_seconds: timedelta | None = None,
    ) -> types.CallToolResult | None:
        # Native per-call timeout (spec §4): the chatbot passes one so a hung
        # tool can't wedge the chat, without cancelling the whole session the
        # way asyncio.wait_for would. Lint runs leave it None and wrap calls
        # in asyncio.wait_for instead.
        result = await self.session().call_tool(
            tool_name, tool_input, read_timeout_seconds=read_timeout_seconds
        )
        return result

    async def list_prompts(self) -> list[types.Prompt]:
        return await self._list_all("list_prompts", "prompts")

    async def get_prompt(self, prompt_name, args: dict[str, str]):
        result = await self.session().get_prompt(prompt_name, args)
        return result.messages

    async def list_resources(self) -> list[types.Resource]:
        return await self._list_all("list_resources", "resources")

    async def list_resource_templates(self) -> list[types.ResourceTemplate]:
        return await self._list_all("list_resource_templates", "resourceTemplates")

    async def read_resource(self, uri: str) -> Any:
        result = await self.session().read_resource(AnyUrl(uri))
        resource = result.contents[0]

        if isinstance(resource, types.TextResourceContents):
            if resource.mimeType == "application/json":
                return json.loads(resource.text)

            return resource.text

    async def cleanup(self):
        await self._exit_stack.aclose()
        self._session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
