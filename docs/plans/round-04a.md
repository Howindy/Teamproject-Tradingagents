# Round-04A | Integrate purchase risk and the formal recommendation

**Planning draft v5, 2026-11-25.** Baseline `5718bacff6cafb9412a805878fe82e97f279a8bc` includes Round 3. D1 version 1.50.0 defines the acceptance criteria. The [architecture blueprint](../../architecture-blueprint.md), [ADR 001](../architecture/adr/001-graph-internal-final-check.md) and [verification constraints](../code-governance/verification-constraints.md) govern the integration. Implementation, test approval and final acceptance are pending.

## Scope and existing evidence

Deliver five outstanding criteria by connecting the existing evaluators to the graph and its consumers. Eight core criteria already have implementations and offline tests. Rerun those suites on the candidate and retain their assertions. The following mapping distinguishes the work needed for each criterion.

| Criteria | Existing evidence on the baseline | Round-04A work |
|---|---|---|
| FR-04-FC01, FR-04-FC02 | `portfolio_risk.evaluate` handles equality, exact comparisons and simultaneous breaches. Risk tests R01-01 through R01-05 exercise boundaries and display rounding. | Regression only |
| FR-04-FC03, FR-04-FC04 | R01-06 through R01-15 cover input validation, explicit invalid thresholds, independently nullable metrics, applicability, model-text isolation and evaluator errors. | Regression only |
| SB-01-FC01, SB-01-FC02 | `final_recommendation.evaluate` preserves valid proposals and consumes the supplied FR-03 summary. R02-01, 03, 04, 05, 06, 07 and 09 cover these decisions. | Regression only |
| SB-01-FC03, SB-01-FC04 | R02-02, 03, 07 through 11 cover risk status, invalid proposals, contradictory summaries, ordinary blocks, internal errors and the prohibition on recomputing risk. | Regression only |
| FR-04-FC05 | Both entries already create a fresh run. The baseline graph ends at the Portfolio Manager (PM). | Carry the caller's scenario into the graph, invoke risk once and deliver its result through both entries and reports. |
| SB-01-FC05, INV-01-FC01 | The PM currently writes the final fields. Consumers can fall back to parsing text. | Make SB-01 the sole formal authority and verify the same rating and decision across actual outputs. Use one integration fixture for both criteria. |
| INV-01-FC02, INV-01-FC03 | Decision append, duplicate suppression, settlement and reflection already exist. | Pass the checked rating and body into the existing write path. Verify conditional append and compare the original decision before and after settlement. |

The core suites are [FR-04 risk](../../test/offline/test_fr04_risk.py) and [SB-01 final check](../../test/offline/test_sb01_final_check.py). This review uses source and test evidence. Candidate verification is a separate step.

## Implementation sequence and ownership

1. **Acquire the scenario.** Use the reviewed OQ-01 contract below. Add optional `--purchase-scenario <json-file>` to `src/cli/main.py` and an optional keyword-only `purchase_scenario=None` to `TradingAgentsGraph.propagate`. Carry the CLI input through the existing flags mapping in `src/cli/run.py`. Preserve positional callers and the programmatic return shape `(final_state, signal)`. A missing option supplies no scenario. An explicitly unreadable file or malformed JSON is an entry error before analysis starts. Parsed but business-invalid data reaches the risk core, which decides applicability and status.
2. **Build the initial state.** In `src/tradingagents/graph/trading_graph.py` and `src/tradingagents/agents/state.py`, carry the current ticker, scenario and supplied threshold keys as JSON-compatible values. Parse decimal JSON tokens without a binary-float intermediate. Preserve the distinction between an omitted threshold and an explicitly invalid value. The core owns the classroom defaults for `max_projected_weight` (0.30) and `max_stop_distance` (0.05). Holdings, model text and vendor data cannot supply missing scenario fields.
3. **Connect the two existing decisions.** In `src/tradingagents/agents/managers/portfolio_manager.py`, emit the advisory `model_proposal` with rating and text. In `src/tradingagents/graph/setup.py`, route PM → Portfolio Risk Check → Final Recommendation Check → END. The risk node obtains a fresh check-time snapshot from the existing FR-03 producer and calls IF-08, `evaluate(analysis_ticker, proposal, scenario, thresholds, asset_type)`. Publish the summary and `portfolio_risk_result`. The final node calls IF-09, `evaluate(proposal, availability, risk, asset_type)`, exactly once. Keep the research-start and terminal snapshots at their existing stages. A late terminal observation cannot rerun either decision.
4. **Validate delivery.** Add a small IF-19 structural validator in `src/tradingagents/final_recommendation.py`, outside the existing evaluator. Require all five fields. The proposal is null or an object with rating and text, each string or null. A passed gate carries a legal five-tier rating. A blocked or error gate carries REVIEW. The decision is nonblank text. Reasons are a string list with at least one substantive reason on blocked/error. An illegal proposal rating can coexist with a valid blocked result. A malformed formal result is an execution error before normal return, display or save. Consumers must never repair it by parsing the proposal or manufacturing REVIEW.
5. **Project the validated values.** Update formal consumers in `src/tradingagents/agents/rating.py`, `src/cli/display.py`, the entry adapters and `src/tradingagents/reporting.py`. Label streamed debate and the PM proposal as intermediate, including section files written while streaming. Show the checked rating and body in the formal area. Render the same risk status, safe inputs, available metrics, thresholds and reasons in CLI, Markdown and HTML. State that the classroom checks apply only to the supplied scenario and do not authorize a trade. Independent report saving reads the passed state. Save the existing state projection before conditional memory append. Preserve the original failure on each save path.

These named application files bound the proposed changes. Keep `src/tradingagents/portfolio_risk.py` and both existing evaluator bodies as regression subjects. Investigate a demonstrated core defect separately. Use the existing memory and report machinery wherever it already satisfies the contract.

## Independent implementation and CI compatibility

Start from the pinned baseline with FR-10 absent. The only shared application files are `graph/setup.py` and `graph/trading_graph.py` under `src/tradingagents/`. A owns post-PM edges, scenario transport and formal delivery. If B is present, preserve its optional graph constructor resolver, fundamentals analyst factory and metric scope in invoke/stream. A requires no financials import, configuration, placeholder or result. A alone owns CLI scenario changes.

Limit the OQ-01 API gate change to the matching one-parameter update in `scripts/ci_checks.py` and its API regression in `test/offline/test_ci_gates.py`. Keep checks for omitted/reordered old parameters and unexpected additions. OQ-04 verifies the existing save interaction. OQ-08 verifies sufficient graph depth. OQ-07 concerns effective file permissions.

One baseline test, P07 in `test/offline/test_financial_metrics_evaluation.py`, assumes the preparation PR has no application diff against moving main. This can fail on either feature branch. Treat it as a separate test-maintenance issue if reproduced. The proposed common correction checks the preparation-only conditions against the pinned historical tree above and retains the current deferred-brief check. Verify a violating preparation fixture is rejected. Either round can carry the same reviewed correction independently or reuse it if already present. It is outside the product increment and confers no permission to relax CI or scoring.

## OQ-01 decision and entry test specification

OQ-01 technical review is complete for this revision. Both entries accept one flat purchase-scenario object. It uses the existing IF-08 scenario field names and two optional top-level keys, `max_projected_weight` and `max_stop_distance`. At the risk boundary, pass those two keys in the IF-08 thresholds mapping only when present, preserving their values, including null. Pass the remaining scenario fields as the scenario argument. This uses one CLI option and one optional programmatic keyword and leaves threshold validation and defaults with the risk evaluator.

Use this JSON as the contents of `purchase.json`. In the programmatic example, `payload` is the mapping obtained by decoding the same file.

```json
{
  "ticker": "AAPL",
  "currency": "USD",
  "portfolio_value": 100000,
  "current_position_value": 0,
  "proposed_buy_value": 30000,
  "entry_price": 100,
  "stop_loss_price": 95
}
```

- CLI invocation: `tradingagents --ticker AAPL --date 2025-01-15 --purchase-scenario purchase.json`.
- Programmatic invocation: `graph.propagate("AAPL", "2025-01-15", purchase_scenario=payload)`.

For FR-04-FC05, SB-01-FC05 and IR-14, use a stock Buy proposal and a sufficient FR-03 summary. Apply each variation to both entries. Compare the structured risk result and formal outcome. With these operands, the risk result must retain `projected_weight="0.3"` and `stop_distance="0.05"` in every row below.

| Variation from the shared sample | Expected result through both entries |
|---|---|
| Neither threshold key is present | The core reports thresholds `{"max_projected_weight":"0.3","max_stop_distance":"0.05"}`. Equality passes both checks. The formal rating is Buy. |
| Add only `"max_projected_weight": "0.25"` | The core reports the supplied weight limit and the default stop limit. Projected weight exceeds 0.25. Risk and gate are blocked and the formal rating is REVIEW. |
| Add only `"max_projected_weight": null` | Input acquisition succeeds. Risk is blocked. Its threshold map contains only `{"max_stop_distance":"0.05"}`. Reasons identify the invalid weight limit and the need for manual review. The gate is blocked and the formal rating is REVIEW. |
| Add only `"max_stop_distance": 1` | Input acquisition succeeds. Risk is blocked. Its threshold map contains only `{"max_projected_weight":"0.3"}`. Reasons identify the out-of-range stop limit and the need for manual review. The gate is blocked and the formal rating is REVIEW. |

With the option or keyword omitted entirely, the applicable Buy reaches FR-04 with a missing scenario and yields a structured block. An explicitly unreadable CLI file or malformed JSON fails before analysis starts. For the precision variant below, use the literal JSON token `30000.0000000001` and the equivalent exact decimal string in the programmatic mapping.

## Acceptance on the candidate

Use real entries, graph, evaluators, registry, writers and memory with controlled external model/vendor responses. New test locations are `test/offline/test_round04a_integration.py` and `test/offline/test_formal_result_contract.py`. Reuse existing rating, graph, reporting and memory tests where they already assert the behavior.

| Boundary | Controlled input and expected observation |
|---|---|
| Both entries and IR-14 | AAPL stock Buy, portfolio 100000, position 0, purchase 30000, entry 100, stop 95, USD. Both metrics equal their limits and pass. Raise the purchase to 30000.0000000001 and expect a block even if the display rounds to 30%. Exercise omitted scenario, invalid explicit limit and evaluator exception. Check actual risk sections and manual-review reasons. |
| Formal authority and IR-01/02/04 | Use distinct proposal and formal-notice markers. For a pass preserve the original conclusion including whitespace. For an applicable risk block/error expect gate blocked and REVIEW. Only an internal SB-01 failure yields gate error. Compare signal, CLI formal area, final state, saved JSON, Markdown and HTML. Count one execution of each evaluator and guard formal consumers against text parsing. |
| Contract failure and IR-03 | Drop a field during stream merge, use a blank decision, an illegal gate/rating pair or empty blocked reasons. Expect an execution error before normal delivery. A legitimate business REVIEW remains deliverable. |
| Memory and IR-04/07 | Inspect a new passed record and a new REVIEW record. Disabled memory and an existing ticker/date produce no forced append. After settlement/reflection, rating and body match the original record while outcome/reflection may change. A state-save failure prevents append. Save failures preserve the formal result and original exception. |
| Run isolation and IR-05/13 | Change the terminal summary after checking. The report shows terminal availability and the original formal decision. Save run A after run B and inspect A's fields. With checkpointing configured, both entries execute fresh and leave old checkpoint data intact. |
| After both merges only | Hold external responses and the proposal fixed. Toggle FR-10 and exercise risk pass/block/error. An unavailable metric adds no veto. Both post-PM nodes still execute once. |

Run the two existing core suites, the two targeted integration/contract suites and then `python -m pytest -q` from the repository root. Use isolated test outputs under `/private/tmp/tradingagents-round-04a/`. Run Ruff, the repository schema/API/permission and mypy-baseline checks, `python -m pip check`, and `git diff --check`. Review applicable PR gates and the actual classification of any prompt change. Record candidate SHA, environment, commands, FC/IR mappings, failures and skips. The default pytest selection excludes live integration.

## Approval records before implementation

1. Record the revised specification commit and an eligible reviewer's test-spec pre-approval using the repository's `APPROVED test-spec:` convention. Identify the test files, FC/IR mappings and expected assertions, including the dual-entry cases above. The previous freeze at `b1b9821` predates this payload decision.
2. Record the ADR 001 safety-critical implementation approval for the same revision and scope, covering the entry contract, post-PM checks and formal delivery. Attach the reviewer, approval reference and timestamp for each approval. The OQ-01 technical decision above settles the payload design; the two approval records are pending.

When implementation starts, record its first commit so reviewers can verify approval order. Completion requires current regression evidence for the eight existing core criteria and production-path evidence for the five outstanding criteria.
