# mcpdoctor

**mcpdoctor** grades an MCP server on the question that matters to an AI agent:

> Could a model use this correctly on the first try, and recover on the second?

It combines a deterministic protocol inspector, safe invalid-input probes, and optional
LLM judges. The same self-healing loop powers both the `doctor` report and the interactive
chatbot.

## Choose a path

- **New to the project?** Follow [Installation](getting-started/installation.md), then run
  your [first lint](getting-started/first-lint.md).
- **Using the CLI?** See the complete [CLI reference](usage/cli.md).
- **Debugging tool calls?** Read about [self-healing chat](usage/chat.md).
- **Building an MCP server?** Start with the [check overview](checks/overview.md) and
  [probe-safety rules](checks/probe-safety.md).
- **Maintaining the project?** See the [development guide](contributing/development.md).

## What gets measured

The linter checks tool clarity, error repairability, safety annotations, resources, prompt
behavior, protocol honesty, and server instructions. Results include a letter grade, the
highest-value fixes, and optional Markdown output suitable for a pull request.

## Project links

- [GitHub repository](https://github.com/Siteshcodes/mcp-doctor)
- [Full check specification](mcpdoctor-check-spec.md)
- [Example reports](usage/reports.md)
