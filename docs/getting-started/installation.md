# Installation

MCPDoctor runs locally and starts MCP servers as child processes using stdio.

## Requirements

- Python **3.12**; the package requires `>=3.12,<3.13`.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git.
- Node.js/npm only for targets launched with `npx`.
- A Groq API key only for LLM judgments, suggested rewrites, and chat.

## Install from GitHub

```bash
git clone https://github.com/Siteshcodes/mcpdoctor.git
cd mcpdoctor
uv sync --frozen
uv run mcpdoctor --help
```

If Python 3.12 is missing, run `uv python install 3.12` and repeat the sync.
These instructions install from source; they do not assume a PyPI release.

## Optional LLM configuration

=== "Windows PowerShell"

    ```powershell
    Copy-Item .env.example .env
    notepad .env
    ```

=== "macOS / Linux"

    ```bash
    cp .env.example .env
    # Open .env in your preferred editor.
    ```

Set:

```dotenv
GROQ_API_KEY=your-key-here
MODEL=llama-3.3-70b-versatile
```

The CLI loads `.env` through python-dotenv. Existing environment variables take precedence.
Obtain a key from the [Groq console](https://console.groq.com/keys). Never commit a real key.

Without a key, static checks and probes still work, with a degraded assessment banner.
An invalid nonempty key attempts API calls and can take longer than an unset key. For
keyless use, leave the key empty in `.env` and unset any exported value.

!!! note "Data sent to the provider"
    With a key configured, judging and repair may send descriptions, schemas, arguments,
    and error text to Groq. Chat also sends conversation messages and tool results.

## Verify

```bash
uv run mcpdoctor doctor fixtures/otherserver.py --ascii
```

Expect an `Overall:` line and category scores. A degraded banner is expected without a key.
Continue with [your first audit](first-lint.md).
