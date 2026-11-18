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

Static checks and probes still work. Set `OPENAI_API_KEY` in `.env` for LLM judgments and
chat. Exported environment values override `.env`. Invalid keys, network failures, and
rate limits can also cause fallbacks.

`OPENAI_MODEL` selects the model; the default is `gpt-5.4-mini`. It must support Chat
Completions, JSON mode, function calls, and temperature settings. Old `GROQ_API_KEY`
and `MODEL` values are ignored. Use an OpenAI API key, not a Groq key.

## OpenAI authentication, quota, or model errors

| Error | Action |
| --- | --- |
| Authentication / 401 | Check `OPENAI_API_KEY`, including exported values that override `.env` |
| Rate limit / 429 | Wait before retrying; reduce request frequency |
| `insufficient_quota` / 429 | Check the OpenAI project's API billing and usage limits; waiting alone will not fix exhausted quota |
| Model not found / access denied | Check `OPENAI_MODEL` and the project's model access and key permissions |
| Bad request / 400 | Use the default model or verify the selected model's supported parameters and tool schemas |
| Timeout or connection error | Check connectivity; individual provider requests have a 20-second timeout |

Chat reports provider errors without printing the raw response body and keeps the
conversation usable after a failed request. Lint checks fall back to safe defaults
and disclose the failed assessment.

## A tool is absent from chat

Discovery follows pagination. If multiple servers expose the same name, chat uses the
first one. Audit them together to detect collisions and rename tools at the server level.

## Markdown export fails

Create the parent directory first, then use `--md reports/latest.md`.

## Website changes are not live

Check Actions for a successful documentation deployment and confirm Pages uses GitHub
Actions. See [deployment](../contributing/deployment.md).
