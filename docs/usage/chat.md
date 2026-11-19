# Self-healing chat

Configure `OPENAI_API_KEY`, then connect the assistant to a fixture:

```bash
uv run mcpdoctor chat fixtures/otherserver.py
```

## Try a repair

```text
Call fetch_metrics with the date set to the literal text "July 5th". Do not convert it.
```

The fixture accepts a string but returns a helpful error if it is not an ISO date.
When the model emits that call, the healing engine receives the schema, failed arguments,
and error. It proposes corrected arguments and retries up to twice. Success prints
`[self-healed]` and returns the real result to the model.

This is an illustrative prompt, not a deterministic transcript. The model may normalize
the date before calling. Provider-side validation may reject a call before it reaches the
server. Neither the chosen year nor successful recovery is guaranteed.

## Audit during chat

```text
/doctor
/doctor --thorough
```

Audits open and close fresh connections. They do not send probes through chat-owned
sessions. `/doctor --unsafe` is refused.

## Operational limits

- Chat executes real calls and repair retries. A failing tool may already have changed
  state; use appropriate development data, especially for non-idempotent operations.
- Tool calls use a 30-second client timeout. Cancellation does not roll back server work.
- Malformed JSON, non-object arguments, and non-finite numbers are rejected before
  execution. The model receives a tool error and can submit corrected arguments.
- If servers expose the same tool name, chat uses the first one. Audit both to find
  collisions and qualify names in the servers.
- API failures are displayed in the REPL; failed turns restore conversation history.
- Conversation messages, tool schemas, and returned tool text are sent to OpenAI.

See [troubleshooting](../getting-started/troubleshooting.md).
