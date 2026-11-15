# D2 Architecture Blueprint — Lean A Extended, ADD-R Round 3

Status: **v0.3 — ADD-R round 3 draft / pending human review**
Date: 2026-11-15
D1 basis: `docs/req/requirements.yaml` v1.25.0 — 18 requirements, 122 fit criteria
Status basis: 17 active requirements are approved as a requirement-design baseline; `QR-02` is deferred and outside current acceptance; approval does not assert implementation or measured results
Implementation status: **design only; no application code changed**
Supersedes: blueprint v0.2 (ADD-R round 2)
Amends: ADR 001 and ADR 002; Round 3 decisions are recorded in `docs/architecture/adr/003-add-r-round-3.md`; the later CR-01 state-semantics correction is recorded in `docs/architecture/adr/004-cr01-state-correction.md`

---

## 1. Purpose, scope, and authority

This blueprint defines the D2 architecture for the **complete functional scope** of D1 v1.25.0:

- 17 active requirements are approved: `FR-01`–`FR-08`, `PR-01`, `CR-01`, `GR-01`, `QR-01`, `SB-01`, `INV-01`, `INV-02`, `SR-01`, `SR-02`;
- `QR-02` is deferred and outside current acceptance;
- total: 18 requirements, 122 fit criteria (120 approved + 2 deferred).

The design direction remains **Lean A**: this is a single-process, in-process modular architecture. `RunCoordinator` coordinates the ordered run; `RunContext` owns identity, fixed clock, versions, run-scoped paths, and dependency references; business rules live in separate, testable logical services; `FinalizedRunRecord` is the only source for formal display, persistence, memory, history, and (deferred) export.

Components are **logical responsibilities**, not a mandatory one-file-per-name layout. The proposed module paths in §9.2 are a reviewable mapping; small components may share a module. A component audit must still prove one owner per responsibility and no duplicate authority.

This round does not create:

- a second final decision authority;
- a second publication transaction or commit marker;
- a second context assembler;
- a second data path that bypasses the unified data access;
- a second memory identity or memory writer;
- a second recovery mechanism or a current lease/fencing/takeover protocol.

### 1.1 Round 3 scope note

Round 3 is an architecture-consolidation round. It resolves the RunCoordinator/RunContext split, component realization, envelope and digest contracts, single-process recovery, scope discipline (TTM/FCF YoY/export/multi-worker are deferred), and the R0–R8 implementation plan. It does not implement, test, measure, or approve anything.

Current `FR-06` uses a **simple exclusive startup guard plus a duplicate-start guard with bounded retries**. `RunOwnershipLock`, `lease.json`, fencing tokens, takeover, and multi-worker claims are a **deferred extension** unless a section explicitly says otherwise. All other statements about shared ownership in this blueprint are read under that qualification.

### 1.2 Authority and evidence rules

1. A requirement is approved only when `docs/req/requirements.yaml` says `status: approved`. Draft requirements are design scope, not approval. The 17 active requirements are approved as a requirement-design baseline; `QR-02` is deferred. Approval does not assert application implementation, tests, or measured results.
2. The architecture documents are **proposed** until a human review records approval. A recommendation in this document is not an approval.
3. **M** = measured baseline evidence. **D** = design expectation. **U** = unknown or unvalidated. **P** = provisional target pending human approval.
4. Only `baseline/runs/baseline-20261020-01/` contains measured runtime evidence. No new runtime measurement, test result, benefit, approval, or transcript is claimed by this round.
5. The baseline was produced by the **original** TradingAgents code. It does not demonstrate any new requirement, gate, risk evaluator, history, recovery, metric block, or brief.
6. Pending thresholds (risk 30%/5%, freshness window, QR-02 2.000 s, brief budgets and quality thresholds, PR-01 manifest overhead) remain provisional and are never described as approved.
7. This round modified only `architecture-blueprint.md`, `docs/architecture/**`, and the new ADR 003. It did not modify `docs/req/**`, application code, tests, `baseline/**`, personal proposals, transcripts, governance rules, permissions, or secrets.

### 1.3 Current evidence caveats

The requirements registry no longer references the absent `yhx/requirements.yaml`; FR-07 and FR-08 state that the personal-proposal source is not retained. The validator uses `pyyaml` and `jsonschema`, and `python3 docs/req/validate_requirements.py --check` passes. ARCH-OD-01 records the resolved provenance note; ARCH-OD-02 records the remaining CI dependency declaration.

There is no current approval-scope coupling because no requirement is approved. The former v1.14.1 coupling is resolved for status purposes: `FR-02` recovery-snapshot generation, the section manifest, the terminal manifest, artifact binding, `INV-01` binding/read-time verification, and the `SB-01` risk branch all remain pending human review together with `FR-04`/`FR-05`/`FR-06`/`FR-07`/`FR-08`/`INV-02`. A machine validation pass is not human approval.

### 1.4 Corrections applied in this round

1. `RunCoordinator` is introduced as the only run-stage coordinator. `RunContext` is reduced to identity, fixed clock, versions, run-scoped paths, and dependency references. Neither owns business policy.
2. Components are logical responsibilities. The module table in §9.2 is a proposed mapping, not a mandatory file layout; one module may host several small components if ownership remains auditable.
3. The old entry points are explicitly adapted: `cli/run.py:run_analysis`, `propagate`, `_run_graph`, `record_decision`, `_log_state`, `save_reports`, `stream_run`, checkpoint lifecycle, `_memory_step`, `settle_pending`/`settle_all_pending`, and `backtest.py:run_backtest`. Intermediate stream/debug output is unapproved and safety-scrubbed; no raw model rating is a formal output.
4. `DataAccessService` now explicitly owns cancellation/timeout release, terminal-outcome reuse, separate retry/fallback budgets, and counting of retries already performed inside adapters. HTTP is counted at the actual request boundary.
5. `AvailabilityIndex` explicitly owns `executed` and `component_missing` records; stock statement preflight is independent of analyst selection; `CoverageView` is versioned and `CoverageSnapshot` is sealed before the gate; late results cannot mutate a used snapshot.
6. The gate blocks an invalid rating before risk applicability and never fakes `not_applicable`; a valid stock Buy/Overweight records the risk result even when coverage blocks. The gate runs before the terminal manifest; a committed manifest is not a gate precondition.
7. Run status, gate status, formal decision status, and publication visibility remain separate. No document may invent schema enum values.
8. Envelope contracts are now explicit: `PublicationEnvelope`, `RecoveryEnvelope`, `ModelProposal`, `CoverageView`, `CoverageSnapshot`, `RiskEvaluation`, `MetricEvidenceBundle`, and `ContextAuditMetadata` (§9.6.8).
9. The publication order is fixed as normalize/redact -> memory plan/reservation -> recovery envelope write/verify -> idempotent memory write -> permanent snapshot write/verify -> security scan and cross-artifact validation -> terminal manifest atomic replace -> read-back -> cleanup. The running manifest precedes model calls; an unsafe terminal write keeps the last valid running record and reports failure.
10. The only commit condition is terminal `run_status=completed` plus read-time `INV-01`. Same `run_id` + same immutable content = no-op; different content = `RUN_ID_CONFLICT`. Post-commit corruption never overwrites the manifest or auto-republishes. Cleanup failure is a warning.
11. Content digests and file-byte hashes are separate. `decision_digest`, `record_hash`, `proposal_digest`, `input_digest`, `entry_digest`, and `evidence_digest` have explicit projections and ordering (§9.6.9). Scanning/redaction precedes digesting; only specified run-level volatile fields are excluded; filing/evidence/risk timestamps are preserved.
12. Memory keeps stable content separate from current evidence. Same content references a committed historical entry; current risk evidence is not written back. Changed content gets a new version; a failed version is never reused. The reservation ledger is allocation/derived status only, not a second commit condition. Waiting holds no lock.
13. Current `FR-06` is single-process sequential recovery with a simple exclusive startup guard, duplicate-start guard, and bounded retries. Lease/fencing/takeover/multi-worker claims are deferred; they are not current obligations.
14. `HistoryService` prefers on-demand scanning of committed publication roots; a rebuildable derived index is optional and non-authoritative. Every read revalidates.
15. GR-01 Stage A precedes the first FR-07 application implementation; Stage B is verified after implementation starts. This architecture round is not FR-07 implementation.
16. FR-07 implements only current direct metrics; TTM, FCF YoY, and single-quarter subtraction are deferred. FR-08 uses deterministic extraction/assembly and its functional acceptance is independent of CR-01 cost acceptance.
17. SR-01 covers preferences, logs, errors, API returns, and streaming/debug output as well as formal files. SR-02 covers reads and writes, platform/symlink behavior, and operation-time path changes; untested platforms are not marked passing.
18. PR-01 uses a fixed offline workload, separate startup/terminal pre-replace samples, 20 enabled/disabled pairs retaining negative differences, and separate percent/absolute p95. QR-01 fixes replay before live; CR-01 uses contract v4 with the two-field execution/acceptance state table. QR-02/export/multi-worker recovery/TTM/FCF YoY remain deferred only.
19. The phase-only plan is replaced by R0–R8 (§18); every requirement and AC range has first-build, main-owner, and final-acceptance rounds (§19 and `trace-matrix.md` §3.19).

---

## 2. ADD-R method and course requirements

`goal.md` §7 phase 2 and the course introduction (I25) require multi-round **Attribute-Driven Design (ADD)** driven by quality attributes and evidence, not a one-shot component diagram. This repository labels the current round **ADD-R** (Round-based ADD with Risk-first closure). ADD-R is a local working label, not a new course requirement.

ADD-R rules used in this round:

1. Start from architectural drivers, constraints, and quality-attribute scenarios derived from D1 and the baseline.
2. Review the existing architecture before adding components: retain, wrap, replace, or retire each existing asset explicitly.
3. For every driver, compare at least two candidates under the **same safety and functional contract**. A candidate that weakens the gate, binding, redaction, or read-time verification is not comparable.
4. Record per iteration: drivers, candidates, selection rationale, component decomposition, interfaces, error contracts, state ownership, review result, and evidence status.
5. Separate design expectation from measured evidence. A local fixture recomputation is requirement-evidence, not an application test.
6. Close the risky flows end to end: risk input/policy, metric fact/period chain, brief mandatory content and token budget, memory reuse/versioning, publication commit/read validation, single-process recovery envelope/idempotency, and history dependency verification. Export and multi-worker recovery are deferred and are not used as current closure evidence.
7. Define one behavior for normal, business-block, system-failure, over-budget, write-interruption, recovery-retry, and concurrency cases. Character and byte counts are auxiliary; the final model request must obey the token budget.
8. Phase implementation so a testable core closed loop exists before memory, recovery, metrics, and context enhancements. A disabled capability must reject or degrade explicitly.
9. Map every requirement and fit criterion to a component and a planned verification; give each deterministic safety boundary a negative-test direction.
10. Keep pending thresholds and unmeasured benefits honest; never fabricate decisions or test results.

### 2.1 ADD-R iterations in this round

| Iteration | Driver focus | Main decision | Status |
|---|---|---|---|
| 0 | Full-scope audit and retain/adjust assessment | Extend Lean A; do not rewrite the graph/agents | Proposed |
| 1 | Deterministic portfolio risk (`FR-04`, `INV-02`, `SB-01` risk branch) | Pure evaluator inside the shared `SafetyGate` | Proposed |
| 2 | Publication lifecycle, history, recovery (`FR-05`, `FR-06`, `QR-02`, `FR-02`, `INV-01`) | Extend `ArtifactPublisher` with permanent publication snapshot and recovery envelope; claim/fencing is deferred | Proposed |
| 3 | Financial fact/metric evidence (`FR-07`, `FR-01`, `FR-03`) | Deterministic fact/metric service through `DataAccessService` | Proposed |
| 4 | Downstream brief and token budget (`FR-08`) | Brief view and budget policy inside the existing `ContextAssembler` | Proposed |
| 5 | Integration, compatibility, phasing, evidence review | Phased extension; adapters rather than rewrite | Proposed |
| 6 | Coordination, component realization, envelope/digest contracts | `RunCoordinator`/`RunContext` split; logical components; explicit envelopes and digests | Proposed |
| 7 | Recovery scope and deliverable rounds | Single-process startup guard; lease/fencing/takeover deferred; R0–R8 plan with per-AC rounds | Proposed |

Round 3 is the current revision. Its decisions are recorded in `docs/architecture/adr/003-add-r-round-3.md` and applied throughout this blueprint. ADR 001 and ADR 002 remain historical decision records, amended where Round 3 changes their current-scope statements.

---

## 3. Scope and requirement inventory

| ID | Type | Status | Title | FCs | Rounds (first build / main owner / final acceptance) |
|---|---|---|---|---|---|
| `FR-01` | functional | approved | Single execution per identical logical data query | 9 | R2 / R4 / R8 |
| `FR-02` | functional | approved | Lifecycle-complete run manifest | 11 | R1 (FC01–FC07), R4 (FC08–FC11) / R4 / R8 |
| `FR-03` | functional | approved | Canonical data-availability state and critical-gap decision table | 10 | R2 / R4 / R8 |
| `FR-04` | functional | approved | Deterministic portfolio-risk evaluation before finalization | 9 | R3 / R3 / R8 |
| `FR-05` | functional | approved | Historical formal publication retrieval | 3 | R6 / R6 / R8 |
| `FR-06` | functional | approved | Startup recovery of pending formal publication | 6 | R4 (snapshot primitives), R6 (startup scan) / R6 / R8 |
| `FR-07` | functional | approved | Deterministic derived financial metrics (direct metrics only) | 10 | R5 / R5 / R8 |
| `FR-08` | functional | approved | Unified downstream analyst-report brief | 4 | R7 / R7 / R8 |
| `PR-01` | performance | approved | Bounded run-record write and end-to-end overhead | 4 | R4 / R8 / R8 |
| `CR-01` | cost | approved | Downstream brief local cost attribution and approved target | 5 | R7 / R7 / R8 |
| `GR-01` | governance | approved | Frozen independent reference set for financial metrics | 6 | R0 (Stage A), R5 (Stage B) / R5 / R8 |
| `QR-01` | quality | approved | Live cache A/B quality and risk-policy separation | 5 | R2 (data path), R8 (evaluation) / R8 / R8 |
| `QR-02` | performance | deferred | Bounded startup recovery performance | 2 | Deferred; no current round assignment |
| `SB-01` | invariant | approved | Deterministic fail-closed final-output gate | 12 | R3 / R3 / R8 |
| `INV-01` | invariant | approved | One bound formal result across artifacts and memory | 11 | R1/R4 (binding), R6 (lifecycle close) / R6 / R8 |
| `INV-02` | invariant | approved | Deterministic portfolio-risk authority and zero unsafe approvals | 6 | R3 / R3 / R8 |
| `SR-01` | security | approved | Secret-safe credential records | 7 | R1 / R7 (all new boundaries) / R8 |
| `SR-02` | security | approved | Path confinement and escape protection | 2 | R1 / R6 (history/recovery read/write integration) / R8 |

Approved total: 17 requirements, 120 fit criteria. Deferred total: 1 requirement, 2 fit criteria. Grand total: 18 requirements, 122 fit criteria.

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
| D-09 Model-free startup recovery with one publication | `FR-06` | Requires a recovery envelope, a single-process duplicate-start guard, idempotent memory completion, and the same commit condition; multi-worker claim/fencing is deferred. |
| D-10 Bounded recovery performance with zero correctness loss | `QR-02` | Requires a fixed workload, monotonic timing, nearest-rank p95, and retained failures; the target is provisional. |
| D-11 Deterministic financial fact and metric evidence | `FR-07` | Requires structured fact identity, as-of visibility, period/fiscal-position matching, exact formulas, n/a reasons, and a persisted evidence bundle. |
| D-12 Bounded downstream brief without authority or quality loss | `FR-08` | Requires canonical mandatory content, separate mandatory/compressible budgets, token measurement, reference resolution, and a quality gate. |
| D-13 Compatibility and operability | Existing codebase, `goal.md` | Requires adapters for CLI, `propagate`, `stream_run`, backtest, reporting, memory, checkpoint, and tools instead of a full rewrite. |
| D-14 Coordination, identity, and incremental modifiability | Round 3 design, `goal.md` | Requires `RunCoordinator`/`RunContext` separation, logical component mapping, explicit envelopes/digests, and R0–R8 so each round has entry/exit evidence. |
| D-15 Single-process recovery honesty | `FR-06`, deferred scope | Requires a simple exclusive startup guard and duplicate-start guard now; lease/fencing/takeover/multi-worker is a deferred extension, not a current claim. |

---

## 5. Constraints

| ID | Constraint |
|---|---|
| C-01 | Single-user local deployment; no multi-user authentication, encryption at rest, or access control in this scope. |
| C-02 | No new vendor, exchange calendar, portfolio simulator, order execution, slippage, fees, or FX conversion. |
| C-03 | Existing vendor caches may remain cross-run; the `FR-01` run cache is per-run and never shared. |
| C-04 | The existing Python/LangGraph graph, agents, tool registry, reporting renderer, and memory substrate remain; the change is a governance extension, not a rewrite. |
| C-05 | D1 v1.25.0 is the current registry; 17 active requirements are approved as a requirement-design baseline and QR-02 is deferred. No implementation, test, live-evaluation, or threshold approval is inferred. |
| C-06 | ADD-R Round 3 modified `architecture-blueprint.md` and `docs/architecture/**` and added ADR 003; it did not modify `docs/req/**`. The later D1 v1.24.0 freeze normalized FC identifiers/approval/mapping, and the v1.25.0 CR-01 correction changes only its state expression and necessary references. |
| C-07 | Application code, tests, member proposals, transcripts, permissions, governance rules, secrets, and `baseline/**` are not modified. |
| C-08 | The 30% concentration, 5% stop-distance, freshness window, QR-02 2.000 s, and brief thresholds remain provisional until human approval. A passed risk check is not a loss guarantee. |
| C-09 | History and recovery paths are confined to configured roots; export is deferred and, if reactivated, must not overwrite a non-empty target. |
| C-10 | One final authority (`SafetyGate`), one publication commit condition (terminal manifest completed plus read-time `INV-01`), one context assembler (`ContextAssembler`), one coordinator (`RunCoordinator`), one data entry (`DataAccessService`). |
| C-11 | Design expectations and measured evidence are labeled separately. No implementation or test is claimed. |
| C-12 | The requirements validator `--check` passes with the current unretained-source note and locally available dependencies; a clean CI dependency declaration remains a D4 task. |
| C-13 | Current `FR-06` is single-process sequential recovery. Lease/fencing/takeover/multi-worker is deferred; no current document may require it. |
| C-14 | TTM metrics, FCF YoY, export, and QR-02 benchmarking are deferred. They may appear only as deferred scope, not as current acceptance obligations. |
| C-15 | Components are logical responsibilities; the module table is a proposed mapping and must be audited for duplicate ownership before implementation. |

---

## 6. Quality-attribute scenarios

| ID | Attribute | Source | Stimulus | Required response and measure |
|---|---|---|---|---|
| QS-01 | Correctness / determinism | `FR-01`, `FR-03`, `INV-01` | Same evidence and inputs, shuffled order, concurrent calls, warm/cold cache | Same business conclusions; duplicate query executions = 0; coverage/gap/binding mismatches = 0. |
| QS-02 | Safety | `SB-01`, `FR-04`, `INV-02` | Stock Buy/Overweight with missing, invalid, stale, inconsistent, insufficient-cash, unsupported, or over-limit risk input | No tradeable output; stable risk code; formal `REVIEW`; reason-specific `review_class`; unsafe approvals = 0. |
| QS-03 | Fail-closed system failure | `SB-01`, `FR-04` | Gate or evaluator raises, times out, or cannot parse input | Gate status `error`, run `failed`, primary reason `portfolio_risk_evaluator_error`/`gate_internal_error`, `review_class=gate_system_error`, no tradeable output. |
| QS-04 | Auditability | `FR-04`, `FR-07`, `INV-02` | Reviewer re-reads a completed publication | Risk input artifact digest, policy digest, metric fact IDs, formula/version, and metric result digest are independently recomputable. |
| QS-05 | Consistency | `INV-01`, `FR-05`, `FR-06` | Reader opens a completed run or a recovered run | Terminal manifest completed plus read-time `INV-01`; all artifacts bind; missing/corrupt content is never returned as success. |
| QS-06 | Security | `SR-01`, `FR-05` | Secret or path traversal appears in a record, history query, or export target (export deferred) | Known-secret/pattern matches = 0; out-of-root writes = 0; if export is reactivated, a non-empty target returns `EXPORT_CONFLICT` and is byte-identical. |
| QS-07 | Recoverability | `FR-06` | Interrupted publication; duplicate single-process startup; unsupported concurrent recovery | Model/data/graph/settlement/reflection calls = 0; one committed publication per `run_id`; at most one memory entry; duplicate start is rejected or waits with bounded retry; concurrent recovery is explicitly rejected. |
| QS-08 | Performance | `FR-02`, `PR-01` | Published manifest and recovery workload | Startup and terminal pre-replace writes are measured separately; 20 paired enabled/disabled end-to-end runs retain negative differences; percent and absolute p95 are separate; provisional thresholds do not block functional acceptance. QR-02 is deferred. |
| QS-09 | Context efficiency and quality | `FR-08`, `CR-01` | Long analyst reports and five downstream debate roles | Mandatory gaps/metrics/safety constraints preserved; token budget obeyed; FR-08 functional acceptance is independent of CR-01; quality/safety claims remain separate from cost/token claims; no saving claimed until accepted. |
| QS-10 | Modifiability / testability | All | New requirement or policy version | Logical service boundary and versioned policy allow table-driven tests without rewriting agents; deterministic rules are pure functions; each round has a bounded change surface. |
| QS-11 | Compatibility | Existing codebase | Existing CLI, `propagate`, `_run_graph`, `stream_run`, `save_reports`, checkpoint, backtest, report, memory, and tool calls | Existing tests keep passing; adapters preserve documented return shapes; stream/debug output stays intermediate/unapproved; no silent behavior change. |
| QS-12 | Operability | `FR-02`, `FR-05`, `FR-06` | Pending, failed, quarantined, or cleanup-failed publication | Distinct run/gate/decision/visibility statuses; history excludes non-committed records; cleanup failure after commit is a warning and does not change history. |
| QS-13 | Contract integrity | `INV-01`, `INV-02`, `SR-01` | Producer/consumer exchange of envelopes and digests | Envelope owner/version/mutability/error fields match; content digests and file-byte hashes are distinct; redaction precedes digesting; no hash DAG cycle. |

---

## 7. Retain / adjust assessment of the existing architecture

| Existing asset | Decision | Adjustment |
|---|---|---|
| LangGraph graph, agents, debate order | Retain | Do not rewrite; insert preflight before analysts and finalization after the graph. |
| `tradingagents/dataflows/router.py` and vendor modules | Retain and wrap | `DataAccessService` owns key normalization, run cache, single-flight, counters, and provenance; direct vendor calls are forbidden for new paths. |
| `reporting.write_report_tree` and `_SECTIONS` | Retain as renderer | `ArtifactPublisher`/`PublicationRenderer` call it; add a versioned section manifest and digest. |
| `memory/log.py`, `settlement.py`, `reflection.py` | Retain as substrate | `MemoryService` becomes the only public writer/reader; extend for risk summary and recovery completion. |
| `cli/run.py`, `cli/display.py`, `cli/prefs.py` | Retain UX | `EntrypointAdapter` normalizes input; display consumes the published result; prefs use the audit/restore split. |
| `TradingAgentsGraph.propagate`, `_run_graph`, `record_decision`, `_log_state` | Retain graph, retire direct formal writes | `propagate` becomes a compatibility adapter that finalizes and publishes; `_run_graph` is an internal stage; `record_decision` records the proposal/evidence only; `_log_state` is internal evidence/render input. |
| `TradingAgentsGraph.stream_run` and debug printing | Retain as intermediate stream | Mark every rating/decision as unapproved/intermediate, scan it, and never present it as the formal result. |
| `TradingAgentsGraph._memory_step`, `settle_pending`, `settle_all_pending` | Retain as substrate activity | Formal decision memory is written only by `MemoryService` after gate/commit; settlement/reflection remain separate. |
| `save_reports`, `save_sections`, HTML rendering | Retain as adapters | Require a finalized/published record; otherwise deterministic error. |
| `backtest.py` | Retain | Per-cell `RunContext`; same gate; `REVIEW` excluded from scoring. |
| `default_config.py` | Retain | Extend with policy identifiers and capability switches; no secrets. |
| Existing tests | Retain | Add regression and new suites; do not change existing test semantics. |
| D2 v0.1/v0.2 Lean A design | Retain and consolidate | Add Round 3 `RunCoordinator`, logical component mapping, envelope/digest contracts, single-process recovery, and R0–R8. |
| D2 v0.1 trace matrix (6 requirements / 54 ACs) | Replace | Superseded by the 18-requirement / 119-FC matrix. |
| D2 v0.1 open decisions | Retain and extend | Resolved items stay resolved; new architecture open decisions are added. |

No existing public writer is deleted. Old writers are wrapped, made private, or require a finalized record. `propagate` keeps its `(final_state, signal)` return shape after publication.

---

## 8. ADD-R iteration record

### 8.1 Iteration 0 — Full-scope drivers and retain/adjust decision

- **Drivers**: D-01 through D-13; the approved requirement design must be implemented without creating duplicate authority, transaction, data path, or context entry.
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
  - P-A: Extend `ArtifactPublisher` with a permanent publication snapshot, a temporary recovery envelope, a single-process duplicate-start guard, and shared read-time verification; multi-worker claim/fencing is deferred.
  - P-B: A separate archive service with its own transaction and commit marker.
  - P-C: Re-run the graph/analysis to recover.
  - P-D: Directory-scan history without a section manifest.
- **Selection**: P-A. P-B creates a second commit authority. P-C violates model-free recovery and cost constraints. P-D can mix foreign/stale files and cannot prove binding.
- **Decomposition**: `PublicationSnapshotStore`, `ReportSectionManifestBuilder`, `HistoryService`, `RecoveryService`, `RecoverySnapshotStore`, `StartupRecoveryGuard`, `PublicationStatusReader`. `ExportService`, `RecoveryClaimStore`/`LeaseManager`, and `RunOwnershipLock` are deferred.
- **Interfaces**: `publish(record) -> PublishResult`; `list_publications(filters) -> HistoryPage`; `get_run(run_id) -> VerifiedPublication`; `scan_and_recover(startup) -> RecoveryReport`; `StartupRecoveryGuard.acquire(run_id, wait_budget)`; deferred: `export`, `claim`, `assert_owner`, `RunOwnershipLock.critical_section`.
- **Review**: permanent-snapshot files are persisted and validated before the terminal commit; the recovery envelope is complete, self-contained, and read-back verified before `snapshot_ready`; the original memory entry is written idempotently; the terminal candidate is validated, atomically committed, read back, and only then is temporary material cleaned. Post-commit read failure never overwrites the committed terminal manifest; it is rejected as success and recorded in an independent diagnostic. Terminal manifest completed plus successful read-time `INV-01` is the only commit condition; no independent marker; recovery uses saved records only; envelope references resolve internally with digests; duplicate startup is rejected or bounded; cleanup failure is a warning; history excludes pending/failed/quarantined. Export, lease/fencing/takeover, and multi-worker claims are deferred.
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
- **Review**: fact identity uses subject + accession + filing_ref; as-of visibility; latest-filed restatement; ambiguous period/filing -> n/a; exact direct-metric formulas; capital-expenditure sign normalization; fiscal-year P/E only; program-appended block regardless of tool use; metric block is numeric authority; conflict detection is limited to recognizable structured claims; missing/corrupt bundle blocks metric-dependent recovery rather than triggering a live fetch. **TTM metrics, FCF YoY, and quarter-by-subtraction are deferred.** **Timing**: facts, metrics, the block, and the conflict check are produced after the fundamentals report exists but before research debate consumes that report; final publication only persists the existing block/bundle.
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

### 8.7 Iteration 6 — Coordination, component realization, envelopes, and digests (Round 3)

- **Drivers**: D-14, D-15, QS-01, QS-05, QS-13; the need to consolidate v0.2 before implementation.
- **Candidates**:
  - C-A: `RunCoordinator` (stages) + `RunContext` (identity/dependencies) + logical components; explicit envelopes and digests.
  - C-B: keep lifecycle, coordination, and business policy in `RunContext`.
  - C-C: one physical module per named component.
  - C-D: keep mutable working objects as the de facto interface between services.
- **Selection**: C-A. C-B risks a god object and hidden policy. C-C creates premature file/module churn and still does not prove ownership. C-D makes version/mutability/error semantics untestable and allows accidental aliasing.
- **Decomposition**: `RunCoordinator`, `RunContext`, logical component map (§9.2), envelope contracts (§9.6.8), digest projections (§9.6.9), single-process guard (§9.6.10).
- **Review**: one coordinator, one identity owner, one gate, one publisher, one data entry, one context entry, one memory writer; every envelope has one owner/version/mutability/error rule; every digest has a field projection and order; scanning precedes digesting.
- **Evidence**: design only. No implementation or measurement is claimed.

### 8.8 Iteration 7 — Recovery scope honesty and round-based delivery (Round 3)

- **Drivers**: `FR-06`, QS-07, QS-08, QS-09; course review needs explicit rounds.
- **Candidates**:
  - R-A: simple exclusive startup guard + duplicate-start guard + bounded retry; single-process only; lease/fencing deferred.
  - R-B: keep lease/fencing/takeover as current obligations.
  - R-C: no guard at all.
  - P-A: R0–R8 with entry/exit evidence and per-AC ownership.
  - P-B: keep phase-only plan.
- **Selection**: R-A + P-A. R-B overstates current `FR-06` and creates unproven concurrency behavior. R-C permits duplicate publication. P-B hides prerequisites and per-AC ownership.
- **Review**: duplicate startup is bounded; unsupported concurrent recovery is rejected; deferred scope (lease/fencing, export, multi-worker, TTM/FCF YoY, QR-02) is labeled; every requirement/AC range has build/owner/acceptance rounds.
- **Evidence**: design only; no recovery test or timing measurement is claimed.

---

## 9. Selected architecture — Lean A Extended

### 9.1 Design principles

1. **One coordinator**: `RunCoordinator` orders stages, invokes services, hands off failures, and hands off publication. It contains no business policy and no direct formal write.
2. **One identity/dependency owner**: `RunContext` fixes the clock, allocates `run_id`, owns versions and run-scoped paths, and holds dependency references. It does not decide business policy.
3. **One evidence path**: all data, including SEC facts for metrics, goes through `DataAccessService`.
4. **One coverage truth**: `AvailabilityIndex` produces the only critical profile, `CoverageView` versions, and sealed `CoverageSnapshot`.
5. **One formal authority**: `SafetyGate` invokes the pure risk evaluator and produces the only `FinalizedRunRecord`.
6. **One publisher**: `ArtifactPublisher` performs the only formal publication, including recovery-driven completion.
7. **One context assembler**: `ContextAssembler` assembles full context and the bounded brief view.
8. **One memory writer**: `MemoryService` owns decision entries, versions, and recovery completion.
9. **One commit condition**: terminal manifest `run_status=completed` plus read-time `INV-01`; no independent commit marker.
10. **Permanent versus temporary**: the committed `publication_snapshot` is permanent; the `recovery_envelope` and guard material are temporary pending artifacts.
11. **Logical components**: components are responsibilities; the module mapping is proposed, not a file-per-name mandate.
12. **Single-process recovery now**: one exclusive startup guard plus duplicate-start guard; lease/fencing/takeover is deferred.
13. **Design versus evidence**: every non-baseline claim is a design expectation until measured.

### 9.2 Component catalog

Expected new governance code lives under `tradingagents/run/`, but **components are logical responsibilities**. Several small components may share one module, and some adapters live beside the existing code. A component audit must verify the owner and write boundary before implementation. Existing modules are wrapped, not rewritten.

| Component | Proposed module | Responsibility | Inputs | Outputs | Error contract | State ownership | Dependencies | Rounds |
|---|---|---|---|---|---|---|---|---|
| `RunCoordinator` | `run/coordinator.py` | Ordered stage coordination, service invocation, failure/publication handoff; no policy | `RunRequest`, `RunContext` | Stage results, final handoff | `CoordinationError`, `StageError` | Stage order/progress (not formal decision) | RunContext, services | R1 |
| `RunContext` | `run/context.py` | Run identity, fixed clock, versions, run-scoped paths, dependency references; no business policy | Config, entrypoint, request | Run handle, `run_clock`, path/version handles | `ConfigError`, `ClockError`, `FutureAnalysisDateError` | Run identity, clock, paths, versions | PolicyCatalog, SecretRedactor | R1 |
| `EntrypointAdapter` | `run/entrypoints.py` | Normalize CLI/programmatic/backtest/headless/stream input | Entry args | `RunRequest` | `UnsupportedEntrypoint` | None | RunContext | R1/R4 |
| `StartupRecoveryGuard` | `run/startup_guard.py` | Single-process exclusive startup guard, duplicate-start protection, bounded retry, unsupported-concurrency rejection | Startup request, lock path | Guard token / rejection | `RecoveryBusy`, `RecoveryUnsupported` | Startup guard state | Local filesystem | R1/R6 |
| `PolicyCatalog` | `run/policy.py` | Versioned policy identities and defaults | Policy files/config | `PolicySet`, risk/brief/recovery policy handles | `PolicyVersionError`, `PolicySnapshotUnavailable` | Immutable policy snapshots | None | R1 |
| `Canonicalizer` | `run/canonical.py` | NFC/LF/sorted-key projection and SHA-256 | Objects | Canonical bytes, digests | `CanonicalizationError` | None | None | R1 |
| `DataAccessService` | `run/data_access.py` | Semantic query key, immutable results, run cache, single-flight/cancel/timeout, retry/fallback budgets, counters, provenance | Query request, run context | `DataResult`, availability record | `VendorError`, `BudgetError`, `CacheScopeError`, `QueryCancelled` | Run cache, query ledger | Vendor adapters | R2 |
| `PreflightCoordinator` | `run/preflight.py` | Mandatory market price and stock statements before analysts, independent of analyst selection | Critical profile | `EvidenceBatch` | `ProfileError`, `PreflightError` | None (writes evidence) | DataAccessService, AvailabilityIndex | R2 |
| `AvailabilityIndex` | `run/availability.py` | Critical profile, executed/missing records, supports, aggregation, versioned `CoverageView`, sealed `CoverageSnapshot` | Clock, config, records | `CoverageView`, `CoverageSnapshot` | `ProfileError`, `AggregationError`, `SnapshotSealed` | Coverage view versions and sealed snapshot | RunEvidenceStore | R2 |
| `RunEvidenceStore` | `run/evidence.py` | Run-scoped records, missing records, supports, counters, digest inputs | Records/events | Evidence snapshot, counters | `EvidenceError` | Run evidence | Canonicalizer | R1/R2 |
| `SafetyGate` | `run/safety_gate.py` | Sole formal authority; invalid rating blocks first; sole caller of risk validation/policy/evaluation; reason priority; review class; formal decision | Proposal, sealed snapshot, raw risk envelope (optional) | `FinalizedRunRecord` or failure; risk evidence payload | `GateInputError`, `GateError` | Formal decision | AvailabilityIndex, RiskInputValidator, RiskPolicyResolver, PortfolioRiskEvaluator | R3 |
| `FinalizedRunRecord` / `RunFailureRecord` | `run/finalization.py` | Immutable formal/failure contract and envelope identity | Gate output | Record | `SchemaError`, `RecordError` | Immutable records | Canonicalizer | R3 |
| `ArtifactPublisher` | `run/publisher.py` | Sole formal writer; normalize/redact; stage/validate permanent and recovery envelopes; security/cross-artifact check; terminal commit; read-back; diagnostic; cleanup | Finalized record, evidence, render inputs, memory plan | `PublishResult`, terminal manifest, diagnostics | `PublishError`, `InvariantError`, `PostCommitCorruption` | Publication commit, artifact hashes, diagnostic records | Renderer, MemoryService, snapshot stores, StartupRecoveryGuard | R4 |
| `MemoryService` | `run/memory_service.py` | Stable-decision/evidence separation, reuse/new plan, idempotent write, recovery completion, settlement | Finalized record, recovery envelope, reservation | `MemoryWriteResult`, `MemoryPlan` | `MemoryConflict`, `MemoryScanError`, `ReservationError` | Memory decision entries | TradingMemoryLog, MemoryReservationStore, SecretRedactor | R4/R6 |
| `MemoryReservationStore` | `run/memory_reservation.py` | Persistent append-only allocation history; high-water over all allocations including failed; retry/recovery reuse; derived status only | ticker/date, decision_id, owner run | `MemoryReservation` | `ReservationError`, `ReservationConflict` | Reservation ledger | MemoryLock, Canonicalizer | R4/R6 |
| `PortfolioManagerAdapter` | `run/proposal.py` | Invoke the original Portfolio Manager with full reports/plans/risk debate/past memory; build the unapproved `ModelProposal`; no formal decision | Full analyst reports, investment plan, Trader plan, risk debate, past memory | `ModelProposal` | `ProposalError` | Model proposal (audit-only) | `agents/managers/portfolio_manager.py`, MemoryService, ContextAssembler | R3 |
| `MemoryRecoveryCoordinator` | `run/memory_coordination.py` | Handle a same-decision uncommitted entry in another run; bounded wait without locks; trigger recovery under the original run identity; typed retry/conflict statuses | B decision/reservation, pending entry/guard status | `MemoryCoordinationResult` | `MemoryPendingRetryable`, `MemoryRecoveryUnavailable`, `MemoryRecoveryFailed`, `MemoryConflict` | Coordination status only; never ownership transfer | MemoryService, MemoryReservationStore, RecoveryService | R6 |
| `SecretRedactor` | `run/security.py` | Known-value/pattern scan for formal files, preferences, logs, errors, API returns, stream/debug; redact; path confinement | Value/record/path | `ScanResult`, redacted value | `SecurityFailure`, `PathEscape` | Scan results | None | R1/R7 |
| `CheckpointCoordinator` | `run/checkpoint.py` | Graph-resume support matrix (distinct from publication recovery) | Checkpoint, signature | `ResumePlan` | `ResumeRejected` | Resume decisions | Evidence, PolicyCatalog | R1 |
| `LegacyWriterAdapter` | `run/adapters.py` | Convert old writers/entry points (CLI, propagate, stream, save_reports, backtest) to finalized-record consumers | Legacy args/state | Published result | `LegacyWriteRejected` | None | Publisher, MemoryService | R4 |
| `RiskInputValidator` | `run/risk_input.py` | Canonical decimal input validation and applicability; invalid rating is blocked before applicability | Caller risk envelope | `ValidatedRiskInput` or `RiskDiagnostic` | `RiskInputError` | None | Canonicalizer | R3 |
| `PortfolioRiskEvaluator` | `run/risk_evaluator.py` | Pure deterministic concentration/stop-distance evaluation | Validated input, policy snapshot | `RiskEvaluation` | `RiskEvaluationError` | None | Decimal only | R3 |
| `RiskPolicyResolver` | `run/risk_policy.py` | Locate, load, validate, digest the policy snapshot | Policy catalog/path | `PortfolioRiskPolicySnapshot` | `PolicySnapshotUnavailable` | Immutable policy snapshot | PolicyCatalog | R3 |
| `RiskEvidenceStore` | `run/risk_evidence.py` | Build normalized input artifact or safe diagnostic payload | Validated input/diagnostic | Artifact payload, `input_ref`/`input_digest` | `RiskEvidenceError` | None (publisher writes) | Canonicalizer, SecretRedactor | R3 |
| `PublicationSnapshotStore` | `run/publication.py` | Permanent committed publication records and read validation | Committed record/sections | Verified publication | `CorruptRecord`, `NotFound` | Permanent publication snapshot | Canonicalizer, SecretRedactor | R4 |
| `ReportSectionManifestBuilder` | `run/render.py` | Versioned rendering and section manifest | Finalized record, fixed inputs, capability set | Sections, manifest, complete report | `RenderError` | None | `reporting.py` | R4 |
| `HistoryService` | `run/history.py` | Bounded listing and `get_run` revalidation; on-demand scan preferred, optional rebuildable non-authoritative index | Filters, run_id | History page, verified publication | `InvalidFilter`, `NotFound`, `CorruptRecord` | Read-only | PublicationSnapshotStore | R6 |
| `ExportService` (deferred) | `run/export.py` | Deferred extension: `display_copy`/`verified_package`, closure, conflict | run_id, mode, target | Export result | `ExportConflict`, `HistoricalReferenceUnverified`, `PathEscape` | Export target only | HistoryService, SR-01 | Deferred |
| `RecoveryService` | `run/recovery.py` | Single-process startup recovery orchestration; terminal-first; bounded retry | Startup scan, guard | `RecoveryReport` | `RecoveryError`, `RecoveryBusy` | Recovery orchestration | Snapshot/guard/publisher/memory | R6 |
| `RecoverySnapshotStore` | `run/recovery_snapshot.py` | Write/verify/read/quarantine temporary `RecoveryEnvelope` | Formal records, fixed inputs | `RecoveryEnvelope` | `SnapshotError` | Temporary recovery envelope | Canonicalizer, SecretRedactor | R4/R6 |
| `RecoveryClaimStore` / `LeaseManager` (deferred) | `run/recovery_claim.py` | Deferred multi-worker extension: per-run claim, lease, fencing token, takeover | run_id, owner | Claim/lease | `ClaimRejected`, `StaleLease` | Claim/lease state | None | Deferred |
| `RunOwnershipLock` (deferred) | `run/ownership.py` | Deferred multi-worker extension: shared per-run lock, owner/fencing, takeover/release | run_id, owner, write function | Protected-write result | `LockBusy`, `StaleLease`, `LostOwnership` | Run lock/lease state | Local filesystem | Deferred |
| `SecEdgarAdapter` (existing, wrapped) | `tradingagents/dataflows/vendors/sec_edgar.py` | Only vendor-facing SEC statement/JSON calls; returns raw statements and filing metadata; invoked only through `DataAccessService` | Query parameters | Raw statements/JSON + filing metadata | vendor errors mapped by `DataAccessService` | None | Vendor/HTTP | R5 |
| `PublicationStatusReader` | `run/publication.py` | Distinguish analysis_complete, snapshot_ready, committed, failed, quarantined, corrupt | run roots | Status | `StatusError` | Read-only | Manifest, snapshot stores | R4/R6 |
| `FinancialFactService` | `run/financial_facts.py` | Request structured SEC fact payloads through `DataAccessService`; normalize into the fact contract; never calls a vendor directly | Ticker, as_of | `StructuredFactSet` | `FactUnavailable`, `FactAmbiguous` | None (evidence cached) | DataAccessService, RunEvidenceStore | R5 |
| `FinancialMetricService` | `run/financial_metrics.py` | Pure current direct metrics, period identity, n/a reasons; TTM/FCF YoY deferred | Fact set, price, as_of | `MetricBlock` | `MetricError` (n/a is a result) | None | Decimal only | R5 |
| `MetricEvidenceBundleBuilder` | `run/metric_evidence.py` | Persist facts/formulas/versions/digests | Fact set, block | `MetricEvidenceBundle` | `MetricEvidenceError` | None (publisher writes) | Canonicalizer | R5 |
| `MetricConflictDetector` | `run/metric_conflict.py` | Detect recognizable structured metric claims that contradict the block | Block, claims | `MetricConflict[]` | None | None | None | R5 |
| `FundamentalsAdapter` | `run/adapters.py` | Append metric block regardless of tool use; expose optional tool | Analyst state | Updated fundamentals output | `AdapterError` | None | Financial services | R5 |
| `ContextAssembler` | `run/context_assembler.py` | L0-L5 context, budget, compression, brief view; for the five target roles the brief replaces full analyst reports | Coverage view/version, reports, history, brief policy | `ContextBundle`, `BriefBundle` | `ContextBudgetError`, `BriefRejected` | None | DownstreamBriefBuilder, TokenCounter | R7 |
| `DownstreamBriefBuilder` | `run/brief.py` | Deterministic extraction/reuse of the five-role brief; mandatory/compressible budget; protected markers; view version; audit metadata | Reports, gaps, metric block, policy, tokenizer, view version | `BriefBundle` | `BriefRejected`, `InvalidMarker` | None | TokenCounter, PolicyCatalog | R7 |
| `TokenCounter` | `run/tokens.py` | Model/tokenizer measurement for the final request | Text, model | Token count | `TokenizerUnavailable` | None | Model tokenizer | R7 |
| `BriefAuditStore` | `run/brief.py` | Persist separate `ContextAuditMetadata` | Brief metadata | Artifact payload | `AuditStoreError` | None (publisher writes) | SecretRedactor | R7 |

`RunContext` remains a lifecycle/DI container. It is not allowed to grow into a business-rule engine.

### 9.3 Principal interfaces

```text
RunCoordinator.run(request, entrypoint) -> PublishedRunResult | RunFailureRecord
  # stages: start -> profile -> running manifest -> preflight -> analysts ->
  # facts/metrics/block -> brief/coverage view -> research/risk debate ->
  # final coverage snapshot -> gate -> publish/handoff
RunContext.start(config, entrypoint, request) -> RunContext
RunContext.fail(exc) -> RunFailureRecord
DataAccessService.query(request, run_ctx) -> DataResult
DataAccessService.cancel(query_key, reason) -> None            # releases the single-flight slot
DataAccessService.preflight(profile, run_ctx) -> EvidenceBatch
AvailabilityIndex.build_profile(clock, config) -> CriticalProfile
AvailabilityIndex.view(version?) -> CoverageView               # program, versioned, immutable
AvailabilityIndex.seal(records) -> CoverageSnapshot            # once, before the gate
PortfolioManagerAdapter.propose(full_reports, investment_plan, trader_plan, risk_debate, past_memory) -> ModelProposal
SafetyGate.finalize(proposal, coverage_snapshot, raw_risk_envelope?) -> FinalizedRunRecord | RunFailureRecord
  # invalid rating -> blocked first; no fake not_applicable
  # inside the gate, exactly once when applicable:
  RiskInputValidator.validate(raw) -> ValidatedRiskInput | RiskDiagnostic
  RiskPolicyResolver.resolve(policy_ref, config) -> PortfolioRiskPolicySnapshot
  PortfolioRiskEvaluator.evaluate(input, policy) -> RiskEvaluation
ArtifactPublisher.stage_risk_evidence(payload) -> RiskInputRef | DiagnosticRef
ArtifactPublisher.publish(record, recovery_envelope?) -> PublishResult
ArtifactPublisher.publish_failure(failure) -> FailurePublishResult
StartupRecoveryGuard.acquire(run_id, wait_budget) -> GuardToken | RecoveryBusy | RecoveryUnsupported
StartupRecoveryGuard.release(token) -> None
PublicationSnapshotStore.read(run_id) -> VerifiedPublication | NotFound | CorruptRecord
HistoryService.list_publications(ticker?, date?, limit, offset) -> HistoryPage
HistoryService.get_run(run_id) -> VerifiedPublication
ExportService.export(run_id, mode, target) -> ExportResult      # deferred extension
RecoveryService.scan_and_recover() -> RecoveryReport
MemoryReservationStore.plan(ticker, date, decision_id, owner_run_id) -> MemoryPlan
MemoryReservationStore.commit_projection(reservation, manifest_ref) -> None   # derived, rebuildable
MemoryReservationStore.fail(reservation) -> None
MemoryRecoveryCoordinator.resolve_pending(decision_id, entry_digest, waiting_run) -> MemoryCoordinationResult
FinancialFactService.fetch(ticker, as_of) -> StructuredFactSet
  # implementation: DataAccessService.query("sec_structured_facts", ...) -> SecEdgarAdapter payload -> normalize
FinancialMetricService.compute(facts, price, as_of) -> MetricBlock   # current direct metrics only
MetricEvidenceBundleBuilder.build(facts, block) -> MetricEvidenceBundle
MetricConflictDetector.detect(block, claims) -> MetricConflict[]
ContextAssembler.assemble(view, reports, history, brief_view?) -> ContextBundle
DownstreamBriefBuilder.build(inputs, policy, tokenizer, coverage_view_version) -> BriefBundle | BriefRejected
MemoryService.store_finalized(record) -> MemoryWriteResult
MemoryService.complete_recovery(envelope) -> MemoryWriteResult
MemoryService.get_past_context(...) -> str
SecretRedactor.scan(value, phase) -> ScanResult                 # includes preferences/logs/errors/API/stream
SecretRedactor.assert_path(path, root, mode: read|write) -> None
Canonicalizer.digest(projection) -> str
```

The deferred multi-worker extension would add `RunOwnershipLock.critical_section(...)`, `RecoveryClaimStore.claim/assert_owner`, and lease/fencing. Those signatures are not current requirements.

### 9.4 State ownership

| State | Owner | Rules |
|---|---|---|
| Run identity, clock, versions, paths | `RunContext` | Created once; future `as_of_date` rejected before analysis/risk; no business policy. |
| Stage order and handoff | `RunCoordinator` | Orders stages and invokes services; does not own coverage, risk, context, or publication decisions. |
| Query executions, run cache, counters | `DataAccessService`/`RunEvidenceStore` | Run-scoped; never shared; terminal outcomes cached. |
| Critical profile, `CoverageView`, sealed snapshot | `AvailabilityIndex` | Program-only; versioned view; snapshot sealed once before the gate; late results cannot mutate a used snapshot. |
| Risk input artifact/diagnostic | `RiskEvidenceStore` builds; `ArtifactPublisher` writes | Valid input only; invalid input produces no raw-value artifact. |
| Risk policy snapshot | `RiskPolicyResolver` | Locatable, versioned, digest-bound; explicit provisional or approved status; missing/invalid blocks. |
| Portfolio risk result | `PortfolioRiskEvaluator` | Pure result; no persistence; returned only to `SafetyGate`. |
| Model proposal | `PortfolioManagerAdapter` creates; `SafetyGate` consumes | Unapproved; source=portfolio_manager; Trader/risk-debater output is only a source reference. |
| Formal decision | `SafetyGate` | Only formal authority; `REVIEW` on block/error. |
| Finalized record | `SafetyGate` creates; `ArtifactPublisher` publishes | Immutable; retries reuse identity. |
| Publication snapshot | `PublicationSnapshotStore` | Files written/validated before terminal commit; authoritative only after commit; permanent and immutable. |
| Recovery envelope | `RecoverySnapshotStore` | Complete/self-contained/read-back verified before `snapshot_ready`; temporary pending envelope; cleanup after commit. |
| Startup guard | `StartupRecoveryGuard` | One exclusive guard per process/run; duplicate start rejected or waits with bounded retry; unsupported concurrent recovery rejected. Lease/fencing is deferred. |
| Recovery claim/lease (deferred) | `RecoveryClaimStore` | Future multi-worker extension only; not current `FR-06`. |
| Memory entries | `MemoryService` | Immutable decision portion; append-only settlement. |
| Memory version reservation | `MemoryReservationStore` | Persistent, append-only allocation history; next version is `high_water + 1` over all historical allocations including failed; retries/recovery reuse; failed versions never reissued. |
| Pending same-decision coordination | `MemoryRecoveryCoordinator` | Bounded wait without locks; recovery under the original run identity/reservation/envelope; typed retry/conflict; never ownership transfer. |
| Metric evidence bundle | `MetricEvidenceBundleBuilder` builds; publisher writes | Current direct metrics only; produced before research debate and persisted in publication/recovery envelopes; recovery never refetches. |
| Brief and audit metadata | `DownstreamBriefBuilder`/`ContextAssembler`; audit payload persisted by publisher | Deterministically extracted/assembled before five-role context; reused with a recorded view version; a view only; never mutates full/formal/history/recovery artifacts. |

### 9.5 Dependency rules

- `run/` may import existing `tradingagents/agents`, `dataflows`, `memory`, `reporting`, and `cli` modules only through adapters.
- `RunCoordinator` may invoke services and order stages; it must not contain coverage, risk, metric, context, gate, or publication policy.
- `RunContext` owns identity/clock/versions/paths/dependency references only; it must not decide business outcomes.
- **Only `DataAccessService` may call vendor adapters.** The existing `tradingagents/dataflows/vendors/sec_edgar.py` capability is wrapped by `SecEdgarAdapter` and invoked only by `DataAccessService`; it returns raw statements/JSON plus filing metadata and is responsible for no policy or fact normalization.
- `FinancialFactService` calls `DataAccessService.query("sec_structured_facts", ...)`, receives the adapter payload, and normalizes it into `financial_fact`s. It never imports or calls a vendor module directly. The same query boundary supplies run cache, counters, provenance, and as-of visibility; `get_income_statement`, `get_balance_sheet`, and `get_cashflow` use the same adapter and cache.
- `PortfolioRiskEvaluator` and `FinancialMetricService` are pure: no LLM, network, vendor, persistence, UI, or clock reads beyond provided inputs.
- `PortfolioManagerAdapter` invokes the original Portfolio Manager and produces the only `ModelProposal`; no Trader or risk-debater output is promoted to the final model proposal.
- `SafetyGate` is the only caller of `RiskInputValidator`, `RiskPolicyResolver`, and `PortfolioRiskEvaluator`. No entrypoint or tool performs an independent applicability/risk evaluation.
- `MemoryRecoveryCoordinator` never transfers an uncommitted entry's ownership to another run. It may only trigger recovery under the original run identity, original reservation, and original recovery envelope.
- `HistoryService` reads through `PublicationSnapshotStore`; it does not scan arbitrary report directories as authority. A derived index, if added, is rebuildable and non-authoritative.
- `ExportService` is deferred; if reactivated, it reads through `HistoryService`/`PublicationSnapshotStore`.
- `RecoveryService` may call only saved-record services, the renderer, the publisher, the startup guard, and the memory completion path; it may not call the graph, LLM, vendors, settlement, or reflection.
- `ContextAssembler` is the only context entry; `DownstreamBriefBuilder` is a helper, not an alternate assembler. For the five target roles, the brief replaces the four full analyst reports rather than being added beside them.
- Current serial publication and recovery use `StartupRecoveryGuard`; there is no current lease/fencing protocol. The future multi-worker extension must add a new ADR/amendment and must not be assumed by current code.

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
    recovery_envelope.json
    inputs/...
  guards/
    startup.lock                     # single-process exclusive startup guard
  diagnostics/
    post_commit_corruption.json      # independent audit diagnostic
```

- `publication_ref` = `{root: "publication", files: [{relative_path, sha256, hash_scope: "file"}], record_hash}`; it contains no terminal-manifest hash. All paths are relative and confined.
- Report, history, and independent verification resolve only inside `publication/` and the terminal manifest. They never require `recovery/`. Export is deferred; if reactivated, it must use the same material.
- The terminal manifest may retain `recovery_envelope_summary` (status, digest, created_at) as **audit information only**. It is not a verification dependency; after cleanup, `get_run` and memory binding validation MUST still work from `publication/`; future export, if reactivated, must also work from permanent material.
- `recovery/` is self-contained while it exists; after successful commit and post-commit validation, it may be removed. A missing `recovery/` after cleanup is not corruption.
- `guards/startup.lock` is a single-process startup guard, not a lease. A future multi-worker design may add `locks/run.lock` and `locks/lease.json`; those files are not part of the current requirement.

#### 9.6.2 Single-process startup guard (current) and deferred lease/fencing

Current `FR-06` is single-process sequential recovery. The current design uses:

- `guards/startup.lock`: one OS advisory exclusive lock (or equivalent single-process lock) acquired at startup recovery. It is held only for the guard check and protected writes, never across model/analyst work.
- A duplicate-start guard: if the lock is held, a second startup is rejected or waits with a bounded retry budget; it does not take over, delete the lock, or publish.
- Unsupported concurrent recovery (multiple processes, workers, or hosts) is rejected with a typed `RecoveryUnsupported`; it is not attempted under a weaker protocol.
- The running manifest and terminal manifest remain the state authority. No separate claim marker is created.
- Normal publication and recovery share the same exclusive guard boundary so the same `run_id` is not written concurrently.
- Failure is isolated per recovery task; retries are bounded; no pending task is a normal startup.

**Deferred extension (not current):** `lease.json`, `owner_id`, `fencing_token`, `lease_expires_at`, takeover, stale-lease reclaim, and multi-worker claims. If reactivated, a new ADR/amendment must define the file-lock/lease distinction, lock order (run lock -> memory lock), takeover, lost-owner rejection, and release rules. Current code and tests must not claim these behaviors.

#### 9.6.3 Memory reservation ledger authority and recovery

- `memory/reservations.jsonl` (or an equivalent sidecar under the memory lock) is an append-only allocation history authoritative for **version allocation**, not for decision content. Each record: `{ticker, trade_date, decision_id, entry_version, owner_run_id, status: reserved|committed|failed, created_at, committed_at, failure_reason}`. A `fencing_token` field is a deferred multi-worker extension and is absent from the current ledger.
- The allocator keeps a persistent, lock-protected **high-water mark over every historical allocation, including failed reservations**. The next version is `high_water + 1`. A failed reservation permanently occupies its version; it never leaves the high-water mark and is never reissued.
- A retry/recovery reuses its own reservation keyed by the original `run_id` and `decision_id`; a different run must receive a higher version. Effective version remains the highest `entry_version` whose source terminal manifest is `completed` and binds the entry.
- `committed` is a derived projection: it is true only when the terminal manifest is `completed` and read-time `INV-01` passes. A ledger commit mark is an audit/cache aid, not a second commit condition; if missing or if the ledger write fails after commit, it is rebuilt from the terminal manifest. Append `reserved` before the recovery envelope, `failed` on abort before a completed manifest, and the `committed` projection only after commit plus read verification.
- Ledger replay/repair: replay the append-only allocation records to reconstruct the high-water mark including failed versions; rebuild `committed` projections from terminal manifests. Do not derive allocation history solely from committed manifests (that would lose failed reservations). If the allocation history is missing or corrupt, stop new allocation, restore from a durable backup or operator-approved reconstruction, and never silently reset the watermark or reissue a failed version.
- Recovery of an uncommitted reservation uses the original `run_id`, original `entry_version`, and original recovery envelope. The reservation is never transferred to another run. A binding conflict is never overwritten.

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
| `record.json` | Canonical `FinalizedRunRecord` content and `artifact_binding` fields, using the §9.6.9 projection with `artifact_binding.record_hash` and all result-carrying hashes removed | Run-level generated/evaluated/finished timestamps, `run_clock.now_utc`, local paths, cache counters, terminal-manifest hash, recovery-envelope hash, record/self/file hashes | 1 |
| `binding.json` | `artifact_binding` fields plus the already-computed `record_hash` | Terminal-manifest hash, its own file hash, recovery-snapshot digest, commit-evidence hash, any field that would feed back into `record_hash` | 2 |
| `report/section_manifest.json` | Section paths, fields, byte sizes, SHA-256, complete-report digest | Terminal-manifest hash, binding file hash, recovery digest | 3 |
| `final_state.json`, `risk/*`, `metrics/*`, `memory/entry_binding.json` | Their own canonical content and referenced evidence digests | Terminal-manifest hash, binding file hash, recovery digest | 3 |
| `recovery/recovery_envelope.json` | Self-contained inputs, formal decision/binding, memory plan/reservation, versions | Final terminal-manifest hash; it may carry terminal-candidate identity (`run_id`, `decision_id`, `record_hash`, reservation) | 4 |
| terminal `run_manifest.json` | `publication_ref.files` hashes (including `binding.json`), formal decision, security scans, section manifest, metric bundle, memory binding, and `recovery_envelope_summary` (audit-only) | Its own hash; any file that contains its hash; optional commit-evidence hash | 5 |
| `diagnostics/commit_evidence.json` (optional) | Terminal-manifest hash and read-time validation result | Never hashed by the terminal manifest; never a commit condition | 6 (after commit) |

- `binding.json` never stores a terminal-manifest hash or a full terminal-manifest file hash.
- The terminal manifest never hashes itself. Readers compute its hash from the manifest bytes and use it as a read-time token.
- If an audit summary of the terminal manifest is needed, use `diagnostics/commit_evidence.json`; it is outside the permanent hashed set and is not a second commit authority.
- A `recovery_envelope_summary` inside the terminal manifest may record status/digest/created-at as audit information. It does not make `recovery/` a required verification dependency.
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

#### 9.6.7 Component realization rules

Components in §9.2 are logical responsibilities. The proposed module is a mapping, not a mandatory one-file-per-name layout.

- A module may host several small components only if each exported symbol maps to exactly one owner and the write boundary remains auditable.
- A component may be a class, a set of pure functions, or an adapter. The name is not the contract; the responsibility, inputs, outputs, errors, and state ownership are the contract.
- The following ownership must not be shared or duplicated: `SafetyGate` (formal decision), `ArtifactPublisher` (publication commit), `DataAccessService` (external data), `ContextAssembler` (context entry), `MemoryService` (decision memory write), `PortfolioManagerAdapter` (model proposal source), `RunCoordinator` (stage order), `RunContext` (identity/clock/versions/paths).
- A helper that only formats, parses, or renders may be shared, but it must not become a second authority or bypass the owner.
- Before implementation, a component audit maps every real symbol to a logical component and records any grouping. The audit is design evidence, not an application test.
- Existing symbols remain where they are unless an adapter is explicitly required: `cli/run.py:run_analysis`, `graph/trading_graph.py:TradingAgentsGraph.propagate`, `_run_graph`, `record_decision`, `_log_state`, `stream_run`, `save_reports`, `memory/log.py:TradingMemoryLog`, `reporting.py:write_report_tree`, `dataflows/router.py:route_to_vendor`, and `backtest.py:run_backtest`.

#### 9.6.8 Envelope contracts

All envelopes are canonical JSON objects with an explicit `schema_version`. Field names below are proposed design names pending review; the D1 manifest/record schema remains authoritative for any field it already defines.

| Envelope | Owner / writer | Required fields | Version and mutability | Error contract | Serialization boundary |
|---|---|---|---|---|---|
| `PublicationEnvelope` | `ArtifactPublisher` builds; `PublicationSnapshotStore` retains | `run_id`, `record_version`, `record_hash`, `decision_id`, `formal_decision`, `model_proposal_ref`, `artifact_binding`, `section_manifest`, `publication_ref`, `risk_evaluation_ref`, `metric_bundle_ref?`, `memory_entry_binding?`, `versions`, `security_scan_summary` | Versioned by `record_version`; immutable after terminal commit; working candidate is not readable as authority | `PublishError`, `InvariantError`, `CorruptRecord` | Canonical JSON plus per-file SHA-256; no terminal-manifest hash inside; no mutable aliases |
| `RecoveryEnvelope` | `RecoverySnapshotStore` | `schema_version`, `run_id`, `decision_id`, `proposal_digest`, `decision_digest`, `record_hash`, `input_digest?`, `entry_digest?`, `evidence_digest`, `sealed_coverage_snapshot`, `risk_refs`, `metric_bundle_ref?`, `memory_plan/reservation`, `render_inputs`, `capability_set`, `terminal_candidate_identity`, `versions`, `created_at` | Versioned by `schema_version`; complete/self-contained; immutable after `snapshot_ready`; temporary | `SnapshotError`, `SnapshotIncomplete`, `SnapshotCorrupt` | Canonical JSON + referenced file digests; every reference resolves internally; no final terminal-manifest hash |
| `ModelProposal` | `PortfolioManagerAdapter` | `schema_version`, `proposal_id`, `run_id`, `rating`, `text`, `source=portfolio_manager`, `source_refs`, `model_provider`, `model_id`, `proposal_status=unapproved`, `created_at` | Versioned by `schema_version`; immutable; never formal | `ProposalError` | Canonical JSON; source refs are digests/handles, not secrets; no formal-decision fields |
| `CoverageView` | `AvailabilityIndex` | `view_version`, `profile_hash`, `executed_refs`, `missing_refs`, `gaps`, `sources`, `status`, `created_at` | Monotonic `view_version`; immutable per version; program-only | `ProfileError`, `AggregationError` | Canonical JSON; version recorded by the brief/context audit |
| `CoverageSnapshot` | `AvailabilityIndex`, consumed by `SafetyGate` | `snapshot_version`, `critical_profile_hash`, `snapshot_hash`, `view_version`, `critical_gap_ids`, `structured_gaps`, `provenance_digest`, `computed_by=program`, `sealed_at` | Sealed once before the gate; immutable; late results cannot mutate it | `ProfileError`, `AggregationError`, `SnapshotSealed` | Canonical JSON; hash bound into gate input and record |
| `RiskEvaluation` | `PortfolioRiskEvaluator` returns to `SafetyGate`; evidence written by publisher | `schema_version`, `applicability`, `status` (`passed`/`blocked`/`error`), `reason_codes`, `primary_reason_code`, `review_class`, `projected_weight`, `stop_distance`, `input_digest?`, `policy_digest`, `threshold_status`, `evaluated_at` | Versioned; immutable once returned; no persistence/memory/UI dependency | `RiskEvaluationError` | Decimal strings, canonical JSON; no binary float; safe diagnostic has no raw invalid value |
| `MetricEvidenceBundle` | `MetricEvidenceBundleBuilder` builds; publisher writes | `schema_version`, `facts`, `metric_block`, `formula_versions`, `normalization_rule_version`, `period_identity`, `as_of`, `input_digest`, `result_digest`, `status` | Versioned; immutable; current direct metrics only | `MetricEvidenceError` | Canonical JSON; facts/formulas/status/n-a reasons; TTM/FCF YoY absent from current bundle |
| `ContextAuditMetadata` | `DownstreamBriefBuilder`/`ContextAssembler` | `schema_version`, `coverage_view_version`, `brief_policy_version`, `mandatory_digest`, `omitted_compressible_ids`, `budget_decision`, `fallback_reason?`, `reference_handles`, `tokenizer_id`, `measured_tokens`, `final_snapshot_hash?` | Versioned; immutable per assembly; stored separately | `AuditStoreError` | Canonical JSON; never mutates full/formal/history/recovery artifacts |

Rules:

- A consumer must not read a mutable working object where an envelope is required.
- Cross-envelope references are digest-bound or immutable-version references. A stale or mismatched reference is a typed error, not a silent substitution.
- Envelopes never contain secrets; scanning/redaction occurs before serialization and digest computation.
- Adding a required field is a version change. Removing or renaming a required field is a schema change that must be reviewed against D1.

#### 9.6.9 Digest projections and generation order

Content digests and file-byte hashes are different. Every digest below is computed after redaction and canonicalization.

| Digest | Canonical projection includes | Explicitly excludes | Computed at |
|---|---|---|---|
| `proposal_digest` | Stable `ModelProposal` fields: rating, text, source, source_refs, model provider/id, proposal_status | Run-level `created_at`, run_id when used only as invocation identity, paths, counters, formal-decision fields | R3, before gate |
| `decision_digest` | Stable formal decision content: decision status, final rating, formal decision text, gate status/primary reason/reason codes/review class, risk status code(s), metric block result digest when referenced | `run_id`, coverage/provenance evidence, timestamps, paths, counters, publication/recovery hashes, model proposal text | R3, after gate |
| `input_digest` | Canonical validated risk input fields and their exact decimal strings; for a timestamp-sensitive input, the valuation time/cutoff and source identifier required by FR-04 | Raw invalid values, secrets, run-level generated time, publication hashes | R3, after validation |
| `policy_digest` | Canonical risk-policy snapshot content, including threshold status, approval reference, precision rule, freshness window | File mtime, local absolute path, run-level time | R3, at policy resolution |
| `entry_digest` | Stable memory decision content: `decision_id`, ticker/trade_date, formal decision status/rating/text | Coverage, gaps, provenance, risk evidence, source run/snapshot, timestamps, commit status, reuse metadata | R4, before memory write |
| `evidence_digest` | Coverage status, critical gap IDs, provenance digest, and the evidence references required by INV-01 | Stable decision text, memory version, publication hashes, run-level timestamps | R4, before publication |
| `record_hash` | Canonical `FinalizedRunRecord` content plus `artifact_binding` fields, including `decision_digest`, `proposal_digest` reference, `input_digest`/`policy_digest` references, metric/risk evidence references, formal decision, and gate result | `artifact_binding.record_hash` and every result-carrying hash; run-level `generated_at`, `evaluated_at`, `finished_at`, `run_clock.now_utc`, local absolute paths, cache counters, computed snapshot timestamps, terminal-manifest hash, recovery-envelope hash, file/self hashes | R4, after envelopes are stable |
| File-byte hash | Actual bytes of each permanent file | N/A | R4, after serialization |

Generation order is fixed:

1. redact and normalize formal content;
2. canonicalize the stable content projections;
3. compute `proposal_digest`, `decision_digest`, `input_digest`, `policy_digest`;
4. compute `entry_digest`/`evidence_digest` for memory/publication references;
5. compute `record_hash` from the canonical projection with result hashes excluded;
6. fill `artifact_binding.record_hash`, serialize `record.json`/`binding.json`;
7. compute file-byte SHA-256 for permanent files;
8. build and validate the terminal manifest;
9. after commit, record read-back result and terminal-manifest replace completion time in external measurement evidence or an audit-only diagnostic, never inside the immutable record hash.

Preserved timestamps include filing `filed_at`, evidence/observation-window timestamps, risk `evaluated_at`, valuation time/cutoff, and other source-evidence times required by FR-04/FR-07. A blanket removal of all timestamps is forbidden.

#### 9.6.10 Single-process recovery protocol

```text
startup
  -> StartupRecoveryGuard.acquire(run_id, wait_budget)
       -> acquired: continue
       -> held: wait bounded then return RecoveryBusy
       -> unsupported concurrent recovery requested: RecoveryUnsupported
  -> scan pending run_ids
  -> terminal-first check (outside model/data calls)
       -> committed + read-time INV-01 + identity match: idempotent success
       -> committed + identity conflict: RUN_ID_CONFLICT
       -> committed + permanent corruption: CORRUPT_RECORD
       -> not committed/absent: continue
  -> read/verify RecoveryEnvelope (references, digests, versions)
  -> determine recorded memory plan/reservation
  -> render fixed sections, compute hashes, stage permanent files
  -> under the guard: idempotent memory write; promote permanent files;
     write/atomically replace the terminal manifest; release guard
  -> post-commit read validation
       -> success: cleanup temporary material (warning only on cleanup failure)
       -> failure: keep committed manifest; independent diagnostic;
          reject as success/history
```

- Recovery uses only saved records, the renderer, the publisher, the guard, and the memory completion path. It calls no model, external data, graph, settlement, or reflection.
- It preserves the original `run_id`, decision identity, reservation, and envelope. It does not transfer ownership or create a substitute entry.
- Duplicate startup is rejected or waits with bounded retry. Unsupported multi-worker/concurrent recovery is rejected; lease/fencing/takeover is not attempted.
- No pending task is a normal startup, not a failure.

---

## 10. Entry points and adaptation

### 10.1 Entry-point matrix

| Entry point | Current path | Target path | Compatibility |
|---|---|---|---|
| CLI analysis | `cli/main.py` → `cli/run.py:run_analysis` | `CliEntrypoint` → `RunContext` + `RunCoordinator` → graph → `SafetyGate` → `ArtifactPublisher` | Existing prompts/options keep working; final display uses the published result. |
| Programmatic graph | `TradingAgentsGraph.propagate` → `_run_graph` | `RunCoordinator.run()` returns a published result; `propagate()` adapter returns `(final_state, signal)` | Tuple shape preserved; `signal` comes from `FinalizedRunRecord.formal_decision`, not a raw state rating. |
| Graph execution | `TradingAgentsGraph._run_graph` | Internal graph stage invoked by `RunCoordinator` | Terminal PM output is a `ModelProposal`; no direct formal write. |
| Stream/debug | `TradingAgentsGraph.stream_run` and `debug=True` printing | Intermediate stream adapter | Every rating/decision is marked `proposal_status=unapproved`, `visibility=intermediate`, and scanned; never shown as formal. |
| Root demo | `TradingAgents/main.py` | Programmatic `run()` | Remove direct writer use; demo prints the published decision. |
| Backtest | `backtest.py:run_backtest` | Per-cell `RunContext` → `RunCoordinator.run()` → same gate | `REVIEW` excluded from scoring; per-cell memory isolation. |
| Data tool calls | `agents/tools.py`, `dataflows/router.py:route_to_vendor` | `DataAccessService` adapter around registered tools | Same tool names/arguments; run cache, counters, and evidence added; direct vendor bypass forbidden. |
| Sentiment prefetch | `agents/analysts/sentiment_analyst.py:sentiment_analyst_node` → `get_news.func`, `fetch_stocktwits_messages`, `fetch_reddit_posts` | `DataAccessService` prefetch queries | Same query key/counters/evidence as tool calls; no hidden second data path. |
| Mandatory preflight | None | `PreflightCoordinator` via `DataAccessService` | Runs before analysts; stock statements independent of analyst selection. |
| Direct report writer | `graph/trading_graph.py:save_reports`, `reporting.py:write_report_tree` | Internal renderer called by `ArtifactPublisher`; public adapter requires a published record | Direct public call without a record fails deterministically. |
| Direct memory writer | `memory/log.py:TradingMemoryLog.store_decision` | `MemoryService.store_finalized`/`complete_recovery` | Legacy method becomes internal or record-dependent. |
| Memory step | `graph/trading_graph.py:_memory_step`, `settle_pending`, `settle_all_pending` | Substrate activity; no formal decision write | Settlement/reflection remain separate; formal memory only after gate/commit. |
| Graph state writer | `trading_graph.record_decision`, `_log_state` | Proposal/evidence only | No direct formal memory or formal visibility. |
| Checkpoint lifecycle | `begin_checkpoint`, `checkpoint_input`, `end_checkpoint`, `clear_checkpoint_on_success` | `CheckpointCoordinator` + graph stage | Graph resume only; new `run_id` on resume; not publication recovery. |
| History CLI/API | None | `HistoryService` adapters | New read-only commands; no legacy migration; export deferred. |
| Startup recovery | None | `RecoveryService.scan_and_recover` + `StartupRecoveryGuard` | Single-process; unsupported concurrent recovery is rejected. |

### 10.2 Old-writer policy

- `reporting.write_report_tree` and HTML rendering remain rendering primitives called only by the publisher/renderer.
- `TradingMemoryLog.store_decision` becomes internal to `MemoryService`.
- `TradingAgentsGraph._log_state` becomes internal evidence/render input; it is not formal visibility.
- `TradingAgentsGraph.record_decision` records the model proposal and run evidence, not the formal decision or formal memory.
- `TradingAgentsGraph.save_reports` is a compatibility adapter requiring a finalized record.
- `TradingAgentsGraph.stream_run` is an intermediate-only stream; its ratings must be marked unapproved and scanned.
- `_memory_step`, `settle_pending`, and `settle_all_pending` remain substrate activities; they cannot write the formal decision entry.
- Direct calls without a `FinalizedRunRecord` fail with a deterministic error and never fall back to an unfinalized path.
- `propagate` publishes before returning; a caller cannot obtain a formal result without publication.

### 10.3 Compatibility and deprecation

| Surface | Approach | Regression evidence |
|---|---|---|
| `propagate` | Adapter; same tuple after publication | Existing programmatic tests plus published-result tests. |
| `_run_graph`/`record_decision`/`_log_state` | Internal proposal/evidence path | Writer-bypass audit; no formal leak. |
| `stream_run`/debug | Intermediate-only, unapproved, scanned | Stream display and bypass-attempt tests. |
| `save_reports`/`write_report_tree` | Adapter requiring a record; renderer primitive | Report regression and negative direct-call tests. |
| `store_decision` | Internal to `MemoryService` | Memory idempotency/conflict regression. |
| `_memory_step`/settlement | Substrate activity only | Memory lifecycle/settlement regression. |
| Checkpoint lifecycle | Graph resume only | Checkpoint resume vs publication recovery tests. |
| CLI display | Consumes published result | CLI smoke and blocking-display tests. |
| Backtest | Per-cell published result | Backtest regression and memory isolation. |

No rewrite of agents or graph structure is planned. `propagate` return semantics, report/memory writers, and backtest callers are explicitly migrated with adapters and tests.

---

## 11. Data flow

### 11.1 Normal run

```text
Entrypoint (CLI / propagate / backtest / headless / stream)
  -> RunCoordinator.run(request)
  -> RunContext.start(config)
       -> reject future as_of_date
       -> fix run_clock (as_of_date, now_utc, timezone, mode)
       -> allocate run_id, versions, run-scoped paths
  -> PolicyCatalog load
  -> AvailabilityIndex.build_profile(run_clock, asset, capabilities, overrides)
  -> write running manifest BEFORE model calls
       (safety_gate.status=not_run, recovery.status=pending)
  -> RunEvidenceStore open
  -> DataAccessService bind
  -> PreflightCoordinator.run(profile)
       -> mandatory market_price
       -> stock income/balance/cashflow (independent of analyst selection)
       -> shared run cache and evidence
  -> Analyst stage (parallel as today)
       -> DataAccessService -> semantic query key, immutable result,
          run cache, single-flight/cancel/timeout, retry/fallback budgets,
          HTTP counters at the request boundary, evidence
       -> sentiment prefetch uses the same DataAccessService path
       -> fundamentals report produced
       -> FinancialFactService.fetch() through DataAccessService
          -> FinancialMetricService.compute() current direct metrics only
          -> MetricEvidenceBundleBuilder.build()
          -> MetricConflictDetector.detect(recognizable claims)
          -> FundamentalsAdapter appends the block before Bull/Bear
  -> AvailabilityIndex.view(version)
  -> DownstreamBriefBuilder.build(view_version) once
  -> Research debate (Bull/Bear)
       -> brief replaces the four full analyst reports for these roles
       -> LLM proposals (unapproved)
  -> Research Manager / Trader
  -> Risk debate (Aggressive/Conservative/Neutral)
       -> reuse brief/view_version; reassemble if the view changed
  -> Portfolio Manager (original terminal node, wrapped by PortfolioManagerAdapter)
       -> consumes full reports/plans/risk debate/memory
       -> produces ModelProposal {rating, text, source=portfolio_manager,
          source_refs, proposal_status=unapproved}
  -> AvailabilityIndex.seal()
       -> executed + component_missing records
       -> critical gaps, sealed CoverageSnapshot, provenance digest
  -> SafetyGate.finalize(model_proposal, sealed coverage_snapshot, raw_risk_envelope?)
       -> invalid rating blocks first; never fakes not_applicable
       -> exactly one risk applicability/validation/policy/evaluation path
       -> applicable risk recorded even when coverage blocks
       -> gate result, primary reason, review class, formal decision, risk evidence
  -> FinalizedRunRecord (immutable; decision_id, binding, digests)
  -> ArtifactPublisher.publish(record)
       1 normalize and redact formal content
       2 memory reuse/new plan and reserve entry_version
       3 write/read-back-verify self-contained RecoveryEnvelope
       4 idempotent memory decision write
       5 stage/validate permanent publication files
       6 security scans + cross-artifact validation
       7 atomically replace running manifest with terminal manifest (completed)
       8 read back and validate
       9 cleanup temporary recovery material (warning only on failure)
  -> formal display/history consume FinalizedRunRecord or verified committed publication only
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

### 11.3 Recovery path (single-process)

```text
startup
  -> StartupRecoveryGuard.acquire(run_id, wait_budget)
       -> held: wait bounded, then RecoveryBusy
       -> unsupported concurrent recovery: RecoveryUnsupported
  -> RecoveryService.scan pending run_ids
  -> FIRST: read the terminal manifest
       -> completed + read-time INV-01 passes + identity matches:
            idempotent success; do NOT require recovery/
       -> completed + identity conflict: RUN_ID_CONFLICT
       -> completed + permanent artifacts corrupt: CORRUPT_RECORD
       -> not completed or absent: continue as a pending publication
  -> read and verify the RecoveryEnvelope (references, digests, versions)
  -> read the recorded memory plan/reservation
  -> render fixed sections; compute hashes; assemble/stage permanent files
  -> under the guard:
       -> re-check terminal identity and envelope validity
       -> no-op/conflict/corrupt exits without writing
       -> complete the one original planned memory entry idempotently
       -> promote staged permanent files; atomically commit terminal manifest
       -> release guard
  -> post-commit read validation
       -> success: cleanup own temporary material (warning only on failure)
       -> failure: keep committed manifest immutable; independent diagnostic;
          reject as success/history
```

- Recovery is single-process and sequential. Duplicate startup is rejected or waits with bounded retry; unsupported multi-worker/concurrent recovery is rejected.
- No lease/fencing/takeover is attempted in the current design. The future multi-worker extension must be a new ADR/amendment.
- Long reads, parsing, rendering, and hashing happen outside the startup guard; the guard protects the check-and-write boundary.
- Recovery uses no LLM, external data, graph, settlement, or reflection. It reuses the original identity and reservation; a failed retry leaves a version gap but not a second publication.
- Lease/fencing/takeover behavior is not claimed by current code or tests.

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

- `SafetyGate.finalize(proposal, coverage_snapshot, raw_risk_envelope?)` is the **only** caller of `RiskInputValidator`, `RiskPolicyResolver`, and `PortfolioRiskEvaluator`. No entrypoint, tool, publisher, or recovery path performs an independent applicability or risk evaluation. The gate runs before the terminal manifest; a committed manifest is not a gate precondition.
- Applicability is determined once inside the gate from `asset_type` and the model rating: stock + Buy/Overweight only. An invalid model rating is blocked first and is never converted to `not_applicable`. The gate validates the risk input, resolves the policy, and evaluates exactly once, then records passed, blocked, or error even when coverage also blocks.
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

**Metric formulas (current direct metrics only)**

- Current metrics: revenue YoY (quarterly and annual), revenue QoQ, gross/operating/net margin, fiscal-year P/E, current ratio, liabilities-to-assets, and current-span free cash flow.
- **Deferred:** TTM revenue, TTM diluted EPS, TTM P/E, FCF YoY, and any single-quarter derivation by subtraction. These are not current FR-07 obligations and must not appear in current acceptance claims.
- YoY uses the prior fiscal year's same fiscal quarter, span, and cumulative duration; QoQ uses the immediately preceding fiscal quarter; FCF uses the current reported span only.
- No single quarter is derived by subtraction. Zero denominators, non-positive growth bases, zero/negative EPS, missing fields, currency mismatch, unit mismatch, or fiscal-period mismatch produce typed n/a reasons.

**Authority and conflict**

- The program appends a `metric_block` regardless of whether the model calls the offered tool. The block carries metric IDs, fact IDs, filing refs, formula and versions, periods, values or n/a reasons, and computed/approximate/n/a status.
- The metric block is the numeric authority; a model narrative cannot override it.
- Conflict detection is limited to a recognizable `metric_id`/declared structured claim, explicit period, and parseable numeric value. A conflict is disclosed and the contradicted claim is labeled unverified. Free-form prose numbers are outside deterministic detection and this limitation is recorded.

**Persistence and recovery**

- The `MetricEvidenceBundle` carries structured facts, formula/fact/policy versions, the current direct metric block, `input_digest`, and `result_digest`; deferred TTM/FCF YoY rows are absent.
- It is written before research debate and persisted in the permanent publication snapshot and the recovery envelope.
- Recovery reads the bundle and never refetches filings, calls a model, or reruns the analysis. A missing/corrupt bundle blocks a metric-dependent publication rather than triggering a live fetch.

### 12.3 Downstream brief, mandatory content, token budget, and references (FR-08)

**Scope and replacement**

- The default brief is deterministic extraction/assembly, not an unchecked model rewrite. Only Bull Researcher, Bear Researcher, and the three risk debaters receive the brief. Analyst, manager, portfolio-manager, memory, history, recovery, and formal readers keep full inputs.
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
- FR-08 functional acceptance is independent of CR-01 optimization acceptance. Missing prices/targets or an unapproved cost threshold block CR-01 claims, not the functional brief behavior required by FR-08.
- Evaluation uses a controlled switch under the same model/config/data/risk policy. Net tokens = added output tokens - reduced downstream input tokens; net cost = added output cost - reduced input cost saving; if either price is missing, cost fields are null. No saving is claimed until the frozen contract reports `accepted` with approved `quality_loss_max` and zero safety escapes.

### 12.4 Memory reuse, version reservation, and recovery completion

**Decision identity**

- `decision_id` is content identity; `run_id` is invocation identity. Memory reuse is keyed by `decision_id`/`entry_digest`, not `run_id`.
- `entry_digest` covers only stable decision content; `evidence_digest` covers coverage/gaps/provenance and may differ across reruns without implying corruption.

**Plan, reservation, and write**

- Before the recovery envelope is written, `MemoryService` determines the plan: reuse a committed entry, reuse an uncommitted reservation owned by the same publication, or reserve a new version. Stable decision content and current-run evidence are separate: identical content may reference a committed historical entry, but current risk evidence is never written back into that entry.
- `MemoryReservationStore` is a persistent, append-only, lock-protected allocation history with a monotonic high-water mark over **all** historical allocations, including failed reservations. The next version is `high_water + 1`; concurrent runs cannot receive the same version.
- The reservation records the ticker/date, decision_id, entry_version, owner `run_id`, and status (`reserved`, `committed`, `failed`). It is written under the memory lock and is included in the recovery envelope. A fencing token is a deferred multi-worker extension, not a current field.
- Retries and recovery reuse their own reservation; they do not allocate a second version. A failed publication permanently occupies its version and leaves a gap; the version does not become effective and the older committed version remains effective.
- `committed` is a derived projection from the terminal manifest plus read-time `INV-01`, not a second commit condition. The ledger's allocation history (including failed reservations) must be durable; repair replays it and must never reissue a failed version.
- The order is fixed: determine plan/reservation -> write recovery envelope containing the plan -> idempotent memory write -> permanent files -> terminal candidate -> commit. The recovery path uses the recorded reservation.
- A different `decision_id` records `supersedes`; only the highest committed version is effective. A same `decision_id` with a different `entry_digest` is a conflict/tamper and is not overwritten. A failed version is never reissued. The reservation ledger owns allocation and derived status only; it is not a second commit condition.
- Memory-disabled runs set `memory.status=disabled` and require no memory artifact.
- Settlement/reflection may append outcome fields but cannot change the binding or formal decision fields.

**Uncommitted same-decision handling**

An entry whose source terminal manifest is not committed is **not** a reusable success. Run B never treats it as committed history and never takes ownership of A's entry.

1. **A is active and its lease is valid**: B waits within a bounded timeout without holding the run lock or memory lock. If A commits and validates within the timeout, B may reuse via `reused_decision_ref`; if not, B returns the explicit retryable status `MEMORY_PENDING_RETRYABLE`. B does not write an entry, allocate a version, or block A's publication.
2. **A is invalid and a valid recovery envelope exists**: B invokes `MemoryRecoveryCoordinator`, which triggers single-process recovery under **A's original `run_id`, original reservation, and original recovery envelope**. The recovered publication remains A's; ownership is never transferred to B. After A commits and validates, B may reuse via historical reference.
3. **A is invalid and no valid recovery envelope exists**: return `MEMORY_RECOVERY_UNAVAILABLE`; B rejects its new-entry path and does not write a substitute entry. Manual recovery/repair is required.
4. **Recovery of A fails**: return `MEMORY_RECOVERY_FAILED` (retryable/manual); B does not transfer ownership or create a second entry.
5. **Binding conflict** (same `decision_id` with different `entry_digest`, inconsistent owner/version, or reserve/commit contradiction): return `MEMORY_CONFLICT`; never overwrite.

Waiting for A holds neither the startup guard nor the memory lock unless the wait is inside a short protected check; it must not prevent A from completing publication. Lease/fencing is not part of the current design.

**Recovery completion**

- If the original publication required memory and the interruption occurred before the first write, recovery creates exactly the one original planned decision entry using the recorded reservation.
- If a partial write exists, recovery idempotently completes that same entry.
- Recovery never changes decision content, creates a different entry, or creates an additional duplicate; memory-disabled originals stay disabled; settlement/reflection calls = 0.

### 12.5 Publication commit and read validation (FR-02/FR-05/FR-06/INV-01)

**Commit order**

1. Running manifest before model calls (`safety_gate.status=not_run`).
2. Preflight; analysts; financial facts/metrics/block; brief and versioned coverage view; research/risk debate; sealed final coverage snapshot.
3. `SafetyGate.finalize` and immutable `FinalizedRunRecord`.
4. Render report sections and the section manifest.
5. Normalize and redact formal content; compute proposal/decision/input/policy digests before any result hash.
6. Determine the memory reuse/new plan and reserve the required `entry_version` under the memory lock; append a `reserved` allocation record.
7. Write the `RecoveryEnvelope`, including the memory plan/version and stable digests, durably; read it back and verify self-contained references; status `snapshot_ready`.
8. Write the original planned memory decision entry idempotently (pending).
9. Stage and validate all permanent publication files **before the terminal commit** in a run-specific staging directory: complete report, section manifest, final-state, risk evidence/policy references, metric bundle when applicable, memory entry/binding, versions, and hashes. The snapshot is not authoritative until the terminal manifest commits.
10. Run security scans and cross-artifact validation, including `entry_digest`/`evidence_digest` consistency and `record_hash` projection. Scanning precedes final digest binding.
11. Build the terminal manifest candidate with binding, formal decision, security scans, section manifest, metric bundle, risk evidence, memory binding, and `publication_ref` hashes. If desired, include a `recovery_envelope_summary` (status/digest/created-at) as audit-only; no terminal-manifest hash is written into `binding.json` or any file hashed by the manifest.
12. Validate the permanent candidate with `INV-01`; separately verify the self-contained recovery envelope for recoverability. The recovery envelope is not part of the formal `INV-01`/history scope. The on-disk manifest is still the running manifest.
13. Enter the `StartupRecoveryGuard` protected boundary for the `run_id`; re-check that the staged content still applies to the current publication state; promote staged permanent files; atomically replace the running manifest with the terminal manifest. This is the only commit point.
14. Post-commit read validation. If it succeeds, history becomes visible; append/refresh the ledger's `committed` projection (audit/cache only, not a commit condition). If it fails, **do not overwrite the committed terminal manifest**: keep it as immutable commit evidence, record an independent corruption diagnostic, reject the record as success, and exclude it from history until repaired.
15. Clean temporary recovery/guard material only after successful post-commit validation; a cleanup failure is a warning and does not change the committed identity.
16. History visibility begins only after steps 13-14 succeed. The permanent snapshot is never created after cleanup.

**Memory ledger integration**

- Before the recovery envelope: append `reserved` with the allocated version; this is durable allocation history.
- On abort before a completed terminal manifest: append `failed`; the version remains permanently occupied and is never reissued.
- On retry/recovery: reuse the same reservation; do not allocate a new version.
- After terminal commit plus read-time `INV-01`: the `committed` projection may be appended, but it is derived/rebuildable. If the ledger update fails, the terminal manifest remains authoritative and the projection is repaired from it.
- A ledger `committed` entry without a completed terminal manifest is not a commit. The ledger never becomes a second commit condition.

**Read predicate and post-commit corruption**

- Every reader requires terminal manifest `run_status=completed` **and** its own read-time `INV-01` validation (manifest hash, artifact hashes, binding, formal decision, security results, section manifest).
- Trusting the manifest status alone is forbidden. A completed manifest that fails validation is treated as corrupt/unavailable, not as a successful formal result.
- A post-commit read failure MUST NOT replace the committed terminal manifest with `failed` or any other status. The terminal manifest is immutable commit evidence. A separate diagnostic record identifies the corrupt run; `HistoryService` returns `CORRUPT_RECORD` and does not return partial content; `ExportService` is deferred.
- A completed-to-failed compensating replace is **not** part of this design. Only pre-commit failures use the running/failed path.
- An independent commit marker is never authoritative. The terminal manifest plus read-time `INV-01` is the only commit condition.

**Recovery cleanup versus formal reads**

- After successful commit and post-commit validation, temporary recovery material (`recovery/`, claim, staging) may be cleaned. Cleanup is not a formal dependency.
- Formal report reads, history `get_run`, and memory binding validation resolve only against the permanent `publication/` snapshot and the terminal manifest. They MUST succeed after `recovery/` is gone. Export is deferred; if reactivated, it must use the same permanent material.
- If the terminal manifest retains a `recovery_envelope_summary`, it is audit metadata only. Readers must not require the temporary recovery file or re-read it to verify the formal record.
- Verification scope: permanent snapshot + terminal manifest = full `INV-01`/history scope (and future export scope if reactivated); recovery envelope = recovery-only, valid until cleanup; terminal recovery summary = audit-only, never a substitute for permanent records.

### 12.6 Single-process recovery, snapshot, and idempotent completion (FR-06)

**Scope**

- Current `FR-06` is single-process sequential recovery. The current protocol is: `StartupRecoveryGuard` -> scan pending -> terminal-first check -> read/verify `RecoveryEnvelope` -> recorded memory plan -> idempotent memory -> permanent files -> terminal commit -> read-back -> cleanup.
- Duplicate startup is rejected or waits with a bounded retry budget; unsupported concurrent recovery is rejected with `RecoveryUnsupported`.
- Lease, fencing, takeover, stale-lease reclaim, and multi-worker claims are a **deferred extension**. They are not required, implemented, or claimed by current `FR-06`.

**Snapshot boundary and order**

- Recovery **first** reads the terminal manifest and verifies the permanent publication. A committed, INV-01-valid, identity-matching publication returns idempotent success and does not require `recovery/`.
- A committed identity conflict returns `RUN_ID_CONFLICT`; a committed publication with corrupt permanent artifacts returns `CORRUPT_RECORD`. Neither overwrites the terminal manifest or auto-republishes.
- Only a record that is not committed and still needs publication continuation reads and verifies the `RecoveryEnvelope`.
- Recovery guarantee begins only at `snapshot_ready`: a complete, durably written, read-back-verified, self-contained, redacted envelope.
- The recovery envelope is temporary. After commit and post-commit validation, it may be cleaned; formal reads depend on the permanent `publication/` snapshot, not the temporary envelope. A terminal `recovery_envelope_summary` is audit-only.
- The memory reuse/new plan and reserved version are determined **before** the envelope is written. The envelope records that plan.
- After the envelope is ready, recovery performs the idempotent memory write, then writes/validates the permanent publication files, then builds and validates the terminal candidate, then commits, then reads back, then cleans temporary material.
- The envelope includes the formal decision and binding, terminal-candidate identity, section manifest and fixed rendering inputs, risk input/policy references, the original required memory decision identity and reserved version, the metric bundle when `FR-07` applies, and schema/renderer versions.
- Every reference resolves inside the envelope with a validated digest; recovery does not depend on a separately lost external file.
- Missing, corrupt, unsupported, or reference-broken envelopes for a still-uncommitted record are quarantined and not published as success; valid source material is retained across persistent faults.

**Guard, retry, and idempotency**

- One simple exclusive startup guard covers the check-and-write boundary. It is not a lease and does not authorize takeover.
- Long reads, parsing, rendering, and hashing run outside the guard; the guard is held only for the protected write/commit boundary.
- Failure is isolated per recovery task; retries are bounded; at most one successful formal publication exists per `run_id` and decision identity.
- A legal completed publication with matching identity is already complete: return idempotent success, do not republish, do not repeat memory, and do not require `recovery/`.
- A completed publication with a different identity returns `RUN_ID_CONFLICT`; a completed publication whose permanent artifacts fail verification returns `CORRUPT_RECORD`. Neither overwrites the terminal manifest or auto-republishes.
- Only an uncommitted/absent record continues to read the recovery envelope. Same `run_id` with the same immutable content is a no-op; different content is `RUN_ID_CONFLICT`.
- Recovery reuses its recorded `reserved` allocation. If the original publication failed, the ledger keeps a `failed` allocation; recovery does not allocate a new version. If recovery fails again, the version remains occupied.
- A post-commit read failure keeps the committed terminal manifest immutable, records an independent corruption diagnostic, and rejects the record as success/history; it does not republish a second terminal manifest.
- `analysis_complete`, `snapshot_ready`, `publication_committed`, `failed`, `quarantined`, and `corrupt` are distinct states; only committed plus read-time `INV-01` is visible as successful history.

**Deferred extension (not current)**

- If multi-worker recovery is reactivated, a new ADR/amendment must define `RunOwnershipLock`, `lease.json`, owner/fencing tokens, takeover, lost-owner rejection, lock order, and release rules. Current code/tests must not claim these behaviors.
- QR-02 remains deferred. If reactivated, it uses the fixed workload and nearest-rank p95 in §12.6.1 below, with the target explicitly provisional.

#### 12.6.1 QR-02 future workload (deferred)

QR-02 is deferred. If reactivated, it uses 100 committed publications and 10 pending valid snapshots, fixed 12-section report maps, one risk evidence object, one required memory write, rendered output and snapshot each at most 1,048,576 bytes, 30 independently reset trials, and nearest-rank p95 at most 2.000 s **provisional**. Timing starts immediately before the startup guard/scan and ends after final read-time validation of every recovered run. Correctness and model-free behavior are zero-tolerance; failures/timeouts are retained and the target is never met by skipping validation.

### 12.7 History retrieval (FR-05/SR-01); export deferred

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

**History authority and index**

- The committed, read-time-verified publication is the only history authority. The current design prefers an on-demand scan of committed publication roots because it has no index-consistency failure mode and the expected run count is small.
- A rebuildable derived index is an optional performance optimization. It must never define commitment, must be reconstructable from permanent publications, and must be revalidated on read. A corrupt/stale index is ignored and rebuilt, not treated as authority.

**Export (deferred)**

- Export is deferred. If reactivated, `display_copy` contains the verified complete report, section manifest, and binding summary; it is not claimed as independently verifiable.
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
| Concurrent normal publication and recovery for same `run_id` | Unchanged | Same formal result | One writer wins; loser rejected before write | Same single-process startup guard; existing completed identity is a no-op; unsupported multi-process concurrency rejected | One committed result | Unchanged | `completed` |
| Two normal publishers for same `run_id` | Unchanged | Same formal result | One writer wins; loser rejected or no-op if identical | Same startup guard and terminal identity check | One committed result | Unchanged | `completed` |
| Recovery duplicate startup | Unchanged | Same gate result | One winner; loser rejected or bounded wait | Simple exclusive startup guard; no claim/fencing | One committed result | Unchanged | `completed` |
| Recovery stale takeover (deferred) | Unchanged | Same gate result | Not current; deferred multi-worker extension | Not current; a new ADR/amendment is required | Not current | n/a | Deferred |
| History query for pending/failed/quarantined | Unchanged | n/a | n/a | n/a | Excluded from successful listing | n/a | n/a |
| History corrupt record | Unchanged | n/a | n/a | n/a | `CORRUPT_RECORD`; no partial content | n/a | n/a |
| Export non-empty target (deferred) | Unchanged | n/a | n/a | n/a | Future `EXPORT_CONFLICT`; byte-identical | n/a | n/a |
| Export unavailable historical proof (deferred) | Unchanged | n/a | n/a | n/a | Future `historical_reference_unverified`, current-run scope | n/a | n/a |
| Secret scan failure | Unchanged | Gate may be blocked; security stage failed | Dangerous content not written; minimal incident record only | Quarantine/fail closed | Not visible | Not written unsafely | `failed` |
| Future `as_of_date` | Rejected before risk | No formal analysis | No manifest completion | No recovery | Not visible | Not generated | Startup failure |

### 13.1 Completed with blocked formal decision

A handled coverage/risk block is a successful **run** with a formal `blocked_for_review` decision, not a system failure. The terminal manifest can be `completed` with `formal_decision.status=blocked_for_review`, `final_rating=REVIEW`, and a passed/blocked gate result, provided all artifacts and security checks pass. A gate **exception** is different: it is a failed run (`run_status=failed`, `error.stage=gate`) and produces no tradeable output. This distinction prevents a business block from being mislabeled as a crash and prevents a crash from being published as a completed block.

### 13.2 Scenario verification plan

| Scenario | Expected unique behavior | Planned verification |
|---|---|---|
| Normal pass | Complete coverage, stock Buy/Overweight risk passes; formal rating unchanged; publication commits once; history visible after post-commit validation | `T-SCEN-01`: end-to-end fixture with fixed replay, query counters, risk boundary pass, manifest/INV-01, permanent files, recovery envelope, memory idempotency, read-back |
| Business block | Critical gap or risk limit/invalid input; formal `REVIEW`; no tradeable output; run `completed` with blocked formal decision; risk result recorded even when coverage blocks | `T-SCEN-02`: gate matrix for critical gap, risk input invalid, risk limit, model REVIEW, combined coverage+ordinary risk; assert primary/review class and absence of tradeable output |
| System exception | Evaluator or gate raises; gate `error`, run `failed`, primary system reason, `review_class=gate_system_error`, no commit | `T-SCEN-03`: fault injection at evaluator/gate; assert failed manifest, no committed publication, no tradeable output |
| Pre-commit interruption | No terminal completed manifest; valid recovery envelope can complete later; permanent snapshot not authoritative without commit | `T-SCEN-04`: crash after recovery envelope/memory/permanent files but before terminal commit; recover model-free; assert one commit and no duplicate memory |
| Post-commit corruption | Committed terminal manifest is preserved; record rejected as success; independent corruption diagnostic; history returns `CORRUPT_RECORD`; no compensating `failed` manifest | `T-SCEN-05`: tamper one bound artifact after commit; assert immutable manifest bytes, diagnostic record, history rejection, no second publication; export portion deferred |
| Duplicate recovery | One single-process startup guard per `run_id`; duplicate startup is rejected or waits; at most one commit; no duplicate memory | `T-SCEN-06`: repeated startup; assert one winner, no duplicate publication/memory, bounded retry, unsupported concurrency rejection |
| Concurrent publication (deferred) | Multi-worker publication/recovery, lease/fencing/takeover: not current | `T-SCEN-07`: deferred; a new ADR/amendment is required |
| Context overflow | No oversized model request; mandatory brief content preserved; safe compression/reference/rejection; all fallbacks obey hard cap | `T-SCEN-08`: over-budget context and brief cases; assert `ContextBudgetError`/`BRIEF_REJECTED`, protected blocks intact, no full+brief duplication |
| History edge cases (export deferred) | Pending/failed/quarantined/corrupt excluded; section isolation; post-commit corruption never success | `T-SCEN-09`: mixed statuses and tampered sections; assert typed results; export closure/conflict is deferred |
| Cleanup after successful commit | Temporary recovery material removed; history read and memory binding verification still succeed from the permanent snapshot | `T-SCEN-10`: commit, validate, cleanup, then `get_run` and memory binding check; assert no recovery-file dependency; export is deferred |
| Brief disabled / full-report fallback / final rejection | Disabled uses normal full reports; allowed full-report fallback preserves mandatory content and hard cap; final rejection is terminal and cannot re-enter normal input/compression | `T-SCEN-11`: three fixtures and a post-rejection bypass attempt; assert statuses, hard-cap behavior, no bypass |
| Concurrent same decision with uncommitted entry | A active -> B bounded wait/retryable; A invalid with envelope -> recovery under A identity; no envelope -> unavailable; binding conflict -> conflict | `T-SCEN-12`: active, duplicate startup, missing-envelope, and mismatch cases; assert no ownership transfer, no duplicate entry, no lock held while waiting |
| Old process paused / recovery takeover (deferred) | Lease/fencing/takeover: not current | `T-SCEN-13`: deferred; a new ADR/amendment is required |
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
- Retries already performed inside a vendor adapter are reported to and counted by the unified retry/fallback budget; they do not stack as hidden extra retries.
- Cancellation/timeout releases the single-flight slot and records a terminal/retryable outcome; the slot is not leaked.

### 14.2 Different runs

- Each run has its own `RunContext`, evidence store, and run cache.
- Existing vendor caches may be shared and are recorded as `vendor_cache_hits`.
- Memory writes are serialized by the existing memory lock and idempotency key.
- Manifest and publication writes use per-run paths and atomic replace.
- The publication snapshot is per `run_id`; no shared mutable publication index is authoritative.

### 14.3 Single-process publication/recovery guard (current)

Current `FR-06` is single-process sequential recovery. Normal publication and recovery share one simple exclusive startup guard. There is no current lease, fencing token, takeover, or multi-worker claim.

**Protocol**

- **Guard**: `StartupRecoveryGuard.acquire(run_id, wait_budget)` is the only startup/commit exclusion boundary. If held, a second startup is rejected or waits with a bounded retry; it does not delete the lock or take over.
- **Protected boundary**: the guard is held only for the check-and-write/commit boundary, never across model/analyst work, rendering, hashing, or waiting for another run's memory.
- **Unsupported concurrency**: multiple processes/workers/hosts performing recovery for the same or different runs are explicitly rejected (`RecoveryUnsupported`) unless a future multi-worker design is approved.
- **Lock order**: when a memory write is needed, the guard is acquired before the memory lock; never acquire the guard while holding the memory lock. Memory-only operations may hold the memory lock alone.
- **Duplicate normal publisher**: one writer wins; identical content is a no-op; different content is `RUN_ID_CONFLICT`; the loser does not write.
- **Duplicate recovery worker**: one startup/guard is active; duplicate startup is rejected or waits with bounded retry; no duplicate publication or memory.
- **Waiting on another run's pending memory**: B holds neither the startup guard nor the memory lock; it uses a bounded wait/retry and never blocks A's publication.
- **Interruption/retry**: process exit releases the OS guard if the OS does so. Retry reacquires the guard, re-reads the terminal identity/reservation, and either reuses the original reservation or completes the same entry idempotently.
- **Cleanup**: cleanup requires the guard, releases only its own material, and never removes another writer's permanent records. Cleanup failure is a warning after a successful commit.
- **Scope**: single-user local filesystem, single process. No distributed consensus, second commit marker, lease, fencing, or takeover.

**Deferred extension (not current)**

- `RunOwnershipLock`, `lease.json`, `owner_id`, `fencing_token`, takeover, stale-lease reclaim, and multi-worker claims are deferred. If reactivated, a new ADR/amendment must define the OS file lock vs logical lease distinction, bounded wait/`LOCK_BUSY`, takeover, lost-owner rejection, and release rules.

### 14.4 Concurrent publication and recovery

- Same-second ticker/date paths do not collide because the path is keyed by `run_id`.
- Current recovery is single-process. A second process/worker is rejected or waits with bounded retry; it does not claim, fence, or take over.
- Two distinct `run_id`s publish sequentially under the startup guard; history lists both without mixing sections.
- Cleanup of one pending envelope cannot remove another run's permanent records.
- Multi-worker publication/recovery is a deferred extension, not current acceptance.

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
| Allowed before/after finalization | Before a `FinalizedRunRecord` exists | After a valid `RecoveryEnvelope` exists |
| Model/data calls | May resume graph execution | Forbidden |
| Identity | New `run_id` | Preserves original `run_id` |
| Evidence | May inherit journal evidence with separate inherited counters | Uses saved records only |
| Commit | Normal publication after graph completion | Same terminal manifest plus read-time `INV-01` |
| Snapshot order | Not applicable | Memory plan/reservation -> recovery envelope -> idempotent memory -> permanent snapshot -> terminal candidate -> commit |
| Lock/ownership | New run; no publication ownership until finalization | Shares the same single-process startup guard as normal publication; lease/fencing is deferred |
| Post-commit corruption | Not applicable | Keep committed terminal manifest immutable; independent diagnostic; reject as `CORRUPT_RECORD` |
| Disabled behavior | `ResumeRejected(unsupported_phase)`; start a new run | No recovery; publication still possible; unsupported concurrent recovery is rejected; no recovery guarantee |
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
- History is read-only over committed publication records. Export is deferred; if reactivated, it must be read-only over committed records and write only to an empty target.
- Coding agents are default-deny; this ADD-R round may write only `architecture-blueprint.md` and `docs/architecture/**`.
- The full boundary list and per-role whitelists are in `docs/architecture/permission-model.md`.
- Redaction uses known-value plus versioned-pattern checks, per-write and final run scans, fail-closed behavior, over-redaction controls, and path confinement. A clean scan proves only the defined scope/rules/fixtures, not universal secret absence.
- Audit endpoints are scheme/host/path only; preference restore endpoints may keep non-sensitive query parameters and `secret_ref` names, never inline sensitive values.

---

## 18. Round-based implementation plan (R0–R8)

The former phase-only plan is replaced by rounds with explicit entry/exit evidence. A round's feature-off state means that round is not implemented/enabled; it is not evidence that a requirement is satisfied. No round may claim a later round's completion.

| Round | Goal | Primary requirements | Main exit condition |
|---|---|---|---|
| R0 | Contracts, trace, evaluation preparation, GR-01 Stage A | all (contracts), GR-01 Stage A | Contracts/envelopes/digests/trace/round map reviewed; Stage A reference freeze ready |
| R1 | RunContext, fixed clock, canonicalization, security/path/counter foundations | FR-02 foundation, FR-03 foundation, INV-01 foundation, SR-01, SR-02 | Pure foundation tests pass; no formal decision yet |
| R2 | Unified data, query reuse, preflight, availability view/snapshot | FR-01, FR-03, QR-01 data path | Query/concurrency/cancel/coverage tests pass; entry integration closed at R4 |
| R3 | PM proposal, pure risk, unified SafetyGate | FR-04, INV-02, SB-01 | Gate/risk/PM-source matrices pass; no publication yet |
| R4 | Manifest, publisher, permanent/recovery envelopes, minimum memory, legacy entry convergence, PR-01 start | FR-01/FR-02 entry integration, FR-06 snapshot primitives, INV-01 binding, PR-01 start | One publish/commit/read-back path; writer bypass closed; PR-01 samples collected |
| R5 | Financial facts/metrics, direct metrics only, GR-01 Stage B | FR-07, GR-01 Stage B | Fact/period/graph placement/bundle tests pass; TTM/FCF YoY absent |
| R6 | History, single-process startup recovery, memory lifecycle and uncommitted conflict | FR-05, FR-06, INV-01 lifecycle close, SR-02 history/recovery integration | History/recovery/memory lifecycle tests pass; concurrent recovery rejected |
| R7 | Brief, token budget, local cost measurement, all SR-01 boundaries | FR-08, CR-01, SR-01 close | Brief functional tests pass; FR-08 acceptance independent of CR-01; all boundaries scanned |
| R8 | QR-01, CR-01 acceptance, PR-01 final review, full regression | QR-01, CR-01, PR-01, all | Full regression + evaluation evidence; unresolved thresholds still block their own acceptance |

### R0 — Contracts, trace, evaluation preparation, GR-01 Stage A

- **Goal**: freeze the reviewable contracts before implementation starts.
- **Components**: `PolicyCatalog`, `Canonicalizer`, envelope schemas (§9.6.8), digest definitions (§9.6.9), trace/round map, evaluation harness skeleton.
- **Entry points**: none executable; documentation and schema review only.
- **Prerequisites**: D1 v1.25.0 approved registry, `req-schema.json`, `run-manifest-schema.json`, current evaluation contracts.
- **Inputs**: requirements, baseline evidence, ADR 001–003, open decisions.
- **Entry criteria**: architecture review accepts the Round 3 contracts as proposed.
- **Exit evidence**: component/interface/round trace; envelope/digest review notes; GR-01 Stage A freeze readiness record.
- **Positive tests**: schema/envelope fixtures parse; digest projections have no cycles; every requirement/AC has a round owner.
- **Negative tests**: missing envelope field, ambiguous digest projection, missing AC round, mutating a sealed envelope.
- **Regression**: none yet; the requirements validator `--check` remains unchanged and read-only.
- **Failure behavior**: contract gaps block dependent rounds; no implementation starts on an unresolved contract.
- **Not implemented**: all runtime behavior; no code, no measurement.
- **Blockers**: OQ-09 risk input source, OQ-14 GR-01 reference manifest, ARCH-OD-03 policy locator for later rounds; contract review itself is not approval.

### R1 — Foundations

- **Goal**: one identity/clock/path/version foundation and one security/path/counter base.
- **Components**: `RunContext`, `RunCoordinator` skeleton, `PolicyCatalog`, `Canonicalizer`, `SecretRedactor`, `StartupRecoveryGuard`, `RunEvidenceStore`, `CheckpointCoordinator`.
- **Entry points**: internal only; no formal output.
- **Prerequisites**: R0 contracts.
- **Inputs**: config, entrypoint request, policy files, path roots.
- **Entry criteria**: R0 exit accepted; no unresolved foundation schema.
- **Exit evidence**: unit tests for clock, future-date rejection, canonicalization, redaction, path read/write confinement, counter primitives, guard acquire/release.
- **Positive tests**: fixed clock; deterministic canonical bytes; in-root path accepted; guard acquired once.
- **Negative tests**: future date; path traversal/symlink escape; secret/pattern hit; duplicate guard; scanner failure.
- **Regression**: existing CLI/config/date tests remain unchanged.
- **Failure behavior**: fail closed; no formal decision; unsafe path/secret blocks the run.
- **Not implemented**: data access, coverage, gate, publisher, history, recovery, brief.
- **Blockers**: none beyond R0; ARCH-OD-02 CI dependency declaration remains evidence work.

### R2 — Unified data, preflight, availability

- **Goal**: one data entry, one coverage view/snapshot, no duplicate query execution.
- **Components**: `DataAccessService`, `PreflightCoordinator`, `AvailabilityIndex`, `RunEvidenceStore`, adapters for tools/prefetch/SEC statements.
- **Entry points**: registered tools, sentiment prefetch, preflight.
- **Prerequisites**: R1 foundations; query-key and coverage policy proposals.
- **Inputs**: critical profile, vendor config, as-of date, requested windows.
- **Entry criteria**: R1 exit accepted; query key/coverage contracts reviewed.
- **Exit evidence**: sequential/concurrent single-flight, cancel/timeout release, terminal-outcome reuse, adapter retry accounting, run/vendor cache separation, HTTP boundary counts, preflight independence from analyst selection, sealed snapshot tests.
- **Positive tests**: one execution per logical key; concurrent join; cancellation releases slot; cached terminal outcome reused; stock statements preflight with no fundamentals analyst.
- **Negative tests**: duplicate execution; hidden adapter retry; cross-run cache reuse; late result mutating sealed snapshot; missing/contradictory coverage record.
- **Regression**: existing router/tool/sentiment tests; no data behavior change for successful calls.
- **Failure behavior**: record evidence/gap; terminate on counter inconsistency; gate later blocks.
- **Not implemented**: gate, publisher, history, recovery, metrics, brief.
- **Blockers**: OQ-04 vendor-cache TTL is non-blocking; OQ-08 concurrency policy is non-blocking for single-process.

### R3 — Proposal, pure risk, unified gate

- **Goal**: one unapproved proposal source and one formal decision authority.
- **Components**: `PortfolioManagerAdapter`, `SafetyGate`, `RiskInputValidator`, `RiskPolicyResolver`, `PortfolioRiskEvaluator`, `RiskEvidenceStore`, `FinalizedRunRecord`.
- **Entry points**: internal after graph execution; no publication yet.
- **Prerequisites**: R2 coverage snapshot; caller risk envelope; policy snapshot.
- **Inputs**: full reports/plans/risk debate/past memory; raw risk envelope (optional); sealed coverage.
- **Entry criteria**: R2 exit accepted; OQ-09 input source decided or an explicit provisional integration path approved.
- **Exit evidence**: gate matrix, invalid-rating-first, risk pass/block/error, applicable risk recorded under coverage block, provisional/approved policy distinction, single-caller audit, PM source audit.
- **Positive tests**: stock Buy pass; add-long pass; crypto not-applicable; complete coverage pass; formal REVIEW on block.
- **Negative tests**: missing/invalid/unsupported/stale/inconsistent/cash/currency input; over-limit; evaluator exception; forged snapshot; Trader/risk-debater promotion; gate bypass.
- **Regression**: existing graph/agent/rating tests.
- **Failure behavior**: block -> formal REVIEW; evaluator/gate exception -> failed run; no tradeable output.
- **Not implemented**: publication, history, recovery, metrics, brief.
- **Blockers**: OQ-09 (implementation), OQ-10 (approved-policy claims only), ARCH-OD-03 policy locator, ARCH-OD-21 PM adapter; OQ-12 for behavioral acceptance.

### R4 — Manifest, publisher, envelopes, minimum memory, entry convergence

- **Goal**: one publish/commit/read path and one legacy entry adapter.
- **Components**: `ArtifactPublisher`, `PublicationSnapshotStore`, `RecoverySnapshotStore`, `MemoryService` minimum identity/idempotency, `MemoryReservationStore`, `ReportSectionManifestBuilder`, `PublicationStatusReader`, `LegacyWriterAdapter`.
- **Entry points**: CLI, `propagate`, `stream_run` intermediate, `save_reports`, backtest.
- **Prerequisites**: R3 final record; envelope/digest contracts; snapshot layout.
- **Inputs**: finalized record, evidence, render inputs, memory plan.
- **Entry criteria**: R3 exit accepted; ARCH-OD-15/23/24 layout/digest proposals reviewed.
- **Exit evidence**: running manifest before model calls; normalize/redact; memory reserve; recovery envelope; idempotent memory; permanent files; scan/cross-artifact; terminal atomic replace; read-back; cleanup; writer-bypass audit; PR-01 starting samples.
- **Positive tests**: one commit; same run_id no-op; history not yet visible before R6; propagate tuple preserved; stream marked intermediate; cleanup warning.
- **Negative tests**: terminal write failure; different content `RUN_ID_CONFLICT`; post-commit tamper; direct old-writer call; raw rating display; unsafe scan; hash DAG cycle.
- **Regression**: CLI smoke, propagate, save_reports, backtest, report rendering.
- **Failure behavior**: pre-commit failure keeps running/failed state; unsafe terminal write keeps last valid running record and reports failure; post-commit failure keeps manifest + diagnostic.
- **Not implemented**: history read UI, startup recovery scan, advanced memory lifecycle, metrics, brief.
- **Blockers**: ARCH-OD-15/20/23/24 implementation decisions; OQ-02 retention non-blocking.

### R5 — Financial facts and metrics, GR-01 Stage B

- **Goal**: deterministic direct metrics from structured facts, before research debate.
- **Components**: `SecEdgarAdapter` wrapper, `FinancialFactService`, `FinancialMetricService`, `MetricEvidenceBundleBuilder`, `MetricConflictDetector`, `FundamentalsAdapter`.
- **Entry points**: fundamentals stage and optional metrics tool; program append regardless of tool use.
- **Prerequisites**: R2 data path; R4 envelopes; GR-01 Stage A complete.
- **Inputs**: ticker, as-of, structured facts, price, normalization rules.
- **Entry criteria**: Stage A frozen; R4 exit accepted.
- **Exit evidence**: disclosure/canonical separation, per-fact period identity, as-of/restatement/ambiguity, direct metric formulas, n/a reasons, block-before-Bull/Bear, bundle persistence, no refetch on recovery, Stage B timing/version record.
- **Positive tests**: NVDA fixture arithmetic; valid same-span YoY/QoQ; margins; fiscal-year P/E; current ratio; liabilities/assets; current-span FCF; conflict disclosure.
- **Negative tests**: near-date/equal-value guessed link; look-ahead; ambiguous filing; TTM/FCF YoY request; quarter subtraction; direct vendor call; block after debate; missing/corrupt bundle recovery.
- **Regression**: existing SEC/fundamentals/report tests.
- **Failure behavior**: typed n/a; conflict disclosed; missing/corrupt bundle blocks metric-dependent publication; no live refetch.
- **Not implemented**: TTM/FCF YoY (deferred); history/recovery; brief.
- **Blockers**: OQ-14 (reference manifest), ARCH-OD-19 (graph/query placement), OQ-15 deferred.

### R6 — History, single-process recovery, memory lifecycle

- **Goal**: committed-only history, model-free single-process recovery, full memory lifecycle.
- **Components**: `HistoryService`, `PublicationStatusReader`, `RecoveryService`, `StartupRecoveryGuard`, `RecoverySnapshotStore`, `MemoryService`, `MemoryReservationStore`, `MemoryRecoveryCoordinator`.
- **Entry points**: startup recovery; history CLI/API adapters; memory step/settlement substrate.
- **Prerequisites**: R4 publication; R5 metric bundle when enabled.
- **Inputs**: committed publications, pending recovery envelopes, reservations, terminal manifests.
- **Entry criteria**: R4/R5 exit accepted; ARCH-OD-06 current-scope decision recorded (single-process only).
- **Exit evidence**: terminal-first idempotency; conflict/corrupt typing; model-free sentinels; duplicate startup bounded; unsupported concurrency rejected; history filters/order/pagination/revalidation; memory reuse/version/supersedes/rotation/memory-disabled; uncommitted conflict statuses; cleanup-vs-permanent reads; INV-01 lifecycle close; SR-02 read/write integration close.
- **Positive tests**: committed history; recovery after cleanup; one original memory entry; same-content reuse; changed-content version; failed-version gap; B waits without locks.
- **Negative tests**: pending/failed/quarantined in history; corrupt record; duplicate startup; concurrent recovery; missing envelope; ownership transfer attempt; duplicate/conflicting entry; recovery model call sentinel.
- **Regression**: memory/settlement/checkpoint/CLI/backtest.
- **Failure behavior**: quarantine; typed busy/conflict/corrupt; no overwrite; no duplicate publication.
- **Not implemented**: multi-worker lease/fencing/takeover (deferred), export (deferred), QR-02 (deferred), brief.
- **Blockers**: ARCH-OD-20/22 implementation decisions; ARCH-OD-06/16 remain deferred; OQ-02 retention non-blocking.

### R7 — Brief, token budget, local cost, all security boundaries

- **Goal**: deterministic five-role brief with protected mandatory content; FR-08 functional acceptance independent of CR-01.
- **Components**: `DownstreamBriefBuilder`, `ContextAssembler`, `TokenCounter`, `BriefAuditStore`, `PolicyCatalog`; `SecretRedactor` across preferences/logs/errors/API/stream.
- **Entry points**: five debate roles only; context assembly; stream/debug scan.
- **Prerequisites**: R2 coverage view; R5 metric block; R6 history/formal paths stable.
- **Inputs**: reports, coverage view/version, metric block, safety constraints, brief policy, tokenizer.
- **Entry criteria**: R6 exit accepted; ARCH-OD-04 tokenizer and ARCH-OD-17/18 brief mapping/timing proposals reviewed.
- **Exit evidence**: deterministic extraction; five-role replacement; no full+brief duplication; mandatory preservation; view-version recording/reassembly; ordered expansion/reference/full-report/rejection; tokenizer measurement; `BRIEF_REJECTED` terminal; audit metadata; FR-08 functional acceptance separate from CR-01; SR-01 all-boundary scans.
- **Positive tests**: brief fits; full-report fallback allowed; disabled path; view changes -> reassembly; protected blocks intact; other roles full inputs.
- **Negative tests**: mandatory over hard cap; unresolvable reference; tokenizer missing; forged/duplicate marker; full+brief duplication; post-rejection bypass; secret in stream/log/error; over-redaction.
- **Regression**: report/context/CLI/settlement.
- **Failure behavior**: `BRIEF_REJECTED` fails closed at context stage; no formal tradeable output; full artifacts may remain evidence.
- **Not implemented**: savings claims; CR-01 acceptance while thresholds/prices missing; export; TTM/FCF YoY.
- **Blockers**: OQ-16 (FR-08/CR-01 thresholds), ARCH-OD-04 tokenizer, ARCH-OD-17/18; FR-08 functional tests may run with provisional policy but acceptance cannot claim approved thresholds.

### R8 — Evaluation, optimization acceptance, final review

- **Goal**: evaluate only what is ready; close PR-01 final review; full regression.
- **Components**: evaluation harness, `DataAccessService`, `SafetyGate`, risk/brief services, `ArtifactPublisher`.
- **Entry points**: offline/fixed replay, then live sampling; benchmark harness.
- **Prerequisites**: R0–R7 implemented and testable; frozen snapshots/approvals where required.
- **Inputs**: fixed replay data, eval set/rubric/contracts, paired PR-01 runs, prices/thresholds if available.
- **Entry criteria**: R7 exit accepted; no unresolved implementation blocker for the measured path.
- **Exit evidence**: QR-01 replay then live; cache A/B with fixed risk policy/input; risk-policy A/B separate; CR-01 contract v4 local cost with usage/attempt rules; PR-01 20 pairs percent/absolute p95; full regression; claim ledger separating cost/token/quality/safety/savings.
- **Positive tests**: fixed replay zero regression; live thresholds when approved; PR-01 paired samples; CR-01 null prices -> blocked; claim boundaries respected.
- **Negative tests**: live sampling before replay; risk policy varied inside cache A/B; missing prices treated as zero; negative PR-01 samples dropped; safety escape; quality drop beyond approved threshold.
- **Regression**: entire existing suite plus new suites.
- **Failure behavior**: no behavioral acceptance without snapshots/approval; no cost/token/saving claim without accepted contract; provisional thresholds do not block FR-08 functional acceptance.
- **Not implemented**: QR-02, export, multi-worker recovery, TTM/FCF YoY (deferred).
- **Blockers**: OQ-10 approved thresholds, OQ-12 risk-policy eval, OQ-16 brief/cost thresholds, OQ-05 PR-01 thresholds (acceptance only), D2-OD-09 snapshots.

**Cross-round rules**

- A requirement is **partial/not implemented** until its final acceptance round and full integration pass.
- FR-01/FR-03 close entry integration at R4; INV-01 closes lifecycle at R6; SR-01 closes all new boundaries at R7; SR-02 closes history/recovery read/write integration at R6. Later changes still require regression.
- Safety closure must be complete before any new formal output is exposed; before that, only internal/offline verification is allowed.
- Deferred scope is never used as evidence that a current requirement is satisfied.

---

## 19. Requirement coverage and planned verification

| Requirement | Primary components | Planned verification focus | Rounds (build / owner / accept) | Evidence status |
|---|---|---|---|---|
| `FR-01` | `DataAccessService`, `RunEvidenceStore`, `Canonicalizer` | Sequential/concurrent single-flight; cancellation/timeout release; terminal failure cache; run isolation; adapter retry accounting; retry/fallback budgets; fixed-replay business equivalence; live quality is QR-01 | R2 / R4 / R8 | Design only |
| `FR-02` | `RunContext`, `RunCoordinator`, `ArtifactPublisher`, `RunEvidenceStore` | Manifest lifecycle, identity, counters, tokens, failure injection, completed negatives, no-overwrite; publication/recovery/section details are INV-01/FR-05/FR-06 | R1/R4 / R4 / R8 | Design only |
| `FR-03` | `AvailabilityIndex`, `DataAccessService`, `RunEvidenceStore` | Closed status table, executed/missing records, profile defaults, preflight independence, fallback contract, aggregation, sealed snapshot, determinism, consumer consistency | R2 / R4 / R8 | Design only |
| `FR-04` | `SafetyGate`, `RiskInputValidator`, `RiskPolicyResolver`, `PortfolioRiskEvaluator`, `RiskEvidenceStore` | Invalid rating first, single caller, applicability once, exact boundaries, invalid input, provisional policy distinction, applicable risk under coverage block, evaluator error; cache/risk separation is QR-01 | R3 / R3 / R8 | Design only; thresholds provisional |
| `FR-05` | `PublicationSnapshotStore`, `ReportSectionManifestBuilder`, `HistoryService`, `SecretRedactor` | Filters/order/pagination, on-demand scan, optional non-authoritative index, revalidation, section isolation, post-commit corrupt rejection; export deferred | R6 / R6 / R8 | Design only |
| `FR-06` | `RecoveryService`, `StartupRecoveryGuard`, `RecoverySnapshotStore`, `ArtifactPublisher`, `MemoryService` | Model-free single-process recovery, exclusive startup guard, duplicate-start bounded retry, unsupported concurrency rejection, envelope validity before `snapshot_ready`, memory idempotency, commit identity, post-commit corruption; lease/fencing deferred | R4/R6 / R6 / R8 | Design only |
| `FR-07` | `FinancialFactService`, `FinancialMetricService`, `MetricEvidenceBundleBuilder`, `MetricConflictDetector`, `SecEdgarAdapter` | Fact identity, as-of, restatement, ambiguity, direct metrics, fiscal-year P/E, current-span FCF, n/a reasons, block before research debate, conflict scope, bundle recovery; TTM/FCF YoY deferred | R5 / R5 / R8 | Design only; reference manifest pending (GR-01) |
| `FR-08` | `ContextAssembler`, `DownstreamBriefBuilder`, `TokenCounter`, `PolicyCatalog`, `BriefAuditStore` | Deterministic extraction, marker handling, mandatory preservation, protected blocks, ordered budget, reference resolution, five-role replacement, view version/reassembly, non-mutation; functional acceptance independent of CR-01 | R7 / R7 / R8 | Design only; budgets pending |
| `PR-01` | `ArtifactPublisher`, benchmark harness | Separate startup/terminal pre-replace samples; 20 paired enabled/disabled runs retaining negative differences; percent and absolute p95; provisional thresholds do not block functional acceptance | R4 / R8 / R8 | Design only; no benchmark |
| `CR-01` | `TokenCounter`, `DownstreamBriefBuilder`, evaluation harness | Contract v4 local cost, two-field execution/acceptance state table, usage/attempt rules, approved target, separate cost/token/quality/safety/saving claims; blocked until prices/thresholds/human approval | R7 / R7 / R8 | Design only; contract blocked |
| `GR-01` | `FinancialFactService`, reference harness | Stage A freeze readiness before first FR-07 implementation; Stage B post-implementation timing/version; no code-generated expected values | R0 (A) / R5 (B) / R8 | Design only; reference pending |
| `QR-01` | `DataAccessService`, `SafetyGate`, risk services, evaluation harness | Fixed replay first, then live; cache A/B keeps risk policy/input fixed; risk-policy A/B separate; live rubric/REVIEW thresholds | R2 / R8 / R8 | Design only; contract blocked |
| `QR-02` | `RecoveryService`, benchmark harness | Fixed workload, 30 trials, nearest-rank p95, retained failures; deferred | Deferred | Deferred; target provisional |
| `SB-01` | `SafetyGate`, `FinalizedRunRecord`, `ArtifactPublisher`, `PortfolioManagerAdapter` | Five-rating matrices, invalid-rating-first, malformed input, forged snapshot, entry-point/stream bypass, gate error, sole risk caller, PM proposal source, combined coverage+error; gate before terminal manifest | R3 / R3 / R8 | Design only |
| `INV-01` | `FinalizedRunRecord`, `ArtifactPublisher`, `MemoryService`, `PublicationSnapshotStore` | Envelope/digest binding, full vs summary records, fallback disclosure, missing artifacts, retry, memory lifecycle, truthful completion; lifecycle closes at R6; section binding via FR-05 | R1/R4 / R6 / R8 | Design only |
| `INV-02` | `SafetyGate`, `PortfolioRiskEvaluator`, `MemoryService`, `ArtifactPublisher` | Generated violation corpus, determinism, injection, cross-artifact risk evidence, single-caller applicability, memory reuse/version; invalid rating not not_applicable | R3 / R3 / R8 | Design only |
| `SR-01` | `SecretRedactor`, all writers | Known-value/pattern scans across formal files, preferences, logs, errors, API returns, stream/debug; endpoint split, fail-closed, over-redaction, scope; all new boundaries close at R7 | R1 / R7 / R8 | Design only |
| `SR-02` | `PathGuard`, `HistoryService`, `RecoveryService` | Read/write confinement, traversal/absolute-path rejection, symlink/junction escape, operation-time path change, out-of-root writes; platform coverage recorded; history/recovery integration closes at R6; export conflict deferred | R1 / R6 / R8 | Design only |

The end-to-end scenario tests `T-SCEN-01`..`T-SCEN-18` in §13.2 cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, single-process duplicate recovery, context overflow, history edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, Portfolio Manager proposal sourcing, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, and committed-publication corruption. `T-SCEN-07` and `T-SCEN-13` are deferred with multi-worker lease/fencing/takeover. Export and QR-02 benchmark scenarios are also deferred.

Every fit criterion and its planned test/monitor is listed in `docs/architecture/trace-matrix.md`. That file is the authoritative requirement-to-component-to-test mapping for this round; its §3.19 assigns first-build, main-owner, and final-acceptance rounds to every requirement and AC range.

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
| Single-process startup guard behavior | **D** — design only; no duplicate-start test run |
| Lease/fencing/takeover/multi-worker recovery | **Deferred** — not designed as current, not implemented, not claimed |
| TTM metrics, FCF YoY, export, QR-02 | **Deferred** — outside current acceptance |
| Any implementation, test, transcript, approval, or benefit | **Not claimed** |

---

## 21. Risks and true coding blockers

### 21.1 Architecture risks

| Risk | Impact | Mitigation |
|---|---|---|
| `RunContext` grows into a god object | Policy coupling and testability loss | Keep lifecycle/DI only; business rules in services; dependency rules in §9.5. |
| Old writers bypass the publisher | Formal decision leak | Writer audit; direct calls require a record; CLI/propagate/backtest/save_reports adapters. |
| Risk evaluator becomes a second authority | Conflicting final decisions | Pure result returned only to `SafetyGate`; no writer/persistence/memory path. |
| Recovery creates a second commit path | Duplicate/inconsistent publication | Same terminal-manifest commit and read-time `INV-01`; single-process exclusive startup guard + duplicate-start guard; unsupported concurrent recovery rejected; multi-worker lease/fencing deferred; no independent marker. |
| History scans arbitrary directories | Mixed/stale sections | Read only the permanent publication snapshot and section manifest; revalidate on read. |
| Metric formulas drift or use ambiguous periods | Wrong numeric authority | Structured fact/period identity, versioned formulas, typed n/a, frozen reference manifest. |
| Brief becomes a second context source | Inconsistent prompts and formal records | Brief is a view inside `ContextAssembler`; full/formal/history/recovery are byte-identical. |
| Brief and full reports are both injected | Duplicated context and budget overflow | For the five target roles, the brief replaces the four full analyst reports; other roles keep full inputs. |
| Brief or metrics are generated after consumers | Downstream sees missing/stale evidence | Fix the execution order: metrics before research debate; brief before five-role delivery; publication only persists existing results. |
| Post-commit corruption overwrites commit evidence | Lost audit trail and ambiguous authority | Keep the committed terminal manifest immutable; reject the record as success; write an independent corruption diagnostic; no compensating failed manifest. |
| Memory version collision | Two runs receive the same version, or a failed version is reissued | Persistent append-only allocation history with a high-water mark over all allocations including failed; retries/recovery reuse their own reservation. |
| Ownership checked before, not inside, the write | Duplicate writes | Single-process check-and-write boundary under the startup guard; lease/fencing/takeover is deferred and must not be claimed. |
| Logical components drift into duplicate owners | Two gates, publishers, or data paths | Component realization audit in §9.6.7; one owner per responsibility; module grouping allowed only with documented symbol mapping. |
| Deferred scope leaks into current acceptance | False completion claims | C-14 and §18 cross-round rules; TTM/FCF YoY/export/multi-worker/QR-02 labeled deferred in every affected document. |
| FR-08 is blocked by CR-01 cost thresholds | Functional brief cannot be accepted | D3-16/D3-18: FR-08 functional acceptance is independent of CR-01; OQ-16 blocks cost/saving claims and CR-01 acceptance, not the functional path. |
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
| OQ-14 | Frozen non-NVDA reference companies/periods/sources | `GR-01-FC01`–`FC06`, FR-07 Stage A implementation gate | Blocking; pending human decision |
| OQ-16 | Brief mandatory/compressible budgets, token/quality thresholds, evaluation contract version | `FR-08` acceptance | Blocking; pending human decision |
| ARCH-OD-01 | Unretained personal-proposal source; path no longer referenced | Provenance | Resolved for current registry |
| ARCH-OD-02 | `pyyaml`/`jsonschema` present locally but not declared | Validator reproducibility/CI | CI declaration pending |
| ARCH-OD-03 | Risk policy file location/locator and approval record | Risk policy loader | Blocking before risk implementation |
| ARCH-OD-04 | Selected model/tokenizer for brief and context budgets | `FR-08` and context budget | Blocking before brief implementation |
| ARCH-OD-06 | Recovery retry/quarantine layout | Current single-process recovery | Non-blocking for single-process start; lease/fencing/takeover deferred |
| ARCH-OD-08 | Risk input envelope shape for CLI/API | `FR-04` integration | Blocking before risk integration |
| ARCH-OD-13 | Former approval of `SB-01` risk branch no longer applies | Status resolved; 17 active requirements approved as requirement design | Review risk branch with the approved registry |
| ARCH-OD-14 | Former approval coupling of `FR-02`/`INV-01` no longer applies | Status resolved; review with draft registry | Review coupled obligations together |
| ARCH-OD-15 | Permanent-snapshot staging/promotion path and hashing before commit | Publication implementation | Blocking before publication implementation |
| ARCH-OD-16 | Shared run-lock/lease/fencing format | Deferred multi-worker extension | Not current; a new ADR/amendment is required |
| ARCH-OD-17 | Brief replacement mapping and protected-marker format | `FR-08` implementation | Blocking before brief implementation |
| ARCH-OD-18 | Brief timing versus final coverage snapshot interpretation | `FR-08` acceptance | Blocking before FR-08 acceptance |
| ARCH-OD-19 | Financial-fact placement in the graph and SEC adapter query shape | `FR-07` implementation | Blocking before FR-07 implementation |
| ARCH-OD-20 | Memory reservation storage/format and authority | Memory/recovery implementation | Blocking before memory/recovery implementation |
| ARCH-OD-21 | Portfolio Manager adapter/model-proposal source | Analysis-chain implementation | Blocking before analysis-chain implementation |
| ARCH-OD-22 | Uncommitted same-decision memory coordination | Memory coordination implementation | Blocking before memory coordination implementation |
| ARCH-OD-23 | Permanent/recovery layout and cleanup dependency | Publication implementation | Blocking before publication implementation |
| ARCH-OD-25 | Logical component/module realization and symbol mapping | Component audit | Blocking before implementation of grouped modules |
| ARCH-OD-26 | Envelope serialization/version/error contract review | All envelopes | Blocking before R4/R6/R7 implementation |
| ARCH-OD-27 | Digest projection review (`decision_digest`, `proposal_digest`, `input_digest`, `entry_digest`, `evidence_digest`, `record_hash`) | R4 publication | Blocking before publication implementation |
| ARCH-OD-28 | Single-process startup guard mechanism and bounded retry | R6 recovery | Blocking before recovery implementation |
| ARCH-OD-29 | R0–R8 round map and per-AC ownership review | Delivery planning | Non-blocking for design; blocking before implementation starts |

Non-blocking decisions: manifest retention, vendor-cache TTL, manifest overhead thresholds, preference/concurrency policy, checkpoint defaults, publication snapshot retention, history index strategy (read-only derived index is allowed but non-authoritative).

### 21.3 Implementation blockers versus acceptance-only

| Class | Items | Effect |
|---|---|---|
| Implementation-start | OQ-09 risk input source; ARCH-OD-03 risk policy locator; ARCH-OD-15/23 snapshot layout; ARCH-OD-24/27 digest projection; ARCH-OD-20 reservation format; ARCH-OD-19 SEC query contract; ARCH-OD-21 PM adapter; ARCH-OD-22 uncommitted-memory protocol; ARCH-OD-04 tokenizer/model; ARCH-OD-25 component mapping; ARCH-OD-26 envelope contract; ARCH-OD-28 startup guard | Decide before the affected module starts. Not an approval claim. |
| Acceptance-only | OQ-10 approved risk thresholds; OQ-13 deferred QR-02 target/platform; OQ-16 brief budgets/quality/cost; D2-OD-09 behavior snapshots; OQ-05 manifest overhead; OQ-12 risk-policy evaluation | Do not block starting implementation; block completion/acceptance claims. |
| Deferred scope | Multi-worker lease/fencing/takeover; export; TTM/FCF YoY; QR-02 | Not current acceptance; requires a new ADR/amendment to activate. |
| Evidence/CI | ARCH-OD-01 missing `yhx` evidence; ARCH-OD-02 validator dependencies | Block reproducible D1 validation/CI, not module design. |

---

## 22. Document index and status

- [ADR 001 — Run governance](docs/architecture/adr/001-run-governance.md) (amended by ADR 003)
- [ADR 002 — Full-scope ADD-R extension](docs/architecture/adr/002-full-scope-add-r.md) (amended by ADR 003)
- [ADR 003 — ADD-R round 3](docs/architecture/adr/003-add-r-round-3.md)
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

- D1: v1.25.0; 17 active requirements are approved as a requirement-design baseline and QR-02 is deferred; approval does not assert implementation or measured results.
- D2: v0.3 ADD-R round 3 draft; all architecture decisions proposed, not approved.
- Application implementation: **not started**.
- Tests: **not started**.
- Runtime monitoring: **not implemented**.
- Benefits: **not measured** except the baseline facts above.
- Current recovery scope: single-process sequential; lease/fencing/takeover/multi-worker is deferred.
- Deferred scope: export, TTM/FCF YoY, QR-02, multi-worker recovery.
- This round changed `architecture-blueprint.md`, `docs/architecture/**`, and added `docs/architecture/adr/003-add-r-round-3.md`; it did not modify requirements, application code, tests, baseline evidence, permissions, or secrets.
