# Invariant Register — Report Archive

All invariants have zero tolerance: one violation fails acceptance. Source IDs refer to docs/req/requirements.yaml.

| ID | Statement | Enforcing component | Verification | Operational fallback |
|---|---|---|---|---|
| INV-03 | A committed run ID identifies one immutable snapshot hash and cannot be overwritten | ArchiveService, FileArchiveStore, root lock | T-RAR-03/07; forced collisions and byte comparison | Same ID/hash: reuse valid result. Different hash: RUN_ID_CONFLICT; retain existing archive |
| INV-04 | Every section and combined report belongs to one saved snapshot and declared section map | ReportRenderer, fresh staging, manifest validator | T-RAR-04/14; disjoint text sentinels, stale sections and corrupted bytes | Refuse commit; isolate failed staging; reconstruct only from valid input |
| INV-05 | Success requires a final run directory with valid marker, manifest, required files and matching hashes | FileArchiveStore publication, QueryService, ArchiveResult | T-RAR-05/06/14; actual process termination and malformed marker/manifest | Return NOT_READY or CORRUPT_ARCHIVE; exclude incomplete data from successful queries; preserve valid snapshot |
| INV-06 | Recovery makes no model/provider/graph/memory/settlement/reflection call and commits each identity at most once | ArchiveService recovery dependency boundary | T-RAR-05/07/13; failing spies and repeated restart | Stop affected recovery; keep source snapshot and prior committed data; return safe error |

The payload is data and has no authority over filenames or commit state. Completeness does not assert correctness of investment recommendations. Snapshot/manifest digests detect inconsistent bytes, not authenticity against an attacker controlling the root. These boundaries are exercised by T-RAR-09/11.
