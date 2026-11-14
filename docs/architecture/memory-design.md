# D2 Memory Design

Status: **v0.2 — ADD-R round 2 draft / pending human review**  
Date: 2026-11-11  
D1 basis: `docs/req/requirements.yaml` v1.14.1  
Approval basis: `INV-01`, `FR-02`, `SB-01`, `SR-01` approved; `FR-04`, `FR-05`, `FR-06`, `INV-02` draft  
Implementation status: **design only; no application code changed**

---

## 1. Purpose

This design defines:

- what is stored after a finalized run;
- how model proposals differ from final decisions;
- how memory writes are idempotent, versioned, and retried;
- how memory is read by the Portfolio Manager and bounded by point-in-time rules;
- how current-run risk evidence differs from reused historical evidence;
- how recovery completes the one original planned decision entry;
- how memory interacts with checkpoint resume, partial publication, rotation, and security.

The existing `TradingMemoryLog` remains the storage substrate. `MemoryService` becomes the only public writer/reader for finalized records.

---

## 2. Existing baseline

Existing code:

- `TradingAgents/tradingagents/memory/log.py:32` `store_decision`
- `TradingAgents/tradingagents/memory/log.py:78` `settling`
- `TradingAgents/tradingagents/memory/log.py:106` `get_past_context`
- `TradingAgents/tradingagents/memory/settlement.py`
- `TradingAgents/tradingagents/memory/reflection.py`

Existing behavior:

- Markdown entries with a tag, `DECISION`, and an optional `REFLECTION`.
- Pending entries are settled on a later run.
- The memory log is read by the Portfolio Manager as `past_context`.
- Memory is local plaintext and is not encrypted.
- The baseline entry was `pending`; no reflection was triggered.
- The baseline entry had no run binding, decision ID, coverage/gaps, gate result, or risk summary.

These are preserved as the substrate, not replaced by a new database.

---

## 3. Authority and boundaries

- `MemoryService.store_finalized(record)` is the only public write path for a new decision.
- `MemoryService.complete_recovery(snapshot)` is the only recovery write path; it may only create the one original planned entry or idempotently complete the same entry.
- `MemoryService.get_past_context(...)` is the only read path for runtime agents; the Portfolio Manager consumes it as applicable historical memory.
- Runtime agents cannot read the memory file directly, another run's records, or raw proposals.
- Memory stores only the formal decision and its binding; it never stores a model proposal as the decision. `PortfolioManagerAdapter` produces the unapproved `ModelProposal`; Trader or risk-debater output is not the final model proposal.
- Memory is not a formal publication authority; the terminal manifest plus read-time `INV-01` decides visibility.
- `MemoryRecoveryCoordinator` coordinates an uncommitted same-decision entry owned by another run; it never transfers ownership.

---

## 4. Memory entry model

### 4.1 Source fields

A new entry consumes:

- `run_id`, `decision_id`, `record_version`, `decision_digest`;
- `run_clock`, `ticker`, `trade_date`;
- `final_rating`, `final_decision_text`;
- `coverage_status`, `critical_gap_ids`, `provenance_digest`;
- `gate_result` summary;
- `model_proposals` only as audit references, never as the decision;
- `entry_version`, `entry_digest`, `evidence_digest`;
- optional `supersedes`;
- optional `reused_decision_ref`;
- when `FR-04` applies, a declared risk summary: status, reason codes, `policy_ref`, `policy_digest`, `threshold_status`;
- `created_at`, `holding_days`, `benchmark`.
- `commit_status` is **not** stored in the immutable entry; it is derived from the terminal manifest.

It does not accept raw `final_state`, raw model text, environment values, endpoints with sensitive query parameters, or secrets.

### 4.2 Entry shape

The human-readable Markdown entry keeps the existing shape, extended with a metadata line:

```text
[<trade_date> | <ticker> | <rating> | pending]
RUN_META: <record_hash> <run_id> <decision_id> <entry_version> <entry_digest> <evidence_digest> <profile_hash> <gate_status>
RISK_META: <risk_status> <risk_reason_codes> <policy_ref> <policy_digest> <threshold_status>
DECISION:
<final_decision_text>
<!-- ENTRY_END -->
```

- `RISK_META` is present only for a newly written entry where `FR-04` applies. A reused historical entry keeps its original risk metadata.
- The exact rendering is a design detail; the required fields are the binding, version, digests, formal decision, and optional declared risk summary.
- The existing separator remains valid.

### 4.3 Structured sidecar (work assumption)

To avoid parsing prose, a structured sidecar is a work assumption:

- `trading_memory.jsonl` beside `trading_memory.md`, or
- a structured metadata line in the Markdown entry.

Either representation must carry `decision_id`, `entry_version`, `entry_digest`, `evidence_digest`, `memory_entry_binding`, `supersedes`, `reused_decision_ref`, risk summary (when applicable), retention status, and same-day-rerun status. The shared memory file is never hashed. See ARCH-OD-06.

---

## 5. Proposal versus final decision

`FinalizedRunRecord` separates:

- `model_proposal`: the unapproved proposal produced by `PortfolioManagerAdapter`, with `rating`, `text`, `source=portfolio_manager`, `source_refs`, model identifiers, and `proposal_status=unapproved`; Trader/risk-debater output is only source material;
- `formal_decision`: deterministic gate output and final rating.

Memory stores only the formal decision and rating. If the gate blocks, memory stores `REVIEW` and the deterministic review notice; the model's Buy/Sell text remains audit-only and is not re-read as the system decision.

---

## 6. Idempotency and versioning

Idempotency key: `(decision_id, entry_digest)` plus the existing `(trade_date, ticker)` guard. `run_id` is invocation identity and is not the reuse key.

| Case | Behavior |
|---|---|
| Same decision_id and entry_digest exists | No-op; memory status `existing` |
| Same trade_date/ticker and same decision_id | Same-day rerun reuses the entry; record `reused_decision_ref` |
| Same trade_date/ticker with different decision_id | Reserve a pre-commit `entry_version` greater than the persistent high-water mark over all historical allocations, including failed; write `supersedes`; effective version is the highest committed |
| Same decision_id with different entry_digest | Conflict/tamper; fail publish; manual review |
| Same decision_id with different risk evidence but identical stable decision content | Reuse; risk evidence may differ without blocking reuse |
| Memory disabled | `memory.status=disabled`; no memory artifact required |
| Entry pending or reserved but no completed terminal manifest | Not reusable success; excluded from reads; `MemoryRecoveryCoordinator` applies bounded wait/`MEMORY_PENDING_RETRYABLE`, recovery under original identity/reservation/snapshot, or typed unavailable/failed/conflict; no ownership transfer |
| Current run reuses a prior committed entry | Current artifacts keep the current run_id; memory records `reused_decision_ref`; no duplicate decision entry |
| Recovery finds a completed publication with matching identity | No-op; do not repeat memory |
| Recovery finds a pre-first-write interruption | Create exactly the one original planned decision entry |
| Recovery finds a partial write | Idempotently complete the same entry |

`entry_digest` covers only stable decision content (decision_id, trade_date/ticker, formal decision status/rating/text). It excludes coverage, gaps, provenance, source run/snapshot, timestamps, commit status, risk evidence, and reuse metadata. `evidence_digest` covers `coverage_status`, `critical_gap_ids`, and `provenance_digest`; it may differ across normal reruns and does not imply corruption. Risk evidence is not an `entry_digest` input.

The write is atomic under the existing lock. A crash after append but before the terminal manifest commit must not create a duplicate on retry. The entry's `pending` tag means settlement is pending, not that the decision is unpublished. There is no separate mark-committed write.

---

## 7. Version reservation and effective version

1. `MemoryReservationStore` is a persistent, append-only, lock-protected allocation history. It records ticker/date, decision_id, entry_version, owner run_id, status (`reserved`, `committed`, `failed`), and fencing token.
2. The allocator keeps a persistent high-water mark over **every historical allocation, including failed reservations**. The next version is `high_water + 1`; a failed reservation permanently occupies its version and is never reissued.
3. Before the recovery snapshot is written, `MemoryService` determines the plan: reuse a committed entry, reuse its own uncommitted reservation, or reserve a new version. A retry/recovery reuses its own reservation; a different run gets a higher version.
4. The reserved version and the planned decision identity are recorded in the recovery snapshot, the permanent snapshot binding, and the terminal manifest.
5. State transitions:
   - `reserved`: before the recovery snapshot; durable and version-occupying.
   - `failed`: publish/memory write aborts before a completed terminal manifest; the version remains occupied forever.
   - `committed`: a derived projection, true only when the terminal manifest is `completed` and read-time `INV-01` passes. A ledger commit mark is an audit/cache aid, not a second commit condition; if missing, rebuild it from the terminal manifest.
6. Effective version = the highest `entry_version` whose source terminal manifest is `completed` and binds the entry.
7. Ledger replay/repair replays the append-only allocation records to reconstruct the high-water mark including failed versions, and rebuilds `committed` projections from terminal manifests. Do not derive allocation history solely from committed manifests. If the allocation history is missing/corrupt, stop new allocation, restore from a durable backup or operator-approved reconstruction, and never silently reset the watermark or reissue a failed version.
8. No post-commit write to an older entry is required; superseded entries remain for audit but are excluded from lessons/statistics.
9. Legal rotation of resolved entries removes them under policy and records `retention_status=rotated` or `not_available`, not a binding mismatch.
10. The order is fixed: plan/reservation -> recovery snapshot containing the plan -> idempotent memory write -> permanent snapshot -> terminal candidate -> commit. Recovery follows the recorded plan.

| Ledger state | Written when | Interruption behavior | Retry/recovery |
|---|---|---|---|
| `reserved` | Before the recovery snapshot; durable allocation history | Remains reserved; version stays occupied | Original run/retry reuses it; no new version |
| `failed` | Publish aborts before a completed terminal manifest, or memory write fails | Remains failed; version stays occupied forever | Original run/retry may reuse the same reservation; other runs get higher versions |
| `committed` projection | After terminal commit plus read-time `INV-01`; audit/cache aid only | Missing/failed ledger write does not change the manifest authority; rebuild from manifest | Repair rebuilds projection; never changes allocation high-water mark |

---

## 8. Retry protocol

### 8.1 Publish retry

- 3 attempts with bounded backoff (work assumption; see ARCH-OD-06);
- no model calls;
- each attempt recorded in the publish manifest/evidence store;
- re-check the idempotency key before each retry;
- same `run_id`, `record_version`, and `record_hash`.

### 8.2 Memory failure after other artifacts

If report/final-state exist but memory fails:

- the terminal manifest is not committed; `run_status` remains running or becomes failed;
- the entry remains settlement-pending and unreadable;
- retry uses the same `FinalizedRunRecord`;
- no graph re-run;
- if memory remains unavailable, the ledger records `failed` (the version stays occupied) and operator action is required;
- after memory succeeds and INV-01 passes on the candidate, the publisher commits the terminal manifest; the ledger `committed` projection may be appended after commit+read verification, but it is derived and rebuildable.
- if the process is interrupted between terminal commit and ledger projection update, the terminal manifest remains authoritative; repair rebuilds `committed` without changing the allocation high-water mark or reissuing a failed version.

### 8.3 Conflict

If the key conflicts with a different record:

- do not overwrite;
- do not append a second decision;
- `publish_status=failed` or `partial`;
- report the conflict and the two record identities/digests;
- manual review.

---

## 9. Risk evidence in memory (FR-04/INV-02)

- A newly written memory entry carries the declared risk summary (status, reason codes, `policy_ref`, `policy_digest`, `threshold_status`).
- A reused historical entry retains its original risk summary and binding; the current run does not inject its current risk summary into it.
- Only identical stable decision content reuses an entry. A changed formal decision status/rating/text creates a new decision version under INV-01.
- A risk-blocked rerun follows the same reuse-or-version rule; it is not governed by a blanket no-new-entry rule.
- Risk evidence does not create a second memory key, a second binding, or a second final decision path.
- Memory-disabled runs still satisfy INV-02 through report, manifest, and final-state.

---

## 10. Read path

`MemoryService.get_past_context(...)` applies:

- only entries whose originating run has a completed terminal manifest and whose binding matches the committed manifest;
- for each (ticker, date), only the highest committed `entry_version` contributes lessons/statistics;
- only entries whose resolved date is on or before the analysis date, when point-in-time filtering is active;
- no raw model proposals;
- no secrets;
- bounded same-ticker/cross-ticker limits;
- a compact record hash, gate status, and optional risk summary as metadata.

The read is a context input, not a source of truth. The gate still decides the current run.

---

## 11. Settlement and reflection

Settlement uses a separate append-only protocol from the current decision commit.

- Current decision commit: `MemoryService.store_finalized` writes the decision with `settlement_status=pending`; the terminal manifest commit makes it readable.
- Historical settlement: `MemoryService.settle_historical`/`ReflectionWriter` appends only outcome and reflection fields to an already committed entry.
- Reflection is an LLM call and must be counted as an LLM call in evidence.
- Settlement/reflection cannot change the decision text, rating, binding, decision_id, entry_digest, or risk summary (except appending outcome/reflection fields).
- Superseded versions may be settled for audit, but only the effective version contributes lessons/statistics.
- A settlement failure leaves the entry pending/unsettled and records a separate failure.
- Historical settlement is authorized by the source entry's provenance, not the current run's record.

---

## 12. Recovery interaction (FR-06)

Recovery is not graph resume and does not change memory policy.

- The memory plan is determined before the recovery snapshot; a valid snapshot records the original required memory decision identity and the reserved `entry_version`.
- If the interruption happened before the first write, recovery creates exactly the one original planned entry.
- If a partial write exists, recovery completes that same entry idempotently.
- Recovery never creates a different decision entry or an additional duplicate of the original planned entry.
- Memory-disabled originals remain disabled; settlement and reflection calls are 0.
- Recovery first reads the terminal manifest and verifies the permanent publication. A committed, verified, identity-matching publication is idempotent success without requiring `recovery/`; a committed identity conflict is `RUN_ID_CONFLICT`; committed permanent-artifact corruption is `CORRUPT_RECORD`; neither overwrites the manifest or auto-republishes. Only an uncommitted record continues with the recovery snapshot.
- Recovery uses the same per-run `RunOwnershipLock`, owner, and fencing token as normal publication; ownership/fencing is checked in the same critical section as the protected memory/publication write.
- The recovery snapshot is temporary. After successful commit and post-commit validation, `recovery/` may be cleaned; history reads, memory binding validation, and export rely on the permanent `publication/` snapshot, not the temporary file. A terminal `recovery_snapshot_summary` is audit-only.
- Lock order is run lock then memory lock; a worker that lost its lease is rejected without writing. A cleanup failure after commit is a warning; it does not change memory or history.

---

## 13. Checkpoint and publish interaction

- Graph checkpoint resume may occur before a `FinalizedRunRecord` exists.
- Once a `FinalizedRunRecord` exists, graph resume is not supported; use publish/recovery.
- If memory append succeeded but the terminal manifest commit is missing, a retry re-checks idempotency and does not duplicate; the entry remains unreadable until commit.
- Resume creates a new `run_id`; inherited evidence is tagged and counted separately; coverage is recomputed and rebound.
- If the `decision_id` changes after resume, it is a different decision and memory version rules apply.

---

## 14. Concurrency and uncommitted entries

- Memory writes are serialized by the existing memory lock. `MemoryService` re-checks idempotency inside the lock.
- `MemoryReservationStore` allocates versions under the same lock from a persistent high-water mark over every historical allocation, including failed reservations. Two concurrent runs cannot receive the same version; a failed version is never reissued.
- Normal publication and recovery share the per-run `RunOwnershipLock`; lock order is run lock -> memory lock. Ownership/fencing is checked in the same critical section as the protected write.
- Two runs for the same ticker/date with different decision_ids are serialized; each reserves a distinct version; the highest committed version is effective.
- A failed publication does not supersede the old entry or make the provisional version effective; a retry reuses its reservation.
- Same decision_id with a different entry_digest is a conflict/tamper and is not versioned.
- If a concurrent run finds the same decision_id/entry_digest reserved or written but uncommitted, `MemoryRecoveryCoordinator` applies the deterministic protocol:
  1. owner A active/lease valid: B waits bounded without holding run or memory locks; on timeout returns `MEMORY_PENDING_RETRYABLE`; no entry/version write by B;
  2. A invalid with a valid recovery snapshot: recovery runs under A's original run_id, original reservation, and original snapshot; ownership is never transferred to B;
  3. A invalid without a valid snapshot: `MEMORY_RECOVERY_UNAVAILABLE`; B rejects, no substitute entry;
  4. recovery of A fails: `MEMORY_RECOVERY_FAILED` (retryable/manual);
  5. binding conflict (same decision_id/different entry_digest, inconsistent owner/version): `MEMORY_CONFLICT`; never overwrite.
  After A commits and validates, B may reuse through `reused_decision_ref`; B never treats the uncommitted entry as success, never creates a duplicate entry, and never allocates a second version.
- The OS file lock is short-lived. The logical lease in `lease.json` identifies the active publisher; lease expiry does not release the file lock. If A is paused while holding the file lock, B waits bounded or returns `LOCK_BUSY`; it must not delete the lock file. Takeover acquires the file lock, increments the fencing token, and A is rejected on its next protected write.
- Two runs for different tickers/dates may append concurrently under the lock.
- Backtest memory is isolated per backtest run, not the live memory log.

---

## 15. Security and provenance

- Memory entries contain no API keys, tokens, passwords, userinfo, query, or fragment.
- Endpoint references are scheme + host + path only.
- Coverage and provenance are stored as digests or short labels, not full raw evidence, unless policy allows.
- Raw model proposals are not stored in memory decision text.
- Every memory write records `write_scan_status`; the terminal manifest records final `run_scan_status`; completed requires both clean or redacted.
- Historical settlement/reflection uses the same scan boundary and cannot alter the decision binding.
- Memory files are local plaintext; encryption at rest is out of scope.
- The shared memory file is never hashed; a memory artifact uses `hash_scope = memory_entry`.

---

## 16. Open decisions

- D2-OD-06: structured sidecar versus Markdown metadata line.
- ARCH-OD-06: recovery lease TTL, takeover, retry, and quarantine layout.
- ARCH-OD-20: reservation ledger storage/authority.
- ARCH-OD-21: Portfolio Manager adapter/model-proposal source.
- ARCH-OD-22: uncommitted same-decision coordination statuses/timeouts.
- ARCH-OD-23: permanent/recovery layout and cleanup dependency.
- OQ-02: memory retention/rotation policy.
- OQ-08: concurrent memory/manifest locking policy.
- OQ-09/OQ-10: risk input source and policy approval (affect the risk summary, not the memory identity).
- OQ-16: brief evaluation contract (does not affect memory).

See `docs/architecture/open-decisions.md`.

---

## 17. Status

- Implementation: **not started**.
- Tests: **not started**.
- Existing memory substrate preserved.
- D1: v1.14.1; six requirements approved, seven draft; human review pending.
- D2: v0.2 ADD-R draft; all architecture decisions proposed, not approved.
