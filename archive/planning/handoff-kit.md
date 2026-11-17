# Claude Code Handoff Kit — mcpdoctor

How to drive this project with Claude Code. Three layers:

1. **`CLAUDE.md`** — permanent project memory, loaded automatically every session. Stable facts + hard rules only.
2. **`docs/mcpdoctor-check-spec.md`** — the 18-check spec (already written). Source of truth. Claude Code reads it from the repo; you never paste it into a prompt.
3. **Prompts** — one kickoff prompt for Phase 1, short follow-ups for Phases 2–4. One phase per session.

## Setup (5 minutes, before any prompt)

```bash
mkdir mcpdoctor && cd mcpdoctor
git init
mkdir docs
# copy in mcpdoctor-check-spec.md → docs/
# copy in your existing chatbot files (mcp_client.py etc.) → legacy/ for now
# create CLAUDE.md with the content below
echo "GROQ_API_KEY=..." > .env && echo ".env" >> .gitignore
claude
```

Then paste the kickoff prompt. **Start in plan mode** (Shift+Tab twice) so Claude Code proposes before it touches anything.

---

## Layer 1 — `CLAUDE.md` (paste-ready)

```markdown
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
```

---

## Layer 2 — Kickoff prompt (Phase 1: static core)

Paste this as your first message, in plan mode:

```text
Read docs/mcpdoctor-check-spec.md fully, and explore everything in
legacy/ (my existing MCP CLI chatbot + client from the Anthropic MCP
course — it connects to MCP servers over stdio, lists tools, and routes
tool calls through Groq).

Then, before writing any code, give me:
1. A 10-line summary of the spec in your own words, so I can confirm
   you've understood the design (especially: CheckResult contract,
   the static/probe/LLM split, probe-safety rules, and why heal.py
   is shared between the chatbot and the doctor).
2. An assessment of legacy/ — what can be reused as-is for
   manifest.py and mcp_client.py, what needs refactoring.
3. Your Phase 1 plan as a numbered task list.

Wait for my approval, then implement Phase 1 only:

a. fixtures/badserver.py — a FastMCP server that is deliberately
   terrible in every way the spec measures: vague one-word tool
   descriptions, an undocumented `date: string` param, a
   `delete_everything` tool with no annotations, errors that just say
   "400", a ~40k-token resource, a declared capability it doesn't
   implement, no instructions field, no prompts. Comment each flaw
   with the check ID that should catch it.
b. src/mcpdoctor/doctor/results.py — CheckResult exactly as specified,
   plus category weights and the letter-grade function (spec §11),
   including the n/a weight-redistribution rule.
c. manifest.py — connect to N servers (stdio to start), gather
   initialize result + tools/resources/prompts into one Manifest.
d. runner.py — check registry, run-all, aggregate.
e. The 10 Phase-1 static checks from spec §12: S1, S2, T2, T3, T5,
   T6, T7, P1, P2, R5. Implement each per its spec section, including
   severity and fix_hint.
f. A plain-text report (rich comes in Phase 4) printing per-category
   scores and every finding.
g. pytest tests: run the full pipeline against badserver.py and assert
   each planted flaw is caught by the right check ID; plus unit tests
   for scoring math.

Definition of done for Phase 1:
`uv run mcpdoctor doctor fixtures/badserver.py` prints a report where
badserver visibly fails T2, T3, T5, T6, S2, P1 — and
`uv run pytest -q` is green.

Rules for this session: follow CLAUDE.md hard rules, no Phase 2+ work
(no probing, no Groq calls yet), ask me before any design deviation
from the spec, commit after each of a–g.
```

---

## Layer 3 — Follow-up prompts (one per session)

Start a fresh session (or `/clear`) for each phase — a clean context plus CLAUDE.md beats a bloated one. Update the Status section in CLAUDE.md at the end of each phase so the next session starts oriented.

### Phase 2 — probe engine

```text
Phase 1 is done (see Status in CLAUDE.md). Re-read spec §4, §5, §6,
§9. Plan first, then implement Phase 2:

a. probes.py — all 7 bad-input templates from §9, generated
   deterministically from a tool's inputSchema. Default 3 probes/tool,
   --thorough runs all 7.
b. The probe engine in checks_probe.py with the §5 safety rules wired
   in from the first line: destructive-tool skip (DESTRUCTIVE_WORDS +
   destructiveHint), invalid-inputs-only, 10s timeout, 40-call budget,
   --unsafe flag that is off by default and prints a loud warning.
c. Checks R1, R2, R3, R4, P3, S3 per their spec sections.
d. The garbage-acceptance trap from §4: a probe that SUCCEEDS is an
   automatic fail with severity "fail" — add a planted flaw to
   badserver.py (a tool that accepts anything) and a test proving we
   catch it.
e. Extend the badserver pytest suite to cover every new check.

Definition of done: doctor run against badserver flags the 40k
resource (R2), the mismatched MIME (R3), and the garbage-acceptor;
against the official filesystem server it completes with zero
crashes and zero destructive calls attempted. pytest green.
```

### Phase 3 — heal loop + LLM judges (the flagship)

```text
Re-read spec §4 and §10. Plan first. This phase has two halves and
the order matters:

Half 1 — heal.py as a RUNTIME feature:
In the chatbot loop, when a tool call returns an error, catch it and
call heal.repair(error_text, tool_schema, original_args) → Groq
(temperature=0, JSON out) proposes corrected args → retry once (max
twice). Log a visible "self-healed ✚" line in the chat when it works.
Add tests with a fake failing tool. Demo path: chat against
badserver, trigger a bad date arg, watch it recover.

Half 2 — the same heal.py becomes T4's grader:
Implement T4 exactly per §4: probe → protocol behavior → garbage
trap → empirical repair test scored by heal.py outcome (1 retry = 2,
2 = 1, fail = 0). The T4 LLM judge from §10 runs ONLY on failing
tools, ONLY to write fix_hint. Then implement T1 with its §10 judge
prompt verbatim, including suggested_description.

Judge hygiene per CLAUDE.md: temperature=0, fence-stripping, retry
once, safe default, never crash the run. Mock all Groq calls in
tests; add one optional live-marked test.

Definition of done: badserver's cryptic "400" errors score 0 on T4
with a concrete fix_hint; a well-written error in my document server
scores 2; the chatbot visibly self-heals a live bad call.
```

### Phase 4 — report, polish, demo

```text
Re-read spec §11 and §12. Plan first, then:

a. report.py: the rich terminal card matching the §11 mock — overall
   letter grade, per-category bars, worst finding per category, "Top
   fixes by points recovered". Plus --md export for the README.
b. --fix flag: for tools failing T1, print the judge's
   suggested_description as a ready-to-paste diff.
c. Wire /doctor into the chatbot as a slash command (reuse runner).
d. Run against three targets and save the md reports into docs/:
   badserver, the official filesystem server, my document server.
e. README.md: the narrative ("I interviewed the AI about what
   frustrates it in MCP, then built the fixes"), install, usage,
   a real report screenshot, the heal-loop demo GIF placeholder,
   and Devpost sections (Inspiration / What it does / How we built
   it / Challenges / What's next: CI mode as a GitHub Action).

Definition of done: a stranger can clone, `uv sync`, and get a
graded report on any MCP server in under 2 minutes.
```

---

## Driving tips

- **Plan mode first, always.** Shift+Tab twice before each phase prompt; approve or edit the plan before code gets written. On a 4-phase project this is where you stay in control.
- **The spec-in-repo pattern is the whole trick.** Prompts stay ~40 lines because "re-read spec §X" replaces pasting requirements. When you change your mind about a check, edit the spec file, not the prompt.
- **Verify, don't vibe.** After each phase, run the doctor against badserver yourself and read the report line by line. You are the judge of your linter's judgments — and every flaw you catch here is a line in your Devpost "Challenges" section.
- **If Claude Code ignores a rule**, check it's actually in CLAUDE.md and phrased as a command ("NEVER probe destructive tools"), not a suggestion. Critical rules can carry an IMPORTANT marker — use that sparingly so it keeps meaning something.
- **End each session with:** "Update the Status section of CLAUDE.md: what's done, what's next, any gotchas discovered." That's your cross-session memory doing its job.
