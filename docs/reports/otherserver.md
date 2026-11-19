# mcpdoctor — otherserver

- **otherserver** — 2 tools · 3 resources · 1 prompts

**Overall: A (100/100)**

| Category | Score | Bar | Worst finding |
|---|---|---|---|
| Error Quality | 100% | `##########` |  |
| Tool Clarity | 100% | `##########` |  |
| Safety | 100% | `##########` |  |
| Resources | 100% | `##########` |  |
| Protocol Hygiene | 100% | `##########` |  |
| Spec Extras | 100% | `##########` |  |

## Findings
- **[info] S3 otherserver** (2/2) — 17 probe calls, all under 5s (max 0.02s)
- **[info] T4 fetch_metrics** (2/2) — errors let the heal loop repair every bad call in 1 retry (live)
- **[info] T4 search** (2/2) — errors let the heal loop repair every bad call in 1 retry (live)
- **[info] T1 fetch_metrics** (2/2) — It clearly states the tool’s purpose, when to use it, and its single-day constraint with an example date.
- **[info] T1 search** (2/2) — It clearly states the tool’s purpose, when to use it, and its key constraint that it matches titles only, not full text.
- **[info] T2 fetch_metrics** (2/2) — all params documented, no ambiguous strings
- **[info] T2 search** (2/2) — all params documented, no ambiguous strings
- **[info] T3 fetch_metrics** (2/2) — example present at tool level
- **[info] T3 search** (2/2) — example present at tool level
- **[info] T6 otherserver** (2/2) — tool names are unique and descriptive
- **[info] T7 otherserver** (2/2) — 2 tools, ~203 manifest tokens
- **[info] T5 otherserver** (2/2) — 100% of tools carry safety annotations
- **[info] R1 otherserver** (2/2) — 3/3 listed resources readable
- **[info] R2 otherserver** (2/2) — largest of 3 resource(s) is ~2 tokens (demo://item/1)
- **[info] R3 demo://item/1** (2/2) — declared text/plain, content is text
- **[info] R3 demo://item/2** (2/2) — declared text/plain, content is text
- **[info] R3 demo://item/3** (2/2) — declared text/plain, content is text
- **[info] R4 demo://item/{n}** (2/2) — params documented; example URI demo://item/1 reads successfully
- **[info] P2 summarize_hits** (2/2) — all arguments documented
- **[info] P3 summarize_hits** (2/2) — renders 1 message(s) with filler args
- **[info] S1 otherserver** (2/2) — handshake clean, declared capabilities match reality
- **[info] P1 otherserver** (2/2) — 1 prompt(s), all documented
- **[info] R5 otherserver** (2/2) — resource subscriptions: subscribe, listChanged
- **[info] S2 otherserver** (2/2) — instructions present and substantial

## Verification

Recorded on 2026-11-19 with OpenAI `gpt-5.4-mini` and the current demo fixture.
All three previous findings are resolved: T5 safety annotations, R5 resource
subscriptions and list changes, and S2 server instructions. The audit used 17 of
40 available probes and had no degraded LLM results.

The separate live chat test also passed tool calling, error repair, `/doctor`,
and a tool call after the audit through the original chat session. Resource
notification delivery and unsubscribe behavior are checked by offline protocol tests;
R5 itself checks the advertised capabilities.

This is a recorded result, not a guarantee of identical model judgments or timing
on future runs. See the [development guide](../contributing/development.md#live-tests)
to reproduce the live test.
