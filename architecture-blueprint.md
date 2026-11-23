# D2 Architecture Blueprint — Graph-Internal Final Check with Run-Scoped Governance

> Current scope amendment — 2026-11-23, D1 v1.49.0: six active requirements / 27 FCs (FR-01, FR-03, FR-04, SB-01, INV-01, SR-01); seven deferred / 28 FCs (FR-02, FR-05, SR-02, FR-06, FR-07, PR-01, CR-01); total 13 / 55. Pre-approved in [PR #12 comment 7089283044](https://github.com/Howindy/Teamproject-Tradingagents/pull/12#issuecomment-7089283044), binding frozen specification cc2c834c3ce9097f08d95b4beef1a5dc1bb0b7e9. This is scoped design/test pre-approval, not final review or product acceptance. Native manifest, new precise statistics, history and their dedicated path controls are future-only. Existing baseline statistics, saves and protections remain.


- Status: Proposed for human review
- Date: 2026-11-17
- Requirements baseline: `docs/req/requirements.yaml` (document version 1.49.0, 13 requirements, 55 fit criteria)
- Code baseline: `src/` imported from TradingAgents v0.7.0 (`UPSTREAM.md`)
- Module-path note: references such as `cli/run.py` and `tradingagents/graph/setup.py` are relative to the application source root; the current paths are `src/cli/run.py` and `src/tradingagents/graph/setup.py`.
- Runtime evidence baseline: `baseline/runs/baseline-20261020-01` (existing behavior only; not new-requirement acceptance)
- Related artifacts:
  - [ADR 001 — Graph-Internal Final Check with Run-Scoped Governance Context](docs/architecture/adr/001-graph-internal-final-check.md)
  - [Evaluation Table](docs/architecture/evaluation-table.md)
  - [`Invariants`](docs/architecture/invariants.md)
  - [`Memory and State Design`](docs/architecture/memory-design.md)
  - [`Runtime Policy Catalog`](docs/architecture/runtime-policy-catalog.md)
  - [`Trace Matrix`](docs/architecture/trace-matrix.md)
  - [`Permission Model`](docs/architecture/permission-model.md)

This blueprint is the main constraint document for implementation planning. It contains architecture decisions and interfaces, not application implementation, test results, measurements, or acceptance claims. A statement marked `[Planned]` is not evidence that the behavior exists.

Implementation-evidence clarification (2026-11-22): the C-08/FR-04 and C-09/IF-09 independent cores exist and were merged through their separate reviewed PRs; the C-09 core covers only SB-01-FC01–FC04 and local IR-01/IR-02 responsibility. This does not change the blueprint's overall `Proposed` status or approve production graph/entry/report/state/memory integration, IF-19, the FR-03 producer, full SB-01, or global invariants.

---

## 1. Purpose, scope, and authority

### 1.1 Purpose

Extend the existing graph with query reuse, program-produced availability, deterministic purchase risk and final checks, consistent delivery and limited credential protection. Retain the existing agents, vendors, CLI, reports, memory and baseline statistics. RunContext owns ephemeral per-analysis reuse and availability state; it adds no current persistent run identity, timer, status machine, statistics collector, manifest or historical lookup.

### 1.2 Requirement inventory used by this design

Independent count from `docs/req/requirements.yaml`:

| Scope | Requirements | Fit criteria |
|---|---|---|
| Active | 6: FR-01, FR-03, FR-04, SB-01, INV-01, SR-01 | 27 |
| Deferred | 7: FR-02, FR-05, SR-02, FR-06, FR-07, PR-01, CR-01 | 28 |
| Total | 13 | 55 |

The count matches the expected 13 requirements / 55 fit criteria / 6 active / 27 active fit criteria / 7 deferred / 28 deferred fit criteria. The five scoped FC wording amendments are recorded in D1 and the frozen PR #12 specification.

### 1.3 Evidence rules

| Label | Meaning |
|---|---|
| `[Requirement]` | Stated by the current requirement object or fit criterion. |
| `[Static code]` | Observed by reading the current repository; no execution. |
| `[Existing test]` | A test file exists under `test/`; it is not claimed to pass for new behavior. |
| `[Baseline]` | Recorded in `baseline/`; describes the old behavior, not new acceptance. |
| `[Planned]` | A design-time verification plan; not executed. |
| `[Not measured]` | No measurement exists. |

Historical D2 drafts in git history are not evidence. They were based on requirements that included now-deleted or now-deferred scope and were removed from the working tree. This design does not restore that scope.

### 1.4 Non-goals

- No new model or data-vendor calls for governance checks.
- No trade execution, broker integration, or order placement.
- No replacement of the LangGraph agent graph with a service-oriented or event-sourced platform.
- No generic secret scanner, immutable archive, cross-file transaction, rollback system, recovery scheduler, history index, or background repair service.
- No unified context assembler, cross-role prompt normalization, input-token budget, automatic history trimming/compression, or new role-failure mechanism.
- No implementation or activation of FR-06, FR-07, PR-01, or CR-01.
- No modification of `docs/req/**` or governance configuration in this design task.

---

## 2. Existing system and constraints

### 2.1 Current runtime paths

**CLI path** `[Static code]`

`cli/main.py:37` → `cli/run.py:99` `run_analysis()`:

1. Collect selections and build configuration (`cli/run.py:111`).
2. Create `StatsCallbackHandler` and `TradingAgentsGraph` (`cli/run.py:115-128`). The current CLI also binds this handler at model construction and passes it in graph config for tools; the existing callback behavior is retained; a new precise per-analysis collector is deferred.
3. Build the initial state. Current code can optionally open a checkpoint (`cli/run.py:219-234`); the new flow in §6.7 does not use that resume path.
4. Stream the graph through `TradingAgentsGraph.stream_run()` (`cli/run.py:241`).
5. Merge streamed chunks into `final_state` (`cli/run.py:346-348`).
6. Call `record_decision()` to write the state log and memory record (`cli/run.py:353`).
7. Display the rating and offer report saving (`cli/run.py:380`, `cli/run.py:426`).

**Programmatic path** `[Static code]`

`TradingAgentsGraph.propagate()` (`tradingagents/graph/trading_graph.py:167`) → `_run_graph()` (`:372`) → `graph.invoke()` → `record_decision()` (`:399`) → returns `(final_state, run_rating(final_state))` (`:404`).

**Graph** `[Static code]`

`tradingagents/graph/setup.py:142` builds:

```text
START
  ├─ market / social / news / fundamentals analysts (parallel)
  └─ Memory Log
        ↓
Bull Researcher ↔ Bear Researcher
        ↓
Research Manager
        ↓
Trader
        ↓
Aggressive ↔ Conservative ↔ Neutral Analysts
        ↓
Portfolio Manager
        ↓
END
```

The Portfolio Manager currently writes `final_rating` and `final_trade_decision` directly (`tradingagents/agents/managers/portfolio_manager.py:80-104`). There is no deterministic final-check node.

**Data path** `[Static code]`

- Tool-based analyst calls enter `tradingagents/agents/tools.py` and then `route_to_vendor()` (`tradingagents/dataflows/router.py:200`).
- `get_news` has a tool path (`tools.py:172`) and a sentiment prefetch path (`tradingagents/agents/analysts/sentiment_analyst.py:66`).
- Sentiment prefetch also calls `fetch_stocktwits_messages` and `fetch_reddit_posts` directly (`sentiment_analyst.py:69-76`).
- `get_verified_market_snapshot` bypasses the router and calls the snapshot builder directly (`tools.py:90`).
- Existing vendor caches and fallback chains remain inside the data-fetch flow.

**Outputs and state** `[Static code]`

- State log: `tradingagents/graph/trading_graph.py:437-475` writes `results_dir/<ticker>/TradingAgentsStrategy_logs/full_states_log_<date>.json`.
- Memory log: `tradingagents/memory/log.py:32` appends decisions; settlement/reflection updates the same entries.
- Reports: `tradingagents/reporting.py:92` writes section files, `complete_report.md`, and optionally `complete_report.html`.
- CLI live sections: `cli/run.py:166-183` wraps `message_buffer` to write section Markdown files immediately.
- Statistics: `cli/stats_handler.py:9` counts LLM/tool starts and adds token usage; missing usage is currently treated as zero (`:53-56`).

### 2.2 Existing behaviors retained

| Behavior | Evidence | Design treatment |
|---|---|---|
| LangGraph agent graph and node names | `graph/setup.py` | Retained; two deterministic nodes added after Portfolio Manager. |
| Vendor routing, fallback, historical withholding | `dataflows/router.py`, `dataflows/date_window.py` | Retained unchanged; governance observes results. |
| Existing report layouts | `reporting.py`, `cli/run.py:36-42` | Retained; no new manifest registration. |
| Memory log format and settlement | `memory/log.py`, `memory/settlement.py` | Retained; new records use the formal result. |
| Checkpoint support | `graph/checkpointer.py`, `graph/trading_graph.py:192-253` | Underlying checkpoint implementation and existing tests are retained, but the new analysis flow does not acquire a checkpoint session, resume, or use old checkpoint data. Each analysis fully re-executes. |
| Existing stats callback shape | `cli/stats_handler.py`, `graph/trading_graph.py:78-80` | Retain baseline behavior; no new FR-02 collector or propagation work is current. |
| CLI interaction and save failure display | `cli/run.py:426-464` | Behavior retained; save and display behavior retained; terminal availability is prepared before save/return. |
| `propagate()` return shape | `trading_graph.py:404` | Retained: `(final_state, signal)`; `signal` is the formal final rating. |
| Existing security helpers | `dataflows/net.py:6`, `dataflows/symbols.py:155` | Retained and reused; scope remains limited. |

### 2.3 Constraints

- Python >= 3.11; LangGraph/LangChain; pytest and ruff (`pyproject.toml`).
- Two supported entry points only: the CLI analysis entry and `TradingAgentsGraph.propagate()`.
- Governance must not add model, data-source, broker, or network calls.
- Existing state/new-memory/requested-report save failures retain their original behavior and never rewrite the SB-01 result. Availability handling does not replace execution errors.
- No new persistence service, database, index, or background worker.
- The design must remain testable offline with fake models and data; the existing test suite blocks network access by default (`test/conftest.py`).

---

## 3. Architecture drivers

### 3.1 Ranked drivers

Ranking considers requirement priority, architectural impact, safety impact, and risk.

| Rank | Driver | Requirements | Architectural impact | Risk if mishandled |
|---|---|---|---|---|
| 1 | Single authoritative final result with fail-closed checks | SB-01, INV-01 | Adds graph-internal deterministic nodes; changes Portfolio Manager output semantics; changes all consumers | Two ratings, bypassed checks, unsafe approval |
| 2 | Deterministic purchase risk boundary | FR-04 | Adds structured scenario input, evaluator, deterministic display | Model text or rounded values alter a pass/block decision |
| 4 | Data availability summary | FR-03 | Adds 15 path-specific observation sites and a run-scoped registry | False completeness, fabricated execution, model override |
| 5 | Run-scoped identical-query reuse | FR-01 | Adds single-flight service for two `get_news` paths | Cross-run leakage, merged different queries, mutable-result pollution |
| 6 | Consistent delivery across outputs | INV-01 | Constrains report, state log, CLI, memory, and return consumers | Different formal ratings in different outputs |
| 8 | Credential protection in limited paths | SR-01 | Endpoint preference, known-value sanitization, safe diagnostics | Credential in supported preferences/config summaries/request errors |
| 10 | Deferred scope discipline | FR-06, FR-07, PR-01, CR-01 | Keep deferred behavior out of the current design; no placeholder classes, modules, flags, or fields | Accidental activation or re-introduction of deferred scope |

### 3.2 Quality attribute scenarios

All response measures reuse fit criteria. No invented latency, cost, or quality target is used.

| ID | Source | Stimulus | Environment | Artifact | Response | Measure |
|---|---|---|---|---|---|---|
| QAS-01 | Program or user | Completed analysis whose model proposal may claim approval or complete data | CLI and programmatic entry; fake model/data offline | Final result | Only SB-01 forms `gate_status`, top-level `reasons`, `final_rating`, and `final_trade_decision`; failure becomes REVIEW plus program notice | SB-01-FC01–FC05 |
| QAS-03 | Concurrent analysts or prefetch | Same supported `get_news` query called sequentially or concurrently | One run context | Data-fetch flow | One underlying execution per query; callers receive equivalent result or same failure type/reason | FR-01-FC01–FC05 |
| QAS-04 | Data path | Necessity data succeeds, fails, is absent, is withheld, or is never queried | One analysis | Availability summary | Deterministic status and basic completeness; research-stage roles receive the start summary; later check/report use their own snapshots; no extra fetch | FR-03-FC01–FC05 |
| QAS-05 | Caller | Missing, invalid, over-limit, or non-applicable purchase scenario | CLI and programmatic entry | Risk result | `blocked`, `error`, or `not_applicable`; no hard analysis failure; no model override | FR-04-FC01–FC05 |
| QAS-07 | Caller/provider | Known credential in supported config/endpoint/error | Local app | Safe summaries/preferences/diagnostics | Omit or mask under SR-01 | SR-01-FC01–FC04 |
| QAS-08 | Runtime | Existing state/report/new-memory save failure | Formed formal result | Existing save paths | Original error, no rollback/recompute/fake success | INV-01-FC01–FC03 |

### 3.3 Driver conflicts and resolutions

| Conflict | Resolution |
|---|---|
| One authority vs two entry points | The authority is the graph-internal `Final Recommendation Check` node. Both entries run the same graph and consume its formal fields. |
| Reusable graph object vs analysis scope | Bind one ephemeral scope at the existing analysis execution boundary, after effective config/basic validation and before the first supported data call. Constructor-only use creates no scope. Explicit delegation shares scope; independent calls do not. No constructor timing or new callback lifecycle is required. |
| Entry cleanup vs scope exit | Resource owner closes once; finish restores binding after cleanup without persistence or new stats. |
| Graph-internal check vs checkpoint resume | The new flow does not resume checkpoints. Each independent outermost analysis has a fresh ephemeral scope and initial state; FR-04/SB-01 always execute. Existing checkpoint code/tests remain outside this flow, and a checkpoint-enabled configuration only produces a notice that this flow will run fully. |
| Portfolio Manager existing fields vs SB-01 authority | The Portfolio Manager writes a separate `model_proposal`. SB-01 alone decides and generates `gate_status`, top-level `reasons`, `final_rating`, and `final_trade_decision`; downstream entries, reductions, and writers may only pass, merge, copy, or save those values unchanged. |
| Fail-closed REVIEW vs existing rating fallback | `run_rating()` text parsing is not a formal authority. SB-01 produces a complete blocked/REVIEW for missing or invalid check inputs and a complete error/REVIEW for its own handled exceptions. If the graph ends without a valid formal result, or the result is lost in transfer or merge, that is an execution contract failure: consumers do not create REVIEW, parse text, or substitute the proposal. |
| CLI report save inside the run vs existing interaction | Save selection and save attempt occur inside the run; existing display/browser ordering is retained; scope exit is not a new persisted terminalization. |
| FR-01 reuse vs FR-03 observation | FR-03 observes actual data-fetch execution. A reuse hit preserves the original observation and does not add a new observation. |
| Required data completeness vs historical withholding | `withheld` remains a distinct status; completeness never bypasses historical policy. |
| Minimal security scope vs perceived completeness | Current SR-01 uses the limited allowlist/credential rules; SR-02 path work is deferred. Existing ticker protection remains; no generic scanner or immutable archive is claimed. |

---

## 4. System context and boundaries

### 4.1 Context

```text
CLI / propagate()
  → ephemeral RunContext (query reuse + availability)
  → existing analysts/research/trader/risk debate
  → Portfolio Manager: advisory model_proposal
  → Portfolio Risk Check: check-time availability + C-08 risk
  → C-09 Final Recommendation Check
  → IF-19 → terminal availability preparation
  → existing CLI / return / report / state log / new memory
  → cleanup and restore scope
```

No current manifest, precise statistics or history branch. Reports consume passed state, not a live registry.

### 4.2 External dependencies

| Dependency | Current use | Governance use |
|---|---|---|
| LLM providers | Analysis, debate, managers, reflection | None in FR-04/SB-01; no new calls |
| Data vendors | Market, fundamentals, news, social, macro, prediction markets | None in governance checks; FR-03 observes existing calls |
| Filesystem | Existing results, cache, memory, checkpoints | Existing state/report/memory outputs; manifest/history deferred |
| CLI terminal | Interactive selections, display | Save selection inside run; display after run |
| GitHub CI | Project-root `.github/workflows/ci.yml` and `.github/workflows/trusted-evaluation.yml`; local gates cover schema, Ruff, mypy baseline, dependency/import, regression, test approval, contract tests, security paths, AI-use log, trusted semantic evidence, and aggregate status | Verification/governance only; CI has no application authority, and local configuration does not prove remote execution, required checks, or branch protection |

### 4.3 Trust boundaries

| Boundary | Trusted side | Untrusted or lower-trust input |
|---|---|---|
| Model output | Program state and deterministic checks | Model rating, model narrative, model claims of approval or data completeness |
| Vendor output | Existing vendor adapters and typed sentinels | Text payloads; status classification uses existing structures/sentinels, not model judgment |
| Caller input | Validated CLI/program parameters | Model-supplied tool arguments; report prose |
| Results root | Configured root after resolution | run_id, report references, ticker components |
| Credentials | Known values configured or used in this run | Arbitrary output text; no generic unknown-secret detection |

### 4.4 Advisory vs authoritative boundary

| Output | Producer | Authority | Consumers |
|---|---|---|---|
| Analyst reports, research plan, trader plan, risk debate | Existing agents | Advisory analysis material | Debate, managers, report |
| `model_proposal` | Portfolio Manager node | Advisory only; nested `{rating, text}` or `null`; explicitly “not yet checked” | Intermediate display, final check input, labeled report section |
| `research_availability_summary` | Research-entry wrapper using `AvailabilitySummarizer` | Fixed research-start program fact | First Bull, later Bull/Bear, Research Manager |
| `data_availability_summary` | Risk node writes check-time summary; entry prepares terminal summary | Deterministic program fact for final check/report delivery | Final check (check-time), CLI/display and report (entry-prepared terminal state) |
| `portfolio_risk_result` | `PortfolioRiskEvaluator` | Deterministic program fact for the supplied scenario | Final check, CLI, final_state, report |
| `gate_status`, `reasons`, `final_rating`, `final_trade_decision` | `FinalRecommendationChecker` (SB-01 node) | Sole formal authority | CLI, `final_state`, `propagate()` signal, report, state log, memory |

`final_rating` and `final_trade_decision` are never parsed from report prose, model narrative, memory, or history. `reasons` is the top-level SB-01 reason list; `portfolio_risk_result.reasons` is a separate risk-scoped list. The risk object is not flattened into the top-level formal fields.

“Sole formal authority” means that C-09/SB-01 is the only component that decides and generates the formal business values. Entries, reducers, report/state writers, and memory adapters may assign, merge, copy, or persist those values unchanged. Such pass-through or projection is not a second authority; it is a violation only if the value is recomputed, re-parsed from model prose, replaced, or fabricated.

`model_proposal` is a nested object with `rating` and `text` keys, or `null` when no proposal was produced. A missing inner value is `null`; there is no `present` boolean or invented proposal. The Portfolio Manager's free-text fallback may be used to extract the proposal rating, but only SB-01 determines the formal rating.

---

## 5. Selected architecture

### 5.1 Style and principles

Selected: **graph-internal deterministic final check with a run-scoped governance context and thin adapters**.

Principles:

1. Keep the existing LangGraph agent graph; add deterministic nodes after the Portfolio Manager.
2. Separate advisory proposal from formal result at the field level.
3. Keep checks pure and model-free; pass them explicit program inputs.
4. Keep run infrastructure (`RunContext`) out of serializable graph state and checkpoints.
5. Keep report, final-state and new-memory failures path-specific; never rewrite the formal result or add rollback. Manifest persistence is deferred.
6. Instrument data access through path-specific local wrappers at the 15 supported call sites, not global monkeypatching.
7. Preserve existing entry return shapes and existing failure displays.
8. Keep security scope explicit and limited.
9. Assign each resource release to its acquiring scope or wrapper; `RunContext.finish()` restores the previous context binding after entry-owned cleanup.

### 5.2 Component catalog

| ID | Component | Responsibility | Does not own |
|---|---|---|---|
| C-01 | CLI Entry Adapter (`cli/main.py`, `cli/run.py`) | Parameter selection, basic validation, scope binding before supported data calls, existing graph object construction, streaming, save coordination, post-run display | Final rating, risk computation, availability classification |
| C-02 | Programmatic Entry Adapter (`TradingAgentsGraph.propagate`) | Per-call validation and effective config on an existing object, run creation, graph invocation, finalization, return shape | Final rating, risk computation, object construction timing |
| C-03 | RunContext | Per-analysis ephemeral binding, C-05/C-07 ownership and isolation | Persistent ID, timers/status, new stats, manifests, output registration |
| C-04 | **Deferred** RunStatsHandler / RunStatsCollector | Future-only FR-02/FR-05 responsibility; no current implementation or monitor | No current authority |
| C-05 | QueryReuseService | FR-01 run-scoped single-flight reuse for supported `get_news` queries | Vendor fallback/retry, cross-run cache |
| C-06 | Supported-path observation sites | 15 path-specific sites using one small local helper at the existing call point; preserve results/failures and pass the original outcome to the classifier | Router/vendor instrumentation, tool-callback observation, governance decisions, status guessing |
| C-07 | AvailabilityRegistry / AvailabilitySummarizer | FR-03 accepted-update ordering, query-path association, query-level failure marks, private pre-fetch call-failure notes, the internal `availability_tracking_error`, the single producer of the five-field `AvailabilitySummary` or its missing result, deterministic stage/final summaries and entry-prepared terminal report summaries, and a small deterministic program-block renderer | Extra fetches, formal rating, second completeness authority, consumer-side completeness rebuilding, fake completed queries, new completion statuses, a general permanent veto, model-generated availability text |
| C-08 | PortfolioRiskEvaluator | FR-04 applicability, parsing/validation, exact-rational decision, one JSON-compatible result projection, and local display formatting | Formal rating, model calls, manifest, a generic numeric-conversion framework, a required class/service/API split |
| C-09 | FinalRecommendationChecker | SB-01 deterministic final decision | Risk recomputation, model/data calls, manifest, memory |
| C-10 | GraphSetup and graph nodes | Existing agent wiring, research-entry wrapper around the first Bull call, plus post-PM deterministic nodes | Proposal/formal field ownership outside node contracts, separate top-level research node |
| C-11 | ReportWriter and CLI renderers | Existing report tree plus deterministic availability/risk/decision sections and intermediate labels; Markdown and HTML read the same passed report state | Availability source lookup, registry access, formal rating generation |
| C-12 | MemoryAdapter (`TradingMemoryLog`) | Existing append/settle/reflection behavior using formal result | Formal rating generation, report regeneration |
| C-13 | **Deferred** HistoryReader | Future-only FR-02/FR-05 responsibility; no current implementation or monitor | No current authority |
| C-14 | **Deferred** ManifestStore | Future-only FR-02/FR-05 responsibility; no current implementation or monitor | No current authority |
| C-15 | SecurityGuard | Current SR-01 omission/preference/safe diagnostics | Deferred SR-02 manifest/history path checks; generic scanner |
| C-16 | CheckpointAdapter (existing, outside the new flow) | Retains the existing checkpointer, thread ID, signature, cleanup tools, and tests | New-flow resume, checkpoint acquisition, old-checkpoint evidence, automatic recovery |
| C-17 | CLI Display Coordinator | Streaming sections, waiting/formal states, post-run browsing | Final rating, save success |
| C-18 | Config/Threshold Access | `run_settings()` allowlist, shared config-summary projection, risk thresholds, provider/config values | Credential persistence, graph construction |
| C-20 | DataResultClassifier | Narrow per-method classification from verified producer branches into status, safe reason, and known/unknown source; a known-query internal exception becomes a conservative per-query unavailable observation at the local-wrapper/registry boundary | Data fetching, model calls, fuzzy keyword guessing, formal business decisions, replacing fetch outcomes, global run failure |

Components in this table are logical responsibilities. They do not require one class, module, service, registry, or file per component. Prefer small functions at existing boundaries: a wrapper for research entry, a shared pure function for formal-result validation, risk parsing/comparison/projection helpers inside the risk module, registry collections and summary functions in one availability module, and small security helpers for the actual paths. Do not add a general registry, plugin framework, event bus, or universal service.

### 5.3 Principal interfaces

| ID | Interface | Contract |
|---|---|---|
| IF-01 | Internal analysis-scope initialization/binding | Use a small local function or context manager with existing analysis/config values; RunSpec, if used as a name, denotes ordinary internal mapping data, not a required DTO, public API or service framework. Bind C-05/C-07 ownership before supported data calls; no manifest, timers, persisted ID or new stats. |
| IF-02 | `RunContext.finish() -> None` | Restore prior scope binding after entry-owned cleanup; no resource double-close, manifest outcome or new persisted terminal state. |
| IF-03 | `RunContext.current() -> RunContext | None` | Context-local access for adapters; no process-global mutable run state. |
| IF-04 | `QueryReuseService.execute(QueryKey, executing_path_id, flow) -> Result` | Register the explicit supported path association, then single-flight per run. The first caller runs the existing fetch once through the local observation helper and preserves its original value/exception. A known-query classifier exception creates a conservative `unavailable` observation with a safe “availability classification failed” reason; if normal or conservative acceptance fails, the service records a query-level failure mark. If even that fallback cannot be recorded, the run-local `availability_tracking_error` is set; later snapshots return `None` and the existing missing/invalid-summary path applies. The shared completion is published on every normal/error path; waiters/cache hits receive the original result or same failure and never receive the observation-handling exception. No public permanent veto flag or cross-run state; only the private tracking error can make later snapshots missing. |
| IF-05 | Local observation helper (ordinary internal function, not a public API) | Executes the existing supported call body once, preserves its original return/exception, attempts one observation in isolation, and returns or propagates the original outcome. With no active `RunContext`, it calls the body directly and records nothing. A known-query classifier exception becomes a conservative per-query `unavailable` observation; a failed registry acceptance becomes a query-level failure mark. A pre-fetch parameter/date rejection with no completed query records a private call-failure note instead of a query observation. If a completed query’s observation cannot be identified or neither local record can be accepted, set the run-local `availability_tracking_error`. It never refetches, retries, calls a model, monkeypatches, or acts as middleware. |
| IF-06 | `AvailabilitySummarizer.snapshot(asset_type, enabled_analysts, analysis_context) -> AvailabilitySummary | None` | Returns one JSON-compatible mapping with `basic_completeness`, `applicability_note`, `observations`, `necessary_items`, and `supplementary_limitations`. It reads the current registry, applies query-level failure marks, matches the fixed necessity targets in §8.3 before selecting the current decision update by accepted-update order, builds the necessary items and supplementary limitations, and computes completeness once. `analysis_context` carries the existing ticker/date/range information needed for matching; no new config system. No I/O, extra fetch, mutable registry exposure, or consumer-side completeness step. Any `necessity_status` helper is internal to the summarizer, not a consumer interface. If `availability_tracking_error` is set, return `None`; if this snapshot construction alone fails, return `None` for this call without setting that error fact. `None` is missing, not a fourth completeness state. |
| IF-08 | `PortfolioRiskEvaluator.evaluate(analysis_ticker, proposal, scenario, thresholds, asset_type) -> PortfolioRiskResult` | Pure deterministic evaluation using the explicit current analysis ticker. Internal decisions use exact rational values; output is one JSON-compatible result with decimal-string metrics/null and risk-scoped reasons. Parse/validate, decide, and project are local responsibilities, not a required class/service/API split. No global state, model/data call, manifest, text extraction, or default Decimal-context dependence. |
| IF-09 | `FinalRecommendationChecker.evaluate(proposal, availability, risk, asset_type) -> FinalDecision` | Pure deterministic final decision; returns the five-field formal result: `model_proposal`, `gate_status`, top-level `reasons`, `final_rating`, and `final_trade_decision`. Risk reasons stay inside the risk result. |
| IF-10 | **Deferred** `ManifestStore.write(record) -> PersistenceOutcome` | Future FR-02/FR-05/SR-02 only; not a current contract. |
| IF-11 | **Deferred** `RunStatsHandler.snapshot() -> StatsSnapshot` | Future FR-02/FR-05/SR-02 only; not a current contract. |
| IF-12 | **Deferred** `HistoryReader.list_runs(ticker=None, analysis_date=None) -> list[RunSummary]` | Future FR-02/FR-05/SR-02 only; not a current contract. |
| IF-13 | **Deferred** `HistoryReader.get_report(run_id) -> str` | Future FR-02/FR-05/SR-02 only; not a current contract. |
| IF-14 | **Deferred** `SecurityGuard.validate_run_id(value) -> str` | Future FR-02/FR-05/SR-02 only; not a current contract. |
| IF-15 | **Deferred** `SecurityGuard.resolve_under_root(root, candidate) -> Path` | Future FR-02/FR-05/SR-02 only; not a current contract. |
| IF-16 | `SecurityGuard.safe_endpoint_for_preference(url, known_secrets) -> PreferenceDecision` | Save/restore only safe endpoint or omit with re-entry notice. |
| IF-17 | `SecurityGuard.safe_error_summary(exc, known_secrets) -> SafeErrorSummary` | Sanitized type/message; no traceback or attached request/response. |
| IF-18 | Existing report writer over passed `final_state` and existing save options | Renders the existing report tree plus deterministic availability/risk/check sections from the passed state. Availability comes from `data_availability_summary` in that state; Markdown and HTML use the same input. The same writer serves run-in save and independent `save_reports(final_state, ...)`, which is read-only over that state. It does not read `RunContext.current()`, the registry, the summarizer, a graph last-run cache, or model text, and does not derive a formal rating. |
| IF-19 | `FormalResultContract.validate(result) -> ValidatedResult | ContractFailure` | Lightweight shared structural check: the five required fields exist with correct types; `model_proposal` is a nested `{rating, text}` object or `null` (an illegal proposal rating is SB-01 input, not a contract failure); formal gate and rating sets are legal; passed has a five-tier formal rating; blocked/error has REVIEW; `final_trade_decision` is a non-whitespace string; `reasons` is a string list and blocked/error has at least one actual reason. Returns the result unchanged or reports an execution contract failure. No business judgment, data/risk recheck, text parsing, model/data call, repair, second status set, or new module/API requirement. |
| IF-20 | Existing CLI save coordination | Preserve optional save interaction and existing failure display/exception behavior; no manifest-reference registration or new save protocol. |
| IF-21 | `ConfigSummary.project(effective_config, selected_analysts) -> dict` | Existing run_settings allowlist shared by report/final-state configuration summaries; omit whole fields containing a nonempty known credential literally. No pre-construction manifest obligation. |
| IF-23 | `DataResultClassifier.classify(method, effective_params, raw_result_or_exception, source_hint) -> DataObservation or ClassificationFailure` | Apply the verified per-method branch table; return status, short safe reason, and source (known or null). A normal unrecognized format is the existing `unavailable` classification; an internal exception is `ClassificationFailure`, not a data-source status. With a known query key, the local observation helper/registry converts that failure into a conservative per-query `unavailable` observation; it does not mean all registry data is corrupt. Preserve the original return/exception; no fetch, model call, global source inference, or fuzzy keyword guessing. |
| IF-24 | `ResearchEntry.prepare(state, first_bull_call) -> (state_update, bull_result)` | On the first research entry after analyst join, obtain one `AvailabilitySummary` from the summarizer using existing asset type, enabled analysts, and analysis context, or `null` when none can be formed. Render the mapping to a labeled program block; for `null`, the renderer emits the fixed display text “program summary currently unavailable.” Inject that block directly into the same first Bull invocation and return `research_availability_summary` as the mapping or `null` in state. It is a wrapper, not a top-level node; no extra data/model call, compression, truncation, refresh loop, seal, version view, registry exposure, or second completeness authority. |
| IF-25 | Risk-module internal helpers | Small local functions for input parsing/validation, exact comparison, one JSON-compatible result projection, and display formatting. They are not public interfaces, separate services, or a generic numeric framework; no canonical state protocol, digest, round-trip proof, consumer-specific float conversion, or implicit encoder is added. |

### 5.4 State ownership and data classes

| State/data | Owner | Persistence | Serializable | Notes |
|---|---|---|---|---|
| Binding, locks, reuse and availability state | RunContext | In-memory only | No | One analysis; no new persistent identity/timers/status/counters |
| Query reuse outcomes | `RunContext` / `QueryReuseService` | In-memory for one run | No | Vendor caches remain separate |
| Availability observations | `RunContext` / `AvailabilityRegistry` | In-memory; snapshot can enter graph state | Registry: no; snapshot: yes | Snapshot is a plain dict/list |
| `model_proposal` | Graph state | Serializable/final state | Yes | Nested `{rating, text}` or `null`; inner values may be `null`; advisory only; never a formal result. No `present` boolean. |
| `purchase_scenario`, thresholds | Initial graph state/config | Graph state | Yes | If carried in graph state, a simple JSON-compatible mapping is enough; entry/risk-boundary conversion handles parsing. No normalized state protocol or scenario/threshold digest is added. |
| `research_availability_summary` | Research-entry wrapper writes; graph state | Serializable/final state | Yes | Independent five-field summary mapping as of research start, or `null` when unavailable; “program summary currently unavailable” is renderer display text, not a stored third type; not refreshed by later observations; old checkpoint material is not used. |
| Necessary-target bindings | C-07 `AvailabilityRegistry` under C-03 | In-memory only | No | First eligible effective request binds before fetch under the registry lock; at most one target per applicable item, never rebound during the run; not a completed observation or summary field |
| Query-path associations | `AvailabilityRegistry` | In-memory | No | `supported_path_ids` only; no sequence/status/source; not a completed observation |
| `availability_call_failures` | RunContext / availability observation management | In-memory for one run | No | Small list of pre-fetch parameter/date rejection notes: supported path/method, safe object, fixed category, short reason; no query key/window/sequence, not in `observations`, not persisted |
| `availability_tracking_error` | RunContext / availability observation management | In-memory for one run | No | `null` or a fixed safe reason for an unlocatable/untrackable observation loss; not in `AvailabilitySummary`, manifest, report state, memory, or checkpoint; cleared only by a new run |
| `data_availability_summary` | Risk node writes check-time snapshot; entry/report preparation replaces it with the terminal delivery snapshot before return/save | Serializable/final state | Yes | Five-field `AvailabilitySummary` plain mapping or null/absent when unavailable; final check keeps using its check-time input; report/independent save read only this terminal state field, never the live registry. |
| `portfolio_risk_result` | Graph state | Serializable/final state | Yes | JSON-compatible result with decimal-string metrics/null and its own `reasons`; exact status is decided before result generation; the new flow does not restore old risk data or flatten this object into top-level formal fields. |
| `gate_status`, `reasons`, `final_rating`, `final_trade_decision` | Graph state; SB-01 alone decides/generates the values | Serializable/final state/report/state log | Yes | Top-level formal authority for the current run; entries, reducers, and writers may pass/merge/copy/save unchanged values but may not recompute, re-parse, replace, or fabricate them; `reasons` does not replace `portfolio_risk_result.reasons`; old persisted values are not used by the new flow. |
| Memory entries | `TradingMemoryLog` | Markdown file | Yes | Cross-run; formal rating/body only |
| Checkpoints | Existing checkpointer | SQLite | Yes | Existing code/tests outside the new flow; not acquired, read, or deleted by the new flow |

The persistence column records whether a value is serializable for existing structures. The new flow does not resume checkpoints.

### 5.5 Dependency rules

- C-08 and C-09 consume the explicit primitive/mapping inputs defined by IF-08/IF-09. They do not import RunSpec, RunContext, entry adapters or required DTO classes. Existing core signatures and plain JSON-compatible results remain unchanged.
- C-09 does not depend on C-14, C-12, C-13, or any network client.
- C-07 depends on C-06 observations and existing data-fetch semantics; it does not trigger fetches.
- C-05 is used only by the two supported `get_news` paths; it does not wrap other methods.
- C-01 and C-02 depend on C-03 and C-10; they do not implement business checks.
- C-11 reads formal fields only for the formal section; it reads `model_proposal` only for the labeled proposal section.
- Current C-15 credential helpers serve the supported entry/config/report/error paths only. C-13/C-14 and their SR-02 path checks are deferred. No business authority is added.
- C-01, C-02, C-11, and C-12 invoke the shared `FormalResultContract` before normal final output. The contract is a validation seam, not a new authority and not necessarily a separate component or file.
- C-01/C-02 bind scope before the first supported data call in an analysis, after effective config/basic validation. Binding before graph-object construction is not required. Constructor-only use creates no scope; explicit delegation shares the caller scope and independent invocations create fresh scope.
- C-18 retains risk thresholds and the shared existing run_settings allowlist for current report/final-state summaries. No pre-construction projection or C-04 callback refactor is required; baseline statistics remain unchanged.
- C-06 observation sites call C-20 with the original result/exception and effective parameters; C-20 does not fetch or infer the configured vendor as the actual source. C-08 receives the analysis ticker explicitly from graph state and does not read a global or report text.
- C-08 contains its own parsing/validation, exact comparison, one result projection, and local display formatting. C-09 consumes only the risk status and needed explanation, and C-01/C-11 consume the same result without re-parsing, recalculating, or re-judging risk.
- C-01 and C-02 coordinate entry-owned cleanup and original error propagation; C-16 describes existing checkpoint code outside the new flow; the new flow acquires no checkpoint session. C-03 / `RunContext.finish()` does not release resources.

---

## 6. Agent workflow and entry points

### 6.1 Graph topology

Selected research-entry and post-PM sequence:

```text
Analyst join (all enabled analysts; Memory Log also completes)
        ↓
Research-entry wrapper (around the first Bull call, not a top-level node)
  request one AvailabilitySummary from the summarizer with existing context
  render a labeled program block deterministically
  inject it directly into the same first Bull invocation
  store research_availability_summary in graph state
        ↓
Bull / Bear debate (read the stage summary directly)
        ↓
Research Manager (reads the stage summary directly)
        ↓
Trader
        ↓
Portfolio Manager (model)
  writes model_proposal only
        ↓
Portfolio Risk Check node (deterministic)
  invokes AvailabilitySummarizer.snapshot(
    asset_type, enabled_analysts, analysis_context)
  invokes PortfolioRiskEvaluator.evaluate()
  writes check-time data_availability_summary + portfolio_risk_result
        ↓
Final Recommendation Check node (deterministic)
  invokes FinalRecommendationChecker.evaluate()
  writes gate_status, reasons,
         final_rating, final_trade_decision
        ↓
END
```

Research start is the analyst join immediately before the first Bull call, not the start of the Research Manager. The research-entry wrapper executes only on the first entry to the research stage. It obtains one summary from the summarizer using existing state/config context, renders the program block without a model/data call or truncation, supplies that block to the same first Bull call, and stores the summary as `research_availability_summary`; it cannot rely on a state update being visible to the current call. Later Bull/Bear rounds and the Research Manager read that same plain mapping from state. The summary is not refreshed or rewritten by later observations and does not re-run research.

The risk node invokes a fresh snapshot before the risk evaluator. The snapshot function and risk evaluator are independent components with separate interfaces; the node is orchestration only. The snapshot has no approval authority. SB-01 consumes that check-time snapshot. After the formal check, the entry prepares a terminal delivery summary from the same run's registry for final_state/report use; this does not rerun SB-01 and does not overwrite the research-stage summary. This preserves the fixed sequence Portfolio Manager → FR-04 risk result → SB-01 final check while ensuring SB-01 receives a serializable current analysis snapshot.

Node contracts:

| Node | Inputs | Outputs | Must not |
|---|---|---|---|
| Portfolio Manager | Existing debate/plans, instrument context, memory context | `model_proposal`: nested `{rating, text}` or `null`; inner values may be `null` | Write `gate_status`, top-level `reasons`, `final_rating`, or `final_trade_decision`; parse a formal rating |
| Portfolio Risk Check | `model_proposal`, `purchase_scenario`, thresholds, asset type, explicit analysis ticker | `data_availability_summary`, `portfolio_risk_result` with risk-scoped `reasons` | Change the proposal; call a model/data source; write formal fields; flatten risk reasons to the top level |
| Final Recommendation Check | `model_proposal`, `data_availability_summary`, `portfolio_risk_result`, asset type | `gate_status`, `reasons` (top-level SB-01 list), `final_rating`, `final_trade_decision` | Recompute risk; call model/data; read manifest; parse proposal text; copy or overwrite risk reasons |

### 6.2 CLI workflow

Use the existing entry/return shape. Validate parameters, initialize one ephemeral scope, execute the full graph with the retained baseline callback behavior, validate SB-01 output, prepare terminal availability, save existing required outputs and any requested report, then clean up and restore scope. No running/terminal manifest or new precise statistics are required. CLI and propagate() pass the same formal fields unchanged. Explicit delegation shares its caller scope; independent calls do not.

### 6.3 Programmatic workflow

Use the existing entry/return shape. Validate parameters, initialize one ephemeral scope, execute the full graph with the retained baseline callback behavior, validate SB-01 output, prepare terminal availability, save existing required outputs and any requested report, then clean up and restore scope. No running/terminal manifest or new precise statistics are required. CLI and propagate() pass the same formal fields unchanged. Explicit delegation shares its caller scope; independent calls do not.

### 6.4 Normal path sequence

```text
Validate invocation → start ephemeral scope → execute full graph
→ validate formal result → prepare terminal availability in delivery state
→ existing state save → conditional new-memory append
→ optional CLI report save → cleanup/restore scope → normal delivery
```

Independent report saves use passed final state only. No terminal manifest, new statistics snapshot or file registration occurs.

### 6.5 Failure paths

| Failure | Current handling | Formal result |
|---|---|---|
| Entry/graph/setup error | Preserve original execution error; clean up acquired resources and restore scope | No fabricated normal result |
| Missing/invalid formal result at IF-19 | Execution contract failure; no proposal parsing, replacement REVIEW or normal save | Not delivered as valid |
| Ordinary risk/final-check condition failure | Existing pure core returns blocked/REVIEW as applicable; entry does not hard-fail solely for missing scenario | C-09 result retained |
| Final-state save failure | Original error; do not attempt subsequent new-memory append | Never recomputed |
| New-memory append failure | Original error; retain saved state | Never recomputed |
| Requested report partially/fully fails | Existing save error/display; keep files actually saved; no rollback/fake success | Never recomputed |
| Terminal availability preparation fails | Safe warning, unavailable display region; no new fetch/model/check | Already formed formal fields retained |
| Cleanup fails | Attempt remaining cleanup; preserve primary error; no double-close | Never recomputed |

No persistent run status or manifest attempt is required on these paths.

### 6.6 Intermediate content vs formal output

| Material | Live display | Immediate files | Final report | State/return | Memory |
|---|---|---|---|---|---|
| Risk debate | Separate risk-analysis section | Existing `4_risk/*.md` | Separate risk section | `risk_debate_state` | Not a decision |
| `model_proposal` | “Original Model Proposal — Not Yet Checked” section | `5_portfolio/proposal.md` with the label | Labeled proposal section | `model_proposal` | Never stored as decision |
| Formal result before check | “Final Recommendation — Waiting for Check” | No formal decision file before check | No formal section yet | Formal fields absent | No new record yet |
| Formal result after pass | Formal decision section | `5_portfolio/decision.md` | Formal decision section | `gate_status`, `reasons`, `final_rating`, `final_trade_decision` | New record uses formal rating/body |
| Formal result after blocked/error | REVIEW + program manual-review notice; proposal labeled “Original Model Proposal — Did Not Pass Final Check” | `5_portfolio/decision.md` contains REVIEW/notice; proposal remains separate | Formal REVIEW section plus labeled proposal | Formal REVIEW fields and top-level reasons | New record uses REVIEW/notice |

Rules:

- The formal decision area is never populated from `model_proposal`.
- Top-level `reasons` is written by SB-01 and is not a copy of `portfolio_risk_result.reasons`.
- The original proposal is never overwritten; it is either labeled unchecked or labeled failed.
- “Model generation complete” and “Final check complete” are separate statuses in the CLI display.
- Report/state/memory consumers use formal fields only. They never parse, synthesize, or substitute a rating. If formal fields are missing or invalid, the shared `FormalResultContract` reports an execution contract failure; consumers do not write REVIEW or a manual-review notice. A business REVIEW is formed only by SB-01.

### 6.7 Checkpoint compatibility limit for the new flow

The existing checkpoint storage, thread ID, run signature, success-cleanup tool, and checkpoint tests remain in the codebase. They are not removed or redesigned by this architecture.

The new CLI analysis flow and `TradingAgentsGraph.propagate()` flow do not use checkpoint resume:

- Each analysis creates a new `RunContext` and a new initial state.
- The graph is executed fully from the normal entry point; the flow does not invoke `invoke(None)` / `stream(None)` to resume a saved schedule.
- The new flow does not acquire a checkpoint session, read an old checkpoint as current evidence, or delete old checkpoint data.
- When `checkpoint_enabled` is set, both entries emit a safe notice that resume is not provided by this flow and that the analysis will execute fully. There is no confirmation prompt and no change to the user's configuration or default.
- Existing checkpoint data is left untouched; it is not used for the current formal result, statistics, availability, or risk.

Normal flow:

```text
parameter validation
  → new RunContext
  → new initial state
  → existing analysis graph
  → FR-04
  → SB-01
  → unified formal output
  → existing save flow
  → restore ephemeral scope
```

Execution failure preserves existing error handling; no automatic recovery/retry is added. A subsequent invocation owns a fresh ephemeral scope. This flow does not add text-completion recovery, cross-analysis evidence inheritance, or automatic model replay.

Explicit compatibility cost: an interrupted analysis is re-run from the beginning on the next invocation, including model and data calls; time and call cost may increase. No performance or cost benefit is claimed.

`finalization_contract` is removed from the current flow's state and node contract because it existed only for checkpoint compatibility. This does not change `FormalResultContract`, the single formal-result authority, or normal consumer validation.

The FR-04 and SB-01 nodes still increase graph depth. The existing recursion-limit compatibility check must reserve the necessary post-analyst steps.

This checkpoint limit is distinct from deferred FR-06, which concerns recovery of already-produced Markdown report text, not graph checkpoint resume.

If a future requirement asks the new flow to resume interrupted analyses, reopen the ADR and first decide analysis identity, observation inheritance, statistics, and formal-result semantics. No such capability is designed or implemented here.

### 6.8 Role input context

The current design preserves each role's existing prompt assembly. Context classes describe provenance and authority only; they are not a shared layer object or a required physical order. A class absent from a role is not applicable and gets no placeholder.

| Role | Existing inputs retained | FR-03 research-stage summary |
|---|---|---|
| Tool-using analysts | System prompt, instrument context, message/tool-call history, tool results | No |
| Sentiment analyst | System prompt, instrument context, prefetched news/StockTwits/Reddit blocks, message history, structured output/fallback | No |
| Bull and Bear Researchers | Instrument context, four full analyst reports through existing missing-report handling, debate history, latest opponent argument | Yes, same stage summary |
| Research Manager | Instrument context, full debate history | Yes, same stage summary |
| Trader | Instrument context, portfolio context, investment plan, optional market report | No |
| Aggressive, Conservative, Neutral analysts | Instrument context, portfolio context, full analyst reports, Trader plan, risk history, latest opponent responses | No; FR-07 remains deferred |
| Portfolio Manager | Instrument context, portfolio context, Research Manager plan, Trader plan, memory lessons, risk debate history | No; SB-01 consumes the program summary separately |

The code paths differ and remain different: analysts use a system prompt with message history and tool calls, the sentiment analyst prefetches source blocks, Bull/Bear and risk roles use inline strings, Trader uses a message list, and managers use structured output with a free-text fallback. The design does not unify these paths.

The only new active context increment is the FR-03 research-stage program summary. It is rendered by a small deterministic function into a clearly labeled block, passed directly to the same first Bull call, stored as `research_availability_summary`, and reused by later Bull/Bear rounds and the Research Manager. It does not replace the full reports, add a model call, refresh on later observations, compress, or truncate. The final check uses its check-time summary; the entry prepares the terminal report summary before save/return, and the writer does not take a snapshot.

Portfolio Manager prompt text is adjusted only to describe a model proposal awaiting deterministic check, not a final formal decision. Its evidence, rating scale, structured `PortfolioDecision` path, and free-text fallback remain. SB-01 authority is established by the program result, never by prompt wording or a prompt-presence check.

No unified context assembler, cross-role deduplication, quick/deep budget, global input cap, tokenizer, automatic history trim, mandatory-block reinjection retry, local overflow refusal, or new role-failure mechanism is added. Existing request assembly, client configuration, and provider limits remain. Long histories or reports may exceed a provider's context limit and follow the existing client error path; the design does not promise arbitrary-length success. Context budgets, compression thresholds, and compressed-constraint reinjection are deferred per ADR 001 D-10c, not current design, implementation, or acceptance. FR-03 research-stage summary remains active.

---

## 7. Run lifecycle

### 7.1 Current in-memory analysis scope

C-03 RunContext is created for each outer analysis and bound only for that execution. Both entries bind it at their existing analysis execution boundary after effective config/basic validation and before the first supported data call. There is no requirement to bind it before graph-object construction; propagate() operates on an existing graph object. Explicit internal delegation shares the same scope. Construction alone creates no analysis context. Scope carries effective analysis identity/config needed by C-05/C-07, reuse state, availability registry and local failure notes; it owns no current manifest, new statistics or persistent identity.

IF-01 start initializes these objects and binds the context. IF-03 current provides context-local access. IF-02 finish restores the prior binding after entry-owned resource cleanup; it does not close resources twice, persist a terminal status or return ManifestWriteOutcome. Initialization failure follows the existing execution-error path; cleanup preserves the primary error. Independently invoked analyses never share mutable scope state.

### 7.2 Delivery and cleanup

Graph completion produces the formal result. Entries validate it with IF-19, prepare the terminal availability summary into delivery state, preserve final-state-save then conditional new-memory append ordering, and retain existing optional report-save behavior. Requested save failures preserve their existing exception/display behavior; completed files are not rolled back and the formal result is not rewritten. Independent save reads passed state and opens no analysis context. No manifest references are collected. Full new-flow execution and the existing checkpoint exclusion remain.

### 7.3 Deferred lifecycle

Persisted run_id, timers, running/completed/failed record transitions, exact new call/token collection, atomic manifest writes, produced-file registration and manifest-based history belong to deferred FR-02/FR-05/SR-02. Their previous detailed design is retained in the future-design archive, not as current instructions.

## 8. Data and state design

### 8.1 Data access adaptation

Fifteen supported call-path positions over fourteen methods:

| Position | Call path | Method/data item |
|---|---|---|
| P-01 | Market analyst | `get_stock_data` |
| P-02 | Market analyst | `get_verified_market_snapshot` |
| P-03 | Market analyst | `get_indicators` |
| P-04 | Fundamentals analyst | `get_fundamentals` |
| P-05 | Fundamentals analyst | `get_income_statement` |
| P-06 | Fundamentals analyst | `get_balance_sheet` |
| P-07 | Fundamentals analyst | `get_cashflow` |
| P-08 | Fundamentals analyst | `get_insider_transactions` |
| P-09 | News analyst | `get_news` |
| P-10 | News analyst | `get_global_news` |
| P-11 | News analyst | `get_macro_indicators` |
| P-12 | News analyst | `get_prediction_markets` |
| P-13 | Sentiment prefetch | `get_news` |
| P-14 | Sentiment prefetch | `fetch_stocktwits_messages` |
| P-15 | Sentiment prefetch | `fetch_reddit_posts` |

Access attachment table:

| Path | Actual existing call site / design attachment | Parameters used for the observation | Unique observation site | FR-01 |
|---|---|---|---|---|
| P-01 | `agents/tools.py:get_stock_data` body, including `as_of_window` | Symbol and the effective start/end after window handling; on date failure, safe requested values and the date/parameter reason | Same tool body, around date handling + final router result | No |
| P-02 | `agents/tools.py:get_verified_market_snapshot` body | Symbol, effective `as_of` date, `look_back_days` (tool default 30), and the builder's returned text or propagated exception | Same tool body, around builder + existing exception-to-text handling | No |
| P-03 | `agents/tools.py:get_indicators`, inside the split-indicator loop | Each lowercased split indicator, effective `as_of` date, `look_back_days` (default 30) | One observation per split indicator execution, never on the final joined string | No |
| P-04 | `agents/tools.py:get_fundamentals` body | Ticker, effective `as_of` date | Same tool body | No |
| P-05 | `agents/tools.py:get_income_statement` body | Ticker, `freq` (default `quarterly`), effective `as_of` date | Same tool body | No |
| P-06 | `agents/tools.py:get_balance_sheet` body | Ticker, `freq` (default `quarterly`), effective `as_of` date | Same tool body | No |
| P-07 | `agents/tools.py:get_cashflow` body | Ticker, `freq` (default `quarterly`), effective `as_of` date | Same tool body | No |
| P-08 | `agents/tools.py:get_insider_transactions` body | Ticker, `trade_date` or known None | Same tool body | No |
| P-09 | Existing call site `agents/tools.py:get_news`; design routes it to the shared news executor with P-09 | Ticker, effective start/end after existing window handling | Shared news executor, first execution only | Yes |
| P-10 | `agents/tools.py:get_global_news` body | Effective `as_of` date; use explicit `look_back_days`/`limit` values when provided, and resolve only omitted/None values from existing `global_news_lookback_days` (default 7)/`global_news_article_limit` (default 10) active config, as the current producers do. Supply these effective values for target binding under §8.3 | Same tool body | No |
| P-11 | `agents/tools.py:get_macro_indicators` body | Indicator, effective `as_of` date; None lookback resolves from the existing `DEFAULT_LOOKBACK_DAYS` (365) | Same tool body | No |
| P-12 | `agents/tools.py:get_prediction_markets` body | Topic, `trade_date` or known None; None limit resolves from the existing `DEFAULT_LIMIT` (6) | Same tool body | No |
| P-13 | Existing call site `agents/analysts/sentiment_analyst.py`; design routes it to the shared news executor with P-13 | Ticker and the existing seven-day prefetch window | Shared news executor, first execution only | Yes |
| P-14 | `agents/analysts/sentiment_analyst.py` direct StockTwits call | Ticker, limit 30, prefetch window, existing screen | Direct-call outer site; StockTwits remains a direct source | No |
| P-15 | `agents/analysts/sentiment_analyst.py` direct Reddit call | Ticker, resolved subreddits, `limit_per_sub` default 5, prefetch window, existing screen | Direct-call outer site; Reddit remains a direct source | No |

The shared news executor is a plain internal function, not a framework API. Its exact name is an implementation detail; it must accept the path ID explicitly from its two callers. The table describes the design attachment points; current code still has separate tool/prefetch implementations and no registry.

Design rules:

- Each position has exactly one observation site. Router and vendor code do not write a second availability record.
- Vendor fallback attempts stay inside one business observation. Tool callbacks remain FR-02 statistics sources, not FR-03 observation sources.
- No global monkeypatch, middleware, dynamic proxy, or automatic inclusion of arbitrary HTTP calls or unlisted direct vendor methods.
- An observation represents a completed supported query result or its existing failure, not an internal HTTP request. Vendor retries/fallbacks remain inside one observation outcome.
- The local helper at the supported site registers the path association, executes the existing function body once with the existing arguments, classifies the final result or exception, and returns the original value or re-raises the original exception. Only an actual execution accepts a completed observation.
- With no active `RunContext`, the helper executes the original body directly and records nothing.
- Observation status is one of `available`, `no_data`, `unavailable`, `withheld`.
- Status recognition follows the normative per-method table in §8.3 and the narrow `DataResultClassifier`. It uses existing types, return structures, and verified producer sentinels; model text is never used, a non-empty string is not success, and an unrecognized format is `unavailable`.
- Existing fallback, withholding, and exception semantics are preserved.
- `get_news` is one method in two paths; the same business query is not split solely by call path.

Early failure and parameter rules:

- The observation boundary starts after control has entered a supported business function. Tool schema validation, an unknown tool name, or message parsing before that point is not an executed data query and receives no fabricated query observation.
- Existing date semantics are preserved. `as_of()` may clamp the requested date to `trade_date` or pass it through; `as_of_window()` may clamp an unreadable end or move a wholly future window back to the trade date. A request that existing logic adjusts is still executed, and the effective values actually passed onward are recorded. No stricter observation-layer validation is added.
- When the original body returns its date-error text before a fetch (for example an unparseable `start_date` from `as_of_window()`), record only a private `availability_call_failures` note with a fixed parameter/date category and short reason. Do not create a query key, window, `CompletedObservation`, completion sequence, or FR-01 entry. Return the original text unchanged.
- If the original body raises before a fetch, record the same kind of private call-failure note and propagate the original exception unchanged. Observation handling never replaces it.
- For P-03, date normalization happens before splitting. If it rejects the call, one private P-03 call-failure note may describe the parameter failure; no split indicator was fetched, and no per-indicator observations are fabricated. After a successful split, each indicator has its own execution and observation; the final joined string is never classified once.
- Effective defaults use existing code: P-10 reads `global_news_lookback_days`/`global_news_article_limit` from active config when its arguments are None; P-11 uses `DEFAULT_LOOKBACK_DAYS` (365); P-12 uses `DEFAULT_LIMIT` (6); P-14 uses limit 30; P-15 uses `limit_per_sub` 5. Do not copy a second default table or change the original call arguments.
- A None trade date or absent optional parameter is recorded as known-null/absent, never as an infinite window. Router paths do not infer a winning vendor from configuration; source remains known or null under the existing rule. If producers interpret a request parameter differently, record the reliable shared request semantics and the limitation, not a fabricated uniform per-vendor value.
- A call-failure note contains only the supported path ID/method, safe business object, fixed category such as `parameter_rejected`, short reason such as “start_date cannot be parsed,” and a fixed necessary item ID only when the path reliably maps to one. It stores no full raw arguments, arbitrary objects, payloads, configuration, or raw exception text. If the note cannot be recorded, emit an existing safe warning; do not create a fake query, do not set `availability_tracking_error` (no fetch completed), and do not alter a valid result or query mark.
- Completion sequence is assigned only when the registry accepts a completion update, not when the helper is entered, fetch returns, or a callback arrives. Ordinary observation, conservative unavailable observation, and query failure mark share the same lock/sequence. One shared FR-01 execution creates at most one accepted update; each real non-reuse execution creates its own. Network time, wall-clock/monotonic time, callback alignment, and distributed ordering are never used to correct acceptance order.

The observation helper is local and internal. It has no module-level mutable state, plugin registry, monkeypatch, middleware, or public API requirement.

### 8.2 FR-01 query reuse

- Scope: only the `get_news` data-fetch flow reached by P-09 and P-13, for the same ticker and date window.
- Query key: method name plus effective business parameters after a method-specific binding of positional/keyword arguments and declared defaults. Keyword order is not semantic.
- Current code has the News tool and sentiment prefetch as separate date-handling/router flows. The design uses one plain internal news executor called explicitly by the News tool with P-09 and by sentiment prefetch with P-13. It performs the existing date/window handling, forms the effective ticker/window key, registers the path association, and enters single-flight. The first execution calls the router once through the local observation helper; waiters/cache hits do not observe again. No outer tool or sentiment wrapper also records that news query.
- If news date/window validation fails before a legal fetch key exists, the executor returns the original error text or propagates the original exception and does not create a single-flight entry. It records at most one private P-09/P-13 call-failure note with the fixed parameter/date category and short safe reason; this is not a query observation, completion sequence, or query mark. If even that note cannot be recorded, it warns. It does not invent a legal window, cache entry, or map the invalid window to an earlier valid one.
- No alias inference, fuzzy matching, list reordering, cross-method merge, or cross-run state.
- First caller starts one existing data-fetch flow; later/concurrent callers reuse its outcome.
- Single-flight waiters receive the value or the same failure type/reason. No production deadline/cancellation protocol is added.
- A mutable result is copied per consumer, or stored in an immutable/serialized form, so one consumer cannot pollute another.
- A reuse hit preserves the original FR-03 status, reason, and source; it does not create a new observation or completion sequence.
- Existing vendor caches remain and are not FR-01 reuse.
- `QueryReuseService` is owned by `RunContext`; no module-level global reuse state.
- The shared news executor receives its internal path identity explicitly from its caller. It is not inferred from the shared function name, a tool callback, the model, or process-global state. This covers both the P-09 tool call and the P-13 sentiment prefetch.
- Path identity does not enter the model-visible business parameters or the query key. Concurrent tasks must carry their own path identity without cross-task leakage. A narrow internal argument or a scoped binding may be used; the exact framework integration remains pending verification.

### 8.3 FR-03 availability summary

Observation record:

`CompletedObservation` fields:

| Field | Meaning |
|---|---|
| `method` / `object` / `range` | Effective business query identity and display context |
| `query_key` | Method plus effective business parameters only; never a call path |
| `executing_path_id` | The supported path that started the shared execution; P-01–P-15 |
| `source` | Actual source when reliably known; otherwise unknown/null |
| `status` | `available` / `no_data` / `unavailable` / `withheld` |
| `reason` | Short safe reason |
| `completion_sequence` | Run-local increasing order assigned when the registry accepts a completion update |

Internal path-association map (conceptual only; not a persistent object):

| Field | Meaning |
|---|---|
| `query_key` | Same method-plus-parameters key; path is excluded |
| `supported_path_ids` | Supported P-01–P-15 paths that actually requested this query in this run |

The registry stores a simple `query_key → set of supported path_id` map. No persistence object, association ID, event log, hit counter, or history interface is added.

Association rules:

- A path association may be recorded when the supported observation site begins the query, before a completed result exists. It does not produce a completion sequence and does not change status, reason, or source.
- Only a path association with no completed observation is not `available`; it cannot fabricate a completed result.
- `executing_path_id` identifies the first caller that started the shared execution. Other requesting paths belong only in `supported_path_ids`.
- If the implementation retains a field named `path_id`, it is an alias for `executing_path_id` only and never represents all requesting paths.
- No hit-event log, call count, or query-execution statistic is added.
- Different objects, windows, methods, or effective parameters remain different queries; path association never merges them.

Classification contract:

`DataResultClassifier.classify(method, effective_params, raw_result_or_exception, source_hint)` returns status, short safe reason, and source. `source_hint` is supplied only by a supported site/direct producer that knows the source (a direct fetcher or single-vendor path); it is never inferred from configuration. The classifier preserves the original return or exception. It does not fetch, call a model, infer a vendor from configuration, or use generic keyword guessing. A non-empty string is never sufficient for `available`. If a result does not match a verified producer branch, the conservative status is `unavailable` with reason `unrecognized result format`; it is not marked available.

Composition order:

```text
Shared news executor called with P-09 or P-13
  → existing parameter/date handling
  → query identity and actual path association
  → run-scoped single-flight
      First caller:
        execute the existing fetch/fallback once
        preserve its original value or exception
        → try DataResultClassifier + accept one CompletedObservation
             normal or conservative observation accepted: record by query
             registry acceptance failed: record a query-level failure mark
             no identifiable query or no fallback record: current summary unavailable
        → always publish shared completion (original value or failure)
        → return the original value or propagate the original failure
      Waiter / cache hit:
        reuse original result or failure
        → no new CompletedObservation, completion sequence, status, reason, source, or failure mark
        → never receive the observation-handling exception
```

- On the normal path the completed observation is accepted before the shared completion is published, so a consumer cannot receive a result while the summary still lacks its observation.
- The shared completion is published for normal results and original fetch failures. Observation handling never gates publication or leaves waiters waiting.
- An observation-handling exception never replaces the original fetch value/exception, never triggers a refetch, and never reaches waiters as their result.
- An internal vendor failure is not automatically a final failure; the router may fall back and return usable data.
- A same-target fallback that finally succeeds may be `available`. Internal fallback does not create a separate completed observation.
- An FR-01 reuse hit preserves the original status, reason, and source and does not create a new observation, sequence, or failure mark.
- P-09 and P-13 share the same business query result through FR-01, while both path identities are associated.
- FR-03 does not require FR-01 to be enabled. Without reuse, every actual execution completion creates its own observation. The logical query identity is still method plus effective parameters independent of call path, so P-09 and P-13 observations for the same query update one logical query; the last accepted update is used, and success/failure may replace each other. Association sets do not replace acceptance order.
- When FR-01 is disabled, the local observation helper applies the same isolation: observation handling cannot replace the fetch result/exception and is not a reason to fetch again.
- No classifier path adds a retry, refetch, model call, or cache scope.

Observation failures and query-level fallback:

- A normal `unrecognized result format` returned by the classifier is an existing `unavailable` classification. It is not an observation-handling failure.
- An exception inside the classifier is an observation-handling failure, not a fifth query status. When the query key is known and the registry accepts it, the local helper creates one conservative `unavailable` observation with a short “availability classification failed” reason and known source or null. This observation participates in normal matching and the shared acceptance order.
- An exception inside the registry while accepting a normal or conservative observation is also a query-level handling failure. The registry stores a small run-local failure mark keyed by `query_key` with a short safe reason. The mark and conservative observation do not store raw payloads, complete configuration, or unhandled exception text. This is not a public interface, history ledger, persisted state machine, or global veto.
- Normal observations, conservative `unavailable` observations, and query failure marks are updates under the same local registry lock and one run-local acceptance sequence. For the same query key, the later accepted update replaces the earlier accepted update, whether the later update is a result or a mark. A query mark is not cleared by another query's success. No external completion time, wall/monotonic clock, distributed ordering, event log, or persistent sequence protocol is used to decide this order.
- While marked, the summary decision view does not use an earlier success to prove the query available. It reports that the query's availability cannot be confirmed, not `no_data` and not “never executed.” The original four query statuses remain unchanged.
- A marked query is replaced only by a later accepted update for that same query; no query, retry, or repair is added to clear it.
- Different objects, windows, methods, and effective parameters remain different queries; a failure mark never expands to the whole method.
- Use the existing safe warning mechanism. Do not add a diagnostic file, repair service, recovery mechanism, or persistent failure ledger.
- If the affected query cannot be identified or the local fallback cannot be recorded, set `availability_tracking_error`; later snapshots return `None`. A snapshot-construction failure alone returns `None` without setting the sticky error.
- A single observation failure that is correctly recorded at query level does not invalidate unaffected registry records or make the entire run permanently unconfirmable.

`availability_tracking_error`:

- This is a private RunContext/availability-observation fact: `null` or a fixed safe reason. It means an observation was actually lost and its affected query cannot be located, or no local query mark could be recorded reliably.
- It is not in `AvailabilitySummary`, not a fifth query status, not a fourth completeness state, not a formal/business gate, and not written to manifest, report state, memory, checkpoint, or a diagnostic file. No public interface is added.
- It is not set for an ordinary data failure, a recordable classifier failure, a successfully recorded query mark, or an explicit supported-call parameter/date validation failure before a fetch. Those keep their existing query-level or parameter failure representation.
- There is no automatic clearing in this round: another query's success or a later successful snapshot call does not clear it. A new analysis gets a new RunContext and starts with `null`, never inheriting the previous run's value. This is not the withdrawn permanent `summary_confirmable` flag: only unlocatable/unrecordable observation loss triggers it.
- Snapshot behavior: when the error fact is set, every later snapshot returns `None`; an older summary is never returned as a new snapshot. If only the current snapshot construction fails while the underlying observations are intact, that call returns `None` without setting this sticky fact, and a later call may construct from complete records.
- The update path should build a safe record before entering the lock. If normal acceptance fails, try the query-level mark; if that local fallback also fails, set the tracking error independently of the failed record write. No transaction log, rollback/double-store framework, retry, or recovery promise is added; memory exhaustion/process termination/arbitrary memory corruption are outside the guarantee.

Pre-fetch call-failure notes:

- `availability_call_failures` is a small private run-local list for supported calls rejected by existing parameter/date handling before a fetch. It lives in the same availability module, separate from the query-keyed mark because no legal query key exists. It is not a query observation, and does not enter `observations`, `CompletedObservation`, query failure marks, FR-01, or the completion sequence.
- It does not overwrite, clear, or invalidate an existing valid observation or query mark. It does not set `availability_tracking_error`, because no query completed and no observation was lost.
- Summary projection: a matching necessary item with no valid completed result remains `not_attempted` with reason “no completed result available; related request was rejected during parameter handling.” A matching supplementary item appears in `supplementary_limitations` with `status = unavailable` and a fixed parameter-failure reason; this is a limitation note, not an executed query result. If a necessary item already has a valid result, the note does not change it.
- A note cannot create `complete`, supply a valid query result, become a necessary gap's completed observation, or be treated as provider `no_data`. Because the supported function was entered but rejected before fetch, the gap reason must not claim “never executed.”
- The note container is private and is not a new `AvailabilitySummary` field, public error collection, persistent ledger, counter, or diagnostic file.

Per-method recognition table:

Legend: A = `available`, N = `no_data`, U = `unavailable`, W = `withheld`. “Source” is the actual source only when the producer makes it reliably known; router results do not expose the winning vendor, so they remain unknown/null.

| Path | Method and effective parameters | Verified producer branches and fixed sentinels | Status mapping | Source | Evidence status |
|---|---|---|---|---|---|
| P-01 Market | `get_stock_data`; symbol, start_date, end_date | yfinance normal header + CSV rows; yfinance empty -> `NoMarketDataError` -> router `NO_DATA_AVAILABLE:`; Alpha Vantage CSV with rows; empty body or header-only CSV; malformed CSV -> `ValueError`; router `DATA_UNAVAILABLE:`; tool date-validation text | A: at least one data row<br>N: empty body, header-only CSV, `NO_DATA_AVAILABLE:`<br>U: `DATA_UNAVAILABLE:`, malformed CSV, date text, other exception | unknown (router does not expose vendor) | Existing branch tests: `test_no_data_handling.py`, `test_ohlcv_*.py`, `test_alpha_vantage_hardening.py`; classifier table test planned, not executed |
| P-02 Market | `get_verified_market_snapshot`; symbol, analysis date, look_back | Normal `## Verified market data snapshot...`; tool catches `NoMarketDataError` -> `NO_DATA_AVAILABLE:`; catches `VendorUnavailableError` -> `DATA_UNAVAILABLE:`; other exception propagates | A: at least one producer-generated price record with parseable date and finite Close<br>N: no such record, or `NO_DATA_AVAILABLE:`<br>U: `DATA_UNAVAILABLE:` or exception | Yahoo (by construction) | Existing `test_ohlcv_latest_bar.py`, `test_graph_end_to_end.py`; classifier table test planned, not executed |
| P-03 Market | `get_indicators`; symbol, indicator, curr_date, look_back | yfinance `## {indicator} values...` with dated values; all values `N/A`/`N/A: Not a trading day...`; Alpha Vantage `## ...`, `No data available for the specified date range.`, `Error: No data returned...`, `Error: 'time' column...`, `Error: Column '...' not found...`; router sentinels. Tool concatenates multiple requested indicators and catches `ValueError`. | A: at least one numeric dated value for that indicator<br>N: all values N/A, known no-data text, `NO_DATA_AVAILABLE:`<br>U: column/format error text, `DATA_UNAVAILABLE:`, exception<br>Record one observation per requested indicator, never classify the concatenated text as one result | unknown | Existing `test_graph_end_to_end.py`; per-indicator classifier table test planned, not executed |
| P-04 Fundamentals | `get_fundamentals`; ticker, curr_date | yfinance normal `# Company Fundamentals...`; yfinance empty -> `NO_DATA_AVAILABLE:`; yfinance/Alpha Vantage withheld text `Profile fundamentals are withheld for this date.`; Alpha Vantage OVERVIEW JSON text; router sentinels | A: at least one producer-recognized non-empty basic-information field beyond a heading or placeholder<br>N: no such field, `NO_DATA_AVAILABLE:`, empty JSON object<br>U: `DATA_UNAVAILABLE:`, malformed non-JSON, exception<br>W: withheld phrase | unknown (both vendors can produce withholding) | Existing `test_fundamentals_lookahead.py`, `test_fundamentals_units.py`; AV empty-JSON fixture planned, not executed |
| P-05 Fundamentals | `get_income_statement`; ticker, freq, curr_date | SEC EDGAR normal CSV or `NoMarketDataError` (`not a US SEC filer`, `no us-gaap facts`, `no {freq} ... filed`); yfinance normal CSV or `NoMarketDataError`; both withheld text `Income Statement data is withheld for this date.`; Alpha Vantage statement JSON with `annualReports`/`quarterlyReports`; router sentinels | A: CSV with at least one data row or at least one report row in either returned array<br>N: header-only CSV, `NO_DATA_AVAILABLE:`, both AV arrays empty/absent<br>U: `DATA_UNAVAILABLE:`, malformed body, exception<br>W: withheld phrase | unknown | Existing `test_sec_edgar.py`, `test_fundamentals_lookahead.py`; AV empty-array fixture planned, not executed |
| P-06 Fundamentals | `get_balance_sheet`; ticker, freq, curr_date | Same producer families as P-05; withheld text `Balance Sheet data is withheld for this date.` | A/N/U/W as P-05 | unknown | Existing `test_sec_edgar.py`, `test_fundamentals_lookahead.py`; AV empty-array fixture planned, not executed |
| P-07 Fundamentals | `get_cashflow`; ticker, freq, curr_date | Same producer families as P-05; withheld text `Cash Flow data is withheld for this date.` | A/N/U/W as P-05 | unknown | Existing `test_sec_edgar.py`, `test_fundamentals_lookahead.py`; AV empty-array fixture planned, not executed |
| P-08 Fundamentals | `get_insider_transactions`; ticker, trade_date | yfinance normal `# Insider Transactions data...`; `No insider transactions reported for symbol '...'`; `VendorUnavailableError` when unreachable; yfinance/Alpha Vantage withheld text `Insider transactions are withheld for this date.`; Alpha Vantage JSON text | A: CSV with at least one data row or non-empty AV data<br>N: header-only CSV, no-insider text, empty AV data array<br>U: `DATA_UNAVAILABLE:`, malformed body, exception<br>W: withheld phrase | unknown | Existing `test_yahoo_rate_limit.py`, `test_fundamentals_lookahead.py`; exact AV empty-data shape pending |
| P-09 News | `get_news`; ticker, start_date, end_date | yfinance normal header `## ... News`; `No news found for ...`; `<Yahoo Finance news unavailable for ...>`; `coverage_gap` unavailable text; `VendorUnavailableError` with no feed/no tagged article -> router fallback/sentinel; Alpha Vantage NEWS_SENTIMENT JSON with `feed`; router sentinels | A: at least one actual producer-generated article entry (for example a formatted `### ... (source: ...)` entry) or non-empty AV feed entry<br>N: `No news found`, empty AV feed<br>U: unavailable/coverage-gap text, `DATA_UNAVAILABLE:`, malformed body, exception<br>W: none | unknown | Existing `test_news_lookahead.py`; AV feed-empty fixture and classifier table test planned, not executed |
| P-10 News | `get_global_news`; curr_date, look_back_days, limit | yfinance normal `## Global Market News...`; `No global news found...`; `coverage_gap` unavailable text; Alpha Vantage NEWS_SENTIMENT JSON `feed`; router fallback/sentinels | A: at least one actual producer-generated news entry or non-empty AV feed entry<br>N: `No global news found`, empty AV feed<br>U: coverage-gap text, `DATA_UNAVAILABLE:`, malformed body, exception<br>W: none | unknown | Existing `test_news_lookahead.py`; AV feed-empty fixture and classifier table test planned, not executed |
| P-11 News | `get_macro_indicators`; indicator, curr_date, look_back_days | FRED normal header + table; header + `No observations for ...`; `FRED series '...' not found.`; `FRED: {guidance}` for invalid alias; `DATA_UNAVAILABLE: optional macro_data...`; missing key -> `DATA_UNAVAILABLE:` | A: normal header + at least one observation<br>N: no-observations text, series-not-found text<br>U: invalid-alias guidance, `DATA_UNAVAILABLE:`, exception<br>W: none | FRED (single configured macro source) | Existing `test_fred.py`; classifier table test planned, not executed |
| P-12 News | `get_prediction_markets`; topic, limit, trade_date | `Prediction-market odds are withheld for {date}.`; normal header with market lines; `No open prediction markets matched '...'`; `Polymarket data is currently unavailable (network error: ...)`; `DATA_UNAVAILABLE: optional prediction_markets...` | A: normal header with at least one market line<br>N: no-open-markets text<br>U: network-unavailable text, `DATA_UNAVAILABLE:`, exception<br>W: withheld phrase | Polymarket (single configured source) | Existing `test_polymarket.py`; classifier table test planned, not executed |
| P-13 Sentiment prefetch | `get_news`; ticker, seven-day prefetch window | Same producer branches as P-09; this is the same business query reached through the sentiment prefetch path | A/N/U as P-09; W: none | unknown | Existing `test_news_lookahead.py` and sentiment prefetch in `test_graph_end_to_end.py`; real-path classifier integration planned, not executed |
| P-14 Sentiment prefetch | `fetch_stocktwits_messages`; ticker, limit, window, optional screen | Normal screened/unscreened summary + message lines; `<stocktwits unavailable: Type>`; `<StockTwits unavailable for ...>`; `<no StockTwits messages found ...>` / `... within ...`; `<none of the N StockTwits messages is about ...>` | A: normal message block with at least one message line<br>N: no-message text, all-screened-out text<br>U: unavailable prefix, coverage-gap text<br>W: none | StockTwits (direct) | Existing `test_stocktwits_resilience.py`; classifier table test planned, not executed |
| P-15 Sentiment prefetch | `fetch_reddit_posts`; ticker, subreddits, window, optional screen | Normal blocks with `r/<sub> — ... recent posts`; `<Reddit unavailable: fetch failed ...>`; `<Reddit unavailable for ...>`; `<no Reddit posts found ...>`; per-sub placeholders `<no posts about ... after screening>`, `<not among the newest ...>`, `<no posts found ...>` | A: at least one sub-block has post lines<br>N: all sub-blocks are no-post/screened/no-match placeholders, or global no-posts text<br>U: Reddit unavailable/coverage-gap text<br>W: none | Reddit (direct) | Existing `test_reddit_fallback.py`; classifier table test planned, not executed |

Minimum-content boundaries:

- A verified snapshot with a valid price record remains `available` even when some indicators are `N/A` or `N/A (...)`; do not require every OHLCV, indicator, or valuation field.
- Fundamentals with at least one recognized non-empty basic field are `available`; do not require every field or a complete profile.
- Ticker/global news with at least one actual article entry are `available`; do not add article-count, relevance, truth, sufficiency, or full-period checks.
- P-01 CSV with only a header has no actual data row and is not `available`. Do not extend this clarification into new CSV rules for unrelated paths.
- A heading, placeholder, error text, or a number found anywhere is not sufficient for `available`.
- If basic data exists and only non-critical parts are missing, remain `available`; do not convert every non-available result to `no_data`.

Unverified or conservative mappings:

- Alpha Vantage `OVERVIEW`, statement, insider, and `NEWS_SENTIMENT` empty-payload shapes are not all represented by dedicated repository fixtures. The design treats an empty JSON object, empty report array, empty `feed`, or empty insider data array as `no_data`, and malformed/non-JSON as `unavailable`; the exact producer shapes must be confirmed before implementation acceptance.
- Alpha Vantage header-only stock CSV classification is derived from `_filter_csv_by_date_range` returning a header-only frame; a direct fixture is still planned.
- Alpha Vantage statement JSON does not use the `freq` parameter in the current producer. The classifier uses the returned report arrays as the producer’s actual output and does not fabricate missing periods or a different frequency.
- Router methods do not expose which vendor served the final result. Actual source remains unknown/null; the configured vendor chain is not used as a substitute.
- `get_indicators` may concatenate multiple indicators in one tool call. Implementation must classify each requested indicator before concatenation. A whole-string non-empty check is not a valid classifier.
- If a producer branch cannot be confidently classified, the observation is `unavailable` with `unrecognized result format`, not `available`.
- If final text cannot reliably distinguish a branch after the table is verified, a minimal internal status hint may be passed from that producer branch. This is a future implementation option, not implemented in this round, and must not become a wholesale rewrite of all vendor responses.

`AvailabilitySummary` contract:

The summarizer returns one ordinary JSON-compatible mapping. It is the complete business summary; consumers do not add fields or rebuild completeness.

| Field | Type and content |
|---|---|
| `basic_completeness` | `complete` / `incomplete` / `not_applicable` |
| `applicability_note` | Short explanation of non-applicability; empty string otherwise |
| `observations` | One projection per current logical query: the last effective result selected by existing object/range/effective-parameter and last-completed rules, with `method`, `object`, `effective_parameters`, `executing_path_id`, `supported_path_ids`, `source`, `status` in the four-status set, and `reason` |
| `necessary_items` | Applicable items for enabled analysts: fixed `item_id`, `method`, `object`, `applicable_range`, `status` in the four-status set or `not_attempted` when no completed result is available, and `reason` |
| `supplementary_limitations` | Actually failed or limited supplementary items, including pre-fetch parameter/date limitations, with `method`, `object`, reliable known parameters, known source or null, `status`, and short `reason` |

Rules:

- The field contents serve only current FR-03 semantics; this is not a generic evidence model.
- A query-level failure mark is projected only into the affected current query's observation as `status = unavailable` with a reason such as `availability record failed; cannot confirm`. The projection is a consumer view, not a fabricated stored `CompletedObservation`. It is not exposed as a failure-mark field, a new status, a public registry object, or a source proof.
- A marked query does not reuse an earlier success. A later accepted update for the same query replaces the mark; other queries are unaffected. `necessary_items` use the selected current projection, so a marked necessary query appears unavailable with the safe failure reason.
- `not_attempted` appears only in `necessary_items`, never in `observations` and never as a fake completed record. Display “no completed result available” unless the item is known not to have been invoked; only then say “not executed.”
- Do not store `missing_necessary_items`. The necessary gap is the simple consumer-visible filter over the at most seven `necessary_items` entries whose status is not `available`. That filter is not a second completeness calculation.
- Supplementary limitations never count as necessary gaps and do not change `basic_completeness`. A necessary-item failure is represented in `necessary_items` and is not duplicated in `supplementary_limitations`.
- Different objects, windows, methods, and effective parameters remain different queries.
- The mapping contains no version, hash, digest, source proof, history ledger, or independent schema file.

Completeness is computed once by the summarizer:

- Non-stock or no applicable necessary item: `not_applicable`, with `applicability_note`.
- Every applicable necessary item in `necessary_items` is `available`: `complete`.
- Otherwise: `incomplete`, with the corresponding non-available necessary item and reason supplying the gap. A query-level mark is already projected as that selected item's `unavailable`; completeness does not separately re-check marks. Supplementary limitations do not change this rule.

The external snapshot interface receives `asset_type`, `enabled_analysts`, and the small existing `analysis_context` needed for object/range matching as explicit arguments. `asset_type` comes from `state["asset_type"]`, populated by `Propagator.create_initial_state`: the CLI derives it from the selected ticker through `detect_asset_type()` and carries it in the selections/state, while `propagate(..., asset_type=...)` supplies the explicit existing parameter (defaulting as that API already does). No separate effective-config key or new asset detector is added. `enabled_analysts` is the existing selected-analyst set used to build the graph; the object is `state["company_of_interest"]`, the analysis date is `state["trade_date"]`, and the existing tool arguments provide any additional date/window values. The research wrapper, final-check node, and report path supply these existing values; no new configuration system is added. A `necessity_status` helper may remain internal only and is not called by consumers.

Existing-data source mapping for the seven necessary items (target-binding amendment authorized by the user on 2026-11-23; not Round 3 test-specification pre-approval):

| Necessary item | Object source | Date/window source | Existing direct matching |
|---|---|---|---|
| `get_stock_data` | `state["company_of_interest"]` | First eligible request's effective `start_date`/`end_date` after existing `as_of_window(..., trade_date)` handling | Exact current object and bound start/end; no coverage inference or substitution by another window |
| `get_verified_market_snapshot` | `state["company_of_interest"]` | Analysis date; tool date still follows existing `as_of(...)` handling | Current object and effective date equal to the analysis date; earlier-date calls remain observations, not substitutes. Utility lookback does not create a necessity dimension; returned price rows may be earlier trading days |
| `get_income_statement` | `state["company_of_interest"]` | First eligible request's effective date and `freq`; omitted frequency resolves to existing `quarterly` default | Exact current object and bound date/frequency under existing interface semantics; no annual/quarter substitution |
| `get_balance_sheet` | `state["company_of_interest"]` | Its own first eligible request's effective date and `freq` | Same binding rule, independent of the other two statements |
| `get_cashflow` | `state["company_of_interest"]` | Its own first eligible request's effective date and `freq` | Same binding rule, independent of the other two statements |
| `get_global_news` | Global news item; no ticker object | First eligible request at the analysis date; explicit lookback/limit, or existing active-config defaults when omitted | Exact analysis date and bound effective lookback/limit; earlier-date calls or other windows cannot substitute; ticker news never substitutes |
| `fetch_reddit_posts` | `state["company_of_interest"]` | Existing sentiment prefetch window from `_seven_days_back(trade_date)` through `trade_date`; `subreddits_for(ticker)`; `limit_per_sub` default 5 | Same object and prefetch window; StockTwits does not substitute for the Reddit item |

These rows describe existing sources and matching only. They do not add an asset-identification rule, parameter registry, range-coverage algorithm, or forced query. Target matching happens before the existing last-accepted-result selection; an available query from another object, window, or data item does not substitute for the necessary target.

#### Necessary-target binding contract

- C-07 owns a small private per-run target mapping for applicable enabled necessity items. C-06 supplies effective parameters after existing parameter/date handling and default resolution, before invoking the existing fetch body. Eligibility follows the existing supported interface, current object and the table above; it adds no stricter tool rejection, alias inference, new input/configuration, forced period, or fetch. Rejected parameters do not bind a target and retain the existing private call-failure-note behavior.
- Atomically check/bind an unbound target under the existing registry lock. The first eligible request to acquire that lock wins; a concurrent later requester cannot replace it. Release the lock before fetch. Target binding and path association are request-time facts, not completed observations, and allocate no completion sequence, clock, counter or success status.
- Never rebind an already bound item during that analysis, including on fetch failure, withheld/no-data, or later success for a different window/frequency/date. Each statement binds independently. A previously unbound item may bind on its first eligible later request; snapshots themselves never bind targets.
- Keep query identity and all other-query observations unchanged. Match the target first, then select the last accepted matching observation or query-level mark using the existing completion sequence. A later matching success replaces failure and vice versa; other queries cannot clear the target's failure. Snapshot utility lookback remains excluded only from necessity matching, not from query identity.
- With no target request, or with a target but neither a matching completed observation nor a matching query-level failure mark, the necessary item is `not_attempted` with the existing no-completed-result reason. A matching mark is projected as `unavailable` under the existing failure rule, not `not_attempted`. A bound/in-flight request is not called never started. Do not use another target or a fabricated result to fill the gap. Existing parameter-rejection reasons may still be disclosed as specified by D-08d.
- Research, check-time and terminal snapshots read a consistent copy of the same run's bindings and accepted updates under that lock. Existing bindings do not change between stages; later observations may change results. No new `AvailabilitySummary` field, public binding API, persistent target record, history, cache, retry or FR-01 prerequisite is introduced. Binding state ends with its run.

This resolves the necessity-target design choice only; implementation, producer/attachment verification, and Round 3's concrete test pre-approval remain pending. Asset types outside the existing `stock`/`crypto` paths remain unconfirmed as before.

Summary rules:

- The summary is run-scoped, produced by `AvailabilitySummarizer` from a read-only registry copy, and returned as an independent plain mapping. The mutable registry is not exposed.
- Each accepted update receives the run-local increasing sequence under the registry lock. Concurrent work is ordered by acceptance, not network/wall/monotonic time.
- The summary uses the state from the last accepted update per query as of the snapshot time. Later accepted success replaces earlier accepted failure and vice versa; success is never selected preferentially.
- A query-level failure mark is a local unresolved-query condition, not a fifth status. It is an accepted update in the same sequence. While it is the latest update, an earlier observation for that query does not prove current availability; the decision view states that availability cannot be confirmed. A later accepted update for that query replaces the mark.
- Different windows are retained separately. A necessity item matches the same object and the analysis's applicable range without complex coverage inference.
- An item with no completed result is `not_attempted` in the decision view; it is never fabricated as an execution record or call count. Display it as “no completed result available” unless the item is known not to have been invoked; only then use “not executed”. An in-flight query is not relabeled as never started or successful.
- The seven necessity items are the union for enabled analysts; disabling an analyst removes its item:
  1. `get_stock_data` for the current object and requested range.
  2. `get_verified_market_snapshot` for the current object and analysis date.
  3. `get_income_statement` under existing interface semantics.
  4. `get_balance_sheet` under existing interface semantics.
  5. `get_cashflow` under existing interface semantics.
  6. `get_global_news` for the current news-analysis range.
  7. `fetch_reddit_posts` for the current object and prefetch window.
- Basic completeness: `complete` only when every applicable `necessary_items` entry is `available`; `incomplete` when any applicable entry is `no_data`, `unavailable`, `withheld`, or has no completed result; `not_applicable` when no item applies or the asset is outside stock scope. A query-level mark is already projected into its selected item as `unavailable`, so there is no second mark check. A withheld necessity item does not bypass completeness. A marked supplementary query is disclosed as a limitation but does not by itself change basic completeness.
- Supplementary data (indicators, profile/fundamentals overview, insider transactions, ticker news, FRED, prediction markets, StockTwits) is disclosed when it actually fails; an unqueried supplementary item is not reported item by item.
- Global news does not represent ticker-news availability; ticker-news unavailability is disclosed separately. StockTwits success does not substitute for the Reddit necessity item.
- No forced fetch, automatic refetch, retry, or model re-run on summary refresh.
- A snapshot returns `None` when `availability_tracking_error` is set or when that snapshot construction fails. With the tracking error, later snapshots remain `None`; with only a construction failure, a later call may reconstruct from intact records. A missing snapshot follows SB-01's existing missing/invalid-summary handling. Neither case fabricates a completeness value or adds a business gate; the tracking error is not the withdrawn public `summary_confirmable` state.
- FR-03 does not write a formal rating or create a new gate condition.
- Consumers:
  - Research stage: the wrapper obtains one summary at research start, renders its program block for the first Bull call, and stores it as `research_availability_summary`. Later Bull/Bear rounds and the Research Manager read that same mapping; they do not refresh, re-aggregate queries, or infer availability from model text.
  - Final check: takes its own current summary and reads `basic_completeness`, `necessary_items`, `applicability_note`, and the necessary-item reasons. It does not read the registry or failure marks and does not recompute completeness.
  - Report: the entry prepares one terminal summary from this run's registry after graph execution and before save/return, and places it in `data_availability_summary` of the report-state/final-state mapping. The writer deterministically displays basic completeness, necessary gaps (by filtering non-available necessary items), and supplementary limitations from that mapping. The writer never obtains a new snapshot. If no valid summary exists, that region says the program summary is unavailable; it does not invent a fourth completeness state. The model cannot overwrite that region.
  - CLI deterministic risk/availability display uses the same prepared final-state summary fields and does not reconstruct the summary; when none exists it says the program summary is unavailable. Showing a previously generated file uses that file's data.
  - Consumers at the same time receive identical content; different-time summaries may differ.
- The deterministic display text is program-generated; model output cannot rewrite structured records or the deterministic availability region.
- A consumer may filter `necessary_items` to find non-available gaps for display or basic contradiction checks; it must not recompute `basic_completeness` or invent another gap list.
- FR-03 does not require FR-01 to be enabled. It records actual query results without a query cache and may reuse the query-identity rule; an FR-01 hit preserves the original status, reason, and source.

#### Research-stage summary attachment

“Research start” is the analyst join immediately before the first Bull Researcher call, not the start of the Research Manager.

```text
Analyst join
  → First research-entry preparation (wrapper around the first Bull call, not a top-level node)
      → snapshot current-run AvailabilityRegistry
      → render a labeled program block deterministically
      → inject it into the same first Bull invocation
      → store research_availability_summary in graph state
  → Bull/Bear debate
  → Research Manager
```

Contract:

- `research_availability_summary` is either the independent JSON-compatible summary mapping as of research start or `null` when none can be formed. The “program summary currently unavailable” text exists only in deterministic rendering, not as a stored third type.
- `null` is not a fourth `basic_completeness` value and does not fabricate a summary. The original analysis materials remain available.
- A small deterministic rendering function produces a clearly labeled program content block. It does not call a model or data source, compress, or truncate.
- The first Bull call receives the rendered block directly. Returning a state update and assuming the current function can read it is not sufficient.
- Subsequent Bull/Bear rounds and the Research Manager read `research_availability_summary` directly from graph state and include the same stage summary as an explicit program block in their prompts.
- The model cannot rewrite structured fields or the deterministic program block. The program summary is not mixed with model-generated analysis as one authority source.
- The full analyst reports remain; the summary is additive and does not replace the reports with briefs.
- Preparation runs only on the first entry to the research stage. A later Bull/Bear round or debate loop does not refresh it.
- Later observations do not rewrite this stage input and do not re-run research.
- The post-PM final check takes its own check-time snapshot. After the formal check, the entry prepares the terminal report/delivery summary from the same run's registry; the report writer itself does not take a snapshot. Neither overwrites the research-stage input. The final program check reads program state, not model prose.
- No new data request, model call, seal, versioned view, or second completeness authority is added.

Checkpoint interaction:

- The new flow always executes research from its normal entry and never resumes a checkpoint. A checkpoint-enabled configuration only emits the no-resume notice; old checkpoint material is not used as current research or final-check evidence.

### 8.4 FR-04 purchase risk

Input transport:

- Optional `purchase_scenario` keyword for `propagate()` and optional CLI `--purchase-scenario <json-file>`.
- An explicitly provided scenario file that cannot be read or parsed is a caller parameter error before run creation (or a controlled setup error). A file that is not provided is distinct from that failure: the absence is passed to FR-04, and an applicable stock Buy/Overweight then gets structured `blocked` without an entry hard failure.
- After successful input acquisition, business-invalid fields, a mismatched object/ticker, or an invalid explicit threshold are FR-04 results, not entry pre-validation hard failures.
- The evaluator receives the current analysis ticker explicitly. It does not read a global, parse a report, or infer the ticker from the scenario.
- The existing `PortfolioContext` is not a source for scenario fields. `average_price`, model text, and network lookup are never used to fill a missing scenario value.

Scenario and threshold contract:

| Field | Constraint |
|---|---|
| `ticker` | Matches the analysis ticker under existing pure ticker normalization (`normalize_symbol`); no network identity lookup |
| `portfolio_value` | Finite decimal, greater than zero |
| `current_position_value` | Finite decimal, between zero and `portfolio_value` inclusive |
| `proposed_buy_value` | Finite decimal, greater than zero |
| `entry_price` | Finite decimal, greater than zero |
| `stop_loss_price` | Finite decimal, greater than zero and less than `entry_price` |
| `currency` | Non-empty common currency label for the amounts and prices |
| `max_projected_weight` | Finite decimal, greater than zero and at most one |
| `max_stop_distance` | Finite decimal, greater than zero and less than one |

Common rules:

- Reject booleans, NaN, Infinity, missing values, and unparseable values.
- Accept ordinary decimal notation. No special length, trailing-zero, or canonical-grammar requirement is added.
- Use `0.30` / `0.05` only when the threshold is omitted. An explicitly invalid threshold is blocked and never falls back to a default.
- Do not add cash sufficiency, fees, slippage, marketability, liveness, account truth, account completeness, currency conversion, order execution, or order-type checks. No additional scenario fields such as cash, quantity, `valuation_price`, `valuation_time`, `candidate_id`, `order_count`, or provenance are required or added. The structure remains one stock, one unlevered purchase/add-long; no derivative, leverage, or multiple-order model is added.
- A mismatched ticker, each invalid field, or an invalid threshold produces `blocked` and names the field or configuration category; no unhandled divide-by-zero or numeric error escapes.
- The thresholds are classroom demonstration defaults, not approved financial policy. Every result states this.

Judgment order:

1. Legal model rating check.
2. Asset/rating applicability.
3. Applicable scenario and threshold validation.
4. Legal metric calculation and comparison.
5. Structured result.

Applicability:

| Case | Result |
|---|---|
| Stock + Buy/Overweight with a valid scenario | Evaluate both rules |
| Stock + Buy/Overweight with missing or invalid scenario | `blocked`; never `not_applicable` |
| Stock + Hold/Underweight/Sell | `not_applicable` |
| Non-stock asset + legal rating | `not_applicable`; stock scenario rules are not used |
| Missing or illegal rating | `blocked`; not disguised as non-applicability |
| Unexpected evaluator exception | `error`; never `passed` |

Numeric handling and exact decision:

- **Evaluator internal representation**: legal decimal values are parsed into an exact numeric representation. Use a standard-library exact rational value (for example, `fractions.Fraction`) for the pass/block arithmetic; do not depend on the ambient `Decimal` context.
- **Decision arithmetic**: after type, finiteness, and business-range validation, convert each legal decimal exactly to an exact rational, then perform exact addition, subtraction, multiplication, and comparison:
  - `current_position_value + proposed_buy_value <= max_projected_weight * portfolio_value`
  - `entry_price - stop_loss_price <= max_stop_distance * entry_price`
- Exact rational operations, not default `Decimal` precision, guarantee the cross-multiplication comparison. Do not globally change the Decimal context.
- Equality passes. Exceeding either threshold blocks; when both exceed, both reasons are retained.
- **Scenario/threshold handling**: do not require all raw inputs to be first projected into a persistent normalized state and then parsed back. Perform the necessary conversion at the actual entry and risk-module boundary. If the scenario must be carried in graph state, use a simple JSON-compatible mapping; it is not a new normalization protocol, representation version, digest, or round-trip contract.
- **Result representation**: the risk result is a JSON-compatible object. `scenario` and `thresholds` are display-safe values, `projected_weight` and `stop_distance` are decimal strings or `null`, and `reasons` is a short safe string list. Do not place `Decimal` or `Fraction` objects in the result or graph state, and do not rely on an implicit universal encoder. The new flow does not use checkpoint state.
- **Serialization discipline**: do not use `json.dump(default=str)` or another implicit encoder for risk objects, do not uniformly convert to float, and do not re-decide risk from formatted percentages.
- **Report metrics**: `projected_weight` and `stop_distance` are computed separately from the exact decision. A repeating quotient remains computable and is not `null`. A small local formatting function may choose display precision; fixed decimal places, round-half-even, no-exponent notation, and trailing-zero rules are implementation choices, not architecture acceptance requirements or separate human-approval gates.
- **Display separation**: display rounding happens after the exact decision and never feeds back into the comparison or status. CLI and report consume the same risk result but may differ in normal layout or percentage presentation; character-for-character equality is not required.
- **Invalid raw input**: do not stringify an arbitrary invalid original value. The display-safe scenario omits unsafe/invalid raw values; metrics are null only by their own operand rule; valid thresholds are the only thresholds shown as used.

Input handling:

| Input | Handling |
|---|---|
| JSON numeric token | Parse directly into a decimal value from the token, without a binary-float intermediate |
| Decimal string | Parse through the same local numeric parser |
| `Decimal` | Check finiteness, then reuse the same parser and convert exactly |
| Integer | Exclude bool first, then accept exactly |
| Finite float | Interpret its stable decimal string representation as the supplied value; do not use float arithmetic; the system validates the converted decimal value and cannot restore precision already lost in the caller’s float computation |
| Bool, NaN, Infinity | Reject |

The program interface supports ordinary numbers and decimal strings; `Decimal` can use the same parser. This is not a promise of complete equivalence among arbitrary Python numeric objects. The input and result contracts also do not add special length, trailing-zero, or canonical-grammar limits.

For the cross-multiplication comparison, the relevant denominator is a legal positive value under the scenario contract; no additional exception or special-case protocol is introduced.

Current-code evidence:

- `_log_state()` currently constructs explicit fields and does not yet persist `portfolio_risk_result` (`trading_graph.py:437-475`, ordinary `json.dump`). This is a new type-contract gap in the design, not a claim that the current code already fails to save a Decimal risk result.

Metric nullability:

- `projected_weight` is non-null only when `portfolio_value`, `current_position_value`, and `proposed_buy_value` have legal arithmetic values and the division is defined. A repeating quotient remains non-null and is formatted only for display.
- `stop_distance` is non-null only when `entry_price` and `stop_loss_price` have legal arithmetic values and the division is defined. A repeating quotient remains non-null and is formatted only for display.
- An invalid ticker, currency, or threshold does not by itself null a metric whose arithmetic operands are legal.
- Never compute a metric from invalid operands, and never clear every metric merely because a non-arithmetic field is invalid.

Result fields:

| Field | Meaning |
|---|---|
| `status` | `passed` / `blocked` / `not_applicable` / `error` |
| `analysis_ticker` | The current analysis ticker used for matching |
| `scenario` | Display-safe actually parsable scenario input with numeric values as decimal strings; unsafe/invalid raw values are omitted |
| `thresholds` | Valid thresholds actually used as decimal strings, with the classroom-demonstration note; an invalid explicit threshold is not shown as a valid default |
| `projected_weight` | Decimal string or null; display precision is a local implementation choice |
| `stop_distance` | Decimal string or null; display precision is a local implementation choice |
| `reasons` | Short safe risk-scoped reason list naming the field or configuration category |

Consumers:

- CLI deterministic risk section.
- `final_state` as `portfolio_risk_result`.
- Generated report deterministic section that the model does not rewrite.
- SB-01 consumes the applicable risk status and any necessary explanation from the same result; it does not recompute or re-parse the metrics. It does not reuse the risk reasons by reference or flatten the risk object into the formal fields.
- CLI and report read the same risk result. They do not re-judge risk; normal layout and percentage-display differences are allowed, and character-for-character equality is not required.
- The deterministic risk area states: “Only the listed caller scenario is checked; other amounts and prices in the model proposal are not verified by this check.” It also keeps the classroom-demonstration and non-trade-authorization statements.
- The check uses only the amounts and prices explicitly supplied in the caller scenario. A different set of numbers in the model proposal is not automatically included, compared, or shown as verified, and does not become a new blocked condition or change the model conclusion.
- The manifest does not add risk fields. The existing final-state log is not required to add a complete risk archive; memory is not required to store risk metadata.
- Serialization requirements do not change existing save-failure handling or checkpoint policy.
- `passed` means only that the supplied scenario meets the two checks; it is not a trade authorization.

The evaluator must not hard-fail the analysis entry merely because the scenario is missing or business-invalid; it returns a structured `blocked` result. FR-04 does not change the model rating or write formal result fields. Unrelated existing analysis exceptions keep their original behavior.

### 8.5 SB-01 final check

Inputs: `model_proposal`, `data_availability_summary` from the risk-node check time, `portfolio_risk_result`, asset type. The later terminal delivery summary does not rerun this check.

Top-level output fields:

| Field | Type and rule |
|---|---|
| `model_proposal` | Nested `{rating, text}` or `null`; each inner value is `rating`/`text` or `null`; no `present` boolean |
| `gate_status` | `passed`, `blocked`, or `error` |
| `reasons` | Top-level SB-01 string list; passed may be empty; blocked/error has at least one actual reason; no reason code/priority system |
| `final_rating` | Five-tier legal rating on passed; REVIEW on blocked/error |
| `final_trade_decision` | Non-whitespace formal conclusion; program-generated manual-review notice on blocked/error |

Rules:

- Legal ratings: Buy, Overweight, Hold, Underweight, Sell.
- Missing/illegal model rating or model REVIEW: blocked, final REVIEW, with a top-level reason.
- Model conclusion: it must be a non-whitespace string. Missing, wrong-type, empty-string, and whitespace-only conclusions are ordinary input-condition failures: blocked, final REVIEW, with a program-generated manual-review notice stating the actual reason. They are not handled as SB-01 internal errors. The check may test non-emptiness after stripping surrounding whitespace but must preserve the original valid conclusion unchanged on pass; it does not trim, rewrite, regenerate, or add length/format/quality/factual scoring.
- FR-03 summary read: use only `basic_completeness`, `necessary_items`, and `applicability_note`, plus necessary-item reasons. `complete` passes; `incomplete` blocks with the non-available necessary items and reasons; `not_applicable` does not alone block and keeps the note.
- Summary validation is limited to required field types and legal states. A complete result containing a non-available necessary item is a basic contradiction; an incomplete result with no non-available necessary item or corresponding reason is also a basic contradiction. A missing or invalid summary uses the existing missing/invalid-summary rule. No raw payload, source proof, hash, full-query audit, or new schema gate is checked.
- Supplementary-data limitations are disclosed but do not separately trigger REVIEW and are not necessary gaps.
- FR-04: for stock Buy/Overweight, only `passed` satisfies the risk condition. `blocked`, `error`, missing, illegal, or wrongly `not_applicable` blocks. Other legal stock ratings and legal non-stock ratings do not require the stock scenario check.
- No model text substitution; no FR-04 re-call/re-implementation; no cash/freshness/policy/digest rules.
- SB-01 consumes only the provided summary and risk status. It does not read the registry or query-level failure marks, re-aggregate queries, or change the formal rating from an observation-handling event.
- On passed: formal rating and decision keep the proposal values; not a trade authorization. `reasons` may be empty and no pass reason is invented.
- On blocked/error: `final_rating = REVIEW`; `final_trade_decision` is a program-generated manual-review notice with actual reasons; top-level `reasons` explains why.
- Risk reasons remain in `portfolio_risk_result.reasons`; SB-01 writes its own top-level `reasons` without flattening or overwriting the risk object.
- `model_proposal` remains separately labeled; never the formal conclusion.
- The node catches unexpected internal errors and returns `error`/REVIEW with an actual top-level reason; it does not raise a substitute analysis failure.

### 8.6 FR-05 history read

**Deferred.** No current implementation, acceptance, component wiring or monitor. Retained prior design appears in the future-design archive. Existing baseline statistics and save behavior are not removed.

### 8.7 Run statistics

**Deferred.** No current implementation, acceptance, component wiring or monitor. Retained prior design appears in the future-design archive. Existing baseline statistics and save behavior are not removed.

### 8.8 Concurrency model

| Shared resource | Protection | Scope |
|---|---|---|
| Query reuse registry | Lock + per-query single-flight completion primitive | One run |
| Availability registry | Lock; append with increasing sequence | One run |
| Active RunContext binding | Context-local; restore previous binding on exit | One active run per execution context |
| Memory log | Existing cross-thread/process file lock | Cross-run (existing) |
| Graph state | LangGraph reducers/state updates; no shared mutable RunContext in state | One run |

Analysts may run concurrently. Reuse and availability adapters must be thread-safe; new precise statistics are deferred. The final post-PM nodes run after the graph's existing risk debate and Portfolio Manager, so they are not concurrent with analyst data calls. Any future new-statistics callback propagation belongs to deferred D2 OQ-16; current baseline callbacks are retained.

---

## 9. Security and permissions

### 9.1 SR-01 credential protection

Supported scope only:

1. Existing report and final-state configuration summaries.
2. CLI endpoint preference save/load.
3. Existing `get_scrubbed()` request-error paths in `dataflows/net.py`, Alpha Vantage `common.py` and its notice helper, and FRED `fred.py` including the passthrough 400 `error_message` path.
4. Warnings from these handlers.

Rules:

- Configuration summary reuses `run_settings()` allowlist. Credential fields do not enter the summary.
- Known credentials are only values configured or used by this application in this run; no collection of all environment variables and no credential registry file. Empty strings do not match; IF-21 defines the literal exact-substring matching contract; no long-string or provider-key heuristic.
- If an allowlisted field contains a known credential as defined by IF-21, omit the entire affected field.
- Endpoint preference: do not save/restore endpoints with userinfo, query, fragment (including an explicit empty separator), a known credential in host/path, or an unparseable form. Omit the item and require re-entry; do not save a masked pseudo-endpoint; do not strip query/fragment and save a different address; do not modify `.env` or migrate credentials.
- Supported request errors: replace known credentials with a fixed marker (`***`); do not reattach unprocessed request/response objects, exception chains, or raw bodies; preserve safe error category and necessary diagnostics.
- Handling failure: omit the field or use a fixed safe message; no raw sensitive fallback; no hard exit.
- Out of scope: model-generated report bodies, arbitrary third-party logs, raw debug/stream output, complete API return objects, historical files, recovery material, future outputs.
- Existing `get_scrubbed` and `.env` 0600 behavior are retained as existing protections, not claimed as new results.

### 9.2 SR-02 path confinement

**Deferred FR-02/FR-05/SR-02 only.** Prior controlled manifest/history path design is archived. Keep existing ticker-safe-component checks and user-explicit report save behavior unchanged; no new generic path system.

### 9.3 Coding-agent permissions

The full whitelist is defined in [`docs/architecture/permission-model.md`](docs/architecture/permission-model.md). This summary reflects the current design constraint:

- Default: no read and no write.
- Each role has explicit path allowlists and read-only/frozen paths.
- Human-maintained: `docs/req/**`, `goal.md`, `baseline/**`, `.github/**`, governance configuration, `.env*`.
- Architecture agent: write only `architecture-blueprint.md` and `docs/architecture/**`; no application code.
- Implementation agent: write only approved application/test paths after human approval; read requirements and architecture.
- Verification agent: read-only repository; write only declared test/report paths.
- Enforcement limits: tool-level permissions are not an OS security boundary; CI path checks and human review are required. No governance configuration is changed by this design.

Application runtime permissions remain separate: the AI has no trade-execution authority; SB-01 is the formal recommendation authority; risk evaluation is caller-scenario-based, not account verification.

---

## 10. Observability and verification

### 10.1 Runtime observability

| Signal | Location | Use |
|---|---|---|
| Availability/risk/formal fields and safe diagnostics | Existing state/report/CLI outputs | Current FR-03/FR-04/SB-01/INV-01/SR-01 observability |
| Availability summary and basic completeness | Graph state, final report, deterministic CLI section | FR-03 |
| Risk status, safe input, metrics, thresholds, reasons | CLI, `final_state`, report | FR-04 |
| Gate status, reasons, formal rating/decision | `final_state`, CLI, report, state log | SB-01, INV-01 |
| Memory decision rating/body | Existing memory log | INV-01 |

No new metrics backend, tracing service, diagnostic database, or warning file is added. When a requirement has no suitable runtime monitor, the trace matrix will state the reason and use test/evidence instead.

### 10.2 Verification strategy

| Layer | Planned verification |
|---|---|
| Pure unit | C-08 risk evaluator boundaries/negatives and the C-09 final-checker truth table: implemented and offline-verified under Round 1 and Round 2 respectively. Remaining pure-unit intents are planned: query identity/single-flight; availability mapping/latest-result; manifest timing/atomic writes; stats usage rules; history filters/order/errors; sanitizers and path guard |
| Graph integration | Offline fake model/data; PM proposal only; risk and final check nodes; formal fields; no extra model/data call; recursion limit; the new flow starts from a new initial state and does not resume a checkpoint |
| Full-execution checkpoint policy | Both entries use fresh ephemeral scope and initial state and execute the full graph. No old checkpoint acquire/resume/read/delete; both checks execute. No new persistent run_id is required. |
| Formal result contract and delivery | SB-01 branches use the same five top-level fields; risk reasons and top-level reasons do not overwrite each other; merged graph/CLI state contains complete fields; consumers do not generate a formal rating from proposal text; missing formal output is an execution contract failure, not a normal REVIEW; actual outputs use the same formal rating and decision; missing/invalid SB-01 input produces complete blocked/REVIEW and a handled exception produces complete error/REVIEW |
| FR-04 numeric and result contract | Equality passes, a small over-limit blocks, and double over-limit keeps both reasons; display rounding does not change status; invalid input and explicit invalid thresholds are handled; each metric's nullability follows its own operands; a different set of model numbers does not change the calculation or appear verified; both entries, CLI, final_state, and report consume the same risk result; no model/network call is added; expected values are independent of the evaluator; save-failure and checkpoint policies are unchanged |
| Research-stage context delivery | The first research call actually receives the research-start FR-03 summary; later research roles receive the same stage summary; full reports, identity, language, tool-message relationships, and structured-output paths remain; summary attachment adds no model call and triggers no query or research re-run; the Portfolio Manager proposal does not become the formal result |
| Context limitations | Context budgets, compression thresholds, and compressed-constraint reinjection are deferred by ADR 001 D-10c and are not current acceptance; existing role inputs/client limits/error paths remain; no arbitrary-length success or token/cost benefit is claimed |
| Observation ordering and minimum content | Interleaved updates use registry acceptance order to decide the latest result; ordinary observations and query marks share that sequence; a later accepted update for one query replaces its earlier mark without affecting another query; a recordable supplementary failure is disclosed but does not alone cause REVIEW; different objects/windows/queries do not contaminate each other; original fetch result/exception and FR-01 waiter semantics remain; minimum-content rules still distinguish unavailable from available |
| Tracking error and snapshots | A local fallback failure sets `availability_tracking_error`, and every later snapshot returns `None` rather than an old complete summary; a single snapshot-construction failure returns `None` but does not set the sticky error, and a later snapshot may reconstruct; a new run starts with no inherited error; consumers see only missing/invalid summaries and never read the tracking fact; no query/retry/model call is added |
| Pre-fetch parameter failures | Existing date adjustment/rejection semantics are unchanged and no stricter validation is added; a rejected pre-fetch call creates no valid query, observation, sequence, FR-01 entry, or tracking error; it does not overwrite a prior valid result; a necessary item without a valid result stays `not_attempted` with a parameter reason; a supplementary failure is disclosed without alone blocking; P-03 early failure creates no per-indicator fake records; original return/exception is preserved and the summary uses only fixed safe reasons; no extra fetch/retry/model call is added |
| AvailabilitySummary producer/consumer | The summarizer is the only completeness calculator; completeness uses only the selected `necessary_items` and does not separately re-veto marks; seven mappings and three states are correct; supplementary limitations are not necessary gaps; failure marks appear only as affected query `unavailable`; research stores a summary mapping or `null`, never a sentinel object; later updates do not change an existing research snapshot; same-time consumers agree; SB-01 does not recompute completeness; report rendering is not model-overwritten; no query/model call is added |
| Statistics handler and propagation | Deferred FR-02/IR-15 only; no current new collector, usage accounting or callback propagation acceptance. Existing baseline callbacks are retained. |
| Report availability source | A result added after research start appears in the run-in report; returned final_state contains this analysis's terminal summary; saving A after consecutive A/B analyses does not use B's data; independent save does not access active registry, query, or rerun; Markdown and HTML use one prepared input; missing summary is disclosed without a fake state; availability refresh does not change formal fields; independent save creates no new scope |
| Path observation attachment | All 15 paths have exactly one attachment site; early returns are observed without missing the outcome; router/vendor and callback layers add no duplicate observation; each split indicator is observed separately; P-09/P-13 with the same query cause one fetch, one observation, and two path associations; direct StockTwits/Reddit prefetches are covered; internal fallback attempts add no business observation; original return/exception/call count behavior is retained; no active run produces no new observation behavior |
| FR-03 completion and path association | P-09/P-13 same parameters: one fetch, one completed observation, both paths associated; different windows do not merge; concurrent success and failure release waiters; cache hit preserves sequence/status; observation is visible before shared result; association alone is not success; FR-03 works without FR-01; path identity is absent from model parameters and query key |
| FR-03 per-method recognition | Each of the 15 paths and 14 methods: success, empty, unavailable/not-configured, withheld, and exception; non-empty error text is not success; fallback, FR-01 reuse, no completed result, object/window isolation, indicator concatenation, and necessity versus supplementary distinction; expectations come from an independent fixture table, not the classifier’s own output |
| Resource cleanup ownership | Acquiring scopes close streams/resources exactly once on normal/error/save-failure paths. Attempt remaining cleanup; preserve primary error over cleanup error; restore prior binding. No clocks, stats snapshot, manifest write or persisted terminal status. |
| Run creation and object lifecycle | Both entries bind ephemeral scope after effective config/basic validation and before the first supported data call. Constructor-only use creates none; no constructor-timing obligation is added. Constructor alone owns no analysis scope. Explicit delegation shares scope, independent calls isolate reuse/availability. Scope failure preserves original error; no new run_id/count/timing/status obligation. |
| Entry integration | CLI and propagate normal/failure paths; current scenario/threshold passing; real availability/risk/check flow; IF-19, terminal summary, original saves and scope restoration; unchanged return shape. No manifest/history/new-stat acceptance. |
| Output consistency | CLI streaming sections, immediate files, final report, final state, state log, memory, return value; waiting/unchecked/failed labels |
| Security regression | Existing `test_get_scrubbed`, `test_safe_ticker_component`, relevant preference/report tests; new limited-scope negatives |
| Static checks | No formal-value decision/generation outside SB-01; pass-through/merge/save of unchanged values is allowed and is not treated as a second authority; no model/data call in FR-04/SB-01; no RunContext in graph state/checkpoint; no credential fields in summaries |

With the exceptions of the Round 1 C-08 offline core (`test/offline/test_fr04_risk.py`) and the Round 2 C-09 offline core (`test/offline/test_sb01_final_check.py`), no test in this list has been executed for this design. Other existing test files are baseline assets, not new acceptance.

### 10.3 Evidence state

- Static code analysis: complete for the paths cited in this blueprint.
- Requirement count: independently checked against the YAML.
- Baseline: existing behavior only; data coverage was incomplete in the recorded run.
- C-08 FR-04 core: implemented as the module-level callable `evaluate(...)` in `src/tradingagents/portfolio_risk.py` and offline-tested by `test/offline/test_fr04_risk.py` under the Round 1 approval (`docs/plans/round-01.md @ a8ec42ecdf4199f91d3001fc6e2b1e887a0c5e41`; RM-7-R1). This covers FR-04-FC01–FC04 and the core portion of IR-14 only.
- C-09/IF-09 core: implemented as the module-level callable `evaluate(proposal, availability, risk, asset_type)` in `src/tradingagents/final_recommendation.py` with no default parameters, and offline-tested by `test/offline/test_sb01_final_check.py` under `docs/plans/round-02.md @ 8ad99c25ea1acd77b6e019fbe3c357899e8fc535`. PR #10 reviewed H `fbba457a9235ef53de52604f9b591aaf89a1972b` and merged M `cc8b17596a81751bd6165899423dd511e93dc394`. This covers SB-01-FC01–FC04 and local IR-01/IR-02 responsibility only.
- FR-03 attachment feasibility: the external isolated probe recorded in [Round 3 partial draft](docs/plans/round-03.md#3-isolated-attachment-feasibility-confirmed) passed 21 attachment probes and 36 related regressions on 2026-11-23. Context propagation, explicit P-09/P-13 entry, same-call first-Bull preparation, passed-state report delivery and no-resume adapters were feasible with controlled fixtures. This is not an implemented FR-03 producer, a complete FC test result, real-model semantic evaluation or implementation approval.
- Remaining new behavior, including the production C-09 node/consumer wiring, SB-01-FC05, full SB-01, global IR-01/IR-02/IR-03/IR-04, IF-19, FR-03 producer, FR-04-FC05, complete IR-14, entry/graph/report/state/memory integration, availability, manifest, history, and statistics: not implemented, not tested, not measured.
- Performance/cost: no target approved; PR-01 and CR-01 remain deferred.

---

## 11. Change policy

### 11.1 When to update artifacts

| Change class | Required updates |
|---|---|
| Formal-result authority, component responsibility, interface, requirement semantics, or security boundary | Architecture review; update the affected ADR, blueprint, and directly affected invariants, trace matrix, runtime policy, or tests |
| Internal naming, file layout, or refactor with no semantic change | No automatic D2 rewrite; update a document only if it mentions the changed name or structure |
| Implementation detail within an approved interface | Update the applicable tests and trace/evidence entries; do not rewrite unrelated architecture |
| Deferred requirement activation | New human decision, requirements revision, re-open only the affected architecture and tests |
| Governance, agent permissions, or security-critical behavior | Human approval retained; never changed by an implementation agent alone |

Update artifacts by actual impact, not as a mandatory full-D2 checklist.

### 11.2 Re-open conditions

- A requirement changes the final authority, entry-point set, or output consumers.
- A supported data path is added/removed, its actual call location changes, or its existing semantics/default parameter handling changes.
- Acceptance-order semantics, pre-fetch call-failure note behavior, query-level failure-marker behavior, `availability_tracking_error` triggers/lifecycle, basic-completeness rules, the `AvailabilitySummary` field contract, or report availability ownership/preparation timing change.
- A future requirement asks the new flow to resume interrupted analyses; reopen the ADR before designing identity, observation inheritance, statistics, or formal-result semantics.
- The top-level formal field set, field types, or reason ownership changes.
- A requirement adds a unified context assembler, cross-role normalization, input budgets, automatic trimming/compression, or different role input obligations.
- A future decision approves context compression; its design must preserve role tasks, required evidence, and trusted FR-03 program facts.
- A security scope expansion is requested beyond SR-01/SR-02.
- A deferred requirement (FR-06/FR-07/PR-01/CR-01) is activated.
- Evidence shows the two deterministic nodes cannot fit the recursion limit or the existing graph contract.

---

## 12. Deferred requirement boundary

| Requirement | Current status | Architecture treatment |
|---|---|---|
| FR-02 run manifest | Deferred | No native manifest, new precise statistics, persisted run-status/timing or output-registration work in current implementation/acceptance. |
| FR-05 history lookup | Deferred | No reader/list/get API, registration, index or history task in current implementation/acceptance. |
| SR-02 manifest/history path confinement | Deferred | No new manifest/history-specific path helpers or tests; existing ticker protection and explicit user-selected save behavior remain. |
| FR-06 local report recovery | Deferred | No recovery component, task material, auto-recovery, CLI flow, placeholder seam, or interface promise is designed. |
| FR-07 analyst briefs | Deferred | No analyst-generated brief field, character limit, full-report replacement, or token/cost claim is added. The current FR-03 research-stage program summary is separate and does not activate FR-07. |
| PR-01 manifest overhead measurement | Deferred | No threshold, benchmark, low-overhead claim, or reserved measurement interface. Activation requires a new decision and measurement plan. |
| CR-01 brief cost comparison | Deferred | No cost formula, price input, OFF/ON experiment, or saving claim. |

These items must not be presented as current acceptance, implementation, or evidence.

---

## 13. Open decisions and risks

### 13.1 Open decisions for review

| ID | Decision | Current proposal | Status |
|---|---|---|---|
| OQ-01 | Exact CLI flag/file shape for `purchase_scenario` | `--purchase-scenario <json-file>`; optional `purchase_scenario` kwarg | Pending before entry implementation; parameter/input form and file read/parse error contract remain unconfirmed |
| OQ-02 | Threshold configuration key names | `max_projected_weight`, `max_stop_distance` | Key names decided by the current user instruction; no other configuration mechanism is approved |
| OQ-04 | Existing CLI save/display behavior and terminal summary timing | Preserve existing interaction; prepare terminal summary before its consumers; no manifest timing | Verification only; a new interaction decision is needed only if baseline behavior is intentionally changed |
| OQ-07 | Coding-agent role names and whitelists | Four-role proposal | Pending D3-stage confirmation and implementation |
| OQ-08 | Recursion-limit reservation size | Reserve at least four post-analyst steps | Pending technical verification; four steps is not a product acceptance value |
| OQ-16 (deferred) | Future new-statistics callback propagation | If FR-02 is reactivated, verify handler propagation and call-ID/usage extraction without a global collector | Future FR-02 only; no current task or blocker |
| OQ-12 | Unverified FR-03 producer branches | Confirm Alpha Vantage empty JSON/feed and header-only CSV shapes with finite, sourced samples; unrecognized formats remain `unavailable` until confirmed | Pending verification; no generic recognizer, network probe, or vendor call is added |
| OQ-13 | Shared news executor and research-wrapper integration | Confirm the plain internal news executor calls from P-09/P-13, explicit path argument, and first-Bull wrapper mechanism without a framework API claim | Isolated attachment feasibility confirmed with explicit P-09/P-13 entry and same-call first-Bull input (Round 3 partial draft); production integration, full verification and test pre-approval remain pending |
| OQ-15 | Observation ordering, pre-fetch parameter failures, tracking error, AvailabilitySummary, and report source | Verify acceptance-order updates, shared observation/mark sequence, later-accepted replacement, pre-fetch note projection without fake queries, local fallback plus tracking-error behavior, snapshot-construction versus observation-loss distinction, new-run isolation, shared publication, summary/report contracts, and P-02/P-04/P-09/P-10 fixtures | Isolated context/stage/terminal-report attachment feasibility confirmed (Round 3 partial draft); target-binding/acceptance-order/failure implementation and production verification remain pending under the existing contract; no extra recovery or global veto |

### 13.2 Risks

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| RSK-01 | Formal fields missing, invalid, or written by a non-SB-01 path | Two authorities, fabricated REVIEW, or unsafe success | Shared `FormalResultContract`; execution contract failure; no consumer-generated REVIEW |
| RSK-02 | New flow accidentally resumes or uses stale checkpoint evidence | Bypass of required checks; old result treated as current | Full execution from a new RunContext/initial state; no checkpoint acquisition or `None` resume; old checkpoint data left untouched and unused |
| RSK-03 | Availability classification misreads a sentinel | False completeness or false failure | Table-driven per-method mapping with fixtures; no model judgment |
| RSK-04 | Query reuse leaks across runs | Wrong data in another analysis | RunContext-owned service; no module global |
| RSK-11 | Report/final-state/new-memory failure misclassified as best-effort | False success and hidden failed save | Path-specific persistence classification; run outcome can be failed; formal result unchanged |
| RSK-13 | Duplicate resource ownership between entry and `RunContext.finish()` | Unclear close order, masked primary error, or double release | Entry/wrapper ownership table; `finish()` restores binding after entry-owned cleanup; no persisted terminalization |
| RSK-14 | FR-04 implemented with float arithmetic, display rounding, or different field rules | Boundary decisions diverge; unsafe pass/block | Field contract, exact rational cross-multiplication, one JSON-compatible result, independent boundary checks |
| RSK-15 | FR-03 classifier treats non-empty error text as available | False completeness and model overconfidence | Per-method producer-branch table; narrow classifier; unrecognized format is unavailable |
| RSK-16 | Research stage reads a summary only after first Bull or refreshes it on every round | First Bull lacks data context; later observations change research inputs | Research-entry wrapper injects same-call snapshot; stage field fixed after first entry |
| RSK-17 | Query path is included in query identity or inferred from shared function name | P-09/P-13 fail to share or associate incorrectly; concurrency misattribution | Query key excludes path; explicit path ID from the two news callers; separate association map |
| RSK-18 | Decimal/Fraction values or default Decimal precision decide the risk check or break serialization | Context-dependent decisions, wrong boundary result, or non-JSON state | Exact rational decision; JSON-compatible result values; local parsing/formatting; no global Decimal context |
| RSK-19 | Classifier/registry failure replaces the fetch outcome, blocks shared publication, or is expanded beyond actual observation loss | Lost original error/result; waiters hang; unrelated recordable failures wrongly invalidated | Observation handling isolated; query-level conservative observation or local failure mark; tracking error only for unlocatable/unrecordable loss; publish in all normal/error paths; no refetch or general public flag |
| RSK-20 | Normal-looking heading or arbitrary number counted as available | False completeness and model overclaim | Minimum content rules; fixed producer structures; unrecognized format unavailable |
| RSK-21 | A consumer rebuilds completeness or necessary gaps from a different rule | Conflicting summaries and SB-01 decisions | Summarizer is the sole producer; consumers read one plain mapping and only filter non-available necessary items for display/contradiction checks |
| RSK-22 | A path is observed twice at different layers or missed on an early return | Duplicate/no observations; false availability or gaps | One curated attachment table; local helper at the existing call point; no router/vendor/callback observation |
| RSK-23 | Observation metadata copies a second default table or invents effective values | Wrong query identity or summary claims | Reuse existing config keys/constants and known requested values; record unknown/null honestly |
| RSK-06 | CLI save phase misclassified | Wrong run status or duration | Explicit save outcome and timing boundary |
| RSK-07 | Stats double-count, lose identity, or fabricate tokens | Misleading observability | One callback-handler site; call-ID dedupe; per-call usage; incomplete/unreliable => null totals |
| RSK-24 | Execution-config callbacks do not propagate through a nested boundary | Under-counted calls or missing reflection | Treat as unverified; add local explicit config handoff at that boundary, not a global collector/router |
| RSK-25 | Report writer sources availability from another run or the live registry | Cross-analysis contamination; report changes after run end | Writer reads only passed state; run-in entry prepares terminal summary; independent save uses final_state only |
| RSK-26 | Unrecordable observation loss is silently ignored, leaving an old success to look current | False completeness from lost observations | Run-local `availability_tracking_error`; later snapshots return `None`; not exposed as a public status/gate |
| RSK-27 | Pre-fetch parameter rejection is misrecorded as a completed query, overwrites a valid result, or sets tracking error | Fake availability/completeness and false lost-observation state | Private call-failure notes with no key/sequence/FR-01; necessary gap reason or supplementary limitation only; no tracking error |
| RSK-08 | Report/state/memory divergence | INV-01 violation | Formal-field-only consumers; cross-output tests |
| RSK-09 | Path check uses string prefix or follows link | Out-of-root access | Resolved-target/component ownership; sentinel tests |
| RSK-10 | Long histories or large reports exceed a provider's context limit | Request failure or incomplete analysis with no automatic recovery | Keep the existing client error path; context budget/compression is deferred by ADR 001 D-10c; do not claim arbitrary-length success |

---

## 14. Traceability summary

The detailed fit-criterion mapping is in [`docs/architecture/trace-matrix.md`](docs/architecture/trace-matrix.md). This blueprint covers:

- FR-01: P-09/P-13 query reuse service and observation boundary.
- FR-02 (deferred, no current task): RunContext lifecycle, manifest, stats, result references.
- FR-03: 15 path-specific observation sites, availability registry, necessity list, consumer snapshots.
- FR-04: structured scenario, evaluator, deterministic display.
- FR-05 (deferred, no current task): manifest registration, list/read interface, path/error rules.
- SB-01: graph-internal final check, proposal/formal separation, fail-closed REVIEW.
- INV-01: formal-field-only consumers across CLI, final state, report, state log, memory.
- SR-01: limited credential protection paths and endpoint preference rule.
- SR-02 (deferred, no current task): run-id and resolved-target path confinement.
- FR-06/FR-07/PR-01/CR-01: explicitly deferred and not designed as current behavior.

---

## 15. Review checklist

- [ ] The fixed graph sequence Portfolio Manager → FR-04 → SB-01 → END is accepted.
- [ ] Portfolio Manager writes only `model_proposal` as a nested `{rating, text}` object or `null`; SB-01 alone decides/generates `gate_status`, top-level `reasons`, `final_rating`, and `final_trade_decision`; unchanged pass-through/merge/save is allowed and is not a second authority.
- [ ] Risk reasons remain in `portfolio_risk_result.reasons`; SB-01 reasons remain at the top level; no `present`, `gate_reasons`, or flattened risk object is required.
- [ ] Missing/invalid formal output is an execution contract failure, not a consumer-generated REVIEW.
- [ ] The availability snapshot is plumbing, not an approval authority.
- [ ] Each of the 15 paths has one curated observation site; P-09/P-13 share one news executor/single-flight, P-03 observes each split indicator, and P-14/P-15 are observed at their direct prefetch calls.
- [ ] No router, vendor, callback, monkeypatch, or middleware layer adds a second availability observation; defaults come from existing config/constants and early failures do not invent a valid query.
- [ ] `AvailabilitySummary` has exactly the five agreed fields; the summarizer is the only completeness calculator, and consumers read one plain mapping without rebuilding it.
- [ ] Necessary gaps are only a filter over non-available `necessary_items`; no duplicate `missing_necessary_items` field or second completeness state exists.
- [ ] Observation, conservative unavailable, and query marks share one acceptance-order sequence; a later accepted update replaces an earlier one for that query, with no external-time ordering. Failure marks appear only as affected-query `unavailable`.
- [ ] Pre-fetch parameter rejection creates only a private safe call-failure note, with no fake query/observation/sequence/FR-01 and no tracking error; it does not overwrite a valid result and appears as necessary-gap reason or supplementary limitation as appropriate.
- [ ] Unlocatable/unrecordable observation loss sets private `availability_tracking_error`; later snapshots are `None`, not old complete data, while a single snapshot-construction failure is not sticky. A new run starts clean, and consumers see only missing/invalid summaries.
- [ ] Each independent analysis binds fresh ephemeral scope before its first supported data call; explicit internal delegation shares scope; every exit restores the prior binding. No pre-construction binding or constructor timing is required.
- [ ] Resource cleanup belongs to the entry or resource wrapper; `RunContext.finish()` does not close streams or clients; the new flow acquires no checkpoint session.
- [ ] FR-04 uses the field/threshold contract and exact rational comparisons; no float arithmetic, default Decimal context, or display rounding decides a check.
- [ ] The risk result is one JSON-compatible object with decimal-string/null metrics; display formatting is local and never feeds back into status.
- [ ] The deterministic risk area says only the listed caller scenario is checked and that other amounts/prices in the model proposal are not verified by this check.
- [ ] Observation handling failure never replaces the fetch outcome or blocks shared publication; recordable failures stay at the query, and only unlocatable/unrecordable observation loss sets the private tracking error that makes later snapshots missing. No public permanent veto exists.
- [ ] Title-only, placeholder, error text, or arbitrary numbers are not sufficient for `available`; minimum content rules are applied per P-02/P-04/P-09/P-10.
- [ ] Every FR-03 path uses the verified per-method branch table; non-empty error text is not treated as `available`.
- [ ] The first Bull call receives the research-start summary directly; later Bull/Bear and the Research Manager use the same stage summary; later observations do not refresh it or re-run research.
- [ ] Existing role prompt assembly, full reports, identity/language, tool-message relationships, and structured-output/fallback paths remain; the context classes are logical, not a shared layer order.
- [ ] Context budgets, compression thresholds, and compressed-constraint reinjection are deferred per ADR 001 D-10c and are not current behavior or acceptance; existing role inputs/client limits/error paths remain, and no unified budget/trim/reinjection flow is added.
- [ ] Query identity excludes call path; completion observations and path associations are separate and ordered correctly.
- [ ] `propagate()` never forces a report save, its return shape is unchanged, and returned final_state carries this analysis's terminal `data_availability_summary`.
- [ ] Run-in reports use one entry-prepared terminal summary; independent `save_reports(final_state)` uses only that state, and the writer never reads active context, registry, summarizer, graph cache, research summary, or model text.
- [ ] Duplicate callbacks are deduped by callback call ID; per-call usage drives null totals; graph-internal reflection is included, independent settlement is not; propagation gaps are treated as unverified with local config handoff, not a new router.
- [ ] Intermediate proposal labels and formal waiting/failed states are accepted.
- [ ] The new flow always executes fully from a new RunContext and initial state; it does not resume, read, or delete checkpoint data, and checkpoint-enabled configurations emit a no-resume notice.
- [ ] Current SR-01 remains limited to the stated paths; SR-02 has no current task and existing ticker protection is retained.
- [ ] Deferred scope is not re-introduced.
- [ ] All remaining open decisions are resolved or explicitly deferred by the human reviewer.

## Deferred and historical design archive — not current implementation instructions

The material below preserves prior design rationale/details and identifiers. Any mandatory wording here applies only if the deferred scope is explicitly reactivated and reviewed. It is not a current task, monitor, acceptance condition or permission grant. Historical mixed clauses are superseded by the current sections above.

### 1.1 Purpose

The architecture extends the existing TradingAgents LangGraph application with a deterministic, auditable final-decision boundary, a run-scoped lifecycle and manifest, a run-scoped data-availability summary, run-scoped reuse of supported queries, deterministic purchase-scenario risk checks, a read-only historical report lookup, and limited credential and path protections.

The design is incremental. It retains the existing graph, agents, data vendors, CLI, report writer, memory log, and checkpoint mechanism, and adds narrow components at existing boundaries.



## 7. Run lifecycle

### 7.1 Creation point and object lifecycle

The program interface uses a reusable `TradingAgentsGraph` object: the object is constructed first, then `propagate()` may be called one or more times. Creating the object is not creating an analysis run. The object constructor does not allocate a run_id, create a manifest, or retain a RunContext.

Entry-specific boundaries:

| Entry | Boundary |
|---|---|
| CLI | Parameter selection, configuration resolution, and basic validation → create RunContext, record start clocks, attempt running manifest → construct the graph object, initialize clients, perform the initial workflow compile → prepare per-run state and output paths → execute |
| Program | An existing graph object → `propagate()` invocation → per-call basic validation and effective configuration → create a new RunContext, record start clocks, attempt running manifest → prepare per-run state → execute |

Consequences:

- CLI object construction, client initialization, initial workflow compile, and per-run preparation occur after the run starts and are included in Analysis Operation Elapsed Time.
- A CLI construction/client/compile/preparation failure is a post-start execution failure: preserve the original error, attempt a failed manifest, and do not let a manifest error replace the construction error.
- The program entry excludes the object's earlier construction, client initialization, initial workflow compile, and idle time. A construction failure before `propagate()` creates no analysis run or manifest.
- Both entries create the RunContext before their per-run execution preparation. This does not promise identical object-initialization scope and does not support a direct performance comparison between entries.
- Each independent `propagate()` creates a new RunContext, run_id, statistics handler/collector, query-reuse registry, and availability registry. The object may be reused, but neither its models nor the graph object retain this run's handler, and the run context is not reused across analyses.
- The initial workflow compile is object construction for the CLI and pre-existing for the program entry. The new flow does not perform a checkpoint recompile.
- The design does not add a requirement to reconstruct model clients or the whole graph for every analysis. The existing CLI construction per operation remains, while a program caller may reuse an existing object. It does not move run creation into the constructor or require lazy initialization.

Configuration summary:

- The initial running manifest cannot depend on a constructed graph instance. A shared config-summary projection uses the existing `run_settings()` allowlist from the effective configuration and selected analysts.
- The instance `run_settings()` method reuses the same projection. There is no second allowlist, no extra graph construction, and no expansion of the credential-protection scope.

Internal reuse:

- Only an explicit internal delegation within the same analysis, such as the CLI delegating to common execution logic, shares the active RunContext.
- An independent `propagate()` call, another graph object, or another ticker analysis is not merged merely because a context variable already holds a context.
- Leaving the context restores the previous binding so a later call cannot inherit it.
- The design does not promise concurrent execution on the same graph instance.

CLI report saving is included in the same run. `propagate()` does not force a report save; a later independent save is outside the run.

### 7.2 Run identity

- `run_id` is a single safe path component: UTC compact timestamp plus a random suffix, e.g. `20261117T101530123456Z-a1b2c3d4`.
- Collision handling: attempt unique directory creation with `mkdir(exist_ok=False)` up to a bounded number of attempts (proposed 5); on each collision generate a new suffix. Never overwrite an existing run directory.
- If no directory can be created, manifest persistence is unavailable; the analysis continues and a safe warning is emitted.
- Manifest path: `<results_dir>/<run_id>/run_manifest.json`.
- Existing report directories are retained. Report references in the manifest point to actual files; relative references are resolved against the configured results root. Existing same-path report saving may overwrite an earlier file; no immutable report version is promised.
- Explicit user-chosen report locations outside the results root remain allowed by the existing save feature but are not automatically eligible for FR-05 history read.

### 7.3 Timing

“Analysis Operation Elapsed Time” is measured with a monotonic clock.

| Included | Excluded |
|---|---|
| Post-start preparation: CLI graph-object construction, client initialization, initial workflow compile, per-run state/output preparation | Pre-start parameter selection and basic validation |
| Graph execution | Post-terminal browser opening and full-report browsing |
| CLI save selection wait, path/HTML selection, save attempt | Final manifest record construction/serialization/write |
| Resource cleanup before terminalization | Program object construction, client initialization, initial workflow compile, and idle time before `propagate()` |
| — | Time after the terminal write attempt returns |

`started_at` is timezone-aware ISO 8601. `finished_at` is recorded before building the terminal record. `duration_seconds` is the monotonic difference between start and end, excluding final manifest serialization/write.

### 7.4 Manifest lifecycle

1. Attempt a `running` record with `finished_at = null`, `duration_seconds = null`, and available identity/configuration.
2. Execute the graph, then the existing final-state JSON save and new-memory append, then the requested CLI report save. An exception in an earlier write prevents later writes in the existing order.
3. The entry execution scope ensures necessary cleanup attempts for resources it acquired, coordinates their order, and summarizes the run outcome. Wrappers release only their own resources.
4. Call `RunContext.finish(outcome)`: after the cleanup attempts, record end clock, take a stats snapshot, build the terminal record, and attempt the terminal write.
5. Restore the prior RunContext binding on scope exit and then return or enter the post-run phase.

Rules:

- `completed` only when analysis execution succeeded, any requested report save succeeded or was not requested, and required final-state JSON and new-memory writes succeeded or no new memory append was required. A historical settlement/reflection/memory-read degradation handled by `_memory_step()` is not a failure.
- `failed` when a caught execution error ends the analysis, the final-state JSON save raises, a new memory decision append raises, a requested CLI report save outcome is `failed`, or the formal result contract fails.
- A CLI graph-object construction, client initialization, initial workflow compile, or per-run preparation failure after RunContext start is a caught execution failure: preserve the original error, attempt a failed manifest, and do not let a manifest error replace it.
- A final-state JSON failure prevents the later memory append in the existing order; the original exception is preserved.
- The entry catches a final-state or new-memory exception only to record the failed outcome and attempt the terminal manifest, then re-raises the original exception unchanged. It does not suppress it or replace it with a manifest error.
- A final-state save success followed by a new-memory append failure does not roll back the saved state and does not become a normal success.
- Memory disabled or an existing same-day record causing no new append is not a save failure.
- Initial manifest write failure does not prevent a later terminal write attempt.
- `RunContext.finish()` does not close streams, call `end_checkpoint()`, delete checkpoint data, close clients, or repeat a close; those responsibilities are defined in §7.8.
- Manifest failure does not re-trigger cleanup and does not block context-binding restoration.
- A `finally` path never writes `completed` unconditionally. `completed` is set only when the normal execution path reached the terminalization step.
- Terminal write uses a temporary file plus atomic replace; a reader sees complete old JSON or complete new JSON.
- Serialization failure does not damage an existing valid file.
- Manifest warnings are safe and short; no raw credential, complete configuration, or uncontrolled traceback.
- Manifest failure does not re-run a model, roll back report/memory, change the run outcome, or replace the original analysis or save error. A failed manifest does not force a new CLI non-zero exit code.
- A remaining `running` record after terminal failure means only that the terminal record is missing; it does not prove the analysis is still running or failed.

Proposed manifest fields (architecture interface, not a new requirement):

| Field | Type | Notes |
|---|---|---|
| `manifest_version` | string | Literal `"1"` for the shared writer/reader contract; any other value is an invalid record |
| `run_id` | string | Safe path component |
| `status` | `running` / `completed` / `failed` | Run status, not recommendation |
| `analysis` | object | Required: `ticker` string, `analysis_date` `YYYY-MM-DD` string, `asset_type` string, `analysts` list of strings |
| `started_at` | string | Timezone-aware ISO 8601 |
| `finished_at` | string or null | Null while running |
| `duration_seconds` | number or null | Monotonic analysis operation elapsed |
| `run_settings` | object | Existing `run_settings()` allowlist only |
| `llm_calls` | integer or null | Started application-level model calls |
| `tool_calls` | integer or null | Started tool calls; direct prefetch excluded |
| `tokens_in` | integer or null | Exact sum only when complete |
| `tokens_out` | integer or null | Exact sum only when complete |
| `usage_complete` | boolean | False if any counted call lacks valid usage |
| `result_files` | list | Required list of confirmed files actually produced by this run; `[]` when none was confirmed. Writer never guesses, fabricates, or scans old files |
| `report` | object or null | Required key. `null` when no confirmed merged report; otherwise exactly `{"complete_report_md": string}` |
| `error_summary` | object or null | `error_type` and safe message; no traceback |

Minimal shared writer/reader contract for `manifest_version = "1"`:

- Writer obligation: `analysis` and `report` use the shapes above. The writer records every confirmed produced-file reference in `result_files`, using `[]` when none exists; it does not omit an existing confirmed file, guess a path, fabricate a reference, or scan old directories to claim a file as current. “Optional output” means a report or other optional artifact is not forced to be generated; once produced and confirmed, its reference is still recorded.
- Writer obligation: `report.complete_report_md` is a string path relative to the configured results root. An absolute value is allowed only when it resolves inside that root under the existing SR-02 checks. When no merged report was confirmed, the normal writer emits `report: null`, not an inferred path and not an empty object.
- Reader obligation: history validates only the fields needed for registration, filtering, ordering, and report lookup. It does not expand validation over `result_files` or other unrelated content. A missing `report` key is format damage: list skips the record with a safe warning, and direct get treats it as an invalid record. A legal `report: null` is a valid no-registration record: it is absent from list and direct get returns not found.
- If `report` is non-null, it must contain the `complete_report_md` string and satisfy the root/ownership checks; a missing member, wrong type, or illegal reference is an invalid record. A legally registered report that is later deleted or unreadable remains registered for list availability purposes and direct read returns a report-read error.
- Missing other required metadata, wrong field types, an unsupported `manifest_version`, or an illegal report reference follows the existing invalid-record/skip rules. No independent schema file, migration, old-version compatibility, hash, archive, index, or new validation system is added.

No rating, gate, reason, or decision fields are added to the manifest. A newly created memory record uses the formal rating and body; it is not required to store the complete gate metadata.

### 7.5 Outcome dimensions

| Dimension | Values | Meaning |
|---|---|---|
| Formal business result | `gate_status` `passed`/`blocked`/`error`, top-level `reasons`, `final_rating`, and `final_trade_decision` | SB-01 output; risk reasons remain inside the risk result; persistence failures never recompute or rewrite it |
| Run outcome | `completed` / `failed` | This analysis operation, including required save outcomes |
| External control flow | Normal return, existing exception propagation, existing CLI error display/exit | Existing behavior; a failed manifest does not force a new non-zero exit code |
| Artifact persistence | Per artifact: `not_requested` / `succeeded` / `failed` | Manifest, report, final-state, and new-memory outcomes; partial success is possible |

A formal result contract failure is an execution failure, not a business REVIEW. A business REVIEW is a `completed` run; a contract failure is `failed` with a best-effort failed manifest.

The formal business result is unchanged by persistence failure. That does not mean every save failure returns normal success: final-state, new-memory, and CLI-requested report failures can make the run `failed`. Manifest failure alone does not.

### 7.6 CLI save boundary

- Save selection wait, path/HTML selection, and save attempt are inside the run.
- The internal `SaveCoordinator` returns `not_requested`, `succeeded`, or `failed`, plus confirmed output references. This is internal coordination, not a new external diagnostic system.
- The CLI catches its report-save exception for display, so the lifecycle uses the internal save outcome rather than inferring success from the absence of an escaping exception.
- After the save attempt and the entry-owned cleanup attempts, `RunContext.finish()` attempts the terminal manifest.
- Post-run display and browser opening occur after the terminal attempt; their duration is excluded.
- Existing save failure messages and exit behavior are preserved. A failed manifest record does not require a new CLI non-zero exit code.
- `propagate()` never forces a report save. A later independent `save_reports()` failure keeps that operation's behavior and does not reopen or update the completed run manifest.
- If Markdown is written and HTML then fails, the overall requested save is `failed`; the confirmed Markdown reference may be recorded, no HTML success is fabricated, and neither file is rolled back or deleted. The lifecycle does not scan old directories to claim files as current outputs.
- A failed manifest that contains a report reference does not make the record eligible for the FR-05 `completed` history list.

Report availability source:

- Run-in report: after graph execution and before save, the entry/save coordination takes one current summary from this run's registry and places the five-field mapping in `data_availability_summary` of the final/report state used for delivery. It leaves the field null/absent if no valid summary can be formed. If a separate report-state copy is used, Markdown, HTML, and post-run CLI display all use that same copy, and the returned final_state retains the same terminal mapping. Showing an already generated report uses that report's data; post-run display of the just-finished analysis uses the prepared final state.
- Updating this delivery/display `data_availability_summary` is a summary refresh only. SB-01 already used its check-time summary; the refresh does not rerun SB-01 or modify `gate_status`, top-level `reasons`, `final_rating`, or `final_trade_decision`. No digest, version, snapshot history, second result, or re-check binding is added.
- The report writer and renderers only read the passed state's `data_availability_summary`. They do not use `RunContext.current()`, the registry, the summarizer, a graph last-analysis cache, or the research-stage summary.
- Independent `save_reports(final_state, ...)` after the run reads only that final_state's terminal `data_availability_summary`. It never uses another analysis's context/registry, never re-summarizes or queries data, and does not reopen or update the ended run/manifest.
- A null/missing/unusable summary in the deterministic report area is stated as “program summary unavailable”; it is not replaced by complete/incomplete/not_applicable and is not reconstructed from the model or research snapshot. A preparation failure only warns and leaves the field null/absent; it does not block report generation/save, replace the formal result, or make the run fail. This notice is failure handling, not normal FR-03 delivery. A missing/invalid formal result still follows `FormalResultContract` and is a separate failure.
- “Report-preparation time” means results already recorded in this run up to that point; it does not mean fetching newer market data at save time. The graph has completed before this preparation, and no later data-fetch/background stage is added, so the prepared terminal summary is the final data available to independent saves. Different-time summaries need not differ; no time-proof/version/hash protocol is added.
- No `report_availability_summary`, availability history, snapshot ID, persistence of the registry, or cross-analysis availability protocol is added.

### 7.7 Persistence and recovery-path classification

| Path | Required behavior |
|---|---|
| Manifest directory creation, serialization, and write | Safe warning only; does not change run outcome or formal result |
| Final-state JSON save | Preserve existing exception propagation; `failed` run and best-effort failed manifest attempt |
| New memory decision append | Preserve existing exception propagation; `failed` run; no replacement record or rewritten recommendation |
| Memory disabled or existing same-day record causes no new append | Not a save failure; do not force a record or mark the run failed |
| Historical settlement/reflection or memory-read failures already handled by `_memory_step()` | Preserve existing degradation and notes; do not automatically promote to run failure |
| CLI report save requested during this operation | Preserve existing exception capture and error display; report the internal save outcome to the lifecycle and mark the run `failed` |
| User declines report save | `not_requested`, not failed; `completed` if other required work succeeds |
| Independent `save_reports()` after `propagate()` returns | Preserve that save operation's failure behavior; do not reopen or modify the completed run manifest |

Additional boundaries:

- The four dimensions above stay separate: a save failure may change the run outcome without changing the formal result.
- Not every optional artifact must exist for a `completed` run: an unrequested report and a memory disabled/same-day no-op are not failures. The table applies to requested or required writes that actually fail.
- No publication transaction, cross-file atomicity, rollback, automatic repair, or recovery protocol is added.
- A successfully saved final state is not rolled back because the later memory append failed.
- A successfully written Markdown report is not rolled back or deleted because HTML failed.
- The existing `record_decision()` no-decision branch is not a normal path after formal-result contract validation; a missing formal result is an execution contract failure, not a silent memory no-op success.

### 7.8 Resource ownership and cleanup coordination

Three layers, with no duplicate release:

1. **Outermost entry or execution scope**: ensures necessary cleanup for resources it acquired is attempted, coordinates the order, and summarizes the run outcome.
2. **Resource wrapper**: releases only the resource it created.
3. **`RunContext.finish()`**: after the necessary cleanup attempts, receives the summarized outcome, records end time, takes the stats snapshot, and attempts the terminal manifest.

| Resource | Owner and responsibility |
|---|---|
| Outer streaming session | CLI or debug streaming caller; ensure exhaustion or explicit termination |
| Underlying graph stream | `stream_run()`; close in its own `finally` |
| Existing checkpoint code (not used by the new flow) | Existing implementation and tests own their behavior; the new flow does not acquire, release, or delete checkpoint resources |
| Persisted checkpoint data | Left untouched by the new flow; never used as current evidence |
| RunContext binding | Scope that created the current context; restore the previous binding on exit |
| Reusable graph and model clients | Object/caller lifecycle; not automatically destroyed by each run finish |
| Output file handles | Local save-function scopes |

`RunContext.finish()` must not close a stream, call `end_checkpoint()`, delete checkpoint data, close model clients, or perform a second resource release.

Execution order on the normal path:

```text
graph execution and complete formal result
  → requested save attempt
  → necessary cleanup attempts complete
  → summarized run outcome
  → RunContext.finish()
  → restore prior RunContext binding
  → return or post-run browsing
```

A resource may be released earlier once it is no longer used. For example, a normally exhausted stream is closed without being held until after report saving.

Cleanup rules:

- Do not close a resource that is still in use.
- End clock and stats snapshot occur after the necessary cleanup attempts.
- `finish()` does not repeat a close.
- Manifest failure does not re-trigger cleanup.
- Context-binding restoration has an exit guarantee and does not depend on manifest success.

Partial initialization:

- The resource-acquisition scope starts at the acquisition attempt.
- If a resource was acquired and a later setup or use fails, it is still released.
- Resources not yet acquired are not treated as open.
- `finish()` is not a fallback for resource leaks.

Cleanup failure:

- If an execution or save primary error already exists, a cleanup error must not replace it.
- If there is no primary error, a cleanup exception follows the existing error style and is not recorded as `completed`.
- One close failure does not prevent attempts to release other acquired resources.
- Manifest errors remain warnings only.
- No infinite retry, fabricated close success, or persistent diagnostic system is added.

Existing checkpoint boundary:

- The new flow does not acquire a checkpoint session or call `clear_checkpoint_on_success()`.
- Existing checkpoint storage, thread IDs, signatures, cleanup tools, and tests remain outside this flow and are preserved.
- Old checkpoint data is neither used as current evidence nor deleted by the new flow.

---



### 8.6 FR-05 history read

Interface:

- `list_runs(ticker=None, analysis_date=None) -> list[RunSummary]`.
- `get_report(run_id) -> str`.

Registration:

- The FR-02 manifest is the only registration source.
- A record enters history only when a parseable, supported-format `completed` manifest registers a merged Markdown report reference. A normal `report: null` is a legal no-report record, not a corrupt one, and does not enter the list.
- Running/failed records, legal no-report records, and unregistered report files are not guaranteed to appear. A missing required `report` key is format damage; list skips it with a safe warning and direct get treats it as an invalid record.
- A legal registration whose report was deleted remains listable with `report_available = false`; it is not converted into an unregistered record.
- No migration of old reports is required; existing ticker/date and timestamp layouts are allowed.

List summary fields: `run_id`, `ticker`, `analysis_date`, `started_at`, `report_available`. The complete report body is never returned by `list_runs`.

Filters:

- Omitted or null filters apply no filtering.
- A non-null ticker must be a non-empty string, reuses existing ticker normalization, and performs no network identity lookup.
- A non-null analysis_date must be a legal `YYYY-MM-DD` string and is never defaulted.
- Both filters intersect; a valid unknown ticker or no match returns an empty list.
- An empty string, wrong type, or invalid date returns a parameter error.

Ordering: `started_at` descending, then `run_id` ascending for equal times. A missing or invalid `started_at` makes the candidate a bad record. Ordering never uses `run_id` as the primary key.

Discovery and path:

- Discover manifests under the configured results root using the existing `<results_dir>/<run_id>/run_manifest.json` layout; do not scan arbitrary directories for report files.
- A report reference resolves under the configured results root. Relative references are resolved against the root; an existing absolute reference is readable only when it still resolves inside the root.
- Component and resolved-target checks are used, not string-prefix checks.

Read:

- `get_report(run_id)` reads only the registered `complete_report.md` as UTF-8.
- It does not assemble sections, re-render, repair, or modify files.
- Invalid UTF-8 is a read error; replacement characters are not used.
- Content may be later edited externally; the reader returns current content and does not claim the original bytes.

Distinct errors:

| Condition | Result |
|---|---|
| Illegal run_id | Parameter error |
| No manifest, non-completed record, or legal `report: null`/no-report reference | Not found |
| Missing required `report` key, corrupt, unsupported, identity-mismatched, malformed report object, or out-of-root-reference manifest | Invalid record |
| Registered report missing or unreadable | Report-read error |
| Missing results root | Empty history |
| Existing but unreadable or scan-failing results root | History-read error |

Bad records are skipped in list with a short safe warning; other valid records continue. Errors and warnings contain no raw file content, credentials, or unnecessary absolute paths.

No pagination, limit/offset, total count, scan budget, index, cross-request snapshot promise, immutability, hash, section validation, repair, or background rebuild is added.



### 8.7 Run statistics

- One analysis owns one `RunStatsHandler` and its directly bound collector; they may be two responsibilities of one local class. The handler is created with the RunContext, never accumulated on a reusable graph/model object.
- The CLI and `propagate()` merge that handler into this graph invocation/stream config's `callbacks`; they do not append it to model constructor callbacks or overwrite existing execution-config callbacks. Only this analysis's own stats handler is not registered twice.
- The handler does not consult an active context to find its run and does not use a global mutable collector. The RunContext ContextVar remains for lifecycle/reuse/availability; only stats ownership no longer depends on it. The analysis `run_id` is separate from model/tool call IDs.
- Handler state is one model-call record map, a tool-call ID set, and one lock. No event router, dispatcher, event bus, or module-level collector is added.
- Callback identity comes from the framework-provided call/run ID and is never synthesized from prompt text, model name, or timestamp. First `start` for a model/tool call counts once; duplicate start/end and streaming fragments do not add counts. If identity cannot be established or matched, the affected count/usage is not fabricated: the snapshot uses null and a safe warning follows the requirement's unknown/null rule.
- LLM calls count application-level model calls started in the run, including failed calls and graph-internal reflection. Tool calls count tool calls started in the run, including failed calls. Direct data prefetch is not a tool call.
- Graph Memory Log reflection belongs to this analysis when its call runs under this graph execution. Independent `settle_pending()`/`settle_all_pending()` activity outside the graph is not automatically attributed merely because it uses the same model object.
- Structured-output attempt actually started counts once; a subsequent free-text fallback actually started counts once more. Local structured binding failure with no model request does not count. Parser, chain, or graph-node work does not count as model calls; schema-tool declaration is not an external tool execution. No manual per-invoke accumulation is added, so callbacks are not double-counted.
- Reflection is ordinary `llm_calls` within this analysis when it executes under this graph; independent settlement or other background work outside the run is not attributed. Direct data prefetch is not a tool call. No reflection, HTTP, prefetch, retry, or fallback-specific counters, cost/price formulas, or benefit claims are added.
- Per-call model records store valid input/output usage on `end`; `error` remains a counted call with incomplete usage. A started call not ended by snapshot time is incomplete.
- Valid usage is a non-negative integer; booleans, negatives, missing, or invalid values are not valid. If every counted model call has valid input and output usage, `tokens_in`/`tokens_out` are exact sums and `usage_complete = true`. If any counted model call lacks either side, both totals are null and `usage_complete = false`. Zero model calls gives 0/0 with `usage_complete = true`.
- No missing-as-zero, character estimate, partial contribution, token reversal, billing, price, retry, HTTP, prefetch, or fallback counter is added. Provider-internal invisible retries are not inferred.
- Callback/collector exceptions are isolated with an existing safe warning and never replace the original model/tool result or exception. No model is re-called to recover usage, no timeout/background wait is added, no diagnostic file or compensation protocol is created, and FR-04/SB-01/formal result are unchanged.
- A snapshot is taken on normal completion or after a caught execution error, after the existing save attempt and resource cleanup, under the RunContext lifecycle. A call still unfinished makes usage incomplete. Manifest best-effort and existing save-failure behavior are unchanged.

The following propagation boundaries remain unverified and must not be stated as guarantees: analyst subgraphs and parallel nodes; structured-output runnable to actual model; graph-internal reflection nested call; start/end/error call-ID association; and the exact usage extraction location in supported responses. If a boundary does not inherit, the preferred fix is to pass the same execution config locally into that call or graph node; do not switch to a global collector or dispatcher. Independent settlement outside the graph remains outside this run's statistics.



### 6.2 CLI workflow

1. Select parameters, resolve configuration, and perform basic validation (`cli/run.py`). If `checkpoint_enabled` is set, emit a safe notice that this flow does not resume and will run fully; do not change the configuration or default.
2. Create `RunContext`: allocate run_id, start clocks, create this analysis's `RunStatsHandler`/collector, and attempt the running manifest using the shared config-summary projection, before a graph object exists.
3. Construct the graph object for this CLI operation: initialize clients, perform the initial workflow compile, and prepare per-run state and output paths. Do not pass the per-analysis stats handler to the model constructors. No checkpoint session is acquired. This construction time is inside the analysis operation elapsed time.
4. If object construction, client initialization, initial compile, or per-run preparation fails, take the existing execution-error path: attempt a failed manifest while preserving the original error; a manifest error does not replace it.
5. Stream the graph with the per-analysis handler in this execution's config (`callbacks`), preserving any existing custom callbacks; update intermediate display sections. A partial streaming chunk is never promoted to a formal result.
6. Merge final state; the post-PM nodes have already produced the formal result.
7. Validate the merged formal result with the shared `FormalResultContract` before `record_decision()`, normal report save, formal display, or successful return.
8. Prepare the delivery/report availability input while this analysis's registry is still accessible: take one current summary, put its plain mapping into the final-state/report-state copy, or leave the field null/absent when no valid summary can be formed. This does not rerun SB-01 or change formal fields.
9. Save phase inside the run: ask save/path/HTML, perform save attempt from that prepared report state, collect confirmed output references; Markdown and HTML use the same input.
10. Exit the entry execution scope: ensure the outer streaming session is exhausted or explicitly ended, and `stream_run()` closes its own underlying graph stream. No checkpoint session is acquired or closed by this flow.
11. Summarize the run outcome and call `RunContext.finish(outcome)`: after the cleanup attempts, it records end time, takes a stats snapshot, and attempts the terminal manifest. `finish()` does not repeat any close.
12. Restore the prior RunContext binding on scope exit, then run the post-run phase: print completion, display formal report and the prepared availability input, offer full report/browser.

The CLI must not display or record a formal rating before the Final Recommendation Check node completes. After the graph, a contract failure takes the execution error path; the CLI does not display a diagnostic as a formal REVIEW and does not claim normal completion.



### 6.3 Programmatic workflow

1. Start from an existing `TradingAgentsGraph` object. Its earlier construction, client initialization, initial workflow compile, and idle time are not part of this analysis run. If object construction failed before `propagate()`, no analysis run or manifest is created.
2. Invoke `propagate()`: validate `trade_date`, asset type, and effective configuration for this call. If `checkpoint_enabled` is set, emit a safe notice that this flow does not resume and will run fully; do not change the configuration or default.
3. Read optional `purchase_scenario` input at the caller boundary. An explicitly provided file that cannot be read or parsed is an entry parameter error; an omitted scenario is not an entry error and is passed to FR-04 as missing input. After successful parsing, business-field validity, object matching, and explicit threshold validity are decided by FR-04, which returns structured `blocked` rather than causing an entry hard failure.
4. Create a new `RunContext`: allocate a new run_id, start clocks, attempt the running manifest, and create this analysis's `RunStatsHandler`/collector together with reuse state.
5. Build initial state including `purchase_scenario` and resolved thresholds. The graph object was already constructed; the new flow does not acquire or recompile a checkpoint, and it does not bind the handler to model constructors.
6. Run the graph fully with the handler in this execution's config (`callbacks`), preserving existing custom callbacks; no checkpoint scope is entered even when checkpointing is configured.
7. Validate the final formal result with the shared `FormalResultContract` before normal final saving and successful return.
8. While this analysis's registry is still accessible, prepare one terminal `data_availability_summary` plain mapping in `final_state`; if no valid summary can be formed, leave it null/absent. This does not rerun SB-01 or change formal fields.
9. After the terminal delivery summary is prepared, use the existing save flow to save final-state JSON and then attempt the existing new-memory append when its conditions create a record. A final-state failure prevents the later memory append; a memory failure does not roll back an already successful final-state save. Preserve the existing exceptions and run/outcome handling; add no transaction, compensation, recovery, or file rollback.
10. After those save attempts complete or fail, exit the execution scope and follow the existing error path for cleanup. Then call `RunContext.finish(outcome)` to record end time, take a stats snapshot, and attempt the terminal manifest.
11. Restore the prior RunContext binding, then return `(final_state, final_rating)` where `final_rating` is the SB-01 formal field and `final_state` carries the terminal delivery summary. The return shape is unchanged. The new flow does not call `run_rating()` or parse the formal text; the existing helper may remain for older callers.
12. On a contract failure, take the execution error path; do not return a fabricated `(final_state, REVIEW)` or parse the decision text. No specific exception class name is fixed.
13. Do not force report saving. A later `save_reports()` call is outside the run and reads only the returned `final_state`; it does not update the manifest.




### 4.1 Context

```text
User / programmatic caller
        │
        ├── CLI entry (cli/main.py, cli/run.py)
        └── propagate() entry (TradingAgentsGraph)
                    │
                    ▼
         RunContext (run identity, timing, stats,
         query reuse, availability registry, manifest)
                    │
                    ▼
   Existing LangGraph analysis and debate
                    │
                    ▼
   Portfolio Manager → model_proposal
                    │
                    ▼
   Deterministic post-PM section:
     availability snapshot → FR-04 risk → SB-01 final check
                    │
                    ▼
   Formal final result in graph state
        │           │            │
        ▼           ▼            ▼
   CLI display   Report writer  Memory log
        │
        ▼
   Run manifest (auxiliary)
        │
        ▼
   FR-05 history lookup (read-only)
```



### 6.4 Normal path sequence

```text
entry validation
  → RunContext.start (running manifest attempt)
  → graph execution
      → analysts + memory
      → research/trader/risk debate
      → Portfolio Manager: model_proposal
      → risk node: availability snapshot + FR-04 result
      → final check node: SB-01 formal result
  → shared FormalResultContract validation
  → prepare terminal availability summary into final/report state
  → CLI save attempt (if requested, same report state) / no save for propagate
  → entry-owned cleanup attempts complete
  → RunContext.finish: end clock + stats snapshot
  → terminal manifest attempt
  → post-run display/browser (CLI only)
  → caller receives formal result
```



### 6.5 Failure paths

| Failure | Graph/entry behavior | Manifest status | Formal result |
|---|---|---|---|
| Analysis execution exception | Existing error propagates after entry-owned cleanup attempts and terminal attempt | `failed` with safe summary | None produced; no fake result |
| CLI graph-object construction, client initialization, or initial workflow compile fails after RunContext start | Existing execution error path; original error preserved; failed manifest attempted | `failed` (attempted); manifest failure only warns | None produced; no fake result |
| Per-run state preparation fails after RunContext start | Existing execution error path; original error preserved; failed manifest attempted | `failed` (attempted) | None produced; no fake result |
| Program object construction fails before `propagate()` is invoked | No analysis run is created; object construction error remains | No run manifest | None |
| Formal result missing/invalid after graph, or lost in transfer/merge | Shared `FormalResultContract` reports an execution contract failure; entry takes the existing execution error path | `failed` (attempted); manifest write failure only warns | None; no consumer-generated REVIEW, no parsed rating, no substitute decision text |
| Independent public report save called with missing/invalid formal result | Contract failure; that save operation fails; no new normal report or memory decision; no failed snapshot file | Existing run manifest unchanged; no run reopen | None |
| CLI requested save fails | Existing save error message; run ends | `failed` | Existing formal result remains displayable |
| Final-state JSON save fails | Existing exception propagates; new memory append is not attempted | `failed` (attempted) | Existing formal result in memory remains unchanged; no successful state file is claimed |
| New memory decision append fails after final-state save | Existing exception propagates; saved final state is not rolled back | `failed` (attempted) | Existing formal result remains unchanged; no replacement record |
| Memory disabled or existing same-day record makes no new append | Not a save failure; no record is forced | `completed` if other required work succeeds | Unchanged |
| Historical settlement, reflection, or memory-read failure handled by `_memory_step()` | Existing degradation and notes; not promoted to run failure | `completed` if other required work succeeds | Unchanged |
| User declines report save | Not requested, not failed | `completed` if other required work succeeds | Unchanged |
| Requested report save partially writes Markdown and then fails on HTML | Existing save exception and error display; overall save outcome `failed`; confirmed Markdown reference retained | `failed` | Unchanged; no fabricated HTML reference and no rollback |
| Manifest running or terminal write fails | Warning only; analysis and requested save continue | May be missing/running | Unchanged; run outcome unchanged |
| FR-04 missing/invalid scenario (stock Buy/Overweight) | Risk node returns `blocked`; SB-01 returns REVIEW/blocked | `completed` (business REVIEW) | REVIEW + program notice |
| FR-04 evaluator exception | Risk node returns `error`; SB-01 blocks | `completed` | REVIEW + program notice |
| FR-03 incomplete | SB-01 blocks | `completed` | REVIEW + missing-data notice |
| FR-03 missing/illegal/contradictory | SB-01 blocks | `completed` | REVIEW + notice |
| Model rating missing/illegal/REVIEW | SB-01 blocks | `completed` | REVIEW + notice |
| SB-01 internal exception it handles | Check node catches and returns `error` | `completed` | REVIEW + notice |
| Unhandled exception escaping SB-01 or the graph | Existing execution exception path; formal contract not satisfied | `failed` (attempted) | None; no fabricated REVIEW or formal text |
| User interrupt/forced termination | No completed claim | May remain running/missing | Not guaranteed |



| 3 | Run lifecycle and manifest | FR-02 | Adds `RunContext`, timing, status, atomic JSON persistence | Misreported success, wrong duration, manifest failure masks an analysis or save error |

| 7 | Historical report lookup | FR-05 | Adds read-only manifest discovery and report read interface | Path escape, repaired/regenerated content, collapsed errors |

| 9 | Path confinement for controlled result paths | SR-02 | Adds run-id validation and resolved-target ownership checks | Write/read outside results root |

| QAS-02 | Program or user | Analysis start, CLI object construction failure, normal finish, caught execution error, requested save failure | Writable results directory | Run manifest | Attempt running/completed/failed records; manifest failure only warns; CLI construction and requested report failures can mark the run failed while preserving the formal result | FR-02-FC01–FC05, INV-01-FC01–FC03 |

| QAS-06 | Caller | Valid, malformed, missing, or out-of-root historical records | Configured results root | History list/read result | Correct filtering/order/read or distinct error; no repair or regeneration | FR-05-FC01–FC05 |

| Run observability vs non-blocking manifest | `ManifestStore` is best-effort; no manifest outcome changes the run outcome or formal result. |

| Run status | `RunContext` | Operational status, not a recommendation | Manifest, CLI warnings |

| Manifest persistence result | `ManifestStore` | Auxiliary persistence status, not a recommendation | Warnings only |

| Run manifest | `ManifestStore` | JSON file | Yes | Auxiliary; no rating, gate, or reason field |

| Stats handler/collector | One lock; model record map + tool ID set | One analysis, passed through that execution's config |

| Manifest writes | Unique run directory + atomic replace; single writer | One run |


| Safe warnings | Existing logging/CLI warning mechanism | Manifest/history/security failures |

| Persistence outcomes | Manifest failure with analysis and requested save succeeding keeps run completed; final-state JSON failure skips memory and preserves the original exception; final-state success plus memory append failure does not roll back state; memory disabled or same-day skip is not a failure; `_memory_step()` settlement/read degradation is not promoted to run failure; CLI report failure keeps error display and attempts failed manifest; Markdown success plus HTML failure makes the requested save failed with truthful refs; user declines save yields completed when other work succeeds; independent post-run save failure leaves the manifest unchanged; original save error is not overwritten by a manifest error and original state/memory exceptions are re-raised unchanged; no case recomputes or rewrites the SB-01 formal result |

| Fault injection | Manifest running/terminal/serialization failures; save failure; corrupt manifest; missing report; invalid UTF-8; unsafe endpoint; symlink escape |

| RSK-05 | Manifest write interferes with analysis | Masked error or false success | Manifest-only best-effort writer; original error/result priority; no run-outcome change |


### 9.2 SR-02 path confinement

- `run_id` must be a single safe path component: non-empty, no path separators, not `.`/`..`, not absolute, no injection form.
- Ticker reuses `safe_ticker_component` (`dataflows/symbols.py:155`); no new symbol system.
- The configured results root is the trusted starting point after resolution. Ownership is decided by components and resolved target, not string prefix (`/results-other` is not inside `/results`).
- A root configured through a link uses the resolved actual location. No new approval or link policy.
- For a not-yet-created manifest, check existing ancestors and controlled appended components; no check-then-use race guarantee.
- Reject a candidate that resolves outside the root through an existing symbolic link. Do not reject a legitimate in-root link merely for containing a link.
- Do not silently switch to the current working directory or another root.
- No URL decoding/double-decoding beyond existing behavior.
- `run_id` itself cannot be absolute; an existing absolute report reference may be read only if it resolves inside the root; out-of-root absolute references are rejected.
- User-chosen report save directories outside the results root follow existing behavior; they are not automatically copied into or retrieved by FR-05, and history read authorization is not expanded.
- Failure: FR-02 abandons the manifest write and warns; analysis continues. FR-05 illegal run_id is a parameter error; out-of-root reference is an invalid record; list skips bad records with warnings; direct read is rejected.
- Threat model: local single-user controlled directory without malicious concurrent modification. Check-then-replace races, hard links, mounts, and all platform link mechanisms are not guaranteed.



| RSK-12 | RunContext or stats handler tied to reusable graph/model object or a different run | Cross-run statistics contamination or wrong attribution | RunContext-owned handler; per-execution config injection; no constructor binding or context-based lookup |

- [ ] Markdown and HTML use the same report input; missing availability is disclosed as unavailable without a fabricated completeness value or SB-01 rerun; independent save does not modify an ended manifest.

- [ ] One stats handler/collector is created per analysis and injected only through that graph execution's config; it is not model-constructor-bound, not stored on the reusable graph/model, and does not look up its run from context.

- [ ] Manifest failure never changes the run outcome or formal result or masks the original error.

- [ ] Report/final-state/new-memory failures use path-specific behavior and are not generalized to manifest best-effort.

- [ ] FR-01/FR-03/FR-04/SB-01/manifest have independent component boundaries.
