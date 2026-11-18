# Working on MCPDoctor

- Python 3.12; run commands with `uv run` and preserve `uv.lock`.
- Application source is in `src/mcpdoctor/`; regression tests are in `tests/`.
- `docs/mcpdoctor-check-spec.md` defines the 18 checks. Keep behavior and the spec aligned.
- The MkDocs site is configured in `mkdocs.yml`. Its source is `docs/`, with minimal
  neutral styling in `docs/assets/documentation.css`. `site/` is generated and must not be committed.
- Preserve existing work. `archive/` is historical reference, not active instructions.
- Never commit `.env`, API keys, credentials, caches, or generated package artifacts.
- Probe safety: destructive tools are skipped unless explicitly opted in; repaired
  calls must honor destructive signals and explicit `readOnlyHint: false`.
- Preserve probe budgets, timeouts, and isolation between chat and doctor sessions.
- Validate code with `uv run pytest -q`; LLM calls are mocked in the default suite.
- Validate docs with `uv run --group docs mkdocs build --strict`.
- Live tests are opt-in (`uv run pytest -m live`) and may use external services.
- GitHub repository: https://github.com/Siteshcodes/mcpdoctor.
