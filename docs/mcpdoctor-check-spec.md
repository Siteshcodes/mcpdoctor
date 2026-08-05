# mcpdoctor — AI-Usability Check Spec (v0.1)

The brain of `/doctor`: 18 checks that grade how usable an MCP server is *for an AI agent*, not for a human reading the docs. Every check answers one question: **"Could a model use this correctly on the first try — and recover on the second?"**

Each check maps a real failure mode (the pain list) to a detection method and a 0/1/2 score.

---

## 1. Architecture in one page

Three engines, one result type:

- **Static inspector** — reads what the server *declares* (initialize result, tools/list, resources/list, prompts/list). No LLM, deterministic, fast. Build these first.
- **Probe engine** — actually calls the server with deliberately broken inputs and measures what comes back.
- **LLM judge** — Groq at `temperature=0`, fixed rubric, JSON-only output. Used only where quality is subjective (description clarity, error-message helpfulness).

```python
from dataclasses import dataclass

@dataclass
class CheckResult:
    id: str              # "T4"
    name: str            # "Error repairability"
    category: str        # "error_quality"
    target: str          # tool/resource/prompt name, or "server"
    score: int           # 0, 1, or 2
    max_score: int       # always 2
    severity: str        # "info" | "warn" | "fail"
    message: str         # what was found
    fix_hint: str | None # concrete suggestion, shown in report
    server: str | None   # owning server; renderers show "server:target"
                         # whenever more than one server is connected
```

Registry pattern — every check is a small async function, `doctor` just runs the list. Because the doctor connects to N servers at once, checks receive a mapping of server name → live session (static checks ignore it; probe checks route calls through it):

```python
Check = Callable[[dict[str, Session], Manifest], Awaitable[list[CheckResult]]]
CHECKS: list[Check] = [t1_description_quality, t2_param_docs, ...]
```

`Manifest` = everything gathered once at startup (init result + all tools/resources/prompts from **all** connected servers — T6 needs the cross-server view).

**Key synergy:** the self-healing loop lives in `heal.py` and is used twice — at runtime by the chatbot (catch → repair → retry) and at lint time by T4, where *"could the heal loop fix it?"* becomes the empirical measure of error quality. One module, two features. Say this out loud in the demo.

---

## 2. The 18 checks

| ID | Check | Method | Category |
|----|-------|--------|----------|
| T1 | Tool description quality | static + LLM judge | Tool Clarity |
| T2 | Parameter docs & format hints | static | Tool Clarity |
| T3 | Examples present | static | Tool Clarity |
| T4 | **Error repairability** | probe + heal loop | Error Quality |
| T5 | Safety annotations | static | Safety |
| T6 | Name collisions & generic names | static, cross-server | Tool Clarity |
| T7 | Manifest bloat (token cost) | static | Tool Clarity |
| R1 | Resource readability | probe | Resources |
| R2 | Context flooding (size) | probe | Resources |
| R3 | MIME declared & matches content | static + probe | Resources |
| R4 | URI template usability | static + probe | Resources |
| R5 | Subscriptions / listChanged | static | Spec Extras |
| P1 | Prompts defined at all | static | Spec Extras |
| P2 | Prompt argument docs | static | Protocol Hygiene |
| P3 | Prompt renders with valid args | probe | Protocol Hygiene |
| S1 | Handshake & capability honesty | probe | Protocol Hygiene |
| S2 | `instructions` field used | static | Spec Extras |
| S3 | Probe response time / hangs | probe | Error Quality |

---

## 3. Tool Clarity (T1, T2, T3, T6, T7) — weight 25%

### T1 — Tool description quality
- **Pain:** "Manages user data" tells the model nothing about *when* to pick this tool over `get_user`.
- **Detect:** static gate first — missing or `< 10` words → score 0, skip the judge *for scoring*. (The judge is still consulted once per gated tool, hint-only, to write `suggested_description` — the same pattern as T4's fix_hint judge; a gated score is never judge-influenced.) Otherwise send name + description to the LLM judge (prompt in §10) asking: does it say what the tool does, *when to use it*, and any constraints?
- **Rubric:** 0 = missing/useless · 1 = says *what* but not *when* · 2 = what + when + constraints.
- **fix_hint:** LLM judge's `reason` field, e.g. `"Add a 'use this when…' sentence and note it only searches titles, not content."`

### T2 — Parameter docs & format hints
- **Pain:** `date: string` — ISO or "tomorrow"? The model finds out by erroring.
- **Detect:** walk `inputSchema.properties`. Each param needs a `description`. Any `string` param whose name hints a format (`date`, `time`, `id`, `url`, `email`, `query`, `path`) additionally needs one of: `format`, `pattern`, `enum`, or an example in its description.
- **Rubric (per tool):** 2 = all params documented, no ambiguous strings · 1 = ≥50% documented · 0 = less.
- **fix_hint:** `"date: add description + format, e.g. 'ISO date, YYYY-MM-DD'"`

### T3 — Examples present
- **Pain:** one example call is worth 500 tokens of prose.
- **Detect:** schema contains `examples`, or the tool/param description contains `e.g.`, `example`, or a quoted sample value.
- **Rubric:** 2 = example at tool level · 1 = some param-level hints · 0 = none.

### T6 — Name collisions & generic names
- **Pain:** two servers both expose `search`; the model picks one at random. Names like `process` or `handle` say nothing.
- **Detect:** exact-duplicate names across the full cross-server manifest → fail per collision. Near-duplicates (Levenshtein ≤ 2, e.g. `get_user` / `get_users`) *within* one server → warn. Names in a generic blocklist (`run`, `do`, `execute`, `process`, `handle`, `manage`, `data`) → warn.
- **Rubric (per server):** 2 = clean · 1 = warns only · 0 = any hard collision.

### T7 — Manifest bloat
- **Pain:** 40+ tools degrade selection accuracy; every schema token is context tax.
- **Detect:** serialize the server's full tool manifest (names + descriptions + schemas) and count tokens (`len(text) / 4` approximation is fine).
- **Rubric:** 2 = ≤ 20 tools and ≤ 4k tokens · 1 = ≤ 40 tools and ≤ 10k · 0 = beyond.
- **Severity:** info/warn only — this is advisory, not a bug.

---

## 4. Error Quality (T4, S3) — weight 30% · the flagship

### T4 — Error repairability
- **Pain:** `"Error: 400"` leaves the model flailing; `"date must be YYYY-MM-DD, got 'July 5th'"` gets fixed in one retry. This is the single biggest determinant of whether an agent survives a server.
- **Detect:** for each (non-destructive — see §5) tool, generate 3–5 bad calls from the probe templates in §9. For each probe:
  1. **Protocol behavior:** did the server return a proper JSON-RPC error (e.g. `-32602`) or a `CallToolResult` with `isError: true`? A crash, hang, or silent malformed reply → automatic 0 for that probe.
  2. **The garbage-acceptance trap:** if a deliberately invalid call ***succeeds***, that is the worst outcome — validation is broken. Score 0, severity `fail`, message `"accepted missing required param without error"`. A linter that catches this looks *very* smart in a demo.
  3. **Empirical repair test:** hand the error text + tool schema + original bad call to `heal.py`. Repaired in 1 retry → 2 · in 2 retries → 1 · not repaired → 0.
- **Score per tool** = the heal-loop result averaged over probes (round down). The LLM judge (§10) runs once per failing tool only to *write the fix_hint*, not to score — empirical beats opinion.
- **fix_hint:** `"edit_document: error should name the field, expected format, and received value."`
- **Lint-time repair safety** — *heal executes retries only when a human intended the call.* At lint time a repaired call is live-executed only if the tool is provably read-only: `readOnlyHint: true` or name tokens ∩ `READ_ONLY_WORDS = {get, list, read, search, fetch, query, show}`. Any other tool has its repaired args validated locally against `inputSchema` (jsonschema) instead, and the result message says "repair validated locally (not executed for safety)". Repair retries count against the probe budget. At chatbot runtime the human intended the call, so heal retries execute for real.

### S3 — Response time / hangs
- **Pain:** a tool that hangs forever kills the whole agent loop; timeouts are the failure mode nobody handles.
- **Detect:** every probe call in T4/R1/P3 runs under a client-side timeout (default 10 s). Record latency.
- **Timeout mechanics:** at lint time every probe call is wrapped in a client-side `asyncio.wait_for` (uniform timeout/latency classification); at chatbot runtime tool calls use the session's native `read_timeout_seconds` instead — a long-lived chat session must never have requests cancelled from under it.
- **Rubric (per server):** 2 = all probes < 5 s · 1 = any 5–10 s · 0 = any timeout hit.

---

## 5. Safety (T5) — weight 15%

### T5 — Safety annotations
- **Pain:** the spec has `readOnlyHint`, `destructiveHint`, `idempotentHint` — almost nobody sets them, so `delete_all_records` and `list_all_records` carry identical metadata and the model must infer danger from the *name*.
- **Detect:** static, two passes:
  1. Coverage — fraction of tools with any annotations set.
  2. **Mismatch scan** — tool name matches `DESTRUCTIVE_WORDS = {delete, remove, drop, purge, destroy, overwrite, truncate, wipe, clear, reset}` but `destructiveHint` is unset/false → severity `fail`.
- **Rubric:** any name/annotation mismatch → category hard-fails to 0. Else 2 = ≥ 80% coverage · 1 = ≥ 30% · 0 = less.

### Probe-safety rules (hard rules for the probe engine itself)
A linter must never nuke someone's data. Non-negotiable defaults:

1. Tools flagged destructive — by annotation **or** by `DESTRUCTIVE_WORDS` in the name — are **never probe-called**. The skip surfaces as a report-level probe-safety note (`"active probes skipped for safety"`), **not** a scored CheckResult — a score in either direction would distort Error Quality. Skipped tools are n/a for T4.
2. Everything else gets *invalid inputs only* — probes are designed to be rejected, never to succeed.
3. `--unsafe` flag opts destructive tools into probing (for people testing their own dev servers). Off by default, loudly labeled.
4. Global probe budget (e.g. max 40 calls/server) + the 10 s timeout, so `/doctor` can't hammer or hang on anyone's server.
5. Repaired probe calls (T4's heal test) follow the same rules: live re-execution only for provably read-only tools (see §4's lint-time repair safety), local schema validation otherwise; repair retries count against the budget.
6. `/doctor` inside the chatbot **never reuses chat sessions**. Lint probes cancel via `asyncio.wait_for` (see §4 timeout mechanics), and a chat session must never have requests cancelled from under it — so the doctor reconnects with fresh sessions from the same server specs, lints, and closes them. Zero lint traffic may cross a chat-owned session.

---

## 6. Resources (R1–R4) — weight 15%

### R1 — Readability
- **Pain:** a listed resource that errors on read is a broken promise.
- **Detect:** `resources/list`, then `resources/read` each one (or the first 10 in listing order if there are many — deterministic rather than random so lint runs are reproducible; respect the probe budget).
- **Rubric (per server):** 2 = 100% readable · 1 = ≥ 80% · 0 = less.

### R2 — Context flooding
- **Pain:** need one field, receive a 50k-token dump.
- **Detect:** measure token size of each successful read (`len/4` approx).
- **Rubric:** 2 = all ≤ 2k tokens · 1 = any 2k–10k · 0 = any > 10k.
- **Severity:** warn — sometimes big is legitimate; the report should just make the cost visible.
- **fix_hint:** `"split into per-section resources or add a summary resource"` (and if you build the query-middleware stretch, plug it here).

### R3 — MIME declared & matches
- **Pain:** the model plans how to parse based on `mimeType`; a lie breaks the plan.
- **Detect:** declared `mimeType` present? On read: `application/json` actually `json.loads`? `text/*` actually text, not base64 blob?
- **Rubric:** 2 = declared + matches · 1 = declared, unverifiable · 0 = missing or mismatch.

### R4 — URI template usability
- **Pain:** the model has to construct URIs from templates itself — easy to malform when parameters are undocumented.
- **Detect:** for each `resources/templates/list` entry: are template params described? Then instantiate one plausible URI from the template + docs, and try reading it. (Phase 2: instantiation is deterministic — an example URI extracted from the template description, if present. The Groq-instantiation upgrade lands in Phase 3 with the other LLM work; a documented template with no extractable example scores 1, not 0.)
- **Rubric:** 2 = documented + instantiated read works · 1 = documented only · 0 = undocumented params.

---

## 7. Protocol Hygiene (S1, P2, P3) — weight 10%

### S1 — Handshake & capability honesty
- **Pain:** declared capabilities that don't match reality poison everything downstream.
- **Detect:** `initialize` succeeds cleanly? Then cross-check: declares `tools` but `tools/list` empty → warn; exposes resources/prompts *without* declaring the capability → fail; declares them but the list call errors → fail.
- **Rubric:** 2 = clean · 1 = warns · 0 = any dishonesty.

### P2 — Prompt argument docs
- **Detect:** for each declared prompt, every argument has `description` + explicit `required`.
- **Rubric:** 2 = all documented · 1 = some · 0 = none. (Skip → n/a if server has no prompts; don't punish twice, P1 already covers existence.)

### P3 — Prompt renders
- **Detect:** `prompts/get` with plausible args → returns valid non-empty `messages`? (Phase 2: args are deterministic typed fillers — every declared argument gets a bland string value. Groq-generated args arrive in Phase 3.)
- **Rubric:** 2 = renders · 0 = errors. (n/a if no prompts.)

---

## 8. Spec Extras (R5, P1, S2) — weight 5% · free points nobody claims

These are the "forgotten primitives." Most servers score 0 here — that's the point; it makes the rare good citizen visible.

- **R5 — Subscriptions:** capabilities declare `resources.subscribe` / `resources.listChanged`? 2 = both · 1 = one · 0 = none.
- **P1 — Prompts exist:** server defines ≥ 1 prompt? 2 = yes with docs · 1 = yes · 0 = none.
- **S2 — `instructions` field:** initialize result includes a non-empty `instructions` string (server-level usage guidance for the LLM — the most underused field in the spec)? 2 = present and > 20 words · 1 = present · 0 = absent.

*(Sampling and elicitation are client-side capabilities — they belong to your chatbot's "most spec-complete client" stretch goal, not to server linting.)*

---

## 9. Bad-input probe templates (deterministic — no LLM needed)

Generate from the tool's own `inputSchema`. Every probe is *designed to be rejected*:

| Template | Construction | Expected server behavior |
|----------|--------------|--------------------------|
| `missing_required` | drop one required param | error naming the missing field |
| `wrong_type` | required string → `42`, number → `"abc"` | error naming field + expected type |
| `bad_enum` | enum param → `"__not_a_real_value__"` | error listing valid values |
| `bad_format` | date/url/email-ish param → `"July 5th"` / `"not a url"` | error showing expected format |
| `null_required` | required param → `null` | error, not a crash |
| `unknown_field` | add `"__mcpdoctor_probe__": true` | ignored or clean error (crash = fail) |
| `huge_string` | string param → 100k chars | clean error or truncation, no hang |

Rule of thumb: 3 probes/tool from the top of this list keeps you inside the probe budget; `--thorough` runs all 7.

**Safety tightening for the two tolerate-probes** (`unknown_field`, `huge_string` — the only templates whose success §9 tolerates): their base call must *also* omit one required param (other than the target), so any input-validating server rejects them and they can never mutate state on tools like `write_file`. If a tool has no such param to drop and does not declare `readOnlyHint: true`, these probes are **skipped entirely** with a probe-safety note (`"tolerate-probes skipped: no safe base"`). No tool may ever receive a probe that could plausibly succeed with a mutation.

---

## 10. LLM judge prompts (paste-ready, temperature=0)

**T1 description judge**

```
You are grading an MCP tool description for AI usability.
Tool name: {name}
Description: {description}

Score 0-2:
2 = an AI agent could decide WHEN to use this tool vs alternatives,
    and knows its constraints
1 = says what the tool does, but not when to use it
0 = vague or content-free

Reply with ONLY JSON: {"score": <0|1|2>, "reason": "<one sentence>",
"suggested_description": "<improved version, <=40 words>"}
```

`suggested_description` is your `--fix` stretch goal for free.

**T4 fix_hint writer** (runs only on tools that failed the heal test)

```
An AI agent sent this tool call and got this error, and could not
repair the call from the error text alone.
Tool schema: {schema}
Bad call: {args}
Error returned: {error}

Reply with ONLY JSON: {"fix_hint": "<one sentence telling the server
author what the error message should have said>"}
```

Parsing rule: strip ```json fences, `json.loads`, and on parse failure retry once then default `{"score": 1, "reason": "judge unparseable"}` — never let the judge crash the lint.

---

## 11. Scoring model

- Every check scores 0/1/2 per target; category score = points ÷ max, as %.
- **Weights:** Error Quality 30 · Tool Clarity 25 · Safety 15 · Resources 15 · Protocol Hygiene 10 · Spec Extras 5.
- Overall = weighted sum → letter: A ≥ 90 · B ≥ 75 · C ≥ 60 · D ≥ 45 · F below.
- Categories that are all-n/a (e.g. no resources at all) redistribute their weight proportionally — don't punish a pure tool server for having no resources, but *do* punish declared-but-broken ones.
- Expect real-world servers to land C/D. A linter with teeth is the story — "even the official filesystem server gets a B-" is a great demo line.
- **Degraded-run disclosure:** any run where the LLM judges/repair degraded to safe defaults (missing GROQ_API_KEY, or the API failing) must say so prominently at the top of the report — "GROQ_API_KEY not set - T1/T4 degraded to safe defaults; grade is a floor, not a final." A silent degraded grade is misinformation.

Terminal report sketch (rich):

```
mcpdoctor — document-mcp   (14 tools · 3 resources · 2 prompts)
Overall: C+  (67/100)

  Error Quality    ██████░░░░  58%   edit_document: "400" teaches the model nothing
  Tool Clarity     ███████░░░  71%   3 tools missing param descriptions
  Safety           ░░░░░░░░░░   0%   delete_document: destructive, no destructiveHint  ✗
  Resources        ████████░░  83%   report.pdf resource is 41k tokens
  Protocol         █████████░  90%
  Spec Extras      ██░░░░░░░░  17%   no instructions field, no subscriptions

Top fixes (by points recovered):
 1. delete_document — set destructiveHint: true                     (+15)
 2. edit_document — errors should name field/expected/received       (+9)
 3. search_docs — add "use when…" to description                     (+4)
```

Markdown export = same content, for README badges and CI later.

---

## 12. Build order (static → probes → LLM)

| Phase | Checks | Notes |
|-------|--------|-------|
| **1. Static core** (~Jul 6–12) | S1, S2, T2, T3, T5, T6, T7, P1, P2, R5 | Zero LLM calls, pure manifest inspection. 10 of 18 checks done in week one — instant momentum. Build `CheckResult` + registry + plain-text report here. |
| **2. Probe engine** (~Jul 13–17) | R1, R2, R3, R4, P3, S3 + probe templates §9 | Timeout + budget + destructive-skip rules from day one. |
| **3. Heal loop + judges** (~Jul 18–24) | T4, T1 (+ fix_hints everywhere) | `heal.py` first as a chatbot runtime feature, then reuse it as T4's grader. |
| **4. Polish** (~Jul 25–Aug 2) | rich report, `--fix`, demo, Devpost | Submit by Aug 3, deadline Aug 6 2:30am IST. |

**Build the fixture first:** a deliberately broken `badserver.py` — vague descriptions, undocumented `date: string`, a `delete_everything` tool with no annotations, errors that just say `"400"`, one 40k-token resource, capability it doesn't implement. It's your test suite *and* the star of your demo video: run `/doctor` against it live and watch every category light up red, then against the official filesystem server, then against your own document server.
