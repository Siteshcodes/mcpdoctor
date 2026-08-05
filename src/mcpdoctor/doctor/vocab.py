"""Shared vocabulary for checks and probes.

Lives in its own module so that checks_static, probes, and checks_probe can
all import it without any check importing another check (CLAUDE.md rule).
"""

import re

# Spec §5 - tools whose names contain these words are never probe-called
# without --unsafe. Also T5's mismatch scan.
DESTRUCTIVE_WORDS = {
    "delete", "remove", "drop", "purge", "destroy",
    "overwrite", "truncate", "wipe", "clear", "reset",
}

# Spec §4/§5 - a repaired probe call is a VALID call, so at lint time it is
# only re-executed for tools that are provably read-only (by this vocab or
# readOnlyHint); everything else is validated locally instead of run.
READ_ONLY_WORDS = {"get", "list", "read", "search", "fetch", "query", "show"}


def name_tokens(name: str) -> set[str]:
    """snake_case / camelCase / kebab-case name -> lowercase word tokens."""
    words: list[str] = []
    for part in re.split(r"[^a-zA-Z0-9]+", name):
        words.extend(re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", part))
    return {w.lower() for w in words if w}
