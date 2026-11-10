# D2 Memory Design

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` v1.9.0 (historical baseline approved; current revision human review pending; IDs renumbered)
Implementation status: **design only; no application code changed**

---

## 1. Purpose

The memory design defines:

- what is stored after a finalized run;
- how raw model proposals differ from final decisions;
- how memory writes are idempotent and retried;
- how memory is read by the Portfolio Manager;
- how memory interacts with checkpoint resume and partial publication;
- how secrets and provenance are handled.

The existing `TradingMemoryLog` remains the storage substrate in D2. `MemoryService` becomes the only public writer/reader for finalized records.

---

## 2. Existing baseline

Existing code:

- `TradingAgents/tradingagents/memory/log.py:32` `store_decision`
- `TradingAgents/tradingagents/memory/log.py:78` `settling`
- `TradingAgents/tradingagents/memory/log.py:106` `get_past_context`
- `TradingAgents/tradingagents/memory/settlement.py`
- `TradingAgents/tradingagents/memory/reflection.py`

Existing behavior:

- Markdown entries with tag, `DECISION`, and optional `REFLECTION`.
- Pending entries are settled on a later run.
- The memory log is read by the Portfolio Manager (`past_context`).
- Memory is local plaintext; it is not encrypted.
- The baseline memory entry was `pending`; no reflection was triggered.

These are preserved as the substrate, not re-implemented as a new database in D2.

---

## 3. Memory entry model

### 3.1 Source

`MemoryService.store_finalized(record: FinalizedRunRecord)` is the only public write path.

It consumes:

- `record_hash`
- `run_id`
- `decision_id`
- `run_clock`
- `ticker`
- `trade_date`
- `final_rating`
- `final_decision_text`
- `coverage_status`
- `critical_gaps_digest`
- `safety_gate_result`
- `model_proposals` only as audit references, not as the decision
- `provenance_digest`
- `created_at`
- `holding_days`
- `benchmark`
- `commit_status` as a projection of the source terminal manifest (`committed` for a completed run; not stored in the immutable entry digest)
- `reused_decision_ref` when the current run reuses a prior committed decision entry

It does not accept raw `final_state`, raw model text, environment values, endpoints with query parameters, or secrets.

### 3.2 Entry fields

The human-readable Markdown entry keeps the existing shape:

```text
[<trade_date> | <ticker> | <rating> | pending]
RUN_META: <record_hash> <run_id> <decision_id> <entry_version> <entry_digest> <evidence_digest> <gate_result> <profile_hash>
DECISION:
<final_decision_text>
<!-- ENTRY_END -->
```

The exact rendering is a design detail. The important fields are:

- final rating, not model proposal rating;
- final decision text, not raw proposal text;
- record hash, run id, decision id, entry_version, entry_digest, and evidence_digest for traceability; memory reuse is keyed by decision_id/entry_digest;
- `reused_decision_ref` records the source run_id/decision_id/entry_digest when a current run reuses a historical entry; the current artifacts keep the current run_id; commit_status is not stored in the entry, only derived for display;
- coverage/gate digest, not the full critical-gap payload unless policy allows;
- no secrets.

The existing separator remains valid.

### 3.3 Structured sidecar (work assumption)

To support FR-02/INV-01 without parsing prose, D2 assumes a structured sidecar:

- `trading_memory.jsonl` beside `trading_memory.md`, or
- a structured metadata line in the Markdown entry.

This is a work assumption; see `docs/architecture/open-decisions.md` (D2-OD-06). If the sidecar is rejected, the Markdown tag and metadata line must carry the same idempotency and provenance fields.

---

## 4. Raw proposal vs final decision

`FinalizedRunRecord` separates:

- `model_proposals`: raw analyst/debate/trader/PM output and model rating.
- `final_decision`: deterministic gate output and final rating.

Memory stores only `final_decision` and `final_rating`. The raw proposal is retained in the record/audit artifact, not in the memory decision body.

This prevents a model-produced Buy/Sell from being re-read as the system's final decision when the gate produced REVIEW.

---

## 5. Idempotency

Idempotency key: `(decision_id, entry_digest)` plus the existing `(trade_date, ticker)` guard. `run_id` is per-invocation and is not the memory reuse key.

| Case | Behavior |
|---|---|
| Same decision_id and entry_digest exists | No-op; mark memory step existing |
| Same trade_date/ticker exists with same decision_id | No-op; same-day rerun reuses the entry |
| Same trade_date/ticker with different decision_id | New pre-commit entry_version; current decision publishes; effective version derived from highest committed entry_version |
| Same decision_id with different entry_digest | Conflict/tamper; fail publish; manual review |
| Memory disabled | `memory.status=disabled`; no memory artifact required |
| Entry pending vs resolved with same key | No new decision entry; settlement may update reflection only |
| Current run reuses a prior committed entry | current artifacts keep current run_id; memory records `reused_decision_ref`; no duplicate decision entry |
| Entry written but run not committed | no completed terminal manifest; excluded from reads regardless of the entry tag |

The memory write is atomic under the existing lock. A crash after append but before the terminal manifest commit must not create a duplicate on retry. The unique readable criterion is the completed terminal manifest plus read-time INV-01; there is no separate mark-committed write. The entry's `pending` tag means outcome settlement is pending; commit_status is derived for display and is not stored in RUN_META or included in entry_digest.

Binding is per decision entry through `memory_entry_binding` (source_run_id, decision_id, record_version, decision_digest, trade_date/ticker, entry_digest, evidence_digest). `entry_digest` covers only stable decision content (decision_id, trade_date/ticker, formal decision fields) and excludes coverage/gaps, provenance, source_run_id, source snapshot hash, timestamps, commit_status, and reuse metadata. `evidence_digest` covers coverage_status, critical_gap_ids, and provenance_digest; it may differ across normal reruns and does not imply entry corruption. The current run keeps its own run_id in the artifact binding; `reused_decision_ref` links to the source entry without rewriting it. The shared memory file is never hashed: normal appends, settlement/reflection, lock maintenance, and policy-based rotation of resolved entries change the file but not any retained decision binding. A memory artifact uses hash_scope = memory_entry. Deleting or modifying a retained decision entry, or changing its entry_digest, is an illegal change and fails INV-01; an evidence_digest change alone is not corruption. Same-day same-binding reruns reuse the entry; different decision_ids create committed versions. Memory-disabled runs require no memory artifact. Rotation absence is recorded as memory not_available.

---

## 6. Retry protocol

### 6.1 Publish retry

`ArtifactPublisher` retries memory append as part of publish:

- 3 attempts (work assumption);
- bounded backoff;
- no model calls;
- each attempt recorded in publish manifest and evidence store;
- before each retry, re-check the idempotency key.

### 6.2 Memory failure after other artifacts

If report/final-state exist but memory fails:

- the terminal manifest is not committed; `run_status` remains running or becomes failed;
- memory remains physically settlement-pending and is unreadable because no completed terminal manifest exists; `commit_status` is a derived projection, not a stored write;
- memory retry uses the same `FinalizedRunRecord`;
- no graph re-run;
- after memory succeeds and INV-01 passes on the terminal candidate, the publisher commits the terminal manifest;
- if memory remains unavailable, operator action is required.

### 6.3 Conflict

If the idempotency key conflicts with a different record:

- do not overwrite;
- do not append a second decision;
- `publish_status=failed` or `partial`;
- report the conflict and the two record hashes;
- manual review.

---

## 7. Read path

The Portfolio Manager reads memory through `MemoryService.get_past_context(...)`.

Rules:

- only entries whose originating run has a completed terminal manifest and whose binding matches the committed manifest; for each (ticker, date), only the highest committed entry_version contributes lessons/statistics; superseded versions are retained for audit but excluded from learning; physical `pending` means settlement pending, not unpublished;
- only entries whose `resolved` date is on or before the analysis date, when point-in-time filtering is active;
- no raw model proposals;
- no secrets;
- record hash and gate result may be included as compact metadata;
- the read is bounded by the existing same-ticker/cross-ticker limits.

The memory read is a context input, not a source of truth. The gate still decides the current run.

Historical same-ticker and cross-ticker lessons are allowed only through `MemoryService.get_past_context(...)`, which applies authorization, committed-entry filtering, point-in-time filtering, retention/rotation state, provenance labels, and secret redaction. Runtime agents cannot read the memory file or another run's records directly.

---

## 8. Settlement and reflection

Settlement remains based on the finalized decision, not the raw proposal. It uses a separate append-only historical write protocol from the current decision commit.

- Current decision commit: `MemoryService.store_finalized` writes the decision with physical `settlement_status=pending`; the terminal manifest commit makes the entry readable. `commit_status=committed` is derived from that manifest and is not a separate write.
- Historical settlement: `MemoryService.settle_historical`/`ReflectionWriter` appends only outcome and reflection fields to an already committed historical entry.
- Reflection is an LLM call; it must be recorded as an LLM call in evidence.
- Reflection text is appended only after the outcome is computed.
- Settlement/reflection cannot change the decision text, rating, binding, decision_id, or entry_digest.
- Superseded versions may be settled for audit, but only the effective version per (ticker, date) contributes lessons or statistics; old entries are retained but excluded from learning to avoid double counting.
- If settlement fails, the entry stays pending/unsettled; the failure is recorded in a separate historical-settlement record.
- Historical settlement is authorized by the source entry’s run provenance, not by the current run’s FinalizedRunRecord.

---

## 9. Checkpoint and publish interaction

- Graph checkpoint resume may occur before a `FinalizedRunRecord` exists.
- Once a `FinalizedRunRecord` exists, graph resume is not supported; use publish-resume.
- If memory append succeeded but terminal manifest commit is missing, publish-resume re-checks idempotency and does not duplicate; the entry remains unreadable until commit.
- Resume creates a new run_id. Inherited evidence is tagged with `origin_run_id`, `inherited=true`, and separate inherited counters; the coverage snapshot is recomputed and rebound to the new run_id.
- If graph checkpoint is resumed with an existing memory entry for the same decision_id, the entry is reused only if it is committed; otherwise it remains pending.
- If the decision_id changes after resume, it is a different decision; memory conflict rules apply.

---

## 10. Concurrency

- Memory writes are serialized by the existing lock file.
- `MemoryService` re-checks idempotency inside the lock.
- Two runs for the same ticker/date with different decision_ids are serialized: each reserves a pre-commit entry_version under the lock, writes the provisional entry and supersedes, and records that version in its terminal manifest. Effective version is derived from committed manifests; no old entry is modified after commit.
- A failed publication does not supersede the old entry or make the provisional entry effective.
- Two concurrent new versions reserve distinct entry_versions under the lock; the highest committed entry_version is effective, lower committed versions remain historical. A failed commit leaves a version gap but no effective change.
- Same decision_id with a different entry_digest is a conflict/tamper and is not versioned.
- Two runs for different tickers/dates may append concurrently under the lock.
- Backtest memory is isolated per backtest run, not the live memory log.

---

## 11. Security and provenance

- Memory entries contain no API keys, tokens, passwords, userinfo, query, or fragment.
- Endpoint references are scheme + host + path only.
- Coverage and provenance are stored as digests or short labels, not full raw evidence, unless policy allows.
- Raw model proposals are not stored in memory decision text.
- Every memory write records `write_scan_status`; the terminal manifest records final `run_scan_status`; completed requires both clean or redacted.
- Historical settlement/reflection writes use the same scan boundary and cannot alter the decision binding.
- Memory files are local plaintext; encryption at rest is out of scope for D2.

---

## 12. Open decisions

- D2-OD-06: structured sidecar vs Markdown metadata line.
- OQ-02: memory retention/rotation policy.
- OQ-06 (resolved in D1 v1.4.0): REVIEW entries are kept in memory as non-tradeable formal decisions and are not scored; settlement/reflection is append-only.
- OQ-08: concurrent memory/manifest locking policy.

See `docs/architecture/open-decisions.md`.

---

## 13. Status

- Implementation: **not started**.
- Tests: **not started**.
- Existing memory substrate preserved.
- D1: **v1.9.0 historical baseline approved; current revision human review pending; FR-01, FR-02, FR-03, SB-01, INV-01, and SR-01 contracts synchronized**.
