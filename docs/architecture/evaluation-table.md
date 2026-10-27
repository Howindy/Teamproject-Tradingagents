# D2 Evaluation Table

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` (working baseline; not finally approved)  
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
| `PR-01` | **M**: 6 FRED, 2 ticker-news, 2 prediction duplicate failed calls | Strong (D) | Strong (D) | Strong (D) |
| `QR-01` | **M**: no native manifest; stderr 0 bytes | Strong (D) | Strong (D) | Strong (D) |
| `FR-02` | **M**: status mix 20 success / 4 withheld / 6 not_configured / 4 unavailable; no unified state | Strong (D) | Strong (D) | Partial (D/U) |
| `SB-01` | **M**: no coverage gate; baseline Hold | Strong (D) | Strong (D) | Partial (D/U) |
| `INV-02` | **M**: decision/report/full-log consistent; source-status consistency not measured | Strong (D) | Strong (D) | Weak (D/U) |
| `SR-02` | **M**: partial key scrub; no full secret scan | Strong (D) | Strong (D) | Partial (D/U) |

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

### 2.2 Why Lean A is recommended for review

- It gives a non-bypassable `FinalizedRunRecord` without full event sourcing.
- It keeps `RunContext` small; policies live in testable services.
- It can cover CLI, programmatic, and backtest entry points.
- It is less fragile than C for zero-tolerance `INV-02` and `SB-01`.
- It costs less than B in schema/replay complexity.

This is a recommendation for review, not an approved decision.

---

## 3. Lean A requirement coverage

| Requirement | Lean A mechanism | Evidence status | Residual risk |
|---|---|---|---|
| `PR-01` | `DataAccessService` run cache, single-flight, terminal failure cache | Design only | Cache-key normalization and vendor-cache semantics are pending |
| `QR-01` | `ArtifactPublisher` manifest from record/evidence | Design only | Manifest overhead and retention pending |
| `FR-02` | `AvailabilityIndex` + report summary | Design only | Critical-source set and fallback contract pending |
| `SB-01` | `SafetyGate` → `FinalizedRunRecord` | Design only | REVIEW acceptance/override pending |
| `INV-02` | Publisher only consumes record; four artifacts projected | Design only | Old-writer migration must be complete |
| `SR-02` | `SecretRedactor` at all boundaries | Design only | Secret-pattern list pending |

---

## 4. Benefit evaluation — separated by type

### 4.1 External requests

**Baseline measured**

- 31 tool calls.
- Duplicate failed calls: 6 FRED, 2 ticker news, 2 prediction markets.
- External request count itself was not separately measured.

**Design expectation**

- Same-run duplicate `query_key` produces one physical request.
- Terminal failures are cached for the run.
- PR-01 should reduce duplicate external requests.

**Status**: not measured. A PR-01 on/off benchmark is required.

### 4.2 Tool rounds

**Baseline measured**

- 31 tool calls.
- 19 LLM calls.

**Design expectation**

- PR-01 may **not** reduce tool rounds directly: the agent can still issue the tool call and receive a cache hit.
- A faster cache hit may reduce latency, but does not guarantee fewer LLM rounds.

**Status**: not measured. Do not claim tool-round reduction.

### 4.3 Token usage

**Baseline measured**

- 156,541 input tokens.
- 27,639 output tokens.

**Design expectation**

- PR-01 may **not** reduce tokens directly; the cached result can still be injected into the prompt.
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

**Status**: not measured. `QR-01-AC4` overhead target is provisional.

### 4.5 Cost

**Baseline measured**

- Token counts only; no monetary price schedule.

**Design expectation**

- PR-01 may reduce external request volume.
- No direct LLM token reduction is assumed.

**Status**: monetary cost remains `null` until a price schedule is provided.

---

## 5. Planned measurement plan

| Measurement | Method | Status |
|---|---|---|
| Duplicate external requests | Mock vendor counter + baseline replay | not started |
| Physical requests | Instrument vendor boundary | not started |
| Vendor cache hits | Instrument vendor cache reads | not started |
| Run cache hits | Instrument run cache | not started |
| Fallback attempts | Evidence counter | not started |
| Retry attempts | Evidence counter | not started |
| Tool rounds | Callback counter | not started |
| Input/output tokens | Provider usage callback | baseline measured; new runs not measured |
| Manifest overhead | Monotonic timer around publish | not started |
| Publish failure/retry | Fault injection | not started |
| Secret scan | Documented pattern scan | not started |
| Context compression | Token-threshold fixtures | not started |

---

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
- D1: **not modified**.
