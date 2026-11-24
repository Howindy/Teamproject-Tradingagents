# FR-10 runtime integration and Round 4 boundary

Implemented against `main @ 5718bac` (merged Round 3). This is the FR-10 branch's
handoff contract, not an assertion of Round 4 implementation or teammate approval.

## Runtime interface

- `FinancialDataProvider.fetch(ticker, as_of) -> FinancialInputs` is the replaceable
  data boundary. SEC and completed-close adapters are the current implementation.
- `build_metrics_factory(config, data_factory=...)` constructs the callable resolver.
  `resolver(state) -> FinancialMetricResult` supplies rendered analyst evidence.
- `TradingAgentsGraph(..., metrics_factory=resolver)` allows explicit injection.
  Normal CLI runs construct the resolver from configuration automatically.
- `create_fundamentals_analyst(llm, metrics_factory=None)` adds the table before the
  first model turn and reuses it during tool turns and wrap-up. The five original
  tools, report return shape, and full-report saving remain intact.
- `MetricProviderFactory.analysis_scope()` owns analysis-local reuse. `propagate()`
  enters it beside the existing FR-03 `RunContext`; `stream_run()` enters it in the
  copied execution context and closes it with the stream. The existing CLI therefore
  needs no modification. A caller-supplied plain resolver may own its own lifecycle.

## Ownership alongside Round 4

| Responsibility | Owner / agreement for this integration |
|---|---|
| Data observations and completeness | Existing FR-03 registry and summarizer; FR-10 adds no observed tool site, target or completeness item |
| Financial calculations | FR-10 financials modules; program values take priority only for the same metric and period |
| Purchase scenario and portfolio-risk result | FR-04 / Round 4; FR-10 never calculates, writes or substitutes them |
| Formal rating, decision, gate status and reasons | SB-01 / Round 4; FR-10 supplies no veto or formal-result field |
| Final delivery, state/report/memory consistency | INV-01 / Round 4; FR-10 preserves the analyst's existing report output |
| Run binding and graph state schema | Existing FR-03 contract; no FR-10 cache/provider/lock/bundle is added to serialized state |

Shared source files are `graph/setup.py` and `graph/trading_graph.py`. Round 4 may
extend their node/edge and final-delivery logic while retaining the optional
`metrics_factory` argument and the financial metric scope. FR-10 adds no node or
edge. There is no change to `src/cli/run.py`, `run_context.py`, AgentState, final
recommendation, risk evaluation or report writers. Future concurrent edits can
still produce textual merge conflicts; these ownership boundaries guide resolution.

## Enable in the normal CLI

From this worktree with its existing Python environment installed:

```powershell
$env:TRADINGAGENTS_FR10_SEC_ENABLED = 'true'
& 'C:\Users\24968\AppData\Local\Temp\opencode\financial-metrics-feature\venv\Scripts\python.exe' -m cli.main
```

Select ticker, date and analysts interactively, including Fundamentals. Both
`fr10_sec_enabled` and `fr10_reference_root` default to off/empty. For a supported
local reference snapshot, set `TRADINGAGENTS_FR10_REFERENCE_ROOT` instead of SEC.
Do not enable SEC for an offline run. Enabling SEC may make network requests;
normal model credentials and provider settings remain the caller's responsibility.

Historical personal-branch `fr07_*` activation names are not used here; current
FR-07 is the separate summary feature. The historical formula version
`fr07-direct-v1` remains unchanged for provenance.

## Verification and limits

Offline integration exercises the real analyst, actual graph, programmatic entry,
CLI entry, repeated runs, early stream close, interleaved streams and exception
cleanup. Only external model/vendor responses are substituted. Paired tests compare
FR-03 availability and existing decision outputs with metrics enabled/disabled.
Risk and final-result sentinels are unchanged by the analyst.

This does not establish live model quality or complete Round 4 acceptance. No live
request was made for this integration. The price freshness policy remains limited
to a matching preceding regular weekday; holiday/data-gap cases may return n/a.
CI configuration has not been disabled or modified.
