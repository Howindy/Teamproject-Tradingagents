# ADR 001 — File Snapshots and Immutable Report Archives

## Context and design process

The requirement is to preserve separately identifiable reports and recover interrupted saves after analysis completes. Static inspection of main identifies ticker/date CLI paths, second-resolution API exports, direct per-file rendering and no recovery snapshot. The process compares three storage candidates, identifies crash windows around snapshot and directory publication, and defines identity, completeness and retry invariants before selecting a protocol.

The baseline contains report rendering, graph/state logging and trading memory. ArchiveService is a new report-specific component. Existing memory policy is not redesigned.

## Decision

Use a local filesystem source of truth: confirmed immutable report snapshot, fresh staging, verified manifest and commit marker, then same-volume no-replacement rename into a run-ID directory. An OS lock serializes cooperating publishers. A read-only query service validates committed archives. Retain run ID, original timestamp, snapshot hash and renderer version through reconstruction.

Automatic archiving is invoked at the existing common completion path used by CLI and API. Archive outcome is separate from analysis completion and legacy memory/state-log outcome. Recovery only renders saved report data; it does not call the analysis completion method again.

## Alternatives and rationale

| Candidate | Advantages | Limitations | Outcome |
|---|---|---|---|
| A: file snapshots and immutable directories | One file-based recovery source; reuses renderer; explicit completeness and isolation | Snapshot storage, lock contention and linear history scan | Selected for the fixed local workload |
| B: SQLite snapshots/catalog plus external reports | Indexed retrieval and transactional row identity | Database/file consistency and schema migration still require a recovery protocol | Reconsider when measured scale requires indexing |
| C: unique report directories without saved snapshots | Small change and unique paths | Cannot reconstruct reports after the in-memory final state is lost | Does not satisfy QR-02 |

The evaluation records design deductions, not measured timing. Correctness is prioritized over concurrent throughput. Archive snapshots are not graph checkpoints and do not provide power-loss or cross-host transactions.

## AI output and recovery boundary

The upstream analysis uses AI-generated report text. The archive receives only an allowlisted report snapshot; deterministic code controls identity, paths, field validation, hashes and publication. Text that asks to write another path or change status remains report content. The archive does not generate an LLM prompt, assemble conversation context, allocate runtime model tokens or compact model history. Its 1 MiB benchmark envelope is a snapshot byte limit, not a model context limit. Report recovery has no model-client dependency.

This scope preserves the analysis result rather than changing the AI's decision or introducing a new AI feature. Product prompt/context behavior upstream of report extraction is outside the archive component. Its safety boundary is the constrained transformation of untrusted AI-generated text into filesystem artifacts.

## Consequences and reconsideration

Positive effects are independent historical reports, accurate completion status and model-free interrupted-save recovery. Costs are snapshot space, digest verification, versioned rendering and serialized publication. An archive may succeed while legacy memory fails, or remain pending after analysis completes; both outcomes must be visible.

Reopen this decision if measured scans or lock waits exceed QR-02, history needs indexed/full-text search, storage moves beyond one local NTFS host, or reproducible rendering across versions cannot be supported. A benchmark failure does not justify dropping failed samples or bypassing integrity checks. See the trace matrix for offline fixtures and the 30-trial measurement protocol.
