# ADR 002 — Deterministic Disclosed Financial Metrics (FR-10)

- Status: Proposed for final human review (design/test pre-approval for preparation recorded in [PR #14 comment 7099714477](https://github.com/Howindy/Teamproject-Tradingagents/pull/14#issuecomment-7099714477), binding `docs/plans/financial-metrics-integration.md @ e99ab57b6e460fad59bb4bf4a81cffa5c717c8da`; runtime integration is delivered)
- Date: 2026-11-23
- Requirements baseline: `docs/req/requirements.yaml` version `1.51.0` (`FR-10`, `FR-10-FC01` through `FR-10-FC10`)
- Historical provenance: succeeds the personal branch's old financial `FR-07` (`origin/haoxi @ 7e676fb00fff319930685a9fa059265f3061aeff`, reference freeze `fr07-sec-reference-v1`); distinct from current deferred `FR-07` (analyst briefs)
- Related: [Architecture Blueprint](../../../architecture-blueprint.md), [ADR 001](001-graph-internal-final-check.md), [Evaluation Table](../evaluation-table.md)

---

## 1. Context and problem

Before FR-10, the Fundamentals Analyst receives five financial tools (`get_fundamentals`, `get_income_statement`, `get_balance_sheet`, `get_cashflow`, `get_insider_transactions`) and computes ratios/growth prose using the LLM. That permits comparative filing `fy`/`fp` misattribution, YTD-vs-quarter confusion, Q4 subtraction, unit/basis mismatch, future-price lookahead, and silent proxy substitution when an issuer omits a concept.

D1 v1.50.0 introduced `FR-10: Deterministic disclosed financial metrics` as an opt-in, source-preserving calculation and prompt-injection feature without activating deferred `FR-07` analyst briefs or altering `FR-03`/`FR-04`/`SB-01` authorities.

## 2. Architecture decisions

### D-201 Bounded `financials` component (`C-21` / `IF-26`)

Logical ownership for `FR-10` is placed under `src/tradingagents/financials/`:

- `models.py`: immutable contracts (`EvaluationClock`, `FinancialFact`, `PriceRecord`, `FinancialInputs`, `MetricResult`, `MetricBundle`) rejecting booleans and binary floats (`Decimal` / exact `Fraction` only).
- `metrics.py`: pure selection, disclosure/cutoff filtering, calculation, `ROUND_HALF_UP` formatting, and deterministic table rendering for the ten fixed metrics (`revenue_yoy_q`, `revenue_yoy_a`, `revenue_qoq`, `gross_margin`, `operating_margin`, `net_margin`, `current_ratio`, `liabilities_to_assets`, `fcf_reported_span`, `pe_fy`).
- `service.py`: `FinancialDataProvider` protocol (`fetch(ticker, as_of) -> FinancialInputs`) and run-scoped `FinancialMetricProvider` calculation/reuse.
- `sec_provider.py`: optional general SEC `companyfacts`/`submissions` + Yahoo completed-close adapter; does not alter existing vendor tool return shapes or failure semantics.
- `wiring.py`: composition seam (`run_clock`, `build_metrics_factory`, per-analysis lifecycle binding).

### D-202 Cutoff, fiscal mapping, and explicit `n/a` semantics

- **Date cutoff:** `00:00 America/New_York` on `trade_date` (`EvaluationClock`). No same-day filing or uncompleted daily trading session is assumed available without explicit time evidence. Filing visibility is date-level and historical prices are reconstructed daily bars, not an intraday point-in-time guarantee.
- **Fiscal position:** Use carrying filing `fy`/`fp`, latest reported instant/end, and covered-period anniversary matching rather than calendar-year shortcuts or equal fiscal-year division. Unprovable fiscal positions yield explicit `n/a` rather than guessing.
- **No synthetic derivations:** No TTM, no FCF YoY, no Q4-by-subtraction, no `abs()` on unknown-sign CapEx, no concept proxy (e.g., XOM absent `GrossProfit`/`OperatingIncomeLoss` stays `n/a: missing_input`).

### D-203 Local fundamentals-analyst pre-model injection and fresh-run isolation

- When `FR-10` is enabled and `fundamentals` is in `selected_analysts`, `create_fundamentals_analyst(llm, metrics_factory=...)` resolves `metrics_factory(state)` before the first model invocation and places the deterministic table in the fundamentals analyst system prompt alongside explicit authority/provenance instructions.
- Repeated tool rounds and wrap-up turns within the same analysis reuse the same rendered text without re-reading or re-computing.
- **Cross-analysis isolation:** A reusable `TradingAgentsGraph` instance must bind fresh metric scope at each outer analysis entry (both CLI streaming and `TradingAgentsGraph.propagate()`), rather than retaining a date-keyed cross-run cache on the factory/graph object. No `FinancialMetricProvider`, lock, or `Decimal` object enters serializable graph state or checkpoints; only plain JSON-compatible projections or rendered text cross boundaries.
- **Opt-in & fail-open degradation:** Default off. When disabled or when `fundamentals` is not selected, zero FR-10 data fetches occur. Unsupported issuers/assets and provider failures degrade explicitly without inventing metrics or aborting otherwise valid baseline analysis.
- **Non-goals / exclusions:** Preserves the five existing financial tools, original report saving/display, `FR-03` availability completeness, `FR-04` purchase-scenario risk checks, and `SB-01` formal decision authority (`FR-10` adds no completeness item and no `SB-01` veto). Excludes shared downstream briefs (`run/brief.py`, `run/summary.py`, `run/assembler.py`, `Context Assembler`).

## 3. Compatibility with ADR 001

ADR 001 Decision `D-10c` preserves existing analyst prompt assembly while noting role-local context additions. `FR-10` adds only a local, opt-in deterministic metric table to the Fundamentals Analyst system prompt; it does not introduce a unified cross-role context assembler, token budget engine, or five-role summary substitution.

## 4. Verification and semantic gate

- **PR 1 (preparation):** Align D1/D2/D4, freeze compact lossless reference projection (`docs/ci/financial-metrics-cases.json`) and rubric (`docs/ci/financial-metrics-rubric.md`), implement trusted semantic runner (`scripts/financial_metrics_eval.py`) and offline evaluation/gate tests (`test/offline/test_financial_metrics_evaluation.py`, `test/offline/test_ci_gates.py`). `docs/ci/semantic_eval.yaml` remains `unapproved` until separate authorization of the 6-request `deepseek-flash` (thinking disabled) run.
- **Delivered integration.** Both public entries bind the analysis-local metric scope. `test/offline/test_financial_metrics.py`, `test/offline/test_sec_financial_provider.py`, `test/offline/test_financial_metrics_integration.py` exercise calculation, source adapters and analyst delivery. Live semantic evaluation has its own approval record.
