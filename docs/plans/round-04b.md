# Round-04B | Integrate deterministic financial metrics through IF-26

**Planning draft v5, 2026-11-25.** Start from `main @ 5718bacff6cafb9412a805878fe82e97f279a8bc` with Round 3 present and Round-04A absent. The supplied `fr10-integration.md` describes the financial team's runtime interface. Use that contract and the team's implementation as the starting point. D1 version 1.50.0 defines the ten acceptance criteria. [ADR 002](../architecture/adr/002-deterministic-financial-metrics.md) defines calculation and ownership boundaries.

## What to reuse

Use [PR #19 at `2fbd1cf`](https://github.com/Howindy/Teamproject-Tradingagents/commit/2fbd1cfe107e2ff985b7b2d079b4c0bfc572ff74) as the candidate implementation. Port the FR-10 delta onto the named baseline. The candidate already supplies the following interfaces, graph wiring and analysis-local cache. Retain their behavior and restrict product edits to demonstrated acceptance failures.

| Handoff interface | Integration decision |
|---|---|
| `FinancialDataProvider.fetch(ticker, as_of) -> FinancialInputs` | Reuse the structured SEC facts/submissions and completed-close adapters. Supply controlled providers at this same boundary in offline tests. Keep issuer, accession, concept, disclosure evidence, covered dates, fiscal position, units, currency, sign convention and share basis attached to the facts. |
| `build_metrics_factory(config, data_factory=...)` | Reuse the factory and its callable resolver. Explicit `data_factory(clock)` supplies controlled inputs for the trusted evaluation driver. Preserve its existing fact/price/input constructor keywords and the result's `.text` field. Run a direct probe using the driver's actual projection. |
| `TradingAgentsGraph(..., metrics_factory=resolver)` | Honor explicit injection. For normal CLI use, construct the resolver from effective configuration. Pass it through graph setup to the fundamentals analyst. A supplied plain callable may manage its own lifecycle. |
| `create_fundamentals_analyst(llm, metrics_factory=None)` | Call `resolver(state)` before the first model turn and reuse the rendered evidence on tool and wrap-up turns. Program values take priority only for the matching metric **and period**. Preserve the five existing tools, language instructions, message history, analyst report and existing full-report save path. |
| `MetricProviderFactory.analysis_scope()` | In `propagate()`, bind an analysis-local metric scope beside the existing FR-03 RunContext. In `stream_run()`, bind the scope inside the copied execution context and close it there on exhaustion, early close or error. In debug propagation through streaming, verify one effective cache per analysis. A reused graph starts fresh even for the same ticker/date. Keep providers, locks, caches and bundles outside serialized state. |

**Configuration.** Retain the handoff names `fr10_sec_enabled` (default false) and `fr10_reference_root` (default empty). Normal CLI users select Fundamentals and opt into SEC with `TRADINGAGENTS_FR10_SEC_ENABLED=true`, or select a supported local snapshot with `TRADINGAGENTS_FR10_REFERENCE_ROOT`. Use a snapshot or injected provider for offline work. Historical `fr07_*` switches do not activate the feature. Preserve `fr07-direct-v1` as formula provenance. The trusted driver's explicit provider injection must work even when its configuration contains a historical key.

## Minimal change boundary

The following paths identify the candidate changes to inspect and reuse. Their inclusion does not require an edit to every file.

- Financial calculations and adapters: `src/tradingagents/financials/__init__.py`, `src/tradingagents/financials/models.py`, `src/tradingagents/financials/metrics.py`, `src/tradingagents/financials/service.py`, `src/tradingagents/financials/sec_provider.py` and `src/tradingagents/financials/wiring.py`.
- Existing structured reads and configuration: `src/tradingagents/dataflows/vendors/sec_edgar.py`, `src/tradingagents/dataflows/vendors/yahoo/market.py` and `src/tradingagents/default_config.py`. Verify decimal source precision before reuse. A binary float converted back to a string cannot recover the original disclosure or price token.
- Application integration: `src/tradingagents/agents/analysts/fundamentals_analyst.py`, `src/tradingagents/graph/setup.py` and `src/tradingagents/graph/trading_graph.py`. B adds no graph node or edge. CLI streaming already uses the graph interface. CLI code, AgentState, RunContext, risk, final recommendation, memory and report writers are outside B's change scope.
- Reuse all three candidate test modules. `test/offline/test_financial_metrics.py` covers frozen rows, missing comparisons, basis/sign checks and scope reuse. `test/offline/test_sec_financial_provider.py` covers structured reads, fiscal spans, filing visibility, price completion and freshness. `test/offline/test_financial_metrics_integration.py` exercises the real analyst, programmatic and CLI entries, repeated runs, stream isolation and cleanup, FR-03 observations and decision-output sentinels. Extend the nearest existing test only where an assertion is missing.

## Remaining acceptance evidence

| Criteria | Smallest check or correction |
|---|---|
| FC01–FC05, FC08 | Replay the trusted driver's actual AAPL and XOM input projection through the injected factory. Its projection omits `calendar_evidence`, which can turn valid comparisons into `incomparable_period` even when the candidate's richer fixtures pass. Check all ten rows, periods, sources and reasons for FM-S01 through FM-S04. Use fiscal evidence available to the product; if a required field is genuinely absent, record the contract mismatch for review. Preserve the frozen expectations and the rejection of ambiguous periods. Check uncovered fiscal-year, sign and basis cases against the matrix below. |
| FC06–FC07 | Verify the adapter precision decisions below, the half-up tie and output under a deliberately low ambient Decimal precision. Exercise both an exact numeric result and a reasoned unavailable row. |
| FC09 | Repeat a same-ticker, same-date analysis on one graph with different controlled values. Assert each prompt contains its own value, with one fetch per analysis. Reuse the existing lifecycle tests for early close, interleaving and exception cleanup. |
| FC10 | Make `data_factory(clock)` raise during construction, before a provider enters the cache. Check visible unavailable evidence, continued baseline delivery and clean state on the next analysis. The existing fetch-failure case exercises a later boundary. |

### Source precision decision (FC06–FC07)

The calculator's rejection of float inputs covers only values reaching its public boundary. For SEC, trace a fractional Company Facts value from the raw JSON response through `response.json()`, the cache and conversion with `Decimal(str(value))`. Use a token with more significant digits than a binary float preserves. Compare the cold and cached paths to that token. Confirm whether existing cache entries retain the original digits and how the adapter handles entries whose precision cannot be verified.

For Yahoo, `auto_adjust=False` selects the unadjusted close. The history frame can already contain a binary float before conversion to decimal text. Confirm whether the source exposes an authoritative decimal close or a documented quote precision and rounding rule acceptable under FC07. Record the evidence and decision for each source independently. Until precision is established, keep the affected live-source row open for acceptance. If an exact value is required and unavailable, use the existing unavailable-row mechanism. Limit any approved fix to the affected read or cache boundary.

## Calculation and acceptance tests

Use the existing selector, calculator and renderer. Verify every row against the cutoff at 00:00 America/New_York on the trade date. Preserve sources and periods even when a value is unavailable. Use the matrix to map existing assertions and the remaining checks above to each criterion.

| Criterion | Controlled case and expected result |
|---|---|
| FR-10-FC01 | Use a January year-end issuer, comparative columns in a later filing, and filings on either side of the cutoff. Select by issuer, covered period, carrying filing fiscal year/period and calendar evidence. Exclude same-day date-only disclosures. Ambiguous fiscal position yields a reasoned n/a. Check both summer and winter UTC offsets. |
| FR-10-FC02 | Revenue 120 versus prior-year quarter 100 and previous quarter 80 gives 20.0% YoY and 50.0% QoQ. Annual 440 versus 400 gives 10.0%. Require directly reported comparisons. A missing comparison or nonpositive base yields n/a. YTD, a nearby column or annual-minus-YTD cannot supply a quarter. |
| FR-10-FC03 | Same-span revenue 200, gross profit 90, operating income 40 and net income 30 give margins 45.0%, 20.0%, 15.0%. Reject incompatible spans or units. XOM's missing gross/operating concepts retain `missing_input`. |
| FR-10-FC04 | Same-date current assets/liabilities 150/100 give 1.5x. Liabilities/assets 400/1000 give 40.0%. A mismatched instant or nonpositive denominator yields n/a for the affected row. |
| FR-10-FC05 | CFO 20 million less disclosed PP&E payments of 30 million gives -10 USD million. Keep the actual annual or YTD span. Unknown payment sign yields n/a. Exclude FCF YoY. |
| FR-10-FC06 | A completed close of 120 and positive FY diluted EPS of 4 yield 30.0x. Check currency, split/share basis, completion timestamp, price date and EPS period. A future, uncompleted, stale or incompatible price yields n/a. The handoff supports a matching preceding regular weekday. Holiday or data-gap cases may yield n/a. Label the metric FY P/E. |
| FR-10-FC07 | Reject bool and binary float as authoritative metric inputs. Verify exact Decimal/Fraction arithmetic, JSON-compatible output, explicit units and ROUND_HALF_UP display to one decimal for percentages and ratios. Verify that 2.25x renders as 2.3x. |
| FR-10-FC08 | Complete, partial and all-missing inputs each produce the same ten ordered rows. Each unavailable row explains why and retains known inputs, periods and sources. Compare the full AAPL/XOM projections with the independent fixtures. |
| FR-10-FC09 | Capture the real fundamentals prompt before initial, tool and wrap-up calls. Assert the same rendered table, five tool definitions, history and original report content. Observe one fetch/calculation per analysis. Repeat twice on one graph, then interleave two same-date streams, close one early and inject an error into the other. Verify isolation and cleanup in the copied context. Exercise explicit resolver injection and automatic CLI construction. |
| FR-10-FC10 | Default/off and fundamentals-omitted runs make zero metric fetches. Explicitly enable with a controlled provider, then exercise unsupported issuer/asset, missing input and provider failure. Expect a visible unavailable reason and normal baseline analysis delivery. Check both entries and their return/save behavior. |

The fixed row order is `revenue_yoy_q`, `revenue_yoy_a`, `revenue_qoq`, `gross_margin`, `operating_margin`, `net_margin`, `current_ratio`, `liabilities_to_assets`, `fcf_reported_span`, `pe_fy`. In FM-S03 only quarterly YoY becomes unavailable (`missing_comparison`), while QoQ remains -1.4%. In FM-S04 a one-second post-cutoff completion changes only FY P/E to `n/a: price_not_completed`. Compare values, periods, reasons and source references using the [frozen cases](../ci/financial-metrics-cases.json) and [rubric](../ci/financial-metrics-rubric.md).

## Independent delivery and shared files

B can run against the baseline PM-to-END graph. In `graph/setup.py`, B owns fundamentals factory injection and A owns the post-PM nodes and edges. In `graph/trading_graph.py`, B owns optional constructor injection and metric scope lifetime. A owns purchase-scenario transport and formal delivery. Preserve both changes if edits meet in `propagate()`. Neither round needs a placeholder, an import from the other feature or a prescribed merge order.

Verify B alone by pairing metrics on/off under fixed model and vendor responses. Compare the FR-03 observations/completeness, baseline decision outputs and saved analyst report structure. Use risk/formal-field sentinels to detect writes from the analyst. FR-10 introduces no observed tool site, necessity item or formal veto. When both rounds are available, repeat with fixed proposals and passing, blocked and errored risk results. Financial n/a leaves the gate decision alone. A genuine FR-03 necessary-data gap still follows SB-01. This last check applies to the combined candidate only.

The existing P07 preparation test in `test/offline/test_financial_metrics_evaluation.py` checks the absence of application migration against the working tree. If it rejects legitimate feature changes, isolate that CI issue from the product scope. Either round can propose the same reviewed fix independently: bind preparation-only assertions to the historical baseline tree, retain the current deferred-brief guard and verify a violating preparation fixture fails. Reuse that fix if already present. Preserve the trusted scorer, cases, rubric and approval checks.

## Verification and approval

1. Compare the pinned candidate delta with the baseline and record the existing test or missing assertion for each criterion. Apply the smallest missing adaptations after the specific implementation plan and tests receive approval.
2. Run the financial unit, adapter and entry tests from the project root with isolated output under `/private/tmp/tradingagents-round-04b/`. Run the preparation regressions, existing FR-03 and entry suites, then `python -m pytest -q`. Substitute external model/vendor responses while retaining the real analyst, graph and both entries. Run Ruff, schema/API/permission checks, mypy against the repository baseline, `python -m pip check` and `git diff --check`.
3. For semantic acceptance, use the trusted `financial_metrics_eval:evaluate` runner with independently installed baseline and candidate at recorded SHAs. Verify module origins and frozen material hashes. The current [semantic configuration](../ci/semantic_eval.yaml) is unapproved. The proposed authorized run uses deepseek-flash, thinking disabled, temperature 0, English output, maximum 4096 tokens, 120 seconds, one non-streaming completion per case and zero retries. Four candidate cases and two paired baselines consume at most six requests. Require dimensions 1-3 on every candidate, at least 18/20 total, zero critical failures and no paired dimension-5 regression. Unresolved ambiguous claims require human adjudication.
4. Record the actual commands, environment, candidate/test/input versions, FC mappings, skipped checks and evidence links. Plan/test approval, candidate offline acceptance, authorization for live evaluation and final review are pending. Track each separately.
