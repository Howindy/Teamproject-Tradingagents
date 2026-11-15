# D2 Invariants

Status: **v0.3 — ADD-R round 3 draft / pending human review**
Date: 2026-11-15
Amended by: `docs/architecture/adr/003-add-r-round-3.md`; `docs/architecture/adr/004-cr01-state-correction.md`
D1 basis: `docs/req/requirements.yaml` v1.25.0 — 18 requirements, 122 fit criteria
Status basis: 17 active requirements are approved as a requirement-design baseline; `QR-02` is deferred and outside current acceptance; approval does not assert implementation or measured results
Implementation status: **design only; no application code changed**

---

## 1. How to read this document

Each invariant has:

- **Source**: D1 requirement IDs and/or D2 design decisions.
- **Enforcement**: component that must enforce it.
- **Verification**: planned test or audit direction.
- **Fallback**: concrete action when the invariant is violated.
- **Status**: design only; nothing is implemented or measured.

Unless stated otherwise, these invariants are **zero-tolerance** (one violation fails). `QR-02` performance is provisional and not zero-tolerance, but its correctness/model-free conditions are.

The 17 active requirements are approved as a requirement-design baseline; the architecture invariants remain design proposals until implementation and verification. `QR-02` is deferred and its performance target is outside current acceptance.

---

## 2. Inventory

| ID | Invariant | Source | Enforcement | Verification | Fallback | Status |
|---|---|---|---|---|---|---|
| INV-A-01 | Only `FinalizedRunRecord` or a verified committed publication may feed formal display, persistence, memory, history, and scoring; future export, if reactivated, must do the same. | `INV-01`, `SB-01`, `FR-05` | `SafetyGate`, `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService`, CLI/backtest adapters | Writer audit + integration test | Block publication; mark failed; never show/store a model proposal as final | Design only |
| INV-A-02 | Model proposal and final decision are separate; the final decision is immutable. | `SB-01` | `SafetyGate`, record schema | Schema/mutation tests | Reject record; produce REVIEW; do not publish | Design only |
| INV-A-03 | The gate runs before formal read/display/persistence/memory/history (and future export if reactivated) and the terminal manifest, but not before the running startup manifest or independent failure record. | `SB-01`, `FR-05` | Entry points, `ArtifactPublisher` | Bypass tests on CLI/programmatic/backtest/recovery | Abort publish; mark failed; no success claim | Design only |
| INV-A-04 | A fallback clears a critical gap only when it satisfies the same coverage contract. | `FR-03`, `SB-01` | `DataAccessService`, `AvailabilityIndex` | Contract fixtures | Keep gap; gate REVIEW | Design only |
| INV-A-05 | Logical queries, physical requests, retries, fallbacks, cache hits, and tool rounds are counted separately. | `FR-01` | `DataAccessService`, `RunEvidenceStore` | Counter reconciliation | Terminate run; new run_id for diagnosis | Design only |
| INV-A-06 | No run-scoped query result is reused across runs except recorded checkpoint inheritance. | `FR-01` | `DataAccessService`, `RunContext` | Two-run isolation | Terminate run; new run_id | Design only |
| INV-A-07 | Partial publication never claims success; completion requires terminal manifest commit and read-time INV-01. Post-commit read failure keeps the committed manifest immutable and is rejected as success. | `FR-02`, `INV-01`, `FR-06` | `ArtifactPublisher`, `PublicationStatusReader` | Failure injection; post-commit tamper | Pre-commit: running/failed; post-commit: immutable manifest + independent corruption diagnostic | Design only |
| INV-A-08 | Memory writes are idempotent, versioned, and conflict-safe; version allocation is persistent, lock-protected, and monotonic over every historical allocation, including failed reservations. | `INV-01`, `FR-06` | `MemoryService`, `MemoryReservationStore` | Duplicate/version/conflict/reservation tests | No-op for same key; new reserved version for changed decision; reuse reservation on retry; conflict on same decision_id/different digest | Design only |
| INV-A-09 | No known secret or unredacted pattern match appears in any in-scope app-controlled record boundary, including archive/history/recovery diagnostics and future export diagnostics if reactivated; paths stay in-root. | `SR-01`, `FR-05`, `FR-06` | `SecretRedactor`, all writers; `ExportService` future | Known-value/pattern/path/over-redaction tests; future export diagnostics | Fail closed; quarantine; block publish; minimal incident record | Design only |
| INV-A-10 | Context compression never removes L0/L1/L2/L5 and re-injects constraints. | D2 design | `ContextAssembler` | Token/compression fixture | Reject compressed prompt; deterministic truncation; log event | Design only |
| INV-A-11 | Checkpoint resume is allowed only for supported state and compatible versions. | D2 design | `CheckpointCoordinator` | Resume matrix | Refuse resume; start new run | Design only |
| INV-A-12 | Runtime AI has no file/system/network authority outside registered tools. | D2 design, `SR-01` | Tool registry, `RunContext` | Permission test + tool audit | Stop run; disable tool; security review | Design only |
| INV-A-13 | Coding agents are default-deny and limited to role/path whitelists. | D2 permission model | Permission model / agent runtime | Permission matrix | Revoke role; stop session; report violation | Design only |
| INV-A-14 | A finalized record hash cannot change during publish or recovery retries. | `INV-01`, `FR-06` | `ArtifactPublisher` | Hash assertion | Abort; quarantine; manual review | Design only |
| INV-A-15 | Coverage snapshot `critical_profile_hash` equals the actual critical profile hash. | `FR-03`, `SB-01` | `AvailabilityIndex`, `SafetyGate` | Hash comparison | Block gate; invalid coverage; failed run | Design only |
| INV-A-16 | `decision_id` is stable for identical decision content and distinct for different content. | `INV-01`, `SB-01` | `SafetyGate`, `MemoryService` | Same-day/different-decision tests | Reuse or version; conflict on tamper | Design only |
| INV-A-17 | Formal blocked text uses the `review_class` of `primary_reason_code`; all reason codes are retained. | `SB-01`, `FR-04` | `SafetyGate`, report writer | Multi-reason matrix | Choose primary by fixed priority; list secondary reasons | Design only |
| INV-A-18 | Every write has a `write_scan_status`; the terminal manifest has a final `run_scan_status`. | `SR-01` | `SecretRedactor`, `ArtifactPublisher` | Boundary fixture | Block unsafe write; fail closed | Design only |
| INV-A-19 | `run_clock` is fixed at run start and inherited by resume/replay unless an override is recorded. | `FR-03`, `FR-04` | `RunContext`, `AvailabilityIndex` | Clock/replay fixture | Refuse or record override; recompute nothing silently | Design only |
| INV-A-20 | Executed records map evidence through `supports`; `http_request_count` counts actual outbound requests. | `FR-01`, `FR-03` | `DataAccessService`, `RunEvidenceStore` | Multi-link/count fixture | Correct counters; mark evidence incomplete | Design only |
| INV-A-21 | Immutable decision timing ends at the gate; publish/risk/metrics timestamps have defined scopes and do not mutate the record hash. | `FR-02`, `INV-01`, `FR-04` | `SafetyGate`, `ArtifactPublisher` | Timing-field audit | Reject mismatch; recompute publish metrics | Design only |
| INV-A-22 | A failed run writes an independent `RunFailureRecord` and failed manifest without a normal finalized record. | `FR-02`, `SB-01` | `RunContext`, `FailureFinalizer`, `ArtifactPublisher` | Startup/graph/gate failure fixtures | Failed manifest; no success | Design only |
| INV-A-23 | Mandatory market price and stock financial statements are preflighted through the shared run cache before analyst/model nodes. | `FR-03` | `PreflightCoordinator`, `DataAccessService` | Preflight fixture | Record gap; gate blocks; no duplicate fetch | Design only |
| INV-A-24 | No applicable stock Buy/Overweight formal approval exists without a validated, policy-bound, passed risk result from the shared gate. | `FR-04`, `INV-02`, `SB-01` | `SafetyGate`, `PortfolioRiskEvaluator` | Generated violation corpus + gate matrix | Block/error; formal REVIEW; no tradeable output | Design only |
| INV-A-25 | Current risk evidence binds across manifest, final-state, report summary, and a new memory entry; a reused historical entry keeps its original evidence. | `FR-04`, `INV-02`, `INV-01` | `ArtifactPublisher`, `MemoryService` | Cross-artifact + reuse tests | Block publication; manual review | Design only |
| INV-A-26 | History returns only committed publications that pass read-time INV-01; pending/failed/quarantined are not successful history. | `FR-05`, `FR-06`, `INV-01` | `HistoryService`, `PublicationSnapshotStore` | Status/history visibility tests | Exclude; return NOT_FOUND/CORRUPT_RECORD | Design only |
| INV-A-27 | Committed report sections come only from the permanent publication snapshot and recorded capability set; no foreign/stale/mixed sections. | `FR-05`, `INV-01` | `ReportSectionManifestBuilder`, `PublicationSnapshotStore` | Section isolation/tamper tests | Fail read as CORRUPT_RECORD | Design only |
| INV-A-28 | Publication recovery checks the terminal manifest first: committed+verified+identity match is idempotent success without `recovery/`; conflict/corrupt are typed; only uncommitted records use saved recovery records; at most one committed publication. | `FR-06` | `RecoveryService`, `ArtifactPublisher` | Terminal-first/model-free/duplicate/retry/corrupt tests | Quarantine; no publish; no overwrite; bounded retry | Design only |
| INV-A-29 | A recovery envelope is complete, durable, read-back-verified, internally referenced, and versioned before recovery guarantees begin. | `FR-06` | `RecoverySnapshotStore` | Snapshot reference/digest/fault tests | Quarantine; retain valid material | Design only |
| INV-A-30 | Financial facts and metrics use structured identity and as-of visibility; the metric block is the numeric authority. | `FR-07` | `FinancialFactService`, `FinancialMetricService`, `MetricConflictDetector` | Fact/period/formula/conflict tests | n/a with typed reason; disclose conflict | Design only |
| INV-A-31 | Mandatory brief content is never truncated; the brief is generated before the five roles, uses a versioned program view, replaces the four full reports for those roles, and never mutates full/formal/history/recovery artifacts. | `FR-08` | `DownstreamBriefBuilder`, `ContextAssembler` | Budget/replacement/view-version/non-mutation tests | `BRIEF_REJECTED`; fail closed; no bypass | Design only |
| INV-A-32 | The final model request obeys the token budget; characters/bytes are auxiliary. | `FR-08`, D2 context design | `TokenCounter`, `ContextAssembler` | Tokenizer fixture | Reject/compress; fail closed | Design only |
| INV-A-33 | If export is reactivated, a `verified_package` either proves every followed history reference or is labeled `historical_reference_unverified`; a non-empty target is never overwritten. | `FR-05`, `SR-01` (deferred export) | `ExportService` (deferred) | Future closure/conflict tests | Label limitation; return EXPORT_CONFLICT | Deferred |
| INV-A-34 | A post-commit read failure never overwrites the committed terminal manifest; the record is rejected as success and an independent diagnostic records the corruption. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationStatusReader`, `HistoryService` | Post-commit tamper tests | Keep immutable manifest; `CORRUPT_RECORD`; no second publication | Design only |
| INV-A-35 | Current normal publication and recovery share one simple exclusive single-process startup guard and a duplicate-start guard with bounded retry; the check-and-write boundary is protected; unsupported concurrent recovery is rejected. Lease/fencing/takeover is deferred. | `FR-02`, `FR-06` | `StartupRecoveryGuard`, `ArtifactPublisher`, `RecoveryService` | Duplicate startup, bounded wait, concurrency rejection, guard-release tests | Reject/retry; one winner; no duplicate write | Design only |
| INV-A-36 | The final model proposal is produced by the Portfolio Manager adapter, not by the Trader or a risk debater; it carries source and unapproved status. | `SB-01`, `INV-01` | `PortfolioManagerAdapter`, `SafetyGate` | Source-field/source-promotion audit | Reject proposal; no formal decision | Design only |
| INV-A-37 | Temporary recovery material may be cleaned after commit/validation; formal reads depend only on the permanent publication snapshot; future export, if reactivated, must use the same material; a terminal recovery summary is audit-only. | `FR-02`, `FR-05`, `FR-06`, `INV-01` | `ArtifactPublisher`, `PublicationSnapshotStore`, `HistoryService`; `ExportService` future | Cleanup-then-read/memory tests; future export check | Reject temporary-file dependency; keep permanent records | Design only |
| INV-A-38 | Brief failure states are distinct: disabled uses normal full input; full-report fallback requires explicit policy permission and hard-cap compliance; final `BRIEF_REJECTED` is terminal and cannot re-enter normal input or generic compression. | `FR-08` | `DownstreamBriefBuilder`, `ContextAssembler` | Disabled/fallback/rejection/bypass tests | Fail closed at context stage; no bypass | Design only |
| INV-A-39 | A same-decision uncommitted entry is never reused or ownership-transferred; B waits bounded or triggers recovery under A's original run_id/reservation/snapshot; missing snapshot/failure/conflict are typed. Failed reservations permanently occupy their versions. | `INV-01`, `FR-06`, `INV-02` | `MemoryRecoveryCoordinator`, `MemoryService`, `RecoveryService` | Active/expired/missing-snapshot/failed/conflict tests | Retryable/unavailable/failed/conflict; no duplicate | Design only |
| INV-A-40 | Permanent artifacts form an acyclic hash DAG; `binding.json` never contains the terminal-manifest hash, and no file hashed by the terminal manifest contains that hash. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService` | Hash-DAG ordering/cycle tests | Reject cyclic candidate; no commit | Design only |
| INV-A-41 | `record_hash` is computed from a canonical content projection that excludes `artifact_binding.record_hash` and every result-carrying hash; content digest and file-byte hash are separate; only specified volatile run fields are excluded and risk/provenance timestamps are preserved. | `INV-01`, `FR-02`, `FR-04` | `SafetyGate`, `ArtifactPublisher`, `Canonicalizer` | Self-exclusion/retry/timestamp/file-hash tests | Reject self-referential or unstable record hash | Design only |
| INV-A-42 | `RunCoordinator` only coordinates stages and hands off failure/publication; `RunContext` only owns identity, fixed clock, versions, paths, and dependency references. Neither contains gate, risk, metric, context, or publication policy. | D3-02, QS-10 | `RunCoordinator`, `RunContext` | Symbol/behavior audit; policy sentinel tests | Reject policy in coordinator/context; manual review | Design only |
| INV-A-43 | Each envelope (`PublicationEnvelope`, `RecoveryEnvelope`, `ModelProposal`, `CoverageView`, `CoverageSnapshot`, `RiskEvaluation`, `MetricEvidenceBundle`, `ContextAuditMetadata`) has exactly one owner, an explicit version and mutability rule, a typed error contract, and a serialization boundary; consumers do not read mutable working objects. | D3-08, QS-13 | Owners per §9.6.8 | Envelope contract/ownership/serialization tests | Reject contract violation; fail closed | Design only |
| INV-A-44 | `decision_digest`, `record_hash`, `proposal_digest`, `input_digest`, `entry_digest`, and `evidence_digest` use the declared field projections and generation order; redaction precedes digesting; content digests and file-byte hashes are distinct; no blanket timestamp removal. | D3-11, `INV-01` | `Canonicalizer`, `SafetyGate`, `ArtifactPublisher`, `MemoryService` | Digest projection/order/self-exclusion/timestamp tests | Reject record; no commit | Design only |
| INV-A-45 | Current recovery is single-process: one exclusive startup guard, duplicate-start guard with bounded retry, explicit rejection of unsupported concurrent recovery; no lease/fencing/takeover is claimed. | D3-13, `FR-06` | `StartupRecoveryGuard`, `RecoveryService` | Duplicate start/bounded wait/concurrency rejection tests | Reject/retry; no duplicate publication | Design only |
| INV-A-46 | FR-08 functional acceptance is independent of CR-01 optimization acceptance; TTM/FCF YoY/export/multi-worker recovery/QR-02 are deferred and never used as current completion evidence. | D3-16, D3-18, `FR-07`, `FR-08`, `CR-01` | `DownstreamBriefBuilder`, `FinancialMetricService`, evaluation harness | Scope/deferred/claim-boundary tests | Block false completion/acceptance claims | Design only |
| INV-A-47 | History uses the verified committed publication as authority; an optional derived index is rebuildable and non-authoritative, and every read revalidates. | D3-14, `FR-05` | `HistoryService`, `PublicationSnapshotStore` | Index rebuild/stale-index/read-revalidation tests | Ignore/rebuild index; return `CORRUPT_RECORD` for bad publication | Design only |

---

## 3. Detailed invariants

### INV-A-01 — Finalized record is the only formal source

- **Statement**: Formal display, persisted report, manifest, final-state, memory, history, export, API return, and backtest scoring that present a decision must consume a `FinalizedRunRecord` or a verified committed publication. Raw `ModelProposal` must not be presented as final. A reused historical memory entry is referenced through `reused_decision_ref` and satisfies the historical source record.
- **Source**: `INV-01`, `SB-01`, `FR-05`.
- **Enforcement**: `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService`, CLI display, backtest adapter.
- **Verification**: static writer audit; integration test that attempts to call an old writer without a record; negative test expects failure.
- **Fallback**: block publication; set run `failed`; do not append memory; display only an error/status.
- **Status**: design only.

### INV-A-02 — Proposal/final separation and immutability

- **Statement**: `FinalizedRunRecord` contains `model_proposal` (rating, text, `proposal_status=unapproved`) and `formal_decision` (status, final rating, decision text, gate result, review class) as separate fields. A blocked decision has `final_rating=REVIEW` and a manual-review text; the proposal is never presented as the formal conclusion. The record is immutable after creation.
- **Source**: `SB-01`.
- **Enforcement**: `SafetyGate`, record schema, publisher hash.
- **Verification**: schema assertions; five-rating block/pass matrix; mutation attempt; proposal/formal separation audit.
- **Fallback**: reject record; produce REVIEW; retain proposal as unapproved; log `record_mutation_attempt`.
- **Status**: design only.

### INV-A-03 — Gate before formal effects

- **Statement**: The safety gate must run before any formal display, persistence, memory, history visibility, API return, backtest scoring, or terminal manifest. Future export, if reactivated, is also a formal effect subject to the gate. No formal entry point may bypass it. The running startup manifest and the independent failed-run record are explicit exceptions; intermediate streaming/debug/staging/checkpoint output may show the proposal only when marked intermediate or unapproved.
- **Source**: `SB-01`, `FR-05`.
- **Enforcement**: CLI, programmatic, backtest, checkpoint, and headless entry adapters; `ArtifactPublisher` requires a passed/blocked/error gate result and a formal decision.
- **Verification**: entry-point bypass matrix; static writer audit; formal/intermediate consumer audit.
- **Fallback**: fail closed with REVIEW and a gate-unavailable notice; set `failed`; no tradeable output; manual review.
- **Status**: design only.

### INV-A-04 — Fallback coverage contract

- **Statement**: A fallback clears a critical gap only if capability, component, instrument, requested window, as-of date, point-in-time rule, minimum record count, and provenance match the coverage contract. A different capability, weaker window, too few records, or undated data leaves the requirement degraded with `fallback_partial` or `insufficient_evidence`.
- **Source**: `FR-03`, `SB-01`.
- **Enforcement**: `DataAccessService`, `AvailabilityIndex`.
- **Verification**: fixtures for capability/component/window/record-count/undated/provenance mismatch and a valid same-contract fallback.
- **Fallback**: keep the gap; coverage `partial`; gate REVIEW.
- **Status**: design only.

### INV-A-05 — Query accounting separation

- **Statement**: `logical_queries`, `unique_query_keys`, `run_cache_hits`, `vendor_cache_hits`, `physical_requests`, `external_requests`, `fallback_attempts`, `retry_attempts`, and `tool_rounds` are separate counters. `component_missing_record` entries are coverage records, not executions, and do not increment execution counters.
- **Source**: `FR-01`.
- **Enforcement**: `RunEvidenceStore`, `DataAccessService`.
- **Verification**: counter reconciliation; duplicate/cache/fallback/retry fixture.
- **Fallback**: terminate current run; new `run_id` for diagnosis.
- **Status**: design only.

### INV-A-06 — Run isolation

- **Statement**: The `FR-01` run cache is never shared between runs. Existing vendor caches may be shared but are recorded as `vendor_cache_hits`.
- **Source**: `FR-01`.
- **Enforcement**: `RunContext`, `DataAccessService`.
- **Verification**: two consecutive runs; zero run-cache reuse; vendor cache hit labeled.
- **Fallback**: terminate run; new `run_id`.
- **Status**: design only.

### INV-A-07 — Partial publish is not success

- **Statement**: A run is formally completed only when all required artifacts exist, read-time INV-01 passes, and the terminal manifest is atomically written with `run_status=completed`. A handled failure before commit writes `run_status=failed`; a partial/failed write must not claim completion. Every reader repeats the same read-time validation. Recovery uses the same condition. A cleanup failure after commit is a warning and does not change the committed identity. A **post-commit** read failure does not write a compensating `failed` manifest: the committed terminal manifest remains immutable evidence, the record is rejected as success, and an independent diagnostic records the corruption.
- **Source**: `FR-02`, `INV-01`, `FR-06`.
- **Enforcement**: `ArtifactPublisher`, `PublicationStatusReader`.
- **Verification**: failure injection at each artifact/manifest step; post-commit tamper; recovery completion; cleanup-failure warning.
- **Fallback**: pre-commit: keep the last running manifest and write `failed`; post-commit: immutable manifest, `CORRUPT_RECORD`, independent diagnostic; retry without model re-run.
- **Status**: design only.

### INV-A-08 — Memory idempotency

- **Statement**: Memory append is keyed by `(decision_id, entry_digest)` plus the existing `(trade_date, ticker)` guard. The readable criterion is the completed terminal manifest plus read-time INV-01. Same key is a no-op; a different decision_id creates a new committed version; only same decision_id with a different entry_digest is a conflict. Reused historical entries use `reused_decision_ref` and keep the current artifact run_id. Version allocation is persistent and lock-protected, and the next version is `high_water + 1` over every historical allocation, including failed reservations. Retries and recovery reuse their own reservation; a failed version permanently occupies the high-water mark and is never reissued. `reserved` is appended before the recovery envelope, `failed` on abort before a completed manifest, and `committed` is a derived projection appended only after terminal commit plus read-time INV-01; a missing/failed projection write is rebuilt from the terminal manifest and is not a second commit condition. An uncommitted entry is never treated as reusable success; `MemoryRecoveryCoordinator` applies bounded wait/`MEMORY_PENDING_RETRYABLE`, recovery under the original run identity/reservation/snapshot, and typed unavailable/failed/conflict statuses; it never transfers ownership. Settlement/reflection is append-only; legal rotation is recorded as `not_available`, not a binding mismatch.
- **Source**: `INV-01`, `FR-06`.
- **Enforcement**: `MemoryService`, `MemoryReservationStore`.
- **Verification**: duplicate/conflict/crash/retry/reservation/uncommitted-entry/settlement/rotation tests.
- **Fallback**: no-op for duplicate; reuse reservation on retry; fail publish for conflict; wait/takeover/reject for uncommitted; manual review.
- **Status**: design only.

### INV-A-09 — Secret-free boundaries and path confinement

- **Statement**: No known secret and no unredacted versioned-pattern match appears in an in-scope app-controlled boundary, including manifest, final-state, risk input/diagnostic, policy snapshot, memory entry, report metadata/content, section manifest, archive, history responses, recovery envelope/diagnostics, logs, preferences, error/gate/availability records, and formal API return. Future export diagnostics, if reactivated, are also in scope. Audit endpoints are scheme/host/path only; restore endpoints may keep non-sensitive query parameters and secret references, never inline sensitive values. Paths derived from prose, filters, or run_id remain within the configured root; traversal, absolute-path injection, symlink/junction escape, and out-of-root writes are forbidden. If export is reactivated, a target path is confined and a non-empty export target returns `EXPORT_CONFLICT` and is not modified.
- **Source**: `SR-01`, `FR-05`, `FR-06`.
- **Enforcement**: `SecretRedactor`, all writers, `ExportService`.
- **Verification**: known-value/pattern scans; boundary matrix; path/link escape; over-redaction; future export conflict if reactivated.
- **Fallback**: fail closed; block record/formal output; minimal secret-free incident record; no evidence deletion.
- **Status**: design only.

### INV-A-10 — Context constraints survive compression

- **Statement**: L0 safety/policy, L1 coverage/gaps, L2 role/output, and L5 gate rules are never removed by compression and are re-injected after compression. The final request obeys the token budget.
- **Source**: D2 context design, `FR-08`.
- **Enforcement**: `ContextAssembler`, `TokenCounter`.
- **Verification**: token threshold fixture; re-injection block; omitted evidence labeled; over-budget failure.
- **Fallback**: reject compressed prompt; deterministic truncation; log event.
- **Status**: design only.

### INV-A-11 — Checkpoint support matrix

- **Statement**: Graph resume is allowed only for supported graph/evidence state and compatible policy, cache-key, context, clock, and record versions. Unsupported paths must be refused or explicitly degraded. Checkpoint resume is distinct from publication recovery.
- **Source**: D2 checkpoint design.
- **Enforcement**: `CheckpointCoordinator`.
- **Verification**: resume matrix; version mismatch; missing journal; finalized record; partial publish.
- **Fallback**: refuse resume; new run; degraded mode requires opt-in and produces partial coverage.
- **Status**: design only.

### INV-A-12 — Runtime AI authority

- **Statement**: Runtime AI may only read provided context/evidence, call registered tools, and produce proposals. It has no file, shell, environment, arbitrary network, or artifact-write authority. The risk and metric evaluators are not model-callable.
- **Source**: D2 permission model, `SR-01`, `FR-04`, `FR-07`.
- **Enforcement**: tool registry, `RunContext`, model client, pure service boundaries.
- **Verification**: permission tests; tool allowlist audit; sentinels on LLM/network/vendor calls.
- **Fallback**: stop run; disable tool; security review.
- **Status**: design only.

### INV-A-13 — Coding-agent default deny

- **Statement**: Coding agents have no permissions by default. Each role receives only the paths/actions in its whitelist. Round 3 may write only `architecture-blueprint.md`, `docs/architecture/**`, and the new ADR 003.
- **Source**: D2 permission model.
- **Enforcement**: permission model and agent runtime.
- **Verification**: per-role/path allow/deny matrix; audit log.
- **Fallback**: revoke role; stop session; report violation.
- **Status**: design only.

### INV-A-14 — Publish hash stability

- **Statement**: `record_hash` is stable across publish and recovery retries; retries must not mutate the record. Only the highest committed version is effective.
- **Source**: `INV-01`, `FR-06`.
- **Enforcement**: `ArtifactPublisher`.
- **Verification**: hash assertion before/after retry; mutation attempt.
- **Fallback**: abort; quarantine; manual review.
- **Status**: design only.

### INV-A-15 — Coverage snapshot binds the actual critical profile

- **Statement**: `coverage_snapshot.critical_profile_hash` equals `critical_profile.profile_hash` for the same run, and the snapshot is produced only by the program.
- **Source**: `FR-03`, `SB-01`.
- **Enforcement**: `AvailabilityIndex`, `SafetyGate`.
- **Verification**: hash comparison; tampered profile/snapshot negative.
- **Fallback**: block gate; invalid coverage; failed run.
- **Status**: design only.

### INV-A-16 — Decision identity and memory reuse

- **Statement**: `decision_id` is derived from stable decision content and is independent of `run_id`. Memory reuse/conflict is decided by `decision_id`/`entry_digest`. `entry_digest` covers stable decision content only; `evidence_digest` covers per-run evidence and may differ. A reused historical entry is referenced through `reused_decision_ref`; current artifacts keep the current run_id.
- **Source**: `INV-01`, `SB-01`.
- **Enforcement**: `SafetyGate`, `MemoryService`.
- **Verification**: same-day/different-decision/memory-disabled/read-filter tests.
- **Fallback**: reuse; fail publish on conflict; mark memory disabled.
- **Status**: design only.

### INV-A-17 — Review class follows primary gate reason

- **Statement**: When multiple reasons occur, `primary_reason_code` is the first in the fixed priority list; `review_class` is derived from that primary reason; all reason codes remain as secondary reasons. A system error (`gate_internal_error` or `portfolio_risk_evaluator_error`) takes the higher-priority error path over a coverage gap.
- **Source**: `SB-01`, `FR-04`.
- **Enforcement**: `SafetyGate`, report writer.
- **Verification**: multi-reason matrix; each reason/combination tested.
- **Fallback**: block; select primary by priority; list all reasons.
- **Status**: design only.

### INV-A-18 — Write scan and run scan are separate

- **Statement**: Every write records `write_scan_status`; the terminal manifest records final `run_scan_status`; completed requires both clean or redacted. The running manifest may have `run_scan_status=not_run`.
- **Source**: `SR-01`.
- **Enforcement**: `SecretRedactor`, `ArtifactPublisher`.
- **Verification**: per-write scan; failed final scan; completed negative.
- **Fallback**: block unsafe write; fail closed; minimal incident record.
- **Status**: design only.

### INV-A-19 — Fixed run clock

- **Statement**: `run_clock` is fixed at run start and records as_of_date, now_utc, timezone, clock_source, analysis_mode, and mode_source. Resume/replay inherits it unless a clock override is recorded; mode is never recomputed from a later call to today. A future `as_of_date` is rejected before risk/analysis, not clipped.
- **Source**: `FR-03`, `FR-04`.
- **Enforcement**: `RunContext`, `AvailabilityIndex`, `CheckpointCoordinator`.
- **Verification**: clock/resume/replay/future-date fixtures.
- **Fallback**: refuse resume or record override; no silent mode change.
- **Status**: design only.

### INV-A-20 — Evidence links and HTTP request counts

- **Statement**: An executed record carries one or more `supports` links; a `component_missing` record carries exactly one. `http_request_count` counts actual outbound HTTP requests per attempt, including retries and redirects; cache hits and local short-circuits are 0; `external_requests` is the sum.
- **Source**: `FR-01`, `FR-03`.
- **Enforcement**: `DataAccessService`, `RunEvidenceStore`.
- **Verification**: multi-link fixture; retry/redirect/cache counter fixture.
- **Fallback**: correct counters; mark evidence incomplete; rerun.
- **Status**: design only.

### INV-A-21 — Decision timing and publication metric boundary

- **Statement**: `FinalizedRunRecord` contains decision-time timing only through the gate. Publish, manifest-write, terminal-manifest write, and end-to-end durations are measured after the decision is frozen and stored in the terminal manifest, not in the immutable record hash. Risk `evaluated_at` and metric computation time are retained in their own evidence fields; they do not mutate the formal decision.
- **Source**: `FR-02`, `INV-01`, `FR-04`.
- **Enforcement**: `SafetyGate`, `ArtifactPublisher`.
- **Verification**: timing-field audit; record-hash stability across retry; risk evidence timestamp retention.
- **Fallback**: reject inconsistent timing; recompute publish metrics without mutating the record.
- **Status**: design only.

### INV-A-22 — Independent failed-run record

- **Statement**: A failure before a normal `FinalizedRunRecord` exists still produces a `RunFailureRecord` and an atomic `run_status=failed` manifest. It carries run identity, fixed clock, failure stage, sanitized error, partial evidence/metrics, security scan status, and a non-success formal state. It does not require model output and is never treated as completed.
- **Source**: `FR-02`, `SB-01`.
- **Enforcement**: `RunContext`, `FailureFinalizer`, `ArtifactPublisher`.
- **Verification**: startup/graph/gate/publish failure fixtures.
- **Fallback**: failed manifest; no formal success; manual review.
- **Status**: design only.

### INV-A-23 — Mandatory preflight ownership and timing

- **Statement**: `PreflightCoordinator` fetches mandatory market price and stock financial statements after the running manifest and before analyst/model nodes, using the same run-scoped `DataAccessService` cache. Preflight failures become availability evidence and critical gaps; they do not trigger a second fetch inside the same run.
- **Source**: `FR-03`.
- **Enforcement**: `PreflightCoordinator`, `DataAccessService`.
- **Verification**: preflight timing/ownership fixture; shared-cache assertion.
- **Fallback**: continue to deterministic gate block; never fetch twice.
- **Status**: design only.

### INV-A-24 — Deterministic risk authority and zero unsafe approvals

- **Statement**: For every applicable stock Buy/Overweight proposal, the effective formal result is produced by the shared `SafetyGate` invoking the pure `PortfolioRiskEvaluator`. `SafetyGate` is the only caller of validation, policy resolution, applicability, and evaluation; it records an applicable result even when coverage blocks. Model text must not supply authoritative risk input, change the result, or approve an over-limit/invalid/stale/inconsistent/insufficient-cash/unsupported proposal. Missing or invalid input must not default to approval. The model proposal and formal result remain distinguishable. The evaluator makes no LLM, network, vendor, persistence, or UI call and does not execute orders.
- **Source**: `FR-04`, `INV-02`, `SB-01`.
- **Enforcement**: `SafetyGate`, `PortfolioRiskEvaluator`, `RiskInputValidator`.
- **Verification**: generated violation corpus (>=1000 fixtures); zero unsafe approvals/default approvals/not-applicable-as-pass; narrative injection; dependency sentinels.
- **Fallback**: block/error; formal REVIEW; no tradeable output; failed run on evaluator error.
- **Status**: design only.

### INV-A-25 — Risk evidence binding and reuse separation

- **Statement**: Current-run `portfolio_risk_result`, `input_ref`, `input_digest`, policy snapshot, `policy_digest`, metrics, and formal decision are identical between manifest and final-state, summarized consistently in the current report, and bound to the same `artifact_binding` as INV-01. A newly written memory entry carries the declared risk summary. A reused historical entry keeps its original evidence and binding and is linked through `reused_decision_ref`; the current run does not inject its risk summary into it. Risk evidence does not create a second binding or memory key.
- **Source**: `FR-04`, `INV-02`, `INV-01`.
- **Enforcement**: `ArtifactPublisher`, `MemoryService`.
- **Verification**: cross-artifact comparison; same-decision reuse; changed-decision versioning; historical-reference reuse; memory-disabled.
- **Fallback**: fail publication; manual review; reuse only immutable decision content.
- **Status**: design only.

### INV-A-26 — History truthfulness

- **Statement**: History visibility is exactly the committed state: terminal manifest `run_status=completed` plus successful read-time INV-01. Analysis completion, pending recovery, failed publication, and quarantined records are not successful history. Listing excludes non-committed/corrupt records; `get_run` returns `NOT_FOUND` or `CORRUPT_RECORD` without partial content.
- **Source**: `FR-05`, `FR-06`, `INV-01`.
- **Enforcement**: `HistoryService`, `PublicationSnapshotStore`, `PublicationStatusReader`.
- **Verification**: status/history visibility; corrupt/tamper; unknown run; pagination.
- **Fallback**: exclude or return typed error; never partial success.
- **Status**: design only.

### INV-A-27 — Section isolation and permanent references

- **Statement**: Every committed report section derives from the permanent publication snapshot, the versioned renderer, and the recorded capability set. The section manifest lists only applicable non-empty sections with path, agent/state fields, byte size, and SHA-256. Foreign, stale, or old-run files are forbidden. Retrieval revalidates the manifest and digests on read; future export, if reactivated, must do the same.
- **Source**: `FR-05`, `INV-01`, `FR-02`.
- **Enforcement**: `ReportSectionManifestBuilder`, `PublicationSnapshotStore`, `HistoryService`.
- **Verification**: exact section sets; digest/byte-size; foreign/stale plants; changed path; tamper.
- **Fallback**: fail read as `CORRUPT_RECORD`; do not return complete.
- **Status**: design only.

### INV-A-28 — Recovery identity and single publication

- **Statement**: Recovery first reads the terminal manifest and verifies the permanent publication. A committed, INV-01-valid, identity-matching publication is an idempotent success without requiring `recovery/`; a committed identity conflict is `RUN_ID_CONFLICT`; committed permanent-artifact corruption is `CORRUPT_RECORD`; neither overwrites the terminal manifest or auto-republishes. Only an uncommitted/absent record continues with saved, verified, redacted formal records and fixed render inputs. Recovery does not re-run analysis or create a separate archive transaction. It preserves the original `run_id`, makes no LLM/external/graph/settlement/reflection calls, and yields at most one committed publication per `run_id` and decision identity.
- **Source**: `FR-06`.
- **Enforcement**: `RecoveryService`, `ArtifactPublisher`, `RecoveryClaimStore`.
- **Verification**: model-free recovery; duplicate startup/claim; same/different content; retry; commit condition.
- **Fallback**: quarantine invalid snapshots; bounded retry; no publish on conflict.
- **Status**: design only.

### INV-A-29 — Recovery envelope integrity and single-process guard

- **Statement**: Recovery guarantee begins only at a complete, durable, read-back-verified, redacted `snapshot_ready` envelope. It contains the formal decision/binding, terminal-manifest candidate identity, section manifest and fixed render inputs, risk input/policy references, original required memory identity and reserved version, metric bundle when applicable, and versions. Every reference resolves inside the envelope with a validated digest. Current `FR-06` uses a single-process exclusive startup guard and duplicate-start guard with bounded retry; unsupported concurrent recovery is rejected. Lease/fencing/takeover/multi-worker claims are deferred, not current. Failure is isolated and retries are bounded.
- **Source**: `FR-06`.
- **Enforcement**: `RecoverySnapshotStore`, `RecoveryClaimStore`, `RecoveryService`.
- **Verification**: envelope reference/digest/fault; duplicate startup; unsupported concurrency rejection; bounded retry; failure isolation.
- **Fallback**: quarantine; retain valid material; reject duplicate/concurrent recovery.
- **Status**: design only.

### INV-A-30 — Financial fact and metric determinism

- **Statement**: Derived metrics use per-fact structured records. **Disclosure fields** (subject, accession/disclosure identifier, filing reference, filed-at, form, source fact reference, raw concept/value/unit/currency/period/fiscal/sign, explicit restatement/supersession identifiers) preserve original evidence. **Canonical fields** (fact_id, canonical concept/period/fiscal identity, span, cumulative duration, canonical sign/unit/currency, explicit lineage) may be validated or derived only by a recorded versioned rule, with input evidence and source references retained. A filing's fiscal year/quarter is not each historical fact's period identity. Missing or multiple plausible sources return unavailable/ambiguous; never use date proximity, equal value, column order, or a default. The fact fetch, metric computation, block append, and conflict check occur after the fundamentals report exists and before research debate consumes it; final publication only persists the existing result. Only facts filed on or before as-of are visible. Current formulas cover direct metrics only; **TTM metrics, FCF YoY, and single-quarter subtraction are deferred**. The program-appended metric block is the numeric authority; conflicts with recognizable structured claims are disclosed and the contradicted claim is labeled unverified.
- **Source**: `FR-07`.
- **Enforcement**: `FinancialFactService`, `FinancialMetricService`, `MetricEvidenceBundleBuilder`, `MetricConflictDetector`.
- **Verification**: fact/period/restatement/as-of; direct-metric formula arithmetic; n/a reasons; program block without tool use; conflict scope; bundle persistence/recovery; no direct vendor; deferred TTM/FCF YoY absent.
- **Fallback**: n/a with typed reason; disclose conflict; block metric-dependent recovery when the bundle is missing/corrupt.
- **Status**: design only.

### INV-A-31 — Brief mandatory preservation and non-mutation

- **Statement**: The brief's mandatory content (program `FR-03` gaps, `FR-07` metric block/sources, safety constraints) is reserved first and never truncated. The brief is generated/reused before the five target roles receive context, uses the program view and its `coverage_view_version`, and the final gate still uses the final coverage snapshot. For those five roles it replaces the four full analyst reports; other roles keep full inputs, and full+brief are not injected together. Full reports, formal records, history, recovery material, and the permanent publication snapshot are byte-identical before and after brief generation. The brief is not a formal artifact or a second context authority. Audit metadata is separate. A model brief missing or forging a required field is rejected or falls back; length alone does not prove fidelity. Protected markers prevent generic compression from shortening mandatory content.
- **Source**: `FR-08`.
- **Enforcement**: `DownstreamBriefBuilder`, `ContextAssembler`, `ArtifactPublisher`.
- **Verification**: mandatory/budget/reference/rejection; marker/Unicode; role replacement/view version; before/after byte comparison; protected markers; forged field; quality/safety.
- **Fallback**: `BRIEF_REJECTED`; fail closed at context stage; full reports remain formal artifacts but are not injected into the rejected five-role context; no bypass via normal input or generic compression.
- **Status**: design only.

### INV-A-32 — Token budget authority

- **Statement**: The final model request must obey the effective token budget. Token measurement uses the selected model or tokenizer; character and byte limits are auxiliary and measured after Unicode normalization. Over-budget context without an enabled safe compression path raises `ContextBudgetError` and fails closed; mandatory brief content is never dropped to meet a budget. For the five target roles, the brief replaces the four full reports; a full-report fallback may be used only when the policy explicitly permits it, mandatory content is complete, and it fits the context hard cap, and it is not combined with the brief.
- **Source**: `FR-08`, D2 context design.
- **Enforcement**: `TokenCounter`, `ContextAssembler`, `DownstreamBriefBuilder`.
- **Verification**: tokenizer fixture; over-budget failure; mandatory overflow; replacement/no-duplication; reference/full-report cap.
- **Fallback**: reject/compress; no oversized prompt.
- **Status**: design only.

### INV-A-33 — Export closure and conflict

- **Statement**: `display_copy` is not claimed as independently verifiable. `verified_package` includes the terminal manifest, final-state, risk/policy references, memory entry/binding, versions, and a `history_reference_closure` for every followed `reused_decision_ref`. If any source proof is unavailable, the package is labeled `historical_reference_unverified` and limited to the current run. Both modes return `EXPORT_CONFLICT` for a non-empty target and leave it byte-identical. Legacy reports are unchanged.
- **Source**: `FR-05`, `SR-01`.
- **Enforcement**: `ExportService`.
- **Verification**: closure complete/unavailable; conflict; legacy before/after bytes; credential/path scans.
- **Fallback**: label limitation; return `EXPORT_CONFLICT`; do not overwrite.
- **Status**: design only.

### INV-A-34 — Post-commit corruption immutability

- **Statement**: A failure during post-commit read validation never overwrites the committed terminal manifest with `failed` or any other status. The committed manifest remains immutable evidence. The record is rejected as a successful formal result, history returns `CORRUPT_RECORD`, and an independent diagnostic records the anomaly. No second publication or compensating terminal state is created. Export is deferred; if reactivated, it must return the same typed result.
- **Source**: `FR-02`, `INV-01`, `FR-05`.
- **Enforcement**: `ArtifactPublisher`, `PublicationStatusReader`, `HistoryService`, `ExportService`.
- **Verification**: tamper each bound artifact after commit; assert manifest bytes unchanged, diagnostic present, history rejected, no second commit; export check is deferred.
- **Fallback**: quarantine/corrupt status; manual repair; never claim success.
- **Status**: design only.

### INV-A-35 — Shared run ownership critical section

- **Statement**: Current normal publication and recovery use one simple exclusive **single-process startup guard** and a duplicate-start guard with bounded retry. The guard is held only for the check-and-write/commit boundary, never across model work or while waiting. Duplicate startup is rejected or waits; unsupported concurrent/multi-worker recovery is rejected. Lease (`lease.json`), fencing tokens, takeover, stale-lease reclaim, and multi-worker claims are a **deferred extension** and must not be claimed by current code/tests. Lock order, when a memory write is needed, is guard then memory lock; never acquire the guard while holding the memory lock.
- **Source**: `FR-02`, `FR-06`.
- **Enforcement**: `StartupRecoveryGuard`, `ArtifactPublisher`, `RecoveryService`, `MemoryService`.
- **Verification**: duplicate startup, unsupported concurrency, check-and-write boundary, release/retry tests. Lease/fencing/takeover is deferred and not tested as current.
- **Fallback**: reject lost owner; one winner; no duplicate write; bounded retry.
- **Status**: design only.

### INV-A-36 — Portfolio Manager proposal source

- **Statement**: The final model proposal is produced by the original Portfolio Manager node through `PortfolioManagerAdapter`. It carries `rating`, `text`, `source=portfolio_manager`, `source_refs`, model identifiers, and `proposal_status=unapproved`. Trader or risk-debater output is source material and is never promoted to the final model proposal. The PM does not produce the formal decision or write formal artifacts.
- **Source**: `SB-01`, `INV-01`.
- **Enforcement**: `PortfolioManagerAdapter`, `SafetyGate`.
- **Verification**: source-field assertions; attempted Trader/risk-debater promotion; unparseable PM output; formal-consumer audit.
- **Fallback**: reject proposal; REVIEW; no formal decision.
- **Status**: design only.

### INV-A-37 — Recovery cleanup versus permanent reads

- **Statement**: Temporary recovery material may be cleaned after successful commit and post-commit validation. Formal report reads, history `get_run`, and memory binding validation depend only on the permanent publication snapshot and terminal manifest; future export, if reactivated, must use the same material. A terminal `recovery_envelope_summary` is audit-only; readers must not require the temporary recovery file.
- **Source**: `FR-02`, `FR-05`, `FR-06`, `INV-01`.
- **Enforcement**: `ArtifactPublisher`, `PublicationSnapshotStore`, `HistoryService`, `ExportService`, `MemoryService`.
- **Verification**: commit -> validate -> cleanup -> history read + memory binding; missing recovery file must not fail the formal read; export check is deferred.
- **Fallback**: reject any temporary-file dependency; keep permanent records.
- **Status**: design only.

### INV-A-38 — Brief failure terminality

- **Statement**: `BRIEF_DISABLED` uses the normal full-input path and is not a fallback/rejection. `BRIEF_FULL_REPORT` is allowed only when the versioned policy explicitly permits it, mandatory content is complete, and the full report fits the context hard cap. `BRIEF_REJECTED` is terminal for the five-role context; the run fails closed at the context stage and must not re-enter the ordinary full-input path or generic compression to bypass the rejection.
- **Source**: `FR-08`.
- **Enforcement**: `DownstreamBriefBuilder`, `ContextAssembler`.
- **Verification**: disabled, full-report-allowed, final-rejection, and post-rejection bypass-attempt fixtures.
- **Fallback**: fail closed at context stage; no bypass.
- **Status**: design only.

### INV-A-39 — Uncommitted same-decision memory coordination

- **Statement**: A same-decision entry with no committed terminal manifest is not reusable success. Run B never takes ownership. If A is active, B waits bounded without holding run/memory locks and returns `MEMORY_PENDING_RETRYABLE` on timeout. If A is invalid with a valid recovery envelope, recovery runs under A's original `run_id`, original reservation, and original snapshot; ownership is never transferred. Missing snapshot -> `MEMORY_RECOVERY_UNAVAILABLE`; recovery failure -> `MEMORY_RECOVERY_FAILED`; binding conflict -> `MEMORY_CONFLICT`. B may reuse A only after A commits and validates, through `reused_decision_ref`. A failed reservation permanently occupies its version; a retry/recovery of A reuses it, while any new run receives a higher version.
- **Source**: `INV-01`, `FR-06`, `INV-02`.
- **Enforcement**: `MemoryRecoveryCoordinator`, `MemoryService`, `RecoveryService`.
- **Verification**: active/expired/missing-snapshot/recovery-failure/binding-conflict; no locks held while waiting; no ownership transfer; no duplicate entry/version.
- **Fallback**: typed retry/unavailable/failed/conflict; manual review.
- **Status**: design only.

### INV-A-40 — Acyclic permanent hash DAG

- **Statement**: Permanent artifacts form a directed acyclic hash graph. `record_hash` is computed first; `binding.json` covers `artifact_binding` plus `record_hash` but excludes the terminal-manifest hash, its own file hash, the recovery digest, and commit-evidence hash. Section/final-state/risk/metric/memory files are hashed next. The recovery envelope may carry terminal-candidate identity but not the final terminal-manifest hash. The terminal manifest covers `publication_ref` hashes (including `binding.json`) and may hold a `recovery_envelope_summary` as audit-only; it never hashes itself. An optional `diagnostics/commit_evidence.json` may record the terminal-manifest hash after commit but is outside the permanent hashed set and is not a commit authority.
- **Source**: `FR-02`, `INV-01`, `FR-05`.
- **Enforcement**: `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService`.
- **Verification**: compute in the declared order; assert no cycle and no file hashed by the terminal manifest contains its hash; assert binding has no terminal-manifest hash.
- **Fallback**: reject cyclic candidate; do not commit; no post-commit rewrite.
- **Status**: design only.

### INV-A-41 — record_hash content projection

- **Statement**: `record_hash` is computed from a canonical content projection with `artifact_binding.record_hash` and all derivative/result-carrying hashes removed; the full record with a populated self-hash is never serialized as the hash input. The order is canonical content -> `record_hash` -> fill binding -> serialize -> file-byte SHA-256 -> terminal manifest. `record_hash` (content digest) and file-byte hashes are distinct. Only the requirement's volatile run-level timestamps are excluded; risk and provenance evidence timestamps are preserved.
- **Source**: `INV-01`, `FR-02`, `FR-04`.
- **Enforcement**: `SafetyGate`, `ArtifactPublisher`, `Canonicalizer`.
- **Verification**: self-digest exclusion; retry stability; risk evidence timestamp change; actual file byte hash verification; no field feedback cycle.
- **Fallback**: reject record; no commit; manual review.
- **Status**: design only.

### INV-A-42 — Coordinator and context scope

- **Statement**: `RunCoordinator` orders stages, invokes services, and hands off failures/publication; it contains no coverage/risk/metric/context/gate/publication policy. `RunContext` owns identity, fixed clock, versions, run-scoped paths, and dependency references only. A policy test that injects a fake gate/risk decision must not be able to route it through either object.
- **Source**: D3-02, QS-10.
- **Enforcement**: `RunCoordinator`, `RunContext`.
- **Verification**: symbol/behavior audit; policy sentinel tests; dependency graph review.
- **Fallback**: reject the design/implementation; move policy to its owner; manual review.
- **Status**: design only.

### INV-A-43 — Envelope ownership and immutability

- **Statement**: Each envelope has one owner, one schema version, one mutability rule, one error contract, and one serialization boundary. A consumer receives an immutable/versioned envelope, not a mutable working object. A required-field change is a version change.
- **Source**: D3-08, QS-13.
- **Enforcement**: envelope owners in §9.6.8; `ArtifactPublisher`/`PublicationSnapshotStore` for published envelopes.
- **Verification**: owner/version/mutability matrix; mutation attempt; missing/extra field; cross-envelope reference mismatch.
- **Fallback**: reject the envelope/record; fail closed; no partial publication.
- **Status**: design only.

### INV-A-44 — Digest projection and order

- **Statement**: `decision_digest`, `record_hash`, `proposal_digest`, `input_digest`, `entry_digest`, and `evidence_digest` use the declared projections and generation order; redaction precedes digesting; self/result hashes are excluded; content digests and file-byte hashes are distinct; filing/evidence/risk timestamps are preserved.
- **Source**: D3-11, `INV-01`.
- **Enforcement**: `Canonicalizer`, `SafetyGate`, `ArtifactPublisher`, `MemoryService`.
- **Verification**: projection fixtures; order/self-exclusion; retry stability; risk/filing timestamp preservation; scan-before-digest.
- **Fallback**: reject record; no commit; no overwrite.
- **Status**: design only.

### INV-A-45 — Single-process recovery guard

- **Statement**: Current recovery is single-process. One exclusive startup guard and a duplicate-start guard with bounded retry are required; unsupported concurrent recovery is rejected; lease/fencing/takeover is deferred and not claimed.
- **Source**: D3-13, `FR-06`.
- **Enforcement**: `StartupRecoveryGuard`, `RecoveryService`.
- **Verification**: duplicate startup; bounded wait; unsupported concurrency; guard release on failure; no takeover claim.
- **Fallback**: typed busy/unsupported; no duplicate publication; manual retry.
- **Status**: design only.

### INV-A-46 — Scope and claim honesty

- **Statement**: FR-08 functional acceptance is independent of CR-01 optimization acceptance. TTM/FCF YoY/export/multi-worker recovery/QR-02 are deferred and are never used as current completion evidence. Cost, token, quality, safety, and saving claims are separate.
- **Source**: D3-16, D3-18, `FR-07`, `FR-08`, `CR-01`.
- **Enforcement**: `DownstreamBriefBuilder`, `FinancialMetricService`, evaluation harness, document review.
- **Verification**: scope audit; deferred-scope grep; claim-boundary fixtures; FR-08 functional run with unresolved CR-01 thresholds.
- **Fallback**: block false completion/acceptance claims; mark deferred.
- **Status**: design only.

### INV-A-47 — History authority

- **Statement**: The verified committed publication is the only history authority. An optional derived index is rebuildable and non-authoritative; every read revalidates. Pending/failed/quarantined/corrupt records are not successful history.
- **Source**: D3-14, `FR-05`.
- **Enforcement**: `HistoryService`, `PublicationSnapshotStore`, `PublicationStatusReader`.
- **Verification**: index rebuild, stale index ignored, read revalidation, status exclusion, corrupt/tamper.
- **Fallback**: ignore/rebuild index; return `NOT_FOUND`/`CORRUPT_RECORD`; no partial content.
- **Status**: design only.

---

## 4. Planned verification summary

| Test family | Invariants |
|---|---|
| Schema and mutation tests | INV-A-02, INV-A-14 |
| Writer bypass audit | INV-A-01, INV-A-03 |
| Coverage/fallback fixtures | INV-A-04, INV-A-15 |
| Query counter and run isolation | INV-A-05, INV-A-06 |
| Publish/recovery failure injection | INV-A-07, INV-A-14, INV-A-28, INV-A-29, INV-A-34, INV-A-35, INV-A-45 |
| Memory duplicate/conflict/version/reservation | INV-A-08, INV-A-16 |
| Secret/path scan (future export) | INV-A-09, INV-A-18, INV-A-33 |
| Context compression/token budget/replacement | INV-A-10, INV-A-31, INV-A-32 |
| Resume matrix | INV-A-11, INV-A-19 |
| Permission matrix | INV-A-12, INV-A-13 |
| Coordinator/context/envelope/digest audit | INV-A-42, INV-A-43, INV-A-44 |
| Scope/deferred/history authority | INV-A-46, INV-A-47 |
| Review-class priority | INV-A-17 |
| Evidence links/HTTP counts | INV-A-20 |
| Timing boundary | INV-A-21 |
| Failure path | INV-A-22 |
| Preflight ownership | INV-A-23 |
| Risk authority/evidence | INV-A-24, INV-A-25 |
| History truthfulness/section isolation | INV-A-26, INV-A-27 |
| Financial fact/metric determinism and timing | INV-A-30 |
| Brief preservation/non-mutation | INV-A-31 |
| Export closure/conflict | INV-A-33 |
| Post-commit corruption | INV-A-34 |
| PM/model-proposal source | INV-A-36 |
| Recovery cleanup/permanent reads | INV-A-37 |
| Brief failure terminality | INV-A-38 |
| Uncommitted same-decision coordination | INV-A-39 |
| Permanent hash DAG | INV-A-40 |
| record_hash projection | INV-A-41 |
| Single-process startup guard | INV-A-35, INV-A-45 |
| Coordinator/context scope | INV-A-42 |
| Envelope/digest contracts | INV-A-43, INV-A-44 |
| Scope/deferred/history authority | INV-A-46, INV-A-47 |

All test status: **not started**. No implementation or monitoring exists.

---

## 5. Status

- Implementation: **not started**.
- Tests: **not started**.
- Monitoring: **not implemented**.
- D1: v1.25.0; 17 active requirements are approved as a requirement-design baseline; QR-02 is deferred; approval does not assert implementation or measured results.
- D2: v0.3 ADD-R round 3 draft; all architecture decisions proposed, not approved.
- Current recovery is single-process; lease/fencing/takeover/multi-worker/export/TTM/FCF YoY/QR-02 are deferred.
- Envelope and digest contracts are proposed in blueprint §9.6.8/§9.6.9.
