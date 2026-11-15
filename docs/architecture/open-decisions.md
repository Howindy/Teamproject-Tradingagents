# D2 Open Decisions

Status: **v0.3 — ADD-R round 3 draft / pending human review**
Date: 2026-11-15
Amended by: `docs/architecture/adr/003-add-r-round-3.md`; `docs/architecture/adr/004-cr01-state-correction.md`
D1 basis: `docs/req/requirements.yaml` v1.25.0 — 18 requirements, 122 fit criteria
Status basis: 17 active requirements are approved as a requirement-design baseline; `QR-02` is deferred and outside current acceptance; approval does not assert implementation or measured results
Implementation status: **design only; no application code changed**

This file records decisions that are **not closed**. Recommendations are for discussion only; they are not approvals. A historical approval or a previously resolved decision is evidence, not approval of the current revision.

---

## 1. Status legend

- **open** — no decision.
- **recommended, not approved** — a recommendation exists; the team must decide.
- **blocking** — implementation or acceptance cannot start safely without it.
- **non-blocking** — can proceed with a recorded work assumption.
- **resolved in D1** — closed in the requirement text; retained for traceability, not re-opened here.
- **proposed by D2** — an architecture choice proposed by this round; pending human review.

## 1.1 Classification for Round 3

| Class | Meaning | Examples |
|---|---|---|
| Implementation-blocking | The affected module cannot start safely without a decision | OQ-09, ARCH-OD-03, ARCH-OD-15/20/23/24/27, ARCH-OD-19/21/22, ARCH-OD-25/26/28, D2-OD-10/11/12/13/14 |
| Acceptance-blocking | Implementation may start, but acceptance/completion claims are blocked | OQ-10 approved thresholds, OQ-12 risk-policy eval, OQ-14 reference freeze, OQ-16 brief/cost thresholds, OQ-05 PR-01 thresholds, D2-OD-09 snapshots, D2-OD-15/16 |
| Non-blocking | A recorded work assumption or later detail | OQ-02, OQ-04, OQ-08, OQ-11, OQ-15, ARCH-OD-05/07/09/10/11/12, D2-OD-05/07 |
| Deferred | Not current acceptance; requires a new ADR/amendment | multi-worker lease/fencing/takeover, export, TTM/FCF YoY, QR-02 |

Unrelated modules must not wait for future thresholds. A threshold that only blocks acceptance does not block starting the module.

---

## 2. D1 open questions carried forward

### OQ-02 — Manifest and memory retention

- **Status**: open; non-blocking.
- **Question**: how long are run manifests, publication snapshots, recovery envelopes, and memory entries retained?
- **Impact**: `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService`, storage growth, audit.
- **Recommendation (not approved)**: keep every run manifest and committed publication snapshot for D1; define retention later; clean only temporary recovery material after commit.
- **Blocking phase**: D3 implementation detail.
- **Related**: FR-02, FR-05, FR-06, INV-01.

### OQ-04 — Vendor-cache retention and TTL

- **Status**: open; non-blocking.
- **Question**: which existing vendor caches remain cross-run, and what TTL applies?
- **Impact**: `DataAccessService`, `FR-01` vendor-cache-hit accounting, evidence counters.
- **Resolution already in D1**: run cache is per-run; vendor cache is separate.
- **Recommendation (not approved)**: keep existing vendor caches under their current TTL; record hits; do not change TTL in this round.
- **Blocking phase**: D3 cache configuration.
- **Related**: FR-01.

### OQ-05 — Manifest overhead thresholds

- **Status**: open; non-blocking; provisional target.
- **Question**: accept startup and terminal pre-replace write p95 <=100 ms each, percent overhead p95 <=1%, and absolute overhead p95 <=1 s for <=256 KiB?
- **Impact**: `ArtifactPublisher`, `PR-01-FC01`–`FC04`, latency.
- **Recommendation (not approved)**: benchmark first with 20 write samples and 20 paired runs; retain negative samples; keep thresholds provisional until measured.
- **Blocking phase**: D3 benchmark.
- **Related**: PR-01, FR-02, QR-02.

### OQ-08 — Concurrent manifest/preference locking

- **Status**: open; non-blocking.
- **Question**: can concurrent runs share a manifest or preference directory without a locking policy?
- **Resolution proposed by D2**: per-run manifest/publication directories; memory uses the existing lock; preferences remain one global atomic-replace file with last-writer-wins; no shared mutable publication index is authoritative.
- **Impact**: `ArtifactPublisher`, `MemoryService`, `RecoveryClaimStore`, preferences.
- **Blocking phase**: D3 concurrency tests.
- **Related**: FR-01, FR-02, FR-06, INV-01.

### OQ-09 — Authoritative risk-input supplier and ownership

- **Status**: open; **blocking**.
- **Question**: who supplies `portfolio_value`, `cash_balance`, current quantity/value, valuation price/time, order fields, currency, and provenance; which broker/portfolio source is approved?
- **Impact**: `FR-04` input ownership, provenance, currency scope, valuation consistency, applicability; implementation cannot be completed safely without it.
- **Recommendation (not approved)**: caller/application supplies a validated structured envelope (CLI file/API argument) with an explicit source identifier; model text is never authoritative; no broker integration in this scope.
- **Blocking phase**: before D3 risk implementation.
- **Related**: FR-04, INV-02.

### OQ-10 — Risk policy and threshold approval

- **Status**: open; **blocking for approved-policy claims**.
- **Question**: are the 0.30 concentration, 0.05 stop-distance, freshness window, and precision rule approved; what `policy_ref`, `policy_version`, and `human_approval_ref` bind them?
- **Impact**: `PortfolioRiskEvaluator`, `RiskPolicyResolver`, gate REVIEW rate, formal risk evidence.
- **Recommendation (not approved)**: a valid provisional snapshot with `threshold_status=provisional` and `human_approval_ref=null` MAY be used and MUST be labeled provisional, as `FR-04` permits. An approved snapshot requires a non-null `human_approval_ref`. Do not claim thresholds are approved without it. Missing/invalid/incomplete policy blocks with `POLICY_SNAPSHOT_UNAVAILABLE`; a valid provisional policy is not treated as absent.
- **Blocking phase**: before claiming approved thresholds/policy, not before the explicit provisional path. D1 marks OQ-10 `blocking: true`; the architecture reads that as blocking approved-policy claims because `FR-04` explicitly permits provisional values.
- **Related**: FR-04, INV-02, SB-01.

### OQ-11 — Historical valuation cutoff and point-in-time portfolio source

- **Status**: open; non-blocking.
- **Question**: is the timezone-aware end-of-day cutoff and the point-in-time portfolio source approved for historical/backtest analyses?
- **Impact**: `FR-04` historical applicability, valuation freshness, `INV-02` evidence scope.
- **D1 text**: cutoff is defined as `min(now_utc, end_of_day(as_of_date, timezone))`; future date rejected.
- **Recommendation (not approved)**: use the defined cutoff; block stale/inconsistent input; no FX conversion; confirm the historical source before backtest use.
- **Blocking phase**: before historical/backtest risk runs.
- **Related**: FR-04, INV-02.

### OQ-12 — Risk-policy behavior-evaluation set and thresholds

- **Status**: open; **blocking** for behavioral acceptance.
- **Question**: should a new risk-policy evaluation set/contract version be created, and what separate REVIEW-rate and quality thresholds apply?
- **Impact**: `QR-01-FC04` (previously `FR-04-AC11`/`INV-02-AC7`, pre-v1.24.0), behavior evaluation.
- **Recommendation (not approved)**: keep the frozen v1 eval set unchanged; create a new version for risk-policy A/B; hold cache A/B risk policy fixed.
- **Blocking phase**: before risk behavioral acceptance.
- **Related**: FR-04, INV-02.

### OQ-13 — QR-02 target and platform matrix

- **Status**: deferred with QR-02; **not blocking current acceptance**.
- **Question**: is the 2.000 s nearest-rank p95 approved; which local filesystems/hardware are supported?
- **Impact**: `QR-02`, recovery benchmark, future acceptance evidence.
- **Recommendation (not approved)**: keep 2.000 s provisional; define a supported local-filesystem/hardware matrix if QR-02 is reactivated; correctness/model-free remain zero-tolerance even if the target is missed.
- **Blocking phase**: none for D1; before any future QR-02 acceptance.
- **Related**: QR-02.

### OQ-14 — Non-NVDA financial reference manifest

- **Status**: open; **blocking**.
- **Question**: which two non-NVDA companies, fiscal periods, and independently published sources should be frozen before the first `FR-07` application implementation?
- **Impact**: `GR-01-FC01`–`FC06`, FR-07 Stage A implementation gate, and tolerance validation.
- **Recommendation (not approved)**: freeze two companies with distinct fiscal calendars; record source URLs/versions/hashes; do not generate expected values from the code under test.
- **Blocking phase**: Stage A before the first FR-07 application implementation; Stage B after implementation starts. This architecture round is not FR-07 implementation.
- **Related**: FR-07.

### OQ-15 — TTM EPS scope

- **Status**: deferred with TTM metrics; non-blocking.
- **Question**: is approximate TTM EPS (annual + current YTD - prior YTD) acceptable, or should the first version report only fiscal-year P/E?
- **Impact**: future `FR-07` TTM EPS/P-E scope; current version retains fiscal-year P/E only.
- **Recommendation (not approved)**: if TTM is reactivated, label approximate TTM EPS and return n/a on incomplete inputs; keep fiscal-year P/E as a separate row. D1 does not implement TTM.
- **Blocking phase**: none for D1; before any future TTM extension.
- **Related**: FR-07.

### OQ-16 — Brief budgets, token/quality thresholds, and contract version

- **Status**: open; **blocking** for acceptance.
- **Question**: what mandatory/compressible budgets, hard cap, token/quality thresholds, and evaluation contract version govern `FR-08`?
- **Impact**: `DownstreamBriefBuilder`, `TokenCounter`, `FR-08` acceptance, cost claims.
- **Recommendation (not approved)**: keep budgets/thresholds provisional; use the frozen brief evaluation contract; no saving claimed until `accepted` with approved `quality_loss_max` and zero safety escapes.
- **Blocking phase**: before FR-08 acceptance.
- **Related**: FR-08.

---

## 3. D2 decisions carried or updated

### D2-OD-01 — FinalizedRunRecord schema/version

- **Status**: proposed; blocking before implementation.
- **Recommendation (not approved)**: reuse the D1 contract: `run_id` plus `decision_id`, `record_version`, critical profile/coverage snapshot, gate result/`input_hash`, formal decision, artifact binding, memory entry binding, and new optional risk/metric/section references. Use canonical JSON/SHA-256. D2 must confirm only versioning/migration mechanics.
- **Impact**: publisher, memory, manifest, trace, all tests.
- **Blocking phase**: before D3.

### D2-OD-02 — Publish order, staging, and commit protocol

- **Status**: proposed in blueprint §12.5; pending review.
- **Recommendation (not approved)**: running manifest -> analysts/metrics/block -> brief/provisional view -> research/risk debate -> final coverage -> gate/record -> sections -> memory plan/reservation -> recovery envelope (complete/read-back verified) -> memory idempotent write -> permanent snapshot write/validate -> terminal candidate + INV-01 -> ownership-protected atomic commit -> post-commit read -> cleanup last. Terminal manifest completed plus read-time INV-01 is the only commit condition; no independent marker. A post-commit read failure keeps the committed manifest immutable and records an independent diagnostic; it does not replace the manifest with `failed`.
- **Impact**: `ArtifactPublisher`, `RecoveryService`, `MemoryService`, `RunOwnershipLock`, tests.
- **Blocking phase**: before D3.

### D2-OD-03 — Checkpoint support matrix and degraded resume

- **Status**: proposed as a work assumption; blocking before checkpoint implementation.
- **Recommendation (not approved)**: support graph/journal state with fixed clock, profile contract version, decision_id, and schema versions; resume creates a new `run_id`; refuse unsupported versions; degraded resume is opt-in, `coverage_status=partial` only, so the gate blocks with REVIEW.
- **Distinction**: checkpoint resume is not startup publication recovery.
- **Impact**: `CheckpointCoordinator`, evidence store, tests.
- **Blocking phase**: before D3 checkpoint.

### D2-OD-04 — Fallback coverage contract

- **Status**: resolved in D1 (retained).
- **Resolution**: a fallback clears a gap only under the same capability/component/instrument/window/as-of/point-in-time/minimum-record/provenance contract. Global news does not clear ticker news; undated Yahoo statements do not clear SEC statements.
- **Impact**: `DataAccessService`, `AvailabilityIndex`, gate.

### D2-OD-05 — Token limits and compression thresholds

- **Status**: proposed as a work assumption; provisional.
- **Recommendation (not approved)**: 128k window, 24k cap, 9k reserves, 80% soft, 95% hard, 4k evidence, 8k history, 2k summary; deterministic truncation first; optional LLM summarization only if enabled. Before compression is enabled, over-budget fails closed.
- **Impact**: `ContextAssembler`, prompts, token cost, tests.
- **Blocking phase**: before D3 context/brief implementation.
- **Related**: ARCH-OD-04.

### D2-OD-06 — Memory sidecar, lease TTL, and retry defaults

- **Status**: proposed as a work assumption; blocking for memory/recovery implementation.
- **Recommendation (not approved)**: either a JSONL sidecar or a structured Markdown metadata line; carry decision/entry/evidence digests, version, supersedes, reuse reference, risk summary, retention status. The reservation ledger is separate (see ARCH-OD-20). Recovery lease TTL and retry budget are configuration values with documented defaults (for example 30 s lease, 3 retries) pending review.
- **Impact**: `MemoryService`, `MemoryReservationStore`, `RecoveryClaimStore`, idempotency tests.
- **Blocking phase**: before D3 memory/recovery.

### D2-OD-07 — Coding-agent role whitelist

- **Status**: proposed; this round uses `architect_add_r`.
- **Recommendation (not approved)**: ADD-R writes only `architecture-blueprint.md` and `docs/architecture/**`; future implementation/test roles require explicit approval.
- **Impact**: agent permissions, audit, workflow.
- **Blocking phase**: before D3 implementation agents.

### D2-OD-08 — Runtime AI tool boundary and context exposure

- **Status**: proposed; blocking before implementation.
- **Recommendation (not approved)**: registered data tools only; no file/env/shell/arbitrary network; context layers per `POL-CTX-01`; runtime may receive supports links, coverage summaries, and the five-role brief but cannot mutate them or supply authoritative risk input.
- **Impact**: tool registry, prompts, permission tests.
- **Blocking phase**: before D3.

### D2-OD-09 — Behavior-evaluation snapshots and approval

- **Status**: open; blocking for behavioral acceptance only.
- **Question**: who captures the pending evaluation snapshots and approves the rubric/contracts?
- **Recommendation (not approved)**: use the frozen v1 files; capture every case snapshot; two independent raters plus adjudication; record human approval before any live A/B acceptance. Add a separate risk-policy version (OQ-12) and brief contract (OQ-16).
- **Impact**: FR-01/FR-04/FR-08 behavior acceptance.
- **Blocking phase**: before behavioral acceptance.

---

## 4. New ADD-R architecture decisions

### ARCH-OD-01 — Unretained personal-proposal source

- **Status**: resolved for D1 v1.18.0; the missing path is no longer referenced.
- **Observation**: `docs/req/requirements.yaml` previously cited `yhx/requirements.yaml`. FR-07/FR-08 now state that the personal-proposal source is not retained, and the validator no longer includes that path in its bound input hashes.
- **Impact**: `--check` passes against the current inputs. Provenance for FR-07/FR-08 is the baseline and source code.
- **Recommendation (not approved)**: if a retained copy is required later, add it with an explicit read-only source record and rebind the validation result.
- **Blocking phase**: none for the current registry.
- **Related**: FR-07, FR-08, validator.

### ARCH-OD-02 — Validator dependencies

- **Status**: resolved in this environment; declaration for CI remains a D4 task.
- **Observation**: `validate_requirements.py` imports `yaml` and `jsonschema`; both are importable here, and `--check` passes.
- **Impact**: the validator runs locally, but a root dependency manifest or documented tool environment is still needed for clean CI reproduction.
- **Recommendation (not approved)**: declare the tooling dependency and add a CI install step; this is a CI/requirements-owner change.
- **Blocking phase**: D4/CI.
- **Related**: all requirements validation.

### ARCH-OD-03 — Risk policy locator, storage, and approval record

- **Status**: open; **blocking before risk implementation**.
- **Question**: where does the risk policy snapshot live (file path/format), how is `policy_digest` computed, and what human-approval record binds `human_approval_ref`?
- **Impact**: `RiskPolicyResolver`, `PortfolioRiskEvaluator`, `SafetyGate`, `FR-04-FC09`.
- **Recommendation (not approved)**: a versioned local policy file (for example `config/risk_policy_v1.json`) with canonical JSON digest; `threshold_status=provisional` and `human_approval_ref=null` until a recorded human decision; approved policy requires a non-null reference.
- **Blocking phase**: before D3 risk.
- **Related**: OQ-10.

### ARCH-OD-04 — Selected model/tokenizer for context and brief budgets

- **Status**: open; **blocking before brief/context implementation**.
- **Question**: which model/tokenizer measures the final request and brief budgets? What happens when the tokenizer is unavailable?
- **Impact**: `TokenCounter`, `ContextAssembler`, `DownstreamBriefBuilder`, `FR-08`.
- **Recommendation (not approved)**: use the selected model's tokenizer; if unavailable, reject the brief/context (`BRIEF_REJECTED`/`ContextBudgetError`) rather than falling back to characters.
- **Blocking phase**: before D3 brief/context.
- **Related**: OQ-16, D2-OD-05.

### ARCH-OD-05 — History index strategy

- **Status**: open; non-blocking.
- **Question**: scan committed publication roots on demand, or maintain a derived index?
- **Impact**: `HistoryService`, bounded listing, performance.
- **Recommendation (not approved)**: scan committed publication roots and optionally maintain a **non-authoritative** derived index that can be rebuilt; never let the index decide commitment or override read-time validation.
- **Blocking phase**: D3 history implementation detail.
- **Related**: FR-05.

### ARCH-OD-06 — Recovery lease, retry, and quarantine layout

- **Status**: current scope: retry/quarantine layout for single-process recovery; lease/fencing/takeover deferred.
- **Question**: what is the bounded retry budget and quarantine path for current single-process recovery?
- **Impact**: `RecoveryService`, `RecoverySnapshotStore`, `QR-02`; current `FR-06` uses a single-process startup guard and bounded retry.
- **Recommendation (not approved)**: keep a bounded retry budget and quarantine path; do not implement claim/fencing/takeover. If multi-worker is reactivated, open a new decision.
- **Blocking phase**: before current recovery implementation (retry/quarantine only); lease/fencing is deferred.
- **Related**: FR-06, QR-02, D2-OD-06.

### ARCH-OD-07 — Publication/recovery envelope retention and cleanup

- **Status**: open; non-blocking.
- **Question**: how long are permanent publication snapshots and temporary recovery envelopes retained? What exactly is cleaned after commit?
- **Impact**: `PublicationSnapshotStore`, `RecoveryService`, storage, audit.
- **Recommendation (not approved)**: keep permanent publication snapshots for D1; after commit clean only claim/staging/temporary recovery material; a cleanup failure is a warning and never changes history.
- **Blocking phase**: D3 retention detail.
- **Related**: FR-02, FR-05, FR-06, OQ-02.

### ARCH-OD-08 — Risk input envelope shape for CLI/API

- **Status**: open; blocking for risk integration.
- **Question**: how does the caller supply the structured risk envelope without confusing it with the existing optional `PortfolioContext` prompt text?
- **Impact**: `EntrypointAdapter`, `RiskInputValidator`, CLI/API, `PortfolioContext`.
- **Recommendation (not approved)**: add a separate validated risk-input object/file (or explicit fields) with provenance; keep `PortfolioContext` as prompt context only; never infer authoritative numbers from rendered text.
- **Blocking phase**: before D3 risk.
- **Related**: OQ-09.

### ARCH-OD-09 — Brief reference resolver and consumer

- **Status**: open; non-blocking.
- **Question**: what handle format can the receiving downstream consumer resolve, and what is the fallback when it cannot?
- **Impact**: `DownstreamBriefBuilder`, `ContextAssembler`, `FR-08`.
- **Recommendation (not approved)**: a run-scoped handle resolvable by the same process/consumer; if the consumer cannot resolve it, treat the reference as invalid and follow the ordered policy to full-report or rejection.
- **Blocking phase**: D3 brief implementation.
- **Related**: FR-08, OQ-16.

### ARCH-OD-10 — Metric evidence bundle optionality by phase

- **Status**: proposed; non-blocking.
- **Decision**: when `FR-07` is not enabled, the metric block/bundle is not required; when enabled, the bundle is persisted in publication and recovery envelopes. A missing/corrupt bundle at recovery blocks a metric-dependent publication rather than triggering a live fetch.
- **Impact**: `ArtifactPublisher`, `RecoveryService`, `FR-07`, `FR-02`.
- **Blocking phase**: before enabling FR-07.

### ARCH-OD-11 — Completed-with-blocked-formal-decision semantics

- **Status**: proposed; pending review.
- **Decision**: a handled coverage/risk block is a completed run with a blocked formal decision (`final_rating=REVIEW`), not a failed run. A gate exception is a failed run (`run_status=failed`, `error.stage=gate`). This prevents a business block from being mislabeled as a crash and a crash from being published as a completed block.
- **Impact**: `SafetyGate`, `ArtifactPublisher`, `PublicationStatusReader`, reports, tests.
- **Blocking phase**: before D3 gate/publication.

### ARCH-OD-12 — Historical memory reference closure scope

- **Status**: deferred with FR-05 export; not current acceptance.
- **Decision**: if export is reactivated, `verified_package` includes a `history_reference_closure` for every followed `reused_decision_ref`; when a source proof is unavailable, label `historical_reference_unverified` and limit verification to the current run. Never depend on original-machine-only files.
- **Impact**: future `ExportService`, `MemoryService`; current FR-05 has no export mode.
- **Blocking phase**: none for D1; before any future export capability.

### ARCH-OD-13 — Former approval of SB-01 risk branch no longer applies

- **Status**: resolved for status purposes; the 17 active requirements are approved as a requirement-design baseline and QR-02 is deferred.
- **Observation**: `SB-01` was approved at v1.14.1 and is now draft. Its current text includes stock Buy/Overweight risk evaluation, `portfolio_risk_input_invalid`, `portfolio_risk_limit_exceeded`, `portfolio_risk_evaluator_error`, and `review_class=portfolio_risk_limit`. `FR-04` and `INV-02` are also draft.
- **Impact**: `SafetyGate`, `PortfolioRiskEvaluator`, `SB-01-FC11/FC12`, `FR-04`, `INV-02`.
- **Recommendation (not approved)**: review the risk branch together with the rest of the draft registry. A valid provisional policy MAY be used and labeled provisional; missing/invalid policy blocks. Do not turn OQ-10 into a rule that unapproved always means absent.
- **Blocking phase**: before enabling stock Buy/Overweight formal approval.
- **Related**: SB-01, FR-04, INV-02, OQ-09, OQ-10.

### ARCH-OD-14 — Former approval coupling no longer applies

- **Status**: resolved for status purposes; the 17 active requirements are approved as a requirement-design baseline and QR-02 is deferred.
- **Observation**: `FR-02` constraint relations reference `FR-05`/`FR-06`/`FR-07`/`FR-08`/`QR-02`, but its fit criteria now cover only the manifest lifecycle; publication, section, and recovery details live in `INV-01`/`FR-05`/`FR-06`. `INV-01` references `FR-04`..`FR-08` and `QR-02`. All of these requirements, including `FR-02`, `INV-01`, and `SB-01`, are now approved as requirement design; implementation and verification remain separate.
- **Impact**: FR-02, INV-01, SB-01, full-scope acceptance, trace matrix claims.
- **Recommendation (not approved)**: review the coupled obligations together. Draft status limits **claims** of approval/completion; it does not delete the obligations. Humans must decide how to bind the draft details; the architecture must not declare any requirement approved.
- **Blocking phase**: before claiming full-scope acceptance.
- **Related**: FR-02, INV-01, SB-01, FR-04..FR-08, QR-02.

### ARCH-OD-15 — Permanent snapshot staging, hashing, and post-commit diagnostics

- **Status**: open; **blocking before publication implementation**.
- **Question**: where are permanent-snapshot files staged before the terminal commit, how are their hashes bound into the terminal manifest, and where is the independent post-commit corruption diagnostic stored?
- **Impact**: `ArtifactPublisher`, `PublicationSnapshotStore`, `PublicationStatusReader`, history; export deferred.
- **Recommendation (not approved)**: write all permanent-snapshot files under a per-run staging/publication directory, fsync/validate them, bind their hashes into the terminal candidate, and atomically commit the terminal manifest last. The snapshot is authoritative only after commit. The hash DAG in blueprint §9.6.5 is acyclic: `binding.json` has no terminal-manifest hash; the manifest hashes permanent files; no hashed file contains the manifest hash. A post-commit validation failure keeps the committed manifest immutable and writes a separate diagnostic record outside the formal decision/commit path.
- **Blocking phase**: before publication implementation.
- **Related**: FR-02, INV-01, FR-05.

### ARCH-OD-16 — Shared run lock, lease, takeover, and lock order

- **Status**: deferred multi-worker extension; not current `FR-06`.
- **Question**: what future local-FS lock file format, lease TTL, takeover condition, fencing-token increment, and release rule would a multi-worker design use?
- **Impact**: future `RunOwnershipLock`, `ArtifactPublisher`, `RecoveryService`, `MemoryService`.
- **Recommendation (not approved)**: current code uses `StartupRecoveryGuard` only. If multi-worker is reactivated, a new ADR/amendment must define `run.lock`, `lease.json`, owner/fencing, bounded wait/`LOCK_BUSY`, takeover, lost-owner rejection, lock order, and release. Current code/tests must not claim these.
- **Blocking phase**: none for current D1; before any future multi-worker recovery.
- **Related**: FR-02, FR-06, INV-01.

### ARCH-OD-17 — Brief replacement mapping and protected-marker format

- **Status**: open; **blocking before FR-08 implementation**.
- **Question**: exactly which full reports are replaced for the five target roles, and what structured protection markers prevent compression from truncating mandatory content?
- **Impact**: `DownstreamBriefBuilder`, `ContextAssembler`, prompts, `FR-08`.
- **Recommendation (not approved)**: the brief replaces `market_report`, `sentiment_report`, `news_report`, and `fundamentals_report` for Bull, Bear, and the three risk debaters; other roles keep full inputs. Mandatory blocks use structured `protected: true` plus begin/end markers; generic compression/reference/full-report fallback must preserve them verbatim.
- **Blocking phase**: before brief implementation.
- **Related**: FR-08.

### ARCH-OD-18 — Brief timing versus the final coverage snapshot

- **Status**: open; **blocking before FR-08 acceptance**.
- **Question**: `FR-08` says the brief uses the `FR-03` availability state, but the five roles run before the final coverage snapshot exists. Which program view/version is authoritative for the brief, and how is it reconciled with the final gate snapshot?
- **Impact**: `DownstreamBriefBuilder`, `AvailabilityIndex`, `SafetyGate`, `FR-08`.
- **Recommendation (not approved)**: the brief uses the program provisional `CoverageView` and records `coverage_view_version`; the final gate uses the final `coverage_snapshot`. Regenerate the brief with a new version if the view changes before a later five-role consumer. This is an interpretation for human review, not a requirement change.
- **Blocking phase**: before FR-08 acceptance.
- **Related**: FR-03, FR-08, SB-01.

### ARCH-OD-19 — Financial-fact graph placement and SEC query shape

- **Status**: open; **blocking before FR-07 implementation**.
- **Question**: where exactly in the graph are facts/metrics computed/block-appended, and what `DataAccessService` query shape does `SecEdgarAdapter` expose for structured facts?
- **Impact**: `FinancialFactService`, `SecEdgarAdapter`, `FundamentalsAdapter`, `FR-07`.
- **Recommendation (not approved)**: after the fundamentals report exists and before Bull/Bear; a `get_structured_financial_facts`-style query through `DataAccessService` returns per-fact records with separate disclosure fields (subject/accession/filing_ref/filed_at/form/source_fact_ref and raw concept/value/unit/currency/period/fiscal/sign) and canonical fields (fact_id/concept/per-fact period/fiscal identity/span/cumulative duration/sign/unit/currency/lineage). `FinancialFactService` validates/normalizes canonical fields only via recorded versioned rules with input evidence and source refs; a filing's fiscal year/quarter is not copied as each historical fact's period identity. Missing or multiple plausible sources return unavailable/ambiguous; never guess from date proximity, equal value, column order, or a default. The existing statement tools use the same adapter/cache/counters.
- **Blocking phase**: before FR-07 implementation.
- **Related**: FR-07, FR-01, FR-03.

### ARCH-OD-20 — Memory reservation storage and format

- **Status**: open; **blocking before memory/recovery implementation**.
- **Question**: where is the persistent reservation history stored, and how does it atomically track the allocation high-water mark (including failed reservations) and derived commit projections?
- **Impact**: `MemoryReservationStore`, `MemoryService`, `RecoveryService`, `INV-01`, `INV-02`.
- **Recommendation (not approved)**: a lock-protected `memory/reservations.jsonl` ledger keyed by ticker/date/decision_id, recording entry_version, owner run_id, and status reserved/committed/failed. A fencing token is a deferred multi-worker extension, not a current field. It is authoritative for version allocation, not for decision content. The next version is `high_water + 1` over every historical allocation, including failed reservations; a failed version is never reissued; retries/recovery reuse their own reservation; recovery uses the original run_id/version/envelope; `committed` is a derived projection from the terminal manifest, not a second commit condition. Repair replays the append-only allocation history and never resets the watermark or reissues failed versions. If a structured sidecar is rejected, the same fields must live in a structured Markdown metadata line under the same lock.
- **Blocking phase**: before memory/recovery implementation.
- **Related**: INV-01, FR-06, D2-OD-06.

### ARCH-OD-21 — Portfolio Manager adapter and model-proposal source

- **Status**: open; **blocking before analysis-chain implementation**.
- **Question**: how is the original Portfolio Manager invoked and how is the `ModelProposal` source represented without promoting Trader/risk-debater output?
- **Impact**: `PortfolioManagerAdapter`, `SafetyGate`, report/memory audit fields, `SB-01`.
- **Recommendation (not approved)**: wrap the original terminal PM node; consume full reports/plans/risk debate/past memory; produce `ModelProposal {rating, text, source=portfolio_manager, source_refs, model_provider/id, proposal_status=unapproved}`. Trader/risk-debater outputs are source references only. The PM does not write formal artifacts.
- **Blocking phase**: before analysis-chain implementation.
- **Related**: SB-01, INV-01, FR-03.

### ARCH-OD-22 — Uncommitted same-decision memory coordination

- **Status**: open; **blocking before memory coordination implementation**.
- **Question**: what wait timeout, retryable statuses, recovery trigger, and conflict behavior apply when run B finds run A's same-decision entry uncommitted?
- **Impact**: `MemoryRecoveryCoordinator`, `MemoryService`, `RecoveryService`, `INV-01`/`INV-02`.
- **Recommendation (not approved)**: A active -> B waits bounded without run/memory locks, then `MEMORY_PENDING_RETRYABLE`; A invalid with valid snapshot -> recover under A's original run_id/reservation/snapshot; missing snapshot -> `MEMORY_RECOVERY_UNAVAILABLE`; recovery failure -> `MEMORY_RECOVERY_FAILED`; binding conflict -> `MEMORY_CONFLICT`. Never transfer ownership; B reuses only after A commits/validates.
- **Blocking phase**: before memory coordination implementation.
- **Related**: INV-01, FR-06, INV-02.

### ARCH-OD-23 — Permanent/recovery envelope layout and cleanup dependency

- **Status**: open; **blocking before publication implementation**.
- **Question**: what exact directories/references distinguish permanent publication from temporary recovery, and what may readers depend on after cleanup?
- **Impact**: `PublicationSnapshotStore`, `RecoverySnapshotStore`, `HistoryService`, `ExportService`, `ArtifactPublisher`.
- **Recommendation (not approved)**: use the `publication/`, `recovery/`, `guards/`, `diagnostics/` layout in blueprint §9.6.1. Formal report/history/memory binding validation depend only on `publication/` + terminal manifest; future export, if reactivated, must use the same material; `recovery/` is temporary and may be cleaned; a terminal `recovery_envelope_summary` is audit-only. The hash DAG is acyclic: `binding.json` contains no terminal-manifest hash; the manifest hashes permanent files including binding; no hashed file contains the manifest hash; optional `commit_evidence.json` is audit-only. `record_hash` uses the §9.6.9 projection excluding `artifact_binding.record_hash` and result-carrying hashes; content digest and file-byte hash are distinct.
- **Blocking phase**: before publication implementation.
- **Related**: FR-02, FR-05, FR-06, INV-01.

### ARCH-OD-24 — record_hash projection and timestamp exclusion

- **Status**: open; **blocking before publication implementation**.
- **Question**: accept the §9.6.9 field-level projection, including exclusion of `artifact_binding.record_hash` and all result-carrying hashes, the content-digest vs file-byte-hash split, and the exact volatile-timestamp list?
- **Impact**: `SafetyGate`, `ArtifactPublisher`, `Canonicalizer`, `INV-01`, `INV-A-41`.
- **Recommendation (not approved)**: canonical content -> exclude self/result hashes and specified volatile run timestamps (`generated_at`, run-level `evaluated_at`, `finished_at`, `run_clock.now_utc`, paths, cache counters, computed snapshot timestamps) -> compute `record_hash` -> fill binding -> serialize -> file-byte SHA-256 -> terminal manifest. Preserve risk `evaluated_at` and provenance/evidence/filed-at timestamps.
- **Blocking phase**: before publication implementation.
- **Related**: INV-01, FR-02, FR-04.

### ARCH-OD-25 — Logical component/module realization

- **Status**: proposed design; blocking before implementation of grouped modules.
- **Decision**: components are logical responsibilities; the module table is a proposed mapping; several small components may share a module only if every exported symbol maps to one owner and the write boundary is auditable.
- **Impact**: all components; component audit; tests.
- **Blocking phase**: before R1/R4/R6/R7 implementation.
- **Related**: D3-01, D3-20.

### ARCH-OD-26 — Envelope contract review

- **Status**: proposed design; blocking before R4/R6/R7 implementation.
- **Decision**: each envelope has one owner, version, mutability, error contract, and serialization boundary (blueprint §9.6.8). Required-field changes are version changes.
- **Impact**: publisher, memory, history, context, gate, risk, metrics.
- **Blocking phase**: before envelope-producing modules start.
- **Related**: D3-08.

### ARCH-OD-27 — Digest projection review

- **Status**: proposed design; blocking before publication implementation.
- **Decision**: accept the §9.6.9 projections/order for `proposal_digest`, `decision_digest`, `input_digest`, `policy_digest`, `entry_digest`, `evidence_digest`, and `record_hash`; redaction precedes digesting; no blanket timestamp removal.
- **Impact**: `Canonicalizer`, `SafetyGate`, `ArtifactPublisher`, `MemoryService`, `INV-01`.
- **Blocking phase**: before R4 publication implementation.
- **Related**: D3-11, ARCH-OD-24.

### ARCH-OD-28 — Single-process startup guard mechanism

- **Status**: proposed design; blocking before recovery implementation.
- **Decision**: one simple exclusive startup guard + duplicate-start guard + bounded retry; unsupported concurrent recovery rejected; no lease/fencing/takeover current.
- **Impact**: `StartupRecoveryGuard`, `RecoveryService`, `ArtifactPublisher`, tests.
- **Blocking phase**: before R6 recovery implementation.
- **Related**: D3-13, ARCH-OD-06/16.

### ARCH-OD-29 — R0–R8 round map and per-AC ownership

- **Status**: proposed design; blocking before implementation starts.
- **Decision**: use R0–R8 in blueprint §18 and the per-AC round table in `trace-matrix.md` §3.19; every requirement/AC has first-build, main-owner, and final-acceptance rounds.
- **Impact**: delivery planning, trace, review evidence.
- **Blocking phase**: before R0 exit; non-blocking for architecture design.
- **Related**: D3-19.

### D2-OD-10 — Coordinator/context scope

- **Status**: proposed design; pending review.
- **Decision**: `RunCoordinator` coordinates stages only; `RunContext` owns identity/clock/versions/paths/dependencies only. Neither contains business policy.
- **Impact**: all services; tests; component audit.
- **Blocking phase**: before R1 implementation.
- **Related**: D3-02.

### D2-OD-11 — Envelope and mutability policy

- **Status**: proposed design; pending review.
- **Decision**: consumers receive immutable/versioned envelopes, not mutable working objects; a required-field change is a version change.
- **Impact**: all envelope producers/consumers.
- **Blocking phase**: before envelope implementation.
- **Related**: D3-08, ARCH-OD-26.

### D2-OD-12 — Digest projection and timestamp policy

- **Status**: proposed design; pending review.
- **Decision**: use §9.6.9 projections; preserve filing/evidence/risk timestamps; exclude only specified run-level volatile fields; record terminal replace completion time externally/audit-only.
- **Impact**: canonicalization, publication, memory.
- **Blocking phase**: before R4.
- **Related**: D3-11, ARCH-OD-27.

### D2-OD-13 — Single-process recovery scope

- **Status**: proposed design; pending review.
- **Decision**: current recovery is single-process; lease/fencing/takeover/multi-worker is deferred.
- **Impact**: recovery, publication, tests.
- **Blocking phase**: before R6; no current lease work.
- **Related**: D3-13, ARCH-OD-28.

### D2-OD-14 — Round-based delivery

- **Status**: proposed design; pending review.
- **Decision**: replace phase-only plan with R0–R8 and per-AC round ownership.
- **Impact**: all rounds, trace, review evidence.
- **Blocking phase**: before implementation starts.
- **Related**: D3-19, ARCH-OD-29.

### D2-OD-15 — FR-08 functional/CR-01 cost separation

- **Status**: proposed design; pending review.
- **Decision**: FR-08 functional acceptance is independent of CR-01 optimization acceptance; OQ-16 blocks cost/threshold claims and CR-01, not FR-08 functional behavior.
- **Impact**: brief, token/cost evaluation, acceptance claims.
- **Blocking phase**: before R7/R8 acceptance claims.
- **Related**: D3-16, D3-18.

### D2-OD-16 — QR-01 replay/live readiness

- **Status**: open; acceptance-blocking.
- **Question**: when are replay snapshots captured, the rubric/contract approved, and live sampling allowed?
- **Impact**: `QR-01`, `DataAccessService`, `SafetyGate`, risk services, evaluation harness.
- **Recommendation (not approved)**: fix deterministic replay first; run live sampling only after replay passes; keep cache A/B risk policy/input fixed; run risk-policy A/B separately; no live acceptance before snapshots and human approval.
- **Blocking phase**: before QR-01 acceptance, not before R2/R8 implementation.
- **Related**: QR-01, OQ-12, D2-OD-09.

### D2-OD-17 — SR-02 platform/path matrix

- **Status**: open; non-blocking for design, acceptance-relevant.
- **Question**: which platforms/filesystems must SR-02 cover, and how are symlink/junction and operation-time path changes tested?
- **Impact**: `PathGuard`, `HistoryService`, `RecoveryService`, `SR-02`.
- **Recommendation (not approved)**: define the supported platform matrix; test read and write confinement, traversal/absolute paths, symlink/junction escapes, and path changes during an operation; untested platforms are not marked passing.
- **Blocking phase**: before SR-02 acceptance; does not block R1 path foundations.
- **Related**: SR-02, ARCH-OD-05.

---

## 5. Blocking summary

| Decision | Blocking phase | Related requirements |
|---|---|---|
| OQ-09 risk input source/ownership | Before risk implementation | FR-04, INV-02 |
| OQ-10 risk policy/threshold approval | Before claiming approved thresholds/policy (provisional path permitted) | FR-04, INV-02, SB-01 |
| OQ-12 risk-policy evaluation set | Before risk behavioral acceptance | FR-04, INV-02 |
| OQ-13 QR-02 target/platform | Deferred with QR-02; no D1 action | QR-02 |
| OQ-14 non-NVDA reference manifest | Stage A before first FR-07 implementation; Stage B after start | FR-07, GR-01 |
| OQ-16 brief budgets/token/quality | Before CR-01/cost-threshold acceptance; does not block FR-08 functional acceptance | FR-08, CR-01 |
| ARCH-OD-01 unretained personal-proposal source | Resolved for current registry | FR-07, FR-08, validator |
| ARCH-OD-02 validator deps locally present; CI declaration pending | D4/CI reproducibility | all requirements |
| ARCH-OD-03 risk policy locator/approval record | Before risk implementation | FR-04, INV-02 |
| ARCH-OD-04 tokenizer/model selection | Before brief/context implementation | FR-08 |
| ARCH-OD-06 recovery retry/quarantine layout | Before current single-process recovery (lease/fencing deferred) | FR-06, QR-02 |
| ARCH-OD-08 risk input envelope | Before risk integration | FR-04 |
| ARCH-OD-13 former approval of SB-01 risk branch | Status resolved; review with draft registry | SB-01, FR-04, INV-02 |
| ARCH-OD-14 former approval coupling | Status resolved; review with draft registry | FR-02, INV-01, FR-04..FR-08, QR-02 |
| ARCH-OD-15 permanent-snapshot staging/post-commit diagnostics | Before publication implementation | FR-02, INV-01, FR-05 |
| ARCH-OD-16 shared run lock/lease/takeover/lock order | Deferred multi-worker; not current | FR-02, FR-06, INV-01 |
| ARCH-OD-17 brief replacement mapping/protected markers | Before FR-08 implementation | FR-08 |
| ARCH-OD-18 brief timing vs final coverage snapshot | Before FR-08 acceptance | FR-03, FR-08, SB-01 |
| ARCH-OD-19 financial-fact graph placement/SEC query shape | Before FR-07 implementation | FR-07, FR-01, FR-03 |
| ARCH-OD-20 memory reservation storage/format | Before memory/recovery implementation | INV-01, FR-06 |
| ARCH-OD-21 Portfolio Manager adapter/model-proposal source | Before analysis-chain implementation | SB-01, INV-01, FR-03 |
| ARCH-OD-22 uncommitted same-decision memory coordination | Before memory coordination implementation | INV-01, FR-06, INV-02 |
| ARCH-OD-23 permanent/recovery layout/cleanup dependency | Before publication implementation | FR-02, FR-05, FR-06, INV-01 |
| ARCH-OD-24 record_hash projection/timestamp exclusion | Before publication implementation | INV-01, FR-02, FR-04 |
| ARCH-OD-25 logical component/module realization | Before grouped-module implementation | all requirements |
| ARCH-OD-26 envelope contract | Before R4/R6/R7 implementation | INV-01, INV-02, FR-02 |
| ARCH-OD-27 digest projection review | Before R4 publication | INV-01, FR-02, FR-04 |
| ARCH-OD-28 single-process startup guard | Before R6 recovery | FR-06 |
| ARCH-OD-29 R0–R8/per-AC ownership | Before implementation starts | all requirements |
| D2-OD-01 record schema/version | Before D3 | SB-01, INV-01, FR-02 |
| D2-OD-02 publish protocol | Before D3 | FR-02, INV-01, FR-06 |
| D2-OD-03 checkpoint matrix | Before D3 checkpoint | D2, SB-01, INV-01 |
| D2-OD-06 memory sidecar shape | Before D3 memory implementation | INV-01, FR-06 |
| D2-OD-08 runtime tool boundary | Before D3 | SR-01, FR-04, FR-07 |
| D2-OD-09 behavior snapshots/approval | Before behavioral acceptance | FR-01, FR-04, FR-08 |
| D2-OD-10 coordinator/context scope | Before R1 implementation | all requirements |
| D2-OD-11 envelope/mutability policy | Before envelope implementation | INV-01, INV-02, FR-02 |
| D2-OD-12 digest/timestamp policy | Before R4 | INV-01, FR-02, FR-04 |
| D2-OD-13 single-process recovery scope | Before R6 | FR-06 |
| D2-OD-14 round-based delivery | Before implementation starts | all requirements |
| D2-OD-15 FR-08/CR-01 separation | Before R7/R8 acceptance claims | FR-08, CR-01 |
| D2-OD-16 QR-01 replay/live readiness | Before QR-01 acceptance | QR-01 |
| D2-OD-17 SR-02 platform matrix | Before SR-02 acceptance; not before R1 | SR-02 |

Resolved/retained: OQ-01 critical profile, OQ-03 secret rules, OQ-04 run-cache semantics (TTL still open), OQ-06 REVIEW policy, OQ-07 SR-01 scope, D2-OD-04 fallback contract.

Non-blocking: OQ-02, OQ-04 TTL, OQ-05, OQ-08, OQ-11, OQ-15, D2-OD-05, D2-OD-07, ARCH-OD-05, ARCH-OD-07, ARCH-OD-09, ARCH-OD-10, ARCH-OD-11, ARCH-OD-12, D2-OD-17 (design phase).

Deferred: multi-worker lease/fencing/takeover, export, TTM/FCF YoY, QR-02. A new ADR/amendment is required to activate them.

---

## 6. Status

- D1: v1.25.0; 17 active requirements are approved as a requirement-design baseline; QR-02 is deferred; approval does not assert implementation or measured results.
- D2: v0.3 ADD-R round 3 draft; all architecture decisions proposed, not approved.
- Current recovery is single-process; lease/fencing/takeover/multi-worker/export/TTM/FCF YoY/QR-02 are deferred.
- Application code: **unchanged**.
- Tests/monitoring: **not started/not implemented**.
- The architecture does not invent approvals, thresholds, measurements, or test results.
