# Your first audit

## 1. Run the flawed fixture

From the repository root:

```bash
uv run mcpdoctor doctor fixtures/badserver.py --ascii
```

This fixture includes vague descriptions, missing safety annotations, invalid JSON advertised
as JSON, and an oversized resource. A low grade is expected. Look for the safety note
confirming `delete_everything` was skipped.

## 2. Read the results

- **Overall:** weighted category score.
- **Findings:** check ID, target, score, and suggested fix.
- **Top fixes:** improvements ranked by recoverable points.
- **Probe safety:** skipped operations and exhausted budgets.
- **Degraded:** fallback LLM results; treat the grade as provisional.

Results vary with model output, API availability, server version, and latency. Saved
[example reports](../usage/reports.md#example-reports) are historical snapshots.

## 3. Audit your server

```bash
uv run mcpdoctor doctor path/to/server.py
uv run mcpdoctor doctor "python path/to/server.py --port 9000"
uv run mcpdoctor doctor "node path/to/server.js"
uv run mcpdoctor doctor "path with spaces/server.py"
```

The server must speak MCP over **stdio**, with protocol messages on stdout and logs on
stderr. HTTP/SSE URLs are not supported launch targets.

On PowerShell, group a launch command containing quoted Windows paths with single quotes:

```powershell
uv run mcpdoctor doctor 'python "C:\MCP servers\server.py"'
```

Use trusted development servers and disposable data. Read [probe safety](../checks/probe-safety.md).

## 4. Save and improve

```bash
uv run mcpdoctor doctor fixtures/otherserver.py --md report.md --fix
```

The export's parent directory must exist. `--fix` prints proposed descriptions when the
LLM supplies them; it does not edit files. Apply relevant changes and run the audit again.

## 5. Inspect multiple servers

```bash
uv run mcpdoctor doctor fixtures/badserver.py fixtures/otherserver.py
```

This gives one combined grade and detects cross-server name collisions. Audit servers
separately if you want individual grades.
