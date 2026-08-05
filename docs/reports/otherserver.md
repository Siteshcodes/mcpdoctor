# mcpdoctor — otherserver

- **otherserver** — 2 tools · 0 resources · 1 prompts

**Overall: B (87/100)**

| Category | Score | Bar | Worst finding |
|---|---|---|---|
| Error Quality | 100% | `##########` |  |
| Tool Clarity | 88% | `#########-` | search: The description explains the tool's function but lacks guidance on when to use it over alternatives. |
| Safety | 50% | `#####-----` | otherserver: 50% of tools carry safety annotations |
| Resources | 100% | `##########` |  |
| Protocol Hygiene | 100% | `##########` |  |
| Spec Extras | 50% | `#####-----` | otherserver: resource subscriptions: none declared |

## Findings
- **[info] S3 otherserver** (2/2) — 14 probe calls, all under 5s (max 0.02s)
- **[info] T4 fetch_metrics** (2/2) — errors let the heal loop repair every bad call in 1 retry (live)
- **[info] T4 search** (2/2) — errors let the heal loop repair every bad call in 1 retry (live)
- **[warn] T1 fetch_metrics** (1/2) — The description explains the tool's function but lacks guidance on when to use it over alternatives.
  - fix: The description explains the tool's function but lacks guidance on when to use it over alternatives.
- **[warn] T1 search** (1/2) — The description explains the tool's function but lacks guidance on when to use it over alternatives.
  - fix: The description explains the tool's function but lacks guidance on when to use it over alternatives.
- **[info] T2 fetch_metrics** (2/2) — all params documented, no ambiguous strings
- **[info] T2 search** (2/2) — all params documented, no ambiguous strings
- **[info] T3 fetch_metrics** (2/2) — example present at tool level
- **[info] T3 search** (2/2) — example present at tool level
- **[info] T6 otherserver** (2/2) — tool names are unique and descriptive
- **[info] T7 otherserver** (2/2) — 2 tools, ~203 manifest tokens
- **[warn] T5 otherserver** (1/2) — 50% of tools carry safety annotations
  - fix: annotate tools with readOnlyHint / destructiveHint / idempotentHint
- **[info] R4 demo://item/{n}** (2/2) — params documented; example URI demo://item/1 reads successfully
- **[info] P2 summarize_hits** (2/2) — all arguments documented
- **[info] P3 summarize_hits** (2/2) — renders 1 message(s) with filler args
- **[info] S1 otherserver** (2/2) — handshake clean, declared capabilities match reality
- **[warn] R5 otherserver** (0/2) — resource subscriptions: none declared
  - fix: support resources.subscribe and resources.listChanged so clients can track changes
- **[info] P1 otherserver** (2/2) — 1 prompt(s), all documented
- **[info] S2 otherserver** (1/2) — instructions present but thin (19 words)
  - fix: pass instructions="..." at server construction - tell the LLM when and how to use this server

## Top fixes (by points recovered)
1. **otherserver** — annotate tools with readOnlyHint / destructiveHint / idempotentHint (+8)
2. **otherserver** — support resources.subscribe and resources.listChanged so clients can track changes (+2)
3. **search** — The description explains the tool's function but lacks guidance on when to use it over alternatives. (+2)
