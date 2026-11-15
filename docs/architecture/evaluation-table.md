# D2 Evaluation Table

Status: **v0.3 — ADD-R round 3 draft / pending human review**
Date: 2026-11-15
Amended by: `docs/architecture/adr/003-add-r-round-3.md`
D1 basis: `docs/req/requirements.yaml` v1.24.0 — 18 requirements, 122 fit criteria
Status basis: 17 active requirements are approved as a requirement-design baseline; `QR-02` is deferred and outside current acceptance; approval does not assert implementation or measured results
Implementation status: **design only; no application code changed**

---

## 1. Evidence legend

- **M** = measured baseline evidence.
- **D** = design expectation; not implemented or measured.
- **U** = unknown or needs validation.
- **P** = provisional target; pending approval.

No numeric score is assigned. No candidate has been implemented. Only baseline observations are measured. Draft requirements are design scope, not approval.

---

## 2. Full-scope candidate comparison

| Requirement | Baseline evidence (M) | Lean A Extended (D) | Independent subsystems (D) | Event ledger (D) | Decorator (D) |
|---|---|---|---|---|---|
| `FR-01` | **M**: 3 ticker-news logical attempts; FRED/prediction rows are distinct local failures | Strong | Strong | Strong | Medium |
| `FR-02` | **M**: no native manifest; stderr 0 bytes | Strong | Medium (fragmented records) | Strong | Medium |
| `FR-03` | **M**: status mix; no unified state | Strong | Medium | Strong | Partial |
| `FR-04`/`INV-02` | **M**: no deterministic risk evaluator | Strong | Weak (second risk gate) | Strong | Weak |
| `FR-05` | **M**: no history/section manifest | Strong | Weak (second transaction) | Strong | Weak/Medium |
| `FR-06` | **M**: no recovery envelope/claim | Strong | Weak (second commit authority) | Strong | Medium |
| `FR-07` | **M**: baseline +68.6% vs filed +105.9%; no metric block | Strong (direct metrics; TTM/FCF YoY deferred) | Medium (duplicate data path risk) | Strong | Medium |
| `FR-08` | **M**: full reports to five roles; no measured saving | Strong (deterministic extraction; functional acceptance independent of CR-01) | Weak (second assembler) | Strong | Medium |
| `QR-02` | **M**: no recovery workload | Strong (D/P) | Medium | Strong (D/P) | Medium |
| `SB-01` | **M**: no coverage gate; model Hold persisted | Strong | Weak | Strong | Partial |
| `INV-01` | **M**: decision/report/full-log consistent; no binding | Strong | Weak | Strong | Weak |
| `SR-01` | **M**: partial exact scrub; no full scan | Strong | Medium | Strong | Partial |

All candidates are compared under the **same safety, gate, binding, history, recovery, and redaction contract**. A candidate that weakens those properties is not comparable and is marked weak.

### 2.1 Architecture attributes

| Attribute | Lean A Extended | Independent subsystems | Event ledger | Decorator |
|---|---|---|---|---|
| One final authority | Yes | No | Yes | Fragile |
| One publication transaction | Yes | No | Yes | Fragile |
| One context assembler | Yes | No | Yes | Fragile |
| Change surface | High | High | Medium | High |
| Complexity | High | Medium–High | Medium–High | Medium–High |
| Runtime cost | Low (D) | Low–Medium (D) | Low–Medium (D) | Low (D) |
| Token cost | No direct change (D) | No direct change (D) | No direct change (D) | No direct change (D) |
| Testability | High | Medium | High | Medium |
| Maintainability | Medium–High | Low–Medium | High | Low–Medium |
| Bypass resistance | High (D) | Low (D) | High (D) | Low–Medium (D) |
| Recovery friendliness | High (D) | Medium | High | Medium |
| Requirement coverage confidence | High (D) | Low (D) | High (D) | Medium (D) |

### 2.2 ADD-R attribute evaluation

| ADD-R attribute | Scenario | Lean A Extended tactic | Evidence status |
|---|---|---|---|
| Correctness/determinism | Same evidence/inputs produce one formal result; risk/metrics exact | Fixed clock, coverage snapshot, pure risk/metric functions, canonicalization | Design only |
| Safety | Invalid/over-limit risk never approved; gate errors fail closed | Single gate, risk branch, reason priority, no default approval | Design only |
| Auditability | Reviewer recomputes risk input/policy/metric evidence | Input artifact digest, policy digest, fact IDs, metric bundle | Design only |
| Consistency | History/recovery bind to one committed result; export deferred | Permanent publication snapshot, section manifest, read-time INV-01 | Design only |
| Recoverability | Interrupted publication completes without model/data | Recovery envelope, single-process exclusive startup guard, duplicate-start bounded retry, idempotent memory; lease/fencing/takeover/multi-worker deferred | Design only |
| Security | No secret/path escape in records; future export path/conflict if reactivated | Known-value/pattern scan, path confinement; export deferred | Design only |
| Context efficiency | Brief preserves mandatory content and obeys token budget | Mandatory reservation, ordered budget, tokenizer measurement | Design only; no saving measured |
| Performance | Manifest/recovery overhead bounded | Separate timings, paired benchmark, provisional p95 | Provisional |
| Testability | Deterministic rules are table-driven | Pure functions, decision tables, negative fixtures | Design only |
| Compatibility | Existing CLI/propagate/backtest/report/memory keep working | Adapters; graph/agents retained | Design only |

### 2.3 ADD-R candidate validation slice

Lean A, independent subsystems, event ledger, and decorator must each implement the same thin slice under identical safety requirements:

- mandatory preflight;
- coverage snapshot with a critical gap;
- stock Buy with passed risk and stock Buy with invalid/over-limit risk;
- gate block and gate error;
- terminal manifest commit and read-time INV-01;
- history retrieval; export conflict deferred;
- recovery envelope, single-process startup guard, model-free completion; multi-worker lease/fencing deferred;
- write/run secret scan;
- same-day memory reuse and a versioned decision.

Record changed files, interfaces, approximate LOC, test count, bypass findings, and time-to-green. This slice is required evidence before changing the Lean A recommendation.

### 2.4 Why Lean A Extended is recommended for review

- It preserves one final authority, one publication transaction, one context assembler, one data path, and one memory identity.
- It gives each new requirement a bounded service without appending authority to the old graph.
- Pure risk/metric functions make deterministic boundaries testable offline.
- The permanent/temporary publication split gives history and recovery a clear source of truth.
- It retains the existing graph, agents, renderer, memory substrate, and CLI.

This is a recommendation for review, not an approved decision.

---

## 2.5 Round 3 consolidation and candidate re-decision

Round 3 retains Lean A Extended. The comparison below is a design judgement, not a numeric score or measurement.

| Attribute | Lean A Extended (Round 3) | Independent subsystems | Event ledger | Decorator |
|---|---|---|---|---|
| One coordinator / one identity owner | `RunCoordinator` + `RunContext` | Fragmented | Possible | Implicit/fragile |
| One final authority | Yes | No | Yes | Fragile |
| One publication transaction | Yes | No | Yes | Fragile |
| One context assembler | Yes | No | Yes | Fragile |
| Logical components without file explosion | Yes | No (separate systems) | Possible | N/A |
| Single-process recovery honesty | Yes | Yes (but duplicate authority risk) | Yes | Medium |
| Deferred multi-worker/lease/fencing | Explicitly deferred | Often implicit | Explicit possible | Fragile |
| Envelope/digest contract clarity | Explicit | Fragmented | Strong | Weak |
| Round-based per-AC ownership | Explicit R0–R8 | Harder | Harder | Harder |
| Compatibility with current graph | High | Medium | Medium | High |
| Bypass resistance | High (D) | Low (D) | High (D) | Low–Medium (D) |

**Why Lean A Extended remains recommended:** it preserves one coordinator, one identity owner, one gate, one publisher, one data entry, one context entry, and one memory writer; it keeps the existing graph/agents/renderer/memory substrate; it matches current `FR-06` without claiming unproven lease/fencing; and it gives R0–R8 a bounded change surface. No candidate is implemented; no benefit is measured.

**Re-decision triggers added in Round 3:** logical components cannot be mapped to real symbols without duplicate authority; `RunCoordinator`/`RunContext` cannot stay policy-free; single-process recovery cannot meet `FR-06`; envelope/digest contracts cannot be serialized without cycles; multi-worker/export/TTM/FCF YoY/QR-02 is reactivated; FR-08 functional acceptance cannot be separated from CR-01.

---

## 3. Requirement coverage

| Requirement | Lean A Extended mechanism | Evidence status | Residual risk |
|---|---|---|---|
| `FR-01` | Run cache, single-flight, policy-terminal outcome cache, distinct counters | Design only | Vendor-cache retention/TTL pending (OQ-04) |
| `FR-02` | Lifecycle manifest, binding, formal decision, security, full availability records, section manifest; permanent snapshot before commit; post-commit corruption diagnostic | Design only | Overhead thresholds provisional (OQ-05); retention pending (OQ-02); snapshot staging (ARCH-OD-15) |
| `FR-03` | Critical profile, canonical state, deterministic aggregation, coverage snapshot | Design only | Profile defaults are design; tests pending |
| `FR-04` | `SafetyGate` is sole caller of pure risk validation/evaluation; caller input; provisional/approved policy snapshot; input artifact | Design only | Input source (OQ-09) blocks implementation; OQ-10 blocks approved-policy claims, not explicit provisional use |
| `FR-05` | Permanent publication snapshot, section manifest, `HistoryService`; export deferred | Design only | Index strategy (ARCH-OD-05) |
| `FR-06` | Memory plan/reservation before envelope; recovery envelope before memory; same publisher; single-process startup guard; idempotent memory; post-commit corruption | Design only | Single-process guard/retry (ARCH-OD-28); lease/fencing/takeover deferred (ARCH-OD-06/16) |
| `FR-07` | Facts/normalization through `DataAccessService`+SEC adapter; pure direct metrics; block before research debate; evidence bundle; conflict detector; TTM/FCF YoY deferred | Design only | Non-NVDA reference manifest (OQ-14) blocking; OQ-15 deferred; graph placement (ARCH-OD-19) |
| `FR-08` | Deterministic brief before five-role context; replaces four full reports; protected mandatory blocks; budget policy; token counter; audit metadata; functional acceptance independent of CR-01 | Design only | OQ-16 blocks cost/threshold claims and CR-01, not FR-08 functional behavior; replacement/marker format (ARCH-OD-17); timing interpretation (ARCH-OD-18) |
| `QR-02` | Fixed recovery workload; per-run timing; nearest-rank p95 | Design only | 2.000 s and platform matrix (OQ-13) deferred; future acceptance only |
| `SB-01` | Shared gate, trusted snapshot, review classes, model-proposal separation, risk branch | Design only | All gate/risk tests pending |
| `INV-01` | Artifact binding, canonical digests, read-time checks, permanent publication snapshot | Design only | Old-writer migration and tests pending |
| `INV-02` | Pure evaluator authority, zero unsafe approvals, cross-artifact risk evidence | Design only | Thresholds and input source blocking |
| `PR-01` | Separate startup/terminal pre-replace samples; 20 paired enabled/disabled runs; percent/absolute p95 | Design only | Provisional thresholds; benchmark not run |
| `CR-01` | Contract v2 local cost; usage/attempt rules; separate claims; blocked while prices/targets missing | Design only | Prices/targets unresolved |
| `GR-01` | Stage A freeze before first FR-07 implementation; Stage B after start | Design only | Reference manifest not frozen (OQ-14) |
| `QR-01` | Fixed replay first, then live; cache A/B fixed risk policy/input; risk-policy A/B separate | Design only | Snapshots/approval missing (D2-OD-16) |
| `SR-01` | Known-value/pattern scan, write/run scans, path confinement, preferences/logs/errors/API/stream | Design only | Full boundary/path tests pending; export deferred |
| `SR-02` | Path read/write confinement, symlink/junction, operation-time path change, platform matrix | Design only | Platform matrix pending (D2-OD-17); export deferred |

---

## 4. Benefit evaluation — separated by type

### 4.1 External requests

**Baseline measured**

- 31 tool calls.
- Repeated logical query: 3 ticker-news attempts with the same key.
- 6 FRED indicators and 2 prediction-market topics are distinct logical queries; FRED was not configured and prediction markets were withheld, so neither made an external request.
- External request count itself was not separately measured.

**Design expectation**

- Same-run duplicate `logical_query` produces one `query_execution`.
- Terminal failures are cached after retry/fallback budgets are exhausted.
- `FR-01` should reduce duplicate logical executions; external requests and vendor-cache hits are measured separately.

**Status**: not measured. An `FR-01` on/off benchmark is required.

### 4.2 Tool rounds

**Baseline measured**

- 31 tool calls; 19 LLM calls.

**Design expectation**

- `FR-01` may **not** reduce tool rounds directly: the agent can still issue a tool call and receive a cache hit.
- A faster cache hit may reduce latency but does not guarantee fewer LLM rounds.

**Status**: not measured. Do not claim tool-round reduction.

### 4.3 Token usage

**Baseline measured**

- 156,541 input tokens; 27,639 output tokens.

**Design expectation**

- `FR-01` may **not** reduce tokens directly; the cached result can still be injected into the prompt.
- Manifest, gate, risk, and metrics add negligible token cost because they are not model prompts.
- `FR-08` may reduce downstream input tokens but adds brief-generation output tokens; net effect is unmeasured.
- Context compression may reduce tokens if enabled, but it is a separate policy.

**Status**: not measured. Do not claim token reduction or brief saving before the frozen evaluation reports `accepted`.

### 4.4 Latency

**Baseline measured**

- 195.383 s total; 194.41 s inner run.

**Design expectation**

- Cache hits may reduce network wait.
- Publish/manifest/gate/risk/metrics add small overhead.
- Recovery is separate from the analysis path.
- Net latency change is unknown.

**Status**: not measured. `PR-01-FC01`–`FC04` and `QR-02` thresholds are provisional.

### 4.5 Cost

**Baseline measured**

- Token counts only; no monetary price schedule.

**Design expectation**

- `FR-01` may reduce duplicate logical executions; external-request volume depends on vendor-cache hits.
- `FR-08` net cost = added output cost - reduced input cost saving; if either price is missing, cost is null.
- No direct LLM token/cost reduction is assumed.

**Status**: monetary cost remains null until a price schedule is provided.

### 4.6 Risk quality and safety

**Baseline measured**

- Baseline persisted a Hold decision without a deterministic risk evaluation.
- No concentration, stop-distance, policy, or risk-input evidence exists.

**Design expectation**

- Applicable stock Buy/Overweight always has a passed/blocked/error risk result.
- Zero unsafe approvals; zero default approvals; zero not-applicable-as-pass.
- A block produces formal REVIEW; an evaluator error produces a failed gate path.

**Status**: design only. The zero-tolerance counters are test expectations, not measured results.

### 4.7 Recovery performance

**Baseline measured**

- No recovery workload or benchmark exists.

**Design expectation**

- 10 pending snapshots recover without model/data/graph calls under the fixed workload.
- p95 at most 2.000 s **provisional**.

**Status**: not measured. Correctness/model-free are zero-tolerance; the time target is provisional.

---

## 5. Planned measurement plan

| Measurement | Method | Status |
|---|---|---|
| Duplicate logical query executions | Mock vendor counter + baseline replay | not started |
| External requests | Instrument vendor boundary | not started |
| Vendor cache hits | Instrument vendor cache reads | not started |
| Run cache hits | Instrument run cache | not started |
| Fallback/retry attempts | Evidence counter | not started |
| Tool rounds | Callback counter | not started |
| Input/output tokens | Provider usage callback | baseline measured; new runs not measured |
| Manifest overhead | External paired timer; nearest-rank p95 | not started |
| Risk exact-boundary/over-limit/invalid | Offline fixture corpus + gate integration | not started |
| Risk artifact/policy digest | Recompute SHA-256 from stored artifacts | not started |
| Metric fixture values | Independent recomputation | requirement-evidence only; app test not started |
| Metric bundle recovery | Model-free recovery with sentinels | not started |
| History filter/order/pagination | Fixture-driven query tests | not started |
| Section isolation/tamper | Exact section set + digest plants | not started |
| Export closure/conflict (deferred) | Content/closure/byte-identical tests | deferred |
| Recovery single-process guard | Duplicate startup, bounded retry, unsupported concurrency rejection | not started |
| Multi-worker claim/fencing | Concurrent workers + stale/lost lease | deferred |
| QR-02 p95 | 30-trial fixed workload | deferred; future target provisional |
| Brief mandatory/budget | Offline budget/reference/rejection fixtures | not started |
| Brief token/cost/quality | Controlled A/B against frozen contract | blocked: snapshots/approval pending |
| Live A/B quality | `docs/req/evaluation` frozen set/rubric/contract | blocked: snapshots and human approval pending |
| Publish failure/retry | Fault injection | not started |
| Scenario matrix T-SCEN-01..18 | Normal, business block, system error, pre-commit interruption, post-commit corruption, single-process duplicate recovery, context overflow, history, cleanup-after-read, brief failure, uncommitted-memory coordination, PM proposal source, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, committed-publication corruption; multi-worker/fencing scenarios deferred | not started |
| Publication order | Assert permanent snapshot before commit; recovery envelope before memory; cleanup last | not started |
| Memory reservation | Concurrent reservations, high-water including failed, retry reuse, failed-version gap, new-run higher version | not started |
| Ledger commit projection | Commit/ledger interruption, rebuild from manifest, failed allocation preservation | not started |
| Permanent hash DAG | binding no terminal hash; no cycles; declared order; `record_hash` self-exclusion | not started |
| record_hash projection | field-level exclusion, canonical digest vs file hash, retry/risk-timestamp stability | not started |
| Recovery terminal-first | committed+verified -> idempotent without `recovery/`; conflict/corrupt typed; no overwrite | not started |
| Startup guard | Normal publisher vs recovery, duplicate start, bounded retry, unsupported concurrency rejection, lock order | not started |
| Brief replacement | Five roles get brief not full reports; other roles get full; no duplication | not started |
| Brief failure states | Disabled -> normal full input; full-report fallback only with policy permission/hard cap; final rejection terminal, no bypass | not started |
| Portfolio Manager proposal | `PortfolioManagerAdapter` terminal node; model_proposal source/fields; no Trader/risk-debater promotion | not started |
| Cleanup vs permanent reads | After cleanup, history get_run and memory binding work from permanent snapshot only; export deferred | not started |
| Uncommitted same-decision coordination | Active wait/retryable; recovery under A identity; missing snapshot/failure/conflict typed; no ownership transfer | not started |
| Lease/fencing (deferred) | Short file-lock critical section; lease expiry; LOCK_BUSY; takeover/fencing | deferred |
| Snapshot layout/SEC query | publication/recovery/guards/diagnostics layout; SEC structured query input/output contract | not started |
| Metric timing | Block exists before Bull/Bear; publication does not recompute | not started |
| Secret/path scan | Known-value/pattern/scope/path tests | not started |
| Context compression | Token-threshold fixtures | not started |

Human approval, case snapshots, and frozen reference manifests are prerequisites for behavioral acceptance. The architecture does not infer them.

A feature flag set to off means that round/capability is not implemented/enabled; it is not evidence that the requirement is satisfied. Requirement completion requires the capability enabled, its acceptance tests passing, and its evidence recorded.

Implementation blockers (risk input source, policy locator, lock format, snapshot layout, memory reservation format, SEC query contract, PM adapter, uncommitted-memory protocol, tokenizer) are distinct from acceptance-only thresholds (risk 30%/5% approval, future QR-02 target, brief budgets/quality/cost, behavior snapshots). Acceptance-only items do not block starting a module; they block completion/acceptance claims.

---

## 6. Threshold status

| Threshold | Value | Status |
|---|---|---|
| Risk policy status | Valid provisional may be used and labeled; approved requires `human_approval_ref`; missing/invalid blocks | **Provisional/approved as recorded** (OQ-10) |
| Risk max projected weight | 0.30 | **Provisional** (OQ-10) |
| Risk max stop distance | 0.05 | **Provisional** (OQ-10) |
| Risk valuation freshness window | Not fixed | **Pending** (OQ-10) |
| Risk precision rule | input <=12 dp; internal >=28 sd; exact compare; display 6 dp half-up | Design proposal |
| QR-02 nearest-rank p95 | 2.000 s over 30 trials | **Provisional/deferred** (OQ-13) |
| FR-02 manifest write p95 | 100 ms for <=256 KiB | **Provisional** (OQ-05) |
| FR-02 end-to-end overhead | p95 <=1% and <=1 s | **Provisional** (OQ-05) |
| Brief mandatory/compressible/hard cap | Versioned policy values | **Pending** (OQ-16) |
| Brief quality_loss_max | Versioned policy value | **Pending** (OQ-16) |
| Context token budgets | 128k/24k/9k/80%/95%/4k/8k/2k | **Provisional** work assumptions |

---

## 7. Candidate re-decision triggers

Re-open the architecture decision if:

1. Lean A cannot prove non-bypassable finalization without pervasive rewrites.
2. The risk evaluator cannot remain pure/shared without a second authority.
3. Recovery cannot reuse the existing publication commit.
4. History cannot verify from the permanent snapshot alone (future export must meet the same condition).
5. Publish/memory idempotency requires event-level replay.
6. Audit requirements require replayable evidence beyond the run journal.
7. Concurrency moves beyond single-user local operation.
8. D1 changes critical-source, REVIEW, risk, history, recovery, metric, or brief semantics.
9. Measured benefits do not justify the complexity.
10. The brief needs a separate context authority to meet quality thresholds.
11. Permission isolation requires stronger separation than the tool boundary.

---

## 8. Status

- Candidate implementation: **not started**.
- Candidate tests: **not started**.
- Runtime monitoring: **not implemented**.
- Baseline evidence: **measured**.
- Design expectations: **not measured**.
- D1: v1.24.0; 17 active requirements are approved as a requirement-design baseline; QR-02 is deferred; approval does not assert implementation or measured results.
- D2: v0.3 ADD-R round 3 draft; all architecture decisions proposed, not approved.
- Current recovery is single-process; lease/fencing/takeover/multi-worker/export/TTM/FCF YoY/QR-02 are deferred.
- R0–R8 and per-AC ownership are recorded in `architecture-blueprint.md` §18 and `trace-matrix.md` §3.19.
