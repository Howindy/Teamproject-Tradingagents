# FR-10 local real-response verification — 2026-11-25

**Result: all four candidate cases pass the versioned local five-gate checker.**

The submission now also includes executable checker/test files at the normal
repository paths. See [test commands and files](../../ci/fr10-report-checks.md);
the snapshots below remain the original evidence copies.
Application commit: `3d457be78fcf72c9aa3b5d1879396292d7b391bc`.
Model: official DeepSeek `deepseek-flash`, thinking explicitly disabled.
These records are local execution evidence, not GitHub check URLs or a new
human approval. No inaccessible temporary paths are needed to inspect them.

| Case | Actual report | Prompt/settings and provider evidence | Local result |
|---|---|---|---|
| FM-S01 | [AAPL complete](reports/FM-S01.md) | [prompts](prompts/FM-S01.json), [response](responses/FM-S01.json) | 5/5 |
| FM-S02 | [XOM missing concepts](reports/FM-S02.md) | [prompts](prompts/FM-S02.json), [response](responses/FM-S02.json) | 5/5 |
| FM-S03 | [missing comparison](reports/FM-S03.md) | [prompts](prompts/FM-S03.json), [response](responses/FM-S03.json) | 5/5 |
| FM-S04 | [cutoff-ineligible price](s04/report.md) | [request](s04/request.json), [metadata](s04/response-metadata.json) | [5/5](s04/result.json) |

S04's first answer was tool intent rather than a final report. The separate
final-stage request used the existing application wrap-up path without binding
tools; it made one request, zero retries and zero vendor calls. It finished
`stop`: 3,032 input + 4,050 output = 7,082 API tokens, 17.33 seconds.
Its P/E is `n/a: price_not_completed`; the other nine metrics are retained.

## Audit material

- [Current summary and artifact hashes](summary.json).
- [Earlier local replay](earlier-local-replay.json): the first three pass;
  the then-incomplete S04 is superseded only by the separate real rerun above.
- [Checker source snapshot](local-checker.py),
  [32 checker cases](local-checker-tests.py),
  [four final-stage wiring checks](final-report-replay-tests.py),
  [32-test console output](targeted-tests.txt).
- [Independent expected cases](reference-cases.json).
- [Original frozen-evaluator result](original-evaluation-result.json), preserved
  as unsuccessful; not rewritten to a pass.

The final-stage preparation/wiring plus selected existing regressions reported
38 passed, 9 deselected. Source snapshots here are audit copies; normal test
commands and their scope are described in the [local test notes](../../drafts/fr10-local-gates.md).

## Scope limits

This is evidence for four candidate reports, not a completed paired D1-D5 run.
The paired baseline S01 remains incomplete. The registered configuration and
GitHub workflow approval/execution status were not changed. Round-04 synthetic
examples retain their original offline status. No financial correctness,
completeness, generalization or cost guarantee beyond these bounded checks is
asserted; no independent human review is fabricated.
