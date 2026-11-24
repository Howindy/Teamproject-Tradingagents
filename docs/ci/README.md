# CI Gate Operation

> 2026-11-23 current-scope clarification: D1 v1.49.0 retains 13 requirements / 55 FCs with six active / 27 FCs and seven deferred / 28 FCs. PR #12 pre-approval: comment 7089283044, frozen specification cc2c834c3ce9097f08d95b4beef1a5dc1bb0b7e9. Existing workflow/classifier/schema are unchanged; only the registry count regression expectation is synchronized. Counts/results below remain historical to their recorded versions. No PR #12 final CI or merge is claimed.

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
- Round 2 C-09/IF-09 independent core: `docs/plans/round-02.md @ 8ad99c25ea1acd77b6e019fbe3c357899e8fc535`; test-spec ([comment 7073333663](https://github.com/Howindy/Teamproject-Tradingagents/pull/10#issuecomment-7073333663)) and safety-critical implementation ([comment 7074759911](https://github.com/Howindy/Teamproject-Tradingagents/pull/10#issuecomment-7074759911)) approvals, final review of H `fbba457a9235ef53de52604f9b591aaf89a1972b`, merge M `cc8b17596a81751bd6165899423dd511e93dc394`, and workflow-level PR/main success are recorded in [RM-10-R1](../review-memo.md#rm-10-r1-ai-authored-draft-final-human-approval-transcribed-below). Scope is SB-01-FC01–FC04 and local IR-01/IR-02 only; production integration, SB-01-FC05, full SB-01, global invariants, IF-19, and the FR-03 producer remain excluded.
- The Round 1, PR #9, and PR #10 GitHub facts are workflow-level. PR #10's main push skipped PR-only jobs. Individual job results, branch-protection enforcement, permission enforcement, trusted semantic evaluation, and optional live evidence remain unverified.

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
- `docs/ci/semantic-suites.yaml`: trusted semantic suite registry (suite ID → configuration and runner); read only from the default branch. See [Semantic suite routing](#semantic-suite-routing).
- `docs/ci/semantic_eval.yaml`: fixed FR-10 evaluation configuration, bound to suite `financial-metrics` (remains `unapproved` until separate human authorization of the 6-request `deepseek-flash` run against PR 2 candidate).
- `docs/ci/financial-metrics-cases.json`: lossless projection of independent `fr07-sec-reference-v1` answers and four fixed semantic cases (`FM-S01`..`FM-S04`).
- `docs/ci/financial-metrics-rubric.md`: deterministic 5-dimension binary rubric, critical failures, and `needs_review` escalation rules (`18/20` threshold).
- `scripts/financial_metrics_eval.py`: trusted semantic evaluation runner (`financial_metrics_eval:evaluate`) verifying candidate/baseline SHAs, normal installed-package discovery, prompt injection capture, and 6-request cap.

## FR-10 semantic runner invocation and limits

Once PR 1 merges to `main`, `docs/ci/semantic_eval.yaml` is explicitly approved for execution, and PR 2 provides the migrated application candidate SHA, the protected `trusted-evaluation.yml` workflow invokes:

```bash
python scripts/ci_semantic_eval.py \
  --registry docs/ci/semantic-suites.yaml \
  --suite financial-metrics \
  --candidate "$CANDIDATE_SHA" \
  --workflow-sha "$GITHUB_SHA" \
  --run-id "$GITHUB_RUN_ID" \
  --output record.json \
  --details-output "$RUNNER_TEMP/semantic-details.json"
```

The runner comes from the registry entry; the former `--config`/`--runner`
semantic invocation is rejected.

Preparation PR 1 adds only this trusted infrastructure and offline gate/runner tests; it does not migrate `src/` modules or run live model requests.

The trusted runner requires `execution.baseline_root`, `execution.baseline_sha`
and `execution.baseline_python_executable` (or equivalent direct Python arguments).
PR 2 must pin that comparison checkout and separately installed environment as
specified by FM-PREP-2; these are intentionally not invented in this preparation
configuration. Missing baseline prerequisites fail before any completion request,
as do invalid origins in any of the six preflight captures. A candidate-only
four-request run cannot produce passing paired-evaluation evidence. Trusted text
hashes use Git's LF representation (only checkout CRLF-to-LF is normalized).

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
fails.

Each machine field (`Plan`, `Approved test specification`, `Approval evidence`,
`Implementation start`, `Approved scope`, `ADR`) must appear AT MOST ONCE in the
PR body. A duplicated field is an error, not last-one-wins: otherwise a pasted
governance-note block could silently override the real P3 values. The parser
reports every duplicated field by name and fails closed. Only `Supplemental test
specification` may legitimately repeat (one line per supplement). Put governance
maintenance notes in prose that does not start a line with a recognised
`Field: value` key. The approval event must precede the first implementation commit, the
approved specification commit must be ancestral, and scope changes after
approval require a new approval. Git ancestry and author timestamps alone
cannot prove the real implementation order; a trusted human approval event is
still required, and this limitation remains. No new approval platform is
introduced. The changed-scope check uses IDs added on changed diff lines and
changed test paths, not every ID present in the full file. Round 1 was an
unapproved example when this convention was written; its later real approval is
recorded in RM-7-R1 and does not change the gate's negative-sequence
requirement.

### Scope-ID extraction (approval gate)

The changed-scope set keeps only GENUINE requirement / fit-criterion /
invariant IDs (namespaces `FR-`, `SB-`, `INV-`, `SR-`, `PR-`, `CR-` with
`-NN`/`-FCNN`, and `IR-NN`). All of these must be in the PR `Approved scope`.
D2 design labels the broad ID regex also matches — component `C-NN`,
interface `IF-NN`, attachment/path `P-NN`, test-case `R03-NN`/`PA-NN`, and the
`FC01-05` range shorthand — are NOT approval scope and are ignored by the
coverage check. A scope ID that appears only on a NEGATED added line (for
example "FR-01 is not implemented here" or "belongs to FR-01") is not treated
as new scope. This is by NAMEspaces and diff-line negation, not by whether the
ID exists in `requirements.yaml`: a genuine, unapproved `FR-`/`IR-` ID (for
example a referenced `FR-04`) and an unknown well-formed ID still FAIL. The PR
`Approved scope` alone cannot prove human approval; it must match the frozen
specification bound by the approval event.

Docstring classification is by syntactic position, not by the mere presence of a
string. Ordinary assignment strings, asserts, dict keys/values, call arguments
and f-strings remain executable and are scanned. A docstring that shares a
physical line with other executable statements (for example
`"""module docs"""; enabled = {"FR-04"}` or an inline `"""body"""; assert ...`)
is conservatively treated as code so its IDs are still detected; only a line
whose entire content is a standalone docstring is treated as documentation.

### Supplemental test specification (P3 + A3 style)

When a round has a second, separately approved specification/adjustment (a
"supplemental" spec), add an optional field:

```text
Supplemental test specification: <spec path> @ <commit> (approval: <GitHub approval URL>)
```

Each supplemental spec is validated independently and, when it fails ANY check,
contributes nothing (fail-closed):

- the reviewer is not the PR author and not a bot;
- the approval event contains exactly one `APPROVED test-spec:` line matching
  the supplemental spec path and commit;
- the approval time is earlier than the first commit that changes the paths the
  supplemental spec covers (its own first related change, not the whole round's
  first commit);
- the supplemental spec commit is an ancestor of that first related change, and
  the spec is not modified after approval without re-approval;
- the supplemental only ADDS coverage; it never relaxes the primary checks and
  cannot cover a changed code path that neither the primary nor the supplemental
  spec mentions.

A valid supplemental joins its test paths into the contract-test selection and
adds only the scope IDs its own approved spec declares. The primary `Approved
test specification` / approval checks always run unchanged.


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
  --pr 1 --pr-body-file pr-body.txt \
  --registry trusted/docs/ci/semantic-suites.yaml --trusted-root trusted \
  --semantic-required
python scripts/ci_checks.py contract-tests --pr-body-file pr-body.txt \
  --base "$BASE" --head "$HEAD" --token "$GH_TOKEN"
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

### Where the gate test itself runs

`test/offline/test_ci_gates.py` is executed by CI independently of
`contract-tests` selection:

- the `regression` job runs `pytest -q` over `testpaths = ["test"]` (excluding
  only `integration`-marked tests), so the gate test is always collected and run;
- when `security_applicable` is true (e.g. a safety-relevant/critical source
  change), the `security-paths` job also runs `test/offline/test_ci_gates.py`
  explicitly.

So a mixed application + governance PR still executes the gate test. What
`contract-tests` does not do for such a PR is add the gate test to its own
selected test set (the pure-governance branch of `contract_test_plan` only runs
when there is no other code path). Governance/CI-script changes still require a
specification that names the governance paths (and, if it wants `contract-tests`
to run the gate test specifically, `test/offline/test_ci_gates.py` too); that
selection detail does not change whether the gate test runs elsewhere in CI.

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
- `suite_id` for `semantic` mode: a suite registered in the default-branch
  `docs/ci/semantic-suites.yaml`. The former free-text `semantic_runner` input
  is removed.

The trusted tool directory is checked out at `${{ github.sha }}` and verified;
the candidate is checked out separately at `inputs.candidate_sha` and verified.
The default-branch source check and protected `trusted-evaluation` environment
remain in place. The protected environment must be configured by a human with
the required reviewers and secrets. The live mode is independent of the
semantic configuration: an unapproved semantic configuration cannot block a
live run. The semantic mode fails closed while the selected suite's
configuration (for `financial-metrics`, `docs/ci/semantic_eval.yaml`) is
`unapproved`.

## Semantic suite routing

Design and test specification: [`docs/plans/semantic-suite-routing.md`](../plans/semantic-suite-routing.md)
(§3 design, §3.5 suite unit contract I1–I6, §5 tests T01–T18).

- **Registry.** `docs/ci/semantic-suites.yaml` maps each suite ID to
  `requirement`, `config` (inside `docs/ci/`) and `runner`
  (`scripts/<module>.py:function`). Only the default-branch copy is used: the
  trusted workflow reads its own checkout, and `evidence-check` checks out the
  default branch into `trusted/`. A new suite takes effect only after merge.
- **Selection.** A PR whose change is classified `semantic_required` must state
  `Semantic suites: <id>[, <id>...]` (or `none`) and
  `Semantic suites approval: <review/comment URL>`. That event must be from a
  non-author, non-bot human and contain exactly one line
  `APPROVED semantic-suites: <same list>`. The body is read from the GitHub API
  at check time, so edits take effect on re-run. A non-semantic PR without the
  field keeps the previous behavior; a non-semantic PR that lists suites opts in.
    The current body is fetched even when the event payload had no selection;
    absent/`none` selection on a non-semantic PR does not load the registry or
    require semantic evidence. This costs one PR-body read, not an evaluation.
- **Dispatch.** Run `trusted-evaluation.yml` once per selected suite with
  `mode=semantic` and `suite_id=<id>`. Status context is `semantic-eval/<id>`;
  artifacts are `ci-evidence-<sha>-semantic-<id>` and
  `ci-semantic-details-<sha>-<id>`. The record carries `suite_id`,
  `config_path`, `config_sha256` (LF-normalized), `config_version`, `runner`,
  `status` (`passed`, `failed` or `needs_review`) and `needs_review` items.
- **Verification.** `evidence-check` requires a passing record for every
  selected suite whose config hash matches the current trusted config. Another
  suite's pass, the legacy `semantic-eval/evidence` context, or a
  `semantic-eval/not-applicable` record never substitutes for a selected suite.
  `none` requires the reviewed not-applicable record. Missing, unknown or
  unapproved selections and `needs_review` results block with the specific
  reason; `needs_review` goes to the existing human review, not to a CI override.
    A runner's `passed` label cannot override reported errors or pending review
    items. I3 fields are required, and the details file must be inside
    `output_dir` with a matching hash. Contract violations are recorded as failed;
    explicit `needs_review` results retain their review items and remain blocking.
- **Bootstrap.** If the default branch has no registry, non-enforced PRs pass as
  before and enforced PRs block with "registry is not present on the default
  branch".
- **Adding a suite.** Follow plan §3.5: own files named per I4, a configuration
  in the existing `validate_config` structure (I2), a runner implementing I3,
  offline tests with a stub `model_transport`, and one registry line, in a PR
  merged after this routing change and before the feature PR that selects it.
- **Limit.** The evidence checker itself still runs from the candidate
  checkout (CI.md "CI self-protection"); only registry and configuration data
  come from the default branch.

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

Status: local CI fixes are complete. The PR #7 (Round 1), PR #9
(contract-test path fix), and PR #10 (Round 2 C-09 core) pull_request runs and
their main push runs completed successfully at workflow level (RM-7-R1,
RM-9-R1, RM-10-R1); PR #10's push skipped PR-only jobs. Individual job
outcomes, trusted semantic evaluation, optional live execution, permission
enforcement, and remote branch protection remain unverified.

## Verification record

The execution results below belong to the 57-gate-test version. They are not
rewritten as current results. At the time of this documentation-sync snapshot,
`test/offline/test_ci_gates.py` statically contained 58 top-level `test_*`
functions; no execution result for that snapshot was generated by this
documentation sync.

Later GitHub evidence, not a rewrite of these local results: the PR/main
workflow runs recorded for PR #7, PR #9, and PR #10 completed successfully at
workflow level (RM-7-R1, RM-9-R1, RM-10-R1). PR #10's main push skipped PR-only
jobs, and individual jobs were not separately checked.

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

## PR #18 supplemental maintenance

The independently approved maintenance specification is
`docs/plans/semantic-registry-test-amendment.md @ 2d10aa4a24eee3cced9cbe4835bb695de0ebaf2f`,
[approved by espino2233](https://github.com/Howindy/Teamproject-Tradingagents/pull/18#issuecomment-7135347793)
at `2026-11-24T15:02:01Z`. This is test-specification pre-approval, not a final
implementation review, configuration activation or model-execution authorization.

Keep the original primary PR fields and add one supplemental line per independent approval:

```text
Supplemental test specification: <path> @ <full 40-character SHA> (approval: <GitHub PR comment/review URL>)
```

Primary and other optional machine fields must occur once. Only
`Supplemental test specification` may repeat: distinct values are retained,
while identical entries or repeated normalized specification paths are rejected.
No earlier approval is overwritten. A supplement must contain an explicit
`## 3. Allowed files` section with project-relative file paths in bullet entries.
Only that list grants path coverage or selects contract tests. Paths mentioned
in rationale, historical references, verification commands or exclusions do not
grant additional coverage. Approval must bind the exact immutable specification,
come from a non-author human, and precede the first related implementation change.
The specification's own creation does not count as that implementation. Invalid
supplements add neither scope nor selected tests; primary checks remain mandatory.

The contract-test command independently validates every supplied supplement
before collection. The contract job now receives the Actions-provided token only
on its command step, with `contents: read` and `pull-requests: read`. It checks
that GH_TOKEN is nonempty and passes it via `--token`. API failures remain
blocking; authentication errors never trigger an anonymous fallback. Direct
callers may omit the optional argument for the previous public-read behavior.
No stored credential discovery or personal token is used. The original
security-path and token-bearing test-approval jobs remain unchanged.

The implementation-start compatibility rule is bounded to the three exact
FR-03 preparation-material paths in specification section 6. Each excluded path
must be named in the primary frozen specification and have the identical Git
blob at the evaluated candidate. The suite configuration at both revisions must
remain unapproved with null approval identity/time and empty approval evidence.
Unverifiable or changed materials remain subject to ordinary classification.
Code, tests, shared routing, workflows, permissions and activation changes are
never covered by this exception; other paths in a mixed commit still count.

T16 now protects the complete `financial-metrics` entry rather than prohibiting
additional registered suites. Its original hash/state protections remain, and
T18 still inspects every registered suite's configuration and runner contract.


### Lean approval-job dependency repair

Run `45423751532` exposed that `test-approval` installs no third-party packages.
Its preparation-material check must therefore remain standard-library-only.
The check now attests the reviewed unapproved FR-03 configuration by its fixed
LF-text SHA-256 (`96f7d51f93316b351ac70949d753d5bd81282cc285c0ed946d003a4de7a7b015`)
at both the approved specification and candidate revisions, instead of importing
PyYAML. The independently checked reference has unapproved status, null approval
identity/time and empty evidence. Other configuration content, including activation
or equivalent but differently formatted YAML, conservatively receives no exception.
Exact Git blob comparisons for each preparation material remain in place.

Tests execute the approval check in an isolated `python -I -S` subprocess,
asserting YAML is unavailable, and check both valid preparation and rejected
activation. No workflow, dependency pin, frozen material or approval is changed.


### Authenticated contract reads and separate supplemental approvals

The auth amendment is `docs/plans/semantic-contract-auth-amendment.md @
0539300c05b1b12c3ccff4a517dc132513a6facb`, independently approved by `espino2233`
at `2026-11-24T16:14:27Z` in
[comment 7137342374](https://github.com/Howindy/Teamproject-Tradingagents/pull/18#issuecomment-7137342374).
It adds the contract job's narrowly scoped workflow allowance. It does not
replace the earlier suite or maintenance approval.

Keep the existing primary fields and earlier supplemental line, and add:

```text
Supplemental test specification: docs/plans/semantic-contract-auth-amendment.md @ 0539300c05b1b12c3ccff4a517dc132513a6facb (approval: https://github.com/Howindy/Teamproject-Tradingagents/pull/18#issuecomment-7137342374)
```

Each supplemental document is checked against its own explicit section-3
allowed-file list and first related change. The earlier maintenance approval
continues covering its original script/test changes; the auth amendment's new
path is `.github/workflows/ci.yml`. Inherited-file prose does not create new
historical coverage. Any invalid supplied supplement blocks the gate, and only
valid documents contribute scope/tests. The approval entry remains stdlib-only.

The first auth implementation delivers workflow wiring, token forwarding,
repeat-field handling and executable tests together after the real approval.
Git commit times alone do not establish actual edit chronology; the drafting
checkpoint and human review remain part of the evidence.

The FR-03 data-availability standard and one run on the reviewed final candidate
were [approved on PR #20](https://github.com/Howindy/Teamproject-Tradingagents/pull/20#issuecomment-7138946184).
The protected evaluation uses at most 20 completion requests across the 15
case/role combinations. Record the non-author suite-selection comment on PR #13
and use the final candidate SHA when dispatching from main.
