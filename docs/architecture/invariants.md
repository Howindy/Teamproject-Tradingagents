# D2 Invariants

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` (working baseline; not finally approved)  
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
| INV-A-01 | Only `FinalizedRunRecord` may feed formal display, persistence, and memory. | `INV-02`, `SB-01` | `ArtifactPublisher`, `MemoryService`, CLI display adapter | Writer audit + integration test | Block publication; mark run failed; do not show/store as final | Design only |
| INV-A-02 | Model proposal and final decision are separate; final decision is immutable. | `SB-01` | `SafetyGate`, `FinalizedRunRecord` schema | Schema test + mutation test | Reject record; produce REVIEW; do not publish | Design only |
| INV-A-03 | Safety gate runs before any formal read, display, persistence, or memory write. | `SB-01` | Entry points, `ArtifactPublisher` | Bypass tests on CLI/programmatic/backtest | Abort publish; mark `gate_missing`; no success claim | Design only |
| INV-A-04 | A fallback clears a critical gap only when it satisfies the same coverage contract. | `FR-02`, `SB-01` | `DataAccessService`, `AvailabilityIndex` | Contract fixture tests | Mark `fallback_partial`; keep gap; gate REVIEW | Design only |
| INV-A-05 | Logical queries, physical requests, fallback attempts, and retries are counted separately. | `PR-01` | `DataAccessService`, `RunEvidenceStore` | Counter reconciliation test | Disable cache path; mark evidence incomplete; rerun | Design only |
| INV-A-06 | No run-scoped query result is reused across different runs. | `PR-01` | `DataAccessService`, `RunContext` | Two-run isolation test | Clear run cache; fail isolation check; rerun | Design only |
| INV-A-07 | Partial publication never claims success; completion requires the complete marker. | `QR-01`, `INV-02` | `ArtifactPublisher` | Failure-injection test | Set `publish_status=partial/failed`; retry same record; no model re-run | Design only |
| INV-A-08 | Memory writes are idempotent and conflict-safe. | `INV-02`, `SB-01` | `MemoryService` | Duplicate/conflict test | Same hash: no-op; different hash: fail publish; manual review | Design only |
| INV-A-09 | No credentials or sensitive URL parameters appear in any record boundary. | `SR-02` | `SecretRedactor`, all writers | Secret scan + boundary test | Quarantine staging; block publish; incident report; no memory append | Design only |
| INV-A-10 | Context compression never removes L0/L1/L2/L5; constraints are re-injected. | D2 design | `ContextAssembler` | Token/compression fixture | Reject compressed prompt; fall back to deterministic truncation; log event | Design only |
| INV-A-11 | Checkpoint resume is allowed only for supported state and compatible versions. | D2 design | `CheckpointCoordinator` | Resume matrix test | Refuse resume or require degraded mode; start new run | Design only |
| INV-A-12 | Runtime AI has no file/system/network authority outside registered tools. | D2 design, `SR-02` | Tool registry, `RunContext` | Permission test + tool audit | Stop run; disable offending tool; security review | Design only |
| INV-A-13 | Coding agents are default-deny and limited to role/path whitelists. | D2 permission model | Permission model / agent runtime | Permission matrix test | Revoke role; stop session; report violation | Design only |
| INV-A-14 | A finalized record hash cannot change during publish retries. | `INV-02`, `SB-01` | `ArtifactPublisher` | Hash assertion test | Abort publish; quarantine staging; manual review | Design only |

---

## 3. Detailed invariants

### INV-A-01 — Finalized record is the only formal source

- **Statement**: Any formal display, persisted report, manifest, final-state, memory entry, or monitoring event that presents a decision must consume a `FinalizedRunRecord`. Raw `ModelProposal` must not be presented as final.
- **Source**: `INV-02`, `SB-01`.
- **Enforcement**: `ArtifactPublisher`, `MemoryService`, CLI display adapter, backtest adapter.
- **Verification**: static writer audit; integration test that attempts to call old writers without a record; negative test expects failure.
- **Fallback**: block publication; set run status `failed`; do not append memory; display only an error/status, not a model proposal.
- **Status**: design only.

### INV-A-02 — Proposal/final separation and immutability

- **Statement**: `FinalizedRunRecord` contains `model_proposals` and `final_decision` as separate fields. The record is immutable after creation. A changed decision requires a new run or record version.
- **Source**: `SB-01`.
- **Enforcement**: `SafetyGate`, record schema, publisher hash.
- **Verification**: schema assertions; attempt mutation after finalization; hash comparison on retry.
- **Fallback**: reject record; produce REVIEW; do not publish; log `record_mutation_attempt`.
- **Status**: design only.

### INV-A-03 — Gate before formal effects

- **Statement**: The safety gate must run before any formal display, persistence, or memory write. No entry point may bypass it.
- **Source**: `SB-01`.
- **Enforcement**: CLI, programmatic, backtest entry adapters; `ArtifactPublisher` requires a record with a passing/blocked gate result.
- **Verification**: bypass matrix tests for all entry points; static writer audit.
- **Fallback**: abort publish; mark `gate_missing`; no success claim; require operator.
- **Status**: design only.

### INV-A-04 — Fallback coverage contract

- **Statement**: A fallback clears a critical gap only if category, instrument, window, as-of date, point-in-time rule, minimum record count, and provenance match the coverage contract. Otherwise status is `fallback_partial` and the gap remains.
- **Source**: `FR-02`, `SB-01`.
- **Enforcement**: `DataAccessService`, `AvailabilityIndex`.
- **Verification**: fixtures for category mismatch, window mismatch, insufficient records, missing provenance, and valid fallback.
- **Fallback**: keep the gap; set coverage `partial`; gate produces REVIEW.
- **Status**: design only.

### INV-A-05 — Query accounting separation

- **Statement**: `logical_queries`, `unique_query_keys`, `run_cache_hits`, `vendor_cache_hits`, `physical_requests`, `external_requests`, `fallback_attempts`, `retry_attempts`, and `tool_rounds` are separate counters. They must not be collapsed into one "data calls" number.
- **Source**: `PR-01`.
- **Enforcement**: `RunEvidenceStore`, `DataAccessService`.
- **Verification**: counter reconciliation; fixture with duplicates, cache hits, fallback, and retry.
- **Fallback**: mark evidence incomplete; disable cache for the run; rerun with instrumentation.
- **Status**: design only.

### INV-A-06 — Run isolation

- **Statement**: The PR-01 run cache is never shared between runs. Existing vendor caches may be shared but are recorded as `vendor_cache_hits`.
- **Source**: `PR-01`.
- **Enforcement**: `RunContext`, `DataAccessService`.
- **Verification**: two consecutive runs with the same key; assert zero run-cache reuse; vendor cache hit is labeled.
- **Fallback**: clear run cache; fail isolation check; rerun.
- **Status**: design only.

### INV-A-07 — Partial publish is not success

- **Statement**: A run is formally published only when all required artifacts exist and `publish-complete.json` is written. Partial writes are `partial` or `failed`.
- **Source**: `QR-01`, `INV-02`.
- **Enforcement**: `ArtifactPublisher`.
- **Verification**: failure injection at each artifact step; assert no complete marker; retry publishes missing artifacts only.
- **Fallback**: set `publish_status=partial`; retain record; retry; never re-run model for publish retry.
- **Status**: design only.

### INV-A-08 — Memory idempotency

- **Statement**: Memory append is keyed by `(run_id, record_hash)` plus the existing `(trade_date, ticker)` guard. Same key/hash is a no-op; same ticker/date with a different hash is a conflict.
- **Source**: `INV-02`, `SB-01`.
- **Enforcement**: `MemoryService`.
- **Verification**: duplicate append test; conflicting append test; crash/retry test.
- **Fallback**: no-op for duplicate; fail publish for conflict; manual review; do not overwrite.
- **Status**: design only.

### INV-A-09 — Secret-free boundaries

- **Statement**: No credentials or sensitive URL parameters appear in CLI output, logs, errors, manifest, final-state, report, memory, preferences, journal, checkpoint, publish manifest, or telemetry.
- **Source**: `SR-02`.
- **Enforcement**: `SecretRedactor` at all boundaries.
- **Verification**: documented secret-pattern scan; fixtures for key, token, password, userinfo, query, fragment.
- **Fallback**: quarantine staging; block publish; incident report; do not append memory; no silent deletion of evidence.
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
- **Source**: D2 permission model, `SR-02`.
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
- **Source**: `INV-02`, `SB-01`.
- **Enforcement**: `ArtifactPublisher`.
- **Verification**: hash assertion before and after retry; mutation attempt.
- **Fallback**: abort publish; quarantine; manual review.
- **Status**: design only.

---

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

All test status: **not started**.

---

## 5. Status

- Implementation: **not started**.
- Tests: **not started**.
- Monitoring: **not implemented**.
- D1: **not modified**.
