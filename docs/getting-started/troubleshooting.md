# Troubleshooting

## Missing uv or Python

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), restart the terminal,
and run `uv python install 3.12`. Then `uv sync --frozen` from the repository root.
Use `uv run mcpdoctor ...` to select the project environment.

## “Could not start MCP server”

Run the reported command by itself. Check the executable, working directory, file path,
and server dependencies. Group launch commands and paths with spaces in quotes.

The server must use stdio, with protocol messages on stdout and logs on stderr. An HTTPS
endpoint is not a supported launch target. Unresponsive initialization times out after 30 seconds.

## Missing key or degraded assessment

Static checks and probes still work. Set `GROQ_API_KEY` in `.env` for LLM judgments and
chat. Exported environment values override `.env`. Invalid keys, network failures, and
rate limits can also cause fallbacks.

Check the provider account and quota for repeated failures. `MODEL` selects the Groq
model; it must support the JSON output and tool calls the application uses.

## Chat reports tool_use_failed

The provider may reject a generated call before it reaches the server. Rephrase so
argument types match the schema. For the healing example, use a string that passes schema
validation but fails the fixture's date-format validation.

## A tool is absent from chat

Discovery follows pagination. If multiple servers expose the same name, chat uses the
first one. Audit them together to detect collisions and rename tools at the server level.

## Markdown export fails

Create the parent directory first, then use `--md reports/latest.md`.

## Website changes are not live

Check Actions for a successful documentation deployment and confirm Pages uses GitHub
Actions. See [deployment](../contributing/deployment.md).
