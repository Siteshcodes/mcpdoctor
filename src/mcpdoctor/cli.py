import asyncio
import sys
from contextlib import AsyncExitStack
from pathlib import Path

import typer
from dotenv import load_dotenv

from mcpdoctor.llm import has_api_key
from mcpdoctor.doctor.probes import ProbeConfig
from mcpdoctor.doctor.report import (
    print_report,
    render_fixes,
    render_markdown,
    render_text,
)
from mcpdoctor.doctor.runner import DoctorRun, run_doctor_specs
from mcpdoctor.mcp_client import (
    ConnectError,
    MCPClient,
    spec_to_command,
    unique_key,
)

load_dotenv()

app = typer.Typer(help="mcpdoctor — AI-usability linter for MCP servers")


@app.callback()
def main() -> None:
    """mcpdoctor: lint MCP servers for AI usability, chat with self-healing tool calls."""


def _fail_connect(err: ConnectError) -> None:
    """One friendly line for a server that won't start — never a traceback."""
    typer.secho(
        f"Could not start MCP server '{err.spec}'\n"
        f"  command: {err.command}\n"
        f"  cause:   {err.cause}\n"
        f"  hint:    run that command by hand to see the server's own output.",
        fg=typer.colors.RED,
        err=True,
    )
    raise typer.Exit(code=1)


@app.command()
def doctor(
    servers: list[str] = typer.Argument(
        ..., help="MCP servers to lint: paths to Python scripts, or quoted commands"
    ),
    thorough: bool = typer.Option(
        False, "--thorough", help="Run all 7 probe templates per tool instead of 3."
    ),
    unsafe: bool = typer.Option(
        False,
        "--unsafe",
        help="Probe destructive tools too. DANGEROUS - only for dev servers "
        "whose data you can afford to lose.",
    ),
    ascii_out: bool = typer.Option(
        False, "--ascii", help="Plain ASCII report instead of the rich card."
    ),
    md: Path = typer.Option(
        None, "--md", help="Also write the report as markdown to this path."
    ),
    fix: bool = typer.Option(
        False, "--fix", help="Print ready-to-paste description rewrites for T1 failures."
    ),
) -> None:
    """Grade MCP servers on how usable they are for an AI agent."""
    if unsafe:
        typer.secho(
            "!!! UNSAFE MODE: tools with destructive names or destructiveHint "
            "WILL be probe-called with invalid inputs. Only run this against "
            "servers whose data you can afford to lose.",
            fg=typer.colors.RED,
            bold=True,
            err=True,
        )
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    config = ProbeConfig(unsafe=unsafe, thorough=thorough)
    try:
        run: DoctorRun = asyncio.run(run_doctor_specs(servers, config))
    except ConnectError as e:
        _fail_connect(e)

    if ascii_out:
        typer.echo(render_text(run.manifest, run.results, run.notes, run.degraded))
    else:
        print_report(run.manifest, run.results, run.notes, run.degraded)

    if md is not None:
        md.write_text(
            render_markdown(run.manifest, run.results, run.notes, run.degraded),
            encoding="utf-8",
        )
        typer.echo(f"\nMarkdown report written to {md}")

    if fix:
        typer.echo("")
        typer.echo(render_fixes(run.manifest, run.results))


async def _chat(specs: list[str]) -> None:
    from mcpdoctor.chatbot import Chat
    from mcpdoctor.llm import OpenAILLM

    from mcpdoctor.mcp_client import root_cause

    clients: dict[str, MCPClient] = {}
    async with AsyncExitStack() as stack:
        for spec in specs:
            command, args = spec_to_command(spec)
            key = unique_key(spec, set(clients))
            client = MCPClient(command, args)
            try:
                await stack.enter_async_context(client)
            except Exception as e:  # noqa: BLE001 - friendly line, not a traceback
                raise ConnectError(
                    spec, " ".join([command, *args]), root_cause(e)
                ) from None
            clients[key] = client
        await Chat(OpenAILLM(), clients, server_specs=specs).repl()


@app.command()
def chat(
    servers: list[str] = typer.Argument(
        ..., help="MCP servers to chat against: Python script paths or quoted commands"
    ),
) -> None:
    """Chat against MCP servers with self-healing tool calls (needs OPENAI_API_KEY)."""
    if not has_api_key():
        typer.secho(
            "OPENAI_API_KEY not set. Add it to .env or your environment to use chat.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        asyncio.run(_chat(servers))
    except ConnectError as e:
        _fail_connect(e)
