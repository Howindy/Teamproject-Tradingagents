# D2 Architecture Blueprint — Lean A Run Governance

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` v1.9.0 (historical baseline approved; current revision human review pending; IDs renumbered)
Implementation status: **design only; no application code changed**

---

## 1. Purpose and scope

This blueprint defines the D2 architecture for the six D1 requirements:

- `FR-01` — single execution per identical logical data query.
- `FR-02` — one lifecycle-complete run manifest.
- `FR-03` — one canonical run-scoped data-availability state with an effective critical profile, closed decision table, and separate critical-gap and non-critical-limitation reporting.
- `SB-01` — deterministic pre-persistence safety gate.
- `INV-01` — consistent provenance and final decision across artifacts.
- `SR-01` — secret-safe app-controlled run records with known-value and versioned-pattern checks, fixed scan scope, audit/restore endpoint rules, and fail-closed behavior.

The design direction is **Lean A**: a variant of the central-coordinator candidate where `RunContext` owns lifecycle and dependency wiring only. Business rules live in separate services. `FinalizedRunRecord` is the only artifact source for formal display, persistence, and memory.

This document is a design draft. It does not approve D1, select an implementation, or claim that any test has passed. Human review of this D2 design remains pending.

---

## 1A. ADD method and architectural drivers

This D2 design follows Attribute-Driven Design (ADD). The drivers come from the
approved D1 requirements and the baseline, not from implementation convenience.

### 1A.1 Architectural drivers

| Driver | Source | Architectural response |
|---|---|---|
| Duplicate logical queries and vendor-cache ambiguity | FR-01, baseline repeated ticker-news query | `DataAccessService`, run cache, single-flight, policy-terminal cache, separate HTTP/cache counters |
| One lifecycle-complete, machine-readable manifest | FR-02 | `RunContext`, `RunEvidenceStore`, `ArtifactPublisher`, run manifest schema |
| Canonical coverage and critical-gap decision table | FR-03 | `AvailabilityIndex`, critical profile, availability/component records, coverage snapshot |
| Fail-closed formal decision with reason-specific review | SB-01 | `SafetyGate`, trusted gate input, `review_class`, formal decision body, model-proposal separation |
| One bound formal result across artifacts | INV-01 | `FinalizedRunRecord`, `artifact_binding`, `decision_id`, hashes, INV-01 checkpoints |
| Secret-safe records and fail-closed scanning | SR-01 | `SecretRedactor`, write/run scan phases, minimal incident record, audit/restore endpoint split |

### 1A.2 Quality attributes and tactics

| Attribute | Scenario | Tactic |
|---|---|---|
| Correctness / determinism | Same evidence and inputs produce the same business conclusions | Fixed `run_clock`, canonical profile, deterministic aggregation, semantic gate checks |
| Auditability | A reviewer can reconstruct why a decision was approved or blocked | Immutable record, manifest, coverage snapshot, provenance digest, gate result |
| Security | A secret never reaches an app-controlled record | Known-value + versioned-pattern scan, fail-closed writes, write/run scan separation |
| Consistency | Four artifacts refer to one formal result | `artifact_binding`, `decision_id`, `decision_digest`, invariants checked at completion and read |
| Performance | Manifest and gate do not dominate run time | Bounded startup manifest, terminal write separated, external paired benchmark |
| Modifiability / testability | Rules can evolve without rewriting agents | Policy catalog, versioned schemas/rules, service boundaries, table-driven tests |

### 1A.3 ADD iterations

1. **Context and boundaries**: separate app-controlled records from vendor/provider logs, shell history, and OS/network captures.
2. **Evidence model**: define executed availability records, `component_missing_record`, `supports` links, `http_request_count`, critical profile, run clock, and coverage snapshot.
3. **Formal decision**: define trusted gate input, gate result, `primary_reason_code`, `review_class`, formal decision, and model-proposal separation.
4. **Publication and consistency**: define `FinalizedRunRecord`, `artifact_binding`, `decision_id`, manifest fields, memory entry binding, and INV-01 checkpoints.
5. **Security and operations**: define write/run scan phases, incident record, redaction boundaries, runtime policies, and checkpoint rules.
6. **Evaluation and selection**: compare Lean A, event ledger, and decorator; record the decision in ADR 001 and the evaluation table.

### 1A.4 Constraints

- Single-user local deployment; no multi-user authentication or encryption at rest in D1.
- No new vendor, exchange calendar, portfolio simulator, or order execution.
- Existing vendor caches remain; the FR-01 run cache is separate.
- The graph and tool stack remain the existing Python/LangGraph implementation.
- D2 changes architecture documents only; application code is not implemented in this phase.

## 1B. Phased implementation scope

The design is broader than one safe increment. Implementation is phased so the core formal-result loop is proven before optional complexity.

| Phase | Scope | Exit evidence |
|---|---|---|
| 1. Core closed loop | FR-01 query reuse/single-flight/counters; fixed clock/profile; mandatory preflight; availability records; coverage snapshot; gate formal decision; failure record; manifest candidate/commit; INV-01; SR-01 write/run scan | cache/concurrency/counter + coverage/gate/manifest/INV-01/security tests |
| 2. Memory lifecycle | decision entry binding, pre-commit versioning/supersedes, settlement/reflection, rotation/disabled | memory lifecycle/read-filter tests |
| 3. Recovery | checkpoint signature, inherited evidence/counters, snapshot rebinding, degraded partial-only resume | resume matrix tests |
| 4. Optional context compression | effective input budget, compression/re-injection | compression fixtures |
| 5. Behavior evaluation | frozen eval/config/prompt/snapshots, rubric, live A/B | behavior contract evidence |

No phase may claim completion of a later phase. Phase 1 must not depend on optional compression or complex recovery.

Until the recovery phase is enabled, `CheckpointCoordinator.resume()` MUST reject resume with `ResumeRejected(unsupported_phase)` and start a new run; no journal evidence is inherited. Until context compression is enabled, `ContextAssembler` MUST reject an over-budget context with `ContextBudgetError` and fail closed; it must not send an oversized prompt or silently truncate constraints.

---

## 2. Non-goals and preserved baseline

### 2.1 Non-goals

- No replacement of StockTwits or other social vendors.
- No point-in-time SEC company profile.
- No parallel Bull/Bear or risk-analyst execution.
- No full exchange calendar.
- No multi-user authentication, encryption at rest, or access control.
- No portfolio simulation or order execution.
- No default TypeSafe Jev screening.
- No production LLM response cache.
- No application code implementation in D2.

### 2.2 Preserved baseline

The existing baseline remains the reference:

- `baseline/runs/baseline-20261020-01/`
- Measured: 195.383s, 19 LLM calls, 31 tool calls, 156,541 input tokens, 27,639 output tokens.
- Measured repeated logical query: 3 ticker-news attempts with the same key. The 6 FRED indicators and 2 prediction-market topics were distinct logical queries that failed locally without an external request.
- Measured data status: 20 success, 4 withheld, 6 not_configured, 4 unavailable.
- Measured source integrity: identical before/after.

All architecture changes in this blueprint are prospective design. They are not implemented or measured.

---

## 3. Architecture overview — Lean A

### 3.1 Design principle

`RunContext` is a **lifecycle and dependency container**, not a business-rule engine. It creates and closes the run, owns the run identity and paths, and wires services. It does not decide coverage, cache policy, safety outcomes, or artifact contents.

Business rules are split into:

| Component | Responsibility |
|---|---|
| `RunContext` | Lifecycle, run identity, paths, clock, config snapshot, service wiring |
| `DataAccessService` | Query key, run cache, single-flight, retry, fallback, coverage contract, HTTP request counting |
| `PreflightCoordinator` | Mandatory market price and stock financial-statement prefetch before analysts; shared run cache and evidence records |
| `FailureFinalizer` | Independent failed-run record when graph/gate/publish fails before a normal FinalizedRunRecord exists |
| `AvailabilityIndex` | Fixed run clock, effective critical profile, component/requirement aggregation, structured gaps, coverage snapshot |
| `RunEvidenceStore` | Run-scoped evidence index: query ledger, availability records, component_missing records, supports links, metrics, provenance |
| `ContextAssembler` | AI context layers, token budget, compression, constraint re-injection |
| `SafetyGate` | Trusted gate input, reason priority, review class, formal decision, immutable `FinalizedRunRecord` |
| `RunFailureRecord` | Minimal failure identity, stage, sanitized error, partial counters/evidence, failed formal state |
| `ArtifactPublisher` | Atomic publication of report, manifest, final-state, memory entry, terminal commit, read-back INV-01 check |
| `MemoryService` | Decision-id binding, same-day deduplication, memory-disabled handling, settlement/rotation, read from finalized records |
| `SecretRedactor` | Redaction at every output boundary |
| `CheckpointCoordinator` | Supported resume matrix and state reconstruction |
| `PolicyCatalog` | Versioned policy identifiers and defaults |
| `EntrypointAdapter` | CLI, programmatic, and backtest entry normalization |
| `LegacyWriterAdapter` | Converts old writers into finalized-record consumers or blocks them |

### 3.2 Component-to-module mapping

| New component | Existing modules it wraps or replaces | Change type |
|---|---|---|
| `RunContext` | `cli/run.py`, `TradingAgentsGraph` entry paths | New lifecycle wrapper |
| `DataAccessService` | `tradingagents/dataflows/router.py:200`, `sentiment_analyst.py:66-76` prefetch, vendor modules | New service around existing calls |
| `PreflightCoordinator` | `router.py`, `tools.get_stock_data`, fundamentals statement tools, `AvailabilityIndex` | New preflight node |
| `FailureFinalizer` | `RunContext`, `ArtifactPublisher`, checkpoint/exception paths | New failure-record writer |
| `AvailabilityIndex` | router outcomes, `date_window.py`, `sentiment_analyst.py` prefetch, analyst selection/config | New availability/coverage service |
| `RunEvidenceStore` | `cli/stats_handler.py:9`, router outcomes, reporting metadata | New run-scoped evidence store |
| `ContextAssembler` | agent prompts in `agents/analysts/*`, `agents/researchers/*`, `agents/managers/*`, `agents/risk_mgmt/*` | New assembly layer |
| `SafetyGate` | `agents/rating.py:96-117`, `agents/managers/portfolio_manager.py:80-103`, `graph/trading_graph.py:358-370` | New finalization gate and review-class builder |
| `FinalizedRunRecord` | report/final-state/memory/CLI payloads | New immutable record |
| `ArtifactPublisher` | `reporting.py:92-119`, `graph/trading_graph.py:437-475`, `cli/run.py:440`, `memory/log.py:32-60` | New sole public writer and INV-01 completion checker |
| `MemoryService` | `memory/log.py`, `memory/settlement.py`, `memory/reflection.py` | New decision-id facade with same-day and rotation rules |
| `SecretRedactor` | `dataflows/net.py:6`, `cli/prefs.py:49`, `graph/trading_graph.py:255` | New boundary service |
| `CheckpointCoordinator` | `graph/checkpointer.py`, `graph/trading_graph.py:192` | New resume policy layer |
| `PolicyCatalog` | `default_config.py`, new policy constants | New versioned catalog |

### 3.3 Target modules, interfaces, and error contracts

All new governance code lives under `tradingagents/run/`; existing modules are wrapped, not rewritten.

| Component | Target module | Primary interface | Error contract |
|---|---|---|---|
| `RunContext` | `tradingagents/run/context.py` | `start(config, entrypoint) -> RunContext`; `fail(exc) -> RunFailureRecord` | `ConfigError`, `ClockError` |
| `EntrypointAdapter` | `tradingagents/run/entrypoints.py` | `normalize(entrypoint, args) -> RunRequest` | `UnsupportedEntrypoint` |
| `PolicyCatalog` | `tradingagents/run/policy.py` | `load() -> PolicySet`; `validate(policy) -> None` | `PolicyVersionError` |
| `DataAccessService` | `tradingagents/run/data_access.py` | `query(request, run_ctx) -> DataResult`; `preflight(profile, run_ctx) -> EvidenceBatch` | `VendorError`, `BudgetError`, `CacheScopeError` |
| `PreflightCoordinator` | `tradingagents/run/preflight.py` | `run(profile, run_ctx) -> EvidenceBatch` | `ProfileError`, `PreflightError` |
| `AvailabilityIndex` | `tradingagents/run/availability.py` | `build_profile(clock, config) -> CriticalProfile`; `view() -> CoverageView`; `finalize(records) -> CoverageSnapshot` | `ProfileError`, `AggregationError` |
| `RunEvidenceStore` | `tradingagents/run/evidence.py` | `record(availability) -> None`; `metrics() -> RunMetrics`; `snapshot() -> EvidenceSnapshot` | `EvidenceError` |
| `ContextAssembler` | `tradingagents/run/context_assembler.py` | `assemble(view, history) -> ContextBundle` | `ContextBudgetError` |
| `SafetyGate` | `tradingagents/run/safety_gate.py` | `finalize(proposal, snapshot) -> FinalizedRunRecord | RunFailureRecord` | `GateInputError`, `GateError` |
| `ArtifactPublisher` | `tradingagents/run/publisher.py` | `publish(record) -> PublishResult`; `publish_failure(failure) -> FailurePublishResult` | `PublishError`, `InvariantError` |
| `MemoryService` | `tradingagents/run/memory_service.py` | `store_finalized(record) -> MemoryWriteResult`; `settle_historical(...)`; `get_past_context(...)` | `MemoryConflict`, `MemoryScanError` |
| `SecretRedactor` | `tradingagents/run/security.py` | `scan(value, phase) -> ScanResult`; `redact(value, scan) -> RedactedValue` | `SecurityFailure` |
| `CheckpointCoordinator` | `tradingagents/run/checkpoint.py` | `resume(thread, signature) -> ResumePlan` | `ResumeRejected` |
| `FinalizedRunRecord` / `RunFailureRecord` | `tradingagents/run/finalization.py` | Immutable dataclasses/schemas | `SchemaError`, `RecordError` |

`RunFailureRecord` is the independent failure path: it is created by `RunContext.fail` or `SafetyGate` on failure, does not require a model proposal or normal `FinalizedRunRecord`, and is published by `ArtifactPublisher.publish_failure`. It records run identity, fixed clock, failure stage, sanitized error, partial metrics/evidence, security scan status, and `formal_decision.status=blocked_for_review` with `final_rating=REVIEW`. All formal readers treat it as non-success.

---

## 4. Entry points and writer migration

The safety gate cannot be optional for terminal decisions. All formal entry points must go through `SafetyGate` and `ArtifactPublisher` before any formal output or terminal manifest. The running startup manifest is the only regular run record allowed before the gate, and it must carry `safety_gate.status = not_run`. The independent failed-run manifest and a minimal secret-free security incident record are explicit exceptions that may be written without completing the normal gate.

Formal programmatic calls return a `PublishedRunResult` containing status, run_id, decision_id, formal rating, manifest path, and sanitized error. A raw `ModelProposal` is available only through an explicit `propose_unfinalized()`/audit interface that is clearly marked, does not write formal artifacts, and cannot be used as a formal decision. Legacy `propagate()` is a deprecated compatibility adapter that still finalizes and publishes before returning its compatibility tuple.

### 4.1 Entry-point matrix

| Entry point | Current path | Target path | Bypass prevention |
|---|---|---|---|
| CLI analysis | `cli/main.py` → `cli/run.py:99` | `CliEntrypoint` → `RunContext` → graph → `SafetyGate` → `ArtifactPublisher` | Publisher requires `FinalizedRunRecord` |
| Programmatic graph | `TradingAgentsGraph.propagate` → `_run_graph` | New `run() -> PublishedRunResult`; legacy `propagate()` adapter also finalizes/publishes | Formal calls return published result; raw proposal only through explicit `propose_unfinalized()` and never writes |
| Root demo | `TradingAgents/main.py` | Programmatic `run()` entrypoint | Remove direct writer path; demo uses published result |
| Backtest | `tradingagents/backtest.py` | Per-cell `RunContext` → `run()` → same finalization service | Per-cell published result; memory per backtest run |
| Direct report writer | `reporting.write_report_tree` | `LegacyWriterAdapter` / internal publisher function | Public call requires record; otherwise raises |
| Direct memory writer | `memory/log.py:store_decision` | `MemoryService.store_finalized` | Old method becomes private or requires record |
| Graph decision writer | `trading_graph.record_decision` | Proposal event only | Does not call `_log_state` or memory directly |
| State log writer | `trading_graph._log_state` | Publisher internal | Not callable as public path |
| `save_reports` | `TradingAgentsGraph.save_reports` | Deprecated adapter → publisher | Requires finalized record or published result |
| CLI display | `cli/display.py:display_complete_report` | Finalized record only | Cannot display raw proposal as final |

### 4.2 Old-writer policy

Old writers are not deleted in this design. They are wrapped or made private:

- `reporting.write_report_tree` becomes an internal rendering primitive called only by `ArtifactPublisher`.
- `TradingMemoryLog.store_decision` becomes internal to `MemoryService`.
- `TradingAgentsGraph._log_state` becomes internal to `ArtifactPublisher`.
- `TradingAgentsGraph.record_decision` no longer persists; it records the model proposal.
- `TradingAgentsGraph.save_reports` becomes a compatibility adapter that calls the publisher with a finalized record.
- Direct calls without a `FinalizedRunRecord` fail with a deterministic error; they do not fall back to an unfinalized path.

A planned static audit lists every public writer and asserts that no production writer accepts raw `final_state` without a record. Test status: **not started**.

### 4.3 Compatibility, deprecation, and regression scope

This is not a wrapper-only change. It changes return values, writers, memory, and report generation.

| Existing surface | Compatibility approach | Deprecation / regression |
|---|---|---|
| `TradingAgentsGraph.propagate` | Legacy adapter calls `run()` and returns the old `(final_state, signal)` tuple after publication | Deprecated; full CLI/programmatic/backtest tests plus new published-result tests |
| `TradingAgentsGraph._run_graph` / `record_decision` | Internal proposal/finalization path; no direct formal writes | Private; writer-bypass audit |
| `TradingAgentsGraph.save_reports` | Adapter requires a finalized/published record | Deprecated; report regression and direct-call negative tests |
| `reporting.write_report_tree` | Internal renderer called only by publisher | Public direct call fails or requires record |
| `TradingMemoryLog.store_decision` | Internal to MemoryService; legacy method requires record or becomes private | Memory idempotency/conflict regression |
| CLI display/report paths | Consume `PublishedRunResult`/FinalizedRunRecord only | CLI smoke/regression |
| Backtest | Per-cell `run()` returning published result | Backtest regression and memory isolation |
| Existing tests | Keep passing; add contract, negative, and compatibility tests | Full historical suite plus new suites |

The implementation plan must list compatibility adapters, deprecation warnings, and a rollback path. ``No rewrite'' means the graph and agent logic remain, not that public callers are unaffected.

---

## 5. Data flow

```text
Entrypoint
  -> RunContext.start(config)
       -> fix run_clock (as_of_date, now_utc, timezone, mode)
       -> allocate run_id
  -> PolicyCatalog load
  -> AvailabilityIndex.build_critical_profile(run_clock, asset type, analysts, overrides)
  -> write running manifest (run_clock, critical_profile, write_scan_status)
  -> RunEvidenceStore open
  -> DataAccessService bind
  -> PreflightCoordinator.run(profile)
       -> mandatory market_price
       -> stock financial_statements (income, balance, cashflow)
       -> shared DataAccessService run cache and evidence records
  -> ContextAssembler bind (provisional CoverageView)
  -> Graph / agents / tools
       -> DataAccessService
            -> query key
            -> run cache / single-flight
            -> vendor / fallback / retry
            -> ordered attempts with http_request_count
            -> RunEvidenceStore
       -> ContextAssembler
            -> L0..L5 context
       -> LLM proposals
  -> AvailabilityIndex.aggregate()
       -> executed records + component_missing records
       -> critical_gaps + critical_gap_ids
       -> coverage_snapshot (critical_profile_hash, provenance_digest)
  -> SafetyGate.finalize(model_proposal, coverage_snapshot)
       -> gate_result (status, reason_codes, primary_reason_code)
       -> review_class + formal_decision
  -> FinalizedRunRecord (immutable; decision_id, artifact_binding)
  -> ArtifactPublisher.publish(record)
       -> report Markdown/HTML
       -> final-state
       -> memory entry (hash_scope = memory_entry)
       -> INV-01 completion check
       -> terminal manifest
  -> formal display consumes FinalizedRunRecord only

Failure path:
  exception / invalid input / gate failure / publish failure
    -> RunContext.fail(exc) or SafetyGate.failure(...)
    -> RunFailureRecord (no normal model record required)
    -> ArtifactPublisher.publish_failure(record)
    -> failed manifest + minimal failure report (if safe)
    -> no formal success; no tradeable output
```

Model proposals are recorded separately from the final decision. The final decision is created by `SafetyGate`; the model does not write it.

---

## 6. Coverage and fallback contract

### 6.1 Availability state

`RunEvidenceStore` maintains one executed `availability_record` per logical query execution, identified by `data_query_key` and `record_kind = executed`:

- `tool`, `category`, `capability`, `component`
- `supports` links to every requirement component the evidence satisfies
- `source` (serving provider, or null), `attempted_sources`, `serving_source`
- `status`: success / insufficient_evidence / no_data / unavailable / withheld / not_configured / not_attempted / error
- `reason_code`, `requested_window`, `observed_window`, `record_count`
- ordered `attempts` with `http_request_count`, cache kind, and evidence timestamps
- `provenance`, `fallback_used`, `vendor_cache_hit`, `run_cache_hit`

A critical component with no query execution is a separate `component_missing_record` with identity `(run_id, requirement_id, capability, component)`, no `data_query_key` or attempts, `status = not_attempted`, and no execution-counter contribution.

`AvailabilityIndex` fixes `run_clock` at run start and computes the effective critical profile from asset type, analysis mode, enabled capabilities, and recorded overrides. It stores the profile, the coverage snapshot, and the provenance digest in the manifest. Aggregation uses the closed `requirement_status` set satisfied / degraded / missing / not_required:

- component query sets follow all / any / min:N; empty-set and out-of-range thresholds follow the FR-03 decision table;
- `complete` only when every critical requirement is satisfied;
- `partial` when any critical requirement is degraded or missing;
- a never-queried critical component produces a `component_missing_record` and a critical gap.

During the graph, `AvailabilityIndex` exposes a monotonic provisional `CoverageView` to the context assembler: current records, current provisional statuses, and a `view_version`. Agents may reason from this view but cannot treat it as the final decision input. After the graph ends, `AvailabilityIndex.aggregate()` produces the immutable final `CoverageSnapshot` used by the gate, formal report, manifest, and INV-01. The final snapshot is never injected as if it existed during the run.

### 6.2 Fallback rule

A fallback can clear a critical gap only if it satisfies the same `CoverageContract`:

- same capability and component;
- same instrument or topic;
- same requested window and as-of date;
- point-in-time rules satisfied;
- minimum record count;
- required provenance fields;
- configured fallback class.

If any field differs, the fallback is `fallback_partial` or `insufficient_evidence` and the primary gap remains. Global macro news does not clear a ticker-news critical gap; an undated Yahoo statement does not clear an SEC financial statement.

This policy is approved in D1 v1.3.0; see `docs/req/requirements.yaml` FR-03 and `docs/architecture/open-decisions.md` (OQ-01 and D2-OD-04, resolved).

---

## 7. Logical queries, physical requests, fallback, and retry

These counters are separate and must not be conflated:

| Counter | Meaning |
|---|---|
| `logical_queries` | Agent/tool requests for data |
| `unique_query_keys` | Distinct normalized keys in the run |
| `run_cache_hits` | Hits in the FR-01 run cache |
| `vendor_cache_hits` | Hits in the existing vendor cache layer |
| `query_executions` | One execution flow per logical query |
| `http_request_count` | Actual outbound HTTP requests per attempt, including retries and redirects; cache hits and local not_configured/withheld are 0 |
| `external_requests` | Sum of `http_request_count` over the run |
| `fallback_attempts` | Attempts to use a fallback source |
| `retry_attempts` | Retries within one execution flow |
| `tool_rounds` | LLM tool-call rounds |

FR-01 limits `query_executions`, not HTTP requests. Success, no_data, withheld, and not_configured may be terminal without retry; unavailable/error is terminal after the budgets allow no further attempt. The existing vendor cache may serve data across runs and is recorded as `vendor_cache_hits`, distinct from run-cache reuse. Benefit types are evaluated separately in `docs/architecture/evaluation-table.md`.

---

## 8. SafetyGate and FinalizedRunRecord

### 8.1 Separation of proposals and final decision

`ModelProposal` contains what the model produced:

- analyst reports;
- debate histories;
- trader proposal;
- portfolio-manager proposal;
- model rating and model decision text.

`FinalizedRunRecord` contains:

- `record_version` and `decision_id` (content identity separate from per-invocation `run_id`);
- run identity: run_id, decision_id, ticker, trade_date, commit, model/provider identifiers, config digest;
- fixed `run_clock`;
- `critical_profile` with per-component evidence contracts and `profile_hash`;
- evidence snapshot: executed availability records, `component_missing_record` entries, `supports` links, ordered attempts with `http_request_count`, provenance, counters, token counts, timing;
- `model_proposal` (rating, text, proposal_status = unapproved; audit-only);
- `coverage_snapshot` (program-produced, immutable, `critical_profile_hash`, `snapshot_hash`, `critical_gap_ids`, structured `critical_gaps`, `provenance_digest`);
- `coverage_status` and structured `critical_gaps`;
- `gate_result` (status, reason_codes, `primary_reason_code`, coverage, gaps, profile_version, snapshot_hash, gate_version, input_hash, run_id, evaluated_at);
- `formal_decision` (status, final_rating, decision_text, review_class);
- `final_rating` and `final_decision_text` compatibility fields carrying the formal values;
- memory entry binding and `hash_scope = memory_entry`;
- artifact references (realized artifact hashes live in the publish manifest);
- `record_hash` over the immutable record, not the shared memory file.

`final_rating` and `final_decision_text` are deterministic gate outputs, not model outputs. If the gate blocks, `final_rating=REVIEW`, the formal decision text uses the review_class matched to the gate reason (data insufficient, model-rating invalid, model REVIEW, gate/system error, invalid input, or coverage inconsistency), and the model's Buy/Sell text is preserved only under `model_proposal` as unapproved, not presented as the final decision. Gate failure records `error.stage = gate`.

### 8.2 Gate decision table and failure

The gate trusts only a program-produced `coverage_snapshot`. It verifies that `critical_profile_hash` equals the actual profile hash, that the snapshot and gate input hashes match, and that coverage, gaps, availability records, and the model rating are mutually consistent. It passes only when coverage is complete, gaps are empty, every critical requirement has an availability record, the profile is valid, the snapshot is current, and the model rating is one of the five legal ratings. Contradictory coverage/gaps, malformed input, missing records, invalid profile, model REVIEW, stale/hash-mismatched snapshots, or a critical gap block the decision. When multiple reasons occur, `primary_reason_code` is the first in the fixed priority list; all `reason_codes` are retained and `review_class` comes from the primary reason. Gate exceptions, timeouts, or internal errors fail closed to REVIEW with a gate-unavailable notice, `error.stage = gate`, and a failed run record.

### 8.3 Immutability and timing boundary

`FinalizedRunRecord` is created once, hashed, and never mutated. A changed decision requires a new run or a new record version. A publish retry reuses the same record hash.

The immutable record contains only decision-time timing up to the gate (`started_at`, `analysis_finished_at`, `analysis_seconds`, `decision_completed_at`). Post-decision publish metrics — `publish_seconds`, `manifest_write_seconds`, terminal-manifest write duration, and total end-to-end duration — are measured during publication and stored in the terminal manifest, not in the immutable decision record or its record hash. The manifest may carry a separate publish-metrics hash.

### 8.4 Formal consumers

Only the following may consume `FinalizedRunRecord` for formal output:

- CLI final summary;
- report Markdown/HTML and `5_portfolio/decision.md`;
- manifest;
- final-state;
- memory;
- publish manifest;
- API return;
- backtest scoring;
- monitoring events.

All formal consumers share one `artifact_binding`: run_id, decision_id, record_version, decision_digest, gate_status, formal_decision_status, final_rating, coverage_status, critical_gap_ids, coverage_snapshot_hash, and optional record_hash. The manifest also stores the critical profile, coverage snapshot (including `critical_profile_hash`), provenance_digest, gate input_hash, run_clock, and memory entry binding. Manifest and final-state carry the full canonical availability records and structured critical gaps; report and memory carry the binding plus declared summaries, `critical_gap_ids`, and provenance_digest. Memory artifacts hash the immutable entry (`hash_scope = memory_entry`), not the shared memory file. Memory reuse is keyed by `decision_id`, not `run_id`; a reused historical entry is referenced through `reused_decision_ref` while current artifacts keep the current run_id, and the entry is readable only when its originating run is committed. INV-01 is claimed only at the completed checkpoint and on read, never while artifacts are partial.

Intermediate streaming messages, debug output, staging files, checkpoint state, and raw agent text may show the model proposal only when explicitly marked intermediate or unapproved.

Raw `ModelProposal` is audit-only and must not be shown as the final decision.

---

## 9. Publish protocol, partial failure, and retry

### 9.1 Publish plan

`ArtifactPublisher` builds an internal `PublishManifest` from `FinalizedRunRecord`:

- `record_hash` and `decision_id`;
- `record_version`;
- artifact list with path, type, hash, and `hash_scope` (file / memory_entry / record);
- `publish_status`: staging / published / partial / failed;
- INV-01 completion result;
- attempts and timestamps.

The `PublishManifest` is an internal staging record, not the run manifest defined by FR-02. The FR-02 run manifest is the single externally visible lifecycle record at `<results_dir>/<run_id>/run_manifest.json`.

The unique authoritatively committed state is the terminal run manifest with `run_status=completed`. A `publish-complete.json` marker is not authoritative; if retained, it is internal staging metadata only. Every read path determines completion from the terminal manifest and a read-time INV-01 verification, not from a side marker.

### 9.2 Commit order

1. Write/refresh the running manifest before model calls.
2. Write `finalized-record.json` in staging.
3. Write report Markdown and HTML.
4. Write final-state JSON.
5. Reserve `entry_version` under the memory lock and write the immutable memory decision entry with physical `settlement_status=pending`, or mark memory disabled/existing. `commit_status` is not written into the entry; it is derived from the terminal manifest. Effective version is the highest committed `entry_version`.
6. Build a terminal manifest candidate in memory/staging with `run_status=completed`, binding, formal decision, security scan results, artifact hashes, and memory entry binding.
7. Run the INV-01 completion check against the terminal manifest candidate and the staged report/final-state/memory state. The on-disk manifest is still the running manifest at this point; the check must not compare against it.
8. Atomically replace the running manifest with the terminal manifest. This is the unique commit point; the terminal manifest is written last.
9. Read back the committed artifacts and re-run INV-01 on the actual published files. If read-back verification fails, atomically replace the terminal manifest with `run_status=failed` and do not claim completion.
10. Optionally move/rename staging artifacts only before the terminal manifest commit; do not perform authoritative moves after it.

Atomic per-file writes use temp file + `os.replace` semantics. A successful commit is determined by terminal manifest `run_status=completed` plus successful read-back INV-01, not by a separate complete marker.

### 9.3 Partial failure

If any step before the terminal manifest commit fails:

- `run_status` remains `running` or becomes `failed`;
- no terminal `completed` manifest exists;
- formal success is not claimed;
- memory is not readable because no completed terminal manifest exists; the entry's `pending` tag remains a settlement status, not a publication status;
- retry publishes missing artifacts only;
- the model is not re-run;
- any CLI/display path that shows the decision must show the incomplete status and must not claim a complete publication.

If `finalized-record.json` cannot be written, the run fails before any formal output. If post-commit read-back verification fails, the terminal manifest is replaced with `run_status=failed`.

The completion predicate for every reader is: terminal manifest `run_status=completed` **and** the reader performs the same read-time INV-01 validation (manifest hash, artifact hashes, binding, formal decision, security result). Trusting the manifest status alone is forbidden. A reader that sees a completed manifest whose validation fails treats the run as incomplete/failed and must not return a formal result. A completed→failed compensating replace is allowed; results returned earlier must be bound to the manifest hash and revalidated before reuse.

### 9.4 Memory idempotency and retry

Memory idempotency key: `(decision_id, entry_digest)` plus the existing `(trade_date, ticker)` guard. `run_id` remains unique per invocation and is not the memory reuse key.

- The unique readable criterion is the terminal manifest `run_status=completed` plus read-time INV-01 validation. There is no separate "mark committed" write that could fail after commit.
- The memory entry's physical `pending` tag means outcome settlement is pending, not that the decision is unpublished. `commit_status` in the terminal manifest is a projection of the terminal manifest commit and is not part of the immutable entry digest.
- Memory reads include only entries whose originating run has a completed terminal manifest and whose binding matches the committed manifest.
- `entry_digest` covers only stable decision content (decision_id, trade_date/ticker, formal decision fields). `evidence_digest` covers coverage/gaps/provenance and may differ across normal reruns without implying corruption.
- Same decision_id/entry_digest from a prior committed run: no new decision entry; the current run records `memory.status=existing` plus `reused_decision_ref` (source run_id, source decision_id, source entry_digest) while its own artifacts keep the current run_id. A different evidence_digest alone does not block reuse.
- Same-day same-binding rerun reuses the existing committed entry. A different decision_id reserves a pre-commit `entry_version` greater than the current highest committed version and writes `supersedes`; the terminal manifest records that version. Effective version is derived from committed manifests; no old entry is modified after commit; report/manifest/final-state publish independently. Only same decision_id with a different entry_digest is a conflict.
- Memory-disabled runs set `memory.status=disabled` and require no memory artifact.
- Memory write is atomic under the existing lock; a retry re-checks the key before append.
- A publisher retry sees a pending or committed existing entry and does not duplicate it; a pending entry from a failed run remains unreadable.
- `entry_version` is reserved inside the memory lock before commit and recorded in the terminal manifest; a failed commit leaves a gap but no effective change. Only the highest committed entry_version per (ticker, date) contributes lessons/statistics.

Historical settlement and reflection use a separate append-only protocol from current decision commit: settlement writes only outcome/reflection fields to an already committed historical entry, is authorized by that entry's provenance, and cannot change its decision text, rating, binding, decision_id, or entry_digest. A failed settlement leaves the entry unsettled and records a separate settlement failure.

### 9.5 Retry policy

Work assumption: 3 publish attempts with bounded backoff. No model calls. Each attempt is recorded in the publish manifest and evidence store. After exhaustion, `publish_status=failed` and operator action is required.

### 9.6 Failure publication path

A run that fails before a normal `FinalizedRunRecord` exists still writes an independent `RunFailureRecord`:

- created by `RunContext.fail(exc)` for startup/graph/preflight failures, or by `SafetyGate` for gate failure;
- contains run_id, run_clock, critical profile if available, partial availability/metrics, security scan status, failure stage, sanitized error type/message;
- contains `formal_decision.status=blocked_for_review`, `final_rating=REVIEW`, and a non-success review class;
- published by `ArtifactPublisher.publish_failure` as an atomic `run_status=failed` manifest;
- does not require report/final-state/memory artifacts and does not claim completion;
- if the failure occurs before the critical profile or coverage snapshot exists, those fields are null in the failed manifest and completed-only conditions do not apply.

This path is separate from the normal finalized-record path and must not call the model.

---

## 10. Concurrency

### 10.1 Same run, same query

`DataAccessService` uses single-flight per `query_key`:

- first request starts exactly one `query_execution`;
- concurrent requests wait on the in-flight result;
- all receive the same `DataResult`;
- `query_execution` count for that key is 1;
- `http_request_count` is not fixed to 1: it depends on cache hits, retries, redirects, and fallback; the exact count is recorded per attempt;
- logical request count remains >1.

### 10.2 Different runs

- Each run has its own `RunContext`, `RunEvidenceStore`, and run cache.
- Run caches are not shared.
- Existing vendor caches may be shared; they are recorded as `vendor_cache_hits`, not `run_cache_hits`.
- Memory writes are serialized by the existing lock and idempotency key.
- Manifest writes use per-run paths, atomic replace, and read-time INV-01 validation. A reader takes this sequence: read terminal manifest bytes and remember their hash; validate every bound artifact against that manifest; re-read the manifest bytes and compare the hash. If the manifest changed during validation, retry a bounded number of times or return incomplete; if validation fails, treat the run as failed/incomplete. A returned result carries the manifest hash and must be revalidated before reuse. No reader may cache a completed result without the manifest hash.
- Preferences remain the original global file and are not per-run; atomic replace gives last-writer-wins for concurrent local runs. The next startup reads that single file. A concurrent run may overwrite defaults; this is accepted for the single-user local D1 deployment.

### 10.3 Backtest

Each cell runs in its own `RunContext` and produces its own `FinalizedRunRecord`. The backtest log is per backtest run. No run cache is shared between cells.

---

## 11. Checkpoint recovery

`CheckpointCoordinator` defines a support matrix.

### 11.1 Supported

- LangGraph checkpoint state: messages, reports, debate state, current node.
- Run identity and config digest.
- A resume creates a new `run_id`; it does not reuse the interrupted invocation identity.
- Run evidence journal, if present and schema-compatible. Inherited records are tagged `origin_run_id`, `inherited=true`, and `origin_attempt_id`.
- Completed data results from the journal can rebuild the run cache, but inherited evidence is counted in separate `inherited_*` counters, not in the new run's execution counters.
- Metrics and availability can be reconstructed, but the coverage snapshot is recomputed and rebound to the new run_id with a new snapshot hash.
- Publish retry after a finalized record exists (publish-resume, not graph-resume).

### 11.2 Not supported

- In-flight external requests.
- In-flight LLM calls.
- Run cache entries without journal evidence.
- Resume after a record has been finalized and published.
- Resume across a changed graph signature, policy version, cache-key version, or record schema.
- Resume when the journal is missing, in strict mode.
- Resume of a partially published run through the graph; use publish-resume instead.

### 11.3 Degraded resume

Degraded resume is opt-in and only if the journal is missing but the graph checkpoint is valid. It sets `coverage_status=partial` only; `unknown` is not a D1 coverage state. Missing evidence for a critical requirement becomes a critical gap, so the gate deterministically blocks with REVIEW. Strict mode refuses the resume. Inherited evidence, if later recovered, remains attributed to its original run and is not silently counted as new execution.

### 11.4 Signature

The checkpoint signature includes:

- graph shape;
- analyst set;
- debate/risk depth;
- asset type;
- portfolio fingerprint;
- fixed `run_clock` (as_of_date, timezone, analysis_mode, mode_source);
- critical profile version and `contract_version`;
- policy catalog version;
- cache-key version;
- context assembler version;
- record and manifest schema versions.

A mismatch starts a new run or refuses resume; it does not silently reuse old state.

---

## 12. AI context layering, assembly, token limits, and compression

### 12.1 Layers

| Layer | Content | Compression |
|---|---|---|
| L0 | Safety and policy constraints, external content is data, tool limits, gate notice | Never compressed |
| L1 | Run identity, ticker, date, latest bar, provisional coverage view (view_version, current records/gaps), fallback labels | Never compressed; final snapshot is not injected |
| L2 | Role instructions, rating scale, task, output format | Never compressed |
| L3 | Evidence blocks: tool outputs, prefetch blocks, reports, provenance | Compressible |
| L4 | Working history: messages, debate history, prior turns | Compressible |
| L5 | Output contract and deterministic gate rules | Never compressed |

### 12.2 Assembly flow

1. Build L0, L1, L2, L5 from policy and run snapshot.
2. Add L3 evidence and L4 history.
3. Estimate input tokens against the effective input budget.
4. If above the soft threshold of the effective input budget, compress L3/L4 in priority order.
5. Re-inject L0/L1/L2/L5 after compression as a final constraint block, within the reserved reinjection space.
6. Record `context_manifest`: layers, estimated tokens, compression events, dropped evidence IDs, re-injected constraints.
7. Send to the model.

### 12.3 Token limits and compression thresholds

These are **work assumptions, pending approval**; no baseline experiment supports them.

| Policy | Work assumption | Status |
|---|---|---|
| Provider context window | 128k tokens | Pending; model-specific |
| Per-call input cap | 24k tokens | Provisional |
| Reserved output space | 6k tokens | Provisional |
| Reserved tool-definition space | 2k tokens | Provisional |
| Reserved constraint-reinjection space | 1k tokens | Provisional |
| Effective input budget | min(per-call input cap, context window - reserves) = 24k | Derived |
| Soft trigger | 80% of effective input budget = 19.2k tokens | Provisional |
| Hard limit | 95% of effective input budget = 22.8k tokens | Provisional |
| Evidence block cap | 4k tokens per block | Provisional |
| History cap | 8k tokens | Provisional |
| Compression summary cap | 2k tokens | Provisional |
| Compression strategy | deterministic truncation first; optional LLM summarization only if explicitly enabled | Provisional |

### 12.4 Re-injection

After any compression, the assembler appends a fixed block containing:

- L0 safety/policy summary;
- L1 coverage and critical gaps;
- L2 role and output contract;
- L5 deterministic gate rules.

Evidence omitted by compression is labeled as omitted; it is not silently removed.

---

## 13. Desensitization output boundaries

The full boundary list is in `docs/architecture/permission-model.md`. Summary:

- CLI stdout/stderr;
- application logs;
- error messages and tracebacks;
- run manifest;
- final-state JSON;
- report Markdown and HTML;
- memory log;
- preferences;
- run evidence journal;
- checkpoint SQLite;
- publish staging and publish manifest;
- telemetry and monitoring;
- coding-agent transcripts.

Rules:

- known secret values are exact-match scanned; pattern values use versioned rules with secret_rule_version/source/effective_at;
- audit endpoints use scheme + host + path only;
- preference restore endpoints may keep allowlisted non-sensitive query parameters and secret_ref names, never inline userinfo, sensitive query values, or fragments;
- configuration is allowlisted;
- all in-scope boundaries use `SecretRedactor`;
- redaction replaces only secret values and preserves structure and non-secret identifiers; over-redaction is forbidden;
- every write records write_scan_status; the terminal manifest records final run_scan_status; completed requires both clean or redacted;
- scanner/sanitizer/rule-version failure or an unredactable secret fails closed; dangerous content and affected formal output are blocked, while a minimal secret-free incident record is allowed;
- the scan proves only the defined scope, rules, and fixtures, not universal secret absence;
- secret scanning is a planned test, not a completed result.

---

## 14. Runtime AI and coding-agent permissions

- Runtime AI agents can read only provided context/evidence, call registered tools, and produce proposals. They cannot read environment variables, access files, run shell commands, access arbitrary networks, modify code, or write artifacts.
- Coding agents default to deny. Per-role and per-path whitelists are in `docs/architecture/permission-model.md`.
- D2 coding agents may write only `architecture-blueprint.md` and `docs/architecture/**`; they may read `docs/req/**`, `TradingAgents/**`, and `baseline/**`.
- D2 coding agents must not modify `TradingAgents/**`, `scripts/**`, `baseline/**`, `docs/req/**`, `.env`, secrets, or Git state.

---

## 15. Candidate comparison summary

| Candidate | Summary | D2 role |
|---|---|---|
| Lean A | RunContext lifecycle/DI; separate services; FinalizedRunRecord; publisher | **Recommended for review** |
| B | Event-sourced ledger + reducers; strongest construction guarantee; higher schema/replay cost | Retained comparison; re-decision option |
| C | Minimal decorators/contextvar; lowest cost; weakest bypass/consistency guarantee | Retained comparison; not recommended for zero-tolerance D1 |

Full comparison and M/D/U evidence status: `docs/architecture/evaluation-table.md`.

Lean A is a recommendation for review, not a team approval.

---

## 16. Document index

- [ADR 001 — Run governance](docs/architecture/adr/001-run-governance.md)
- [Invariants](docs/architecture/invariants.md)
- [Trace matrix](docs/architecture/trace-matrix.md)
- [Memory design](docs/architecture/memory-design.md)
- [Permission model](docs/architecture/permission-model.md)
- [Runtime policy catalog](docs/architecture/runtime-policy-catalog.md)
- [Evaluation table](docs/architecture/evaluation-table.md)
- [Open decisions](docs/architecture/open-decisions.md)
- [Requirements registry](docs/req/requirements.yaml)
- [Run manifest schema](docs/req/run-manifest-schema.json)
- [Requirements validator](docs/req/validate_requirements.py)

The D2 documents share a v0.1 draft / pending-human-review status. D1 v1.9.0 is the approved historical baseline; the current requirement revision is still pending human review.

---

## 17. Implementation and evidence status

- Application implementation: **not started**.
- Tests: **not started**.
- Runtime monitoring: **not implemented**.
- Benefits: **not measured**.
- Only the baseline facts in `baseline/runs/baseline-20261020-01/` are measured.
- Validation results bind the requirement/schema/script/evaluation hashes and support `--check` stale detection.
- D1 v1.9.0 is the approved historical baseline; the current requirement revision is pending human review; remaining open questions are non-blocking retention and concurrency items.
