# Structural Constraints

## 1. Scope and authority

This D3 structural-constraints document is located at the course-required project path `docs/code-governance/structural-constraints.md`. All paths below are relative to the application project root containing `AGENTS.md` and `architecture-blueprint.md`. Module allocations marked proposed remain proposals; this document neither implements code nor grants file permissions or architecture approval.

Inputs are `docs/req/requirements.yaml` (current v1.48.0), `architecture-blueprint.md`, `docs/architecture/adr/001-graph-internal-final-check.md`, and the D2 invariant, trace, state, runtime-policy, and permission artifacts. Verification is governed by `docs/code-governance/verification-constraints.md`. Course requirements are taken from the project specification, pages 5–6: unique module ownership for architecture elements, incremental extension of the baseline, module/function references to relevant ADRs and invariants, and explicit authority boundaries.

D1 controls product semantics; D2 controls architecture contracts. This file constrains code organization without adding business checks or acceptance thresholds. Use the actual round plan. `docs/plans/round-01.md` is approved at `a8ec42ecdf4199f91d3001fc6e2b1e887a0c5e41`; its internal Pending/Proposed cells are historical, and later rounds need their own approval. No code or plan-file creation is authorized by this document alone.

## 2. Existing baseline and implementation status

Preserve the imported TradingAgents application under `src/`. Its packages are `src/tradingagents/` and `src/cli/`; tests are under `test/offline/` and `test/live/`. Do not replace the baseline, introduce another source/test layout, reformat unrelated code, or rewrite existing vendors and agent workflows merely to implement governance.

Static inspection shows that `src/tradingagents/graph/setup.py` currently connects Portfolio Manager directly to END. `src/tradingagents/graph/trading_graph.py` currently saves state and memory through `record_decision()`, uses `run_rating()` for the baseline rating, and contains checkpoint behavior. These are existing behaviors to adapt at approved integration points, not evidence that the proposed deterministic tail or other new requirements are already implemented. The C-08 FR-04 and C-09/IF-09 cores are implemented separately under their rounds; neither is wired into the production graph or formal-authority path. C-09 is the independent final-check callable only, not a production node or consumer contract.

The active scope is FR-01–FR-05, SB-01, INV-01, SR-01, and SR-02. FR-06, FR-07, PR-01, and CR-01 remain deferred. Do not add recovery, analyst briefs, performance/cost experiments, or reserved future interfaces for them.

## 3. Unique primary module ownership

Each logical architecture element must have exactly one primary owning module. Multiple related elements may share a module; an element does not require its own class, service, or file. Other modules may provide explicit call-site adapters or consume its outputs, but must not duplicate its decision logic.

The table below is a proposed implementation allocation for review, except that Round 1 created the C-08 module and Round 2 created the independent C-09 module. It is not a claim that other new files exist or an authorization to create them. Paths start at the project root; application paths use `src/`. A round may approve a different equally small allocation before implementation, provided the affected ownership table and D2 references remain consistent. Do not silently introduce a second owner.

| D2 element | Primary owner | Existing integration sites / constraints |
|---|---|---|
| C-01 CLI Entry Adapter | `src/cli/run.py` (existing) | `src/cli/main.py` delegates; entry coordinates, never decides formal rating |
| C-02 Programmatic Entry Adapter | `src/tradingagents/graph/trading_graph.py` (existing) | Preserve `propagate()` return shape and entry-specific lifecycle |
| C-03 RunContext / RunGovernor | `src/tradingagents/run_context.py` (proposed) | Per-run identity, infrastructure ownership, terminalization; no business authority |
| C-04 Run statistics | `src/cli/stats_handler.py` (existing, adapted) | One run-owned callback handler/collector; no CLI UI dependency in reusable statistics logic |
| C-05 QueryReuseService | `src/tradingagents/dataflows/query_reuse.py` (proposed) | Supported news executor delegates here; existing vendor flow remains intact |
| C-06 Observation protocol / local helper | `src/tradingagents/dataflows/availability.py` (proposed) | Local attachments remain at D2-listed tool/prefetch sites; they delegate to one protocol owner |
| C-07 Availability registry/summarizer/renderer | `src/tradingagents/dataflows/availability.py` (proposed) | One completeness calculation; independent plain snapshots |
| C-08 PortfolioRiskEvaluator | `src/tradingagents/portfolio_risk.py` (exists; Round 1) | Public module-level callable `evaluate(...)` (IF-08) plus local parse/validate/compare/project helpers, not a generic numeric framework. Offline tests: `test/offline/test_fr04_risk.py`; only FR-04-FC01–FC04/core IR-14 are verified. |
| C-09 FinalRecommendationChecker | `src/tradingagents/final_recommendation.py` (exists; Round 2 independent core) | Public module-level callable `evaluate(proposal, availability, risk, asset_type)` with no default parameters, plus local projection/validation/result helpers; no class is required. It is the sole formal-business-value authority at the core boundary. Production graph/entry/consumer wiring and `FormalResultContract` (IF-19) remain unimplemented. Offline tests: `test/offline/test_sb01_final_check.py`; only SB-01-FC01–FC04 core and local IR-01/IR-02 responsibility are verified. |
| C-10 Graph wiring / deterministic nodes | `src/tradingagents/graph/setup.py` (existing, adapted) | Existing agent factories remain; wrapper and thin nodes delegate business logic |
| C-11 Report writer | `src/tradingagents/reporting.py` (existing) | HTML and CLI renderers consume prepared values, not new business decisions |
| C-12 Memory decision adapter | `src/tradingagents/memory/log.py` (existing) | Existing reflection/settlement modules retain their responsibilities |
| C-13 HistoryReader | `src/tradingagents/history.py` (proposed) | Read-only manifest/report lookup |
| C-14 ManifestStore | `src/tradingagents/run_context.py` (proposed) | Small atomic JSON helper alongside lifecycle, no separate persistence platform |
| C-15 Limited security helpers | `src/tradingagents/security.py` (proposed) | Existing `src/tradingagents/dataflows/net.py`, `src/tradingagents/dataflows/symbols.py`, and CLI preferences delegate/reuse helpers as applicable; retain their existing interfaces |
| C-16 Existing checkpoint adapter | `src/tradingagents/graph/checkpointer.py` (existing) | Outside the selected new flow; preserve baseline tooling/tests |
| C-17 CLI display coordinator | `src/cli/display.py` (existing) | Streaming labels and prepared formal display; no rating generation |
| C-18 Configuration/threshold access | `src/tradingagents/default_config.py` (existing, adapted) | Small shared allowlist projection accessible before graph construction; instance `run_settings()` delegates rather than owns a second rule |
| C-20 DataResultClassifier | `src/tradingagents/dataflows/availability.py` (proposed) | Narrow producer-format recognition, no fetching or model judgment |

Do not create a missing C-19 or renumber D2 IDs. Exact new filenames are organizational proposals; approval must identify them in the round's file list. Reuse an existing suitable module when that makes the approved change smaller; do not create all proposed modules upfront.

## 4. Dependency and interface constraints

Keep dependencies directional: entry and graph orchestration call narrow infrastructure/business functions; pure risk and final-check functions do not import CLI orchestration, instantiate models, fetch data, or depend on manifest success. Avoid importing the graph object from lower-level helpers. Keep reusable code free of interactive CLI behavior and avoid circular imports. Do not introduce a plugin registry, service container, global event dispatcher, universal security framework, or new dependency without a separate scoped decision.

Use the blueprint IF-* contracts rather than inventing duplicate DTOs or a second state vocabulary. Simple JSON-compatible mappings suffice at graph/report boundaries. Do not put RunContext, locks, collectors, mutable registries, model objects, Decimal, or Fraction objects in serialized graph state. Internal exact arithmetic is separate from display-safe result projection.

### 4.1 Graph and formal authority

- Retain the existing analyst/research/trader/risk-debate flow. The selected tail is Portfolio Manager → Portfolio Risk Check → Final Recommendation Check → END.
- Portfolio Manager produces only the advisory `model_proposal`. C-08 produces risk output; C-09 alone generates `gate_status`, top-level `reasons`, `final_rating`, and `final_trade_decision`.
- Entries, reducers, and writers may copy, merge, pass, and save formal values unchanged. Assignment count alone does not establish a second authority. They must not re-parse proposal/report text, recompute, replace, or fabricate formal values.
- A missing/non-string/empty/whitespace-only proposal conclusion is ordinary blocked/REVIEW input. Preserve valid original text on pass. A missing/invalid formal result at delivery is an execution contract failure, not a consumer-generated REVIEW.
- Keep risk reasons inside the risk result and final-check reasons at the top level. Do not flatten one into the other or introduce duplicate gate status fields.

### 4.2 Run, statistics, and persistence

- Create one RunContext per analysis; explicit internal delegation shares it. Independent analyses do not share query reuse, availability, statistics, or identity. Reusable model/graph objects must not retain prior-run handlers.
- Inject the run's statistics handler through that execution's configuration and preserve existing callbacks. If propagation fails at a nested boundary, use a local handoff; do not add global collection or infer invisible provider calls.
- Resource release belongs to the acquiring scope/wrapper. `finish()` terminalizes after cleanup attempts and does not close resources twice.
- Validate formal results before normal delivery/save. Preserve final-state-save then conditional new-memory-append ordering. The programmatic path does not force report saving.
- Manifest persistence is best-effort. Preserve analysis results/errors and path-specific state/memory/report failures; no rollback or cross-file transaction. Writer and history reader use the blueprint's minimal version-1 contract and their distinct validation responsibilities.
- The selected new flow executes fully, does not acquire/resume/read old checkpoints as current evidence, and does not delete them. Preserve underlying checkpoint code/tests outside this flow.

### 4.3 Queries and availability

- Restrict run reuse to D2's P-09/P-13 news paths. Query identity excludes call path and follows effective business parameters. Preserve vendor selection, fallback/retry, original return/failure, and cross-run vendor caches.
- Attach observation at the 15 supported business call positions, not in router/vendor/callback layers. P-03 observes individual indicators before concatenation; the two news paths delegate to a shared execution boundary without double observation.
- Availability classification and tracking failures must not replace fetch results, strand reuse waiters, or trigger refetches. Follow D2's local failure-mark, pre-fetch-note, and tracking-error distinctions; do not add new statuses or a global public veto.
- Match necessary targets before selecting the last accepted result. Do not substitute another object/window/item or prefer success. Unresolved multi-window/frequency choices remain unresolved, not guessed.
- Obtain and deliver the research snapshot in the same first Bull call. Later research roles use the stored stage mapping. Terminal delivery is prepared by the entry; report writers and independent saves read passed state only. No refresh reruns a model or changes the already formed formal result.

### 4.4 Risk, history, and security

- Risk uses the caller's minimal scenario, current object, and configured classroom thresholds. Follow D2 applicability/validation order and exact comparisons; formatting never determines status. No model/network fill, broker/account validation, or trade authorization.
- Parsed business-invalid scenario/threshold inputs go to FR-04 for structured blocked results; missing applicable scenario is not an entry hard failure. Explicit file read/parse errors follow the entry contract still subject to OQ-01.
- Reports and new memory consume formal output without another model call to restate it. Preserve optional outputs and memory no-op cases; reflection does not rewrite recorded decision authority.
- History reads only registered merged reports under the authorized root; it does not regenerate, repair, re-register, scan unrelated report directories, or require risk/memory evidence closure.
- Reuse existing ticker protection and request-error scrubbing. Known-credential literal-substring omission follows IF-21; empty secrets do not match. Scope remains limited to D1's listed paths. No generic secret scanning or all-platform race guarantee is added.

## 5. ADR/invariant references in code

New or behaviorally changed modules and functions must reference the ADR decision and invariant they implement, using a short module comment/docstring and local function comment/docstring where applicable. Example: `Architecture: ADR 001 D-11/D-12; IR-14; FR-04-FC01–FC04`. Use real identifiers and keep the reference next to the relevant responsibility; a call-site adapter may cite the delegated contract rather than repeat its implementation.

Do not invent an invariant for an unrelated utility. State that no specific invariant applies when appropriate and cite the applicable architectural decision. Avoid mass-editing untouched baseline functions just to add annotations; maintain the mapping for new/changed work and record any baseline annotation gap honestly. References explain traceability and do not prove runtime enforcement.

## 6. Verification and change control

Each round declares exact module/file ownership, interfaces, and approved FC/IR assertions. Product behavior follows D1; architecture conformity follows approved D2. Structural checks can use review, narrow static inspection, or equivalent verification; this file does not mandate a custom AST engine, new framework, coverage percentage, or separate test file per component.

Run the D4 structural, prior-suite regression, and behavioral checks required for the change. Use independent expected results, controlled external substitutes, and negative scenarios. Do not modify implementation during a pure verification role or weaken tests to conceal failure. This draft itself claims no new test execution, permission enforcement, or acceptance; the Round 1 C-08 and Round 2 C-09 core results are recorded in their own approval and review records.

Changes to authority, interfaces, requirement semantics, or security-critical behavior require the affected architecture decision and human approval before implementation. Ordinary internal details within an approved contract need no new architecture gate. If a proposed module allocation conflicts with D2, resolve only the affected allocation before coding rather than silently changing D2 or expanding the round.

OQ-01/OQ-04 remain pending before affected entry implementation; OQ-07 belongs to D3 permission setup. OQ-08/12/13/15/16 remain technical verification items; OQ-02 fixes only the two threshold key names. Do not confirm OQs through this document. Context budgeting/compression/reinjection and the deferred requirements are not activated here; the known course-alignment question remains for human decision.
