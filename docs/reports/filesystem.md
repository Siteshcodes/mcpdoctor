# mcpdoctor — secure-filesystem-server

> ⚠️ **LLM call failed (RateLimitError) - T1/T4 degraded to safe defaults; grade is a floor, not a final**

- **secure-filesystem-server** — 14 tools · 0 resources · 0 prompts

**Overall: D (48/100)**

| Category | Score | Bar | Worst finding |
|---|---|---|---|
| Error Quality | 23% | `##--------` | read_file: errors did not let the heal loop repair the call (live) |
| Tool Clarity | 35% | `####------` | read_media_file: params missing descriptions: path; ambiguous string params without format/pattern/enum/example: path |
| Safety | 100% | `##########` |  |
| Resources | n/a | `n/a` |  |
| Protocol Hygiene | 100% | `##########` |  |
| Spec Extras | 0% | `----------` | npx: no instructions field in initialize result |

## Findings
- **[fail] T4 create_directory** (0/2) — errors did not let the heal loop repair the call (validated locally (not executed for safety))
  - fix: error should name the field, the expected format, and the received value
- **[fail] T4 directory_tree** (0/2) — errors did not let the heal loop repair the call (validated locally (not executed for safety))
  - fix: The error message should have explicitly stated that the 'path' property is required and was missing from the input.
- **[fail] T4 get_file_info** (0/2) — errors did not let the heal loop repair the call (validated locally (not executed for safety))
  - fix: error should name the field, the expected format, and the received value
- **[fail] T4 list_directory** (0/2) — errors did not let the heal loop repair the call (validated locally (not executed for safety))
  - fix: error should name the field, the expected format, and the received value
- **[fail] T4 list_directory_with_sizes** (0/2) — errors did not let the heal loop repair the call (validated locally (not executed for safety))
  - fix: error should name the field, the expected format, and the received value
- **[fail] T4 read_file** (0/2) — errors did not let the heal loop repair the call (live)
  - fix: The error message should have explicitly stated that the 'path' field is required and was missing from the input.
- **[fail] T4 read_multiple_files** (0/2) — errors did not let the heal loop repair the call (validated locally (not executed for safety))
  - fix: error should name the field, the expected format, and the received value
- **[fail] T4 search_files** (0/2) — errors did not let the heal loop repair the call (validated locally (not executed for safety))
  - fix: error should name the field, the expected format, and the received value
- **[warn] T4 read_text_file** (1/2) — errors repairable but only after 2 retries (live)
- **[info] S3 npx** (2/2) — 40 probe calls, all under 5s (max 0.02s)
- **[info] T4 read_media_file** (2/2) — errors let the heal loop repair every bad call in 1 retry (validated locally (not executed for safety))
- **[fail] T2 create_directory** (0/2) — params missing descriptions: path; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T2 directory_tree** (0/2) — params missing descriptions: path, excludePatterns; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T2 edit_file** (0/2) — params missing descriptions: path, edits; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T2 get_file_info** (0/2) — params missing descriptions: path; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T2 list_directory** (0/2) — params missing descriptions: path; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T2 move_file** (0/2) — params missing descriptions: source, destination
  - fix: source: add a description explaining what to pass
- **[fail] T2 read_media_file** (0/2) — params missing descriptions: path; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T2 search_files** (0/2) — params missing descriptions: path, pattern, excludePatterns; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T2 write_file** (0/2) — params missing descriptions: path, content; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[fail] T3 create_directory** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 edit_file** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 get_file_info** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 list_allowed_directories** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 list_directory** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 list_directory_with_sizes** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 move_file** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 read_file** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 read_media_file** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 read_multiple_files** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[fail] T3 write_file** (0/2) — no examples anywhere
  - fix: add an example to the tool description - one sample call with realistic values
- **[warn] T1 create_directory** (1/2) — The description explains what the tool does but lacks information on when to use it over alternatives.
  - fix: The description explains what the tool does but lacks information on when to use it over alternatives.
- **[warn] T1 directory_tree** (1/2) — The description explains the tool's functionality but lacks guidance on when to use it.
  - fix: The description explains the tool's functionality but lacks guidance on when to use it.
- **[warn] T1 edit_file** (1/2) — The description explains the tool's functionality but lacks guidance on when to use it.
  - fix: The description explains the tool's functionality but lacks guidance on when to use it.
- **[warn] T1 get_file_info** (1/2) — The description explains what the tool does but lacks information on when to use it over alternatives.
  - fix: The description explains what the tool does but lacks information on when to use it over alternatives.
- **[warn] T1 list_allowed_directories** (1/2) — The description explains the tool's function but lacks guidance on when to use it.
  - fix: The description explains the tool's function but lacks guidance on when to use it.
- **[warn] T1 list_directory** (1/2) — The description explains the tool's function but lacks guidance on when to use it over alternatives.
  - fix: The description explains the tool's function but lacks guidance on when to use it over alternatives.
- **[warn] T1 list_directory_with_sizes** (1/2) — The description explains the tool's functionality but lacks guidance on when to use it.
  - fix: The description explains the tool's functionality but lacks guidance on when to use it.
- **[warn] T1 move_file** (1/2) — The description explains what the tool does but lacks information on when to use it over alternatives.
  - fix: The description explains what the tool does but lacks information on when to use it over alternatives.
- **[warn] T1 read_file** (1/2) — The description only states what the tool does, but does not provide information on when to use it.
  - fix: The description only states what the tool does, but does not provide information on when to use it.
- **[warn] T1 read_media_file** (1/2) — The description explains the tool's functionality but lacks information on when to use it.
  - fix: The description explains the tool's functionality but lacks information on when to use it.
- **[warn] T1 read_multiple_files** (1/2) — The description explains the tool's functionality but lacks guidance on when to use it over alternatives.
  - fix: The description explains the tool's functionality but lacks guidance on when to use it over alternatives.
- **[warn] T1 read_text_file** (1/2) — The description explains the tool's functionality but lacks clear guidance on when to use it over alternatives.
  - fix: The description explains the tool's functionality but lacks clear guidance on when to use it over alternatives.
- **[warn] T1 search_files** (1/2) — The description explains what the tool does but lacks information on when to use it over alternatives.
  - fix: The description explains what the tool does but lacks information on when to use it over alternatives.
- **[warn] T1 write_file** (1/2) — The description explains what the tool does but lacks guidance on when to use it over alternatives.
  - fix: The description explains what the tool does but lacks guidance on when to use it over alternatives.
- **[warn] T2 list_directory_with_sizes** (1/2) — params missing descriptions: path; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[warn] T2 read_file** (1/2) — params missing descriptions: path; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[warn] T2 read_text_file** (1/2) — params missing descriptions: path; ambiguous string params without format/pattern/enum/example: path
  - fix: path: add description + format hint (e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)
- **[info] T2 list_allowed_directories** (2/2) — no parameters to document
- **[info] T2 read_multiple_files** (2/2) — all params documented, no ambiguous strings
- **[info] T3 directory_tree** (2/2) — example present at tool level
- **[info] T3 read_text_file** (2/2) — example present at tool level
- **[info] T3 search_files** (2/2) — example present at tool level
- **[info] T6 npx** (2/2) — tool names are unique and descriptive
- **[info] T7 npx** (2/2) — 14 tools, ~2041 manifest tokens
- **[info] T5 npx** (2/2) — 100% of tools carry safety annotations
- **[info] S1 npx** (2/2) — handshake clean, declared capabilities match reality
- **[warn] P1 npx** (0/2) — no prompts defined
  - fix: define at least one documented prompt - a pre-baked workflow clients can surface
- **[warn] R5 npx** (0/2) — resource subscriptions: none declared
  - fix: support resources.subscribe and resources.listChanged so clients can track changes
- **[warn] S2 npx** (0/2) — no instructions field in initialize result
  - fix: pass instructions="..." at server construction - tell the LLM when and how to use this server

## Top fixes (by points recovered)
1. **read_file** — The error message should have explicitly stated that the 'path' field is required and was missing from the input. (+3)
2. **read_multiple_files** — error should name the field, the expected format, and the received value (+3)
3. **create_directory** — error should name the field, the expected format, and the received value (+3)

## Probe safety
- npx/write_file: active probes skipped for safety
- npx/edit_file: active probes skipped for safety
- npx/move_file: active probes skipped for safety
