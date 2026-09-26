# Development

## Set up

```bash
uv sync
uv run pytest -q
```

The default test command excludes live tests that download or launch external servers.
Run those explicitly when you have the required environment:

```bash
uv run pytest -q -m live
```

## Preview the documentation

Install the optional docs dependency group and start the live-reloading server:

```bash
uv sync --group docs
uv run mkdocs serve
```

Build the static site exactly as CI or GitHub Pages would:

```bash
uv run mkdocs build --strict
```

## Documentation guidelines

- Prefer task-oriented pages over long undifferentiated references.
- Keep commands copy-pasteable and verify them against the current CLI.
- Link to the canonical check specification instead of duplicating detailed scoring rules.
- Mark roadmap ideas clearly so they are not mistaken for supported behavior.
