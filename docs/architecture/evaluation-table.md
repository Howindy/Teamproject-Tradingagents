# D2 Evaluation Table

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` v1.9.0 (historical baseline approved; current revision human review pending; IDs renumbered)
Implementation status: **design only; no application code changed**

---

## 1. Evidence legend

- **M** = measured baseline evidence.
- **D** = design expectation; not implemented or measured.
- **U** = unknown or needs validation.
- **P** = provisional target; pending approval.

No numeric score is assigned. No candidate has been implemented. Only baseline observations are measured.

---

## 2. Candidate comparison

| Requirement | Baseline evidence (M) | Lean A | B: Event Ledger | C: Decorator |
|---|---|---|---|---|
| `FR-01` | **M**: 3 ticker-news logical attempts; 6 FRED indicators and 2 prediction topics were distinct local failures | Strong (D) | Strong (D) | Strong (D) |
| `FR-02` | **M**: no native manifest; stderr 0 bytes | Strong (D) | Strong (D) | Strong (D) |
| `FR-03` | **M**: status mix 20 success / 4 withheld / 6 not_configured / 4 unavailable; no unified state or effective critical profile | Strong (D) | Strong (D) | Partial (D/U) |
| `SB-01` | **M**: no coverage gate; baseline persisted the model's Hold text as the formal decision while critical sources were unavailable | Strong (D) | Strong (D) | Partial (D/U) |
| `INV-01` | **M**: decision/report/full-log consistent; no run binding, source-status, fallback, or memory consistency measured | Strong (D) | Strong (D) | Weak (D/U) |
| `SR-01` | **M**: partial exact-value scrub in provider errors; no known-value or pattern scan across records; preferences can store full backend_url | Strong (D) | Strong (D) | Partial (D/U) |

### 2.1 Architecture attributes

| Attribute | Lean A | B: Event Ledger | C: Decorator |
|---|---|---|---|
| Change surface | High | Medium | Low–Medium |
| Complexity | High | Medium–High | Low |
| Runtime cost | Low (D) | Low–Medium (D) | Low (D) |
| Token cost | No direct change (D) | No direct change (D) | No direct change (D) |
| Testability | High | High | Medium |
| Maintainability | Medium | High | Low |
| Bypass resistance | High (D) | High (D) | Low (D/U) |
| Checkpoint friendliness | Medium–High | High | Medium |
| Requirement coverage confidence | High (D) | High (D) | Low–Medium (D/U) |

### 2.2 ADD attribute evaluation

| ADD attribute | Scenario | Lean A tactic | Evidence status |
|---|---|---|---|
| Correctness | Same evidence and inputs produce one formal result | Fixed run clock, critical profile, coverage snapshot, deterministic gate | Design only |
| Auditability | Reviewer reconstructs a blocked or approved decision | decision_id, artifact_binding, provenance_digest, gate input_hash | Design only |
| Security | Secret is blocked before any app-controlled record | known-value + versioned pattern checks, write/run scan, fail-closed | Design only |
| Consistency | Four artifacts bind to one formal decision | artifact_binding, INV-01 checkpoint, memory entry hash scope | Design only |
| Performance | Manifest and gate do not dominate latency | startup manifest, terminal write, external paired benchmark | Provisional threshold |
| Testability | Zero-tolerance rules are table-driven | availability/gate decision tables, schema negative fixtures | Design only |

### 2.3 Candidate validation slice

Lean A, B, and C must each implement the same thin slice under identical safety requirements: mandatory preflight, coverage snapshot with a gap, gate block, failure record, terminal commit + INV-01 read-back, secret scan, and same-day memory reuse/version. Record changed files, interfaces, LOC, tests, bypass findings, and time-to-green. This slice is the required evidence before changing the Lean A recommendation.

### 2.4 Why Lean A is recommended for review

- It gives a non-bypassable `FinalizedRunRecord` without full event sourcing.
- It keeps `RunContext` small; policies live in testable services.
- It can cover CLI, programmatic, and backtest entry points.
- It is less fragile than C for zero-tolerance `INV-01` and `SB-01`.
- It costs less than B in schema/replay complexity.

This is a recommendation for review, not an approved decision.

---

## 3. Lean A requirement coverage

| Requirement | Lean A mechanism | Evidence status | Residual risk |
|---|---|---|---|
| `FR-01` | `DataAccessService` run cache, single-flight, policy-terminal outcome cache | Design only | Vendor-cache retention policy is pending; run-cache semantics are defined in D1 v1.9.0 |
| `FR-02` | `ArtifactPublisher` lifecycle manifest with binding, formal decision, security, and full availability records | Design only | Manifest overhead provisional; retention pending; schema synchronized in D1 v1.9.0 |
| `FR-03` | `AvailabilityIndex` + canonical state + report summary | Design only | Effective profile, fallback contract, and component_missing records defined in D1 v1.9.0; implementation and tests pending |
| `SB-01` | `SafetyGate` → `FinalizedRunRecord` | Design only | Gate contract and REVIEW policy defined in D1 v1.9.0; implementation and tests pending |
| `INV-01` | Publisher only consumes record; current artifacts bound by artifact_binding plus memory reference | Design only | Binding, canonicalization, hash-input, and memory lifecycle contracts defined in D1 v1.9.0; old-writer migration and tests pending |
| `SR-01` | `SecretRedactor` at all app-controlled boundaries | Design only | Known-value/pattern/scope/incident contract defined in D1 v1.9.0; implementation and tests pending |

---

## 4. Benefit evaluation — separated by type

### 4.1 External requests

**Baseline measured**

- 31 tool calls.
- Repeated logical query: 3 ticker-news attempts with the same key.
- The 6 FRED indicators and 2 prediction-market topics are distinct logical queries; FRED was not configured and prediction markets were withheld, so neither made an external request.
- External request count itself was not separately measured.

**Design expectation**

- Same-run duplicate `logical_query` produces one `query_execution`.
- Terminal failures are cached for the run after retry and fallback budgets are exhausted.
- FR-01 should reduce duplicate logical query executions; external requests and vendor-cache hits are measured separately.

**Status**: not measured. A FR-01 on/off benchmark is required.

### 4.2 Tool rounds

**Baseline measured**

- 31 tool calls.
- 19 LLM calls.

**Design expectation**

- FR-01 may **not** reduce tool rounds directly: the agent can still issue the tool call and receive a cache hit.
- A faster cache hit may reduce latency, but does not guarantee fewer LLM rounds.

**Status**: not measured. Do not claim tool-round reduction.

### 4.3 Token usage

**Baseline measured**

- 156,541 input tokens.
- 27,639 output tokens.

**Design expectation**

- FR-01 may **not** reduce tokens directly; the cached result can still be injected into the prompt.
- Manifest and gate add negligible token cost because they are not model prompts.
- Context compression may reduce tokens if enabled, but it is a separate policy.

**Status**: not measured. Do not claim token reduction.

### 4.4 Latency

**Baseline measured**

- 195.383s total; 194.41s inner run.

**Design expectation**

- Cache hits may reduce network wait.
- Publish/manifest/gate add small overhead.
- Net latency change is unknown.

**Status**: not measured. `FR-02-AC8` manifest-write and end-to-end overhead targets are provisional.

### 4.5 Cost

**Baseline measured**

- Token counts only; no monetary price schedule.

**Design expectation**

- FR-01 may reduce duplicate logical query executions; external-request volume also depends on vendor-cache hits.
- No direct LLM token reduction is assumed.

**Status**: monetary cost remains `null` until a price schedule is provided.

---

## 5. Planned measurement plan

| Measurement | Method | Status |
|---|---|---|
| Duplicate logical query executions | Mock vendor counter + baseline replay | not started |
| External requests | Instrument vendor boundary | not started |
| Vendor cache hits | Instrument vendor cache reads | not started |
| Run cache hits | Instrument run cache | not started |
| Fallback attempts | Evidence counter | not started |
| Retry attempts | Evidence counter | not started |
| Tool rounds | Callback counter | not started |
| Input/output tokens | Provider usage callback | baseline measured; new runs not measured |
| Manifest overhead | External paired timer around publish; nearest-rank p95 | not started |
| Live A/B quality | Frozen `docs/req/evaluation/eval-set-v1.json`, `rubric-v1.json`, `behavior-eval-contract-v1.json`; deterministic gate regression zero-tolerance; live mean drop ≤0.5, per-case drop ≤1.0, live REVIEW-rate increase ≤10pp | blocked: snapshots pending capture; human review pending |
| Publish failure/retry | Fault injection | not started |
| Secret scan | Documented pattern scan | not started |
| Context compression | Token-threshold fixtures | not started |

---

Behavior acceptance is blocked until every case snapshot is captured and the behavior contract is human-approved. The contract file records `acceptance_status = blocked_until_snapshots_and_human_approval`.

## 6. Candidate re-decision triggers

Re-open the architecture decision if:

1. Lean A cannot prove non-bypassable finalization without pervasive rewrites.
2. Publish/memory idempotency requires event-level replay.
3. Audit requirements require replayable evidence beyond the run journal.
4. Concurrency moves beyond single-user local operation.
5. D1 changes critical-source, REVIEW, or cross-run cache semantics.
6. Measured benefits do not justify Lean A complexity.
7. Context compression needs deterministic event-level reconstruction.
8. Permission isolation requires stronger separation than the tool boundary.

---

## 7. Status

- Candidate implementation: **not started**.
- Candidate tests: **not started**.
- Runtime monitoring: **not implemented**.
- Baseline evidence: **measured**.
- Design expectations: **not measured**.
- D1: **v1.9.0 historical baseline approved; current revision human review pending; FR-01, FR-02, FR-03, SB-01, INV-01, and SR-01 contracts synchronized**.
