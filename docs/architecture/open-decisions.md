# D2 Open Decisions

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` (working baseline; not finally approved)  
Implementation status: **design only; no application code changed**

This file records decisions that are **not closed**. Recommendations are for discussion only; they are not approvals.

---

## 1. Decision status legend

- **open** — no decision.
- **recommended, not approved** — a recommendation exists; the team must decide.
- **blocking** — implementation cannot start safely without it.
- **non-blocking** — can proceed with a work assumption, but the assumption must be recorded.

---

## 2. D1 open questions

### OQ-01 — Critical-source set

- **Status**: open; blocking.
- **Question**: which sources are critical for coverage and gate?
- **Options**:
  1. Fixed set in code.
  2. Per-source configuration.
  3. Per-category configuration.
  4. Include optional enrichment (FRED, prediction markets) as critical.
- **Recommendation (not approved)**: per-source configuration; default ticker news, fundamentals statements, and social sentiment; FRED and prediction markets optional.
- **Impact**: `AvailabilityIndex`, `SafetyGate`, report gaps, tests, evaluation.
- **Related requirements**: FR-02, SB-01.
- **Blocking phase**: D2 review / before D3 implementation.
- **D1 change suggestion**: add the default critical-source set and `not_attempted` semantics to D1 FR-02 or an appendix.

### OQ-02 — Manifest location and retention

- **Status**: open; non-blocking.
- **Question**: where is the manifest stored, and how long is it retained?
- **Options**:
  1. Run results directory only.
  2. Results plus a global manifest index.
  3. Retention window with rotation.
- **Recommendation (not approved)**: per-run manifest in the run's results directory; no automatic deletion in D2; retention policy later.
- **Impact**: `ArtifactPublisher`, results layout, audit.
- **Related requirements**: QR-01.
- **Blocking phase**: D3 implementation detail.
- **D1 change suggestion**: none required for D2; retention may be added later.

### OQ-03 — Secret-pattern list

- **Status**: open; blocking.
- **Question**: which patterns are authoritative for SR-02?
- **Options**:
  1. Generic key/token/password patterns.
  2. Provider-specific patterns.
  3. Both, plus URL query/userinfo detection.
- **Recommendation (not approved)**: both generic and provider-specific patterns; document the list in the policy catalog.
- **Impact**: `SecretRedactor`, tests, all output boundaries.
- **Related requirements**: SR-02.
- **Blocking phase**: D2 review / before D3 security tests.
- **D1 change suggestion**: add the required pattern categories to SR-02 acceptance or an appendix.

### OQ-04 — `data_query_key` normalization and vendor cache semantics

- **Status**: open; blocking.
- **Question**: what exactly does a query key include, and how do run cache and existing vendor cache interact?
- **Options**:
  1. method + ticker + dates/window + indicator/lookback + asset type.
  2. Include vendor chain/config digest.
  3. Include policy/cache-key version.
  4. Run cache only; vendor cache separate.
- **Recommendation (not approved)**: include method, normalized ticker, analysis date, window, indicator/lookback, asset type, and cache-key version; record vendor cache hits separately; run cache never shared across runs.
- **Impact**: `DataAccessService`, PR-01 tests, evidence counters.
- **Related requirements**: PR-01.
- **Blocking phase**: D2 review / before D3 implementation.
- **D1 change suggestion**: **PR-01-AC3** should distinguish run-cache reuse from vendor-cache reads. Suggested wording: “cross-run run-cache reuse = 0; vendor-cache reads may serve a request and are recorded as `vendor_cache_hits`.” This avoids requiring a bypass of the existing vendor cache.

### OQ-05 — Manifest overhead target

- **Status**: open; non-blocking.
- **Question**: is ≤1 second per run the right QR-01 overhead target?
- **Options**:
  1. Accept 1s.
  2. Set a lower target after benchmark.
  3. Measure only, no hard target in D2.
- **Recommendation (not approved)**: benchmark first; keep 1s as provisional.
- **Impact**: QR-01-AC4, publisher design.
- **Related requirements**: QR-01.
- **Blocking phase**: D3 benchmark.
- **D1 change suggestion**: mark QR-01-AC4 as provisional until measured.

### OQ-06 — REVIEW acceptance and override

- **Status**: open; blocking.
- **Question**: is REVIEW acceptable as the terminal state, and is there any override?
- **Options**:
  1. REVIEW, no override.
  2. REVIEW, explicit operator override with audit.
  3. REVIEW only for certain critical sources.
- **Recommendation (not approved)**: REVIEW, no model override; no operator override in D1; REVIEW persisted to memory but not scored as tradeable.
- **Impact**: `SafetyGate`, CLI, memory, backtest, user experience.
- **Related requirements**: SB-01.
- **Blocking phase**: D2 review / before D3 implementation.
- **D1 change suggestion**: add “no model override” and REVIEW persistence/scoring semantics to SB-01.

### OQ-07 — SR-02 scope

- **Status**: open; non-blocking.
- **Question**: does SR-02 cover only `.env` and run records, or also shell history/provider logs?
- **Options**:
  1. Run records only.
  2. Run records plus `.env` mode.
  3. Include host shell history/provider logs (out of app control).
- **Recommendation (not approved)**: app-controlled boundaries only; document host/provider logs as external.
- **Impact**: permission model, redaction tests, security scope.
- **Related requirements**: SR-02.
- **Blocking phase**: D2 review.
- **D1 change suggestion**: clarify the app-controlled boundary in SR-02.

### OQ-08 — Concurrent locking

- **Status**: open; non-blocking.
- **Question**: can concurrent runs share manifest/preference directories without a locking policy?
- **Options**:
  1. Per-run directories; no shared manifest.
  2. Shared manifest index with lock.
  3. Serialize all runs.
- **Recommendation (not approved)**: per-run directories; memory uses existing lock; no shared manifest index in D2.
- **Impact**: `ArtifactPublisher`, `MemoryService`, prefs, concurrency tests.
- **Related requirements**: PR-01, QR-01, INV-02.
- **Blocking phase**: D3 implementation.
- **D1 change suggestion**: none required for D2.

---

## 3. New D2 decisions

### D2-OD-01 — FinalizedRunRecord schema/version

- **Status**: open; blocking.
- **Question**: exact fields, canonicalization, hash algorithm, schema version.
- **Recommendation (not approved)**: versioned record with run identity, evidence snapshot, model proposals, final decision, coverage, gate result, artifact references, record hash; realized artifact hashes live in the publish manifest; canonical JSON; SHA-256.
- **Impact**: publisher, memory, manifest, trace, all tests.
- **Related requirements**: SB-01, INV-02, QR-01.
- **Blocking phase**: before D3.

### D2-OD-02 — Publish order, staging layout, complete marker

- **Status**: open; blocking.
- **Question**: artifact order, staging directory, complete marker, retry count.
- **Recommendation (not approved)**: record → report → final-state → memory → manifest → complete marker; 3 retries; no model re-run.
- **Impact**: `ArtifactPublisher`, `MemoryService`, tests.
- **Related requirements**: QR-01, INV-02.
- **Blocking phase**: before D3.

### D2-OD-03 — Checkpoint support matrix and degraded resume

- **Status**: open; blocking.
- **Question**: which state is resumable, and is degraded resume allowed?
- **Recommendation (not approved)**: support graph/journal state; refuse unsupported versions; degraded resume opt-in only with partial coverage and likely REVIEW.
- **Impact**: `CheckpointCoordinator`, evidence store, tests.
- **Related requirements**: D2 design, SB-01, INV-02.
- **Blocking phase**: before D3.

### D2-OD-04 — Fallback coverage contract and substitution

- **Status**: open; blocking.
- **Question**: which fallback classes can clear which gaps?
- **Recommendation (not approved)**: same-category fallback only by default; global news does not clear ticker-news gap unless explicitly configured.
- **Impact**: `DataAccessService`, `AvailabilityIndex`, gate.
- **Related requirements**: FR-02, SB-01.
- **Blocking phase**: before D3.

### D2-OD-05 — Token limits and compression thresholds

- **Status**: open; non-blocking for architecture, blocking for implementation.
- **Question**: exact per-call/evidence/history limits and compression strategy.
- **Recommendation (not approved)**: provisional values in `runtime-policy-catalog.md`; deterministic truncation first; no LLM summarizer by default.
- **Impact**: `ContextAssembler`, prompts, token cost, tests.
- **Related requirements**: QR-01, quality.
- **Blocking phase**: before D3 context implementation.

### D2-OD-06 — Memory structured sidecar vs Markdown metadata

- **Status**: open; blocking for memory implementation.
- **Question**: add JSONL sidecar, or keep structured metadata in Markdown?
- **Recommendation (not approved)**: sidecar if machine consistency is required; Markdown metadata line if minimal change is preferred.
- **Impact**: `MemoryService`, idempotency, INV-02 tests.
- **Related requirements**: INV-02, QR-01.
- **Blocking phase**: before D3 memory implementation.

### D2-OD-07 — Coding-agent role whitelist

- **Status**: open; non-blocking for D2 docs, blocking for implementation workflow.
- **Question**: approve the roles/paths in `permission-model.md`.
- **Recommendation (not approved)**: D2 architect writes docs only; future implementation/test roles require explicit approval.
- **Impact**: agent permissions, audit, workflow.
- **Related requirements**: D2 governance, SR-02.
- **Blocking phase**: before coding agents implement D3.

### D2-OD-08 — Runtime AI tool boundary and context exposure

- **Status**: open; blocking for implementation.
- **Question**: exact tool list, context layer exposure, and prohibited data.
- **Recommendation (not approved)**: registered data tools only; no file/env/shell/arbitrary network; context layers per `POL-CTX-01`.
- **Impact**: tool registry, prompts, permission tests.
- **Related requirements**: SR-02, D2 governance.
- **Blocking phase**: before D3.

---

## 4. D1 suggested changes (not applied)

D1 was not modified. The following changes are suggested for team review:

1. **PR-01-AC3** — distinguish run-cache reuse from vendor-cache reads. Current wording can be read as requiring every run to perform its own external execution, which conflicts with existing Yahoo/SEC caches. Suggested: “cross-run run-cache reuse = 0; vendor-cache reads may serve a request and are recorded as `vendor_cache_hits`.”
2. **FR-02** — define the critical-source set and `not_attempted` semantics; define the fallback coverage contract.
3. **SB-01** — state explicitly that the model cannot override the gate; define whether REVIEW is persisted to memory and excluded from tradeable scoring.
4. **INV-02** — add `FinalizedRunRecord` as the canonical artifact and define structured memory fields; clarify exact vs whitespace-normalized comparison.
5. **QR-01** — consider adding `record_hash` and `publish_status` to the manifest fields.
6. **SR-02** — extend the boundary list to the run journal, checkpoint, telemetry, and publish staging; define the secret-pattern categories.
7. **OQ-05** — mark QR-01-AC4 as provisional until measured.

These are suggestions only. D1 remains unchanged.

---

## 5. Blocking summary

| Decision | Blocking phase | Related requirements |
|---|---|---|
| OQ-01 critical sources | D2 review | FR-02, SB-01 |
| OQ-03 secret patterns | D2 review / D3 security | SR-02 |
| OQ-04 query key / vendor cache | D2 review / D3 | PR-01 |
| OQ-06 REVIEW policy | D2 review / D3 | SB-01 |
| D2-OD-01 record schema | Before D3 | SB-01, INV-02, QR-01 |
| D2-OD-02 publish protocol | Before D3 | QR-01, INV-02 |
| D2-OD-03 checkpoint matrix | Before D3 | D2, SB-01, INV-02 |
| D2-OD-04 fallback contract | Before D3 | FR-02, SB-01 |
| D2-OD-06 memory sidecar | Before D3 memory | INV-02 |
| D2-OD-08 runtime tool boundary | Before D3 | SR-02 |

Non-blocking: OQ-02, OQ-05, OQ-07, OQ-08, D2-OD-05, D2-OD-07.

---

## 6. Status

- D1: **not modified**.
- D2 documents: **v0.1 draft / pending human review**.
- Application code: **unchanged**.
- Tests/monitoring: **not started/not implemented**.
