# D2 Runtime Policy Catalog

Status: **v0.2 — ADD-R round 2 draft / pending human review**  
Date: 2026-11-11  
D1 basis: `docs/req/requirements.yaml` v1.14.1  
Approval basis: `FR-01`, `FR-02`, `FR-03`, `SB-01`, `INV-01`, `SR-01` approved; `FR-04`, `FR-05`, `FR-06`, `FR-07`, `FR-08`, `INV-02`, `QR-02` draft  
Implementation status: **design only; no application code changed**

---

## 1. Purpose and status

This catalog names every runtime policy needed by the full D1 v1.14.1 scope, its status, related requirements, and change impact. A policy is not approved just because it appears here.

Status values:

- **pending_decision** — needs a human decision;
- **work_assumption** — used to make the draft concrete, but may change;
- **design_only** — architecture design, not implemented;
- **provisional** — a value is proposed but not approved;
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
| `POL-CLOCK-01` | Fixed run clock and mode inheritance | D2 architecture proposal; pending human review | FR-03, FR-04 |
| `POL-GATE-01` | Safety gate, REVIEW, and risk branch | D1-required; D2 proposal pending human review | SB-01, FR-04, INV-01, INV-02 |
| `POL-PROPOSAL-01` | Portfolio Manager and model proposal source | D1-required; D2 proposal pending human review | SB-01, INV-01 |
| `POL-SNAP-01` | Permanent/recovery snapshot layout and cleanup dependency | D1-required; D2 proposal pending human review | FR-02, FR-05, FR-06, INV-01 |
| `POL-RISK-01` | Risk input authority and applicability | D1 draft; D2 proposal pending human review | FR-04, INV-02 |
| `POL-RISK-02` | Risk policy snapshot and exact comparison | D1 draft; provisional values; pending human review | FR-04, INV-02 |
| `POL-RISK-03` | Risk evidence, input artifact, and memory summary | D1 draft; D2 proposal pending human review | FR-04, INV-01, INV-02 |
| `POL-PUB-01` | Publish protocol and retries | D1-required; D2 proposal pending human review | FR-02, INV-01, FR-06 |
| `POL-PUB-02` | Post-commit corruption and diagnostics | D1-required; D2 proposal pending human review | FR-02, INV-01, FR-05 |
| `POL-LOCK-01` | Shared run ownership, lock order, and fencing | D1-required; D2 proposal pending human review | FR-02, FR-06, INV-01 |
| `POL-ARCH-01` | History, section manifest, and export | D1 draft; D2 proposal pending human review | FR-05, INV-01, SR-01 |
| `POL-REC-01` | Recovery snapshot, claim, fencing, and idempotency | D1 draft; D2 proposal pending human review | FR-06, QR-02 |
| `POL-PERF-01` | Recovery benchmark and provisional p95 | D1 draft; provisional target | QR-02 |
| `POL-MEM-01` | Memory idempotency and lifecycle | D1-required; D2 proposal pending human review | INV-01, FR-04, FR-06 |
| `POL-FIN-01` | Structured financial facts and metrics | D1 draft; D2 proposal pending human review | FR-07, FR-01, FR-03 |
| `POL-BRIEF-01` | Brief mandatory content and ordered budget | D1 draft; provisional budgets | FR-08, FR-03, FR-07 |
| `POL-BRIEF-02` | Brief token/quality evaluation and lifecycle | D1 draft; provisional thresholds | FR-08, INV-01 |
| `POL-CTX-01` | AI context layers | work_assumption | FR-02, FR-03, SB-01, FR-08 |
| `POL-CTX-02` | Token limits and compression thresholds | work_assumption; provisional | FR-02, FR-08 |
| `POL-RED-01` | Redaction boundaries and path confinement | D1-required; D2 proposal pending human review | SR-01, FR-05, FR-06 |
| `POL-CHK-01` | Checkpoint resume matrix | work_assumption | D2 design |
| `POL-PERM-01` | Runtime AI permissions | design_only | SR-01, FR-04, FR-07 |
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
  - explicit overrides are recorded with `profile_source=override`.
- **Inputs**: asset type, analysis mode, enabled capabilities, explicit override.
- **Outputs**: `effective_critical_profile`, `critical_gaps`, `coverage_status`.
- **Change impact**: `AvailabilityIndex`, `SafetyGate`, report generation, trace matrix, tests.
- **Related decision**: OQ-01 (resolved in D1).

### POL-COV-02 — Fallback coverage contract

- **Status**: D1-required; D2 proposal pending human review.
- **Required contract fields**: same capability/component, instrument/topic, requested window/as-of date, point-in-time rule, minimum record count, provenance, attempted/serving sources, allowed fallback class.
- **Default**: a fallback clears a gap only when it satisfies the full contract. Global news does not clear ticker news; undated Yahoo statements do not clear SEC financial statements; partial fallback leaves `fallback_partial`/`insufficient_evidence` and the gap remains.
- **Change impact**: `DataAccessService`, `AvailabilityIndex`, `SafetyGate`, tests, report labels.
- **Related decision**: D2-OD-04 (resolved in D1).

### POL-CACHE-01 — Query-key normalization

- **Status**: D1-required; D2 proposal pending human review.
- **Key fields**: vendor method, asset type, normalized instrument/topic, analysis date, requested window/lookback, method parameters, vendor selector digest, cache-key version.
- **Excluded**: retries, fallback attempts, call site, timing.
- **Change impact**: `DataAccessService`, cache hit rate, FR-01 tests, traceability.
- **Related decision**: OQ-04 (vendor-cache retention only).

### POL-CACHE-02 — Run cache / negative cache / retry

- **Status**: D1-required; D2 proposal pending human review.
- **Rules**: cache scope is one run; success and terminal failure/withheld/not_configured statuses are cached; retries happen before the terminal status; no cross-run run-cache reuse; existing vendor caches are counted separately.
- **Retry**: success, no_data, withheld, and not_configured may be terminal without retry; unavailable/error is terminal after retry/fallback budgets are exhausted.
- **Failure**: a cache/counting inconsistency terminates the current run; no in-run re-execution; diagnosis uses a new `run_id`.
- **Change impact**: counters, tool rounds, token usage, FR-01 tests.

### POL-CACHE-03 — Single-flight and run isolation

- **Status**: D1-required; D2 proposal pending human review.
- **Rules**: same `data_query_key` has one in-flight `query_execution`; concurrent callers wait; each run has its own run cache; existing vendor caches are recorded separately.
- **Failure**: inconsistency terminates the run; new `run_id` for diagnosis.
- **Change impact**: `DataAccessService`, concurrency tests, evidence counters.

### POL-COV-03 — Critical profile, run clock, and coverage snapshot

- **Status**: D1-required; D2 proposal pending human review.
- **Critical profile**: `profile_version`, `profile_source`, `contract_version`, `analysis_mode`, `asset_type`, per-requirement/component contracts, and `profile_hash`.
- **Run clock**: `as_of_date`, `now_utc`, `timezone`, `clock_source`, `analysis_mode`, `mode_source`; fixed at start; resume/replay inherits unless an override is recorded; a future date is rejected.
- **Coverage snapshot**: `critical_profile_hash`, `snapshot_hash`, `critical_gap_ids`, structured gaps, `provenance_digest`, `computed_by=program`.
- **Rule**: `coverage_snapshot.critical_profile_hash` must equal `critical_profile.profile_hash`.

### POL-PRE-01 — Mandatory data preflight

- **Status**: D2 architecture proposal; pending human review.
- **Timing**: after the running manifest and critical profile, before any analyst/model node.
- **Owner**: `PreflightCoordinator` calls `DataAccessService`.
- **Scope**: `market_price` for every run; stock income/balance/cashflow.
- **Shared cache**: preflight and analyst calls share the run cache and key; no duplicate fetch.
- **Failure**: recorded as evidence and a critical gap; analysis may continue only to a deterministic gate block.

### POL-EVD-01 — Evidence supports links and HTTP request counting

- **Status**: D1-required; D2 proposal pending human review.
- **Rule**: an executed record may carry multiple `supports` links; a `component_missing` record carries exactly one.
- **Counting**: `http_request_count` counts actual outbound requests per attempt, including retries/redirects; cache hits and local short-circuits are 0; `external_requests` is the sum.

### POL-CLOCK-01 — Fixed run clock and mode inheritance

- **Status**: D2 architecture proposal; pending human review.
- **Rule**: historical/current mode is derived once from the fixed clock, never from a later call to today. Resume/replay inherits the original clock unless a `clock_override` is recorded.
- **Change impact**: `RunContext`, `AvailabilityIndex`, `CheckpointCoordinator`, report, risk, tests.

### POL-PROPOSAL-01 — Portfolio Manager and model proposal source

- **Status**: D1-required; D2 proposal pending human review.
- **Node**: the original Portfolio Manager remains the terminal analysis node, wrapped by `PortfolioManagerAdapter`.
- **Inputs**: full analyst reports, investment plan, Trader plan, risk debate, applicable committed historical memory.
- **Output**: one unapproved `ModelProposal` with `rating` (five-tier or REVIEW), `text`, `source=portfolio_manager`, `source_refs`, model provider/id, and `proposal_status=unapproved`.
- **Rule**: Trader or risk-debater output is source material, never the final model proposal. The PM does not produce the formal decision or write formal artifacts; `SafetyGate` consumes the proposal.
- **Failure**: unparseable rating -> REVIEW proposal; the gate still applies `model_review`/`invalid_model_rating`.
- **Change impact**: `PortfolioManagerAdapter`, `SafetyGate`, report/memory audit fields, tests.
- **Related decision**: ARCH-OD-21.

### POL-GATE-01 — Safety gate, REVIEW, and risk branch

- **Status**: D1-required; D2 proposal pending human review.
- **Input**: one immutable program-produced `coverage_snapshot`, one `model_proposal` produced by `PortfolioManagerAdapter` (`source=portfolio_manager`), and when `FR-04` applies, the raw caller risk envelope (or absence) from which the gate validates, resolves policy, and evaluates. `SafetyGate.finalize` is the only caller of `RiskInputValidator`, `RiskPolicyResolver`, and `PortfolioRiskEvaluator`; applicability runs once inside the gate.
- **Status set**: gate `passed`/`blocked`/`error`; formal `approved`/`blocked_for_review`; `REVIEW` is a terminal sentinel outside the five-tier set.
- **Blocking rules**:
  - critical gap, coverage/gap contradiction, invalid/missing input, missing availability record, invalid profile, invalid rating, model REVIEW, stale/hash-mismatched snapshot -> blocked;
  - stock Buy/Overweight with missing/invalid/unsupported/stale/inconsistent/insufficient-cash/currency/policy input -> `portfolio_risk_input_invalid`;
  - risk limit breach -> `portfolio_risk_limit_exceeded`;
  - risk evaluator exception -> `error`, `portfolio_risk_evaluator_error`, failed run;
  - gate exception/timeout/internal error -> `error`, `gate_internal_error`, failed run.
- **Applicable risk always recorded**: stock Buy/Overweight records a passed, blocked, or error risk result even when coverage or another check already blocks. No entrypoint/tool runs a separate applicability or evaluation.
- **Policy status**: a valid provisional snapshot is used and labeled provisional; missing/invalid/incomplete policy blocks. "Not approved" is not "policy absent".
- **Formal body**: blocked decisions use the `review_class` matched to the primary reason; all reason codes are retained; the model proposal is retained as unapproved.
- **Boundaries**: the gate runs before the terminal manifest and every formal output with a formal decision; the running startup manifest may precede it with `not_run`; intermediate streaming/staging may show the proposal only when marked intermediate/unapproved.
- **Entry points**: CLI, programmatic `propagate`, backtest, checkpoint, headless/API, and recovery use the same gate.
- **Risk priority**: when coverage and an ordinary risk failure coexist, `critical_gap` is primary; an evaluator exception takes the higher-priority error path and `critical_gap` is secondary.
- **Change impact**: `SafetyGate`, entry points, publisher, memory, report, backtest, risk services, tests.

### POL-RISK-01 — Risk input authority and applicability

- **Status**: D1 draft; D2 proposal pending human review.
- **Authority**: caller/application supplies canonical decimal strings with provenance; model text, rendered portfolio text, and Markdown are never authoritative.
- **Single caller**: `SafetyGate.finalize` performs validation, policy resolution, applicability, and evaluation exactly once. No entrypoint/tool/recovery path performs a second applicability check.
- **Applicability**: `asset_type=stock` and model rating Buy/Overweight; first entry (`new_long`) and add (`add_long`) are in scope; crypto and other non-stock assets or Hold/Underweight/Sell/REVIEW/invalid rating may be `not_applicable`.
- **Unsupported**: short, derivative, leveraged, multiple-order, non-common-stock, or FX-conversion candidates block when applicable, not `not_applicable`.
- **Validation**: presence, type, decimal scale <=12 dp, finite/no exponent, applicability, one currency, valuation time, cash, exact amount/price identities, portfolio total.
- **Failure**: missing/invalid/unsupported/inconsistent/insufficient-cash/currency/stale input blocks; no default approval.
- **Related decisions**: OQ-09 (input source), OQ-11 (historical source).

### POL-RISK-02 — Risk policy snapshot and exact comparison

- **Status**: D1 draft; provisional values; pending human review.
- **Snapshot fields**: `policy_version`, `policy_ref`, `policy_digest`, `max_projected_weight`, `max_stop_distance`, `max_valuation_age_seconds`, precision rule, `threshold_status`, `human_approval_ref`.
- **Defaults**: 0.30 concentration and 0.05 stop distance are provisional classroom values; not approved financial policy. A valid provisional snapshot MAY be used only with `threshold_status=provisional` and `human_approval_ref=null`, and every result/report MUST label it provisional. An approved snapshot requires a non-null `human_approval_ref`.
- **Precision**: input <=12 dp; internal >=28 significant digits; exact compare; display 6 dp half-up; display rounding never affects pass/fail.
- **Valuation cutoff**: `min(run_clock.now_utc, end_of_day(as_of_date, timezone))`; future `as_of_date` rejected; stale/future valuation blocks.
- **Comparison**: projected weight and stop distance at most the limits pass; boundary equality passes; a dual breach retains both codes with `POSITION_LIMIT_EXCEEDED` primary.
- **Policy failure**: missing/incomplete/unknown/digest-mismatched snapshot blocks with `POLICY_SNAPSHOT_UNAVAILABLE`. Do not treat an unapproved (but valid provisional) policy as absent.
- **Related decisions**: OQ-10 (approval), OQ-12 (risk-policy evaluation).

### POL-RISK-03 — Risk evidence, input artifact, and memory summary

- **Status**: D1 draft; D2 proposal pending human review.
- **Valid input**: a normalized artifact under the run results directory with relative path, SHA-256, `hash_scope=file`, and scan scope; `input_digest = input_ref.sha256`.
- **Invalid input**: no normalized artifact; `input_ref=null`, `input_digest=null`, a safe `diagnostic_ref` with failure outcome/reason; no raw invalid values.
- **Artifacts**: risk result in manifest/final-state; report summary; new memory entry risk summary; reused historical entry keeps its own evidence.
- **Rule**: risk evidence does not create a second binding, memory key, or final authority.
- **Related decisions**: OQ-09, OQ-10.

### POL-PUB-01 — Publish protocol and retries

- **Status**: D1-required; D2 proposal pending human review.
- **Assumptions**:
  - running manifest before model calls;
  - staged publish with atomic per-file writes;
  - order: running manifest -> analysts/metrics/block -> brief/provisional view -> research/risk debate -> final coverage -> gate/record -> sections -> memory plan/reservation -> recovery snapshot (complete/read-back verified) -> memory idempotent write -> permanent snapshot write/validate -> terminal candidate + INV-01 -> ownership-protected atomic commit -> post-commit read -> cleanup last;
  - terminal manifest `run_status=completed` is the unique commit point; no independent marker;
  - permanent-snapshot files are staged/validated outside the lock before commit, then promoted in the short commit critical section; they are authoritative only after commit; the permanent snapshot is never created after cleanup;
  - permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; an optional `diagnostics/commit_evidence.json` is audit-only;
  - `record_hash` uses the §9.6.6 field-level projection with `artifact_binding.record_hash` and all result-carrying hashes removed; content digest and file-byte hash are distinct; only specified volatile run timestamps are excluded and risk/provenance evidence timestamps are preserved;
  - INV-01 passes on the candidate and on post-commit read;
  - memory remains pending/unreadable until commit; the allocation ledger appends `reserved` before the recovery snapshot, `failed` on abort before a completed manifest, and a rebuildable `committed` projection only after commit plus read verification; ledger write failure after commit does not block the manifest authority;
  - handled failure before commit uses the failure path;
  - forced termination preserves only the last running manifest;
  - 3 publish attempts with bounded backoff; no model calls; same `run_id`/`record_version`/`record_hash`; no duplicate memory;
  - cleanup failure after commit is a warning.
- **Related decisions**: D2-OD-02, OQ-02, ARCH-OD-07.

### POL-PUB-02 — Post-commit corruption and diagnostics

- **Status**: D1-required; D2 proposal pending human review.
- **Rule**: a post-commit read validation failure does not overwrite the committed terminal manifest, does not create a compensating `failed` state, and does not create a second publication. The committed manifest remains immutable evidence.
- **Handling**: the record is rejected as successful formal output; history/export return `CORRUPT_RECORD` without partial content; an independent diagnostic records the corrupt run, failed check, and artifact references. Manual repair is required.
- **Change impact**: `ArtifactPublisher`, `PublicationStatusReader`, `HistoryService`, `ExportService`, diagnostics, tests.
- **Related decision**: ARCH-OD-15.

### POL-SNAP-01 — Permanent/recovery snapshot layout and cleanup dependency

- **Status**: D1-required; D2 proposal pending human review.
- **Layout**: proposed in blueprint §9.6.1. Permanent `publication/` contains record, binding, report/section manifest, final-state, risk, metrics, memory binding, and versions. Temporary `recovery/` contains the self-contained recovery envelope. `locks/` contains `run.lock` and `lease.json`; `diagnostics/` contains independent corruption records.
- **Dependency**: report, history, export, and memory binding validation depend on `publication/` and the terminal manifest. They do not depend on `recovery/`. The hash DAG is acyclic: `binding.json` has no terminal-manifest hash; the terminal manifest hashes permanent files; no hashed file contains the manifest hash.
- **Cleanup**: after commit and post-commit validation, `recovery/`, claim, and staging may be cleaned. A terminal `recovery_snapshot_summary` is audit-only.
- **Change impact**: `PublicationSnapshotStore`, `RecoverySnapshotStore`, `ArtifactPublisher`, `HistoryService`, `ExportService`.
- **Related decision**: ARCH-OD-15/23.

### POL-ARCH-01 — History, section manifest, and export

- **Status**: D1 draft; D2 proposal pending human review.
- **History**: only committed + read-time INV-01; optional ticker/date filters intersect; strict `YYYY-MM-DD`; order analysis_date desc/ticker asc/run_id asc; limit 1-500 default 50; offset >=0 default 0; malformed/boolean/out-of-range -> `INVALID_FILTER`; bounded page with total_matches/returned/truncated/next_offset; corrupt records counted/warned separately.
- **Retrieval**: `get_run` revalidates terminal manifest, binding, complete report, section manifest, and permanent references; unknown -> `NOT_FOUND`; corrupt -> `CORRUPT_RECORD`; no partial content.
- **Sections**: only permanent publication snapshot + versioned renderer + recorded capability set; only applicable non-empty sections with path/fields/byte size/SHA-256; no foreign/stale/mixed.
- **Export**: `display_copy` vs `verified_package`; closure for every `reused_decision_ref`; unavailable proof -> `historical_reference_unverified`; non-empty target -> `EXPORT_CONFLICT`; legacy unchanged.
- **Change impact**: `HistoryService`, `PublicationSnapshotStore`, `ReportSectionManifestBuilder`, `ExportService`, `SecretRedactor`.
- **Related decision**: ARCH-OD-05 (index strategy).

### POL-REC-01 — Recovery snapshot, claim, fencing, and idempotency

- **Status**: D1 draft; D2 proposal pending human review.
- **First check**: read the terminal manifest and verify the permanent publication before reading `recovery/`. Committed + INV-01 + identity match -> idempotent success (no snapshot required); committed + identity conflict -> `RUN_ID_CONFLICT`; committed + corrupt permanent artifacts -> `CORRUPT_RECORD`; neither overwrites the manifest or auto-republishes.
- **Continuation order**: only for an uncommitted record, determine the memory reuse/new plan and reserve the version -> write the recovery snapshot containing the plan -> idempotent memory write -> permanent snapshot write/validate -> terminal candidate + INV-01 -> commit -> post-commit read -> cleanup.
- **Snapshot**: `snapshot_ready` = complete, durable, read-back-verified, self-contained, redacted; includes formal decision/binding, terminal candidate identity, section manifest/fixed render inputs, risk/policy references, original memory identity + reserved version, metric bundle when applicable, and versions; all references resolve internally with digests.
- **No model/data**: no LLM, external data, analysis graph, settlement, or reflection.
- **Claim/fencing**: uses the same `RunOwnershipLock` as normal publication; atomic per `run_id`; owner + fencing token; one active worker; stale lease reclaim increments the token; ownership/fencing is checked in the same critical section as each protected write; lost-lease writes rejected; failure isolated; retries bounded; at most one committed publication. Lock order is run lock then memory lock.
- **Lock-external preparation**: reads, parsing, rendering, and hashing run outside the locks; staged content is revalidated against current ownership/publication state inside the short critical section before use.
- **Identity**: terminal manifest first. Completed + matching identity -> idempotent success without `recovery/`; different content -> `RUN_ID_CONFLICT`; committed but permanent artifacts corrupt -> `CORRUPT_RECORD`; only uncommitted/absent continues with the recovery snapshot.
- **Memory**: may create the one original planned entry or complete it idempotently; never a different/duplicate entry; memory-disabled stays disabled.
- **Status**: `analysis_complete`, `snapshot_ready`, `committed`, `failed`, `quarantined`, `corrupt` are distinct; only committed + read-time INV-01 is history. Post-commit corruption preserves the committed manifest and uses an independent diagnostic.
- **Change impact**: `RecoveryService`, `RecoverySnapshotStore`, `RecoveryClaimStore`, `ArtifactPublisher`, `MemoryService`.
- **Related decision**: ARCH-OD-06 (lease/retry defaults).

### POL-PERF-01 — Recovery benchmark and provisional p95

- **Status**: D1 draft; provisional target.
- **Workload**: 100 committed publications + 10 pending valid snapshots; fixed 12-section report map; one risk evidence object with policy reference; one required memory idempotent write; rendered output and snapshot each <= 1,048,576 bytes; local supported filesystem; no competing writer.
- **Measurement**: 30 independently reset trials; nearest-rank p95; timing from immediately before claim/scan through final read-time validation, including locks, scans, rendering, risk evidence, publication, memory, cleanup; record platform/OS, CPU/RAM, filesystem/mount, sizes, section count, fixture version, commit, all samples/failures.
- **Target**: 2.000 s p95 **provisional** (OQ-13). Correctness and model-free behavior are zero-tolerance; no validation/hash/path/manifest/read-time check may be skipped to meet the target.
- **Change impact**: `RecoveryService`, benchmark harness, evidence table.

### POL-LOCK-01 — Shared run ownership, lock order, and fencing

- **Status**: D1-required; D2 proposal pending human review.
- **Scope**: normal publication and recovery use the same per-run `RunOwnershipLock`, owner identity, and fencing token. Single-user local filesystem only; no distributed consensus or second commit marker.
- **OS file lock vs logical lease**: `run.lock` is an OS advisory file lock held only for short critical sections (read lease, update owner/token/expiry, protected write); it is never held for the whole recovery or while waiting. `lease.json` is the logical lease (`owner_id`, `fencing_token`, `lease_expires_at`, status). Lease expiry does not release the OS file lock.
- **Critical section**: acquire the run file lock, re-read owner/fencing, compare with the caller token, perform the protected write, release. The check and write are in the same critical section; a pre-check outside the write is insufficient.
- **Order**: run lock -> memory lock. Never acquire the run lock while holding the memory lock. Memory-only operations may hold the memory lock alone; if they need run ownership, acquire the run lock first.
- **Takeover**: acquire the run file lock first (bounded wait or `LOCK_BUSY`); if acquired and the lease is expired, increment the fencing token and write the new owner. If a paused old process still holds the file lock, wait or return lock busy; never delete the lock file or force-unlock. The old owner rechecks the token on every protected write and is rejected with `LostOwnership`.
- **Release**: process exit releases the OS file lock if the OS does; the logical lease may remain active until expiry. Retry reacquires and re-checks. Cleanup releases only its own file lock and never removes another owner's claim or permanent records.
- **Change impact**: `RunOwnershipLock`, `ArtifactPublisher`, `RecoveryService`, `MemoryService`, tests.
- **Related decision**: ARCH-OD-16.

### POL-MEM-01 — Memory idempotency and lifecycle

- **Status**: D1-required; D2 proposal pending human review.
- **Rules**:
  - key = `(decision_id, entry_digest)` plus `(trade_date, ticker)`;
  - same key/hash = no-op; same decision_id/different entry_digest = conflict/tamper; different decision_id = new committed version;
  - atomic append under lock; finalized decision only;
  - entries physically `pending`; `commit_status` derived from the completed manifest, not stored in the entry;
  - reads include only committed entries; reused entries carry `reused_decision_ref`;
  - decision portion immutable; settlement/reflection append-only;
  - `MemoryReservationStore` is a persistent, append-only allocation history; the next version is `high_water + 1` over **all** historical allocations, including failed reservations; a failed version is never reissued; retries/recovery reuse their own reservation; `committed` is a derived projection from the terminal manifest, not a second commit condition;
  - same-day same-binding rerun reuses; different decision_id reserves version and supersedes; effective version is the highest committed; no post-commit old-entry write;
  - uncommitted entries are never reusable success; `MemoryRecoveryCoordinator` applies: A active -> bounded wait/`MEMORY_PENDING_RETRYABLE` without locks; A invalid with snapshot -> recovery under A's original run_id/reservation/snapshot; no snapshot -> `MEMORY_RECOVERY_UNAVAILABLE`; recovery failure -> `MEMORY_RECOVERY_FAILED`; binding conflict -> `MEMORY_CONFLICT`; no ownership transfer;
  - memory-disabled runs require no memory artifact; the ledger's `committed` projection is derived from terminal manifests, not a second commit condition;
  - risk summary only on a newly written entry; reused historical entry keeps its original;
  - retention/rotation absence is `not_available`, not a binding mismatch.
- **Change impact**: `MemoryService`, `MemoryReservationStore`, `TradingMemoryLog`, publish/recovery, INV-01/INV-02 tests.
- **Related decision**: D2-OD-06 (storage shape), ARCH-OD-20 (allocation authority/replay).

### POL-FIN-01 — Structured financial facts and metrics

- **Status**: D1 draft; D2 proposal pending human review.
- **Adapter boundary**: only `DataAccessService` calls the vendor. `SecEdgarAdapter` wraps the existing `sec_edgar.py` statement/JSON capability; `FinancialFactService` requests and normalizes facts through `DataAccessService`; `get_income_statement`/`get_balance_sheet`/`get_cashflow` use the same adapter, cache, counters, and provenance. No direct vendor call is allowed.
- **Timing**: facts, metrics, the metric block, and the conflict check occur after the fundamentals report exists and before research debate consumes it; final publication only persists the existing result.
- **Facts**: each fact separates **disclosure fields** (subject/accession/filing_ref/filed_at/form/source_fact_ref and raw concept/value/unit/currency/period/fiscal/sign) that preserve original evidence from **canonical fields** (fact_id/concept/period/fiscal identity/span/cumulative duration/sign/unit/currency/lineage) that may be validated or derived only by a recorded versioned rule with input evidence and source refs. A filing's fiscal year/quarter is not each historical fact's period identity. Missing/multiple plausible sources return unavailable/ambiguous; never use date proximity, equal value, column order, or a default. CIK never substitutes for accession/filing_ref.
- **Visibility**: `filed_at <= as_of_date`; latest filed restatement on or before as-of; near dates/equal values/same-day multiple accessions never merged without lineage; ambiguity -> typed n/a.
- **Metrics**: revenue YoY (quarterly/annual), QoQ, margins, TTM revenue/EPS, fiscal-year P/E and TTM P/E separately, current ratio, liabilities-to-assets, FCF, FCF YoY.
- **Formulas**: YoY uses prior fiscal year same quarter/span/cumulative duration; QoQ uses immediately preceding quarter; TTM = annual + current YTD - prior matching YTD; no quarter by subtraction; capex normalized positive; zero denominator/non-positive base/negative EPS/missing/currency/unit/period mismatch -> n/a.
- **Authority**: program-appended metric block regardless of tool use; metric block is numeric authority; conflict detection limited to structured metric claims; free-form prose limitation recorded.
- **Persistence**: `metric_evidence_bundle` in publication/recovery snapshot; recovery never refetches; missing/corrupt bundle blocks metric-dependent publication.
- **Disablement**: if `FR-07` is not enabled, no metric block requirement; if enabled, the bundle must be persisted.
- **Related decisions**: OQ-14 (reference manifest), OQ-15 (TTM EPS scope).

### POL-BRIEF-01 — Brief mandatory content and ordered budget

- **Status**: D1 draft; provisional budgets.
- **Scope and timing**: Bull Researcher, Bear Researcher, and three risk debaters only. The brief is generated/reused before these roles receive context, uses the program coverage view and its `coverage_view_version`, and is not generated after the final decision.
- **Replacement**: for the five target roles the brief replaces the four full analyst reports; other roles keep full inputs; full+brief are not injected together.
- **Mandatory and protected**: program `FR-03` gaps, `FR-07` metric block/sources, safety constraints; reserved first and never truncated; protected markers prevent generic compression from shortening them.
- **Compressible**: stance, key levels/triggers, conclusion.
- **Ordered resolution**: mandatory above hard cap -> reject; otherwise expand to hard cap if allowed; otherwise downstream-resolvable reference whose payload counts against the context hard cap; otherwise full report only if the policy explicitly allows it, mandatory content is complete, and it fits the context hard cap; otherwise `BRIEF_REJECTED`. Every branch obeys the context hard cap; no branch combines full report and brief for the same role.
- **Failure states**: `BRIEF_DISABLED` uses the normal full-input path; `BRIEF_FULL_REPORT` is an allowed fallback only under the stated conditions; `BRIEF_REJECTED` is terminal for the five-role context and fails closed at the context stage. No re-entry to normal input or generic compression after `BRIEF_REJECTED`.
- **Run status**: `BRIEF_REJECTED` -> `failed` at context stage; full artifacts may remain as evidence but no tradeable formal decision is produced.
- **References**: must be resolvable by the receiving consumer; unresolvable path is invalid.
- **Markers/Unicode**: deterministic fallback/rejection for missing/duplicate/forged/overlong markers; Unicode normalized.
- **Audit**: separate `context_audit_metadata`; full/formal/history/recovery unchanged; brief is not a formal artifact.
- **Related decision**: OQ-16.

### POL-BRIEF-02 — Brief token/quality evaluation and lifecycle

- **Status**: D1 draft; provisional thresholds.
- **Measurement**: token measurement uses the selected model/tokenizer; characters auxiliary.
- **Costs**: added output tokens = brief-generation output; reduced downstream input tokens = full-report input - brief input; added_output_cost = added_output_tokens x output price; reduced_input_cost_saving = reduced_downstream_input_tokens x input price; net_cost = added - reduced; net_tokens = added - reduced; negative means saving; if either price is missing, cost fields are null.
- **Quality**: record fidelity, key-number/gap preservation, `quality_loss` (positive = degradation), approved `quality_loss_max`, zero safety escapes, latency.
- **Lifecycle**: `blocked`, `ready`, `accepted`, `failed` with the frozen contract's evidence conditions; no saving claimed before `accepted`; unapproved threshold blocks acceptance.
- **Related decision**: OQ-16.

### POL-CTX-01 — AI context layers

- **Status**: work_assumption.
- **Layers**: L0 safety/policy (never compressed); L1 run identity + provisional coverage view (never compressed; final snapshot not injected as final); L2 role/output (never compressed); L3 evidence (compressible); L4 history (compressible); L5 output/gate rules (never compressed); L6 brief view for five roles (mandatory/compressible split; replaces the four full reports for those roles).
- **Assembly**: L0+L1+L2+L3/L4+L6; re-inject L0/L1/L2/L5 after compression. Protected mandatory blocks are never shortened; other roles keep full reports.
- **Change impact**: `ContextAssembler`, `DownstreamBriefBuilder`, prompts, token usage, tests.

### POL-CTX-02 — Token limits and compression thresholds

- **Status**: work_assumption; provisional.
- **Assumptions**: provider window 128k; per-call input cap 24k; reserves 9k; effective input budget = min(cap, window - reserves); soft trigger 80%; hard limit 95%; evidence block cap 4k; history cap 8k; compression summary cap 2k; deterministic truncation first; optional LLM summarization only if enabled.
- **Before compression is enabled**: over-budget raises `ContextBudgetError` and fails closed; no oversized prompt or silent constraint truncation. For the five target roles, the brief replaces full reports; a full-report fallback is allowed only when it fits the hard cap and is not combined with the brief.
- **Brief**: budgets from `POL-BRIEF-01`; token measurement from `POL-BRIEF-02`.
- **Related decision**: D2-OD-05, ARCH-OD-04.

### POL-RED-01 — Redaction boundaries and path confinement

- **Status**: D1-required; D2 proposal pending human review.
- **In-scope**: manifest, final-state, risk input/diagnostic, risk policy, memory entry, report metadata/content, section manifest, metric bundle, archive, history index/responses, recovery snapshot/diagnostics, export diagnostics, logs, preferences, error/gate/availability records, formal API return.
- **Out of scope**: vendor/provider logs, shell history, OS/network captures, external service logs.
- **Checks**: known-secret exact match; versioned pattern rules with version/source/effective_at; per-write `write_scan_status`; final `run_scan_status`; separate counters and scope.
- **URLs**: audit = scheme/host/path; restore = scheme/host/path + allowlisted non-sensitive query params + `secret_ref` names; no inline userinfo/sensitive query/fragment.
- **Redaction**: replace only secret values; preserve structure/status/reason codes/counts/timings/source/vendor/ticker/date/model/path; over-redaction forbidden.
- **Failure**: scanner/sanitizer/rule-version failure or unredactable secret fails closed; dangerous content/formal output blocked; minimal secret-free incident allowed; run failed at security stage.
- **Path**: history/export/recovery paths confined; traversal/absolute/symlink escape/out-of-root forbidden; non-empty export -> `EXPORT_CONFLICT`.
- **Claim limit**: a clean scan proves only the defined scope/rules/fixtures.

### POL-CHK-01 — Checkpoint resume matrix

- **Status**: work_assumption.
- **Supported**: graph checkpoint, messages, reports, debate state, evidence journal, rebuildable cache/metrics/availability. Resume creates a new `run_id`.
- **Inherited evidence**: tagged with origin_run_id/inherited and separate counters; coverage recomputed and rebound.
- **Not supported**: in-flight requests/LLM, cache without journal, finalized/published record, schema/policy/cache-key/context/clock mismatch, missing journal in strict mode.
- **Degraded mode**: explicit opt-in; coverage `partial` only; missing critical evidence becomes a gap and the gate blocks with REVIEW.
- **Before recovery phase is enabled**: `ResumeRejected(unsupported_phase)`; start a new run; no journal inheritance.
- **Distinction**: checkpoint resume is not startup publication recovery.
- **Related decision**: D2-OD-03.

### POL-PERM-01 — Runtime AI permissions

- **Status**: design_only.
- **Allowed**: provided context, registered tools, proposals, the brief for five debate roles.
- **Denied**: files, env, shell, arbitrary network, artifacts, gate override, code modification, authoritative risk input, metric block edits, history/recovery/export.
- **Change impact**: tool registry, agent runtime, permission tests.
- **Related decision**: D2-OD-08.

### POL-PERM-02 — Coding-agent permissions

- **Status**: design_only.
- **Default**: deny.
- **ADD-R**: write `architecture-blueprint.md` and `docs/architecture/**` only.
- **Future roles**: implementation, test, baseline operator, D1 editor, reviewer; see `permission-model.md`.
- **Change impact**: permission model, agent runtime, audit tests.

---

## 4. Behavior matrix reference

The unique behavior for normal, business-block, system-failure, over-budget, write-interruption, recovery-retry, and concurrency cases is defined in `architecture-blueprint.md` §13. This catalog owns the policy values and failure classes; the blueprint owns the end-to-end behavior.

Key invariants:

- A handled coverage/risk block is a completed run with a blocked formal decision; a gate exception is a failed run.
- Recovery never invents approval and never creates a second publication.
- Brief rejection never changes the full report or formal record.
- History/export never returns unverified or partial content.
- Disabled capabilities have explicit rejection/degradation, not silent bypass.

---

## 5. Work-assumption change impact

If a work assumption changes, revisit:

| Assumption changes | Affected interfaces/components | Affected documents |
|---|---|---|
| Critical-source set | `AvailabilityIndex`, `SafetyGate`, report, trace tests | `architecture-blueprint.md`, `invariants.md`, `trace-matrix.md`, `open-decisions.md` |
| Fallback substitute policy | `DataAccessService`, `AvailabilityIndex`, gate | `architecture-blueprint.md`, `invariants.md`, `evaluation-table.md` |
| Query-key normalization | `DataAccessService`, cache, tests | `architecture-blueprint.md`, `trace-matrix.md`, `open-decisions.md` |
| REVIEW/risk priority | `SafetyGate`, entry points, memory, backtest | `architecture-blueprint.md`, `memory-design.md`, `open-decisions.md` |
| Risk input/policy | `RiskInputValidator`, `RiskPolicyResolver`, `PortfolioRiskEvaluator`, gate | `architecture-blueprint.md`, `invariants.md`, `evaluation-table.md`, `open-decisions.md` |
| Publish/recovery order | `ArtifactPublisher`, `RecoveryService`, `MemoryService` | `architecture-blueprint.md`, `memory-design.md`, `open-decisions.md` |
| Portfolio Manager/model proposal source | `PortfolioManagerAdapter`, `SafetyGate` | `architecture-blueprint.md`, `adr/002-full-scope-add-r.md`, `open-decisions.md` |
| Permanent/recovery snapshot layout | `PublicationSnapshotStore`, `RecoverySnapshotStore`, `HistoryService` | `architecture-blueprint.md`, `invariants.md`, `open-decisions.md` |
| Shared run lock/ownership | `RunOwnershipLock`, `ArtifactPublisher`, `RecoveryService` | `architecture-blueprint.md`, `invariants.md`, `open-decisions.md` |
| Post-commit corruption handling | `ArtifactPublisher`, `PublicationStatusReader`, `HistoryService` | `architecture-blueprint.md`, `invariants.md`, `trace-matrix.md` |
| Memory reservation ledger | `MemoryReservationStore`, `MemoryService` | `memory-design.md`, `invariants.md`, `open-decisions.md` |
| Brief replacement/timing/markers | `DownstreamBriefBuilder`, `ContextAssembler` | `architecture-blueprint.md`, `permission-model.md`, `open-decisions.md` |
| Financial adapter/graph placement | `FinancialFactService`, `SecEdgarAdapter`, `FundamentalsAdapter` | `architecture-blueprint.md`, `permission-model.md`, `open-decisions.md` |
| History/export semantics | `HistoryService`, `PublicationSnapshotStore`, `ExportService` | `architecture-blueprint.md`, `invariants.md`, `open-decisions.md` |
| Metric formulas/periods | `FinancialFactService`, `FinancialMetricService` | `architecture-blueprint.md`, `invariants.md`, `evaluation-table.md`, `open-decisions.md` |
| Brief budgets/token/quality | `DownstreamBriefBuilder`, `ContextAssembler`, `TokenCounter` | `architecture-blueprint.md`, `evaluation-table.md`, `open-decisions.md` |
| Token limits/compression | `ContextAssembler`, prompts, cost metrics | `architecture-blueprint.md`, `evaluation-table.md`, `open-decisions.md` |
| Checkpoint support | `CheckpointCoordinator`, graph | `architecture-blueprint.md`, `invariants.md`, `open-decisions.md` |
| Coding-agent roles/paths | permission model, agent runtime | `permission-model.md`, `open-decisions.md` |

---

## 6. Implementation blockers versus acceptance-only items

| Class | Items | Effect |
|---|---|---|
| Implementation-start blockers | Risk input source (OQ-09), risk policy locator/approval record (ARCH-OD-03), shared lock/lease format (ARCH-OD-16), permanent/recovery layout (ARCH-OD-15/23), record_hash projection (ARCH-OD-24), memory reservation format/authority (ARCH-OD-20), SEC query contract (ARCH-OD-19), PM adapter/model-proposal source (ARCH-OD-21), uncommitted-memory status protocol (ARCH-OD-22), tokenizer/model (ARCH-OD-04) | Must be decided before the affected module starts; not a claim of approval. |
| Acceptance-only | Risk 30%/5% approved thresholds (OQ-10 approved-policy claims), QR-02 2.000 s/platform (OQ-13), brief budgets/quality thresholds (OQ-16), behavior-eval snapshots (D2-OD-09), manifest overhead (OQ-05) | Do not block starting implementation; block acceptance/completion claims. |
| Evidence/CI blockers | `yhx/requirements.yaml` absent (ARCH-OD-01), validator dependencies undeclared (ARCH-OD-02) | Block reproducible D1 validation/CI, not module design. |

## 7. Status

- Policies are classified as D1-required, D2 architecture proposals, provisional parameters, or design-only; none of the D2 additions is approved.
- No policy is implemented; human review of D2 remains pending.
- No threshold is measured unless it is a baseline observation.
- D1 v1.14.1; six approved, seven draft; human review pending.
