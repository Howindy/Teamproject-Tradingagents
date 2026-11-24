# D4 Review Memo

- Document status: Reusable review-record template with two historical closeout records and one AI-authored implementation-review draft whose final human `APPROVED` event is separately transcribed from user-provided GitHub evidence. The AI-authored analysis remains distinct from the human verdict; this update is not a new review or approval.
- Registered records: RM-7-R1 and RM-9-R1 are historical human closeout records; both GitHub review bodies are empty and written rationale was not provided. RM-10-R1's analysis was authored by the AI; its later human formal review and written rationale are transcribed separately below. The AI did not select or invent the human verdict.
- Purpose: Keep one human-reviewed memo per PR, covering specification and architecture alignment, code and test quality, operational metadata, security, and efficiency.
- Related records: [Bug diary](bug-diary.md) and [Debt register](debt-register.md).

This file is a record format, not a second requirements document, a test plan, or a new approval gate. Passing tests do not constitute review approval, and an AI-authored draft does not constitute a human verdict.

## 1. Recording rules

1. Add one record per PR. Append new records or review rounds; do not erase earlier findings, verdicts, or evidence.
2. Use the actual PR number and URL. When no PR exists, write `PR: none` and label the material as a pre-PR verification summary; do not invent a PR number or a final PR verdict.
3. Record only events that actually occurred. If a review has not happened, keep the reviewer, time, and verdict placeholders unfilled.
4. Record actual commands, environments, failures, skips, and blocks. Link to raw output or an authorized evidence artifact instead of duplicating a full test log here.
5. Apply only the approved round scope and existing D1/D2/D4 obligations. Do not introduce new quality thresholds, efficiency targets, or acceptance criteria in this file.
6. The final verdict must be one of `APPROVE`, `CHANGES REQUIRED`, or `REJECT`. Only a human reviewer may select it and provide the rationale.
7. Use stable record IDs so other QA records can link back. A suggested ID is `RM-<PR-number>-R<review-round>` when a PR exists, or `RM-LOCAL-<sequence>-R<review-round>` for a pre-PR summary.

## 2. Reference basis

Use the current approved inputs that apply to the actual PR. Do not treat a Proposed or draft document as review evidence.

- Round plan: [`docs/plans/round-01.md`](plans/round-01.md) is the frozen approved Round 1 specification at `a8ec42ecdf4199f91d3001fc6e2b1e887a0c5e41`; its internal Pending/Proposed cells are historical pre-approval text, not the current approval record.
- Round 2 plan: [`docs/plans/round-02.md`](plans/round-02.md) is frozen at `8ad99c25ea1acd77b6e019fbe3c357899e8fc535`; its internal Pending cells remain the pre-implementation specification and are not rewritten by the later approval, execution, review, or merge evidence.
- Verification rules: [`docs/code-governance/verification-constraints.md`](code-governance/verification-constraints.md).
- Requirements: [`docs/req/requirements.yaml`](req/requirements.yaml) v1.48.0.
- D2 invariants: [`docs/architecture/invariants.md`](architecture/invariants.md).
- Trace matrix: [`docs/architecture/trace-matrix.md`](architecture/trace-matrix.md).
- Runtime policies: [`docs/architecture/runtime-policy-catalog.md`](architecture/runtime-policy-catalog.md).
- Relevant ADR: [`ADR 001`](architecture/adr/001-graph-internal-final-check.md).

For the currently available Round 1 plan, the candidate review scope is the FR-04 core FCs `FR-04-FC01` through `FR-04-FC04` and the core portion of `IR-14`; `FR-04-FC05` and the entry/graph/report portion of `IR-14` are excluded by that plan. For Round 2, the reviewed scope is the C-09/IF-09 independent core, `SB-01-FC01` through `SB-01-FC04`, and local `IR-01`/`IR-02` responsibility; production integration, `SB-01-FC05`, full SB-01, global invariant acceptance, `IF-19`, and the FR-03 producer remain excluded. This is plan context only. Record the IDs that the actual PR implements and test evidence demonstrates, not a whole-requirement claim inferred from the plan.

## 3. Review record template

Copy the structure below for each actual PR. Replace every angle-bracket placeholder with recorded evidence or an explicit `none`, `not applicable`, or `not recorded` value. Do not replace a placeholder with an assumed fact.

### RM-`<PR-number-or-local>`-R`<review-round>`

#### Identification and scope

| Field | Recorded value |
|---|---|
| Review ID | `RM-<PR-number-or-local>-R<review-round>` |
| PR link and number | `<PR URL and number, or "none" for a pre-PR summary>` |
| Round plan reference | `<plan path and exact approved version/commit, or "none">` |
| Reviewed commit or tree | `<commit/tree reference; do not use "latest">` |
| Application/test/input version | `<versions or immutable references actually reviewed>` |
| Review time | `<UTC timestamp with timezone, or "not recorded">` |
| Reviewer | `<human reviewer, or "not recorded">` |
| Change summary | `<concise description of the actual change>` |
| Changed files | `<actual file list or bounded diff reference>` |
| Requirement / FC IDs | `<actual IDs, for example FR-04-FC01; list only covered IDs>` |
| Invariant / runtime policy IDs | `<actual IR/RP IDs, or "none">` |
| ADR decision IDs | `<actual ADR decisions, or "none">` |
| Excluded or deferred scope | `<explicit exclusions, including deferred FR-06/FR-07/PR-01/CR-01 where relevant>` |

#### Pre-approval and safety gates

| Gate | Actual state and evidence |
|---|---|
| Execution plan approved before implementation | `<approved version/date/location, or "not verified">` |
| Specific tests approved before implementation | `<approved test scope/version/location, or "not verified">` |
| Safety-critical ADR and human approval | `<applicable decision/approval evidence, "not applicable", or "pending">` |
| Round permissions and output locations ready | `<actual scoped setup evidence, or "not verified">` |

Do not infer any of these from the existence of a plan, a Proposed ADR, a passing test, or an AI summary.

#### Quality review

**Specification alignment**

- Expected behavior and source: `<D1 requirement/FC and applicable boundary or failure rule>`
- Actual implementation behavior: `<observed behavior or reviewed code path>`
- Gaps or deviations: `<none found, or specific gap with evidence>`
- Notes on applicability, exact boundaries, invalid input, and authority boundaries: `<actual review notes>`

**Architecture alignment**

- Expected D2 component/interface/ownership: `<IF-*, component, module owner>`
- Actual integration and ownership: `<observed modules, calls, state, or boundaries>`
- Authority and failure semantics: `<formal authority, pass-through, blocked/error/REVIEW, persistence and manifest behavior as applicable>`
- Gaps or unapproved deviations: `<none found, or specific gap with evidence>`

**Code quality**

- Scope discipline: `<only approved files and minimal increment, or deviation>`
- Readability and local design: `<observations>`
- Error handling and fail-closed behavior: `<observations>`
- Dependencies, imports, side effects, and forbidden abstractions: `<observations>`
- Secret handling or unsafe diagnostic exposure: `<observations or "not in scope">`

**Test quality**

- Independent expected results: `<source of the oracle; confirm it is not the implementation under test>`
- FC/IR traceability: `<test names/docstrings/markers and cited IDs>`
- Negative and boundary coverage: `<actual cases>`
- Invariant violation detection: `<actual must-fail case, or "not applicable">`
- Regression preservation: `<old tests changed or weakened? evidence>`
- Test gaps and residual risk: `<specific gaps>`

#### Verification results

Record actual outcomes only. `Not run`, `skipped`, and `blocked` are not passes.

| Check | Scope or command | Actual result | Evidence link or reference |
|---|---|---|---|
| Structural | `<scope/check>` | `<passed/failed/not run/not reviewed>` | `<link>` |
| Regression | `<prior suites/command>` | `<passed/failed/not run/blocked>` | `<link>` |
| Behavioral (offline) | `<targeted tests/command>` | `<passed/failed/not run/blocked>` | `<link>` |
| Behavioral (live/integration, if authorized) | `<command or CI run>` | `<passed/failed/not run/not authorized>` | `<link>` |
| Lint/type/dependency/schema | `<commands or CI jobs>` | `<passed/failed/not run/not available>` | `<link>` |

**Operational metadata**

- Environment and versions: `<OS/interpreter/dependency/environment reference>`
- Exact commands or CI run reference: `<commands and working directory, or CI run URL/ID>`
- Test files and fixed fixtures/input version: `<references>`
- Failures, skips, environment blocks, and baseline failures: `<actual list and explanation>`
- Evidence location: `<authorized report, log, artifact, or CI link>`

#### Security and efficiency review

Keep this review within the actual PR scope. Do not invent a scanner, threshold, benchmark, or security guarantee.

- Security-relevant scope: `<SR/IR/ADR IDs or "none">`
- Credential, path, authority, and fail-closed review: `<findings and evidence>`
- Security residual risk or limitation: `<actual limitation>`
- Efficiency-relevant changes: `<new calls, loops, data volumes, dependencies, or "none observed">`
- Efficiency evidence: `<approved measurement/CI evidence, or "not measured">`
- Efficiency threshold status: `<approved threshold or "not applicable; no threshold introduced">`

#### Issues and re-review

| Issue ID | Finding | Required action | Owner | Status | Evidence of resolution |
|---|---|---|---|---|---|
| `<review-local issue ID>` | `<specific issue>` | `<action>` | `<human owner or blank>` | `<open/fixed/rechecked/etc.>` | `<link or "not yet resolved">` |

**Re-review history**

| Review round | Verdict | Reviewer | Time | Rationale and affected evidence |
|---|---|---|---|---|
| `R<round>` | `<APPROVE / CHANGES REQUIRED / REJECT, if actually decided>` | `<human reviewer>` | `<UTC timestamp>` | `<short rationale and links>` |

Repeat the history row only for real review rounds. Do not prefill a future verdict.

#### Final human review

- Final verdict: `<Not decided; human must select APPROVE, CHANGES REQUIRED, or REJECT>`
- Rationale: `<human reviewer's actual rationale>`
- Reviewer identity: `<human reviewer, or "not recorded">`
- Review time: `<UTC timestamp with timezone, or "not recorded">`
- Approval record or signature: `<link/record reference, or "not recorded">`

An AI may draft findings, checklists, and a recommended disposition, but it must not impersonate the reviewer or complete this verdict. If a PR has no final human decision, this record remains unfinished.

## 4. Registered records

### RM-7-R1

- Record type: Historical transcription of the GitHub `APPROVED` event, corresponding to `APPROVE` in this memo; not a new AI-authored verdict.
- PR: [#7](https://github.com/Howindy/Teamproject-Tradingagents/pull/7), `MERGED`.
- Round plan: `docs/plans/round-01.md @ a8ec42ecdf4199f91d3001fc6e2b1e887a0c5e41`.
- Final review: commit `6325db571a14a059ea39ac0d94afa5e8223269bb`; reviewer `espino2233`; state `APPROVED`; time `2026-11-21T16:36:19Z`. The review body is empty; no written rationale was provided.
- Merge: `2026-11-21T16:37:00Z`, commit `eb861e060993ee20bb561246ca5f745d6300dff0`.
- Scope: C-08 core, `FR-04-FC01` through `FR-04-FC04`, and the core portion of `IR-14`; ADR 001 D-11/D-12/D-12a. `FR-04-FC05`, complete `IR-14`, entry/graph/report integration, and C-09 remain excluded.
- Pre-approval: [test specification](https://github.com/Howindy/Teamproject-Tradingagents/pull/7#issuecomment-7063035434) and [safety-critical approval](https://github.com/Howindy/Teamproject-Tradingagents/pull/7#issuecomment-7063094382) are separate events.
- CI: [PR run 44925212277](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/44925212277), `pull_request`, head `6325db571a14a059ea39ac0d94afa5e8223269bb`, completed/success; [main run 44925551661](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/44925551661), `push`, head `eb861e060993ee20bb561246ca5f745d6300dff0`, completed/success.
- Verification scope: `src/tradingagents/portfolio_risk.py` and `test/offline/test_fr04_risk.py`. R01-01 through R01-15 are specification scenario IDs; actual tests are the functions in that file. Historical local results and limitations remain in AI-045 and AI-047; no new test execution is claimed here.
- Evidence limit: User-provided, checked GitHub facts are transcribed at workflow level; individual job results were not separately checked for this record. Merge and CI success do not supply a missing review rationale or prove unimplemented integration.

### RM-9-R1

- Record type: Historical transcription of the GitHub `APPROVED` event, corresponding to `APPROVE` in this memo; not a new AI-authored verdict.
- PR: [#9](https://github.com/Howindy/Teamproject-Tradingagents/pull/9), `MERGED`.
- Specification: `docs/plans/ci-contract-test-paths-fix.md @ fbbafc61dcd5bf6c527cabfa6af3b9a3a3942de1`.
- Pre-approval: [comment 7065323701](https://github.com/Howindy/Teamproject-Tradingagents/pull/9#issuecomment-7065323701), `espino2233`, `2026-11-21T16:01:47Z`.
- Fix/final review commit: `ff3e32bf952538a1f8c5c37b8129e765f6865d1d`; reviewer `espino2233`; state `APPROVED`; time `2026-11-21T16:21:14Z`. The review body is empty; no written rationale was provided.
- Merge: `2026-11-21T16:21:26Z`, commit `43ac0bb27ca29e7eff797d06689bfbb61e084046`.
- Scope: Exact-basename placeholder filter in `scripts/ci_checks.py` at `plan_test_paths`, with six regression scenarios in `test/offline/test_ci_gates.py`; real-path extraction, existence checking, collection and execution remain intact. This is CI maintenance, not acceptance of an application FC.
- CI: [PR run 44923393413](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/44923393413), `pull_request`, head `ff3e32bf952538a1f8c5c37b8129e765f6865d1d`, completed/success; [main run 44924133256](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/44924133256), `push`, head `43ac0bb27ca29e7eff797d06689bfbb61e084046`, completed/success.
- Verification: T1-T6 are specification scenario IDs, not function names. AI-038 records user-reported post-fix `76 passed in 8.07s`, pre-fix `5 failed, 1 passed in 0.36s`, target Ruff passed, mypy baseline `errors=[]`/`fixed=[]`, and a clean diff check. OpenCode did not execute those checks.
- Evidence limit: Workflow-level results are recorded without inferring every individual job's outcome. No application behavior, permission, dependency, or baseline change is accepted by this maintenance review. Related defect: [BUG-01](bug-diary.md#bug-01-contract-test-placeholder-path).

### RM-10-R1 (AI-authored draft; final human approval transcribed below)

- Record type: AI-authored post-implementation review draft for PR #10 with a separately transcribed final human `APPROVED` event. The analysis and findings below remain AI-authored. The human verdict and rationale are recorded only from the real GitHub event and linked comment; the AI did not select them or authorize merge.
- PR: [#10](https://github.com/Howindy/Teamproject-Tradingagents/pull/10), `MERGED`. Historical draft-time state, retained: the working tree was uncommitted and no candidate commit or reviewed SHA had been formed. Final reviewed implementation commit: `fbba457a9235ef53de52604f9b591aaf89a1972b` (H). Merge commit: `cc8b17596a81751bd6165899423dd511e93dc394` (M), merged at `2026-11-22T06:29:54Z`.
- Frozen specification: `docs/plans/round-02.md @ 8ad99c25ea1acd77b6e019fbe3c357899e8fc535`.
- Scope: C-09/IF-09 independent core; `SB-01-FC01` through `SB-01-FC04`; local `IR-01`/`IR-02` responsibility. Excluded: `SB-01-FC05`, full SB-01, global IR-01/IR-03/IR-04, IF-19, graph/entry/report/memory/checkpoint/RunContext/manifest integration, the FR-03 producer, and FR-04-FC05.
- Approvals: [test specification](https://github.com/Howindy/Teamproject-Tradingagents/pull/10#issuecomment-7073333663) and [C-09 safety-critical implementation](https://github.com/Howindy/Teamproject-Tradingagents/pull/10#issuecomment-7074759911). At draft time the user reported an Approve without supplying the complete review object, time, or reviewed SHA; that limitation is retained as history and did not approve future additional code. The later formal review and separate written rationale are recorded below.
- Changed files reviewed: `src/tradingagents/final_recommendation.py` and `test/offline/test_sb01_final_check.py`. The original record-maintenance activity also appended the AI-use log, review memo, and bug diary; it did not change application or test behavior.

**Specification alignment**

- The callable is the fixed four-parameter `evaluate(proposal, availability, risk, asset_type)` with no defaults, supporting positional and keyword calls.
- Proposal handling preserves only safe `rating`/`text` strings, uses `None` for missing/non-string fields, blocks illegal strings including `REVIEW`, treats missing/wrong-type/empty/whitespace conclusions as ordinary blocked input, and does not parse a rating from text.
- Availability handling consumes only `basic_completeness`, `applicability_note`, and necessary-item status/reason; it applies the specified complete/incomplete/not_applicable conditions, ignores supplementary-only limitations, and does not rebuild completeness or read a registry.
- Risk handling accepts only exact stock Buy/Overweight `status == "passed"`; other applicable outcomes block, upstream risk error is not C-09 error, and other legal stock/crypto ratings do not require risk.
- Passed preserves the original rating and valid text. Blocked/error produce `REVIEW` and a program-generated manual-review notice from actual reasons. The result has exactly the five required fields and no `status`/`gate_reasons`/`present` alias. No integration, IF-19, or production default is introduced.

**Architecture and code/test review**

- The module is pure and imports only the standard library. It has no model, data, graph, storage, manifest, or risk-recomputation call and no production fault-injection parameter.
- Tests were authored before implementation with hand-controlled fixtures and independent round-table expectations, not implementation-generated oracles. Codex's read-only review identified issues in cause/notice separation, original-proposal separation, unrelated-field key checking, and the exception-injection approach; OpenCode applied the corresponding test/code corrections.
- The implementation generates new result containers, does not mutate inputs or share mutable input containers, and catches only its own unexpected exception into a fixed safe error/REVIEW while preserving the safely projected proposal.
- The tentative `_evaluate_impl` boundary is the private result assembler; `evaluate` performs projection and ordinary input validation before calling it, so the existing test monkeypatch lands after validation. The name is not an approved production contract.
- User-executed Ruff found SIM114; the equivalent R02-02 branches were merged. User-executed mypy found a `note.strip` union-attr; an `isinstance(note, str)` narrowing was added without changing business behavior. No baseline, assertion, dependency, or rule was weakened.

**Verification results**

| Check | Actual result | Evidence / attribution |
|---|---|---|
| Target behavior | `99 passed in 0.58s` | User-executed; `targeted.xml` |
| Target Ruff | Passed | User-executed terminal |
| `pip check` | No broken requirements | User-executed terminal |
| mypy baseline | `errors=[]`, `fixed=[]`; not repository-wide zero | User-executed; `mypy-current.txt` read by Codex |
| Requirements schema | `errors=[]`; 9 active/40 FC; 4 deferred/15 FC | User-executed terminal |
| Permissions / API | Permissions `errors=[]`/`warnings=[]`; API `errors=[]`; not runtime authentication | User-executed terminal |
| Full Ruff | Initial `38` errors from untracked `tmp/round-01/regression-pytest` historical artifacts; excluding only that directory passed | User-executed; initial failure retained |
| Default regression | `3 failed, 1615 passed, 1 skipped, 1 deselected, 20 warnings, 100 subtests passed in 15.37s`; integration excluded | User-executed; `regression.xml` read by Codex |
| Remote CI at draft time | Not verified for this code | None; retained as the draft-time state |
| PR CI after H | [run 44993034732](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/44993034732), `pull_request`, completed/success | User-provided GitHub output; workflow level only; H |
| main CI after M | [run 44993981274](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/44993981274), `push`, completed/success | User-provided GitHub output; workflow level only; M; PR-only jobs were skipped, so this is not evidence that every PR task ran in push |

- The three regression failures are the existing `test_cache_writes.py` `errno.EDEADLOCK` cases recorded in [BUG-02](bug-diary.md#bug-02-macos-windows-lock-tests); the skip is the optional `langchain_aws` absence. These are not passes.
- Operational metadata: interpreter `/Users/ichihann/Desktop/CS5351/round1-runtime/bin/python` resolved to the current checkout. All commands were executed by the user; Codex performed read-only source review and read the target/regression JUnit and mypy report; OpenCode did not execute or read the raw reports. Evidence paths: `/private/tmp/cs5351-round02/targeted.xml`, `/private/tmp/cs5351-round02/regression.xml`, and `/private/tmp/cs5351-round02/mypy-current.txt`; these are local temporary files, not committed or remote CI evidence.

**Security and efficiency**

- Security-relevant scope is the fail-closed formal-result core. No credential, path, network, model, data, or storage boundary is added or exercised; no generic scanner or new policy is introduced.
- No new dependency or external call is added. The core iterates over the supplied necessary items and their reasons; no complexity or performance guarantee is claimed. Efficiency was not measured and no performance threshold is introduced.

**Open issues and remaining limits**

| Issue | Finding | Required action | Status |
|---|---|---|---|
| RM10-I1 | Working tree is uncommitted; no candidate SHA exists | Form the candidate and review the exact diff | Resolved at the workflow level: H `fbba457a9235ef53de52604f9b591aaf89a1972b` was reviewed and merged as M `cc8b17596a81751bd6165899423dd511e93dc394`; the original finding remains as draft-time history |
| RM10-I2 | Remote CI for this Round 2 code is unverified | Run the applicable CI after candidate formation | Resolved at the workflow level: PR run 44993034732 and main run 44993981274 are completed/success; main skipped PR-only jobs; individual job results were not separately inspected |
| RM10-I3 | Default regression retains three BUG-02 failures and one optional skip | Keep BUG-02 open; no waiver or platform fix in this round | Open |
| RM10-I4 | Initial full Ruff failed on untracked historical generated artifacts | Preserve the failure; decide cleanup separately without lowering rules | Open |

Uncovered integration: no graph/Portfolio Manager/state/CLI/report/memory/checkpoint/RunContext/manifest attachment, no IF-19 validator, no FR-03 producer, and no current-run sourcing. A pure-core pass would not establish full SB-01 or global invariant acceptance.

#### Final human review

- Final verdict: `APPROVE`, transcribed from the GitHub review state `APPROVED`.
- Rationale: The formal review body is empty. A separate ordinary comment by the same reviewer at `2026-11-22T06:25:42Z` records approval of the independent core and limited closeout while retaining local failures and integration exclusions: [comment 7075320080](https://github.com/Howindy/Teamproject-Tradingagents/pull/10#issuecomment-7075320080).
- Reviewer identity: `espino2233`.
- Review time: `2026-11-22T06:25:52Z`; reviewed implementation commit H `fbba457a9235ef53de52604f9b591aaf89a1972b`.
- Approval record or signature: PR #10 formal review event on H; the rationale is the linked ordinary comment, not the empty review body. Merge M `cc8b17596a81751bd6165899423dd511e93dc394` at `2026-11-22T06:29:54Z`.
- Evidence limit: The review event, comment, commit, merge, and workflow-level CI facts are user-provided GitHub output. The AI did not query GitHub or inspect individual CI jobs; the approval covers only the frozen independent core and limited closeout, not production integration or full SB-01.

## RM-12-SCOPE — Six-active scope revision (AI review draft; final human verdict pending)

- PR: https://github.com/Howindy/Teamproject-Tradingagents/pull/12
- Baseline: main closeout merge `91dc374e8ff6ddd770a7eb693fc98af710f187ad`.
- Frozen specification P: `cc2c834c3ce9097f08d95b4beef1a5dc1bb0b7e9`; unchanged after approval.
- Pre-approval: non-author `jyy722`, 2026-11-23T01:37:12Z; exact test-spec line and explicit architecture/scope amendment verified through GitHub API at comment 7089283044. PR author Howindy; remote head was P before local implementation edits.
- Implementation T / final H: not committed yet; populate using the actual first classifier-relevant commit. No publication/merge performed by the assistant.

### Scope and architecture alignment

Keep 13 requirements / 55 FCs; current six active / 27 FCs, seven deferred / 28 FCs. Only FR-04-FC05, SB-01-FC05, INV-01-FC01, SR-01-FC01 and SR-01-FC04 lose the approved manifest-specific clauses. FR-02/FR-05/SR-02 future FCs remain intact. Current trace and D4 each have 27 unique active rows. C-03 remains ephemeral reuse/availability scope; manifest/new precise stats/history/path work is deferred. Mixed save/cleanup rules retain primary-error and formal-result protection. Prior design details are explicitly archived as future/historical, not silently applied to current implementation. R1/R2 core evidence, business contracts, 15 observation paths, seven necessity items and three summary times remain.

### Actual local verification and limitations

Interpreter: existing round1-runtime Python; temporary results under `/private/tmp/cs5351-six-active/`. No dependency installation, live call or application change.

| Check | Observed result |
|---|---|
| Existing schema checker | No errors; exact counts 13 / 55 / 6 / 27 / 7 / 28 |
| Requirement/FC preservation | Same ID sets; only five approved FC objects changed |
| Gate suite in restricted sandbox | 70 passed, 6 failed because loopback socket binding was denied |
| Gate suite with authorized loopback execution | 76 passed, no skips; gates-unrestricted.xml |
| Default prior regression | 1615 passed, 3 failed, 1 skipped, 1 deselected; 100 subtests passed; regression.xml |
| Regression failures | Three unchanged Windows-lock emulation cases use errno.EDEADLOCK unavailable on macOS; matches existing BUG-02 limitation; not waived or fixed by this task |
| Optional skip | langchain_aws unavailable; not installed by this task |
| Full repository Ruff | Failed: 38 errors in pre-existing untracked tmp generated probe files; no cleanup/rule relaxation performed |
| Tracked Python Ruff | Passed using git ls-files Python/pyi list and unchanged Ruff configuration |
| Mypy baseline | errors=[] and fixed=[]; unchanged baseline |
| Dependency / API / permission checks | Passed; permission file and public APIs unchanged |

Full local regression and full-directory Ruff are **not green**. Tracked-file lint does not replace or erase the failed full-directory command. The existing records already identify BUG-02 and generated-artifact Ruff limitations; remote Linux outcomes remain separate evidence. No remote final gate result, product acceptance, safety escape claim or final human verdict is fabricated.

### Human review / next handoff

Pending real final human review. This section is AI-authored preparation, not an APPROVE/CHANGES REQUIRED/REJECT verdict on a human's behalf. Required next facts: actual T/H and completed PR fields, current PR-event CI including aggregate, resolution/review of reported limitations, final review and authorized merge. AI-use logging is pending user consolidation; the assistant-authored AI-058/AI-059 entries were removed at the user's explicit request. No raw transcript was invented.

### Classifier applicability clarification

Working-tree path classification using unchanged classify_paths returned approval_applicable=false, ai_log_required=true, security_applicable=true, semantic_required=false. The governance-only test is excluded from application_tests; no executable script/application path changes. Consequently this diff uses governance contract mode (the fixed gate suite), rather than automatic test-approval mode. The specification anticipated automatic approval applicability; this expectation does not match the existing classifier. Real prior non-author approval was nevertheless independently verified and preserved. No classifier edit or artificial application change was made to force applicability; do not report a skipped test-approval job as machine-verified pre-approval. The exact test pre-approval remains manual/API-reviewed evidence for this PR. This clarification requires human review of the applicability discrepancy, not retroactive alteration of frozen P.

AI-use association check: errors=[], required=true, changed_entries=1, unassociated_paths=[]. Final source/schema/workflow/control and frozen-plan preservation checks are local working-tree checks, not remote CI.

### Follow-up consistency correction — 2026-11-23

The user requested resolving substantive review findings without reducing/restructuring the documentation diff or archive. This follow-up is within the existing six-active scope; frozen specification P remains unchanged.

- D2 dependency rules and current verification tables no longer require C-04 callbacks, pre-construction manifest projection, timing/counts, new persistent IDs/status or manifest attempts. Baseline callbacks and saves remain.
- C-03 consistently owns ephemeral binding/reuse/availability only. CLI scope starts after effective config/basic validation and before graph-object construction; propagate scope is per validated invocation. Explicit delegation shares scope. Acquiring owners clean up, then finish restores binding. No resource double-close or persisted terminalization.
- C-08/C-09 use their existing primitive/mapping signatures, without a RunSpec/DTO import or framework. IF-09 explicitly lists all five required result fields. IF-18 uses existing writer/save options with passed state, not a new output-reference registry.
- Current ADR selected-design failure semantics, invariants, runtime vocabulary/intents, candidate-selection rationale and D3 component allocation now match that scope. Historical ADD decisions and future archives are retained as history, not current tasks.
- IR-05/IR-07 D4 rows again have seven columns, specific injected violations and independent must-fail assertions. Current setup/save/cleanup verification removes deferred FR-02 duties while preserving error priority, no rollback and formal-result protection.
- Current SR-01 candidate/verification covers credentials; new SR-02 resolved-target controls remain deferred. Existing ticker guards remain.

Executed follow-up checks: schema no errors and exact 13/55/6/27/7/28; requirement and FC ID sets preserved; only the five approved FC objects changed; deferred statements/FCs retained; dependency sets checked; exact 27 unique current FC mappings in trace and D4; 14 current invariant verification rows, all seven columns; approved-file boundary and unchanged source/workflow/scripts/schema/permission/frozen-plan checks; git diff --check passed. These finite checks and focused review do not mechanically prove every architecture statement or implement any feature. Prior gate-suite result and full regression/Ruff findings remain as recorded above; no new full-suite green claim.

Residual preconditions: entry input/UI choices, actual role configuration and producer/framework attachment verification remain pending where applicable. Context budget/compaction/reinjection remains an unresolved course alignment item; no implementation or full course-compliance claim is added. Final human review and remote CI remain pending. This follow-up is not added to ai-use-log at the user's request.


### User-directed logging handoff — 2026-11-23 (historical intermediate state; superseded below)

The user instructed that this assistant's modifications must not be recorded in ai-use-log and requested removal of Codex entries for later user consolidation. Only the newly added Codex-authored AI-058/AI-059 were removed; pre-existing OpenCode entries, including historical prose mentioning Codex, are preserved byte-for-byte. The AI-use log is now identical to the specification baseline. Prior successful association-check results above describe the earlier local state, not the current candidate: unchanged log plus a changed test does not satisfy the current AI-use-log gate. The user will supply/consolidate the actual record before merge. No gate was disabled or made optional, and no new activity entry is added by this review.


### Accurate Codex log restoration — 2026-11-23

The user explicitly requested restoring AI-058/AI-059 with accurate authorship. They now record Codex desktop implementation and subsequent design review/corrections separately; no OpenCode/deepseek-flash attribution is made. Exact model identifier is not independently recorded. Both transcript_refs lists are empty because this chat has no exported repository transcript; the missing export is explicit. AI-057 and its session-20 OpenCode evidence remain unchanged. The earlier removal/failed-association statements above are historical intermediate states, not the restored candidate. Local AI-use association is checked separately after restoration; remote CI remains unverified and no commit/merge is implied.

### Latest local review — remaining five findings corrected (2026-11-23)

Current working-tree status supersedes the earlier read-only finding list; final human review/remote CI/commit/merge remain pending.

| Finding | Current disposition |
|---|---|
| ADR report-summary arrow precedes the formal check despite saying after-check | Corrected: check-time summary/risk → SB-01 → END → IF-19 → entry-prepared terminal summary → unchanged formal delivery |
| IR-17 negative cases might require full-report scanning | Corrected: only supported config-summary fields, endpoint preference and listed diagnostics; model-generated bodies/unlisted channels explicitly excluded |
| Generic Every IR rule could activate deferred invariant tests | Corrected: current applicable IRs only; IR-06/15/16/18 excluded from current obligations |
| CI current baseline omitted three newly deferred requirements | Corrected: seven deferred IDs listed; manifest/new stats/history/SR-02 work separated from current remaining features |
| Trace evidence row and tool manifest retain stale OQ-16/Round 1 status | Corrected: new-stat propagation future-only; frozen Round 1 Proposed cells distinguished from actual approval and merged C-08 scope |

Executed local checks: unchanged schema errors=[] with 13/55/6/27/7/28; all IDs preserved; exact five approved FC-object changes and unchanged verification/zero_tolerance; deferred contracts unchanged; dependency sets correct; trace/D4 each exactly 27 current FCs; 14 current invariant verification rows each seven columns; diagram ordering and bounded security scenarios checked; exact four test count changes; approved paths and unchanged source/CI mechanisms/schema/permission/dependencies/frozen specification; no missing current design Markdown link targets; git diff --check passed. AI-use association passed locally (three changed records, zero unassociated paths). No new full-suite or remote result is implied.

No additional business feature, quality threshold, generic scan/platform, new required DTO or test-count requirement was introduced. Archive organization/diff-size cleanup remains deliberately untouched. Historical baseline functions, tests and records are retained rather than treated as current new scope. Runtime production integration, applicable entry/UI and producer/framework decisions, actual role setup and course context-budget alignment remain explicit preconditions/gaps, not completed facts. Codex follow-up stays within AI-059; no new activity ID or transcript is fabricated.

### Current minimal-scope tightening — 2026-11-23

The user adopted the next read-only review recommendations. This current amendment supersedes earlier constructor-before-scope timing statements in intermediate review notes; those notes remain historical.

- C-03 binds after effective config/basic validation and before the first supported data call. Binding before graph-object construction is not required. Keep independent-call isolation, explicit delegation sharing and restoration on every exit; no new constructor timing/statistics/status coverage.
- M-V01 verifies current scope/reuse/availability only. New-statistics OQ-16 is future-only across current state, trace, blueprint and D4 descriptions.
- Blueprint deferred boundary lists all seven requirements; the D4 self-check now describes 27 current FCs, 14 applicable IRs and 28 deferred FCs as documentation coverage, not test execution.
- OQ-04 preserves existing UI/save/display interaction and verifies terminal summary placement. A separate product decision is necessary only if interaction is deliberately changed; OQ-01 still affects the genuinely undecided purchase-scenario input.
- No product FC, model-quality threshold or runtime prompt was added. Existing scope helpers/mappings are enough; no mandatory RunSpec DTO/service framework or output registry.

Local schema/FC-set/deferred-row/boundary/diff checks passed. Actual path classification for this working tree is semantic_required=false; docs/ci/semantic_eval.yaml remains unapproved and unchanged. Future runtime prompt/model changes must be classified on their real diff. Formal semantic evaluation requires a genuinely approved fixed dataset/rubric/threshold/model/runner and candidate-bound trusted evidence from the default-branch workflow; this scope-maintenance PR neither prepares nor claims that evaluation. A genuine human not-applicable determination is a separate existing path, not a substitute for required evaluation of real behavior changes. No workflow, classifier or evidence rule was relaxed. AI-059 records the same-activity follow-up. Prior regression/Ruff findings, absent Codex transcript export, remote CI and final human review remain as recorded.

### Authorized local submission preparation — 2026-11-23

The user requested tracking the actual session-20 export and making the local implementation commit. Staged scope is the 19 approved revision paths plus the user-selected transcripts/session-20.md; tmp remains excluded. The staged transcript matches the supplied working-tree bytes exactly. Full staged git diff --check returns exit 2 with 1328 whitespace notices, all confined to the original transcript (trailing spaces and final blank line). The other 19 staged files pass the same whitespace check. Raw evidence was not reformatted to manufacture a green check; this transcript-specific finding supersedes earlier diff-check passes before the raw export was staged. Staged schema and AI-use association checks pass. No source, workflow, gate script, schema, permission or frozen specification is staged. Local commit is authorized; push/remote CI/final review/merge are separate and not performed by this preparation.

## RM-14-R1 — FR-10 Integration Preparation (AI-authored review summary; final human verdict pending)

- PR: [#14](https://github.com/Howindy/Teamproject-Tradingagents/pull/14)
- Baseline: `origin/main` `5c6e2caed5e4baceb136b5544ba5e283c0822cdb` (D1 v1.49.0)
- Frozen specification: `docs/plans/financial-metrics-integration.md @ e99ab57b6e460fad59bb4bf4a81cffa5c717c8da` (unchanged after approval)
- Test-spec pre-approval: [comment 7099714477](https://github.com/Howindy/Teamproject-Tradingagents/pull/14#issuecomment-7099714477) by `Howindy` (non-author owner) at `2026-11-23T11:29:36Z`, matching `APPROVED test-spec: docs/plans/financial-metrics-integration.md @ e99ab57b6e460fad59bb4bf4a81cffa5c717c8da`
- Implementation start: `f08bcab058dac13ec8b5898e4521b630aa221fbd` (freeze of `docs/ci/financial-metrics-cases.json`, `docs/ci/financial-metrics-rubric.md`, and `docs/ci/semantic_eval.yaml`, strictly after pre-approval timestamp)
- Scope: `FR-10`, `FR-10-FC01`–`FR-10-FC10`; PR 1 D1 v1.50.0 / ADR 002 / D2 / D3 / D4 alignment, lossless projection, trusted semantic evaluation runner/workflow handoff, and `P01`–`P07` offline tests. Excluded: `src/` feature migration (deferred to PR 2), deferred `FR-07` analyst briefs, and live 6-request `deepseek-flash` execution (`docs/ci/semantic_eval.yaml` remains `unapproved`).

### Actual local verification (isolated Python 3.12.14 venv)

- `scripts/ci_checks.py schema`: 0 errors; `14` requirements / `65` FCs (`7` active / `37` FCs, `7` deferred / `28` FCs).
- `ruff check .`: passed (0 errors).
- `scripts/ci_checks.py permissions`, `api`, `mypy --baseline mypy-baseline.txt`: 0 new errors (`errors=[]`).
- `pytest -q test/offline/test_financial_metrics_evaluation.py`: `6 passed` (`P01`–`P07`).
- `pytest -q`: `1616 passed, 7 failed, 4 skipped, 1 deselected, 100 subtests passed` — all 7 failures are pre-existing Windows-environment assertions (`test_chatgpt_auth.py` POSIX `0o600`, `test_ci_gates.py` `127.1` DNS, `test_cli_updates.py` upgrade commands, `test_suite_isolation.py` Temp under home).

### Final human review

- Final verdict: Pending human review (`APPROVE`, `CHANGES REQUIRED`, or `REJECT` to be supplied by `Howindy` after inspecting PR #14 and CI).

### CI follow-up (not a human review verdict)

PR is now Ready for review. Run [45198004951](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/45198004951)
passed approval, evidence, AI-use, security, schema, type, static, dependency and installation gates,
but failed the two new loader/evaluation tests (and consequently contract-tests/aggregate).
Diagnostics at `e842657` identified the frozen dataset's Windows-CRLF versus Git-LF digest mismatch.
The correction binds trusted text hashes to LF, preserves the original case/rubric bytes in Git, and
tests both checkout line endings plus a real numeric mutation. Local targeted tests: 6 passed;
Ruff: passed. Remote result for the correction remains pending until checked.

The earlier blanket description of all seven Windows failures as pre-existing is not established
by a complete baseline reproduction in this continuation; retain them as local environment findings,
not waived passes. No live semantic score, final human approval, or merge is claimed.

Run [45198769895](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/45198769895)
at `b20d8a8` subsequently passed all applicable PR jobs, including four Python regression jobs,
contract-tests and aggregate. Follow-up fixes within P03–P06 require a pinned, separately installed
baseline and all six import preflights before any completion; missing baseline cannot become a
candidate-only pass. Exact model controls/hashes are enforced, conflicting asserted numbers fail,
and absent source/period/interpretation claims route to review. Captured request/response details
are retained on truncation. Local targeted tests: 6 passed; Ruff: passed. These fixes retain the
frozen oracle, rubric, thresholds and six-request maximum. Final-HEAD CI must be checked again.

## RM-17-R1 — Semantic Suite Routing (AI-authored review summary; final human verdict pending)

- PR: [#17](https://github.com/Howindy/Teamproject-Tradingagents/pull/17)
- Baseline: `origin/main` `00833f4b281692c266bbd52c5955a4f40ec89493`
- Frozen specification: `docs/plans/semantic-suite-routing.md @ 684ddb22460992831fc15348884778d76c505a32` (unchanged by the implementation)
- Test-spec pre-approval: [Howindy's comment](https://github.com/Howindy/Teamproject-Tradingagents/pull/17#issuecomment-7127811834), 2026-11-24T09:43:55Z, approves the frozen specification above. The CI `test-approval` gate verifies the real event, author, phrase and time; this record does not substitute for it.
- Scope: CI maintenance per the plan §3–§5 (registry, reviewer-confirmed suite selection, suite-scoped trusted dispatch and evidence, suite unit contract I1–I6); `FR-10` appears only as registry traceability. Excluded: `src/**`, FR-10 dataset/rubric/configuration/runner/tests, classifier detection rules, aggregate logic, `.opencode/**`, requirements and D2 documents.
- Changed paths: `docs/ci/semantic-suites.yaml` (new), `scripts/ci_checks.py`, `scripts/ci_semantic_eval.py`, `.github/workflows/trusted-evaluation.yml`, `.github/workflows/ci.yml` (`evidence-check` only), `test/offline/test_ci_gates.py`, `docs/ci/README.md`, `CI.md`, `docs/ai-use-log.yaml`, this memo.

### Actual local verification (cloud workspace, Python 3.13.18; not the CI 3.12 environment)

- Tests first: with only the new/adapted tests applied, `pytest -q test/offline/test_ci_gates.py` gave 24 failed / 72 passed (18 new T01–T18 cases plus 6 adapted evidence tests).
- After implementation: `pytest -q test/offline/test_ci_gates.py test/offline/test_financial_metrics_evaluation.py`: 100 passed, 2 failed. Both failures are FR-10 `P04` subprocess tests needing `langchain_core`, which is not installed in this workspace (same 2 failures on the unmodified baseline: 82 passed, 2 failed). Local runs used import stubs for `yfinance`, `curl_cffi`, `dotenv` and `cli.prefs` outside the repository only to load `test/conftest.py`.
- `ruff check .` (Ruff 0.16.9 locally; CI pins 0.17.5): passed.
- `mypy --config-file mypy.ini --python-version 3.12` on the two CI scripts and the gate test file: no diagnostics before or after the change.
- `git diff --check`: clean. Workflows and registry parse as YAML. `docs/ci/semantic_eval.yaml`, `scripts/financial_metrics_eval.py`, `test/offline/test_financial_metrics_evaluation.py` and `src/` are byte-identical to the baseline.
- Not run locally: full `pytest -q` regression (application dependencies unavailable), remote workflows, trusted dispatch, model calls. Remote PR CI is the regression evidence.

### Changed assertions (approved behavior change, not weakening)

- Existing evidence tests now use the suite context `semantic-eval/financial-metrics`; every earlier negative (wrong SHA, untrusted path/repo/event/branch, missing artifact, config version mismatch, unapproved config, failed status, noop without reason) is retained.
- The FR-10 `P06` entry test runs through a registered suite; a `needs_review` runner result is now recorded as `needs_review` with its items instead of `failed` (plan problem P6). Exit code remains non-zero.
- The trusted details-upload condition now also requires the validated suite step.

### Final human review

- Final verdict: Pending human review (`APPROVE`, `CHANGES REQUIRED`, or `REJECT`).

### Local defect repair — 2026-11-24

- Reproduced two defects in `0112cbc`: self-reported `passed` overrode errors/pending review or missing I3 evidence; an old event body without selection prevented reading a later PR-body opt-in.
- Added regression cases before fixing: the initial 14 new cases failed against the original implementation. Final coverage adds 17 cases, including legacy review items, invalid field types, unavailable/mismatched/out-of-directory details and latest-body selection.
- Runner contract errors now fail; `passed` plus errors fails; `passed` plus review items becomes blocking `needs_review`. Explicit `needs_review` with diagnostic errors remains `needs_review`, preserving P06. Dataset/rubric factual verification stays with the suite runner; the framework validates their required result fields, request count and actual details file/hash.
- For a PR, read its current body before deciding whether suite evidence is enforced. T12 retains no semantic enforcement/approval fetch/registry load for absent or `none` selections on non-semantic PRs. Its former no-PR-fetch assertion was corrected: detecting a newly added opt-in requires one current-body GET. This clarifies the implementation of P9; the frozen plan and I1-I6 interfaces remain unchanged. The plan's historical "no GitHub fetch for suites" wording does not describe this necessary body read.
- Verification: existing financial-prep Python 3.12.14 environment, no dependency installation. Command: `python -B -m pytest test/offline/test_ci_gates.py test/offline/test_financial_metrics_evaluation.py -q -p no:cacheprovider --basetemp <review-root>/verified-regression --junitxml=<review-root>/verified-regression.xml --tb=short`: **117 passed, 2 failed**. Both failures are existing redirect tests whose `127.1` hostname does not resolve on this Windows host; both reproduce using the original `0112cbc` scripts and tests in a separate snapshot. No skipped or suppressed failures.
- `python -B -m ruff check scripts/ci_checks.py scripts/ci_semantic_eval.py test/offline/test_ci_gates.py`: passed. `python -B -m mypy --config-file mypy.ini --follow-imports=silent` on those same files: no diagnostics. `git diff --check`: passed. Earlier attempts with the project `.venv` additionally lacked jsonschema and sandbox loopback access; these were not counted as passes.
- Evidence root: `D:/CityU/cs5351/project/baseline-review/semantic-routing-review/`; final JUnit `verified-regression.xml`, baseline reproduction `original-redirects.xml`, original source snapshot `original-0112cbc/`.
- Application source, FR-10 scorer/configuration/oracle, workflows and frozen plan are unchanged by this repair. Full application regression, GitHub CI and live evaluation were not run. Final human verdict remains pending. No commit, push or merge in this repair session.


## RM-18-R1 — FR-03 semantic maintenance (AI-authored; independent final review pending)

- PR: [#18](https://github.com/Howindy/Teamproject-Tradingagents/pull/18).
- Starting tree: `2d10aa4a24eee3cced9cbe4835bb695de0ebaf2f`; original suite specification
  `1440c1ca2ae0806ce3b4b09c20634cfa213e63da` and original implementation start
  `2982819d91784d29448671995dcf5937fc61ad27` remain unchanged.
- Maintenance specification: `docs/plans/semantic-registry-test-amendment.md @
  2d10aa4a24eee3cced9cbe4835bb695de0ebaf2f`, approved by non-author `espino2233`
  [comment 7135347793](https://github.com/Howindy/Teamproject-Tradingagents/pull/18#issuecomment-7135347793)
  at `2026-11-24T15:02:01Z`, before this maintenance implementation.
- Changed files: `scripts/ci_checks.py`, `test/offline/test_ci_gates.py`,
  `docs/ci/README.md`, `docs/ai-use-log.yaml`, this memo.
- R1-R6: T16 preserves exact FR-10 entry/hash/state checks while allowing valid
  additional suites. T18 is unchanged and still inspects every registered runner.
- S1-S7: supplements use their own reviewer, marker, ancestry and first-related-change
  chronology. Only the explicit section-3 allowed-file list grants path coverage;
  rationale and exclusions cannot expand selection. Invalid supplements contribute
  nothing. Primary checks stay mandatory; duplicate machine fields are rejected.
- C1-C10: the exact three frozen preparation paths can be removed from the primary
  start-path set only under section-6 conditions. Git blob identity is used;
  configuration approval/activation prevents the exception. Mixed-commit code,
  shared routing, workflow and permission paths remain included.
- No workflow, dependency, permission, runtime prompt, source application, FR-10
  material or frozen FR-03 material/specification change is included.

### Local evidence and limits

Evidence root: `/private/tmp/cs5351-pr18-maintenance-13jnh35d`. Python 3.12.14 and pytest 9.2.0 from the existing
suite environment; no installation. Imported application source was checked to
resolve inside the isolated snapshot. HOME/temp/cache/JUnit outputs were confined
to the new temporary evidence tree.

- Reproduced the original T16 failure before implementation (`before.out`).
- Final gate/FR-03/FR-10 combined tests: **220 passed**, including 45 new maintenance cases (`combined-final.xml`).
- Default offline regression: **1759 passed, 3 failed, 1 skipped, 1 deselected**;
  100 subtests passed (`regression.xml`). Remaining failures are the three simulated
  Windows cache-lock tests using absent macOS `errno.EDEADLOCK`.
- Repeated unchanged `2d10aa4` baseline cache tests: **5 passed, 3 failed**, with
  the same cases/errors (`baseline-platform.xml`). They remain failures, not waived
  passes; the optional skip is missing `langchain_aws`.
- Ruff, baseline-relative mypy, direct changed-code/test mypy, requirements schema
  and dependency check passed. No baseline diagnostics were changed.
- Actual fetched PR fields and original/supplemental comments were replayed in an
  isolated Git candidate: approval and contract-test selection reported no errors
  (`actual-history-result.json`). That candidate is verification-only, not the
  final project commit or a GitHub CI run.
- The first sandbox gate run had six loopback-bind permission errors; existing
  redirect tests were rerun with local loopback access. No skip/assertion weakening.
- Public contract-job approval reads use no empty Bearer header; API failures or
  rate limits block selection. No credentials are discovered and no workflow is changed.
- Raw chat export is not in the repository; local command/JUnit evidence does not
  substitute for it. No project commit/push, PR write, live semantic evaluation,
  configuration activation or merge was performed in this implementation task.

Independent human implementation verdict: pending. AI delivery recommendation
while final remote CI and independent review remain outstanding: **CHANGES REQUIRED**.


## RM-18-R2 — Lean approval-job dependency repair (AI-authored; human final review pending)

- Starting commit: `e52ac47abebbc89489f7e5ddeeb88cd4559979c0` on the freshly cloned
  `prep/fr03-semantic-suite` worktree under `~/Projects/CS5351`. Remote refs were
  fetched and the branch was synchronized before implementation.
- Existing maintenance basis: `docs/plans/semantic-registry-test-amendment.md @
  2d10aa4a24eee3cced9cbe4835bb695de0ebaf2f`, approved by `espino2233`
  [comment 7135347793](https://github.com/Howindy/Teamproject-Tradingagents/pull/18#issuecomment-7135347793).
- Actual remote defect: [test-approval job](https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/45423751532/job/138550088770)
  raises `ModuleNotFoundError: No module named 'yaml'`. That job installs no
  third-party packages; earlier rich-environment tests missed this runtime boundary.
- Repair: use stdlib SHA-256 attestation of the exact reviewed unapproved config
  on the approval path, preserving the existing three-path bound and Git blob
  equality checks. Unrecognized or activated config text is not exempt. The
  reference's unapproved/null/empty approval fields are independently asserted.
- Added tests run the full approval function under `python -I -S` with YAML
  unavailable, covering valid preparation and rejected activation. The synthetic
  Git fixture uses actual frozen input bytes rather than values derived from the gate.
- Changed files: `scripts/ci_checks.py`, `test/offline/test_ci_gates.py`,
  `docs/ci/README.md`, `docs/ai-use-log.yaml`, this memo. Workflows, dependencies,
  permissions, application source and frozen specifications/materials are unchanged.

### Actual validation and limitations

Evidence: `/private/tmp/cs5351-pr18-stdlib-fix-e7kuh4u0`. The old checker reproduced missing YAML in both isolated
cases (`before-stdlib.out`). Patched standalone public-gate tests: **161 passed**;
maintenance-only subset: **48 passed**. Python 3.14.7 / pytest 9.1.1 was used with
`--confcutdir=test/offline` and external plugin autoload disabled. This isolates
CI-unit tests from missing application-level conftest dependencies and unrelated
locally installed plugins; it is not a default application-regression pass.

On the existing Python 3.12.14 interpreter, `-I -S` confirmed YAML and pytest were
unavailable, then the approval CLI replayed current real PR fields/events against
the existing `e52ac47` Git history and returned `errors: []` (`approval-stdlib.out`).
This does not establish final-candidate remote CI. Python 3.12 syntax, requirements
schema and the existing application environment's `pip check` passed.

Full default regression cannot start in the existing application interpreter
because pytest is missing. Ruff and mypy are unavailable. Their attempted command
outputs are retained; no dependency installation, skipped assertion or fake pass
was used to conceal these gaps. The old iCloud-dependent environment and the
interrupted disappearing-file regression are not treated as current evidence.

No iCloud source was used for the repair. No project commit/push, PR write, model
call, activation or merge is included. Original approvals and chronology remain.
Independent final verdict: pending. Until final-candidate CI and independent review
complete, AI delivery recommendation: **CHANGES REQUIRED**.
