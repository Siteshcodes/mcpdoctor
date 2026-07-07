"""Unit tests for deterministic probe generation (spec §9). No I/O."""

from mcp import types

from mcpdoctor.doctor.probes import (
    DEFAULT_PROBES_PER_TOOL,
    generate_probes,
)


def make_tool(props: dict, required: list[str], read_only: bool = False) -> types.Tool:
    return types.Tool(
        name="synthetic",
        inputSchema={"type": "object", "properties": props, "required": required},
        annotations=types.ToolAnnotations(readOnlyHint=True) if read_only else None,
    )


ALL_SEVEN = make_tool(
    {
        "due_date": {"type": "string"},
        "color": {"type": "string", "enum": ["red", "green"]},
    },
    required=["due_date", "color"],
)


def templates(plan):
    return [p.template for p in plan.probes]


def test_all_seven_templates_in_spec_order_under_thorough():
    plan = generate_probes(ALL_SEVEN, thorough=True)
    assert templates(plan) == [
        "missing_required",
        "wrong_type",
        "bad_enum",
        "bad_format",
        "null_required",
        "unknown_field",
        "huge_string",
    ]
    assert plan.notes == []


def test_default_runs_first_three_applicable():
    plan = generate_probes(ALL_SEVEN)
    assert len(plan.probes) == DEFAULT_PROBES_PER_TOOL
    assert templates(plan) == ["missing_required", "wrong_type", "bad_enum"]


def test_missing_required_drops_the_param_and_fills_the_rest():
    plan = generate_probes(ALL_SEVEN, thorough=True)
    probe = plan.probes[0]
    assert "due_date" not in probe.args
    assert probe.args["color"] == "red"  # enum filler = first value
    assert probe.expect == "reject"


def test_wrong_type_sends_int_for_string():
    probe = generate_probes(ALL_SEVEN, thorough=True).probes[1]
    assert probe.args["due_date"] == 42


def test_bad_enum_sends_value_outside_the_enum():
    probe = generate_probes(ALL_SEVEN, thorough=True).probes[2]
    assert probe.args["color"] == "__not_a_real_value__"


def test_bad_format_targets_date_named_param():
    probe = generate_probes(ALL_SEVEN, thorough=True).probes[3]
    assert probe.args["due_date"] == "July 5th"


def test_bad_format_respects_schema_format_key():
    tool = make_tool({"when": {"type": "string", "format": "date"}}, ["when"])
    plan = generate_probes(tool, thorough=True)
    fmt = [p for p in plan.probes if p.template == "bad_format"]
    assert fmt and fmt[0].args["when"] == "July 5th"


def test_bad_format_never_targets_path_or_query_params():
    # "July 5th" is a legal filename - garbage-by-format only applies where
    # garbage cannot plausibly be valid (dates, urls, emails).
    tool = make_tool(
        {"path": {"type": "string"}, "query": {"type": "string"}}, ["path"]
    )
    plan = generate_probes(tool, thorough=True)
    assert "bad_format" not in templates(plan)


def test_null_required_sends_null():
    probe = generate_probes(ALL_SEVEN, thorough=True).probes[4]
    assert probe.args["due_date"] is None


def test_tolerate_probes_carry_a_hard_violation():
    plan = generate_probes(ALL_SEVEN, thorough=True)
    unknown = plan.probes[5]
    assert unknown.args["__mcpdoctor_probe__"] is True
    assert unknown.expect == "tolerate"
    assert "due_date" not in unknown.args  # omitted required param

    huge = plan.probes[6]
    assert len(huge.args["due_date"]) == 100_000
    # the OTHER required param is omitted so validation must reject the call
    assert "color" not in huge.args


def test_huge_string_skipped_when_no_safe_base():
    # Single required string param: dropping it would just duplicate
    # missing_required, and sending it alone could plausibly succeed.
    tool = make_tool({"text": {"type": "string"}}, ["text"])
    plan = generate_probes(tool, thorough=True)
    assert "huge_string" not in templates(plan)
    assert "tolerate-probes skipped: no safe base" in plan.notes


def test_no_param_tool_gets_no_probes_unless_read_only():
    mutating = make_tool({}, [])
    plan = generate_probes(mutating, thorough=True)
    assert plan.probes == []
    assert "tolerate-probes skipped: no safe base" in plan.notes

    read_only = make_tool({}, [], read_only=True)
    plan = generate_probes(read_only, thorough=True)
    assert templates(plan) == ["unknown_field"]
    assert plan.notes == []


def test_default_mode_suppresses_irrelevant_no_safe_base_note():
    # ALL_SEVEN has >= 3 earlier probes, so under the default budget the
    # tolerate-probes would be truncated anyway - no note.
    tool = make_tool(
        {"text": {"type": "string"}, "n": {"type": "integer"}}, ["text", "n"]
    )
    # huge_string IS safe here (omit n) - craft the unsafe variant instead:
    single = make_tool({"text": {"type": "string"}}, ["text"])
    assert "tolerate-probes skipped: no safe base" in generate_probes(single, thorough=True).notes
    assert generate_probes(tool, thorough=True).notes == []
    default_plan = generate_probes(single)  # 3 earlier probes exist -> no note
    assert default_plan.notes == []
