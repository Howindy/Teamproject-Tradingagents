# FR-04 Invariant Contribution

Status: **personal draft / pending team review**
Implementation status: **design only; no application code changed**

All items are zero-tolerance. A single violation fails the related invariant.

| ID | Invariant | Source requirement | Enforcement | Verification | Operational fallback | Status |
|---|---|---|---|---|---|---|
| FR04-INV-01 | Every applicable effective Buy or Overweight result passes the evaluator through the shared gate. | `FR-04`, `INV-07` | Entry adapters and `SafetyGate` | Entry-point bypass matrix | Refuse finalization; produce REVIEW; publish no tradeable result | Design only |
| FR04-INV-02 | A risk-limit breach or invalid required input never becomes tradeable. | `FR-04`, `INV-07` | `PortfolioRiskEvaluator` and `SafetyGate` | Boundary, malformed-input, and generated tests | REVIEW; zero effective proposed value; stable reason code | Design only |
| FR04-INV-07 | Model text cannot change the deterministic risk result. | `INV-07` | Typed input authority | Narrative-injection test | Ignore prose; block if authoritative numeric input is unavailable | Design only |
| FR04-INV-04 | Evaluation performs no LLM, network, vendor, persistence, UI, or artifact call. | `INV-07` | Module dependency boundary | Import audit and call sentinels | Fail the check and block finalization | Design only |
| FR04-INV-05 | Model proposal and effective result remain separate and consistent across formal artifacts. | `INV-07` | `FinalizedRunRecord` and formal writers | Mutation, bypass, and cross-artifact tests | Block publication and require human review | Design only |
| FR04-INV-06 | Authoritative numeric values remain typed through finalization and are never reconstructed from rendered Markdown. | `FR-04`, `INV-07` | State schema and gate input adapter | Typed-state contract and prose-confusion tests | Reject the input; produce REVIEW; report `UNTRUSTED_NUMERIC_SOURCE` | Design only |

Changing or weakening an invariant requires requirement, ADR, trace, test, and
human-review updates before implementation or merge.

This fragment must be merged into the team's consolidated invariant register;
it must not replace the team's existing invariants.
