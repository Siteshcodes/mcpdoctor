# Contributing

Use Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Siteshcodes/mcpdoctor.git
cd mcpdoctor
uv sync --frozen --group docs
uv run pytest -q
uv run mkdocs build --strict
```

Create a focused branch, add regression coverage for behavior changes, and open a
pull request. Explain the problem, resulting behavior, and validation performed.
Update the check specification and user documentation when behavior changes.

Default tests use fixture servers and mocked LLM responses. Live tests are opt-in;
see [development](docs/contributing/development.md). Avoid probing production data.

See [architecture](docs/contributing/architecture.md) for the module layout and
[deployment](docs/contributing/deployment.md) for the documentation release process.
