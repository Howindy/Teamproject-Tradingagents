# CI Test Pre-Approval Positive-Path Probe

## 1. Status

- Status: Proposed test specification; pending human approval.
- Approval state: not approved; no test implementation may start before the
  approval described in Section 6.
- Branch: `verify-ci-approval-positive`, created from the `main` baseline.
- Purpose: validate the CI test-pre-approval gate's positive path.
- This is not a Round 1 plan and does not approve Round 1 or application work.
- This branch is for temporary CI validation and must not be merged into `main`.
- No Python test file exists yet. The future test file in Section 3 must be
  created only after approval.

## 2. Scope and exclusions

This specification covers only the existing local
`scripts/ci_checks.py::classify_paths()` behavior for two synthetic path inputs.
It does not test application behavior, network access, credentials, models,
vendor APIs, or CI workflow execution.

Excluded:

- changes to `scripts/ci_checks.py`, the CI workflow, gate logic, or application
  source;
- changes to `docs/ai-use-log.yaml` in this plan-only step;
- changes to `docs/plans/round-01.md` or any Round 1 scope;
- live tests, integration tests, model calls, or external data calls;
- replacement of the two assertions with a constant-true or unrelated test.

## 3. Exact files and test selection

- Test specification and Plan path: `docs/plans/ci-gate-positive.md`
- Future test file, created only after approval:
  `test/offline/test_ci_approval_probe.py`
- Code under test, read-only: `scripts/ci_checks.py`
- Selected test path for `contract-tests`:
  `test/offline/test_ci_approval_probe.py`

The future test file is the only code path changed by the implementation PR.
It must load `scripts/ci_checks.py` by project-relative file path, as the
existing gate tests do. It must not modify `scripts/ci_checks.py`.

The approved specification must name both the future test file and the selected
test path. This document names the exact path above. No other test path is
selected by this specification.

The planned local execution command is:

```text
python -m pytest -q test/offline/test_ci_approval_probe.py
```

The command is offline. It must not read `.env`, credentials, or external
resources, and must not call a model or data API.

## 4. Exact test assertions

### 4.1 Documentation path does not require code approval or AI log

- Test function name:
  `test_docs_path_does_not_require_code_approval_or_ai_log`
- Input:
  `classify_paths(["docs/ci-gate-positive-note.md"])`
- Independent expected outputs:
  - `docs_only is True`
  - `approval_applicable is False`
  - `ai_log_required is False`
  - `code == []`
  - `tests == []`
  - `semantic_required is False`
- The assertion uses only the static path string. No file needs to exist.

### 4.2 Python script path requires code approval and AI log

- Test function name:
  `test_script_path_requires_code_approval_and_ai_log`
- Input:
  `classify_paths(["scripts/local_analysis_helper.py"])`
- Independent expected outputs:
  - `docs_only is False`
  - `approval_applicable is True`
  - `ai_log_required is True`
  - `code == ["scripts/local_analysis_helper.py"]`
  - `tests == []`
  - `semantic_required is False`
- The assertion uses only the static path string. The input is a normal
  executable Python path under `scripts/`; no such file is created by this plan.
  No network, credentials, model, or file access is used.

### 4.3 Independence rules

- The two tests must be separate test functions.
- Each must assert its own expected booleans and path lists directly.
- The test must not use `assert True`, a vacuous assertion, or another test file
  as the verification subject.
- The test must not derive expected values from `classify_paths()` output.
- No FC or IR IDs are assigned by this CI-classification probe; it does not
  claim D1 coverage.

## 5. AI-use log consequence

The future `test/offline/test_ci_approval_probe.py` is executable code. Its
implementation PR must add an AI-use-log entry whose `files_changed` associates
the test path, unless an already-approved rule exempts it. This plan-only file
does not update the AI-use log. The future entry must record actual events and
must not invent approval, a run, or a test pass.

## 6. Approval flow and future PR fields

Before the future test file is created, a human must commit this specification,
review it, and provide a trusted GitHub approval event in this branch's same
temporary validation PR. A local statement, an approval on another PR, or an
invented approval does not satisfy this requirement. The approval event must
occur after the specification commit and before the first commit that changes
`test/offline/test_ci_approval_probe.py`.

The future implementation PR body must contain these exact fields:

```text
Plan: docs/plans/ci-gate-positive.md
Approved test specification: docs/plans/ci-gate-positive.md @ <PLAN_COMMIT_SHA>
Approval evidence: <GITHUB_REVIEW_OR_COMMENT_URL>
Implementation start: <FIRST_TEST_COMMIT_SHA>
Approved scope: CI classification probe; test/offline/test_ci_approval_probe.py
```

`<PLAN_COMMIT_SHA>`, `<GITHUB_REVIEW_OR_COMMENT_URL>`, and
`<FIRST_TEST_COMMIT_SHA>` are placeholders that must be replaced with real
values after the events occur. They must not be invented.

The approval reviewer must provide exactly one line with this prefix:

```text
APPROVED test-spec: docs/plans/ci-gate-positive.md @ <PLAN_COMMIT_SHA>
```

The approved value after `APPROVED test-spec:` must match the
`Approved test specification` PR field exactly after whitespace normalization.
The approval event must be a human GitHub review or comment, must not be from
the PR author or a bot, and must precede the implementation start.

The specification commit must be an ancestor of the implementation start. Any
change to this specification or these assertions after approval requires a new
approval. No approval or SHA is claimed by this unapproved document.

## 7. Contract-test expectations

After approval and creation of the future test file:

- `plan_test_paths()` must select exactly
  `test/offline/test_ci_approval_probe.py`;
- the approved specification must mention
  `test/offline/test_ci_approval_probe.py` as the changed code path and as the
  selected test path;
- The specification file must exist at the approved specification commit. The
  selected test file is created only after approval and must exist at the
  implementation head, where pytest collects and executes it.
- pytest must collect and execute both test functions;
- skipped, failed, errored, or zero-executed cases must fail the gate.

This specification does not itself execute tests and does not claim that either
test has passed.
