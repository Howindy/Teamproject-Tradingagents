# P07 maintenance specification for the FR-10 preparation check

## 1. Decision requested

Approve a test-only correction to P07 on Round-04A at `af50d74b9cccb08d0ac3ed7ae023cbb89f956955`. P07 was introduced to establish what [preparation PR #14](https://github.com/Howindy/Teamproject-Tradingagents/pull/14) delivered. Its final assertion currently compares the executing worktree with a moving `origin/main` and runs only when that ref exists. An unrelated change under `src/` on Round-04A therefore fails the historical claim. The change below retains the original preparation evidence and the current checks for deferred or obsolete activation paths. See the [original P07 scope](financial-metrics-integration.md) and the [Round-04A integration plan](round-04a.md).

## 2. Evidence and expected behavior

PR #14 was merged as `00833f4b281692c266bbd52c5955a4f40ec89493`. Its first parent is also the merge base of the two parents. Use these two distinct commit objects as the endpoints:

| Role | Immutable commit |
|---|---|
| Preparation base | `5c6e2caed5e4baceb136b5544ba5e283c0822cdb` |
| Reviewed preparation head | `88d47e712f7eac6e6babc8d2e1b0dc87d17c4b17` |

Both endpoints currently resolve to the same `src/` tree, `9cb5e297d58581e4c5b8628b40938b99b08d79da`. This observation corroborates the expected empty source diff. The test must perform the comparison itself.

| Assertion | Evidence to read | Expected result |
|---|---|---|
| Preparation introduced no application migration | Run `git diff --name-only <base> <preparation-head> -- src/` with both pinned commits. | Git succeeds and returns no paths. Any source addition, modification, rename or deletion in the net preparation delta fails the check. |
| Financials had not shipped in the preparation tree | Inspect the preparation head's tree at `src/tradingagents/financials`. | The path is absent. Later feature branches may implement FR-10 under that path. |
| Semantic evaluation was unapproved at handoff | Read `docs/ci/semantic_eval.yaml` from the preparation head. Parse that blob and use the existing configuration validator. | The document explicitly declares `status: unapproved`, validation has no errors and `approved` is false. An unreadable or malformed document cannot satisfy this assertion. |
| Deferred features remain guarded on the executing branch | Keep the live checks for absence of `src/tradingagents/run` and absence of the exact tokens `fr08_enabled` and `fr07_sec_enabled` in `src/tradingagents/default_config.py`. | Each assertion continues to inspect the current checkout, including on feature branches. A prohibited token with a false default still violates the existing guard. |

Keep the original P07 test as the entry point. A small test-local helper may accept a repository and two revisions so the real history check and the counterexample exercise the same comparison. Read objects locally without switching branches. Verify both commits and surface Git errors, missing history or missing required blobs as explicit failures with the affected revision or path. An absent remote-tracking ref has no bearing on the result.

## 3. Allowed files

- `test/offline/test_financial_metrics_evaluation.py`

## 4. Controls and counterexamples

Use the module's existing temporary Git repository setup and pytest temporary directories. Keep every source or configuration mutation for these controls inside the temporary fixture.

1. **Clean preparation followed by legitimate development.** Commit a minimal baseline with an existing source file and the default configuration. Create a preparation commit changing only documentation, followed by a later commit adding `src/tradingagents/financials/example.py`. While the later commit is checked out, the comparison of baseline and preparation head must pass. The fixture can have no `origin/main`.
2. **Violation inside the preparation range.** In the same fixture, compare the baseline with the commit containing the source addition as the purported preparation head. Require the shared preparation check to reject it and identify the changed path. Both revisions must exist so a missing object cannot cause a false-positive rejection.
3. **Live deferred guard.** With the clean historical pair fixed, introduce each forbidden condition independently in the current fixture tree: the `run` path, the `fr08_enabled` token and the `fr07_sec_enabled` token. Each variant must fail its corresponding live assertion even though the historical source diff stays empty.
4. **Unavailable evidence.** Supply an unresolved preparation revision to the historical check. Require a revision-resolution failure, distinct from the source-difference failure.

## 5. Verification and pre-approval

After approval, run the P07 cases first, then the entire financial metrics evaluation test module and the repository's default pytest selection. Record the candidate SHA, commands, JUnit results and any skips or failures. Compare with the four failures at `af50d74`: the original P07 case should turn green, all new controls should pass, and the three known Windows lock failures should be accounted for separately. Leave P01–P06, trusted scoring, semantic approval configuration, the mypy baseline, Windows lock tests and Round-04B outside this change.

Approval is pending. Before the first P07 test edit, an eligible non-author human reviewer on PR #24 should verify the two endpoints, the historical and live assertions, the counterexamples and the one-file allowance. Post the exact marker below with the full SHA of this document-only freeze:

```text
APPROVED test-spec: docs/plans/p07-preparation-scope-maintenance.md @ <full freeze SHA>
```

After approval, register the real event as an additional `Supplemental test specification` entry with its path, full SHA and approval URL. Preserve the existing approval entries and chronology. Changes to the pinned endpoints, guard semantics, expected results or allowed files require renewed review of the affected scope.
