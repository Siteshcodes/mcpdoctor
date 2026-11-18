---
template: home.html
title: MCPDoctor — Make your MCP server easier to use
description: An open-source CLI for auditing MCP server usability, understanding errors, and testing self-healing tool calls.
hide:
  - toc
  - feedback
---

<section class="home-hero" aria-labelledby="hero-title">
  <div class="hero-copy">
    <div class="eyebrow"><span class="status-dot"></span> OPEN SOURCE · MCP DEVELOPER TOOLS</div>
    <h1 id="hero-title">Good tools.<br>Better <em>AI interactions.</em></h1>
    <p class="hero-lead">Find the friction between your MCP server and the agents using it. Audit usability, understand failures, and make the next call better.</p>
    <div class="hero-actions"><a class="button button-primary" href="getting-started/installation/">Start your first audit <span aria-hidden="true">↗</span></a><a class="button button-secondary" href="https://github.com/Siteshcodes/mcp-doctor">View on GitHub <span aria-hidden="true">↗</span></a></div>
    <div class="install-line"><code id="quick-command">uv run mcpdoctor doctor fixtures/otherserver.py</code><button class="copy-button" type="button" data-copy="quick-command" aria-label="Copy example audit command">Copy</button></div>
    <p class="hero-note">Python 3.12 · Runs locally · Start without an API key</p>
  </div>
  <div class="report-window">
    <div class="window-head"><span class="window-dots" aria-hidden="true"><i></i><i></i><i></i></span><span>mcpdoctor / sample report</span><span class="window-label">STDIO</span></div>
    <div class="report-body">
      <div class="terminal-command"><span>$</span> mcpdoctor doctor otherserver.py</div>
      <div class="report-grade"><div><span class="report-overline">USABILITY ASSESSMENT</span><strong>Ready to improve.</strong><span class="report-server">otherserver · 2 tools · 1 prompt</span></div><div class="grade-badge">B<span>87 / 100</span></div></div>
      <div class="score-row"><span>Error quality</span><div class="meter"><i style="width:100%"></i></div><b>100</b></div>
      <div class="score-row"><span>Tool clarity</span><div class="meter"><i style="width:88%"></i></div><b>88</b></div>
      <div class="score-row"><span>Safety</span><div class="meter"><i class="amber" style="width:50%"></i></div><b>50</b></div>
      <div class="sample-finding"><span class="finding-tag">T1</span><p>Explain <strong>when</strong> to use this tool,<br>not only what it does.</p></div>
      <div class="report-caption"><span class="status-dot"></span> Historical fixture result <a href="reports/otherserver/">Read full report ↗</a></div>
    </div>
  </div>
</section>

<div class="facts-strip" aria-label="Project capabilities">
  <div><strong>18</strong><span>usability checks</span></div><div><strong>6</strong><span>weighted categories</span></div><div><strong>2</strong><span>repair attempts</span></div><div><strong>MIT</strong><span>open-source license</span></div>
</div>

<section class="workflow-section" aria-labelledby="workflow-title">
  <div class="section-heading"><div><span class="eyebrow">FROM SERVER TO SIGNAL</span><h2 id="workflow-title">An audit you can act on.</h2></div><p>Go from a working connection to a clear list of improvements. Keep the details in your terminal or export them as Markdown.</p></div>
  <div class="steps-grid">
    <article><span class="step-number">01 / CONNECT</span><h3>Bring your server.</h3><p>Point the CLI at a Python script or a launch command. Discover tools, resources, templates, and prompts over stdio.</p><code>mcpdoctor doctor server.py</code></article>
    <article><span class="step-number">02 / INSPECT</span><h3>Find the rough edges.</h3><p>Combine metadata checks, bounded invalid-input probes, and optional LLM judgments to assess real usability gaps.</p><a href="checks/overview/">Explore all 18 checks <span aria-hidden="true">↗</span></a></article>
    <article><span class="step-number">03 / IMPROVE</span><h3>Fix what matters.</h3><p>Read the grade with its qualifications, prioritize suggested fixes, and rerun the audit after improving your server.</p><a href="usage/reports/">Understand the report <span aria-hidden="true">↗</span></a></article>
  </div>
</section>

<section class="heal-section" aria-labelledby="heal-title">
  <div><span class="eyebrow">ONE ENGINE. TWO USES.</span><h2 id="heal-title">An error can be<br>a way forward.</h2><p>The chatbot proposes corrected arguments after a failed tool call. The linter uses that same healing engine to assess whether your errors help an agent recover.</p><a class="text-link" href="usage/chat/">Try self-healing chat <span aria-hidden="true">↗</span></a><p class="small-note">Requires a Groq key. Retries execute real calls in chat.</p></div>
  <div class="heal-example" aria-label="Illustrative self-healing example"><div class="example-label">ILLUSTRATIVE REPAIR FLOW</div><div class="repair-step"><span class="repair-symbol fail-symbol">!</span><div><b>Call fails</b><code>date: "July 5th"</code></div></div><div class="repair-error">“date must be YYYY-MM-DD”</div><div class="repair-step"><span class="repair-symbol pass-symbol">↳</span><div><b>Propose corrected arguments</b><p>Use the schema and error to choose an ISO date, then retry.</p></div></div><div class="repair-footer">Up to two attempts. Recovery is not guaranteed.</div></div>
</section>

<section class="builder-section" aria-labelledby="builder-title">
  <div class="section-heading"><div><span class="eyebrow">YOUR NEXT COMMAND</span><h2 id="builder-title">Make it your own.</h2></div><p>Build a command, copy it, and run it in your local checkout. Your server specification stays in this browser.</p></div>
  <form id="command-builder">
    <div class="builder-fields"><label>What would you like to do?<select id="command-mode"><option value="doctor">Audit a server</option><option value="chat">Chat with a server</option></select></label><label>Terminal<select id="command-shell"><option value="powershell">Windows PowerShell</option><option value="bash">macOS / Linux shell</option></select></label><label class="server-field">Server path or launch command<input id="command-target" type="text" value="fixtures/otherserver.py" autocomplete="off" spellcheck="false" maxlength="2000" required></label></div>
    <div id="audit-options" class="builder-options"><label><input id="command-thorough" type="checkbox"> All applicable probes</label><label><input id="command-ascii" type="checkbox" checked> Plain-text report</label></div>
    <div class="command-output"><code id="generated-command">uv run mcpdoctor doctor 'fixtures/otherserver.py' --ascii</code><button type="button" class="copy-button" data-copy="generated-command">Copy command</button></div>
    <p id="builder-note" class="small-note">Run on trusted development servers and disposable data. Active probes execute requests.</p>
    <p id="copy-status" class="copy-status" role="status" aria-live="polite"></p>
  </form>
  <noscript><p>Enable JavaScript for the command builder, or use the examples in the <a href="usage/cli/">CLI reference</a>.</p></noscript>
</section>

<section class="docs-section" aria-labelledby="docs-title">
  <div><span class="eyebrow">THE FIELD GUIDE</span><h2 id="docs-title">Everything you need<br>to get going.</h2><p>Practical instructions, clear boundaries,<br>and the details behind every score.</p></div>
  <div class="guide-links"><a href="getting-started/installation/"><span><b>Installation & setup</b><small>Python, uv, and optional model configuration</small></span><span aria-hidden="true">↗</span></a><a href="usage/cli/"><span><b>CLI reference</b><small>Commands, options, and launch specifications</small></span><span aria-hidden="true">↗</span></a><a href="checks/probe-safety/"><span><b>Probe safety</b><small>Know what executes and where the limits are</small></span><span aria-hidden="true">↗</span></a><a href="contributing/deployment/"><span><b>Development & deployment</b><small>Contribute, preview, and publish the docs</small></span><span aria-hidden="true">↗</span></a></div>
</section>

<div class="home-closing"><p>Make the interface between tools and agents a little better.</p><a href="https://github.com/Siteshcodes/mcp-doctor">Explore the source <span aria-hidden="true">↗</span></a></div>
