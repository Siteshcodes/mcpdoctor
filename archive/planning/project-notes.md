# mcpdoctor

CLI chatbot with MCP integration that (a) self-heals failed tool calls and
(b) has a /doctor command: an AI-usability linter that grades any MCP server
on how usable it is for an AI agent. Devpost hackathon project; hard
deadline Aug 6 2026 2:30am IST, target submission Aug 3.

## Source of truth
docs/mcpdoctor-check-spec.md defines all 18 checks, scoring, probe
templates, judge prompts, and build phases. When implementing a check,
re-read its section first. If code and spec conflict, the spec wins;
if the spec is wrong, propose a spec edit — don't silently diverge.

## Stack & environment
- Python 3.12 pinned via uv (NOT 3.13/3.14 — pydantic-core wheel issues).
  Run everything with `uv run`.
- MCP: official `mcp` SDK / FastMCP for servers.
- LLM: Groq, model `llama-3.3-70b-versatile`. Key in .env (GROQ_API_KEY),
  loaded with python-dotenv. NEVER hardcode or commit keys.
- CLI: typer. Terminal report: rich.
- Tests: pytest, `uv run pytest -q`.

## Layout
src/mcpdoctor/
  chatbot.py          # CLI chat loop (evolved from legacy/)
  mcp_client.py       # MCP connection layer (evolved from legacy/)
  heal.py             # self-healing loop — shared by chatbot AND doctor
  doctor/
    runner.py         # check registry + orchestration
    results.py        # CheckResult dataclass, scoring, weights
    manifest.py       # gather init/tools/resources/prompts (all servers)
    checks_static.py  # no network beyond list calls, no LLM
    checks_probe.py   # bad-input probing
    checks_llm.py     # Groq judges (T1, T4 fix_hints)
    probes.py         # bad-input templates (spec §9)
    report.py         # rich terminal card + markdown export
fixtures/badserver.py # deliberately broken MCP server — test suite + demo
tests/

## Hard rules (IMPORTANT)
- Probe safety is non-negotiable: tools whose name matches
  DESTRUCTIVE_WORDS or have destructiveHint are NEVER probe-called
  unless --unsafe. All probes use invalid inputs designed to be
  rejected. 10s timeout per call, max 40 probe calls per server.
- All LLM judge calls: temperature=0, JSON-only output, strip ```json
  fences, one retry on parse failure, then a safe default. A judge
  failure must never crash a lint run.
- Every check is a small async function returning list[CheckResult],
  registered in runner.py. No check may import another check.
- Do not rewrite the legacy chatbot/client wholesale — evolve it in
  small reviewed steps. It is working code with hard-won fixes.
- No new dependencies without asking first.
- Small commits, one logical change each, imperative messages.

## Workflow
- Propose a plan before non-trivial changes; wait for approval.
- After each phase: run full pytest, then update the "Status" section
  below with what's done and what's next.

## Status
Phase 0 — repo scaffolded, nothing built yet.