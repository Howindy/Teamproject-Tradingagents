# FR-01 / CR-01 Invariant Contribution

Status: **personal draft / pending team review**
Implementation status: **design only; no application code changed**

All items are zero-tolerance. A single violation fails the related invariant.

| ID | Invariant | Source requirement | Enforcement | Verification | Operational fallback | Status |
|---|---|---|---|---|---|---|
| DM-INV-01 | No metric uses a period derived by subtracting filed periods. | `FR-01` | `DerivedMetricsCalculator` has no subtraction path between periods except the TTM formula on filed figures | Unit tests on fixtures missing Q4 and with year-to-date columns | Report the metric as `n/a` | Design only |
| DM-INV-02 | A comparison period is chosen by end date and span; with no single unambiguous candidate the metric is `n/a`. | `FR-01` | `PeriodMatcher` | Removed-column, duplicate-date, and conflicting-duplicate fixtures | `n/a` with reason | Design only |
| DM-INV-03 | No input was filed or priced after the analysis date. | `FR-01` | `MetricsInputAdapter` passes the as-of date to vendor functions and filters price rows | Two-date test on the same fixture | Drop the input; affected rows `n/a` | Design only |
| DM-INV-04 | Identical inputs give byte-identical output. | `FR-01` | Pure calculator; fixed formatting and ordering | Repeated evaluation test | Fail the test; block merge | Design only |
| DM-INV-05 | The calculator performs no LLM, network, file, or environment access. | `FR-01` | Module split between adapter and calculator; structural constraint for the coding agent | Import audit `T-STRUCT-01` (blocking CI gate) and call sentinels | Fail the test; block merge | Design only |
| DM-INV-06 | The verified-metrics block in a report equals the formatter output for the same inputs and sits after the model's text. | `FR-01` | `VerifiedBlockAppender` appends after the final model reply | Fake-LLM node test, including a reply that imitates the marker | Do not append; log a warning | Design only |
| DM-INV-07 | Every value states its period end, inputs, and formula; every `n/a` states a reason. | `FR-01` | `MetricResult` construction | Schema check on all fixture outputs | Fail the test | Design only |
| DM-INV-08 | Every expected value in FR-01 tests has a recorded independent source and was supplied by a team member, not computed by the code under test. | `FR-01` | Task specification and reviewer check | Fixture schema requires a `source` field per value | Reject the test file | Design only |
| CB-INV-01 | A downstream brief never exceeds the configured limit, excluding the verified block. | `CR-01` | `BriefExtractor` and `FallbackCondenser` | Oversized and adversarial fixtures | Fall back to condensation | Design only |
| CB-INV-02 | Every paragraph stating unavailable, withheld, or not-configured data is kept in the brief. | `CR-01` | `FallbackCondenser` priority order; brief validation | Baseline news and fundamentals text (5 and 7 mentions) | Use condensation instead of the model's brief | Design only |
| CB-INV-03 | The verified-metrics block is copied verbatim into the brief of the fundamentals report. | `CR-01`, `FR-01` | `report_brief_or_absent` | Byte comparison test | Pass the full report | Design only |
| CB-INV-04 | Report fields in state, saved reports, and memory are unchanged by CR-01. | `CR-01` | Brief applied only while building downstream prompts | Compare report fields before and after downstream prompt assembly | Not applicable; violation is a defect | Design only |

Changing or weakening an invariant requires requirement, ADR, trace, test, and
human-review updates before implementation or merge.

This fragment must be merged into the team's consolidated invariant register;
it must not replace the team's existing invariants.
