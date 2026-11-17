# Devpost Submission Package - mcpdoctor

Use the content below to fill out your Devpost submission form fields.

---

## 1. Project Story (Copy & Paste into "About the project")

## Inspiration

We kept watching AI agents fail against Model Context Protocol (MCP) servers for the exact same preventable reasons:
- A tool taking `date: string` with zero indication of whether it expects `2026-07-06`, `"tomorrow"`, or `"July 5th"`.
- A cryptic HTTP `400 Bad Request` response that gave the LLM no diagnostic context on how to fix its call.
- Dangerous operations like `delete_database` exposed without setting the MCP `destructiveHint` safety flag.

Instead of guessing what makes an MCP server good, we interviewed the model about what actually frustrates it during tool execution. We translated those pain points into 18 automated checks across 6 categories, and built the solution directly into the codebase: an AI-usability linter paired with a self-healing interactive chat runtime.

---

## What it does

`mcpdoctor` evaluates MCP servers on one fundamental question: **"Could an AI model use this server correctly on the first try, and self-heal on the second?"**

1. **18 Usability & Safety Checks**: Evaluates Tool Clarity, Error Quality, Safety Annotations, Resource Structure, Protocol Hygiene, and Spec Extras.
2. **Empirical & Dynamic Scoring**: Calculates an overall score from \(0\) to \(100\) and assigns a letter grade (A+ through F). Category weights are dynamically redistributed if a server does not expose certain primitives (such as resources or prompts):
   $$S_{\text{overall}} = \frac{\sum_{i \in \text{Active}} W_i \cdot S_i}{\sum_{i \in \text{Active}} W_i}$$
3. **Prioritized Actionable Fixes**: Lists recommended fixes sorted by the exact number of points recovered (e.g., `+15 pts` for setting `destructiveHint: true`).
4. **Self-Healing Interactive Chat**: Includes a chat REPL where broken tool call errors are handed to the LLM alongside the schema, auto-corrected live, and transparently retried with a `[self-healed]` indicator.

---

## How we built it

`mcpdoctor` is written in Python 3.12 using [`uv`](https://docs.astral.sh/uv/), the official `mcp` SDK, Groq (`llama-3.3-70b-versatile`), and `typer` + `rich` for the terminal UI.

The architecture separates inspection into three distinct engines based on trust levels:
- **Static Inspector** (`checks_static.py`): Non-executing inspector that reads schema definitions, annotations, and protocol declarations.
- **Active Safe Probe Engine** (`checks_probe.py`): Sweeps tools using bad-input templates with strict safety barriers (destructive tools are never probed without `--unsafe`).
- **LLM Usability Judge** (`checks_llm.py`): Uses Groq Llama 3.3-70B at temperature 0 to grade description clarity (Check T1) and error repairability.

### The Dual-Use Self-Healing Loop
The self-healing core (`heal.py`) is used **twice as literally the same code**:
- **At Chat Runtime**: Automatically catches tool errors, prompts the LLM for corrected arguments, and retries the call.
- **At Lint Time (Check T4)**: Serves as the empirical benchmark for error quality. An unhelpful error that cannot be self-healed scores \(0/2\), while a descriptive error that repairs in 1 retry scores \(2/2\). Empirical testing beats opinion!

---

## Challenges we ran into

1. **Pydantic's Schema Traps**: Pydantic automatically injects a `title` attribute into every parameter schema. Our parameter documentation check initially mistook titles for documentation until we explicitly filtered them out.
2. **Multi-Layer Validation Boundaries**: FastMCP validates types before tool execution, and Groq validates tool call arguments server-side before emitting calls. We discovered that the most interesting failures occur at **declared-but-unenforced constraints** (e.g., `date: string` with `format: date` that nothing checks until runtime).
3. **Probe Execution Safety**: Probes carrying hard schema violations could accidentally succeed on poorly validated mutating tools. We enforced a strict local validation gate so lint probes never mutate live server data.
4. **Keyless Graceful Degradation**: Ensuring `mcpdoctor` works out of the box without requiring an API key while remaining honest about reporting floor scores.

---

## Accomplishments that we're proud of

- **Empirical Usability Measurement**: Testing error quality by attempting actual AI self-healing retries rather than relying on static heuristic rules.
- **Zero-Mutation Safety Guarantees**: Building an active probing engine that safely audits arbitrary MCP servers without risk of data loss.
- **118 Passing Unit & Integration Tests**: Complete test coverage across static checks, probe sweeps, REPL commands, and live FastMCP server instances.

---

## What we learned

AI usability in protocol design is fundamentally different from human API design. Humans can read external documentation or infer intent from context; LLMs rely strictly on parameter descriptions, explicit schema formats, clear error messages, and safety annotations. Designing for AI usability requires treating tool descriptions as prompt engineering targets and error messages as diagnostic repair instructions.

---

## What's next for mcpdoctor

- **GitHub Action / CI Integration**: Automatically fail PRs when a server's usability score drops below a configured threshold.
- **Multi-Model Judge Support**: Add a `--model` flag to compare usability grades across Claude 3.5 Sonnet, GPT-4o, and Llama 3.3.
- **Resource Summarization Middleware**: Middleware that automatically condenses oversized MCP resource payloads before context limits are exceeded.

---

## 2. Built With (Copy & Paste Tags)

Copy and paste these tags into the **"Built with"** input field:

`python`, `mcp`, `model-context-protocol`, `groq`, `llama-3.3-70b`, `uv`, `typer`, `rich`, `pydantic`, `pytest`, `asyncio`, `ai-usability`, `linter`, `self-healing`, `cli`, `developer-tools`

---

## 3. "Try it out" Links

- **GitHub Repository**: `https://github.com/Siteshcodes/mcpdoctor`
