# Trace Matrix — Report Archive

## Requirement and fit-criterion trace

Application checks and monitors are specified, not executed or implemented.

| Fit criterion | Enforcing component | Tests | Runtime observation |
|---|---|---|---|
| FR-03-AC1 | Analysis adapter, ArchiveService and QueryService | T-RAR-01, T-RAR-12 | MON-ARCH-01 archive_status |
| FR-03-AC2 | Run identity, root lock, fresh staging, no-replacement commit | T-RAR-03, T-RAR-04 | MON-ARCH-04/05 duplicate commits/conflicts |
| FR-03-AC3 | QueryService and manifest validation | T-RAR-02, T-RAR-14 | MON-ARCH-06/07 query/integrity outcome |
| FR-03-AC4 | Snapshot save, startup recovery, cleanup | T-RAR-05, T-RAR-06, T-RAR-07, T-RAR-13 | MON-ARCH-02/03/10/12 recovery, invalid input, retries, cleanup |
| FR-03-AC5 | Allowlist, content scan, path containment and export reservation | T-RAR-09, T-RAR-10, T-RAR-11, T-RAR-12 | MON-ARCH-13/14 boundary/export rejection |
| FR-03-AC6 | Per-analysis context and separate archive result | T-RAR-01, T-RAR-07, T-RAR-12 | MON-ARCH-01/04 archive status and duplicate commit count |
| QR-02-AC1 | Complete archive recovery and normal query verification | T-RAR-08 | MON-ARCH-16 recovery duration; recovered_count |
| INV-03-AC1 | Lock, UUID/hash checks and exclusive publication | T-RAR-03, T-RAR-07 | MON-ARCH-05 conflict_count |
| INV-04-AC1 | Fixed section map, staging and manifest | T-RAR-04, T-RAR-14 | MON-ARCH-07 integrity_error_count |
| INV-05-AC1 | Final-directory marker and query validation | T-RAR-05, T-RAR-06, T-RAR-14 | MON-ARCH-06 false_success_count, target 0 |
| INV-06-AC1 | Recovery dependency boundary and stable saved identity | T-RAR-05, T-RAR-07, T-RAR-13 | MON-ARCH-15 forbidden_recovery_calls, target 0 |

## Test specifications

| Test | Fixture/action | Pass oracle |
|---|---|---|
| T-RAR-01 | CLI/API complete-result fixtures, separate archive failure and legacy-memory failure | Automatic archive in both paths; independent statuses; propagate shape retained; memory failure cannot invalidate a committed archive |
| T-RAR-02 | Ticker/date/combined/empty filters, unknown ID, incomplete directory | Exact valid committed ID sets and stable order; empty list, NOT_FOUND and NOT_READY as specified |
| T-RAR-03 | 10 worker processes publish 100 runs for same ticker/date/second; force ID/hash collision | 100 separately retrievable runs; existing bytes unchanged; conflicting ID rejected. Workers may retry explicit LOCK_BUSY; no latency target in this test |
| T-RAR-04 | Disjoint analyst sets and planted stale sections | Exact sections and complete-report text for each snapshot; no foreign content |
| T-RAR-05 | Terminate actual writer subprocess after snapshot, during render, before rename, and after rename | Every valid saved run recovers once; no partial output appears committed; pre-snapshot loss is reported |
| T-RAR-06 | Missing/corrupt snapshot, denied/full disk, persistent fault | Typed failure, no false success, valid snapshot retained, disk-independent error reporting |
| T-RAR-07 | Repeated recovery, same ID/hash and changed hash; spies fail on model/provider/graph/memory/settlement/reflection | Stable identity, one commit, conflicting content preserved, forbidden calls zero |
| T-RAR-08 | 30 reset batches: 100 committed + 10 pending, each snapshot <=1 MiB | All 300 recovered outputs correct; rank-29 duration <=2s; retain all samples and host/fixture metadata |
| T-RAR-09 | Credentials in configuration/environment/payload and URL-like content | Unknown fields excluded; sentinel values never persisted in archive/diagnostics; detected credentials reject the save |
| T-RAR-10 | Pre-existing legacy files and legacy output directories | Byte hashes unchanged; no automatic migration/indexing |
| T-RAR-11 | Traversal, malformed UUID, absolute/drive/ADS paths, symlink/junction escapes | Reject invalid inputs; zero writes outside root; no prose-controlled filenames |
| T-RAR-12 | Explicit/env/default root; optional save_reports export; same completed context exported twice; non-empty target | Shared resolver, preserved API shape, one canonical run, explicit export conflict and no target overwrite |
| T-RAR-13 | Kill lock owner, lock contention, cleanup failure after commit | OS ownership reclaimed on exit; bounded LOCK_BUSY; COMMITTED retained with cleanup warning |
| T-RAR-14 | Tamper bytes, missing file/marker, hash mismatch and unsupported versions | CORRUPT_ARCHIVE or UNSUPPORTED_VERSION; no silent repair or successful partial report |

## Benchmark fixture and limits

Restore the same fixture before each trial outside the timer. Include snapshots awaiting render, partially rendered snapshots and residual pending data after commit; ten runs awaiting publication remain the measured recovery set, and residual copies of already committed runs do not count as additional recovered runs. Use fixed snapshot sizes/content and configured Markdown/HTML output. Record the exact fixture digest and renderer settings.

Time starts immediately before recover_pending and includes lock acquisition, scans, snapshot/hash checks, rendering, retries/backoff if triggered, final rename, normal get_run validation and cleanup attempts. End after all ten outputs validate. Include every sample in the dataset. Larger inputs and arbitrary history scale have no two-second guarantee. All archive-specific tests use synthetic inputs and do not require live API credentials.
