# CLI reference

## `mcpdoctor doctor`

```text
mcpdoctor doctor SERVERS... [OPTIONS]
```

`SERVERS` can be Python script paths or quoted commands such as
`"npx -y @modelcontextprotocol/server-filesystem ./sandbox"`.

| Option | Description |
| --- | --- |
| `--thorough` | Run all seven invalid-input probe templates per tool instead of the default three. |
| `--unsafe` | Include tools identified as destructive in active probes. Off by default. |
| `--ascii` | Render a plain ASCII report instead of the Rich report card. |
| `--md PATH` | Write the report as Markdown to `PATH`. |
| `--fix` | Print rewritten descriptions for T1 failures. |

## `mcpdoctor chat`

```text
mcpdoctor chat SERVERS...
```

Starts an interactive model session against the supplied MCP servers. It requires
`GROQ_API_KEY`; see [Self-healing chat](chat.md).

## Exit behavior and connection errors

If a server cannot start, mcpdoctor prints the command, root cause, and a manual
debugging hint instead of a traceback. Run the displayed command directly when you need
to inspect server startup output.
