# ADR 003 — ADD-R Round 3: In-Process Modular Architecture, Single-Process Recovery, and Round-Based Delivery

Status: **v0.3 — ADD-R round 3 draft / pending human review**
Date: 2026-11-15
D1 basis: `docs/req/requirements.yaml` v1.24.0 — 18 requirements, 122 fit criteria
Status basis: 17 active requirements are approved as a requirement-design baseline; `QR-02` is deferred and outside current acceptance; approval does not assert implementation or measured results
Decision status: **proposed**
Amends: ADR 001 (Lean A Extended) and ADR 002 (Full-Scope ADD-R Extension)  
Implementation status: **design only; no application code changed**

---

## 1. Context

ADR 001 and ADR 002 selected Lean A Extended and defined the bounded services for the full D1 v1.24.0 scope. Round 3 is an architecture-consolidation round, not a new implementation round. It resolves ambiguities that remained in the previous drafts:

1. The design described many components with one proposed file each, which could be misread as a mandatory file-per-name layout.
2. Lifecycle ownership and coordination were folded into `RunContext`, risking a god object.
3. The previous recovery design described lease, fencing, takeover, and multi-worker claims, while current `FR-06` requires only single-process sequential recovery. The stricter protocol was designed but not required, and some documents described it as current.
4. Envelope contracts, digest projections, and publication ordering were spread across sections; each required a single authoritative definition.
5. The implementation plan used phase numbers, while the course review expects explicit incremental rounds with entry/exit evidence and per-AC ownership.
6. Some documents still listed TTM metrics, FCF YoY, export, and multi-worker recovery as current obligations, although D1 defers them.

This ADR records the Round 3 decisions. It does not approve any requirement, threshold, test, measurement, or implementation. A design selection is not a requirement approval.

---

## 2. Decision

### D3-01 — In-process modular architecture; logical components

Retain one in-process Python application. Components are **logical responsibilities**, not necessarily one file per component. Existing graph, agents, vendor adapters, renderer, and memory substrate are retained. The proposed module paths in the blueprint are a reviewable mapping; several small components may share a module, and a component may be a class, a set of functions, or an adapter.

A component audit must still prove: one owner per responsibility, no duplicate final authority, no duplicate publication transaction, no duplicate context entry, and no unrecorded write path.

### D3-02 — RunCoordinator / RunContext split

- `RunCoordinator` coordinates the run: entry normalization, ordered stages, service invocation, failure handoff, and publication handoff. It contains no business policy, no gate logic, no risk/metric formula, and no direct vendor/formal write.
- `RunContext` owns run identity, fixed `run_clock`, versions, run-scoped paths, and run-scoped dependency references. It does not decide coverage, risk, metrics, context, or publication.
- `SafetyGate` remains the only formal decision authority.
- `ArtifactPublisher` remains the only publication-commit authority.
- `DataAccessService` remains the only external data entry for new governed paths.
- `ContextAssembler` remains the only context assembly entry.

### D3-03 — Unified entry adaptation

All of the following become adapters to the same coordinator/gate/publisher path:

| Existing surface | Real symbol | Round 3 treatment |
|---|---|---|
| CLI analysis | `cli/run.py:run_analysis` | Normalize selections, start a `RunContext`, invoke `RunCoordinator`, display the published result. |
| Programmatic graph | `graph/trading_graph.py:TradingAgentsGraph.propagate` | Compatibility adapter; returns `(final_state, signal)` after publication; `signal` comes from the formal decision, not `run_rating(final_state)` of a raw proposal. |
| Graph execution | `graph/trading_graph.py:_run_graph` | Internal execution stage; the terminal PM output is a `ModelProposal`; no direct formal write. |
| Decision writer | `graph/trading_graph.py:record_decision` | Records the proposal and state evidence only; it does not write the formal memory decision. |
| State writer | `graph/trading_graph.py:_log_state` | Internal evidence/render input; no direct formal visibility. |
| Report writer | `graph/trading_graph.py:save_reports` and `reporting.write_report_tree` | Adapter requiring a finalized/published record; renderer remains a primitive. |
| Stream/debug | `graph/trading_graph.py:stream_run` | **Intermediate-only** stream. Any rating/decision in it is marked `proposal_status=unapproved`, `visibility=intermediate`, and is safety-scrubbed. It must not be presented as the formal result. |
| Checkpoint lifecycle | `begin_checkpoint`, `checkpoint_input`, `end_checkpoint`, `clear_checkpoint_on_success` | Graph-resume support only; distinct from publication recovery. A resumed run gets a new `run_id`. |
| Memory step | `graph/trading_graph.py:_memory_step`, `settle_pending`, `settle_all_pending` | Memory substrate activity; formal decision memory is written only by `MemoryService` after gate/commit. |
| Backtest | `backtest.py:run_backtest` | Per-cell `RunContext` and the same gate/publisher; `REVIEW` excluded from scoring. |
| Prefetch | `agents/analysts/sentiment_analyst.py:sentiment_analyst_node` calling `get_news.func` | Routed through `DataAccessService` with the same query key, counters, and evidence as tool calls. |

No path may promote a raw model rating directly to formal output. `propagate` keeps its tuple shape, but the second element is derived from `FinalizedRunRecord.formal_decision`, not from an unfinalized state field.

### D3-04 — Unified data access and query semantics

`DataAccessService` covers registered tools, sentiment prefetch, mandatory preflight, structured SEC facts, and the existing statement queries (`get_income_statement`, `get_balance_sheet`, `get_cashflow`).

- A complete semantic query key covers method, asset type, normalized instrument/topic, analysis date, requested window/lookback, method-specific parameters, vendor selector digest, and cache-key version.
- Results are immutable; concurrent callers join one in-flight execution.
- Cancellation and timeout release the single-flight slot and record a terminal or retryable outcome; a released slot must not leave a permanent lock.
- Terminal outcomes are reusable within the run. Run cache and vendor cache are separate; vendor-cache hits are counted separately.
- Retry and fallback budgets are owned by `DataAccessService`. Retries already performed inside an existing vendor adapter must be reported to and counted by the unified budget; they must not stack as hidden extra retries.
- `http_request_count` is incremented at the actual outbound request boundary, including redirects and retries. Cache hits and local short-circuits are 0.

### D3-05 — Availability, preflight, and sealed coverage

- `AvailabilityIndex` owns `executed` and `component_missing` records, `supports` links, the closed status set, and deterministic aggregation.
- After the fixed critical profile exists, mandatory preflight runs. For stocks, financial statements are required regardless of analyst selection.
- `CoverageView` is the program-produced, versioned, model-immutable view used by the five-role brief. `CoverageSnapshot` is sealed before the gate and used by the gate.
- A late-arriving result must not mutate a snapshot already used by a consumer or the gate; it may only appear in a later run or a newly versioned view if policy permits.

### D3-06 — Proposal and gate semantics

- The original Portfolio Manager remains terminal and is wrapped by `PortfolioManagerAdapter`; it produces only `ModelProposal {rating, text, source=portfolio_manager, source_refs, model_provider/id, proposal_status=unapproved}`.
- An invalid model rating blocks first. It must not be converted to `not_applicable` risk merely to bypass the risk branch.
- For a valid stock Buy/Overweight, the gate records the applicable risk result even when coverage already blocks.
- The caller/application is the authoritative risk-input source. The pure risk services use `Decimal` only and have no model, network, vendor, persistence, or UI dependency.
- A valid `threshold_status=provisional` policy may be used and is labeled provisional; missing/invalid/incomplete policy blocks. "Not approved" is not "policy absent."
- An evaluator exception maps to gate `error`, failed run, formal `REVIEW`; all reason codes and the fixed primary reason are retained.
- The gate runs before the terminal manifest. A committed manifest is not a precondition for running the gate.

### D3-07 — Separate status domains

The design keeps distinct:

- run lifecycle status (`running`, `completed`, `failed`);
- gate status (`not_run`, `passed`, `blocked`, `error`);
- formal decision status (`approved`, `blocked_for_review`);
- publication visibility (not committed, committed+verified, corrupt, quarantined).

No document may collapse these into one enum or invent schema values. The public schema enums remain the D1 authority.

### D3-08 — Envelope contracts

The following immutable or versioned contracts are defined in blueprint §9.6.8: `PublicationEnvelope`, `RecoveryEnvelope`, `ModelProposal`, `CoverageView`, `CoverageSnapshot`, `RiskEvaluation`, `MetricEvidenceBundle`, and `ContextAuditMetadata`. Each has one owner, explicit version, mutability rule, error contract, and serialization boundary. A consumer must not read a mutable working object where the envelope is required.

### D3-09 — Publication order, atomicity, and failure

The fixed order is:

1. normalize and redact formal content;
2. determine memory reuse or reserve a version;
3. write and verify the self-contained recovery envelope;
4. perform the idempotent memory write;
5. write and verify permanent publication files;
6. run security scans and cross-artifact validation;
7. atomically replace the terminal manifest;
8. read back and validate;
9. clean temporary material.

The running manifest is written before model calls. If the terminal state cannot be written safely, the last valid running manifest is retained and the failure is reported; a completed manifest is never fabricated. Cleanup failure after a valid commit is a warning only.

### D3-10 — One commit condition and idempotency

The only commit condition is terminal `run_manifest.json` with `run_status=completed` plus successful read-time `INV-01`. Same `run_id` with the same immutable content is a no-op; different content is `RUN_ID_CONFLICT`. A post-commit read failure never overwrites the manifest and never auto-republishes; it is recorded in an independent diagnostic. All formal references resolve from permanent material after recovery cleanup.

### D3-11 — Digest projections

Content digests and file-byte hashes are separate. Blueprint §9.6.9 defines the projections and generation order for `decision_digest`, `record_hash`, `proposal_digest`, `input_digest`, `entry_digest`, and `evidence_digest`. Scanning/redaction happens before digest computation. A simple "drop all timestamps" rule is forbidden; filing, evidence, observation-window, and requirement-mandated risk timestamps are preserved. Terminal-manifest replace completion time and similar self-referential measurements live in external measurement evidence or an audit-only diagnostic, not inside the immutable record hash.

### D3-12 — Memory content/evidence separation

- `MemoryService` keeps stable decision content separate from current-run evidence.
- Identical stable content reuses a committed historical entry through `reused_decision_ref`; the current run's risk evidence is not written back into the historical entry.
- Changed content allocates a new version; a failed version is never reissued.
- `MemoryReservationStore` owns allocation and derived status only; it is not a second commit condition.
- Settlement/reflection, rotation, memory-disabled runs, same-day reruns, supersedes, and uncommitted-entry conflicts follow `INV-01`. Waiting never holds the memory or startup guard.

### D3-13 — Single-process sequential recovery

Current `FR-06` is single-process sequential recovery only.

- Use one simple exclusive startup guard and a duplicate-start guard with bounded retries.
- Reject unsupported concurrent recovery explicitly.
- Do not implement lease, fencing, takeover, or multi-worker claims in the current design. Those are a deferred extension in blueprint §12.6 and `open-decisions.md`.
- Normal publication and recovery share the same exclusive guard boundary so the same `run_id` is not written concurrently.
- Recovery checks the terminal manifest first. Committed+verified+identity match is idempotent success; conflict/corruption is typed failure. Only an uncommitted record uses the recovery envelope.
- Recovery preserves the original identity and version, calls no model, external data, graph, settlement, or reflection, isolates failures per task, and treats no pending task as normal startup.

### D3-14 — History authority

`HistoryService` treats the verified committed publication as the authority. Filters intersect, ordering is deterministic, pagination is bounded, unknown records return `NOT_FOUND`, and corrupt records return `CORRUPT_RECORD`. The current design prefers an on-demand scan of committed publication roots; a rebuildable derived index is an optional, non-authoritative optimization. The index never defines commitment and every read revalidates.

### D3-15 — GR-01 staging

GR-01 Stage A (reference freeze readiness) must complete before the first FR-07 application implementation. Stage B (post-implementation timing/version verification) occurs after implementation starts. This architecture round is not FR-07 implementation and does not create an independent reference or retroactive approval.

### D3-16 — FR-07 and FR-08 scope discipline

- FR-07 implements only the current direct metrics. TTM metrics, FCF YoY, and single-quarter derivation by subtraction are deferred.
- The metric block is appended by program after the fundamentals report and before Bull/Bear; it does not depend on a model tool call. Conflicts are limited to recognizable structured claims.
- FR-08 uses deterministic extraction/assembly by default. Only Bull, Bear, and the three risk debaters receive the brief replacing the four analyst reports; other roles keep full inputs. Mandatory content is program coverage gaps, the metric block, and safety constraints. The `coverage_view_version` is recorded; if it changes before a consumer, the brief is reassembled. Expansion, resolvable reference, full report, and rejection follow the contract order; the final request is measured by the selected tokenizer; `BRIEF_REJECTED` is terminal.
- FR-08 functional acceptance is independent of CR-01 optimization acceptance. A missing cost threshold blocks CR-01 claims, not FR-08 functional behavior.

### D3-17 — Security and path boundaries

- SR-01 applies to all actual boundaries, including preferences, logs, error/API returns, and streaming/debug output, not only persisted formal files.
- Short/empty secret rules, over-redaction controls, endpoint audit/restore rules, and scanner-failure behavior follow the current requirement.
- SR-02 protects both reads and writes, defines platform and symlink/junction behavior, and records the race risk of path changes during an operation. An untested platform is not marked as passing.
- A clean scan proves only the defined scope, rules, and fixtures; it does not prove universal absence of unknown secrets.

### D3-18 — PR-01, QR-01, CR-01 boundaries

- PR-01 uses a fixed offline workload, records startup and terminal pre-replace write samples separately, keeps 20 enabled/disabled paired external end-to-end measurements including negative differences, and reports percent and absolute p95 separately. Provisional thresholds do not block functional acceptance.
- QR-01 fixes deterministic replay first, then live sampling; cache A/B keeps risk policy and risk input fixed; risk-policy comparison is separate.
- CR-01 uses contract v2 local-cost formulas and usage/attempt rules. Missing prices or targets leave it blocked. Cost, token, quality, safety, and savings claims are recorded separately.
- QR-02, export, multi-worker recovery, and TTM/FCF YoY remain deferred only.

### D3-19 — Round-based implementation

Blueprint §18 replaces the former phase-only plan with R0–R8. Each round records goal, components, entry points, prerequisites, inputs, entry criteria, exit evidence, positive/negative tests, regression scope, failure behavior, not-implemented status, and blockers. A round's feature-off state is not evidence that a requirement is satisfied. Trace-matrix §3.19 assigns first-build, main-owner, and final-acceptance rounds to every requirement and AC range.

### D3-20 — Document consistency

All architecture documents must use the same envelope names, status domains, digest names, recovery model, round labels, and deferred scope. Historical decisions remain visible through explicit `amended`/`superseded` notes; they are not rewritten as if they had always been different.

---

## 3. Options considered

| Option | Description | Result |
|---|---|---|
| A — Lean A Extended, consolidated | In-process modular services; one gate, publisher, data path, context assembler, memory writer; single-process recovery now; lease/fencing deferred | **Selected for proposal** |
| B — Independent subsystems | Separate risk, archive, brief, and recovery subsystems | Rejected: creates second authorities/transactions/context entries |
| C — Event-sourced ledger | Every fact appended and reduced | Retained as re-decision option; higher schema/replay/compatibility cost |
| D — Decorator/contextvar | Wrappers around current writers/graph | Rejected as primary: bypass resistance and cross-entry coverage are weaker |

No numeric scores are assigned. No candidate has been implemented. The comparison is a design judgement under the same safety, binding, recovery, and redaction contract.

---

## 4. Consequences

### Positive

- One coordination owner (`RunCoordinator`) and one identity/dependency owner (`RunContext`) reduce god-object risk.
- Logical components avoid a premature file explosion while preserving responsibility audits.
- Single-process recovery matches the current requirement without pretending lease/fencing is implemented.
- Envelope and digest contracts remove cross-document ambiguity.
- R0–R8 gives each requirement and AC a build/owner/acceptance round.
- Deferred TTM/FCF YoY/export/multi-worker items no longer appear as current obligations.

### Negative

- More explicit contracts and round gates to maintain.
- A future multi-worker extension will require a new ADR or an amendment to this one; lease/fencing cannot be claimed now.
- Logical component mapping must be audited to prevent "one name, several conflicting implementations."
- Acceptance remains blocked by unresolved human decisions and unimplemented tests.

### Neutral

- The 17 active requirements are approved as a requirement-design baseline; QR-02 is deferred; thresholds remain provisional or pending as applicable.
- No application code, test, measurement, or approval is created by this ADR.
- Existing graph, agents, vendor adapters, renderer, and memory substrate are retained.

---

## 5. Re-decision conditions

Reopen this ADR if:

1. Logical components cannot be mapped to real symbols without duplicate authority.
2. `RunCoordinator`/`RunContext` cannot remain free of business policy.
3. Single-process recovery cannot meet `FR-06` correctness or bounded retry.
4. Envelope/digest contracts cannot be serialized without cycles or mutable aliasing.
5. A future requirement activates multi-worker recovery, export, TTM/FCF YoY, or QR-02.
6. FR-08 functional acceptance cannot be separated from CR-01 cost acceptance.
7. A D1 change alters gate, risk, history, recovery, memory, metric, or brief semantics.

---

## 6. Related documents

- `architecture-blueprint.md` §2, §8, §9.6, §10–§19, §21
- `docs/architecture/adr/001-run-governance.md` (amended)
- `docs/architecture/adr/002-full-scope-add-r.md` (amended)
- `docs/architecture/trace-matrix.md`
- `docs/architecture/evaluation-table.md`
- `docs/architecture/invariants.md`
- `docs/architecture/memory-design.md`
- `docs/architecture/permission-model.md`
- `docs/architecture/runtime-policy-catalog.md`
- `docs/architecture/open-decisions.md`

---

## 7. Status

- Decision status: **proposed, pending human review**.
- Application implementation: **not started**.
- Tests: **not started**.
- Monitoring: **not implemented**.
- Benefits: **not measured** except the baseline facts.
- D1: v1.24.0; 17 active requirements are approved as a requirement-design baseline; QR-02 is deferred; approval does not assert implementation or measured results.
- This ADR changes only architecture documents; it does not modify requirements, application code, tests, baseline evidence, permissions, or secrets.
