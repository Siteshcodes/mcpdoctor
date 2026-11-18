# CLI reference

## Commands

```text
mcpdoctor doctor SERVERS... [OPTIONS]
mcpdoctor chat SERVERS...
```

Prefix these commands with `uv run` in the source checkout. `--help` works at both
application and command level.

## Server specifications

Each argument is a Python script path or a single quoted launch command. Python script
paths run under MCPDoctor's interpreter. Explicit commands use their selected executable.
Commands launch directly: shell pipes, redirection, globbing, and environment-variable
expansion are not performed by MCPDoctor.

```bash
uv run mcpdoctor doctor fixtures/otherserver.py
uv run mcpdoctor doctor "python fixtures/otherserver.py"
uv run mcpdoctor doctor "npx -y @modelcontextprotocol/server-filesystem ./sandbox"
```

Create a disposable `sandbox` first. The first `npx` invocation may download the server;
select a trusted version for repeatable runs.

| Option | Default | Effect |
| --- | --- | --- |
| `--thorough` | Off | All applicable templates instead of the first three per tool |
| `--ascii` | Off | Plain-text output instead of the Rich card |
| `--md PATH` | None | Also export Markdown; parent directory must exist |
| `--fix` | Off | Print T1 description suggestions; no source edits |
| `--unsafe` | Off | Include destructive tools in active probes |

The 40-call budget per server remains in force with `--thorough`. Resource reads,
templates, prompts, tool probes, and live repair retries share it. Some templates are
inapplicable to a tool's schema; a thorough audit does not guarantee seven calls per tool.

## Chat commands

| Input | Effect |
| --- | --- |
| `/doctor` | Audit this chat's server specifications through fresh sessions |
| `/doctor --thorough` | Expand applicable probes |
| `/doctor "python other-server.py"` | Audit another launch specification |
| `/doctor --unsafe` | Refused in chat |
| Ctrl+C / end of input | Exit |

Unknown `/doctor` options are reported.

## Exit status and limits

- **0:** completed, including an audit with a low grade.
- **1:** startup/handshake or other runtime failure.
- **2:** invalid CLI arguments reported by Typer.

There is no grade threshold flag, JSON/CSV export, HTTP transport, or hosted audit API.
See the [roadmap](../contributing/roadmap.md).
