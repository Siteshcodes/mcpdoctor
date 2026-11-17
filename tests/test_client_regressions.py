"""Regressions for server commands and complete manifest discovery."""

import sys
from types import SimpleNamespace

import pytest

from mcpdoctor import mcp_client
from mcpdoctor.mcp_client import ConnectError, MCPClient, spec_to_command, unique_key


def test_explicit_python_command_is_not_a_filename():
    assert spec_to_command("python fixtures/badserver.py") == (
        "python", ["fixtures/badserver.py"]
    )


def test_script_path_with_spaces_and_arguments(tmp_path):
    script = tmp_path / "my server.py"
    script.write_text("", encoding="utf-8")
    assert spec_to_command(str(script)) == (sys.executable, [str(script)])
    assert spec_to_command(f'"{script}" --port 9000') == (
        sys.executable, [str(script), "--port", "9000"]
    )


def test_windows_commands_preserve_backslashes(monkeypatch):
    monkeypatch.setattr(mcp_client, "os", SimpleNamespace(name="nt"))
    assert spec_to_command(r'"C:\Program Files\Python\python.exe" "C:\MCP tools\server.py"') == (
        r"C:\Program Files\Python\python.exe", [r"C:\MCP tools\server.py"]
    )
    assert spec_to_command(r"node C:\servers\index.js") == (
        "node", [r"C:\servers\index.js"]
    )


@pytest.mark.parametrize("spec", ["", "  ", '"unterminated', '""'])
def test_bad_command_has_friendly_error(spec):
    with pytest.raises(ConnectError):
        spec_to_command(spec)


def test_unique_keys_use_script_names():
    assert unique_key("fixtures/badserver.py", {"badserver"}) == "badserver_2"


@pytest.mark.parametrize("method,field", [
    ("list_tools", "tools"), ("list_resources", "resources"),
    ("list_prompts", "prompts"), ("list_resource_templates", "resourceTemplates"),
])
async def test_all_manifest_pages_are_collected(method, field):
    calls = []

    async def fetch(cursor=None):
        calls.append(cursor)
        return SimpleNamespace(**{
            field: ["first"] if cursor is None else ["second"],
            "nextCursor": "page-two" if cursor is None else None,
        })

    client = MCPClient("unused", [])
    client._session = SimpleNamespace(**{method: fetch})
    assert await getattr(client, method)() == ["first", "second"]
    assert calls == [None, "page-two"]


async def test_repeated_page_cursor_stops_discovery():
    async def fetch(cursor=None):
        return SimpleNamespace(tools=[], nextCursor="loop")

    client = MCPClient("unused", [])
    client._session = SimpleNamespace(list_tools=fetch)
    with pytest.raises(ValueError, match="repeated pagination cursor"):
        await client.list_tools()
