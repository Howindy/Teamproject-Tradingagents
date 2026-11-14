# D2 Architecture Blueprint — Lean A Extended, ADD-R Round 2

Status: **v0.2 — ADD-R round 2 draft / pending human review**  
Date: 2026-11-11  
D1 basis: `docs/req/requirements.yaml` v1.20.0 — 18 requirements, 119 fit criteria
Status basis: 17 requirements are draft pending human review; `QR-02` is deferred and outside current acceptance
Implementation status: **design only; no application code changed**  
Supersedes: blueprint v0.1 (D1 v1.9.0, 6 requirements, 54 acceptance criteria)

---

## 1. Purpose, scope, and authority

This blueprint defines the D2 architecture for the **complete functional scope** of D1 v1.18.0:

- all thirteen requirements are draft: `FR-01`, `FR-02`, `FR-03`, `FR-04`, `FR-05`, `FR-06`, `FR-07`, `FR-08`, `SB-01`, `INV-01`, `INV-02`, `SR-01`;
- `QR-02` is deferred and outside current acceptance.

The design direction remains **Lean A**: `RunContext` owns lifecycle and dependency wiring only; business rules live in separate, testable services; `FinalizedRunRecord` is the only source for formal display, persistence, memory, history, and export.

This round does not create:

- a second final decision authority;
- a second publication transaction or commit marker;
- a second context assembler;
- a second data path that bypasses the unified data access;
- a second memory identity or memory writer.

### 1.1 Authority and evidence rules

1. A requirement is approved only when `docs/req/requirements.yaml` says `status: approved`. Draft requirements are design scope, not approval. Historical approvals at v1.9.0 are evidence, not current approval of v1.18.0. No requirement is currently approved; all are draft and `QR-02` is deferred.
2. The architecture documents are **proposed** until a human review records approval. A recommendation in this document is not an approval.
3. **M** = measured baseline evidence. **D** = design expectation. **U** = unknown or unvalidated. **P** = provisional target pending human approval.
4. Only `baseline/runs/baseline-20261020-01/` contains measured runtime evidence. No new runtime measurement, test result, benefit, approval, or transcript is claimed by this round.
5. The baseline was produced by the **original** TradingAgents code. It does not demonstrate any new requirement, gate, risk evaluator, history, recovery, metric block, or brief.
6. Pending thresholds (risk 30%/5%, freshness window, QR-02 2.000 s, brief budgets and quality thresholds, PR-01 manifest overhead) remain provisional and are never described as approved.
7. This round modifies only `architecture-blueprint.md` and `docs/architecture/**`. It does not modify `docs/req/**`, application code, member proposals, or `baseline/**`.

### 1.2 Current evidence caveats

The requirements registry no longer references the absent `yhx/requirements.yaml`; FR-07 and FR-08 state that the personal-proposal source is not retained. The validator uses `pyyaml` and `jsonschema`, and `python3 docs/req/validate_requirements.py --check` passes. ARCH-OD-01 records the resolved provenance note; ARCH-OD-02 records the remaining CI dependency declaration.

There is no current approval-scope coupling because no requirement is approved. The former v1.14.1 coupling is resolved for status purposes: `FR-02` recovery-snapshot generation, the section manifest, the terminal manifest, artifact binding, `INV-01` binding/read-time verification, and the `SB-01` risk branch all remain pending human review together with `FR-04`/`FR-05`/`FR-06`/`FR-07`/`FR-08`/`INV-02`. A machine validation pass is not human approval.

### 1.3 Corrections applied in this revision

1. Structured financial facts, metric computation, the fundamentals metric block, and applicable conflict checks are moved **before research debate consumes the fundamentals report**. Final publication persists those existing results; it does not compute them after finalization.
2. The downstream brief is generated or reused **before the five target roles receive context**, uses the program coverage view and its version at that time, and is never regenerated after the final decision. The final safety gate still uses the final coverage snapshot.
3. For the five target roles, the brief **replaces** the four full analyst reports instead of being injected alongside them. Other roles keep full inputs. Mandatory gaps, metrics, sources, and safety constraints carry protection markers; no generic compression path may truncate them, and every fallback path obeys the context hard cap.
4. The publication transaction is reclosed: permanent-snapshot files are persisted and validated before the terminal commit; the recovery snapshot is complete, self-contained, and read-back verified before recovery is promised; the original memory entry is written idempotently; the terminal candidate is validated and atomically committed; read validation follows; cleanup is last. Post-commit read failure never overwrites the committed terminal manifest; the record is rejected as success and an independent diagnostic records the anomaly.
5. Memory version allocation considers already-reserved but uncommitted versions through a persistent, lock-protected monotonic reservation. Retries and recovery reuse the reservation; failure may leave a gap. The reuse/new-entry plan and version are fixed before the recovery snapshot is written.
6. Normal publication and recovery share one per-run ownership lock, owner identity, and fencing token. Ownership/isolation is checked in the same critical section as the protected write, not once before it. Takeover, lost-owner rejection, memory/run lock order, and release rules are explicit.
7. Risk validation and evaluation have one caller: `SafetyGate.finalize`. Applicability runs once inside the gate; the gate records an applicable risk result even when coverage already blocks. Valid provisional policy is used and labeled provisional; missing or invalid policy blocks. "Not approved" is not treated as "policy absent."
8. Only `DataAccessService` calls vendor adapters. `FinancialFactService` requests structured facts through it and normalizes the returned payload; the existing SEC statement capability is connected through an explicit SEC adapter boundary, preserving cache, counters, and provenance.
9. The core publication phase includes the minimum memory identity/idempotency, permanent snapshot, and recovery snapshot write/read verification. History listing, startup recovery scanning, export, and performance benchmarking follow. A disabled capability means "this phase is not implemented"; it is not evidence that the full requirement is satisfied.
10. The original terminal Portfolio Manager is retained and wrapped by `PortfolioManagerAdapter`; it produces the unapproved `ModelProposal` with explicit source fields. Trader or risk-debater output is never promoted to the final model proposal.
11. Temporary recovery material may be cleaned after commit/validation; formal report, history, memory binding, and export reads depend only on the permanent publication snapshot. A terminal recovery summary is audit-only.
12. Brief failure states are explicit: disabled uses normal full input; full-report fallback requires explicit policy permission, complete mandatory content, and hard-cap compliance; final `BRIEF_REJECTED` is terminal and cannot re-enter normal input or generic compression.
13. Cross-run same-decision uncommitted entries use `MemoryRecoveryCoordinator`: bounded wait/retryable, recovery under the original run identity/reservation/snapshot, typed missing-snapshot/failure/conflict statuses, and no ownership transfer.
14. OS file locks and logical leases are separated: the file lock is short-lived; the lease records activity; takeover acquires the file lock and increments fencing; lease expiry does not release the OS lock or authorize deleting the lock file.
15. No requirement is currently approved. `FR-02`/`INV-01`/`SB-01` and their recovery-snapshot, section-manifest, binding, and risk-branch obligations are draft and remain pending human review; draft status limits completion/acceptance claims.
16. Concrete implementation-start proposals are recorded for snapshot layout, the acyclic hash DAG, lock/lease records and state transitions, memory reservation authority/replay, and the per-fact SEC structured query contract; they are proposals pending review, not approvals.
17. Recovery checks the terminal manifest first: committed+verified+identity match is idempotent success without requiring `recovery/`; committed identity conflict or permanent-artifact corruption returns a typed conflict/corrupt result and never overwrites or auto-republishes. Only uncommitted records read the recovery snapshot.
18. `record_hash` uses a field-level canonical projection that excludes `artifact_binding.record_hash` and all result-carrying hashes; content digest and file-byte hash are separate, and only specified volatile run fields are excluded while risk/provenance timestamps are preserved.
19. SEC facts separate preserved disclosure fields from versioned canonical derivations; a filing's fiscal year/quarter is not copied as each historical fact's period identity, and missing/ambiguous evidence is never guessed.

---

## 2. ADD-R method and course requirements

`goal.md` §7 phase 2 and the course introduction (I25) require multi-round **Attribute-Driven Design (ADD)** driven by quality attributes and evidence, not a one-shot component diagram. This repository labels the current round **ADD-R** (Round-based ADD with Risk-first closure). ADD-R is a local working label, not a new course requirement.

ADD-R rules used in this round:

1. Start from architectural drivers, constraints, and quality-attribute scenarios derived from D1 and the baseline.
2. Review the existing architecture before adding components: retain, wrap, replace, or retire each existing asset explicitly.
3. For every driver, compare at least two candidates under the **same safety and functional contract**. A candidate that weakens the gate, binding, redaction, or read-time verification is not comparable.
4. Record per iteration: drivers, candidates, selection rationale, component decomposition, interfaces, error contracts, state ownership, review result, and evidence status.
5. Separate design expectation from measured evidence. A local fixture recomputation is requirement-evidence, not an application test.
6. Close the risky flows end to end: risk input/policy, metric fact/period chain, brief mandatory content and token budget, memory reuse/versioning, publication commit/read validation, recovery snapshot/fencing/idempotency, history/export dependency verification.
7. Define one behavior for normal, business-block, system-failure, over-budget, write-interruption, recovery-retry, and concurrency cases. Character and byte counts are auxiliary; the final model request must obey the token budget.
8. Phase implementation so a testable core closed loop exists before memory, recovery, metrics, and context enhancements. A disabled capability must reject or degrade explicitly.
9. Map every requirement and fit criterion to a component and a planned verification; give each deterministic safety boundary a negative-test direction.
10. Keep pending thresholds and unmeasured benefits honest; never fabricate decisions or test results.

### 2.1 ADD-R iterations in this round

| Iteration | Driver focus | Main decision | Status |
|---|---|---|---|
| 0 | Full-scope audit and retain/adjust assessment | Extend Lean A; do not rewrite the graph/agents | Proposed |
| 1 | Deterministic portfolio risk (`FR-04`, `INV-02`, `SB-01` risk branch) | Pure evaluator inside the shared `SafetyGate` | Proposed |
| 2 | Publication lifecycle, history, recovery (`FR-05`, `FR-06`, `QR-02`, `FR-02`, `INV-01`) | Extend `ArtifactPublisher` with permanent publication snapshot and recovery snapshot; claim/fencing is deferred | Proposed |
| 3 | Financial fact/metric evidence (`FR-07`, `FR-01`, `FR-03`) | Deterministic fact/metric service through `DataAccessService` | Proposed |
| 4 | Downstream brief and token budget (`FR-08`) | Brief view and budget policy inside the existing `ContextAssembler` | Proposed |
| 5 | Integration, compatibility, phasing, evidence review | Phased extension; adapters rather than rewrite | Proposed |

---

## 3. Scope and requirement inventory

| ID | Type | Status | Title | FCs | Phase |
|---|---|---|---|---|---|
| `FR-01` | functional | draft | Single execution per identical logical data query | 6 | 1 |
| `FR-02` | functional | draft | Lifecycle-complete run manifest | 11 | 1 |
| `FR-03` | functional | draft | Canonical data-availability state and critical-gap decision table | 10 | 1 |
| `FR-04` | functional | draft | Deterministic portfolio-risk evaluation before finalization | 9 | 1 |
| `FR-05` | functional | draft | Historical formal publication retrieval | 3 | 4 |
| `FR-06` | functional | draft | Startup recovery of pending formal publication | 6 | 4 |
| `FR-07` | functional | draft | Deterministic derived financial metrics | 10 | 3 |
| `FR-08` | functional | draft | Unified downstream analyst-report brief | 4 | 5 |
| `PR-01` | performance | draft | Bounded run-record write and end-to-end overhead | 4 | 1 |
| `CR-01` | cost | draft | Downstream brief local cost attribution and approved target | 5 | 5 |
| `GR-01` | governance | draft | Frozen independent reference set for financial metrics | 6 | 3 |
| `QR-01` | quality | draft | Live cache A/B quality and risk-policy separation | 5 | 1 |
| `QR-02` | performance | deferred | Bounded startup recovery performance | 2 | 4 |
| `SB-01` | invariant | draft | Deterministic fail-closed final-output gate | 12 | 1 |
| `INV-01` | invariant | draft | One bound formal result across artifacts and memory | 11 | 1 |
| `INV-02` | invariant | draft | Deterministic portfolio-risk authority and zero unsafe approvals | 6 | 1 |
| `SR-01` | security | draft | Secret-safe credential records | 7 | 1 |
| `SR-02` | security | draft | Path confinement and escape protection | 2 | 1 |

Draft total: 17 requirements, 117 fit criteria. Deferred total: 1 requirement, 2 fit criteria. Grand total: 18 requirements, 119 fit criteria.

Out of scope remains: replacing StockTwits, point-in-time SEC company profile, parallel debate execution, a full exchange calendar, multi-user authentication/encryption, portfolio simulation or order execution, a production LLM cache, direct vendor bypass, deriving a quarter by subtraction, and a second context assembler.

---

## 4. Architecture drivers

| Driver | Source | Why it shapes the architecture |
|---|---|---|
| D-01 Duplicate logical queries and cache ambiguity | `FR-01`, baseline repeated ticker-news query | Requires a run-scoped single-flight query service with distinct run-cache, vendor-cache, retry, fallback, and HTTP counters. |
| D-02 One lifecycle-complete, machine-readable run record | `FR-02` | Requires a running manifest before model calls, atomic terminal states, schema-valid counters, security results, and artifact hashes. |
| D-03 One canonical coverage and critical-gap truth | `FR-03`, `SB-01` | Requires a fixed run clock, effective critical profile, executed and missing records, deterministic aggregation, and one coverage snapshot. |
| D-04 Fail-closed formal decision separated from the model proposal | `SB-01`, `INV-01` | Requires a deterministic gate before any formal effect and an immutable record consumed by every writer. |
| D-05 One bound formal result across artifacts | `INV-01`, `FR-05`, `FR-06` | Requires canonical binding, digests, read-time verification, and permanent publication records. |
| D-06 Secret-safe records and path confinement | `SR-01`, `FR-05`, `FR-06` | Requires one redactor at every boundary, write/run scans, path confinement, and export conflict behavior. |
| D-07 Deterministic portfolio-risk authority | `FR-04`, `INV-02`, `SB-01` | Requires validated caller input, a locatable policy snapshot, exact-decimal evaluation, and no model/network dependency. |
| D-08 Historical visibility only for committed publications | `FR-05` | Requires permanent publication snapshots, section manifests, bounded listing, and read-time revalidation. |
| D-09 Model-free startup recovery with one publication | `FR-06` | Requires a recovery snapshot, a single-process duplicate-start guard, idempotent memory completion, and the same commit condition; multi-worker claim/fencing is deferred. |
| D-10 Bounded recovery performance with zero correctness loss | `QR-02` | Requires a fixed workload, monotonic timing, nearest-rank p95, and retained failures; the target is provisional. |
| D-11 Deterministic financial fact and metric evidence | `FR-07` | Requires structured fact identity, as-of visibility, period/fiscal-position matching, exact formulas, n/a reasons, and a persisted evidence bundle. |
| D-12 Bounded downstream brief without authority or quality loss | `FR-08` | Requires canonical mandatory content, separate mandatory/compressible budgets, token measurement, reference resolution, and a quality gate. |
| D-13 Compatibility and operability | Existing codebase, `goal.md` | Requires adapters for CLI, `propagate`, backtest, reporting, memory, and tools instead of a full rewrite. |

---

## 5. Constraints

| ID | Constraint |
|---|---|
| C-01 | Single-user local deployment; no multi-user authentication, encryption at rest, or access control in this scope. |
| C-02 | No new vendor, exchange calendar, portfolio simulator, order execution, slippage, fees, or FX conversion. |
| C-03 | Existing vendor caches may remain cross-run; the `FR-01` run cache is per-run and never shared. |
| C-04 | The existing Python/LangGraph graph, agents, tool registry, reporting renderer, and memory substrate remain; the change is a governance extension, not a rewrite. |
| C-05 | D1 v1.18.0 is the current registry; 17 requirements are draft and QR-02 is deferred. No new approval is inferred. |
| C-06 | The D2 round modifies `architecture-blueprint.md` and `docs/architecture/**`; the D1 status revision modifies `docs/req/**`. |
| C-07 | Application code, member proposals, and `baseline/**` are not modified. |
| C-08 | The 30% concentration, 5% stop-distance, freshness window, QR-02 2.000 s, and brief thresholds remain provisional until human approval. A passed risk check is not a loss guarantee. |
| C-09 | History, recovery, and export paths are confined to configured roots; non-empty export targets are never overwritten. |
| C-10 | One final authority (`SafetyGate`), one publication commit condition (terminal manifest completed plus read-time `INV-01`), one context assembler (`ContextAssembler`). |
| C-11 | Design expectations and measured evidence are labeled separately. No implementation or test is claimed. |
| C-12 | The requirements validator `--check` passes with the current unretained-source note and locally available dependencies; a clean CI dependency declaration remains a D4 task. |

---

## 6. Quality-attribute scenarios

| ID | Attribute | Source | Stimulus | Required response and measure |
|---|---|---|---|---|
| QS-01 | Correctness / determinism | `FR-01`, `FR-03`, `INV-01` | Same evidence and inputs, shuffled order, concurrent calls, warm/cold cache | Same business conclusions; duplicate query executions = 0; coverage/gap/binding mismatches = 0. |
| QS-02 | Safety | `SB-01`, `FR-04`, `INV-02` | Stock Buy/Overweight with missing, invalid, stale, inconsistent, insufficient-cash, unsupported, or over-limit risk input | No tradeable output; stable risk code; formal `REVIEW`; reason-specific `review_class`; unsafe approvals = 0. |
| QS-03 | Fail-closed system failure | `SB-01`, `FR-04` | Gate or evaluator raises, times out, or cannot parse input | Gate status `error`, run `failed`, primary reason `portfolio_risk_evaluator_error`/`gate_internal_error`, `review_class=gate_system_error`, no tradeable output. |
| QS-04 | Auditability | `FR-04`, `FR-07`, `INV-02` | Reviewer re-reads a completed publication | Risk input artifact digest, policy digest, metric fact IDs, formula/version, and metric result digest are independently recomputable. |
| QS-05 | Consistency | `INV-01`, `FR-05`, `FR-06` | Reader opens a completed run or a recovered run | Terminal manifest completed plus read-time `INV-01`; all artifacts bind; missing/corrupt content is never returned as success. |
| QS-06 | Security | `SR-01`, `FR-05` | Secret or path traversal appears in a record, history query, or export target | Known-secret/pattern matches = 0; out-of-root writes = 0; non-empty export returns `EXPORT_CONFLICT` and is byte-identical. |
| QS-07 | Recoverability | `FR-06`, `QR-02` | Interrupted publication; duplicate startup; stale lease; lost lease | Model/data/graph/settlement/reflection calls = 0; one committed publication per `run_id`; at most one memory entry; failed samples retained; correctness zero-tolerance. |
| QS-08 | Performance | `FR-02`, `QR-02` | Published manifest and recovery workload | Manifest write and end-to-end overhead measured separately against provisional thresholds; QR-02 is deferred; its future nearest-rank p95 target is 2.000 s provisional, with correctness never skipped. |
| QS-09 | Context efficiency and quality | `FR-08` | Long analyst reports and five downstream debate roles | Mandatory gaps/metrics/sources/safety constraints preserved; token budget obeyed; quality loss within the approved threshold and zero safety escapes; no token/cost saving claimed until accepted. |
| QS-10 | Modifiability / testability | All | New requirement or policy version | Service boundary and versioned policy allow table-driven tests without rewriting agents; deterministic rules are pure functions. |
| QS-11 | Compatibility | Existing codebase | Existing CLI, `propagate`, backtest, report, memory, and tool calls | Existing tests keep passing; legacy adapters preserve return shapes and write only through the publisher; no silent behavior change. |
| QS-12 | Operability | `FR-02`, `FR-05`, `FR-06` | Pending, failed, quarantined, or cleanup-failed publication | Distinct statuses; history excludes non-committed records; cleanup failure after commit is a warning and does not change history. |

---

## 7. Retain / adjust assessment of the existing architecture

| Existing asset | Decision | Adjustment |
|---|---|---|
| LangGraph graph, agents, debate order | Retain | Do not rewrite; insert preflight before analysts and finalization after the graph. |
| `tradingagents/dataflows/router.py` and vendor modules | Retain and wrap | `DataAccessService` owns key normalization, run cache, single-flight, counters, and provenance; direct vendor calls are forbidden for new paths. |
| `reporting.write_report_tree` and `_SECTIONS` | Retain as renderer | `ArtifactPublisher`/`PublicationRenderer` call it; add a versioned section manifest and digest. |
| `memory/log.py`, `settlement.py`, `reflection.py` | Retain as substrate | `MemoryService` becomes the only public writer/reader; extend for risk summary and recovery completion. |
| `cli/run.py`, `cli/display.py`, `cli/prefs.py` | Retain UX | `EntrypointAdapter` normalizes input; display consumes the published result; prefs use the audit/restore split. |
| `TradingAgentsGraph.propagate`, `_run_graph`, `record_decision`, `_log_state` | Retain graph, retire direct formal writes | `propagate` becomes a compatibility adapter that finalizes and publishes; internal writers require a finalized record. |
| `save_reports`, `save_sections`, HTML rendering | Retain as adapters | Require a finalized/published record; otherwise deterministic error. |
| `backtest.py` | Retain | Per-cell `RunContext`; same gate; `REVIEW` excluded from scoring. |
| `default_config.py` | Retain | Extend with policy identifiers and capability switches; no secrets. |
| Existing tests | Retain | Add regression and new suites; do not change existing test semantics. |
| D2 v0.1 Lean A design | Retain | Extend with risk, publication lifecycle, metrics, and brief capabilities. |
| D2 v0.1 trace matrix (6 requirements / 54 ACs) | Replace | Superseded by the 18-requirement / 119-FC matrix. |
| D2 v0.1 open decisions | Retain and extend | Resolved items stay resolved; new architecture open decisions are added. |

No existing public writer is deleted. Old writers are wrapped, made private, or require a finalized record. `propagate` keeps its `(final_state, signal)` return shape after publication.

---

## 8. ADD-R iteration record

### 8.1 Iteration 0 — Full-scope drivers and retain/adjust decision

- **Drivers**: D-01 through D-13; the draft requirements must be designed without creating duplicate authority, transaction, data path, or context entry.
- **Candidates**:
  - A: Extend Lean A with bounded capability services.
  - B: Add independent risk/archive/brief subsystems, each with its own gate or writer.
  - C: Rewrite into an event-sourced pipeline.
  - D: Add decorators/contextvars around the current graph.
- **Selection**: A. B violates the single-authority constraint. C has the highest schema/replay/compatibility cost and is retained only as a re-decision option. D cannot prove non-bypassability across CLI, programmatic, backtest, and recovery paths under the same contract.
- **Output**: retain/adjust table, full component catalog, phased plan.
- **Review result**: accepted for proposal; no human approval claimed.

### 8.2 Iteration 1 — Deterministic portfolio risk

- **Drivers**: D-07, `FR-04`, `INV-02`, the `SB-01` risk branch.
- **Candidates**:
  - R-A: Pure `PortfolioRiskEvaluator` invoked **only** by `SafetyGate.finalize`, which performs validation, policy resolution, applicability, and evaluation exactly once.
  - R-B: A separate `RiskGate` after `SafetyGate`.
  - R-C: Model-assisted risk narrative plus deterministic checks.
  - R-D: Pre-model hard filter on portfolio state.
- **Selection**: R-A. R-B creates a second final authority and ordering ambiguity. R-C cannot be deterministic and violates no-model/network requirements. R-D cannot know the candidate trade before the model proposes it and could block valid runs.
- **Decomposition**: `RiskInputValidator`, `PortfolioRiskEvaluator`, `RiskPolicyResolver`, `RiskEvidenceStore`, gate integration.
- **Interfaces**: `SafetyGate.finalize(proposal, coverage_snapshot, raw_risk_envelope?)` is the only entry; internally it calls `validate(raw) -> ValidatedRiskInput | RiskDiagnostic`, `resolve(policy_ref, config) -> PortfolioRiskPolicySnapshot`, and `evaluate(input, policy) -> PortfolioRiskResult` once. `ArtifactPublisher.stage_risk_evidence(payload)` writes the returned evidence.
- **Review**: applicability is stock + Buy/Overweight only; missing/unsupported blocks, never `not_applicable`; exact decimal comparison; dual-breach primary code; evaluator error follows the gate error path; no LLM/network/persistence in the evaluator; normalized input artifact and diagnostics are separate; current risk evidence versus reused historical memory evidence is distinct. A valid provisional policy is used and labeled provisional; missing/invalid policy blocks. The gate records the applicable risk result even when coverage already blocks.
- **Evidence**: design only; local fixtures are requirement-evidence; 30%/5% and freshness are provisional (OQ-10). OQ-10 blocks approved-policy claims, not the explicit provisional path permitted by `FR-04`.

### 8.3 Iteration 2 — Publication lifecycle, history, and recovery

- **Drivers**: D-08, D-09, D-10, `FR-05`, `FR-06`, `QR-02`, `FR-02`, `INV-01`.
- **Candidates**:
  - P-A: Extend `ArtifactPublisher` with a permanent publication snapshot, a temporary recovery snapshot, a single-process duplicate-start guard, and shared read-time verification; multi-worker claim/fencing is deferred.
  - P-B: A separate archive service with its own transaction and commit marker.
  - P-C: Re-run the graph/analysis to recover.
  - P-D: Directory-scan history without a section manifest.
- **Selection**: P-A. P-B creates a second commit authority. P-C violates model-free recovery and cost constraints. P-D can mix foreign/stale files and cannot prove binding.
- **Decomposition**: `PublicationSnapshotStore`, `ReportSectionManifestBuilder`, `HistoryService`, `ExportService`, `RecoveryService`, `RecoverySnapshotStore`, `RecoveryClaimStore`/`LeaseManager`, `RunOwnershipLock`, `PublicationStatusReader`.
- **Interfaces**: `publish(record) -> PublishResult`; `list_publications(filters) -> HistoryPage`; `get_run(run_id) -> VerifiedPublication`; `export(run_id, mode, target) -> ExportResult`; `scan_and_recover(startup) -> RecoveryReport`; `claim(run_id, owner) -> Claim`; `assert_owner(claim)`; `RunOwnershipLock.critical_section(run_id, owner, write_fn)`.
- **Review**: permanent-snapshot files are persisted and validated before the terminal commit; the recovery snapshot is complete, self-contained, and read-back verified before `snapshot_ready`; the original memory entry is written idempotently; the terminal candidate is validated, atomically committed, read back, and only then is temporary material cleaned. Post-commit read failure never overwrites the committed terminal manifest; it is rejected as success and recorded in an independent diagnostic. Terminal manifest completed plus successful read-time `INV-01` is the only commit condition; no independent marker; recovery uses saved records only; snapshot references resolve internally with digests; lost-lease writes are rejected; duplicate startup yields at most one publication; cleanup failure is a warning; history excludes pending/failed/quarantined; export uses `EXPORT_CONFLICT` and keeps legacy trees unchanged.
- **Evidence**: design only; QR-02 2.000 s is provisional (OQ-13).

### 8.4 Iteration 3 — Structured financial facts and metrics

- **Drivers**: D-11, `FR-07`, `FR-01`, `FR-03`.
- **Candidates**:
  - F-A: Deterministic `FinancialFactService` plus pure `FinancialMetricService`, reusing `DataAccessService`.
  - F-B: Model computes metrics from raw statement text.
  - F-C: New direct SEC client or parallel vendor path.
  - F-D: Derive a single quarter by subtraction.
- **Selection**: F-A. F-B reproduces the baseline error and is not verifiable. F-C duplicates counters/cache/provenance and violates the unified data path. F-D is explicitly prohibited.
- **Decomposition**: `FinancialFactService`, `FinancialMetricService`, `MetricEvidenceBundleBuilder`, `MetricConflictDetector`, `FundamentalsAdapter`.
- **Interfaces**: `fetch(ticker, as_of) -> StructuredFactSet`; `compute(facts, price, as_of) -> MetricBlock`; `build_bundle(facts, block) -> MetricEvidenceBundle`; `detect(block, claims) -> MetricConflict[]`.
- **Review**: fact identity uses subject + accession + filing_ref; as-of visibility; latest-filed restatement; ambiguous period/filing -> n/a; fiscal-position and cumulative-span matching for TTM; exact formulas; capital-expenditure sign normalization; separate fiscal-year and TTM P/E rows; program-appended block regardless of tool use; metric block is numeric authority; conflict detection is limited to structured claims; missing/corrupt bundle blocks metric-dependent recovery rather than triggering a live fetch. **Timing**: facts, metrics, the block, and the conflict check are produced after the fundamentals report exists but before research debate consumes that report; final publication only persists the existing block/bundle.
- **Evidence**: design only; NVDA fixture arithmetic is requirement-evidence; the non-NVDA reference manifest is not frozen (OQ-14).

### 8.5 Iteration 4 — Downstream brief and token budget

- **Drivers**: D-12, `FR-08`, `FR-03`, `FR-07`, `SB-01`, `INV-01`, `SR-01`.
- **Candidates**:
  - B-A: A brief view and versioned budget policy inside the existing `ContextAssembler`.
  - B-B: A separate brief context assembler.
  - B-C: Fixed character truncation of full reports.
  - B-D: Unchecked model-written brief.
- **Selection**: B-A. B-B creates a second context authority. B-C cannot preserve mandatory content. B-D can omit or forge required fields and is not auditable.
- **Decomposition**: `DownstreamBriefBuilder`, `TokenCounter`, `BriefBudgetPolicy` in `PolicyCatalog`, `BriefAuditStore`.
- **Interfaces**: `build(inputs, policy, tokenizer, coverage_view_version) -> Brief | BriefRejection`; `count(text, model) -> int`; `resolve_reference(handle, consumer) -> ReferencePayload | InvalidReference`.
- **Review**: the brief is generated before the five target roles receive context and reused across Bull, Bear, and the three risk debaters with the same recorded `coverage_view_version` unless the program view changes, in which case a new versioned brief replaces it. It uses the program coverage view at that time; the final gate still uses the final coverage snapshot. For the five roles it replaces the four full analyst reports (no duplicate full+brief injection); other roles keep full inputs. Mandatory content is canonical `FR-03` gaps, the `FR-07` metric block and sources, and safety constraints; mandatory budget is reserved first; protected markers prevent any generic compression from truncating them; ordered resolution expansion -> reference -> full report -> `BRIEF_REJECTED`; token measurement uses the selected model/tokenizer; character limits are auxiliary; full reports/formal records/history/recovery are byte-identical; audit metadata is stored separately; quality is judged only against the approved `quality_loss_max`; no saving is claimed before acceptance. No brief is generated after the final decision.
- **Evidence**: design only; no token/cost benefit measured; budgets and quality thresholds pending (OQ-16).

### 8.6 Iteration 5 — Integration, compatibility, phasing, and review

- **Drivers**: all; QS-11, QS-12.
- **Candidates**: big-bang rewrite versus phased extension.
- **Selection**: phased extension. The graph and agents remain; adapters migrate public surfaces; each phase has an exit test.
- **Review result**: no duplicate authority/transaction/context entry; all existing entry points are covered; disabled capabilities have explicit behavior; pending thresholds and unmeasured benefits are labeled; open decisions list the true coding blockers.

---

## 9. Selected architecture — Lean A Extended

### 9.1 Design principles

1. **One lifecycle owner**: `RunContext` fixes the clock, allocates `run_id`, owns paths, and wires services. It does not decide business policy.
2. **One evidence path**: all data, including SEC facts for metrics, goes through `DataAccessService`.
3. **One coverage truth**: `AvailabilityIndex` produces the only critical profile and coverage snapshot.
4. **One formal authority**: `SafetyGate` invokes the pure risk evaluator and produces the only `FinalizedRunRecord`.
5. **One publisher**: `ArtifactPublisher` performs the only formal publication, including recovery-driven completion.
6. **One context assembler**: `ContextAssembler` assembles full context and the bounded brief view.
7. **One memory writer**: `MemoryService` owns decision entries, versions, and recovery completion.
8. **One commit condition**: terminal manifest `run_status=completed` plus read-time `INV-01`; no independent commit marker.
9. **Permanent versus temporary**: the committed `publication_snapshot` is permanent; the `recovery_snapshot` and claim material are temporary pending envelopes.
10. **Design versus evidence**: every non-baseline claim is a design expectation until measured.

### 9.2 Component catalog

All new governance code lives under `tradingagents/run/`. Existing modules are wrapped, not rewritten.

| Component | Target module | Responsibility | Inputs | Outputs | Error contract | State ownership | Dependencies | Phase |
|---|---|---|---|---|---|---|---|---|
| `RunContext` | `run/context.py` | Lifecycle, run identity, fixed clock, paths, service wiring | Config, entrypoint, request | Run handle, `run_clock`, paths | `ConfigError`, `ClockError`, `FutureAnalysisDateError` | Run identity, clock, paths | PolicyCatalog, SecretRedactor | 1 |
| `EntrypointAdapter` | `run/entrypoints.py` | Normalize CLI/programmatic/backtest/headless input | Entry args | `RunRequest` | `UnsupportedEntrypoint` | None | RunContext | 1 |
| `PolicyCatalog` | `run/policy.py` | Versioned policy identities and defaults | Policy files/config | `PolicySet`, risk/brief/recovery policy handles | `PolicyVersionError`, `PolicySnapshotUnavailable` | Immutable policy snapshots | None | 1 |
| `Canonicalizer` | `run/canonical.py` | NFC/LF/sorted-key projection and SHA-256 | Objects | Canonical bytes, digests | `CanonicalizationError` | None | None | 1 |
| `DataAccessService` | `run/data_access.py` | Query key, run cache, single-flight, retry/fallback, counters, provenance | Query request, run context | `DataResult`, availability record | `VendorError`, `BudgetError`, `CacheScopeError` | Run cache, query ledger | Vendor adapters | 1 |
| `PreflightCoordinator` | `run/preflight.py` | Mandatory market price and stock statements before analysts | Critical profile | `EvidenceBatch` | `ProfileError`, `PreflightError` | None (writes evidence) | DataAccessService, AvailabilityIndex | 1 |
| `AvailabilityIndex` | `run/availability.py` | Critical profile, aggregation, gaps, coverage snapshot | Clock, config, records | `CoverageSnapshot` | `ProfileError`, `AggregationError` | Final coverage snapshot | RunEvidenceStore | 1 |
| `RunEvidenceStore` | `run/evidence.py` | Run-scoped records, missing records, supports, metrics | Records/events | Evidence snapshot, counters | `EvidenceError` | Run evidence | Canonicalizer | 1 |
| `SafetyGate` | `run/safety_gate.py` | Sole formal authority; sole caller of risk validation/policy resolution/evaluation; reason priority; review class; formal decision | Proposal, final snapshot, raw risk envelope (optional) | `FinalizedRunRecord` or failure; risk evidence payload for publisher | `GateInputError`, `GateError` | Formal decision | AvailabilityIndex, RiskInputValidator, RiskPolicyResolver, PortfolioRiskEvaluator | 1 |
| `FinalizedRunRecord` / `RunFailureRecord` | `run/finalization.py` | Immutable formal/failure contract | Gate output | Record | `SchemaError`, `RecordError` | Immutable records | Canonicalizer | 1 |
| `ArtifactPublisher` | `run/publisher.py` | Sole formal writer; stages/validates permanent snapshot and recovery snapshot; terminal commit; post-commit read; independent corruption diagnostic; cleanup last | Finalized record, evidence, render inputs, memory plan | `PublishResult`, terminal manifest, diagnostics | `PublishError`, `InvariantError`, `PostCommitCorruption` | Publication commit, artifact hashes, diagnostic records | Renderer, MemoryService, Snapshot stores, RunOwnershipLock | 1 |
| `MemoryService` | `run/memory_service.py` | Decision entry binding, reuse/new plan, idempotent write, recovery completion, settlement | Finalized record, recovery snapshot, reservation | `MemoryWriteResult`, `MemoryPlan` | `MemoryConflict`, `MemoryScanError`, `ReservationError` | Memory decision entries | TradingMemoryLog, MemoryReservationStore, SecretRedactor | 1/2 |
| `MemoryReservationStore` | `run/memory_reservation.py` | Persistent, append-only allocation history with a monotonic high-water mark over all historical allocations, including failed; retry/recovery reuse; new runs get higher versions | ticker/date, decision_id, owner/lease | `MemoryReservation` | `ReservationError`, `ReservationConflict` | Reservation ledger | MemoryLock, Canonicalizer | 1/2 |
| `PortfolioManagerAdapter` | `run/proposal.py` | Invoke the original Portfolio Manager with full reports/plans/risk debate/past memory; build the unapproved `ModelProposal`; no formal decision | Full analyst reports, investment plan, Trader plan, risk debate, past memory | `ModelProposal` | `ProposalError` | Model proposal (audit-only) | `agents/managers/portfolio_manager.py`, MemoryService, ContextAssembler | 1 |
| `MemoryRecoveryCoordinator` | `run/memory_coordination.py` | Handle a same-decision uncommitted entry in another run; bounded wait; trigger recovery under the original run identity; typed retry/conflict statuses | B decision/reservation, pending entry/lease status | `MemoryCoordinationResult` | `MemoryPendingRetryable`, `MemoryRecoveryUnavailable`, `MemoryRecoveryFailed`, `MemoryConflict` | Coordination status only; never ownership transfer | MemoryService, MemoryReservationStore, RecoveryService, RunOwnershipLock | 2 |
| `SecretRedactor` | `run/security.py` | Known-value/pattern scan, redact, path confinement | Value/record/path | `ScanResult`, redacted value | `SecurityFailure`, `PathEscape` | Scan results | None | 1 |
| `CheckpointCoordinator` | `run/checkpoint.py` | Graph-resume support matrix (distinct from publication recovery) | Checkpoint, signature | `ResumePlan` | `ResumeRejected` | Resume decisions | Evidence, PolicyCatalog | 2 |
| `LegacyWriterAdapter` | `run/adapters.py` | Convert old writers/entry points to finalized-record consumers | Legacy args/state | Published result | `LegacyWriteRejected` | None | Publisher, MemoryService | 1 |
| `RiskInputValidator` | `run/risk_input.py` | Canonical decimal input validation and applicability | Caller risk envelope | `ValidatedRiskInput` or `RiskDiagnostic` | `RiskInputError` | None | Canonicalizer | 1 |
| `PortfolioRiskEvaluator` | `run/risk_evaluator.py` | Pure deterministic concentration/stop-distance evaluation | Validated input, policy snapshot | `PortfolioRiskResult` | `RiskEvaluationError` | None | Decimal only | 1 |
| `RiskPolicyResolver` | `run/risk_policy.py` | Locate, load, validate, digest the policy snapshot | Policy catalog/path | `PortfolioRiskPolicySnapshot` | `PolicySnapshotUnavailable` | Immutable policy snapshot | PolicyCatalog | 1 |
| `RiskEvidenceStore` | `run/risk_evidence.py` | Build normalized input artifact or safe diagnostic payload | Validated input/diagnostic | Artifact payload, `input_ref`/`input_digest` | `RiskEvidenceError` | None (publisher writes) | Canonicalizer, SecretRedactor | 1 |
| `PublicationSnapshotStore` | `run/publication.py` | Permanent committed publication records and read validation | Committed record/sections | Verified publication | `CorruptRecord`, `NotFound` | Permanent publication snapshot | Canonicalizer, SecretRedactor | 4 |
| `ReportSectionManifestBuilder` | `run/render.py` | Versioned rendering and section manifest | Finalized record, fixed inputs, capability set | Sections, manifest, complete report | `RenderError` | None | `reporting.py` | 1/4 |
| `HistoryService` | `run/history.py` | Bounded listing and `get_run` revalidation | Filters, run_id | History page, verified publication | `InvalidFilter`, `NotFound`, `CorruptRecord` | Read-only | PublicationSnapshotStore | 4 |
| `ExportService` | `run/export.py` | `display_copy`/`verified_package`, closure, conflict | run_id, mode, target | Export result | `ExportConflict`, `HistoricalReferenceUnverified`, `PathEscape` | Export target only | HistoryService, SR-01 | 4 |
| `RecoveryService` | `run/recovery.py` | Startup recovery orchestration | Startup scan, claim | `RecoveryReport` | `RecoveryError` | Recovery orchestration | Snapshot/claim/publisher/memory | 4 |
| `RecoverySnapshotStore` | `run/recovery_snapshot.py` | Write/verify/read/quarantine temporary recovery envelope | Formal records, fixed inputs | Recovery snapshot | `SnapshotError` | Temporary recovery snapshot | Canonicalizer, SecretRedactor | 4 |
| `RecoveryClaimStore` / `LeaseManager` | `run/recovery_claim.py` | Per-run claim, lease, fencing token, commit ownership check | run_id, owner | Claim/lease | `ClaimRejected`, `StaleLease` | Claim/lease state | None | 4 |
| `RunOwnershipLock` | `run/ownership.py` | Shared normal-publication/recovery per-run lock; owner token + fencing; protected write critical section; takeover/release | run_id, owner, write function | Protected-write result | `LockBusy`, `StaleLease`, `LostOwnership` | Run lock/lease state | Local filesystem | 1 |
| `SecEdgarAdapter` (existing, wrapped) | `tradingagents/dataflows/vendors/sec_edgar.py` | Only vendor-facing SEC statement/JSON calls; returns raw statements and filing metadata; invoked only through `DataAccessService` | Query parameters | Raw statements/JSON + filing metadata | vendor errors mapped by `DataAccessService` | None | Vendor/HTTP | 1/3 |
| `PublicationStatusReader` | `run/publication.py` | Distinguish analysis_complete, snapshot_ready, committed, failed, quarantined | run roots | Status | `StatusError` | Read-only | Manifest, snapshot stores | 4 |
| `FinancialFactService` | `run/financial_facts.py` | Request structured SEC fact payloads through `DataAccessService`; normalize raw statement/filing payloads into the fact contract; never calls a vendor directly | Ticker, as_of | `StructuredFactSet` | `FactUnavailable`, `FactAmbiguous` | None (evidence cached) | DataAccessService, RunEvidenceStore | 3 |
| `FinancialMetricService` | `run/financial_metrics.py` | Pure metric formulas, period identity, n/a reasons | Fact set, price, as_of | `MetricBlock` | `MetricError` (n/a is a result) | None | Decimal only | 3 |
| `MetricEvidenceBundleBuilder` | `run/metric_evidence.py` | Persist facts/formulas/versions/digests | Fact set, block | `MetricEvidenceBundle` | `MetricEvidenceError` | None (publisher writes) | Canonicalizer | 3 |
| `MetricConflictDetector` | `run/metric_conflict.py` | Detect structured metric claims that contradict the block | Block, claims | `MetricConflict[]` | None | None | None | 3 |
| `FundamentalsAdapter` | `run/adapters.py` | Append metric block regardless of tool use; expose tool | Analyst state | Updated fundamentals output | `AdapterError` | None | Financial services | 3 |
| `ContextAssembler` | `run/context_assembler.py` | L0-L5 context, budget, compression, brief view; for the five target roles the brief replaces full analyst reports | Coverage view/version, reports, history, brief policy | `ContextBundle`, `BriefBundle` | `ContextBudgetError`, `BriefRejected` | None | DownstreamBriefBuilder, TokenCounter | 1/5 |
| `DownstreamBriefBuilder` | `run/brief.py` | Generate/reuse the five-role brief before context delivery; mandatory/compressible budget; protected markers; view version; audit metadata | Reports, gaps, metric block, policy, tokenizer, view version | `BriefBundle` | `BriefRejected`, `InvalidMarker` | None | TokenCounter, PolicyCatalog | 5 |
| `TokenCounter` | `run/tokens.py` | Model/tokenizer measurement | Text, model | Token count | `TokenizerUnavailable` | None | Model tokenizer | 5 |
| `BriefAuditStore` | `run/brief.py` | Persist separate `context_audit_metadata` | Brief metadata | Artifact payload | `AuditStoreError` | None (publisher writes) | SecretRedactor | 5 |

`RunContext` remains a lifecycle/DI container. It is not allowed to grow into a business-rule engine.

### 9.3 Principal interfaces

```text
RunContext.start(config, entrypoint, request) -> RunContext
RunContext.fail(exc) -> RunFailureRecord
DataAccessService.query(request, run_ctx) -> DataResult
DataAccessService.preflight(profile, run_ctx) -> EvidenceBatch
AvailabilityIndex.build_profile(clock, config) -> CriticalProfile
AvailabilityIndex.finalize(records) -> CoverageSnapshot
PortfolioManagerAdapter.propose(full_reports, investment_plan, trader_plan, risk_debate, past_memory) -> ModelProposal
SafetyGate.finalize(proposal, coverage_snapshot, raw_risk_envelope?) -> FinalizedRunRecord | RunFailureRecord
  # inside the gate, exactly once:
  RiskInputValidator.validate(raw) -> ValidatedRiskInput | RiskDiagnostic
  RiskPolicyResolver.resolve(policy_ref, config) -> PortfolioRiskPolicySnapshot
  PortfolioRiskEvaluator.evaluate(input, policy) -> PortfolioRiskResult
ArtifactPublisher.stage_risk_evidence(payload) -> RiskInputRef | DiagnosticRef
ArtifactPublisher.publish(record, recovery_inputs?) -> PublishResult
ArtifactPublisher.publish_failure(failure) -> FailurePublishResult
RunOwnershipLock.critical_section(run_id, owner, write_fn) -> ProtectedWriteResult
PublicationSnapshotStore.read(run_id) -> VerifiedPublication | NotFound | CorruptRecord
HistoryService.list_publications(ticker?, date?, limit, offset) -> HistoryPage
HistoryService.get_run(run_id) -> VerifiedPublication
ExportService.export(run_id, mode, target) -> ExportResult
RecoveryService.scan_and_recover() -> RecoveryReport
RecoveryClaimStore.claim(run_id, owner) -> Claim
RecoveryClaimStore.assert_owner(claim) -> None
MemoryReservationStore.plan(ticker, date, decision_id, owner) -> MemoryPlan
MemoryReservationStore.commit(reservation, entry_digest) -> None
MemoryReservationStore.fail(reservation) -> None
MemoryRecoveryCoordinator.resolve_pending(decision_id, entry_digest, waiting_run) -> MemoryCoordinationResult
FinancialFactService.fetch(ticker, as_of) -> StructuredFactSet
  # implementation: DataAccessService.query("sec_structured_facts", ...) -> SecEdgarAdapter payload -> normalize
FinancialMetricService.compute(facts, price, as_of) -> MetricBlock
MetricEvidenceBundleBuilder.build(facts, block) -> MetricEvidenceBundle
MetricConflictDetector.detect(block, claims) -> MetricConflict[]
ContextAssembler.assemble(view, reports, history, brief_view?) -> ContextBundle
DownstreamBriefBuilder.build(inputs, policy, tokenizer, coverage_view_version) -> BriefBundle | BriefRejected
MemoryService.store_finalized(record) -> MemoryWriteResult
MemoryService.complete_recovery(snapshot) -> MemoryWriteResult
MemoryService.get_past_context(...) -> str
SecretRedactor.scan(value, phase) -> ScanResult
SecretRedactor.assert_path(path, root) -> None
Canonicalizer.digest(projection) -> str
```

### 9.4 State ownership

| State | Owner | Rules |
|---|---|---|
| Run identity, clock, paths | `RunContext` | Created once; future `as_of_date` rejected before analysis/risk. |
| Query executions, run cache, counters | `DataAccessService`/`RunEvidenceStore` | Run-scoped; never shared; terminal outcomes cached. |
| Critical profile and coverage snapshot | `AvailabilityIndex` | Program-only; immutable final snapshot; model cannot mutate. |
| Risk input artifact/diagnostic | `RiskEvidenceStore` builds; `ArtifactPublisher` writes | Valid input only; invalid input produces no raw-value artifact. |
| Risk policy snapshot | `RiskPolicyResolver` | Locatable, versioned, digest-bound; explicit provisional or approved status; missing/invalid blocks. |
| Portfolio risk result | `PortfolioRiskEvaluator` | Pure result; no persistence; returned only to `SafetyGate`. |
| Model proposal | `PortfolioManagerAdapter` creates; `SafetyGate` consumes | Unapproved; source=portfolio_manager; Trader/risk-debater output is only a source reference. |
| Formal decision | `SafetyGate` | Only formal authority; `REVIEW` on block/error. |
| Finalized record | `SafetyGate` creates; `ArtifactPublisher` publishes | Immutable; retries reuse identity. |
| Publication snapshot | `PublicationSnapshotStore` | Files written/validated before terminal commit; authoritative only after commit; permanent and immutable. |
| Recovery snapshot | `RecoverySnapshotStore` | Complete/self-contained/read-back verified before `snapshot_ready`; temporary pending envelope; cleanup after commit. |
| Run ownership lock/lease | `RunOwnershipLock` | One per `run_id`; owner + fencing token; checked inside the same critical section as the protected write; stale takeover increments. |
| Recovery claim/lease | `RecoveryClaimStore` | Owner + fencing token; uses the same per-run ownership lock as normal publication; lost-owner writes rejected. |
| Memory entries | `MemoryService` | Immutable decision portion; append-only settlement. |
| Memory version reservation | `MemoryReservationStore` | Persistent, append-only allocation history; next version is `high_water + 1` over all historical allocations including failed; retries/recovery reuse; failed versions never reissued. |
| Pending same-decision coordination | `MemoryRecoveryCoordinator` | Bounded wait without locks; recovery under the original run identity/reservation/snapshot; typed retry/conflict; never ownership transfer. |
| Metric evidence bundle | `MetricEvidenceBundleBuilder` builds; publisher writes | Produced before research debate and persisted in publication/recovery snapshots; recovery never refetches. |
| Brief and audit metadata | `DownstreamBriefBuilder`/`ContextAssembler`; audit payload persisted by publisher | Generated before five-role context, reused with a recorded view version; a view only; never mutates full/formal/history/recovery artifacts. |

### 9.5 Dependency rules

- `run/` may import existing `tradingagents/agents`, `dataflows`, `memory`, `reporting`, and `cli` modules only through adapters.
- **Only `DataAccessService` may call vendor adapters.** The existing `tradingagents/dataflows/vendors/sec_edgar.py` capability is wrapped by `SecEdgarAdapter` and invoked only by `DataAccessService`; it returns raw statements/JSON plus filing metadata and is responsible for no policy or fact normalization.
- `FinancialFactService` calls `DataAccessService.query("sec_structured_facts", ...)`, receives the adapter payload, and normalizes it into `financial_fact`s. It never imports or calls a vendor module directly. The same query boundary supplies run cache, counters, provenance, and as-of visibility; `get_income_statement`, `get_balance_sheet`, and `get_cashflow` use the same adapter and cache.
- `PortfolioRiskEvaluator` and `FinancialMetricService` are pure: no LLM, network, vendor, persistence, UI, or clock reads beyond provided inputs.
- `PortfolioManagerAdapter` invokes the original Portfolio Manager and produces the only `ModelProposal`; no Trader or risk-debater output is promoted to the final model proposal.
- `SafetyGate` is the only caller of `RiskInputValidator`, `RiskPolicyResolver`, and `PortfolioRiskEvaluator`. No entrypoint or tool performs an independent applicability/risk evaluation.
- `MemoryRecoveryCoordinator` never transfers an uncommitted entry's ownership to another run. It may only trigger recovery under the original run identity, original reservation, and original recovery snapshot.
- `HistoryService` and `ExportService` read through `PublicationSnapshotStore`; they do not scan arbitrary report directories as authority.
- `RecoveryService` may call only saved-record services, the renderer, the publisher, the ownership lock, and the memory completion path; it may not call the graph, LLM, vendors, settlement, or reflection.
- `ContextAssembler` is the only context entry; `DownstreamBriefBuilder` is a helper, not an alternate assembler. For the five target roles, the brief replaces the four full analyst reports rather than being added beside them.
- Lock order is fixed: acquire the per-run `RunOwnershipLock` before the memory lock when a protected write needs both; never acquire the run lock while holding the memory lock. All ownership/fencing checks occur inside the same critical section as the protected write.

### 9.6 Concrete design choices for implementation start

These are reviewable proposals, not approvals. They make the module boundaries concrete enough to start without inventing behavior.

#### 9.6.1 Permanent and temporary directory/reference layout

```text
<results_dir>/<run_id>/
  run_manifest.json                  # running -> terminal; unique commit record
  publication/                       # permanent, authoritative only after commit
    record.json                      # FinalizedRunRecord
    binding.json                     # artifact_binding + record_hash; no terminal-manifest hash
    report/complete_report.md|.html
    report/section_manifest.json
    final_state.json
    risk/input.json | risk/diagnostic.json
    risk/policy.json
    risk/result.json
    metrics/metric_block.json
    metrics/metric_evidence_bundle.json
    metrics/conflicts.json
    memory/entry_binding.json
    versions.json
  recovery/                          # temporary pending envelope
    recovery_snapshot.json
    inputs/...
  locks/
    run.lock                         # OS advisory lock file; short-lived
    lease.json                       # logical lease/fencing record
  diagnostics/
    post_commit_corruption.json      # independent audit diagnostic
```

- `publication_ref` = `{root: "publication", files: [{relative_path, sha256, hash_scope: "file"}], record_hash}`; it contains no terminal-manifest hash. All paths are relative and confined.
- Report, history, export, and independent verification resolve only inside `publication/` and the terminal manifest. They never require `recovery/`.
- The terminal manifest may retain `recovery_snapshot_summary` (status, digest, created_at) as **audit information only**. It is not a verification dependency; after cleanup, `get_run`, memory binding validation, and `verified_package` MUST still work from `publication/`.
- `recovery/` is self-contained while it exists; after successful commit and post-commit validation, it may be removed. A missing `recovery/` after cleanup is not corruption.

#### 9.6.2 Lock and lease record/state transitions

- `run.lock` is an OS advisory lock used only for short critical sections: read lease, update owner/token/expiry, and perform the protected write. It is never held for the whole recovery, never held while waiting for another run's memory, and never held across a model call.
- `lease.json` is the logical lease: `{run_id, owner_id, owner_started_at, fencing_token, lease_expires_at, status: active|released|expired|taken_over, updated_at}`.
- State transitions under `run.lock`: `unclaimed -> active`; `active -> active` (renew, token unchanged); `active -> released`; `expired -> active` by takeover (increment token, replace owner); `active -> taken_over` for the old owner when it observes a newer token.
- Lease expiry does not release the OS file lock. If a paused old process still holds `run.lock`, a new owner may only wait bounded or return `LOCK_BUSY`; it must not delete the lock file or force-take ownership. Once the file lock is acquired, the takeover atomically increments `fencing_token` and writes the new owner. The old process must re-check the token inside every later protected write and is rejected with `LostOwnership`.
- Memory lock is short-lived and ordered after the run lock. Waiting for another run's pending memory holds neither lock.

#### 9.6.3 Memory reservation ledger authority and recovery

- `memory/reservations.jsonl` (or an equivalent sidecar under the memory lock) is an append-only allocation history authoritative for **version allocation**, not for decision content. Each record: `{ticker, trade_date, decision_id, entry_version, owner_run_id, status: reserved|committed|failed, fencing_token, created_at, committed_at, failure_reason}`.
- The allocator keeps a persistent, lock-protected **high-water mark over every historical allocation, including failed reservations**. The next version is `high_water + 1`. A failed reservation permanently occupies its version; it never leaves the high-water mark and is never reissued.
- A retry/recovery reuses its own reservation keyed by the original `run_id` and `decision_id`; a different run must receive a higher version. Effective version remains the highest `entry_version` whose source terminal manifest is `completed` and binds the entry.
- `committed` is a derived projection: it is true only when the terminal manifest is `completed` and read-time `INV-01` passes. A ledger commit mark is an audit/cache aid, not a second commit condition; if missing or if the ledger write fails after commit, it is rebuilt from the terminal manifest. Append `reserved` before the recovery snapshot, `failed` on abort before a completed manifest, and the `committed` projection only after commit plus read verification.
- Ledger replay/repair: replay the append-only allocation records to reconstruct the high-water mark including failed versions; rebuild `committed` projections from terminal manifests. Do not derive allocation history solely from committed manifests (that would lose failed reservations). If the allocation history is missing or corrupt, stop new allocation, restore from a durable backup or operator-approved reconstruction, and never silently reset the watermark or reissue a failed version.
- Recovery of an uncommitted reservation uses the original `run_id`, original `entry_version`, and original recovery snapshot. The reservation is never transferred to another run. A binding conflict is never overwritten.

#### 9.6.4 SEC structured query input/output contract

`DataAccessService.query("sec_structured_facts", request) -> StructuredFactPayload`

- **Input**:
  ```text
  {ticker, subject_id? (CIK), as_of_date,
   forms? ["10-K", "10-Q"], concepts? [...],
   periods? {annual: n, quarterly: n, ytd: n},
   filing_ref_required: true}
  ```
- **Output** (returned by `SecEdgarAdapter`, normalized by `FinancialFactService`): each fact is a self-describing record, not an unlinked row plus a separate filing list.

  ```text
  {subject_id, source: "SEC EDGAR", source_retrieved_at,
   facts: [{
     fact_id,                          # canonical stable id (derived)
     disclosure: {                     # original evidence, preserved
       subject_id, accession_no, filing_ref, filed_at, form,
       source_fact_ref, raw_concept, raw_value, raw_unit, raw_currency,
       raw_period_start?, raw_period_end?, raw_fiscal_year?, raw_fiscal_quarter?,
       raw_span?, raw_sign?, restates_fact_id?, supersedes?
     },
     canonical: {                      # validated/derived, versioned rules
       concept, value, unit, currency,
       period_start, period_end, fiscal_year, fiscal_quarter,
       span: annual|quarter|ytd|instant,
       cumulative_duration_days, sign,
       restates_fact_id?, supersedes?
     },
     derivation: {
       normalization_rule_version, derived_fields[], input_evidence_refs[],
       source_refs[], status: original|normalized|derived|ambiguous|unavailable, reason?
     }
   }],
   provenance: {...}}
  ```

- **Disclosure fields (must preserve raw evidence)**: `subject_id`, `accession_no`, `filing_ref`, `filed_at`, `form`, `source_fact_ref`, raw concept/tag, raw value, raw unit, raw currency, raw period fields when present, raw fiscal fields when present, raw sign/capex presentation, and explicit restatement/supersession identifiers. The adapter preserves these; the normalizer may copy/attach them but must not overwrite them.
- **Canonical fields (validated or derived by versioned rules)**: `fact_id`, canonical concept, canonical period start/end, per-fact fiscal year/quarter, span, cumulative duration, canonical sign, canonical unit/currency (no FX conversion), and explicit restatement/supersession links. The normalizer may derive these only from explicit evidence and a recorded `normalization_rule_version`; each derived field records its input evidence and source references.
- **Filing-level versus fact-level identity**: a filing's fiscal year/quarter is filing metadata and MUST NOT be copied as every historical fact's period identity. Each fact needs its own period/fiscal identity or explicit derivation evidence. A missing/ambiguous period identity returns `FactUnavailableError`/`FactAmbiguousError`.
- **Prohibited inference**: never connect a fact to a filing/period by date proximity, equal value, column order, or a default. If more than one fact remains a plausible source, return ambiguity; if required evidence is absent, return unavailable.
- **Errors**: `VendorUnavailableError`, `NoMarketDataError`, `VendorNotConfiguredError`, `FactAmbiguousError`, `FactUnavailableError`, mapped by `DataAccessService`; no raw vendor call outside the adapter.
- The existing `get_income_statement`, `get_balance_sheet`, and `get_cashflow` tools use the same query path, run cache, counters, and provenance. `FinancialFactService` performs validation/normalization and records derivation metadata; the adapter does not decide metric semantics.

#### 9.6.5 Digest and hash DAG

The permanent artifacts form a directed acyclic hash graph. A file that is hashed by the terminal manifest must not contain the terminal manifest hash.

| Artifact | Digest covers | Explicitly excludes | Order |
|---|---|---|---|
| `record.json` | Canonical `FinalizedRunRecord` content and `artifact_binding` fields, using the §9.6.6 projection with `artifact_binding.record_hash` and all result-carrying hashes removed | Run-level generated/evaluated/finished timestamps, `run_clock.now_utc`, local paths, cache counters, terminal-manifest hash, recovery-snapshot hash, record/self/file hashes | 1 |
| `binding.json` | `artifact_binding` fields plus the already-computed `record_hash` | Terminal-manifest hash, its own file hash, recovery-snapshot digest, commit-evidence hash, any field that would feed back into `record_hash` | 2 |
| `report/section_manifest.json` | Section paths, fields, byte sizes, SHA-256, complete-report digest | Terminal-manifest hash, binding file hash, recovery digest | 3 |
| `final_state.json`, `risk/*`, `metrics/*`, `memory/entry_binding.json` | Their own canonical content and referenced evidence digests | Terminal-manifest hash, binding file hash, recovery digest | 3 |
| `recovery/recovery_snapshot.json` | Self-contained inputs, formal decision/binding, memory plan/reservation, versions | Final terminal-manifest hash; it may carry terminal-candidate identity (`run_id`, `decision_id`, `record_hash`, reservation) | 4 |
| terminal `run_manifest.json` | `publication_ref.files` hashes (including `binding.json`), formal decision, security scans, section manifest, metric bundle, memory binding, and `recovery_snapshot_summary` (audit-only) | Its own hash; any file that contains its hash; optional commit-evidence hash | 5 |
| `diagnostics/commit_evidence.json` (optional) | Terminal-manifest hash and read-time validation result | Never hashed by the terminal manifest; never a commit condition | 6 (after commit) |

- `binding.json` never stores a terminal-manifest hash or a full terminal-manifest file hash.
- The terminal manifest never hashes itself. Readers compute its hash from the manifest bytes and use it as a read-time token.
- If an audit summary of the terminal manifest is needed, use `diagnostics/commit_evidence.json`; it is outside the permanent hashed set and is not a second commit authority.
- A `recovery_snapshot_summary` inside the terminal manifest may record status/digest/created-at as audit information. It does not make `recovery/` a required verification dependency.
- Computation order is fixed as above; a later artifact may hash an earlier one, never the reverse.

#### 9.6.6 record_hash projection and file-byte hashes

`record_hash` is a **canonical content digest**, not `sha256(record.json bytes)`.

1. Build the canonical content projection.
2. **Exclude** `artifact_binding.record_hash` and every other field that carries the computed result or a derivative of it (including `publication_ref.record_hash`, binding self-hash, terminal-manifest hash, file hashes, commit-evidence hash).
3. Compute `record_hash = SHA-256(canonical projection)`.
4. Fill `artifact_binding.record_hash`.
5. Serialize `record.json` and `binding.json` to bytes.
6. Compute each file's byte-level SHA-256 for `publication_ref`.
7. Build the terminal manifest from the file hashes.

**Excluded volatile run fields** (only those allowed by the requirement): run-level `generated_at`, `evaluated_at`, `finished_at`, `run_clock.now_utc`, local absolute paths, cache counters, computed snapshot timestamps, and any terminal/file/self hash.

**Preserved evidence timestamps**: risk `evaluated_at`, valuation time/cutoff, attempt/evidence timestamps, provenance timestamps, filing `filed_at`, and other source-evidence timestamps are retained in their own evidence fields and are not treated as run-level volatile fields. A change in risk evidence timestamp must change the risk evidence digest/record projection where required, not be silently dropped by the record-hash exclusion.

A retry must produce the same `record_hash` for the same canonical decision content. The file-byte hash may differ only if serialization bytes change; the two hash kinds must not be conflated.

---

## 10. Entry points and adaptation

### 10.1 Entry-point matrix

| Entry point | Current path | Target path | Compatibility |
|---|---|---|---|
| CLI analysis | `cli/main.py` → `cli/run.py` | `CliEntrypoint` → `RunContext` → graph → `SafetyGate` → `ArtifactPublisher` | Existing prompts/options keep working; final display uses the published result. |
| Programmatic graph | `TradingAgentsGraph.propagate` → `_run_graph` | `run()` returns `PublishedRunResult`; `propagate()` adapter finalizes and returns `(final_state, signal)` | Return shape preserved; raw proposal only through an explicit audit interface. |
| Root demo | `TradingAgents/main.py` | Programmatic `run()` | Remove direct writer use; demo prints the published decision. |
| Backtest | `backtest.py` | Per-cell `RunContext` → `run()` → same gate | `REVIEW` excluded from scoring; per-cell memory isolation. |
| Data tool calls and prefetch | `agents/tools.py`, `dataflows/router.py`, `sentiment_analyst.py` prefetch | `DataAccessService` adapter around the registered tools and prefetch | Same tool names/arguments; run cache, counters, and evidence are added; direct vendor bypass forbidden. |
| Direct report writer | `reporting.write_report_tree` | Internal renderer called by `ArtifactPublisher` | Direct public call without a record fails deterministically. |
| Direct memory writer | `memory/log.py:store_decision` | `MemoryService.store_finalized`/`complete_recovery` | Legacy method becomes internal or record-dependent. |
| Graph state writer | `trading_graph.record_decision` | Proposal event only | No direct `_log_state` or memory write. |
| `save_reports` | `TradingAgentsGraph.save_reports` | Adapter through the publisher | Requires a finalized/published record. |
| History/export CLI | None | `HistoryService`/`ExportService` adapters | New read-only commands; no legacy migration. |
| Startup recovery | None | `RecoveryService.scan_and_recover` at startup | No recovery when disabled: explicit `unsupported_phase`. |

### 10.2 Old-writer policy

- `reporting.write_report_tree` and HTML rendering remain rendering primitives called only by the publisher/renderer.
- `TradingMemoryLog.store_decision` becomes internal to `MemoryService`.
- `TradingAgentsGraph._log_state` becomes internal to `ArtifactPublisher`.
- `TradingAgentsGraph.record_decision` records the model proposal, not the formal decision.
- `TradingAgentsGraph.save_reports` is a compatibility adapter requiring a finalized record.
- Direct calls without a `FinalizedRunRecord` fail with a deterministic error and never fall back to an unfinalized path.
- `propagate` publishes before returning; a caller cannot obtain a formal result without publication.

### 10.3 Compatibility and deprecation

| Surface | Approach | Regression evidence |
|---|---|---|
| `propagate` | Adapter; same tuple after publication | Existing programmatic tests plus published-result tests. |
| `_run_graph`/`record_decision` | Internal proposal/finalization path | Writer-bypass audit. |
| `save_reports` | Adapter requiring a record | Report regression and negative direct-call tests. |
| `write_report_tree` | Internal renderer | Rendering regression and section-manifest tests. |
| `store_decision` | Internal to `MemoryService` | Memory idempotency/conflict regression. |
| CLI display | Consumes published result | CLI smoke and blocking-display tests. |
| Backtest | Per-cell published result | Backtest regression and memory isolation. |

No rewrite of agents or graph structure is planned. `propagate` return semantics, report/memory writers, and backtest callers are explicitly migrated with adapters and tests.

---

## 11. Data flow

### 11.1 Normal run

```text
Entrypoint
  -> RunContext.start(config)
       -> reject future as_of_date
       -> fix run_clock (as_of_date, now_utc, timezone, mode)
       -> allocate run_id, paths
  -> PolicyCatalog load
  -> AvailabilityIndex.build_profile(run_clock, asset, analysts, overrides)
  -> write running manifest (safety_gate.status=not_run, recovery.status=pending)
  -> RunEvidenceStore open
  -> DataAccessService bind
  -> PreflightCoordinator.run(profile)
       -> mandatory market_price and stock financial statements
       -> shared run cache and evidence
  -> Analyst stage
       -> DataAccessService -> query key, run cache, single-flight,
          vendor/fallback/retry, ordered attempts, counters, evidence
       -> fundamentals report produced
       -> FinancialFactService.fetch() through DataAccessService
          -> FinancialMetricService.compute() -> metric block
          -> MetricEvidenceBundleBuilder.build()
          -> MetricConflictDetector.detect(structured claims)
          -> FundamentalsAdapter appends the block before research debate
       -> other analyst reports
  -> ContextAssembler builds the program provisional CoverageView
       -> DownstreamBriefBuilder.build(view_version) once, before five-role delivery
  -> Research debate (Bull/Bear)
       -> brief replaces the four full analyst reports for these roles
       -> LLM proposals (unapproved)
  -> Research Manager / Trader
  -> Risk debate (Aggressive/Conservative/Neutral)
       -> reuse the same brief/view_version; regenerate only if the view changes
  -> Portfolio Manager (original terminal node, wrapped by PortfolioManagerAdapter)
       -> consumes full analyst reports, investment plan, trader plan,
          risk debate, and applicable historical memory
       -> produces ModelProposal {rating, text, source=portfolio_manager,
          source_refs, proposal_status=unapproved}
  -> AvailabilityIndex.finalize()
       -> executed + component_missing records
       -> critical gaps, final coverage snapshot, provenance digest
  -> SafetyGate.finalize(model_proposal, final coverage snapshot, raw_risk_envelope?)
       -> exactly one risk applicability/validation/policy/evaluation path
       -> gate result, primary reason, review class, formal decision, risk evidence payload
  -> FinalizedRunRecord (immutable; decision id, binding, digests)
  -> ReportSectionManifestBuilder.render()
  -> MemoryReservationStore.plan() and reserve the required entry_version
  -> recovery_snapshot write/read-back (snapshot_ready; contains the memory plan/version)
  -> memory entry idempotent write (pending)
  -> permanent publication snapshot files write/validate (before terminal commit)
  -> terminal manifest candidate + INV-01 over candidate and all referenced files
  -> RunOwnershipLock.critical_section(run_id, terminal commit)
       -> atomic terminal manifest commit (completed)
  -> post-commit read validation under the same ownership rules
       -> success: history visibility becomes true
       -> failure: keep the committed terminal manifest immutable;
          record an independent corruption diagnostic; reject as success/history/export
  -> cleanup temporary recovery material (warning only on failure)
  -> formal display consumes FinalizedRunRecord only
```

### 11.2 Failure path

```text
exception / invalid input / gate failure / publish failure before the terminal commit
  -> RunContext.fail(exc) or SafetyGate.failure(...)
  -> RunFailureRecord (no normal model record required)
  -> ArtifactPublisher.publish_failure(record)
  -> failed manifest + minimal safe failure report
  -> no formal success; no tradeable output
```

Post-commit read failure is not this path: the terminal commit already happened. It keeps the committed manifest as evidence and records corruption separately.

### 11.3 Recovery path

```text
startup
  -> RecoveryService.scan pending run_ids
  -> FIRST: read the terminal manifest, if present, outside the locks
       -> completed + read-time INV-01 passes + identity matches:
            return idempotent success; do NOT require recovery_snapshot
       -> completed + identity conflict:
            return RUN_ID_CONFLICT; do not overwrite or republish
       -> completed + permanent artifacts corrupt:
            return CORRUPT_RECORD; do not overwrite or republish
       -> not completed or absent: continue as a pending publication
  -> short lock: claim/read lease, read current terminal identity,
     update owner/token/expiry; release
  -> outside lock (no run/memory lock held):
       -> only now read and verify recovery_snapshot (references, digests, versions)
       -> re-check terminal identity; a completed matching run becomes no-op,
          a completed conflicting/corrupt run returns the typed result
       -> read the recorded memory plan/reservation
       -> render fixed sections; compute hashes; assemble permanent files
       -> stage permanent files under an owner-specific staging directory
       -> stage the original memory entry payload
  -> short lock (run lock -> memory lock):
       -> re-read lease/fencing and current terminal identity
       -> verify the staged content still belongs to the current owner,
          run_id, decision_id, reservation, snapshot, and versions
       -> no-op/conflict/corrupt exits without writing
       -> complete the one original planned memory entry idempotently
       -> promote staged permanent files; write terminal manifest;
          atomically commit; release
  -> outside lock: post-commit read validation
       -> success: short lock: cleanup own staging/recovery material; release
       -> failure: keep committed manifest; independent corruption diagnostic;
          reject as success/history/export
```

- The terminal manifest is checked first. A committed, verified, identity-matching publication is an idempotent success even if `recovery/` no longer exists.
- A committed identity conflict returns `RUN_ID_CONFLICT`; committed-but-corrupt permanent artifacts return `CORRUPT_RECORD`. Neither path overwrites the terminal manifest or auto-republishes.
- The recovery snapshot is read and verified only for a record that is not yet committed and still needs publication continuation.
- Long reads, parsing, rendering, and hashing happen outside the run/memory locks.
- Ownership/fencing and the current publication state are re-checked inside each short critical section, and staged content is rejected if it no longer matches the current owner/publication state.
- Recovery uses no LLM, external data, analysis graph, settlement, or reflection. It reuses the original run identity and the recorded reservation; a failed retry leaves a version gap but does not create a second publication.

### 11.4 Read path

```text
HistoryService.list_publications(filters)
  -> scan committed publication roots only
  -> exclude pending/failed/quarantined/corrupt records
  -> order analysis_date desc, ticker asc, run_id asc
  -> bounded page with total_matches/returned/truncated/next_offset

HistoryService.get_run(run_id)
  -> PublicationSnapshotStore.read()
  -> revalidate terminal manifest, artifact binding, complete report,
     section manifest, permanent references
  -> return verified publication or NOT_FOUND/CORRUPT_RECORD
  -> a post-commit corruption is never returned as success and never overwrites
     the committed terminal manifest; an independent diagnostic records it
```

### 11.5 Portfolio Manager and model proposal

- The original terminal `Portfolio Manager` node remains in the graph and is wrapped by `PortfolioManagerAdapter`. It is not replaced by the Trader, Research Manager, or a risk debater.
- The PM consumes the full analyst reports, the research investment plan, the Trader plan, the risk debate, and applicable committed historical memory (through `MemoryService.get_past_context`).
- It produces one `ModelProposal` with explicit fields: `rating` (five-tier or REVIEW), `text`, `source = portfolio_manager`, `source_refs` (prompt/model/input artifact references), `model_provider`/`model_id`, and `proposal_status = unapproved`.
- A Trader or risk-debater output is never the final model proposal. Those outputs remain source material referenced by `source_refs`.
- The PM does not produce the formal decision, does not call the gate, and does not write formal artifacts. `SafetyGate` remains the only formal decision authority.
- If the PM output cannot be parsed into a rating, the proposal is `REVIEW` with `proposal_status=unapproved`; the gate still applies the deterministic `model_review`/`invalid_model_rating` rules.

---

## 12. Key flow closures

### 12.1 Risk input, policy, and evaluation (FR-04/INV-02)

**Input source and authority**

- The caller/application supplies a structured risk envelope. The existing `PortfolioContext` may carry cash/positions for prompt context, but it is not authoritative numeric risk input.
- The envelope contains `portfolio_value`, `cash_balance`, `current_asset_quantity`, `current_asset_value`, `valuation_price`, `valuation_time`, one currency, `position_effect`, `order_quantity`, `entry_price`, `proposed_order_value`, `stop_loss_price`, and provenance.
- Model prose, rendered portfolio text, Markdown, and model-supplied numbers are never authoritative.

**Validation**

- Canonical decimal strings only; finite; no exponent; at most 12 fractional digits.
- `position_effect` is `new_long` only when both current quantity and current value are zero; `add_long` when both are positive.
- Instrument is common stock, action Buy, order count 1, leverage 1.0; short, derivative, leveraged, multiple-order, non-common-stock, and FX cases are unsupported and block when applicable.
- Exact identities: `current_asset_value = current_asset_quantity * valuation_price`; `proposed_order_value = order_quantity * entry_price`; `cash_balance >= proposed_order_value`; `portfolio_value >= cash_balance + current_asset_value`; every monetary field shares one currency.
- `valuation_cutoff = min(run_clock.now_utc, end_of_day(as_of_date, timezone))`; a future `as_of_date` is rejected before analysis/risk and never clipped; `valuation_time` must be at or before the cutoff and within `max_valuation_age_seconds`.
- Invalid input records only `input_ref = null`, `input_digest = null`, and a safe `diagnostic_ref`; no raw invalid value (for example NaN) is persisted.

**Policy**

- The policy is a locatable `portfolio_risk_policy_snapshot` with `policy_version`, `policy_ref`, `policy_digest`, actual thresholds, `max_valuation_age_seconds`, precision rule, `threshold_status`, and `human_approval_ref`.
- The default 0.30 concentration and 0.05 stop distance are provisional classroom values. A valid `threshold_status=provisional` snapshot with `human_approval_ref=null` MAY be used and MUST be labeled provisional in every result/report. An approved snapshot requires a non-null `human_approval_ref`.
- Missing, incomplete, unknown, or digest-mismatched policy blocks with `POLICY_SNAPSHOT_UNAVAILABLE`; it never defaults to approval. "Not approved" is not treated as "policy absent": a valid provisional snapshot is a real policy and is used with its explicit status. Human approval changes only the approved/provisional label and the ability to claim approved thresholds.

**Evaluation**

- Pure decimal arithmetic with at least 28 significant digits; no binary floating point.
- `projected_weight = (current_asset_value + proposed_order_value) / portfolio_value`; `stop_distance = (entry_price - stop_loss_price) / entry_price`.
- Boundary equality passes. A breach blocks with `POSITION_LIMIT_EXCEEDED` and/or `STOP_DISTANCE_EXCEEDED`; both codes are retained and `POSITION_LIMIT_EXCEEDED` is the primary risk code.
- Display rounds half-up to 6 decimals; display rounding never changes the comparison.
- An evaluator exception returns `EVALUATOR_ERROR`; the shared gate follows the system-error path.

**Gate and evidence**

- `SafetyGate.finalize(proposal, coverage_snapshot, raw_risk_envelope?)` is the **only** caller of `RiskInputValidator`, `RiskPolicyResolver`, and `PortfolioRiskEvaluator`. No entrypoint, tool, publisher, or recovery path performs an independent applicability or risk evaluation.
- Applicability is determined once inside the gate from `asset_type` and the model rating: stock + Buy/Overweight only. The gate validates the risk input, resolves the policy, and evaluates exactly once, then records passed, blocked, or error even when coverage also blocks.
- Missing/unsupported/invalid/stale/inconsistent/insufficient-cash/currency/policy input blocks with `portfolio_risk_input_invalid` and `review_class=input_invalid`; never `not_applicable`.
- A limit breach blocks with `portfolio_risk_limit_exceeded` and `review_class=portfolio_risk_limit`.
- A risk evaluator exception yields gate status `error`, primary reason `portfolio_risk_evaluator_error`, `review_class=gate_system_error`, run `failed`, formal `REVIEW`, and no tradeable output.
- When coverage and an ordinary risk failure coexist, `critical_gap` remains primary; a risk evaluator exception takes the higher-priority error path and `critical_gap` is secondary.
- `input_digest` and `policy_digest` enter the gate `input_hash`; manifest and final-state carry the full result, input reference, policy snapshot, and digests.
- `RiskEvidenceStore` builds the normalized input artifact or safe diagnostic payload from the gate's single evaluation; `ArtifactPublisher.stage_risk_evidence` writes it.
- A newly written memory entry carries a declared risk summary (status, reason codes, `policy_ref`, `policy_digest`, `threshold_status`); a reused historical entry keeps its original evidence through `reused_decision_ref`.

### 12.2 Financial facts and metrics (FR-07)

**Timing and placement**

- The structured-fact fetch, metric computation, `metric_block` append, and applicable conflict check happen **after the fundamentals report exists and before research debate consumes that report**. They are not deferred to final publication.
- Final publication persists the existing `metric_block` and `metric_evidence_bundle`; it does not recompute metrics after the decision.
- If `FR-07` is enabled and the fundamentals analyst is disabled, the preflight/statement path still supplies the facts for the program-appended block. If `FR-07` is not enabled, no metric block is required.

**Adapter boundary**

- Only `DataAccessService` may call vendor adapters. The existing `sec_edgar.py` statement/JSON capability is wrapped by `SecEdgarAdapter` and invoked only by `DataAccessService`.
- `FinancialFactService.fetch(ticker, as_of)` issues a structured-fact query through `DataAccessService`; the adapter returns per-fact records that preserve `subject_id`, `accession_no`, `filing_ref`, `filed_at`, `form`, `concept`, period/fiscal identity, `span`, `unit`, `currency`, `value`, `sign`, and restatement/supersession lineage. `FinancialFactService` validates/normalizes these records into `financial_fact`s; it never imports or calls a vendor module directly, and it never guesses a filing/fact link from date proximity or equal value.
- The existing `get_income_statement`, `get_balance_sheet`, and `get_cashflow` tools use the same adapter, run cache, `data_query_key`, counters, as-of rules, and provenance. There is no second SEC path.

**Fact identity and visibility**

- A `financial_fact` records `fact_id`, `subject_id` (CIK or equivalent), `accession_no`, locatable `filing_ref`, concept, value, unit, currency, periods, fiscal year/quarter, span (annual/quarter/ytd/instant), cumulative duration, `filed_at`, source, sign convention, and restatement lineage.
- CIK never substitutes for accession/filing_ref.
- Only facts with `filed_at <= as_of_date` are visible. Same-period multiple filings select the latest filed_at on or before as-of and record supersession. Near dates or equal values are never merged. Ambiguous period/filing returns a typed n/a reason.

**Metric formulas**

- Metrics: revenue YoY (quarterly and annual), revenue QoQ, gross/operating/net margin, TTM revenue, TTM diluted EPS, fiscal-year P/E and TTM P/E as separate rows, current ratio, liabilities-to-assets, free cash flow, and FCF YoY.
- YoY uses the prior fiscal year's same fiscal quarter, span, and cumulative duration; QoQ uses the immediately preceding fiscal quarter; cash-flow YoY uses the same fiscal calendar position and cumulative span.
- TTM revenue = latest annual revenue + current fiscal-year YTD revenue - prior-year matching YTD revenue. TTM diluted EPS uses the same form and is labeled approximate.
- The current YTD starts the day after the latest annual period ends and belongs to the next fiscal year; the prior-year YTD has `fiscal_year - 1`, the same quarter/span, and matching duration; TTM coverage is approximately one fiscal year.
- No single quarter is derived by subtraction. Zero denominators, non-positive growth bases, zero/negative EPS, missing fields, currency mismatch, unit mismatch, or fiscal-period mismatch produce typed n/a reasons.

**Authority and conflict**

- The program appends a `metric_block` regardless of whether the model calls the offered tool. The block carries metric IDs, fact IDs, filing refs, formula and versions, periods, values or n/a reasons, and computed/approximate/n/a status.
- The metric block is the numeric authority; a model narrative cannot override it.
- Conflict detection is limited to a recognizable `metric_id`/declared structured claim, explicit period, and parseable numeric value. A conflict is disclosed and the contradicted claim is labeled unverified. Free-form prose numbers are outside deterministic detection and this limitation is recorded.

**Persistence and recovery**

- The `metric_evidence_bundle` carries structured facts, formula/fact/policy versions, the metric block, `input_digest`, and `result_digest`.
- It is written before research debate and persisted in the permanent publication snapshot and the recovery snapshot.
- Recovery reads the bundle and never refetches filings, calls a model, or reruns the analysis. A missing/corrupt bundle blocks a metric-dependent publication rather than triggering a live fetch.

### 12.3 Downstream brief, mandatory content, token budget, and references (FR-08)

**Scope and replacement**

- Only Bull Researcher, Bear Researcher, and the three risk debaters receive the brief. Analyst, manager, portfolio-manager, memory, history, recovery, and formal readers keep full inputs.
- For those five roles, the brief **replaces** the four full analyst reports (`market_report`, `sentiment_report`, `news_report`, `fundamentals_report`). The same role must not receive both the full reports and the brief.
- The brief is generated once before the Bull/Bear stage. The three risk debaters reuse the same brief and `coverage_view_version` unless the program coverage view changes; if it changes, a new versioned brief replaces it and both audit records are retained. No brief is generated after the final decision.

**Program view versus final snapshot**

- The brief uses the program coverage view and `view_version` available at generation time. The view is program-produced, monotonic, and model-immutable.
- The final safety gate still uses the final `coverage_snapshot`; the brief's view is not a substitute for the final snapshot.
- The audit metadata records `coverage_view_version`, the final snapshot hash when later bound, and any view change that triggered regeneration.

**Mandatory content and protection**

- Program-generated canonical coverage gaps from the program `FR-03` availability view.
- The `FR-07` metric block and source references.
- Applicable safety constraints.
- Mandatory content is reserved first and is never truncated. Gap text is never derived by keyword matching `unavailable`.
- Mandatory blocks carry explicit protection markers (structured `protected: true` plus begin/end markers). `ContextAssembler` compression and any reference/full-report fallback MUST preserve them verbatim; a generic compression path may not remove or shorten them.

**Budget and resolution**

- A versioned `brief_budget_policy` defines separate mandatory and compressible budgets, a total budget, and a hard cap.
- Ordered resolution:
  1. mandatory above hard cap -> reject without trying a reference;
  2. expansion up to the hard cap when allowed;
  3. a downstream-resolvable reference whose payload counts against the context hard cap;
  4. full report only when it fits the existing context hard cap;
  5. otherwise `BRIEF_REJECTED`.
- An unresolvable path string is invalid. Full-report fallback never bypasses the context hard cap; if neither the brief, the reference, nor the full report fits, the brief is rejected and the full report is not injected into the five-role context.
- Token measurement uses the selected model/tokenizer; character limits are auxiliary and measured after Unicode normalization. Missing, duplicate, forged, or overlong markers use deterministic fallback or rejection.

**Failure-state machine**

| State | Cause | Behavior |
|---|---|---|
| `BRIEF_DISABLED` | Brief capability not enabled | Normal role input path: five roles receive the four full analyst reports; no brief audit; not a rejection/fallback. |
| `BRIEF_OK` | Brief fits the budget | Brief replaces the four full reports; protected mandatory content preserved. |
| `BRIEF_FULL_REPORT` | Policy explicitly allows full-report fallback; mandatory content complete; full report fits the context hard cap | Full report replaces the brief for that role; no full+brief duplication; audit records the fallback reason. |
| `BRIEF_REJECTED` | Mandatory content exceeds hard cap, no resolvable reference, full-report fallback not allowed or does not fit, tokenizer unavailable, or invalid markers | Terminal for the five-role context: fail closed with `error.stage=context`; no ordinary input path, no generic compression, and no full-report injection may be used to bypass the rejection. |

- Full-report fallback is allowed only when the versioned policy explicitly permits it, all mandatory content is preserved, and the final request is within the context hard cap. It is never a recovery from `BRIEF_REJECTED`.
- After `BRIEF_REJECTED`, the five-role stage does not fall back to normal full input or generic compression; the run fails closed with a typed brief rejection record. Other formal artifacts already computed may be retained as evidence, but no tradeable formal decision is produced.

**Audit and non-mutation**

- `context_audit_metadata` records the source summary, policy version, `coverage_view_version`, mandatory digest, omitted compressible identifiers, budget decision, fallback reason, and reference handle. It is stored separately.
- The brief is not a formal artifact and does not mutate the full report, formal record, history, recovery material, or the formal publication snapshot.
- Evaluation uses a controlled switch under the same model/config/data/risk policy. Net tokens = added output tokens - reduced downstream input tokens; net cost = added output cost - reduced input cost saving; if either price is missing, cost fields are null. No saving is claimed until the frozen contract reports `accepted` with approved `quality_loss_max` and zero safety escapes.

### 12.4 Memory reuse, version reservation, and recovery completion

**Decision identity**

- `decision_id` is content identity; `run_id` is invocation identity. Memory reuse is keyed by `decision_id`/`entry_digest`, not `run_id`.
- `entry_digest` covers only stable decision content; `evidence_digest` covers coverage/gaps/provenance and may differ across reruns without implying corruption.

**Plan, reservation, and write**

- Before the recovery snapshot is written, `MemoryService` determines the plan: reuse a committed entry, reuse an uncommitted reservation owned by the same publication, or reserve a new version.
- `MemoryReservationStore` is a persistent, append-only, lock-protected allocation history with a monotonic high-water mark over **all** historical allocations, including failed reservations. The next version is `high_water + 1`; concurrent runs cannot receive the same version.
- The reservation records the ticker/date, decision_id, entry_version, owner `run_id`, status (`reserved`, `committed`, `failed`), and fencing token. It is written under the memory lock and is included in the recovery snapshot.
- Retries and recovery reuse their own reservation; they do not allocate a second version. A failed publication permanently occupies its version and leaves a gap; the version does not become effective and the older committed version remains effective.
- `committed` is a derived projection from the terminal manifest plus read-time `INV-01`, not a second commit condition. The ledger's allocation history (including failed reservations) must be durable; repair replays it and must never reissue a failed version.
- The order is fixed: determine plan/reservation -> write recovery snapshot containing the plan -> idempotent memory write -> permanent snapshot -> terminal candidate -> commit. The recovery path uses the recorded reservation.
- A different `decision_id` records `supersedes`; only the highest committed version is effective. A same `decision_id` with a different `entry_digest` is a conflict/tamper and is not overwritten.
- Memory-disabled runs set `memory.status=disabled` and require no memory artifact.
- Settlement/reflection may append outcome fields but cannot change the binding or formal decision fields.

**Uncommitted same-decision handling**

An entry whose source terminal manifest is not committed is **not** a reusable success. Run B never treats it as committed history and never takes ownership of A's entry.

1. **A is active and its lease is valid**: B waits within a bounded timeout without holding the run lock or memory lock. If A commits and validates within the timeout, B may reuse via `reused_decision_ref`; if not, B returns the explicit retryable status `MEMORY_PENDING_RETRYABLE`. B does not write an entry, allocate a version, or block A's publication.
2. **A is invalid and a valid recovery snapshot exists**: B invokes `MemoryRecoveryCoordinator`, which triggers recovery under **A's original `run_id`, original reservation, and original recovery snapshot**. The recovered publication remains A's; ownership is never transferred to B. After A commits and validates, B may reuse via historical reference.
3. **A is invalid and no valid recovery snapshot exists**: return `MEMORY_RECOVERY_UNAVAILABLE`; B rejects its new-entry path and does not write a substitute entry. Manual recovery/repair is required.
4. **Recovery of A fails**: return `MEMORY_RECOVERY_FAILED` (retryable/manual); B does not transfer ownership or create a second entry.
5. **Binding conflict** (same `decision_id` with different `entry_digest`, inconsistent owner/version, or reserve/commit contradiction): return `MEMORY_CONFLICT`; never overwrite.

Waiting for A holds neither the per-run lock nor the memory lock unless the wait is inside a short protected check; it must not prevent A from completing publication.

**Recovery completion**

- If the original publication required memory and the interruption occurred before the first write, recovery creates exactly the one original planned decision entry using the recorded reservation.
- If a partial write exists, recovery idempotently completes that same entry.
- Recovery never changes decision content, creates a different entry, or creates an additional duplicate; memory-disabled originals stay disabled; settlement/reflection calls = 0.

### 12.5 Publication commit and read validation (FR-02/FR-05/FR-06/INV-01)

**Commit order**

1. Running manifest before model calls (`safety_gate.status=not_run`).
2. Preflight; analysts; financial facts/metrics/block; brief and provisional coverage view; research/risk debate; final coverage.
3. `SafetyGate.finalize` and immutable `FinalizedRunRecord`.
4. Render report sections and the section manifest.
5. Determine the memory plan and reserve the required `entry_version` under the memory lock; append a `reserved` allocation record.
6. Write the recovery snapshot, including the memory plan/version, durably; read it back and verify self-contained references; status `snapshot_ready`.
7. Write the original planned memory decision entry idempotently (pending).
8. Stage and validate all permanent publication snapshot files **before the terminal commit** in an owner-specific staging directory: complete report, section manifest, final-state, risk evidence/policy references, metric bundle when applicable, memory entry/binding, versions, and hashes. The snapshot is not authoritative until the terminal manifest commits; promotion happens in the commit critical section.
9. Build the terminal manifest candidate with binding, formal decision, security scans, section manifest, metric bundle, risk evidence, memory binding, and `publication_ref` hashes. If desired, include a `recovery_snapshot_summary` (status/digest/created-at) as audit-only; no terminal-manifest hash is written into `binding.json` or any file hashed by the manifest.
10. Validate the permanent candidate with `INV-01`; separately verify the self-contained recovery snapshot for recoverability. The recovery snapshot is not part of the formal `INV-01`/history/export scope. The on-disk manifest is still the running manifest.
11. Enter `RunOwnershipLock.critical_section` for the `run_id`; re-check owner/fencing and that the staged content still applies to the current publication state; promote staged permanent files; atomically replace the running manifest with the terminal manifest. This is the only commit point.
12. Post-commit read validation under the same ownership rules. If it succeeds, history becomes visible; append/refresh the ledger's `committed` projection (audit/cache only, not a commit condition). If it fails, **do not overwrite the committed terminal manifest**: keep it as immutable commit evidence, record an independent corruption diagnostic, reject the record as success, and exclude it from history/export until repaired.
13. Clean temporary recovery material only after successful post-commit validation; a cleanup failure is a warning and does not change the committed identity.
14. History visibility begins only after steps 11-12 succeed. The permanent snapshot is never created after cleanup.

**Memory ledger integration**

- Before the recovery snapshot: append `reserved` with the allocated version; this is durable allocation history.
- On abort before a completed terminal manifest: append `failed`; the version remains permanently occupied and is never reissued.
- On retry/recovery: reuse the same reservation; do not allocate a new version.
- After terminal commit plus read-time `INV-01`: the `committed` projection may be appended, but it is derived/rebuildable. If the ledger update fails, the terminal manifest remains authoritative and the projection is repaired from it.
- A ledger `committed` entry without a completed terminal manifest is not a commit. The ledger never becomes a second commit condition.

**Read predicate and post-commit corruption**

- Every reader requires terminal manifest `run_status=completed` **and** its own read-time `INV-01` validation (manifest hash, artifact hashes, binding, formal decision, security results, section manifest).
- Trusting the manifest status alone is forbidden. A completed manifest that fails validation is treated as corrupt/unavailable, not as a successful formal result.
- A post-commit read failure MUST NOT replace the committed terminal manifest with `failed` or any other status. The terminal manifest is immutable commit evidence. A separate diagnostic record identifies the corrupt run; `HistoryService`/`ExportService` return `CORRUPT_RECORD` and do not return partial content.
- A completed-to-failed compensating replace is **not** part of this design. Only pre-commit failures use the running/failed path.
- An independent commit marker is never authoritative. The terminal manifest plus read-time `INV-01` is the only commit condition.

**Recovery cleanup versus formal reads**

- After successful commit and post-commit validation, temporary recovery material (`recovery/`, claim, staging) may be cleaned. Cleanup is not a formal dependency.
- Formal report reads, history `get_run`, memory binding validation, and `verified_package` export resolve only against the permanent `publication/` snapshot and the terminal manifest. They MUST succeed after `recovery/` is gone.
- If the terminal manifest retains a `recovery_snapshot_summary`, it is audit metadata only. Readers must not require the temporary recovery file or re-read it to verify the formal record.
- Verification scope: permanent snapshot + terminal manifest = full `INV-01`/history/export scope; recovery snapshot = recovery-only, valid until cleanup; terminal recovery summary = audit-only, never a substitute for permanent records.

### 12.6 Recovery snapshot, lease fencing (deferred), and idempotent completion (FR-06/QR-02)

**Snapshot boundary and order**

- Recovery **first** reads the terminal manifest and verifies the permanent publication. A committed, INV-01-valid, identity-matching publication returns idempotent success and does not require `recovery/`.
- A committed identity conflict returns `RUN_ID_CONFLICT`; a committed publication with corrupt permanent artifacts returns `CORRUPT_RECORD`. Neither overwrites the terminal manifest or auto-republishes.
- Only a record that is not committed and still needs publication continuation reads and verifies the recovery snapshot.
- For that continuation, recovery guarantee begins only at `snapshot_ready`: a complete, durably written, read-back-verified, self-contained, redacted snapshot.
- The recovery snapshot is a temporary pending envelope. After commit and post-commit validation, it may be cleaned; formal reads and export do not depend on it.
- The memory reuse/new plan and reserved version are determined **before** the snapshot is written. The snapshot records that plan.
- After the snapshot is ready, recovery performs the idempotent memory write, then writes/validates the permanent publication snapshot candidate, then builds and validates the terminal candidate, then commits, then reads back, then cleans temporary material.
- The snapshot includes the formal decision and binding, terminal-manifest candidate identity, section manifest and fixed rendering inputs, risk input/policy references, the original required memory decision identity and reserved version, the metric bundle when `FR-07` applies, and schema/renderer versions.
- Every reference resolves inside the snapshot with a validated digest; recovery does not depend on a separately lost external file.
- Missing, corrupt, unsupported, or reference-broken snapshots for a still-uncommitted record are quarantined and not published as success; valid source material is retained across persistent faults.

**Shared claim, lock, and fencing**

- Normal publication and recovery use the **same** per-run `RunOwnershipLock` and owner/fencing records. There is no second lock or commit marker.
- Long recovery reads, parsing, rendering, and hashing run outside the run/memory locks. The run lock is acquired only for claim/lease state changes and protected writes; the memory lock is acquired after it only for the memory write.
- Recovery claims atomically per `run_id`; one worker is active per `run_id`; duplicate startup/claim does not create a second publication.
- A stale claim/lock may be taken over after lease expiry; takeover increments the fencing token. The old owner is rejected on its next protected write.
- The ownership/fencing check is performed inside the same critical section as the protected write (and memory write when the order requires it), not once before it.
- Lock order is fixed: run lock before memory lock; never acquire the run lock while holding the memory lock.
- Interruption/retry: process exit releases the OS file lock if the OS does so; the logical lease may remain active until expiry. Retry reacquires the file lock, re-reads the lease/reservation/terminal identity, and either reuses the original reservation or completes the same entry idempotently. Cleanup releases only its own lock and never deletes another owner's claim.
- Every publication and memory write checks current ownership/fencing at commit; a worker that lost its lease is rejected without writing.
- Failure is isolated per task; retries are bounded; at most one successful formal publication exists per `run_id` and decision identity.

**Identity and idempotency**

- Recovery checks the terminal manifest **before** reading the recovery snapshot.
- A legal completed publication with matching identity is already complete: return idempotent success, do not republish, do not repeat memory, and do not require `recovery/`. The ledger's `committed` projection may be rebuilt from that manifest.
- A completed publication with a different identity returns `RUN_ID_CONFLICT`; a completed publication whose permanent artifacts fail verification returns `CORRUPT_RECORD`. Neither overwrites the terminal manifest or auto-republishes.
- Only an uncommitted/absent record continues to claim and read the recovery snapshot. Same `run_id` with the same immutable content is a no-op; different content is `RUN_ID_CONFLICT`.
- Recovery reuses its recorded `reserved` allocation. If the original publication failed, the ledger keeps a `failed` allocation; recovery does not allocate a new version. If recovery fails again, the version remains occupied.
- A post-commit read failure keeps the committed terminal manifest immutable, records an independent corruption diagnostic, and rejects the record as success/history/export; it does not republish a second terminal manifest.
- `analysis_complete`, `snapshot_ready`, `publication_committed`, `failed`, `quarantined`, and `corrupt` are distinct states; only committed plus read-time `INV-01` is visible as successful history.

**Performance**

- QR-02 is deferred. If reactivated, it uses 100 committed publications and 10 pending valid snapshots, fixed 12-section report maps, one risk evidence object, one required memory write, rendered output and snapshot each at most 1,048,576 bytes, 30 independently reset trials, and nearest-rank p95 at most 2.000 s **provisional**.
- Timing starts immediately before claim/scan and ends after final read-time validation of every recovered run, including rendering, risk evidence handling, publication, memory, and cleanup attempts.
- Correctness and model-free behavior are zero-tolerance; failures/timeouts are retained and the target is never met by skipping validation.

### 12.7 History retrieval and independent export (FR-05/SR-01)

**Listing**

- Optional ticker and strict `YYYY-MM-DD` date filters use intersection semantics; ticker normalization is the same as data access; dates are never defaulted.
- Order is analysis_date descending, ticker ascending, run_id ascending.
- `limit` is an integer 1-500, default 50; `offset` is an integer >=0, default 0; booleans, non-integers, zero/negative/over-limit values return `INVALID_FILTER`.
- Response includes `total_matches`, `returned`, `truncated`, and `next_offset`; the listing is bounded.
- Only verified committed records are listed; pending/failed/quarantined/corrupt records are excluded; corrupt records are counted/warned separately.

**Retrieval**

- `get_run(run_id)` revalidates the terminal manifest, binding, complete report, section manifest, and permanent publication references on every read.
- The section manifest comes from the committed publication's versioned renderer and recorded capability set; only applicable non-empty sections with path, agent/state fields, byte size, and SHA-256 are listed.
- Foreign/stale/mixed-run sections are rejected. A successful read never returns partial or unverified content.
- A post-commit validation failure returns `CORRUPT_RECORD`, leaves the committed terminal manifest untouched, and records an independent diagnostic. It is never converted into a new `failed` terminal state or a second publication.

**Export**

- `display_copy` contains the verified complete report, section manifest, and binding summary; it is not claimed as independently verifiable.
- `verified_package` additionally contains the terminal manifest, final-state, risk evidence/policy references, memory entry/binding, schema/renderer versions, and a `history_reference_closure` for every followed `reused_decision_ref`.
- The closure includes source run/decision/entry/digest, source terminal manifest hash, source publication proof, source decision content/digest, and required source artifact binding. If unavailable, the package is labeled `historical_reference_unverified` and limited to the current run; it does not depend on original-machine-only files.
- Both modes return `EXPORT_CONFLICT` for a non-empty target and leave it byte-identical. Legacy report trees are not migrated, indexed, or modified. Path confinement and credential scanning reuse `SR-01`.

---

## 13. Unique behavior matrix

| Situation | Risk branch | Gate / formal decision | Publication | Recovery | History/export | Brief | Run status |
|---|---|---|---|---|---|---|---|
| Normal stock Buy/Overweight, complete coverage, risk passes | `passed`; metrics recorded | `passed`; rating unchanged | Commits normally | Snapshot ready; no recovery needed | Visible after commit | Budget policy applied | `completed` |
| Critical data gap | If Buy/Overweight, risk still evaluated | `blocked`, `critical_gap` primary | Blocked formal `REVIEW`; no tradeable output | Snapshot may exist; recovery continues block | Not visible as success | Canonical gap in mandatory content | `completed` with blocked formal decision |
| Model rating REVIEW/invalid | `not_applicable` | `blocked`, `model_review`/`invalid_model_rating` | Formal `REVIEW` | Recovery preserves the blocked decision | Not tradeable history | Mandatory safety constraints | `completed` with blocked formal decision |
| Missing/invalid/unsupported/stale/inconsistent/cash/currency/policy risk input | `blocked` with the matching input code | `blocked`, `portfolio_risk_input_invalid`, `input_invalid` | No normalized input artifact; safe diagnostic only | Recovery reads the diagnostic/blocked decision | Not tradeable history | Risk block summary if present | `completed` with blocked formal decision |
| Risk limit breach | `blocked` with limit code(s) | `blocked`, `portfolio_risk_limit_exceeded`, `portfolio_risk_limit` | `effective_order_value=0`; evidence retained | Recovery preserves the block | Not tradeable history | Risk block summary | `completed` with blocked formal decision |
| Risk evaluator exception | `error`, `EVALUATOR_ERROR` | `error`, `portfolio_risk_evaluator_error`, `gate_system_error` | Failed run record; no tradeable output | Failed publication; recovery does not invent approval | Not visible | No brief as formal content | `failed` |
| Crypto Buy / non-stock | `not_applicable` | Other SB-01 rules unchanged | Normal | Normal | Visible if committed | Normal | `completed` |
| Metrics missing/ambiguous | n/a reasons; no live fetch | Normal gate (metric block is evidence) | Metric block with n/a; bundle persisted if enabled | Reads bundle; missing/corrupt bundle blocks metric-dependent publication | Visible if committed | n/a reasons preserved as mandatory | `completed` |
| Metric conflict | n/a to risk | Formal decision still gate-controlled; conflict disclosed | Report labels contradicted claim unverified | Recovery preserves disclosure | Visible if committed | Mandatory metric block + conflict label | `completed` |
| Brief capability disabled | n/a | n/a | No brief audit; full artifacts unchanged | Recovery uses full records | Unchanged | Five roles receive full analyst reports | `completed` (normal path) |
| Brief enabled, mandatory fits | n/a | n/a | Audit metadata stored; full artifacts unchanged | Recovery uses full records, not brief | Unchanged | Brief replaces four full reports | `completed` |
| Brief full-report fallback allowed and fits | n/a | n/a | Audit records fallback reason; full artifacts unchanged | Recovery uses full records | Unchanged | Full report replaces brief for the role; mandatory content complete | `completed` |
| Brief mandatory exceeds hard cap or all safe fallbacks fail | n/a | n/a | Full artifacts may remain as evidence; no formal decision | Recovery unaffected | Unchanged | `BRIEF_REJECTED`; no re-entry to normal input/generic compression | `failed` at context stage |
| Brief tokenizer missing | n/a | n/a | Full artifacts may remain as evidence | Unaffected | Unchanged | `BRIEF_REJECTED` | `failed` at context stage |
| Context above token budget, compression disabled or unsafe | Gate/formal output may still be computed | No model request with an oversized prompt | The model call is not sent; run fails closed before invalid prompting | Recovery uses saved records only | Not visible | Not delivered | `failed` (context budget) |
| Write interruption before terminal manifest | Whatever was computed | Formal record may exist; not committed | Running/failed; no completed manifest | Valid snapshot -> recover; missing/corrupt -> quarantine | Not visible | Unchanged | `running`/`failed` |
| Post-commit read validation fails | Unchanged; committed formal result | Committed formal decision remains immutable | Committed terminal manifest is not overwritten; independent corruption diagnostic | Does not republish; record is quarantined/corrupt | `CORRUPT_RECORD`; no partial content | Unchanged | `completed` commit evidence, marked corrupt for readers |
| Concurrent normal publication and recovery for same `run_id` | Unchanged | Same formal result | One owner wins; loser rejected before write | Same run lock/owner/fencing; existing completed identity is a no-op | One committed result | Unchanged | `completed` |
| Two normal publishers for same `run_id` | Unchanged | Same formal result | One owner wins; loser rejected or no-op if identical | Same run lock/ownership rules | One committed result | Unchanged | `completed` |
| Recovery duplicate startup | Unchanged | Same gate result | One winner; loser rejected | Claim/fencing prevents duplicate | One committed result | Unchanged | `completed` |
| Recovery stale takeover | Unchanged | Same gate result | New owner increments fencing; old owner rejected | New owner completes | One committed result | Unchanged | `completed` |
| History query for pending/failed/quarantined | Unchanged | n/a | n/a | n/a | Excluded from successful listing | n/a | n/a |
| History corrupt record | Unchanged | n/a | n/a | n/a | `CORRUPT_RECORD`; no partial content | n/a | n/a |
| Export non-empty target | Unchanged | n/a | n/a | n/a | `EXPORT_CONFLICT`; byte-identical | n/a | n/a |
| Export unavailable historical proof | Unchanged | n/a | n/a | n/a | `historical_reference_unverified`, current-run scope | n/a | n/a |
| Secret scan failure | Unchanged | Gate may be blocked; security stage failed | Dangerous content not written; minimal incident record only | Quarantine/fail closed | Not visible | Not written unsafely | `failed` |
| Future `as_of_date` | Rejected before risk | No formal analysis | No manifest completion | No recovery | Not visible | Not generated | Startup failure |

### 13.1 Completed with blocked formal decision

A handled coverage/risk block is a successful **run** with a formal `blocked_for_review` decision, not a system failure. The terminal manifest can be `completed` with `formal_decision.status=blocked_for_review`, `final_rating=REVIEW`, and a passed/blocked gate result, provided all artifacts and security checks pass. A gate **exception** is different: it is a failed run (`run_status=failed`, `error.stage=gate`) and produces no tradeable output. This distinction prevents a business block from being mislabeled as a crash and prevents a crash from being published as a completed block.

### 13.2 Scenario verification plan

| Scenario | Expected unique behavior | Planned verification |
|---|---|---|
| Normal pass | Complete coverage, stock Buy/Overweight risk passes; formal rating unchanged; publication commits once; history visible after post-commit validation | `T-SCEN-01`: end-to-end fixture with fixed replay, query counters, risk boundary pass, manifest/INV-01, permanent snapshot, recovery snapshot, memory idempotency, read-back |
| Business block | Critical gap or risk limit/invalid input; formal `REVIEW`; no tradeable output; run `completed` with blocked formal decision; risk result recorded even when coverage blocks | `T-SCEN-02`: gate matrix for critical gap, risk input invalid, risk limit, model REVIEW, combined coverage+ordinary risk; assert primary/review class and absence of tradeable output |
| System exception | Evaluator or gate raises; gate `error`, run `failed`, primary system reason, `review_class=gate_system_error`, no commit | `T-SCEN-03`: fault injection at evaluator/gate; assert failed manifest, no committed publication, no tradeable output |
| Pre-commit interruption | No terminal completed manifest; valid recovery snapshot can complete later; permanent snapshot not authoritative without commit | `T-SCEN-04`: crash after recovery snapshot/memory/permanent snapshot but before terminal commit; recover model-free; assert one commit and no duplicate memory |
| Post-commit corruption | Committed terminal manifest is preserved; record rejected as success; independent corruption diagnostic; history/export return `CORRUPT_RECORD`; no compensating `failed` manifest | `T-SCEN-05`: tamper one bound artifact after commit; assert immutable manifest bytes, diagnostic record, history/export rejection, no second publication |
| Duplicate recovery | One claim/owner per `run_id`; duplicate startup is rejected or waits; at most one commit; no duplicate memory | `T-SCEN-06`: repeated startup and duplicate claims; assert one winner, no duplicate publication/memory, bounded retry |
| Concurrent publication | Two normal publishers and a recovery worker for one `run_id` use the shared lock/fencing; one winner; stale takeover increments token; old owner cannot write | `T-SCEN-07`: two normal publishers plus recovery; assert one commit, lost-owner rejection, lock order, no duplicate memory |
| Context overflow | No oversized model request; mandatory brief content preserved; safe compression/reference/rejection; all fallbacks obey hard cap | `T-SCEN-08`: over-budget context and brief cases; assert `ContextBudgetError`/`BRIEF_REJECTED`, protected blocks intact, no full+brief duplication |
| History/export edge cases | Pending/failed/quarantined/corrupt excluded; section isolation; export closure/conflict; post-commit corruption never success | `T-SCEN-09`: mixed statuses, tampered sections, unavailable historical proof, non-empty export target; assert typed results and byte-identical legacy/target |
| Cleanup after successful commit | Temporary recovery material removed; history read, memory binding verification, and verified export still succeed from the permanent snapshot | `T-SCEN-10`: commit, validate, cleanup, then `get_run`, memory binding check, `verified_package` export; assert no recovery-file dependency |
| Brief disabled / full-report fallback / final rejection | Disabled uses normal full reports; allowed full-report fallback preserves mandatory content and hard cap; final rejection is terminal and cannot re-enter normal input/compression | `T-SCEN-11`: three fixtures and a post-rejection bypass attempt; assert statuses, hard-cap behavior, no bypass |
| Concurrent same decision with uncommitted entry | A active -> B bounded wait/retryable; A invalid with snapshot -> recovery under A identity; no snapshot -> unavailable; binding conflict -> conflict | `T-SCEN-12`: active, expired, missing-snapshot, and mismatch cases; assert no ownership transfer, no duplicate entry, no lock held while waiting |
| Old process paused / recovery takeover | File lock held -> bounded wait or `LOCK_BUSY`; no lock-file deletion; takeover after acquiring file lock increments fencing; old process rejected on next write | `T-SCEN-13`: paused process holding file lock, lease expiry, takeover, old-process resume; assert lock-busy/token behavior |
| Portfolio Manager proposal source | PM consumes full reports/plans/risk debate/memory; model_proposal source=portfolio_manager; Trader/risk-debater output never final proposal | `T-SCEN-14`: normal PM output, missing/parsing failure, and attempted Trader/risk-debater promotion; assert source fields and gate input |
| Failed version, new run, old retry | Highest version fails and remains in the high-water mark; a new run gets a higher version; the old run retries its own reservation and never reuses the new version | `T-SCEN-15`: fail version N, allocate N+1 to a new run, retry the old run; assert no version reuse, no duplicate entry, effective versions correct |
| Commit/ledger-update interruption | Terminal manifest commit succeeds but ledger `committed` projection is missing/fails; manifest remains authority; repair rebuilds projection without losing failed allocations or reissuing versions | `T-SCEN-16`: crash between commit and ledger update; assert history reads, ledger repair, high-water preservation, no second commit condition |
| Recovery after cleanup | Successful publication and recovery-directory cleanup, then recovery is called again; terminal manifest first gives idempotent success without `recovery/` | `T-SCEN-17`: commit, validate, cleanup `recovery/`, run recovery again; assert idempotent success and no snapshot requirement |
| Committed publication corrupt | Terminal manifest committed but a permanent artifact fails verification; recovery returns `CORRUPT_RECORD`, does not overwrite the manifest, and does not auto-republish | `T-SCEN-18`: tamper a permanent file after commit, run recovery; assert immutable manifest, typed corruption, no second publication |

---

## 14. Concurrency

### 14.1 Same run, same query

- First request starts one `query_execution`; concurrent callers join the in-flight result.
- `query_execution` count per key is 1; logical request count can be greater than 1.
- `http_request_count` is per attempt and includes retries/redirects; cache hits and local short-circuits are 0.

### 14.2 Different runs

- Each run has its own `RunContext`, evidence store, and run cache.
- Existing vendor caches may be shared and are recorded as `vendor_cache_hits`.
- Memory writes are serialized by the existing memory lock and idempotency key.
- Manifest and publication writes use per-run paths and atomic replace.
- The publication snapshot is per `run_id`; no shared mutable publication index is authoritative.

### 14.3 Shared run ownership protocol (normal publication and recovery)

Normal publication and recovery use the **same** `RunOwnershipLock`, owner identity, and fencing token. There is no second lock and no second commit marker.

**OS file lock versus logical lease**

- `run.lock` is an OS advisory file lock used only for short critical sections: read the lease, update owner/token/expiry, and perform the protected write. It is never held for the whole recovery, across model calls, or while waiting for another run.
- `lease.json` is a logical lease record. It identifies the active publisher and carries `owner_id`, `fencing_token`, `lease_expires_at`, and status. Lease expiry means "the active publisher may be stale"; it does **not** release the OS file lock and does **not** authorize deleting the lock file.
- A paused old process may still hold `run.lock`. A new owner may only wait bounded or return `LOCK_BUSY`; it must not delete or force-unlock the file. Once the file lock is acquired, takeover atomically increments the fencing token and writes the new owner under that lock.

**Protocol**

- **Protected critical section**: for every protected write (risk/metric/permanent-snapshot promotion, terminal commit, ordered memory write, post-commit diagnostic), acquire the run file lock, re-read the lease owner/fencing token and current publication state, compare with the caller token, verify lock-external prepared content still applies, perform the write, then release. The check and write are in the same critical section; a pre-check outside the write is insufficient.
- **Lock order**: run lock -> memory lock. Never acquire the run lock while holding the memory lock. Memory-only operations may hold the memory lock alone; when they also need run ownership, acquire the run lock first.
- **Takeover**: acquire the run file lock first (bounded wait or `LOCK_BUSY`); if acquired and the old lease is expired, increment `fencing_token`, write the new owner/expiry, release the file lock. If the file lock is held, wait or return lock busy; do not assume lease expiry frees it.
- **Old owner after resume**: the old process must re-check the token inside every protected write. On mismatch it returns `LostOwnership` and must not write publication, memory, cleanup, or owner diagnostics.
- **Duplicate normal publisher**: one owner wins; identical content is a no-op; different content is `RUN_ID_CONFLICT`; the loser does not write.
- **Duplicate recovery worker**: one claim/owner is active per `run_id`; duplicate startup/claim is rejected or waits; it does not publish or repeat memory.
- **Waiting on another run's pending memory**: B holds neither run lock nor memory lock; it uses a bounded wait/retry and never blocks A's publication.
- **Interruption/retry**: process exit releases the OS file lock (if the OS does so); the logical lease may still show active until expiry. Retry reacquires the file lock, re-reads the lease/reservation/terminal identity, and either reuses the original reservation or completes the same entry idempotently.
- **Cleanup**: cleanup requires current ownership, releases only its own file lock, and never removes another owner's claim or permanent records. Cleanup failure is a warning after a successful commit.
- **Scope**: single-user local filesystem. No distributed consensus, second commit marker, or separate publication transaction. Lease TTL, wait timeout, and retry budget are configuration values (ARCH-OD-06/16).

### 14.4 Concurrent publication and recovery

- Same-second ticker/date paths do not collide because the path is keyed by `run_id`.
- Multiple workers may attempt recovery; the shared lock plus fencing ensures one active worker per `run_id`.
- A worker that loses its lease is rejected at commit; it must not write publication or memory.
- Two distinct `run_id`s publish independently; history lists both without mixing sections.
- Cleanup of one pending snapshot cannot remove another run's permanent records.

### 14.5 Backtest

- Each cell has its own `RunContext` and published result.
- Memory is per backtest run, not the live memory log.
- `REVIEW` is excluded from scoring.

---

## 15. Checkpoint recovery versus publication recovery

These are different mechanisms and must not be conflated.

| Aspect | Graph checkpoint resume | Startup publication recovery |
|---|---|---|
| Driver | `CheckpointCoordinator` | `RecoveryService` |
| Allowed before/after finalization | Before a `FinalizedRunRecord` exists | After a valid `recovery_snapshot` exists |
| Model/data calls | May resume graph execution | Forbidden |
| Identity | New `run_id` | Preserves original `run_id` |
| Evidence | May inherit journal evidence with separate inherited counters | Uses saved records only |
| Commit | Normal publication after graph completion | Same terminal manifest plus read-time `INV-01` |
| Snapshot order | Not applicable | Memory plan/reservation -> recovery snapshot -> idempotent memory -> permanent snapshot -> terminal candidate -> commit |
| Lock/ownership | New run; no publication ownership until finalization | Shares the same `RunOwnershipLock`/fencing as normal publication |
| Post-commit corruption | Not applicable | Keep committed terminal manifest immutable; independent diagnostic; reject as `CORRUPT_RECORD` |
| Disabled behavior | `ResumeRejected(unsupported_phase)`; start a new run | No recovery; publication still possible; no recovery guarantee |
| Failure | Refuse resume or degraded mode | Quarantine; never publish a corrupt snapshot; never overwrite committed evidence |

Graph resume remains phased; publication recovery is a separate phase with its own disabled behavior.

---

## 16. Context layering, token limits, and brief budget

### 16.1 Layers

| Layer | Content | Compression |
|---|---|---|
| L0 | Safety/policy constraints, external content is data, tool limits, gate notice | Never compressed |
| L1 | Run identity, ticker/date, latest bar, provisional coverage view, fallback labels | Never compressed; final snapshot is not injected as final |
| L2 | Role instructions, rating scale, task, output format | Never compressed |
| L3 | Evidence blocks: tool outputs, prefetch, reports, provenance | Compressible |
| L4 | Working history: messages, debate history, prior turns | Compressible |
| L5 | Output contract and deterministic gate rules | Never compressed |
| L6 | Downstream brief view for the five debate roles | Mandatory/compressible split; replaces the four full analyst reports for those roles |

### 16.2 Replacement and protection rules

| Role | Full analyst reports | Brief | Result |
|---|---|---|---|
| Bull Researcher, Bear Researcher, three risk debaters | Not injected when the brief is delivered | Injected, with protected mandatory blocks | No full+brief duplication |
| Analyst, Research Manager, Trader, Portfolio Manager, memory/history/recovery/formal readers | Injected | Not injected | Existing full inputs preserved |
| Brief rejected | No brief or full reports injected for the five roles; run fails closed at context stage | `BRIEF_REJECTED` | No bypass via normal input or generic compression |

- Mandatory brief blocks carry `protected: true` plus begin/end markers. Generic compression, reference fallback, or full-report fallback MUST preserve them verbatim.
- A protected block is never shortened to meet a character or token budget. If the protected content alone exceeds the hard cap, the brief is rejected.
- Full-report fallback is a separate path and may only be used when it fits the existing context hard cap; it must not be combined with the brief for the same role.

### 16.3 Assembly and budget

1. Build L0/L1/L2/L5 from policy and run snapshot.
2. Add L3/L4. For the five target roles, branch on the brief state: `BRIEF_DISABLED` uses the role's normal full-report path; `BRIEF_OK`/`BRIEF_FULL_REPORT` use the selected brief/full-report replacement; `BRIEF_REJECTED` fails closed at the context stage and does not use normal full input or generic compression.
3. Measure input tokens with the selected model/tokenizer against the effective input budget.
4. If above the soft threshold, compress L3/L4 in priority order, but never remove or shorten a protected block.
5. Re-inject L0/L1/L2/L5 after compression.
6. Record `context_manifest`: layers, tokens, compression events, dropped evidence IDs, re-injected constraints, `coverage_view_version`, and brief audit metadata.
7. Send to the model only when the final request obeys the token budget; otherwise fail closed.

### 16.4 Provisional token parameters

These are work assumptions, not measured facts:

| Policy | Work assumption | Status |
|---|---|---|
| Provider context window | 128k tokens | Pending; model-specific |
| Per-call input cap | 24k tokens | Provisional |
| Reserved output/tool/constraint space | 9k tokens | Provisional |
| Effective input budget | min(per-call cap, window - reserves) | Derived |
| Soft trigger | 80% of effective budget | Provisional |
| Hard limit | 95% of effective budget | Provisional |
| Evidence block cap | 4k tokens | Provisional |
| History cap | 8k tokens | Provisional |
| Compression summary cap | 2k tokens | Provisional |
| Brief budgets/hard cap | Defined by the versioned brief policy; values pending OQ-16 | Provisional |
| Compression strategy | Deterministic truncation first; optional LLM summarization only if enabled | Provisional |

Before compression is enabled, over-budget context raises `ContextBudgetError` and fails closed; no oversized prompt or silent constraint truncation is allowed.

---

## 17. Security, permissions, and redaction boundaries

- Runtime AI may read provided context/evidence, call registered tools, and produce proposals. It has no file, environment, shell, arbitrary network, artifact-write, gate-override, or code-modification authority.
- The pure risk and metric services make no LLM, network, vendor, persistence, UI, or clock reads beyond provided inputs.
- Recovery makes no LLM, external data, graph, settlement, or reflection calls.
- History/export are read-only over committed publication records and write only to an empty export target.
- Coding agents are default-deny; this ADD-R round may write only `architecture-blueprint.md` and `docs/architecture/**`.
- The full boundary list and per-role whitelists are in `docs/architecture/permission-model.md`.
- Redaction uses known-value plus versioned-pattern checks, per-write and final run scans, fail-closed behavior, over-redaction controls, and path confinement. A clean scan proves only the defined scope/rules/fixtures, not universal secret absence.
- Audit endpoints are scheme/host/path only; preference restore endpoints may keep non-sensitive query parameters and `secret_ref` names, never inline sensitive values.

---

## 18. Phased implementation

| Phase | Scope | Exit evidence | Disabled behavior |
|---|---|---|---|
| 0. Foundations | `RunContext`, `PolicyCatalog`, `Canonicalizer`, `SecretRedactor`, `EntrypointAdapter`, `RunOwnershipLock`; fixed clock; path safety | Unit tests for clock/config/path/canonicalization/lock; no formal decision yet | Future date rejected; unsafe path rejected; lock contention typed |
| 1. Core closed loop + durability + risk | `FR-01`, `FR-02`, `FR-03`, `SB-01`, `INV-01`, `SR-01`, `FR-04`, `INV-02`; preflight; coverage; gate; sole risk caller; **Portfolio Manager adapter and ModelProposal**; manifest; publisher; **minimum memory identity/idempotency and version reservation**; **FR-02-required permanent snapshot and recovery-snapshot generation**; **permanent snapshot write/validate before commit**; **recovery snapshot write/read verify**; post-commit read validation; section manifest | Query/counter/concurrency; coverage/gate matrix; risk pass/block/error; PM/model_proposal source; manifest lifecycle; INV-01; security scans; memory identity/idempotency; snapshot durability; section manifest; post-commit corruption behavior; existing CLI/propagate/backtest regressions | Valid provisional risk policy is used and labeled; missing/invalid policy blocks. Memory disabled means no memory artifact; publication still requires identity/binding rules. |
| 2. Memory lifecycle enhancements | Supersession, settlement/reflection, rotation, same-day advanced cases, concurrent uncommitted-entry wait/takeover/reject hardening | Memory duplicate/conflict/version/settlement/rotation/concurrency tests | Memory disabled -> no memory artifact; publication still valid |
| 3. Financial metrics | `FR-07`; structured facts through the SEC adapter; metric block before research debate; evidence bundle; conflict detection; fundamentals adapter | Fact/period/restatement/TTM/n-a/conflict/bundle tests; no direct vendor; block exists before Bull/Bear | FR-07 disabled -> no metric block requirement; enabled but bundle missing at recovery -> block metric-dependent publication |
| 4. History, recovery scan, export, benchmark (partly deferred) | `FR-05`, `FR-06`, `QR-02`; history listing; single-process recovery scan; export and multi-worker claim/fencing deferred; QR-02 benchmark deferred | History filter/order/pagination/revalidation; recovery model-free; single-process duplicate guard; QR-02 future correctness/timing | Recovery scan disabled -> `ResumeRejected(unsupported_phase)`; history may still read committed runs; export/fencing/benchmark deferred |
| 5. Brief and context | `FR-08`; brief before five-role context; replacement mapping; protected markers; token counter; budget policy; audit metadata; compression | Mandatory preservation; budget/reference/rejection; role replacement; non-mutation; quality/safety evaluation; over-budget failure | Brief disabled -> full reports to five roles (existing behavior); tokenizer missing or all safe fallbacks fail -> `BRIEF_REJECTED` and run failed at context stage; compression disabled -> over-budget fails closed |
| 6. Behavior evaluation | Frozen eval set, rubric, snapshots, human approval; cache A/B; risk-policy A/B; brief A/B | Per-case scores, safety escapes, coverage changes, REVIEW rate, token/cost fields; no acceptance before snapshots/approval | No behavioral acceptance claimed; no cost optimization claimed |

Phase ordering rationale: risk is part of the core safety loop (`SB-01` depends on it), so it belongs to Phase 1. The core publish loop also needs the minimum memory identity/idempotency, permanent snapshot, and recovery snapshot write/read verification; without them the publication is not closed or recoverable. Phase 2 adds advanced memory lifecycle behavior. Financial metrics precede history/recovery because the recovery snapshot may include the metric bundle, and they must exist before research debate. Phase 4 adds startup recovery scanning, history listing, export, and performance benchmarking; the snapshot primitives already exist from Phase 1. Phase 5 adds the brief, which depends on `FR-03` gaps and `FR-07` metrics. Phase 6 is the frozen behavioral evaluation.

A phase's "feature off" setting means **that phase is not implemented/enabled**. It is not evidence that the requirement is satisfied. A requirement is complete only when its capability is enabled, its acceptance tests pass, and its evidence is recorded. No phase may claim completion of a later phase.

A valid provisional risk policy is used and must be labeled provisional. Missing, incomplete, or invalid policy blocks. OQ-10 remains blocking for any claim that the thresholds are approved; it does not convert a valid provisional snapshot into an absent policy.

**Draft obligations are reviewed together.** `FR-02` requires recovery-snapshot generation, section manifest, terminal manifest, and binding; `INV-01` binding/read-time verification; and `SB-01` risk-branch behavior. These are draft obligations and remain pending human review together with `FR-04`/`FR-05`/`FR-06`/`FR-07`/`FR-08`/`INV-02`. Phase 1 does not claim `FR-05` history, `FR-06` startup scan, or `FR-08` brief completion.

---

## 19. Requirement coverage and planned verification

| Requirement | Primary components | Planned verification focus | Phase | Evidence status |
|---|---|---|---|---|
| `FR-01` | `DataAccessService`, `RunEvidenceStore`, `Canonicalizer` | Sequential/concurrent single-flight; terminal failure cache; run isolation; retry/fallback budgets; fixed-replay business equivalence; live quality is QR-01 | 1 | Design only |
| `FR-02` | `RunContext`, `ArtifactPublisher`, `RunEvidenceStore` | Manifest lifecycle, identity, counters, tokens, failure injection, completed negatives, no-overwrite; publication/recovery/section details are INV-01/FR-05/FR-06 | 1 | Design only |
| `FR-03` | `AvailabilityIndex`, `DataAccessService`, `RunEvidenceStore` | Closed status table, profile defaults, fallback contract, aggregation, determinism, consumer consistency | 1 | Design only |
| `FR-04` | `SafetyGate`, `RiskInputValidator`, `RiskPolicyResolver`, `PortfolioRiskEvaluator`, `RiskEvidenceStore` | Single caller, applicability once, exact boundaries, invalid input, provisional policy distinction, evaluator error; cache/risk separation is QR-01 | 1 | Design only; thresholds provisional |
| `FR-05` | `PublicationSnapshotStore`, `ReportSectionManifestBuilder`, `HistoryService`, `SecretRedactor` | Filters/order/pagination, revalidation, section isolation, post-commit corrupt rejection; export deferred | 4 | Design only |
| `FR-06` | `RecoveryService`, `RecoverySnapshotStore`, `ArtifactPublisher`, `MemoryService` | Model-free single-process recovery, snapshot validity before `snapshot_ready`, memory idempotency, commit identity, post-commit corruption; multi-worker fencing deferred | 1 (snapshot primitives) / 4 (startup scan) | Design only |
| `FR-07` | `FinancialFactService`, `FinancialMetricService`, `MetricEvidenceBundleBuilder`, `MetricConflictDetector`, `SecEdgarAdapter` | Fact identity, as-of, restatement, ambiguity, direct metrics, fiscal-year P/E, current-span FCF, n/a reasons, block before research debate, conflict scope, bundle recovery; TTM/FCF YoY deferred | 3 | Design only; reference manifest pending (GR-01) |
| `FR-08` | `ContextAssembler`, `DownstreamBriefBuilder`, `TokenCounter`, `PolicyCatalog`, `BriefAuditStore` | Marker handling, mandatory preservation, protected blocks, ordered budget, reference resolution, five-role replacement, view version, non-mutation; cost is CR-01 | 5 | Design only; budgets pending |
| `PR-01` | `ArtifactPublisher`, benchmark harness | Paired manifest-write p95 and end-to-end overhead; provisional thresholds | 1 | Design only; no benchmark |
| `CR-01` | `TokenCounter`, `DownstreamBriefBuilder`, evaluation harness | Controlled brief on/off local cost attribution, approved target, and claim boundary; blocked until prices/thresholds/human approval | 5 | Design only; contract blocked |
| `GR-01` | `FinancialFactService`, reference harness | Stage A freeze readiness; Stage B post-implementation timing; no code-generated expected values | 3 | Design only; reference pending |
| `QR-01` | `DataAccessService`, `SafetyGate`, risk services, evaluation harness | Live rubric/REVIEW thresholds; fixed-replay zero-tolerance; separate risk-policy A/B | 1 | Design only; contract blocked |
| `QR-02` | `RecoveryService`, benchmark harness | Fixed workload, 30 trials, nearest-rank p95, retained failures; deferred | 4 | Deferred; target provisional |
| `SB-01` | `SafetyGate`, `FinalizedRunRecord`, `ArtifactPublisher`, `PortfolioManagerAdapter` | Five-rating matrices, malformed input, forged snapshot, entry-point bypass, gate error, sole risk caller, PM proposal source, combined coverage+error | 1 | Design only |
| `INV-01` | `FinalizedRunRecord`, `ArtifactPublisher`, `MemoryService`, `PublicationSnapshotStore` | Binding/canonicalization, full vs summary records, fallback disclosure, missing artifacts, retry, memory lifecycle, truthful completion; section binding via FR-05 | 1/4 | Design only |
| `INV-02` | `SafetyGate`, `PortfolioRiskEvaluator`, `MemoryService`, `ArtifactPublisher` | Generated violation corpus, determinism, injection, cross-artifact risk evidence, single-caller applicability, memory reuse/version | 1 | Design only |
| `SR-01` | `SecretRedactor`, all writers | Known-value/pattern scans, endpoint split, fail-closed, over-redaction, scope, credential scans of archive/history/recovery diagnostics | 1/4 | Design only |
| `SR-02` | `PathGuard`, `HistoryService`, `RecoveryService` | Path confinement, traversal/absolute-path rejection, symlink/junction escape, out-of-root writes; export conflict deferred | 1/4 | Design only |

The end-to-end scenario tests `T-SCEN-01`..`T-SCEN-18` in §13.2 cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, single-process duplicate recovery, context overflow, history edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, Portfolio Manager proposal sourcing, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, and committed-publication corruption. Export, multi-worker fencing, and QR-02 benchmark scenarios are deferred.

Every fit criterion and its planned test/monitor is listed in `docs/architecture/trace-matrix.md`. That file is the authoritative requirement-to-component-to-test mapping for this round.

---

## 20. Evidence status and measurement honesty

| Claim | Status |
|---|---|
| Baseline duration 195.383 s, 19 LLM calls, 31 tool calls, 156,541 input tokens, 27,639 output tokens | **M** — measured baseline |
| Repeated ticker-news logical query; 6 FRED and 2 prediction-market rows are distinct local failures | **M** — measured baseline |
| No native manifest, no coverage gate, no risk evaluator, no history/recovery, no metric block, no brief | **M/D** — baseline inspection; new capability design is **D** |
| `FR-01` reduces duplicate logical executions | **D/U** — not measured; external requests and vendor-cache hits measured separately |
| `FR-01` reduces tool rounds or tokens | **D/U** — not claimed |
| Risk thresholds 30%/5%, freshness window | **P** — provisional; not approved |
| QR-02 2.000 s p95 | **P** — provisional; not measured |
| Brief token/cost saving | **D/U** — no saving claimed before accepted evaluation |
| PR-01 manifest overhead thresholds | **P** — provisional; not measured |
| Any implementation, test, transcript, approval, or benefit | **Not claimed** |

---

## 21. Risks and true coding blockers

### 21.1 Architecture risks

| Risk | Impact | Mitigation |
|---|---|---|
| `RunContext` grows into a god object | Policy coupling and testability loss | Keep lifecycle/DI only; business rules in services; dependency rules in §9.5. |
| Old writers bypass the publisher | Formal decision leak | Writer audit; direct calls require a record; CLI/propagate/backtest/save_reports adapters. |
| Risk evaluator becomes a second authority | Conflicting final decisions | Pure result returned only to `SafetyGate`; no writer/persistence/memory path. |
| Recovery creates a second commit path | Duplicate/inconsistent publication | Same terminal-manifest commit and read-time `INV-01`; single-process duplicate-start guard; multi-worker claim/fencing deferred; no independent marker. |
| History scans arbitrary directories | Mixed/stale sections | Read only the permanent publication snapshot and section manifest; revalidate on read. |
| Metric formulas drift or use ambiguous periods | Wrong numeric authority | Structured fact/period identity, versioned formulas, typed n/a, frozen reference manifest. |
| Brief becomes a second context source | Inconsistent prompts and formal records | Brief is a view inside `ContextAssembler`; full/formal/history/recovery are byte-identical. |
| Brief and full reports are both injected | Duplicated context and budget overflow | For the five target roles, the brief replaces the four full analyst reports; other roles keep full inputs. |
| Brief or metrics are generated after consumers | Downstream sees missing/stale evidence | Fix the execution order: metrics before research debate; brief before five-role delivery; publication only persists existing results. |
| Post-commit corruption overwrites commit evidence | Lost audit trail and ambiguous authority | Keep the committed terminal manifest immutable; reject the record as success; write an independent corruption diagnostic; no compensating failed manifest. |
| Memory version collision | Two runs receive the same version, or a failed version is reissued | Persistent append-only allocation history with a high-water mark over all allocations including failed; retries/recovery reuse their own reservation. |
| Ownership checked before, not inside, the write | Lost-owner writes after takeover | Run ownership/fencing check and protected write in one critical section; shared by serial publication and recovery. |
| Token budget measured by characters | Budget violation | Tokenizer measurement for the final request; characters auxiliary. |
| Compatibility adapters diverge | Existing callers break | Keep `propagate` tuple, existing CLI/backtest/report behavior; regression suites. |
| Requirements evidence is not reproducible | CI/D4 evidence blocked | ARCH-OD-01/02 must be fixed by the requirement/CI owner. |

### 21.2 True blockers before coding

| ID | Blocker | Blocks | Status |
|---|---|---|---|
| OQ-09 | Authoritative supplier/ownership of portfolio risk input | `FR-04` implementation | Blocking; pending human decision |
| OQ-10 | Approval of 0.30/0.05, freshness window, precision rule, policy identity/digest/approval reference | Claiming approved thresholds and policy; a valid provisional snapshot may still be used and labeled | Blocking for approved-policy claims; pending human decision |
| OQ-12 | Risk-policy behavior-evaluation set and thresholds | `FR-04`/`INV-02` behavioral acceptance | Blocking; pending human decision |
| OQ-13 | QR-02 2.000 s target and supported platform matrix | `QR-02` future performance acceptance | Deferred; no D1 acceptance |
| OQ-14 | Frozen non-NVDA reference companies/periods/sources | `GR-01-AC1`–`AC6`, FR-07 Stage A implementation gate | Blocking; pending human decision |
| OQ-16 | Brief mandatory/compressible budgets, token/quality thresholds, evaluation contract version | `FR-08` acceptance | Blocking; pending human decision |
| ARCH-OD-01 | Unretained personal-proposal source; path no longer referenced | Provenance | Resolved for current registry |
| ARCH-OD-02 | `pyyaml`/`jsonschema` present locally but not declared | Validator reproducibility/CI | CI declaration pending |
| ARCH-OD-03 | Risk policy file location/locator and approval record | Risk policy loader | Blocking before risk implementation |
| ARCH-OD-04 | Selected model/tokenizer for brief and context budgets | `FR-08` and context budget | Blocking before brief implementation |
| ARCH-OD-06 | Recovery lease/TTL, takeover, retry, claim storage, quarantine layout | `FR-06` implementation | Blocking before recovery implementation |
| ARCH-OD-08 | Risk input envelope shape for CLI/API | `FR-04` integration | Blocking before risk integration |
| ARCH-OD-13 | Former approval of `SB-01` risk branch no longer applies | Status resolved; all requirements draft | Review risk branch with the draft registry |
| ARCH-OD-14 | Former approval coupling of `FR-02`/`INV-01` no longer applies | Status resolved; review with draft registry | Review coupled obligations together |
| ARCH-OD-15 | Permanent-snapshot staging/promotion path and hashing before commit | Publication implementation | Blocking before publication implementation |
| ARCH-OD-16 | Shared run-lock file format, lease TTL, takeover, and lock-release rules | Normal publication and recovery | Blocking before publication/recovery |
| ARCH-OD-17 | Brief replacement mapping and protected-marker format | `FR-08` implementation | Blocking before brief implementation |
| ARCH-OD-18 | Brief timing versus final coverage snapshot interpretation | `FR-08` acceptance | Blocking before FR-08 acceptance |
| ARCH-OD-19 | Financial-fact placement in the graph and SEC adapter query shape | `FR-07` implementation | Blocking before FR-07 implementation |
| ARCH-OD-20 | Memory reservation storage/format and authority | Memory/recovery implementation | Blocking before memory/recovery implementation |
| ARCH-OD-21 | Portfolio Manager adapter/model-proposal source | Analysis-chain implementation | Blocking before analysis-chain implementation |
| ARCH-OD-22 | Uncommitted same-decision memory coordination | Memory coordination implementation | Blocking before memory coordination implementation |
| ARCH-OD-23 | Permanent/recovery layout and cleanup dependency | Publication implementation | Blocking before publication implementation |

Non-blocking decisions: manifest retention, vendor-cache TTL, manifest overhead thresholds, preference/concurrency policy, checkpoint defaults, publication snapshot retention, history index strategy (read-only derived index is allowed but non-authoritative).

### 21.3 Implementation blockers versus acceptance-only

| Class | Items | Effect |
|---|---|---|
| Implementation-start | OQ-09 risk input source; ARCH-OD-03 risk policy locator; ARCH-OD-16 lock/lease format; ARCH-OD-15/23 snapshot layout; ARCH-OD-24 record_hash projection; ARCH-OD-20 reservation format; ARCH-OD-19 SEC query contract; ARCH-OD-21 PM adapter; ARCH-OD-22 uncommitted-memory protocol; ARCH-OD-04 tokenizer/model | Decide before the affected module starts. Not an approval claim. |
| Acceptance-only | OQ-10 approved risk thresholds; OQ-13 deferred QR-02 target/platform; OQ-16 brief budgets/quality/cost; D2-OD-09 behavior snapshots; OQ-05 manifest overhead | Do not block starting implementation; block completion/acceptance claims. |
| Evidence/CI | ARCH-OD-01 missing `yhx` evidence; ARCH-OD-02 validator dependencies | Block reproducible D1 validation/CI, not module design. |

---

## 22. Document index and status

- [ADR 001 — Run governance](docs/architecture/adr/001-run-governance.md)
- [ADR 002 — Full-scope ADD-R extension](docs/architecture/adr/002-full-scope-add-r.md)
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

Status:

- D1: v1.20.0; 17 requirements are draft and QR-02 is deferred; human review is pending for the revision and the deferred requirement.
- D2: v0.2 ADD-R draft; all architecture decisions proposed, not approved.
- Application implementation: **not started**.
- Tests: **not started**.
- Runtime monitoring: **not implemented**.
- Benefits: **not measured** except the baseline facts above.
- This round changed only `architecture-blueprint.md` and `docs/architecture/**`.
