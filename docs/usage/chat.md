# Self-healing chat

Launch a chat session with one or more servers:

```bash
uv run mcpdoctor chat fixtures/otherserver.py
```

When a tool call fails, the loop sends the original arguments, the tool schema, and the
server error back to the model. It proposes corrected arguments and retries. Successful
repairs are shown with a `[self-healed]` marker.

For example, a tool may reject `July 5th` with:

```text
date must be YYYY-MM-DD, got 'July 5th'
```

The model can then retry with `2026-07-05`.

## Run the doctor from chat

Inside a chat, use:

```text
/doctor
/doctor --thorough
```

With no arguments, `/doctor` lints the servers used to start the chat. Linting uses fresh
MCP sessions so probes cannot cancel or interfere with a live conversation.

## Limitations

The model provider validates tool-call types before the tool body runs. The most useful
healing examples therefore use schema-valid arguments that the server body rejects, such
as a badly formatted date, rather than a wrong-typed value.
