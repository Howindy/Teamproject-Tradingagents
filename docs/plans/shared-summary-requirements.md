# Shared-summary requirements and architecture alignment — SS-REQ-1

## 1. Status and exact approval boundary

**Proposed specification; non-author approval pending.** This is the actual next-checkpoint test specification for PR #15, not an implementation authorization obtained by writing it. The current publication checkpoint changes planning/records only. After genuine approval of this immutable specification, the next checkpoint may perform only the bounded requirement/architecture maintenance and inventory assertion update below, verify them, then stop for human inspection.

Overall roadmap: [shared-summary-integration.md](shared-summary-integration.md). It retains core migration, graph integration and later semantic evaluation designs, but is **not** this checkpoint's contract-test source. This specification neither recursively includes its test paths nor approves those later implementation slices. No core migration, graph/consumer/config changes, runtime prompts, evaluation runner/configuration, API requests, dependency installation, merge or final acceptance.

Baseline verified after fetch: `origin/main @ 5c6e2caed5e4baceb136b5544ba5e283c0822cdb`, D1 v1.49.0. PR #14 remains open/unmerged at `88d47e712f7eac6e6babc8d2e1b0dc87d17c4b17`; FR-10 is not on this main. PR #13/FR-03 is not assumed merged. Earlier PR/roadmap approval is not this specification's non-author test approval. The user's review retained the summary design and requested this narrowed specification; it did not authorize starting maintenance before Yifan's approval.

## 2. D1 amendment and preserved FC IDs

Activate current **FR-07**, with all five IDs retained, replacing the deferred same-analyst-call/character policy with the independent shared-summary policy. Personal summary FR-08 maps to team FR-07; historical financial FR-07 is a different meaning, and FR-10 remains the other session's feature. Preserve historical version/approval records and explain the new amendment rather than backdating approval.

D1 must describe these proposed functional expectations. The verification column below is **future product acceptance intent only**, not runtime tests selected for this maintenance checkpoint, and not a claim of implemented/passed behavior.

| Retained ID | Updated input and expected behavior | Future verification intent |
|---|---|---|
| FR-07-FC01 | Four settled complete report texts and controlled model response: at analyst/memory join, one separate LLM request produces structured JSON. Program validates exact root/item fields, types, nonempty text/allowed source labels and schema version, then deterministically renders categories. No analyst same-call summary requirement, tools, repair or summary-specific retry. Empty/absent report inputs use deterministic fallback without a request or forced analyst generation. Structure is not semantic truth verification. | Independent call counter, complete-source markers, valid/invalid JSON and deterministic rendering cases in the later core checkpoint. |
| FR-07-FC02 | Distinct report/plan/history markers: Bull, Bear and Aggressive/Conservative/Neutral share one selected material block instead of four reports; no duplicate brief/full-report bypass. Other roles keep existing inputs; instructions, plans and debate history unchanged. | Real prompt capture for the five consumers in the later graph checkpoint. |
| FR-07-FC03 | Explicit policy/counter plus boundary/failure inputs: delivery budget uses `len(text.split())` whitespace-token proxy, includes rendered labels/separators/protected block, and accepts equality. Count actual combined text; M is protected reservation, C narrative ceiling, T=M+C, H>=T. No approved default, real-tokenizer/API-token guarantee or whole-request cap. Invalid/over-budget/model-failed narrative falls back to deterministic extraction; protected overflow or invalid configuration/counter at integration boundary restores full reports/placeholders plus complete program material. Never clip protected evidence, repair/retry, terminate ordinary analysis or fabricate REVIEW because a brief failed. Preserve unrelated primary data/analysis errors. | Independent boundary counts, safe failure inputs and fallback assertions in later core/graph checkpoints. |
| FR-07-FC04 | Caller-supplied protected evidence and program FR-03 mapping: complete fixed research-start availability block, including applicability, observations, necessity gaps/reasons and supplementary limitations, reaches all five consumers once, including fallback. FR-03 alone calculates completeness; no report-keyword inference, model override, truncation or duplicate injection. Null uses FR-03's fixed unavailable text, never invented completeness. Financial table/citations are optional opaque caller input, not a requirement or scorer dependency. | Program-region/structured-state equality, first-Bull same-call visibility and single-injection negatives in later integration. |
| FR-07-FC05 | Repeated debate, independent runs, disabled analyst and save cases: prepare one run-owned immutable selected result and reuse it, including failures, without additional summary calls per role/round or later observation. Separate runs do not share it; original/saved reports unchanged. No new data fetch, forced analyst call, manifest/history/recovery prerequisite. Failure of a summary is nonblocking; no fabricated source/report/usage/success. | Run isolation, repeated-read/call counters, originals/save comparisons and failure delivery in later integration. |

Update the full FR-07 statement/problem/title/tradeoff/conflicts/assumptions/notes consistently, not only the FC cells. Keep it functional, Must when active. Direct functional dependency is FR-03, not deferred FR-02 or optional FR-10. A manifest write does not condition delivery. Actual FR-03 integration is still needed for eventual full acceptance; this phase does not implement it. No activation of FR-02, FR-05, SR-02, FR-06, PR-01 or CR-01, or new requirement/FC ID.

Keep estimated proxy counts and actual provider input/output/cached/reasoning usage distinct; unknown actual usage stays unknown/null. The extra summary attempt is included when later usage is measured; no savings, equivalence, semantic fidelity or cost target is approved by this maintenance. No alteration to the independent financial evaluation standard/configuration.

## 3. Exact maintenance file allowlist after approval

The following are the **only** proposed next-checkpoint editable files. An entry permits only affected summary scope/contract/count/current-status maintenance, not unrelated rewrites or runtime implementation.

| File | Bounded change |
|---|---|
| `docs/req/requirements.yaml` | §2 FR-07 amendment, scope/MoSCoW/relations/trace metadata and current validation/version metadata; preserve other requirement semantics, all IDs, historical approvals and unmeasured states. |
| `architecture-blueprint.md` | Summary responsibility/module ownership and one replaceable assembly seam; narrow no-new-summary-call/compression exception; counts and accurate planned status. Reserve no finance-owned component/interface IDs. |
| `docs/architecture/adr/001-graph-internal-final-check.md` | Explicit advisory-summary exception and first-research seam coordination; deterministic governance checks still make no model/data calls. |
| `docs/architecture/adr/003-shared-summary-integration.md` | New focused decision for independent generation, validation, proxy budget/protected/full-report fallback and single-injection ownership; slot checked unused on current main, recheck before creation. No safety-critical application approval implied. |
| `docs/architecture/invariants.md` | Affected no-compression/deferred wording and preservation obligations; do not redefine formal authority, stage timing, risk, state/memory or credential invariants. |
| `docs/architecture/trace-matrix.md` | Five active FR-07 FC rows with planned verification/gaps explicitly marked; active/deferred totals. No invented implemented test links. |
| `docs/architecture/runtime-policy-catalog.md` | Summary-local nonblocking failure/fallback and narrow new-call exception; unrelated error propagation unchanged. |
| `docs/architecture/memory-design.md` | Planned plain serializable delivered material vs ephemeral adapter/locks; original reports and memory/formal consumers unchanged. |
| `docs/architecture/evaluation-table.md` | Summary design tradeoffs; historical pilot limits, semantic evaluation separately pending. |
| `docs/code-governance/structural-constraints.md` | One primary owner per summary responsibility, single replaceable seam; no competing availability/risk/final authority. |
| `docs/code-governance/verification-constraints.md` | Five FR-07 FC maintenance/coverage intents, correct counts/status; future product tests remain planned/unrun, not new obligations to execute this phase. |
| `AGENTS.md` | Affected active/deferred inventory and selected phase boundaries only. |
| `Prompt.md` | Only if needed to reconcile affected summary/selected-spec language; retain all approval-before-code and human-stop controls. |
| `.agent/rules.md` | FR-07 no longer blanket-deferred, bounded authority/timing consistency; no permission expansion. |
| `CI.md` | Inventory/remaining-work statements and this exact specification's operation; no gate change/exemption. |
| `docs/ci/README.md` | Affected inventory/spec selection/current limitations; no financial semantic-profile overwrite. |
| `test/offline/test_ci_gates.py` | **Only** four active/deferred inventory values in `test_schema_current_document_and_invalid_inputs` per §4. Preserve all negative tests and all other logic/assertions. |
| `docs/ai-use-log.yaml` | Actual maintenance/checks/human interventions, no inferred approval or raw transcript. |
| `docs/review-memo.md` | Append PR #15 phase-specific factual review/evidence, pending genuine human final verdict; do not rewrite historical review records. |

Current specification/roadmap files are frozen approval inputs, not a place to rewrite expectations after implementation. Record subsequent outcomes in the two record files above. If a material correction is needed, approve a new immutable affected specification first.

No changes to source, other tests, schemas, dependency manifests, workflows, checker/runner code, semantic data/rubrics/configs, baseline evidence, finance files/branch or frozen earlier plans. `.opencode/rules.md` remains human-only; no permission-file edit or self-expanded control. If effective human-owned rules/role configuration block this exact phase, present the needed human amendment and stop dependent work, rather than bypassing it. OQ-07 remains unresolved where not actually verified.

## 4. Actual baseline and exact independent count oracle

Counts are fixed for the verified main in §1; moving FR-07's five FCs from deferred to active adds no ID:

| Inventory key | Before | After this phase |
|---|---:|---:|
| requirements | 13 | 13 |
| fit_criteria | 55 | 55 |
| active_requirements | 6 | 7 |
| active_fit_criteria | 27 | 32 |
| deferred_requirements | 7 | 6 |
| deferred_fit_criteria | 28 | 23 |

Active after: FR-01, FR-03, FR-04, SB-01, INV-01, SR-01, FR-07. Deferred after: FR-02, FR-05, SR-02, FR-06, PR-01, CR-01. Preserve all five FR-07 FC IDs and every non-FR-07 FC object. Keep current registry draft/approval metadata honest; non-author scoped maintenance pre-approval is not product acceptance or a retroactive replacement for PR #12 history. Use an actual new document version; do not overwrite an independently merged financial version.

The exact existing test is `test_schema_current_document_and_invalid_inputs` in `test/offline/test_ci_gates.py`. Change only active_requirements 6->7, active_fit_criteria 27->32, deferred_requirements 7->6, deferred_fit_criteria 28->23. The 13/55 totals stay unchanged. The oracle is this explicit inventory arithmetic and fixed ID sets, not values copied from the checker output. Do not add permanent counts to the checker or calculate this test's expected counts using the implementation under test.

Before maintenance fetch/check actual main and compare D1. If FR-10 or another inventory-changing amendment merges meanwhile, **stop the affected count/spec update and request approval of a revised immutable count oracle**. Do not apply PR #14's branch numbers to today's main or silently switch this specification's expected values. Preserve independently merged FR-10 and its financial config; coordinate overlapping documentation based on the real diff. Unchanged independent approved work need not be reapproved.

## 5. This checkpoint's verification — one existing test module only

The sole selected contract-test file is **`test/offline/test_ci_gates.py`**. The existing parser selects whole file paths, not individual pytest node selectors; the full existing module is intentionally runnable, and only its named inventory assertion may be edited. No later product/evaluation test path is written into this specification. A link to the roadmap is context, not recursive test selection.

Current checker detail: that existing gate-test file is itself a governance path. `contract_test_plan` on this phase's proposed documentation-plus-gate-test diff therefore returns `mode=governance` and the fixed existing gate module, rather than the application-code specification branch. Independently run `plan_test_paths` on this exact document to verify its own selection is the same singleton. Do not report this governance dry-run as proof that an approval event was validated, or change classification to force a desired result. `extract_ids` reports contextual requirement identifiers too; they are not all approved implementation scope. Actual changed-scope collection uses the relevant added code/test lines; the proposed four integer edits introduce no new FC/IR ID. The explicit maintenance scope remains FR-07 and §3 only.

| Check | Controlled inputs / independent expected result |
|---|---|
| SS-REQ-V01 schema/inventory | Updated D1 and unchanged schema -> valid schema, unique IDs, exact after-count dictionary/ID sets in §4; baseline schema remains valid before maintenance. |
| SS-REQ-V02 preserved negatives | Existing malformed YAML, wrong document shape, invalid schema and duplicate-ID cases in the selected test -> errors remain nonempty. No suppression/skip, count-derived self-oracle or relaxed schema. |
| SS-REQ-V03 minimal test diff | Compare named test with baseline -> exactly four literal inventory changes, totals/negative assertions and every other test byte/logic retained except unavoidable line ending normalization, which must be reported, not mass-reformatted. |
| SS-REQ-V04 D1 scope preservation | Read baseline D1 via Git and candidate D1 -> same requirement/FC ID sets, exactly five FR-07 FCs; other requirement statements/FCs/dependencies/status/priority unchanged. Only affected references and current inventory/document metadata may change. No accidental finance insertion or other deferral activation. |
| SS-REQ-V05 D2/D3/D4 consistency | Read current portions of allowlisted docs -> FR-07 is active but implementation/acceptance pending; same-call/no-summary-call/character policy no longer current FR-07 acceptance. Record explicit narrow exception, not generic deletion of deterministic-check call bans. Historical/future-only text stays clearly labeled. Five FR-07 trace/verification rows remain planned; aggregate coverage/acceptance is not fabricated. |
| SS-REQ-V06 authority/timing | Documentation review -> C-07 sole five-field availability producer; first Bull sees same-invocation material; research stage snapshot frozen, terminal/check-time separate; single program injection; optional finance; no second formal/risk authority; no requirement for extra data calls/FR-02 manifest. These are design checks, not runtime integration passes. |
| SS-REQ-V07 parser/scope | Use unchanged `plan_test_paths`, `contract_test_plan`, `specification_mentions_path`, `classify_paths`, `extract_ids` from existing checker -> extracted paths exactly the sole module above; it exists; proposed changed test is mentioned; no missing-test/code-scope errors. A synthetic extra unlisted application path must be rejected. This local dry-run supplies no approval evidence and does not prove the real approval gate passed. |
| SS-REQ-V08 regression/governance | Full selected existing module and all prior applicable offline suites; schema, Ruff, mypy baseline, dependency/API/permission checks and actual diff classification/log association -> report actual success/failure/skips/environment blocks without waiver. Current docs-only plan publication is separate from the later test-edit classification. |

New product behavior is not tested or claimed here. The selected module already supplies negative governance coverage. Independent one-off comparisons may use installed Python/stdlib/YAML facilities in memory; do not create new checker/test frameworks or persistent executable files just for this maintenance. Pure verification does not edit the tested implementation.

## 6. Execution, outputs and human stop

Run from the verified summary-prep worktree on `prep/shared-summary-integration`. Keep all other worktrees and finance evidence intact. Use installed tooling only; never load credential files or trigger model/vendor calls. The currently discovered system Python supports checker/YAML/schema but lacks pytest; confirm a suitable existing isolated interpreter before executing pytest, no dependency installation implied. Missing tools are not passes.

After actual approval and effective setup, planned commands include:

```text
python -B -m pytest -q test/offline/test_ci_gates.py
python -B -m pytest -q
python -B scripts/ci_checks.py schema --requirements docs/req/requirements.yaml --schema docs/req/req-schema.json
python -B -m ruff check .
python -B scripts/ci_checks.py mypy --output <approved-output>/mypy-current.txt --baseline mypy-baseline.txt
python -B -m pip check
python -B scripts/ci_checks.py permissions
python -B scripts/ci_checks.py api
git diff --check
```

Parser dry-runs/format/schema checks are permitted in the current planning checkpoint without modifying tests. Full pytest excludes live/integration by existing configuration; live execution is not authorized. Keep later JUnit/stdout/mypy/temp outputs under `C:\Users\24968\AppData\Local\Temp\opencode\shared-summary-prep\` or isolated pytest-owned temp paths, not finance outputs or baseline. Preserve all earlier failures; no deletion/xfail/gate weakening. Remote CI retains its existing framework and actual approval/start chronology; passing local parser checks alone is not CI or human acceptance.

Maintenance order after approval: snapshot baseline/confirm permissions -> align D1/D2 and affected governance -> exactly four count-assertion edits -> run bounded checks and full regression -> record actual evidence/review -> **stop for human inspection**. If evidence contradicts the approved specification, return the affected issue for review; do not proceed to core/graph/semantic work. Safety-sensitive architecture changes require real applicable ADR review; no runtime safety change is authorized here.

## 7. PR fields and genuine non-author approval

Use these real PR fields, with full immutable SHA substituted after this specification is committed:

```text
Plan: docs/plans/shared-summary-integration.md
Approved test specification: docs/plans/shared-summary-requirements.md @ <FULL_SPEC_COMMIT_SHA>
Approved scope: FR-07 FR-07-FC01 FR-07-FC02 FR-07-FC03 FR-07-FC04 FR-07-FC05; SS-REQ-1 requirements/architecture/count maintenance and selected existing gate module only
```

The field label is the existing gate's metadata format, **not a claim that approval has occurred**. Approval evidence and Implementation start are pending/not established until the actual events. The first test-edit commit is the true relevant implementation start; never replace it with a planning commit or adjust timestamps. Preserve the frozen specification before that event.

Yifan (a genuine non-author teammate) should review this exact specification and post:

```text
APPROVED test-spec: docs/plans/shared-summary-requirements.md @ <FULL_SPEC_COMMIT_SHA>
```

The old roadmap marker is no longer requested for the next phase. Record the real approval comment URL/time only after it exists. Final per-PR human review is distinct; no APPROVE verdict is prefilled by the agent. Approval of SS-REQ-1 covers neither core/graph tests from the roadmap nor semantic configuration/runner execution. Stop after publishing this specification revision; await approval before maintenance.
