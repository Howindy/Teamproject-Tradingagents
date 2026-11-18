# FR-01 / CR-01 Traceability Contribution

Status: **personal draft / pending team review**
Implementation status: **design only; tests and monitors not started**

## Acceptance criteria to design, tests, and evidence

| Acceptance | Design element | Invariants | Planned test | Test layer | Runtime monitor | Expected evidence | Status |
|---|---|---|---|---|---|---|---|
| `FR-01-AC1` | `StatementParser`, `PeriodMatcher`, `DerivedMetricsCalculator` | DM-INV-02, DM-INV-07 | `T-FR01-01` | offline, pure | `MON-FR01-01` | revenue_yoy +105.9% vs 2025-07-27; +85.2%; +17.9%; margins 75.0 / 66.2 / 62.0% | Not started |
| `FR-01-AC2` | `PeriodMatcher` missing-period path | DM-INV-01, DM-INV-02 | `T-FR01-02` | offline, pure | `MON-FR01-02` | `n/a` with reason; substitutions = 0 | Not started |
| `FR-01-AC3` | `PeriodMatcher` duplicate handling | DM-INV-02 | `T-FR01-03` | offline, pure | `MON-FR01-02` | Equal duplicates merged; conflicts `n/a` ambiguous | Not started |
| `FR-01-AC4` | TTM and P/E rules | DM-INV-01, DM-INV-07 | `T-FR01-04` | offline, pure | `MON-FR01-01` | 302,969; 7.91 approx; 27.4x and 44.3x | Not started |
| `FR-01-AC5` | Adapter as-of filter; span-aware cash flow | DM-INV-01, DM-INV-03 | `T-FR01-05` | offline, pure | `MON-FR01-03` | Look-ahead uses = 0; cross-filing subtractions = 0 | Not started |
| `FR-01-AC6` | Whole calculator on reference companies | DM-INV-04, DM-INV-08 | `T-FR01-06` | offline, pure | — | Mismatches against human-specified references = 0; repeat output identical | Not started |
| `FR-01-AC7` | Tool error handling | — | `T-FR01-07` | offline, mocked vendors | `MON-FR01-04` | Explicit message; escaped exceptions = 0 | Not started |
| `FR-01-AC8` | Tool registration, `VerifiedBlockAppender`, prompt instructions | DM-INV-05, DM-INV-06 | `T-FR01-08` | offline, fake LLM | `MON-FR01-05` | Tool in TOOLS; block identical and last; instruction in 6 prompts | Not started |
| `CR-01-AC1` | `BriefExtractor`, `FallbackCondenser` | CB-INV-01 | `T-CR01-01` | offline, pure | `MON-CR01-02` | Output within limit; short reports byte-identical | Not started |
| `CR-01-AC2` | Fallback order; verified-block copy | CB-INV-02, CB-INV-03 | `T-CR01-02` | offline, pure | `MON-CR01-03` | Dropped gap statements = 0; block byte-identical | Not started |
| `CR-01-AC3` | Prompt builders | CB-INV-04 | `T-CR01-03` | offline, pure | — | Only downstream prompt report sections change; full state report fields unchanged | Not started |

Structural check: `T-STRUCT-01` (offline import audit) enforces DM-INV-05 and
the dependency rules in blueprint §9.

## Test to file

| Test | File |
|---|---|
| `T-FR01-01` to `T-FR01-06`, `T-STRUCT-01` | `test/offline/test_derived_metrics.py` |
| `T-FR01-07`, `T-FR01-08` | `test/offline/test_derived_metrics_tool.py` |
| `T-CR01-01` to `T-CR01-03` | `test/offline/test_context_brief.py` |
| Fixtures and reference values | `test/offline/fixtures/derived_metrics/` |

## Requirement to code

Paths are relative to the application package root (`tradingagents/`).

| Requirement | Existing files changed | New files |
|---|---|---|
| `FR-01` | `agents/analysts/fundamentals_analyst.py`; prompt text in `agents/researchers/bull_researcher.py`, `agents/researchers/bear_researcher.py`, `agents/risk_mgmt/aggressive_debator.py`, `agents/risk_mgmt/conservative_debator.py`, `agents/risk_mgmt/neutral_debator.py` | `dataflows/derived_metrics.py`, `agents/derived_metrics_tool.py` |
| `CR-01` | `agents/context.py`; brief block in `agents/analysts/market_analyst.py`, `agents/analysts/news_analyst.py`, `agents/analysts/fundamentals_analyst.py`; consumer call in the five downstream files | none |

## Requirement to architecture artifacts

| Requirement | ADR | Invariants | Policies | Options | Risks | Evaluations |
|---|---|---|---|---|---|---|
| `FR-01` | ADR-003 §2.1, §3 | DM-INV-01 to 08 | POL-DM-01 to 05 | O-01 to O-06, O-17, O-18, O-20, O-21 | R-06 to R-10, R-13 | EL-02 to EL-10, EL-P2 |
| `CR-01` | ADR-003 §2.2, §4, §5 | CB-INV-01 to 04 | POL-CB-01 to 03 | O-08, O-10 to O-13, O-15, O-16, O-19 | R-01, R-03, R-04, R-17 | EL-01, EL-11 to EL-15, EL-P5 |

## Runtime monitor definitions

| Monitor | Signal | Failure condition | Status |
|---|---|---|---|
| `MON-FR01-01` | Metric status counts in the tool footer | A covered SEC filer returns no `ok` growth metric | Not implemented |
| `MON-FR01-02` | `n/a` reasons | A metric is `ok` while its comparison period was missing or ambiguous | Not implemented |
| `MON-FR01-03` | Latest input date per run | Any input dated after the analysis date | Not implemented |
| `MON-FR01-04` | Tool error messages | An exception escapes the tool | Not implemented |
| `MON-FR01-05` | Verified block in the fundamentals report | Covered filer and no block, or block not last | Not implemented |
| `MON-CR01-02` | Brief source per report | `error` count above zero, or `fallback` dominant for a prompt-briefed analyst | Not implemented |
| `MON-CR01-03` | Gap statements in full report vs brief | Any gap statement missing from the brief | Not implemented |

No test, monitor, threshold, or benefit is claimed complete.

This fragment must be merged into the team's consolidated trace matrix.
