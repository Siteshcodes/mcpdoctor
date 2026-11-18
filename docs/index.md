# MCPDoctor documentation

MCPDoctor is a command-line tool for checking how usable an MCP server is for AI agents.
It runs 18 checks and produces a score, findings, and suggested improvements. It also
includes a chatbot that can retry failed tool calls with corrected arguments.

## Quick start

Requires Git, Python 3.12, and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/Siteshcodes/mcp-doctor.git
cd mcp-doctor
uv sync --frozen
uv run mcpdoctor doctor fixtures/otherserver.py
```

Static checks and active probes work without an API key. LLM-dependent checks use
fallback values when a key is unavailable, so the resulting grade is provisional.

For LLM judgments and chat, copy `.env.example` to `.env` and set `GROQ_API_KEY`.
See [installation](getting-started/installation.md) for platform-specific instructions.

## Common commands

Audit a server:

```bash
uv run mcpdoctor doctor path/to/server.py
```

Audit a server launched with a command:

```bash
uv run mcpdoctor doctor "python path/to/server.py"
```

Save a Markdown report:

```bash
uv run mcpdoctor doctor path/to/server.py --md report.md
```

Start a chat session:

```bash
uv run mcpdoctor chat fixtures/otherserver.py
```

Chat requires a Groq key. Use `/doctor` within chat to audit the connected server
specifications through fresh sessions.

## Documentation

| Guide | Contents |
| --- | --- |
| [Installation](getting-started/installation.md) | Requirements, setup, and optional API key |
| [First audit](getting-started/first-lint.md) | Run a fixture, read findings, and audit your server |
| [CLI reference](usage/cli.md) | Commands, options, and exit codes |
| [Self-healing chat](usage/chat.md) | Repair flow and chat limitations |
| [Reports](usage/reports.md) | Scores, grades, exports, and example reports |
| [Checks](checks/overview.md) | The 18 checks and their categories |
| [Probe safety](checks/probe-safety.md) | Execution policy, timeouts, and budgets |
| [Troubleshooting](getting-started/troubleshooting.md) | Common setup and runtime problems |
| [Development](contributing/development.md) | Tests and local documentation preview |
| [Deployment](contributing/deployment.md) | GitHub Pages setup and publishing |

## Before auditing your own server

MCPDoctor launches local stdio servers and sends active requests. Use trusted development
servers and disposable data. A server may change data even when given invalid input.
Read [probe safety](checks/probe-safety.md) before running an audit.

HTTP/SSE connections and browser-based audits are not supported. The website provides
documentation; the CLI runs on your machine.

## Project

[Source code](https://github.com/Siteshcodes/mcp-doctor) ·
[Report an issue](https://github.com/Siteshcodes/mcp-doctor/issues) ·
[MIT license](https://github.com/Siteshcodes/mcp-doctor/blob/main/LICENSE)
