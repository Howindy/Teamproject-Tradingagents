# Deterministic financial metrics: integration preparation

Version: FM-PREP-2 (2026-11-23), superseding the proposal at `4799b33b26dd97823dec937d3b8264eb7f9007aa`. **Approval pending.** This is a proposed execution/test specification, not approval, implementation, or acceptance. The former 16-request proposal is withdrawn; this revision proposes at most six requests and executes none.

## 1. Immutable inputs and the two PRs

- Repository: `Howindy/Teamproject-Tradingagents`; target: `main`.
- Preparation baseline: `origin/main` = `5c6e2caed5e4baceb136b5544ba5e283c0822cdb`, fetched on 2026-11-23. D1 is **v1.49.0**, not the previously discussed v1.48 branch. Existing inventory: 13 requirements / 55 FCs; six active / 27 FCs; seven deferred / 28 FCs.
- Implementation source: `origin/haoxi` = `7e676fb00fff319930685a9fa059265f3061aeff`. Preserve that branch, `haoxi-fr08-downstream-brief`, all earlier commits and original evidence. Do not merge the entire source branch into main.
- Working branch: `prep/financial-metrics-integration`; independent worktree: `D:/CityU/cs5351/project/Teamproject-Tradingagents-financial-prep`.
- **PR 1 / preparation:** first freeze this plan and open a Draft PR; stop for a real independent human's specification approval. Only after that event, revise D1/D2/D4 and add the shared evaluation configuration, fixed evidence projection, trusted runner and runner tests described below. No application migration in PR 1. Obtain final review and separate merge authorization.
- **PR 2 / feature integration:** branch from then-current main after PR 1 merges; submit a separate immutable migration/test plan and Draft PR. Obtain its own test and safety-impact approval before adapting existing code/tests. Run offline regression and approved fixed semantic evaluation against its exact candidate SHA. Separate final review and merge authorization are required.
- This session is authorized only to read, fetch, create the worktree/branch, submit this plan and necessary planning records, push this branch, and create the Draft PR. It does not authorize execution of the post-approval work, paid/model/vendor requests, workflow dispatch, dependency installation, GitHub settings changes, implementation, or merge. Do not contact/request review from Yifan automatically.

## 2. Requirement proposal (for explicit human decision)

Use **FR-10: Deterministic disclosed financial metrics**, a currently unoccupied registry ID; do not reuse current deferred FR-07 (analyst briefs), historical FR-08 (shared brief), or historical FR-09 proposal terminology. FR-10 is the successor of the personal branch's **old financial FR-07**, not a new summary feature. Keep historical formula identifiers such as `fr07-direct-v1` as provenance, with this mapping documented; do not rewrite old records to imply current approval.

Propose FR-10 active/approved only after the actual scoped requirements decision. This adds one requirement with ten FCs: proposed totals **14 / 65**, active **7 / 37**, deferred unchanged **7 / 28**. Update counts only after approval; other requirements and existing core acceptance stay unchanged. Frozen reference evidence supports FR-10; it does not automatically reactivate the deleted GR-01 registry object.

| Proposed FC | Required behavior and independent acceptance |
|---|---|
| FR-10-FC01 | Select disclosed structured facts for the issuer and actual fiscal position as of the cutoff; retain concept, accession, fact/source references and calendar evidence. Never select using prose or approximate equal fiscal-quarter division. Ambiguity is explicit n/a, not guessing. |
| FR-10-FC02 | Quarterly and annual revenue YoY use the directly reported same fiscal quarter/year comparison; revenue QoQ uses the immediately preceding directly reported fiscal quarter. Missing/non-positive comparison bases have explicit reasons. No YTD-as-quarter, nearest-column replacement, or quarter subtraction. |
| FR-10-FC03 | Gross, operating and reported net margins use same-span/scope revenue and appropriate numerator, with compatible units/currency. Missing disclosed concepts yield n/a, not invented proxies. |
| FR-10-FC04 | Current assets/current liabilities and total liabilities/total assets use compatible same-date instant facts. Invalid/non-positive denominators yield n/a. |
| FR-10-FC05 | Reported-span FCF = operating cash flow minus positive reported PP&E payments, using compatible spans and evidenced sign convention. Preserve annual/YTD labels; negative valid FCF remains negative; unknown sign is n/a, not abs(). |
| FR-10-FC06 | Fiscal-year P/E = eligible completed daily close / positive annual diluted EPS, with explicit price date, EPS period, currency/share basis and freshness evidence. This is not TTM P/E. Future/stale/incompatible prices and non-positive EPS yield n/a. |
| FR-10-FC07 | Decimal/exact arithmetic, explicit units/scales, ROUND_HALF_UP display; percentages and ratios to one decimal, FCF in source-compatible USD millions. Values/status/reasons, input IDs, periods and sources are deterministic and JSON-projectable; no binary float authority. |
| FR-10-FC08 | Ten stable rows: revenue_yoy_q, revenue_yoy_a, revenue_qoq, gross_margin, operating_margin, net_margin, current_ratio, liabilities_to_assets, fcf_reported_span, pe_fy. Every unavailable row has a reason and retains known inputs/periods; no zero-fill, invented source or falsely verified statement. |
| FR-10-FC09 | When enabled and fundamentals selected, inject the program-rendered table before the fundamentals analyst's first model invocation and keep it on tool/wrap-up turns. Existing five financial tools, instructions/history and saved original reports remain. Repeated turns reuse calculation within one analysis; independent analyses do not inherit mutable metric results. |
| FR-10-FC10 | Explicit opt-in configuration and unchanged disabled path; unsupported issuer/asset and provider failure degrade explicitly without invented metrics or aborting otherwise valid baseline analysis. No metrics fetch when disabled or fundamentals omitted. Preserve CLI/programmatic return shapes and other query/tool behavior. |

Product boundary: ten metrics, directly reported spans only. No TTM, FCF YoY, subtraction-derived Q4, investment correctness guarantee, trade authority, metric publication/recovery system, new statistics, or shared summaries. FR-10 does not decide completeness, risk or formal recommendation and does not add an SB-01 veto. Unsupported instrument behavior and all failure notices must be explicit in the approved contract; old implementation's silent/no-block paths are review targets, not automatically accepted.

Date policy proposal: `00:00 America/New_York` on the analysis date; no same-day filing/close assumed available without time evidence. Filing visibility is date-level and historical prices are reconstructed daily bars, not an intraday point-in-time guarantee. Actual fiscal labels and anniversary matching need evidence; unprovable positions remain unavailable. AAPL/XOM calendars differ; MSFT and January-year-end regression guard against calendar-year shortcuts.

## 3. Architecture and migration findings

Read inputs: AGENTS.md, Prompt.md, architecture-blueprint.md, current requirements/schema, ADR 001, invariants, trace matrix, runtime policy, memory design, permission model, evaluation table, D3 structural/tool rules, D4 verification constraints, .agent/.opencode rules, CI workflows/scripts/config, and relevant source/tests.

- Main uses `src/tradingagents`, `src/cli`, `test/offline`, `test/live`. Imports remain `tradingagents`; old test paths/root discovery and `tests.test_graph_end_to_end` imports cannot be copied unchanged.
- Reusable source modules under `TradingAgents/tradingagents/financials/`: `models.py`, `metrics.py`, `service.py`, `sec_provider.py`, `wiring.py`, `__init__.py`. Arithmetic/selection logic is reusable, not pre-certified for the current framework. Reference-only loading should stay an explicitly selected adapter/test concern, not a hidden production fixture dependency.
- Existing SEC adapter adds `company_facts()`/`submissions()` using the existing CIK/cache path; Yahoo adapter adds completed-close/basis evidence. Preserve original vendor entry functions and failure semantics. Actual provenance and split/basis edge cases require tests, not merely renamed code.
- Integration sites on main are still `create_fundamentals_analyst(llm)`, GraphSetup's fundamentals factory, TradingAgentsGraph construction and default configuration. Original analyst tools are get_fundamentals/get_balance_sheet/get_cashflow/get_income_statement/get_insider_transactions.
- **Do not copy the old date-keyed factory cache as a run-isolation proof.** Graphs can be reused across analyses; make metric scope fresh at the actual analysis entry while sharing turns inside it. Check both CLI's streaming path and `propagate()`. The PR 2 plan must name the minimal lifecycle hookup after inspecting then-current main/FR-03 work.
- Old `test_financial_metrics.py` mixes financial tests with FR-08 protection/summary assertions. Port only financial coverage; leave FR-08 tests/implementation in the personal branch. Both old financial test files resolve fixtures through `parents[2]/docs/fr07`; replace with the approved fixed projection, not accidental sibling-worktree reads.
- Preserve current FR-03 observation/necessity semantics and IF-24 research snapshot; SEC/price reads introduced by FR-10 are not automatically new supported FR-03 paths or news FR-01 queries. Do not synthesize completeness from metric n/a. Keep C-08/C-09 independent cores, formal result fields, IF-19 boundaries, saved reports and memory unchanged.
- No `run/brief.py`, `run/summary.py`, `run/assembler.py`, brief config/state fields, five-role prompt substitution or Context Assembler node is included.

Proposed ADR 002 owns only FR-10 structured inputs, calculation, rendering, local analyst injection, fresh-run reuse and failure semantics. Add a narrow exception to ADR 001 D-10c's analyst-input description for this approved metric table; do not reopen global context assembly or final authority. Primary owners remain financials/models (contracts), metrics (pure selection/calculation/rendering), service (data protocol/cache), sec_provider (source translation), wiring (composition/lifecycle). Plain projections cross serializable boundaries; no provider/lock/Decimal object enters graph checkpoints. Existing IR-01/02/04/05/14/17 are compatibility boundaries, not newly claimed global acceptance. No new IR ID is reserved by this plan.

## 4. Exact PR 1 post-approval file allowlist

Only the plan and planning log are changed at the initial freeze. The following is the proposed **maintenance** allowlist after real approval; it is not a standing implementation grant. It is a maximum scope, not a checklist requiring a change to every file: edit only what resolves an actual inconsistency or implements the approved preparation. No wildcard edit permission follows.

| File | Exact preparation work |
|---|---|
| `docs/plans/financial-metrics-integration.md` | Freeze specification. After approval leave this file byte-identical: the checker detects any change to the bound specification. Put actual events in the AI-use log/review memo/PR body; an edited plan needs a new freeze/reapproval. |
| `docs/ai-use-log.yaml` | Append actual planning/maintenance participation; preserve old entries. |
| `docs/review-memo.md` | PR-specific findings and actual human verdict only when received. |
| `docs/req/requirements.yaml` | Add FR-10 and ten FCs; scope/counts, successor mapping, narrow definitions/trace/conflict entries; retain existing deferred items and history. |
| `architecture-blueprint.md` | Update inventory; add the bounded financial module/input contract, ownership/data flow, analyst input, failure boundary and verification links (sections 1, 5, 6.8, 8, 10, 14). |
| `docs/architecture/adr/002-deterministic-financial-metrics.md` | New scoped proposed/approved decision with real evidence; no invented approval. |
| `docs/architecture/adr/001-graph-internal-final-check.md` | Narrow D-10c/section 7 compatibility clarification; preserve final-check decisions and historical text. |
| `docs/architecture/invariants.md` | Record FR-10 compatibility with existing authority/run isolation, without renumbering IRs or claiming global implementation. |
| `docs/architecture/trace-matrix.md` | FR-10 FC to module/test/evidence links, marked planned until PR 2. |
| `docs/architecture/runtime-policy-catalog.md` | Narrow optional metrics failure/n-a policy, not formal business-state rules. |
| `docs/architecture/memory-design.md` | Ephemeral metric cache lifetime; no new memory/persistence/recovery policy. |
| `docs/architecture/evaluation-table.md` | Scoped option rationale and fixed evaluation references; no invented measurements. |
| `docs/code-governance/structural-constraints.md` | Add financial ownership/dependency allocation; keep analyst-brief prohibition. |
| `docs/code-governance/verification-constraints.md` | FR-10 planned FC/test mapping and semantic gate link; no passing acceptance claim. |
| `docs/ci/semantic_eval.yaml` | Fixed dataset/rubric/model/repetition/threshold proposal, approved status only after actual approval metadata. |
| `docs/ci/financial-metrics-cases.json` | Fixed cases/compact structured inputs, independent expected rows, source byte hashes and old commit/path/pointer provenance; no candidate-generated oracle. |
| `docs/ci/financial-metrics-rubric.md` | Scoring, critical failures, model call controls, baseline comparison and human adjudication rules. |
| `docs/ci/README.md` | Runner invocation, provenance, evidence locations, preparation-vs-feature limitations. |
| `scripts/financial_metrics_eval.py` | Trusted `evaluate(config, candidate_sha) -> mapping` runner, candidate subprocess loader, prompt capture/scoring and failure handling. |
| `scripts/ci_semantic_eval.py` | Minimal preservation of detailed runner score/provenance references in record.json; fail closed on invalid/failed result. Keep CLI compatibility. |
| `.github/workflows/trusted-evaluation.yml` | Minimal semantic-mode secret handoff and details artifact upload for the approved runner; maintain default-branch/candidate checks and protected environment. No pull-request secret exposure. |
| `test/offline/test_financial_metrics_evaluation.py` | Runner/case/provenance/scorer/loader negatives and positives, isolated fake candidate and fake external model. No feature acceptance claim. |
| `test/offline/test_ci_gates.py` | Update exact inventory expectation to 14/65, active 7/37 and deferred 7/28; test new detailed evidence serialization and workflow handoff while retaining all existing negative gates. |

`docs/req/req-schema.json`, `scripts/ci_checks.py`, ordinary CI workflow, dependencies and mypy baseline are not planned edits. The current schema checker exists (the earlier historical validator's removal is not a current missing-check claim). If a schema/API change is actually necessary, propose it before extending this allowlist.

No edit to human-only `.opencode/rules.md`, `.opencode/permissions.jsonc`, `docs/architecture/permission-model.md`, `AGENTS.md`, `Prompt.md`, or `.agent/rules.md` is authorized by this plan. Their scope/count descriptions and permission-model maxima need human-owned alignment/explicit scoped maintenance decisions before dependent work. Current task explicitly names this plan output and Git operations; effective deployment of the V1 permission file is unverified, not claimed. Do not self-expand controls. `transcripts/` must retain a real harness export through a human-approved capture path; do not reconstruct a raw transcript from this summary or fabricate a session export. If unavailable, disclose that evidence gap.

## 5. Fixed evidence and proposed semantic evaluation

### 5.1 Reuse and freeze before runner implementation

Use source SHA `7e676fb00fff319930685a9fa059265f3061aeff`, not mutable branch names. Original reference: `docs/fr07/sec-reference-draft-v1`, version `fr07-sec-reference-v1`, freeze digest `a1256bdef7ef8d46f71f0ef3bba7b06550d87e962f957da8b7e30e68702a2af6`. It was independently prepared before the old implementation. Preserve original freeze time, pending labels/encoding defects and old approval wording as history; new human approval selects the material for this round and does not rewrite that history.

PR 1 creates one compact JSON projection from original selected facts, selection plan, filing metadata, price records and independent expected_metrics.json. Include each source blob SHA-256, old Git path/JSON pointer and relevant calendar/share-basis evidence. Copy exact numbers as decimal strings and exact expected rational/display/status/reason; never run migrated calculators to create expected values. The independent expectations, counterexamples and projection rules in this plan are submitted together for approval. After real plan approval, lossless copying and verification against those approved contents may continue under this scoped authorization without a second routine projection-approval gate; record the resulting projection version/hash before runner/scorer implementation. Material changes to expectations, scoring or scope require approval of the affected revision. No full 21 MB raw snapshot duplication or source retrieval is needed. Retain immutable links to original source blobs for review. MSFT selected_metrics.json is implementation output, **not an independent oracle**; any added MSFT expectation changes this fixed evaluation scope and requires corresponding approval, supported by independent arithmetic from source facts.

Fixed as-of: 2025-08-05, midnight New York, historical completed session 2025-08-04. Four semantic cases:

| Case | Controlled material | Independent required interpretation |
|---|---|---|
| FM-S01 | AAPL fixed facts/prices plus identical fixed basic/company/statement text for baseline and candidate | Ten values in metric order: 9.6%, 2.0%, -1.4%, 46.5%, 30.0%, 24.9%, 0.9x, 80.1%, 72,281 USD_millions, 33.4x; Q3 FY2025, FY2024 annual comparison, YTD FCF and FY P/E labels preserved. |
| FM-S02 | XOM fixed facts/prices and its fixed source text | -12.4%, 1.5%, -2.0%, gross/operating margins n/a (missing_input), 8.7%, 1.2x, 39.7%, 12,322 USD_millions, 13.7x. No proxy for absent gross/operating concepts. |
| FM-S03 | FM-S01 with only `aapl.rev.q3.2024` removed; keep current and immediately preceding quarter | revenue_yoy_q n/a/missing_comparison; known current input retained; QoQ still -1.4%. No nearest-quarter-as-YoY substitution. Other rows unchanged. |
| FM-S04 | FM-S01 with price date still 2025-08-04 but completed_at changed to `2025-08-05T04:00:01+00:00` (one second after the cutoff), all financial facts unchanged | pe_fy n/a/price_not_completed; all other rows unchanged. Report cannot call the price eligible or relabel annual EPS as TTM. |

For each case include a complete frozen statement-material string exposing the approved raw source facts, fixed task/language/history and five original tool definitions. For the two paired normal cases baseline and candidate receive identical raw statement material (so metric preparation is not withholding baseline evidence); the two counterexamples run candidate-only. Use controlled external substitutes; no SEC/Yahoo fetches during evaluation. Freeze the losslessly copied input, reason vocabulary, case answer/provenance and rubric at a separate PR 1 commit **before** evaluation/scorer implementation, and seek affected-case approval only for a material change to approved expectations, scoring or scope, not routine copying/hash verification. Historical MSFT live pilot is background only: two HTTP attempts (one rejected, one successful); it does not certify this migration or replace these cases.

### 5.2 Proposed scoring and model controls (not yet approved)

- Candidate must receive all ten program rows before first invocation, and its generated report must correctly discuss the ten values/unavailable rows with appropriate periods/units/sources. Prompt-presence and number-mention checks alone are not report semantic acceptance.
- Per candidate case score five binary dimensions: (1) numeric/status/reason correctness; (2) period/unit and price/EPS basis; (3) disclosure/source traceability and no lookahead claim; (4) useful fundamental interpretation without treating n/a as zero/verified; (5) retained ordinary fundamental task coverage and qualifications. Publish atomic assertions, recognized metric labels/aliases and human adjudication examples before running, consistent with these submitted scoring rules. Unparseable/ambiguous claims are `needs_review`, not automatic pass. A human may resolve them with a linked claim-level review, never change the oracle to fit output.
- Proposed threshold (pending approval): candidate dimensions 1-3 pass for all four cases; total at least 90% across **20 candidate dimension checks (4 cases x 1 execution x 5)**, i.e. at least 18/20. Any wrong asserted target metric, invented missing value/source, future-price use, YTD-as-quarter or FY-as-TTM label is a critical failure, regardless of average. Dimension 5 must not regress relative to baseline for either paired normal case FM-S01/AAPL or FM-S02/XOM; FM-S03/FM-S04 have no baseline run/comparison and must satisfy the candidate rubric on their own. Baseline dimensions are reported separately and never enter the 20-check denominator; baseline metrics performance is not required to pass a feature it does not implement. No profitability/cost guarantee or repeated-run stability claim.
- Proposed model: official DeepSeek endpoint `https://api.deepseek.com`, provider `deepseek`, API model **`deepseek-flash`**, matching the historical successful pilot's model rather than `deepseek-chat`. Fix temperature=0, max_tokens=4096, stream=false, n=1, English output, client max_retries=0, request timeout=120 seconds and `extra_body={"thinking":{"type":"disabled"}}`; leave other optional sampling controls unset and record that omission. Thinking is explicitly disabled, not inferred from the model name. **Six completion requests maximum**: FM-S01/FM-S02/FM-S03/FM-S04 candidate once each, then FM-S01/AAPL and FM-S02/XOM baseline once each; no repetitions or LLM judge. Record exact request controls, returned model/version if supplied, usage, finish reason and raw response; alias name/temperature do not guarantee bitwise reproducibility. A rejected/failed/truncated request counts against the six-request cap; missing/failed/skipped required cases cannot pass. Do not silently retry or reinstate the withdrawn 16-request proposal.
- This plan proposes that configuration for review but **does not authorize the requests**. Live semantic execution requires separate real human authorization of this fixed set/model/budget and protected-environment access. Ordinary `mode=live` tests are optional and not a substitute for this semantic gate. If reviewers choose a different model, threshold or request budget, freeze/reapprove the affected configuration before execution.

### 5.3 Trusted runner interface and candidate loading

Existing trusted workflow dispatches only from default branch, checks out trusted tools at github.sha into root and exact candidate SHA into `candidate/`, verifies both HEADs, installs `candidate[dev]` plus trusted CI requirements. It reads **root** `docs/ci/semantic_eval.yaml`, runs root `scripts/ci_semantic_eval.py` and imports `module:function` from the trusted tool environment. Merely putting config/runner in PR 2 is insufficient. Semantic mode currently has no model-secret handoff; only live mode does. Configuration is currently unapproved and no financial runner exists.

PR 1 must merge the approved fixed config/cases/rubric/runner first. Invoke runner as `financial_metrics_eval:evaluate` through the existing CLI. Root script directory provides that trusted module; never import a runner supplied by candidate code or add candidate/scripts ahead of it. Approved data/rubric/model/config hashes must match trusted files; unapproved/missing material fails before model requests.

Runner verifies candidate/HEAD equals the requested full SHA and baseline SHA equals the frozen comparison commit selected in PR 2. Load application in a fresh subprocess using main's normal installed-package discovery (`pyproject.toml` setuptools package-dir/where=src), cwd=candidate; do not inject PYTHONPATH or prepend source directories to sys.path as a substitute for installation. Record and assert `tradingagents.__file__` and analyst/financial module origins resolve inside the exact candidate/src checkout for the workflow's editable installation; reject installed sibling/editable-worktree packages. Baseline loads independently from its correctly installed frozen main source in a separate environment, without importing candidate financials. Baseline source checkout and installation strategy must be pinned in PR 2; no moving main comparisons or changing the shared environment between variants. Missing installation is a prerequisite failure, not permission to override discovery. Child uses original analyst factory and real candidate selector/calculator/renderer/injection; replace only model/vendor transports, not the feature being tested. Missing financial module in candidate is failure, not full-report fallback or skip. A feature-absent baseline is valid only in explicitly labeled baseline mode.

Pass controlled cases through candidate `FinancialInputs` and factory boundary, capture real first-turn/wrap-up prompt, then invoke the approved external model with that captured request and fixed tool-material protocol. Do not substitute a hand-written prompt for candidate assembly. Keep trusted case answers/scorer outside candidate import path and never load candidate-generated expected results. Candidate code is execution under the existing protected workflow trust model, not a new sandbox claim; no new checkout/install action may be described as safe arbitrary-code isolation. Human review is required before secret-bearing dispatch.

Return mapping: `status` (`passed`, `failed`, `needs_review`), candidate/base SHAs, dataset/rubric/model configuration versions and hashes, per-case/per-repetition scores and critical failures, request/usage counts, import-origin checks and artifact paths. The existing entry accepts only status=passed. Preserve candidate_sha/workflow_sha/run_id/kind/config_version in record.json and add details references/hashes without removing existing evidence validation. Upload prompt/response/score details even on failure within credential-safe bounds. Output root is runner temporary storage, not tracked application results. Exceptions, wrong SHA/import origin/hash, missing modules/cases, empty output, budget overrun, truncation or unresolved review produce nonzero/no successful semantic record. No placeholder success, candidate self-attestation, reviewed-not-applicable shortcut for the feature prompt change, or automatic threshold relaxation.

## 6. PR 1 tests: concrete approval scope

These tests validate **preparation infrastructure**, not migrated feature behavior. Selected contract files are only `test/offline/test_ci_gates.py` and `test/offline/test_financial_metrics_evaluation.py`. PR 2 tests are deliberately not selected by this specification: the current checker extracts every project-relative test path from the approved plan and requires them all to exist/execute.

| Test group | Controlled inputs and expected assertions |
|---|---|
| P01 inventory/schema | Current registry plus the approved FR-10 object: schema passes; 14/65, active 7/37, deferred 7/28 exactly. Duplicate ID/FC and scope/status inconsistencies remain rejected. No invented historical approval. |
| P02 fixed material | Independently copied AAPL/XOM values above, fixed variant fact/timestamp edits; verify source hashes and projection pointers/types. Mutation of one number, period, reason or source hash fails. No import of candidate calculator in answer construction. |
| P03 runner status | Fake external model returns fixed correct reports: pass. Independently mutate each critical dimension (e.g. XOM fabricated margin; FCF quarterly label; FY P/E called TTM; missing comparison treated as zero): fail, even if average otherwise passes. Ambiguous target claim: needs_review/nonzero. Only scored candidate features affect feature threshold; retained-task regression vs baseline blocks. |
| P04 loading | Temporary candidate Git trees and synthetic modules: right SHA/origin accepted; different SHA, stale installed package, path escape or missing module rejected before external request. Feature-absent baseline accepted only in baseline mode. These synthetic loader tests are not product acceptance. |
| P05 execution completeness | Inject exception, timeout, rejected request, output truncation, missing case, skip, malformed runner mapping, unapproved config, absent runner/model credentials, hash mismatch and request overrun. Assert no success evidence; no retry; failure details retained; zero model calls for invalid prerequisites. Mock all external transport. |
| P06 trusted evidence | Existing trusted workflow/candidate separation, exact specification binding, non-author/non-bot human approval and time/ancestry tests remain. Add semantic secret handoff only to protected manual job, details artifact on failure, record details hash round-trip; ensure candidate score status cannot bypass entry's failure rule. |
| P07 no app migration | Diff contains no src/ change, no shared-summary import/config/state/node and no baseline rewrite. Run existing governance/authority/security regressions; report unrun/skipped separately. |

PR 2's separate plan will specify product tests for all FR-10 FCs, actual fiscal mapping (including January year end with one annual boundary), disclosure/price/basis/sign/n-a boundaries, first-turn/tool/wrap-up injection, single-analysis reuse and independent-run invalidation, both entry paths, disabled/omitted-analyst no-fetch, graph regression and semantic evaluation. Likely financial test leaves are `test_financial_metrics.py` and `test_sec_financial_provider.py`; do not implement them in this PR or carry over FR-08 assertions.

## 7. Commands, records and actual readiness

Working directory is the preparation root. Local application checks must follow main's installation and normal package discovery, not a PYTHONPATH/src or sys.path workaround. This planning task has not installed the new worktree into an environment; a suitable installation and CI-check dependencies are explicit prerequisites before application verification. After separately authorized setup, use main's installation command `python -m pip install -e ".[dev]" -r .github/requirements-ci.txt` in the approved environment (and its type-check constraints for that job), then verify actual imported package/module paths against this worktree before running application checks. Existing environments must not be assumed to import this checkout. Direct gate-script parser/document checks do not certify application discovery. Local bounded outputs: `C:/Users/24968/AppData/Local/Temp/opencode/financial-metrics-prep/`; CI outputs: RUNNER_TEMP and action artifacts. No background tasks, vendor/model calls or dependency installs are authorized by the planning task.

Initial planning checks: `git diff --check`; existing `scripts/ci_checks.py` parser/classifier functions against frozen plan; requirements schema check if installed. These are documentation/gate checks, not application verification. Record exact actual results in the planning log/final response; do not prefill passes.

Observed installation prerequisite at FM-PREP-2: `D:/CityU/cs5351/project/.venv/Scripts/python.exe` with normal `importlib.util.find_spec('tradingagents')` resolves to `D:/CityU/cs5351/project/tradingagents/__init__.py`, **not this worktree's src/**. This environment is not suitable evidence for this checkout's application tests until separately authorized installation/setup and import-origin verification. No package-path override or installation was performed.

Post-approval proposed verification commands (execution is not authorized yet):

```text
python scripts/ci_checks.py schema --requirements docs/req/requirements.yaml --schema docs/req/req-schema.json
python -m ruff check .
python -m pytest -q test/offline/test_ci_gates.py test/offline/test_financial_metrics_evaluation.py
python -m pytest -q
python scripts/ci_checks.py permissions --path .opencode/permissions.jsonc
python scripts/ci_checks.py api
python scripts/ci_checks.py mypy --output <bounded-output>/mypy-current.txt --baseline mypy-baseline.txt
python -m pip check
python scripts/ci_checks.py classify --base <PR-base-SHA> --head <candidate-SHA>
python scripts/ci_checks.py contract-tests --pr-body-file <bounded-output>/pr-body.txt --base <PR-base-SHA> --head <candidate-SHA>
```

Run existing PR CI/aggregate without weakening any gate. Full local regression may expose Windows/environment failures; reproduce against this round's baseline rather than reusing old branch failure exemptions. Missing dependencies are blocked, not passes. Dependency/install and multi-Python checks executed by existing CI are reported as CI results, not local runs. Maintain actual command/env/commit/test/input versions, expectations/results and evidence links in AI-use log and PR review memo. Pure preparation adds no runtime prompt, so its semantic applicability is determined by actual classification; do not fabricate semantic feature evidence merely to merge infrastructure. PR 2's analyst prompt change requires real fixed semantic evidence.

## 8. Real approval mechanism and stop points

Current checker: scripts/ci_checks.py `parse_approved_specification`, `approval_phrases`, `approval_check`, `verify_approval`, `contract_test_plan`. PR body after approval must contain:

```text
Plan: docs/plans/financial-metrics-integration.md
Approved test specification: docs/plans/financial-metrics-integration.md @ <FULL-FROZEN-SPEC-COMMIT-SHA>
Approval evidence: <real GitHub issuecomment or pullrequestreview URL>
Implementation start: <first code/test/governance-changing commit AFTER approval>
Approved scope: FR-10 FR-10-FC01 FR-10-FC02 FR-10-FC03 FR-10-FC04 FR-10-FC05 FR-10-FC06 FR-10-FC07 FR-10-FC08 FR-10-FC09 FR-10-FC10; PR 1 maintenance files and P01-P07 only
ADR: docs/architecture/adr/002-deterministic-financial-metrics.md
```

Until actual approval/start, fields must honestly say pending/not started; this documentation-only freeze is not the later implementation-start commit. Generate the suggested comment after freezing the commit, using exactly one line beginning `APPROVED test-spec:` with precisely the specification field value. This plan contains no fabricated approval event. The checker has no comment generator; use its actual parsers to validate the produced text and equality.

Approver must be a real human other than the PR author, not a bot. The event must be a COMMENTED/APPROVED review or an issue comment on this PR, contain exactly one matching approval phrase, and have a real GitHub creation time **strictly earlier** than the first implementation commit. The frozen spec commit must be its ancestor; materially changed expectations require a new freeze/approval. The checker also verifies changed IDs are covered, declared start is the first relevant commit, and every changed code path/test is named by the frozen specification. Do not backdate commits or treat an approval on old haoxi as this event. No reviewer name/time/URL is populated before it happens.

Ask the human reviewer (Yifan only when the user supplies the exact message) to confirm simultaneously: FR-10 ID/successor/scope and ten FCs; two-PR separation and no brief activation; source/cutoff/fiscal/basis/n-a policy; the ADR/module/authority/run-lifetime boundary including cross-analysis cache isolation; maximum maintenance allowlist and P01-P07 tests; the independent expectations/counterexamples/projection rules submitted together here, with lossless copying and verification proceeding after approval without a redundant gate; official deepseek-flash/thinking-disabled configuration, rubric/threshold and six-request proposal with no repetitions and separate execution authorization; normal installation/import verification prerequisites; permission/governance alignment and raw-session export process. A test-spec phrase alone does not grant merge, paid requests, application migration or change protected settings.

## 9. Preparation PR actual completion criteria (after approval)

1. Real fixed-version plan/test approval exists; affected requirements/ADR/evaluation decisions are explicitly confirmed, not inferred from a prior conversation.
2. D1 FR-10 and affected D2/D4/ownership/trace/counts are consistent; human-owned rule/permission discrepancies are resolved before dependent execution. Deferred brief remains unchanged.
3. Independent expectations/counterexamples/projection rules and rubric/config have real approval under this specification; the lossless fixed projection is copied, verified and hash-frozen before scorer implementation, with provenance recorded. Routine copying needs no second approval; material expectation/scoring/scope changes require affected-revision approval. No new acceptance is derived from old implementation output.
4. Trusted runner/config/details artifacts and tests are implemented within the allowlist, fail closed, and can be read by the default-branch workflow once merged. Missing candidate feature fails; fake-model unit tests do not imply model quality. No application migration is included.
5. Applicable existing CI/contract/regression/schema/lint/type/dependency/security/log gates actually pass, or blockers are reported and resolved by review rather than hidden; no placeholder-success job or changed threshold.
6. Actual review record, AI-use record and available raw-session references exist; no historical development is erased or relabeled as newly pre-approved.
7. Final human review and merge authorization occur separately. Only after this PR merges may PR 2 planning begin under a new explicit task; no automatic migration/merge.

**Current stop:** plan/Draft-PR submission only. Approval: pending; preparation implementation: not started; feature migration: not started; semantic execution: not run; final review/merge: not authorized.
