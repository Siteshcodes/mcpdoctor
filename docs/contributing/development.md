# Development

## Setup and validation

```bash
git clone https://github.com/Siteshcodes/mcpdoctor.git
cd mcpdoctor
uv sync --frozen --group docs
uv run pytest -q
uv run mkdocs build --strict
uv build
```

CI tests Python 3.12 on Ubuntu and Windows, builds the package, and validates the site
with strict warnings. It does not require a Groq secret.

Default tests use local fixtures and mocked LLM responses. They cover command parsing,
malformed judge fields, pagination, budgets, safety classification, scoring, startup
failures, and chat-session isolation.

## Live tests

```bash
uv run pytest -q -m live
```

These opt-in tests may download the filesystem server through `npx` and contact Groq
when a key is available. Provider failures can skip the judge test. Mocked tests do not
establish live provider availability.

## Website preview

```bash
uv run --group docs mkdocs serve
```

Open the printed URL, usually `http://127.0.0.1:8000`. Content lives under `docs/`.
The homepage is ordinary Markdown in `docs/index.md`; neutral styling lives in
`docs/assets/documentation.css`. Keep the layout simple and focused on documentation.
Generated `site/` output is ignored.

## Conventions

- Keep source, tests, docs, and historical artifacts in their dedicated directories.
- Update `docs/mcpdoctor-check-spec.md` when check behavior changes.
- Add focused regression coverage; keep network calls out of default tests.
- Never commit environment files, credentials, caches, or generated artifacts.
- Use the canonical GitHub and Pages URLs in `mkdocs.yml` and `pyproject.toml`.

The [archive](https://github.com/Siteshcodes/mcpdoctor/tree/main/archive) preserves planning,
submission assets, audits, and the original prototype. It is excluded from the website and wheel.
