# Reports and examples

The report renderer supports Rich terminal output, plain ASCII output, and Markdown.
Markdown output is useful for pull requests and CI artifacts:

```bash
uv run mcpdoctor doctor fixtures/badserver.py --md report.md
```

The repository includes complete examples:

- [Bad server](../reports/badserver.md)
- [Document server](../reports/document-server.md)
- [Filesystem server](../reports/filesystem.md)
- [Other server](../reports/otherserver.md)

When reviewing a report, start with **Top fixes**. Each fix estimates how many points
the change can recover, so a server owner can prioritize high-impact improvements first.
