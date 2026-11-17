# D4 Review Memo

- Document status: Reusable review-record template. No PR review, approval, test execution, or acceptance result has been recorded here yet.
- Registered records: None yet.
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

- Round plan: [`docs/plans/round-01.md`](plans/round-01.md) (currently marked proposed in the file; verify approval status before relying on it).
- Verification rules: [`docs/code-governance/verification-constraints.md`](code-governance/verification-constraints.md).
- Requirements: [`docs/req/requirements.yaml`](req/requirements.yaml) v1.48.0.
- D2 invariants: [`docs/architecture/invariants.md`](architecture/invariants.md).
- Trace matrix: [`docs/architecture/trace-matrix.md`](architecture/trace-matrix.md).
- Runtime policies: [`docs/architecture/runtime-policy-catalog.md`](architecture/runtime-policy-catalog.md).
- Relevant ADR: [`ADR 001`](architecture/adr/001-graph-internal-final-check.md).

For the currently available Round 1 plan, the candidate review scope is the FR-04 core FCs `FR-04-FC01` through `FR-04-FC04` and the core portion of `IR-14`; `FR-04-FC05` and the entry/graph/report portion of `IR-14` are excluded by that plan. This is plan context only. Record the IDs that the actual PR implements and test evidence demonstrates, not a whole-requirement claim inferred from the plan.

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
