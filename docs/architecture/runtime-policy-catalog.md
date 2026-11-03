# FR-01 / CR-01 Runtime Policy Fragment

All values are provisional until the related open decisions close.

## POL-DM-01 — Period matching

| Comparison | Same span | End date earlier by | If no match | If several matches |
|---|---|---|---|---|
| Year over year | Yes | 355-380 days | `n/a`: no comparable period filed | Equal values: merge; unequal: `n/a` ambiguous |
| Quarter over quarter | `Q` only | 80-100 days | `n/a`: no prior quarter filed | Same as above |
| Annual | `FY` only | 355-380 days | `n/a` | Same as above |

The windows cover 52- and 53-week fiscal years. Duplicate end dates are those
within 7 days of each other.

## POL-DM-02 — No derived periods

- Never compute a quarter by subtracting filed periods (for example annual
  minus three quarters, or 6-month minus 3-month).
- TTM uses only: latest `FY` + current-year `Q` values - their year-ago `Q`
  values. If any of those is missing, TTM is `n/a`.

## POL-DM-03 — As-of discipline

- Statements: vendor functions called with the run's analysis date.
- Price: the latest verified close on or before the analysis date.
- The tool output header states the analysis date, the statement source, and
  the price date.

## POL-DM-04 — Metric catalog (version 1)

| Metric ID | Formula | Span | Unit |
|---|---|---|---|
| `revenue_yoy` | Revenue / year-ago revenue - 1 | Q, FY | pct |
| `net_income_yoy` | Net income / year-ago net income - 1 (`n/a` if year-ago ≤ 0) | Q, FY | pct |
| `revenue_qoq` | Revenue / prior-quarter revenue - 1 | Q | pct |
| `gross_margin` | Gross profit / revenue | Q, FY | pct |
| `operating_margin` | Operating income / revenue | Q, FY | pct |
| `net_margin` | Net income / revenue | Q, FY | pct |
| `eps_yoy` | Diluted EPS / year-ago diluted EPS - 1 (`n/a` if year-ago ≤ 0) | Q, FY | pct |
| `ttm_revenue` | POL-DM-02 TTM rule | TTM | usd_m |
| `ttm_eps` | POL-DM-02 TTM rule on diluted EPS; status `approx` | TTM | usd_per_share |
| `pe_ttm` | Close / `ttm_eps` (`n/a` if ≤ 0) | — | multiple |
| `pe_fy` | Close / latest FY diluted EPS (`n/a` if ≤ 0) | — | multiple |
| `current_ratio` | Current assets / current liabilities | Balance date | ratio |
| `liabilities_to_assets` | Total liabilities / total assets | Balance date | ratio |
| `free_cash_flow` | Operating cash flow - capital expenditure | As filed: Q, 6M, 9M, FY | usd_m |
| `fcf_yoy` | FCF / year-ago FCF on the same span - 1 (`n/a` if year-ago ≤ 0) | As filed | pct |

Each metric is reported for the latest four periods where available. A growth
rate on a non-positive base is `n/a`, because its sign has no meaning.

## POL-DM-05 — Display

- Percentages and multiples: 1 decimal. Ratios: 2 decimals. USD millions:
  integer with thousands separators.
- Every row shows period end, value, and "computed from" (inputs and formula).
- Footer: counts of `ok`, `approx`, and `n/a` rows.
- Unsupported instrument: `Derived metrics are not available for <ticker>:
  <reason>.` No block is appended.

## POL-CB-01 — Brief size and structure

- Limit: 2,000 characters per report, excluding the verified block.
- Required fields, in order: Stance, Key figures (at most 8, each with its
  period), Key levels / triggers, Data gaps (`none` if none).
- A brief missing a field or over the limit is invalid and triggers POL-CB-02.

## POL-CB-02 — Fallback condensation order

Fill the limit in this order and stop when it is reached:

1. every paragraph stating unavailable, withheld, or not-configured data
   (always kept, even past the limit);
2. paragraphs starting with "Bottom line", "Overall", "Conclusion", or
   "Summary";
3. headings, each with the first sentence of its section;
4. the first paragraph of the report.

Cut at a sentence boundary and end with
`[condensed: <kept> of <total> characters; full report available to the user]`.

## POL-CB-03 — Configuration and verification

- The provisional brief limit is 2,000 characters, configured in context.py.
- Any exception in brief handling returns the full report and logs a warning.
- Offline fixtures verify extraction, content preservation, and prompt hand-off.
- Savings remain character-based planning estimates, not measured token benefits.
