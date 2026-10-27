# ADR 001 — Run Governance Architecture: Lean A with FinalizedRunRecord

Status: **v0.1 — draft / pending human review**  
Decision status: **proposed**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` (working baseline; not finally approved)  
Implementation status: **design only; no application code changed**

---

## 1. Context

D1 defines six requirements: `PR-01`, `QR-01`, `FR-02`, `SB-01`, `INV-02`, `SR-02`. The baseline establishes:

- 195.383s end-to-end, 19 LLM calls, 31 tool calls.
- 156,541 input tokens, 27,639 output tokens.
- Repeated failed calls: 6 FRED, 2 ticker news, 2 prediction markets.
- No native manifest; default stderr is empty.
- No unified availability state and no coverage-aware safety gate.
- The baseline decision/report/full-state were consistent, but source-status consistency across every artifact was not measured.
- Partial secret scrubbing exists, but no full secret scan was performed.

The architecture must make the safety gate non-bypassable, keep model proposals separate from final decisions, and ensure formal outputs share one canonical record.

---

## 2. Decision

Adopt **Lean A** as the working D2 architecture:

- `RunContext` is lifecycle and dependency wiring only.
- Business rules are separate services: `DataAccessService`, `RunEvidenceStore`, `ContextAssembler`, `SafetyGate`, `ArtifactPublisher`, `MemoryService`, `SecretRedactor`, `CheckpointCoordinator`.
- `SafetyGate` produces an immutable `FinalizedRunRecord`.
- Model proposals and final decisions are separate fields.
- All formal display, persistence, and memory consume `FinalizedRunRecord` only.
- Old writers are wrapped, made private, or require a finalized record.
- Publish is staged, atomic per file, and complete only after a publish-complete marker.
- Memory writes are idempotent by `(run_id, record_hash)`.
- Coverage fallback only clears a gap if it satisfies the same coverage contract.

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

- Strongest construction guarantee for `INV-02`.
- Pure reducers and replay are highly testable.
- Cache, availability, metrics, and gate inputs derive from one event stream.
- Ledger outside graph state is checkpoint-friendly.

**Costs**

- Higher schema/replay complexity.
- Event schema evolution cost.
- Retention and sanitization of the ledger are additional concerns.
- More implementation work than Lean A.

### Option C — Minimal Decorator / Contextvar Layer

Keep current architecture; add wrappers, contextvar, stats manifest, and a CLI gate.

**Advantages**

- Lowest change surface and lowest implementation cost.
- Minimal runtime overhead.
- Fastest prototype path.

**Costs**

- `INV-02` and `SR-02` depend on every writer/wrapper being migrated; bypass risk is high.
- Gate is easy to place only in CLI, missing programmatic/backtest paths.
- Hidden contextvar state complicates concurrency and testing.

---

## 4. Comparison summary

| Criterion | Lean A | B: Event Ledger | C: Decorator |
|---|---|---|---|
| Requirement coverage confidence | High (design expectation) | High (design expectation) | Low–Medium (design expectation) |
| Change surface | High | Medium | Low–Medium |
| Complexity | High | Medium–High | Low |
| Runtime cost | Low (design expectation) | Low–Medium (design expectation) | Low (design expectation) |
| Testability | High | High | Medium |
| Maintainability | Medium | High | Low |
| Bypass resistance | High | High | Low |
| Checkpoint friendliness | Medium–High | High | Medium |

No candidate has been implemented. All ratings except baseline facts are design expectations, not measurement results.

Full table: `docs/architecture/evaluation-table.md`.

---

## 5. Why Lean A

1. It satisfies the D1 zero-tolerance safety and consistency requirements without the full event-schema/replay cost of B.
2. `FinalizedRunRecord` provides a single formal output contract; the publisher can enforce that only finalized data is displayed or persisted.
3. RunContext remains small; business policy is testable in separate services.
4. It is less likely than C to leave a bypass through programmatic or backtest paths.
5. It gives the team a concrete migration path: wrap old writers, then make them private or record-dependent.

Lean A is chosen for the D2 draft because it balances safety and change cost. B remains the fallback if Lean A cannot prove non-bypassability or if replay becomes necessary. C is retained only as a tactical prototype comparison.

---

## 6. Consequences

### Positive

- Model proposals cannot be mistaken for final decisions.
- Coverage and fallback provenance can be enforced before persistence.
- Manifest, report, final-state, and memory can be checked against one record hash.
- Partial publish is explicit; success requires a complete marker.
- Memory duplication is controlled by an idempotency key.
- Concurrency rules for same-run queries and different runs are explicit.

### Negative

- Old writers must be migrated; direct calls will fail until adapted.
- More components and interfaces than the current codebase.
- Publish staging and idempotency add implementation and test work.
- Context assembler and token policy are new complexity.
- D1 open decisions still block implementation details.

### Neutral

- Existing vendor caches remain; they are distinct from the PR-01 run cache.
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
- D1: **not modified**.
