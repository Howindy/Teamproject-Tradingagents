# D2 Runtime Policy Catalog

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` (working baseline; not finally approved)  
Implementation status: **design only; no application code changed**

---

## 1. Purpose

This catalog names every runtime policy that D2 needs, its status, its related requirements, and the impact of changing it. A policy is not approved just because it appears here.

Status values:

- **pending_decision** — needs a human decision;
- **work_assumption** — used to make the draft concrete, but may change;
- **design_only** — architecture design, not implemented;
- **baseline_measured** — a measured baseline fact, not a policy choice.

---

## 2. Policy index

| Policy ID | Name | Status | Related requirements |
|---|---|---|---|
| `POL-COV-01` | Critical-source set | pending_decision | FR-02, SB-01 |
| `POL-COV-02` | Fallback coverage contract | pending_decision | FR-02, SB-01 |
| `POL-CACHE-01` | Query-key normalization | pending_decision | PR-01 |
| `POL-CACHE-02` | Run cache / negative cache / retry | work_assumption | PR-01 |
| `POL-CACHE-03` | Single-flight and run isolation | work_assumption | PR-01 |
| `POL-GATE-01` | Safety gate and REVIEW | pending_decision | SB-01, INV-02 |
| `POL-PUB-01` | Publish protocol and retries | work_assumption | QR-01, INV-02 |
| `POL-MEM-01` | Memory idempotency | work_assumption | INV-02 |
| `POL-CTX-01` | AI context layers | work_assumption | QR-01, FR-02, SB-01 |
| `POL-CTX-02` | Token limits and compression thresholds | work_assumption | QR-01 |
| `POL-RED-01` | Redaction boundaries | pending_decision | SR-02 |
| `POL-CHK-01` | Checkpoint resume matrix | work_assumption | D2 design |
| `POL-PERM-01` | Runtime AI permissions | design_only | SR-02 |
| `POL-PERM-02` | Coding-agent permissions | design_only | D2 governance |

---

## 3. Policy details

### POL-COV-01 — Critical-source set

- **Status**: pending_decision.
- **Question**: which sources are critical?
- **Candidate work assumptions**:
  - ticker news;
  - social sentiment;
  - fundamentals statements;
  - FRED macro;
  - prediction markets.
- **Proposed default** (not approved): ticker news, fundamentals statements, and social sentiment are critical; FRED and prediction markets are optional enrichment.
- **Inputs**: source category, source id, configuration.
- **Outputs**: `critical_sources`, `critical_gaps`.
- **Change impact**: `AvailabilityIndex`, `SafetyGate`, report generation, trace matrix, tests.
- **Related open decision**: OQ-01.

### POL-COV-02 — Fallback coverage contract

- **Status**: pending_decision.
- **Required contract fields**:
  - same category;
  - same instrument;
  - same window and as-of date;
  - point-in-time rule;
  - minimum record count;
  - provenance fields;
  - allowed fallback class.
- **Work assumption**: a fallback that does not satisfy the contract produces `fallback_partial`; the gap remains.
- **Proposed default** (not approved): global macro news is not a substitute for ticker news unless explicitly configured.
- **Change impact**: `DataAccessService`, `AvailabilityIndex`, `SafetyGate`, tests, report labels.
- **Related open decision**: D2-OD-04.

### POL-CACHE-01 — Query-key normalization

- **Status**: pending_decision.
- **Proposed key fields** (not approved):
  - vendor method;
  - normalized ticker;
  - analysis date;
  - requested start/end;
  - indicator/lookback;
  - asset type;
  - policy/cache-key version.
- **Open question**: include vendor chain/config digest or not.
- **Change impact**: `DataAccessService`, cache hit rate, PR-01 tests, traceability.
- **Related open decision**: OQ-04.

### POL-CACHE-02 — Run cache / negative cache / retry

- **Status**: work_assumption.
- **Assumptions**:
  - cache scope is one run;
  - success and terminal failure/withheld/not_configured statuses are cached;
  - retries happen before caching the final status;
  - negative cache stores the final status/reason;
  - no cross-run run-cache reuse.
- **Retry**: vendor-specific retry policy remains as existing; cache is written after retries are exhausted.
- **Change impact**: external request counts, tool rounds, token usage, PR-01 acceptance, tests.
- **Related open decision**: OQ-04.

### POL-CACHE-03 — Single-flight and run isolation

- **Status**: work_assumption.
- **Assumptions**:
  - same query key has one in-flight physical request;
  - concurrent callers wait for the same result;
  - each run has its own cache;
  - existing vendor caches are recorded separately.
- **Change impact**: `DataAccessService`, concurrency tests, evidence counters.
- **Related open decision**: OQ-08.

### POL-GATE-01 — Safety gate and REVIEW

- **Status**: pending_decision.
- **Proposed default** (not approved):
  - gate runs before formal persistence/display;
  - critical gap forces `REVIEW`;
  - model cannot override;
  - REVIEW is persisted to memory but not scored as a tradeable position;
  - operator override is out of D1.
- **Change impact**: `SafetyGate`, entry points, publisher, memory, report, backtest, tests.
- **Related open decision**: OQ-06.

### POL-PUB-01 — Publish protocol and retries

- **Status**: work_assumption.
- **Assumptions**:
  - staged publish;
  - atomic per-file writes;
  - commit order: record → report → final-state → memory → manifest → complete marker;
  - 3 publish attempts with bounded backoff;
  - no model calls during publish retry;
  - same record hash across retries.
- **Change impact**: `ArtifactPublisher`, memory, tests, run status.
- **Related open decision**: D2-OD-02, OQ-02.

### POL-MEM-01 — Memory idempotency

- **Status**: work_assumption.
- **Assumptions**:
  - key = `(run_id, record_hash)` plus `(trade_date, ticker)`;
  - same key/hash = no-op;
  - different hash for same ticker/date = conflict;
  - memory append is atomic under lock;
  - memory uses finalized decision only.
- **Change impact**: `MemoryService`, `TradingMemoryLog`, publish retry, tests.
- **Related open decision**: D2-OD-06.

### POL-CTX-01 — AI context layers

- **Status**: work_assumption.
- **Layers**:
  - L0 safety/policy — never compressed;
  - L1 run identity/coverage/gaps — never compressed;
  - L2 role/output — never compressed;
  - L3 evidence — compressible;
  - L4 history — compressible;
  - L5 output contract/gate rules — never compressed.
- **Assembly order**: L0 + L1 + L2 + L3/L4 + L5; re-inject L0/L1/L2/L5 after compression.
- **Change impact**: `ContextAssembler`, agent prompts, token usage, tests.

### POL-CTX-02 — Token limits and compression thresholds

- **Status**: work_assumption; all values are **provisional, pending approval**.
- **Assumptions**:
  - provider context window: 128k;
  - soft limit: 75%;
  - hard limit: 90%;
  - per-call input cap: 24k;
  - evidence block cap: 4k;
  - history cap: 8k;
  - compression summary cap: 2k;
  - deterministic truncation first; optional LLM summarization only if enabled.
- **Change impact**: `ContextAssembler`, prompt sizes, token cost, compression tests.
- **Related open decision**: D2-OD-05.

### POL-RED-01 — Redaction boundaries

- **Status**: pending_decision.
- **Boundaries**: CLI/logs/errors/manifest/final-state/report/memory/prefs/journal/checkpoint/staging/telemetry/coding-agent transcripts.
- **Rules**:
  - endpoint scheme + host + path only;
  - remove userinfo/query/fragment;
  - no keys/tokens/passwords;
  - allowlist config;
  - hash metadata where possible.
- **Change impact**: `SecretRedactor`, all writers, tests, permission model.
- **Related open decision**: OQ-03, OQ-07.

### POL-CHK-01 — Checkpoint resume matrix

- **Status**: work_assumption.
- **Supported**: graph checkpoint, messages, reports, debate state, evidence journal, rebuildable cache/metrics/availability.
- **Not supported**: in-flight requests/LLM, cache without journal, finalized/published record, schema/policy/cache-key/context version mismatch, missing journal in strict mode.
- **Degraded mode**: explicit opt-in; coverage partial/unknown; gate likely REVIEW.
- **Change impact**: `CheckpointCoordinator`, graph, evidence store, tests.
- **Related open decision**: D2-OD-03.

### POL-PERM-01 — Runtime AI permissions

- **Status**: design_only.
- **Allowed**: provided context, registered tools, proposals.
- **Denied**: files, env, shell, arbitrary network, artifacts, gate override, code modification.
- **Change impact**: tool registry, agent runtime, permission tests.
- **Related open decision**: D2-OD-08.

### POL-PERM-02 — Coding-agent permissions

- **Status**: design_only.
- **Default**: deny.
- **D2**: write `architecture-blueprint.md` and `docs/architecture/**` only.
- **Future roles**: implementation, test, baseline operator, D1 editor, reviewer; see `permission-model.md`.
- **Change impact**: permission model, agent runtime, audit tests.

---

## 4. Work-assumption change impact

If a work assumption changes, the following must be revisited:

| Assumption changes | Affected interfaces/components | Affected documents |
|---|---|---|
| Critical-source set | `AvailabilityIndex`, `SafetyGate`, report, trace tests | `architecture-blueprint.md`, `invariants.md`, `trace-matrix.md`, `open-decisions.md` |
| Fallback substitute policy | `DataAccessService`, `AvailabilityIndex`, gate | `architecture-blueprint.md`, `invariants.md`, `evaluation-table.md` |
| Query key normalization | `DataAccessService`, cache, tests | `architecture-blueprint.md`, `trace-matrix.md`, `open-decisions.md` |
| REVIEW policy/override | `SafetyGate`, entry points, memory, backtest | `architecture-blueprint.md`, `memory-design.md`, `open-decisions.md` |
| Publish order/retries | `ArtifactPublisher`, `MemoryService` | `architecture-blueprint.md`, `memory-design.md`, `open-decisions.md` |
| Token limits/compression | `ContextAssembler`, prompts, cost metrics | `architecture-blueprint.md`, `evaluation-table.md`, `open-decisions.md` |
| Checkpoint support | `CheckpointCoordinator`, graph | `architecture-blueprint.md`, `invariants.md`, `open-decisions.md` |
| Coding-agent roles/paths | permission model, agent runtime | `permission-model.md`, `open-decisions.md` |

---

## 5. Status

- Policies are design-only or pending decisions.
- No policy is implemented.
- No policy threshold has been measured unless it is a baseline observation.
- D1 is not modified.
