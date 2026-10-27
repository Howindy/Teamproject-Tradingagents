# Runtime Policy Catalog — Report Archive

| Policy | Trigger | Deterministic action | Verification / monitor |
|---|---|---|---|
| POL-ARCH-01 | Completed CLI/API result | Extract allowlisted snapshot, save and commit automatically; expose separate archive result | T-RAR-01/12; MON-ARCH-01 archive_status |
| POL-ARCH-02 | Valid pending snapshot at startup | Reconstruct using saved identity, timestamp and renderer; no model calls | T-RAR-05/07; MON-ARCH-02 recovered_count |
| POL-ARCH-03 | Missing/corrupt snapshot | Safe identifiable error where intent is trusted; quarantine ambiguous fragments | T-RAR-06; MON-ARCH-03 invalid_snapshot_count |
| POL-ARCH-04 | Same ID/hash already valid | Return existing COMMITTED; clean redundant temporary data | T-RAR-07; MON-ARCH-04 duplicate_commit_count, target 0 |
| POL-ARCH-05 | Same ID/different hash | RUN_ID_CONFLICT; preserve destination; never allocate a different ID for recovery | T-RAR-03/07; MON-ARCH-05 conflict_count |
| POL-ARCH-06 | Incomplete query target | NOT_READY; exclude from successful history results | T-RAR-02/05; MON-ARCH-06 false_success_count, target 0 |
| POL-ARCH-07 | Committed bytes/manifest/marker invalid | CORRUPT_ARCHIVE; no silent repair or partial successful report | T-RAR-14; MON-ARCH-07 integrity_error_count |
| POL-ARCH-08 | Unsupported schema/renderer | UNSUPPORTED_VERSION; preserve original data | T-RAR-14; MON-ARCH-08 unsupported_version_count |
| POL-ARCH-09 | Root lock unavailable | Wait <=5 seconds then LOCK_BUSY; do not delete a live owner's lock | T-RAR-13; MON-ARCH-09 lock_wait_seconds |
| POL-ARCH-10 | Transient write error | Initial attempt plus two retries after 50/100 ms; preserve snapshot as RETRY_PENDING if exhausted | T-RAR-06; MON-ARCH-10 retry_count |
| POL-ARCH-11 | Disk cannot save diagnostics | Return safe code through result/terminal without depending on a failure file | T-RAR-06; MON-ARCH-11 write_failure_count |
| POL-ARCH-12 | Cleanup fails after commit | Keep COMMITTED and add CLEANUP_WARNING; retry cleanup later | T-RAR-13; MON-ARCH-12 cleanup_warning_count |
| POL-ARCH-13 | Path or credential violation | Reject before persistence/out-of-root writes; safe diagnostic only | T-RAR-09/11; MON-ARCH-13 boundary_rejection_count |
| POL-ARCH-14 | Non-empty/overlapping extra export target | EXPORT_CONFLICT; retain destination and canonical archive | T-RAR-12; MON-ARCH-14 export_conflict_count |
| POL-ARCH-15 | Forbidden model/provider/graph/memory call during recovery | Stop affected recovery; retain snapshot and prior valid artifacts | T-RAR-07; MON-ARCH-15 forbidden_recovery_calls, target 0 |
| POL-ARCH-16 | Benchmark timeout, wrong content or p95 above target | Fail acceptance; retain all samples; do not skip integrity checks | T-RAR-08; MON-ARCH-16 archive_batch_recovery_duration_seconds |

Normal listings use exact normalized ticker/date filters and stable creation-time-descending, ID-ascending ordering. Unknown run IDs return NOT_FOUND; no matches return an empty successful list. Failure entries appear as diagnostics, not complete report results. Cleanup applies only to obsolete temporary artifacts after verified commit; there is no automatic archive pruning.

Configuration resolution is explicit archive_dir, then TRADINGAGENTS_ARCHIVE_DIR, then results_dir/archive. Snapshot completion defines the recovery guarantee. Valid snapshots above 1 MiB are not truncated; they are outside the fixed QR-02 latency envelope. Observability contains safe IDs, codes, timestamps and durations, not full configuration or report bodies.
