# ADR 002 — Deterministic Portfolio-Risk Evaluation inside SafetyGate

Status: **v0.1 — draft / pending human review**
Decision status: **proposed**
Date: 2026-10-27
Related draft requirements: `FR-04`, `INV-07`
Implementation status: **design only; no application code changed**

Merge note: this is a personal FR-04 architecture contribution. It must be
integrated into the team's ADR-001 and consolidated D2 artifacts; it must not
replace the team's complete architecture documents.

---

## 1. Context

TradingAgents v0.7.0 already contains an LLM risk debate, a structured Trader
proposal with optional entry price, stop loss, and textual sizing, a Portfolio
Manager rating, caller-supplied portfolio context, and a graph edge from the
Portfolio Manager to `END`. It does not contain a deterministic calculation that
prevents an over-concentrated or excessively wide-stop new-long advisory result
from becoming formal output.

ADR-001 proposes one shared `SafetyGate` that creates the immutable
`FinalizedRunRecord`. FR-04 must extend that authority rather than create a
second finalization path.

## 2. Decision

Add a pure `PortfolioRiskEvaluator` policy service called by the shared
`SafetyGate` before it creates `FinalizedRunRecord`.

For the first version, the evaluator covers unleveraged new-long stock Buy or
Overweight proposals. It consumes validated numeric `RiskContext`,
`CandidateTrade`, and versioned `PortfolioRiskPolicy` values. It never parses
model prose as authoritative portfolio state.

The evaluator calculates:

```text
projected_weight = (current_asset_value + proposed_order_value) / portfolio_value
long_stop_distance = (entry_price - stop_loss_price) / entry_price
```

Provisional defaults, pending team approval:

- maximum projected single-asset weight: 30%;
- maximum long stop distance: 5%.

The projected-weight denominator remains unchanged only when the purchase is
funded from cash already included in `portfolio_value`. External funding,
withdrawals, fees, and simultaneous orders require a separately approved
valuation rule.

Exact-boundary values pass. Values above an active limit block. Invalid,
inconsistent, missing, or unsupported required inputs fail closed. The current
work assumption is a non-tradeable `REVIEW` result with zero effective proposed
order value and stable violation codes. The original model proposal remains
separate audit evidence.

The evaluator performs no LLM, network, vendor, persistence, UI, or artifact
write. `SafetyGate` remains the sole authority and `ArtifactPublisher` remains
the sole formal writer.

## 3. Proposed ownership and dependency direction

| Concern | Owner |
|---|---|
| Validated caller portfolio snapshot | Entrypoint adapter / `RunContext` |
| Candidate trade normalization | Safety-gate input adapter |
| Versioned limits | `PolicyCatalog` |
| Risk arithmetic and validation | `PortfolioRiskEvaluator` |
| Final rating and gate result | Shared `SafetyGate` |
| Formal record | `FinalizedRunRecord` |
| Report, manifest, final-state, memory | `ArtifactPublisher` / `MemoryService` |

Proposed module: `TradingAgents/tradingagents/guardrails/portfolio_risk.py`.
The pure domain module depends only on standard-library types and its own data
models. Orchestration may depend on it; it must not depend on graph, CLI,
provider, storage, or model modules.

### 3.1 Required baseline contract changes

TradingAgents v0.7.0 currently renders the typed `TraderProposal` and
`PortfolioContext` into Markdown strings before finalization. FR-04 must not
recover authoritative numeric values by parsing those strings.

Implementation therefore requires:

1. retaining the structured Trader proposal, including entry and stop values;
2. adding a typed candidate-order value or position fraction;
3. retaining a typed portfolio/risk snapshot with provenance and freshness;
4. passing these typed values to the shared `SafetyGate`;
5. treating rendered Markdown as display-only output.

These are planned contract changes, not existing baseline behavior.

## 4. Options considered

### Prompt instruction only — rejected

An LLM can misunderstand or ignore a numeric boundary. Prompt text is advisory,
not a zero-tolerance authority.

### Second LLM risk judge — rejected as authority

It adds nondeterminism, latency, token cost, and another model failure path. It
may provide analysis but cannot be the final boundary.

### Parse sizing from prose with regular expressions — rejected

The existing sizing field is text and can be ambiguous. A safety boundary needs
validated numeric inputs, not fragile prose extraction.

### Independent Risk Guard after the Portfolio Manager — rejected

It duplicates ADR-001's final authority and creates disagreement or bypass risk.
The evaluator must be a policy service inside the one shared `SafetyGate`.

### Typed deterministic evaluator inside SafetyGate — proposed

This gives stable arithmetic, offline tests, explicit input ownership, and one
final record without model or vendor dependency.

## 5. Consequences

### Positive

- Risk limits are deterministic, repeatable, and testable offline.
- Model wording cannot override the result.
- Original proposal and effective final result remain distinguishable.
- FR-04 reuses the team's one finalization and publication path.
- Invalid inputs fail visibly instead of silently becoming approval.

### Negative

- New structured numeric inputs are required; current textual portfolio context
  and sizing guidance are insufficient.
- REVIEW may reduce actionable output when callers omit required values.
- Fixed defaults may over-block or under-protect outside the prototype domain.
- Graph, record, report, and memory adapters must all carry the same risk result.

## 6. Scope boundary

FR-04 does not execute orders, connect to a broker, maintain holdings, simulate
portfolio returns, guarantee realized loss, support slippage, or claim financial
suitability. It evaluates one advisory proposal against one caller-supplied
snapshot. Market gaps can exceed a planned stop; the 5% rule is not a guaranteed
loss cap.

## 7. Verification obligations

- exact 30% and 5% provisional boundaries pass;
- any representable value above an active limit blocks;
- malformed and inconsistent input fails closed;
- fixed-seed generated suite has zero unsafe approvals;
- identical inputs produce identical canonical results;
- narrative approval text cannot change the result;
- dependency sentinels observe no forbidden calls;
- every formal artifact uses the same finalized result and record hash;
- no entry point bypasses the shared gate.

All tests are planned and not started.

## 8. Open decisions

- FR04-OD-01: approve or change the 30% and 5% defaults.
- FR04-OD-02: approve numeric input ownership and provenance.
- FR04-OD-03: approve REVIEW versus a separate blocked state.
- FR04-OD-04: approve the first-version trade-type scope.

## 9. Re-decision conditions

Re-open this ADR before supporting short, derivative, leveraged, multiple-order,
or live-execution workflows; when input ownership changes; when threshold
calibration evidence becomes available; or when the shared SafetyGate contract
changes.

## 10. Status

- Decision: **proposed, not approved**.
- Thresholds: **provisional, not measured**.
- Implementation: **not started**.
- Tests and monitoring: **not started**.
