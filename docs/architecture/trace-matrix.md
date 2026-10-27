# D2 Trace Matrix

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` (working baseline; not finally approved)  
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
| `PR-01` | `DataAccessService`, `RunEvidenceStore` | `RunContext`, `FinalizedRunRecord` | OQ-04, OQ-08, D2-OD-03 |
| `QR-01` | `ArtifactPublisher`, `RunEvidenceStore` | `RunContext`, `SecretRedactor` | OQ-02, OQ-05, D2-OD-02 |
| `FR-02` | `AvailabilityIndex`, `RunEvidenceStore` | `DataAccessService`, `SafetyGate` | OQ-01, D2-OD-04 |
| `SB-01` | `SafetyGate`, `FinalizedRunRecord` | `ArtifactPublisher`, `MemoryService` | OQ-06, D2-OD-01, D2-OD-02 |
| `INV-02` | `FinalizedRunRecord`, `ArtifactPublisher` | `MemoryService`, all formal writers | D2-OD-01, D2-OD-02, D2-OD-06 |
| `SR-02` | `SecretRedactor` | all output boundaries | OQ-03, OQ-07, D2-OD-07, D2-OD-08 |

---

## 3. Acceptance-criterion trace

### 3.1 PR-01 — Run-scoped data-query reuse

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `PR-01-AC1` | `DataAccessService` single-flight + run cache | `T-PR01-01` | `MON-PR01-01` duplicate physical requests | design only; test not started; monitor not implemented |
| `PR-01-AC2` | terminal failure cache; status/reason reuse | `T-PR01-02` | `MON-PR01-02` terminal failure reuse | design only; test not started; monitor not implemented |
| `PR-01-AC3` | run isolation; no cross-run run-cache reuse | `T-PR01-03` | `MON-PR01-03` cross-run cache reuse | design only; test not started; monitor not implemented |
| `PR-01-AC4` | cache does not change semantic output | `T-PR01-04` | `MON-PR01-04` report/manifest diff | design only; test not started; monitor not implemented |

**Trace**: `DataAccessService` (blueprint §7), `RunEvidenceStore` (blueprint §4, §7), invariant `INV-A-05`, `INV-A-06`.

---

### 3.2 QR-01 — Lean run manifest

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `QR-01-AC1` | `ArtifactPublisher` writes one manifest per run | `T-QR01-01` | `MON-QR01-01` manifest count/schema | design only; test not started; monitor not implemented |
| `QR-01-AC2` | manifest schema fields | `T-QR01-02` | `MON-QR01-02` required-field presence | design only; test not started; monitor not implemented |
| `QR-01-AC3` | manifest values reconcile with callbacks and availability | `T-QR01-03` | `MON-QR01-03` count/token/status mismatch | design only; test not started; monitor not implemented |
| `QR-01-AC4` | manifest write overhead | `T-QR01-04` | `MON-QR01-04` publish/manifest duration | design only; test not started; threshold provisional |

**Trace**: `ArtifactPublisher` (blueprint §9), `RunEvidenceStore` (blueprint §4), invariant `INV-A-07`.

---

### 3.3 FR-02 — Unified availability and critical gaps

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `FR-02-AC1` | `AvailabilityIndex` records failed critical source and report gap | `T-FR02-01` | `MON-FR02-01` coverage/gap mismatch | design only; test not started; monitor not implemented |
| `FR-02-AC2` | coverage partial; one gap; report section | `T-FR02-02` | `MON-FR02-02` coverage status | design only; test not started; monitor not implemented |
| `FR-02-AC3` | complete when all critical sources succeed | `T-FR02-03` | `MON-FR02-03` false gap detection | design only; test not started; monitor not implemented |
| `FR-02-AC4` | configured critical set respected | `T-FR02-04` | `MON-FR02-04` active critical set | design only; test not started; monitor not implemented |

**Trace**: `AvailabilityIndex` (blueprint §6), `DataAccessService` (blueprint §6–7), invariant `INV-A-04`.

---

### 3.4 SB-01 — Deterministic final-output gate

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `SB-01-AC1` | critical gap → REVIEW across artifacts | `T-SB01-01` | `MON-SB01-01` final rating/gate result | design only; test not started; monitor not implemented |
| `SB-01-AC2` | no gap + valid rating unchanged | `T-SB01-02` | `MON-SB01-02` gate pass/unchanged | design only; test not started; monitor not implemented |
| `SB-01-AC3` | missing/invalid rating or coverage → REVIEW | `T-SB01-03` | `MON-SB01-03` invalid-output rejection | design only; test not started; monitor not implemented |
| `SB-01-AC4` | gate result present in manifest | `T-SB01-04` | `MON-SB01-04` missing gate result | design only; test not started; monitor not implemented |

**Trace**: `SafetyGate` and `FinalizedRunRecord` (blueprint §8), invariants `INV-A-02`, `INV-A-03`.

---

### 3.5 INV-02 — Consistent provenance and final decision

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `INV-02-AC1` | four-artifact source/provenance consistency | `T-INV02-01` | `MON-INV02-01` artifact mismatch | design only; test not started; monitor not implemented |
| `INV-02-AC2` | fallback provenance in all artifacts | `T-INV02-02` | `MON-INV02-02` fallback label mismatch | design only; test not started; monitor not implemented |
| `INV-02-AC3` | final rating/decision identical | `T-INV02-03` | `MON-INV02-03` rating/decision mismatch | design only; test not started; monitor not implemented |
| `INV-02-AC4` | missing artifact fails invariant | `T-INV02-04` | `MON-INV02-04` missing artifact | design only; test not started; monitor not implemented |

**Trace**: `FinalizedRunRecord` and `ArtifactPublisher` (blueprint §8–9), `MemoryService` (blueprint §9), invariants `INV-A-01`, `INV-A-02`, `INV-A-07`, `INV-A-08`.

---

### 3.6 SR-02 — Secret-free run records

| AC ID | Design element | Planned test | Runtime monitor | Status |
|---|---|---|---|---|
| `SR-02-AC1` | endpoint sanitization; zero secret matches | `T-SR02-01` | `MON-SR02-01` secret pattern match | design only; test not started; monitor not implemented |
| `SR-02-AC2` | prefs contain no userinfo/query/fragment | `T-SR02-02` | `MON-SR02-02` prefs URL scan | design only; test not started; monitor not implemented |
| `SR-02-AC3` | `.env` mode 0600 | `T-SR02-03` | `MON-SR02-03` file mode check | design only; test not started; monitor not implemented |
| `SR-02-AC4` | secret fixture redaction across boundaries | `T-SR02-04` | `MON-SR02-04` boundary scan | design only; test not started; monitor not implemented |

**Trace**: `SecretRedactor` and permission model (blueprint §13–14), invariant `INV-A-09`.

---

## 4. Planned test inventory

| Test ID | Purpose | Status |
|---|---|---|
| `T-PR01-01` | duplicate logical query → one physical request | not started |
| `T-PR01-02` | terminal failure reuse | not started |
| `T-PR01-03` | cross-run isolation | not started |
| `T-PR01-04` | cache/no-cache semantic diff | not started |
| `T-QR01-01` | one manifest per run | not started |
| `T-QR01-02` | manifest schema/fields | not started |
| `T-QR01-03` | manifest reconciliation | not started |
| `T-QR01-04` | manifest overhead benchmark | not started |
| `T-FR02-01` | critical source gap propagation | not started |
| `T-FR02-02` | coverage partial and report section | not started |
| `T-FR02-03` | complete coverage | not started |
| `T-FR02-04` | configurable critical set | not started |
| `T-SB01-01` | critical gap → REVIEW | not started |
| `T-SB01-02` | no gap → unchanged | not started |
| `T-SB01-03` | malformed output → REVIEW | not started |
| `T-SB01-04` | gate result in manifest | not started |
| `T-INV02-01` | four-artifact consistency | not started |
| `T-INV02-02` | fallback provenance consistency | not started |
| `T-INV02-03` | rating/decision equality | not started |
| `T-INV02-04` | missing artifact failure | not started |
| `T-SR02-01` | endpoint and record secret scan | not started |
| `T-SR02-02` | preferences URL scan | not started |
| `T-SR02-03` | `.env` mode | not started |
| `T-SR02-04` | boundary redaction fixture | not started |

Additional architecture tests:

| Test ID | Purpose | Status |
|---|---|---|
| `T-ARCH-01` | writer bypass audit | not started |
| `T-ARCH-02` | publish failure/retry | not started |
| `T-ARCH-03` | memory idempotency/conflict | not started |
| `T-ARCH-04` | checkpoint resume matrix | not started |
| `T-ARCH-05` | context compression/re-injection | not started |
| `T-ARCH-06` | runtime AI permission boundary | not started |
| `T-ARCH-07` | coding agent permission matrix | not started |

---

## 5. Runtime monitor inventory

| Monitor ID | Signal | Status |
|---|---|---|
| `MON-PR01-01` | duplicate physical requests per query key | not implemented |
| `MON-PR01-02` | terminal failure reuse count | not implemented |
| `MON-PR01-03` | cross-run run-cache reuse | not implemented |
| `MON-PR01-04` | report/manifest semantic diff | not implemented |
| `MON-QR01-01` | manifest count/schema | not implemented |
| `MON-QR01-02` | missing manifest fields | not implemented |
| `MON-QR01-03` | count/token/status mismatch | not implemented |
| `MON-QR01-04` | manifest write duration | not implemented |
| `MON-FR02-01` | coverage/gap mismatch | not implemented |
| `MON-FR02-02` | coverage status distribution | not implemented |
| `MON-FR02-03` | false gap/completeness | not implemented |
| `MON-FR02-04` | active critical set | not implemented |
| `MON-SB01-01` | gate result/rating | not implemented |
| `MON-SB01-02` | gate pass/unchanged | not implemented |
| `MON-SB01-03` | invalid-output rejection | not implemented |
| `MON-SB01-04` | missing gate result | not implemented |
| `MON-INV02-01` | artifact mismatch | not implemented |
| `MON-INV02-02` | fallback label mismatch | not implemented |
| `MON-INV02-03` | rating/decision mismatch | not implemented |
| `MON-INV02-04` | missing artifact | not implemented |
| `MON-SR02-01` | secret pattern match | not implemented |
| `MON-SR02-02` | prefs URL scan | not implemented |
| `MON-SR02-03` | `.env` mode | not implemented |
| `MON-SR02-04` | boundary scan | not implemented |

---

## 6. Coverage statement

- All 6 D1 requirements are represented.
- All 24 D1 acceptance criteria are represented.
- Each criterion has a planned test and a runtime monitor.
- No test or monitor has been implemented or executed.
- D1 has not been modified; D1 conflicts are listed in `docs/architecture/open-decisions.md`.
