# Architecture Evaluation Table

- Status: Proposed for human review
- Date: 2026-11-17
- Requirements baseline: `docs/req/requirements.yaml` version 1.48.0
- Related: [Architecture Blueprint](../../../architecture-blueprint.md), [ADR 001](adr/001-graph-internal-final-check.md)

This document compares architecture candidates and key design options. It does not contain numeric scores, performance measurements, cost estimates, test results, or approvals. Ratings are qualitative and trace to requirements or static code evidence.

---

## 1. Evaluation method

### 1.1 Evidence basis

| Evidence type | Source | Use |
|---|---|---|
| Requirement | `docs/req/requirements.yaml` | Defines required behavior and acceptance |
| Static code | `src/` source paths | Defines existing behavior and constraints |
| Existing tests | `test/` | Shows existing regression assets; no new-behavior pass is claimed |
| Baseline | `baseline/runs/baseline-20261020-01` | Describes old behavior only |
| Planned | Design-time verification | Not executed |

Historical D2 drafts in git history are not used as evidence. They included now-deleted or deferred scope.

### 1.2 Evaluation dimensions

Dimensions are derived from the architecture drivers in the blueprint:

| Dimension | What it evaluates | Source |
|---|---|---|
| D1 Authority integrity | One formal result source; no bypass | SB-01, INV-01 |
| D2 Safety determinism | Fail-closed checks; no model/data calls in checks | FR-04, SB-01 |
| D3 Lifecycle/observability | Run identity, status, timing, manifest, stats | FR-02 |
| D4 Data correctness | Query identity, reuse isolation, availability semantics | FR-01, FR-03 |
| D5 Output consistency | CLI, final state, report, state log, memory, return value | INV-01, SB-01 |
| D6 Compatibility | Existing entries, return shapes, graph, reports, memory | Constraints |
| D7 Security | Limited credential and path scope | SR-01, SR-02 |
| D8 Maintainability/testability | Offline tests, pure components, bounded scope | Constraints |
| D9 Deferred-scope discipline | No accidental activation of deferred requirements | FR-06, FR-07, PR-01, CR-01 |

### 1.3 Rating scale

| Rating | Meaning |
|---|---|
| High | Strong fit; few material gaps; traceable design |
| Medium | Acceptable fit with explicit gaps or migration work |
| Low | Material conflict or high risk |
| Rejected | Not compatible with the fixed design or requirement scope |

No rating is a numeric score or measured result.

---

## 2. Whole-architecture candidates

### 2.1 Candidate descriptions

| ID | Candidate | Strategy |
|---|---|---|
| A | Entry-boundary RunFinalizer | Graph ends at Portfolio Manager; each entry calls a shared finalizer for risk/final decision. |
| B | Graph-internal final check + RunContext | Deterministic post-PM nodes own risk and final check; run-scoped context owns lifecycle/infrastructure. |
| C | Post-graph finalization service | Graph ends at PM; both entries call an independent service after the graph. |
| D | Event-sourced run ledger | Emit and persist events; derive outputs from a ledger. |
| E | Display-only separation | Keep PM as authority; add labels/warnings only. |

### 2.2 Comparison

| Dimension | A Entry finalizer | B Graph check + RunContext | C Post-graph service | D Ledger | E Display only |
|---|---|---|---|---|---|
| D1 Authority integrity | Medium | High | Medium | High | Low |
| D2 Safety determinism | Medium | High | Medium | High | Low |
| D3 Lifecycle/observability | Medium | High | Medium | High | Low |
| D4 Data correctness | Medium | High | Medium | High | Low |
| D5 Output consistency | Medium | High | Medium | High | Low |
| D6 Compatibility | High | Medium | High | Low | High |
| D7 Security | High | High | High | Medium | High |
| D8 Maintainability/testability | Medium | High | High | Low | Medium |
| D9 Deferred-scope discipline | High | High | High | Low | High |

Medium D1/D2 for A/C reflects entry-boundary placement and orchestration uncertainty, not an inherent second authority: a shared finalizer/service can be the only check. A/C overlap each other; C is an external-service packaging of the same boundary. RunContext, per-run stats, and query reuse are reusable by A/C, so they are not B-only advantages. B's D6 Medium reflects no new-flow checkpoint continuation and full re-execution cost, not complete compatibility.

### 2.3 Rationale

**Candidate A — rejected as the primary design.**

- Pros: smallest graph change; one shared implementation is possible.
- Cons: it sits outside the selected graph-internal placement; the graph can complete without the entry invoking the check; save/display and checkpoint coordination move to entry orchestration. It need not create multiple authorities or mix cleanup.
- Evidence: SB-01 requires the check before return/display/save, not a graph node; the current CLI and `propagate()` paths diverge (`cli/run.py:353-389`, `graph/trading_graph.py:372-404`).

**Candidate B — selected.**

- Pros: matches the selected graph-internal decision; every normal graph completion reaches the check; formal values have one decision/generation authority; checks are pure and offline-testable.
- Cons: adds two nodes; PM output semantics change; checkpoint continuation is not supported, so interrupted analyses re-execute model/data work and may cost more; availability must be snapshotted.
- Evidence: selected graph-internal placement (ADR 001 remains Proposed for human review; no separate approval record is claimed); existing graph extension point after Portfolio Manager (`graph/setup.py:185`); existing context-scoped config pattern (`dataflows/config.py:44`).

**Candidate C — rejected.**

- Pros: graph unchanged; independent service can be tested.
- Cons: semantically overlaps A as entry-boundary finalization; external service packaging creates a second orchestration path that can be skipped or called twice; still needs the same snapshot and full-execution handling, with no requirement-driven advantage.

**Candidate D — rejected.**

- Pros: auditable event history in principle.
- Cons: new persistence/replay model; far beyond active requirements; recovery/version/commit scope is out of scope; high migration cost.

**Candidate E — rejected.**

- Pros: smallest change.
- Cons: does not satisfy SB-01/INV-01; model remains formal authority; no deterministic fail-closed result.

---

## 3. Key design options

### 3.1 Final check location

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-01 | Entry-boundary shared finalizer | Minimal graph change | Reviewer withdrawn; bypass/divergence risk; checkpoint ambiguity | Rejected |
| O-02 | Graph node after Portfolio Manager | One path; one writer; testable | Adds node; availability snapshot and formal-field work | Selected |
| O-03 | Independent post-graph service | Decoupled from graph | Second orchestration; bypass risk | Rejected |
| O-04 | Keep PM authority with labels | Minimal | Violates both invariants | Rejected |

Selected: **O-02**.

### 3.2 Proposal/formal field separation

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-05 | Overwrite PM fields in place | No new fields | Loses proposal after check; hard to prove intermediate/formal separation | Rejected |
| O-06 | Nested `model_proposal` (`{rating, text}` or `null`) plus top-level formal fields | Explicit separation; no fabricated proposal or `present` flag; easy labeling | Requires consumer/test updates | Selected |
| O-07 | Separate parallel dicts for rating/text | Explicit | More field sprawl and duplicated semantics | Rejected |
| O-08 | Store only formal fields | Simple | No original proposal for audit | Rejected |

Selected: **O-06**.

### 3.3 Availability snapshot for the final check

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-09 | Separate snapshot node before risk | Strong separation | Adds a third node; sequence visual change | Rejected to preserve fixed topology |
| O-10 | Risk node calls snapshot function, then risk evaluator | Fixed topology; pure snapshot; serializable state | One node orchestrates two functions | Selected |
| O-11 | Final check reads live RunContext registry | No snapshot | Impure input; harder tests; snapshot state risk | Rejected |
| O-12 | Final check reads report text | No new state | Violates program-authority rule | Rejected |

Selected: **O-10**. The node is orchestration only; the snapshot and risk evaluator remain independent components.

### 3.4 Query reuse mechanism

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-13 | RunContext-owned cache + single-flight for `get_news` | Run-scoped; concurrent-safe; minimal scope | New service | Selected |
| O-14 | Module-level global cache | Simple | Cross-run leakage; violates FR-01 isolation | Rejected |
| O-15 | Rely only on vendor cache | No new code | Does not provide one logical execution per run; vendor behavior unchanged | Rejected |
| O-16 | Cache every router method | Broad reuse | Exceeds FR-01 scope; different methods/identity risks | Rejected |

Selected: **O-13**.

### 3.5 Data observation mechanism

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-17 | Global monkeypatch of router/vendor functions | Low call-site change | Hidden; order-dependent; hard to test; may observe arbitrary calls | Rejected |
| O-18 | Path-specific local observation sites, per-method classifier, registry-internal query-key-to-path-set map, isolated observation handling, query-level failure marks, private pre-fetch call-failure notes, private tracking error, and minimum-content rules | Finite; testable; fetch outcomes are preserved; non-empty error text is not success; pre-fetch rejection cannot fake a query; recordable failures stay local, while unrecordable loss cannot hide behind old success | Requires a verified attachment table, explicit path identity, local synchronization, and content fixtures | Selected |
| O-19 | Event bus | Decoupled | New platform; unnecessary | Rejected |
| O-20 | Model-reported availability | No adapters | Violates FR-03/SB-01; unreliable | Rejected |

Selected: **O-18**.

Rules:

- A known-query classifier exception becomes one conservative per-query `unavailable` observation with a safe “availability classification failed” reason; it is not a provider-failure claim or a fifth status.
- If normal or conservative acceptance fails, a small local query-level failure mark holds the query key and short reason. It is not a public interface, ledger, persistent state machine, or global veto.
- Normal observations, conservative `unavailable` observations, and query marks share one lock and acceptance sequence. For the same query, a later accepted update replaces an earlier accepted update, result or mark; acceptance order alone decides, with no network/wall/monotonic correction. Another query's success does not clear the mark.
- Supplementary observation failures are disclosed only. A necessary query mark is already projected as that selected necessary item's `unavailable`; the item makes basic completeness incomplete with its reason, and completeness does not separately check marks.
- A supported call rejected by existing date/parameter handling before a fetch gets a private call-failure note only: no query key/window, `CompletedObservation`, sequence, FR-01 entry, tracking error, or overwrite of a valid result. It appears as a necessary gap reason when no valid result exists, or as a supplementary limitation; it is not provider `no_data`.
- If the affected query cannot be identified or neither the normal record nor query mark can be reliably recorded, set the private run-local `availability_tracking_error`; later snapshots return `None`, not old success. A single snapshot-construction failure returns `None` without setting that sticky error, and a later call may reconstruct.
- SB-01 consumes only the provided summary and risk status; it does not read the registry or failure marks, re-aggregate queries, or change the formal rating from an observation event.
- Fetch success/failure, shared FR-01 completion, waiter behavior, and no-refetch/no-retry semantics are unchanged.

### 3.6 Manifest persistence

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-21 | Best-effort atomic JSON per run | Non-blocking; simple; observable | May remain running/missing | Selected |
| O-22 | SQLite/DB record | Queryable | New persistence; migration; overkill | Rejected |
| O-23 | In-memory only | Simple | No persistence; fails FR-02 | Rejected |
| O-24 | Background writer | Decoupled | New lifecycle/concurrency; not required | Rejected |

Selected: **O-21**.

### 3.7 Statistics collection

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-25 | One per-analysis handler/collector, injected through that graph execution's config; call-ID dedupe and per-call usage | No cross-run binding; no permanent model binding; direct handler-to-collector ownership; incomplete-usage null rule | Config propagation through nested/parallel boundaries remains unverified | Selected |
| O-26 | Existing counter with missing usage as zero | Minimal | Violates FR-02 token rule | Rejected |
| O-27 | Infer usage from text length | No missing usage | Forbidden; not real usage | Rejected |
| O-28 | Estimate hidden provider retries | More complete in theory | Fabricates calls; forbidden | Rejected |

Selected: **O-25**.

Rules:

- Create one handler/collector per analysis with the RunContext; merge it into that graph invocation/stream's execution config, not model constructors or a replacement callback list.
- Preserve existing custom callbacks, replace no caller callback, and add the analysis handler once. If CLI delegation and propagate share one analysis, they share one handler.
- Callback call IDs dedupe starts/ends and are never synthesized from prompt, model name, or timestamp; per-call usage is stored and summarized. Valid usage is non-negative integers; booleans are invalid. Error/unfinished/invalid usage makes both token totals null; zero calls is true zero. If identity or association cannot be established, do not fabricate a precise count/usage; use null plus a safe warning.
- Graph-internal reflection is included; independent settlement outside the graph is not. The same model object does not establish run ownership.
- Structured-output request actually started counts; a later free-text fallback actually started counts again. Local binding failure, parser/chain/node work, and schema-tool declaration do not count as model/tool executions. No manual per-invoke accumulation is added.
- No event router, global collector, context lookup per callback, hidden retry estimate, model re-call/wait to recover usage, or new diagnostic/compensation mechanism. Callback exceptions only warn and leave business results unchanged.
- Config propagation through subgraphs, parallel nodes, structured/free-text fallback, and reflection remains pending verification; use local config handoff if a boundary does not inherit.

### 3.8 History read

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-29 | Read-only manifest discovery + report read | Minimal; matches FR-05 | Scans run directories | Selected |
| O-30 | Separate index | Faster queries | New index lifecycle; not required | Rejected |
| O-31 | Regenerate reports on read | Always readable | Violates read-only rule | Rejected |
| O-32 | Immutable archive | Strong integrity | Out of scope | Rejected |

Selected: **O-29**.

### 3.9 Security approach

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-33 | Allowlist + known-value sanitization + resolved-target path checks | Matches SR-01/SR-02 scope | Limited coverage; must be stated honestly | Selected |
| O-34 | Generic secret scanner and all-output scan | Broad appearance | Exceeds scope; false positives; no guarantee | Rejected |
| O-35 | Immutable archive/transaction system | Strong integrity | Out of scope | Rejected |
| O-36 | No new security work | Minimal | Fails SR-01/SR-02 | Rejected |

Selected: **O-33**.

### 3.10 Checkpoint policy for the new flow

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-37 | Resume the new flow with a deterministic-tail re-entry and per-position recovery | Could avoid repeating completed model work | Complex identity, observation, statistics, formal-result, and scheduling semantics; beyond current requirements | Rejected for this version |
| O-38 | Trust old checkpoint formal fields when a signature matches | No re-entry work | Matching signature is not proof of a current-run check; old results are not current evidence | Rejected |
| O-39 | Execute the complete analysis every time; no new-flow resume; retain underlying checkpoint code/tests outside the flow | Simple; every run reaches FR-04/SB-01; no old-checkpoint evidence | Interrupted analyses repeat model/data calls; time and cost may increase | Selected |
| O-40 | Add a new recovery/lease/scheduler protocol | Strong ownership in theory | Out of scope; new platform; no requirement | Rejected |
| O-41 | Re-run SB-01 only over old checkpoint summary/risk | Small re-entry | Old summary/risk/formal fields are not current evidence | Rejected |

Selected: **O-39**.

Policy:

- Both entries create a new RunContext, run_id, and initial state and execute the full graph.
- No checkpoint session is acquired; no `invoke(None)` / `stream(None)` resume; no old checkpoint is read as current evidence or deleted.
- A checkpoint-enabled configuration emits a no-resume notice; it does not change configuration/defaults.
- Underlying checkpoint storage, thread IDs, signatures, cleanup tools, and tests remain regression assets but are outside the new flow.
- Failure follows FR-02; a later invocation is a new analysis and re-executes model/data work. No automatic recovery, retry, text completion, or cross-analysis evidence inheritance is added.
- This limit is distinct from deferred FR-06 Markdown report-text recovery. Any future new-flow resume requires reopening the ADR.

### 3.11 Formal result missing or invalid

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-42 | Consumer generates REVIEW when formal fields are missing | Always produces a rating string | Violates SB-01/INV-01; diagnostic masquerades as a check result | Rejected |
| O-43 | Consumer parses the model/report text to recover a formal rating | Reuses existing text | Re-parsing is forbidden; can create a different rating | Rejected |
| O-44 | Shared `FormalResultContract` validates the five-field structure and reports execution contract failure | SB-01 remains sole business authority; missing output is not disguised; field ambiguity is removed | Entries/save paths must handle execution failure | Selected |
| O-45 | Treat missing formal fields as normal success | Minimal handling | Unsafe and false success | Rejected |

Selected: **O-44**. This is the same shared contract described in the blueprint and ADR; it is not a third handling scheme.

Rules:

- Formal fields are exactly `model_proposal`, `gate_status`, top-level `reasons`, `final_rating`, and `final_trade_decision`.
- `model_proposal` is `{rating, text}` or `null`; inner values may be `null`; no `present` field is used. An illegal proposal rating is handed to SB-01, not rejected as a contract failure.
- FR-04 reasons stay in `portfolio_risk_result.reasons`; top-level `reasons` is SB-01-owned. The risk object is not flattened into the formal fields.
- SB-01 missing/invalid input or condition failure => complete blocked/REVIEW with actual reasons.
- SB-01 handled internal exception => complete error/REVIEW with an actual reason.
- Passed keeps a legal five-tier rating; blocked/error uses REVIEW and a non-whitespace manual-review notice. Passed may have an empty reason list.
- Missing/invalid formal output after the graph, or lost in transfer/merge => execution contract failure, not REVIEW.
- No text parsing, proposal fallback, consumer-generated REVIEW, or substitute formal text.
- The contract validates field presence/types, proposal shape, legal gate/rating sets, passed/blocked/error rating consistency, a non-whitespace `final_trade_decision` per IF-19, and string-list reasons with a blocked/error reason; it does not re-judge data or risk, call model/data, repair, or create a second status.

### 3.12 Save and persistence failure classification

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-46 | Treat manifest, report, final-state, and memory uniformly as best-effort | Simple rule | Conflicts with FR-02/INV-01 and hides failed state/memory/report saves | Rejected |
| O-47 | Let all save failures return normal success | Always succeeds | False success; violates existing failure behavior | Rejected |
| O-48 | Path-specific classification | Manifest warns only; state/new-memory/requested report preserve existing failure behavior and can fail the run; disabled/same-day no-op is not failure | Requires internal save outcome and careful lifecycle wiring | Selected |
| O-49 | Transactional rollback across artifacts | Strong consistency | Out of scope; not required by FR-02/INV-01 | Rejected |

Selected: **O-48**.

Rules:

- Manifest failure only warns; it does not change run outcome or formal result.
- Final-state JSON failure preserves exception propagation and makes the run `failed`; later memory append is not attempted.
- New-memory append failure makes the run `failed`; a saved final state is not rolled back.
- Memory disabled or existing same-day record is not a save failure.
- `_memory_step()` settlement/reflection/read degradation is not promoted to run failure.
- CLI requested report failure is captured for display but reported internally as `failed`; the run is `failed`.
- User declines report save: `not_requested`, not failed.
- Partial Markdown/HTML failure: overall save `failed`, truthful Markdown ref retained, no rollback and no fabricated HTML success.
- Independent `save_reports()` after `propagate()` does not reopen or modify the completed run manifest.

The run outcome may change without changing the formal result. This is the same classification used by the blueprint and ADR, not a third scheme.

### 3.13 RunContext creation versus reusable object lifecycle

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-50 | Create the analysis RunContext in the graph constructor | One early point | Confuses object construction with an analysis; creates manifest without analysis; contaminates repeated use | Rejected |
| O-51 | Require RunContext before object construction for every entry | Uniform wording | Impossible for the existing program API, where the object exists before `propagate()` | Rejected |
| O-52 | Entry-specific creation point with reusable object and per-run stats handler/collector injected via execution config | Matches both entry lifecycles; keeps object construction distinct; isolates runs; no permanent model binding | Different timing coverage; config propagation needs verification | Selected |
| O-53 | Store RunContext or collector on the graph and reuse it | Fewer objects | Cross-run identity/statistics/cache contamination | Rejected |

Selected: **O-52**.

Rules:

- CLI: selection/config/basic validation → RunContext and running manifest → graph-object construction/client initialization/initial compile → per-run preparation → execution. Construction time is inside the run.
- Program: existing object → `propagate()` → per-call validation/effective config → new RunContext and running manifest → per-run preparation → execution. Object construction and idle time are outside the run; construction failure before `propagate()` creates no run.
- The object constructor creates no run_id or manifest and stores no RunContext. Each independent call gets a new run_id, stats handler/collector, reuse registry, and availability registry.
- The initial config summary uses a shared projection over the existing `run_settings()` allowlist; it does not require a constructed graph.
- Model clients may be reusable, but the stats handler/collector is per-analysis and injected only through that execution's `callbacks` config. Its callbacks directly update that collector; no active-context lookup or global router is used.
- Existing custom callbacks are preserved; only the analysis's own stats handler is added once. Exact propagation through subgraphs, parallel nodes, structured/free-text fallback, and graph-internal reflection remains pending verification.

### 3.14 Risk numeric handling and result representation

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-54 | Exact rational decision plus `Decimal` objects in graph state | Direct arithmetic | Type/serialization ambiguity; state not JSON-compatible | Rejected |
| O-55 | Exact rational decision, one JSON-compatible risk result with decimal-string/null metrics, local display formatting | JSON-compatible; context-independent decisions; no normalized-state round trip | Requires local parsing and formatting, not a new protocol | Selected |
| O-56 | Float arithmetic with display formatting | Simple | Boundary and large-scale errors; display can change judgment | Rejected |
| O-57 | `json.dump(default=str)` or per-consumer conversion | Minimal plumbing | Implicit values, inconsistent types, no canonical semantics | Rejected |

Selected: **O-55**.

Rules:

- Pass/block uses exact rational cross-multiplication, not ambient `Decimal` precision.
- The risk module has local parse/validate, decide, and one-result-projection responsibilities; these do not require separate classes, services, modules, or public APIs.
- Raw scenario inputs are not required to enter a persistent normalized state and be parsed back. If carried in graph state, a simple JSON-compatible mapping is enough; the result metrics are decimal strings or null.
- Report metrics may be locally formatted; a repeating quotient is still computed and not null. Each metric is null only when its own operands are invalid; an invalid ticker, currency, or threshold does not clear a computable metric. Fixed decimal places, round-half-even, no-exponent notation, and trailing-zero rules are not acceptance requirements or approval gates.
- Display formatting never feeds back into status. CLI and report consume the same result but may differ in layout or percentage presentation.
- The deterministic risk area states that only the listed caller scenario is checked and that other model-proposal amounts/prices are not verified; it also keeps the classroom and non-trade-authorization statements.
- The manifest receives no risk fields and memory is not required to store risk metadata; the current state log does not yet persist risk data. Existing save-failure and full-execution checkpoint policies are unchanged.

### 3.15 Context delivery for the research stage

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-58 | Cross-role context framework with shared layers, normalization, deduplication, token budgets, automatic trimming, and reinjection | Uniform appearance in theory | No current requirement; changes existing prompts and failure behavior; adds unverified tokenizer and role-failure machinery; risks dropping required evidence | Rejected |
| O-59 | Keep each role's existing prompt path; add only the FR-03 research-stage program summary at the first Bull call and reuse it in later Bull/Bear and Research Manager calls | Minimal behavior change; preserves full reports and structured paths; directly traceable to FR-03 | Small wrapper and renderer; research-stage summary must be carried in state | Selected |
| O-60 | Do not pass the FR-03 summary to the research stage | No prompt change | Does not satisfy the current research-start summary requirement | Rejected |

Selected: **O-59**.

Rules:

- Context classes are logical descriptions of provenance and authority, not a shared physical order or layer object.
- Existing analyst prompt assembly, tool-message history, full reports, debate history, manager plans, memory lessons, and structured-output/fallback paths remain.
- Only Bull, Bear, and Research Manager receive the FR-03 research-stage summary. It is program-rendered, labeled, uncompressed, untruncated, and reused across those calls; it does not replace analyst reports.
- The first Bull invocation receives the summary directly; a state update is also stored for later roles.
- No new model or data call is added by summary attachment.
- No unified input budget, global cap, tokenizer, automatic history trimming, compression, mandatory-block reinjection, local overflow refusal, or new role-failure mechanism is added.
- Existing client/provider limits apply; long histories or reports may fail through the existing error path.
- Context budgets, compression thresholds, and compressed-constraint reinjection are deferred by ADR 001 D-10c. They are not current design, implementation, or acceptance, and no tokenizer/trim/reinjection flow is added. FR-03 research-stage summary remains active.

Implementation cost: one small wrapper around the first Bull call, one deterministic program-block renderer, one state field, and local prompt additions for the three research-stage roles. Behavior change is limited to those prompts; the full-report and manager paths remain intact.

### 3.16 AvailabilitySummary producer and consumers

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-61 | Each consumer rebuilds completeness and necessary gaps from the registry | Flexible local views | Conflicting rules; failure marks leak; repeated maintenance; SB-01 would re-aggregate | Rejected |
| O-62 | Summarizer produces one plain five-field `AvailabilitySummary`; consumers read it | One completeness calculator; stable JSON-compatible shape; same-time consistency; no registry exposure | Requires a small summary-construction function and explicit context arguments | Selected |
| O-63 | Store extra `missing_necessary_items` and/or a second completeness field alongside the summary | Apparent convenience | Duplicate truth, divergence risk, unnecessary state | Rejected |

Selected: **O-62**.

Rules:

- Fields are exactly `basic_completeness`, `applicability_note`, `observations`, `necessary_items`, and `supplementary_limitations`.
- The summarizer reads a registry copy, applies failure marks, selects each necessary item's current update by existing object/range and acceptance order, builds necessary items and supplementary limitations, and computes completeness once from the selected `necessary_items` only.
- `observations` carry one current logical-query projection with method, object, effective parameters, path identity, source, one of the four statuses, and a safe reason. Failure marks become affected-query `unavailable` consumer projections, not fabricated stored observations or a public status.
- `necessary_items` carry item id/method, object/range, status, and reason; `not_attempted` appears only here when no completed result exists.
- Necessary gaps are a filter over non-available necessary items, not a second completeness calculation. No duplicate gap list or second completeness state is stored.
- Supplementary limitations are separate and never count as necessary gaps.
- Research gets one independent summary at start and keeps it. SB-01, the final check, and CLI read only summary fields; the report writer reads only prepared report state. The entry report-preparation step is the only path from this run's registry to the report, and no consumer rebuilds completeness.
- A `None`/absent summary is stored as `null` for research, with a renderer-generated unavailable display text; SB-01 uses its missing/invalid rule and report/CLI shows the unavailable notice. `null` is not a fourth completeness value or a stored third summary type.
- No independent schema file, version, hash, digest, source proof, or registry exposure is added.

### 3.17 Observation attachment point

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-64 | Observe in router/vendor code or tool callbacks | Central-looking | Duplicates or misses direct prefetch, mixes FR-02 callbacks with FR-03, and cannot preserve per-path semantics | Rejected |
| O-65 | Wrap only tool functions | Small call-site count | Misses P-14/P-15 direct prefetch and complicates P-09/P-13 sharing | Rejected |
| O-66 | One local helper at each supported call site; shared news executor for P-09/P-13; per-indicator P-03; direct prefetch wrappers P-14/P-15 | One observation per business execution; early failures covered; direct paths covered; no router/vendor duplication | Requires an explicit attachment table and careful argument/default handling | Selected |
| O-67 | Global monkeypatch or generic middleware | No call-site edits | Hidden, order-dependent, may observe arbitrary calls, and does not fit the finite supported scope | Rejected |

Selected: **O-66**.

Rules:

- The 15 paths have exactly one observation site at their existing call location.
- Router/vendor internals and tool callbacks do not write FR-03 observations; fallback attempts remain inside one business execution.
- P-03 observes each split indicator, not the joined string. P-09/P-13 use one plain shared news executor with explicit path IDs, one fetch and one observation for the same query, and two path associations; a date failure before a legal key creates no reuse entry and may add one private parameter call-failure note.
- Early returns before a fetch use the private call-failure note, not a query observation or invented effective window; schema/name/message errors before the supported body are not executed queries.
- P-14/P-15 are observed around their existing direct sentiment calls.
- Early date/parameter rejections create no valid query, sequence, FR-01 entry, or tracking error; no active `RunContext` means no observation behavior.
- Effective defaults reuse existing code/config: P-10 config lookback/limit, P-11 365, P-12 6, P-14 30, P-15 5; None is not recorded as infinite.
- Router paths do not infer a winning vendor; differing producer interpretations are recorded as reliable request semantics plus a limitation, not a fabricated uniform value.
- No new model/vendor/network call, monkeypatch, middleware, or public framework is added.

Implementation cost: one small internal helper, a shared news executor, and localized wrappers at the 15 call sites. No router/vendor changes or observation framework.

### 3.18 Report availability source

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-68 | Writer reads active `RunContext`, registry, or graph last-run summary | Appears current | Run-outside files can mix analyses; violates data ownership; writer has a hidden data source | Rejected |
| O-69 | Run-in entry prepares one terminal summary from this registry into report/final state; writer reads that state; independent save uses only passed final_state | Clear ownership; no cross-run mixing; Markdown/HTML share input; no writer lookup | Requires report-preparation step before save/return | Selected |
| O-70 | Reuse `research_availability_summary` for the report | No preparation step | Misses results after research start; violates report-time scope | Rejected |
| O-71 | Persist a registry/history for later report regeneration | Could reconstruct later | New persistence/protocol; outside FR-03 scope | Rejected |

Selected: **O-69**.

Rules:

- Run-in report preparation takes one current terminal summary after graph execution while the registry is accessible, then writes the plain mapping to `data_availability_summary` in report/final state. No later data-fetch/background stage is added.
- Updating delivery/display availability is only a refresh: SB-01 keeps its check-time summary and formal fields/reasons are not rerun or changed. No hash/version/history/second-result binding is added.
- The writer only reads the passed state; it does not read active context, registry, summarizer, graph last-run cache, research summary, or model text. Report-preparation time does not mean fetching newer market data.
- Markdown and HTML use the same prepared state. Post-run display uses the prepared final state; showing an already generated file uses that file's data.
- Independent `save_reports(final_state, ...)` uses only that final_state's terminal summary, even while another analysis runs. It does not query, re-summarize, rerun SB-01, reopen the run, or modify the ended manifest.
- Null/missing/unusable availability is disclosed as “program summary unavailable” in the deterministic region; no completeness value is fabricated and no formal-result failure is inferred. A preparation failure only warns and leaves the field null/absent, without blocking report generation/save or changing the formal result/run outcome. This is failure handling, not normal FR-03 delivery. Formal-result invalidity remains a separate `FormalResultContract` issue.
- No `report_availability_summary`, history, version, hash, snapshot ID, persistent registry, or cross-file transaction is added.

### 3.19 Observation ordering and tracking error

| Option | Description | Pros | Cons | Outcome |
|---|---|---|---|---|
| O-72 | Order by fetch/network completion time, wall clock, or monotonic time | Attempts to reflect external timing | Contradicts registry acceptance semantics; concurrency ambiguity; external-time protocol | Rejected |
| O-73 | One registry acceptance sequence for observations, conservative unavailable updates, and query marks; private sticky tracking error only for unlocatable/unrecordable loss | Consistent latest update; local failures stay local; lost observations cannot be hidden by old success | Tracking error makes later snapshots unavailable for that run | Selected |
| O-74 | Ignore unrecordable observation loss and reuse old success | No extra state | False current availability; hides lost data | Rejected |
| O-75 | Reinstate a public permanent `summary_confirmable` veto for any observation failure | Simple global block | Reintroduces withdrawn over-broad veto; violates query-level recovery | Rejected |

Selected: **O-73**.

Rules:

- Acceptance under the registry lock is the only ordering source. No helper/fetch/callback entry sequence, network time, clock time, or distributed proof is used.
- Normal observations, conservative `unavailable` observations, and query marks use the same sequence; for one query the later accepted update wins, while other queries remain independent.
- A pre-fetch parameter/date rejection uses a private `availability_call_failures` note, not an observation or completion sequence. It never creates a key/window, enters FR-01, overwrites a valid result, or sets tracking error. It projects only to a necessary-item `not_attempted` reason when no valid result exists, or to `supplementary_limitations`; note-write failure only warns.
- `availability_tracking_error` is private, null or fixed safe reason, not in `AvailabilitySummary` or any consumer, and not persisted. Only unlocatable/unrecordable observation loss sets it; new runs start null; success/snapshot does not clear it. Pre-fetch parameter/date rejection does not set it.
- With tracking error, every later snapshot returns `None` and never old success. A single snapshot-construction failure returns `None` without setting the sticky fact.
- Local fallback failures set tracking error independently of the failed write. No transaction log, retry, recovery, double store, or public gate is added.

---

## 4. Selected architecture summary

| Area | Selection | Primary requirements |
|---|---|---|
| Final authority | Graph-internal `Final Recommendation Check` node | SB-01, INV-01 |
| Proposal | `model_proposal` is `{rating, text}` or `null`; PM does not write formal fields | SB-01 |
| Risk | Pure `PortfolioRiskEvaluator` from caller scenario plus explicit analysis ticker; field/threshold contract; risk-scoped `reasons`; exact rational cross-multiplication; one JSON-compatible result; local display formatting; only the listed caller scenario is checked | FR-04 |
| Availability | 15 path-specific observation sites; shared news executor for P-09/P-13; per-indicator P-03; direct P-14/P-15 wrappers; run-scoped registry; one acceptance sequence for observations/marks; private pre-fetch call-failure notes; private tracking error; summarizer-produced five-field `AvailabilitySummary` or None; entry-prepared terminal run-in report summary; independent saves use final_state only | FR-03 |
| Context delivery | Existing per-role prompt paths remain; only research-stage roles receive the FR-03 program summary; no unified assembler, input budget, automatic trimming, or compression | FR-03 |
| Query reuse | RunContext-owned single-flight for two `get_news` paths; completed observation accepted before publish; path associations separate | FR-01, FR-03 |
| Lifecycle | CLI creates RunContext before graph-object construction; `propagate()` creates a new one after invocation; manifest best-effort; report/state/memory path-specific; run outcome can fail without rewriting the formal result | FR-02, INV-01 |
| Statistics | One per-analysis handler/collector injected via execution config; call-ID dedupe, per-call usage, graph-internal reflection included; no cross-run accumulation; incomplete/unreliable usage => null | FR-02 |
| History | Read-only manifest discovery and report read | FR-05 |
| Credentials | Limited allowlist/known-value sanitization | SR-01 |
| Paths | run_id validation + resolved-target ownership | SR-02 |
| Checkpoint | New flow always executes fully; no resume or old-checkpoint evidence; underlying checkpoint code/tests retained outside the flow | Compatibility constraint, FR-02, SB-01 |
| Formal result contract | Shared validation of `model_proposal`, `gate_status`, top-level `reasons`, `final_rating`, and `final_trade_decision`; missing/invalid formal output is execution failure, not consumer REVIEW | SB-01, INV-01 |
| Deferred scope | No implementation or acceptance claim | FR-06, FR-07, PR-01, CR-01 |

---

## 5. Evidence ledger

| Claim | Evidence | Status |
|---|---|---|
| Two entry points diverge | `cli/run.py:99-389`; `graph/trading_graph.py:167-404` | Static code |
| PM currently writes formal fields | `agents/managers/portfolio_manager.py:80-104` | Static code |
| Graph ends at PM | `graph/setup.py:185` | Static code |
| Graph object constructed before `propagate()` | `graph/trading_graph.py:54-113`; `cli/run.py:123` | Static code |
| Current state log has no risk field | `graph/trading_graph.py:437-475` | Static code; new type-contract gap, not an existing failure |
| Analyst join precedes first Bull | `graph/setup.py:160-166` | Static code |
| Role prompt assembly differs by role | analysts use system/message/tool history; Bull/Bear and risk debaters use inline strings; Trader uses a message list; managers use structured output/fallback | Static code |
| Portfolio Manager currently asks for a final trading decision | `agents/managers/portfolio_manager.py` prompt and structured `PortfolioDecision` path | Static code; prompt wording changes only for proposal semantics |
| Research consumers currently lack an availability field | `bull_researcher.py`, `bear_researcher.py`, `research_manager.py`; `agents/state.py` | Static code; design addition required |
| Sentiment prefetch calls `get_news.func()` | `sentiment_analyst.py:66` | Static code |
| Current CLI binds stats callbacks at model construction and graph config | `graph/trading_graph.py:78-80`; `cli/run.py:115-128`, `:222-224` | Static code; design replaces permanent model binding with per-run execution config |
| Current program entry passes no stats callbacks | `graph/trading_graph.py:376` | Static code; design adds the same per-run config injection path |
| Existing context-scoped config | `dataflows/config.py:44-62` | Static code |
| Existing safe ticker component | `dataflows/symbols.py:155` | Static code; existing test `test_safe_ticker_component.py` |
| Existing request scrubber | `dataflows/net.py:6` | Static code; existing test `test_get_scrubbed.py` |
| Existing memory log | `memory/log.py:32` | Static code; existing memory tests |
| Existing report writer | `reporting.py:92` | Static code; existing `test_reporting.py` |
| Independent report save takes final_state | `graph/trading_graph.py:277-286`; `cli/run.py:426-449` | Static code; design adds availability preparation before this read |
| Markdown and HTML share final_state/parts | `reporting.py:100-119`; `report_html.py:248` | Static code; design requires one prepared report input |
| Existing stats counter | `cli/stats_handler.py:9` | Static code; lacks call-ID dedupe, per-call records, and the null-usage rule |
| FR-04 scenario is not derived from portfolio text | `portfolio.py:23-51` renders holdings/cash only | Static code; no scenario fields are filled |
| FR-03 producer branches | `router.py`, vendor modules, `date_window.py`, social fetchers | Static code; authoritative mapping in blueprint §8.3; some AV empty-payload fixtures pending |
| Baseline behavior | `baseline/runs/baseline-20261020-01` | Baseline only; data coverage incomplete |
| Requirement counts | `docs/req/requirements.yaml` | Independently counted; matches 13/55 |
| New behavior | None | Not implemented, not tested |

---

## 6. Trade-offs and limitations

- The selected design changes Portfolio Manager output semantics; existing consumers and tests must be updated in implementation. Its prompt wording changes only to request a proposal for the deterministic check; the evidence, rating scale, structured output, and fallback remain.
- The graph gains two nodes; the new flow fully re-executes after interruption, repeating model/data calls, so time and cost may increase.
- The design does not add new-flow resume or claim a performance/cost benefit.
- Missing or invalid formal output is an execution contract failure, not a business REVIEW; consumers do not fabricate REVIEW status or formal text.
- The formal contract has exactly five top-level fields; `model_proposal` is nested-or-null and has no `present` flag. FR-04 reasons remain in the risk object, while SB-01 reasons use the top-level `reasons` list.
- Report, final-state, and new-memory failures are not uniformly best-effort; they preserve existing failure behavior and can make the run `failed` without rewriting the formal result.
- CLI construction time is inside the run; program object construction and idle time are outside. The two entries are not directly comparable on initialization time.
- Stats handler/collector is per-analysis and injected through execution config, not model construction. Exact callback propagation through analyst subgraphs, parallel nodes, structured/free-text fallback, and graph-internal reflection remains unverified.
- Independent settlement is outside the graph and is not automatically attributed to an analysis merely because it shares a model object. If a graph boundary does not inherit config, the local fallback is explicit config handoff, not a global collector or router.
- FR-04 decisions must use exact rational cross-multiplication, not float arithmetic or display rounding; the result uses decimal-string/null metrics and local display formatting without feeding back into status.
- FR-04 validates only the amounts and prices explicitly supplied in the caller scenario. Other model-proposal numbers are not extracted, compared, shown as verified, or used as a new blocked condition.
- Display precision and layout are local implementation choices; fixed decimal places, round-half-even, no-exponent notation, and trailing-zero rules are not architecture acceptance requirements.
- Components are logical responsibilities; implementation should use small functions at existing boundaries and not one class/module/service per component. Deferred requirements require no placeholder interfaces.
- FR-03 relies on a verified producer-branch table; non-empty text is not success, and some Alpha Vantage empty-payload shapes remain unverified.
- The first Bull call must receive the research-start summary directly; explicit P-09/P-13 path identity and the wrapper integration are pending framework verification.
- Observation handling cannot block shared publication or replace the original fetch outcome. Classifier failures become conservative per-query observations; failed acceptance becomes a local query-level mark; pre-fetch parameter rejection becomes only a private call-failure note. An unidentifiable completed query or unrecordable local fallback sets the private tracking error, making later snapshots `None`; this is not a general public veto. A single snapshot-construction failure is not sticky. Minimum available content (P-02/P-04/P-09/P-10) needs fixture verification.
- `AvailabilitySummary` is one read-only five-field mapping produced by the summarizer. Consumers do not rebuild completeness, do not rely on a duplicate gap list, and do not receive registry failure marks as a public status.
- Run-in reports use one entry-prepared terminal summary from the current registry; independent saves use only the passed final_state. The writer never reads active context/registry/summarizer, and missing availability is disclosed without a fabricated state or SB-01 rerun.
- Observation attachment is path-specific: 15 unique sites, a shared internal news executor for P-09/P-13, per-indicator P-03, and direct-call P-14/P-15. Early failures and existing defaults are recorded from the actual call context without changing router/vendor behavior.
- Availability snapshotting in the risk node is a pragmatic orchestration choice; it must be documented as non-authoritative plumbing.
- The CLI save/display split changes interaction ordering; it must preserve existing error display and user expectations.
- Context delivery changes only the research-stage prompts: the FR-03 program summary is added to the first Bull call and reused by later Bull/Bear and Research Manager calls. Existing analyst, Trader, risk-debate, and Portfolio Manager inputs remain otherwise intact.
- No unified context assembler, cross-role deduplication, input-token budget, global cap, tokenizer, automatic history trimming, compression, reinjection retry, or local overflow refusal is added. Existing client/provider limits apply, and long histories may fail through the existing error path.
- Context budgets, compression thresholds, and compressed-constraint reinjection are deferred by ADR 001 D-10c; they are not a current design gap, implementation task, or acceptance target.
- FR-07 briefs and CR-01 cost comparison remain deferred; no short-summary replacement, cost comparison, or optimization benefit is claimed.
- Security coverage is explicitly limited; no comprehensive no-leak or all-platform path guarantee is claimed.
- History reads current file content; no immutability, hash, or repair guarantee is claimed.
- No performance, cost, quality, or live-data evidence exists for the new design.

---

## 7. Decision record references

| Decision | ADR section | Status |
|---|---|---|
| Graph-internal final check | ADR 001 §2, §3.2, §4.2 | Proposed |
| `model_proposal` separation and nested-or-null shape | ADR 001 §3.2, §6.1, §6.5 | Proposed |
| RunContext and manifest lifecycle | ADR 001 §3.3, §6.3 | Proposed |
| Stats handler, config injection, and reflection attribution | ADR 001 §3.3, §6.3, §6.4 | Proposed; propagation unverified |
| Data adapters and reuse | ADR 001 §3.4 | Proposed |
| Risk input and thresholds | ADR 001 §3.4, §6.1 | Proposed |
| Security and history scope | ADR 001 §3.5 | Proposed |
| Full-execution checkpoint policy | ADR 001 §3.5, §6.2 | Proposed |
| Formal result contract and top-level reason scope | ADR 001 §3.2, §6.1, §6.5 | Proposed |
| Persistence classification | ADR 001 §3.3, §6.4, §6.6 | Proposed |
| Entry-specific run creation and stats-handler ownership | ADR 001 §3.3, §6.3, §6.4 | Proposed; execution-config propagation unverified |
| FR-04 numeric contract and FR-03 recognition | ADR 001 §3.4 | Proposed; some producer branches unverified |
| Research-entry summary and query-path association | ADR 001 §3.4, §6.1 | Proposed; path identity integration unverified |
| Risk result representation and input boundary | ADR 001 §3.4 | Proposed; implementation pending |
| Acceptance ordering, pre-fetch call failures, tracking error, and AvailabilitySummary contract | ADR 001 §3.4 | Proposed; fixtures pending |
| Report availability source and terminal final_state handoff | ADR 001 §3.4, §6.3 | Proposed; integration pending verification |
| Path-specific observation attachment and shared news execution | ADR 001 §3.4, §6.1 | Proposed; call-site integration pending verification |
| Role-local context delivery and research summary | ADR 001 §3.4, §7 | Proposed; wrapper integration pending verification |

---

## 8. Review questions

1. Is Candidate B accepted over A/C/D/E?
2. Is the risk node orchestrating `AvailabilitySummarizer.snapshot(asset_type, enabled_analysts, analysis_context)` and `PortfolioRiskEvaluator.evaluate()` acceptable, or is a separate snapshot node required?
3. Is the selected proposal shape accepted: `model_proposal` is `{rating, text}` or `null`, with no `present` field, and only SB-01 writes the formal fields?
4. Are the CLI save/display boundaries accepted?
5. Is the role-local context delivery accepted: existing prompt paths remain, only research-stage roles receive the FR-03 program summary, and no unified assembler is added, with input budget/trimming/compression/reinjection deferred by ADR 001 D-10c?
6. Are the security and history scopes accepted without expansion?
7. Is the full-execution checkpoint policy accepted: new RunContext/initial state every time, no new-flow resume or old-checkpoint evidence, underlying checkpoint code/tests retained?
8. Is the shared `FormalResultContract` accepted with exactly `model_proposal`, `gate_status`, top-level `reasons`, `final_rating`, and `final_trade_decision`, including the rule that missing/invalid output is an execution failure rather than REVIEW?
9. Is the path-specific persistence classification accepted: manifest warns only, while final-state/new-memory/requested report failures can make the run `failed` without rewriting the formal result?
10. Is the entry-specific RunContext creation boundary accepted, with CLI object construction inside the run, program object construction/idle outside it, and one per-analysis stats handler/collector injected through execution config?
11. Are the FR-04 field/threshold and caller-scenario-only contract, and the FR-03 per-method recognition table, accepted, including conservative handling of unverified branches?
12. Are the research-start summary attachment to the first Bull call, the five-field `AvailabilitySummary`, and the separation of completed observations from path associations accepted?
13. Are the exact-rational decision, one JSON-compatible result with decimal-string/null metrics, local display formatting, and caller-scenario-only boundary accepted?
14. Are query-level observation failure handling, conservative classification failures, one shared acceptance sequence for observations and marks, later-accepted replacement, guaranteed shared publication, and the minimum available-content rules accepted?
15. Is the five-field `AvailabilitySummary` accepted as the sole completeness output, with consumers reading it without rebuilding completeness or receiving failure marks/tracking error as public states?
16. Is the path-specific attachment accepted: 15 unique observation sites, shared P-09/P-13 news execution, per-indicator P-03, direct P-14/P-15 wrappers, and no router/vendor/callback duplication?
17. Is the stats design accepted: one per-analysis handler bound to one collector and injected through execution config, call-ID dedupe, per-call usage/null totals, graph-internal reflection attribution, no EventRouter, and unverified propagation treated as a local handoff question?
18. Is the report source design accepted: run-in reports use one entry-prepared terminal summary; independent saves use only passed final_state; writer has no registry/context/query lookup; missing availability is disclosed without a fabricated state or SB-01 rerun?
19. Is the ordering/tracking design accepted: registry acceptance order only, private pre-fetch call-failure notes with no fake query/single-flight/tracking error, private sticky tracking error only for unlocatable/unrecordable completed-query loss, later snapshots None rather than old success, and single snapshot-construction failure non-sticky?
20. Are all deferred requirements explicitly excluded from current acceptance?
