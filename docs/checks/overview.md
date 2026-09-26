# Check overview

mcpdoctor evaluates six weighted categories. Categories with nothing to measure are
marked not applicable and their weight is redistributed instead of penalizing a server
for not exposing optional primitives.

| Category | Weight | Focus |
| --- | ---: | --- |
| Error Quality | 30% | Helpful errors, repairability, and response time |
| Tool Clarity | 25% | Descriptions, parameters, examples, names, and manifest size |
| Safety | 15% | `readOnlyHint`, `destructiveHint`, and mismatch detection |
| Resources | 15% | Readability, size, MIME types, and URI templates |
| Protocol Hygiene | 10% | Handshake, capabilities, prompts, and prompt arguments |
| Spec Extras | 5% | Subscriptions, prompts, and server `instructions` |

The full rubric, detection methods, and scoring rules are in the [check specification](../mcpdoctor-check-spec.md).
