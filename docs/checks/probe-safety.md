# Probe safety

MCPDoctor starts server processes and makes active calls. Use trusted development servers
and disposable data. These safeguards reduce risk; they cannot establish that arbitrary
server code is safe or that rejected inputs have no side effects.

## Defaults

1. Destructive name tokens or `destructiveHint: true` skip tools unless `--unsafe` is supplied.
2. Tool probes deliberately send invalid inputs. Servers accepting them may still mutate state.
3. Active probes have a **10-second timeout** and **40-call budget per server**, shared by
   resource reads, templates, prompts, tool probes, and live repair retries.
4. Initialization and discovery requests use a **30-second session read timeout**.
5. Chat `/doctor` uses fresh sessions, separate from live chat connections.

A timeout stops the client waiting. It cannot undo server work already performed.

## Repair retries

- Destructive signals prevent read-only classification, even under `--unsafe`.
- Explicit `readOnlyHint: false` overrides read-like names.
- Otherwise, `readOnlyHint: true` or tokens such as `get`, `read`, or `search` allow a live retry.
- Other repairs, or retries after budget exhaustion, use local JSON Schema validation.

Names and metadata are heuristics, not proof. Reports distinguish local validation from
live execution. Chat retries execute real calls for the user's intended task.

## Templates

Default runs select the first three applicable templates per tool; `--thorough` selects
all applicable templates within the same budget.

| Template | Input |
| --- | --- |
| Missing required | Omit a required parameter |
| Wrong type | Substitute an incompatible primitive |
| Bad enum | Supply an option outside the enum |
| Bad format | Malformed date, URL, or email text |
| Null required | Null for a required non-nullable input |
| Unknown field | Add an unexpected field to a guarded base call |
| Huge string | Oversized string with the generator's guard |

The last two use an intentionally invalid base where possible. They may be skipped when
no guarded base exists and the tool lacks `readOnlyHint: true`.

## Unsafe mode

```bash
uv run mcpdoctor doctor my-development-server.py --unsafe
```

This includes destructive tools in invalid-input probes. It does not remove budgets or
bypass repair classification. The CLI prints a warning; chat refuses this option.
