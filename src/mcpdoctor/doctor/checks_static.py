"""The 10 Phase-1 static checks: S1, S2, T2, T3, T5, T6, T7, P1, P2, R5.

Pure manifest inspection - no probe calls, no LLM. Each function implements
one spec section; severities follow the default mapping 2→info, 1→warn,
0→fail, with two spec-driven exceptions:
- T7 is advisory (spec §3: "info/warn only"), so 0 → warn.
- Spec-extras checks (S2, P1, R5) cap at warn - most servers score 0 there
  by design (§8 "free points nobody claims"), and that's absence, not breakage.

n/a convention (spec §11): a check that doesn't apply emits no results.
"""

import json
import re

from mcp import ClientSession

from mcpdoctor.doctor.manifest import Manifest, ServerManifest
from mcpdoctor.doctor.results import CheckResult
from mcpdoctor.doctor.vocab import DESTRUCTIVE_WORDS, name_tokens

# Spec T6 - names that say nothing about what the tool does.
GENERIC_NAMES = {"run", "do", "execute", "process", "handle", "manage", "data"}

# Spec T2 - string params with these name tokens need a format hint.
FORMAT_HINT_TOKENS = {"date", "time", "id", "url", "email", "query", "path"}

_ANNOTATION_HINTS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")

_EXAMPLE_RE = re.compile(
    r"e\.g\.|for example|example|'[^']{1,40}'|\"[^\"]{1,40}\"", re.IGNORECASE
)


def _severity(score: int) -> str:
    return {2: "info", 1: "warn", 0: "fail"}[score]


def _extras_severity(score: int) -> str:
    return "warn" if score == 0 else "info"


def _levenshtein(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 3  # callers only care about distance <= 2
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _has_example(text: str | None) -> bool:
    return bool(text and _EXAMPLE_RE.search(text))


# --- Tool Clarity -----------------------------------------------------------


async def t2_param_docs(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """T2 - every param needs a description; format-hinted string params
    (date, id, url, ...) additionally need format/pattern/enum or an example."""
    results = []
    for server in manifest.servers:
        for tool in server.tools:
            props: dict = (tool.inputSchema or {}).get("properties", {})
            undocumented = [
                p for p, s in props.items() if not str(s.get("description", "")).strip()
            ]
            ambiguous = [
                p
                for p, s in props.items()
                if s.get("type") == "string"
                and (name_tokens(p) & FORMAT_HINT_TOKENS)
                and not any(k in s for k in ("format", "pattern", "enum"))
                and not _has_example(s.get("description"))
            ]

            if not props:
                score, message = 2, "no parameters to document"
            elif not undocumented and not ambiguous:
                score, message = 2, "all params documented, no ambiguous strings"
            else:
                documented_frac = 1 - len(undocumented) / len(props)
                score = 1 if documented_frac >= 0.5 else 0
                parts = []
                if undocumented:
                    parts.append(f"params missing descriptions: {', '.join(undocumented)}")
                if ambiguous:
                    parts.append(
                        f"ambiguous string params without format/pattern/enum/example: "
                        f"{', '.join(ambiguous)}"
                    )
                message = "; ".join(parts)

            fix_hint = None
            if ambiguous:
                fix_hint = (
                    f"{ambiguous[0]}: add description + format hint "
                    "(e.g. 'ISO date, YYYY-MM-DD' for dates, a pattern or enum otherwise)"
                )
            elif undocumented:
                fix_hint = f"{undocumented[0]}: add a description explaining what to pass"

            results.append(
                CheckResult(
                    id="T2",
                    server=server.name,
                    name="Parameter docs & format hints",
                    category="tool_clarity",
                    target=tool.name,
                    score=score,
                    max_score=2,
                    severity=_severity(score),
                    message=message,
                    fix_hint=fix_hint,
                )
            )
    return results


async def t3_examples(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """T3 - one example call is worth 500 tokens of prose."""
    results = []
    for server in manifest.servers:
        for tool in server.tools:
            schema = tool.inputSchema or {}
            props: dict = schema.get("properties", {})
            tool_level = "examples" in schema or _has_example(tool.description)
            param_level = any(
                "examples" in s or _has_example(s.get("description"))
                for s in props.values()
            )

            if tool_level:
                score, message = 2, "example present at tool level"
            elif param_level:
                score, message = 1, "param-level hints only, no tool-level example"
            else:
                score, message = 0, "no examples anywhere"

            results.append(
                CheckResult(
                    id="T3",
                    server=server.name,
                    name="Examples present",
                    category="tool_clarity",
                    target=tool.name,
                    score=score,
                    max_score=2,
                    severity=_severity(score),
                    message=message,
                    fix_hint=None
                    if score == 2
                    else "add an example to the tool description - one sample call with realistic values",
                )
            )
    return results


async def t6_names(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """T6 - exact cross-server collisions fail; near-dupes and generic names warn."""
    owners: dict[str, list[str]] = {}
    for server in manifest.servers:
        for tool in server.tools:
            owners.setdefault(tool.name, []).append(server.name)

    results = []
    for server in manifest.servers:
        if not server.tools:
            continue
        names = [t.name for t in server.tools]

        collisions = [
            (n, [o for o in owners[n] if o != server.name])
            for n in names
            if len(owners[n]) > 1
        ]
        generic = [n for n in names if n in GENERIC_NAMES]
        near_dupes = [
            (a, b)
            for i, a in enumerate(names)
            for b in names[i + 1 :]
            if a != b and _levenshtein(a, b) <= 2
        ]

        if collisions:
            score = 0
        elif generic or near_dupes:
            score = 1
        else:
            score = 2

        parts = []
        if collisions:
            parts.append(
                "cross-server collisions: "
                + "; ".join(f"'{n}' also on {', '.join(others)}" for n, others in collisions)
            )
        if generic:
            parts.append(f"generic names: {', '.join(generic)}")
        if near_dupes:
            parts.append(
                "near-duplicates: " + ", ".join(f"{a}/{b}" for a, b in near_dupes)
            )
        message = "; ".join(parts) or "tool names are unique and descriptive"

        fix_hint = None
        if score < 2:
            worst = collisions[0][0] if collisions else (generic + [a for a, _ in near_dupes])[0]
            fix_hint = f"rename '{worst}' to something unique and action-specific, e.g. '{server.name}_{worst}'"

        results.append(
            CheckResult(
                id="T6",
                server=server.name,
                name="Name collisions & generic names",
                category="tool_clarity",
                target=server.name,
                score=score,
                max_score=2,
                severity=_severity(score),
                message=message,
                fix_hint=fix_hint,
            )
        )
    return results


async def t7_manifest_bloat(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """T7 - every schema token is context tax. Advisory only (spec §3)."""
    results = []
    for server in manifest.servers:
        if not server.tools:
            continue
        text = json.dumps(
            [
                {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
                for t in server.tools
            ]
        )
        tokens = len(text) // 4
        n = len(server.tools)

        if n <= 20 and tokens <= 4_000:
            score = 2
        elif n <= 40 and tokens <= 10_000:
            score = 1
        else:
            score = 0

        results.append(
            CheckResult(
                id="T7",
                server=server.name,
                name="Manifest bloat (token cost)",
                category="tool_clarity",
                target=server.name,
                score=score,
                max_score=2,
                severity="info" if score == 2 else "warn",  # advisory, never fail
                message=f"{n} tools, ~{tokens} manifest tokens",
                fix_hint=None
                if score == 2
                else "split the server or trim schemas - 40+ tools degrade selection accuracy",
            )
        )
    return results


# --- Safety -----------------------------------------------------------------


def _has_any_annotation(tool) -> bool:
    a = tool.annotations
    return a is not None and any(getattr(a, f) is not None for f in _ANNOTATION_HINTS)


async def t5_safety_annotations(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """T5 - destructive-name/annotation mismatch hard-fails the category to 0
    (spec §5), so when any mismatch exists only the score-0 mismatch results
    are emitted and coverage results are suppressed."""
    mismatches: list[tuple[ServerManifest, str]] = []
    for server in manifest.servers:
        for tool in server.tools:
            destructive_name = bool(name_tokens(tool.name) & DESTRUCTIVE_WORDS)
            hinted = tool.annotations is not None and tool.annotations.destructiveHint is True
            if destructive_name and not hinted:
                mismatches.append((server, tool.name))

    if mismatches:
        return [
            CheckResult(
                id="T5",
                server=server.name,
                name="Safety annotations",
                category="safety",
                target=name,
                score=0,
                max_score=2,
                severity="fail",
                message="destructive name but destructiveHint unset - "
                "indistinguishable from a read-only tool by metadata",
                fix_hint=f"set destructiveHint: true on {name}",
            )
            for server, name in mismatches
        ]

    results = []
    for server in manifest.servers:
        if not server.tools:
            continue
        coverage = sum(_has_any_annotation(t) for t in server.tools) / len(server.tools)
        score = 2 if coverage >= 0.8 else 1 if coverage >= 0.3 else 0
        results.append(
            CheckResult(
                id="T5",
                server=server.name,
                name="Safety annotations",
                category="safety",
                target=server.name,
                score=score,
                max_score=2,
                severity=_severity(score),
                message=f"{coverage:.0%} of tools carry safety annotations",
                fix_hint=None
                if score == 2
                else "annotate tools with readOnlyHint / destructiveHint / idempotentHint",
            )
        )
    return results


# --- Protocol Hygiene -------------------------------------------------------


async def s1_capability_honesty(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """S1 - declared capabilities must match reality (spec §7)."""
    results = []
    for server in manifest.servers:
        caps = server.capabilities
        warns: list[str] = []
        fails: list[str] = []

        for kind in ("tools", "resources", "prompts"):
            declared = caps is not None and getattr(caps, kind) is not None
            outcome = server.list_outcomes.get(kind)
            if outcome is None:
                continue
            exposed = bool(getattr(server, kind))
            if kind == "resources":
                exposed = exposed or bool(server.resource_templates)

            if declared and outcome.status in ("error", "unsupported"):
                fails.append(f"{kind} capability declared but {kind}/list {outcome.status}"
                             + (f": {outcome.error}" if outcome.error else ""))
            elif declared and outcome.status == "empty" and not exposed:
                warns.append(
                    f"{kind} capability declared but nothing registered (framework default)"
                )
            elif not declared and exposed:
                fails.append(f"server exposes {kind} without declaring the capability")

        # Templates ride on the resources capability; an erroring templates/list
        # under a declared resources capability is dishonesty too. "unsupported"
        # is tolerated - many real servers skip templates entirely.
        templates_outcome = server.list_outcomes.get("resource_templates")
        if (
            caps is not None
            and caps.resources is not None
            and templates_outcome is not None
            and templates_outcome.status == "error"
        ):
            fails.append("resources capability declared but resources/templates/list errors")

        score = 0 if fails else 1 if warns else 2
        message = "; ".join(fails + warns) or "handshake clean, declared capabilities match reality"
        results.append(
            CheckResult(
                id="S1",
                server=server.name,
                name="Handshake & capability honesty",
                category="protocol_hygiene",
                target=server.name,
                score=score,
                max_score=2,
                severity=_severity(score),
                message=message,
                fix_hint=None
                if score == 2
                else "declare exactly the capabilities the server implements - register the primitive or drop the claim",
            )
        )
    return results


async def p2_prompt_arg_docs(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """P2 - every prompt argument needs a description + explicit required flag.
    n/a (no results) when a server has no prompts: P1 already covers existence."""
    results = []
    for server in manifest.servers:
        for prompt in server.prompts:
            args = prompt.arguments or []
            documented = [
                a for a in args if (a.description or "").strip() and a.required is not None
            ]
            if not args:
                score, message = 2, "no arguments to document"
            elif len(documented) == len(args):
                score, message = 2, "all arguments documented"
            elif documented:
                score = 1
                missing = [a.name for a in args if a not in documented]
                message = f"partially documented; missing description/required on: {', '.join(missing)}"
            else:
                score, message = 0, "no argument has a description + explicit required flag"

            results.append(
                CheckResult(
                    id="P2",
                    server=server.name,
                    name="Prompt argument docs",
                    category="protocol_hygiene",
                    target=prompt.name,
                    score=score,
                    max_score=2,
                    severity=_severity(score),
                    message=message,
                    fix_hint=None
                    if score == 2
                    else "give every prompt argument a description and an explicit required flag",
                )
            )
    return results


# --- Spec Extras ------------------------------------------------------------


async def s2_instructions(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """S2 - the most underused field in the spec: server-level guidance for the LLM."""
    results = []
    for server in manifest.servers:
        text = (server.instructions or "").strip()
        if not text:
            score, message = 0, "no instructions field in initialize result"
        elif len(text.split()) > 20:
            score, message = 2, "instructions present and substantial"
        else:
            score, message = 1, f"instructions present but thin ({len(text.split())} words)"

        results.append(
            CheckResult(
                id="S2",
                server=server.name,
                name="instructions field used",
                category="spec_extras",
                target=server.name,
                score=score,
                max_score=2,
                severity=_extras_severity(score),
                message=message,
                fix_hint=None
                if score == 2
                else 'pass instructions="..." at server construction - tell the LLM when and how to use this server',
            )
        )
    return results


async def p1_prompts_exist(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """P1 - does the server define prompts at all?"""
    results = []
    for server in manifest.servers:
        if not server.prompts:
            score, message = 0, "no prompts defined"
        elif all((p.description or "").strip() for p in server.prompts):
            score, message = 2, f"{len(server.prompts)} prompt(s), all documented"
        else:
            score, message = 1, f"{len(server.prompts)} prompt(s), some undocumented"

        results.append(
            CheckResult(
                id="P1",
                server=server.name,
                name="Prompts defined at all",
                category="spec_extras",
                target=server.name,
                score=score,
                max_score=2,
                severity=_extras_severity(score),
                message=message,
                fix_hint=None
                if score == 2
                else "define at least one documented prompt - a pre-baked workflow clients can surface",
            )
        )
    return results


async def r5_subscriptions(
    sessions: dict[str, ClientSession], manifest: Manifest
) -> list[CheckResult]:
    """R5 - resources.subscribe / resources.listChanged declared?"""
    results = []
    for server in manifest.servers:
        res_caps = server.capabilities.resources if server.capabilities else None
        subscribe = bool(res_caps and res_caps.subscribe)
        list_changed = bool(res_caps and res_caps.listChanged)
        score = int(subscribe) + int(list_changed)
        supported = [
            n for n, on in (("subscribe", subscribe), ("listChanged", list_changed)) if on
        ]
        results.append(
            CheckResult(
                id="R5",
                server=server.name,
                name="Subscriptions / listChanged",
                category="spec_extras",
                target=server.name,
                score=score,
                max_score=2,
                severity=_extras_severity(score),
                message=f"resource subscriptions: {', '.join(supported) or 'none declared'}",
                fix_hint=None
                if score == 2
                else "support resources.subscribe and resources.listChanged so clients can track changes",
            )
        )
    return results
