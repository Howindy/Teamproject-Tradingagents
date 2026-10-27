# Candidate Evaluation — Report Archive

## Decision evidence

Static evidence comes from the main revision recorded in D1: ticker/date CLI paths, second-resolution API export paths, fixed section rendering and direct writes into existing directories. These facts establish mechanisms requiring improvement, not a measured incident rate. No archive candidate has been implemented or benchmarked in this document.

| Criterion | A: filesystem snapshots and immutable directories | B: SQLite snapshots/index plus report files | C: unique directories only |
|---|---|---|---|
| Retain independent same-day runs | UUID run paths | Unique database keys and file paths | Unique paths |
| Recover after in-memory output is lost | Yes, from confirmed complete snapshot | Yes, if complete content is stored transactionally and file replay is implemented | No reliable reconstruction input |
| Reject incomplete results | Final-path marker plus manifest/file validation | Needs consistent database and file publication rules | Needs additional completeness protocol |
| Section isolation | Fresh staging and fixed section set | File isolation still required | Unique paths help but do not solve recovery |
| Concurrency | One root lock serializes commit | Database transactions plus filesystem coordination | Naming alone does not ensure idempotent retry |
| Historical queries | Manifest scan and simple filters | Indexed queries scale further | Directory scan |
| State/complexity cost | One file-based recovery source, explicit lock and cleanup | Database schema plus coordination with report files | Lowest initial cost, fails recovery requirement |
| Selection | Chosen for one local Windows host and fixed workload | Reconsider if measured indexing needs justify it | Rejected for QR-02 |

## Tradeoff and measurement

Accept snapshot storage, serialized writes and integrity validation to obtain deterministic recovery. Avoid an additional database consistency domain at the current scale. This is a design comparison; expected advantages are not measured speed or cost savings.

T-RAR-08 measures 30 independently reset batches with 100 committed archives and 10 pending snapshots, each <=1,048,576 bytes. Include root lock, scan, rendering, publication, integrity checks and cleanup attempts through final normal retrieval. All ten outputs must be correct in every trial. Sort the 30 durations; one-based rank 29 must be <=2 seconds. Failed/time-out samples fail acceptance and remain in the record. Record machine/runtime/storage, source revision, renderer settings and fixture digest.

The fixture contains no competing publisher or persistent external fault. Reset time, Python startup and waiting for restart/external-fault resolution are outside the timer. Memory/settlement is not part of this archive transaction and is never invoked as recovery work. The target does not establish arbitrary-scale history query performance or faster model analysis.

Reconsider option A if measured scans or lock waits cannot satisfy QR-02, search requirements grow, deployment requires shared/synchronized storage or recovery needs power-loss durability. Do not meet the target by weakening correctness or truncating report inputs.
