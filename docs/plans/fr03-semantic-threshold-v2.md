# FR-03 data-availability release policy v2

Proposed for independent test pre-approval. Applies to FR-03-FC05 / IR-12.
The release decision measures research-role delivery and absence of detected
material contradictions. It offers weaker assurance of factual coverage than
v1. A reply may omit a coverage explanation and still meet this policy.

Require all five cases, all three distinct roles per case, and exactly A/B/C
for each combination. Every C must pass. Any failed dimension, critical
contradiction, unknown grade, incomplete matrix, invalid provider response,
truncation, evidence error or budget violation blocks release. A/B
needs_review grades are advisory. Preserve their original grades, counts,
excerpts and reasons in the detailed evidence and show the advisory count
alongside the release decision. No minimum count of passed A/B grades.

Change only the data-availability suite's config, rubric, runner and offline
controls: docs/ci/semantic-suites/data-availability.yaml,
docs/ci/data-availability-rubric.md, scripts/data_availability_eval.py and
test/offline/test_data_availability_evaluation.py. Record maintenance in
docs/ai-use-log.yaml and docs/review-memo.md. Use a new, distinctly versioned
rubric and approved configuration digest. Expose nonblocking observations
separately from blocking review reasons; preserve the shared runner contract
and financial-metrics thresholds. Retain the case set, model, one repetition,
and twenty-request maximum.

## Independent offline acceptance controls

- All C passed and all A/B unresolved yields release pass with 30 advisories.
- Any single failed A, B or C, unresolved C, or critical finding blocks.
- Duplicate/missing role, missing/extra dimension, unknown value or truncated
  response blocks even when all remaining scores pass.
- Runner/record normalization retains the suite decision and all advisory
  evidence; a blocking result or malformed record cannot produce success.
- Replay 45459356876 to compare policies: v1 needs_review; v2 expected pass
  with 19 passed, 26 advisory and zero failed. No stored v1 result is amended.
- Replay 45453248371 using the PR 21 scorer: its S02 Manager contradiction
  must still block release under v2.
- Apply the new standard to future candidates uniformly. Activating v2
  requires independent approval; a formal run needs fresh evidence under
  the approved material version and a separately authorized request budget.
