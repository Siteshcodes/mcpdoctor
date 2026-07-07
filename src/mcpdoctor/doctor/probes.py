"""Bad-input probe templates (spec §9), generated deterministically from a
tool's inputSchema. No I/O, no LLM - pure functions the engine can plan with.

Every probe is designed to be rejected. The two tolerate-probes
(unknown_field, huge_string) are the only ones whose success §9 accepts, so
their base call must also carry a hard schema violation (omit one required
param); when no safe base exists and the tool isn't readOnlyHint=true, they
are skipped entirely (spec §9 safety tightening). No probe may ever
plausibly succeed with a mutation.
"""

from dataclasses import dataclass, field
from typing import Any

from mcp import types

from mcpdoctor.doctor.vocab import name_tokens

# Spec §9 order - "3 probes/tool from the top of this list" is the default.
TEMPLATE_ORDER = [
    "missing_required",
    "wrong_type",
    "bad_enum",
    "bad_format",
    "null_required",
    "unknown_field",
    "huge_string",
]

DEFAULT_PROBES_PER_TOOL = 3

# bad_format targets only params whose garbage value cannot plausibly be
# valid: dates, urls, emails. Deliberately NOT path/query/id - "July 5th"
# is a perfectly legal filename, and a non-validating server might act on it.
_FORMAT_KEYS = {"date", "date-time", "time", "uri", "url", "email"}
_FORMAT_NAME_TOKENS = {"date", "time", "url", "uri", "email"}

_HUGE_STRING_LEN = 100_000
_UNKNOWN_FIELD = "__mcpdoctor_probe__"


@dataclass
class ProbeConfig:
    """Spec §5 safety knobs. Rides on the Manifest because the check
    signature is fixed at (sessions, manifest)."""

    unsafe: bool = False  # probe destructive tools too - off by default
    thorough: bool = False  # all 7 templates instead of 3
    timeout_s: float = 10.0
    budget_per_server: int = 40


@dataclass
class Probe:
    template: str
    args: dict[str, Any]
    expect: str  # "reject" - success trips the garbage trap | "tolerate"
    target_param: str | None
    note: str  # human description, used in trap messages


@dataclass
class ProbePlan:
    probes: list[Probe] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # probe-safety notes


def _filler(schema: dict) -> Any:
    """Bland, deterministic value satisfying the param's declared shape."""
    if schema.get("enum"):
        return schema["enum"][0]
    return {
        "string": "probe",
        "integer": 1,
        "number": 1,
        "boolean": False,
        "array": [],
        "object": {},
    }.get(schema.get("type"), "probe")


def _base_args(props: dict, required: list[str], omit: str | None = None) -> dict:
    """Minimal call shape: required params only, filled with bland values."""
    return {p: _filler(props[p]) for p in required if p != omit and p in props}


def _format_kind(name: str, schema: dict) -> str | None:
    """Which bad_format garbage applies to this param, if any."""
    fmt = schema.get("format")
    if fmt in _FORMAT_KEYS:
        return fmt
    tokens = name_tokens(name) & _FORMAT_NAME_TOKENS
    if tokens:
        return sorted(tokens)[0]
    return None


_FORMAT_GARBAGE = {
    "date": "July 5th",
    "date-time": "July 5th",
    "time": "July 5th",
    "uri": "not a url",
    "url": "not a url",
    "email": "not-an-email",
}


def _is_read_only(tool: types.Tool) -> bool:
    return tool.annotations is not None and tool.annotations.readOnlyHint is True


def generate_probes(tool: types.Tool, thorough: bool = False) -> ProbePlan:
    """All applicable §9 probes for a tool, in spec order.

    Default: the first DEFAULT_PROBES_PER_TOOL applicable; thorough: all.
    """
    schema = tool.inputSchema or {}
    props: dict[str, dict] = schema.get("properties", {}) or {}
    required: list[str] = [p for p in schema.get("required", []) if p in props]

    plan = ProbePlan()
    tolerate_skipped = False

    def add(template, args, expect, target, note):
        plan.probes.append(Probe(template, args, expect, target, note))

    # missing_required - drop one required param
    if required:
        target = required[0]
        add(
            "missing_required",
            _base_args(props, required, omit=target),
            "reject",
            target,
            f"a call missing required param '{target}'",
        )

    # wrong_type - required string -> 42, number -> "abc"
    typed = [(p, s) for p, s in props.items() if s.get("type") in
             ("string", "integer", "number", "boolean", "array", "object")]
    if typed:
        target, tschema = typed[0]
        wrong = 42 if tschema["type"] == "string" else "abc"
        args = _base_args(props, required)
        args[target] = wrong
        add(
            "wrong_type",
            args,
            "reject",
            target,
            f"a {type(wrong).__name__} for '{target}' (declared {tschema['type']})",
        )

    # bad_enum - enum param -> value not in the enum
    enums = [p for p, s in props.items() if s.get("enum")]
    if enums:
        target = enums[0]
        args = _base_args(props, required)
        args[target] = "__not_a_real_value__"
        add(
            "bad_enum",
            args,
            "reject",
            target,
            f"an invalid enum value for '{target}'",
        )

    # bad_format - date/url/email-ish param -> garbage of the wrong shape
    formatted = [
        (p, kind)
        for p, s in props.items()
        if s.get("type") == "string" and (kind := _format_kind(p, s))
    ]
    if formatted:
        target, kind = formatted[0]
        args = _base_args(props, required)
        args[target] = _FORMAT_GARBAGE[kind]
        add(
            "bad_format",
            args,
            "reject",
            target,
            f"a malformed {kind} ({_FORMAT_GARBAGE[kind]!r}) for '{target}'",
        )

    # null_required - required param -> null
    if required:
        target = required[0]
        args = _base_args(props, required)
        args[target] = None
        add(
            "null_required",
            args,
            "reject",
            target,
            f"null for required param '{target}'",
        )

    # unknown_field - add a field the schema doesn't know. Safe base: also
    # omit one required param; a param-free tool is only safe if read-only.
    if required or _is_read_only(tool):
        omit = required[0] if required else None
        args = _base_args(props, required, omit=omit)
        args[_UNKNOWN_FIELD] = True
        add(
            "unknown_field",
            args,
            "tolerate",
            None,
            f"an unknown field '{_UNKNOWN_FIELD}'",
        )
    else:
        tolerate_skipped = True

    # huge_string - 100k chars into a string param. Safe base: omit a
    # required param OTHER than the target, or the tool is read-only.
    strings = [p for p, s in props.items() if s.get("type") == "string"]
    if strings:
        target = strings[0]
        other_required = [p for p in required if p != target]
        if other_required or _is_read_only(tool):
            omit = other_required[0] if other_required else None
            args = _base_args(props, required, omit=omit)
            args[target] = "x" * _HUGE_STRING_LEN
            add(
                "huge_string",
                args,
                "tolerate",
                target,
                f"a {_HUGE_STRING_LEN}-char string for '{target}'",
            )
        else:
            tolerate_skipped = True

    if not thorough:
        plan.probes = plan.probes[:DEFAULT_PROBES_PER_TOOL]

    # Only note the skip when it changed what actually runs - under the
    # default budget a tolerate-probe at the back of the list would have
    # been truncated anyway.
    if tolerate_skipped and (thorough or len(plan.probes) < DEFAULT_PROBES_PER_TOOL):
        plan.notes.append("tolerate-probes skipped: no safe base")
    return plan
