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
Phase 4 DONE (report, polish, demo) — project feature-complete.
Built on Phase 3: server-qualified findings (CheckResult.server set at
every call site; report.display_target renders server:target on
multi-server runs), degraded-run disclosure (llm records a degradation
event only when the completion CALL fails, not on parse-fallback;
runner.degraded_banners → top-of-report banner: key-missing up front
or API-failed mid-run), session isolation (runner.run_doctor_specs
owns connect-lint-close with FRESH sessions; spec_to_command/
unique_key moved to mcp_client; spy test proves zero lint traffic
crosses chat sessions), rich terminal card (report.build_rich, §11:
bars + worst-per-category + Top fixes by points recovered) with
--ascii fallback, --md markdown export, --fix (before/after T1
rewrites parsed from the '| suggested:' convention; display_hint keeps
that marker OUT of the report body), friendly connect-failure UX
(MCPClient.connect closes partial state; ConnectError → one line, exit
1, no anyio traceback), /doctor in the chatbot (fresh sessions,
refuses --unsafe). 116 default tests + 2 live-marked. Four committed
reports in docs/reports/. README with narrative + Devpost sections.
DoD verified: keyless run graded + degraded banner in <4s; keyed full
grades real (otherserver B/87, document-server D/54); /doctor
isolation test-proven; bad spec → friendly line + exit 1, no
traceback; tripwire untouched; `uv run pytest -q` green; `-m live`
green (filesystem safety pass, T1 judge skips on Groq degradation).
Phase 4 gotchas:
- Groq FREE-TIER quota (RPM + daily) throttles bursts: a 14-tool
  server fires ~14 T1 judges at once and rate-limits. max_retries=0 +
  _complete skipping the network when GROQ_API_KEY is absent keeps a
  KEYLESS run fast (~4s) — but a present-but-rate-limited key degrades
  mid-run (correctly banners it). badserver/filesystem committed
  reports show the degraded banner for this reason (honest; regen with
  fresh quota via --md). Live T1 judge test SKIPS (not fails) when
  llm.degradation_events() is non-empty — never be flaky on the
  provider's availability.
- click >= 8.2 CliRunner dropped mix_stderr; combine result.output +
  result.stderr defensively in CLI tests.
- The '| suggested: <text>' convention (Phase 3, T1 fix_hint) must be
  stripped for display (report.display_hint) in findings AND top-fixes
  across all three renderers — else the internal marker leaks into
  committed reports. --fix still parses the full hint.
- run_doctor_specs is THE orchestration seam: cli.doctor and chat
  /doctor both call it, so session isolation holds by construction.
  Rich card returns a renderable (build_rich); render_rich exports via
  a recording Console for tests.
- mcp_client.connect now closes its partial _exit_stack on failure —
  this is what actually kills the dangling-anyio-generator traceback
  from the Phase-2 gotcha; the CLI then prints one friendly line.
- Legacy status below (Phase 3 and earlier) retained for reference.

Phase 3 DONE (heal loop + LLM judges). All 18 checks now live.
Half 1 (runtime): llm.py (GroqLLM + json_call hygiene — temp=0,
JSON-only, fence-strip, one parse retry, safe default, never raises),
heal.py (repair_args + heal loop, max 2 attempts, policy-free via an
execute callback), chatbot.py (generalized REPL, native per-call
read_timeout_seconds, visible [self-healed] line), `mcpdoctor chat`.
Half 2 (doctor): lint-repair safety policy FIRST (make_repair_executor
— read-only tools re-execute live as repair_exec records, others
validate locally via jsonschema; READ_ONLY_WORDS in vocab.py), unified
t4_error_repairability (absorbs the Phase-2 trap + heal scoring:
repaired in 1→2, 2→1, unrepaired→0, floor(mean)), t1_description_quality
(static gate owns score, §10 judge writes suggested_description),
partial labels retired. 93 default tests + 2 live-marked.
DoD verified (real Groq): badserver+otherserver → F (41/100);
get_data T4=0 (cryptic "400" body, live) and log_event T4=0 (garbage
trap) with fix_hints; fetch_metrics T4=2 (exemplary error healed in 1,
live-executed); process/handle T4=2 (validated locally, NOT executed —
interpretation on record); T1=0 on one-word descriptions with
suggested_description in fix_hint; no "partial (" labels; chatbot
self-heals a live bad log_event call. Safety proof: no repair_exec on
process/handle (non-read-only); tripwire untouched; budgets 38/14 ≤40.
Keyless run degrades to safe defaults, no crash. `uv run pytest -q`
green; `-m live` green (filesystem safety + real T1 judge).
Next: Phase 4 — rich report card (§11), --fix (parse suggested_
description out of T1 fix_hint), /doctor slash command in the chatbot,
md exports for 3 targets, README + Devpost. Graceful connect-failure
handling (the anyio-traceback gotcha) is Phase-4 polish.
Phase 3 gotchas:
- heal.py is policy-free: the `execute` callback is the seam. Chatbot
  passes real execution (native timeout); T4 passes make_repair_executor
  which live-runs ONLY read-only tools and validates others locally.
  A repaired call is a VALID call — executing it on a mutating tool
  would mutate, so the read-only gate is load-bearing, not cosmetic.
- Interpretation on record: non-read-only tools (process/handle) score
  T4 by LOCAL jsonschema validation of repaired args, so they can hit 2
  despite always-"400" bodies (the body is unreachable safely). Accepted
  safety-vs-fidelity trade. Read-only-named tools (get/search) execute
  live and still score 0 on cryptic bodies.
- Unified T4 replaced the Phase-2 t4_garbage_trap: one check must own a
  tool's T4 result (two would double the category max). Trap MESSAGE
  preserved verbatim so the "accepted ... without error" tests still pass.
- T4 must be registered BEFORE s3_response_time: its repair_exec calls
  add ProbeRecords that S3 scores over.
- Tests mock Groq at the module seam (conftest autouse session fixture
  patches llm.json_call); the deterministic fake extracts the schema
  from the repair prompt and returns valid args (date-ish→"2026-07-06").
  Individual tests still override with their own monkeypatch.
- Cross-server name collisions make per-tool check targets non-unique
  (two "search" T1 results in collision_run) — assert on the set, not
  one(). A real reporting weakness for Phase 4 to disambiguate.
- read_timeout_seconds IS available on ClientSession.call_tool (native);
  read_resource/get_prompt still are not — hence wait_for at lint time.
- FastMCP @tool accepts annotations=ToolAnnotations(readOnlyHint=True);
  used for fetch_metrics to prove the live-repair read-only path.
Phase 2 gotchas:
- FastMCP/pydantic rejects wrong-type/missing-required before the
  tool body runs — a FastMCP tool literally cannot accept those. The
  garbage trap therefore fires on UNENFORCED declared constraints:
  log_event declares format=date via json_schema_extra (propagates
  into the schema), pydantic only checks str, "July 5th" succeeds.
- Tolerate-probes (unknown_field/huge_string) must carry a hard
  violation (omit a required param) or be skipped ("no safe base")
  — spec §9 was tightened; bad_format never targets path/query/id
  params ("July 5th" is a legal filename).
- Probe checks share ONE engine pass cached on manifest._probe_run;
  synthetic tests preseed that attr to fake slow/timeout/budget paths.
- ClientSession.read_resource/get_prompt have no timeout param —
  everything runs under asyncio.wait_for uniformly.
- A server that dies at startup (e.g. bad directory arg to the
  filesystem server) surfaces as an ugly anyio traceback from the
  CLI — graceful connect-failure handling is Phase 4 polish.
- mktemp -d in Git Bash yields /tmp/... which Windows-native servers
  can't see — use real Windows paths when testing by hand.
Phase 1 gotchas (still true):
- Check signature is (sessions: dict[str, Session], manifest) — spec
  §1 was updated for N-server support; probe checks route through it.
- FastMCP auto-declares prompts/resources capabilities even with
  nothing registered → S1 words this "framework default" (warn, not
  accusatory). Declared-but-errors is covered by a synthetic-manifest
  unit test (test_s1_synthetic.py) — can't be faked live in FastMCP.
- pydantic auto-adds "title" to every param schema — T2 must not
  count title as documentation.
- n/a convention: a non-applicable check emits NO CheckResults; a
  category with zero results is n/a and its weight redistributes.
- T6 solo server tops out at warn/score 1 (exact dupes impossible in
  one FastMCP server); hard collision proven by two-server test.
- Report output is ASCII-only: Windows legacy codepages mangle
  em-dashes and box chars. Keep it that way until rich (Phase 4).
- Tests run the async pipeline via asyncio.run inside sync
  session-scoped fixtures — no pytest-asyncio loop-scope juggling.
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