# mcpdoctor — DocumentMCP

- **DocumentMCP** — 2 tools · 1 resources · 1 prompts

**Overall: D (54/100)**

| Category | Score | Bar | Worst finding |
|---|---|---|---|
| Error Quality | 67% | `#######---` | read_doc_content: errors did not let the heal loop repair the call (live) |
| Tool Clarity | 44% | `####------` | read_doc_content: static gate: only 9 words - says what but not when to use it |
| Safety | 0% | `----------` | mcp_server: 0% of tools carry safety annotations |
| Resources | 75% | `########--` | docs://documents/{doc_id}: no description at all |
| Protocol Hygiene | 100% | `##########` |  |
| Spec Extras | 33% | `###-------` | mcp_server: no instructions field in initialize result |

## Findings
- **[fail] T4 read_doc_content** (0/2) — errors did not let the heal loop repair the call (live)
  - fix: The error message should have explicitly stated that the 'doc_id' field is required and was missing from the input.
- **[info] S3 mcp_server** (2/2) — 14 probe calls, all under 5s (max 0.02s)
- **[info] T4 edit_doc** (2/2) — errors let the heal loop repair every bad call in 1 retry (validated locally (not executed for safety))
- **[fail] T1 read_doc_content** (0/2) — static gate: only 9 words - says what but not when to use it
  - fix: only 9 words - says what but not when to use it
- **[fail] T3 edit_doc** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 read_doc_content** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[warn] T1 edit_doc** (1/2) — The description lacks information on when to use the tool or its constraints.
  - fix: The description lacks information on when to use the tool or its constraints.
- **[warn] T2 edit_doc** (1/2) — ambiguous string params without format/pattern/enum/example: doc_id
  - fix: doc_id: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[warn] T2 read_doc_content** (1/2) — ambiguous string params without format/pattern/enum/example: doc_id
  - fix: doc_id: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[info] T6 mcp_server** (2/2) — tool names are unique and descriptive
- **[info] T7 mcp_server** (2/2) — 2 tools, ~227 manifest tokens
- **[fail] T5 mcp_server** (0/2) — 0% of tools carry safety annotations
  - fix: annotate tools with readOnlyHint / destructiveHint / idempotentHint
- **[fail] R4 docs://documents/{doc_id}** (0/2) — no description at all
  - fix: describe every template param and include a working example URI in the description
- **[info] R1 mcp_server** (2/2) — 1/1 listed resources readable
- **[info] R2 mcp_server** (2/2) — largest of 1 resource(s) is ~25 tokens (docs://documents)
- **[info] R3 docs://documents** (2/2) — declared application/json, content parses as JSON
- **[info] P2 format_document** (2/2) — all arguments documented
- **[info] P3 format_document** (2/2) — renders 1 message(s) with filler args
- **[info] S1 mcp_server** (2/2) — handshake clean, declared capabilities match reality
- **[warn] R5 mcp_server** (0/2) — resource subscriptions: none declared
  - fix: support resources.subscribe and resources.listChanged so clients can track changes
- **[warn] S2 mcp_server** (0/2) — no instructions field in initialize result
  - fix: pass instructions="..." at server construction - tell the LLM when and how to use this server
- **[info] P1 mcp_server** (2/2) — 1 prompt(s), all documented

## Top fixes (by points recovered)
1. **mcp_server** — annotate tools with readOnlyHint / destructiveHint / idempotentHint (+15)
2. **read_doc_content** — The error message should have explicitly stated that the 'doc_id' field is required and was missing from the input. (+10)
3. **docs://documents/{doc_id}** — describe every template param and include a working example URI in the description (+4)
