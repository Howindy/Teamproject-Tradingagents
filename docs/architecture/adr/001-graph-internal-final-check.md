# ADR 001 — Graph-Internal Final Check with Run-Scoped Governance

> D1 v1.51.0 (2026-11-25) records five delivered requirements (FR-03, FR-04, FR-10, SB-01, INV-01, 28 fit criteria) and nine deferred requirements (FR-01, FR-02, FR-05, FR-06, FR-07, PR-01, CR-01, SR-01, SR-02, 37 fit criteria). FR-01 reuse and SR-01 credential controls below are retained designs for future activation. Existing vendor caches and baseline credential protections still apply.


- Status: Proposed for human review
- Date: 2026-11-17
- Decision owners: Architecture review (human) with coding-agent analysis support
- Requirements baseline: `docs/req/requirements.yaml` version 1.51.0
- Related: [Architecture Blueprint](../../../architecture-blueprint.md), [Evaluation Table](../evaluation-table.md)
- Supersedes: the earlier proposal to run the final business check in a shared entry-boundary `RunFinalizer`

This ADR records the architecture selection and the ADD-R process. It intentionally separates:

- what the requirements require,
- what the existing code does,
- what this design selects,
- what remains an unapproved candidate or an unverified assumption.

No application code, test run, live model call, data-vendor call, measurement, or human approval is claimed.

---

## 1. Context and problem

### 1.1 Pre-decision architecture (historical baseline)

The repository is a LangGraph multi-agent analysis application. Both supported entry points eventually run the same graph:

- CLI: `cli/main.py` → `cli/run.py` → `TradingAgentsGraph` stream.
- Programmatic: `TradingAgentsGraph.propagate()` → graph invoke.

The graph ends at the Portfolio Manager (`tradingagents/graph/setup.py:185`). The Portfolio Manager currently writes `final_rating` and `final_trade_decision` directly (`tradingagents/agents/managers/portfolio_manager.py:80-104`). Consumers then read or re-parse those fields:

- `tradingagents/agents/rating.py:106` `run_rating()` returns the field or parses the decision text.
- `tradingagents/graph/trading_graph.py:404` returns `(final_state, run_rating(final_state))`.
- CLI displays the rating and offers report saving (`cli/run.py:380`, `cli/run.py:426`).
- `record_decision()` writes the state log and memory (`trading_graph.py:358`).
- `write_report_tree()` renders the decision (`tradingagents/reporting.py:92`).

There is no native run manifest, no run lifecycle, no structured purchase-scenario risk check, no availability summary, no query reuse service, and no history lookup. Existing security helpers are partial: `get_scrubbed()` (`dataflows/net.py:6`) and `safe_ticker_component()` (`dataflows/symbols.py:155`).

### 1.2 Requirements problem

The active requirements introduce a deterministic authority boundary:

- Portfolio Manager must produce only a model proposal.
- FR-04 must evaluate a caller-supplied structured purchase scenario.
- SB-01 must be the sole decision/generation authority for `final_rating` and `final_trade_decision`; downstream pass-through, merge, copy, and save of unchanged values are allowed.
- Consumers must not re-parse text into another formal rating.
- The normal completion path must not bypass SB-01.
- Checkpointing must not silently skip required checks.
- Intermediate proposal and formal output must be visibly separated.
- Manifest persistence is deferred. Report, final-state, and new-memory failures preserve existing exception/error behavior and preserve the original execution/save failure; they never recompute or rewrite the formal result.

This is not a greenfield redesign. The graph, agents, vendors, reports, and memory remain usable; checkpoint code/tests remain in the repository outside the new flow.

### 1.3 Design constraints

- Python >= 3.11, LangGraph, pytest, ruff.
- Two entries only.
- No model/data calls in FR-04/SB-01.
- No new database, index, background worker, recovery system, or generic scanner.
- Offline testability; the suite blocks network by default.
- No modification of requirements or governance configuration in this task.
- Module paths in this ADR are relative to `src/` after the approved layout migration; for example `cli/run.py` is `src/cli/run.py`.

### 1.4 Requirement scope check

Independent count from `docs/req/requirements.yaml`:

| Scope | Requirements | Fit criteria |
|---|---|---|
| Active | 5 | 28 |
| Deferred | 9 | 37 |
| Total | 14 | 65 |

Active: FR-03, FR-04, FR-10, SB-01, INV-01.
Deferred: FR-01, FR-02, FR-05, FR-06, FR-07, PR-01, CR-01, SR-01, SR-02.

This matches the expected scope. Deferred items are not designed as current behavior.

---

## 2. Decision summary

Select **graph-internal deterministic finalization with a run-scoped governance context and thin adapters**.

The graph becomes:

```text
Existing analysis and debate
  → Portfolio Manager: model_proposal (advisory only)
  → Portfolio Risk Check node:
       AvailabilitySummarizer.snapshot(asset_type, enabled_analysts, analysis_context)
       PortfolioRiskEvaluator.evaluate()
       writes check-time data_availability_summary + portfolio_risk_result
  → Final Recommendation Check node:
       FinalRecommendationChecker.evaluate()
       writes gate_status, reasons,
              final_rating, final_trade_decision
  → END
  → Entry validates the formal result (IF-19)
  → Entry prepares the terminal report summary into final/report state
       without rerunning the check or changing formal fields
  → CLI / propagate() deliver the unchanged formal fields
```

`RunContext` owns the ephemeral availability registry and scope binding. It is not serialized into graph state or checkpoints.

The entry adapters do not perform a second business check. If an entry-boundary `RunFinalizer` exists, it coordinates entry-owned cleanup and binding restoration; it does not create a second close path, and `RunContext.finish()` does not close resources.

---

## 3. ADD-R design process (v1.48.0 historical decisions; current scope amended above)

ADD-R is used because the design retains and adjusts an existing architecture. Each round states its inputs, candidate concepts, decision, and remaining gap.

### 3.1 Round 0 — Baseline, scope, and drivers

Inputs:

- Current source paths in Section 1.1.
- Active and deferred requirement counts.
- Baseline run `baseline-20261020-01` (old behavior only).

Activities:

- Confirm the two entry points and their divergence.
- Confirm the graph ends at the Portfolio Manager.
- Confirm the existing output surfaces: CLI, report, state log, memory, return value.
- Confirm the absence of the new governance components.

Decision D-00: retain the existing graph and add deterministic post-PM nodes; do not rewrite the analysis pipeline.

Remaining gap: no authority boundary, no run lifecycle, no data observation.

### 3.2 Round 1 — Authority and intermediate/formal separation

Candidate concepts:

1. Entry-boundary finalizer in both entries.
2. Graph-internal final-check node.
3. Independent post-graph service invoked by both entries.
4. No new authority; keep Portfolio Manager fields and add display labels only.

Analysis:

- Entry-boundary finalizer duplicates the authority boundary and can diverge between CLI and `propagate()`. It also makes checkpoint behavior ambiguous.
- A graph node is part of every normal completion path and produces one state source for all consumers. Checkpoint compatibility can be handled explicitly.
- An independent service is a second orchestration path and risks bypass.
- Display-only labels do not satisfy SB-01/INV-01.

Decision D-01: graph-internal final check. Portfolio Manager writes only `model_proposal`. SB-01 alone decides and generates the formal values; entries, reducers, and writers may pass, merge, copy, or save them unchanged, but may not recompute, re-parse, replace, or fabricate them. Such pass-through is not a second authority.

Decision D-02: retain `model_proposal` separately as a nested `{rating, text}` object or `null`; inner values may be `null`, and no `present` boolean or fabricated proposal is added. Consumers never use it for formal fields. SB-01 produces a complete blocked/REVIEW for missing or invalid check inputs and a complete error/REVIEW for its own handled exceptions. A missing, wrong-type, empty-string, or whitespace-only model conclusion is an ordinary input-condition failure producing blocked/REVIEW, not an SB-01 internal error. A valid conclusion is preserved unchanged; whitespace stripping may be used only to test non-emptiness. A missing or invalid formal output after the graph is an execution contract failure, not a consumer-generated REVIEW and not a text-parsed rating. Top-level `reasons` belongs to SB-01; `portfolio_risk_result.reasons` stays scoped to FR-04 and is not flattened into the formal result.

Decision D-02a: define a lightweight shared `FormalResultContract` that validates the five top-level fields (`model_proposal`, `gate_status`, `reasons`, `final_rating`, `final_trade_decision`) and their types. It checks that `model_proposal` is a nested `{rating, text}` object or `null`, formal gate and rating sets are legal, passed has a five-tier formal rating, blocked/error has REVIEW, `final_trade_decision` is a non-whitespace string, `reasons` is a string list, and blocked/error has at least one actual reason. An illegal proposal rating is SB-01 input, not a contract failure. It returns the result unchanged or reports an execution contract failure. It does not recheck data or risk, call a model/data source, parse text, repair the result, or create a second business status. No `present` field, `gate_reasons` alias, signature, hash, source proof, persistent diagnostic system, or new module/public API is added.

Decision D-03: intermediate surfaces use explicit labels:

- “Original Model Proposal — Not Yet Checked” before the check.
- “Original Model Proposal — Did Not Pass Final Check” for blocked/error.
- Formal area waits, then displays SB-01 fields only.

Remaining gap: risk input and availability snapshot must reach the final node.

### 3.3 Round 2 — Run lifecycle, manifest, and statistics

Candidate concepts:

1. A process-global run singleton.
2. A `RunContext` owned by the outermost entry and exposed through a context variable.
3. A graph-managed manifest node.
4. A separate manifest service with its own queue/process.

Analysis:

- A process-global singleton breaks parallel runs and tests.
- A graph node cannot own CLI save timing, resource close, or terminal status without mixing graph state and operational state.
- A separate service adds a new process/persistence system and violates the minimal constraint.
- A run-scoped context with a context variable matches the existing `run_config` pattern (`dataflows/config.py:44`) and supports concurrent analysts.

Decision D-04: `RunContext` creation is entry-specific and scoped to one analysis; it is not created by the object constructor. The CLI creates it after selection/config/basic validation and before graph-object construction. `propagate()` creates a new one after invocation, per-call validation, and effective-config resolution on an existing object. Object construction is analyzed separately from the analysis run. The context owns run_id, timers, status, the per-analysis stats handler/collector, reuse, availability, output references, and manifest orchestration, and is not serialized.

Decision D-04a: CLI object construction, client initialization, initial workflow compile, and per-run preparation are inside the run and its elapsed time. A CLI construction/client/compile/preparation failure is a post-start execution failure with a failed-manifest attempt and the original error preserved. Program object construction and idle time are outside the run; construction failure before `propagate()` creates no analysis run or manifest. The initial workflow compile is object construction for the CLI and pre-existing for the program entry; the new flow does not perform a checkpoint recompile.

Decision D-04b: the initial running manifest uses a shared config-summary projection over the effective configuration and selected analysts, following the existing `run_settings()` allowlist. It does not require a constructed graph, a second allowlist, extra graph construction, or a credential-policy expansion. The instance `run_settings()` reuses the projection.

Decision D-04c: resource cleanup has one owner per resource. The entry/execution scope coordinates necessary cleanup and summarizes the outcome; each wrapper releases only its own resource; `RunContext.finish()` receives the summarized outcome after cleanup attempts and records end time, stats snapshot, and terminal manifest. It does not close streams, call `end_checkpoint()`, delete checkpoint data, close clients, or repeat a close. Existing checkpoint storage, cleanup tools, and tests remain outside the new flow; the new flow does not acquire a checkpoint session or call success cleanup.

Decision D-05: manifest persistence is best-effort and atomic. Running and terminal writes are separate attempts. Manifest failure never changes the run outcome or formal result or masks the original error.

Decision D-05a: persistence handling is path-specific. Final-state JSON, new-memory append, and CLI-requested report failures preserve existing exception/error behavior and can make the run `failed`. Memory disabled or an existing same-day record is not a failure; `_memory_step()` settlement/reflection/read degradation stays degraded; an independent `save_reports()` after `propagate()` preserves that operation’s behavior and does not reopen the completed run. No transaction, rollback, or automatic repair is added.

Decision D-06: CLI save selection and save attempt are inside the run; display/browser are after the terminal attempt. `propagate()` does not force a save; a later save is outside the run.

Decision D-07: one per-analysis `RunStatsHandler` is created with the RunContext and directly owns its collector: a model-call record map, a tool-call ID set, one lock, and a snapshot method. The handler is merged into this graph invocation/stream's execution `callbacks` config, not bound to quick/deep model construction and not overwriting existing execution-config callbacks. Existing custom callbacks are preserved; only this analysis's handler is added once. Internal CLI delegation to propagate shares one analysis RunContext/handler, while an independent call gets a new one. The handler does not look up its run through active context and there is no global collector, event router, or dispatcher. The RunContext ContextVar remains for other lifecycle/reuse/availability purposes; only stats ownership is direct. Callback IDs deduplicate starts/ends and distinguish analysis `run_id`; they are never synthesized from prompt text, model name, or timestamp. If identity or association cannot be established, the affected totals become null with a safe warning rather than a fabricated count. Per-call end usage drives totals; error counts a call with incomplete usage; unfinished calls are incomplete; any incomplete/invalid usage makes both totals null. Zero calls is true zero. Callback/collector exceptions are isolated and do not change model/tool outcomes. Exact config propagation and usage extraction boundaries remain pending verification; local explicit config handoff is preferred if a boundary does not inherit.

Decision D-07a: reflection attribution follows execution. A graph Memory Log reflection belongs to this analysis when its call runs under this graph execution; an independent `settle_pending()` / `settle_all_pending()` call outside the graph is not attributed merely because it shares a model object. Prefer inherited execution config. If read-only evidence or later verification shows a specific nested boundary does not inherit, pass that same execution config locally into the graph node/reflection call. Do not attach a permanent collector, refactor settlement, add background-task association, cross-thread ownership, or recovery protocol.

Decision D-07b: callbacks count application-level model calls only. A structured-output request that actually starts counts once; a subsequent free-text fallback that actually starts counts again. A local structured-binding failure with no model request does not count. Parser, chain, and graph-node work does not add a model call, and a schema-tool declaration is not an external tool execution. There is no manual per-invoke accumulation beside callbacks and no inference of hidden provider retries. Graph-internal reflection remains ordinary `llm_calls`; direct data prefetch remains outside `tool_calls`; no reflection/HTTP/prefetch/retry/fallback counter is added.

Remaining gap: data observation/reuse and the specific risk/final inputs.

### 3.4 Round 3 — Data observation, reuse, and risk

Candidate concepts for data observation:

1. Global monkeypatch of router/vendor functions.
2. Event bus with data events.
3. Explicit finite adapters for the 15 supported paths.
4. Model-reported availability.

Analysis:

- Global monkeypatch is hidden, order-dependent, and hard to test.
- An event bus is a larger platform than needed.
- Explicit adapters are finite, testable, and preserve original returns/exceptions.
- Model-reported availability violates FR-03 and SB-01.

Decision D-08: 15 path-specific observation sites using one small local helper at the existing call points; no global monkeypatch, middleware, dynamic proxy, or arbitrary HTTP observation. Each site preserves the original result/exception and passes it to the narrow `DataResultClassifier`; a non-empty string is not success. Router/vendor internals and tool callbacks are not additional FR-03 observation sources, and fallback attempts do not create separate business observations.

Decision D-08a: observation handling is isolated from the fetch result. The existing fetch executes once; classifier/registry handling runs separately. A known-query classifier exception creates one conservative `unavailable` observation with a short “availability classification failed” reason and known source or null; it is not a fifth status, does not imply provider failure, and stores no raw payload, complete configuration, or unhandled exception text. If a normal or conservative observation cannot be accepted, the registry records a local query-level failure mark. If the query cannot be identified or that local fallback also cannot be recorded, set the private run-local `availability_tracking_error`; later snapshots return `None`. This is limited to actual observation loss, not a general observation-failure veto. The shared completion is still published, waiters receive the original result or same failure, and the original value/exception is returned or propagated. Observation handling never triggers a refetch or replaces the fetch outcome.

Decision D-08b: the single observation helper is an ordinary internal function, not a framework API. It runs the original supported body once, preserves the result/exception, attempts one observation in isolation, then returns or re-raises the original outcome. With no active `RunContext`, it calls the body directly and records nothing. It does not retry, refetch, call a model, use a global, or monkeypatch. Early date/parameter failures inside the supported body that occur before a fetch are recorded only as private `availability_call_failures` notes with fixed safe reasons (D-08d); they never create a fake effective window, query key, observation, sequence, or tracking error. Exceptions after a fetch are observed then re-raised unchanged. Tool schema/name/message errors before the business body are not treated as executed queries. Completion sequence is assigned only when the registry accepts an update, never at helper entry, fetch return, or callback arrival; network/wall/monotonic time is never used to correct it.

Decision D-08c: attachment is path-specific, not router/vendor-wide. The News tool and sentiment prefetch share one plain internal news executor that receives P-09/P-13 explicitly; it performs existing date handling, forms the effective ticker/window key, enters FR-01 single-flight, and lets only the first execution call the router through the observation helper. A date failure before key creation returns the original error/exception, creates no single-flight entry, and may add at most one private P-09/P-13 parameter call-failure note. Waiters/cache hits create no observation. `get_indicators` observes each split indicator separately, never the joined string; date failure before splitting creates no per-indicator observations. StockTwits and Reddit are observed at their existing sentiment direct-call sites. Effective optional defaults reuse existing config/constants: P-10 config lookback/limit, P-11 365, P-12 6, P-14 30, P-15 5; none is recorded as an infinite window. A router path does not guess a winning vendor, and differing producer interpretations are recorded as reliable request semantics plus a limitation, not a fabricated uniform value.

Decision D-08d: a supported call rejected by existing date/parameter handling before any fetch gets a private `availability_call_failures` note, not a query observation. It records only path/method, safe object, fixed `parameter_rejected` category, a short safe reason, and a fixed necessary item ID when reliably known; no raw args/exception/payload/config, query key/window, completion sequence, FR-01 entry, or tracking error. Existing `as_of()`/`as_of_window()` adjustment/rejection semantics are unchanged; no stricter validation is added. If the note cannot be recorded, warn only. In a summary, a matching necessary item with no valid result stays `not_attempted` with a parameter-rejection reason; a matching supplementary item appears in `supplementary_limitations` as `unavailable` with a fixed parameter reason. The note never overwrites a valid result or query mark and never calls provider `no_data`.

Decision D-09: FR-01 reuse is a run-scoped single-flight service for the two `get_news` paths only. It does not reuse other methods or cross runs. A reuse hit preserves the original observation and adds no new observation.

Decision D-09a: a `CompletedObservation` has `query_key`, `executing_path_id`, status, safe reason, source, and acceptance sequence. The registry also keeps a small in-memory query-level failure-mark container (`query_key` plus a short reason), not a fifth status, public interface, history ledger, persistent state machine, or general permanent veto. Normal observations, conservative `unavailable` observations, and query marks are updates under the same local lock and one run-local acceptance sequence. For the same query, a later accepted update replaces an earlier accepted update, result or mark; an earlier success accepted later is simply the newest update and wins, while no external completion time corrects it. Another query's success never clears the mark. `query_key` contains only method and effective business parameters, never a call path. The registry keeps a simple internal `query_key → set of supported path_id` map; it is not a persistent object, association ID, or history interface. Association may exist before completion but creates no sequence, status, reason, or source and cannot by itself make the query `available`. Different objects, windows, methods, or effective parameters remain different queries. If a legacy `path_id` field remains, it aliases `executing_path_id` only.

Decision D-09b: the two news callers pass their internal path identity explicitly to the shared news executor; it is not inferred from a shared function name, tool callback, model, or global. A narrow internal argument is sufficient; no framework-specific API is required. Path identity is not model-visible, not in the query key, and must not leak across concurrent tasks. This covers P-09 tool calls and the P-13 sentiment prefetch.

Decision D-09c: the RunContext/availability-observation state has one private `availability_tracking_error`, null or a fixed safe reason. It is set only when an observation is actually lost and its query cannot be identified, or neither the normal record nor query-level failure mark can be recorded reliably. Ordinary data failures, recordable classifier failures, successful query marks, and pre-fetch parameter/date validation failures do not set it. It is not in `AvailabilitySummary`, not a fifth query status/fourth completeness state/business gate, not persisted, and not exposed publicly. Another query's success or a later successful snapshot does not clear it; only a new analysis starts null. It is not the withdrawn `summary_confirmable` flag.

Decision D-09d: if `availability_tracking_error` is set, every later snapshot returns `None` and never returns an older summary as new. If only the current snapshot construction fails with intact observations, that call returns `None` without setting the sticky error, and a later call may reconstruct. The update path builds the safe record first; on normal acceptance failure it tries the query mark; if that also fails it sets the tracking error independently of the failed record write. No transaction log, rollback/double-store, retry, or recovery guarantee is added; process/memory failure is outside scope.

Decision D-10: FR-03 uses a run-scoped registry with one run-local acceptance sequence and last-accepted-update semantics. Query identity is method plus effective parameters, independent of call path, so P-09 and P-13 update the same logical query. Necessity completeness is computed from a fixed seven-item list and enabled analysts. The summarizer first selects each necessary item's current result using existing matching and acceptance order. Complete requires every applicable selected item to be `available`; any `no_data`, `unavailable`, `withheld`, or no completed result makes it incomplete. A query-level mark is already projected as that selected item's `unavailable`, so completeness does not separately check marks. A withheld necessity item does not bypass completeness. A supplementary query failure or mark is disclosed as a limitation and does not by itself change basic completeness.

Decision D-10a: status recognition follows the verified per-method branch table in blueprint §8.3. Minimum `available` conditions include: P-02 needs a producer-generated price record with parseable date and finite Close; P-04 needs at least one recognized non-empty basic-information field; P-09/P-10 need at least one actual producer-generated article/news entry. Partial snapshot indicators N/A, partial fundamentals fields, and missing non-critical parts remain available. Headings, placeholders, error text, or arbitrary numbers are not sufficient; CSV paths require at least one actual data row, and a normal StockTwits block requires at least one message line. No article-count, relevance, truth, or full-period check is added. Router methods keep actual source unknown/null; configured vendors are not treated as actual source. `get_indicators` is classified per requested indicator before concatenation. Fixed sentinels and producer strings are matched only in their verified context. An unrecognized format is `unavailable`, never `available`. Unverified producer branches are listed as pending and are not fabricated. If a branch remains indistinguishable from final text, a minimal internal status hint may be considered later; it is not implemented in this round and must not rewrite all vendor responses.

Target-binding clarification authorized by the user on 2026-11-23 (not Round 3 implementation/test pre-approval): C-07 binds necessity targets before fetch after existing parameter/date handling and default resolution. The first eligible request under the registry lock fixes the current object's stock-price window and, independently for each statement, its effective date/frequency; global news binds effective lookback/limit only for the analysis date. Snapshot requires the current object and analysis date, ignoring utility lookback only for necessity matching; Reddit uses the existing sentiment-prefetch target. Binding allocates no completion sequence and never depends on success or completion order. Rejected requests do not bind; later requests cannot rebind an existing target, though an unbound item may bind later. Snapshots read bindings and updates consistently, match targets first, then apply the last accepted matching observation or query mark. Other-query success cannot substitute. With neither a matching completed observation nor a query-level mark, an applicable item remains `not_attempted`, without calling an in-flight query never started; a matching mark retains its existing `unavailable` projection. No forced query, extra summary field, public binding API, persisted identity, new input/configuration, period rule or FR-01 prerequisite is introduced. See blueprint §8.3 for the exact target table; existing producer/failure semantics and D-08d notes remain.

Decision D-10b: a lightweight research-entry wrapper around the first Bull call, not a new top-level node, defines research start as the analyst join immediately before that call. It requests one `AvailabilitySummary` from the summarizer using existing asset type, enabled analysts, and analysis context, or stores `null` if none is formed. It renders the mapping deterministically; for `null`, the renderer emits the fixed display text “program summary currently unavailable.” It injects the block into the same first Bull invocation and stores the mapping or `null` as `research_availability_summary` in state. Later Bull/Bear rounds and the Research Manager read that same stage summary directly; later observations do not refresh it or re-run research. The post-PM final check takes its own check-time snapshot. After the formal check, the entry prepares one terminal report/delivery summary from the same run's registry and places it in the report/final-state mapping; the report writer itself never takes a snapshot or reads the registry. This does not overwrite the research-stage input. The new flow does not resume checkpoints; research always starts from its normal entry, and old checkpoint-derived research material is not used as current evidence.

Decision D-10c: context delivery is role-local, not a cross-role context framework. Existing analyst prompt assembly, tool-message history, full-report research inputs, debate history, manager plans, memory lessons, and structured-output/fallback paths remain. Only the active FR-03 requirement adds the research-stage program summary to the first Bull call, later Bull/Bear rounds, and the Research Manager, with one narrow FR-10 compatibility exception under ADR 002: when FR-10 is enabled, the Fundamentals Analyst receives a deterministic pre-model financial metrics table in its system prompt while preserving its five financial tools and all other roles' inputs. A unified layer object, common ordering, normalized deduplication, input budget, automatic trimming, mandatory-block reinjection, local overflow refusal, and new role-failure mechanism are not introduced because no current requirement needs them and they would change existing prompts and failure behavior. Logical input classes describe provenance and authority only; they are not a required physical assembly order. Context budgets, compression thresholds, and reinjection of critical constraints after compression are deferred topics: they are not designed, implemented, accepted, or an open implementation task in this D2 round. Existing role inputs, client/provider limits, and error handling remain. No tokenizer, automatic trim, local overflow rejection, or reinjection flow is added. The active FR-03 research-stage program summary remains current and is not deferred.

Decision D-10d: observation failure is handled at the affected query, not as a global summary veto. A supplementary failure is disclosed only; a necessary item already projected as `unavailable` from its selected query mark makes basic completeness incomplete with that item's reason; only unlocatable/unrecordable observation loss sets the private tracking error, and only a missing/current snapshot or a snapshot-construction failure returns `None` to SB-01's existing missing/invalid-summary rule. SB-01 consumes only the provided summary and risk status; it does not read the registry, failure marks, or tracking error, re-aggregate queries, or change the formal rating from an observation event. No general permanent run state, automatic repair, retry, new exception framework, or new completeness/gate condition is added. Research still uses its fixed start-time summary; SB-01 uses its check-time summary, and the entry prepares the terminal report summary before return/save. Report writers do not obtain a new snapshot. If no valid summary exists, research stores `null` and its renderer emits the unavailable display text; SB-01 uses its missing/invalid rule, and the deterministic report/CLI area states that the program summary is unavailable without presenting a fourth completeness state.

Decision D-10e: `AvailabilitySummary` is one ordinary JSON-compatible mapping with five fields: `basic_completeness`, `applicability_note`, `observations`, `necessary_items`, and `supplementary_limitations`. The summarizer is the only producer and the only calculator of basic completeness. It receives `asset_type`, `enabled_analysts`, and the small existing `analysis_context` needed for matching as explicit arguments, reads a registry copy, applies query-level marks, selects the current decision update by existing match and acceptance order, builds necessary items and supplementary limitations, and returns a new mapping. The private tracking error is not a summary field; it makes the snapshot return `None`. `observations` carry one current projection per logical query with method, object, effective parameters, path identity, source, one of the four statuses, and a safe reason. Failure marks are projected into that shape as `unavailable` as a consumer view, not a fabricated stored `CompletedObservation`; they are not exposed as marks or a fifth status. `necessary_items` carry the fixed item id/method, object/range, status, and reason; `not_attempted` may appear only there when no completed result exists. Private pre-fetch call-failure notes (D-08d) surface only as a necessary item's `not_attempted` reason when no valid result exists, or as a `supplementary_limitations` entry; they never enter `observations` or produce a query key/sequence. No duplicate `missing_necessary_items` or second completeness field is stored; filtering non-available necessary items is only a view over the same list. Any `necessity_status` helper remains internal to the summarizer and is not a consumer step. Consumers read the mapping and do not rebuild completeness. At the same snapshot time they receive identical content; different times may differ. `None` means no valid current summary and is not a fourth completeness value. No independent schema file, version, hash, digest, or source proof is added.

Decision D-10f: report availability has two sources only. A run-in report uses one terminal summary prepared by the entry after graph execution, while this run's registry is still accessible, and placed in the report/final-state `data_availability_summary`; Markdown and HTML consume that same input. Post-run display of the just-finished analysis uses that prepared state; showing an already generated file uses that file's data. An independent `save_reports(final_state, ...)` after the run reads only that passed final_state's terminal `data_availability_summary`; it does not use another run's active context/registry, re-summarize, query, rerun SB-01, or reopen/update the ended manifest. Updating the delivery/display summary is a refresh only: SB-01 already used its check-time summary, and this update does not rerun SB-01 or change `gate_status`, top-level `reasons`, `final_rating`, or `final_trade_decision`; no digest/version/history/second-result binding is added. The writer does not look up `RunContext.current()`, registry, summarizer, graph last-run cache, research-stage summary, or model text. A null/missing/unusable summary is disclosed as “program summary unavailable” in the deterministic area, not replaced by a completeness value and not treated as a formal-result failure. A preparation failure only warns and leaves the field null/absent; it does not block report generation/save, change the formal result, or change the run outcome. `research_availability_summary` remains the fixed research-stage input; `data_availability_summary` is the delivery/terminal summary; no `report_availability_summary`, history, snapshot ID, version, hash, or persistent registry is added. Graph execution is complete before this preparation, no later data-fetch/background stage is added, and report-preparation time does not mean fetching newer market data.

Candidate concepts for risk input:

1. Derive the scenario from `--portfolio` or model text.
2. Add an optional structured `purchase_scenario` kwarg and CLI JSON file.
3. Add a new account/broker integration.

Analysis:

- Deriving from portfolio/model text violates FR-04's caller-supplied and no-fill rules.
- A structured optional input is minimal and testable.
- Broker integration is out of scope and would add account-truth claims.

Decision D-11: optional `purchase_scenario` kwarg and CLI `--purchase-scenario <json-file>`. An explicitly provided file that cannot be read or parsed is a caller parameter error; a not-provided file is distinct and its absence is passed to FR-04. After successful acquisition, business-invalid fields, object/ticker mismatch, and invalid explicit thresholds are FR-04 results, returning structured `blocked` for applicable Buy/Overweight rather than an entry hard failure. The evaluator receives the current analysis ticker explicitly and uses existing pure ticker normalization (`normalize_symbol`); no network identity lookup, global, report extraction, `PortfolioContext.average_price`, model text, or network fill.

The scenario contract is: ticker matching the analysis ticker; `portfolio_value` finite decimal > 0; `current_position_value` finite decimal in [0, portfolio_value]; `proposed_buy_value` finite decimal > 0; `entry_price` > 0; `stop_loss_price` > 0 and < entry_price; non-empty common currency label; `max_projected_weight` finite decimal in (0, 1]; `max_stop_distance` finite decimal in (0, 1). Booleans, NaN, Infinity, missing, and unparseable values are rejected. Ordinary decimal notation is accepted. Defaults 0.30/0.05 apply only when omitted; explicit invalid thresholds do not fall back. A mismatched ticker, each invalid field, or an invalid threshold produces `blocked` with the field/configuration category; no unhandled numeric error escapes. No cash, fee, slippage, liveness, account-truth, completeness, currency-conversion, or order-execution checks are added. No additional fields such as cash, quantity, valuation_price, valuation_time, candidate_id, order_count, or provenance are required; the structure remains one stock, one unlevered purchase/add-long.

Judgment order: legal rating → asset/rating applicability → scenario/threshold validation → legal metric calculation/comparison → structured result. Missing stock Buy/Overweight scenario is `blocked`; other legal non-applicable cases are `not_applicable`; missing/illegal rating is `blocked`; unexpected evaluator exception is `error`.

Decision D-12: FR-04 is a pure evaluator. It never changes the rating. Parse legal decimals, then convert exactly to an exact rational value (standard-library capability such as `fractions.Fraction`) and decide with exact arithmetic:
- `current_position_value + proposed_buy_value <= max_projected_weight * portfolio_value`
- `entry_price - stop_loss_price <= max_stop_distance * entry_price`

Exact rational arithmetic, not the ambient `Decimal` context, guarantees the cross-multiplication comparison under the contract's legal positive denominators. Do not globally change the Decimal context. Equality passes; both over-limit reasons are retained. Do not use float arithmetic or display rounding before judgment.

Input conversion boundary:
- JSON numeric tokens parse directly from the decimal token without a binary-float intermediate.
- Decimal strings parse through the same local numeric parser.
- `Decimal` is checked for finiteness and reuse the same parser.
- Integers are accepted exactly after excluding bool.
- A finite float is interpreted through its stable decimal string representation; no float arithmetic is used and precision already lost by the caller cannot be restored.
- Bool, NaN, and Infinity are rejected.
- Ordinary decimal notation is accepted without special length, trailing-zero, or canonical-grammar limits.
- The program interface supports ordinary numbers and decimal strings; this is not a promise of complete equivalence among arbitrary Python numeric objects.

Decision D-12a: the risk module has local responsibilities: parse and validate, decide, and generate one JSON-compatible result. These are not required to be separate classes, services, modules, or public APIs. Do not require all raw inputs to be first projected into a persistent normalized state and then parsed back; perform necessary conversion at the actual entry and risk-module boundary. If the scenario enters graph state, a simple JSON-compatible mapping is enough, not a normalized state protocol, representation version, digest, or round-trip proof. The result's metrics are decimal strings or null, and its `scenario`, `thresholds`, and `reasons` are display-safe values. The exact status is decided before result projection. `projected_weight` and `stop_distance` are computed separately; each is null only when its own operands cannot produce a legal metric, and an invalid ticker, currency, or threshold does not null a metric whose operands are legal. A repeating quotient is still computable and not null. A local formatting function may choose display precision; fixed decimal places, round-half-even, no-exponent notation, and trailing-zero rules are not architecture acceptance requirements or human-approval gates. Report/CLI display differences in layout or percentages are allowed, and character-for-character equality is not required.

FR-04 reasons remain inside `portfolio_risk_result.reasons`; SB-01 writes its own top-level `reasons` and does not flatten or reuse the risk object. The check covers only the amounts and prices explicitly supplied in the caller scenario; other model-proposal numbers are not compared or shown as verified, and do not create a new blocked condition or change the model conclusion. No scenario/threshold signature extension is added for the new flow. Do not use `json.dump(default=str)` or another implicit encoder for risk objects, uniformly convert to float, or re-decide risk from formatted percentages. The manifest does not add risk fields, and memory is not required to store risk metadata. The state log includes the checked risk result.

Remaining gap: security, history, and integration details.

### 3.5 Round 4 — Security, history, checkpoint, integration

Candidate concepts for security:

1. Generic secret scanning of all outputs.
2. Allowlist plus known-value sanitization in stated paths.
3. Immutable archive and transactional publication.

Analysis:

- Generic scanning exceeds SR-01, risks false positives, and cannot guarantee all channels.
- Allowlist plus known-value handling matches SR-01's explicit scope.
- Archive/transaction systems are explicitly out of scope.

Decision D-13: SR-01 limited-path sanitization and endpoint preference rule; SR-02 resolved-target path confinement. No generic scanner or archive.

Candidate concepts for history:

1. Manifest discovery with read-only list/get.
2. Separate index or database.
3. Regenerate reports on read.

Analysis:

- Manifest discovery is the required registration source and adds no index.
- A separate index adds synchronization and recovery scope.
- Regeneration violates FR-05's read-only rule.

Decision D-14: read-only `HistoryReader` over `<results_dir>/<run_id>/run_manifest.json` and the recorded report reference. Missing root is empty; unreadable root is an error; bad records are skipped with warnings.

Checkpoint analysis:

- The existing checkpoint storage, thread ID, run signature, success-cleanup tool, and tests remain outside the new flow. They are not removed or redesigned.
- The new CLI and `propagate()` flows do not use checkpoint resume. Each analysis creates a new `run_id`, new `RunContext`, and new initial state, then executes the whole graph.
- The new flow does not acquire a checkpoint session, use `invoke(None)` / `stream(None)`, read old checkpoint data as current evidence, or delete old checkpoint data.
- When `checkpoint_enabled` is set, both entries emit a safe no-resume notice; there is no confirmation prompt and no change to configuration/defaults.
- A failure follows FR-02 and is not automatically recovered or retried. A later invocation is a new analysis with a new run_id and re-executes model/data work.
- `finalization_contract` is removed from the current flow state/node contract because it existed only for checkpoint compatibility.
- Distinct from deferred FR-06: FR-06 concerns saved Markdown report-text recovery, not graph checkpoint resume.

Decision D-15: the new flow always executes fully and does not resume checkpoints. Retain the existing checkpoint code/tests without using them in this flow. Do not add signature digests, recovery positions, deterministic-tail re-entry, cross-process proof, or `finalization_contract`. Keep the recursion-limit reserve for the normal FR-04/SB-01 graph depth. If a future requirement asks for new-flow resume, reopen this ADR and define identity, observation inheritance, statistics, and formal-result semantics first.

Decision D-16: reserve post-analyst graph steps in the recursion-limit validation because two deterministic nodes are added.

Remaining gap: unverified assumptions and measurements.

---

## 4. Candidates considered

### 4.1 Candidate A — Entry-boundary RunFinalizer (withdrawn)

Strategy: graph ends at Portfolio Manager; each entry calls a shared finalizer that computes risk and the final decision.

Pros:

- Minimal graph change.
- Could share one component.

Cons:

- The selected decision for this ADR is a graph-internal check; candidate A is outside that selected placement. The ADR remains Proposed for human review.
- The graph can finish without the check if entry orchestration is skipped or ordering changes.
- Save/display and checkpoint boundaries add entry-level coordination.
- A and C overlap as boundary finalization; A need not create multiple authorities or mix cleanup.

Outcome: withdrawn by the reviewer and not selected.

### 4.2 Candidate B — Graph-internal final check plus RunContext (selected)

Strategy: deterministic post-PM nodes own the risk and final checks; a run-scoped context owns lifecycle and infrastructure.

Pros:

- It matches the selected graph-internal placement rather than a requirement-mandated architecture.
- Every normal graph completion reaches the check.
- Formal fields come from one node.
- Deterministic checks are testable pure functions.

Cons:

- Adds two graph nodes and changes Portfolio Manager output semantics.
- Checkpoint continuation is not supported; interrupted analyses re-execute model/data work and may cost more, so compatibility is limited.
- Availability must be snapshotted before the final check.

Outcome: selected.

### 4.3 Candidate C — Independent post-graph finalization service

Strategy: graph ends at PM; both entries call an external service that computes risk and final result.

Pros:

- Keeps graph unchanged.
- Service can be tested independently.

Cons:

- Semantically overlaps A: both are entry-boundary finalization; C only packages it as a separate service.
- Creates a second orchestration path outside the graph and can be skipped or called twice.
- Still needs the same availability snapshot and full-execution handling; the service boundary adds no requirement-driven capability.

Outcome: rejected.

### 4.4 Candidate D — Event-sourced run ledger

Strategy: emit events for analysis, data, risk, final check, and manifest; derive outputs from the ledger.

Pros:

- Strong audit trail in principle.

Cons:

- New persistence and replay model.
- Far beyond active requirements.
- Recovery/version/commit scope is explicitly out of scope.
- High migration and operational cost.

Outcome: rejected.

### 4.5 Candidate E — Display-only changes

Strategy: keep Portfolio Manager as the authority; add labels and warnings.

Pros:

- Smallest code change.

Cons:

- SB-01/INV-01 not satisfied.
- Model can remain the formal authority.
- No deterministic fail-closed path.

Outcome: rejected.

---

## 5. Comparison and rationale

Qualitative comparison; no numeric scores or performance measurements are invented.

| Criterion | A Entry finalizer | B Graph check | C Post-graph service | D Ledger | E Display only |
|---|---|---|---|---|---|
| Single normal-completion authority | Medium | High | Medium | High | Low |
| SB-01/INV-01 fit | Medium | High | Medium | High | Low |
| Checkpoint policy simplicity | Medium | High | Medium | Low | High |
| Minimal change to existing graph | High | Medium | High | Low | High |
| Testability offline | Medium | High | High | Low | Medium |
| Avoids new platform scope | High | High | High | Low | High |
| Preserves existing return shapes | High | High | High | Medium | High |
| Intermediate/formal separation | Medium | High | Medium | High | Low |

A and C can each use one finalizer/service as a single authority; D1/D2 do not by themselves distinguish them from B. RunContext, the per-run stats handler, and query reuse are usable by A/C too, so they are not counted as B-only advantages. The practical distinction is placement and orchestration: B is inside the selected graph completion path, while A/C are entry-boundary paths that overlap each other.

Rationale for B:

- It matches the selected graph-internal decision; the requirement does not itself mandate this placement and no additional approval is claimed.
- It gives one formal-field writer on every normal graph completion.
- It keeps pure checks independent from entries and persistence.
- It retains existing checkpoint code/tests outside the flow but does not support new-flow checkpoint continuation; interrupted runs re-execute work.
- It preserves entry return shapes and the existing report/memory surfaces, while the graph and Portfolio Manager output contract change.

---

## 6. Selected architecture details

### 6.1 Graph nodes and contracts

| Node | Type | Inputs | Outputs |
|---|---|---|---|
| Research-entry wrapper | Wrapper around the first Bull call; not a top-level node | Analyst-join state, asset type, enabled analysts, existing analysis context, current summary | `research_availability_summary` (plain mapping or `null`) and the same first Bull result |
| Portfolio Manager | Existing model node | Existing debate/plans/context | `model_proposal` only: nested `{rating, text}` or `null`, inner values may be `null` |
| Portfolio Risk Check | New deterministic node | `model_proposal`, `purchase_scenario`, thresholds, asset type, explicit analysis ticker | `data_availability_summary`, `portfolio_risk_result` (one JSON-compatible result with decimal-string/null metrics and risk-scoped `reasons`) |
| Final Recommendation Check | New deterministic node | `model_proposal`, availability snapshot, risk result, asset type | `gate_status`, top-level `reasons`, `final_rating`, `final_trade_decision` |

The research-entry wrapper runs after analyst join and before the first Bull call. It obtains one summary from the summarizer using existing context, renders a labeled program block with a small deterministic function (or the unavailable display text when the summary is `null`), injects that block into the same first Bull invocation, and returns the plain mapping or `null`; it does not add a node, data request, model call, compression, truncation, or registry exposure. Later Bull/Bear rounds and the Research Manager read the same stage summary directly. Blueprint §8.1 is the authoritative table of the 15 observation attachment points; this ADR does not add a second adapter layer.

The Portfolio Manager's free-text fallback may be used to extract the proposal rating, but no consumer re-parses that text into a formal rating. The risk node writes only the risk result; its `reasons` list stays inside that object. The final check writes the top-level `reasons` and never copies or flattens the risk object into the formal fields.

The deterministic CLI and report risk area displays the safe scenario, thresholds actually used, metrics, status, and reasons. It states: “Only the listed caller scenario is checked; other amounts and prices in the model proposal are not verified by this check.” It also retains the classroom-demonstration and non-trade-authorization statements. No consumer extracts model numbers, compares them with the scenario, or adds a blocked condition for a different model suggestion.

The risk node calls `AvailabilitySummarizer.snapshot(asset_type, enabled_analysts, analysis_context)` and `PortfolioRiskEvaluator.evaluate()` as independent functions. The summary is plumbing and has no approval authority. This keeps the fixed PM → FR-04 → SB-01 sequence and gives SB-01 a serializable input.

These components are logical responsibilities, not a requirement for one class, module, service, or file per row. Prefer small functions: a research-entry wrapper, a shared pure formal-result validator, risk parsing/comparison/projection helpers in the risk module, registry collections and summary functions in one availability module, and small security helpers at the actual paths. Do not add a general registry, plugin framework, event bus, or universal service.

### 6.2 Checkpoint policy for the new flow

The existing checkpoint implementation, thread IDs, run signature, cleanup tools, and tests remain in the codebase. They are not changed by this ADR.

The new flow does not use them for resume:

- Each analysis creates a fresh ephemeral RunContext and initial state; no new persisted run_id is required.
- The graph runs fully from its normal entry point; no `None` input resumes a saved schedule.
- The new flow does not acquire a checkpoint session, read old checkpoint data as current evidence, or delete old checkpoint data.
- When `checkpoint_enabled` is set, both entries emit a safe notice that this flow runs fully and does not resume. There is no confirmation prompt and no configuration/default change.
- Existing checkpoint data remains untouched and is not used for the current formal result, statistics, availability, or risk.

Normal order: validation → new RunContext → new initial state → full graph → FR-04 → SB-01 → unified output → existing save flow → entry-owned cleanup → restore scope.

Failure follows FR-02 and is not automatically recovered or retried. A later invocation is a new analysis and may repeat model/data calls; time and cost may increase. No performance or cost benefit is claimed.

`finalization_contract` is not part of the current flow state or node contract because it existed only for checkpoint compatibility. `FormalResultContract` and the single formal-result authority are unchanged.

The recursion-limit reserve for the normal FR-04/SB-01 graph depth is still required. This checkpoint limit is distinct from deferred FR-06 Markdown report-text recovery. A future requirement for new-flow resume requires reopening the ADR to define analysis identity, observation inheritance, statistics, and formal-result semantics.

### 6.3 Run lifecycle

Current scope binds one ephemeral C-03 context for reuse/availability after effective config/basic validation and before the first supported data call; no pre-construction binding is required. Explicit delegation shares scope and independent invocations isolate it. Entry-owned cleanup restores binding and preserves the original error. Existing state save, optional report save and conditional memory append retain their ordering and failure behavior. No current manifest, precise statistics, persistent run identity/status or history is required; those previous details are future-only in the archive. The sole SB-01 formal authority and full new-flow execution remain.

### 6.4 Failure semantics

Use the current runtime policy catalog: ordinary C-08/C-09 business failures produce their specified blocked/error results; missing/invalid formal output at a consumer is an execution contract failure. Setup/graph/state-save/new-memory/requested-report errors retain their existing exception/display behavior. State-save failure prevents later new-memory append; a later failure does not roll back saved files or rewrite formal values. Independent saves consume passed state and create no scope. Acquiring owners clean once, preserve primary errors and restore prior binding. No new manifest, persisted outcome/status, counters or timing step is required.

### 6.5 Formal result contract

SB-01 must return the same five top-level fields on every normal branch:

| Field | Type and rule |
|---|---|
| `model_proposal` | Nested `{rating, text}` or `null`; each inner value may be `null`; no `present` boolean |
| `gate_status` | `passed`, `blocked`, or `error` |
| `reasons` | Top-level SB-01 string list; passed may be empty; blocked/error has at least one actual reason; no reason codes or priority system |
| `final_rating` | Five-tier legal rating on passed; REVIEW on blocked/error |
| `final_trade_decision` | Non-whitespace formal conclusion; program-generated manual-review notice on blocked/error |

Branches:

| Branch | Result |
|---|---|
| Passed | Original model rating and conclusion retained; `reasons` may be empty |
| Missing/invalid input or condition failure, including a missing, wrong-type, empty-string, or whitespace-only conclusion | `blocked`; REVIEW; program-generated manual-review notice; actual top-level reasons |
| Handled internal exception | `error`; REVIEW; program-generated manual-review notice; actual safe top-level reason |

A missing or invalid formal output after the graph, or a result lost in transfer or merge, is an execution contract failure. It is not a business REVIEW. The shared `FormalResultContract` validates:

- all five required top-level fields exist and have the stated types;
- `model_proposal` is a nested `{rating, text}` object or `null`, with no `present` field; an illegal proposal rating is not a contract failure because SB-01 handles it;
- `gate_status` is in the legal set and `final_rating` is in the legal formal set;
- passed has a five-tier formal rating and blocked/error has REVIEW;
- `final_trade_decision` is a non-whitespace string;
- `reasons` is a list of strings, and blocked/error contains at least one actual reason.

It returns the result unchanged or reports the contract failure. It does not recheck data, recompute risk, call a model/data source, parse model text, repair the result, or create a second business status. Risk reasons remain in `portfolio_risk_result.reasons`; top-level `reasons` is not a copy or flattening of that object. An execution diagnostic such as “Final result was not produced” is not a manual-review notice and is never written into `final_trade_decision`. No signature, hash, source proof, persistent diagnostic system, complex state machine, or new module/public API is added.

Invocation:

- Both entries validate after graph execution and before normal final saving and successful return, especially before `record_decision()`.
- The validated formal rating and decision are passed explicitly to `record_decision()`, the report writer, and the CLI formal area; these consumers do not use the `run_rating()` text fallback or re-parse the body. The new flow does not call `run_rating()`; the existing helper may remain for older callers.
- CLI formal streaming regions accept only complete SB-01 output; partial chunks are not promoted. The final merged state is validated after graph completion.
- `propagate()` preserves `(final_state, signal)`. A contract failure takes an execution error path; it never returns a fabricated `(final_state, REVIEW)`. No specific exception class is prescribed.
- CLI reports that the formal result was not formed, does not claim normal completion, and does not present the execution diagnostic as a formal REVIEW. Existing error display and exit style are reused.
- A normal final report requires a complete formal result. An independent public report-save entry may reuse the same contract. Without a complete result, it writes no new normal report and no new memory decision, and no failed snapshot file. Existing intermediate material is kept; unrelated outputs are not rolled back. This is not a cross-file all-or-nothing rule.
- A contract failure preserves the original execution-error path; no consumer-generated REVIEW, normal delivery or manifest attempt.
- A contract error found in an independent post-run save fails that save and does not reopen or rewrite the ended run.

Checkpoint interaction:

- The new flow does not resume checkpoints. Every analysis reaches FR-04 and SB-01 from a new RunContext and initial state.
- Insufficient current inputs at SB-01 produce a complete blocked/REVIEW.
- Incomplete formal output is an execution contract failure; consumers do not generate REVIEW or use old checkpoint material.

---

### 6.6 Persistence and recovery-path classification

Current scope binds one ephemeral C-03 context for reuse/availability after effective config/basic validation and before the first supported data call; no pre-construction binding is required. Explicit delegation shares scope and independent invocations isolate it. Entry-owned cleanup restores binding and preserves the original error. Existing state save, optional report save and conditional memory append retain their ordering and failure behavior. No current manifest, precise statistics, persistent run identity/status or history is required; those previous details are future-only in the archive. The sole SB-01 formal authority and full new-flow execution remain.

### 6.7 Resource ownership and cleanup coordination

Each acquiring owner releases its resources exactly once. Entry cleanup preserves the primary execution/save exception and attempts remaining cleanup. IF-02 finish only restores context binding after cleanup; it does not receive a persisted outcome, collect statistics, close resources again or write a manifest. Retain existing stream/client failure behavior.

## 7. AI context design

This section is an architecture policy, not an approved performance target. Existing role prompts, prompt assembly paths, and output shapes remain. The selected design adds only the FR-03 research-stage summary required by the active requirements. It does not introduce a unified context framework.

The local approach is selected because the active requirements add one specific context obligation, not a general context-management capability. Existing roles already consume different inputs through different mechanisms, including message/tool history, prefetched blocks, inline debate strings, and structured-output prompts. A cross-role framework would add abstraction, token handling, trimming, and role-failure behavior without a requirement, while increasing the risk of dropping reports, plan text, or evidence. The local wrapper is testable against FR-03 and leaves unrelated prompts and failure behavior unchanged.

### 7.1 Logical input classes, not a physical assembly order

The following classes describe where a role's inputs come from and how much authority they carry. They are descriptive categories, not layer objects, an L1–L6 sequence, or a shared assembler. A class that a role does not have is not applicable and receives no placeholder.

| Logical class | Meaning | Authority | Current treatment |
|---|---|---|---|
| Identity | Instrument and run identity already provided by existing code | Program-provided | Inline context or state field, per role |
| Role constraints | No trade execution; role boundary; PM proposal is advisory; FR-04/SB-01 authority; output language; required output shape | Program-provided | Existing role prompt text |
| Retrieved evidence | Analyst reports, analyst-prefetched source blocks, and the FR-03 research-stage summary | Program/vendor or prior model output; structured program fields cannot be overridden by model text | Existing prompt text; summary only for the research stage |
| Run history | Memory lessons and research/trader/risk debate history | Prior model/program output; advisory | Existing history fields |
| Current task | The role instruction, current question, and debate round | Program-provided | Existing prompt text |

Actual code has different assembly paths: the tool-using analysts combine a system message with `MessagesPlaceholder` and tool-call history; the sentiment analyst prefetches source blocks into a system message; Bull/Bear and risk debaters build inline strings; Trader uses a message list; managers use structured output with a free-text fallback. The design preserves those paths and does not normalize them.

### 7.2 Role-specific input mapping

| Role | Existing inputs retained | FR-03 stage summary | Authority boundary |
|---|---|---|---|
| Market, News, Fundamentals analysts | Instrument context, role prompt, message/tool history and tool results | No | Analyst reports remain model evidence, not formal authority |
| Sentiment analyst | Instrument context, role prompt, prefetched news/StockTwits/Reddit blocks, message history, structured output/fallback | No | Prefetched blocks are evidence, not an availability authority |
| Bull and Bear Researchers | Instrument context; the four full analyst reports through existing missing-report handling; debate history; latest opponent argument | Yes, same research-start snapshot | Debate text is advisory; program summary is a separate program block |
| Research Manager | Instrument context; full debate history | Yes, same research-start snapshot | Produces a research plan, not a formal rating |
| Trader | Instrument context, portfolio context, investment plan, optional market report | No | Produces a transaction plan, not a formal rating |
| Aggressive, Conservative, Neutral analysts | Instrument context, portfolio context, full analyst reports, Trader plan, risk debate history and latest opponent responses | No; deferred FR-07 is not active | Debate text is advisory |
| Portfolio Manager | Instrument context, portfolio context, Research Manager plan, Trader plan, existing memory lessons, risk debate history | No; the final check consumes the program summary separately | Produces `model_proposal`; SB-01 alone produces formal fields |

The four full analyst reports remain intact for research and risk roles. Only the deferred FR-07 design would replace them with briefs; that replacement is not part of this design. The FR-03 program summary is additive only for the three research-stage roles and does not replace an analyst report.

### 7.3 FR-03 research-stage summary injection

Research start is the analyst join immediately before the first Bull call. A small deterministic rendering function turns the current-run availability snapshot into a clearly labeled program block. The wrapper:

1. takes the snapshot before the first Bull call;
2. renders the program block without a model call, query, compression, or truncation;
3. passes the rendered block directly into the same first Bull invocation;
4. stores the same stage summary as `research_availability_summary`.

Returning a state update alone is insufficient because the first call cannot read an update that has not merged. Later Bull/Bear rounds and the Research Manager consume `research_availability_summary` from graph state, so all research-stage roles use one stage snapshot. Later observations do not refresh or rewrite it and do not re-run research.

The final check and report use their own snapshots at their own times. The program summary is kept separate from model-generated analysis: model text cannot rewrite the structured availability state or the deterministic program block, and FR-04/SB-01 do not treat that text as a substitute for program results. The design does not ask a model to re-judge the deterministic FR-04/SB-01 result, and no prompt is used to establish formal authority.

### 7.4 Portfolio Manager prompt responsibility

The Portfolio Manager prompt is adjusted only where it describes the output's authority. It now asks for a model proposal for the deterministic final check, not a final formal decision. The existing evidence requirements, rating scale, investment thesis, structured `PortfolioDecision` path, and free-text fallback remain. The prompt keeps the distinction between the original proposal and the formal result; the implementation does not rely on prompt wording or a check for prompt presence to establish SB-01 authority.

### 7.5 Deliberately omitted mechanisms and known limit

The current design does not add:

- a unified context assembler or shared layer objects;
- cross-role prompt normalization or exact/near-duplicate removal;
- quick/deep input budgets, a global input cap, or cross-provider token counting;
- automatic history trimming, report compression, or summary generation;
- mandatory-block reinjection retries, local overflow rejection, or a new role-failure mechanism.

Existing request assembly, client configuration, and provider limits remain in use. The existing `max_tokens`-style setting is an output-token control where supported, not an application-level input budget. There is no claim that arbitrary request lengths succeed. Context budgets, compression thresholds and constraint reinjection remain an unresolved course-D2 alignment question under D-10c. They are outside this maintenance scope; this revision neither implements them nor establishes full course compliance. FR-03 research-stage summary remains active and is not part of that deferral; FR-10 adds only ADR 002's bounded Fundamentals Analyst pre-model financial metrics table when enabled.

FR-07 briefs and CR-01 cost comparison remain deferred; no short summaries, full-report replacement, token/cost comparison, or optimization acceptance is added.

---

## 8. Consequences

### Positive

- One formal-result authority across both entries.
- Deterministic, offline-testable checks separated from model output.
- Explicit intermediate/formal separation for audit.
- Ephemeral run ownership isolates reuse/availability without new persistent lifecycle infrastructure.
- Data reuse and availability are run-scoped and isolated.
- History and security remain limited and testable.
- Existing graph, vendors, reports, and memory remain in use; checkpoint code/tests remain in the repository outside the new flow.
- Missing or invalid formal output is separated from business REVIEW: it is an execution contract failure, not a fabricated check result.
- The formal result has one five-field shape, and risk reasons stay in the risk object while SB-01 reasons use the top-level list.
- Existing save errors preserve their original behavior and do not rewrite the formal result; manifest work is deferred.
- The reusable graph/model object is separated from per-analysis identity, collector, and reuse state.
- Each resource has one release owner; `RunContext.finish()` restores binding after entry-owned cleanup attempts.
- FR-04 has a complete field/threshold contract and exact rational comparisons; FR-03 has a verified per-method branch table instead of a generic non-empty check.
- Research-start availability enters the first Bull call through a wrapper, and query completion is separated from path association.
- FR-04 uses exact rational decisions and one JSON-compatible result with decimal-string/null metrics; display formatting is local and occurs only after the status is fixed.
- Observation handling is isolated from fetch outcomes, and recordable failures affect the relevant query rather than creating a general permanent veto. Unlocatable/unrecordable observation loss becomes an explicit private tracking error, so later snapshots cannot silently return old success.
- Each of the 15 paths has one curated observation site; the shared news executor covers P-09/P-13 without router/vendor duplication, and each split indicator is observed separately.
- Pre-fetch parameter/date rejection is disclosed from a private safe note without fabricating a query, sequence, FR-01 entry, or tracking error.
- Context delivery is a narrow role-local increment: existing prompts and assembly paths remain, and only the research stage receives the required FR-03 program summary.
- Run-in reports use one prepared terminal summary from the current registry; independent saves use only the passed final_state and never another run's context/registry.

### Negative

- Portfolio Manager output semantics change; existing tests and consumers must be updated.
- Two graph nodes add depth; the new flow fully re-executes after interruption.
- Availability must be snapshotted into graph state for a pure final check.
- CLI save/display flow must be split.
- Long histories or large reports may exceed a provider's context limit; no application-level input budget, automatic trimming, or compression is added, and arbitrary request lengths are not promised.
- Interrupted analyses repeat model and data calls because this flow does not resume; time and cost may increase.
- If an observation is unlocatable or cannot be locally marked, the private tracking error makes subsequent availability snapshots unavailable for the rest of that run; this is intentional and not auto-recovered.
- Entry adapters, the report writer, and the memory adapter must handle contract failure as an execution error rather than substituting REVIEW.
- Existing report, final-state and new-memory failure policies remain distinct; none becomes best-effort merely because manifest work was deferred.
- CLI construction time and program idle time have different inclusion boundaries; the design does not support a direct performance comparison between entries.
- Execution-config callback propagation through every nested/parallel boundary remains unverified; the design does not claim automatic framework propagation.
- Cleanup coverage and primary-versus-cleanup error ordering require implementation verification; the new flow acquires no checkpoint session.
- Some FR-03 producer branches (Alpha Vantage empty JSON payloads and header-only/empty feed shapes) are not fixture-verified; they remain conservative until confirmed. New FR-03 recognition checks and FR-04 boundary checks are planned, not executed.

### Neutral

- Existing report layout is retained; same-path overwrite semantics remain.
- Memory format is retained.
- Vendor fallback/retry/withholding behavior is unchanged.
- Deferred requirements remain inactive.

---

## 9. Re-open conditions

Re-open this ADR if:

- The final authority moves outside the graph or the requirement changes the entry-point set.
- A new supported data path changes the 15-position scope, its actual call location, or its existing semantics/default parameter handling.
- A future requirement asks the new flow to resume interrupted analyses.
- Resource cleanup ownership or primary-error precedence becomes ambiguous.
- Stats-handler construction, execution-config injection, call-ID/usage rules, or reflection attribution changes.
- The top-level formal field set, proposal shape, or reason ownership changes.
- FR-03 producer formats or FR-04 field/threshold semantics change.
- Research-stage summary attachment or path-association semantics change.
- A requirement adds a unified context assembler, cross-role normalization, input budgets, automatic trimming/compression, or different role input obligations.
- A future decision approves context compression; its design must preserve role tasks, required evidence, and trusted FR-03 program facts.
- The FR-04 input boundary, result representation, or scenario-versus-model-proposal scope changes.
- Acceptance-order semantics, pre-fetch call-failure note behavior, query-level observation-failure isolation, failure-marker semantics, `availability_tracking_error` triggers/lifecycle, snapshot-construction failure handling, the `AvailabilitySummary` field contract, report availability ownership/preparation timing, or minimum available-content rules change.
- A consumer cannot distinguish a business REVIEW from an execution contract failure without preserving the shared contract boundary.
- The CLI save/display split conflicts with an approved interaction requirement.
- A security scope expands beyond SR-01/SR-02.
- FR-06, FR-07, PR-01, or CR-01 is activated.
- Measurements show the graph depth is unworkable.
- The reviewer rejects the graph-internal final check.

---

## 10. Open questions and pending approvals

| ID | Question | Current proposal | Needed decision |
|---|---|---|---|
| OQ-01 | Purchase-scenario CLI/file shape | `--purchase-scenario <json-file>`; optional kwarg | Confirm before entry implementation: parameter/input form plus file read/parse error contract |
| OQ-02 | Threshold key names | `max_projected_weight`, `max_stop_distance` | Decided for these two key names only by the current user instruction; no other configuration mechanism is approved |
| OQ-04 | CLI save/display boundary | Save in run; display/browser after terminal attempt | Confirm before CLI entry implementation; not approved by this document |
| OQ-07 | Coding-agent roles/whitelists | Four-role proposal; design is in `docs/architecture/permission-model.md` | Confirm and implement in D3-stage permission work |
| OQ-08 | Recursion-limit reservation | Reserve at least four post-analyst steps | Pending technical verification by an actual normal path; the four-step figure is not acceptance |
| OQ-16 | Execution-config callback propagation | Verify one per-analysis handler reaches model/tool calls in analyst subgraphs, parallel nodes, structured-output runnables, and graph-internal reflection; if a boundary does not inherit, pass the same execution config locally; call-ID/usage extraction details remain pending | Pending offline integration verification; local same-config handoff only |
| OQ-12 | Unverified FR-03 producer branches | Confirm Alpha Vantage empty JSON/feed and header-only CSV shapes with finite sourced samples and cover every blueprint §8.3 row; unrecognized formats remain `unavailable` until confirmed | Pending verification; keep conservative behavior, no generic recognizer or network probe |
| OQ-13 | Shared news executor and path identity integration | Confirm the plain internal news executor call from the News tool (P-09) and sentiment prefetch (P-13), explicit path argument, and first-Bull wrapper mechanism without a framework API claim | Pending offline integration verification within the existing scope |
| OQ-15 | Observation ordering, pre-fetch parameter failures, tracking error, AvailabilitySummary, and report source | Verify acceptance-order updates, shared observation/mark sequence, later-accepted replacement, pre-fetch note projection without fake queries, local fallback plus tracking-error behavior, snapshot-construction versus observation-loss distinction, new-run isolation, shared publication, summary/report contracts, and P-02/P-04/P-09/P-10 minimum available-content fixtures | Pending verification under the existing contract; no new state, recovery, or global veto |

No item above is an approved requirement change.

---

## 11. References

- `docs/req/requirements.yaml` — current requirements.
- `docs/req/req-schema.json` — structural schema.
- `architecture-blueprint.md` — main architecture constraints.
- `docs/architecture/evaluation-table.md` — candidate comparison.
- Existing source paths cited in Section 1.1.
- `baseline/runs/baseline-20261020-01` — old behavior baseline only.

## Deferred and historical design archive — not current implementation instructions

The material below preserves prior design rationale/details and identifiers. Any mandatory wording here applies only if the deferred scope is explicitly reactivated and reviewed. It is not a current task, monitor, acceptance condition or permission grant. Historical mixed clauses are superseded by the current sections above.

### 6.3 Run lifecycle

CLI boundary:

1. Parameter selection, configuration resolution, and basic validation. If `checkpoint_enabled` is set, emit a no-resume notice; do not change configuration/defaults.
2. Create `RunContext`, record start clocks, create this analysis's stats handler/collector, and attempt running manifest with the shared config projection.
3. Construct the graph object, initialize clients, perform the initial workflow compile, and prepare per-run state and output paths. Do not pass this analysis's stats handler to model constructors. No checkpoint session is acquired. This is inside the run and elapsed time.
4. A construction/client/compile/preparation failure is a post-start execution failure; preserve the original error and attempt a failed manifest.
5. Execute the graph with the handler in this execution's `callbacks` config; validate the formal result; prepare one terminal availability summary from this run's registry into the report/final-state mapping; then perform the existing final-state JSON save and new-memory append; then the CLI report save if requested from that prepared state. An earlier write failure prevents later writes in the existing order.
6. `completed` only when execution succeeded, any requested report save succeeded or was not requested, and required final-state/new-memory writes succeeded or no new memory append was required.
7. `failed` on execution error, final-state JSON failure, new-memory append failure, requested report save failure, or formal result contract failure. Manifest failure does not change the outcome.
8. Entry execution scope performs necessary cleanup attempts (outer stream, `stream_run`), summarizes the outcome, then calls `RunContext.finish()` to record end time, stats snapshot, and terminal manifest; restore the prior context binding before post-run display/browser.

Program boundary:

1. Start from an existing graph object. Its construction, client initialization, initial compile, and idle time are outside the run.
2. Invoke `propagate()`; perform per-call validation and effective-config resolution. If `checkpoint_enabled` is set, emit a no-resume notice; do not change configuration/defaults.
3. Create a new `RunContext`, record start clocks, attempt running manifest, create this analysis's stats handler/collector, and initialize reuse state.
4. Build initial state. Initial workflow compile is pre-existing; no checkpoint is acquired or recompiled, and the stats handler is not bound to model constructors.
5. Execute graph with the handler in this execution's `callbacks` config, validate the formal result, prepare the terminal availability summary from this run's registry into `final_state`, save existing state/memory, exit the execution scope, summarize the outcome, call `RunContext.finish()` for end time/stats/terminal manifest, then restore the prior context binding.
6. Return formal fields and the final_state carrying the terminal delivery summary; no forced save. Each independent call gets a new RunContext, run_id, stats handler/collector, and reuse state. Object construction failure before `propagate()` creates no run or manifest.

Explicit internal delegation within one analysis may share the active RunContext. Independent `propagate()` calls, other objects, or other tickers do not merge merely because a context variable is set. Exiting the context restores the previous binding. No concurrent same-graph promise is added.



### 6.6 Persistence and recovery-path classification

| Path | Required behavior |
|---|---|
| Manifest directory creation, serialization, and write | Safe warning only; does not change run outcome or formal result |
| Final-state JSON save | Preserve existing exception propagation; `failed` run and best-effort failed manifest attempt |
| New memory decision append | Preserve existing exception propagation; `failed` run; no replacement record or rewritten recommendation |
| Memory disabled or existing same-day record causes no new append | Not a save failure; do not force a record or mark the run failed |
| Historical settlement/reflection or memory-read failures already handled by `_memory_step()` | Preserve existing degradation and notes; do not promote to run failure |
| CLI report save requested during this operation | Preserve existing exception capture and error display; report the internal save outcome to the lifecycle and mark the run `failed` |
| User declines report save | `not_requested`, not failed; `completed` if other required work succeeds |
| Independent `save_reports()` after `propagate()` returns | Preserve that save operation’s failure behavior; do not reopen or modify the completed run manifest |

Additional rules:

- The formal result is unchanged by any persistence failure; the run outcome, control flow, and each artifact persistence outcome remain separate.
- Not every optional artifact must exist for a `completed` run: an unrequested report and a memory disabled/same-day no-op are not failures. The table applies to requested or required writes that actually fail.
- A partial report save is `failed` as a whole while confirmed Markdown may be recorded; no HTML success is fabricated and no successful file is rolled back.
- A failed manifest containing a report reference is not eligible for the FR-05 `completed` history list.
- The existing `record_decision()` no-decision branch is not a normal path after formal-result contract validation; a missing formal result is an execution contract failure, not a silent memory no-op success.
- No publication transaction, cross-file atomicity, rollback, automatic repair, or recovery protocol is added.


### 6.7 Resource ownership and cleanup coordination

| Resource | Owner and responsibility |
|---|---|
| Outer streaming session | CLI or debug streaming caller; ensure exhaustion or explicit termination |
| Underlying graph stream | `stream_run()`; close in its own `finally` |
| Existing checkpoint code (not used by the new flow) | Existing implementation/tests own their behavior; the new flow does not acquire, release, or delete checkpoint resources |
| Persisted checkpoint data | Left untouched by the new flow; never used as current evidence |
| RunContext binding | Scope that created it; restore the previous binding on exit |
| Reusable graph and model clients | Object/caller lifecycle; not destroyed by each run finish |
| Output file handles | Local save-function scopes |

Rules:

- The entry/execution scope ensures necessary cleanup attempts, coordinates order, and summarizes the outcome.
- Resource wrappers release only resources they created.
- `RunContext.finish()` receives the summarized outcome after cleanup attempts and records end time, stats snapshot, and terminal manifest. It does not close streams, acquire or release a checkpoint session, delete checkpoint data, close clients, or repeat a close.
- Normal order: graph execution and formal result → requested save attempt → necessary cleanup attempts → summarized outcome → `finish()` → restore context binding → return/post-run browsing.
- Resources may be released earlier once no longer used; do not hold an exhausted stream until report saving.
- End clock and stats snapshot occur after necessary cleanup attempts.
- Manifest failure does not re-trigger cleanup and does not block context-binding restoration.
- Partial initialization: acquisition scope starts at the attempt; an acquired resource is released if later setup/use fails; resources not yet acquired are not treated as open; `finish()` is not a leak fallback.
- Cleanup failure: a primary execution/save error wins; without a primary error, cleanup follows existing error style and is not `completed`; one close failure does not prevent other cleanup attempts; manifest errors remain warnings; no infinite retry, fabricated success, or persistent diagnostic system.
- Existing checkpoint data is not acquired, read, or deleted by the new flow; the existing cleanup tool remains outside this flow.

---
