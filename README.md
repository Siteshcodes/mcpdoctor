# MCPDoctor

**Build MCP servers that AI agents can understand, use, and recover with.**

[![CI](https://github.com/Siteshcodes/mcpdoctor/actions/workflows/ci.yml/badge.svg)](https://github.com/Siteshcodes/mcpdoctor/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-get_started-286448)](https://siteshcodes.github.io/mcpdoctor/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

MCPDoctor is a command-line usability linter for [Model Context Protocol](https://modelcontextprotocol.io/) servers, paired with a chatbot that can repair failed tool calls. It evaluates descriptions, parameters, error recovery, resources, prompts, and protocol behavior through **18 checks across six weighted categories**.

[Documentation](https://siteshcodes.github.io/mcpdoctor/) · [Quick start](#quick-start) · [Check specification](docs/mcpdoctor-check-spec.md) · [Issues](https://github.com/Siteshcodes/mcpdoctor/issues)

## What it does

- Discover tools, resources, templates, and prompts over MCP stdio, including paginated listings.
- Combine static checks, bounded active probes, and optional LLM judgments.
- Produce a score out of 100, a letter grade, and fixes ranked by recoverable points.
- Print terminal reports, export Markdown, and suggest improved descriptions.
- Use the same healing engine in chat and in the error-repairability check.

MCPDoctor launches local **stdio servers**. Direct HTTP/SSE connections are not supported. The website explains how to run the CLI; server execution happens on your machine.

## Quick start

Requirements: Git, Python **3.12**, and [uv](https://docs.astral.sh/uv/getting-started/installation/). Node.js/npm is needed only for servers launched through `npx`.

```bash
git clone https://github.com/Siteshcodes/mcpdoctor.git
cd mcpdoctor
uv sync --frozen
uv run mcpdoctor doctor fixtures/otherserver.py
```

No API key is required for static checks and probes. Without an OpenAI key, LLM-dependent checks use fallback values and the report marks the assessment as degraded. Treat the grade as provisional.

To enable LLM judgments, description suggestions, and chat, copy `.env.example` to `.env` (or edit your existing `.env`) and set `OPENAI_API_KEY`. The default model is `gpt-5.4-mini`; `OPENAI_MODEL` overrides it. See [installation](docs/getting-started/installation.md) for setup and model requirements.

```dotenv
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.4-mini
```

Migrating from Groq: obtain an OpenAI API key and run `uv sync --frozen`. The old `GROQ_API_KEY` and `MODEL` variables are no longer used; a Groq key cannot authenticate with OpenAI.

## Usage

```bash
# Inspect a local Python server.
uv run mcpdoctor doctor fixtures/badserver.py

# Pass an explicit launch command as one quoted argument.
uv run mcpdoctor doctor "python fixtures/otherserver.py"

# Inspect multiple servers and detect name collisions.
uv run mcpdoctor doctor fixtures/badserver.py fixtures/otherserver.py

# Export findings and suggest description improvements.
uv run mcpdoctor doctor fixtures/otherserver.py --ascii --md report.md --fix

# Start a chat; requires OPENAI_API_KEY.
uv run mcpdoctor chat fixtures/otherserver.py
```

| Doctor option | Behavior |
| --- | --- |
| `--thorough` | All applicable probe templates, within the existing call budget |
| `--ascii` | Plain-text report |
| `--md PATH` | Also save Markdown; the parent directory must exist |
| `--fix` | Print suggested T1 descriptions; does not edit server source |
| `--unsafe` | Include destructive tools in probes; use disposable development data only |

In chat, `/doctor` audits the launch specifications using fresh sessions. `/doctor --thorough` expands the probes. Chat refuses `/doctor --unsafe`.

A completed audit exits with code `0` even when the grade is F. Startup failures exit with `1`; argument errors use `2`. Grade-based CI failure thresholds are not implemented.

## How scoring works

| Category | Weight | Checks |
| --- | ---: | --- |
| Error quality | 30% | T4 repairability, S3 response time |
| Tool clarity | 25% | T1 descriptions, T2 parameters, T3 examples, T6 names, T7 manifest size |
| Safety | 15% | T5 annotations and destructive-name mismatches |
| Resources | 15% | R1 readability, R2 size, R3 MIME honesty, R4 templates |
| Protocol hygiene | 10% | S1 capabilities, P2 prompt arguments, P3 rendering |
| Spec extras | 5% | R5 resource change capabilities, P1 prompts, S2 instructions |

Checks award 0–2 points. Categories without applicable results are excluded and their weights redistributed. Grades: **A ≥ 90, B ≥ 75, C ≥ 60, D ≥ 45, F < 45**. Multi-server runs produce a combined grade with server-qualified findings.

[Complete rubric](docs/mcpdoctor-check-spec.md) · [Historical example reports](docs/reports/)

## Safety and interpretation

Audits execute server code and active requests. Use trusted development servers and disposable data. Invalid input can still have side effects on a server that does not validate it.

- Destructive names or `destructiveHint: true` skip active tool probes by default.
- Probes use a 10-second timeout and a shared budget of 40 calls per server.
- Lint-time repair retries execute only for tools classified read-only. Destructive signals and explicit `readOnlyHint: false` override read-like names. Other repairs are validated locally.
- Classification relies on server metadata and naming; it is not a security boundary. Local validation does not prove a repaired call would succeed.
- Chat retries execute real calls.
- With an OpenAI key, descriptions and relevant schemas, arguments, and error text may be sent to OpenAI. Chat messages and tool results are also sent to the provider.

See [probe safety](docs/checks/probe-safety.md) and [report interpretation](docs/usage/reports.md).

## Development

```bash
uv sync --frozen --group docs
uv run pytest -q
uv run mkdocs build --strict
uv run mkdocs serve
```

Default tests use local fixtures and mocked LLM calls. Opt-in live tests use `uv run pytest -m live`; they may download an external server or contact OpenAI.

```text
src/mcpdoctor/     CLI, MCP client, chat, healing, and checks
tests/             Unit and fixture integration tests
fixtures/          Flawed and well-described example servers
docs/              User guides, check specification, and website theme
.github/workflows/ Cross-platform CI and GitHub Pages deployment
archive/           Historical planning, audits, submission assets, and prototype
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [architecture](docs/contributing/architecture.md), and [deployment](docs/contributing/deployment.md).

## Documentation hosting

MkDocs Material builds the website at **https://siteshcodes.github.io/mcpdoctor/**. Enable **Settings → Pages → Build and deployment → GitHub Actions** once. Pushes to `main` that change site inputs then deploy automatically. Generated `site/` output stays out of Git.

GitHub Pages serves documentation; the Python CLI runs locally. The [deployment guide](docs/contributing/deployment.md) covers setup, custom domains, and troubleshooting.

## License

[MIT](LICENSE) © 2026 Sitesh Gupta.
