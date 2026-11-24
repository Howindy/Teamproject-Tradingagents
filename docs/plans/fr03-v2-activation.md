# FR-03 v2 activation specification

Independent activation decision requested for FR-03-FC05 / IR-12. Baseline main: 3121578ad98afcb4374f5228ca2506f6f7e1917c. The v2 implementation merged in PR #22. Approval of this specification authorizes publishing the following materials, updating the frozen-material tests and performing offline verification. Live provider request allowance for this change: zero.

## Exact materials

In docs/ci/data-availability-rubric.md change the heading to rubric v2, replace the draft status sentence with “Release policy: FR-03 v2.”, use rubric ID fr03-data-availability-rubric-v2, and replace the opening aggregate-threshold paragraph with:

All five cases and all three roles per case must execute with valid A/B/C grades. All C grades must pass. A/B needs_review grades are advisory and retain their original grades, excerpts and reasons. Record the advisory count alongside the release decision. Any failed dimension, critical contradiction, unresolved C, invalid grade, incomplete or duplicate matrix, malformed evidence, truncation or budget violation blocks release.

Expected LF-normalized rubric SHA-256: 977c52c1a2c4180c3135d931cab4177213244f73c4de49c89dedcd38e021f1d9

In docs/ci/semantic-suites/data-availability.yaml use the rubric version and digest above, the exact V2_THRESHOLDS mapping from the baseline runner and the following definition:

All role-delivery grades must pass. Unresolved coverage and contradiction grades are advisory. Explicit failures and evidence errors block release.

Expected configuration settings SHA-256: 55a697db3e57e048291d391572f52f3471b04039e8781765d216849de54e5ff3
Hash UTF-8 JSON of the parsed mapping after removing only the approval field, with sorted keys and compact separators. Record the actual reviewer login, UTC approval event timestamp and permalink in that field after approval. Record the resulting full YAML digest for verification. Preserve the five cases, all per-dimension scoring rules, dataset, provider/model settings, 20-request limit, and one repetition.

## Verification and files

Update test/offline/test_data_availability_evaluation.py to verify the registered materials, real approval, v2 settings, rubric digest and normal runner entry. Explicitly supply v1 fixtures where testing rejection of v1 materials or the v1 contract. Keep positive and negative tests for blockers and advisories. Record implementation and offline results in docs/ai-use-log.yaml and docs/review-memo.md.

Run the offline data-availability evaluation suite. Recompute both frozen digests. Verify that the registered config resolves and loads its materials. Replay archived replies from run 45459356876 (19 passed, 26 advisory, release pass) and run 45453248371 (S02 Manager contradiction, release fail). Verify the financial-metrics registry entry and shared evidence contract retain their behavior.

Activation takes effect when the independently reviewed change reaches trusted main. Formal evaluation of PR #13 requires a separately approved final candidate SHA and new evidence. Historical v1 records retain their original status.
