# D2 Architecture Blueprint — Lean A Run Governance

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` (working baseline; not finally approved)  
Implementation status: **design only; no application code changed**

---

## 1. Purpose and scope

This blueprint defines the D2 architecture for the six D1 requirements:

- `PR-01` — run-scoped reuse of identical data queries.
- `QR-01` — lean run manifest.
- `FR-02` — one run-scoped data-availability state and user-visible critical gaps.
- `SB-01` — deterministic pre-persistence safety gate.
- `INV-02` — consistent provenance and final decision across artifacts.
- `SR-02` — no credentials or sensitive URL parameters in run records.

The design direction is **Lean A**: a variant of the central-coordinator candidate where `RunContext` owns lifecycle and dependency wiring only. Business rules live in separate services. `FinalizedRunRecord` is the only artifact source for formal display, persistence, and memory.

This document is a design draft. It does not approve D1, select an implementation, or claim that any test has passed.

---

## 2. Non-goals and preserved baseline

### 2.1 Non-goals

- No replacement of StockTwits or other social vendors.
- No point-in-time SEC company profile.
- No parallel Bull/Bear or risk-analyst execution.
- No full exchange calendar.
- No multi-user authentication, encryption at rest, or access control.
- No portfolio simulation or order execution.
- No default TypeSafe Jev screening.
- No production LLM response cache.
- No application code implementation in D2.

### 2.2 Preserved baseline

The existing baseline remains the reference:

- `baseline/runs/baseline-20261020-01/`
- Measured: 195.383s, 19 LLM calls, 31 tool calls, 156,541 input tokens, 27,639 output tokens.
- Measured duplicate failed calls: 6 FRED, 2 ticker news, 2 prediction markets.
- Measured data status: 20 success, 4 withheld, 6 not_configured, 4 unavailable.
- Measured source integrity: identical before/after.

All architecture changes in this blueprint are prospective design. They are not implemented or measured.

---

## 3. Architecture overview — Lean A

### 3.1 Design principle

`RunContext` is a **lifecycle and dependency container**, not a business-rule engine. It creates and closes the run, owns the run identity and paths, and wires services. It does not decide coverage, cache policy, safety outcomes, or artifact contents.

Business rules are split into:

| Component | Responsibility |
|---|---|
| `RunContext` | Lifecycle, run identity, paths, clock, config snapshot, service wiring |
| `DataAccessService` | Query key, run cache, single-flight, retry, fallback, coverage contract |
| `RunEvidenceStore` | Run-scoped evidence index: query ledger, availability index, metrics, provenance |
| `ContextAssembler` | AI context layers, token budget, compression, constraint re-injection |
| `SafetyGate` | Deterministic finalization into immutable `FinalizedRunRecord` |
| `ArtifactPublisher` | Atomic publication of report, manifest, final-state, memory, complete marker |
| `MemoryService` | Idempotent memory append and read from finalized records |
| `SecretRedactor` | Redaction at every output boundary |
| `CheckpointCoordinator` | Supported resume matrix and state reconstruction |
| `PolicyCatalog` | Versioned policy identifiers and defaults |
| `EntrypointAdapter` | CLI, programmatic, and backtest entry normalization |
| `LegacyWriterAdapter` | Converts old writers into finalized-record consumers or blocks them |

### 3.2 Component-to-module mapping

| New component | Existing modules it wraps or replaces | Change type |
|---|---|---|
| `RunContext` | `cli/run.py`, `TradingAgentsGraph` entry paths | New lifecycle wrapper |
| `DataAccessService` | `tradingagents/dataflows/router.py:200`, `sentiment_analyst.py:69` prefetch, vendor modules | New service around existing calls |
| `RunEvidenceStore` | `cli/stats_handler.py:10`, router outcomes, reporting metadata | New run-scoped store |
| `ContextAssembler` | agent prompts in `agents/analysts/*`, `agents/researchers/*`, `agents/managers/*`, `agents/risk_mgmt/*` | New assembly layer |
| `SafetyGate` | `agents/rating.py:106`, `agents/managers/portfolio_manager.py:80`, `graph/trading_graph.py:358` | New finalization gate |
| `FinalizedRunRecord` | report/final-state/memory/CLI payloads | New immutable record |
| `ArtifactPublisher` | `reporting.py:92`, `graph/trading_graph.py:437`, `cli/run.py:440`, `memory/log.py:32` | New sole public writer |
| `MemoryService` | `memory/log.py`, `memory/settlement.py`, `memory/reflection.py` | New finalized-record facade |
| `SecretRedactor` | `dataflows/net.py:6`, `cli/prefs.py:49`, `graph/trading_graph.py:255` | New boundary service |
| `CheckpointCoordinator` | `graph/checkpointer.py`, `graph/trading_graph.py:192` | New resume policy layer |
| `PolicyCatalog` | `default_config.py`, new policy constants | New versioned catalog |

---

## 4. Entry points and writer migration

The safety gate cannot be optional. All entry points must go through `SafetyGate` and `ArtifactPublisher`.

### 4.1 Entry-point matrix

| Entry point | Current path | Target path | Bypass prevention |
|---|---|---|---|
| CLI analysis | `cli/main.py` → `cli/run.py:99` | `CliEntrypoint` → `RunContext` → graph → `SafetyGate` → `ArtifactPublisher` | Publisher requires `FinalizedRunRecord` |
| Programmatic graph | `TradingAgentsGraph.propagate` → `_run_graph` | `ProgrammaticEntrypoint` → same finalization service | `propagate` returns record or proposal; it does not write |
| Root demo | `TradingAgents/main.py` | Programmatic entrypoint | Remove direct writer path; demo uses record |
| Backtest | `tradingagents/backtest.py` | Per-cell `RunContext` → same finalization service | Per-cell record; memory per backtest run |
| Direct report writer | `reporting.write_report_tree` | `LegacyWriterAdapter` / internal publisher function | Public call requires record; otherwise raises |
| Direct memory writer | `memory/log.py:store_decision` | `MemoryService.store_finalized` | Old method becomes private or requires record |
| Graph decision writer | `trading_graph.record_decision` | Proposal event only | Does not call `_log_state` or memory directly |
| State log writer | `trading_graph._log_state` | Publisher internal | Not callable as public path |
| `save_reports` | `TradingAgentsGraph.save_reports` | Deprecated adapter → publisher | Requires finalized record |
| CLI display | `cli/display.py:display_complete_report` | Finalized record only | Cannot display raw proposal as final |

### 4.2 Old-writer policy

Old writers are not deleted in this design. They are wrapped or made private:

- `reporting.write_report_tree` becomes an internal rendering primitive called only by `ArtifactPublisher`.
- `TradingMemoryLog.store_decision` becomes internal to `MemoryService`.
- `TradingAgentsGraph._log_state` becomes internal to `ArtifactPublisher`.
- `TradingAgentsGraph.record_decision` no longer persists; it records the model proposal.
- `TradingAgentsGraph.save_reports` becomes a compatibility adapter that calls the publisher with a finalized record.
- Direct calls without a `FinalizedRunRecord` fail with a deterministic error; they do not fall back to an unfinalized path.

A planned static audit lists every public writer and asserts that no production writer accepts raw `final_state` without a record. Test status: **not started**.

---

## 5. Data flow

```text
Entrypoint
  -> RunContext.start(config)
  -> PolicyCatalog load
  -> RunEvidenceStore open
  -> DataAccessService bind
  -> ContextAssembler bind
  -> Graph / agents / tools
       -> DataAccessService
            -> query key
            -> run cache / single-flight
            -> vendor / fallback / retry
            -> RunEvidenceStore
       -> ContextAssembler
            -> L0..L5 context
       -> LLM proposals
  -> SafetyGate.finalize(proposals, evidence snapshot)
  -> FinalizedRunRecord (immutable)
  -> ArtifactPublisher.publish(record)
       -> report Markdown/HTML
       -> manifest
       -> final-state
       -> memory
       -> publish-complete marker
  -> formal display consumes FinalizedRunRecord only
```

Model proposals are recorded separately from the final decision. The final decision is created by `SafetyGate`; the model does not write it.

---

## 6. Coverage and fallback contract

### 6.1 Availability state

`RunEvidenceStore` maintains per-source entries:

- `source_id`
- `category`
- `status`: success / unavailable / withheld / not_configured / not_attempted / fallback_partial
- `reason`
- `requested_window`
- `record_count`
- `provenance`
- `attempts`
- `fallback_of` (when applicable)

`AvailabilityIndex` computes `coverage_status`:

- `complete` only when every configured critical source has `status=success`.
- `partial` when any configured critical source has a critical gap.
- A critical source that was never attempted is `not_attempted` and is a gap under the current work assumption.

### 6.2 Fallback rule

A fallback can clear a critical gap only if it satisfies the same `CoverageContract`:

- same source category;
- same instrument;
- same requested window and as-of date;
- point-in-time rules satisfied;
- minimum record count;
- required provenance fields;
- configured fallback class.

If any field differs, the fallback is `fallback_partial` and the primary gap remains. Global macro news does not clear a ticker-news critical gap unless the policy explicitly allows that substitution.

This is a work assumption; see `docs/architecture/open-decisions.md` (D2-OD-04).

---

## 7. Logical queries, physical requests, fallback, and retry

These counters are separate and must not be conflated:

| Counter | Meaning |
|---|---|
| `logical_queries` | Agent/tool requests for data |
| `unique_query_keys` | Distinct normalized keys in the run |
| `run_cache_hits` | Hits in the PR-01 run cache |
| `vendor_cache_hits` | Hits in the existing vendor cache layer |
| `physical_requests` | Calls into a vendor implementation |
| `external_requests` | Network requests to an external service |
| `fallback_attempts` | Attempts to use a fallback source |
| `retry_attempts` | Retries of a physical request |
| `tool_rounds` | LLM tool-call rounds |

PR-01 primarily targets `external_requests` and duplicate `physical_requests`. It does not automatically reduce `tool_rounds` or `token` usage, because the agent may still call the tool and receive a cached result. Benefit types are evaluated separately in `docs/architecture/evaluation-table.md`.

The existing vendor cache may serve data across runs. This is distinct from the PR-01 run cache. D1 `PR-01-AC3` says cross-run reuse count is zero; this needs clarification for vendor caches. See `docs/architecture/open-decisions.md` (OQ-04 / D1 suggested change).

---

## 8. SafetyGate and FinalizedRunRecord

### 8.1 Separation of proposals and final decision

`ModelProposal` contains what the model produced:

- analyst reports;
- debate histories;
- trader proposal;
- portfolio-manager proposal;
- model rating and model decision text.

`FinalizedRunRecord` contains:

- `record_version`;
- run identity: run_id, ticker, trade_date, commit, model/provider identifiers, config digest;
- evidence snapshot: source statuses, provenance, query counters, token counts, timing;
- `model_proposals` (raw, audit-only);
- `coverage_status` and `critical_gaps`;
- `safety_gate` result, policy id, reasons;
- `final_rating`;
- `final_decision_text`;
- artifact references (realized artifact hashes live in the publish manifest);
- `record_hash`.

`final_rating` and `final_decision_text` are deterministic gate outputs, not model outputs. If a critical gap exists, `final_rating=REVIEW` and the model's Buy/Sell text is preserved only under `model_proposals`, not presented as the final decision.

### 8.2 Immutability

`FinalizedRunRecord` is created once, hashed, and never mutated. A changed decision requires a new run or a new record version. A publish retry reuses the same record hash.

### 8.3 Formal consumers

Only the following may consume `FinalizedRunRecord` for formal output:

- CLI display;
- report Markdown/HTML;
- manifest;
- final-state;
- memory;
- publish manifest;
- backtest scoring;
- monitoring.

Raw `ModelProposal` is audit-only and must not be shown as the final decision.

---

## 9. Publish protocol, partial failure, and retry

### 9.1 Publish plan

`ArtifactPublisher` builds a `PublishManifest` from `FinalizedRunRecord`:

- `record_hash`;
- artifact list with path, type, hash;
- `publish_status`: staging / published / partial / failed;
- attempts and timestamps.

### 9.2 Commit order

1. Write `finalized-record.json` in staging.
2. Write report Markdown and HTML.
3. Write final-state JSON.
4. Append memory entry.
5. Write manifest JSON with realized artifact hashes.
6. Write `publish-complete.json`.
7. Optionally move/rename staging artifacts into the published run directory.

Atomic per-file writes use temp file + `os.replace` semantics. Directory publication uses a complete marker after all artifacts exist.

### 9.3 Partial failure

If any step fails:

- `publish_status=partial`;
- no `publish-complete.json`;
- formal success is not claimed;
- the finalized record stays available;
- retry publishes missing artifacts only;
- the model is not re-run;
- any CLI/display path that shows the decision must also show `publish_status=partial` and must not claim a complete publication.

If `finalized-record.json` cannot be written, the run fails before any formal output.

### 9.4 Memory idempotency and retry

Memory idempotency key: `(run_id, record_hash)` plus the existing `(trade_date, ticker)` guard.

- Same key exists with same hash: no-op, mark memory step complete.
- Same ticker/date exists with different hash: conflict; publish fails; manual review required.
- Memory write is atomic under the existing lock; a retry re-checks the key before append.
- If memory succeeds but the complete marker is missing, a publisher retry sees the existing entry and does not duplicate it.

### 9.5 Retry policy

Work assumption: 3 publish attempts with bounded backoff. No model calls. Each attempt is recorded in the publish manifest and evidence store. After exhaustion, `publish_status=failed` and operator action is required.

---

## 10. Concurrency

### 10.1 Same run, same query

`DataAccessService` uses single-flight per `query_key`:

- first request executes;
- concurrent requests wait on the in-flight result;
- all receive the same `DataResult`;
- external request count for that key is 1;
- logical request count remains >1.

### 10.2 Different runs

- Each run has its own `RunContext`, `RunEvidenceStore`, and run cache.
- Run caches are not shared.
- Existing vendor caches may be shared; they are recorded as `vendor_cache_hits`, not `run_cache_hits`.
- Memory writes are serialized by the existing lock and idempotency key.
- Manifest/preference writes use per-run paths and atomic replace.

### 10.3 Backtest

Each cell runs in its own `RunContext` and produces its own `FinalizedRunRecord`. The backtest log is per backtest run. No run cache is shared between cells.

---

## 11. Checkpoint recovery

`CheckpointCoordinator` defines a support matrix.

### 11.1 Supported

- LangGraph checkpoint state: messages, reports, debate state, current node.
- Run identity and config digest.
- Run evidence journal, if present and schema-compatible.
- Completed data results from the journal can rebuild the run cache.
- Metrics and availability can be reconstructed from the journal.
- Publish retry after a finalized record exists (publish-resume, not graph-resume).

### 11.2 Not supported

- In-flight external requests.
- In-flight LLM calls.
- Run cache entries without journal evidence.
- Resume after a record has been finalized and published.
- Resume across a changed graph signature, policy version, cache-key version, or record schema.
- Resume when the journal is missing, in strict mode.
- Resume of a partially published run through the graph; use publish-resume instead.

### 11.3 Degraded resume

Degraded resume is opt-in and only if the journal is missing but the graph checkpoint is valid. It sets `coverage_status=partial` or `unknown`, records a resume warning, and the gate will likely produce REVIEW. Strict mode refuses the resume.

### 11.4 Signature

The checkpoint signature includes:

- graph shape;
- analyst set;
- debate/risk depth;
- asset type;
- portfolio fingerprint;
- policy catalog version;
- cache-key version;
- context assembler version;
- record schema version.

A mismatch starts a new run or refuses resume; it does not silently reuse old state.

---

## 12. AI context layering, assembly, token limits, and compression

### 12.1 Layers

| Layer | Content | Compression |
|---|---|---|
| L0 | Safety and policy constraints, external content is data, tool limits, gate notice | Never compressed |
| L1 | Run identity, ticker, date, latest bar, coverage status, critical gaps, fallback labels | Never compressed |
| L2 | Role instructions, rating scale, task, output format | Never compressed |
| L3 | Evidence blocks: tool outputs, prefetch blocks, reports, provenance | Compressible |
| L4 | Working history: messages, debate history, prior turns | Compressible |
| L5 | Output contract and deterministic gate rules | Never compressed |

### 12.2 Assembly flow

1. Build L0, L1, L2, L5 from policy and run snapshot.
2. Add L3 evidence and L4 history.
3. Estimate input tokens.
4. If above the soft threshold, compress L3/L4 in priority order.
5. Re-inject L0/L1/L2/L5 after compression as a final constraint block.
6. Record `context_manifest`: layers, estimated tokens, compression events, dropped evidence IDs, re-injected constraints.
7. Send to the model.

### 12.3 Token limits and compression thresholds

These are **work assumptions, pending approval**; no baseline experiment supports them.

| Policy | Work assumption | Status |
|---|---|---|
| Provider context window | 128k tokens | Pending; model-specific |
| Soft limit | 75% of context window | Provisional |
| Hard limit | 90% of context window | Provisional |
| Per-call input cap | 24k tokens | Provisional |
| Evidence block cap | 4k tokens per block | Provisional |
| History cap | 8k tokens | Provisional |
| Compression summary cap | 2k tokens | Provisional |
| Compression strategy | deterministic truncation first; optional LLM summarization only if explicitly enabled | Provisional |

### 12.4 Re-injection

After any compression, the assembler appends a fixed block containing:

- L0 safety/policy summary;
- L1 coverage and critical gaps;
- L2 role and output contract;
- L5 deterministic gate rules.

Evidence omitted by compression is labeled as omitted; it is not silently removed.

---

## 13. Desensitization output boundaries

The full boundary list is in `docs/architecture/permission-model.md`. Summary:

- CLI stdout/stderr;
- application logs;
- error messages and tracebacks;
- run manifest;
- final-state JSON;
- report Markdown and HTML;
- memory log;
- preferences;
- run evidence journal;
- checkpoint SQLite;
- publish staging and publish manifest;
- telemetry and monitoring;
- coding-agent transcripts.

Rules:

- endpoint records use scheme + host + path only;
- URL userinfo, query, and fragment are removed;
- API keys, tokens, passwords, and secret-pattern values are never recorded;
- configuration is allowlisted;
- all boundaries use `SecretRedactor`;
- secret scanning is a planned test, not a completed result.

---

## 14. Runtime AI and coding-agent permissions

- Runtime AI agents can read only provided context/evidence, call registered tools, and produce proposals. They cannot read environment variables, access files, run shell commands, access arbitrary networks, modify code, or write artifacts.
- Coding agents default to deny. Per-role and per-path whitelists are in `docs/architecture/permission-model.md`.
- D2 coding agents may write only `architecture-blueprint.md` and `docs/architecture/**`; they may read `docs/req/**`, `TradingAgents/**`, and `baseline/**`.
- D2 coding agents must not modify `TradingAgents/**`, `scripts/**`, `baseline/**`, `docs/req/**`, `.env`, secrets, or Git state.

---

## 15. Candidate comparison summary

| Candidate | Summary | D2 role |
|---|---|---|
| Lean A | RunContext lifecycle/DI; separate services; FinalizedRunRecord; publisher | **Recommended for review** |
| B | Event-sourced ledger + reducers; strongest construction guarantee; higher schema/replay cost | Retained comparison; re-decision option |
| C | Minimal decorators/contextvar; lowest cost; weakest bypass/consistency guarantee | Retained comparison; not recommended for zero-tolerance D1 |

Full comparison and M/D/U evidence status: `docs/architecture/evaluation-table.md`.

Lean A is a recommendation for review, not a team approval.

---

## 16. Document index

- [ADR 001 — Run governance](docs/architecture/adr/001-run-governance.md)
- [Invariants](docs/architecture/invariants.md)
- [Trace matrix](docs/architecture/trace-matrix.md)
- [Memory design](docs/architecture/memory-design.md)
- [Permission model](docs/architecture/permission-model.md)
- [Runtime policy catalog](docs/architecture/runtime-policy-catalog.md)
- [Evaluation table](docs/architecture/evaluation-table.md)
- [Open decisions](docs/architecture/open-decisions.md)

All documents share the same v0.1 draft status and the same D1 working baseline.

---

## 17. Implementation and evidence status

- Application implementation: **not started**.
- Tests: **not started**.
- Runtime monitoring: **not implemented**.
- Benefits: **not measured**.
- Only the baseline facts in `baseline/runs/baseline-20261020-01/` are measured.
- D1 remains a working baseline; D1 open questions are not resolved by this document.
