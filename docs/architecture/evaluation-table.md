# FR-04 Architecture Evaluation Fragment

Status: **personal draft / pending team review**
Implementation status: **design only; no candidate has been implemented**
Evidence basis: **TradingAgents v0.7.0 source inspection and team D1/D2 draft**

## Evaluator options

| Candidate | Determinism | Bypass resistance | Offline testability | Cost/latency | Decision |
|---|---|---|---|---|---|
| Prompt instruction only | Weak | Weak | Low | No code cost | Rejected as authority |
| Second LLM risk judge | Weak | Medium | Low | Adds model cost/latency | Rejected as authority |
| Regular-expression parsing of prose | Medium/unknown | Low | Medium | Low runtime cost | Rejected for safety boundary |
| Independent post-manager gate | Strong | Medium | High | Low runtime cost | Rejected because it duplicates team authority |
| Typed pure evaluator inside shared SafetyGate | Strong | Strong | High | Low runtime cost | Proposed |

## Provisional threshold comparison

| Candidate | Maximum weight | Maximum stop distance | Benefit | Cost | Status |
|---|---:|---:|---|---|---|
| Conservative | 20% | 3% | Stronger restriction | High false-block risk | Not selected |
| Classroom prototype | 30% | 5% | Clear boundaries and meaningful demonstration | Not calibrated for every user/asset | Proposed, not approved |
| Permissive | 40% | 10% | Fewer blocks | Weaker safety demonstration | Not selected |

No candidate or threshold has been implemented, measured, or empirically
calibrated. The proposed values are configurable classroom defaults, not
financial advice or guaranteed loss limits.

## Baseline integration impact

| Baseline fact | Required FR-04 change | Reason |
|---|---|---|
| `TraderProposal` is typed before rendering | Retain the typed proposal through finalization | Entry and stop values must not be recovered from prose |
| Position sizing is textual | Add a validated numeric order value or position fraction | Projected weight requires an authoritative numerator |
| `PortfolioContext` is rendered to text in graph state | Retain a typed risk snapshot with provenance and freshness | The denominator and current holding must be validated |
| Portfolio Manager connects to `END` | Route finalization through the team's shared `SafetyGate` | All formal paths must be non-bypassable |
| Formal outputs currently consume model-produced decisions | Publish one immutable finalized record | Proposal and effective result must remain distinguishable |

These are planned integration changes. They do not describe behavior already
implemented in the baseline repository.
