# D2 Open Decisions

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` v1.9.0 (historical baseline approved; current revision human review pending; IDs renumbered)
Implementation status: **design only; no application code changed**

This file records decisions that are **not closed**. Recommendations are for discussion only; they are not approvals.

---

## 1. Decision status legend

- **open** — no decision.
- **recommended, not approved** — a recommendation exists; the team must decide.
- **blocking** — implementation cannot start safely without it.
- **non-blocking** — can proceed with a work assumption, but the assumption must be recorded.

---

## 2. D1 open questions

### OQ-01 — Critical-source set

- **Status**: resolved in D1 v1.3.0.
- **Question**: which capabilities are critical for coverage and gate?
- **Resolution**: the effective critical profile is generated from asset type, analysis mode, and enabled capabilities. `market_price` is mandatory and fetched by the deterministic preflight; stock `financial_statements` is mandatory in every mode, independent of fundamentals-analyst selection, and is fetched by the deterministic preflight; each of income, balance, and cashflow requires at least one annual and the latest quarterly period known by as_of with an as-filed point-in-time rule. Crypto has no financial_statements requirement. Current-date runs add `ticker_news` when news is enabled and `social_sentiment` when social is enabled; social uses StockTwits and Reddit with at least one success, while sentiment news is optional context. Historical mode excludes live-only capabilities from the critical set; macro, prediction, technical, profile, insider, and global-news capabilities are non-critical by default. Explicit overrides are recorded.
- **Impact**: `AvailabilityIndex`, `SafetyGate`, report gaps, tests, evaluation.
- **Related requirements**: FR-03, SB-01.
- **Blocking phase**: none; defaults and override rules are defined.
- **D1 change applied**: FR-03 now defines `critical_requirement`, the effective profile defaults, `not_attempted`, and the closed decision table.

### OQ-02 — Manifest retention

- **Status**: location resolved in D1 v1.2.0; retention remains open and non-blocking.
- **Question**: how long is a run manifest retained?
- **Options**:
  1. Keep every run manifest indefinitely.
  2. Retention window with rotation.
  3. Results plus a global manifest index.
- **Recommendation (not approved)**: keep every run manifest in D1; define retention later.
- **Impact**: `ArtifactPublisher`, results layout, audit.
- **Related requirements**: FR-02.
- **Blocking phase**: D3 implementation detail.
- **D1 change applied**: FR-02 now fixes the manifest path at `<results_dir>/<run_id>/run_manifest.json`; retention remains outside D1.

### OQ-03 — Secret-pattern list

- **Status**: resolved in D1 v1.6.0.
- **Question**: which patterns are authoritative for SR-01?
- **Resolution**: SR-01 separates exact known-secret value checks from versioned pattern rules. The fixed minimum pattern categories are provider key formats, generic bearer/JWT, URL userinfo, sensitive query parameter names and values, sensitive authorization headers, and password/token assignments. Rules carry secret_rule_version, secret_rule_source, and effective_at; an unknown or missing version fails closed.
- **Impact**: `SecretRedactor`, tests, all output boundaries.
- **Related requirements**: SR-01.
- **Blocking phase**: none; rule categories and versioning are defined.
- **D1 change applied**: SR-01 now defines separate known-value and pattern checks, rule versioning, scan scope, and fail-closed behavior.

### OQ-04 — Vendor-cache retention and FR-01 key normalization

- **Status**: resolved for FR-01 in D1 v1.1.0; vendor-cache retention remains open and non-blocking.
- **Question**: which existing vendor caches remain cross-run, and what TTL applies to each?
- **Resolution**: `data_query_key` now includes method, normalized instrument or topic, asset type, analysis date, window or lookback, method-specific parameters, vendor selector digest, and cache-key version. FR-01 limits `query_execution` count, not external HTTP requests; run-cache reuse across runs is forbidden, while existing vendor caches may serve a request and are recorded as vendor-cache hits.
- **Impact**: `DataAccessService`, FR-01 tests, evidence counters, vendor-cache retention policy.
- **Related requirements**: FR-01.
- **Blocking phase**: none for the FR-01 run-cache definition; retention policy may be decided during D3.
- **D1 change applied**: FR-01-AC4 now separates cross-run run-cache reuse from vendor-cache reads and records `vendor_cache_hit` and `http_request_count`/`external_requests` separately.

### OQ-05 — Manifest overhead targets

- **Status**: provisional targets and measurement method defined in D1 v1.9.0; measurement pending.
- **Question**: are the FR-02-AC8 thresholds right: manifest write p95 at most 100 ms for a payload at most 256 KiB, and end-to-end overhead p95 at most 1% and at most 1 second?
- **Options**:
  1. Accept the provisional thresholds.
  2. Set lower thresholds after the benchmark.
  3. Record measurements without a hard target.
- **Recommendation (not approved)**: benchmark first; keep the thresholds provisional until measured.
- **Impact**: FR-02-AC8, publisher design, end-to-end latency.
- **Related requirements**: FR-02.
- **Blocking phase**: D3 benchmark.
- **D1 change applied**: FR-02-AC8 separates manifest write duration from end-to-end overhead, defines an external paired measurement and nearest-rank p95, and marks both thresholds provisional.

### OQ-06 — REVIEW acceptance and override

- **Status**: resolved in D1 v1.4.0.
- **Question**: is REVIEW acceptable as the terminal state, and is there any override?
- **Resolution**: REVIEW is a terminal non-tradeable sentinel outside the five-tier set. The gate has no model override and no operator override in D1. A blocked decision persists a formal REVIEW decision with a manual-review notice; the model proposal is retained separately as unapproved. Backtest scoring excludes REVIEW. A gate failure also fails closed to REVIEW and marks the run failed.
- **Impact**: `SafetyGate`, CLI, memory, backtest, user experience.
- **Related requirements**: SB-01.
- **Blocking phase**: none; gate input/output, blocked body, proposal separation, and failure fallback are defined.
- **D1 change applied**: SB-01 now defines trusted gate input, formal decision body, model-proposal separation, the blocked-input decision table, fail-closed gate failure, output boundaries, and entry-point coverage.

### OQ-07 — SR-01 scope

- **Status**: resolved in D1 v1.6.0.
- **Question**: does SR-01 cover only `.env` and run records, or also shell history/provider logs?
- **Resolution**: SR-01 covers app-controlled boundaries: manifest, final-state, memory decision entry, report metadata/content, logs, preferences, error/gate/availability records, and formal API return. Vendor/provider logs, shell history, OS/network captures, and external service logs are explicitly out of scope. `.env` mode 0600 is a preserved existing control, not a new D1 acceptance item.
- **Impact**: permission model, redaction tests, security scope.
- **Related requirements**: SR-01.
- **Blocking phase**: none; scope is closed and out-of-scope boundaries are named.
- **D1 change applied**: SR-01 now records scan_scope and explicitly limits the scan claim to defined boundaries, rules, and fixtures.

### OQ-08 — Concurrent locking

- **Status**: open; non-blocking.
- **Question**: can concurrent runs share manifest/preference directories without a locking policy?
- **Options**:
  1. Per-run directories; no shared manifest.
  2. Shared manifest index with lock.
  3. Serialize all runs.
- **Recommendation (not approved)**: per-run manifest/run directories; memory uses the existing lock; no shared manifest index in D2. Preferences remain the original global file with atomic replace and last-writer-wins for concurrent local runs; next startup reads that single file.
- **Impact**: `ArtifactPublisher`, `MemoryService`, prefs, concurrency tests.
- **Related requirements**: FR-01, FR-02, INV-01.
- **Blocking phase**: D3 implementation.
- **D1 change suggestion**: none required for D2.

---

## 3. New D2 decisions

### D2-OD-01 — FinalizedRunRecord schema/version

- **Status**: open; blocking.
- **Question**: which parts of the D1 v1.9.0 record contract still need a D2 implementation decision?
- **Recommendation (not approved)**: reuse the D1 contract: `run_id` plus `decision_id`, `record_version`, critical profile/coverage snapshot, gate result/input_hash, formal decision, artifact binding, and memory entry binding. Use canonical JSON/SHA-256 for decision, provenance, and record hashes; keep realized artifact hashes in the publish manifest. D2 must confirm only the versioning/migration mechanics.
- **Impact**: publisher, memory, manifest, trace, all tests.
- **Related requirements**: SB-01, INV-01, FR-02.
- **Blocking phase**: before D3.

### D2-OD-02 — Publish order, staging layout, and commit protocol

- **Status**: open; blocking.
- **Question**: exact staging layout, retry count, and terminal-commit implementation.
- **Recommendation (not approved)**: running manifest → record → report → final-state → memory entry pending → terminal manifest candidate + INV-01 check → atomic terminal manifest commit → read-back verification. The terminal manifest `run_status=completed` is the unique commit point; a complete marker is non-authoritative internal staging metadata only. 3 retries; no model re-run.
- **Impact**: `ArtifactPublisher`, `MemoryService`, tests.
- **Related requirements**: FR-02, INV-01.
- **Blocking phase**: before D3.

### D2-OD-03 — Checkpoint support matrix and degraded resume

- **Status**: open; blocking.
- **Question**: which state is resumable, and is degraded resume allowed?
- **Recommendation (not approved)**: support graph/journal state with fixed `run_clock`, critical profile contract version, decision_id, and schema versions; resume creates a new run_id and tags inherited evidence/counters separately; refuse unsupported versions; degraded resume is opt-in and uses coverage_status=partial only, so missing critical evidence deterministically blocks with REVIEW.
- **Impact**: `CheckpointCoordinator`, evidence store, tests.
- **Related requirements**: D2 design, SB-01, INV-01.
- **Blocking phase**: before D3.

### D2-OD-04 — Fallback coverage contract and substitution

- **Status**: resolved in D1 v1.3.0.
- **Question**: which fallback classes can clear which gaps?
- **Resolution**: a fallback clears a gap only under the same capability, component, instrument, requested window, as-of date, point-in-time rule, minimum-record count, and provenance contract. Global news does not clear ticker news; undated Yahoo statements do not clear SEC financial statements; partial fallback leaves the requirement degraded with `fallback_partial` or `insufficient_evidence`.
- **Impact**: `DataAccessService`, `AvailabilityIndex`, gate.
- **Related requirements**: FR-03, SB-01.
- **Blocking phase**: none; same-contract fallback is the default and approved substitutes must be recorded.

### D2-OD-05 — Token limits and compression thresholds

- **Status**: open; non-blocking for architecture, blocking for implementation.
- **Question**: exact per-call/evidence/history limits and compression strategy.
- **Recommendation (not approved)**: provisional values in `runtime-policy-catalog.md`; deterministic truncation first; no LLM summarizer by default.
- **Impact**: `ContextAssembler`, prompts, token cost, tests.
- **Related requirements**: FR-02, quality.
- **Blocking phase**: before D3 context implementation.

### D2-OD-06 — Memory structured sidecar vs Markdown metadata

- **Status**: open; blocking for memory implementation.
- **Question**: add JSONL sidecar, or keep structured metadata in Markdown?
- **Recommendation (not approved)**: either representation must carry `decision_id`, `entry_version`, `entry_digest`, `evidence_digest`, `memory_entry_binding`, `supersedes` (effective version derived from committed records), `reused_decision_ref`, retention status, and same-day-rerun status; the shared memory file is never hashed. A sidecar is preferred if machine consistency is required; a Markdown metadata line is acceptable for minimal change.
- **Impact**: `MemoryService`, idempotency, INV-01 tests.
- **Related requirements**: INV-01, FR-02.
- **Blocking phase**: before D3 memory implementation.

### D2-OD-07 — Coding-agent role whitelist

- **Status**: open; non-blocking for D2 docs, blocking for implementation workflow.
- **Question**: approve the roles/paths in `permission-model.md`.
- **Recommendation (not approved)**: D2 architect writes docs only; future implementation/test roles require explicit approval.
- **Impact**: agent permissions, audit, workflow.
- **Related requirements**: D2 governance, SR-01.
- **Blocking phase**: before coding agents implement D3.

### D2-OD-08 — Runtime AI tool boundary and context exposure

- **Status**: open; blocking for implementation.
- **Question**: exact tool list, context layer exposure, and prohibited data.
- **Recommendation (not approved)**: registered data tools only; no file/env/shell/arbitrary network; context layers per `POL-CTX-01`; the runtime may receive supports links and coverage summaries but cannot mutate them.
- **Impact**: tool registry, prompts, permission tests.
- **Related requirements**: SR-01, D2 governance.
- **Blocking phase**: before D3.

### D2-OD-09 — Behavior evaluation snapshots and approval

- **Status**: open; blocking for behavioral acceptance only.
- **Question**: who captures the nine pending evaluation snapshots, and who approves the rubric/contract?
- **Recommendation (not approved)**: use `docs/req/evaluation/eval-set-v1.json`, `rubric-v1.json`, `behavior-eval-contract-v1.json`, `config-v1.json`, `prompt-v1.0.yaml`, and `snapshots-v1.json`; capture every case snapshot with the documented fields; obtain two independent raters plus adjudication; record human approval before any live A/B acceptance claim.
- **Impact**: FR-01-AC7, evaluation-table, report evidence.
- **Related requirements**: FR-01.
- **Blocking phase**: before behavioral acceptance, not before architecture implementation.

---

## 4. D1 suggested changes (not applied)

D1 v1.1.0 applied the FR-01 change, v1.2.0 applied the FR-02 change, v1.3.0 applied the FR-03 change, v1.4.0 applied the SB-01 change, v1.5.0 applied the INV-01 change, and v1.6.0 applied the SR-01 change; v1.7.0 renumbered the requirement IDs to match their types, v1.8.0 synchronized the manifest schema and cross-artifact contracts, and v1.9.0 completed the gate, security, memory, clock, and aggregation synchronization. The remaining items below are suggestions for team review:

1. **FR-01** — applied in D1 v1.1.0. FR-01 now limits `query_execution` count, defines `data_query_key`, separates run-cache reuse from vendor-cache reads, and adds concurrent, terminal-outcome, retry/fallback, offline, and live acceptance criteria.
2. **FR-03** — applied in D1 v1.3.0. FR-03 now defines the minimal availability record, source identity, closed record/requirement status sets, effective critical profile defaults, fallback clearing, multi-query aggregation, and deterministic reporting.
3. **SB-01** — applied in D1 v1.4.0. SB-01 now defines the trusted gate input, formal decision body, model-proposal separation, complete blocked-input decision table, fail-closed gate failure, output boundaries, and entry-point coverage.
4. **INV-01** — applied in D1 v1.5.0. INV-01 now defines the completed checkpoint, artifact binding and per-artifact contract, canonicalization, provenance granularity, legal fallback, retry behavior, and memory settlement/rotation lifecycle.
5. **FR-02** — applied in D1 v1.2.0. The manifest now carries lifecycle status, a schema version, artifact hashes, timing, counters, and token-usage status.
6. **SR-01** — applied in D1 v1.6.0. SR-01 now defines known-secret and versioned-pattern checks, fixed scan scope and its limitation, preference audit/restore endpoints, fail-closed failure behavior, existing-control preservation, and over-redaction controls.
7. **OQ-05** — applied in D1 v1.9.0. FR-02-AC8 separates manifest write duration from end-to-end overhead, defines external paired measurement and nearest-rank p95, and marks both thresholds provisional.

Items 1, 2, 3, 4, 5, 6, and 7 are applied; the rest remain suggestions. D1 is at v1.9.0; requirement IDs are renumbered and manifest/gate/security/memory/aggregation contracts are synchronized.

---

## 5. Blocking summary

| Decision | Blocking phase | Related requirements |
|---|---|---|
| D2-OD-01 record schema | Before D3 | SB-01, INV-01, FR-02 |
| D2-OD-02 publish protocol | Before D3 | FR-02, INV-01 |
| D2-OD-03 checkpoint matrix | Before D3 | D2, SB-01, INV-01 |
| D2-OD-06 memory sidecar | Before D3 memory | INV-01 |
| D2-OD-08 runtime tool boundary | Before D3 | SR-01 |
| D2-OD-09 behavior evaluation snapshots/approval | Before behavioral acceptance | FR-01 |

Resolved in D1: OQ-01 critical profile, OQ-03 secret rules, OQ-04 run-cache semantics, OQ-06 REVIEW policy, OQ-07 SR-01 scope, D2-OD-04 fallback contract.
Non-blocking: OQ-02, OQ-04 (vendor-cache retention), OQ-05, OQ-08, D2-OD-05, D2-OD-07.

---

## 6. Status

- D1: **v1.9.0 historical baseline approved; current revision human review pending; FR-01, FR-02, FR-03, SB-01, INV-01, and SR-01 contracts synchronized**.
- D2 documents: **v0.1 draft / pending human review**.
- Application code: **unchanged**.
- Tests/monitoring: **not started/not implemented**.
