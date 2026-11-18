# The 18 checks

These identifiers match the implemented registry.

| ID | Check | Method | Category |
| --- | --- | --- | --- |
| T1 | Description quality | Static gate + LLM | Tool clarity |
| T2 | Parameter docs and format hints | Static | Tool clarity |
| T3 | Examples present | Static | Tool clarity |
| T4 | Error repairability | Probe + healing loop | Error quality |
| T5 | Safety annotations | Static | Safety |
| T6 | Name collisions and generic names | Static, cross-server | Tool clarity |
| T7 | Manifest size | Static estimate | Tool clarity |
| R1 | Resource readability | Probe | Resources |
| R2 | Resource context size | Probe | Resources |
| R3 | MIME declaration and content | Static + probe | Resources |
| R4 | URI template usability | Static + probe | Resources |
| R5 | Resource subscriptions / list changes | Static | Spec extras |
| P1 | Prompts defined | Static | Spec extras |
| P2 | Prompt argument documentation | Static | Protocol hygiene |
| P3 | Prompt rendering | Probe with filler arguments | Protocol hygiene |
| S1 | Capability honesty | Initialization + list outcomes | Protocol hygiene |
| S2 | Server instructions | Static | Spec extras |
| S3 | Response time and hangs | Probe timings | Error quality |

A check can produce findings for several tools or resources. Eighteen check types do not
mean eighteen requests or eighteen report rows.

Read the [specification](../mcpdoctor-check-spec.md) for scoring details and
[probe safety](probe-safety.md) before auditing your own tools.
