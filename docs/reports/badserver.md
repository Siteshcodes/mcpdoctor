# mcpdoctor — badserver

> ⚠️ **LLM call failed (RateLimitError) - T1/T4 degraded to safe defaults; grade is a floor, not a final**

- **badserver** — 7 tools · 2 resources · 0 prompts

**Overall: F (25/100)**

| Category | Score | Bar | Worst finding |
|---|---|---|---|
| Error Quality | 43% | `####------` | get_data: errors did not let the heal loop repair the call (live) |
| Tool Clarity | 7% | `#---------` | process: static gate: only 1 words - says what but not when to use it |
| Safety | 0% | `----------` | delete_everything: destructive name but destructiveHint unset - indistinguishable from a read-only tool by metadata |
| Resources | 40% | `####------` | data://config: declared application/json but content is not valid JSON |
| Protocol Hygiene | 50% | `#####-----` | badserver: prompts capability declared but nothing registered (framework default) |
| Spec Extras | 0% | `----------` | badserver: no instructions field in initialize result |

## Findings
- **[fail] T4 get_data** (0/2) — errors did not let the heal loop repair the call (live)
  - fix: error should name the field, the expected format, and the received value
- **[fail] T4 get_dates** (0/2) — errors did not let the heal loop repair the call (validated locally (not executed for safety))
  - fix: error should name the field, the expected format, and the received value
- **[fail] T4 log_event** (0/2) — accepted a malformed date ('July 5th') for 'when' without error - input validation is broken
  - fix: error should name the field, the expected format, and the received value
- **[fail] T4 search** (0/2) — errors did not let the heal loop repair the call (validated locally (not executed for safety))
  - fix: error should name the field, the expected format, and the received value
- **[info] S3 badserver** (2/2) — 23 probe calls, all under 5s (max 0.03s)
- **[info] T4 handle** (2/2) — errors let the heal loop repair every bad call in 1 retry (validated locally (not executed for safety))
- **[info] T4 process** (2/2) — errors let the heal loop repair every bad call in 1 retry (validated locally (not executed for safety))
- **[fail] T1 delete_everything** (0/2) — static gate: only 1 words - says what but not when to use it
  - fix: only 1 words - says what but not when to use it
- **[fail] T1 get_data** (0/2) — static gate: only 2 words - says what but not when to use it
  - fix: only 2 words - says what but not when to use it
- **[fail] T1 get_dates** (0/2) — static gate: only 2 words - says what but not when to use it
  - fix: only 2 words - says what but not when to use it
- **[fail] T1 handle** (0/2) — static gate: only 1 words - says what but not when to use it
  - fix: only 1 words - says what but not when to use it
- **[fail] T1 log_event** (0/2) — static gate: only 1 words - says what but not when to use it
  - fix: only 1 words - says what but not when to use it
- **[fail] T1 process** (0/2) — static gate: only 1 words - says what but not when to use it
  - fix: only 1 words - says what but not when to use it
- **[fail] T1 search** (0/2) — static gate: only 1 words - says what but not when to use it
  - fix: only 1 words - says what but not when to use it
- **[fail] T2 delete_everything** (0/2) — params missing descriptions: target
  - fix: target: add a description explaining what to pass
- **[fail] T2 get_data** (0/2) — params missing descriptions: date; ambiguous string params without format/pattern/enum/example: date
  - fix: date: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T2 get_dates** (0/2) — params missing descriptions: date; ambiguous string params without format/pattern/enum/example: date
  - fix: date: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T2 handle** (0/2) — params missing descriptions: input
  - fix: input: add a description explaining what to pass
- **[fail] T2 log_event** (0/2) — params missing descriptions: when
  - fix: when: add a description explaining what to pass
- **[fail] T2 process** (0/2) — params missing descriptions: data
  - fix: data: add a description explaining what to pass
- **[fail] T2 search** (0/2) — params missing descriptions: query; ambiguous string params without format/pattern/enum/example: query
  - fix: query: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T3 delete_everything** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 get_data** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 get_dates** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 handle** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 log_event** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 process** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 search** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[warn] T6 badserver** (1/2) — generic names: process, handle; near-duplicates: get_data/get_dates
  - fix: rename 'process' to something unique and action-specific, e.g. 'badserver_process'
- **[info] T7 badserver** (2/2) — 7 tools, ~356 manifest tokens
- **[fail] T5 delete_everything** (0/2) — destructive name but destructiveHint unset - indistinguishable from a read-only tool by metadata
  - fix: set destructiveHint: true on delete_everything
- **[fail] R3 data://config** (0/2) — declared application/json but content is not valid JSON
  - fix: declare the mimeType the content actually has - agents parse based on it
- **[fail] R4 data://entry/{key}** (0/2) — no description at all
  - fix: describe every template param and include a working example URI in the description
- **[warn] R2 badserver** (0/2) — largest of 2 resource(s) is ~38250 tokens (data://big-report)
  - fix: split into per-section resources or add a summary resource
- **[info] R1 badserver** (2/2) — 2/2 listed resources readable
- **[info] R3 data://big-report** (2/2) — declared text/plain, content is text
- **[warn] S1 badserver** (1/2) — prompts capability declared but nothing registered (framework default)
  - fix: declare exactly the capabilities the server implements - register the primitive or drop the claim
- **[warn] P1 badserver** (0/2) — no prompts defined
  - fix: define at least one documented prompt - a pre-baked workflow clients can surface
- **[warn] R5 badserver** (0/2) — resource subscriptions: none declared
  - fix: support resources.subscribe and resources.listChanged so clients can track changes
- **[warn] S2 badserver** (0/2) — no instructions field in initialize result
  - fix: pass instructions="..." at server construction - tell the LLM when and how to use this server

## Top fixes (by points recovered)
1. **delete_everything** — set destructiveHint: true on delete_everything (+15)
2. **badserver** — declare exactly the capabilities the server implements - register the primitive or drop the claim (+5)
3. **get_data** — error should name the field, the expected format, and the received value (+4)

## Probe safety
- badserver/delete_everything: active probes skipped for safety
