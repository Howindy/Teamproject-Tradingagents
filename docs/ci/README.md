# CI Gate Operation

This directory contains the implementation notes and the single semantic
configuration container for the CI described in [`CI.md`](../../CI.md). The
documents and scripts implement gates; they do not approve application work,
replace branch protection, or prove live model quality.

## Approval record

- Approval basis: the human user approved the then-current `CI.md`
  implementation scope and gate-test specification in that OpenCode session.
- Approval date recorded from the session environment: `2026-11-18`. The exact
  wall-clock time was not supplied; no time is invented here.
- Original approved document: `CI.md`, SHA-256
  `208dd88da792d1f120c285332d6a67b78c40cf1b42bc89a5fb321001ba821385`,
  45,368 bytes.
- Original approved scope: implement the CI files listed in `CI.md` section 5,
  install the necessary CI-only tools in an isolated environment, add gate
  tests, wire the push/PR workflows, add the controlled semantic entry, and
  record actual verification. The approval excludes Round 1 application
  development.
- Security-review trim authorization: the human user separately authorized
  this specific CI trim in the current session. That version had SHA-256
  `4c8b097e1bd543640fd176ce51d97b562450880e2303d2ca7709c2c9896cc7f9`.
  The trim keeps the ADR reference check and all other gates, removes the
  GitHub review query from the security-path job, and leaves human approval to
  branch protection.
- Five-defect repair authorization: the human user separately approved the
  prior repair scope and its positive/negative test expectations. That version
  had SHA-256
  `4cf22ee8b6ce1c5b3d08547b89b0466c8605391739e8a4838b0271c33a20f481`.
- Contract-execution/trusted-version repair authorization: the human user
  separately approved the prior structured contract-result and trusted-tool
  checkout fixes. That version had SHA-256
  `71715ac6c142575412c19a041da1f588162d951ae24baf9e8870a54e183d12d8`.
- Scope/live/classification repair authorization: the human user approved the
  prior test-approval scope, optional-live, path-classification, approved-spec
  binding, and changed-scope repair. That version had SHA-256
  `a28ba27413fa770b7079991dfba2a0dc5e40148c808184388629ca80ae14b751`.
- Second-round prompt/code classification repair authorization: the human user
  approved the prior `prompts/` runtime-path, code-outside-`src/`, docs
  executable-code, and semantic-diff scope repairs. That version had SHA-256
  `1ecbafb7a36010e9fb71eeb1255818f653a6d1075e1af79d3be2cf2ef3228571`.
- src-outside approved-test association repair authorization: the human user
  approved the prior contract-test association repair for executable code
  outside `src/`. That version had SHA-256
  `252b61f925054fd4c45ad53367e7c27efa5089775c73ace817a581480eacf5f9`.
- Semantic/AI-log scope correction authorization: the human user approved the
  mixed-file semantic-trigger and AI-use-log blocking corrections. That version
  had SHA-256
  `1fd2fcaddea44af1c9f1dfbe79f6e414f15271409f5860e15986ad29e05a4e66`.
- Documentation-only baseline synchronization: later non-behavioral edits
  aligned `CI.md` with the current local CI, test inventory, and historical
  record wording. That version had SHA-256
  `059687c4ff8141b9852c3c0e2b71779121b384f4ead89ab22fbfa3d967efddd7`,
  58,684 bytes. This record documents a pure documentation sync; it does not
  extend, renew, or replace any approval scope above.
- Current local-verification note, not an approval: `CI.md` was later updated
  on `2026-11-21` with the current pre-commit local verification record. The
  SHA-256 `798f271af0dcdc34e5bc0296dede18125a0fa371a24a31bcebcc139d973f3bf5`
  and 59,699-byte count recorded for that pre-closeout version are historical;
  a later status-only clarification changed the file, and no new hash is
  claimed. The historical hashes and approval scopes above remain unchanged;
  this note does not mark any version as approved.
- Exclusions: no application behavior, D1 requirements, historical records,
  permission controls, test weakening, automatic push/merge, paid API calls, or
  GitHub settings changes.

The test-pre-approval gate cannot verify this one-time pre-approval as a GitHub
event. Future PRs must use the evidence convention below.

## Related real approvals and execution evidence

- Round 1: `docs/plans/round-01.md @ a8ec42ecdf4199f91d3001fc6e2b1e887a0c5e41`; test and safety pre-approvals, final review, merge, and the PR/main workflow runs are recorded in [RM-7-R1](../review-memo.md#rm-7-r1). This covers the C-08 core only; no integration or complete SB-01 acceptance follows.
- Contract-test path fix: PR #9, recorded in [RM-9-R1](../review-memo.md#rm-9-r1). That was CI maintenance, not an application FC.
- Round 2 core specification: PR #10 records a fixed-version pre-approval of `docs/plans/round-02.md @ 8ad99c25ea1acd77b6e019fbe3c357899e8fc535` ([comment 7073333663](https://github.com/Howindy/Teamproject-Tradingagents/pull/10#issuecomment-7073333663)). The current work is documentation closeout only, C-09 is not implemented, and this specification pre-approval is not safety-critical implementation approval, execution evidence, or final acceptance.
- The Round 1 and PR #9 GitHub facts are workflow-level; the PR #10 record is a fixed-version specification pre-approval, not implementation or execution evidence. Individual job results, branch-protection enforcement, permission enforcement, trusted semantic evaluation, and optional live evidence remain unverified.

## Files

- `scripts/ci_checks.py`: classification/build configuration, approval, schema,
  AI-use-log, API, permission, security-path ADR, trusted evidence, live JUnit,
  contract-test selection, mypy-baseline, and aggregate checks.
- `scripts/ci_semantic_eval.py`: config validation and the controlled
  success/not-applicable entry.
- `test/offline/test_ci_gates.py`: shared positive and negative gate tests.
- `.github/workflows/ci.yml`: push/PR jobs and the PR-only `aggregate` check.
- `.github/workflows/trusted-evaluation.yml`: manual trusted semantic run with
  optional live evidence.
- `.github/requirements-ci.txt`: CI-only tool pins.
- `mypy.ini` and `mypy-baseline.txt`: explicit type-check scope and the exact
  existing-diagnostic baseline.
- `docs/ci/semantic_eval.yaml`: unapproved configuration container.

## Test pre-approval fields

An applicable code/test or runtime-prompt PR must put these fields in its body. Code outside `src/` (including `scripts/**/*.py`, `scripts/**/*.sh`, `tools/**/*.py`, `setup.py`, root executables, and `docs/**/*.py`/`docs/**/*.sh`) is still code; non-code documentation and `pyproject.toml`/`requirements.txt` configuration do not require them:

```text
Plan: docs/plans/round-01.md
Approved test specification: <path and commit SHA>
Approval evidence: <GitHub review or comment URL>
Implementation start: <first committing SHA that changes approved paths>
Approved scope: <FC/IR IDs and affected test paths>
```

The `approval` command verifies the event through the GitHub API, rejects the
PR author and bot reviewers, and requires exactly one explicit approval line:

```text
APPROVED test-spec: <exact Approved test specification value>
```

The phrase must match the PR field exactly; `Not approved`, `Approval pending`,
an `APPROVED` review without the phrase, or a phrase for a different version
fails. The approval event must precede the first implementation commit, the
approved specification commit must be ancestral, and scope changes after
approval require a new approval. Git ancestry and author timestamps alone
cannot prove the real implementation order; a trusted human approval event is
still required, and this limitation remains. No new approval platform is
introduced. The changed-scope check uses IDs added on changed diff lines and
changed test paths, not every ID present in the full file. Round 1 was an
unapproved example when this convention was written; its later real approval is
recorded in RM-7-R1 and does not change the gate's negative-sequence
requirement.

## Evidence format

Trusted semantic records are JSON artifacts containing:

- `candidate_sha`
- `workflow_sha` (the default-branch workflow commit)
- `run_id`
- `kind`: `semantic`, `semantic-noop`, or optional `live`
- `status`: `passed` or `not_applicable`
- `config_version` for semantic evidence
- `reason` and `reviewed_by` for a reviewed not-applicable determination
- `executed` and `collected_only` for optional live evidence

The trusted workflow writes `semantic-eval/evidence` or
`semantic-eval/not-applicable` for merge-blocking semantic evidence, and may
write optional `live-tests/evidence` to the candidate SHA.
The PR evidence check verifies the status, repository, trusted workflow path,
run `head_branch` equal to the repository default branch, manual dispatch,
successful run, candidate artifact record, and configuration version. The run
`head_sha` is the trusted workflow version and must match the artifact record
`workflow_sha`; it does not have to equal the candidate SHA.

## Commands

```bash
python scripts/ci_checks.py classify --base "$BASE" --head "$HEAD"
python scripts/ci_checks.py approval --pr-body-file pr-body.txt \
  --base "$BASE" --head "$HEAD" --repo owner/repo --pr 1 --token "$GH_TOKEN"
python scripts/ci_checks.py schema \
  --requirements docs/req/requirements.yaml --schema docs/req/req-schema.json
python scripts/ci_checks.py permissions --path .opencode/permissions.jsonc
python scripts/ci_checks.py api
python scripts/ci_checks.py security-paths --pr-body-file pr-body.txt \
  --base "$BASE" --head "$HEAD"
python scripts/ci_checks.py ai-log --base-log base-log.yaml \
  --head-log docs/ai-use-log.yaml --base "$BASE" --head "$HEAD"
python scripts/ci_checks.py evidence --candidate "$HEAD" \
  --repo owner/repo --default-branch main --token "$GH_TOKEN" \
  --semantic-config docs/ci/semantic_eval.yaml \
  --semantic-required
python scripts/ci_checks.py contract-tests --pr-body-file pr-body.txt \
  --base "$BASE" --head "$HEAD"
python scripts/ci_checks.py live-result --junit "$RUNNER_TEMP/live.xml"
python scripts/ci_checks.py aggregate --needs-json "$NEEDS" \
  --required "classify,test-approval,requirements-schema,static,type-check,dependency-check,regression,smoke-install,security-paths,ai-use-log,evidence-check,contract-tests" \
  --applicable "test-approval=$APPROVAL_APPLICABLE,security-paths=$SECURITY_APPLICABLE,ai-use-log=$AI_LOG_REQUIRED"
python scripts/ci_checks.py mypy --output mypy-current.txt --baseline mypy-baseline.txt
```

The gate tests use temporary Git repositories, temporary files, and synthetic
GitHub responses:

```bash
pytest -q test/offline/test_ci_gates.py
```

## Push/PR split

- `push` runs basic checks and does not create a successful `ci / aggregate`.
- `pull_request` checks out `github.event.pull_request.head.sha`, not the merge
  ref, and adds the PR-only gates, including `contract-tests`.
- `ci / aggregate` is the required PR check. An applicable conditional job that is skipped fails the aggregate; a job whose classification is explicitly false may be skipped. Missing or invalid applicability values fail closed.
- Known build configuration is classified explicitly, but `setup.py` and other executable code are not exempt. Executable code under `scripts/`, `tools/`, and `docs/` enters the existing approval/log path; arbitrary scripts use the generic code path, while the known CI scripts use governance gate tests. Unknown non-code paths still run the generic checks and are not treated as documentation; a missing or unreadable diff fails closed. Renames are checked by both old and new paths.
- A manual trusted evaluation does not modify the earlier failed PR run. Rerun
  the PR CI on the same candidate SHA after evidence is written.

## Contract tests

The `contract-tests` job selects actual tests rather than trusting plan prose:

- all executable code changes, including code outside `src/`, require the
  existing `Plan`, `Approved test specification`, and `Approved scope` fields;
  the test-approval job remains the authoritative approval check;
- the job reads the `Approved test specification` path at its approved commit,
  not the Plan’s current content; Plan and specification may be different
  files;
- the approved specification must exist and name each changed code path and
  the selected `test/offline/`/`test/live/` paths; missing paths, unnamed code
  paths, missing test files, zero executed cases, skipped selected cases,
  failures, and errors fail;
- a shared approved specification and shared test path may cover multiple
  related code files;
- only the current approved/changed scope is required; unimplemented
  out-of-scope FCs are not scanned;
- governance code may use `test/offline/test_ci_gates.py` only when the
  approved specification names both the governance code path and that gate
  test; non-code governance changes use gate/permission checks; arbitrary helper
  scripts are not automatically covered by fixed CI tests;
- pure documentation and build configuration require no application FC test;
- plan text, `V-*` rows, or fixed baseline security tests are not accepted as
  new-feature coverage.

## Runtime prompt and semantic classification

- `prompts/*.yaml` and other supported runtime prompt files under `prompts/` trigger semantic evaluation and AI-use-log checks.
- Python prompt definitions under the agent/model/graph/CLI scopes are compared between the old and new Git versions using AST-level full assignment/call/function snapshots; long prompt text changes in the middle, replacement, or deletion are detected. Ordinary control-flow changes outside prompt definitions do not trigger semantic evaluation.
- Mixed files are content-sensitive: `default_config.py` and `llm_clients/factory.py` compare model-related dict entries/assignments/functions; `model_catalog.py` and `capabilities.py` compare model data definitions; `agents/context.py`, `structured.py`, and `memory/reflection.py` use prompt-definition snapshots. Comment, formatting, output-path, and unrelated logic changes do not trigger semantic evaluation.
- `Prompt.md` is a static launch document, not a runtime prompt, and does not trigger semantic evaluation.
- `scripts/**/*.py`/`.sh`, `tools/**/*.py`, `setup.py`, root executables, and `docs/**/*.py`/`.sh` are code for approval/log purposes; ordinary Markdown and images remain documentation. Arbitrary helper scripts are not automatically covered by fixed CI gate tests.

## AI-use log gate

- Code, test, CI-script, runtime-prompt, and model-config changes require at least one new or materially changed log entry.
- At least one changed entry must be associated with at least one changed code/prompt path; other unassociated paths are diagnostics, not additional blocking errors.
- Whitespace-only or structurally equivalent log changes are not material updates.
- Pure documentation, non-code workflow configuration, and non-code build configuration do not require log updates.
- CI scripts and other executable code are not exempt merely because they are under a governance directory.

## Trusted evaluation

The trusted workflow is manually dispatched from the default branch with:

- `candidate_sha`: exact commit to evaluate;
- `mode`: `semantic`, `live`, or `semantic-not-applicable`;
- `reviewer`, `not_applicable_reason`, `approval_evidence` for not-applicable;
- optional `semantic_runner` for an approved configuration.

The trusted tool directory is checked out at `${{ github.sha }}` and verified;
the candidate is checked out separately at `inputs.candidate_sha` and verified.
The default-branch source check and protected `trusted-evaluation` environment
remain in place. The protected environment must be configured by a human with
the required reviewers and secrets. The live mode is independent of the
semantic configuration: an unapproved semantic configuration cannot block a
live run. The semantic mode fails closed while `docs/ci/semantic_eval.yaml` is
`unapproved`.

The live mode is optional and not a merge gate. It runs `test/live/` directly
with pytest and writes JUnit XML. The `live-result` check requires at least one
executed, passing live case and fails on any failure, error, skip, zero cases,
or collect-only result. A normal deselection that leaves the required live
cases in the JUnit result is not a failure. Missing `DEEPSEEK_API_KEY` fails
before the optional suite runs.

## Branch-protection checklist

A human with repository administration rights must:

1. Require the `ci / aggregate` PR check and any other selected required
   checks; block force-pushes.
2. Require at least one human approving review; dismiss stale approvals and
   require review again after a new commit.
3. Require review from the safety-critical path owners or security reviewers;
   configure path restrictions/CODEOWNERS if the repository uses them.
4. Protect `.github/**`, `scripts/ci_checks.py`,
   `scripts/ci_semantic_eval.py`, `mypy.ini`, `mypy-baseline.txt`, and
   `docs/ci/**`.
5. Configure the `trusted-evaluation` environment, reviewers, and
   `DEEPSEEK_API_KEY` secret only if live execution is authorized.
6. Confirm that the remote repository actually executes the workflow files
   under the project-root `.github/workflows/` directory.

The security-path job's ADR check validates only the reference. It does not
query GitHub reviews, request `pull-requests: read`, or decide human approval;
the branch-protection settings above enforce that approval. Repository files
cannot prove these settings are enabled, so no remote enforcement is claimed.
Fork PRs require the candidate SHA to be fetchable from the base repository;
no cross-repository checkout or credential proxy is added.

Status: local CI fixes are complete. The PR #7 (Round 1) and PR #9
(contract-test path fix) pull_request runs and their main push runs completed
successfully at workflow level (RM-7-R1, RM-9-R1); individual job outcomes,
trusted semantic evaluation, optional live execution, permission enforcement,
and remote branch protection remain unverified.

## Verification record

The execution results below belong to the 57-gate-test version. They are not
rewritten as current results. At the time of this documentation-sync snapshot,
`test/offline/test_ci_gates.py` statically contained 58 top-level `test_*`
functions; no execution result for that snapshot was generated by this
documentation sync.

Later GitHub evidence, not a rewrite of these local results: the PR/main
workflow runs recorded for PR #7 and PR #9 completed successfully at workflow
level (RM-7-R1, RM-9-R1). Individual jobs were not separately checked.

Phase 1 (offline scripts and gate tests, 57-test version):

- `pytest -q test/offline/test_ci_gates.py`: 57 passed.
- `python scripts/ci_checks.py schema ...`: 0 errors; 13 requirements, 55 FCs,
  9 active requirements/40 active FCs, 4 deferred/15 deferred FCs.
- `python scripts/ci_checks.py permissions --path .opencode/permissions.jsonc`:
  0 errors.
- `python scripts/ci_checks.py api`: 0 errors.
- `python scripts/ci_checks.py mypy ... --baseline mypy-baseline.txt`: no new
  diagnostics; the baseline contains the existing application diagnostics.
- The security-path ADR checks cover missing, empty, invalid, out-of-root, and
  existing ADR references; safety-relevant-only changes do not require an ADR.
  The security-path job no longer queries reviews or requests
  `pull-requests: read`; the test pre-approval job still does.
- Test approval now applies only to applicable code/test/runtime-prompt
  changes, including code outside `src/` and `setup.py`, requires one explicit
  `APPROVED test-spec:` line matching the PR field, rejects bots and ambiguous
  text, and uses changed diff lines for the scope check.
- Trusted evidence requires the repository default branch and a workflow
  `head_sha` matching the artifact record `workflow_sha`, while still allowing
  the candidate SHA to differ.
- Live results are optional; if requested, JUnit XML rejects zero cases, skips,
  failures, and collect-only while ordinary deselection with the required
  cases present passes. No live evidence is claimed.
- Known build configuration is classified; `setup.py`, executable files under
  `scripts/`, `tools/`, and `docs/`, and root executables remain code; unknown
  non-code paths run generic checks and are not treated as documentation; both
  sides of a rename are checked.
- Runtime `prompts/*.yaml` changes trigger semantic and AI-use-log checks.
  Python prompt definitions are compared by AST-level old/new definition
  snapshots, so long prompt text edits, replacement, and deletion trigger even
  when the changed line is outside the diff token window; ordinary logic outside
  prompt definitions does not. Mixed model/config files compare relevant AST
  model definitions; unrelated output-path/comment/format changes do not trigger.
  `Prompt.md` remains static documentation.
- The AI-use log check now requires at least one substantive changed entry
  associated with at least one changed code/prompt path. Other unassociated
  paths are reported as diagnostics; pure documentation, non-code workflow
  config, and build config do not require log updates.
- `contract-tests` selects actual test paths from the approved test
  specification at its approved commit, requires each changed code path to be
  named in that approved specification, requires collection and JUnit-validated
  execution, and uses gate tests for approved governance code. Shared specs and
  shared tests can cover multiple related files; arbitrary helper scripts are
  not automatically covered by fixed CI tests. Missing approval, unnamed code
  paths, missing tests, all-skipped, failed, errored, and zero-executed cases
  are tested as failures.
- The trusted workflow now checks out the trusted tool directory at
  `github.sha`, verifies that checkout, and keeps the candidate checkout and
  default-branch/protected-environment checks separate.
- The AI-use-log check passed for the CI implementation file set recorded in
  `AI-027`, `AI-028`, `AI-029`, `AI-030`, `AI-031`, `AI-032`, `AI-033`, and
  `AI-034`. The broader uncommitted worktree contains earlier governance work
  outside this task and still needs its own log association before a combined
  commit or PR.
- `ruff check` on the new CI scripts and gate test: passed. Full-repository
  Ruff still reported 16 pre-existing findings in `scripts/finalize_run.py`,
  `scripts/probe_data.py`, `scripts/rebuild_evidence.py`, and
  `scripts/run_baseline.py` at that verification point. Those files were
  outside that task's approved file list and were not changed then.
- Later Ruff repair: commit `b56da53` repaired those 16 findings. No Ruff run
  was performed as part of the documentation-only baseline synchronization.

Phase 2 (workflow wiring):

- `ci.yml` and `trusted-evaluation.yml` parse as YAML and contain the required
  push/PR split and PR-only aggregate.
- The workflows have not been executed on GitHub in this task. No remote CI,
  branch protection, or GitHub settings change is claimed.

Phase 3/4 (trusted evidence and real verification):

- Semantic evaluation is blocked: `docs/ci/semantic_eval.yaml` is `unapproved`;
  no dataset, rubric, threshold, model, or runner is approved.
- Optional live evaluation was not run; no live environment or
  `DEEPSEEK_API_KEY` was used.
- Full regression at the 57-gate-test version remained red on this host: 1415
  passed (including the 57 new gate tests), 3 existing Windows-specific
  failures, 1 skip, 1 deselected, 100 subtests passed. This is a historical
  result, not current-version coverage.
- No application behavior, requirement, history, permission, or test
  assertion was changed to make a gate green.

## Tool versions used

- Python `3.12.14` in an isolated local virtual environment.
- `PyYAML==6.0.3`
- `jsonschema==4.26.0`
- `mypy==2.4.1`
- `ruff==0.17.5`
- `pytest==9.2.0` with the project dev extras.
