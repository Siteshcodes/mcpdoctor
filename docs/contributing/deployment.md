# Publish the documentation

The static MkDocs Material website is hosted on **GitHub Pages**:

**[siteshcodes.github.io/mcpdoctor](https://siteshcodes.github.io/mcpdoctor/)**

The CLI runs on each user's machine. Publishing docs does not host Python, execute MCP
servers, or supply an API key to visitors.

## One-time setup

1. Open [the repository](https://github.com/Siteshcodes/mcpdoctor).
2. Open **Settings → Pages**.
3. Select **GitHub Actions** under **Build and deployment**.
4. Open **Actions → Deploy documentation → Run workflow**, choosing `main`.
5. Wait for `build` and `deploy` to finish. The deployment shows the website URL.

`.github/workflows/docs.yml` installs locked dependencies, builds with strict warnings,
uploads only `site/`, and deploys with scoped Pages permissions. No OpenAI key or separate
hosting secret is required.

See GitHub's [custom Pages workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
for the platform requirements.

## Updates

Edit the documentation and validate:

```bash
uv sync --frozen --group docs
uv run mkdocs build --strict
```

Push reviewed changes to `main`. Changes to docs, configuration, the lockfile, or the
deployment workflow trigger publication. Pull requests build in CI without publishing.
Other changes can be deployed by running the workflow manually.

## Custom domain

Add a domain you own in **Settings → Pages**. Configure DNS using GitHub's
[domain guide](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site),
update `site_url` in `mkdocs.yml`, and keep `docs/CNAME` consistent with the chosen
domain. Update public documentation links and enable HTTPS after verification.

## Other static hosting

`uv run mkdocs build --strict` creates `site/`. Another static host can serve that
complete directory, including assets and the search index. Set `site_url` to the
actual public URL and serve directory URLs through their `index.html` files.
Do not publish the repository root or environment files.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Pages returns 404 | Pages uses Actions and the deployment succeeded |
| Build reports a broken link | Fix the relative Markdown target and rebuild |
| Deployment denied | Repository/environment rules allow main and Pages permissions |
| Missing styles | Complete site output was uploaded; URLs and asset paths are correct |
| Update did not run | Branch and path filters match, or run manually |

## CLI releases are separate

Installation currently uses GitHub source. `uv build` creates a wheel and source
archive under `dist/`; that does not publish to PyPI. A future package release needs
its own ownership, versioning, and publishing configuration.
