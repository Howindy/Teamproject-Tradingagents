# FR-04 D2 Architecture Contribution Fragment

Status: **personal draft / pending team review**
Related requirements: `FR-04`, `INV-07`
Implementation status: **design only**

Merge instruction: manually integrate this fragment into the team's master
`architecture-blueprint.md`. Do not replace the complete team blueprint with
this shorter contribution file.

## Placement

FR-04 extends the team's proposed shared finalization architecture. It does not
create an independent final gate.

```text
Portfolio Manager model proposal
  -> shared SafetyGate
       -> coverage and rating checks (team design)
       -> PortfolioRiskEvaluator (FR-04)
  -> immutable finalized record
  -> formal display, report, manifest, state, and memory
```

## Component responsibility

| Component | Responsibility |
|---|---|
| Entrypoint adapter | Builds validated, timestamped caller `RiskContext` |
| Candidate adapter | Normalizes applicable Buy/Overweight proposal without parsing prose as authority |
| PolicyCatalog | Supplies versioned limits |
| PortfolioRiskEvaluator | Pure arithmetic, validation, and violation codes |
| SafetyGate | Combines team safety policies and creates the effective final result |
| Finalized record | Keeps model proposal and effective result separate and immutable |
| Publisher/Memory | Consume finalized result only |

## Inputs

First-version typed inputs:

- portfolio value;
- current value of the target asset;
- proposed order value;
- entry price;
- stop-loss price;
- trade type;
- policy identifier and version;
- provenance and observation timestamp.

Required values are supplied by deterministic caller/application code. Model
reasoning and textual sizing are not authoritative numeric inputs.

## Baseline contract changes

The current baseline stores `trader_investment_plan` and `portfolio_context` as
rendered strings in graph state. FR-04 requires typed values to survive until
finalization.

The implementation must therefore introduce or retain:

- a structured Trader proposal;
- a typed candidate trade containing proposed order value or position fraction;
- a typed portfolio-risk snapshot;
- provenance and freshness metadata;
- a deterministic adapter into `PortfolioRiskEvaluator`.

Rendered Markdown remains display-only and is never authoritative input.

## Calculations

```text
projected_weight = (current_asset_value + proposed_order_value) / portfolio_value
long_stop_distance = (entry_price - stop_loss_price) / entry_price
```

Provisional limits pending team approval:

- projected weight ≤ 30%;
- long stop distance ≤ 5%.

Exact limit passes; above limit blocks. Missing, boolean, negative, non-finite,
zero-denominator, inconsistent, stale, or unsupported required input fails closed.

The projected-weight formula assumes an internal cash-funded purchase: the
proposed order consumes cash already included in `portfolio_value`. External
cash flows require a different, separately approved denominator rule.

## Result contract

Proposed result fields:

- applicability;
- policy id/version;
- normalized calculated metrics and active limits;
- `passed`, `blocked`, or `error_blocked` status;
- stable violation codes;
- original proposal reference;
- effective final rating and effective proposed order value.

Current work assumption: failed check produces `final_rating=REVIEW` and zero
effective proposed order value. The model proposal remains audit-only.

## Dependency direction

The pure evaluator depends only on its own typed domain values and standard
library arithmetic. It has no dependency on LLM, graph, CLI, network, vendor,
storage, report, memory, or UI modules. Orchestration may call the evaluator;
the evaluator never calls orchestration or external systems.

## Scope and limitations

First version supports unleveraged new-long stock Buy or Overweight proposals.
Hold, Underweight, and Sell do not create a positive new-long proposal. Shorts,
derivatives, leverage, multiple orders, execution, persistent accounting,
slippage, and guaranteed loss limits are out of scope.

## Proposed source and tests

- Proposed source: `TradingAgents/tradingagents/guardrails/portfolio_risk.py`.
- Proposed tests: pure boundary/validation tests plus shared-gate and writer-path integration tests.

Exact paths require team approval before implementation.

## Verification and observability

Every acceptance criterion maps to an offline deterministic test and a runtime
monitor. Runtime evidence records policy version, normalized metrics, active
limits, status, violation codes, and finalized-record identity.

## Change policy

Changes to formulas, supported trade types, authoritative input ownership,
thresholds, or fail-closed behavior require updates to D1, ADR-002, invariants,
traceability, tests, and human approval before merge.

## Team architecture dependency

This fragment depends on the team's proposed shared `SafetyGate`,
`FinalizedRunRecord`, `ArtifactPublisher`, and context-governance design. The
final consolidated blueprint must retain the team's AI context layering,
token-budget, compaction, permission, and publication rules.
