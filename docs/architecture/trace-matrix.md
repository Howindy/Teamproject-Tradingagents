# D2 Trace Matrix

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` v1.9.0 (historical baseline approved; current revision human review pending; IDs renumbered)
Implementation status: **design only; no application code changed**

---

## 1. Purpose

This matrix traces every D1 acceptance criterion to:

- the D2 component that is expected to satisfy it;
- a planned test ID;
- a runtime monitor ID;
- the current implementation/test status.

Status values are intentionally conservative:

- **design only** — no application code exists for this requirement;
- **not started** — the planned test/monitor has not been implemented;
- **not measured** — no performance/cost benefit has been measured.

Only the baseline facts under `baseline/runs/baseline-20261020-01/` are measured evidence.

---

## 2. Requirement-to-component summary

| Requirement | Primary components | Secondary components | Open decisions |
|---|---|---|---|
| `FR-01` | `DataAccessService`, `RunEvidenceStore` | `RunContext`, `FinalizedRunRecord` | OQ-04 resolved; OQ-08, D2-OD-03 |
| `FR-02` | `ArtifactPublisher`, `RunEvidenceStore` | `RunContext`, `SecretRedactor` | OQ-02/OQ-05 non-blocking; D2-OD-02 |
| `FR-03` | `AvailabilityIndex`, `RunEvidenceStore` | `DataAccessService`, `SafetyGate` | OQ-01 and D2-OD-04 resolved |
| `SB-01` | `SafetyGate`, `FinalizedRunRecord` | `ArtifactPublisher`, `MemoryService` | OQ-06 resolved; D2-OD-01, D2-OD-02 |
| `INV-01` | `FinalizedRunRecord`, `ArtifactPublisher` | `MemoryService`, all formal writers | D2-OD-01, D2-OD-02, D2-OD-06 |
| `SR-01` | `SecretRedactor` | all app-controlled output boundaries | OQ-03 and OQ-07 resolved; D2-OD-07, D2-OD-08 |

---

## 3. Acceptance-criterion trace

### 3.1 FR-01 — Single execution per identical logical data query

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `FR-01-AC1` | sequential callers; one query_execution per logical_query | `T-FR01-01` | `MON-FR01-01` duplicate query executions | design only; test not started; monitor not implemented |
| `FR-01-AC2` | concurrent single-flight join | `T-FR01-02` | `MON-FR01-02` concurrent duplicate executions | design only; test not started; monitor not implemented |
| `FR-01-AC3` | terminal failure cache; status/reason/provenance reuse | `T-FR01-03` | `MON-FR01-03` terminal failure reuse | design only; test not started; monitor not implemented |
| `FR-01-AC4` | run isolation versus cross-run vendor-cache hits | `T-FR01-04` | `MON-FR01-04` run-cache reuse and vendor-cache hits | design only; test not started; monitor not implemented |
| `FR-01-AC5` | retry and fallback budgets inside one execution | `T-FR01-05` | `MON-FR01-05` retry/fallback counters | design only; test not started; monitor not implemented |
| `FR-01-AC6` | business-conclusion equivalence; execution metadata compared separately | `T-FR01-06` | `MON-FR01-06` business/execution diff | design only; test not started; monitor not implemented |
| `FR-01-AC7` | frozen live A/B: eval set, rubric, safety/coverage and quality thresholds | `T-FR01-07` | `MON-FR01-07` live quality/safety delta | design only; test not started; monitor not implemented; thresholds frozen |

**Trace**: `DataAccessService` (blueprint §7), `RunEvidenceStore` (blueprint §4, §7), invariant `INV-A-05`, `INV-A-06`.

---

### 3.2 FR-02 — Lifecycle-complete run manifest

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `FR-02-AC1` | completed run writes one manifest at `<results_dir>/<run_id>/run_manifest.json` | `T-FR02-01` | `MON-FR02-01` manifest count/path/schema | design only; test not started; monitor not implemented |
| `FR-02-AC2` | handled failure writes terminal failed manifest | `T-FR02-02` | `MON-FR02-02` failed terminal record | design only; test not started; monitor not implemented |
| `FR-02-AC3` | forced termination preserves the running manifest | `T-FR02-03` | `MON-FR02-03` running-record integrity | design only; test not started; monitor not implemented |
| `FR-02-AC4` | run identity, path, parent linkage, and uniqueness | `T-FR02-04` | `MON-FR02-04` duplicate/orphan manifest | design only; test not started; monitor not implemented |
| `FR-02-AC5` | manifest schema, critical profile, coverage snapshot, hashes, config allowlist | `T-FR02-05` | `MON-FR02-05` schema/field validation | design only; test not started; monitor not implemented |
| `FR-02-AC6` | counter boundary against fixture ground truth | `T-FR02-06` | `MON-FR02-06` counter reconciliation | design only; test not started; monitor not implemented |
| `FR-02-AC7` | complete/partial/unavailable token usage | `T-FR02-07` | `MON-FR02-07` missing-usage count | design only; test not started; monitor not implemented |
| `FR-02-AC8` | end-to-end timing and manifest write overhead | `T-FR02-08` | `MON-FR02-08` phase and overhead duration | design only; test not started; thresholds provisional |
| `FR-02-AC9` | write failure and final-path integrity | `T-FR02-09` | `MON-FR02-09` corrupt/partial manifest | design only; test not started; monitor not implemented |
| `FR-02-AC10` | completed-state counterexamples rejected | `T-FR02-10` | `MON-FR02-10` invalid completed record | design only; test not started; monitor not implemented |

**Trace**: `ArtifactPublisher` (blueprint §9), `RunEvidenceStore` (blueprint §4), invariant `INV-A-07`.

---

### 3.3 FR-03 — Canonical availability and critical-gap decision table

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `FR-03-AC1` | closed record statuses and evidence contract | `T-FR03-01` | `MON-FR03-01` status/decision-table mismatch | design only; test not started; monitor not implemented |
| `FR-03-AC2` | record identity, supports links, source identity, and aggregation levels | `T-FR03-02` | `MON-FR03-02` record/source/aggregation mismatch | design only; test not started; monitor not implemented |
| `FR-03-AC3` | effective critical profile defaults and overrides | `T-FR03-03` | `MON-FR03-03` profile drift | design only; test not started; monitor not implemented |
| `FR-03-AC4` | fallback gap clearing under the same contract | `T-FR03-04` | `MON-FR03-04` invalid fallback clearing | design only; test not started; monitor not implemented |
| `FR-03-AC5` | all/any/min:N multi-query aggregation | `T-FR03-05` | `MON-FR03-05` aggregation mismatch | design only; test not started; monitor not implemented |
| `FR-03-AC6` | critical-gap versus non-critical-limitation reporting | `T-FR03-06` | `MON-FR03-06` hidden/leaked gap | design only; test not started; monitor not implemented |
| `FR-03-AC7` | component_missing record versus excluded capability | `T-FR03-07` | `MON-FR03-07` missing-record/attempt mismatch | design only; test not started; monitor not implemented |
| `FR-03-AC8` | canonical state and deterministic consumers | `T-FR03-08` | `MON-FR03-08` consumer/order divergence | design only; test not started; monitor not implemented |
| `FR-03-AC9` | final decision consumes the same canonical state | `T-FR03-09` | `MON-FR03-09` consumer gap mismatch | design only; test not started; monitor not implemented |
| `FR-03-AC10` | query-set all/any/min:N, empty-set, missing-component, and invalid-profile rules | `T-FR03-10` | `MON-FR03-10` aggregation rule violation | design only; test not started; monitor not implemented |

**Trace**: `AvailabilityIndex` (blueprint §6), `DataAccessService` (blueprint §6–7), invariant `INV-A-04`.

---

### 3.4 SB-01 — Deterministic fail-closed final-output gate

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `SB-01-AC1` | five legal ratings under a critical gap → REVIEW and formal review notice | `T-SB01-01` | `MON-SB01-01` blocked formal rating/text | design only; test not started; monitor not implemented |
| `SB-01-AC2` | five legal ratings with complete coverage → passed unchanged | `T-SB01-02` | `MON-SB01-02` gate pass/unchanged | design only; test not started; monitor not implemented |
| `SB-01-AC3` | model-returned REVIEW semantics | `T-SB01-03` | `MON-SB01-03` model-review case | design only; test not started; monitor not implemented |
| `SB-01-AC4` | complete+non-empty and partial+empty contradictions | `T-SB01-04` | `MON-SB01-04` coverage/gap mismatch | design only; test not started; monitor not implemented |
| `SB-01-AC5` | malformed/missing inputs and invalid profile | `T-SB01-05` | `MON-SB01-05` invalid gate input | design only; test not started; monitor not implemented |
| `SB-01-AC6` | trusted snapshot versus forged model fields | `T-SB01-06` | `MON-SB01-06` snapshot trust/hash | design only; test not started; monitor not implemented |
| `SB-01-AC7` | formal versus intermediate output separation | `T-SB01-07` | `MON-SB01-07` unapproved proposal leak | design only; test not started; monitor not implemented |
| `SB-01-AC8` | all entry points use the gate | `T-SB01-08` | `MON-SB01-08` gate bypass | design only; test not started; monitor not implemented |
| `SB-01-AC9` | gate self-failure fails closed | `T-SB01-09` | `MON-SB01-09` gate error/run failure | design only; test not started; monitor not implemented |
| `SB-01-AC10` | gate result, primary reason, review class, and consumer consistency | `T-SB01-10` | `MON-SB01-10` gate-result mismatch | design only; test not started; monitor not implemented |

**Trace**: `SafetyGate` and `FinalizedRunRecord` (blueprint §8), invariants `INV-A-02`, `INV-A-03`.

---

### 3.5 INV-01 — Bound formal result across current artifacts and memory reference

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `INV-01-AC1` | current-run artifact contract, decision_id binding, and reused-memory reference | `T-INV01-01` | `MON-INV01-01` binding mismatch | design only; test not started; monitor not implemented |
| `INV-01-AC2` | per-field canonicalization, attempt order, evidence timestamps | `T-INV01-02` | `MON-INV01-02` false/missed mismatch | design only; test not started; monitor not implemented |
| `INV-01-AC3` | executed versus component_missing identity; provenance digest | `T-INV01-03` | `MON-INV01-03` provenance mismatch | design only; test not started; monitor not implemented |
| `INV-01-AC4` | legal fallback versus silent substitution | `T-INV01-04` | `MON-INV01-04` silent substitution | design only; test not started; monitor not implemented |
| `INV-01-AC5` | decision equality scope | `T-INV01-05` | `MON-INV01-05` decision/digest mismatch | design only; test not started; monitor not implemented |
| `INV-01-AC6` | missing/empty artifact negative cases | `T-INV01-06` | `MON-INV01-06` missing artifact | design only; test not started; monitor not implemented |
| `INV-01-AC7` | partial write, crash, and retry identity | `T-INV01-07` | `MON-INV01-07` partial/duplicate publish | design only; test not started; monitor not implemented |
| `INV-01-AC8` | memory_entry_binding, legal settlement/rotation, illegal deletion | `T-INV01-08` | `MON-INV01-08` memory lifecycle mismatch | design only; test not started; monitor not implemented |
| `INV-01-AC9` | invariant checkpoints and read-time tamper | `T-INV01-09` | `MON-INV01-09` checkpoint/tamper failure | design only; test not started; monitor not implemented |
| `INV-01-AC10` | same-day rerun, memory-disabled, and entry dedup | `T-INV01-10` | `MON-INV01-10` memory rerun/disabled mismatch | design only; test not started; monitor not implemented |

**Trace**: `FinalizedRunRecord` and `ArtifactPublisher` (blueprint §8–9), `MemoryService` (blueprint §9), invariants `INV-A-01`, `INV-A-02`, `INV-A-07`, `INV-A-08`.

---

### 3.6 SR-01 — Secret-safe run records

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `SR-01-AC1` | known-secret exact match and write-scan across in-scope writers | `T-SR01-01` | `MON-SR01-01` known-secret match | design only; test not started; monitor not implemented |
| `SR-01-AC2` | versioned pattern categories and redaction/block | `T-SR01-02` | `MON-SR01-02` pattern match/rule version | design only; test not started; monitor not implemented |
| `SR-01-AC3` | preference audit/restore endpoint split | `T-SR01-03` | `MON-SR01-03` inline secret in prefs | design only; test not started; monitor not implemented |
| `SR-01-AC4` | fail-closed dangerous-output block and minimal incident record | `T-SR01-04` | `MON-SR01-04` scanner failure/leak | design only; test not started; monitor not implemented |
| `SR-01-AC5` | over-redaction avoidance | `T-SR01-05` | `MON-SR01-05` over-redaction | design only; test not started; monitor not implemented |
| `SR-01-AC6` | scan scope, version, and limitation | `T-SR01-06` | `MON-SR01-06` scope/version gap | design only; test not started; monitor not implemented |
| `SR-01-AC7` | existing scrub and .env controls preserved | `T-SR01-07` | `MON-SR01-07` existing-control regression | design only; test not started; monitor not implemented |

**Trace**: `SecretRedactor` and permission model (blueprint §13–14), invariant `INV-A-09`.

---

## 4. Planned test inventory

| Test ID | Purpose | Status |
|---|---|---|
| `T-FR01-01` | sequential duplicate logical query → one query_execution | not started |
| `T-FR01-02` | concurrent duplicate logical query → single-flight | not started |
| `T-FR01-03` | terminal failure status/reason/provenance reuse | not started |
| `T-FR01-04` | run isolation versus vendor-cache hits | not started |
| `T-FR01-05` | retry and fallback budget separation | not started |
| `T-FR01-06` | offline cache/no-cache business-field diff | not started |
| `T-FR01-07` | frozen live A/B rubric and thresholds | not started |
| `T-FR02-01` | completed-run manifest path/identity/schema | not started |
| `T-FR02-02` | handled-failure terminal manifest | not started |
| `T-FR02-03` | forced-termination running manifest | not started |
| `T-FR02-04` | run-id/path/parent/resume uniqueness | not started |
| `T-FR02-05` | manifest schema and config allowlist | not started |
| `T-FR02-06` | counter ground-truth reconciliation | not started |
| `T-FR02-07` | missing and partial token usage | not started |
| `T-FR02-08` | end-to-end and manifest-write benchmark | not started |
| `T-FR02-09` | write-failure and integrity injection | not started |
| `T-FR02-10` | completed-state counterexamples | not started |
| `T-FR03-01` | closed record statuses and evidence contract | not started |
| `T-FR03-02` | source identity and record/aggregation levels | not started |
| `T-FR03-03` | effective critical profile defaults/overrides | not started |
| `T-FR03-04` | fallback gap clearing | not started |
| `T-FR03-05` | all/any/min:N aggregation | not started |
| `T-FR03-06` | critical-gap versus limitation reporting | not started |
| `T-FR03-07` | not-attempted versus excluded capability | not started |
| `T-FR03-08` | canonical state determinism | not started |
| `T-FR03-09` | final-decision state consumption | not started |
| `T-FR03-10` | query-set cardinality/threshold rules | not started |
| `T-SB01-01` | five-rating critical-gap matrix | not started |
| `T-SB01-02` | five-rating complete-coverage matrix | not started |
| `T-SB01-03` | model REVIEW semantics | not started |
| `T-SB01-04` | coverage/gap contradiction matrix | not started |
| `T-SB01-05` | malformed/missing input matrix | not started |
| `T-SB01-06` | trusted snapshot and forged fields | not started |
| `T-SB01-07` | formal/intermediate consumer audit | not started |
| `T-SB01-08` | entry-point gate matrix | not started |
| `T-SB01-09` | gate fault injection | not started |
| `T-SB01-10` | gate-result consistency | not started |
| `T-INV01-01` | artifact contract and binding equality | not started |
| `T-INV01-02` | canonicalization stability | not started |
| `T-INV01-03` | source-status/provenance granularity | not started |
| `T-INV01-04` | legal fallback versus silent substitution | not started |
| `T-INV01-05` | decision equality scope | not started |
| `T-INV01-06` | missing/empty artifact negatives | not started |
| `T-INV01-07` | partial write/crash/retry | not started |
| `T-INV01-08` | memory settlement/rotation | not started |
| `T-INV01-09` | invariant checkpoints and tamper | not started |
| `T-INV01-10` | same-day rerun and memory-disabled | not started |
| `T-SR01-01` | known-secret exact match | not started |
| `T-SR01-02` | versioned pattern rules | not started |
| `T-SR01-03` | preference audit/restore split | not started |
| `T-SR01-04` | scanner/redaction fail-closed | not started |
| `T-SR01-05` | over-redaction avoidance | not started |
| `T-SR01-06` | scan scope and rule version | not started |
| `T-SR01-07` | existing scrub/.env regression | not started |

Additional architecture tests:

| Test ID | Purpose | Status |
|---|---|---|
| `T-ARCH-01` | writer bypass audit | not started |
| `T-ARCH-02` | publish candidate check, unique commit point, read-back verification, retry | not started |
| `T-ARCH-03` | memory commit status, read filtering, reuse and conflict | not started |
| `T-ARCH-04` | checkpoint resume matrix | not started |
| `T-ARCH-05` | context compression/re-injection | not started |
| `T-ARCH-06` | runtime AI permission boundary | not started |
| `T-ARCH-07` | coding agent permission matrix | not started |
| `T-ARCH-08` | ADD driver/tactic trace audit | not started |
| `T-ARCH-09` | requirements validator and result-record reproducibility | implemented in docs/req/validate_requirements.py |
| `T-ARCH-10` | decision timing vs publish-metrics boundary | not started |
| `T-ARCH-11` | independent failed-run publication path | not started |
| `T-ARCH-12` | mandatory preflight timing, ownership, and shared cache | not started |
| `T-ARCH-13` | component module/interface/error contract audit | not started |
| `T-ARCH-14` | validation-result content hashes and stale detection | implemented in validator --check |
| `T-ARCH-15` | candidate comparison under identical safety contract | not started |
| `T-ARCH-16` | thin implementation slice for Lean A/B/C comparison | not started |

---

## 5. Runtime monitor inventory

| Monitor ID | Signal | Status |
|---|---|---|
| `MON-FR01-01` | duplicate query_executions per data_query_key | not implemented |
| `MON-FR01-02` | concurrent duplicate executions | not implemented |
| `MON-FR01-03` | terminal failure reuse count | not implemented |
| `MON-FR01-04` | run-cache reuse and vendor-cache hits | not implemented |
| `MON-FR01-05` | retry/fallback counters | not implemented |
| `MON-FR01-06` | business-field diff under fixed replay | not implemented |
| `MON-FR01-07` | live quality and safety delta | not implemented |
| `MON-FR02-01` | manifest count/path/schema | not implemented |
| `MON-FR02-02` | failed terminal record | not implemented |
| `MON-FR02-03` | running-record integrity | not implemented |
| `MON-FR02-04` | duplicate/orphan manifest | not implemented |
| `MON-FR02-05` | schema/field validation | not implemented |
| `MON-FR02-06` | counter reconciliation | not implemented |
| `MON-FR02-07` | missing-usage count | not implemented |
| `MON-FR02-08` | phase and overhead duration | not implemented |
| `MON-FR02-09` | corrupt/partial manifest | not implemented |
| `MON-FR02-10` | invalid completed record | not implemented |
| `MON-FR03-01` | status/decision-table mismatch | not implemented |
| `MON-FR03-02` | record/source/aggregation mismatch | not implemented |
| `MON-FR03-03` | profile drift | not implemented |
| `MON-FR03-04` | invalid fallback clearing | not implemented |
| `MON-FR03-05` | aggregation mismatch | not implemented |
| `MON-FR03-06` | hidden/leaked gap | not implemented |
| `MON-FR03-07` | criticality/attempt mismatch | not implemented |
| `MON-FR03-08` | consumer/order divergence | not implemented |
| `MON-FR03-09` | consumer gap mismatch | not implemented |
| `MON-FR03-10` | aggregation rule violation | not implemented |
| `MON-SB01-01` | blocked formal rating/text | not implemented |
| `MON-SB01-02` | gate pass/unchanged | not implemented |
| `MON-SB01-03` | model-review case | not implemented |
| `MON-SB01-04` | coverage/gap mismatch | not implemented |
| `MON-SB01-05` | invalid gate input | not implemented |
| `MON-SB01-06` | snapshot trust/hash | not implemented |
| `MON-SB01-07` | unapproved proposal leak | not implemented |
| `MON-SB01-08` | gate bypass | not implemented |
| `MON-SB01-09` | gate error/run failure | not implemented |
| `MON-SB01-10` | gate-result mismatch | not implemented |
| `MON-INV01-01` | binding mismatch | not implemented |
| `MON-INV01-02` | false/missed mismatch | not implemented |
| `MON-INV01-03` | provenance mismatch | not implemented |
| `MON-INV01-04` | silent substitution | not implemented |
| `MON-INV01-05` | decision/digest mismatch | not implemented |
| `MON-INV01-06` | missing artifact | not implemented |
| `MON-INV01-07` | partial/duplicate publish | not implemented |
| `MON-INV01-08` | memory lifecycle mismatch | not implemented |
| `MON-INV01-09` | checkpoint/tamper failure | not implemented |
| `MON-INV01-10` | memory rerun/disabled mismatch | not implemented |
| `MON-SR01-01` | known-secret match | not implemented |
| `MON-SR01-02` | pattern match/rule version | not implemented |
| `MON-SR01-03` | inline secret in prefs | not implemented |
| `MON-SR01-04` | scanner failure/leak | not implemented |
| `MON-SR01-05` | over-redaction | not implemented |
| `MON-SR01-06` | scope/version gap | not implemented |
| `MON-SR01-07` | existing-control regression | not implemented |

---

## 6. Coverage statement

- All 6 D1 requirements are represented.
- All 54 D1 acceptance criteria are represented.
- Each criterion has a planned test and a runtime monitor.
- No test or monitor has been implemented or executed.
- D1 v1.9.0 is the approved historical baseline; the current revision is pending human review. Resolved conflicts and remaining non-blocking decisions are in `docs/architecture/open-decisions.md`.
