# FR-10 Financial Metrics Semantic Evaluation Rubric

- Version: `fr10-eval-rubric-v1`
- Dataset: `docs/ci/financial-metrics-cases.json` (`fr10-sec-reference-projection-v1`)
- Scope: Candidate reports for `FM-S01`, `FM-S02`, `FM-S03`, `FM-S04` (4 candidate runs) paired with baseline reports for `FM-S01` and `FM-S02` (2 baseline runs). Maximum **6 completion requests**, `deepseek-flash`, `extra_body={"thinking":{"type":"disabled"}}`, `temperature=0`, `max_tokens=4096`, `stream=false`, `n=1`, English output, `max_retries=0`, `timeout_seconds=120`, no repetitions, no LLM judge.

## 1. Binary scoring dimensions (5 per candidate case = 20 total checks)

Each candidate case (`FM-S01`..`FM-S04`) is scored across five binary (`pass` = 1, `fail` = 0, or `needs_review` if ambiguous) dimensions:

1. **D1 — Numeric, status, and `n/a` reason correctness**
   - Every computed metric in the case appears with its exact independent rounded value (or unrounded decimal equivalent within the `0.1 pp` / `0.1x` / exact USD-million resolution).
   - Every `n/a` metric (`FM-S02` `gross_margin` and `operating_margin`; `FM-S03` `revenue_yoy_q`; `FM-S04` `pe_fy`) is reported explicitly as unavailable / `n/a` with its typed reason (`missing_input`, `missing_comparison`, `price_not_completed`) and never fabricated or zero-filled.
   - `FM-S03` preserves `revenue_qoq = -1.4%` without substituting Q2 as YoY; `FM-S04` preserves all nine non-P/E rows.
2. **D2 — Period, unit, and price/EPS basis**
   - Preserves reported spans and fiscal identifiers (`Q3 FY2025` for AAPL quarterlies, `FY2024` vs `FY2023` for annual YoY, `9M FY2025` / YTD for AAPL FCF, `Q2 FY2025` and `6M YTD` for XOM, `at 2025-06-28` / `at 2025-06-30` for balance-sheet ratios).
   - Preserves `%`, `x`, and `USD_millions` (or USD millions) units; states `pe_fy` uses `2025-08-04` completed close over `FY2024` annual diluted EPS (never TTM P/E).
3. **D3 — Disclosure/source traceability and no lookahead claim**
   - Cites filing/source references consistent with the injected program table without inventing accession numbers, filings, or sources for `n/a` rows.
   - Makes no claim of post-cutoff data availability (`FM-S04` must not claim the `2025-08-05T04:00:01+00:00` completed price is eligible as of `2025-08-05T00:00:00-04:00`).
4. **D4 — Useful fundamental interpretation without misreading `n/a`**
   - Interprets computed growth, margins, liquidity, leverage, cash generation, and valuation accurately while treating `n/a` metrics as unavailable rather than zero or verified.
5. **D5 — Retained ordinary fundamental task coverage and qualifications**
   - Produces a structured English fundamental report covering company context, financial statement findings, limitations/qualifications, and a summary Markdown table matching the existing fundamental analyst task.
   - For paired normal cases `FM-S01` and `FM-S02`, candidate D5 must not regress relative to the paired baseline output on the same frozen statement material.

## 2. Recognized metric labels and atomic assertions

| `metric_id` | Recognized labels / aliases | Atomic check focus |
|---|---|---|
| `revenue_yoy_q` | `revenue_yoy_q`, `Quarterly Revenue YoY`, `YoY Revenue (Q)` | `FM-S01/04`: `9.6%`; `FM-S02`: `-12.4%`; `FM-S03`: `n/a` (`missing_comparison`) |
| `revenue_yoy_a` | `revenue_yoy_a`, `Annual Revenue YoY`, `FY Revenue YoY` | `FM-S01/03/04`: `2.0%`; `FM-S02`: `1.5%` |
| `revenue_qoq` | `revenue_qoq`, `Revenue QoQ`, `Sequential Revenue` | `FM-S01/03/04`: `-1.4%`; `FM-S02`: `-2.0%` |
| `gross_margin` | `gross_margin`, `Gross Margin` | `FM-S01/03/04`: `46.5%`; `FM-S02`: `n/a` (`missing_input`) |
| `operating_margin` | `operating_margin`, `Operating Margin` | `FM-S01/03/04`: `30.0%`; `FM-S02`: `n/a` (`missing_input`) |
| `net_margin` | `net_margin`, `Net Margin`, `Reported Net Margin` | `FM-S01/03/04`: `24.9%`; `FM-S02`: `8.7%` |
| `current_ratio` | `current_ratio`, `Current Ratio` | `FM-S01/03/04`: `0.9x`; `FM-S02`: `1.2x` |
| `liabilities_to_assets` | `liabilities_to_assets`, `Liabilities / Assets`, `Liabilities-to-Assets` | `FM-S01/03/04`: `80.1%`; `FM-S02`: `39.7%` |
| `fcf_reported_span` | `fcf_reported_span`, `Reported-Span FCF`, `Free Cash Flow` | `FM-S01/03/04`: `72,281` / `72281` USD millions (YTD); `FM-S02`: `12,322` / `12322` USD millions (YTD) |
| `pe_fy` | `pe_fy`, `Fiscal-Year P/E`, `FY P/E` | `FM-S01/03`: `33.4x`; `FM-S02`: `13.7x`; `FM-S04`: `n/a` (`price_not_completed`) |

## 3. Critical failures (automatic `failed` regardless of average)

Any of the following in a candidate report triggers an immediate critical failure (`status = "failed"`):

- Asserting a wrong numeric value for any computed target metric (e.g., `FM-S03` using `-1.4%` as `revenue_yoy_q`, or substituting YTD revenue for quarterly revenue).
- Inventing a numeric value or source for an `n/a` metric (e.g., fabricating XOM `gross_margin` / `operating_margin`, fabricating `FM-S03` `revenue_yoy_q`, or treating `n/a` as `0` / `0.0%`).
- Using or endorsing the post-cutoff price in `FM-S04` (`33.4x` claimed valid or eligible).
- Mislabeling YTD FCF as single-quarter FCF (`YTD-as-quarter`) or labeling `pe_fy` as `TTM P/E` (`FY-as-TTM`).
- Candidate system prompt missing the injected ten-row program financial metrics table before the first model call.

## 4. Ambiguous claims (`needs_review`) and thresholds

- **Ambiguity rule:** If deterministic scoring detects conflicting numbers, missing expected labels without an explicit contradiction, or unparseable phrasing for a target metric, the case is flagged `needs_review` (never automatic `pass`). `ci_semantic_eval.py` accepts only `status == "passed"`, so `needs_review` fails closed until a human reviewer resolves the claim with a linked claim-level review record (never altering the oracle).
- **Proposed pass threshold (pending separate authorization):**
  - Candidate D1, D2, and D3 pass on all 4 cases (`4/4` each).
  - At least `18 / 20` (`90%`) across the 20 candidate dimension checks (`4 cases x 1 execution x 5 dimensions`).
  - Zero critical failures across all 4 candidate cases.
  - Dimension 5 non-regression on paired normal cases `FM-S01` and `FM-S02` relative to baseline (baseline scores are reported separately and excluded from the 20-check denominator).

## 5. Human adjudication examples

- **Pass example (`FM-S02` `gross_margin`):** `"Gross margin: n/a (missing_input; GrossProfit is absent in XOM's disclosed filings, so no proxy is substituted)."` → D1 pass, D3 pass.
- **Critical fail example (`FM-S04` `pe_fy`):** `"Fiscal-year P/E is 33.4x (or TTM P/E is 33.4x) using the August 4 close."` → Critical failure (`future_price_or_post_cutoff_used` / `fy_as_ttm_mislabel`) → overall `failed`.
- **Ambiguous (`needs_review`) example (`FM-S01` `fcf_reported_span`):** Report states `72,281` million USD without stating the nine-month YTD period (`2024-09-29..2025-06-28`) or labels it ambiguously as `"recent period FCF"` without explicitly calling it quarterly or YTD → D2 / case marked `needs_review` for human claim-level inspection.
