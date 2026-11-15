# ADR 001 — Run Governance Architecture: Lean A Extended

Status: **v0.2 — amended by ADR 003 (ADD-R round 3)**
Decision status: **proposed**
Amendment note: ADR 003 introduces `RunCoordinator`, keeps `RunContext` to identity/clock/versions/paths/dependencies, treats components as logical responsibilities, and replaces current lease/fencing/takeover/multi-worker recovery with a single-process startup guard. TTM/FCF YoY/export remain deferred. ADR 001 remains the historical Lean A decision; where it says lease/fencing is current, ADR 003 governs the current scope.
Date: 2026-11-11
D1 basis: `docs/req/requirements.yaml` v1.24.0 — 18 requirements, 122 fit criteria
Status basis: 17 active requirements are approved as a requirement-design baseline; `QR-02` is deferred and outside current acceptance; approval does not assert implementation or measured results
Supersedes: ADR 001 v0.1 (D1 v1.9.0, 6 requirements)
Implementation status: **design only; no application code changed**

---

## 1. Context

The baseline establishes only the original TradingAgents behavior:

- 195.383 s end-to-end, 19 LLM calls, 31 tool calls.
- 156,541 input tokens, 27,639 output tokens.
- Three ticker-news logical attempts with the same key; 6 FRED indicators and 2 prediction-market topics were distinct local failures.
- 20 success, 4 withheld, 6 not_configured, 4 unavailable data-status rows.
- No native lifecycle manifest, no unified coverage state, no coverage-aware safety gate, no deterministic portfolio-risk check, no history/recovery interface, no structured metric block, and no bounded downstream brief.
- The baseline decision/report/full-state were consistent, but source-status consistency, risk evidence, and memory binding were not measured.

D1 v1.18.0 marks all requirements draft; the v1.14.1 additions did not remove the original six:

- `FR-04`/`INV-02`: deterministic portfolio risk inside the finalization gate.
- `FR-05`: historical retrieval of committed publications.
- `FR-06`: model-free startup recovery of pending publication.
- `QR-02`: bounded recovery performance.
- `FR-07`: deterministic derived financial metrics.
- `FR-08`: bounded downstream brief with canonical mandatory content.

The architecture must satisfy all of them without creating a second final authority, a second publication transaction, a second data path, a second memory identity, or a second context assembler.

---

## 2. Decision

Retain **Lean A** and extend it with bounded capability services:

- `RunContext` owns lifecycle, run identity, fixed clock, paths, and dependency wiring only.
- Business rules live in separate services: `DataAccessService`, `AvailabilityIndex`, `RunEvidenceStore`, `SafetyGate`, `ArtifactPublisher`, `MemoryService`, `SecretRedactor`, `CheckpointCoordinator`, and the new risk/publication/finance/brief services.
- `AvailabilityIndex` produces the only critical profile and coverage snapshot.
- The original terminal Portfolio Manager remains and is wrapped by `PortfolioManagerAdapter`; it consumes full reports, plans, risk debate, and past memory, and produces the unapproved `ModelProposal` with `source=portfolio_manager`. Trader/risk-debater output is never promoted to the final model proposal.
- `SafetyGate` is the only formal decision authority and the **only caller** of `RiskInputValidator`, `RiskPolicyResolver`, and `PortfolioRiskEvaluator`; applicability runs once inside the gate and an applicable result is recorded even when coverage blocks. The evaluator is pure and has no writer, persistence, memory, or decision path.
- `ArtifactPublisher` is the only formal publication writer. It determines the memory plan/reservation, writes/verifies the recovery envelope before promising recovery, writes the original memory entry idempotently, persists/validates the permanent-snapshot files before the terminal commit, validates the terminal candidate, atomically commits, reads back, and cleans temporary material last. Recovery first checks the terminal manifest: committed+verified+identity match is idempotent success without `recovery/`; committed conflict/corruption returns a typed result without overwrite or republish; only uncommitted records proceed with the recovery envelope. Recovery drives the same publisher and commit; it has no separate transaction or marker.
- Post-commit read failure keeps the committed terminal manifest immutable, rejects the record as success, and records an independent corruption diagnostic. It does not replace the committed manifest with `failed`.
- `PublicationSnapshotStore` holds permanent committed records. `RecoverySnapshotStore` holds temporary pending envelopes. History and export read the permanent snapshot and revalidate on every read. Permanent artifacts form an acyclic hash DAG: `binding.json` has no terminal-manifest hash; the manifest hashes permanent files; no hashed file contains the manifest hash. `record_hash` is a canonical content digest with `artifact_binding.record_hash` and result-carrying hashes excluded; file-byte hashes are separate.
- Only `DataAccessService` calls vendor adapters. `FinancialFactService` requests structured facts through it and normalizes the returned payload; the existing SEC statement capability is connected through an explicit SEC adapter boundary with shared cache, counters, and provenance. `FinancialMetricService` is pure; the metric block is computed before research debate and persisted in a `metric_evidence_bundle`.
- `ContextAssembler` remains the only context entry. `DownstreamBriefBuilder` generates/reuses the five-role brief before context delivery, using the program coverage view and its version; for those roles the brief replaces the four full analyst reports. It does not mutate full/formal/history/recovery artifacts.
- `MemoryService` remains the only memory writer. `MemoryReservationStore` provides a persistent, append-only allocation history with a high-water mark over all historical allocations, including failed; a failed version is never reissued; retries/recovery reuse their own reservation; `committed` is a derived projection, not a second commit condition. The reuse/new plan is fixed before the recovery envelope.
- Current normal publication and recovery share one simple exclusive `StartupRecoveryGuard` and a duplicate-start guard with bounded retry. The guard is held only for the check-and-write/commit boundary; unsupported concurrent recovery is rejected. `RunOwnershipLock`, `lease.json`, owner/fencing tokens, and takeover are a deferred multi-worker extension, not current `FR-06`. The lock order, when needed, is guard then memory lock. Recovery reads/parses/renders outside the guard; staged content is revalidated before use.
- All formal display, persistence, memory, history, export, and scoring consume `FinalizedRunRecord` or a verified committed publication.
- Old writers are wrapped, made private, or require a finalized record; `propagate` keeps its `(final_state, signal)` return shape after publication.
- The terminal manifest `run_status=completed` plus read-time `INV-01` is the only commit condition.
- Implementation is phased: foundations; core closed loop + Portfolio Manager/model proposal + minimum memory identity/idempotency + FR-02-required section manifest/permanent snapshot/recovery envelope; memory enhancements; financial metrics; history/startup scan/export/benchmark; brief/context; behavior evaluation. FR-02/INV-01/SB-01 obligations remain draft and are reviewed with the whole registry.
- Disabled capabilities reject or degrade explicitly; a disabled phase is not evidence that the requirement is satisfied.
- `FR-02` recovery-snapshot generation, section manifest, terminal manifest, and binding; `INV-01` binding/read-time verification; and `SB-01` risk-branch behavior remain obligations in the draft registry. Draft status limits completion/acceptance claims.

### 2.1 ADD-R iterations applied

1. Full-scope drivers, constraints, and retain/adjust assessment.
2. Risk: pure evaluator inside the shared gate (chosen over a separate risk gate, model-assisted risk, or pre-model filter).
3. Publication lifecycle: extend the publisher with permanent/recovery envelopes and a single-process duplicate-start guard; multi-worker claim/fencing is deferred (chosen over a separate archive transaction, graph re-run, or directory-scan history).
4. Financial metrics: deterministic fact/metric service through the unified data access (chosen over model arithmetic, a direct vendor path, or subtraction-derived quarters).
5. Brief: a budgeted view inside the existing context assembler (chosen over a second assembler, character truncation, or an unchecked model brief).
6. Integration, compatibility, phasing, and evidence review.

See `architecture-blueprint.md` §8 for the iteration record and `docs/architecture/adr/002-full-scope-add-r.md` for the extension decisions.

Lean A remains a **recommendation for review**, not an approved team decision.

---

## 3. Options considered

### Option A — Lean A Extended (selected for proposal)

`RunContext` owns lifecycle/DI; services own policy; one gate, one publisher, one context assembler, one memory writer.

**Advantages**

- Covers all 18 requirements without a second authority or transaction.
- Keeps the graph and agents; adapters migrate public surfaces.
- Testable pure risk/metric functions and table-driven gate/coverage rules.
- Explicit permanent/temporary record split for history and recovery.

**Costs**

- Cross-cutting integration across CLI, graph, tools, reporting, memory, history, export, and recovery.
- Requires strict writer migration and bypass audits.
- More service interfaces and test suites than v0.1.
- Risk and recovery add new failure modes that must be proven.

### Option B — Independent capability subsystems

Risk, archive, and brief each get their own gate, transaction, or assembler.

**Advantages**

- Local ownership and simpler individual modules.

**Costs**

- Creates multiple final authorities, commit markers, and context sources.
- Makes cross-artifact consistency and INV-01 unprovable.
- Rejected under the same safety and functional contract as Option A.

### Option C — Event-sourced run ledger

Every run fact is appended to a ledger; reducers produce availability, metrics, gate input, risk result, publication, and recovery.

**Advantages**

- Strongest replay and construction guarantee.
- Audit-friendly for every derived result.

**Costs**

- Higher schema, replay, migration, and sanitization cost.
- More work than Lean A for the same D1 outcome.
- Retained as a re-decision option if Lean A cannot prove non-bypassability or replay becomes mandatory.

### Option D — Decorator/contextvar extension

Keep the current architecture and add wrappers around writers and the graph.

**Advantages**

- Low conceptual overhead for one entry point.

**Costs**

- Under the same required coverage (CLI, programmatic, backtest, checkpoint, recovery), the change surface becomes high.
- Hidden state complicates concurrency and testing.
- Bypass risk remains higher than Lean A.
- Retained only as a tactical prototype comparison.

---

## 4. Comparison summary

| Criterion | A: Lean A Extended | B: Independent subsystems | C: Event ledger | D: Decorator |
|---|---|---|---|---|
| One final authority | Yes | No | Yes | Fragile |
| One publication transaction | Yes | No | Yes | Fragile |
| One context assembler | Yes | No | Yes | Fragile |
| Requirement coverage confidence | High (D) | Low (D) | High (D) | Medium (D) |
| Change surface | High | High | Medium | High |
| Complexity | High | Medium–High | Medium–High | Medium–High |
| Testability | High | Medium | High | Medium |
| Compatibility with existing graph | High | Medium | Medium | High |
| Replay/audit strength | Medium–High | Medium | High | Low–Medium |

All candidates are compared under the same gate, binding, redaction, and history/recovery contract. No candidate has been implemented. All ratings except baseline facts are design expectations.

---

## 5. Why Lean A Extended

1. It preserves the single-authority and single-transaction properties that the new requirements depend on.
2. It reuses the existing graph, agents, renderer, memory substrate, and CLI instead of rewriting them.
3. Pure risk and metric functions make deterministic boundaries testable with offline fixtures.
4. The permanent/temporary publication split gives history and recovery a clear source of truth without a second commit marker.
5. The brief remains a view, so it cannot silently change formal records or context authority.
6. It gives a concrete migration path: wrap old writers, then make them record-dependent.

### 5.1 Candidate validation slice

Before final implementation approval, each candidate must implement the same thin slice under identical safety requirements:

- one mandatory preflight run;
- one coverage snapshot with a critical gap;
- one stock Buy with a passed risk evaluation and one with an over-limit/invalid input;
- one gate block, one gate error, and one failure record;
- one terminal manifest commit and read-time INV-01;
- one recovery envelope, a single-process duplicate-start guard, and model-free completion; multi-worker claim/fencing is deferred;
- one history retrieval and one export-conflict case;
- one write/run secret scan;
- one same-day memory reuse and one versioned decision.

Record changed files, interfaces, approximate LOC, test count, bypass findings, and time-to-green. The slice is evidence for the comparison, not a production implementation. If Lean A does not show an acceptable complexity advantage under the same contract, reopen this ADR.

---

## 6. Consequences

### Positive

- Model proposals cannot be mistaken for final decisions.
- Stock Buy/Overweight cannot be approved without a deterministic risk result.
- Coverage, risk, metrics, and decision evidence share one binding and one read-time verification.
- History contains only committed, verified publications.
- Recovery completes the existing publication without model/data/graph calls and without a second commit authority.
- Financial metrics have structured fact/period identity and a persistable evidence bundle.
- The brief preserves mandatory content and cannot mutate formal artifacts.
- Compatibility adapters keep existing callers working.

### Negative

- Old writers must be migrated; direct calls fail until adapted.
- More components, interfaces, and test suites than v0.1.
- Risk and recovery add failure modes that must be proven with negative tests.
- The temporary/permanent snapshot split adds storage and cleanup complexity.
- Token measurement, reference resolution, and quality evaluation are new.
- Remaining open decisions block parts of implementation and acceptance.

### Neutral

- Existing vendor caches remain and are counted separately.
- Checkpoint resume remains stricter and is distinct from publication recovery.
- Coding-agent permissions are documented, not implemented by this ADR.

---

## 7. Re-decision conditions

Re-open this ADR if any of the following occurs:

1. Lean A cannot guarantee non-bypassability of `FinalizedRunRecord` without pervasive rewrites.
2. The risk evaluator cannot remain pure and shared without creating a second authority.
3. Recovery cannot use the existing publication path without a second commit marker.
4. History/export cannot verify a committed publication from the permanent snapshot alone.
5. Publish/retry/memory idempotency requires event-level replay.
6. Multi-user or concurrent publication becomes in scope.
7. D1 changes critical-source, REVIEW, risk-policy, history, or recovery semantics.
8. Measured benefits do not justify the complexity.
9. The brief requires a separate context authority to meet quality thresholds.
10. Permission isolation requires stronger separation than the tool boundary.

---

## 8. Related documents

- `architecture-blueprint.md`
- `docs/architecture/adr/002-full-scope-add-r.md`
- `docs/architecture/invariants.md`
- `docs/architecture/trace-matrix.md`
- `docs/architecture/memory-design.md`
- `docs/architecture/permission-model.md`
- `docs/architecture/runtime-policy-catalog.md`
- `docs/architecture/evaluation-table.md`
- `docs/architecture/open-decisions.md`

---

## 9. Status

- Decision status: **proposed, pending human review**.
- Application implementation: **not started**.
- Tests: **not started**.
- Monitoring: **not implemented**.
- Benefits: **not measured** except the baseline facts.
- D1: v1.24.0; 17 active requirements are approved as a requirement-design baseline; QR-02 is deferred; approval does not assert implementation or measured results.
