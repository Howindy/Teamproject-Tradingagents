# D2 Runtime Policy Catalog

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` v1.9.0 (historical baseline approved; current revision human review pending; IDs renumbered)
Implementation status: **design only; no application code changed**

---

## 1. Purpose

This catalog names every runtime policy that D2 needs, its status, its related requirements, and the impact of changing it. A policy is not approved just because it appears here.

Status values:

- **pending_decision** — needs a human decision;
- **work_assumption** — used to make the draft concrete, but may change;
- **design_only** — architecture design, not implemented;
- **baseline_measured** — a measured baseline fact, not a policy choice.

---

## 2. Policy index

| Policy ID | Name | Status | Related requirements |
|---|---|---|---|
| `POL-COV-01` | Critical-source set | D1-required; D2 proposal pending human review | FR-03, SB-01 |
| `POL-COV-02` | Fallback coverage contract | D1-required; D2 proposal pending human review | FR-03, SB-01 |
| `POL-CACHE-01` | Query-key normalization | D1-required; D2 proposal pending human review | FR-01 |
| `POL-CACHE-02` | Run cache / negative cache / retry | D1-required; D2 proposal pending human review | FR-01 |
| `POL-CACHE-03` | Single-flight and run isolation | D1-required; D2 proposal pending human review | FR-01 |
| `POL-COV-03` | Critical profile, run clock, and coverage snapshot | D1-required; D2 proposal pending human review | FR-03, SB-01 |
| `POL-PRE-01` | Mandatory data preflight | D2 architecture proposal; pending human review | FR-03, SB-01 |
| `POL-EVD-01` | Evidence supports links and HTTP request counting | D1-required; D2 proposal pending human review | FR-01, FR-03 |
| `POL-CLOCK-01` | Fixed run clock and mode inheritance | D2 architecture proposal; pending human review | FR-03 |
| `POL-GATE-01` | Safety gate and REVIEW | D1-required; D2 proposal pending human review | SB-01, INV-01 |
| `POL-PUB-01` | Publish protocol and retries | D1-required; D2 proposal pending human review | FR-02, INV-01 |
| `POL-MEM-01` | Memory idempotency | D1-required; D2 proposal pending human review | INV-01 |
| `POL-CTX-01` | AI context layers | work_assumption | FR-02, FR-03, SB-01 |
| `POL-CTX-02` | Token limits and compression thresholds | work_assumption | FR-02 |
| `POL-RED-01` | Redaction boundaries | D1-required; D2 proposal pending human review | SR-01 |
| `POL-CHK-01` | Checkpoint resume matrix | work_assumption | D2 design |
| `POL-PERM-01` | Runtime AI permissions | design_only | SR-01 |
| `POL-PERM-02` | Coding-agent permissions | design_only | D2 governance |

---

## 3. Policy details

### POL-COV-01 — Critical-source set

- **Status**: D1-required; D2 proposal pending human review.
- **Default profile**:
  - `market_price` is mandatory and cannot be removed; it is fetched by the deterministic preflight;
  - stock `financial_statements` is mandatory in every mode, independent of fundamentals-analyst selection, and is fetched by the deterministic preflight. Each of income, balance, and cashflow requires at least one annual and the latest quarterly period known by as_of, with filing date on or before as_of, as-filed point-in-time, and at least one record. Crypto has no financial_statements requirement;
  - current-date runs add `ticker_news` when the news analyst is enabled;
  - current-date runs add `social_sentiment` when the social analyst is enabled; its critical components are `sentiment_stocktwits` and `sentiment_reddit`, with at least one successful; `sentiment_news` is optional context;
  - historical mode excludes live-only `social_sentiment`, `prediction_markets`, `company_profile`, and `insider_transactions` from the critical set;
  - `macro_indicators`, `technical_indicators`, `global_news`, `company_profile`, `insider_transactions`, and `prediction_markets` are non-critical by default;
  - explicit overrides are recorded with `profile_source=override`.
- **Inputs**: asset type, analysis mode, enabled capabilities, explicit override.
- **Outputs**: `effective_critical_profile`, `critical_gaps`, `coverage_status`.
- **Change impact**: `AvailabilityIndex`, `SafetyGate`, report generation, trace matrix, tests.
- **Related open decision**: OQ-01 (resolved).

### POL-COV-02 — Fallback coverage contract

- **Status**: D1-required; D2 proposal pending human review.
- **Required contract fields**:
  - same capability and component;
  - same instrument or topic;
  - same requested window and as-of date;
  - point-in-time rule;
  - minimum record count;
  - provenance and attempted/serving sources;
  - allowed fallback class.
- **Default**: a fallback clears a gap only when it satisfies the full contract. Global news does not clear ticker news; undated Yahoo statements do not clear SEC financial statements; partial fallback produces `fallback_partial` or `insufficient_evidence` and the gap remains.
- **Change impact**: `DataAccessService`, `AvailabilityIndex`, `SafetyGate`, tests, report labels.
- **Related open decision**: D2-OD-04 (resolved).

### POL-CACHE-01 — Query-key normalization

- **Status**: D1-required; D2 proposal pending human review.
- **Key fields**:
  - vendor method;
  - asset type;
  - normalized instrument or topic;
  - analysis date;
  - requested start/end or lookback;
  - method-specific parameters such as indicator, series, frequency, or limit;
  - vendor selector digest;
  - cache-key version.
- **Excluded from the key**: retries, fallback attempts, call site, and timing.
- **Change impact**: `DataAccessService`, cache hit rate, FR-01 tests, traceability.
- **Related open decision**: OQ-04 (vendor-cache retention only).

### POL-CACHE-02 — Run cache / negative cache / retry

- **Status**: D1-required; D2 proposal pending human review.
- **Assumptions**:
  - cache scope is one run;
  - success and terminal failure/withheld/not_configured statuses are cached;
  - retries happen before caching the final status;
  - negative cache stores the final status/reason;
  - no cross-run run-cache reuse.
- **Retry**: vendor-specific retry policy remains as existing; the outcome is cached when the execution policy reaches a terminal state. Success, no_data, withheld, and not_configured may be terminal without retry; unavailable/error is terminal after retries and fallback budgets allow no further attempt.
- **Failure**: a cache/counting inconsistency or invariant violation terminates the current run; it does not clear and re-execute the same query inside the same run. Diagnosis uses a new run_id.
- **Change impact**: query-execution, HTTP-request, and vendor-cache-hit counts; tool rounds; token usage; FR-01 acceptance; tests.
- **Related open decision**: OQ-04.

### POL-CACHE-03 — Single-flight and run isolation

- **Status**: D1-required; D2 proposal pending human review.
- **Assumptions**:
  - same `data_query_key` has one in-flight `query_execution`;
  - concurrent callers wait for the same result;
  - each run has its own run cache;
  - existing vendor caches are recorded separately and may serve an execution without an external request.
- **Failure**: single-flight/counting inconsistency terminates the current run; a new run_id is used for diagnosis; the same query is never re-executed in the same run.
- **Change impact**: `DataAccessService`, concurrency tests, evidence counters.
- **Related open decision**: OQ-08.

### POL-GATE-01 — Safety gate and REVIEW

- **Status**: D1-required; D2 proposal pending human review.
- **Input**: one immutable program-produced `coverage_snapshot` and one `model_proposal`; the model cannot supply or mutate coverage or gaps.
- **Status set**: gate status `passed`, `blocked`, `error`; formal decision status `approved`, `blocked_for_review`; REVIEW is a terminal sentinel outside the five-tier set.
- **Blocking rules**:
  - critical gap, coverage/gap contradiction, invalid or missing input, missing availability record, invalid critical profile, invalid model rating, model REVIEW, stale or hash-mismatched snapshot -> blocked;
  - gate exception, timeout, or internal error -> error and fail closed.
- **Formal body**: blocked decisions use the review_class matched to the primary reason code (data insufficient, model-rating invalid, model REVIEW, gate/system error, invalid input, or coverage inconsistency); when multiple reasons occur, primary_reason_code is the first in the fixed priority list and all reason_codes are retained; the model proposal is retained separately as unapproved.
- **Boundaries**: gate runs before the terminal manifest and every formal output containing a formal decision; the running startup manifest may precede the gate with gate status not_run. Intermediate streaming/staging may show the proposal only when marked intermediate/unapproved.
- **Entry points**: CLI, programmatic propagate, backtest cell, checkpoint resume, and headless/API use the same gate.
- **Inputs and hashes**: coverage_snapshot, provenance_digest, and gate input_hash are recorded; gate failure uses error.stage = gate.
- **Change impact**: `SafetyGate`, entry points, publisher, memory, report, backtest, tests.
- **Related open decision**: OQ-06 (resolved).

### POL-PUB-01 — Publish protocol and retries

- **Status**: D1-required; D2 proposal pending human review.
- **Assumptions**:
  - a running manifest is written before model calls;
  - staged publish with atomic per-file writes;
  - commit order: running manifest → record → report → final-state → memory pending → terminal manifest candidate + INV-01 check → atomic terminal manifest commit → read-back verification;
  - the terminal manifest `run_status=completed` is the unique commit point; a complete marker is non-authoritative;
  - INV-01 must pass on the terminal candidate before commit and on read-back after commit;
  - memory remains pending/unreadable until the terminal manifest commits;
  - a handled failure before a normal FinalizedRunRecord uses FailureFinalizer/RunFailureRecord and replaces the running manifest with a failed terminal manifest;
  - a handled failure after finalization replaces the terminal manifest with failed if read-back verification fails;
  - forced termination is guaranteed only to preserve the last running manifest;
  - 3 publish attempts with bounded backoff;
  - no model calls during publish retry;
  - same run_id, record_version, and record_hash across retries;
  - retry does not duplicate the memory decision entry.
- **Change impact**: `ArtifactPublisher`, memory, tests, run status, manifest integrity.
- **Related open decision**: D2-OD-02, OQ-02.

### POL-MEM-01 — Memory idempotency and lifecycle

- **Status**: D1-required; D2 proposal pending human review.
- **Assumptions**:
  - key = `(decision_id, entry_digest)` plus `(trade_date, ticker)`;
  - same key/hash = no-op;
  - same decision_id with different entry_digest = conflict/tamper; different decision_id for same ticker/date creates a new committed version;
  - memory append is atomic under lock;
  - memory uses the finalized decision only;
  - entries are physically written with settlement_status=pending; commit_status is derived from the completed terminal manifest, not written into the entry; no separate mark-committed write;
  - reads include only committed entries from completed runs; reused historical entries carry reused_decision_ref and keep the current artifact run_id;
  - the decision portion is immutable after write;
  - settlement/reflection is append-only and cannot change the binding or formal decision fields;
  - same-day same-binding reruns reuse the entry; a different decision_id reserves a pre-commit entry_version and supersedes; effective version is derived from committed manifests; only same decision_id with a different entry_digest conflicts;
  - entry_version is reserved under the memory lock before commit and recorded in the terminal manifest; failed publication leaves a gap but no effective change; no post-commit old-entry write;
  - for each ticker/date, only the highest committed version contributes lessons/statistics; superseded versions are retained for audit;
  - memory-disabled runs require no memory artifact;
  - current decision commit and historical settlement/reflection are separate protocols: settlement appends only outcome/reflection to committed history and cannot change decision binding;
  - retention/rotation absence is recorded as memory not_available, not a binding mismatch.
- **Change impact**: `MemoryService`, `TradingMemoryLog`, publish retry, INV-01 tests.
- **Related open decision**: D2-OD-06 (storage shape only).

### POL-CTX-01 — AI context layers

- **Status**: D2 architecture proposal; work assumption pending human review.
- **Layers**:
  - L0 safety/policy — never compressed;
  - L1 run identity plus the current provisional coverage view — never compressed; the final immutable coverage snapshot is used by the gate and formal report, not injected as a final result into the running context;
  - L2 role/output — never compressed;
  - L3 evidence — compressible;
  - L4 history — compressible;
  - L5 output contract/gate rules — never compressed.
- **Assembly order**: L0 + L1 + L2 + L3/L4 + L5; re-inject L0/L1/L2/L5 after compression.
- **Change impact**: `ContextAssembler`, agent prompts, token usage, tests.

### POL-CTX-02 — Token limits and compression thresholds

- **Status**: D2 proposal with provisional parameters; pending human review.
- **Assumptions**:
  - provider context window: 128k;
  - per-call input cap: 24k;
  - reserved output/tool-definition/constraint space: 9k;
  - effective input budget: min(per-call cap, window minus reserves) = 24k;
  - soft trigger: 80% of effective budget = 19.2k;
  - hard limit: 95% of effective budget = 22.8k;
  - evidence block cap: 4k;
  - history cap: 8k;
  - compression summary cap: 2k;
  - deterministic truncation first; optional LLM summarization only if enabled.
- **Before compression phase is enabled**: over-budget context raises `ContextBudgetError` and the run fails closed; no oversized prompt or silent constraint truncation.
- **Change impact**: `ContextAssembler`, prompt sizes, token cost, compression tests.
- **Related open decision**: D2-OD-05.

### POL-RED-01 — Redaction boundaries

- **Status**: D1-required; D2 proposal pending human review.
- **In-scope boundaries**: manifest, final-state, memory decision entry, report metadata/content, logs, preferences, error/gate/availability records, formal API return.
- **Out of scope**: vendor/provider logs, shell history, OS/network captures, external service logs.
- **Checks**:
  - known-secret exact match against values configured or used in the run;
  - versioned pattern rules with fixed minimum categories and secret_rule_version/source/effective_at;
  - per-write write_scan_status and final run_scan_status are recorded separately;
  - separate counters and scan scope recorded in the manifest security object.
- **URL rules**:
  - audit endpoint = scheme + host + path only;
  - restore endpoint = scheme + host + path + allowlisted non-sensitive query params + secret_ref names;
  - no inline userinfo, sensitive query value, or fragment.
- **Redaction**: replace only secret values with a stable marker; preserve structure, status/reason codes, counts, timings, source/vendor names, tickers, dates, model ids, relative paths; over-redaction forbidden.
- **Failure**: scanner/sanitizer/rule-version failure or unredactable secret fails closed; dangerous content and affected formal output are blocked; a separate minimal secret-free security incident record is allowed; run failed at security stage.
- **Claim limit**: a clean scan proves only the defined scope, rules, and fixtures, not universal secret absence.
- **Change impact**: `SecretRedactor`, all writers, tests, permission model.
- **Related open decision**: OQ-03 and OQ-07 (resolved).

### POL-CHK-01 — Checkpoint resume matrix

- **Status**: work_assumption.
- **Supported**: graph checkpoint, messages, reports, debate state, evidence journal, rebuildable cache/metrics/availability. Resume creates a new run_id.
- **Inherited evidence**: tagged with origin_run_id, inherited=true, and separate inherited counters; coverage snapshot is recomputed and rebound to the new run_id.
- **Not supported**: in-flight requests/LLM, cache without journal, finalized/published record, schema/policy/cache-key/context/clock mismatch, missing journal in strict mode.
- **Degraded mode**: explicit opt-in; coverage_status=partial only (`unknown` is not a D1 state); missing critical evidence becomes a gap and the gate deterministically blocks with REVIEW.
- **Before recovery phase is enabled**: `ResumeRejected(unsupported_phase)`; start a new run; no journal inheritance.
- **Change impact**: `CheckpointCoordinator`, graph, evidence store, tests.
- **Related open decision**: D2-OD-03.

### POL-PERM-01 — Runtime AI permissions

- **Status**: design_only.
- **Allowed**: provided context, registered tools, proposals.
- **Denied**: files, env, shell, arbitrary network, artifacts, gate override, code modification.
- **Change impact**: tool registry, agent runtime, permission tests.
- **Related open decision**: D2-OD-08.

### POL-PERM-02 — Coding-agent permissions

- **Status**: design_only.
- **Default**: deny.
- **D2**: write `architecture-blueprint.md` and `docs/architecture/**` only.
- **Future roles**: implementation, test, baseline operator, D1 editor, reviewer; see `permission-model.md`.
- **Change impact**: permission model, agent runtime, audit tests.

---

### POL-COV-03 — Critical profile, run clock, and coverage snapshot

- **Status**: D1-required; D2 proposal pending human review.
- **Critical profile**: `profile_version`, `profile_source`, `contract_version`, `analysis_mode`, `asset_type`, per-requirement/component evidence contracts, and `profile_hash`.
- **Run clock**: `as_of_date`, `now_utc`, `timezone`, `clock_source`, `analysis_mode`, `mode_source`; fixed at run start and inherited on resume/replay unless an override is recorded.
- **Coverage snapshot**: `critical_profile_hash`, `snapshot_hash`, `critical_gap_ids`, structured `critical_gaps`, `provenance_digest`, `computed_by=program`.
- **Rule**: `coverage_snapshot.critical_profile_hash` must equal `critical_profile.profile_hash`; the gate rejects a mismatch.
- **Change impact**: `AvailabilityIndex`, `SafetyGate`, manifest, trace tests.

### POL-PRE-01 — Mandatory data preflight

- **Status**: D2 architecture proposal; pending human review.
- **Timing**: after the running manifest and critical profile, before any analyst/model node.
- **Owner**: `PreflightCoordinator` calls `DataAccessService`.
- **Mandatory scope**: `market_price` for every run; stock `financial_statements` components income/balance/cashflow.
- **Shared cache**: preflight and analyst calls use the same run-scoped `DataAccessService` cache and `data_query_key`; a preflight result is not re-fetched by an analyst.
- **Failure**: a failed mandatory preflight is recorded as availability evidence and a critical gap; analysis may continue only to a deterministic gate block, not a tradeable decision.
- **Change impact**: `PreflightCoordinator`, `DataAccessService`, `AvailabilityIndex`, graph entry, tests.

### POL-EVD-01 — Evidence supports links and HTTP request counting

- **Status**: D1-required; D2 proposal pending human review.
- **Rule**: one executed availability record may carry multiple `supports` links; a component_missing record carries exactly one.
- **Counting**: `http_request_count` counts actual outbound HTTP requests per attempt, including retries and redirects; cache hits and local not_configured/withheld count 0; `external_requests` is the sum.
- **Change impact**: `DataAccessService`, `RunEvidenceStore`, manifest, INV-01 tests.

### POL-CLOCK-01 — Fixed run clock and mode inheritance

- **Status**: D2 architecture proposal; pending human review.
- **Rule**: historical/current mode is derived once from the fixed run clock, not from a later call to today. Resume/replay inherits the original clock unless a `clock_override` is recorded.
- **Change impact**: `RunContext`, `AvailabilityIndex`, `CheckpointCoordinator`, report, tests.

## 4. Work-assumption change impact

If a work assumption changes, the following must be revisited:

| Assumption changes | Affected interfaces/components | Affected documents |
|---|---|---|
| Critical-source set | `AvailabilityIndex`, `SafetyGate`, report, trace tests | `architecture-blueprint.md`, `invariants.md`, `trace-matrix.md`, `open-decisions.md` |
| Fallback substitute policy | `DataAccessService`, `AvailabilityIndex`, gate | `architecture-blueprint.md`, `invariants.md`, `evaluation-table.md` |
| Query key normalization | `DataAccessService`, cache, tests | `architecture-blueprint.md`, `trace-matrix.md`, `open-decisions.md` |
| REVIEW policy/override | `SafetyGate`, entry points, memory, backtest | `architecture-blueprint.md`, `memory-design.md`, `open-decisions.md` |
| Publish order/retries | `ArtifactPublisher`, `MemoryService` | `architecture-blueprint.md`, `memory-design.md`, `open-decisions.md` |
| Token limits/compression | `ContextAssembler`, prompts, cost metrics | `architecture-blueprint.md`, `evaluation-table.md`, `open-decisions.md` |
| Checkpoint support | `CheckpointCoordinator`, graph | `architecture-blueprint.md`, `invariants.md`, `open-decisions.md` |
| Coding-agent roles/paths | permission model, agent runtime | `permission-model.md`, `open-decisions.md` |

---

## 5. Status

- Policies are classified as D1-required, D2 architecture proposals, provisional parameters, or design-only; none of the D2 additions is approved.
- No policy is implemented; human review of D2 remains pending.
- No policy threshold has been measured unless it is a baseline observation.
- D1 v1.9.0 is the approved historical baseline; the current requirement revision and all D2 policies remain pending human review.
