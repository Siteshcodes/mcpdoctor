# Architecture

The CLI exposes `doctor` for audits and `chat` for conversations. Both share the MCP
connection layer and healing engine.

| Module | Responsibility |
| --- | --- |
| `cli.py` | Typer commands, environment loading, output options, startup failures |
| `mcp_client.py` | Launch parsing, stdio sessions, pagination, request timeouts |
| `doctor/manifest.py` | Inventory and outcomes of discovery requests |
| `doctor/runner.py` | Registry of 18 checks and fresh-session orchestration |
| `doctor/checks_static.py` | Documentation, naming, and metadata checks |
| `doctor/probes.py` | Deterministic invalid-input generation |
| `doctor/checks_probe.py` | Bounded requests and lint-time repair policy |
| `doctor/checks_llm.py` | T1 judgments and T4 repair scoring |
| `heal.py` | Argument proposals and retries through an execution callback |
| `llm.py` | Groq access, JSON parsing, fallback handling |
| `chatbot.py` | Conversation, tool routing, error recovery, /doctor |
| `doctor/results.py` | Findings, weights, and grades |
| `doctor/report.py` | Terminal and Markdown reports, prioritized fixes |

## Shared healing, distinct execution policies

`heal.py` delegates execution to a callback. Chat supplies actual tool execution.
T4 supplies live execution only for read-only-classified tools, otherwise local schema
validation. Both use at most two repair attempts.

## Session isolation

Chat's `/doctor` passes launch specifications to `run_doctor_specs`, which owns fresh
connections. Probe cancellation therefore does not cancel chat-owned sessions.

## Current boundaries

Only stdio transport and one configured Groq model are supported. Synchronous provider
calls block the active async flow while waiting. Duplicate tool names in chat use the
first server. The static website has no server-execution backend.
