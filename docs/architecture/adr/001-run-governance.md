# ADR 001 — Run Governance Architecture: Lean A with FinalizedRunRecord

Status: **v0.1 — draft / pending human review**  
Decision status: **proposed**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` v1.9.0 (historical baseline approved; current revision human review pending; IDs renumbered)
Implementation status: **design only; no application code changed**

---

## 1. Context

D1 defines six requirements: `FR-01`, `FR-02`, `FR-03`, `SB-01`, `INV-01`, `SR-01`. The baseline establishes:

- 195.383s end-to-end, 19 LLM calls, 31 tool calls.
- 156,541 input tokens, 27,639 output tokens.
- Repeated logical query: 3 ticker-news attempts with the same key. The 6 FRED indicators and 2 prediction-market topics were distinct logical queries that failed locally without an external request.
- No native manifest; default stderr is empty.
- No unified availability state and no coverage-aware safety gate.
- The baseline decision/report/full-state were consistent, but source-status consistency across every artifact was not measured.
- Partial secret scrubbing exists, but no full secret scan was performed.

The architecture must make the safety gate non-bypassable, keep model proposals separate from final decisions, and ensure formal outputs share one canonical record.

---

## 2. Decision

Adopt **Lean A** as the working D2 architecture:

- `RunContext` is lifecycle and dependency wiring only; it fixes `run_clock` and allocates a unique `run_id`.
- Business rules are separate services: `DataAccessService`, `AvailabilityIndex`, `RunEvidenceStore`, `ContextAssembler`, `SafetyGate`, `ArtifactPublisher`, `MemoryService`, `SecretRedactor`, `CheckpointCoordinator`.
- `AvailabilityIndex` produces the critical profile, ordered attempts, supports links, component_missing records, and a coverage snapshot containing `critical_profile_hash` and `provenance_digest`.
- `PreflightCoordinator` fetches mandatory market price and stock financial statements before analyst nodes, using the same `DataAccessService` run cache.
- `FailureFinalizer` writes an independent `RunFailureRecord` and failed manifest when no normal `FinalizedRunRecord` exists; this path does not require model output.
- `SafetyGate` consumes a trusted coverage snapshot and model proposal, selects `primary_reason_code` and `review_class`, and produces an immutable `FinalizedRunRecord`.
- Model proposals and formal decisions are separate fields; memory reuses by `decision_id`, not by per-invocation `run_id`.
- All formal display, persistence, and memory consume `FinalizedRunRecord` only.
- Old writers are wrapped, made private, or require a finalized record.
- Publish is staged and atomic per file; `run_status=completed` requires an INV-01 check and the terminal manifest.
- Memory writes use `(decision_id, entry_digest)` plus the existing `(trade_date, ticker)` guard; same-day same-binding reruns reuse the entry, different decision_ids reserve pre-commit versions with supersedes and effective version is derived from committed manifests; only same decision_id with different entry_digest conflicts, and memory-disabled runs require no memory artifact.
- Coverage fallback only clears a gap if it satisfies the same component/window/point-in-time/minimum-record contract.
- The terminal manifest `run_status=completed` is the unique commit point; INV-01 checks the terminal candidate and the committed files, not the running manifest.
- Runtime context uses a provisional coverage view; the final coverage snapshot is created after the graph and used only by the gate/formal outputs.
- The context budget is the effective input budget (per-call cap minus output/tool/constraint reserves), not 75% of the provider window.
- Historical settlement/reflection uses a separate append-only protocol from current decision commit.
- Immutable decision timing ends at the gate; publish metrics live in the terminal manifest.
- Implementation is phased: core formal-result loop with query reuse first, then memory lifecycle, recovery, optional compression, and behavior evaluation. Before recovery/compression are enabled, resume is rejected and over-budget context fails closed.

### 2.1 ADD iterations applied

1. **Context and drivers**: app-controlled records versus external logs; six D1 requirement drivers.
2. **Evidence model**: executed availability records, supports links, component_missing records, fixed run clock, critical profile, coverage snapshot.
3. **Formal decision**: trusted gate input, reason priority, review class, formal decision, model-proposal separation.
4. **Publication and consistency**: artifact binding, decision id, manifest, memory entry binding, INV-01 checkpoints.
5. **Security and operations**: write/run scan phases, incident record, checkpoint signature, runtime policies.
6. **Evaluation**: compare Lean A, event ledger, and decorator; select Lean A for review.

See `architecture-blueprint.md` §1A for the full ADD driver/quality-attribute table.

Lean A is a **recommendation for review**, not an approved team decision.

---

## 3. Options considered

### Option A — Central Run Coordinator (Lean A variant)

RunContext owns lifecycle/DI; services own business logic.

**Advantages**

- Clear separation of lifecycle from policy.
- Strong path to `FinalizedRunRecord` and non-bypassable gate.
- Testable services with explicit interfaces.
- Lower conceptual overhead than event sourcing.

**Costs**

- Cross-cutting integration across CLI, graph, tools, reporting, memory, prefs.
- Requires strict writer migration and static bypass checks.
- Risk of RunContext growing into a god object if boundaries are not enforced.

### Option B — Event-Sourced Run Ledger + Reducers

Every run fact is appended to a ledger; reducers produce availability, metrics, manifest, gate input, and artifacts.

**Advantages**

- Strongest construction guarantee for `INV-01`.
- Pure reducers and replay are highly testable.
- Cache, availability, metrics, and gate inputs derive from one event stream.
- Ledger outside graph state is checkpoint-friendly.

**Costs**

- Higher schema/replay complexity.
- Event schema evolution cost.
- Retention and sanitization of the ledger are additional concerns.
- More implementation work than Lean A.

### Option C — Minimal Decorator / Contextvar Layer under the same safety contract

Keep current architecture; add wrappers, contextvar, stats manifest, and a gate. For a fair comparison, this option must satisfy the same entry coverage, `SB-01`, `INV-01`, and `SR-01` requirements as Lean A; a CLI-only gate is not a valid candidate.

**Advantages**

- Lower conceptual overhead than event sourcing.
- Minimal runtime overhead for a single entry point.
- Fastest prototype path if coverage is narrow.

**Costs**

- Under the required same safety contract, it must wrap CLI, programmatic, backtest, checkpoint, and headless paths; change surface becomes high.
- `INV-01` and `SR-01` depend on every writer/wrapper being migrated; bypass risk remains higher than Lean A unless migration is pervasive.
- Hidden contextvar state complicates concurrency, retry, and testing.

---

## 4. Comparison summary

| Criterion | Lean A | B: Event Ledger | C: Decorator (same safety contract) |
|---|---|---|---|
| Entry coverage under same contract | High (design) | High (design) | High required, difficult to prove |
| Requirement coverage confidence | High (design) | High (design) | Medium (design) |
| Change surface | High | Medium | High |
| Complexity | High | Medium–High | Medium–High |
| Runtime cost | Low (design) | Low–Medium (design) | Low (design) |
| Testability | High | High | Medium |
| Maintainability | Medium | High | Low–Medium |
| Bypass resistance | High | High | Medium–Low |
| Checkpoint friendliness | Medium–High | High | Medium |

All candidates are compared under the same entry coverage, gate, invariant, and secret-scanning requirements. No candidate has been implemented. All ratings except baseline facts are design expectations, not measurement results.

Full table: `docs/architecture/evaluation-table.md`.

---

## 5. Why Lean A

1. It satisfies the D1 zero-tolerance safety and consistency requirements without the full event-schema/replay cost of B.
2. `FinalizedRunRecord` provides a single formal output contract; the publisher can enforce that only finalized data is displayed or persisted.
3. RunContext remains small; business policy is testable in separate services.
4. Under the same required entry coverage, it is less likely than C to leave a bypass through programmatic or backtest paths.
5. It gives the team a concrete migration path: wrap old writers, then make them private or record-dependent.

Lean A is chosen for the D2 draft because it balances safety and change cost. B remains the fallback if Lean A cannot prove non-bypassability or if replay becomes necessary. C is retained only as a tactical prototype comparison.

### 5.1 Candidate validation slice

Before final implementation approval, build the same thin vertical slice for Lean A, B, and C under identical entry coverage and safety requirements:

- one mandatory preflight run;
- one coverage snapshot with a critical gap;
- one gate block and one failure record;
- one terminal manifest commit and INV-01 read-back;
- one write/run secret scan;
- one same-day memory reuse/version case.

Record changed files, new interfaces, approximate LOC, test count, bypass findings, and time-to-green. The slice is evidence for the change/complexity comparison, not a production implementation. If Lean A does not show an acceptable complexity advantage under the same safety contract, reopen this ADR.

---

## 6. Consequences

### Positive

- Model proposals cannot be mistaken for final decisions.
- Coverage and fallback provenance can be enforced before persistence.
- Manifest, report, final-state, and memory share one artifact_binding and decision_id.
- Partial publish is explicit; completed requires an INV-01 check and terminal manifest.
- Memory duplication is controlled by decision_id/entry_digest; same-day reruns and disabled memory are explicit.
- Concurrency rules for same-run queries and different runs are explicit.

### Negative

- Old writers must be migrated; direct calls will fail until adapted. `propagate` return semantics, report/memory writers, and backtest callers require compatibility adapters, deprecation notes, and full regression tests.
- More components and interfaces than the current codebase.
- Publish staging, coverage snapshot, and cross-artifact semantic checks add implementation and test work.
- Context assembler and token policy are new complexity.
- Fixed run clock, decision_id, and memory lifecycle require migration of old writers.
- Remaining D1 open decisions are non-blocking retention and concurrency items.

### Neutral

- Existing vendor caches remain; they are distinct from the FR-01 run cache.
- Checkpoint resume becomes stricter and may refuse more cases.
- Coding-agent permissions are documented, not implemented by this ADR.

---

## 7. Re-decision conditions

Re-open this ADR if any of the following occurs:

1. Lean A cannot guarantee non-bypassability of `FinalizedRunRecord` without pervasive rewrites.
2. Publish/retry/memory idempotency becomes too complex without an event ledger.
3. The team requires replayable evidence for audit or debugging beyond the run evidence journal.
4. Multi-user or concurrent publication becomes in scope.
5. D1 changes the critical-source, REVIEW, or cross-run cache semantics.
6. Measured cache/latency/token benefits show Lean A does not justify its complexity.
7. Context compression requires event-level replay or deterministic summaries.
8. The permission model requires stronger isolation than the runtime tool boundary provides.

---

## 8. Related documents

- `architecture-blueprint.md`
- `docs/architecture/invariants.md`
- `docs/architecture/trace-matrix.md`
- `docs/architecture/memory-design.md`
- `docs/architecture/permission-model.md`
- `docs/architecture/runtime-policy-catalog.md`
- `docs/architecture/evaluation-table.md`
- `docs/architecture/open-decisions.md`

---

## 9. Status

- Decision status: **proposed, pending human review**.
- Application implementation: **not started**.
- Tests: **not started**.
- Monitoring: **not implemented**.
- Benefits: **not measured**.
- D1: **v1.9.0 historical baseline approved; current revision human review pending; FR-01, FR-02, FR-03, SB-01, INV-01, and SR-01 contracts synchronized**.
