# D2 Invariants

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` v1.9.0 (historical baseline approved; current revision human review pending; IDs renumbered)
Implementation status: **design only; no application code changed**

---

## 1. How to read this document

Each invariant has:

- **Source**: D1 requirement IDs and/or D2 design decision.
- **Enforcement**: component that must enforce it.
- **Verification**: planned test or audit.
- **Fallback**: concrete action when the invariant is violated.
- **Status**: all are design-only; none has been implemented or tested.

Unless stated otherwise, these invariants are **zero-tolerance** (one violation fails).

---

## 2. Inventory

| ID | Invariant | Source | Enforcement | Verification | Fallback | Status |
|---|---|---|---|---|---|---|
| INV-A-01 | Only `FinalizedRunRecord` may feed formal display, persistence, and memory. | `INV-01`, `SB-01` | `ArtifactPublisher`, `MemoryService`, CLI display adapter | Writer audit + integration test | Block publication; mark run failed; do not show/store as final | Design only |
| INV-A-02 | Model proposal and final decision are separate; final decision is immutable. | `SB-01` | `SafetyGate`, `FinalizedRunRecord` schema | Schema test + mutation test | Reject record; produce REVIEW; do not publish | Design only |
| INV-A-03 | Safety gate runs before formal read/display/persistence/memory and the terminal manifest, not before the running startup manifest or independent failure record. | `SB-01` | Entry points, `ArtifactPublisher` | Bypass tests on CLI/programmatic/backtest | Abort publish; mark `gate_missing`; no success claim | Design only |
| INV-A-04 | A fallback clears a critical gap only when it satisfies the same coverage contract. | `FR-03`, `SB-01` | `DataAccessService`, `AvailabilityIndex` | Contract fixture tests | Mark `fallback_partial`; keep gap; gate REVIEW | Design only |
| INV-A-05 | Logical queries, physical requests, fallback attempts, and retries are counted separately. | `FR-01` | `DataAccessService`, `RunEvidenceStore` | Counter reconciliation test | Terminate current run; new run_id for diagnosis | Design only |
| INV-A-06 | No run-scoped query result is reused across different runs except recorded checkpoint inheritance. | `FR-01` | `DataAccessService`, `RunContext` | Two-run isolation test | Terminate current run; new run_id for diagnosis | Design only |
| INV-A-07 | Partial publication never claims success; completion requires terminal manifest commit and read-back INV-01. | `FR-02`, `INV-01` | `ArtifactPublisher` | Failure-injection test | Set `run_status=failed`; retry same record; no model re-run | Design only |
| INV-A-08 | Memory writes are idempotent, versioned, and conflict-safe. | `INV-01`, `SB-01` | `MemoryService` | Duplicate/version/conflict test | Same entry_digest: no-op; different decision_id: new version; same decision_id different entry_digest: fail publish | Design only |
| INV-A-09 | No known secret value or unredacted pattern match appears in any in-scope app-controlled record boundary. | `SR-01` | `SecretRedactor`, all writers | Known-value + versioned-pattern scan; boundary and over-redaction tests | Fail closed; quarantine; block publish; incident record without secret | Design only |
| INV-A-10 | Context compression never removes L0/L1/L2/L5; constraints are re-injected. | D2 design | `ContextAssembler` | Token/compression fixture | Reject compressed prompt; fall back to deterministic truncation; log event | Design only |
| INV-A-11 | Checkpoint resume is allowed only for supported state and compatible versions. | D2 design | `CheckpointCoordinator` | Resume matrix test | Refuse resume or require degraded mode; start new run | Design only |
| INV-A-12 | Runtime AI has no file/system/network authority outside registered tools. | D2 design, `SR-01` | Tool registry, `RunContext` | Permission test + tool audit | Stop run; disable offending tool; security review | Design only |
| INV-A-13 | Coding agents are default-deny and limited to role/path whitelists. | D2 permission model | Permission model / agent runtime | Permission matrix test | Revoke role; stop session; report violation | Design only |
| INV-A-14 | A finalized record hash cannot change during publish retries. | `INV-01`, `SB-01` | `ArtifactPublisher` | Hash assertion test | Abort publish; quarantine staging; manual review | Design only |
| INV-A-15 | Coverage snapshot `critical_profile_hash` equals the actual critical profile hash. | `FR-03`, `SB-01` | `AvailabilityIndex`, `SafetyGate` | Hash comparison fixture | Block gate; mark coverage invalid; failed run | Design only |
| INV-A-16 | `decision_id` is stable for identical decision content and distinct for different content. | `INV-01`, `SB-01` | `SafetyGate`, `MemoryService` | Same-day rerun/different-decision test | Reuse on same binding; conflict otherwise | Design only |
| INV-A-17 | Formal blocked text uses the review_class of `primary_reason_code`; all reason codes are retained. | `SB-01` | `SafetyGate`, report writer | Multi-reason matrix | Choose primary by fixed priority; list secondary reasons | Design only |
| INV-A-18 | Every write has a write_scan_status; terminal manifest has a final run_scan_status. | `SR-01` | `SecretRedactor`, `ArtifactPublisher` | Boundary fixture | Block unsafe write; fail closed | Design only |
| INV-A-19 | `run_clock` is fixed at run start and inherited by resume/replay unless an override is recorded. | `FR-03` | `RunContext`, `AvailabilityIndex` | Clock/replay fixture | Refuse or record override; recompute nothing silently | Design only |
| INV-A-20 | Executed records map evidence through `supports`; `http_request_count` counts actual outbound HTTP requests. | `FR-01`, `FR-03` | `DataAccessService`, `RunEvidenceStore` | Multi-link/count fixture | Correct counters; mark evidence incomplete | Design only |
| INV-A-21 | Immutable decision timing ends at the gate; publish metrics live in the terminal manifest. | `FR-02`, `INV-01` | `SafetyGate`, `ArtifactPublisher` | Timing-field audit | Reject record/manifest mismatch; recompute publish metrics | Design only |
| INV-A-22 | A failed run writes an independent RunFailureRecord and failed manifest without requiring a normal FinalizedRunRecord. | `FR-02`, `SB-01` | `RunContext`, `FailureFinalizer`, `ArtifactPublisher` | Startup/graph/gate failure fixtures | Write failed manifest; no formal success | Design only |
| INV-A-23 | Mandatory market price and stock financial statements are preflighted before analyst/model nodes through the shared run cache. | `FR-03` | `PreflightCoordinator`, `DataAccessService` | Preflight fixture | Record gap; gate blocks; no duplicate fetch | Design only |

---

## 3. Detailed invariants

### INV-A-01 — Finalized record is the only formal source

- **Statement**: Any formal display, persisted report, manifest, final-state, memory entry, or monitoring event that presents a decision must consume a `FinalizedRunRecord`. Raw `ModelProposal` must not be presented as final. Reused historical memory is referenced through `reused_decision_ref`; it satisfies the historical source record but is not required to carry the current run_id/snapshot fields.
- **Source**: `INV-01`, `SB-01`.
- **Enforcement**: `ArtifactPublisher`, `MemoryService`, CLI display adapter, backtest adapter.
- **Verification**: static writer audit; integration test that attempts to call old writers without a record; negative test expects failure.
- **Fallback**: block publication; set run status `failed`; do not append memory; display only an error/status, not a model proposal.
- **Status**: design only.

### INV-A-02 — Proposal/final separation and immutability

- **Statement**: `FinalizedRunRecord` contains `model_proposal` (rating, text, proposal_status = unapproved) and `formal_decision` (status, final_rating, decision_text, gate_result) as separate fields. A blocked formal decision has `final_rating=REVIEW` and a manual-review decision text; the proposal is never presented as the formal conclusion. The record is immutable after creation.
- **Source**: `SB-01`.
- **Enforcement**: `SafetyGate`, record schema, publisher hash.
- **Verification**: schema assertions; five-rating block/pass matrix; attempt mutation after finalization; proposal/formal separation audit.
- **Fallback**: reject record; produce REVIEW; retain proposal as unapproved; do not publish it as formal; log `record_mutation_attempt`.
- **Status**: design only.

### INV-A-03 — Gate before formal effects

- **Statement**: The safety gate must run before any formal display, persistence, memory, API return, backtest scoring, or terminal manifest, using one program-produced coverage snapshot. No formal entry point may bypass it. The running startup manifest and the independent failed-run record are explicit exceptions; intermediate streaming/debug/staging/checkpoint output may show the proposal only when marked intermediate or unapproved.
- **Source**: `SB-01`.
- **Enforcement**: CLI, programmatic, backtest, checkpoint, and headless entry adapters; `ArtifactPublisher` requires a formal decision with a passed, blocked, or error gate result.
- **Verification**: entry-point bypass matrix; static writer audit; formal/intermediate consumer audit.
- **Fallback**: fail closed with REVIEW and a gate-unavailable notice; set run status failed; no tradeable output; require manual review.
- **Status**: design only.

### INV-A-04 — Fallback coverage contract

- **Statement**: A fallback clears a critical gap only if capability, component, instrument, requested window, as-of date, point-in-time rule, minimum record count, and provenance match the coverage contract. A different capability, a weaker window, too few records, or undated data leaves the requirement degraded with `fallback_partial` or `insufficient_evidence`.
- **Source**: `FR-03`, `SB-01`.
- **Enforcement**: `DataAccessService`, `AvailabilityIndex`.
- **Verification**: fixtures for capability mismatch, component mismatch, window mismatch, insufficient records, undated data, missing provenance, and a valid same-contract fallback.
- **Fallback**: keep the gap; keep coverage `partial`; gate produces REVIEW.
- **Status**: design only.

### INV-A-05 — Query accounting separation

- **Statement**: `logical_queries`, `unique_query_keys`, `run_cache_hits`, `vendor_cache_hits`, `physical_requests`, `external_requests`, `fallback_attempts`, `retry_attempts`, and `tool_rounds` are separate counters. They must not be collapsed into one "data calls" number. `component_missing_record` entries are coverage records, not query executions, and do not increment execution counters.
- **Source**: `FR-01`.
- **Enforcement**: `RunEvidenceStore`, `DataAccessService`.
- **Verification**: counter reconciliation; fixture with duplicates, cache hits, fallback, and retry.
- **Fallback**: terminate the current run; do not re-execute the same query inside it; start a new run_id for diagnosis with corrected instrumentation.
- **Status**: design only.

### INV-A-06 — Run isolation

- **Statement**: The FR-01 run cache is never shared between runs. Existing vendor caches may be shared but are recorded as `vendor_cache_hits`.
- **Source**: `FR-01`.
- **Enforcement**: `RunContext`, `DataAccessService`.
- **Verification**: two consecutive runs with the same key; assert zero run-cache reuse; vendor cache hit is labeled.
- **Fallback**: terminate the current run; do not clear and reuse its cache; start a new run_id for diagnosis.
- **Status**: design only.

### INV-A-07 — Partial publish is not success

- **Statement**: A run is formally completed only when all artifacts required by the memory-enabled status exist, INV-01 passes across report/manifest/final-state/(memory when enabled), and the terminal manifest is atomically written with `run_status=completed`. A handled failure writes `run_status=failed`; a partial or failed write must not claim completion. Every reader repeats the same INV-01 validation: read the terminal manifest hash, validate all bound artifacts, re-read the manifest hash, and retry/incomplete if it changed. A completed manifest that fails validation is treated as incomplete/failed; a completed→failed compensating replace is allowed and returned results must be revalidated before reuse.
- **Source**: `FR-02`, `INV-01`.
- **Enforcement**: `ArtifactPublisher`.
- **Verification**: failure injection at each artifact and manifest-write step; assert no completed status without all artifacts and a passing INV-01 check; retry publishes missing artifacts only.
- **Fallback**: keep the last running manifest, set `run_status=failed` when a terminal record can be written, retain the record, retry; never re-run the model for publish retry.
- **Status**: design only.

### INV-A-08 — Memory idempotency

- **Statement**: Memory append is keyed by `(decision_id, entry_digest)` plus the existing `(trade_date, ticker)` guard. The unique readable criterion is the completed terminal manifest plus read-time INV-01; the physical pending tag means settlement pending, not unpublished; reused historical entries use `reused_decision_ref` and keep the current artifact run_id. Same decision_id/entry_digest is a no-op; a different decision_id creates a new committed version; only same decision_id with a different entry_digest is a conflict/tamper. entry_digest covers stable decision content only; evidence_digest may differ without implying corruption. Entry_version is reserved under the lock before commit and recorded in the terminal manifest; failed publish leaves a gap but no effective change. Effective version is the highest committed entry_version; no post-commit old-entry write. The memory decision portion is immutable after write; settlement/reflection may append outcome fields but must not change the binding or formal decision fields. A memory artifact hashes the canonical entry with hash_scope = memory_entry, not the shared file. Same-day same-binding reruns reuse the entry; different decision_ids reserve pre-commit versions and effective version is derived from committed manifests; memory-disabled runs require no memory artifact. Retention/rotation may remove an entry, which is recorded as memory not_available, not as a binding mismatch.
- **Source**: `INV-01`, `SB-01`.
- **Enforcement**: `MemoryService`.
- **Verification**: duplicate append test; conflicting append test; crash/retry test; settlement/rotation immutability test.
- **Fallback**: no-op for duplicate; fail publish for conflict; manual review; do not overwrite; record rotation as not_available.
- **Status**: design only.

### INV-A-09 — Secret-free boundaries

- **Statement**: No known secret value and no unredacted versioned-pattern match appears in an in-scope app-controlled record boundary: manifest, final-state, memory decision entry, report metadata/content, logs, preferences, error/gate/availability records, or formal API return. Exact known-value matches and pattern matches are counted separately. Audit endpoints are scheme/host/path only; preference restore endpoints may keep non-sensitive query parameters and secret_ref names, never inline sensitive values. A separate minimal security incident record is allowed only when it contains no secret value and is not a formal decision artifact. Every write has a write_scan_status and the terminal manifest records a final run_scan_status; completed requires both clean or redacted. Detector/sanitizer/rule-version failure fails closed.
- **Source**: `SR-01`.
- **Enforcement**: `SecretRedactor` at all in-scope boundaries.
- **Verification**: known-secret exact-match scan; versioned pattern rules with positive/negative controls; boundary-coverage matrix; over-redaction tests; scanner-failure injection.
- **Fallback**: fail closed; block record and formal output; set run failed at security stage; incident record without secret; no silent pass or evidence deletion.
- **Status**: design only.

### INV-A-10 — Context constraints survive compression

- **Statement**: L0 safety/policy, L1 coverage/gaps, L2 role/output, and L5 gate rules are never removed by compression and are re-injected after compression.
- **Source**: D2 context design.
- **Enforcement**: `ContextAssembler`.
- **Verification**: token threshold fixtures; assert re-injection block; assert omitted evidence is labeled.
- **Fallback**: reject compressed prompt; use deterministic truncation; log compression event.
- **Status**: design only.

### INV-A-11 — Checkpoint support matrix

- **Statement**: Resume is allowed only for supported graph/evidence state and compatible policy, cache-key, context, and record versions. Unsupported paths must be refused or explicitly degraded.
- **Source**: D2 checkpoint design.
- **Enforcement**: `CheckpointCoordinator`.
- **Verification**: resume matrix tests; version mismatch; missing journal; finalized record; partial publish.
- **Fallback**: refuse resume; start a new run; degraded mode requires explicit opt-in and produces partial coverage.
- **Status**: design only.

### INV-A-12 — Runtime AI authority

- **Statement**: Runtime AI may only read provided context/evidence, call registered tools, and produce proposals. It has no file, shell, environment, arbitrary network, or artifact-write authority.
- **Source**: D2 permission model, `SR-01`.
- **Enforcement**: tool registry, `RunContext`, model client.
- **Verification**: permission tests; tool allowlist audit; attempt forbidden tool/URL.
- **Fallback**: stop run; disable offending tool; security review.
- **Status**: design only.

### INV-A-13 — Coding-agent default deny

- **Statement**: Coding agents have no permissions by default. Each role receives only the paths/actions in its whitelist.
- **Source**: D2 permission model.
- **Enforcement**: permission model and agent runtime.
- **Verification**: per-role/path allow/deny test matrix; audit log review.
- **Fallback**: revoke role; stop session; report violation.
- **Status**: design only.

### INV-A-14 — Publish hash stability

- **Statement**: The `record_hash` is stable across publish retries; retries must not mutate the record.
- **Source**: `INV-01`, `SB-01`.
- **Enforcement**: `ArtifactPublisher`.
- **Verification**: hash assertion before and after retry; mutation attempt.
- **Fallback**: abort publish; quarantine; manual review.
- **Status**: design only.

---

### INV-A-15 — Coverage snapshot binds the actual critical profile

- **Statement**: `coverage_snapshot.critical_profile_hash` equals `critical_profile.profile_hash` for the same run, and the snapshot is produced only by the program.
- **Source**: `FR-03`, `SB-01`.
- **Enforcement**: `AvailabilityIndex`, `SafetyGate`.
- **Verification**: hash comparison fixture; tampered profile/snapshot negative test.
- **Fallback**: block the gate; mark coverage invalid; failed run.
- **Status**: design only.

### INV-A-16 — Decision identity and memory reuse

- **Statement**: `decision_id` is derived from stable decision content (`trade_date`, ticker, decision_digest) and is independent of the per-invocation `run_id`. Memory reuse and conflict are decided by `decision_id`/`entry_digest`, not by the shared memory file. `entry_digest` covers stable decision content only and excludes coverage/gaps, provenance, source run_id, source snapshot hash, timestamps, commit_status, and reuse metadata. `evidence_digest` covers per-run evidence and may differ across normal reruns. A reused historical entry is referenced through `reused_decision_ref`; the current artifacts keep the current run_id, and the entry is readable only when its originating terminal manifest is completed and binds the entry.
- **Source**: `INV-01`, `SB-01`.
- **Enforcement**: `SafetyGate`, `MemoryService`.
- **Verification**: same-day same-binding rerun with reused_decision_ref, different-decision rerun, memory-disabled run, and uncommitted-entry read filtering.
- **Fallback**: reuse same entry; fail publish on conflict; mark memory disabled.
- **Status**: design only.

### INV-A-17 — Review class follows primary gate reason

- **Statement**: When multiple gate reasons occur, `primary_reason_code` is the first in the fixed priority list; `review_class` is derived from that primary reason; all `reason_codes` remain available as secondary reasons.
- **Source**: `SB-01`.
- **Enforcement**: `SafetyGate`, report writer.
- **Verification**: multi-reason matrix; each reason and combination tested.
- **Fallback**: block, select primary by priority, list all reasons.
- **Status**: design only.

### INV-A-18 — Write scan and run scan are separate

- **Statement**: Every write records `write_scan_status`; the terminal manifest records final `run_scan_status`; completed requires both clean or redacted.
- **Source**: `SR-01`.
- **Enforcement**: `SecretRedactor`, `ArtifactPublisher`.
- **Verification**: per-write scan fixture; failed final scan; completed negative test.
- **Fallback**: block unsafe write; fail closed; allow only minimal secret-free incident record.
- **Status**: design only.

### INV-A-19 — Fixed run clock

- **Statement**: `run_clock` is fixed at run start and records as_of_date, now_utc, timezone, clock_source, analysis_mode, and mode_source. Resume/replay inherits it unless a clock override is recorded; mode is never recomputed from a later call to today. Resume creates a new run_id; inherited evidence is tagged with origin_run_id/inherited and counted separately; the coverage snapshot is recomputed and rebound to the new run_id.
- **Source**: `FR-03`.
- **Enforcement**: `RunContext`, `AvailabilityIndex`, `CheckpointCoordinator`.
- **Verification**: clock/resume/replay fixtures.
- **Fallback**: refuse resume or record override; do not silently change mode.
- **Status**: design only.

### INV-A-20 — Evidence links and HTTP request counts

- **Statement**: An executed record carries one or more `supports` links to requirement components; a component_missing record carries exactly one. `http_request_count` counts actual outbound HTTP requests per attempt, including retries and redirects; cache hits and local short-circuits count 0; `external_requests` is the sum.
- **Source**: `FR-01`, `FR-03`.
- **Enforcement**: `DataAccessService`, `RunEvidenceStore`.
- **Verification**: multi-link fixture; retry/redirect/cache counter fixture.
- **Fallback**: correct counters; mark evidence incomplete; rerun.
- **Status**: design only.

### INV-A-21 — Decision timing and publish metrics boundary

- **Statement**: `FinalizedRunRecord` contains decision-time timing only through the gate (`started_at`, `analysis_finished_at`, `analysis_seconds`, `decision_completed_at`). `publish_seconds`, `manifest_write_seconds`, terminal-manifest write duration, and total end-to-end duration are measured after the decision is frozen and stored in the terminal manifest, not in the record or its record hash.
- **Source**: `FR-02`, `INV-01`.
- **Enforcement**: `SafetyGate`, `ArtifactPublisher`.
- **Verification**: timing-field audit across record and manifest; record-hash stability across publish retry.
- **Fallback**: reject inconsistent record/manifest timing; recompute publish metrics without mutating the record.
- **Status**: design only.

### INV-A-22 — Independent failed-run record

- **Statement**: A failure before a normal `FinalizedRunRecord` exists still produces a `RunFailureRecord` and an atomic `run_status=failed` manifest. It carries run identity, fixed clock, failure stage, sanitized error, partial evidence/metrics, security scan status, and a non-success formal state. It does not require model output and is never treated as completed.
- **Source**: `FR-02`, `SB-01`.
- **Enforcement**: `RunContext`, `FailureFinalizer`, `ArtifactPublisher`.
- **Verification**: startup failure, graph exception, gate failure, publish failure.
- **Fallback**: failed manifest; no formal success; manual review.
- **Status**: design only.

### INV-A-23 — Mandatory preflight ownership and timing

- **Statement**: `PreflightCoordinator` fetches mandatory market price and stock financial statements after the running manifest and before analyst/model nodes, using the same run-scoped `DataAccessService` cache. Preflight failures become availability evidence and critical gaps; they do not trigger a second fetch inside the same run.
- **Source**: `FR-03`.
- **Enforcement**: `PreflightCoordinator`, `DataAccessService`.
- **Verification**: preflight timing/ownership fixture; shared-cache assertion.
- **Fallback**: continue to deterministic gate block; never fetch twice in the same run.
- **Status**: design only.

## 4. Planned verification summary

| Test family | Invariants |
|---|---|
| Schema and mutation tests | INV-A-02, INV-A-14 |
| Writer bypass audit | INV-A-01, INV-A-03 |
| Coverage/fallback fixtures | INV-A-04 |
| Query counter and run isolation | INV-A-05, INV-A-06 |
| Publish failure injection | INV-A-07, INV-A-14 |
| Memory duplicate/conflict | INV-A-08 |
| Secret scan | INV-A-09 |
| Context compression | INV-A-10 |
| Resume matrix | INV-A-11 |
| Permission matrix | INV-A-12, INV-A-13 |
| Coverage/profile hash | INV-A-15 |
| Decision identity/memory | INV-A-16 |
| Review-class priority | INV-A-17 |
| Write/run scan phases | INV-A-18 |
| Run clock | INV-A-19 |
| Evidence links/HTTP counts | INV-A-20 |
| Timing boundary | INV-A-21 |
| Failure path | INV-A-22 |
| Preflight ownership | INV-A-23 |

All test status: **not started**.

---

## 5. Status

- Implementation: **not started**.
- Tests: **not started**.
- Monitoring: **not implemented**.
- D1: **v1.9.0 historical baseline approved; current revision human review pending; FR-01, FR-02, FR-03, SB-01, INV-01, and SR-01 contracts synchronized**.
