# Devpost Media Guide & Video Demo Script - mcpdoctor

Use this guide to select your image gallery uploads and record a winning 90-second to 2-minute video demo for Devpost.

---

## Part 1: What to Upload to Project Media (Image Gallery)

Upload 3 to 5 clean, high-resolution screenshots/images to the Devpost **Image gallery**:

1. **Primary Project Thumbnail (3:2 Ratio)**:
   - **File**: [`docs/mcpdoctor_devpost_thumbnail.png`](file:///d:/3.Projectx/mcpdoctor/docs/mcpdoctor_devpost_thumbnail.png)
   - **Description**: Official high-resolution 3:2 banner image.

2. **Linter Terminal Output Card**:
   - **Screenshot**: Terminal running `uv run mcpdoctor doctor fixtures/badserver.py`
   - **Caption**: *mcpdoctor grading an MCP server with 18 checks across 6 categories, showing letter grades and prioritized fixes.*

3. **System Architecture Diagram**:
   - **Screenshot/Graphic**: The system architecture diagram showing CLI, Client, 3 Inspection Engines, and `heal.py`.
   - **Caption**: *Three-engine inspection architecture powered by a dual-use self-healing core.*

4. **Self-Healing Chat REPL**:
   - **Screenshot**: Terminal running `uv run mcpdoctor chat fixtures/otherserver.py` showing `[self-healed]` in action.
   - **Caption**: *Live interactive chat REPL automatically healing a broken tool call from 'July 5th' to '2026-07-05'.*

5. **Multi-Server & Markdown Export**:
   - **Screenshot**: Terminal showing multi-server linting (`serverA.py serverB.py`) and `--md` export.
   - **Caption**: *Multi-server auditing and markdown report export for CI pipelines.*

---

## Part 2: Video Demo Script (90 Seconds)

> **Format Tip**: Keep your video between 60 and 90 seconds. Record your terminal screen while reading the script below or overlaying background music with text captions.

---

### 🎬 Scene 1: The Problem (0:00 - 0:15)

**Visual**: Screen shows a split terminal or slide displaying an AI agent failing with a cryptic `400 Bad Request` or passing `"tomorrow"` to a parameter typed as `date: string`.

**Voiceover / Captions**:
> *"Model Context Protocol servers are exploding in popularity — but real-world servers fail AI agents all the time. Vague parameter types, cryptic 400 errors, and unflagged destructive tools frustrate models and break workflows. How do we fix this?"*

---

### 🎬 Scene 2: Introducing `mcpdoctor doctor` (0:15 - 0:45)

**Visual**: Open terminal and type:
```bash
uv run mcpdoctor doctor fixtures/badserver.py
```
*Pause to highlight the Rich terminal card rendering.*

**Voiceover / Captions**:
> *"Meet `mcpdoctor` — the AI-usability linter for MCP servers. In seconds, `mcpdoctor` runs 18 checks across six weighted categories, evaluating tool clarity, error quality, safety, resources, and protocol hygiene."*
>
> *"It assigns an overall letter grade, checks probe safety without mutating data, and ranks top fixes by exact points recovered so developers know what to fix first."*

---

### 🎬 Scene 3: The Magic of Self-Healing Chat (0:45 - 1:15)

**Visual**: Type in terminal:
```bash
uv run mcpdoctor chat fixtures/otherserver.py
```
Then prompt the REPL:
`Call fetch_metrics with the date set to "July 5th"`

Watch as the terminal shows:
```text
[mcpdoctor] Tool error: date must be YYYY-MM-DD, got 'July 5th'
[mcpdoctor] [self-healed] Retrying fetch_metrics(date='2026-07-05')...
```

**Voiceover / Captions**:
> *"Here’s the flagship feature: `mcpdoctor` ships with an interactive self-healing chat. When a tool call errors because of a human-style input like 'July 5th', our heal loop inspects the error and schema, auto-corrects the argument to ISO format, retries live, and keeps the conversation moving seamlessly!"*

---

### 🎬 Scene 4: Dual-Use Core Architecture (1:15 - 1:30)

**Visual**: Show a quick diagram or code snippet of `src/mcpdoctor/heal.py`.

**Voiceover / Captions**:
> *"What makes `mcpdoctor` special is that this self-healing engine is dual-use. At runtime, it repairs broken chat calls. At lint time, it empirically benchmarks whether a server's errors contain enough diagnostic info for an AI to repair itself. Empirical testing beats opinion!"*

---

### 🎬 Scene 5: Wrap-up & Call to Action (1:30 - 1:40)

**Visual**: Show project logo / GitHub link on screen: `https://github.com/Siteshcodes/mcpdoctor`

**Voiceover / Captions**:
> *"Audit your MCP servers today with `mcpdoctor` — available on GitHub with full UV support. Build better MCP servers for AI models!"*
