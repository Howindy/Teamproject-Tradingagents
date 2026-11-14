# D2 Trace Matrix

Status: **v0.2 — ADD-R round 2 draft / pending human review**  
Date: 2026-11-11  
D1 basis: `docs/req/requirements.yaml` v1.14.1 — 13 requirements, 111 acceptance criteria  
Approval basis: `FR-01`, `FR-02`, `FR-03`, `SB-01`, `INV-01`, `SR-01` approved; `FR-04`, `FR-05`, `FR-06`, `FR-07`, `FR-08`, `INV-02`, `QR-02` draft  
Implementation status: **design only; no application code changed**

---

## 1. Purpose and status legend

This matrix traces every D1 acceptance criterion to:

- the D2 component expected to satisfy it;
- a planned test ID;
- a planned runtime monitor ID;
- the current implementation/test status.

Status values:

- **design only** — no application code exists;
- **not started** — the planned test/monitor is not implemented;
- **not measured** — no performance/cost/quality benefit has been measured.

Only the baseline facts under `baseline/runs/baseline-20261020-01/` are measured evidence. No new test, monitor, implementation, approval, or measurement is claimed.

Draft requirement rows are design proposals, not approved requirements. A trace row is not approval.

---

## 2. Requirement-to-component summary

| Requirement | Status | ACs | Primary components | Secondary components | Phase |
|---|---|---|---|---|---|
| `FR-01` | approved | 7 | `DataAccessService`, `RunEvidenceStore` | `RunContext`, `Canonicalizer` | 1 |
| `FR-02` | approved | 15 | `ArtifactPublisher`, `RunEvidenceStore` | `RunContext`, `ReportSectionManifestBuilder`, `PublicationSnapshotStore`, `RecoverySnapshotStore`, `RunOwnershipLock` | 1/4 |
| `FR-03` | approved | 10 | `AvailabilityIndex`, `RunEvidenceStore` | `DataAccessService`, `SafetyGate` | 1 |
| `FR-04` | draft | 11 | `SafetyGate` (sole caller), `PortfolioRiskEvaluator`, `RiskPolicyResolver` | `RiskInputValidator`, `RiskEvidenceStore`, `MemoryService` | 1 |
| `FR-05` | draft | 4 | `HistoryService`, `PublicationSnapshotStore` | `ReportSectionManifestBuilder`, `ExportService`, `SecretRedactor` | 4 |
| `FR-06` | draft | 6 | `RecoveryService`, `RecoverySnapshotStore`, `RecoveryClaimStore`, `RunOwnershipLock` | `ArtifactPublisher`, `MemoryService`, `MemoryReservationStore` | 1/4 |
| `FR-07` | draft | 11 | `FinancialFactService`, `FinancialMetricService` | `SecEdgarAdapter`, `MetricEvidenceBundleBuilder`, `MetricConflictDetector`, `FundamentalsAdapter` | 3 |
| `FR-08` | draft | 5 | `DownstreamBriefBuilder`, `ContextAssembler` | `TokenCounter`, `BriefAuditStore`, `PolicyCatalog`, protected-marker policy, failure-state policy | 5 |
| `QR-02` | draft | 2 | `RecoveryService`, `PublicationSnapshotStore` | `RecoverySnapshotStore`, benchmark harness | 4 |
| `SB-01` | approved | 12 | `SafetyGate`, `FinalizedRunRecord` | `PortfolioManagerAdapter`, `PortfolioRiskEvaluator`, `ArtifactPublisher` | 1 |
| `INV-01` | approved | 12 | `FinalizedRunRecord`, `ArtifactPublisher` | `MemoryService`, `MemoryReservationStore`, `PublicationSnapshotStore`, `RunOwnershipLock` | 1/4 |
| `INV-02` | draft | 7 | `SafetyGate`, `PortfolioRiskEvaluator` | `MemoryService`, `MemoryRecoveryCoordinator`, `ArtifactPublisher` | 1 |
| `SR-01` | approved | 9 | `SecretRedactor` | all writers, `ExportService` | 1/4 |

Total: 13 requirements, 111 acceptance criteria.

---

## 3. Acceptance-criterion trace

### 3.1 FR-01 — Single execution per identical logical query (7 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `FR-01-AC1` | `DataAccessService` | `T-FR01-01` sequential duplicate -> one execution | `MON-FR01-01` duplicate executions | design only; not started |
| `FR-01-AC2` | `DataAccessService` | `T-FR01-02` concurrent single-flight | `MON-FR01-02` concurrent duplicates | design only; not started |
| `FR-01-AC3` | `DataAccessService`, `RunEvidenceStore` | `T-FR01-03` terminal failure reuse | `MON-FR01-03` terminal outcome reuse | design only; not started |
| `FR-01-AC4` | `DataAccessService` | `T-FR01-04` run isolation vs vendor cache | `MON-FR01-04` cache-hit classification | design only; not started |
| `FR-01-AC5` | `DataAccessService`, `RunEvidenceStore` | `T-FR01-05` retry/fallback budgets | `MON-FR01-05` retry/fallback counters | design only; not started |
| `FR-01-AC6` | `Canonicalizer`, `RunEvidenceStore` | `T-FR01-06` business-field equivalence | `MON-FR01-06` business/execution diff | design only; not started |
| `FR-01-AC7` | `DataAccessService`, evaluation harness | `T-FR01-07` frozen live A/B | `MON-FR01-07` live quality/safety delta | design only; not started |

### 3.2 FR-02 — Lifecycle-complete run manifest (15 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `FR-02-AC1` | `RunContext`, `ArtifactPublisher` | `T-FR02-01` completed manifest path/identity/schema | `MON-FR02-01` manifest count/path/schema | design only; not started |
| `FR-02-AC2` | `FailureFinalizer`, `ArtifactPublisher` | `T-FR02-02` handled-failure terminal manifest | `MON-FR02-02` failed terminal record | design only; not started |
| `FR-02-AC3` | `RunContext`, `ArtifactPublisher` | `T-FR02-03` forced-termination running manifest | `MON-FR02-03` running-record integrity | design only; not started |
| `FR-02-AC4` | `RunContext`, `EntrypointAdapter` | `T-FR02-04` run-id/path/parent uniqueness | `MON-FR02-04` duplicate/orphan manifest | design only; not started |
| `FR-02-AC5` | `ArtifactPublisher`, `RunEvidenceStore` | `T-FR02-05` manifest schema/fields | `MON-FR02-05` schema/field validation | design only; not started |
| `FR-02-AC6` | `RunEvidenceStore`, `DataAccessService` | `T-FR02-06` counter ground truth | `MON-FR02-06` counter reconciliation | design only; not started |
| `FR-02-AC7` | `RunEvidenceStore` | `T-FR02-07` token complete/partial/unavailable | `MON-FR02-07` missing-usage count | design only; not started |
| `FR-02-AC8` | `ArtifactPublisher` | `T-FR02-08` timing and overhead benchmark | `MON-FR02-08` phase/overhead duration | design only; not started |
| `FR-02-AC9` | `ArtifactPublisher` | `T-FR02-09` write-failure integrity | `MON-FR02-09` corrupt/partial manifest | design only; not started |
| `FR-02-AC10` | `ArtifactPublisher`, `SafetyGate` | `T-FR02-10` completed-state counterexamples | `MON-FR02-10` invalid completed record | design only; not started |
| `FR-02-AC11` | `PublicationSnapshotStore`, `ArtifactPublisher` | `T-FR02-11` resubmission no-op / `RUN_ID_CONFLICT` | `MON-FR02-11` identity conflict | design only; not started |
| `FR-02-AC12` | `ReportSectionManifestBuilder`, `SafetyGate` | `T-FR02-12` section manifest and unapproved labels | `MON-FR02-12` section/formal label mismatch | design only; not started |
| `FR-02-AC13` | `PublicationSnapshotStore`, `ArtifactPublisher` | `T-FR02-13` completed negatives and cleanup warning | `MON-FR02-13` false completed result | design only; not started |
| `FR-02-AC14` | `EntrypointAdapter`, `RecoverySnapshotStore`, `PublicationSnapshotStore`, `ArtifactPublisher` | `T-FR02-14` CLI/API recovery-snapshot generation + permanent snapshot before commit + cleanup; history read after cleanup from permanent | `MON-FR02-14` snapshot/commit/cleanup-read ordering | design only; not started |
| `FR-02-AC15` | `ArtifactPublisher`, `PublicationSnapshotStore` | `T-FR02-15` concurrent same-second publication | `MON-FR02-15` mixed/stale sections | design only; not started |

### 3.3 FR-03 — Canonical availability state (10 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `FR-03-AC1` | `AvailabilityIndex` | `T-FR03-01` closed status evidence table | `MON-FR03-01` status/decision mismatch | design only; not started |
| `FR-03-AC2` | `RunEvidenceStore`, `AvailabilityIndex` | `T-FR03-02` record/source/supports/aggregation | `MON-FR03-02` record/source mismatch | design only; not started |
| `FR-03-AC3` | `AvailabilityIndex`, `PolicyCatalog` | `T-FR03-03` profile defaults and overrides | `MON-FR03-03` profile drift | design only; not started |
| `FR-03-AC4` | `DataAccessService`, `AvailabilityIndex` | `T-FR03-04` fallback contract | `MON-FR03-04` invalid fallback clearing | design only; not started |
| `FR-03-AC5` | `AvailabilityIndex` | `T-FR03-05` all/any/min:N aggregation | `MON-FR03-05` aggregation mismatch | design only; not started |
| `FR-03-AC6` | `AvailabilityIndex`, report adapter | `T-FR03-06` critical gap vs limitation | `MON-FR03-06` hidden/leaked gap | design only; not started |
| `FR-03-AC7` | `AvailabilityIndex`, `RunEvidenceStore` | `T-FR03-07` component_missing records | `MON-FR03-07` missing-record/attempt mismatch | design only; not started |
| `FR-03-AC8` | `AvailabilityIndex`, `Canonicalizer` | `T-FR03-08` deterministic consumers | `MON-FR03-08` consumer/order divergence | design only; not started |
| `FR-03-AC9` | `SafetyGate`, report, memory | `T-FR03-09` final decision consumes canonical state | `MON-FR03-09` consumer gap mismatch | design only; not started |
| `FR-03-AC10` | `AvailabilityIndex` | `T-FR03-10` empty-set/threshold/invalid profile | `MON-FR03-10` aggregation rule violation | design only; not started |

### 3.4 FR-04 — Deterministic portfolio risk (11 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `FR-04-AC1` | `SafetyGate`, `RiskInputValidator`, `PortfolioRiskEvaluator` | `T-FR04-01` exact 0.30/0.05 boundary pass; applicability once | `MON-FR04-01` boundary/digest/single-caller mismatch | design only; provisional threshold |
| `FR-04-AC2` | `PortfolioRiskEvaluator`, `SafetyGate` | `T-FR04-02` concentration breach block | `MON-FR04-02` position-limit escape | design only; provisional threshold |
| `FR-04-AC3` | `PortfolioRiskEvaluator`, `SafetyGate` | `T-FR04-03` stop-distance breach block | `MON-FR04-03` stop-distance escape | design only; provisional threshold |
| `FR-04-AC4` | `PortfolioRiskEvaluator`, `SafetyGate` | `T-FR04-04` dual breach priority | `MON-FR04-04` reason-order mismatch | design only; provisional threshold |
| `FR-04-AC5` | `RiskInputValidator`, `RiskEvidenceStore` | `T-FR04-05` invalid input matrix and diagnostic | `MON-FR04-05` invalid-input default approval | design only; not measured |
| `FR-04-AC6` | `RiskInputValidator`, `SafetyGate` | `T-FR04-06` applicability matrix | `MON-FR04-06` not-applicable-as-pass | design only; not measured |
| `FR-04-AC7` | `PortfolioRiskEvaluator`, `SafetyGate` | `T-FR04-07` narrative injection/dependency sentinels | `MON-FR04-07` forbidden dependency call | design only; not measured |
| `FR-04-AC8` | `PortfolioRiskEvaluator`, `Canonicalizer` | `T-FR04-08` determinism/cutoff/boundary fuzz | `MON-FR04-08` deterministic result mismatch | design only; provisional threshold |
| `FR-04-AC9` | `RiskPolicyResolver` | `T-FR04-09` policy snapshot/digest/approval | `MON-FR04-09` policy default approval | design only; provisional threshold |
| `FR-04-AC10` | `RiskEvidenceStore`, `MemoryService` | `T-FR04-10` current vs reused memory evidence | `MON-FR04-10` risk evidence mismatch | design only; not measured |
| `FR-04-AC11` | evaluation harness | `T-FR04-11` cache A/B + risk-policy A/B | `MON-FR04-11` risk/cache misclassification | design only; provisional threshold |

### 3.5 FR-05 — Historical formal publication retrieval (4 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `FR-05-AC1` | `HistoryService`, `PublicationSnapshotStore` | `T-FR05-01` filters/order/pagination/visibility | `MON-FR05-01` history filter/order mismatch | design only; not started |
| `FR-05-AC2` | `HistoryService`, `PublicationSnapshotStore` | `T-FR05-02` retrieval/revalidation/errors | `MON-FR05-02` partial/corrupt retrieval | design only; not started |
| `FR-05-AC3` | `ReportSectionManifestBuilder`, `PublicationSnapshotStore` | `T-FR05-03` section isolation/tamper | `MON-FR05-03` foreign/stale section | design only; not started |
| `FR-05-AC4` | `ExportService`, `HistoryService`, `SecretRedactor` | `T-FR05-04` export modes/closure/conflict/path | `MON-FR05-04` export conflict/path escape | design only; not started |

### 3.6 FR-06 — Startup recovery (6 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `FR-06-AC1` | `RecoveryService`, `RecoverySnapshotStore`, `ArtifactPublisher` | `T-FR06-01` model-free valid recovery | `MON-FR06-01` forbidden dependency call | design only; not started |
| `FR-06-AC2` | `RecoverySnapshotStore`, `PublicationSnapshotStore` | `T-FR06-02` missing/corrupt snapshot, persistent fault, cleanup | `MON-FR06-02` false successful publication | design only; not started |
| `FR-06-AC3` | `RecoveryClaimStore`, `RecoveryService` | `T-FR06-03` duplicate/stale/lost-lease workers | `MON-FR06-03` lost-lease write/duplicate publication | design only; not started |
| `FR-06-AC4` | `HistoryService`, `PublicationStatusReader` | `T-FR06-04` status/history visibility | `MON-FR06-04` status confusion | design only; not started |
| `FR-06-AC5` | `RecoveryService`, `PublicationSnapshotStore` | `T-FR06-05` retry/identity/no-op/conflict | `MON-FR06-05` duplicate publication | design only; not started |
| `FR-06-AC6` | `MemoryService`, `RecoveryService` | `T-FR06-06` first-write/partial-write/memory-disabled | `MON-FR06-06` extra/duplicate memory entry | design only; not started |

### 3.7 FR-07 — Deterministic financial metrics (11 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `FR-07-AC1` | `FinancialMetricService` | `T-FR07-01` NVDA growth/margin recomputation | `MON-FR07-01` formula/value mismatch | design only; provisional threshold |
| `FR-07-AC2` | `FinancialFactService`, `FinancialMetricService` | `T-FR07-02` missing/ambiguous comparison n/a | `MON-FR07-02` substituted input | design only; not started |
| `FR-07-AC3` | `FinancialFactService`, `SecEdgarAdapter` | `T-FR07-03` disclosure vs canonical fields; per-fact period/fiscal identity; near-date/restatement/as-of; unavailable/ambiguous, no guessing | `MON-FR07-03` filing-level fiscal copy/silent merge/look-ahead/guessed link | design only; not started |
| `FR-07-AC4` | `FinancialMetricService` | `T-FR07-04` TTM continuity/formulas/P-E | `MON-FR07-04` fiscal-position mismatch | design only; provisional threshold |
| `FR-07-AC5` | `FinancialFactService`, `FinancialMetricService` | `T-FR07-05` cash-flow span/FCF/capex sign | `MON-FR07-05` span/sign mismatch | design only; provisional threshold |
| `FR-07-AC6` | `FinancialFactService` | `T-FR07-06` as-of/zero/EPS/currency/unit | `MON-FR07-06` look-ahead/default value | design only; not started |
| `FR-07-AC7` | `FinancialFactService`, `DataAccessService`, `SecEdgarAdapter` | `T-FR07-07` unified data access/counters/per-fact provenance | `MON-FR07-07` direct vendor call/lost provenance | design only; not started |
| `FR-07-AC8` | `FundamentalsAdapter`, `MetricEvidenceBundleBuilder` | `T-FR07-08` program block before research debate + bundle persistence | `MON-FR07-08` missing/metric/timing mismatch | design only; not started |
| `FR-07-AC9` | `MetricConflictDetector` | `T-FR07-09` structured conflict/unmapped limitation | `MON-FR07-09` wrong number authoritative | design only; not started |
| `FR-07-AC10` | evaluation harness, independent reference | `T-FR07-10` NVDA + frozen non-NVDA references | `MON-FR07-10` reference/hash mismatch | design only; reference pending |
| `FR-07-AC11` | `RecoveryService`, `MetricEvidenceBundleBuilder` | `T-FR07-11` model-free metric recovery | `MON-FR07-11` refetch/model/graph call | design only; not started |

### 3.8 FR-08 — Downstream brief (5 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `FR-08-AC1` | `DownstreamBriefBuilder`, `TokenCounter` | `T-FR08-01` markers/Unicode/short cases; protected blocks intact | `MON-FR08-01` marker/budget/forgery/protected truncation | design only; not started |
| `FR-08-AC2` | `DownstreamBriefBuilder`, `PolicyCatalog` | `T-FR08-02` mandatory/ordered budget/reference; coverage_view_version | `MON-FR08-02` mandatory drop/view-version mismatch | design only; provisional budget |
| `FR-08-AC3` | `ContextAssembler`, `BriefAuditStore` | `T-FR08-03` five-role replacement/non-mutation/audit metadata/coverage_view_version | `MON-FR08-03` full-artifact mutation/full+brief duplication/view-version mismatch | design only; not started |
| `FR-08-AC4` | `DownstreamBriefBuilder`, evaluation harness | `T-FR08-04` fidelity/forged field/quality/safety | `MON-FR08-04` safety escape/quality loss | design only; provisional threshold |
| `FR-08-AC5` | evaluation harness, `TokenCounter` | `T-FR08-05` controlled A/B/lifecycle/cost fields | `MON-FR08-05` unmeasured saving claim | design only; provisional threshold |

### 3.9 QR-02 — Bounded recovery performance (2 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `QR-02-AC1` | `RecoveryService`, benchmark harness | `T-QR02-01` 30-trial p95 correctness | `MON-QR02-01` p95/failure sample | design only; target provisional |
| `QR-02-AC2` | `RecoveryService`, dependency sentinels | `T-QR02-02` slow/failing filesystem correctness | `MON-QR02-02` skipped validation/model-free violation | design only; not started |

### 3.10 SB-01 — Deterministic fail-closed gate (12 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `SB-01-AC1` | `SafetyGate` | `T-SB01-01` five-rating critical-gap matrix | `MON-SB01-01` blocked formal rating/text | design only; provisional threshold |
| `SB-01-AC2` | `SafetyGate` | `T-SB01-02` five-rating complete-coverage matrix | `MON-SB01-02` gate pass/unchanged | design only; provisional threshold |
| `SB-01-AC3` | `SafetyGate` | `T-SB01-03` model REVIEW semantics | `MON-SB01-03` model-review mishandling | design only; not started |
| `SB-01-AC4` | `SafetyGate` | `T-SB01-04` coverage/gap contradiction | `MON-SB01-04` coverage/gap mismatch | design only; not started |
| `SB-01-AC5` | `SafetyGate` | `T-SB01-05` malformed/missing input | `MON-SB01-05` invalid gate input | design only; not started |
| `SB-01-AC6` | `SafetyGate`, `AvailabilityIndex` | `T-SB01-06` forged/stale/hash snapshot | `MON-SB01-06` snapshot trust/hash | design only; not started |
| `SB-01-AC7` | `SafetyGate`, all formal consumers | `T-SB01-07` formal/intermediate separation | `MON-SB01-07` unapproved proposal leak | design only; not started |
| `SB-01-AC8` | entry adapters, `SafetyGate` | `T-SB01-08` entry-point gate matrix | `MON-SB01-08` gate bypass | design only; not started |
| `SB-01-AC9` | `SafetyGate`, `FailureFinalizer` | `T-SB01-09` gate fault injection | `MON-SB01-09` silent pass | design only; not started |
| `SB-01-AC10` | `SafetyGate`, `ArtifactPublisher` | `T-SB01-10` gate-result consistency | `MON-SB01-10` gate-result mismatch | design only; provisional threshold |
| `SB-01-AC11` | `SafetyGate`, risk services | `T-SB01-11` risk-branch gate matrix | `MON-SB01-11` risk bypass/masked failure | design only; provisional threshold |
| `SB-01-AC12` | `SafetyGate`, risk services | `T-SB01-12` combined coverage+error | `MON-SB01-12` wrong primary/review class | design only; not started |

### 3.11 INV-01 — Bound formal result (12 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `INV-01-AC1` | `ArtifactPublisher`, `MemoryService` | `T-INV01-01` artifact binding/summary | `MON-INV01-01` binding mismatch | design only; not started |
| `INV-01-AC2` | `Canonicalizer` | `T-INV01-02` canonicalization/order/timestamps | `MON-INV01-02` false/missed mismatch | design only; not started |
| `INV-01-AC3` | `RunEvidenceStore`, `Canonicalizer` | `T-INV01-03` record identity/provenance | `MON-INV01-03` provenance mismatch | design only; not started |
| `INV-01-AC4` | `AvailabilityIndex`, all artifacts | `T-INV01-04` legal fallback vs silent substitution | `MON-INV01-04` silent substitution | design only; not started |
| `INV-01-AC5` | `SafetyGate`, `ArtifactPublisher` | `T-INV01-05` decision equality scope | `MON-INV01-05` decision/digest mismatch | design only; not started |
| `INV-01-AC6` | `ArtifactPublisher` | `T-INV01-06` missing/empty artifact negatives | `MON-INV01-06` missing artifact | design only; not started |
| `INV-01-AC7` | `ArtifactPublisher`, `MemoryService` | `T-INV01-07` partial write/crash/retry | `MON-INV01-07` partial/duplicate publish | design only; not started |
| `INV-01-AC8` | `MemoryService` | `T-INV01-08` settlement/rotation/illegal change | `MON-INV01-08` memory lifecycle mismatch | design only; not started |
| `INV-01-AC9` | `ArtifactPublisher`, `PublicationSnapshotStore` | `T-INV01-09` checkpoint/read-time tamper | `MON-INV01-09` checkpoint/tamper failure | design only; not started |
| `INV-01-AC10` | `MemoryService` | `T-INV01-10` same-day/version/memory-disabled | `MON-INV01-10` memory rerun/disabled mismatch | design only; not started |
| `INV-01-AC11` | `ReportSectionManifestBuilder`, `PublicationSnapshotStore` | `T-INV01-11` section manifest tamper | `MON-INV01-11` missing/foreign section | design only; not started |
| `INV-01-AC12` | `PublicationSnapshotStore`, `PublicationStatusReader` | `T-INV01-12` truthful completion/cleanup warning | `MON-INV01-12` false committed result | design only; not started |

### 3.12 INV-02 — Portfolio-risk authority (7 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `INV-02-AC1` | `SafetyGate`, `PortfolioRiskEvaluator` | `T-INV02-01` generated >=1000 fixture corpus | `MON-INV02-01` unsafe/default/not-applicable approval | design only; not started |
| `INV-02-AC2` | `PortfolioRiskEvaluator` | `T-INV02-02` repeated determinism/boundaries | `MON-INV02-02` deterministic mismatch | design only; not started |
| `INV-02-AC3` | `SafetyGate`, pure services | `T-INV02-03` narrative injection/sentinels | `MON-INV02-03` forbidden dependency call | design only; not started |
| `INV-02-AC4` | `ArtifactPublisher`, `MemoryService` | `T-INV02-04` cross-artifact risk evidence | `MON-INV02-04` cross-artifact mismatch | design only; not started |
| `INV-02-AC5` | `MemoryService` | `T-INV02-05` reuse/supersede/risk-block/memory-disabled | `MON-INV02-05` second memory identity | design only; not started |
| `INV-02-AC6` | `SafetyGate`, risk services | `T-INV02-06` applicability/failure matrix | `MON-INV02-06` risk masking/not-applicable pass | design only; not started |
| `INV-02-AC7` | evaluation harness | `T-INV02-07` cache A/B + risk-policy A/B | `MON-INV02-07` cache/risk misclassification | design only; provisional threshold |

### 3.13 SR-01 — Secret-safe records and path confinement (9 ACs)

| AC | Component | Planned test | Monitor | Status |
|---|---|---|---|---|
| `SR-01-AC1` | `SecretRedactor`, all writers | `T-SR01-01` known-secret exact match | `MON-SR01-01` known-secret match | design only; not started |
| `SR-01-AC2` | `SecretRedactor` | `T-SR01-02` versioned pattern categories | `MON-SR01-02` pattern/rule-version mismatch | design only; not started |
| `SR-01-AC3` | preference writer/resolver | `T-SR01-03` audit/restore endpoint split | `MON-SR01-03` inline secret in preferences | design only; not started |
| `SR-01-AC4` | `SecretRedactor`, `ArtifactPublisher` | `T-SR01-04` fail-closed scanner/redaction | `MON-SR01-04` scanner failure treated as pass | design only; not started |
| `SR-01-AC5` | `SecretRedactor` | `T-SR01-05` over-redaction avoidance | `MON-SR01-05` over-redaction | design only; not started |
| `SR-01-AC6` | `SecretRedactor`, all writers | `T-SR01-06` scan scope/version/report | `MON-SR01-06` scope/version gap | design only; not started |
| `SR-01-AC7` | existing scrub/.env + new writers | `T-SR01-07` preserved controls/regression | `MON-SR01-07` existing-control regression | design only; not started |
| `SR-01-AC8` | `ExportService`, `SecretRedactor` | `T-SR01-08` path confinement/link escape | `MON-SR01-08` out-of-root write | design only; not started |
| `SR-01-AC9` | `ExportService` | `T-SR01-09` export conflict/legacy preservation | `MON-SR01-09` overwritten target/legacy change | design only; not started |

---

## 4. Planned test inventory (counts)

| Family | Tests | Status |
|---|---|---|
| FR-01 | 7 | not started |
| FR-02 | 15 | not started |
| FR-03 | 10 | not started |
| FR-04 | 11 | not started |
| FR-05 | 4 | not started |
| FR-06 | 6 | not started |
| FR-07 | 11 | not started |
| FR-08 | 5 | not started |
| QR-02 | 2 | not started |
| SB-01 | 12 | not started |
| INV-01 | 12 | not started |
| INV-02 | 7 | not started |
| SR-01 | 9 | not started |
| **Total** | **111** | **not started** |

Additional scenario tests: `T-SCEN-01`..`T-SCEN-18` (18 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-44`, not started.

### Scenario tests

| Test ID | Scenario | Status |
|---|---|---|
| `T-SCEN-01` | Normal pass: coverage complete, risk passes, one commit, snapshots, memory idempotency, post-commit read | not started |
| `T-SCEN-02` | Business block: critical gap, invalid/limit risk, model REVIEW, combined coverage+risk | not started |
| `T-SCEN-03` | System exception: evaluator/gate error, failed run, no commit, no tradeable output | not started |
| `T-SCEN-04` | Pre-commit interruption: recover from snapshot, one commit, no duplicate memory | not started |
| `T-SCEN-05` | Post-commit corruption: immutable committed manifest, `CORRUPT_RECORD`, independent diagnostic, no second publication | not started |
| `T-SCEN-06` | Duplicate recovery: repeated startup/claim, one winner, no duplicate publication/memory | not started |
| `T-SCEN-07` | Concurrent publication: two normal publishers plus recovery, shared lock/fencing, lost-owner rejection | not started |
| `T-SCEN-08` | Context overflow: protected mandatory blocks, brief replacement, hard-cap fallback/rejection | not started |
| `T-SCEN-09` | History/export edge cases: status exclusion, section tamper, closure, conflict | not started |
| `T-SCEN-10` | Cleanup after successful commit: history get_run, memory binding, verified export from permanent snapshot only | not started |
| `T-SCEN-11` | Brief disabled/full-report fallback/final rejection; post-rejection bypass attempt | not started |
| `T-SCEN-12` | Concurrent same decision with uncommitted entry: active wait/retryable, recovery under A identity, missing snapshot/failure/conflict | not started |
| `T-SCEN-13` | Old process paused holding file lock; lease expiry; takeover; lost-owner rejection | not started |
| `T-SCEN-14` | Portfolio Manager proposal source; Trader/risk-debater output not promoted | not started |
| `T-SCEN-15` | Highest version failed, new run allocates, old run retries own reservation; no version reuse | not started |
| `T-SCEN-16` | Commit/ledger-update interruption; manifest authority; ledger projection repair; failed allocations preserved | not started |
| `T-SCEN-17` | Recovery after cleanup: terminal-first idempotent success without recovery directory | not started |
| `T-SCEN-18` | Committed permanent artifact corrupt: `CORRUPT_RECORD`, no overwrite/republish | not started |

Additional architecture tests:

| Test ID | Purpose | Status |
|---|---|---|
| `T-ARCH-01` | writer bypass audit | not started |
| `T-ARCH-02` | publish candidate/commit/read-back/retry | not started |
| `T-ARCH-03` | memory commit status/read filtering/reuse/conflict | not started |
| `T-ARCH-04` | checkpoint resume matrix | not started |
| `T-ARCH-05` | context compression/re-injection/token budget | not started |
| `T-ARCH-06` | runtime AI permission boundary | not started |
| `T-ARCH-07` | coding-agent permission matrix | not started |
| `T-ARCH-08` | ADD-R driver/tactic/iteration trace audit | not started |
| `T-ARCH-09` | requirements validator and result reproducibility | implemented in `docs/req/validate_requirements.py`; currently not reproducible in this checkout (ARCH-OD-01/02) |
| `T-ARCH-10` | decision timing vs publish/risk/metric boundary | not started |
| `T-ARCH-11` | independent failed-run publication | not started |
| `T-ARCH-12` | mandatory preflight timing/ownership/shared cache | not started |
| `T-ARCH-13` | component module/interface/error-contract audit | not started |
| `T-ARCH-14` | validation-result hashes and stale detection | implemented in validator `--check`; blocked by ARCH-OD-01/02 |
| `T-ARCH-15` | candidate comparison under identical safety contract | not started |
| `T-ARCH-16` | thin implementation slice for Lean A/B/C comparison | not started |
| `T-ARCH-17` | risk authority/no-second-gate audit | not started |
| `T-ARCH-18` | recovery claim/fencing/lost-lease audit | not started |
| `T-ARCH-19` | history/export permanent-snapshot dependency audit | not started |
| `T-ARCH-20` | metric bundle persistence/model-free recovery audit | not started |
| `T-ARCH-21` | brief mandatory preservation/non-mutation audit | not started |
| `T-ARCH-22` | execution order: metrics before debate, brief before five roles, no post-decision brief | not started |
| `T-ARCH-23` | publication order: permanent snapshot before commit, recovery snapshot before memory, cleanup last | not started |
| `T-ARCH-24` | memory allocation high-water over all historical allocations including failed; retry reuse; failed-version gap; new-run higher version | not started |
| `T-ARCH-25` | shared run lock/fencing critical section; normal publisher vs recovery | not started |
| `T-ARCH-26` | post-commit corruption immutability and independent diagnostic | not started |
| `T-ARCH-27` | risk single caller/applicability once; provisional vs approved policy distinction | not started |
| `T-ARCH-28` | SEC adapter boundary: no direct vendor, shared cache/counters/provenance | not started |
| `T-ARCH-29` | brief replacement mapping/protected markers/no full+brief duplication | not started |
| `T-ARCH-30` | Portfolio Manager remains terminal; model_proposal source/fields; no Trader/risk-debater promotion | not started |
| `T-ARCH-31` | recovery snapshot cleanup vs permanent publication read dependency; `recovery_snapshot_summary` audit-only | not started |
| `T-ARCH-32` | brief failure state machine: `BRIEF_DISABLED`/`BRIEF_FULL_REPORT`/`BRIEF_REJECTED`; no post-rejection bypass | not started |
| `T-ARCH-33` | uncommitted same-decision coordination: `MEMORY_PENDING_RETRYABLE`/`MEMORY_RECOVERY_UNAVAILABLE`/`MEMORY_RECOVERY_FAILED`/`MEMORY_CONFLICT`; original identity/reservation/snapshot | not started |
| `T-ARCH-34` | OS file lock vs logical lease: short critical section, LOCK_BUSY, takeover/fencing, old-owner rejection | not started |
| `T-ARCH-35` | SEC structured query contract; disclosure fields preserved; canonical fields derived with rule/version/evidence; per-fact period identity; unavailable/ambiguous, no guessing | not started |
| `T-ARCH-36` | permanent/publication vs temporary/recovery layout and reference confinement | not started |
| `T-ARCH-37` | lock/lease record state transitions and run/memory lock order | not started |
| `T-ARCH-38` | memory allocation high-water mark includes failed reservations; new/retry version behavior | not started |
| `T-ARCH-39` | permanent hash DAG: binding no terminal hash, no cycles, declared computation order | not started |
| `T-ARCH-40` | ledger reserved/failed/committed timing and commit-projection repair | not started |
| `T-ARCH-41` | `record_hash` field-level projection excludes `artifact_binding.record_hash` and other result-carrying fields | not started |
| `T-ARCH-42` | canonical digest vs file-byte hash; retry stability; risk/provenance timestamps preserved; actual file hash verified | not started |
| `T-ARCH-43` | recovery terminal-first check: committed+verified+identity match -> idempotent success without `recovery/` | not started |
| `T-ARCH-44` | committed identity conflict/corrupt permanent artifacts -> typed result; no overwrite/republish | not started |

---

## 5. Planned runtime monitor inventory

Each `MON-*` ID corresponds to the acceptance criterion with the same number. All monitors are **not implemented**.

| Monitor family | Signals |
|---|---|
| `MON-FR01-*` | duplicate query executions; concurrent duplicates; terminal outcome reuse; run/vendor cache hits; retry/fallback counters; business-field diff; live quality/safety delta |
| `MON-FR02-*` | manifest count/path/schema; failed terminal record; running-record integrity; duplicate/orphan manifest; counter reconciliation; token-usage gaps; phase timing; corrupt/partial manifest; invalid completed record; identity conflict; section/formal label mismatch; snapshot/commit separation; mixed/stale sections |
| `MON-FR03-*` | status/decision mismatch; record/source mismatch; profile drift; invalid fallback; aggregation mismatch; hidden/leaked gap; missing-record mismatch; consumer/order divergence; consumer gap mismatch; aggregation rule violation |
| `MON-FR04-*` | boundary/digest mismatch; position/stop escape; reason-order mismatch; invalid-input default approval; not-applicable-as-pass; forbidden dependency call; deterministic mismatch; policy default approval; risk evidence mismatch; cache/risk misclassification |
| `MON-FR05-*` | filter/order mismatch; partial/corrupt retrieval; foreign/stale section; export conflict/path escape |
| `MON-FR06-*` | forbidden dependency call; false successful publication; lost-lease/duplicate publication; status confusion; duplicate publication; extra/duplicate memory entry |
| `MON-FR07-*` | formula/value mismatch; substituted input; silent merge/look-ahead; fiscal-position mismatch; span/sign mismatch; look-ahead/default; direct vendor call; missing/metric mismatch; wrong number authoritative; reference/hash mismatch; refetch/model/graph call |
| `MON-FR08-*` | marker/budget/forgery failure; mandatory drop; full-artifact mutation; safety escape/quality loss; unmeasured saving claim |
| `MON-QR02-*` | p95/failure samples; skipped validation/model-free violation |
| `MON-SB01-*` | blocked formal rating/text; pass/unchanged; model-review mishandling; coverage/gap mismatch; invalid gate input; snapshot trust/hash; unapproved proposal leak; gate bypass; silent pass; gate-result mismatch; risk bypass/masked failure; wrong primary/review class |
| `MON-INV01-*` | binding mismatch; false/missed mismatch; provenance mismatch; silent substitution; decision/digest mismatch; missing artifact; partial/duplicate publish; memory lifecycle mismatch; checkpoint/tamper failure; memory rerun/disabled mismatch; missing/foreign section; false committed result |
| `MON-INV02-*` | unsafe/default/not-applicable approval; deterministic mismatch; forbidden dependency call; cross-artifact mismatch; second memory identity; risk masking/not-applicable pass; cache/risk misclassification |
| `MON-SR01-*` | known-secret match; pattern/rule-version mismatch; inline secret in preferences; scanner failure treated as pass; over-redaction; scope/version gap; existing-control regression; out-of-root write; overwritten target/legacy change |

---

## 6. Coverage statement

- All 13 D1 requirements are represented.
- All 111 acceptance criteria are represented with a component, planned test, and planned monitor.
- No test or monitor has been implemented or executed.
- 6 requirements are approved; 7 are draft.
- D1 v1.14.1 is the current registry; human review is pending.
- Requirements evidence reproducibility is currently blocked by the absent `yhx/requirements.yaml` and undeclared validator dependencies; see `docs/architecture/open-decisions.md` ARCH-OD-01/02.
- Approval-scope coupling remains open: approved `SB-01` references the draft `FR-04` risk branch, and approved `FR-02`/`INV-01` reference draft recovery/section/metric/brief behavior. Approved obligations (FR-02 recovery-snapshot generation/section manifest/terminal manifest/binding; INV-01 binding/read-time verification; SB-01 risk branch) remain required and are not downgraded by draft status. Draft status limits completion/acceptance claims; see ARCH-OD-13/14.
- The scenario tests `T-SCEN-01`..`T-SCEN-18` cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, and committed-publication corruption. They are planned, not executed.
