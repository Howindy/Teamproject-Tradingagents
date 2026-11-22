# D4 Bug Diary

- Document status: Reusable significant-bug record template with two registered records; this does not claim that no other bugs exist.
- Registered records: BUG-01 (contract-test placeholder path, Closed) and BUG-02 (reported macOS errno.EDEADLOCK failures, Open).
- Purpose: Preserve symptoms, reproduction, classification, root cause, fix history, regression evidence, and any exposed invariant or test gap for important bugs.
- Related records: [Review memo](review-memo.md) and [Debt register](debt-register.md).

This file does not claim that the project has no bugs. It records only bugs that have actually been observed and judged important. A failed test is not automatically an application defect; it may be a test defect, fixture problem, environment block, dependency gap, or expected behavior change requiring review.

## 1. Recording rules

1. Add a record only after a real symptom has been observed. Do not create illustrative bugs or prefill a root cause, fix, or result.
2. Keep the lifecycle honest:
   - `Found`: symptom observed; cause not yet identified.
   - `Located`: root cause identified with evidence.
   - `Fix proposed`: a change is proposed but not implemented.
   - `Fixed`: a change exists, but independent re-verification is not complete.
   - `Re-verified`: the relevant regression test passed in the recorded environment.
   - `Closed`: re-verification is accepted and any follow-up is recorded.
3. A proposal is not a fix. A code change without a recorded re-run is not `Re-verified`.
4. Record actual versions, commands, inputs, and evidence. Do not invent timestamps, reviewers, commits, or pass results.
5. Link the relevant D1 requirement/FC, D2 invariant/ADR, review memo, and debt record when known. If no relation is known, write `None known` rather than guessing.
6. Preserve earlier findings when new evidence changes the diagnosis. Correct a prior statement explicitly instead of silently replacing history.
7. Use a stable ID such as `BUG-<sequence>-<short-slug>`; use the same ID in review and debt records.

## 2. Classification and impact guidance

Record a classification based on evidence. Common labels include behavior defect, test defect, fixture/data defect, environment or dependency failure, security or path-confinement defect, contract mismatch, and regression. Add a short impact statement covering affected entry points, outputs, state, reports, memory, or security boundaries.

A classification is not a severity threshold and does not create a new bug-acceptance rule. If the cause or impact is not yet established, say `Unknown` and keep the record open.

## 3. Bug record template

Copy this structure for each actual bug. Replace angle-bracket placeholders with recorded evidence or an explicit `not recorded`/`not applicable` value.

### BUG-`<sequence>`-`<short-slug>`

#### Identification

| Field | Recorded value |
|---|---|
| Bug ID | `BUG-<sequence>-<short-slug>` |
| Discovery time | `<UTC timestamp with timezone, or "not recorded">` |
| Round | `<round/plan reference, or "not recorded">` |
| Affected code/version | `<commit/tree and application/test version, or "not recorded">` |
| Current state | `<Found / Located / Fix proposed / Fixed / Re-verified / Closed>` |
| Related review memo | `<[RM-...](review-memo.md) link, or "none">` |
| Related debt record | `<[DEBT-...](debt-register.md) link, or "none">` |

#### Symptom

- Summary: `<one-sentence observable symptom>`
- Expected behavior: `<expected result and its D1/FC/IR or other approved source>`
- Actual behavior: `<actual result, error, output, or state>`
- When and where observed: `<entry point, command, environment, or artifact>`

#### Reproduction

- Controlled inputs: `<fixture/input values or immutable reference>`
- Preconditions: `<configuration, environment, state, feature flags, or "none known">`
- Steps: `<numbered minimal steps>`
- Observed evidence: `<link to raw output, report, log, or artifact>`
- Reproducibility: `<always/intermittent/not reproduced; actual observation count>`

Do not include real credentials or secret values. Use synthetic values for security reproductions.

#### Classification and impact

- Classification: `<behavior/test/fixture/environment/security/contract/regression/unknown>`
- Affected scope: `<entry points, modules, outputs, state, persistence, or security boundary>`
- Impact: `<actual user/developer/security impact>`
- Severity or prioritization basis: `<approved project basis, or "not assigned">`

#### Requirement, architecture, and test linkage

- Requirements / FCs: `<actual IDs, or "None known">`
- Invariants / ADR decisions: `<actual IR/ADR IDs, or "None known">`
- Runtime policies: `<actual RP IDs, or "None known">`
- Existing tests or evidence: `<test IDs/paths/links, or "None known">`

#### Root cause

- Status: `<Unknown / Confirmed>`
- Cause: `<specific cause, or "Unknown; not yet established">`
- Evidence: `<code path, controlled experiment, trace, or link>`
- Why the bug escaped detection: `<missing/weak test, uncovered boundary, environment difference, or "Unknown">`

Do not fill this section from suspicion alone. Keep it `Unknown` until evidence supports a cause.

#### Fix and change history

- Fix approach: `<proposed approach, or "None yet">`
- Actual change implemented: `<files/behavior/commit/PR, or "Not implemented">`
- PR or review reference: `<[RM-...](review-memo.md) or PR link, or "None">`
- Compatibility or scope impact: `<required interface/D1/D2 changes, or "None identified">`
- State at this point: `<Fix proposed / Fixed; not yet re-verified>`

A planned change belongs in `Fix approach`. Do not describe it as completed until an actual change is recorded.

#### Regression and re-verification

- New regression test: `<test name/path and cited FC/IR, or "None added">`
- Reused test: `<existing test/path and coverage, or "None">`
- Exact command or CI run: `<command/working directory or CI reference>`
- Environment and input version: `<environment and fixture/version>`
- Expected result: `<independent expected result>`
- Actual result: `<actual result>`
- Status: `<Re-verified / Failed / Not run / Blocked>`
- Evidence: `<link to output or artifact>`

If the test was not run or was skipped, do not record `Re-verified`.

#### Exposed invariant or test gap

- Invariant gap: `<IR/contract that was not enforced, or "None identified">`
- Test gap: `<missing negative/boundary/integration check, or "None identified">`
- Other QA gap: `<fixture/telemetry/environment/documentation gap, or "None identified">`
- Follow-up record: `<[DEBT-...](debt-register.md) link or review action, or "None">`

#### Status, remaining work, and follow-up

- Current state: `<Found / Located / Fix proposed / Fixed / Re-verified / Closed>`
- Unresolved items: `<specific open questions, missing evidence, or "none recorded">`
- Follow-up actions: `<owner/action/trigger, or "not assigned">`
- Closure evidence: `<re-verification and human review link, or "not closed">`

Important bugs may remain open with partial information. Leave unresolved fields explicit rather than inventing completeness.

## 4. Registered records

### BUG-01-contract-test-placeholder-path

- State: `Closed`. Related review: [RM-9-R1](review-memo.md#rm-9-r1).
- Discovery: PR #7 [CI run 44921168528](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/44921168528), `contract-tests`; symptoms are recorded in `docs/plans/ci-contract-test-paths-fix.md`.
- Classification/impact: CI test-path contract defect causing a false contract-test failure; no application behavior change.
- Symptom: An explanatory placeholder was extracted as a real test path and failed existence checking, although a real test path was also present.
- Expected behavior: Ignore only the basename consisting of three ASCII periods followed by `py`; still extract, sort, deduplicate and existence-check real paths. Missing real tests and placeholder-only specifications still fail.
- Root cause: `CONTRACT_TEST_PATTERN` permits periods in path segments; `plan_test_paths` did not filter the exact placeholder before existence checking. Reproduce with the old extractor and the mixed real/placeholder specification. Why earlier tests missed the case was not recorded.
- Fix: A narrow exact-basename filter at the extraction boundary; no existence-based filtering or weakening of `contract_test_plan`. Implementation: `scripts/ci_checks.py` and `test/offline/test_ci_gates.py`, commit `ff3e32bf952538a1f8c5c37b8129e765f6865d1d`.
- Specification: `docs/plans/ci-contract-test-paths-fix.md @ fbbafc61dcd5bf6c527cabfa6af3b9a3a3942de1`; six approved regression scenarios T1-T6 map to the existing test functions.
- Review/merge: [PR #9](https://github.com/Howindy/Teamproject-Tradingagents/pull/9), APPROVED by `espino2233` at `2026-11-21T16:21:14Z`; empty review body, no written rationale. Merged at `2026-11-21T16:21:26Z` as `43ac0bb27ca29e7eff797d06689bfbb61e084046`.
- Closure evidence: [PR run 44923393413](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/44923393413) completed/success at head `ff3e32bf952538a1f8c5c37b8129e765f6865d1d`; [main run 44924133256](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/44924133256) completed/success at head `43ac0bb27ca29e7eff797d06689bfbb61e084046`. These are user-provided, checked workflow-level facts, not separate inspection of every job.
- Local re-verification: AI-038 preserves user-reported `76 passed in 8.07s`, pre-fix `5 failed, 1 passed in 0.36s`, target Ruff passed, mypy baseline `errors=[]`/`fixed=[]`, and clean diff check. No new test run is claimed by this record.
- Remaining work: None recorded for this defect. No product FC, business invariant, new debt, or unrelated repair is introduced.

### BUG-02-macos-windows-lock-tests

- State: `Open`.
- Discovery/evidence: User-reported local macOS post-implementation regression, summarized in AI-045. Affected file: `test/offline/test_cache_writes.py`.
- Symptom: Three Windows-lock test cases fail because `errno.EDEADLOCK` is absent in the reported macOS environment. The historical full run had `3 failed, 1 skipped, 1 deselected`; it was not fully green.
- Classification/impact: Test/environment/platform failure; not established as an application-introduced regression. The baseline/current comparison in AI-045 reports the same three failures in both versions.
- Root cause of the observed failure: The cases reference a constant absent in that environment. No claim about all platforms or a complete cross-platform policy is made.
- Historical verification: `Failed` in the reported macOS runs. This closeout task did not rerun those cases; it does not replace their historical result with `Not run`.
- Fix: None recorded. No application/test change, guard, skip policy, or waiver is approved here.
- Remaining work: Decide how to handle the affected cases on non-Windows hosts and verify the selected treatment. No owner or closure evidence is recorded. Successful remote workflows are distinct evidence and do not fix the macOS issue.
- Requirement/IR/ADR/debt linkage: None assigned; no additional product acceptance condition is introduced.
