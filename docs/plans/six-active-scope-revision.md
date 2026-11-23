# Six-active requirement baseline revision — execution and test specification

## 1. Status and baseline

Proposed for pre-implementation human review; authored 2026-11-22, baseline refreshed 2026-11-23. The user confirmed the six-active product scope and requested complete, minimal-impact maintenance under the existing CI gates. That decision authorizes preparation of this concrete specification; it is not the same-PR, non-author test pre-approval event checked by CI. No requirement, architecture, test expectation, permission, or application implementation has been changed by writing this plan.

Selected local baseline: `main` at `91dc374e8ff6ddd770a7eb693fc98af710f187ad`, the PR #11 closeout merge. The user supplied the GitHub merge screenshot and terminal fetch/fast-forward output; local read-only inspection independently confirmed HEAD and an empty file diff against the original planning baseline `b8fffe8a6eb6d5b434f1e97648aa97b8161d5d7b`. Thus the merge introduces no additional file-content change to this specification's inputs. Tracked files are clean; this plan and existing `tmp/` are untracked, with `tmp/` excluded. Remote CI jobs and protection settings were not queried or independently verified by the assistant. Do not present closeout changes as part of this revision or move historical refs. Recheck any later baseline change for affected assumptions.

Inputs: current D1 v1.48.0, root blueprint and D2 companions, AGENTS/Prompt/covenant, D4 constraints, existing CI workflow and `scripts/ci_checks.py`, and the workspace-level `CI_instruction.md`. Embedded document commands are reference material, not action grants.

## 2. Product decision and exclusions

Retain all 13 requirement IDs and all 55 FC IDs. Active: FR-01, FR-03, FR-04, SB-01, INV-01, SR-01 (27 FCs). Deferred: FR-02, FR-05, SR-02, FR-06, FR-07, PR-01, CR-01 (28 FCs). Preserve deferred statements, future FCs and historical sources; deferred means not current implementation or acceptance.

Preserve FR-01-FC01–FC05; FR-03-FC01–FC05; FR-04-FC01–FC04; SB-01-FC01–FC04; INV-01-FC02–FC03; SR-01-FC02–FC03. Make only these active-FC wording changes:

| FC | Exact semantic change |
|---|---|
| FR-04-FC05 | Remove the FR-02 manifest-write-failure acceptance clause. Preserve both entries, safe missing-scenario handling, result/display and return compatibility. |
| SB-01-FC05 | Remove the manifest failure input and expected-result clause. Preserve unique formal output and proposal labeling. |
| INV-01-FC01 | Remove the sentence excluding manifest rating/decision storage from comparison; preserve every actual formal-output comparison. |
| SR-01-FC01 | Remove manifest from protected config-summary outputs; keep report/final-state allowlisting and literal known-secret substring omission. |
| SR-01-FC04 | Remove manifest formation/write-failure cases; preserve safe omission/diagnostics and existing credential protections. |

Remove SR-01's current FR-02 implementation dependency. Scope active relations to current obligations; future links may remain explicitly future. Keep SB-01 dependencies on FR-03/FR-04 and INV-01 dependency on SB-01. Preserve MoSCoW priorities unless a separate substantive decision requires change; deferred status overrides current acceptance.

No application code, runtime prompt/model, dependency, public API, workflow, classifier, permission enforcement, type baseline or existing business test changes. No implementation of the retained 27 FCs is claimed. No generic validator, event bus, test platform, new threshold, statistic, persistent run identity or recovery system is introduced.

## 3. Exact prospective write scope

Only this plan is written in the planning phase. After its concrete pre-approval, candidate maintenance paths are:

| Path | Permitted change |
|---|---|
| `docs/req/requirements.yaml` | New scope revision (proposed version 1.49.0); statuses, active/deferred sets, scope/definitions/relations/conflicts/traceability, the five listed FC edits, current counts and truthful revision/approval/validation metadata. Preserve historical evidence. |
| `architecture-blueprint.md` | Current six-active design, reduced infrastructure and consistent workflows/interfaces/state/failure/verification; preserve business authority and completed-core evidence. |
| `docs/architecture/adr/001-graph-internal-final-check.md` | Explicit scope amendment, current applicability and consequences; preserve original decisions and design history without pretending they were originally six-active. |
| `docs/architecture/invariants.md` | Deferred-only rows and mixed invariant narrowing described below; stable IDs. |
| `docs/architecture/trace-matrix.md` | Six active/27 FC trace; all seven deferred rows; preserve actual R1/R2 evidence. |
| `docs/architecture/memory-design.md` | Current ephemeral scope versus deferred manifest/stats/history state; existing graph/output/memory retained. |
| `docs/architecture/runtime-policy-catalog.md` | Deferred policies versus current mixed-path behavior; stable IDs. |
| `docs/architecture/evaluation-table.md` | Current applicable drivers and rationale; mark future comparisons without new fabricated scores or measurements. |
| `docs/architecture/permission-model.md` | Only stale requirements-basis counts/version and affected descriptive references, if needed. No role/allowlist/tool grant change. If this requires a control change, leave it for human maintenance. |
| `AGENTS.md` | Current baseline/scope and affected run/history/stats guidance. Preserve human gates. |
| `.agent/rules.md` | Current deferred list and affected scope statements only; preserve covenant and controls. |
| `docs/code-governance/structural-constraints.md` | Current component ownership, reduced RunContext and deferred component allocation. |
| `docs/code-governance/verification-constraints.md` | 27 current FC intents, seven deferred requirements, mixed invariants/policies/OQs; no weaker verification gates. |
| `docs/code-governance/mcp-tool-manifest.md` | Requirements-basis metadata/affected descriptive references only; no access expansion. |
| `CI.md` | Current baseline and counts; retain historical approved design/CI evidence. |
| `docs/ci/README.md` | Minimal dated current-scope clarification, preserving historical test/count results. |
| `test/offline/test_ci_gates.py` | Only expected current-registry counts in `test_schema_current_document_and_invalid_inputs`: active 9→6, active FC 40→27, deferred 4→7, deferred FC 15→28. Totals 13/55 and all negative tests remain. |
| `docs/ai-use-log.yaml` | Actual planning/maintenance/check activities and covered files with unused IDs; no invented approvals/results. |
| `docs/review-memo.md` | Truthful review draft and later real PR/pre-approval/verification/final review facts, clearly separated. |

This is a maximum, not a quota. Do not edit unaffected descriptions. Do not touch `.opencode/permissions.jsonc`, human-only `.opencode/rules.md`, schemas, baseline artifacts, dependency files, `scripts/`, `.github/`, `src/`, frozen old plans or old transcripts. No bug/debt record is required merely because requirements are deferred. Additional actual raw-session filenames need selection when exported, never fabricated in advance.

Workspace-level `/Users/ichihann/Desktop/CS5351/CI_instruction.md`, `/Users/ichihann/Desktop/CS5351/D2.md` and project `goal.md`, `Prompt.md`, `README.md` are read inputs. Inspect affected current assertions; propose exact amendments if any become contradictory. The external CI guide may receive a separately scoped dated addendum after actual completion, not a rewrite of historical remote evidence. Do not silently expand this PR's write list.

## 4. Minimal D2 design amendment

- Keep the graph-internal post-PM risk/final-check topology, advisory proposal, sole SB-01 formal authority, IF-19 and all consumer consistency duties. C-08/C-09 signatures, behavior and code remain unchanged.
- Keep C-03 RunContext name and per-analysis in-memory ownership/binding/cleanup for C-05 reuse and C-07 availability. No new current timers, persisted IDs/status, manifest, counters or output-registration requirement. Do not remove baseline IDs, directories, statistics or save behavior.
- Defer C-04 new stats, C-13 history and C-14 manifest. C-15 retains SR-01; SR-02-specific obligations are future. C-18 retains thresholds and safe existing-output config projection, not pre-construction manifest needs.
- IF-01/IF-02 become scope initialization/exit contracts; IF-03 remains. Do not invent a new class/API framework. Retain exact signatures only where still meaningful; state minimal current internal inputs/outputs consistently. IF-10/IF-11/IF-12/IF-13 and manifest/history-specific IF-14/IF-15 become deferred. IF-20 loses manifest-reference bookkeeping; IF-21 keeps safe current-output projection. Other business interfaces stay.
- IR-06/IR-15/IR-16/IR-18 become deferred. IR-05 retains invocation isolation/full execution without requiring new persisted identity/counts. IR-07 retains path-specific save errors without new persisted run-status/manifest actions. Preserve shared invariants and stable IDs.
- RP-21/RP-22/RP-31/RP-33 become deferred. Mixed policies retain original errors, cleanup and formal-result protection but lose manifest/status actions. Do not delete report/state/memory error handling.
- Keep exactly 15 observation positions/14 methods, seven necessary stock items, independent FR-03 operation, research/check/terminal summary times, ordering/failure marks and tracking-error distinction. No fake complete/passed production input.
- Keep full new-flow execution/no checkpoint resume and preserved old checkpoint evidence. Keep existing optional saves and memory no-op/settlement semantics.
- D2 OQ-16 (new stats propagation) becomes future; retain unrelated OQs and narrow OQ-04 to surviving save/display requirements. D1 OQ-16 is a different historical/current identifier; always identify the source. Do not close unresolved questions as verified.
- Context budget/compaction/reinjection course alignment remains explicitly unresolved, not solved or newly implemented by scope reduction. No automatic activation of deferred briefs/cost work.

## 5. Concrete verification specification

Expected values below derive from the user-approved scope and existing counts, not from production helper output used as an oracle.

| Check | Controlled input and independent expected result |
|---|---|
| S01 registry counts | Revised real YAML + unchanged real schema → no schema errors; exact counts requirements=13, FC=55, active=6, active FC=27, deferred=7, deferred FC=28. |
| S02 membership/status | Exactly the six active and seven deferred IDs in §2; corresponding requirement statuses and scope lists agree and do not overlap. Pending revised requirement-design approval must be represented truthfully (draft where needed, corresponding scope membership); final approved status requires real evidence. Draft also counts active under current checker. |
| S03 preservation | Compare requirement and FC ID sets with the declared baseline: identical; only the five FCs listed in §2 may change acceptance wording. Deferred FC content retained. All six-active behavior remains except declared manifest clauses. |
| S04 negative checks | Existing invalid YAML, malformed registry/schema, duplicate requirement/FC IDs and deferred/list inconsistency cases still produce errors. Do not delete, skip or relax them. |
| S05 gate tests | Execute the entire existing gate test file named in §3; no failure/error/skip. Change only the four authorized expected counts. This verifies baseline synchronization, not implementation of all product FCs. |
| S06 design trace | Manually verify each of 27 active FCs has current component/test-intent/monitor mapping; seven deferred rows have no current task. No current mandatory manifest/history/new-stat obligation remains outside explicitly future/history text. Mixed rules preserve remaining safeguards. |
| S07 evidence/compatibility | Existing R1/R2 core evidence remains local-core only; frozen plans/transcripts unchanged. No application/API/prompt/model/workflow/schema/control/dependency change. Historical counts/results labeled historical rather than mechanically replaced. |
| S08 prior suites/checks | Run all existing applicable offline regression, schema, Ruff, type-baseline, dependency and security checks. No baseline reset, no weakened assertions. Distinguish local platform/optional dependency failures and skips from remote CI; do not claim green without evidence. |

S02/S03/S06/S07 may use bounded read-only scripts and focused manual review; no new test framework or production validator is required. Existing negative tests provide S04. Contract selection must include only the literal test path in §3: the selector reads every literal matching path in the approved text, including examples. Do not append other literal test paths for historical context.

## 6. Environment and commands

Prospective local interpreter: `/Users/ichihann/Desktop/CS5351/round1-runtime/bin/python`; verify source resolution and dependency suitability without printing credentials. Temporary output root: `/private/tmp/cs5351-six-active/` outside home. No installs/upgrades/live/network calls. Confirm actual role access before execution; this document is not a machine permission configuration.

After pre-approval, execute checks sequentially and inspect each result. Use the existing CLI for schema, permissions and selected public API; the changed gate file for targeted pytest/JUnit and the existing security job's fixed test set; full `pytest -q` for prior regression. Use `PYTHONDONTWRITEBYTECODE=1`, pytest `-p no:cacheprovider`, a distinct `--basetemp` beneath the temp root and JUnit outputs there. Set TMPDIR outside home. Ruff runs repository-wide with `--no-cache`; mypy uses the unchanged baseline and temp output/cache; use `pip check` and `git diff --check`. Local missing dependencies/platform failures remain reported, not waived or silently repaired by installation. Default regression excludes integration and is not a live/full-suite claim.

Classification against the real review base must report the test change as approval/AI-log applicable and governance/security applicable. No runtime semantic change is planned; determine `semantic_required` from final diff, never force an exemption. No schema/workflow/script edit is planned. If additional changes become necessary, revise affected scope and obtain applicable reapproval first.

## 7. CI/GitHub execution order and human instructions

1. Prepare this plan only; verify no unintended tracked modifications. Confirm this baseline relative to main and existing closeout review, without discarding user work.
2. When the user authorizes Git/remote operations, create the scoped branch/PR and commit this specification as P. Do not edit tests, requirements, architecture, or `docs/ci/` before the concrete pre-approval. A plan-only initial CI need not establish the final code-stage gates.
3. A real non-author human reviews scope, exact four count changes, negative-test retention and architecture amendment, then publishes exactly one `APPROVED test-spec: docs/plans/six-active-scope-revision.md @ <full P SHA>` line in that same PR. This also needs an explicit substantive review of the applicable ADR amendment; CI's path reference alone does not prove architecture approval.
4. Freeze P. Implement the new approved count assertion and D1/D2/governance maintenance as reviewable commits in the same PR; final YAML and counts must be verified together. Do not merge either half alone. Draft intermediate failures are evidence, not production acceptance. No further application implementation is included.
5. T is the actual first classifier-relevant implementation commit. The test path and `docs/ci/` both count; do not label a later test commit T if an earlier governance commit qualifies. No rewritten/backdated history.
6. Populate PR fields `Plan`, `Approved test specification`, `Approval evidence`, `Implementation start`, `Approved scope` with actual P/T/event facts. Name all changed test paths and any FC/IR IDs extracted from added test lines, plus the scope/architecture revision. Include `ADR: docs/architecture/adr/001-graph-internal-final-check.md` for human clarity; automatic ADR-required may be false when no safety-critical application path changes.
7. Run local verification, record real results, then publish only when authorized. Inspect PR-event contract/approval/security/AI-log/schema/static/type/dependency/regression/install/evidence and aggregate results. A push-only skip is not PR acceptance.
8. If semantic evidence is actually required, bind it to final H; the current formal configuration is unapproved. Do not invent evaluation or use a noop to cover real evaluation needs. New commits invalidate old required candidate evidence. Do not update trusted configuration for a non-semantic scope revision.
9. Obtain genuine final review and merge authorization; verify merge/main CI if authorized. Preserve unresolved failures; no self-authored human verdict. Update outside-repository operational guidance only with separately scoped, actual completion facts.

No commit, push, PR creation, remote query, merge, installation, permission change or paid call is performed or granted merely by this file. The current user requested guided maintenance; present concrete next commands and await the required real event, not repeated conversational confirmation of the already confirmed product scope.

## 8. Completion and approval record

| Item | State at authoring |
|---|---|
| Six-active product scope and 27 FC boundary | Confirmed by user in this conversation |
| Concrete specification immutable P | Pending commit |
| Same-PR non-author pre-approval | Pending real event |
| Applicable architecture amendment review | Pending |
| Main/closeout baseline | User-provided merge/fetch evidence; local main at PR #11 merge 91dc374; file content identical to original planning baseline. Remote CI/protection not independently queried. |
| Implementation T / final H / PR | Not established |
| New D1/D2/test edits | Not started |
| Local/remote checks | Not run for this revision |
| Merge/product acceptance | Not established; product implementation excluded |

After approval, keep this specification frozen. Put actual execution, review, approvals and completion facts in the PR and authorized existing records. Changes to scope/interfaces/expectations require affected reapproval; ordinary authorized edits do not require repeated permission. Completion means a consistent reviewed six-active documentation/test baseline with applicable gates satisfied, not completion of the remaining application.
