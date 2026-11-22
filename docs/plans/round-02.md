# Round 02 — Deterministic Final Recommendation Core

## 1. Status and source baseline

Status: proposed execution and test specification for human review. The user selected the scope and confirmed the interface, safe proposal projection, and asset-type rules below, then authorized writing this plan. Those design decisions and this authoring task are not pre-approval of an immutable test-specification commit, approval to implement the application, or evidence that tests passed. No application/test file or other record is created or changed by this planning task.

The selected source baseline is merged main commit `eb861e060993ee20bb561246ca5f745d6300dff0` (PR #7). The authoring checkout remains on `round-01-portfolio-risk` at `6325db571a14a059ea39ac0d94afa5e8223269bb`; its tracked file content was compared with that merged main and is identical. This task does not switch branches, update refs, move historical tags, or establish a Round 2 branch. Recheck the actual main and effective environment before authorized implementation; do not silently incorporate a materially different baseline.

Round 1 implemented the independent C-08 risk core and its tests, received final human review, and merged with successful PR and main CI. Its approved specification remains `docs/plans/round-01.md @ a8ec42ecdf4199f91d3001fc6e2b1e887a0c5e41`. Its entry/graph/report integration remains excluded. Neither that approval nor the CI maintenance approvals authorize this round. The existing Portfolio Manager still writes final fields and the graph still ends at that node: this round does not yet replace that production authority path.

Sources: [D1 v1.48.0 SB-01](../req/requirements.yaml), [blueprint §8.5 and IF-09](../../architecture-blueprint.md), [ADR 001 D-01/D-02 and §6.5](../architecture/adr/001-graph-internal-final-check.md), [IR-01/IR-02 and the later IR-03 boundary](../architecture/invariants.md), [trace matrix](../architecture/trace-matrix.md), [runtime policies RP-14/RP-18/RP-19](../architecture/runtime-policy-catalog.md), [memory/state ownership](../architecture/memory-design.md), [architecture evaluation](../architecture/evaluation-table.md), [D4 V-SB01-01–04](../code-governance/verification-constraints.md), [structural constraints](../code-governance/structural-constraints.md), and project AGENTS/rules. Read the actual applicable artifacts; a Proposed document and a historical approval are not approval of this implementation.

## 2. Scope and exclusions

Implement C-09 as a pure deterministic consumer of the caller-provided proposal, availability summary, risk result, and asset type. Target the independent core of SB-01-FC01–FC04 and IR-02, plus C-09's local formal-result generation and proposal/formal separation responsibility under IR-01. Reuse the existing contracts rather than adding another completeness authority or risk evaluator.

There are two bounded work packages in the same proposed PR:

- **Core:** one new application module and one new offline test file, specified below.
- **Round 1 closeout:** actual approval/review/CI/merge evidence and narrowly affected current-status/trace updates in the listed existing records. This is maintenance of completed work, not a Round 2 application feature or permission to change business semantics.

Exclude SB-01-FC05, full SB-01 acceptance, and global IR-01/IR-03/IR-04 enforcement. Do not implement the IF-19 consumer entry/validator in this round. Do not change Portfolio Manager output, rating parsing, AgentState, graph wiring, recursion limits, CLI, `propagate()` signatures/return signals, report/HTML rendering, state saving, memory, or checkpoints. The pure callable is not invoked by the production graph yet; completing it does not mean every application recommendation passes through SB-01.

Do not implement FR-03 classification, observation, registry, necessity-list generation, summary production, or real adapter attachment. Do not add RunContext/statistics, manifests, history, query reuse, source proofs, snapshots, hashes, extra status sets, reason-priority protocols, dependencies, generic validators, or new configuration. Do not activate FR-06/FR-07/PR-01/CR-01 or add account/broker, financial-policy, or trade-execution checks. No runtime prompt/model change or live evaluation is proposed.

FR-03 and FR-04 remain SB-01's product implementation dependencies. Unit tests use controlled contract inputs; they neither supply a production FR-03 implementation nor prove real current-run sourcing. This round does not manufacture default `complete` or risk `passed` results in production to bridge that gap.

## 3. Exact development scope

After the specific tests and safety-critical scope are approved, the only application/test paths allowed to be created or changed are:

- `src/tradingagents/final_recommendation.py`: C-09 and small private helpers.
- `test/offline/test_sb01_final_check.py`: independent offline core tests.

Read-only code inputs include `src/tradingagents/portfolio_risk.py`, the five-tier vocabulary in `src/tradingagents/agents/rating.py`, Portfolio Manager/state/graph/entry/report/memory code needed to understand the excluded production boundary, relevant existing tests, `test/conftest.py`, `pyproject.toml`, and the existing CI scripts/configuration. Do not alter them to accommodate the new module. Avoid importing the agent/model package merely to obtain a five-value vocabulary; do not introduce a shared-vocabulary refactor or additional application file.

The following existing documents are the exact candidate write scope for the separately identified closeout work package, subject to that package's task/role authorization:

| Existing path | Permitted maintenance only |
|---|---|
| `AGENTS.md` | Correct the obsolete statement that Round 1 has no approval; retain all ongoing gates and future-round boundaries. |
| `CI.md` | Add a clearly dated current-status clarification/link for obsolete execution and Round 1 claims; preserve historical approved design and verification meaning. |
| `docs/ci/README.md` | Link actual CI-maintenance and Round 1 approvals, successful runs, and merges; preserve prior-version results and remaining unverified controls. |
| `architecture-blueprint.md` | Qualify the old global no-implementation statement with C-08 core status and locatable evidence; do not rewrite the architecture or claim integration. |
| `docs/architecture/invariants.md` | Update only affected evidence-state text: C-08 core exists, integrated IR-14 remains pending; C-09 remains pending until actual verification. |
| `docs/architecture/trace-matrix.md` | Map completed C-08 core and subsequently verified C-09 core to real tests/records; retain excluded FCs and integration gaps. |
| `docs/architecture/runtime-policy-catalog.md` | Update only affected core evidence/status references; keep runtime policies and unimplemented attachment boundaries unchanged. |
| `docs/code-governance/structural-constraints.md` | Mark actual C-08 and later C-09 module ownership accurately, with module-level callables; no new allocation or architectural responsibility. |
| `docs/code-governance/verification-constraints.md` | Correct only affected approval/test-location mappings, with references to records; do not change verification rules or append a growing execution log. |
| `docs/review-memo.md` | Record actual Round 1/relevant maintenance PR evidence and later Round 2 review; distinguish an AI draft from the human's real verdict and rationale. |
| `docs/ai-use-log.yaml` | Preserve existing activities and unique IDs; append actual closeout/Round 2 work and follow-up evidence with truthful attribution. |
| `docs/bug-diary.md` | Record significant observed defects and their actual lifecycle, including the contract-path defect; distinguish the unresolved macOS baseline failures from fixed issues. |
| `docs/migration/permission-path-changes.md` | Add a short historical/supersession clarification for the obsolete absolute-path instructions; do not reapply the migration or alter permissions. |

This list is a maximum, not a requirement to touch every document. Edit only demonstrably stale statements or affected mappings; preserve design rules, historical counts/results, unknowns, and all unrelated content. Do not mark this round passed or merged before those events. Preserve old AI-log entries' historical evidence limits and any existing ID-reconciliation provenance. A human verdict may be transcribed from its real record, but the AI must not supply a verdict or rationale on the reviewer's behalf.

Raw sessions continue under `transcripts/` through the existing export process. Each actual new export filename must be selected and authorized when it exists; this plan does not invent session numbers or authorize rewriting an existing transcript. There is no new mandatory evidence directory, annotations file, approval registry, summary file, or debt entry. `docs/debt-register.md` is not included merely because work is deferred or an OQ is open; a real debt decision would require its own scoped record task.

All older approved plans, D1/schema, baseline evidence, permission files, human-only `.opencode/rules.md`, `.agent/rules.md`, static launch prompt, workflows, dependency manifests, and mypy baseline remain unchanged. Approval of the closeout task must not be used to expand an implementation role's permissions or reinterpret limited prior runtime probes as complete permission enforcement. Confirm exact role/task access once before the affected work; ordinary work already authorized within that scope does not require repeated approval.

## 4. Interface and behavior

Use IF-09 through one module-level callable:

```text
evaluate(proposal, availability, risk, asset_type)
```

Parameter names/order are fixed; support both positional calls in this order and keyword calls. No default argument, required class/DTO, second evaluator, IF-19 public entry, or new service is required.

| Parameter | Accepted core input and boundary |
|---|---|
| `proposal` | A mapping containing `rating`/`text`, or `None`. Wrong-type/missing proposal is ordinary blocked input, not a fabricated proposal or an internal error. |
| `availability` | A program-produced D2 summary mapping or `None`; this consumer reads only completeness, necessary-item status/reasons and an available safe label, and applicability note. Controlled test mappings are not production evidence. |
| `risk` | The supplied current-analysis FR-04 result mapping or `None`. Only the applicable risk outcome and necessary explanation are consumed; metrics/thresholds are not recalculated or revalidated. |
| `asset_type` | Exactly `stock` or `crypto`, matching the existing supported paths for this round. Missing, wrong-type, or unknown values are ordinary blocked input. No detection, aliasing, lowercasing, or future asset policy is added. |

### 4.1 Safe proposal projection and valid model input

Return `model_proposal = None` when the proposal is missing or not a mapping. For a supplied mapping, project only `{rating, text}`: preserve each string exactly, and use `None` for a missing/null/non-string field. Never call `str()` or `repr()` on an arbitrary object and never copy unrelated fields. This is a safe representation, not a correction of model output.

Validate the original field categories while projecting: the legal ratings are Buy, Overweight, Hold, Underweight, and Sell. An unknown rating string or `REVIEW` is retained as the original string but blocks; wrong-type/missing rating becomes null and blocks. A conclusion must be a string with non-whitespace content. Empty/whitespace-only strings remain strings in the proposal but block; wrong-type/missing text becomes null and blocks. On passed, preserve the original valid rating and conclusion, including leading/trailing whitespace, line breaks, and Unicode. Do not add length, format, factual, semantic-quality, or financial-policy scoring. Do not parse rating labels or claims from the text.

### 4.2 Data and risk conditions

The FR-03 producer contract remains the five-field mapping `basic_completeness`, `applicability_note`, `observations`, `necessary_items`, and `supplementary_limitations`. C-09 does not become its producer or full-schema validator. For the fields this check consumes, require legal completeness, a necessary-item list with readable mapping entries and legal statuses/reason strings, and a string applicability note. Necessary statuses are `available`, `no_data`, `unavailable`, `withheld`, or `not_attempted`. An available item's reason may be empty. A missing or invalid consumed field is ordinary blocked input. Use safe item labels/methods when available; do not define a new canonical item-ID vocabulary or enforce producer-owned metadata.

- `complete` satisfies the data condition unless it contains a non-available necessary item (a basic contradiction).
- `incomplete` blocks with the non-available necessary item(s) and their corresponding reason(s). An incomplete summary with no such item or no corresponding usable reason is contradictory/unconfirmable and blocks.
- A legal `not_applicable` does not by itself block and retains its non-applicability explanation. It is not renamed complete; the applicable risk and proposal conditions still apply.
- Supplementary limitations do not independently block and are not converted into necessity gaps. They remain FR-03's disclosure responsibility; no renderer or duplicate availability output is added here.

Do not validate unused observations/supplementary payloads, require exact summary key-set equality, regenerate the seven-item list, inspect analyst enablement, audit raw queries/source/window/acceptance order, read a registry, or rederive completeness. The non-available-item view used for actual reasons and the two specified contradiction checks are not a second summary engine. Ignore unrelated extra keys rather than creating an extensible validation framework. An upstream field this consumer does not use must not create a new rejection rule.

For stock Buy/Overweight, require a supplied risk mapping with `status = passed`. `blocked`, `error`, missing/wrong-type risk, missing/illegal status, and wrongly `not_applicable` all fail the risk condition and give SB-01 `blocked`, not SB-01 internal `error`. Other legal stock ratings and legal crypto ratings do not require that risk input. C-09 does not call C-08, inspect scenario arithmetic or displayed percentages, or introduce ticker/freshness/digest binding. The current-analysis program source is the future caller's responsibility, not something this four-argument core proves from model text or signatures.

### 4.3 One complete formal result

Return one plain JSON-compatible mapping with these required fields on passed, blocked, and handled-error branches:

| Key | Meaning |
|---|---|
| `model_proposal` | Safe original `{rating, text}` projection or `None`; advisory only. |
| `gate_status` | Exactly `passed`, `blocked`, or `error`. |
| `reasons` | SB-01-owned list of short safe strings; blocked/error has at least one actual reason. A complete passed case may have none. A supplied applicability note may be retained here without inventing a pass claim or rewriting formal text. |
| `final_rating` | Original legal rating on passed; `REVIEW` on blocked/error. |
| `final_trade_decision` | Original valid text unchanged on passed; a program-generated non-whitespace manual-review notice with actual causes on blocked/error. |

A pass is not trade authorization; do not append an invented approval to the original conclusion. Ordinary input/condition failures are `blocked`. An unexpected exception inside C-09 is caught and yields a complete `error`/REVIEW with a safe notice, without echoing arbitrary raw objects, exception text, or traceback. Preserve any already safely available proposal; do not fabricate one. No production fault-injection argument is added.

When independently confirmable problems coexist, retain their actual short reasons, notably data and applicable-risk failures; no primary/secondary reason scheme, fixed order, duplicate gate status, `gate_reasons`, or `present` field is added. Risk reasons stay in their supplied object; use an SB-01 explanation of the failed risk condition rather than aliasing a risk list or flattening its entire result. Do not mutate any caller input or expose its mutable containers as result containers.

IF-19 validation of a missing/damaged/lost formal result at a real consumer is excluded. Tests assert this callable's output contract directly; do not add a production validator solely to implement their oracle. Future consumer contract failures must not be disguised as business REVIEW, but no entry/save path is modified now.

## 5. Complete offline test specification

All cases call `evaluate(proposal=..., availability=..., risk=..., asset_type=...)`, or the equivalent positional call. Unless overridden, fixture B is: asset_type `stock`; proposal `{rating: "Buy", text: "MODEL-ORIGINAL: retain this conclusion"}`; a controlled D2-shaped availability mapping with `basic_completeness = complete`, an empty string applicability note, a necessary global-news item with `status = available` and empty reason, and observation/supplementary lists; and a supplied risk mapping with `status = passed`. The necessary item's label/method are explicit fixture inputs. Other producer-owned metadata may be included for readability but is not a new consumer acceptance condition. Fixtures are hand-authored consumer inputs, not a claim that FR-03 exists or a fake production summarizer.

Derive expected decisions and notice categories directly from D1 and this approved table, never by calling evaluator helpers to create the oracle. Parameterized/shared tests are encouraged; the rows are behavior groups, not a required number of functions or cases.

| ID / trace | Controlled input | Required independent assertions |
|---|---|---|
| R02-01 / SB-01-FC01, IR-01 core | Five legal ratings with complete data; supply passed risk for applicable stock Buy/Overweight; cover positional and keyword calls. | passed; original legal rating/text retained; safe proposal representation; complete formal fields. |
| R02-02 / SB-01-FC04, IR-01 core | `proposal=None`, a non-mapping proposal, missing/null/non-string rating, `REVIEW`, and an unknown rating string; other B conditions valid. | ordinary blocked/REVIEW; no guessed Hold, text rating parse, or fabricated proposal; preserve safe strings and null only missing/unsafe-type fields. |
| R02-03 / SB-01-FC01/FC04 | Valid leading/trailing whitespace, multiline and Unicode text; then missing/null/non-string/empty/whitespace-only text. | valid text preserved exactly on pass; invalid text is ordinary blocked, never internal error; empty/whitespace strings stay in the proposal; formal text becomes an actual manual-review notice. |
| R02-04 / SB-01-FC01/FC03/FC04, IR-02 core | Legal stock/crypto cases; missing/null, non-string, empty or unknown asset type. For legal crypto and legal stock Hold/Underweight/Sell, pass `risk=None`. | unsupported/invalid asset type blocked; valid non-applicable cases do not require risk; no asset guessing or new policy. |
| R02-05 / SB-01-FC02, IR-02 core | `incomplete` with an actual necessary item respectively no_data/unavailable/withheld/not_attempted and a corresponding short reason. | blocked/REVIEW; reasons and formal notice identify the necessary-data condition and actual supplied cause; no refetch. |
| R02-06 / SB-01-FC02 | Complete data with an actual supplementary limitation; legal `not_applicable` with a nonempty applicability note and no applicable necessary items. Test the latter with otherwise passing conditions and with applicable stock Buy plus missing risk. | supplementary alone does not block; non-applicability alone does not block and its note is retained without rewriting the original passed conclusion; it does not bypass applicable risk. |
| R02-07 / SB-01-FC04, IR-02 core | Missing/non-mapping availability; missing/illegal completeness; missing/wrong-type necessary list, malformed consumed item status/reason, or wrong-type applicability note; complete plus a non-available necessary item; incomplete without a gap or corresponding usable reason. | ordinary blocked/REVIEW with invalid/unconfirmable data reason; no fabricated complete, registry lookup, schema service, or internal error for these ordinary cases. |
| R02-08 / SB-01-FC03, IR-02 core | Stock Buy and Overweight paired with risk passed/blocked/error/missing/non-mapping/missing-or-illegal status/not_applicable; other B inputs valid. | only passed satisfies risk; all other applicable results yield blocked/REVIEW; upstream risk error is not SB-01 internal error; no metric recheck or risk call. |
| R02-09 / SB-01-FC02/FC03/FC04 | Model text claims complete data or approved risk while structured inputs fail; valid text contains a contradictory rating label; separate case combines an actual data gap with applicable risk failure. | model claims never override inputs or determine rating; valid text is retained on a genuine pass; independently confirmable data and risk problems both remain explained, without an ordering/priority assertion. |
| R02-10 / SB-01-FC04, IR-02 core | Inject one controlled exception at a narrow private C-09 boundary after ordinary input validation, with otherwise valid B inputs. | complete error/REVIEW; actual safe check-failure reason and manual-review notice; no escaping exception/raw traceback; no production hook. |
| R02-11 / SB-01-FC01–FC04, IR-01/IR-02 core | Representative passed/blocked/error outputs; safe strings, wrong-type proposal values with a distinctive unsafe string conversion; snapshots of all caller inputs; controlled applicability note. | standard JSON serialization without an implicit encoder; required field types and gate/rating relationships; no unsafe string conversion; no input mutation/container aliasing; preserved proposal and actual notice semantics; no duplicate status aliases. |

Use narrow static inspection and, where useful, a dependency-call sentinel to verify no model/data/storage/graph work or risk recomputation in the callable. Do not build a generic dependency scanner, intercept every filesystem operation, or count pytest/import setup as evaluator I/O. One compatible result from the existing C-08 may be reused in a case if useful; a separate C-08→C-09 integration suite, C-08 mutation, or additional integration acceptance is not required.

Do not assert an exact full key set, notice paragraph, helper name, class count, reason order, text length/quality score, test count, or coverage percentage. Do not exhaustively multiply every input dimension. Existing contract requirements still apply: five required fields, no duplicate formal status mechanism, actual reasons, and no proposal substitution. Tests must detect relevant regressions such as accepting non-passed applicable risk, treating incomplete data as complete, accepting invalid asset types, parsing a rating from text, trimming valid text, or mapping ordinary invalid input to internal error; no mutation-testing platform is required.

## 6. Verification and execution sequence

1. Human reviews this exact core and closeout scope, interface decisions, specific controlled inputs/expectations, and safety-critical ADR applicability.
2. Commit the final specification P2 and obtain real non-author pre-approval in the same PR before corresponding implementation. This planning task grants no Git or publication operation.
3. Confirm the existing environment, actual role permissions, exact record paths, raw-session process and bounded command outputs. Do not self-edit controls.
4. Under the applicable approval/task grant, make minimal closeout updates and write approved tests before the core. Keep closeout, code and subsequent evidence changes reviewable as distinct work; do not manufacture commit history.
5. Run targeted behavior, structural checks and all prior applicable suites; fix code in the implementation phase, then reverify. Report failures/skips and preserve evidence.
6. Record actual results and final review, pass the applicable PR gates, and merge only with the corresponding human authorization. Do not report full SB-01 or integrated IR completion.

The contract-test selection for this round is exactly `test/offline/test_sb01_final_check.py`. The approved specification names that test and its application module. Do not add unrelated literal test paths to this specification merely as historical references: the existing selector extracts paths from the committed text, including examples and commands. Prior tests are exercised through the existing regression suite. Do not modify the selector or add another CI gate for this round.

### 6.1 Proposed commands and side-effect bounds

These are command designs, not commands executed or authorized by writing this file. From the project root, use the existing interpreter only after confirming it resolves `tradingagents` to this checkout and its dependencies match the existing CI requirements and type-check constraints. Inspect `test/conftest.py`'s existing settings overlay, temporary locations and network blocking; do not display credentials or silently disable project fixtures to manufacture a regression pass. No installation, upgrade, live call, or dependency-file edit is included.

Use one bounded temporary root outside the user's home, so the existing suite-isolation test is not broken by locating TMPDIR beneath the home directory. `/private/tmp/cs5351-round02/` is the proposed macOS location; use a reviewed equivalent outside home on another platform. No repository evidence directory is created, no output is committed, and no historical baseline is regenerated.

```bash
round2_python=/Users/ichihann/Desktop/CS5351/round1-runtime/bin/python
round2_output_root=/private/tmp/cs5351-round02
mkdir -p "$round2_output_root/tmp" "$round2_output_root/mypy-cache"

TMPDIR="$round2_output_root/tmp" PYTHONDONTWRITEBYTECODE=1 \
  "$round2_python" -B -m pytest -q -p no:cacheprovider \
  --basetemp="$round2_output_root/targeted-pytest" \
  --junitxml="$round2_output_root/targeted.xml" \
  test/offline/test_sb01_final_check.py

PYTHONDONTWRITEBYTECODE=1 "$round2_python" -B -m ruff check --no-cache \
  src/tradingagents/final_recommendation.py test/offline/test_sb01_final_check.py

PYTHONDONTWRITEBYTECODE=1 MYPY_CACHE_DIR="$round2_output_root/mypy-cache" \
  "$round2_python" -B scripts/ci_checks.py mypy \
  --output "$round2_output_root/mypy-current.txt" --baseline mypy-baseline.txt

TMPDIR="$round2_output_root/tmp" PYTHONDONTWRITEBYTECODE=1 \
  "$round2_python" -B -m pytest -q -p no:cacheprovider \
  --basetemp="$round2_output_root/regression-pytest" \
  --junitxml="$round2_output_root/regression.xml"

PYTHONDONTWRITEBYTECODE=1 "$round2_python" -B -m pip check
git diff --check
```

Execute and inspect each result before proceeding; do not pipe away failures. The default suite excludes `integration` and is not a live/full offline-and-live pass. Targeted cases must execute without skips; default-suite skips/missing optional dependencies and the previously observed macOS Windows-lock test failures must be reported, not called passes or automatically waived. Compare unexplained failures with the reviewed baseline in an authorized isolated check when needed; do not repeat baseline work solely for a new count. Remote Linux CI and local macOS outcomes are distinct evidence. No new coverage, latency, quality or warning-count threshold is added.

Local checks do not replace the existing full-repository lint, type-baseline, dependency/import, requirements-schema, regression, security/API/permission, test-approval, AI-use, contract and aggregate gates when applicable. Do not expand `mypy-baseline.txt` or weaken old assertions. Whether semantic evidence is applicable is determined by the real final diff and current CI classification, not a fabricated semantic pass; no runtime prompt/model change is proposed.

### 6.2 Records, scope fields and implementation start

Record actual command/environment/code version, independent input/expected result, FC/IR mapping, failures/skips and evidence location in the existing authorized records. Keep source authorship, human command execution and later read-only review distinct. Preserve unknown metadata rather than inventing reviewer identities, times, raw transcripts or CI results. Retain the existing AI-log ID-reconciliation provenance; select unused IDs from the actual new baseline.

Keep the final approved P2 file unchanged. Put later approval, execution and completion evidence in the same PR and existing records, not into its frozen Pending cells. Reapproval applies only when affected scope, interfaces or expectations materially change.

The existing CI implementation-start calculation includes classified governance paths such as `docs/ci/`, not only application Python files. Therefore commit P2 and obtain pre-approval before those closeout edits as well. T2 is the actual first gate-relevant changing commit under the current classifier; if a governance closeout commit comes first, do not declare a later application commit as T2. Preserve the real approval-before-implementation sequence; do not change CI or backdate commits to satisfy it. Populate PR fields with the actual plan P2, approval URL, T2 and covered IDs/paths after those facts exist. Contextual dependency IDs in code comments must be accounted for honestly without claiming their implementation complete.

## 7. Preconditions and unresolved items

The user confirmed this draft's scope, four-parameter module-level callable, no IF-19 consumer entry, safe string/null proposal projection, and exact stock/crypto asset boundary. These are execution decisions for the submitted specification, not the immutable test-specification pre-approval or safety-critical implementation approval.

No FR-03 producer is implemented by this round. Controlled consumer fixtures permit independent core verification; current-analysis sourcing, actual graph execution, global formal authority, IF-19 consumer validation, entry/report consistency and final-state/memory propagation remain future integration obligations. Do not close them because the core tests pass.

D2 OQ-01/OQ-04 affect entry/file and save/display work, OQ-08 affects graph depth, and OQ-12/OQ-13/OQ-15/OQ-16 concern producer, observation, summary and callback integration; they are not resolved here. Identify OQs by their source document as well as ID because historical/current artifacts may use the same number differently. OQ-07 requires checking actual role/task configuration for this round; configuration presence and prior limited positive/negative probes do not certify all permissions. No new business OQ, asset detector or financial-policy approval is invented.

`src/tradingagents/final_recommendation.py` is safety-critical. The implementation PR needs the applicable existing ADR reference and real human approval for C-09/IF-09 and these tests. The ADR's global Proposed status must not be changed into blanket architecture approval by a status-maintenance edit. The Round 1 approval covers C-08 only; PR #9 covers the CI path fix only.

Environment/import resolution, limited command outputs, current main, selected role, exact record/transcript access, CI/PR fields and real independent approvals remain prerequisites to their dependent actions. An unavailable prerequisite blocks only dependent work; it is not a reason to alter requirements or permissions. This plan adds no push, PR-creation, final-review or merge grant.

## 8. Approval and completion record

| Item | Current state |
|---|---|
| Scope/design decisions | Selected by the user; this file records the concrete specification for review, not application implementation approval. |
| Selected baseline | main `eb861e060993ee20bb561246ca5f745d6300dff0`; authoring checkout `6325db571a14a059ea39ac0d94afa5e8223269bb` has identical tracked content. |
| Plan version | Initial proposed Round 2 specification; P2 is not committed by this task. |
| Specific test pre-approval | Pending; no immutable P2 approval event recorded. |
| Safety-critical C-09 implementation approval | Pending for this round. |
| Role/environment/output/record readiness | Pending verification and scoped setup for the selected task. |
| Application/test implementation and execution | Not started by this planning task; no test/lint/type result claimed. |
| Round 1 closeout | Included as bounded proposed maintenance; not performed by this planning task. |
| SB-01-FC01–FC04 core / local IR-01 and IR-02 responsibility | Completion not established. |
| SB-01-FC05 / full SB-01 / global IR-01/IR-03/IR-04 / FR-03 production | Excluded and not accepted by this round. |

After actual approval, record the precise version, scope, reviewer/event time and evidence location in the PR or an authorized existing record. Completion requires the approved core assertions, applicable regression and structural checks, real PR gates and final human review, plus truthful closeout records. Report unrun/blocked/skipped checks and unimplemented integration separately. A pure-core pass, CI pass, human review and merge are distinct facts; none establishes trade authorization or whole-system safety.
