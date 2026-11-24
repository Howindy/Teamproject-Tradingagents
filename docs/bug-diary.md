# D4 Bug Diary

- Document status: Reusable significant-bug record template with three registered records; this does not claim that no other bugs exist.
- Registered records: BUG-01 (contract-test placeholder path, Closed), BUG-02 (reported macOS errno.EDEADLOCK failures, Open) and BUG-03 (optional price failure discarded SEC facts, Re-verified).
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

#### Round 2 post-implementation reproduction update (2026-11-22)

- Context: default offline regression after the C-09 core work; integration was excluded.
- User-reported result: `3 failed, 1615 passed, 1 skipped, 1 deselected, 20 warnings, 100 subtests passed in 15.37s`.
- Same three affected cases in `test/offline/test_cache_writes.py`:
  - `test_on_windows_the_lock_is_waited_for_while_another_writer_holds_it`
  - `test_on_windows_a_lock_that_cannot_be_taken_is_reported_not_retried_forever`
  - `test_on_windows_a_held_lock_is_reported_when_not_waiting`
- Assessment: the failures remain consistent with the missing `errno.EDEADLOCK` cause already recorded above. No additional failure was reported in this run. This does not prove zero regressions on all platforms or replace the historical failure with a pass.
- State: remains `Open`. No fix, guard, skip policy, waiver, or cross-platform treatment is approved by this update.
- Evidence: `/private/tmp/cs5351-round02/regression.xml` (local temporary evidence; user-reported; Codex read the JUnit read-only; OpenCode did not execute the run or read the report; not committed or remote CI evidence).
- Remaining work: unchanged; decide and verify a non-Windows treatment, with no owner or closure evidence recorded.

### BUG-03-optional-price-failure-discards-sec-facts

#### Identification

| Field | Recorded value |
|---|---|
| Bug ID | `BUG-03-optional-price-failure-discards-sec-facts` |
| Discovery time | Not recorded; teammate P1 report captured in `AI-FM-PRICE-ISOLATION-001` (2026-11-25). |
| Round | FR-10 feature integration, PR #19; regression extension in PR #25. |
| Affected code/version | `src/tradingagents/financials/sec_provider.py` before commit `33f3eb9`; regression file `test/offline/test_sec_financial_provider.py`. |
| Current state | `Re-verified` |
| Related review memo | No dedicated RM record; see [PR #19](https://github.com/Howindy/Teamproject-Tradingagents/pull/19) and [PR #25](https://github.com/Howindy/Teamproject-Tradingagents/pull/25). |
| Related debt record | None. |

#### Symptom

- Summary: SEC financial facts were retrieved successfully, but a timeout or invalid value from the optional Yahoo price read caused metrics that depend only on SEC facts to become unavailable too.
- Expected behavior: A price failure should affect only the annual P/E row; the other nine metrics should remain computed from their complete SEC inputs. This follows FR-10-FC06 and FR-10-FC10 and the failure-isolation intent of RP-36.
- Actual behavior: Before the fix, the price exception escaped `SecCompanyFactsProvider.fetch()` before it returned the successfully acquired facts. `FinancialMetricProvider.get()` caught the exception and replaced the whole input with `data_entry_failure`, so every row became `n/a` instead of only `pe_fy`.
- When and where observed: FR-10-enabled Fundamentals Analyst material, exercised through the provider, metric factory and calculator with controlled SEC and Yahoo substitutes.

#### Reproduction

- Controlled inputs: The AAPL fixture in `test/offline/test_financial_metrics.py` (`DATA`), with valid SEC `companyfacts` and a first `yahoo.market.completed_close` call that raises `TimeoutError`; later calls return the fixture close. The current parameterized test also covers `Infinity`, `NaN` and a binary-float quote.
- Preconditions: FR-10 is enabled through an injected SEC provider or `fr10_sec_enabled`; the run has an active analysis scope; no network access is required.
- Steps:
  1. Monkeypatch `sec_edgar.company_facts` to return the valid AAPL companyfacts payload.
  2. Monkeypatch `market.completed_close` to fail on the first price read and succeed afterwards.
  3. Build the metrics factory with `SecCompanyFactsProvider` and call it for `AAPL` on `2025-08-05`.
  4. Inspect the ten rows and then run a second analysis scope with a successful price read.
- Observed evidence: [`test_sec_financial_provider.py:230`](test/offline/test_sec_financial_provider.py#L230), `test_price_failure_preserves_sec_metrics_and_next_analysis_recovers`. The recorded pre-fix run had three failing cases (timeout, Infinity, NaN); after the fix the same targeted group recorded 90 passed. PR #25 added the float-quote case and the recovery assertion.
- Reproducibility: Deterministic in the controlled test; no intermittent network condition is required.

#### Classification and impact

- Classification: External-dependency exception handling and fault-isolation defect.
- Affected scope: `SecCompanyFactsProvider.fetch()`, the FR-10 metric factory/cache, the rendered financial-metrics table and the annual P/E row; no formal recommendation field.
- Impact: A successful SEC fetch could be discarded because an optional price source failed, hiding nine valid metrics and producing an unnecessarily unavailable analyst table. It did not grant trade authority or change SB-01/FR-04 decisions.
- Severity or prioritization basis: Reported by a teammate as a P1 integration issue; no separate project severity scale is introduced.

#### Requirement, architecture, and test linkage

- Requirements / FCs: `FR-10-FC06` (fiscal-year P/E and price evidence), `FR-10-FC10` (explicit degradation without aborting valid analysis).
- Invariants / ADR decisions: `ADR 002` D-201–D-203; no dedicated IR number was assigned to this narrow failure. The exposed property is stated in the invariant-gap section below.
- Runtime policies: `RP-36` (FR-10 disabled/unsupported/provider-failure degradation).
- Existing tests or evidence: [`test_sec_financial_provider.py:230`](test/offline/test_sec_financial_provider.py#L230); `AI-FM-PRICE-ISOLATION-001`; `AI-FR10-SOURCE-CONTRACTS-001`; commit `33f3eb9`; PR #19; PR #25.

#### Root cause

- Status: Confirmed.
- Cause: `_price()` was called inside `SecCompanyFactsProvider.fetch()` before constructing the `FinancialInputs` return value. In the pre-fix source, the call was an unguarded expression in the same execution path as the already selected SEC facts. A `TimeoutError` or another price-read exception escaped `fetch()`. The broader `FinancialMetricProvider.get()` boundary then caught it and substituted `FinancialInputs(..., issues=("data_entry_failure",))`, so the calculator saw no facts and marked every metric unavailable.
- Evidence: The diff in commit `33f3eb9` wraps only the price read in `try/except` and records `price_availability_unknown`; the current test asserts nine computed rows and a P/E-only `n/a` row. See [`sec_provider.py:255`](src/tradingagents/financials/sec_provider.py#L255).
- Why the bug escaped detection: The initial tests exercised a successful price path and did not inject a failure at the optional price boundary. They therefore did not distinguish "SEC facts acquired" from "price evidence acquired".

#### Fix and change history

- Fix approach: Isolate the optional price source at its own boundary. Preserve the SEC facts and return `price=None` with `price_availability_unknown` when the price read raises. Only the annual P/E row becomes unavailable; the other nine rows continue to use their complete inputs.
- Actual change implemented: Commit `33f3eb9` added the narrow `try/except` around `_price()` in `SecCompanyFactsProvider.fetch()`. The later source-contract repair in PR #25 retained that boundary and extended the regression inputs to include a binary-float quote, which is rejected as `price_precision_unknown` without discarding the facts.
- PR or review reference: [PR #19](https://github.com/Howindy/Teamproject-Tradingagents/pull/19), commit [`33f3eb9`](https://github.com/Howindy/Teamproject-Tradingagents/commit/33f3eb958de9bd6b525cd42c8d392a6cf806c5f9); [PR #25](https://github.com/Howindy/Teamproject-Tradingagents/pull/25), commit [`dd47a4e`](https://github.com/Howindy/Teamproject-Tradingagents/commit/dd47a4e555a301bfec2346fec1a41071c31478ff).
- Compatibility or scope impact: No formal rating, SB-01, FR-04, FR-03 availability or graph-state change. The degraded path adds an explicit P/E reason and leaves the other metric rows intact.
- State at this point: `Fixed`; targeted regression was recorded after the fix.

#### Regression and re-verification

- New regression test: [`test_price_failure_preserves_sec_metrics_and_next_analysis_recovers`](test/offline/test_sec_financial_provider.py#L230), parameterized over `timeout`, `infinity`, `nan` and `float` (the float case was added in PR #25). It cites FR-10-FC06/FC10 in its docstring.
- Reused test: None required; the existing financial-metric and SEC-adapter suites were also exercised in the recorded target run.
- Exact command or CI run: The exact original command was not recorded. The evidence is the targeted run summarized in `AI-FM-PRICE-ISOLATION-001` (90 passed) and the PR #25 targeted run summarized in `AI-FR10-SOURCE-CONTRACTS-001` (460 targeted tests passed on macOS/Python 3.12). A reproducible command from the project root is:
  `python -m pytest -q test/offline/test_sec_financial_provider.py::test_price_failure_preserves_sec_metrics_and_next_analysis_recovers`
- Environment and input version: Controlled offline substitutes; AAPL fixture from `test_financial_metrics.DATA`; analysis date `2025-08-05`; no live Yahoo or SEC request.
- Expected result: The first nine rows remain computed with their fact IDs and sources; `pe_fy` is `n/a` with `price_availability_unknown` (or `price_precision_unknown` for a float quote) and retains the annual EPS evidence; one price attempt occurs per analysis; a new analysis scope recovers all ten computed rows.
- Actual result: The current regression test asserts exactly those outcomes. The recorded targeted runs passed after the fix.
- Status: `Re-verified` (recorded evidence, not a new execution performed by this diary update).
- Evidence: [`test_sec_financial_provider.py:230`](test/offline/test_sec_financial_provider.py#L230); `AI-FM-PRICE-ISOLATION-001`; `AI-FR10-SOURCE-CONTRACTS-001`.

#### Exposed invariant or test gap

- Invariant gap: The property "a failure of an optional input for one metric must not suppress metrics whose required inputs are complete" was not enforced. No formal IR number was assigned; the property should be treated as part of FR-10-FC06/FC10's degradation contract.
- Test gap: The original suite had no injected failure at the optional price boundary and did not verify next-analysis recovery. The new parameterized regression covers timeout, non-finite values, float precision and recovery.
- Other QA gap: The fix relies on a broad `except Exception` at the price boundary; the test set now makes the intended narrow behavior observable, but it is not a universal exception taxonomy.
- Follow-up record: None; no separate debt item is opened by this record.

#### Status, remaining work, and follow-up

- Current state: `Re-verified`.
- Unresolved items: No dedicated review-memo record was created for the fix; the PR #25 merge and targeted test records are the current evidence. No live-provider validation is claimed.
- Follow-up actions: None assigned; keep the price-boundary regression in the FR-10 suite.
- Closure evidence: The regression test above and the recorded targeted runs; no new run was performed for this diary update.
