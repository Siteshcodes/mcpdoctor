# Installation

MCPDoctor runs locally and starts MCP servers as child processes using stdio.

## Requirements

- Python **3.12**; the package requires `>=3.12,<3.13`.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git.
- Node.js/npm only for targets launched with `npx`.
- An OpenAI API key only for LLM judgments, suggested rewrites, and chat.

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

For a new checkout, copy the example below. If `.env` already exists, edit it directly
and keep your other settings.

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
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-5.4-mini
```

The CLI loads `.env` through python-dotenv. Existing environment variables take precedence.
Obtain a key from the [OpenAI API dashboard](https://platform.openai.com/api-keys).
Requests use your OpenAI project's API quota and billing. Never commit a real key.

The default [GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
supports the JSON judgments and function calls used here. `OPENAI_MODEL` can select
another model with Chat Completions, JSON mode, function calling, and custom temperature
support. The default model uses no reasoning step; reasoning-only models and models
that require the Responses API for function calls are not supported by this adapter.

### Migrating from Groq

Run `uv sync --frozen` to install the OpenAI SDK. Set `OPENAI_API_KEY` to a new OpenAI
key and use `OPENAI_MODEL` for the model name. `GROQ_API_KEY` and the old `MODEL`
variable are ignored and can be removed from your local configuration. A Groq key
cannot be reused as an OpenAI key.

Without an OpenAI key, static checks and probes still work, with a degraded assessment banner.
An invalid nonempty key attempts API calls and can take longer than an unset key. For
keyless use, leave the key empty in `.env` and unset any exported value.

!!! note "Data sent to the provider"
    With a key configured, judging and repair may send descriptions, schemas, arguments,
    and error text to OpenAI. Chat also sends conversation messages and tool results.

## Verify

```bash
uv run mcpdoctor doctor fixtures/otherserver.py --ascii
```

Expect an `Overall:` line and category scores. A degraded banner is expected without a key.
Continue with [your first audit](first-lint.md).
