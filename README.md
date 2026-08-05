# mcpdoctor

**An AI-usability linter for MCP servers — plus a chatbot that heals its own broken tool calls.**

I kept watching AI agents fail against MCP servers for the same dumb reasons: a tool
called `date: string` with no hint whether it wanted `2026-07-06` or "tomorrow"; an
error that said only `400`; two servers both exposing `search`. So I interviewed the
model about what actually frustrates it in an MCP server — *when* to pick a tool, how to
recover from an error, which call is destructive — turned those frustrations into 18
concrete checks, and then built the fix into the same codebase: a self-healing chat loop.

`mcpdoctor` grades a server on one question: **could a model use this correctly on the
first try, and recover on the second?**

```
mcpdoctor — badserver (7 tools · 2 resources · 0 prompts)
Overall: F (25/100)

  Error Quality    ####------  43%   get_data: errors did not let the heal loop repair the call
  Tool Clarity     #---------   7%   process: static gate: only 1 words - says what but not when
  Safety           ----------   0%   delete_everything: destructive name but destructiveHint unset
  Resources        ####------  40%   data://config: declared application/json but content is not JSON
  Protocol Hygiene #####-----  50%   prompts capability declared but nothing registered
  Spec Extras      ----------   0%   no instructions field in initialize result

Top fixes (by points recovered):
  1. delete_everything - set destructiveHint: true on delete_everything (+15)
  2. badserver - register the primitive or drop the capability claim (+5)
  3. get_data - error should name the field, the expected format, and the received value (+4)

Probe safety:
  badserver/delete_everything: active probes skipped for safety
```

Full example reports live in [`docs/reports/`](docs/reports/) — the official filesystem
server, the Anthropic MCP-course document server, and two deliberate fixtures.

## The flagship idea

The self-healing loop in [`heal.py`](src/mcpdoctor/heal.py) is used **twice, as literally the
same code**:

- **At chat runtime** — when a tool call errors, the loop hands the error + schema to the
  model, gets corrected arguments, and retries. You see a `[self-healed]` line and the
  conversation carries on.
- **At lint time (check T4)** — *"could the heal loop repair this error?"* becomes the
  empirical measure of error quality. A cryptic `400` can't be repaired → score 0. An
  error that names the field, the expected format, and the received value gets fixed in
  one retry → score 2. Empirical beats opinion.

## Install

```bash
git clone <this-repo> && cd mcpdoctor
uv sync
```

A `GROQ_API_KEY` is **optional but recommended**. Set it in `.env`:

```
GROQ_API_KEY=your-key-here
```

Without a key, `mcpdoctor` still runs every static and probe check and prints a graded
report in seconds — the two LLM-judged checks (T1 description quality, T4 error
repairability) degrade to safe defaults, and the report says so at the top. **A degraded
grade is a floor, not a final.**

## Usage

### Lint a server

```bash
uv run mcpdoctor doctor fixtures/badserver.py
uv run mcpdoctor doctor "npx -y @modelcontextprotocol/server-filesystem ./sandbox"
uv run mcpdoctor doctor serverA.py serverB.py      # multi-server; findings show server:tool
```

Servers are given as a `.py` path (run under the project interpreter) or a quoted command
line for anything else.

| Flag | What it does |
|------|--------------|
| `--thorough` | Run all 7 bad-input probe templates per tool instead of the default 3. |
| `--unsafe` | Also probe destructive-named tools. **Dangerous** — off by default, loudly warned. |
| `--ascii` | Plain ASCII report instead of the rich card (for consoles that mangle glyphs). |
| `--md PATH` | Also write the report as markdown (for READMEs / CI). |
| `--fix` | Print ready-to-paste rewritten tool descriptions for every T1 failure. |

### Chat (with self-healing)

```bash
uv run mcpdoctor chat fixtures/otherserver.py
> Call fetch_metrics with the date set to the literal text "July 5th" (do not convert it)
```

`fetch_metrics` accepts any string, but its body rejects a non-ISO date with a helpful
error — `date must be YYYY-MM-DD, got 'July 5th'`. The heal loop reads that, proposes
`2026-07-05`, the retry succeeds, and you see a `[self-healed]` line. Inside a chat you can
also run `/doctor [servers…] [--thorough]` — with no arguments it lints the servers the
chat launched with, in **fresh sessions** (a lint must never cancel a request out from
under your live chat).

> Note: you can't demo healing by forcing a *wrong-typed* argument through the model —
> Groq validates tool-call arguments against the schema and refuses to emit a type-invalid
> call at all. The runtime heal needs a schema-valid input the tool *body* then rejects.

## The 18 checks

Grouped into six weighted categories — Error Quality (30), Tool Clarity (25), Safety (15),
Resources (15), Protocol Hygiene (10), Spec Extras (5). A category with nothing to measure
is n/a and its weight is redistributed, so a pure-tools server isn't punished for having no
resources. The full rubric — scoring, probe templates, judge prompts — is in
[`docs/mcpdoctor-check-spec.md`](docs/mcpdoctor-check-spec.md).

Safety is non-negotiable: tools whose name matches a destructive word (`delete`, `drop`,
`wipe`, …) or that set `destructiveHint` are **never probe-called** without `--unsafe`;
every probe uses invalid input designed to be rejected; there's a 10s timeout and a 40-call
budget per server. A repaired probe is a *valid* call, so at lint time it is only
re-executed against provably read-only tools — everything else is validated locally so a
lint never mutates anyone's data.

## What we learned building it

- **Pydantic injects a `title` into every parameter schema.** Our "is this parameter
  documented?" check counted it as a description until we noticed every tool scoring
  suspiciously well.
- **FastMCP validates types *before* your tool body runs** — so a server literally can't
  accept a wrong-typed argument. The interesting failure isn't bad validation, it's a
  *declared-but-unenforced* constraint: `date: string` with `format: date` that nothing
  checks. That's what the garbage-acceptance trap actually catches.
- **The "harmless" probes weren't.** Two probe templates (`unknown_field`, `huge_string`)
  can *succeed* — and a successful call against a mutating tool like `write_file` would
  write junk. They now always carry a hard schema violation, or are skipped entirely when
  no safe base exists.
- **A repaired probe is a valid call.** The heal loop that measures error quality had to be
  taught never to *execute* its repair against a tool that could change state — the read-
  only gate is load-bearing, not cosmetic.
- **Validation keeps happening before you can watch the bad call.** Pydantic checks types
  before the tool body; FastMCP won't accept a mismatched argument; and Groq validates the
  model's tool call server-side and refuses to emit a type-invalid one. The same lesson at
  three layers — which is exactly why the interesting failure is a *declared-but-unenforced*
  constraint, and why the self-heal demo triggers on a body-level error, not a type error.

## How it's built

Python 3.12, [uv](https://docs.astral.sh/uv/), the official `mcp` SDK / FastMCP, Groq
(`llama-3.3-70b-versatile`) for the two judges, `typer` + `rich` for the CLI. Every check is
a small async function returning `list[CheckResult]`, registered in one list; no check
imports another. 116 tests (`uv run pytest -q`), plus opt-in live tests (`-m live`) that
lint the real filesystem server and prove the probe sweep mutates nothing.

---

## Devpost

**Inspiration.** Every MCP demo shows a model using a *well-built* server. Reality is
messier — vague descriptions, cryptic errors, unmarked destructive tools. I wanted to
measure that gap the way the model experiences it, then close it.

**What it does.** Grades any MCP server with 18 checks across six categories and an overall
letter grade, tells you the top fixes ranked by how many points each recovers, and ships a
chatbot that self-heals failed tool calls live — the same heal loop that scores error
quality.

**How we built it.** Three engines by trust level: a static inspector (reads only what the
server declares), a probe engine (calls the server with inputs designed to be rejected,
under hard safety rules), and two Groq judges at temperature 0. The heal loop is the hinge
between the linter and the chatbot.

**Challenges.** Making the probe engine provably safe (it must never mutate a stranger's
data); realizing a repaired call is a valid call; keeping a keyless run useful *and* honest
about being degraded; the quiet gotchas above.

**What's next.** A CI mode as a GitHub Action (fail a PR when a server's grade drops); a
`--model` flag to grade with a Claude judge; the query-middleware idea for R2 to summarize
oversized resources instead of just flagging them.
