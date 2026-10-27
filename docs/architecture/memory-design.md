# D2 Memory Design

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` (working baseline; not finally approved)  
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

It does not accept raw `final_state`, raw model text, environment values, endpoints with query parameters, or secrets.

### 3.2 Entry fields

The human-readable Markdown entry keeps the existing shape:

```text
[<trade_date> | <ticker> | <rating> | pending]
RUN_META: <record_hash> <run_id> <gate_result>
DECISION:
<final_decision_text>
<!-- ENTRY_END -->
```

The exact rendering is a design detail. The important fields are:

- final rating, not model proposal rating;
- final decision text, not raw proposal text;
- record hash and run id for idempotency and traceability;
- coverage/gate digest, not the full critical-gap payload unless policy allows;
- no secrets.

The existing separator remains valid.

### 3.3 Structured sidecar (work assumption)

To support QR-01/INV-02 without parsing prose, D2 assumes a structured sidecar:

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

Idempotency key: `(run_id, record_hash)` plus the existing `(trade_date, ticker)` guard.

| Case | Behavior |
|---|---|
| Same run_id and same record_hash exists | No-op; mark memory step complete |
| Same trade_date/ticker exists with same record_hash | No-op |
| Same trade_date/ticker exists with different record_hash | Conflict; publish fails; manual review |
| Same run_id with different record_hash | Conflict; publish fails; manual review |
| Entry pending vs resolved with same key | No new decision entry; settlement may update reflection only |

The memory write is atomic under the existing lock. A crash after append but before the complete marker must not create a duplicate on retry.

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

- `publish_status=partial`;
- manifest and `publish-complete.json` are not written yet;
- memory retry uses the same `FinalizedRunRecord`;
- no graph re-run;
- after memory succeeds, the publisher writes the manifest and complete marker;
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

- only finalized, non-pending entries;
- only entries whose `resolved` date is on or before the analysis date, when point-in-time filtering is active;
- no raw model proposals;
- no secrets;
- record hash and gate result may be included as compact metadata;
- the read is bounded by the existing same-ticker/cross-ticker limits.

The memory read is a context input, not a source of truth. The gate still decides the current run.

---

## 8. Settlement and reflection

Settlement remains based on the finalized decision, not the raw proposal.

- A pending memory entry is settled when the holding window has traded.
- Reflection is an LLM call; it must be recorded as an LLM call in evidence.
- Reflection text is appended to memory only after the outcome is computed.
- Reflection cannot change the historical final decision or rating.
- If settlement fails, the entry stays pending; the failure is recorded.
- Settlement is outside the D2 implementation scope except for the finalized-record source and idempotency implications.

---

## 9. Checkpoint and publish interaction

- Graph checkpoint resume may occur before a `FinalizedRunRecord` exists.
- Once a `FinalizedRunRecord` exists, graph resume is not supported; use publish-resume.
- If memory append succeeded but complete marker is missing, publish-resume re-checks idempotency and does not duplicate.
- If graph checkpoint is resumed with an existing memory entry for the same run/record, the memory entry is treated as already complete.
- If the record hash changes after resume, it is a new run/record; memory conflict rules apply.

---

## 10. Concurrency

- Memory writes are serialized by the existing lock file.
- `MemoryService` re-checks idempotency inside the lock.
- Two runs for the same ticker/date with different records conflict; the second must not overwrite the first.
- Two runs for different tickers/dates may append concurrently under the lock.
- Backtest memory is isolated per backtest run, not the live memory log.

---

## 11. Security and provenance

- Memory entries contain no API keys, tokens, passwords, userinfo, query, or fragment.
- Endpoint references are scheme + host + path only.
- Coverage and provenance are stored as digests or short labels, not full raw evidence, unless policy allows.
- Raw model proposals are not stored in memory decision text.
- Memory files are local plaintext; encryption at rest is out of scope for D2.

---

## 12. Open decisions

- D2-OD-06: structured sidecar vs Markdown metadata line.
- OQ-02: memory retention/rotation policy.
- OQ-06: whether REVIEW entries are kept in memory and whether they are settled.
- OQ-08: concurrent memory/manifest locking policy.

See `docs/architecture/open-decisions.md`.

---

## 13. Status

- Implementation: **not started**.
- Tests: **not started**.
- Existing memory substrate preserved.
- D1: **not modified**.
