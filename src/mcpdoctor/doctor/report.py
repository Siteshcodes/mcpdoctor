"""Report renderers (spec §11): an ASCII fallback (render_text), a rich
terminal card (render_rich), and a markdown export (render_markdown). All
three share the same helpers — server-qualified targets, the degraded-run
banner, per-category worst finding, and "Top fixes by points recovered".
"""

from dataclasses import replace

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mcpdoctor.doctor.manifest import Manifest
from mcpdoctor.doctor.results import (
    CATEGORY_WEIGHTS,
    CheckResult,
    category_scores,
    letter_grade,
    overall_score,
)

CATEGORY_LABELS = {
    "error_quality": "Error Quality",
    "tool_clarity": "Tool Clarity",
    "safety": "Safety",
    "resources": "Resources",
    "protocol_hygiene": "Protocol Hygiene",
    "spec_extras": "Spec Extras",
}

# Categories with a specced-but-unimplemented check are labeled "partial" so
# scores aren't misread. Empty since Phase 3 (T4 and T1 landed) — grades are
# now real and comparable. The mechanism stays for any future phased check.
PENDING_CHECKS: dict[str, tuple[str, ...]] = {}

_SEVERITY_ORDER = {"fail": 0, "warn": 1, "info": 2}


def display_target(result: CheckResult, multi: bool) -> str:
    """Qualify a finding's target as 'server:target' when more than one server
    is connected (ruling 2); leave it bare for a single-server run."""
    if multi and result.server and result.target != result.server:
        return f"{result.server}:{result.target}"
    return result.target


def display_hint(fix_hint: str | None) -> str | None:
    """Strip the internal '| suggested: ...' convention (Phase 3) off a hint for
    display — the suggested rewrite belongs in --fix, not in every finding line."""
    if fix_hint and " | suggested: " in fix_hint:
        return fix_hint.split(" | suggested: ", 1)[0]
    return fix_hint


def _ordered(results: list[CheckResult]) -> list[CheckResult]:
    return sorted(
        results,
        key=lambda r: (
            list(CATEGORY_LABELS).index(r.category),
            _SEVERITY_ORDER[r.severity],
            r.id,
            r.server or "",
            r.target,
        ),
    )


def worst_finding(results: list[CheckResult], category: str) -> CheckResult | None:
    """Lowest-scoring, most-severe finding in a category — the one line the
    per-category summary should surface."""
    in_cat = [r for r in results if r.category == category]
    if not in_cat:
        return None
    return min(in_cat, key=lambda r: (r.score, _SEVERITY_ORDER[r.severity]))


def top_fixes(
    results: list[CheckResult], limit: int = 3
) -> list[tuple[CheckResult, float]]:
    """Findings ranked by points recovered — the overall-score delta if that
    single finding scored a 2 instead of what it got. Answers 'what should I
    fix first?' in the currency the grade is actually in."""
    base = overall_score(results)
    scored: list[tuple[CheckResult, float]] = []
    for r in results:
        if r.score >= 2 or not r.fix_hint:
            continue
        bumped = [replace(x, score=2) if x is r else x for x in results]
        delta = overall_score(bumped) - base
        if delta > 0:
            scored.append((r, delta))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]


def degraded_banner_lines(degraded: list[str] | None) -> list[str]:
    return list(degraded) if degraded else []


def _gain_text(points: float) -> str:
    """Keep fractional gains visible, including gains below display precision."""
    if 0 < points < 0.01:
        return "<0.01"
    return f"+{points:.2f}".rstrip("0").rstrip(".")


def _header_lines(manifest: Manifest, results: list[CheckResult]) -> list[str]:
    lines = []
    for server in manifest.servers:
        lines.append(
            f"mcpdoctor - {server.server_info_name or server.name} "
            f"({len(server.tools)} tools | {len(server.resources)} resources | "
            f"{len(server.prompts)} prompts)"
        )
    overall = overall_score(results)
    lines.append(f"Overall: {letter_grade(overall)} ({overall:.0f}/100)")
    return lines


def render_text(
    manifest: Manifest,
    results: list[CheckResult],
    notes: list[str] | None = None,
    degraded: list[str] | None = None,
) -> str:
    multi = len(manifest.servers) > 1
    lines: list[str] = []

    for banner in degraded_banner_lines(degraded):
        lines.append(f"!! {banner}")
    if degraded:
        lines.append("")

    lines.extend(_header_lines(manifest, results))
    lines.append("")

    per_category = category_scores(results)
    for category, label in CATEGORY_LABELS.items():
        pct = per_category[category]
        shown = "n/a" if pct is None else f"{pct:3.0f}%"
        line = f"  {label:<17} {shown:>4}  (weight {CATEGORY_WEIGHTS[category]})"
        if category in PENDING_CHECKS:
            line += f"  partial ({', '.join(PENDING_CHECKS[category])} pending)"
        lines.append(line)
    lines.append("")

    lines.append("Findings:")
    for r in _ordered(results):
        lines.append(
            f"  [{r.severity:<4}] {r.id} {display_target(r, multi)}: "
            f"{r.message} ({r.score}/{r.max_score})"
        )
        if r.fix_hint:
            lines.append(f"          fix: {display_hint(r.fix_hint)}")

    fixes = top_fixes(results)
    if fixes:
        lines.append("")
        lines.append("Top fixes (by points recovered):")
        for i, (r, delta) in enumerate(fixes, 1):
            lines.append(
                f"  {i}. {display_target(r, multi)} - {display_hint(r.fix_hint)} ({_gain_text(delta)})"
            )

    if notes:
        lines.append("")
        lines.append("Probe safety:")
        for note in notes:
            lines.append(f"  {note}")
    return "\n".join(lines)


# --- rich terminal card (spec §11) ------------------------------------------

_GRADE_STYLE = {"A": "bold green", "B": "green", "C": "yellow", "D": "red", "F": "bold red"}


def _bar(pct: float | None, width: int = 10) -> Text:
    if pct is None:
        return Text("n/a".ljust(width), style="dim")
    filled = round(pct / 100 * width)
    style = "green" if pct >= 75 else "yellow" if pct >= 45 else "red"
    return Text("#" * filled + "-" * (width - filled), style=style)


def _truncate(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_rich(
    manifest: Manifest,
    results: list[CheckResult],
    notes: list[str] | None = None,
    degraded: list[str] | None = None,
) -> RenderableType:
    """The §11 terminal card as a rich renderable (Group). CLI prints it to a
    live Console; tests render it through a recording Console."""
    multi = len(manifest.servers) > 1
    blocks: list[RenderableType] = []

    if degraded:
        blocks.append(
            Panel(
                Text("\n".join(degraded), style="bold red"),
                title="degraded run",
                border_style="red",
            )
        )

    header = Text()
    for server in manifest.servers:
        header.append(
            f"mcpdoctor — {server.server_info_name or server.name} "
            f"({len(server.tools)} tools · {len(server.resources)} resources · "
            f"{len(server.prompts)} prompts)\n",
            style="bold",
        )
    overall = overall_score(results)
    grade = letter_grade(overall)
    header.append("Overall: ")
    header.append(f"{grade} ({overall:.0f}/100)", style=_GRADE_STYLE[grade])
    blocks.append(header)

    per_category = category_scores(results)
    table = Table(show_edge=False, box=None, pad_edge=False, expand=False)
    table.add_column("Category", style="bold", width=17)
    table.add_column("", width=10)
    table.add_column("Score", justify="right", width=4)
    table.add_column("Worst finding")
    for category, label in CATEGORY_LABELS.items():
        pct = per_category[category]
        worst = worst_finding(results, category)
        worst_text = ""
        if worst is not None and worst.score < 2:
            worst_text = _truncate(f"{display_target(worst, multi)}: {worst.message}")
        table.add_row(
            label,
            _bar(pct),
            "n/a" if pct is None else f"{pct:.0f}%",
            worst_text,
        )
    blocks.append(table)

    fixes = top_fixes(results)
    if fixes:
        fix_text = Text("Top fixes (by points recovered):\n", style="bold")
        for i, (r, delta) in enumerate(fixes, 1):
            fix_text.append(
                f" {i}. {display_target(r, multi)} — {display_hint(r.fix_hint)} ",
                style="default",
            )
            fix_text.append(f"({_gain_text(delta)})\n", style="green")
        blocks.append(fix_text)

    if notes:
        note_text = Text("Probe safety:\n", style="bold")
        for note in notes:
            note_text.append(f"  {note}\n", style="dim")
        blocks.append(note_text)

    return Group(*blocks)


def render_rich(
    manifest: Manifest,
    results: list[CheckResult],
    notes: list[str] | None = None,
    degraded: list[str] | None = None,
    width: int = 100,
) -> str:
    """Rich card as plain text (for tests / non-tty capture)."""
    import io

    console = Console(record=True, width=width, file=io.StringIO())
    console.print(build_rich(manifest, results, notes, degraded))
    return console.export_text()


def print_report(
    manifest: Manifest,
    results: list[CheckResult],
    notes: list[str] | None = None,
    degraded: list[str] | None = None,
) -> None:
    """Print the rich card to the real terminal (color when supported)."""
    Console().print(build_rich(manifest, results, notes, degraded))


# --- markdown export (spec §11: same content, for README/CI) ----------------


def _bar_text(pct: float | None, width: int = 10) -> str:
    if pct is None:
        return "n/a"
    filled = round(pct / 100 * width)
    return "#" * filled + "-" * (width - filled)


def render_markdown(
    manifest: Manifest,
    results: list[CheckResult],
    notes: list[str] | None = None,
    degraded: list[str] | None = None,
) -> str:
    multi = len(manifest.servers) > 1
    names = ", ".join(s.server_info_name or s.name for s in manifest.servers)
    out: list[str] = [f"# mcpdoctor — {names}", ""]

    if degraded:
        for banner in degraded:
            out.append(f"> ⚠️ **{banner}**")
        out.append("")

    for server in manifest.servers:
        out.append(
            f"- **{server.server_info_name or server.name}** — "
            f"{len(server.tools)} tools · {len(server.resources)} resources · "
            f"{len(server.prompts)} prompts"
        )
    overall = overall_score(results)
    out += ["", f"**Overall: {letter_grade(overall)} ({overall:.0f}/100)**", ""]

    per_category = category_scores(results)
    out += ["| Category | Score | Bar | Worst finding |", "|---|---|---|---|"]
    for category, label in CATEGORY_LABELS.items():
        pct = per_category[category]
        worst = worst_finding(results, category)
        worst_text = ""
        if worst is not None and worst.score < 2:
            worst_text = f"{display_target(worst, multi)}: {worst.message}"
        shown = "n/a" if pct is None else f"{pct:.0f}%"
        out.append(f"| {label} | {shown} | `{_bar_text(pct)}` | {worst_text} |")
    out.append("")

    out.append("## Findings")
    for r in _ordered(results):
        out.append(
            f"- **[{r.severity}] {r.id} {display_target(r, multi)}** "
            f"({r.score}/{r.max_score}) — {r.message}"
        )
        if r.fix_hint:
            out.append(f"  - fix: {display_hint(r.fix_hint)}")
    out.append("")

    fixes = top_fixes(results)
    if fixes:
        out.append("## Top fixes (by points recovered)")
        for i, (r, delta) in enumerate(fixes, 1):
            out.append(
                f"{i}. **{display_target(r, multi)}** — {display_hint(r.fix_hint)} ({_gain_text(delta)})"
            )
        out.append("")

    if notes:
        out.append("## Probe safety")
        for note in notes:
            out.append(f"- {note}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


# --- --fix: ready-to-paste description rewrites (spec §10) -------------------

_SUGGESTED = " | suggested: "


def render_fixes(manifest: Manifest, results: list[CheckResult]) -> str:
    """For T1 failures carrying a judge suggestion (the '| suggested:' convention
    from Phase 3), print before/after description blocks grouped by server —
    ready to paste into the server source."""
    current: dict[tuple[str | None, str], str] = {}
    for server in manifest.servers:
        for tool in server.tools:
            current[(server.name, tool.name)] = tool.description or ""

    by_server: dict[str | None, list[tuple[str, str]]] = {}
    for r in results:
        if r.id != "T1" or r.score >= 2 or not r.fix_hint or _SUGGESTED not in r.fix_hint:
            continue
        suggestion = r.fix_hint.split(_SUGGESTED, 1)[1].strip()
        by_server.setdefault(r.server, []).append((r.target, suggestion))

    if not by_server:
        return "No T1 description suggestions available (needs OPENAI_API_KEY)."

    lines = ["Suggested description rewrites (T1) — paste into your server:"]
    for server, items in by_server.items():
        lines.append(f"\n# {server}")
        for tool, suggestion in items:
            lines.append(f"{tool}")
            lines.append(f'  - current:   "{current.get((server, tool), "")}"')
            lines.append(f'  + suggested: "{suggestion}"')
    return "\n".join(lines)
