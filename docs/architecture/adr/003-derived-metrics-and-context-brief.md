# ADR 003 — Deterministic Derived Metrics and Bounded Downstream Context

Status: **v0.1 — draft / pending human review**
Decision status: **proposed**
Date: 2026-11-03
Related draft requirements: `FR-01`, `CR-01`
Implementation status: **design only; no application code changed**

The ADR number is provisional (team open question OQ-01). This is a personal
contribution to be integrated into the team's consolidated D2 artifacts.

---

## 1. Context

### 1.1 Model arithmetic on irregular statement tables

The fundamentals analyst receives raw SEC EDGAR statements as CSV text and
computes every growth rate, margin, and multiple itself. The quarterly tables
are irregular:

- fourth quarters are absent, because filers report them only inside the
  annual figure, and the vendor deliberately never derives them;
- some quarters appear under two end dates (2010-07-31 and 2010-08-01);
- cash flows are often reported only year to date (37 such columns in the
  baseline cash-flow table).

In the recorded baseline run the analyst reported Q2 FY2027 revenue growth as
+68.6%. The filed figures give +105.9%. The +68.6% value is the ratio against
the 2025-10-26 quarter, which the model labeled Q2 FY2026 — the error that
counting columns produces when a quarter is missing. Both researchers repeated
the figure, and the final decision used it to argue that growth was
decelerating, although it was accelerating (+85.2% to +105.9%).

The same run cited a "trailing P/E" of 44x without a definition. On the
recorded inputs the fiscal-year P/E is 44.3x and the TTM P/E is 27.4x.

Of 48 percentages in the baseline fundamentals report, 41 do not appear in any
tool output and were produced by the model.

### 1.2 Repeated evidence in downstream prompts

The Bull and Bear researchers and the three risk debaters each interpolate all
four analyst reports in full (45,219 characters in the baseline) through
`context.report_or_absent`. This repeated evidence is an estimated 36-41% of
the run's 156,541 input tokens. Each downstream prompt is an estimated
11k-17k tokens (45k-58k characters), far below any context-window limit, so compression that triggers only
near a limit never applies to it.

## 2. Decision

### 2.1 FR-01

Add a deterministic derived-metrics service with a pure calculator and a
separate I/O adapter. Deliver its output through two paths:

1. a `get_derived_metrics` tool offered to the fundamentals analyst; and
2. a `VERIFIED-METRICS` block that code appends after the analyst's final
   report text.

Comparison periods are matched by end date. Ambiguous or missing comparisons
are `n/a` with a reason. No period is derived by subtraction. Six prompts
(fundamentals analyst, both researchers, three risk debaters) instruct the
model to quote verified values instead of recomputing them.

### 2.2 CR-01

The market, news, and fundamentals analysts end their report with a marked
`DOWNSTREAM-BRIEF` block. A new `context.report_brief_or_absent` function
returns that block if it is valid and within the size limit, otherwise a
deterministic condensation of the report. The five downstream agents call it
in place of `report_or_absent`. Full reports in state, reports, and memory are
unchanged. The verified-metrics block is copied verbatim into every brief of
the fundamentals report.

## 3. Options considered — FR-01

### A. Prompt instruction only ("compute growth carefully") — rejected

It leaves the arithmetic with the model. The baseline error came from
selecting the wrong comparison column, which an instruction does not prevent
and which cannot be tested offline.

### B. Model self-check or a second model as verifier — rejected

It adds an LLM call and its cost and latency, and the verifier faces the same
irregular tables. Its result is nondeterministic, so there is no fixed
expected value to test against.

### C. Add derived columns to the vendor's statement output — rejected

The vendor's contract is "values as filed". Mixing computed values into that
output blurs filed and derived data, and every consumer of the statement tools
would receive the new columns whether it needs them or not.

### D. A new vendor method behind the data router — rejected

The router chooses among vendors whose statement formats and date semantics
differ (SEC EDGAR, yfinance, Alpha Vantage). Derived metrics are a computation
over one well-defined input, not a vendor. Fallback to another vendor would
change results silently depending on availability.

### E. Tool only — rejected as the sole delivery path

The model decides whether to call a tool. If it does not, downstream agents
still receive model arithmetic only.

### F. Appended block only — rejected as the sole delivery path

The analyst writes its report before code appends the block, so the analyst's
own prose would still rest on its own arithmetic.

### G. Pure calculator + tool + code-appended block — proposed

The tool serves the analyst while it writes. The block guarantees that every
downstream reader sees the verified values regardless of what the analyst did.
The calculator is a pure function and is fully testable offline.

## 4. Options considered — CR-01

### A. Limit-triggered compression only — rejected for this problem

Downstream prompts are an estimated 11k-17k tokens. A threshold near the context window
never fires, so the repeated evidence is still sent on every run.

### B. Fixed truncation to N characters — rejected as the primary method

Truncation keeps the start of each report and drops the conclusions and
data-gap statements, which are usually at the end.

### C. A dedicated LLM summarization node — rejected

It adds one model call per report, adds a graph node and a state field, and
adds a new place where numbers can be altered. The analyst that wrote the
report is better placed to summarize it in the same call.

### D. Pass only the fundamentals report to downstream agents — rejected

It removes evidence the debaters use: price levels from the market report and
events from the news report.

### E. Analyst-written brief + deterministic extraction and fallback — proposed

The brief costs a few hundred output tokens in a call that already happens.
Extraction and fallback are deterministic, size-bounded, and testable offline.
When the model ignores the format, the fallback still meets the size bound and
keeps data gaps.

## 5. Brief size

| Limit per report | Downstream characters per consumer | Estimated input saving | Share of baseline input |
|---:|---:|---:|---:|
| 1,000 | 5,500 | 49.6k-56.7k tokens | 32%-36% |
| **2,000 (proposed)** | **9,500** | **44.6k-51.0k tokens** | **29%-33%** |
| 3,000 | 13,500 | 39.6k-45.3k tokens | 25%-29% |
| 4,000 | 17,500 | 34.6k-39.6k tokens | 22%-25% |

Estimates use the baseline reports, a 1,500-character verified-metrics block,
five consumers, and 3.5-4 characters per token. 2,000 characters leaves room
for about eight key figures with their periods while keeping most of the
saving. The limit is configurable and is reviewed against offline content-preservation fixtures.

## 6. Consequences

### Positive

- The recorded +68.6% error class (wrong comparison period) cannot come from
  the calculator; ambiguous cases become explicit `n/a`.
- Valuation multiples carry a definition.
- Every downstream agent sees the same verified figures.
- Downstream prompts shrink by an estimated 29%-33% of total run input.
- Both changes are testable offline on recorded data.

### Negative

- SEC-only coverage: non-US instruments get no verified metrics.
- TTM EPS is approximate.
- Downstream agents see less narrative detail, which may weaken debate.
- The model may still recompute values despite the instruction.
- Net token savings and effects on decision quality remain unmeasured.

## 7. Verification obligations

- AC1 to AC4 reproduce hand-computed baseline values exactly.
- No neighboring-column substitution when a comparison period is missing.
- No figure from a filing or price after the analysis date.
- Reference values for multi-company tests come from earnings releases or
  hand calculation, are written by a team member into the coding agent's task
  specification with their source, and are never derived by running the code
  under test.
- An import-audit test keeps the calculator free of I/O (blocking CI gate).
- Brief output never exceeds the limit; short reports pass byte-identical.
- Data-gap statements and the verified block survive condensation.
- Prompt hand-off preserves the full report fields in state.

All tests are planned and not started.

## 8. Re-decision conditions

Re-open this ADR if:

- a non-SEC fundamentals source must be supported;
- the vendor changes its statement text format;
- offline checks find lost evidence, data gaps, or verified figures;
- the team context assembler adopts a different L3 policy for these calls;
- per-call input limits change so that downstream prompts approach them.

## 9. Status

- Decision: **proposed, not approved**.
- Thresholds: **provisional**.
- Implementation and tests: **not started**; token benefits remain estimates.
