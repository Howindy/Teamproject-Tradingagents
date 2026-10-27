# FR-04 Traceability Contribution

Status: **personal draft / pending team review**
Implementation status: **design only; tests and monitors not started**

| Acceptance | Design element | Planned test | Runtime monitor | Expected evidence | Status |
|---|---|---|---|---|---|
| `FR-04-AC1` | Typed context, candidate, policy, exact-boundary pass | `T-FR04-01` | `MON-FR04-01` | Metrics, policy version, unchanged valid rating | Not started |
| `FR-04-AC2` | Concentration breach through shared gate | `T-FR04-02` | `MON-FR04-02` | REVIEW, zero effective value, `POSITION_LIMIT_EXCEEDED` | Not started |
| `FR-04-AC3` | Stop-distance breach through shared gate | `T-FR04-03` | `MON-FR04-03` | REVIEW, zero effective value, `STOP_DISTANCE_EXCEEDED` | Not started |
| `FR-04-AC4` | Fail-closed validation and unsupported behavior | `T-FR04-04` | `MON-FR04-04` | REVIEW and stable validation code | Not started |
| `INV-07-AC1` | Fixed-seed generated safety suite | `T-INV07-01` | `MON-INV07-01` | At least 1,000 cases; unsafe approvals = 0 | Not started |
| `INV-07-AC2` | Canonical deterministic result | `T-INV07-02` | `MON-INV07-02` | 100 repeats per representative input; mismatches = 0 | Not started |
| `INV-07-AC3` | Narrative and dependency isolation | `T-INV07-03` | `MON-INV07-03` | Authority/dependency violations = 0 | Not started |
| `INV-07-AC4` | Proposal/effective separation across writers | `T-INV07-04` | `MON-INV07-04` | Cross-artifact mismatches and bypasses = 0 | Not started |

## Runtime monitor definitions

| Monitor | Signal | Failure condition | Status |
|---|---|---|---|
| `MON-FR04-01` | Recorded metrics and policy version | Missing or inconsistent evidence | Not implemented |
| `MON-FR04-02` | Concentration-limit escapes | Any violating proposal remains tradeable | Not implemented |
| `MON-FR04-03` | Stop-distance escapes | Any violating proposal remains tradeable | Not implemented |
| `MON-FR04-04` | Invalid/unsupported input handling | Any invalid input defaults to approval | Not implemented |
| `MON-INV07-01` | Unsafe approval count | Count is greater than zero | Not implemented |
| `MON-INV07-02` | Repeated-result mismatch count | Count is greater than zero | Not implemented |
| `MON-INV07-03` | Forbidden dependency or authority call | Count is greater than zero | Not implemented |
| `MON-INV07-04` | Writer mismatch or gate bypass | Count is greater than zero | Not implemented |

Proposed runtime evidence includes policy version, normalized metrics, active
limits, result status, violation codes, and finalized-record identity. No test,
monitor, threshold benefit, or implementation is claimed complete.

This fragment must be merged into the team's consolidated trace matrix.
