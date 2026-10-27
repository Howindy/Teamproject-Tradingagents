# Memory and State Design — Report Archive

## Ownership and persistent state

The analysis adapter owns the per-analysis run ID and initial metadata. ArchiveService coordinates archive state; FileArchiveStore owns disk transitions. ReportSnapshot is the immutable saved input. QueryService has read access to validated committed artifacts. The baseline trading-memory log retains its existing identity, settlement and context-reading behavior; the archive does not append to or reshape it.

| State | Location | Lifetime and read policy |
|---|---|---|
| New analysis context | In-process adapter | New UUID and metadata per analysis; not sufficient for recovery until snapshot is saved |
| Intent | pending/<run_id>/intent.json | Identifies a partial receipt; no successful report retrieval |
| Complete snapshot | pending/<run_id>/snapshot.json | Survives process interruption; retain until validated commit |
| Render attempt | staging/<run_id>.<attempt_id> | Private temporary data; never returned as a committed result |
| Committed report bundle | runs/<run_id> | Immutable source of historical results; marker/manifest/file validation required |
| Failure/quarantine data | pending diagnostics or quarantine/<incident_id> | Retain identifiable safe diagnostics; never invent missing metadata |

## Write and retrieval policy

The root is fixed at service opening. Writers hold the OS root lock; snapshots are written through same-directory temporary files and read-back verified. Each render uses a fresh directory. Commit is a same-volume rename into a previously absent final run path. Idempotent retries use the same ID/hash. Lists include valid committed runs only and expose invalid-run diagnostics separately. Filter by ticker and analysis date using intersection; sort creation time descending, run ID ascending on ties. get_run verifies marker, exact manifest hash, identity, section set, sizes and digests before returning content.

After interruption, a valid saved snapshot rebuilds reports deterministically using the saved creation time and supported renderer version. A matching valid committed destination is reused. Unknown versions remain intact. Corrupt committed data produces CORRUPT_ARCHIVE and is not overwritten as automatic repair.

## Retention, versions and privacy

Keep successful archives and identifiable failure summaries indefinitely in this iteration. No automatic pruning, legacy report migration or history indexing of legacy paths occurs. Cleanup removes only run-owned pending/staging residue after verified commit. Losing unsaved model output, power failure, external deletion and synchronized-folder conflicts are outside the guarantee.

Allowlist report fields and necessary metadata; exclude raw message history, full configuration, environment and credentials. Scan content and diagnostics deterministically before snapshot persistence; never invoke a model to sanitize. Files are local plaintext; encryption and multi-user authentication are outside scope. Hashes are integrity checks, not authentication.

## Separation from other persistence

Graph checkpoints resume unfinished analysis and use the existing checkpoint lifecycle. Archive snapshots reconstruct reports after final content exists. Archive recovery never executes a graph checkpoint, legacy state-log write, trading-memory append, settlement or reflection. Multiple archived runs can share ticker/date even when legacy memory retains only one decision for that pair. An archive COMMITTED status attests only to the archive bundle.

## Verification

T-RAR-03/04 test identity and section isolation; T-RAR-05/07/13 test crash/replay/cleanup; T-RAR-09/11 test data and path boundaries; T-RAR-14 tests versions and integrity. T-RAR-08 includes normal snapshot and query validation in its timed recovery workload. These are specified checks; no application execution result is claimed.
