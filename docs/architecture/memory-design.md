# Memory and State Design

> Current scope amendment — 2026-11-23, D1 v1.50.0: seven active requirements / 37 FCs (FR-01, FR-03, FR-04, FR-10, SB-01, INV-01, SR-01); seven deferred / 28 FCs (FR-02, FR-05, SR-02, FR-06, FR-07, PR-01, CR-01); total 14 / 65. Six-active scope pre-approved in [PR #12 comment 7089283044](https://github.com/Howindy/Teamproject-Tradingagents/pull/12#issuecomment-7089283044) (`cc2c834c3ce9097f08d95b4beef1a5dc1bb0b7e9`); FR-10 preparation pre-approved in [PR #14 comment 7099714477](https://github.com/Howindy/Teamproject-Tradingagents/pull/14#issuecomment-7099714477) (`docs/plans/financial-metrics-integration.md @ e99ab57b6e460fad59bb4bf4a81cffa5c717c8da`), governed by [ADR 002](adr/002-deterministic-financial-metrics.md). This is scoped design/test pre-approval, not final review or product acceptance. Native manifest, new precise statistics, history and their dedicated path controls are future-only. Existing baseline statistics, saves and protections remain.


- Document status: Proposed companion architecture document; not an approval, implementation claim, or test result.
- Requirements basis: [`docs/req/requirements.yaml`](../req/requirements.yaml) version 1.50.0, independently counted as 14 requirements and 65 fit criteria: 7 approved active requirements with 37 FCs, and 7 deferred requirements with 28 FCs.
- Architecture basis: [`architecture-blueprint.md`](../../architecture-blueprint.md), [`ADR 001`](adr/001-graph-internal-final-check.md), and [`ADR 002`](adr/002-deterministic-financial-metrics.md).
- Cross-check basis: [`invariants.md`](invariants.md), [`trace-matrix.md`](trace-matrix.md), and [`evaluation-table.md`](evaluation-table.md).
- Related runtime behavior: [`runtime-policy-catalog.md`](runtime-policy-catalog.md).
- Evidence rule: `Existing code` or `baseline` describes verified current behavior only. `Planned` describes the selected D2 design with no implementation or executed test. No code, test, measurement, approval, or recovery claim is made here.
- Scope limit: this document organizes state already required or selected. It adds no persistent registry, database, event log, vector store, RAG, memory index, migration protocol, hash, version allocation, encryption layer, or retention service.

## 1. Scope and state model

“Memory” here includes all of the following, not just long-term model lessons:

1. ephemeral per-analysis control state;
2. serializable graph state used by the current analysis;
3. JSON, Markdown, HTML, and memory-log artifacts actually written to disk;
4. existing cross-run vendor caches and checkpoint storage.

A value being JSON-compatible or marked serializable in the blueprint does not prove that the current application persists it. The table therefore separates the owning object, the intended carrier, and the actual writer. The current code still has the pre-D2 Portfolio Manager, report, state-log, memory, and checkpoint structure; C-08/C-09 independent cores exist, but their graph/entry wiring and the FR-03 registry remain unimplemented; manifest/history/new-stat work is deferred.

FR-06, FR-07, PR-01, and CR-01 are deferred. They add no recovery material, summary field, cost record, retention task, or placeholder interface here.

## 2. State inventory and lifecycle

| State | Owner | Carrier | Writer and timing | Reader and use | Session, interruption, and version behavior | Retention and deletion | Privacy boundary |
|---|---|---|---|---|---|---|---|
| Active binding, locks, reuse/availability objects | C-03 | Process memory | Entry start/exit | Local adapters and snapshots | Lost at process end; fresh per analysis | No new persistent retention | No credential/config/payload archive |
| FR-01 query-reuse outcomes and single-flight synchronization | C-05 `QueryReuseService` under C-03 | Process memory, one run | First caller completes and publishes the existing result/failure; waiters reuse it | P-09 and P-13 callers | Lost on process end. No cross-run reuse, module global, or persistent cache entry. | No retention after the run. Existing vendor caches remain separate. | Reuses the existing business result/failure; adds no payload archive or source log. |
| FR-03 observations, acceptance sequence, query marks, and path associations | C-07 `AvailabilityRegistry` under C-03 | Process memory, one run | C-06 helper and C-20 classifier accept an observation; path association may be added when a supported query begins | C-07 summarizer, research/final/report consumers through snapshots | Lost on process end. Not written to manifest, memory, checkpoint, or a diagnostic file. No snapshot version history. | No independent deletion; object lifetime is the run. Materialized summary may survive only if written into returned/saved state or report. | Safe status, reason, method/object/parameters, known source or null, and path IDs. No raw payload, prompt, full config, or unhandled exception text. |
| Private pre-fetch call-failure notes and `availability_tracking_error` | C-07 availability management under C-03 | Process memory, one run | A supported call rejected before fetch adds a note; unlocatable/unrecordable completed-query observation loss sets the tracking error | C-07 summarizer; tracking error makes later snapshots `None` | Lost on process end. Not in `AvailabilitySummary`, final state, report, memory, manifest, or checkpoint. A new run starts clean. | No ledger, diagnostic file, or repair record. | Fixed category and short safe reason only; no raw arguments, exception, payload, or configuration. |
| `research_availability_summary` | Research-entry wrapper C-10; graph state | Graph state mapping or `null` | On first research entry only, after analyst join and before the first Bull call | First Bull directly; later Bull/Bear and Research Manager from state | Serialized only if the state is actually returned or saved by an implemented writer. No checkpoint resume, refresh, version, or second stage snapshot. Lost on interruption unless an actual save captured it. | No stage-summary history or deletion mechanism. Superseded only by a new analysis's own state. | Fixed five-field program summary or `null`; it is rendered into a model prompt but is not model-authored. No raw payloads or credentials. |
| Check-time availability input and terminal delivery summary | Risk node and entry adapters; C-07 source | Graph state field `data_availability_summary`; terminal mapping may enter returned/saved final state and report | Risk node writes a check-time snapshot; SB-01 consumes it; after the formal check, the entry prepares a terminal summary into final/report state | C-09 uses the check-time input; C-11 and independent save read only the terminal passed state | Check-time and terminal values are not versioned or hashed. The terminal field can replace the state value used for delivery, but it cannot change the already-formed formal result. Lost on process end unless actually saved. | The run-in report/final state may retain the terminal mapping; no snapshot history, archive, or automatic deletion is added. | Same five-field safe summary semantics. No live registry access from the writer and no raw payload. A missing summary is shown as unavailable, not fabricated. |
| Analyst reports, debate histories, plans, memory lessons, and other graph fields | Graph nodes and existing state reducers | LangGraph graph state; existing return/state-log projection | Analysts, researchers, Trader, risk debaters, Portfolio Manager, and `_memory_step()` | Later graph nodes, report writer, returned final state, existing state log | Run-scoped. No new-flow checkpoint continuation. Serializability is not proof of persistence; the current `_log_state()` writes a fixed projection, not the whole graph state. | Depends on actual outputs: returned state, report sections, and existing state log. No new retention mechanism. | Existing model-generated reports and debate text can be sensitive and may be written to reports or state. The design does not claim full-body sanitization. |
| Memory-derived `past_context` and `memory_note` | `_memory_step()` and graph state | Graph state strings | At the graph's Memory Log step, before the Portfolio Manager | Portfolio Manager prompt and report header note | Run-scoped and regenerated from the persistent memory log in a later analysis. Not a new memory version. | Not separately persisted beyond a returned/saved state or report note. | Contains selected prior decision text/reflections and a safe degradation note; existing model text may be sent to the model provider again. |
| Purchase scenario and risk thresholds | Entry and graph state/config | Simple JSON-compatible mapping in graph state when carried | Caller/CLI input at the entry boundary; validation by C-08 | C-08 and report/state consumers | No normalized state protocol, digest, version, or checkpoint requirement. Lost on process end unless an actual output includes it. | No separate scenario file or history is added. | Caller-supplied financial inputs are not credentials. The risk result omits unsafe/raw invalid values; no model text or account data fills missing values. |
| `model_proposal` | Portfolio Manager C-10; graph state | Nested `{rating, text}` or `null` in graph state; labeled report section when implemented | Portfolio Manager model completion | SB-01 as input; separately labeled proposal display/report | Advisory only. Lost on process end unless an actual output includes it. No checkpoint continuation. | No memory record and no manifest rating field. Existing report/state overwrite behavior applies if included. | Model-generated recommendation text. It may be shown separately but must not replace formal fields. |
| `portfolio_risk_result` | C-08; graph state | JSON-compatible mapping with display-safe scenario/thresholds, decimal-string/null metrics, status, and risk-scoped reasons | Risk node after evaluating the caller scenario | SB-01 and CLI/report consumers | Run-scoped. The current `_log_state()` fixed projection does not include a complete risk/availability archive, and this design does not require expanding it; returned final_state and generated reports still deliver the required risk result. No checkpoint requirement. | No risk metadata is required in memory or the manifest. Only actual report/state outputs may retain it. | Display-safe values only; invalid/unsafe raw inputs are omitted. No model text, raw account data, or network fill. |
| Formal result: `gate_status`, top-level `reasons`, `final_rating`, `final_trade_decision` | C-09 `FinalRecommendationChecker`; graph state | Graph state; intended final-state JSON, CLI, report, and state log | SB-01 node only | Entry return, CLI, report, state log, memory adapter | Run-scoped authority. Missing/invalid output is an execution contract failure, not a persisted fallback state. No manifest rating field or read-time version proof. | Retained only in outputs actually written. Existing same-path report/state overwrite behavior remains; no immutable archive. | Formal decision text is model-derived on a pass and program-generated on REVIEW, with actual safe reasons. No credential or raw payload is added. |
| Saved final-state JSON | Existing `record_decision()`/state-log path; D2 final-state save boundary | Existing `<results_dir>/<ticker>/TradingAgentsStrategy_logs/` JSON path | Existing state save after a valid formal result; D2 preserves path-specific failure behavior | Operator, later inspection, current memory step after state save | An existing file can remain after interruption. Same ticker/date uses the existing file path and can be overwritten by a later save. The D2 design adds no run_id-specific state file or migration. | Existing file behavior only. No automatic rotation, cleanup, backup, or immutability. | Existing fixed projection of reports, debate/plans, final fields, and allowlisted `run_settings`; this design does not require adding a complete risk/availability archive, while returned final_state and generated reports still deliver those results as required and INV-01 keeps its formal rating/body save requirement. No new full-config dump. |
| Saved report tree, merged Markdown, and HTML | C-11 `ReportWriter`; CLI save or independent save | Run-in default path under `results_dir`, or caller-chosen path | Requested CLI save inside the run; independent `save_reports(final_state, ...)` after the run | User, CLI display, user; future FR-05 deferred | A partial tree can remain after a failure or interruption. Existing same-path saves may overwrite earlier files. No original-byte, hash, or version guarantee. | No automatic cleanup or immutable archive. History references current file content; manual edit/delete changes availability. | Contains existing model-generated report text plus deterministic formal/risk/availability sections. No full config/credential scan is claimed. |
| New memory decision entry and later settlement/reflection updates | C-12 `MemoryAdapter` / existing `TradingMemoryLog` and `Reflector` | Configured `memory_log_path` Markdown file | New decision appended after final-state save; existing settlement updates the same entry later | Later analyses' Memory Log step and Portfolio Manager; operator inspection | Persistent across sessions. New D2 entry must use the formal rating/body. Settlement may later update outcome/reflection but not regenerate the original rating/decision body. No version allocation. | New entries are blocked by the existing same-ticker/date idempotency guard. When `memory_log_max_entries` is set, the oldest resolved entries are pruned on a settlement write; pending entries are kept. Default is `None`, which disables rotation. No other automatic deletion. | Stores trade date, ticker, rating, decision prose, outcome percentages, and reflection; model text may be re-injected into later prompts. No credential store or encrypted memory. |
| Existing vendor caches | Vendor adapter / configured `data_cache_dir` | Yahoo OHLCV per-symbol CSV; SEC EDGAR JSON under `sec_edgar` | Existing data fetch writes cache files | Later analyses and vendor calls | Cross-run and independent of FR-01. Verified current behavior: Yahoo cache is reusable only when written on the current day, with a 900-second same-day TTL for a current-day request; SEC JSON uses a 24-hour mtime TTL. No new persistent registry. | Cache files persist until replaced or removed externally; this design adds no automatic purge beyond existing freshness checks. | Contains vendor market/filing data, not model prompts or credentials. Cache contents remain subject to existing vendor handling. |
| Existing checkpoint databases | C-16 `CheckpointAdapter` / existing checkpointer | SQLite under `<data_cache_dir>/checkpoints/<TICKER>.db`; thread ID from ticker/date/signature | Existing checkpoint code outside the D2 flow | Existing checkpoint tooling/tests only; not the new flow | May persist across sessions under old behavior. The new flow acquires no session, does not resume, reads no old checkpoint as evidence, and deletes none. Version/signature behavior belongs to existing code. | Existing storage and clear tools remain. The new flow adds no retention or deletion action. | May contain graph state from an older run. It is not current analysis evidence, not a formal output, and not exposed through the new availability/history interfaces. |
| FR-10 ephemeral metric cache (planned PR 2) | C-21 `FinancialMetricProvider` / `wiring` (ADR 002) | Process memory, strictly scoped to one analysis run | First Fundamentals Analyst resolution before model turn; reused across tool/wrap-up turns in that same run | Fundamentals Analyst system prompt only | Lost at run end; never enters graph state/checkpoints (`Decimal`, locks, and providers stay out of serializable state) and never inherited across independent analyses on a reused `TradingAgentsGraph`. | No persistent metric bundle store, history, or recovery policy added. | Contains only structured public financial metrics/periods/sources or explicit `n/a` reasons; no credentials or full config. |

## 3. Write, read, and update rules

### 3.1 Run-scoped control state

C-03 owns only ephemeral scope binding, reuse and availability objects. Restore the previous binding on every normal/error exit. Do not serialize locks, registries or runtime objects into graph state/checkpoints. Independent analyses never share these objects; explicit delegation shares its caller scope.

### 3.2 Available summaries and research delivery

- The research wrapper obtains one summary at research start. It stores a five-field mapping or `null`; the unavailable display sentence is renderer text, not a third stored type. Later observations do not refresh it.
- The risk node obtains a separate check-time summary for SB-01. After the formal check, the entry may prepare a terminal delivery summary from the current run's registry and place it in `data_availability_summary` for the final/report state.
- Refreshing the terminal delivery field is not a formal re-check. It does not rerun SB-01 or change `gate_status`, `reasons`, `final_rating`, or `final_trade_decision`.
- A run-in report writer reads only the prepared passed state. Independent `save_reports(final_state, ...)` reads only that final state and never the live registry, active context, graph cache, or another run.

### 3.3 Formal result and memory decision

- The Portfolio Manager produces only `model_proposal`. SB-01 is the only producer of the formal four fields (plus the proposal's nested representation in the five-field result).
- If this run creates a new memory decision, its rating and body come from the formal result. If memory is disabled or the existing same-day guard means no new record is created, no record is forced. A historical record is not rewritten to the current decision.
- Settlement and reflection may later update outcome, reflection, and related fields. They do not regenerate the decision body or replace the original rating.

### 3.4 Memory retrieval

The existing memory read path is preserved, not redesigned:

- only resolved entries are eligible;
- a historical `as_of` keeps entries whose stored resolution date is on or before that date; a live/current-date run disables that point-in-time filter as existing code does;
- the prompt context takes up to five most recent same-ticker entries and three most recent cross-ticker entries;
- no embeddings, vector database, semantic search, RAG, ranking model, or new cross-ticker strategy is added.

The resulting text is inserted into the Portfolio Manager's existing prompt. This is an existing model-input path, not a new memory write.

### 3.5 Persistence and ordering

Preserve existing final-state-save then conditional new-memory append ordering and optional reports. A failed save is not claimed successful; preserve its original handling and files already saved. There is no cross-file transaction or current manifest/registration step.

### 3.6 History and vendor caches

History is deferred. Existing cross-run vendor caches remain baseline behavior and are distinct from the new per-analysis FR-01 reuse state.

## 4. Session, interruption, and version boundaries

### 4.1 Normal process lifetime

Before analysis no scope exists. During analysis C-03 holds ephemeral reuse/availability; graph state holds serializable snapshots and business results. On normal delivery only outputs actually saved survive. Restore scope after entry-owned cleanup; no terminal manifest/new statistics are required.

### 4.2 Interruption and process end

Ephemeral scope and unsaved graph state are lost. Preserve files already written without claiming terminal success or automatic recovery. A later invocation creates fresh state and fully reexecutes; it does not resume old checkpoints.

### 4.3 Version and compatibility

Keep existing source/test layouts, saved report/state/memory formats and old checkpoint evidence. No new manifest format, history migration, persistent analysis-identity protocol or retention service is current.

## 5. Retention, deletion, and privacy

### 5.1 Retention and deletion

- No new automatic expiry, rotation, backup, archive, or migration is introduced for manifests, run directories, final-state files, reports, vendor caches, or checkpoints.
- Existing report directories and same-path files are retained; a later save may overwrite the same path. File retention does not imply immutable original bytes.
- Vendor cache freshness is not retention policy: an expired or invalid entry may be refetched and replaced. There is no new scheduled cache purge in this design.
- The memory log has one verified retention control: when `memory_log_max_entries` is configured, the oldest resolved entries are dropped during an outcome-update write; pending entries are kept. The default is `None`, meaning no rotation.
- Manual deletion, external edit, or overwrite is not detected or repaired by the new design. A deleted registered report becomes unavailable to history according to existing FR-05 rules.

### 5.2 Privacy boundaries

- Current report/final-state configuration summaries use the existing `run_settings()` allowlist. Credential fields, endpoints, and local paths are not added to the summary.
- Availability records, failure marks, call-failure notes, and tracking error use fixed safe reasons and do not store raw payloads, prompts, complete configuration, or raw exception text.
- The risk result is display-safe; unsafe or invalid raw scenario values are omitted. No model recommendation, caller portfolio context, or memory text fills a missing risk value.
- Reports and returned/saved final state contain existing model-generated analysis and decision text. The design does not scan or redact the full report body.
- Memory stores model-generated decision prose and reflection, and selected memory text is re-injected into later model prompts. This can send prior model text to the configured external model provider under existing behavior.
- The security scope is limited: no full-application redaction, encryption at rest, access isolation, universal secret scanner, credential store, data-classification platform, or privacy-governance service is added.
- Existing safe warnings must not contain raw credentials, complete configuration, or uncontrolled exception text.

## 6. Verification intents and open items

| ID | Verification intent | Evidence state |
|---|---|---|
| M-V01 | Independent analyses isolate RunContext, FR-01 reuse, availability observations and context binding; explicit delegation shares scope, and exit restores prior binding. No new statistics isolation/refactor acceptance is added. | Planned; existing checkpoint/entry tests are baseline only. |
| M-V02 | Research uses one fixed stage summary; later observations do not change it. | Planned; wrapper/executor integration pending OQ-13/OQ-15. |
| M-V03 | Check-time and terminal availability inputs have the intended consumers; report writers never access live registry or rerun SB-01. | Planned; report source integration pending OQ-15. |
| M-V04 | New memory entries use the formal rating/body; disabled/no-new-record creates nothing; settlement does not rewrite the decision. | Planned; existing `test_memory_log.py` and `test_cli_memory_log.py` are baseline only. |
| M-V05 | Interruption leaves only actually written artifacts and does not claim completion/recovery. | Planned boundary inspection; no forced-termination claim |
| M-V06 | Existing state/report/memory failures preserve original errors and do not roll back saved files. | Planned |
| M-V07 | Memory retrieval retains existing same-ticker/cross-ticker limits and point-in-time filtering; no vector/RAG component exists. | Static code review of existing memory log; no new retrieval implementation. |

Current pending items that affect implementation: OQ-12 unverified FR-03 producer branches; OQ-13 shared news executor and research wrapper; OQ-15 ordering, fixtures, and report source. OQ-01 remains pending before affected input implementation; OQ-04 is verification of retained save/display behavior, not an extra product decision; OQ-02 is decided only for the key names `max_projected_weight` and `max_stop_distance`; OQ-08 remains pending technical verification. These are evidence or interface gaps, not new state or new requirements. D2 OQ-16 callback/statistics propagation belongs only to deferred FR-02 and does not block the current six requirements.

No source conflict was found for the state boundaries above. Deferred FR-02/FR-05/SR-02/FR-06/FR-07/PR-01/CR-01 and context budgeting/compression/reinjection remain outside this design.

## Deferred and historical design archive — not current implementation instructions

Prior mixed/current design text below is retained only for historical rationale or future reactivation review. Its mandatory wording is not current acceptance.



### 3.1 Run-scoped control state

- `RunContext`, the stats collector, FR-01 reuse state, availability observations, path associations, query marks, call-failure notes, and the tracking error remain in process memory for one analysis. They are not moved into graph state or checkpoints.
- A reusable graph or model object may serve multiple analyses, but it must not retain the prior analysis's collector, reuse registry, availability registry, or context binding. Exiting the context restores the prior binding.
- FR-01 results are keyed only within one run. Existing vendor caches are a separate cross-run layer and never count as FR-01 reuse.



### 3.5 Persistence and ordering

- Manifest persistence is best-effort and atomic per visible file. A failure is a safe warning and does not change analysis, formal result, or run outcome.
- Final-state JSON, a new memory append, and a requested CLI report retain their path-specific failure behavior. They are not uniformly best-effort.
- Existing order is preserved: graph and formal result, existing final-state save, new memory append, requested report save. An earlier failure prevents later writes in the existing order.
- There is no cross-file transaction, rollback, repair, or automatic re-registration. A successful final state is not rolled back because memory fails; a successful Markdown report is not deleted because HTML fails.



### 3.6 History and vendor caches

- History is read-only after implementation. It discovers only completed, supported manifests with a legal report reference; it does not infer unregistered files, repair records, regenerate reports, or create an index.
- Cache reads are existing vendor behavior. Cache hit/miss, fallback, and withholding semantics remain inside the data-fetch flow and are distinct from FR-01 and FR-03 observation state.



### 4.1 Normal process lifetime

| Point | What can exist | What is not guaranteed |
|---|---|---|
| Before entry validation succeeds | No analysis run, no manifest, no new memory record | Nothing beyond existing caller state |
| After `RunContext` starts | In-memory run control state; possibly a running manifest | No formal result, no completed report, no new memory |
| During graph execution | Graph state, run-scoped registries, possibly a running manifest | No final formal result; no checkpoint resume in the new flow |
| After SB-01 and before saves | Complete formal result in memory/state; terminal summary preparation may exist | Files are not yet guaranteed; a process crash can lose all unsaved state |
| After final-state save, before memory | Saved final-state JSON may exist | Memory may not exist; do not infer it from state success |
| After memory, before terminal manifest | Saved outputs may exist; manifest may still be running | No terminal manifest guarantee |
| Normal finish | Requested outputs that succeeded; terminal manifest attempted | No recovery proof, immutability, or terminal guarantee if the manifest write failed |



### 4.2 Interruption and process end

- All in-memory `RunContext`, stats, FR-01, availability, research-entry runtime state, and unsaved graph state are lost.
- A manifest may be missing or remain `running`; that is not evidence that the analysis is still running or that it failed.
- A report save interrupted between Markdown and HTML can leave a partial tree. The confirmed Markdown may be usable, but no HTML success is claimed.
- Final-state and memory may be absent, or final-state may exist while memory does not. No automatic rollback is performed.
- A pending memory entry may be settled by the existing later settlement path, but this is existing memory behavior, not analysis-run recovery. The design adds no background worker or recovery scheduler.
- Existing checkpoint data may remain on disk, but the new flow does not read, resume from, or delete it. A later invocation is a new analysis and repeats model/data work.



### 4.3 Version and compatibility

- The existing memory parser accepts its current tag shape and optional resolution-date field. Malformed entries are skipped by existing parsing; there is no migration, version allocation, or upgrade pass in this design.
- A proposed manifest has a format/version marker, but no manifest implementation exists. Unsupported or unparseable manifests are outside history; no migration is added.
- Reports and final-state JSON have no new version protocol, hash, or read-time compatibility proof. Same-path saves and external edits may change current content.
- Existing checkpoint signature compatibility belongs to the old checkpoint subsystem and is not used by the new flow.
- No automatic compatibility between old and new files is promised. Existing formats may be read only where the implemented reader explicitly supports them.



| Per-analysis stats handler and collector | C-03 creates C-04 for one analysis | Process memory: model-call record map, tool-call ID set, one lock | C-04 receives this execution's callbacks; snapshot on normal completion or a caught execution error | C-03/`finish()` and C-14 manifest projection | Lost on process end. Not stored on the reusable graph or model clients; independent analyses get separate instances. | No current persistence beyond the manifest fields. No cross-run counter store. | Call IDs, counts, and token totals only; no prompt text, response body, raw usage object, or credential is required. |

| Run manifest | C-03 and C-14 `ManifestStore` | JSON at `<results_dir>/<run_id>/run_manifest.json` | Attempted at start, terminal attempt at `finish()` | Operator, diagnostics, FR-05 registration | In-memory events are lost on crash; the JSON may be missing, running, completed, or failed. No automatic terminalization or recovery. | Persistent file. Existing run directories are retained; this design adds no automatic cleanup, rotation, or garbage collection. | Identity, timing, allowlisted config summary, counts, token totals, confirmed refs, and safe error summary. No formal rating, prompt, raw tool body, credential, or complete config. |

| History list and report-read result | C-13 `HistoryReader` | Derived process result; no index | On an explicit list/get call after implementation | Caller | Recomputed from manifests/report path on each call after implementation. No cross-request snapshot, cached index, or version promise. | No persistent history state. Manual file changes affect the next call. | Read result contains report text or safe summaries/errors; no credentials or unrelated file content. |
