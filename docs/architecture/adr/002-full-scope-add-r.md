# ADR 002 — Full-Scope ADD-R Extension: Risk, Publication Lifecycle, Metrics, and Brief

Status: **v0.2 — amended by ADR 003 (ADD-R round 3)**
Decision status: **proposed**
Date: 2026-11-11
Amendment note: ADR 003 consolidates this extension into `RunCoordinator`/`RunContext`, explicit envelopes/digests, single-process recovery, logical component mapping, and R0–R8. The `RecoveryClaimStore`/`RunOwnershipLock` lease/fencing/takeover statements below are a deferred multi-worker extension, not current `FR-06`. TTM metrics, FCF YoY, export, and QR-02 remain deferred; current FR-07 uses direct metrics only.
D1 basis: `docs/req/requirements.yaml` v1.24.0
Depends on: ADR 001 (Lean A Extended)
Implementation status: **design only; no application code changed**

---

## 1. Context

ADR 001 retains Lean A for the original six requirements and establishes the single lifecycle, gate, publisher, memory writer, and context assembler. D1 v1.18.0 marks all requirements draft; the v1.14.1 additions were:

- `FR-04` and `INV-02`: deterministic portfolio risk and zero unsafe approvals.
- `FR-05`: historical retrieval of committed formal publications.
- `FR-06`: model-free startup recovery of pending publication.
- `QR-02`: bounded recovery performance.
- `FR-07`: deterministic derived financial metrics from structured facts.
- `FR-08`: bounded downstream brief for the five debate roles.

These must be added without violating the constraints that made Lean A viable: one final authority, one publication transaction, one context assembler, one data path, and one memory identity. The ADD-R round therefore evaluates extension options per capability rather than appending names to the v0.1 component table.

At the time of this ADR the draft requirements were not approved; they are now approved as a requirement-design baseline. This ADR still records a proposed architecture design for review and does not assert that any threshold, policy, implementation, or test is approved.

The extension reuses the approved foundations: `FR-01` unified data access/counters, `FR-02` lifecycle manifest/publication, `SB-01` final-decision gate, `INV-01` artifact binding, and `SR-01` security boundaries. It adds no second authority, transaction, data path, memory identity, or context assembler.

---

## 2. Decisions

### 2.1 Risk (FR-04/INV-02)

Adopt a **pure `PortfolioRiskEvaluator` invoked only by the shared `SafetyGate`**.

- `SafetyGate.finalize(proposal, coverage_snapshot, raw_risk_envelope?)` is the only entry. Inside the gate, `RiskInputValidator`, `RiskPolicyResolver`, and `PortfolioRiskEvaluator` are called exactly once; applicability is determined once from asset type and rating.
- `RiskInputValidator` canonicalizes and validates caller/application-supplied decimal input.
- `RiskPolicyResolver` loads a locatable, versioned, digest-bound policy snapshot with an explicit `threshold_status` and `human_approval_ref`.
- `PortfolioRiskEvaluator` computes projected concentration and stop distance with exact decimal arithmetic; it has no LLM, network, vendor, persistence, or UI dependency.
- `RiskEvidenceStore` builds the normalized input artifact or a safe diagnostic payload from that one evaluation; `ArtifactPublisher` writes it.
- The gate maps the result to `passed`, `blocked`, or `error`, retains all reason codes, and produces the formal `REVIEW` decision on block/error. It records the applicable risk result even when coverage already blocks.
- A stock Buy/Overweight is never `not_applicable`; missing, invalid, stale, inconsistent, insufficient-cash, unsupported, or invalid-policy input blocks.
- A valid provisional snapshot is used and labeled provisional; it is not treated as an absent policy merely because thresholds are not approved. Missing/invalid policy blocks rather than defaulting to approval.

Rejected alternatives: a separate risk gate (second authority); model-assisted risk (non-deterministic); a pre-model portfolio filter (no candidate trade yet).

### 2.2 Publication lifecycle, history, and recovery (FR-05/FR-06/QR-02)

Adopt a **permanent publication snapshot plus a temporary recovery envelope inside the existing publisher**.

- `PublicationSnapshotStore` retains the committed formal decision, binding, section manifest, complete report, final-state, risk evidence/policy references, memory entry/binding, metric bundle, and versions. Its files are written and validated **before** the terminal commit and are authoritative only after commit.
- `ReportSectionManifestBuilder` uses the versioned renderer and current capability set; only applicable non-empty sections are listed.
- `HistoryService` lists and retrieves only verified committed publications; `get_run` revalidates on every read.
- `ExportService` supports `display_copy` and `verified_package`; the latter includes a `history_reference_closure` for every followed `reused_decision_ref`.
- `RecoverySnapshotStore` writes, verifies, and quarantines the temporary recovery envelope. **Current scope:** a simple exclusive `StartupRecoveryGuard` and duplicate-start guard with bounded retry; unsupported concurrent recovery is rejected. `RecoveryClaimStore` and `RunOwnershipLock` lease/fencing/takeover are a **deferred multi-worker extension**, not current `FR-06`.
- Recovery first reads the terminal manifest and verifies the permanent publication. Committed + INV-01 + identity match is idempotent success without `recovery/`; committed + identity conflict -> `RUN_ID_CONFLICT`; committed + corrupt permanent artifacts -> `CORRUPT_RECORD`; neither overwrites or auto-republishes. Only an uncommitted record continues: memory plan/reservation -> recovery envelope -> idempotent memory write -> permanent snapshot -> terminal candidate -> commit -> read-back -> cleanup.
- `RecoveryService` uses saved records only, calls no model/data/graph/settlement/reflection, completes the one original memory entry idempotently, and commits through the same terminal manifest plus read-time `INV-01`.
- History visibility begins only at `committed` plus successful read-back validation.
- A post-commit read failure keeps the committed terminal manifest immutable, rejects the record as success, and records an independent corruption diagnostic. It does not replace the manifest with `failed`.
- After successful commit and post-commit validation, temporary `recovery/` material may be cleaned. Formal report reads, history `get_run`, memory binding validation, and `verified_package` export depend only on the permanent `publication/` snapshot; a terminal `recovery_envelope_summary` is audit-only, not a re-read dependency. A cleanup failure after commit is a warning, not a committed-identity change.
- Permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; optional `diagnostics/commit_evidence.json` is audit-only. `record_hash` uses the field-level projection in blueprint §9.6.9: build canonical content, exclude `artifact_binding.record_hash` and all result-carrying hashes, compute the content digest, fill binding, serialize, compute file-byte hashes, then build the terminal manifest.
- Concrete layout, references, lock/lease records, and reservation format are proposed in blueprint §9.6.

Rejected alternatives: a separate archive transaction/commit marker (second authority); graph re-run for recovery (not model-free); directory-scan history without a section manifest (mixing/corruption).

### 2.3 Financial metrics (FR-07)

Adopt a **deterministic fact/metric service through the unified data access**.

- Only `DataAccessService` calls vendor adapters. The existing `sec_edgar.py` statement/JSON capability is wrapped by `SecEdgarAdapter`; `FinancialFactService` requests and normalizes facts through `DataAccessService` and never calls a vendor directly.
- The existing `get_income_statement`, `get_balance_sheet`, and `get_cashflow` tools share the same adapter, run cache, counters, as-of rules, and provenance.
- Each fact separates **disclosure fields** (subject/accession/filing_ref/filed_at/form/source_fact_ref and raw concept/value/unit/currency/period/fiscal/sign) preserved from the source from **canonical fields** (fact_id/concept/per-fact period and fiscal identity/span/cumulative duration/sign/unit/currency/lineage) validated or derived only by a recorded versioned rule with input evidence and source refs. A filing's fiscal year/quarter is not copied as each historical fact's period identity. Missing or multiple plausible sources return unavailable/ambiguous; the normalizer never guesses from date proximity, equal value, column order, or a default.
- `FinancialMetricService` is pure and computes the **current direct metrics only** with exact formulas and typed n/a reasons; no quarter is derived by subtraction. TTM metrics and FCF YoY are deferred.
- `MetricEvidenceBundleBuilder` persists facts, formulas, versions, the metric block, and digests.
- `FundamentalsAdapter` appends the metric block **after the fundamentals report exists and before research debate consumes it**, regardless of whether the model calls the offered tool. Final publication only persists the existing block/bundle.
- `MetricConflictDetector` detects only structured claims with a recognizable metric ID/period/value; free-form prose is outside deterministic detection and that limitation is recorded.
- The SEC structured query contract (`DataAccessService.query("sec_structured_facts", ...)`) is proposed in blueprint §9.6.4; the adapter returns raw statements/filing metadata and `FinancialFactService` normalizes facts.
- Recovery reads the persisted bundle and never refetches filings.

Rejected alternatives: model arithmetic (baseline error, unverifiable); a direct SEC client (duplicate data path/counters); subtraction-derived quarters (prohibited).

### 2.4 Downstream brief (FR-08)

Adopt a **bounded brief view inside the existing `ContextAssembler`**.

- `DownstreamBriefBuilder` produces mandatory content (program `FR-03` gaps, `FR-07` metric block and sources, safety constraints) and compressible narrative.
- The brief is generated/reused **before the five target roles receive context**, using the program coverage view and its `coverage_view_version`; the final gate still uses the final coverage snapshot. No brief is generated after the final decision.
- For the five target roles, the brief **replaces** the four full analyst reports; other roles keep full inputs. Full and brief are not injected together.
- Mandatory content is reserved first and never truncated. Protected markers prevent generic compression from shortening it.
- A versioned budget policy defines the ordered resolution: expansion -> resolvable reference -> full report within the context hard cap -> `BRIEF_REJECTED`. Every branch obeys the context hard cap.
- Failure states are distinct: `BRIEF_DISABLED` uses the normal full-input path; `BRIEF_FULL_REPORT` is allowed only when the policy explicitly permits it, mandatory content is complete, and the full report fits the hard cap; `BRIEF_REJECTED` is terminal for the five-role context and cannot re-enter normal input or generic compression. The run fails closed at the context stage.
- `TokenCounter` measures the final request with the selected model/tokenizer; characters are auxiliary.
- `BriefAuditStore` records separate `context_audit_metadata`, including `coverage_view_version`.
- Only the five debate roles receive the brief; full reports, formal records, history, and recovery are unchanged.
- No token/cost saving is claimed until the frozen contract reports `accepted` with approved quality-loss and zero safety escapes.

Rejected alternatives: a second context assembler (second authority); fixed character truncation (mandatory loss); an unchecked model-written brief (omission/forgery).

### 2.5 Portfolio Manager and model proposal

- The original Portfolio Manager remains the terminal analysis node, wrapped by `PortfolioManagerAdapter`.
- It consumes full analyst reports, investment plan, Trader plan, risk debate, and applicable committed memory, and produces the unapproved `ModelProposal` with `rating`, `text`, `source=portfolio_manager`, `source_refs`, model identifiers, and `proposal_status=unapproved`.
- Trader or risk-debater output is source material, never the final model proposal.
- The PM does not produce the formal decision or write formal artifacts; `SafetyGate` consumes the proposal.

### 2.6 Uncommitted same-decision memory

- `MemoryRecoveryCoordinator` handles a same-decision entry owned by another uncommitted run.
- If A is active, B waits bounded without holding run/memory locks and returns `MEMORY_PENDING_RETRYABLE` on timeout.
- If A is invalid with a valid recovery envelope, recovery runs under A's original `run_id`, reservation, and snapshot; ownership is never transferred to B.
- Missing snapshot -> `MEMORY_RECOVERY_UNAVAILABLE`; recovery failure -> `MEMORY_RECOVERY_FAILED`; binding conflict -> `MEMORY_CONFLICT`.
- B may reuse A only after A commits and validates, through `reused_decision_ref`; B never writes a duplicate entry or takes A's version.
- `MemoryReservationStore` keeps a persistent high-water mark over all historical allocations, including failed reservations; a failed version is never reissued. `committed` is a derived projection from the terminal manifest, not a second commit condition.

---

## 3. Component and dependency rules

| Component | Target module | Depends on | Must not depend on |
|---|---|---|---|
| `RiskInputValidator` | `run/risk_input.py` | Canonicalizer | LLM, vendor, network, UI |
| `PortfolioRiskEvaluator` | `run/risk_evaluator.py` | Decimal only | LLM, network, vendor, persistence, UI, gate state |
| `RiskPolicyResolver` | `run/risk_policy.py` | PolicyCatalog, file/policy source | Model, network |
| `RiskEvidenceStore` | `run/risk_evidence.py` | Canonicalizer, SecretRedactor | Vendor, model |
| `PublicationSnapshotStore` | `run/publication.py` | Canonicalizer, SecretRedactor | Model, vendor |
| `ReportSectionManifestBuilder` | `run/render.py` | `reporting.py` | Model, network |
| `HistoryService` | `run/history.py` | PublicationSnapshotStore | Model, vendor, arbitrary directory scan as authority |
| `ExportService` | `run/export.py` | HistoryService, SR-01 | Model, vendor |
| `RecoveryService` | `run/recovery.py` | Snapshot/claim stores, publisher, memory completion, renderer | LLM, external data, graph, settlement, reflection |
| `RecoverySnapshotStore` | `run/recovery_snapshot.py` | Canonicalizer, SecretRedactor | Model, vendor |
| `RecoveryClaimStore` (deferred) | `run/recovery_claim.py` | Future multi-worker claim state, future ownership lock | Model, vendor |
| `RunOwnershipLock` (deferred) | `run/ownership.py` | Local filesystem | Model, vendor, second commit marker |
| `MemoryReservationStore` | `run/memory_reservation.py` | Memory lock, Canonicalizer | Model, vendor, unlocked version allocation |
| `MemoryService` | `run/memory_service.py` | MemoryReservationStore, TradingMemoryLog, SecretRedactor | Direct model output |
| `MemoryRecoveryCoordinator` | `run/memory_coordination.py` | MemoryService, MemoryReservationStore, RecoveryService | Ownership transfer, second entry, lock held while waiting |
| `PortfolioManagerAdapter` | `run/proposal.py` | `agents/managers/portfolio_manager.py`, MemoryService, ContextAssembler | Formal decision, gate override, Trader/risk-debater promotion |
| `FinancialFactService` | `run/financial_facts.py` | DataAccessService, RunEvidenceStore | Direct vendor |
| `SecEdgarAdapter` (existing, wrapped) | `tradingagents/dataflows/vendors/sec_edgar.py` | Vendor/HTTP | Policy, fact normalization, direct caller outside DataAccessService |
| `FinancialMetricService` | `run/financial_metrics.py` | Decimal only | Model, network, vendor |
| `MetricEvidenceBundleBuilder` | `run/metric_evidence.py` | Canonicalizer | Model, vendor |
| `MetricConflictDetector` | `run/metric_conflict.py` | None | Model |
| `FundamentalsAdapter` | `run/adapters.py` | Financial services | Direct vendor |
| `DownstreamBriefBuilder` | `run/brief.py` | TokenCounter, PolicyCatalog | Model as unchecked author |
| `TokenCounter` | `run/tokens.py` | Selected model/tokenizer | Approximate character counting as final measure |
| `BriefAuditStore` | `run/brief.py` | SecretRedactor | Full-report mutation |

`SafetyGate`, `ArtifactPublisher`, `MemoryService`, and `ContextAssembler` remain the only final-decision, publication, memory, and context authorities. `PortfolioManagerAdapter` is the only producer of the final model proposal. `SafetyGate` is the only caller of the risk services; `DataAccessService` is the only vendor caller; current normal publication and recovery share one `StartupRecoveryGuard`. Lease/fencing/takeover is deferred.

---

## 4. Compatibility

- Existing graph and agents remain.
- `propagate` keeps `(final_state, signal)` after publication.
- `save_reports`, `write_report_tree`, `store_decision`, and `_log_state` become internal or record-dependent adapters.
- CLI, backtest, and programmatic entry points share the same gate and publisher.
- Existing tests remain; new suites cover risk, history/recovery, metrics, and brief.
- No legacy report migration or indexing is performed.

---

## 5. Risks

| Risk | Mitigation |
|---|---|
| Risk evaluator becomes a second authority | Pure result only; `SafetyGate` is the sole caller; gate owns the decision. |
| Recovery duplicates publication | Same commit condition; single-process startup guard; identity check before publication. |
| Post-commit corruption overwrites evidence | Keep the committed terminal manifest immutable; independent diagnostic; reject as success. |
| Ownership is checked outside the protected write | One check-and-write boundary under the startup guard; lock order guard -> memory lock; lease/fencing deferred. |
| Memory versions collide or failed versions are reissued | Persistent append-only allocation history with a high-water mark over all allocations including failed; retries/recovery reuse their own reservation. |
| History mixes stale sections | Permanent snapshot + section manifest + read-time revalidation. |
| Metric periods/restatements are wrong | Structured identity, as-of filtering, typed n/a, frozen reference manifest; block before research debate. |
| Brief drops mandatory content or duplicates full reports | Mandatory reservation, protected markers, five-role replacement mapping; full artifacts immutable. |
| Token budget is exceeded | Tokenizer measurement for the final request; characters auxiliary; hard-cap rejection. |
| Compatibility adapters diverge | Regression suites and explicit deprecation. |
| Draft requirements are mistaken for approved | Status labels and open decisions; no approval claimed. |

---

## 6. Consequences

Positive:

- All 18 requirements have a component owner and a planned verification.
- One final authority, one publication transaction, one context assembler, one data path, and one memory identity remain intact.
- Risk and metric logic are pure and testable.
- History and recovery have a clear permanent/temporary split.

Negative:

- More components, storage states, and tests.
- Risk and recovery failure modes require extensive negative testing.
- Several implementation/acceptance decisions remain open and blocking.
- The brief's benefit is unmeasured until the frozen evaluation runs.

---

## 7. Re-decision conditions

Reopen this ADR if:

1. The risk evaluator cannot be shared without a second authority.
2. Recovery cannot reuse the existing publication commit.
3. History cannot verify from the permanent snapshot alone.
4. Metric facts cannot be obtained through the unified data access.
5. The brief needs a separate context authority to meet quality thresholds.
6. A requirement approval changes the risk, history, recovery, metric, or brief contract.
7. Measured costs/complexity do not justify the extension.

---

## 8. Status

- Decision status: **proposed, pending human review**.
- Application implementation: **not started**.
- Tests: **not started**.
- Monitoring: **not implemented**.
- Benefits: **not measured**.
- D1: v1.24.0; 17 active requirements are approved as a requirement-design baseline; QR-02 is deferred; approval does not assert implementation or measured results.
