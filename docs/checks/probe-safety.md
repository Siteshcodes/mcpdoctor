# Probe safety

Probes are designed to be rejected. They are not synthetic success calls and must not
mutate a user's data.

## Default guarantees

1. Tools with destructive names or `destructiveHint: true` are never probe-called by
   default.
2. Probes use invalid arguments and run under a 10-second timeout.
3. A global call budget prevents a lint run from hammering a server.
4. A repaired probe is executed only for tools proven read-only. Otherwise its arguments
   are validated locally against the schema.
5. Chat `/doctor` runs against fresh sessions, never a live chat-owned session.

## Unsafe mode

`--unsafe` opts destructive tools into probing. Use it only with a development server
and data you can afford to lose:

```bash
uv run mcpdoctor doctor my-server.py --unsafe
```

The CLI prints a prominent warning whenever unsafe mode is enabled.

## Probe templates

The default sweep uses a subset of these templates:

- missing required parameter
- wrong type
- invalid enum
- invalid format
- null required parameter
- unknown field
- oversized string

The `--thorough` flag runs all seven templates. The unknown-field and oversized-string
templates also require a safe rejected base call; otherwise they are skipped.
