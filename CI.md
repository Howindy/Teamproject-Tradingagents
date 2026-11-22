# CI Governance Plan

- Status: **Approved for implementation by the human user; implemented locally. Round 1 and PR #9 have real approvals, merges, and successful workflow-level PR/main runs; individual job results, trusted semantic evaluation, permission enforcement, and remote branch protection remain unverified; live execution is optional and not a merge gate.**
- Scope: minimum viable implementation of the six course CI gates and branch-protection requirements for this repository.
- This document is a design and test specification. It does not approve a round plan, application implementation, branch protection, semantic-evaluation standards, or a live-test environment.
- The CI checks and workflows listed in section 5 are implemented locally in this checkout; this document does not execute them or prove their remote behavior.
- `CI.md` itself is the test specification for the CI implementation. The human approval is recorded in `docs/ci/README.md`; the new CI cannot retroactively machine-verify its own pre-approval.
- D2.md is not a current input. Course D2 requirements come from the course PDF; project architecture is represented by the existing blueprint and `docs/architecture/` artifacts.

**Current-status clarification (2026-11-22):** Round 1 (C-08 core) and the PR #9 contract-test path fix have real human approvals, merges, and successful PR/main workflow runs; see [RM-7-R1 and RM-9-R1](docs/review-memo.md#4-registered-records). This does not establish branch protection, individual job success, trusted semantic/live evaluation, full permission enforcement, or any unrun check. Historical sections below keep their original version context.

---

## 1. Current baseline and real gaps

### Requirement and architecture inputs

- D1 is v1.48.0 with 13 requirements and 55 fit criteria: 9 active requirements with 40 active fit criteria, and 4 deferred requirements with 15 future fit criteria.
- Active requirements: FR-01, FR-02, FR-03, FR-04, FR-05, SB-01, INV-01, SR-01, SR-02.
- Deferred requirements: FR-06, FR-07, PR-01, CR-01.
- D2 includes the blueprint, ADR 001, invariants, trace matrix, memory/state design, permission model, runtime policy catalog, and evaluation table.
- The current ADR and architecture package remain Proposed; they are not implementation or test acceptance.
- D4 defines verification obligations. Its `V-*` identifiers are planned verification intents, not actual test coverage.
- The C-08 FR-04 core now has offline tests and a merged Round 1 record. Other new D2 behavior, including SB-01/C-09, availability, manifest, history, and broader security paths, has no dedicated test yet.

### Application and test layout

- Application packages: `src/tradingagents/` and `src/cli/`.
- Offline tests: `test/offline/` (88 test modules, including the CI gate test).
- Live tests: `test/live/` (1 test module, 1 live test case).
- Default `pytest -q` uses `-m "not integration"` and excludes live tests.
- Original baseline before the CI work: 1358 passed, 3 failed, 1 skipped, 1 deselected, 100 subtests passed.
- Historical local offline result at the 57-gate-test version (2026-11-18): 1415 passed, 3 failed, 1 skipped, 1 deselected, 100 subtests passed.
- Static inventory at the documentation-sync version: `test/offline/test_ci_gates.py` contained 58 top-level `test_*` functions. No execution result for that snapshot is recorded by this documentation sync.
- The 3 failures are existing Windows-specific lock tests in `test/offline/test_cache_writes.py`; they must be rechecked in the target CI environment, not assumed to reproduce or be exempt.
- The 1 skip is `test_construction_when_extra_installed` because `langchain_aws` is not installed.
- Live tests have not been run.

### CI status: original baseline, local implementation, actual verification

Original baseline:

- `.github/workflows/ci.yml` ran the Python 3.11–3.14 regression matrix, a 3.12 `America/New_York` run, `pytest -q`, a clean-install smoke import, and `ruff check .`.
- The original baseline had no test-approval, type-check, schema, AI-use-log, contract-test, unknown-path, trusted-evidence, or aggregate gate.

Local implementation in the current checkout:

- `scripts/ci_checks.py` and `scripts/ci_semantic_eval.py`.
- `.github/workflows/ci.yml` with push/PR split, PR-only `ci / aggregate`, applicable-test approval, contract tests, security-path ADR checks, AI-use-log, and trusted semantic evidence.
- `.github/workflows/trusted-evaluation.yml` with default-branch trust, tool checkout at `github.sha`, separate candidate checkout, protected environment, semantic evidence, optional live evidence, and structured JUnit validation.
- `mypy.ini`, `mypy-baseline.txt`, `.github/requirements-ci.txt`, `docs/ci/README.md`, and `docs/ci/semantic_eval.yaml`.
- Test approval, schema, type, dependency, lint, API, permission, AI-use-log, contract, build/unknown-path classification, semantic, and aggregate logic are locally implemented. Live execution remains optional.

Historical local verification at the 57-gate-test version:

- 57 gate tests passed.
- Schema, permission, and API checks passed.
- mypy reported no diagnostics outside the existing 162-line baseline.
- Modified CI files passed Ruff; full-repository Ruff still reported 16 pre-existing findings in unmodified scripts at that time.
- Full offline pytest was 1415 passed, 3 existing failures, 1 skip, 1 deselected, 100 subtests.
- Workflows parsed but did not execute on GitHub; semantic evaluation did not run; live execution is optional and did not run; branch protection and remote settings were not verified.
- Later Ruff repair: commit `b56da53` repaired those 16 findings. This documentation sync did not re-run Ruff or the 58-function gate-file snapshot referenced above.

### Current pre-commit local verification (2026-11-21)

Run window: `2026-11-21T11:35:45+0800`–`2026-11-21T11:35:51+0800`
(`2026-11-21T03:35:45Z`–`2026-11-21T03:35:51Z`), from the project root with
Python `3.12.14` and Ruff `0.17.5` from the existing isolated CI environment.

Commands and results:

- `python -m pytest -q test/offline/test_ci_gates.py`: 61 passed in 5.31s,
  exit 0. At that run, the file statically contained 58 top-level `test_*`
  functions; 61 cases were collected and passed.
- `python -m ruff check .`: `All checks passed!`, exit 0.
- `git diff --check`: no output, exit 0. This covers tracked diffs; `CI.md`
  remains untracked and was separately checked: no trailing whitespace and a
  final newline is present.

This is current-working-tree local evidence only. It does not prove GitHub
Actions execution, trusted semantic evaluation, live tests, Docker, application
behavior, branch protection, or remote required checks. It does not replace the
historical 57-gate-test/1415-passed record above.

### Current tooling

- CI-only pins are in `.github/requirements-ci.txt`; the CI checks use an isolated local environment.
- The existing application diagnostics are recorded in `mypy-baseline.txt`; new diagnostics remain blocking.
- The 16 full-repository Ruff findings recorded by the earlier CI verification were later repaired by commit `b56da53`; workflow-level PR/main runs succeeded for the recorded PRs, but the individual lint-job result was not separately verified by this documentation sync.
- `docs/ci/semantic_eval.yaml` remains `unapproved`; no threshold or model configuration is invented.

### Governance state

- Round 1 is approved at `docs/plans/round-01.md @ a8ec42ecdf4199f91d3001fc6e2b1e887a0c5e41`; RM-7-R1 records its test and safety pre-approvals and merge. That approval covers the C-08 core only; FR-04-FC05, complete IR-14, entry/graph/report integration, and C-09 remain unimplemented.
- Round 1 test and safety pre-approvals are recorded in PR #7 (see RM-7-R1). PR #9 is the separate contract-test path-fix approval and merge (see RM-9-R1); neither CI maintenance nor workflow success expands application scope.
- PR #10 records a fixed-version pre-approval of `docs/plans/round-02.md @ 8ad99c25ea1acd77b6e019fbe3c357899e8fc535` ([comment 7073333663](https://github.com/Howindy/Teamproject-Tradingagents/pull/10#issuecomment-7073333663)); the current work is documentation closeout only, C-09 is not implemented, and that specification pre-approval is not safety-critical implementation approval, execution evidence, or final acceptance.
- No fixed semantic-evaluation dataset, rubric, threshold, or model configuration exists.
- No live-test environment is configured or verified; the course does not require a live call for every change.
- No actual CODEOWNERS owner accounts or branch-protection settings are confirmed from the local checkout.
- CI implementation and semantic/live evaluation remain separate from the Round 1 application approval and do not expand its C-08-only scope.

---

## 2. Course requirements and minimum mechanisms

| Requirement | Minimum mechanism | Trigger | Failure condition | Evidence | Human responsibility |
|---|---|---|---|---|---|
| Test pre-approval | Bind the approval to an exact plan/test-specification version and an implementation start commit; verify one explicit human `APPROVED test-spec:` phrase, reject bots, and require the event to predate that start | Applicable application code/test change; pure documentation and build configuration are not applicable | No approved version, scope mismatch, bot or ambiguous approval, phrase/version mismatch, approval event later than implementation start, test design changed without reapproval, or unverifiable evidence | PR description fields, plan path/commit, approval URL/event time, exact phrase/version, implementation start commit, approved scope | Confirm that approval preceded the actual coding start; git ancestry and commit times alone are insufficient |
| Static analysis | Ruff, one type checker, and dependency consistency | Every push/PR | Lint error, new type error outside an explicit temporary baseline, or dependency check failure | CI logs, type baseline diff, dependency output | Review and own baseline/dependency exceptions |
| Security-path checks | Targeted contract/security tests, small API-signature assertions, permissions config check; safety-critical changes also require a non-empty, existing project ADR reference. Human approval is enforced by branch protection, not by a CI review query. | Safety-relevant or safety-critical path PR | Missing applicable test/check, assertion failure, unapproved or contract-breaking API surface change, unsafe permission change, or missing/empty/invalid/out-of-root ADR for a safety-critical change | Test node IDs, API assertion output, permission check output, ADR path | Confirm whether the cited ADR applies and is approved; do not require ADR for safety-relevant-only changes. Configure and verify human review enforcement remotely. |
| Requirements Schema | Validate `requirements.yaml` against `req-schema.json`; validate the Schema itself; light ID checks | Every push/PR | Schema error, invalid Schema, duplicate IDs, or invalid active/deferred structure | Schema error paths, parsed counts | Do not edit requirements to hide a failure |
| Semantic evaluation | Fixed dataset/rubric/threshold/config and a trusted evaluation entry; block prompt/model changes without approved evidence | Runtime prompt/model change | Dataset/threshold unapproved, evaluation missing, config/hash mismatch, failed threshold, missing credentials | Dataset/config version, model configuration, result summary, trusted status | Approve evaluation standard and review quality claims |
| Regression | All existing offline tests on every code change | Every push/PR | Any regression failure | Pytest output and collection | Distinguish existing failures from new regressions |
| AI-use log | Existing log format; require at least one new or materially changed entry associated with at least one changed code/prompt path. Per-file unassociated paths are diagnostic, not blocking. | Code/runtime-prompt change | No changed entry, only a touched/whitespace-equivalent entry, or no changed entry associated with any changed code/prompt path | Log diff, entry IDs, at least one path association | Verify factual truth and human interventions |
| Branch protection | GitHub-native required CI and human review; CI validates the safety-critical ADR reference only | Merge | Required check absent/failed, safety-critical change lacks human review, or the required ADR check fails | PR status, reviews, ruleset | Configure and verify the remote settings; do not claim they are enabled |
| D4 coverage | Current-round approved tests selected from the approved test specification at its approved commit, collected, and executed; final human acceptance review against D1/D2/D4 | Round/release | Approved current-round test missing, zero tests collected, or final acceptance lacks real FC/IR evidence | Test IDs, plan test paths, pytest output, D4 review, final acceptance record | Confirm actual assertion coverage; V-* tables and plan prose are not evidence |

The “one negative test per feature” rule is not expanded into “one independent negative test per FC.” A negative test may cover multiple related FCs when its assertions clearly cover them.

The single aggregate check is a project implementation choice for simplifying required GitHub status checks. It is not an additional course gate. Native branch protection and human review remain the enforcement mechanism for merge and security-critical approval.

---

## 3. Minimum workflow structure

```text
ci.yml
  push (all branches; candidate version = github.sha)
    ├─ classify (known build configuration separated; unknown paths remain generic)
    ├─ requirements-schema
    ├─ static (Ruff)
    ├─ type-check
    ├─ dependency-check
    └─ regression matrix

  pull_request (candidate version = github.event.pull_request.head.sha)
    ├─ classify (known build configuration separated; unknown paths remain generic)
    ├─ test-approval       (only when approval_applicable)
    ├─ requirements-schema
    ├─ static (Ruff)
    ├─ type-check
    ├─ dependency-check
    ├─ regression matrix
    ├─ contract-tests       (approved test-spec paths at approved commit; governance gate tests; docs/config exempt)
    ├─ security-paths       (only when classified)
    ├─ ai-use-log           (only for code/runtime prompt)
    ├─ evidence-check       (semantic status only for prompt/model changes)
    └─ aggregate

trusted-evaluation.yml (manual dispatch from trusted default branch, protected environment)
  input: candidate SHA
  trusted tools: checked out at github.sha (the default-branch trigger commit) and verified
  candidate: checked out separately at candidate SHA and verified
  ├─ verify checked-out HEAD == candidate SHA
  ├─ semantic-eval        -> semantic-eval/evidence on candidate SHA
  ├─ semantic-noop review -> semantic-eval/not-applicable on candidate SHA
  └─ live-tests           -> optional live-tests/evidence on candidate SHA (not a merge gate)

Manual loop:
  PR CI on candidate SHA fails evidence-check
  -> human reviews exact candidate SHA and approves protected environment
  -> trusted workflow checks out candidate, verifies HEAD, evaluates, records evidence
  -> writes status to candidate SHA
  -> human reruns PR CI on the same candidate SHA
  -> aggregate passes only if every required status and job passes
```

- `push` covers all branches. It runs the push jobs listed in Section 3: `classify`, `requirements-schema`, `static`, `type-check`, `dependency-check`, `regression`, and `smoke-install`, using that push's explicit commit SHA. It does not require a PR body, review, PR head, test approval, AI-use log, or online evidence, and it must not fail merely because those PR-only inputs do not exist.
- A successful push check does not mean the change is mergeable and does not establish the complete course suite.
- `pull_request` covers opened, synchronize, reopened, and ready-for-review events. It adds applicable test approval, current-round contract tests, AI-use log, safety-path checks, and semantic evidence for prompt/model changes. Live evidence is not required.
- PR jobs use `github.event.pull_request.head.sha` as the candidate SHA and checkout that exact ref. They must not silently test the default PR merge ref while citing evidence for the head SHA.
- `merge_group` is optional and should be enabled only if the remote repository actually uses a merge queue.
- `ci.yml` uses `permissions: contents: read`; `test-approval` adds `pull-requests: read`, and `evidence-check` adds `statuses: read` and `actions: read`. The security-path job does not query reviews and does not request `pull-requests: read`.
- `ci.yml` does not receive model or data API secrets.
- `trusted-evaluation.yml` is manually dispatched from the trusted default branch and uses a protected environment. It checks out the trusted tool directory at the triggering `github.sha`, verifies that checkout, and checks out/verifies the candidate separately.
- The trusted workflow writes `semantic-eval/evidence`, `semantic-eval/not-applicable`, or optional `live-tests/evidence` to the candidate SHA. It needs `statuses: write`; the PR workflow only reads.
- A manual evaluation does not modify the earlier failed CI run. The human must rerun the PR CI on the same candidate SHA.
- A new commit creates a new candidate SHA and cannot reuse an earlier evaluation status.
- No polling service, automatic retry, cross-workflow event bus, or evidence platform is added.
- The mandatory final status is `ci / aggregate`. This is an implementation choice for a stable required check, not an additional course gate.
- Conditional jobs may be skipped only when classification proves they are not applicable. A failure, cancellation, timeout, or unexplained skip cannot become a success.
- No `continue-on-error`, ignored exit code, empty success command, or fallback pass is permitted.

### Workflow version versus candidate version

- `workflow SHA` is the commit of the trusted default branch that contains `.github/workflows/trusted-evaluation.yml` and its check logic.
- `candidate SHA` is the exact code version checked out, tested, and evaluated. For a PR it is the PR head SHA; for a push it is the pushed commit SHA.
- The two SHAs are different concerns. A manual workflow run's `head_sha` may be the default-branch workflow version; its checked-out/evaluated candidate is an explicit input.
- The run must verify after checkout that `git rev-parse HEAD` equals the candidate SHA. If it differs, the run fails.
- The evaluation record must contain candidate SHA, workflow SHA, run ID, approved configuration/dataset version, and actual result.
- The status is written to the candidate SHA, not the default-branch workflow SHA.
- The PR evidence check must verify the run belongs to the specified repository, uses `.github/workflows/trusted-evaluation.yml` from the trusted default branch, has a successful conclusion, and has an artifact/record matching the candidate SHA and required configuration.
- It must not require the workflow run's `head_sha` to equal the candidate SHA.
- GitHub Actions bot identity, status name, or `target_url` alone is not proof. `target_url` locates the run; the run, candidate checkout, and artifact/record must be verified.
- If the run or record cannot be verified, the evidence check fails rather than assuming success.

### Trusted evaluation status verification

- Merge-blocking status names are `semantic-eval/evidence` and `semantic-eval/not-applicable`. `live-tests/evidence` remains optional and is not required by the aggregate.
- `evidence-check` queries statuses for the exact PR head SHA. It does not search other commits or branches.
- A successful status must be present on the candidate SHA. A status on the default-branch workflow SHA is not sufficient.
- `target_url` only locates the trusted run. The check must verify that run belongs to the specified repository, uses `.github/workflows/trusted-evaluation.yml`, was dispatched from the repository default branch, was manually dispatched, concluded successfully, and produced an artifact/record with the same candidate SHA and required configuration/dataset version.
- The run `head_branch` must equal the repository default branch. The run `head_sha` is the trusted workflow version and must match the artifact record `workflow_sha`; it must not be required to equal the candidate SHA.
- The evidence description/record must include candidate SHA, workflow SHA, run ID, approved configuration/dataset version, and actual result.
- It must not require the workflow run's `head_sha` to equal the candidate SHA.
- GitHub Actions bot identity, status name, and `target_url` alone are not evidence of correctness; the run and artifact/record must be verified.
- The semantic/no-op status must include a human-reviewed reason; a PR file cannot self-report it.
- An arbitrary PR-provided file, a same-named status from another workflow, or an unverified local result is not accepted.
- The normal PR run does not call the model or live vendor API. It only reads trusted semantic status and fails if required semantic evidence is absent.
- If the run or record cannot be verified, the evidence check fails rather than guessing.

### Candidate-code credential boundary

- A default-branch workflow plus a protected environment does not make candidate code inherently safe. The trusted workflow version and the candidate code version are separate.
- Before online evaluation, a human must review the exact candidate SHA and approve use of the protected environment.
- The trusted workflow receives the candidate SHA explicitly, checks out that candidate, and verifies `HEAD` equals the candidate before running tests or evaluation.
- Credentials are not automatically supplied to unreviewed external PR code.
- The execution scope is limited to the reviewed candidate and the necessary semantic or optional live tests.
- A new commit invalidates the prior candidate approval; the new SHA requires a new review and run.
- This control relies on human review. It reduces the risk but cannot guarantee that reviewed candidate code will never leak credentials.
- No new isolation platform or credential proxy is introduced.

### CI self-protection

- Changes to `.github/workflows/**`, `scripts/ci_checks.py`, `scripts/ci_semantic_eval.py`, `mypy.ini`, or `docs/ci/**` require human review through branch protection.
- The aggregate workflow must remain present as the required check. If a PR removes or renames it, the required status is missing and merge is blocked.
- This is a minimal native-protection model. It does not prevent every possible bypass: a human reviewer could approve a malicious workflow change, and repository files cannot prove remote rulesets are enabled.
- A separate trusted `policy-guard` workflow, gate-owner registry, and policy snapshot are optional enhancements, not default requirements.

---

## 4. Gate details

### 4.1 Test pre-approval

Reuse the existing plan structure. Add no separate approval registry, double hash, or approval PR by default. The approval may live on the plan/test-specification PR; it does not have to be merged to the default branch before implementation, provided the plan commit and trusted approval event are verifiable.

Implementation PR body fields:

```text
Plan: docs/plans/round-01.md
Approved test specification: <supported test-specification path and commit SHA>
Approval evidence: <GitHub review/comment URL>
Implementation start: <first commit SHA that changes approved implementation/test paths>
Approved scope: <FC/IR IDs, assertions, and affected test paths>
```

These fields are required only for applicable application code/test or runtime-prompt changes. Pure documentation and non-code build/dependency configuration do not require them. Non-code CI workflow/configuration changes do not require these approval fields, but executable CI/governance code does; `contract-tests` still runs `test/offline/test_ci_gates.py` for non-code governance paths according to the current classification. The changed-scope comparison uses IDs introduced on changed diff lines and changed test paths, not every ID present in the whole file, so unchanged FC/IRs do not expand the approval scope. The approved test-specification path/commit is also the source used by the contract-test job; a Plan and the test specification may be different files.

The check:

- reads the plan path/commit, approval URL, implementation start, and approved scope;
- verifies the approval is a real human GitHub review/comment, not an agent-filled boolean or local timestamp;
- excludes bot reviewers, including `type: Bot` and `[bot]` logins;
- requires exactly one clear approval line: `APPROVED test-spec: <Approved test specification value>`;
- binds that approval line to the exact `Approved test specification` value; a different version fails;
- rejects ambiguous text such as `Not approved` or `Approval pending`, even when it contains the substring `approv`;
- verifies the approved test-specification version matches the current plan/test scope;
- verifies `Implementation start` is the first commit in the PR that changes the approved implementation/test paths;
- verifies the approved test-specification commit is an ancestor of the implementation start;
- verifies the trusted approval event timestamp is earlier than the implementation start commit's recorded time;
- fails if a later change alters the affected test specification or assertion scope without a new approval;
- fails if the approval is unverifiable, the reviewer is the PR author, or the evidence is missing;
- does not treat git ancestry, git author time, local time, a label, or an `approved` field as sufficient by itself.

The negative sequence **plan commit -> implementation commit -> approval event** must fail: the trusted approval timestamp is later than the implementation start. A human review with state `APPROVED` but no exact phrase also fails. At CI-authoring time Round 1 was used as an unapproved example; its later real approval is recorded in RM-7-R1 and does not change this negative-sequence requirement.

Git ancestry proves only commit relationships. Git timestamps can be rewritten or misleading; the human reviewer remains responsible for confirming that actual coding began after approval. If the approval event cannot be dated reliably relative to the implementation start, the gate fails rather than guessing.

The current CI implementation uses this `CI.md` as its test specification. Human approval of this document must be recorded before implementation. The new gate cannot verify its own historical pre-approval; that one-time limitation is explicit and does not exempt future application changes. Only affected test specifications need reapproval when scope or assertions change.

### 4.2 Static analysis and security paths

#### Ruff

- Keep the existing `[tool.ruff]` configuration.
- Run `ruff check .` from the project root.
- Do not add whole-directory exclusions for `src/`, `test/`, or `scripts/`.
- If the current tree contains pre-existing lint failures, record exact files/rules and propose a bounded fix. Do not add broad ignores or make lint permanently non-blocking.

#### Type checking

- Use mypy as the single type checker.
- Add `mypy.ini` focused on `src/tradingagents`, `src/cli`, and CI scripts as appropriate.
- Do not require full-repository strict annotations in this task.
- If existing diagnostics require a baseline, use an exact diagnostic baseline (`mypy-baseline.txt`) that blocks new errors and can only shrink. Record this as a temporary implementation tradeoff with a named owner; it is not a new debt-management system.
- No global `ignore_errors`, no whole-package excludes, and no permanent non-blocking mode.

#### Dependencies

Required minimum:

- install the project and dev extras;
- run `pip check`;
- perform a clean install and import smoke check.

`pip check` verifies installed-dependency consistency. The clean install catches undeclared runtime imports. These are distinct checks.

Vulnerability scanning with `pip-audit` is an optional enhancement; it is not the only permitted interpretation of the course dependency requirement. If adopted later, it needs its own approved exception policy.

#### Security-path checks

All paths below are project-root-relative. The security classification follows current D1/D2 authority and boundary responsibilities; it does not classify all source code or all vendors as safety-critical.

#### Safety-critical paths

Changes here require the four security checks **plus** a valid project ADR reference. GitHub branch protection enforces the human review; the CI check does not query reviews or judge an `APPROVED` state:

- formal recommendation authority and fail-closed output:
  - `src/tradingagents/agents/managers/portfolio_manager.py`
  - `src/tradingagents/agents/rating.py`
  - `src/tradingagents/agents/state.py`
  - `src/tradingagents/agents/schemas.py`
  - `src/tradingagents/graph/setup.py`
  - `src/tradingagents/graph/trading_graph.py`
  - `src/tradingagents/reporting.py`
  - `src/tradingagents/memory/log.py`
  - `src/cli/run.py`
  - `src/cli/display.py`
  - proposed `src/tradingagents/final_recommendation.py`
  - proposed `src/tradingagents/portfolio_risk.py`
  - proposed `src/tradingagents/run_context.py`
- trusted availability and fail-closed shared behavior:
  - `src/tradingagents/dataflows/router.py`
  - `src/tradingagents/dataflows/errors.py`
  - `src/tradingagents/dataflows/date_window.py`
  - `src/tradingagents/dataflows/config.py`
  - proposed `src/tradingagents/dataflows/availability.py`
  - proposed `src/tradingagents/dataflows/query_reuse.py`
- credential and path boundaries:
  - `src/tradingagents/dataflows/net.py`
  - `src/tradingagents/dataflows/files.py`
  - `src/tradingagents/dataflows/symbols.py`
  - `src/cli/prefs.py`
  - `src/cli/prompts.py`
  - `src/tradingagents/llm_clients/chatgpt_auth.py`
  - proposed `src/tradingagents/security.py`
  - proposed `src/tradingagents/history.py`

#### Safety-relevant but not automatically safety-critical

Changes here trigger the applicable four checks, but not an automatic ADR requirement:

- `src/tradingagents/dataflows/vendors/**`
- `src/tradingagents/agents/tools.py`
- `src/tradingagents/agents/analysts/sentiment_analyst.py`
- `src/tradingagents/portfolio.py`
- `src/tradingagents/report_html.py`
- `src/tradingagents/backtest.py`
- `src/tradingagents/agents/post_screen.py`

A vendor change that alters shared availability classification, fallback semantics, or trust in an input is reclassified as safety-critical. A vendor-local implementation detail that does not affect the shared boundary remains safety-relevant.

#### Governance and CI paths

- `.opencode/**`
- `.github/**`
- `scripts/ci_checks.py`
- `scripts/ci_semantic_eval.py`
- `docs/ci/**`

Changes here require human review and the corresponding permission/gate tests. They do not automatically require an ADR unless they change an architecture boundary.

#### Checks

- **Contract:** run the approved current-round tests associated with the changed FC/IR. For CI/governance changes, run the gate tests and configuration checks instead. Do not substitute a keyword scan.
- **Security:** run the applicable existing security tests (for example `test/offline/test_get_scrubbed.py`, `test/offline/test_safe_ticker_component.py`, `test/offline/test_cli_prefs.py`, and applicable `test/offline/test_api_key_env.py` cases).
- **API surface:** run explicit assertions for selected public signatures and entry points. An unapproved, contract-breaking, or caller/test-inconsistent signature change fails. An approved interface change may update the necessary assertions and tests in the same approved scope; changing assertions alone does not establish that approval. Do not build a general API-snapshot platform unless the simple assertions are insufficient.
- **Permissions:** parse `.opencode/permissions.jsonc` with the existing JSONC/comment rules, check for old `TradingAgents/` paths, duplicate keys, and unintended broadening of writable paths. This is a configuration check, not proof of OS enforcement.

Changes to a safety-critical path require a non-empty `ADR:` PR field whose project-relative path exists under `docs/architecture/adr/`. The reference must be non-empty, resolve inside the project root, and point to an existing ADR file. An existing ADR may be cited; a changed boundary may require a new or updated ADR and human review. The CI check validates only the reference; it does not judge applicability or approval. Human approval is enforced by branch protection, not by a CI review API query, and no separate review-check mechanism is added. A safety-relevant-only change does not fail merely because no ADR is supplied; it still needs the applicable four checks and human review according to branch protection.

A security-path change that changes behavior must not require completing every FC associated with the whole module. It requires tests for the changed scope. A pure documentation change requires no non-existent application FC test.

#### Change classification and unknown paths

- Known build/dependency configuration such as `pyproject.toml`, `requirements.txt`, and CI requirements files is explicitly classified. It runs the generic static/type/dependency/regression checks and is not blocked merely for being outside the source/test trees. `setup.py` is executable code, not a non-code build exemption.
- Code outside `src/` is still code: executable files under `scripts/`, `tools/`, and `docs/`, `setup.py`, and root executables enter test approval/AI-use-log and do not receive the pure-documentation exemption. Known CI scripts use the existing governance gate tests; arbitrary helper scripts use the generic code path and are not treated as covered by fixed CI tests.
- Unknown paths still run the generic checks. They are not automatically treated as documentation. A new executable or runtime file may be unclassified, but that fact alone is not a permanent hard block.
- Ordinary documentation, images, and non-executable resources do not require application contract tests or per-file AI-use log association.
- Diff/base missing or unreadable, merge-base unavailable, or classification failure: block and report. Do not assume “not applicable”.
- Renames and deletions: evaluate both the old and new paths so a rename cannot bypass classification.
- Unknown executable paths cannot enter the docs-only exemption. They remain subject to the generic checks and are not silently classified as documentation.

### 4.3 Requirement Schema and scope traceability

Required checks:

- validate `docs/req/req-schema.json` as a Draft 2020-12 Schema;
- validate `docs/req/requirements.yaml` against it;
- print field paths and exit non-zero on error;
- check unique requirement and FC IDs;
- check active/deferred status consistency without making 13/55/9/4 permanent constants or requiring original order.

Traceability is minimal:

- current-round implementation must use the approved plan/test specification and actual tests in `test/offline/`/`test/live/`;
- tests for a changed scope must cite FC/IR IDs in names, docstrings, markers, or an equivalent reviewed convention;
- full active-FC/IR coverage is a final acceptance requirement, not a per-PR state machine;
- the final acceptance review uses D1/D2/D4 and actual test evidence; V-* intent rows do not count;
- unimplemented FCs remain visible as gaps and are not removed to make CI green.

Contract-test association:

- all executable code changes, including `src/` and code outside `src/` such as `scripts/`, `tools/`, `docs/`, and `setup.py`, require the existing `Plan`, `Approved test specification`, and `Approved scope` PR fields, together with the test-approval evidence gate;
- the `contract-tests` job reads the `Approved test specification` path at its approved commit, not the Plan’s current content; Plan and specification may be different files;
- the approved specification must name each changed code path and the selected `test/offline/`/`test/live/` paths; missing specification path/commit, a changed code path not named in the approved specification, a specification with no test paths, missing test files, zero executed cases, a skipped selected case, or any failure/error blocks;
- supported specification formats include Markdown, YAML, JSON, and text paths; the check is not limited to `.md`;
- the job checks only the current approved/changed scope; it does not scan or require every FC in the plan or repository;
- governance code may use `test/offline/test_ci_gates.py` only when the approved specification names both the changed governance code path and that gate test; non-code governance changes use the gate/configuration checks; arbitrary helper scripts are not automatically treated as covered by fixed CI tests;
- pure documentation changes require no application FC test;
- plan prose, a `V-*` intent row, or a fixed baseline security test is not accepted as new-feature coverage;
- no new approval registry is added; the existing plan/PR/GitHub evidence remains authoritative.

The current project has no complete D2 test coverage. A release/final-acceptance claim therefore remains blocked until the evidence exists.

### 4.4 Semantic evaluation for prompt/model changes

Path detection covers actual runtime prompt/model locations without treating every file under an `agents/` or `llm_clients/` directory as semantic:

- runtime prompt files under `prompts/` with supported text/config suffixes such as YAML, JSON, TXT, Jinja, and J2;
- mixed prompt/model configuration modules are compared by their relevant AST definitions rather than by file path alone: `default_config.py` and `llm_clients/factory.py` use model-related dict entries/assignments/functions; `model_catalog.py` and `capabilities.py` compare model data definitions; `agents/context.py`, `structured.py`, and `memory/reflection.py` use prompt-definition snapshots. Comment, formatting, output-path, and unrelated logic changes do not trigger semantic evidence.
- Python prompt definitions under `src/tradingagents/agents/`, `src/tradingagents/llm_clients/`, `src/tradingagents/graph/`, `src/cli/run.py`, or `src/cli/main.py` are compared between old and new Git versions using AST-level full assignment/call/function snapshots, so middle-of-string prompt edits, replacement, and deletion are detected. Model/config changes use the same AST comparison where applicable and changed-hunk model tokens for client logic; ordinary control-flow changes outside prompt/model definitions do not trigger semantic evidence.

Ordinary control-flow or formatting changes in those files do not by themselves require semantic evidence. `src/cli/prompts.py` is interactive CLI text, not a model prompt. `Prompt.md` is a development launch workflow, not an application runtime prompt, so neither is automatically subject to model semantic evaluation. Ambiguous changes may use the existing candidate-bound reviewed `semantic-eval/not-applicable` path; no new confirmation field or general semantic analyzer is added.

The minimal configuration is a single `docs/ci/semantic_eval.yaml` containing:

- dataset version and cases;
- rubric/version;
- thresholds;
- model/provider configuration;
- repetition rule if any;
- approval state and evidence reference.

No dataset, rubric, threshold, or model configuration is approved yet. The file will remain in an `unapproved` state; prompt/model changes are blocked rather than evaluated against invented standards.

The minimum semantic-evaluation loop is:

1. Main CI runs for a candidate SHA and fails the evidence check when semantic evaluation is required but no result exists.
2. A human reviews the exact candidate SHA and approves use of the protected environment.
3. The trusted default-branch workflow receives the candidate SHA as input, checks out that candidate, verifies `HEAD`, runs the approved dataset/config, and writes `semantic-eval/evidence` or `semantic-eval/not-applicable` to the candidate SHA. It records candidate SHA, workflow SHA, run ID, configuration/dataset version, and actual result.
4. The human reruns the PR CI on the same candidate SHA.
5. The evidence check reads the trusted status and artifact/record; aggregate succeeds only after this rerun and all other checks pass.

A manual evaluation does not automatically change an already failed CI run. A new commit creates a new candidate SHA and cannot reuse the prior status. No polling, automatic retry, or cross-workflow event coordinator is added.

The PR-side check uses `target_url` only to locate the trusted run. It must verify the run repository, trusted workflow path, `head_branch` equal to the repository default branch, manual dispatch, successful conclusion, candidate checkout, artifact/record values, and that the run `head_sha` matches the record `workflow_sha`. It must not require the workflow run's `head_sha` to equal the candidate SHA. GitHub Actions bot identity, status name, and `target_url` alone are not accepted as proof. A PR-provided file or an arbitrary workflow using the same status name is not valid. The status is bound to the exact candidate SHA.

A manually reviewed, justified non-semantic determination can be recorded by the trusted workflow for comment-only or layout-only changes; it is not a general self-service bypass.

This merge-blocking choice is deliberate release control. It does not make mock output, prompt-integrity tests, or `V-*` plans a substitute for real model quality.

The protected environment is not evidence that candidate code is safe. Before the trusted workflow runs, a human must review the exact candidate SHA and its diff, approve the protected environment, and limit execution to that reviewed candidate and the necessary tests. Credentials are never automatically exposed to an unreviewed external PR. A new commit requires a new review and evaluation. This is a human-review control; it reduces risk but cannot guarantee that reviewed candidate code will never leak credentials.

Optional extensions such as an LLM judge, repeated sampling, or multi-model comparison are not defaults.

### 4.5 Regression tests (live is optional)

Every code, prompt, or test change runs all existing offline tests on the existing Python/timezone matrix:

```bash
pytest -q
```

Offline collection and execution are reported separately. The current three failures and one skip remain real. No test is deleted, skipped, or weakened to get a green result.

The course does not require a new live API call for every code or offline-test change. The trusted workflow retains an optional `live` mode that runs `test/live/` with structured JUnit validation, but `live-tests/evidence` is not required by the PR aggregate and absent live evidence is not a merge failure. The optional live mode fails on zero cases, skipped required cases, failures, or errors; ordinary deselection is not used as a failure signal. It is not a substitute for semantic evaluation.

No live-test environment is required for the six course gates. The current three offline failures must be rechecked in the target CI environment and are not exempted.

### 4.6 AI-use log

Use the existing `docs/ai-use-log.yaml` format. For code, test, CI-script, runtime-prompt, or model-config changes:

Pure documentation, images, non-code CI/workflow configuration, and non-code build/dependency configuration do not require AI-use-log updates. CI scripts and other executable code still count as code.

- compare base/head entries, not only file modification; whitespace-only or structurally equivalent changes are not material;
- require at least one new or materially changed entry;
- require that at least one changed entry is associated with at least one changed code/prompt path via exact paths or a directory/description field that actually contains the changed file;
- report other changed paths without a per-file association as diagnostics, not additional blocking errors;
- preserve duplicate-ID and structure checks;
- allow empty `transcript_refs` with a pending-export note;
- do not require the current commit SHA;
- do not require transcript content.

The automated check validates structure and at least one association. It cannot prove that the recorded human intervention or evidence is truthful; human review remains responsible.

---

## 5. Files to create or modify

| File | Action | Reason |
|---|---|---|
| `.github/workflows/ci.yml` | Modify | Add the six gates, evidence checks, and mandatory aggregate status while retaining the existing matrix |
| `.github/workflows/trusted-evaluation.yml` | Add | Manual trusted semantic evaluation and optional live evidence; keeps secrets out of PR code |
| `.github/requirements-ci.txt` | Add | Pin CI-only tools without changing application runtime dependencies |
| `scripts/ci_checks.py` | Add | One small CLI for classification, approval/schema/log/API/permission checks, and aggregation |
| `scripts/ci_semantic_eval.py` | Add | Validate approved evaluation configuration and run the trusted evaluation |
| `test/offline/test_ci_gates.py` | Add | Shared positive/negative tests for the gate logic and aggregate behavior |
| `mypy.ini` | Add | Explicit type-check scope and baseline settings |
| `mypy-baseline.txt` | Conditional | Only if existing mypy diagnostics require an exact, shrinking baseline |
| `docs/ci/README.md` | Add | Gate operation, evidence format, test approval, commands, branch-protection checklist, and limitations |
| `docs/ci/semantic_eval.yaml` | Add | Single unapproved configuration container for dataset, rubric, thresholds, and model configuration |
| `README.md` | Modify | Link the gate design and document local/offline and optional live test commands |
| `docs/ai-use-log.yaml` | Modify after implementation | Record the actual CI maintenance work and evidence |

No separate test-approval registry, policy-guard workflow, gate-owner registry, API snapshot platform, full traceability database, CODEOWNERS file with invented owners, or release workflow is required by default.

`scripts/ci_checks.py` should use a small CLI/subcommand structure rather than one file per rule. Tests should share fixtures and parameterization rather than create one test file per gate.

Recommended CI-only pins at implementation time:

- `PyYAML==6.0.3` (observed locally);
- `jsonschema==4.26.0` (observed locally);
- `mypy` current stable 1.x, pinned in the CI requirements file;
- existing Ruff `>=0.16` constraint, pinned to the selected CI version;
- existing pytest/pytest-subtests from dev extras.

No application runtime dependency is changed.

---

## 6. Gate self-tests

One shared offline test module, `test/offline/test_ci_gates.py`, should use temporary Git repositories, temporary files, and synthetic GitHub API responses. It must not require credentials or a real PR.

Parameterized cases:

### Test approval

- no plan/approval evidence;
- approval URL unverifiable;
- reviewer is the PR author;
- bot reviewer (type `Bot` or `[bot]` login);
- `Not approved`, `Approval pending`, or another ambiguous comment without the exact phrase;
- `APPROVED` review without the exact `APPROVED test-spec:` phrase;
- approval phrase for a different test-specification version;
- approved test-specification commit is not ancestral;
- approved scope does not cover changed FC/IR;
- test specification changed after approval;
- missing or incorrect implementation-start commit;
- trusted approval event later than implementation start;
- **plan commit -> implementation commit -> approval event** is rejected;
- valid plan + matching test-specification version + exact phrase + earlier human approval + implementation start;
- only affected test-specification changes require reapproval;
- pure documentation/build configuration sets `approval_applicable=false` and skips this gate;
- `scripts/**/*.py`, `setup.py`, root Python files, and `docs/**/*.py` remain code and require approval/log checks; non-code `pyproject.toml`/`requirements.txt` stay configuration;
- changed-scope IDs come from changed diff lines and changed test paths; unchanged FC/IRs in the same file do not expand approval;
- Round 1 remains proposed and an application change without approval fields is blocked.

### Schema

- invalid YAML;
- invalid requirement shape;
- invalid Schema itself;
- duplicate IDs;
- deferred status inconsistency;
- valid current document.

### Static/security

- sample command exit failure;
- new type diagnostic against a synthetic baseline;
- permission JSONC duplicate key or stale `TradingAgents/` path;
- unapproved or contract-breaking API signature change;
- approved interface change with the necessary assertions updated in scope passes;
- assertion edits without approval do not establish an API change approval;
- safety-relevant change passes applicable four checks without an ADR;
- safety-critical change with missing, empty, invalid, or out-of-root ADR fails;
- safety-critical change with an existing project ADR path passes the ADR reference check without a simulated GitHub `APPROVED` event;
- the security-path gate does not query reviews, request `pull-requests: read`, or pass a review token.

### Path classification

- modified file, new file, deletion, rename, base missing, diff failure;
- `pyproject.toml`, `requirements.txt`, and CI requirements files are classified as build configuration, not unknown;
- `scripts/helper.py`, `scripts/helper.sh`, `tools/helper.py`, `setup.py`, `docs/helper.py`, and `docs/helper.sh` are executable code, not documentation; `setup.py` is not a build-config exemption;
- unknown executable/runtime paths remain outside the docs-only exemption and run generic checks; unknown alone is not a permanent hard block;
- new ordinary Markdown or image remains documentation;
- classification failure does not default to pass;
- rename/delete evaluates both old and new paths;
- deletion or modification of a gate file triggers review requirements;
- diff/base unreadable blocks with a clear error.

### Contract tests

- approved scope and existing approved-specification test path: collected and executed;
- approved specification path/commit is the selection source; a different current Plan does not select tests;
- approved specification read from a real Git commit selects its test path, not a different current Plan test;
- non-Markdown specification format is supported;
- `scripts/`, `tools/`, `docs/` executable code and `setup.py` require the same approved-spec association as `src/` code;
- missing approval fields: fail;
- missing specification path/commit, changed code path not named in the approved specification, missing test file, or specification with no test paths: fail;
- a shared approved specification and shared test path may cover multiple related code files;
- governance code may use the gate test only when the approved specification names both the governance code path and the gate test; arbitrary helper scripts are not automatically covered by fixed CI tests;
- zero collected tests: fail;
- all selected contract cases skipped: fail, not reported as executed;
- a selected contract case failing or erroring: fail;
- zero executed JUnit cases: fail;
- governance/CI change uses `test/offline/test_ci_gates.py` and permission checks;
- pure documentation change requires no application FC test;
- unimplemented out-of-scope FC does not cause a false rejection;
- plan prose or a fixed baseline security test is not accepted as new-feature coverage.

### AI-use log

- code change with no log update;
- touched or whitespace-equivalent log with no substantive entry;
- no changed entry associated with any changed code/prompt path;
- at least one changed entry associated with a changed path passes even when other changed paths are not individually listed;
- directory/description `files_changed` entry that legitimately contains the changed path;
- valid new entry;
- prompt/model change uses the same association rule;
- runtime prompt change and CI script code require the log;
- static `Prompt.md`, pure documentation, non-code workflow configuration, and build configuration do not require the log.

### Workflow version and event split

- push basic checks pass without a PR body, review, or PR head SHA;
- push is not reported as mergeable or as full course-suite completion;
- PR checks use `github.event.pull_request.head.sha`, not the merge-ref SHA;
- PR checkout and tested code match the candidate head SHA;
- PR-only checks do not run in push context;
- trusted tool checkout uses `github.sha` and is verified, candidate checkout uses the candidate SHA separately, and the protected environment/default-branch check remains.

### Semantic evidence (live optional)

- missing evidence status;
- status for a different candidate SHA;
- status written to the default-branch workflow SHA instead of the candidate;
- untrusted or same-named status from an arbitrary workflow;
- bot identity/status name/target_url alone is insufficient;
- artifact/record candidate or config version mismatch;
- trusted run is not from the repository default branch, wrong repository, wrong workflow, or not manually dispatched;
- trusted workflow version does not match the artifact record `workflow_sha`;
- checked-out HEAD does not equal candidate SHA;
- workflow run's `head_sha` differs from candidate SHA but the artifact/record matches: accepted;
- unapproved threshold/config;
- dataset/config version mismatch;
- threshold failure;
- missing credentials or environment block;
- no-op semantic review without a reason;
- manual evaluation does not automatically turn the earlier failed run green;
- re-run of PR CI on the same candidate SHA reads the trusted status;
- new SHA invalidates previous evidence;
- `prompts/*.yaml` runtime prompt changes trigger semantic and AI-use-log checks;
- inline Python prompt definitions are compared by AST old/new snapshots, so long middle-string edits, replacement, and deletion trigger; ordinary logic outside prompt definitions does not; model/config changes use AST model definitions or hunk model tokens;
- `default_config.py` comment, formatting, output-directory, and unrelated logic changes do not trigger semantic evaluation; its actual model/provider/temperature/max-token/backend/thinking/effort/output-language changes do;
- `agents/context.py` unrelated logic does not trigger while prompt-definition changes do;
- `Prompt.md` and ordinary documentation/configuration do not trigger semantic evaluation;
- unapproved semantic configuration blocks only prompt/model changes, not unrelated changes;
- optional live result: collect-only is not execution; zero cases, a skipped required case, or a failed/erroring case fails; ordinary deselection with the required cases present passes;
- missing optional live evidence does not fail the aggregate.

### Aggregate

- the aggregate is an implementation choice, not a seventh course gate;
- all required jobs pass;
- one job fails;
- one job is cancelled;
- one required job is skipped without an applicability reason;
- an optional job is skipped with a valid not-applicable reason;
- evidence artifact missing;
- an applicable test-approval job skipped, failed, or cancelled fails; a non-applicable documentation/build job may be skipped;
- an applicability value is missing or invalid, so a conditional skip cannot silently pass;
- a workflow change removes the aggregate job or required steps.

These tests validate the gate logic. They do not replace actual Ruff, mypy, dependency, or regression runs; live runs are optional.

---

## 7. Phases and blocking decisions

### Phase 0 — review and approval

- Human reviews this document and approves it as the test specification for the CI implementation.
- Human approves CI-only tool installation, the test-approval evidence convention, and the one-time test-specification approval for this CI implementation itself.
- No application code or workflow implementation starts before this approval.

### Phase 1 — scripts and gate tests

- Implement `scripts/ci_checks.py`, `scripts/ci_semantic_eval.py`, `mypy.ini`, and `test/offline/test_ci_gates.py`.
- Run the new offline gate tests.
- Do not modify application behavior.

### Phase 2 — workflow wiring

- Modify `.github/workflows/ci.yml`.
- Add `.github/workflows/trusted-evaluation.yml`.
- Add `.github/requirements-ci.txt`.
- Add `docs/ci/README.md` and `docs/ci/semantic_eval.yaml`.
- Update `README.md`.
- Run local static checks where tools are available.

### Phase 3 — human configuration

- Configure required status `ci / aggregate`.
- Configure branch protection, human review, stale-review dismissal, and security-path ownership.
- Configure the protected semantic environment and any optional live environment/secrets.
- Approve the semantic evaluation dataset, rubric, threshold, and model configuration.
- Recheck existing failures in the target CI environment.

### Blocking decisions

1. Authorize CI-only installation of PyYAML, jsonschema, mypy, and the selected Ruff version.
2. Name the human test approver and accept the plan-review evidence method.
3. Approve the semantic dataset, rubric, quality threshold, model configuration, and secret/cost environment.
4. Configure branch protection and human security reviewers/ADR responsibility; no real owner accounts are currently known.
5. Decide how the three existing test failures and dependency-version drift are fixed. They remain red until resolved; this CI task does not change application code.
6. Approve mypy's exact baseline/convergence approach if existing diagnostics require a temporary baseline.

CI implementation does not approve Round 1 application work or any D2 behavior.

---

## 8. Optional enhancements — not default merge blockers

- `pip-audit` vulnerability scanning with time-bounded exceptions.
- A separate trusted `policy-guard` workflow.
- A gate-owner registry or CODEOWNERS enforcement beyond native branch protection.
- A generated API-surface snapshot platform.
- A complete active-FC/IR traceability state machine.
- LLM-as-judge scoring, repeated sampling, or multi-model comparison.
- Merge-queue and release-branch workflows.
- Coverage percentage thresholds.
- Extra bootstrap metadata files or approval platforms.

These may be adopted later through separate approved work. They are not required to satisfy the six course gates in this plan.

---

## 9. Unmet or unverified course requirements

Current GitHub execution evidence: the PR and main workflow runs recorded for PR #7 (Round 1) and PR #9 (contract-test path fix) completed successfully at workflow level in RM-7-R1 and RM-9-R1. Individual job outcomes, branch protection, permission enforcement, and semantic/live evidence were not separately verified. Remaining "unverified" statements below refer to those unverified aspects, not to the absence of any successful PR/main workflow run.

- Test pre-approval: the explicit `APPROVED test-spec:` phrase, bot exclusion, and version binding are implemented and offline-tested. Round 1's real pre-approvals and merged PR are recorded in RM-7-R1; PR #10 records the fixed-version Round 2 plan/test-spec pre-approval, with C-09 still unimplemented and no safety-critical implementation approval, execution evidence, or final acceptance; individual gate-job results and branch-protection enforcement remain unverified.
- Trusted evaluation source: default-branch and trusted-workflow-version checks are implemented and offline-tested; no real trusted run exists.
- Optional live result: JUnit-based execution/skip/deselection logic is implemented and offline-tested; the live suite has not been run and is not a merge gate.
- Build/unknown classification and contract-test association: implemented and offline-tested; unknown paths run generic checks without a permanent hard block; PR #9 exercised the contract-path fix at workflow level, but individual job results were not separately checked.
- Security-path contract coverage: new D2 tests do not exist; security changes remain blocked.
- Type checking: mypy configuration and an exact baseline are implemented locally; workflow-level PR/main runs succeeded for the recorded PRs, but the type-check job result was not separately verified.
- Dependency check: `pip check` is wired into CI; workflow-level runs succeeded, but the dependency/install job results and installation consistency were not separately verified.
- Schema: validation is wired into CI and passes locally; workflow-level runs succeeded, but the schema job result was not separately checked.
- Semantic evaluation: no approved dataset, rubric, threshold, configuration, or evidence.
- AI-use-log gate: implemented and passes the local association check; workflow-level runs succeeded, but the AI-use-log job result was not separately verified.
- Regression: current local 3 failures and 1 skip are real; workflow-level PR/main runs succeeded, but individual regression job results and target-CI behavior were not separately checked.
- Live tests: optional and not required by the course gates; no live evidence is claimed.
- Full active-FC/IR coverage: not established.
- Branch protection: not configured or verified.
- Required CI aggregate: implemented as the PR-only `ci / aggregate`; workflow-level PR runs succeeded, but the aggregate job outcome was not separately checked and branch protection is not configured or verified.
- CI self-protection: only native human review is proposed; no strong policy guard.
- D2 design and ADR remain Proposed; no application acceptance is claimed.

---

## 10. Status conclusion

- This document's implementation scope was approved by the human user and the files are present in the current checkout.
- Round 1 and PR #9 have real approvals, merges, and workflow-level PR/main success (RM-7-R1, RM-9-R1). This does not prove individual job success or branch-protection enforcement.
- Local implementation does not enable branch protection or prove per-job GitHub CI execution.
- A green local gate test does not prove semantic quality or optional live model/vendor behavior.
- Semantic evaluation stays blocked without approved standards; the optional live workflow is not a course gate.
- Remote branch protection, individual required-job results, and full permission enforcement remain unverified; this implementation does not claim full course compliance.
- No application behavior, requirements, thresholds, machine permissions, or approval records were changed by this document.
