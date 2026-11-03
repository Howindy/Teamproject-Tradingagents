# FR-01 / CR-01 State and Memory Contribution

Status: **personal draft / pending team review**
Implementation status: **design only; no application code changed**

## State ownership

| State | Owner | Lifetime | Authority |
|---|---|---|---|
| SEC statement text | Existing SEC vendor and its file cache | 24-hour cache, as today | Filed values as of the analysis date |
| `MetricResult` list | `DerivedMetricsCalculator` | One tool call; not stored separately | Authoritative derived values for that call |
| Verified-metrics block | `VerifiedBlockAppender` | Part of `fundamentals_report` for the run | Authoritative copy of the derived values in the report |
| Downstream brief block | Analyst model | Part of the analyst report for the run | Advisory; size and structure checked by code |
| Brief passed to a downstream agent | `report_brief_or_absent` | Exists only while a prompt is built | Derived view of the report; not stored |

No new `AgentState` field is introduced. The verified block and the brief block
travel inside the existing report strings.

## Write policy

- The calculator and formatter write nothing.
- The verified block is written once, by code, at the end of the fundamentals
  analyst node. No later node edits it.
- Briefs given to downstream agents are computed when each prompt is built and
  are never written back to state.
- Saved reports and full-state logs receive the full report text, including
  both blocks, through the existing writers. The trading memory log stores
  only the final decision (`store_decision`), so neither block reaches it.

## Retrieval and memory

The trading memory log stores decisions and later reflections, not analyst
reports, so neither feature changes what memory retrieves. A later run
recomputes derived metrics for its own analysis date. It does not reuse a
previous run's verified block, because filings and prices differ by date.

## Resume and checkpoints

Both blocks live in report fields that checkpoints already store. On resume
after the analyst stage, `report_brief_or_absent` extracts the same brief from
the same text, so downstream prompts are identical to an uninterrupted run.
Resuming with a different brief limit gives different prompts; keep the same
policy throughout a resumed run.

## Verification records

Offline fixture results record the policy limit, preserved data-gap statements,
verified-block equality, and report fields before and after prompt assembly.
No model endpoint key or live comparison harness is required.

## Privacy

Neither feature handles personal data. Records contain only public filing
data, model output, and usage counts. Endpoint records keep only scheme, host,
and path, following the team's redaction rules.

This fragment must be merged into the team's memory design.
