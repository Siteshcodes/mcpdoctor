# Installation

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- An MCP server exposed as a Python script or a command line
- A `GROQ_API_KEY` for the two optional LLM-judged checks and chat

The key is optional. Without it, static and probe checks still run and the report marks
LLM-dependent results as degraded.

## Install from source

```bash
git clone https://github.com/Siteshcodes/mcp-doctor.git
cd mcp-doctor
uv sync
```

For local development of this documentation site:

```bash
uv sync --group docs
uv run mkdocs serve
```

Open the local URL printed by MkDocs, usually `http://127.0.0.1:8000`.

## Configure the optional model key

Create a `.env` file in the project directory:

```dotenv
GROQ_API_KEY=your-key-here
```

Never commit `.env` or a real API key.
