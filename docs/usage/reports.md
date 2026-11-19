# Understanding reports

## Output formats

```bash
uv run mcpdoctor doctor fixtures/otherserver.py
uv run mcpdoctor doctor fixtures/otherserver.py --ascii
uv run mcpdoctor doctor fixtures/otherserver.py --md report.md
```

The default is a Rich terminal card. `--ascii` prints detailed plain text; `--md`
also writes Markdown. The export directory must exist. JSON/CSV is not a CLI output format.

## Scoring

Each applicable finding awards 0–2 points. Category percentages divide earned by available
points. Overall is a weighted mean of categories with results.

| Category | Weight | IDs |
| --- | ---: | --- |
| Error quality | 30 | T4, S3 |
| Tool clarity | 25 | T1, T2, T3, T6, T7 |
| Safety | 15 | T5 |
| Resources | 15 | R1, R2, R3, R4 |
| Protocol hygiene | 10 | S1, P2, P3 |
| Spec extras | 5 | R5, P1, S2 |

Grades: **A ≥ 90**, **B ≥ 75**, **C ≥ 60**, **D ≥ 45**, **F < 45**.
The displayed score is rounded; the grade uses the unrounded score.

## Qualifications matter

A missing key or failed API call produces a degraded banner. The current banner calls the
grade a “floor”; interpret it as provisional. It is not a mathematical lower bound:
a fallback T1 score of 1 can exceed a real judge score of 0.

For T4, “validated locally” means proposed repair arguments passed JSON Schema validation.
It does not prove that the server would accept or successfully execute the call.
Skipped tools and budget-limited probes are not evidence of passing behavior.

Top fixes estimate recoverable points under the current findings and category denominators.
Gains retain up to two decimal places; positive gains below 0.01 are shown as `<0.01`.
Their displayed sum can differ slightly from the actual total improvement because of rounding.
Changing the server inventory can change the weights in a later report.

Resource templates can be audited even when the server lists no static resources.
Those findings appear under R4. Subscription support (R5) contributes to Spec Extras,
so its warning can coexist with a Resources category score of 100%.

## Example reports

Historical snapshots; server versions, API availability, model responses, and latency can
change fresh results:

- [Flawed fixture](../reports/badserver.md)
- [Well-described fixture](../reports/otherserver.md)
- [Filesystem server](../reports/filesystem.md)
- [Document server](../reports/document-server.md)
