# Run your first lint

The `doctor` command accepts a Python script path or a quoted command. The server is
started by mcpdoctor, inspected, and closed after the report is produced.

```bash
uv run mcpdoctor doctor fixtures/badserver.py
```

You can lint multiple servers together. Cross-server checks then detect duplicate or
ambiguous tool names:

```bash
uv run mcpdoctor doctor server-a.py server-b.py
```

## Read the report

The report contains:

1. An overall letter grade and numeric score.
2. Category scores such as Tool Clarity and Error Quality.
3. Findings attached to a server, tool, resource, or prompt.
4. Top fixes ranked by points recovered.
5. Probe-safety and degraded-mode notes when applicable.

Write a Markdown copy for a pull request or CI artifact:

```bash
uv run mcpdoctor doctor fixtures/badserver.py --md report.md
```

For a plain-text terminal report:

```bash
uv run mcpdoctor doctor fixtures/badserver.py --ascii
```

## Improve descriptions

Add `--fix` to print ready-to-paste suggestions for tools that fail the description
quality check:

```bash
uv run mcpdoctor doctor fixtures/badserver.py --fix
```
