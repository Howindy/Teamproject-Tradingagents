# Round 01 — Deterministic Portfolio Risk Core

## 1. Status and source baseline

Status: proposed execution and test specification for human review. The user requested writing this plan after checking its scope; this is not approval to implement the application or evidence that these tests passed. No application/test file is created by this plan.

Current working baseline: `31bcf7808c7a471c581ae49c06d1352802235d90` on branch `round-01-portfolio-risk`. The historical `pre-round1-baseline-20261121` tag remains an earlier historical snapshot and is not moved or re-pointed by this plan. This revision is Draft 2; it is still an unapproved specification. The CI implementation and PR #6 approvals are not approvals of this round.

Sources: [D1 v1.48.0](../req/requirements.yaml), [blueprint §8.4 and IF-08/IF-25](../../architecture-blueprint.md), [ADR 001 D-11/D-12/D-12a](../architecture/adr/001-graph-internal-final-check.md), [IR-14](../architecture/invariants.md), [trace matrix](../architecture/trace-matrix.md), [D4 V-FR04-01–04](../code-governance/verification-constraints.md), [structural constraints](../code-governance/structural-constraints.md), and project AGENTS/rules. Read the actual source artifacts before implementation; their Proposed status is not blanket approval.

## 2. Scope and exclusions

Implement C-08, a pure evaluator of the caller's single-stock purchase/add-long scenario. Target FR-04-FC01–FC04 and the corresponding core portion of IR-14. FC05 and the entry/graph/report portion of IR-14 remain unimplemented and unaccepted after this round. No whole-FR-04 completion claim is allowed.

Exclude CLI/file input, propagate signature changes, graph wiring/state integration, report/HTML rendering, SB-01, availability, RunContext/statistics, manifests, history, memory and checkpoint changes. Do not activate FR-06/FR-07/PR-01/CR-01. Do not add account/cash verification, FX, broker/order execution, financial-policy approval, hashes, evidence files, dependencies, or generic parsing/security frameworks.

## 3. Exact development scope

After implementation/test approval, only these application/test files may be created or changed:

- `src/tradingagents/portfolio_risk.py`: C-08 and small local helpers.
- `test/offline/test_fr04_risk.py`: offline core tests.

Read-only inputs include D1/D2/D3/D4, `src/tradingagents/dataflows/symbols.py`, the existing five-tier vocabulary in `src/tradingagents/agents/rating.py`, relevant existing tests, `test/conftest.py` and `pyproject.toml`. Reuse the existing pure `normalize_symbol` rather than adding ticker rules; the five legal proposal ratings are Buy, Overweight, Hold, Underweight and Sell, with `REVIEW` not a legal proposal rating. Do not change `portfolio.py`: its PortfolioContext is not an authoritative scenario source.

This plan's creation authorizes neither those code writes nor governance edits. Permission/rule changes, logging/transcript output files, and commands must be separately made available through the approved round setup; do not invent output locations. This file may be updated only within an explicitly authorized planning/approval-record task.

## 4. Interface and behavior

Use IF-08 through one small callable in `src/tradingagents/portfolio_risk.py`:

```text
evaluate(analysis_ticker, proposal, scenario, thresholds, asset_type)
```

The parameter order and names are fixed; callers may pass them positionally in this order or by keyword. Threshold input follows the confirmed per-key omission rule: `thresholds=None` or `{}` uses both defaults; a missing key uses its default; a valid provided key uses its value; an explicitly provided invalid value blocks without falling back for that key. The test specification passes the mapping explicitly; omitting the argument is not relied on. This is the only public risk API; do not add a second entry, a required DTO, or a class/service split that D-12a/IF-25 do not require.

Inputs are explicit, not global:

| Parameter | Accepted form and omitted value |
|---|---|
| `analysis_ticker` | The explicit current analysis ticker string. Matching uses the existing pure `normalize_symbol`; no network identity lookup or inference from scenario/model text. |
| `proposal` | A mapping with `rating` and `text` keys (values may be `None`), or `None`. `rating` determines applicability; `text` is advisory, does not participate in risk calculation, and missing/empty/`None` text alone does not block. |
| `scenario` | A mapping with the seven scenario keys below, or `None` for an omitted scenario. |
| `thresholds` | A mapping that may contain `max_projected_weight` and `max_stop_distance`, or `None`/`{}` for both defaults. A missing key uses that key's default; a valid provided key uses its value; an explicitly invalid provided value blocks without falling back for that key. |
| `asset_type` | The asset-type string; `stock` is the only applicable case for the core. |

Check legal rating, then applicability, then applicable scenario/threshold validation and exact calculation. Legal stock Hold/Underweight/Sell and legal non-stock ratings return `not_applicable` without requiring a scenario (tests may pass `scenario=None`); unused scenario data is not validated. Missing/illegal rating is `blocked`; an applicable stock Buy/Overweight with `scenario=None` or a missing/invalid field is `blocked`; unexpected evaluator exception is `error`. Invalid business input must not escape as an analysis-hard-failure exception. A missing `proposal` or a proposal whose `rating` is missing, `REVIEW`, or not one of the five legal values is a missing/illegal rating case, not a scenario-validation case.

Scenario fields: ticker, portfolio_value > 0, 0 <= current_position_value <= portfolio_value, proposed_buy_value > 0, entry_price > 0, 0 < stop_loss_price < entry_price, and a non-empty common currency label. Reject bool, non-finite, missing and unparseable numeric values. Follow D2 number conversion for integers, ordinary decimal strings, Decimal and finite float. A finite float means its stable decimal string, not restoration of precision lost by its caller. JSON file token parsing is excluded with entry transport.

Confirmed by the user for this draft, the per-key threshold rule is:

| Threshold input | Behavior |
|---|---|
| `thresholds=None` or `{}` | Both defaults: max_projected_weight=0.30, max_stop_distance=0.05. |
| `max_projected_weight` missing | Use 0.30; other provided valid values remain in force. |
| `max_stop_distance` missing | Use 0.05; other provided valid values remain in force. |
| A key provided with a legal value | Use that actual value. |
| A key explicitly provided as invalid (`None`, bool, non-finite, unparseable, or outside its legal range) | Blocked; that key does not fall back to its default. |

Legal ranges remain 0 < max_projected_weight <= 1 and 0 < max_stop_distance < 1. A missing key is distinguished from an explicitly provided invalid value. This confirmed execution rule does not approve the plan, tests, ADR, or implementation.

Compare exactly before display formatting:

- current_position_value + proposed_buy_value <= max_projected_weight * portfolio_value
- entry_price - stop_loss_price <= max_stop_distance * entry_price

Use local standard-library exact rational arithmetic as designed; no global Decimal-context change. Equality passes; either breach blocks; retain both reasons for a double breach.

Result follows D2: status, analysis_ticker, safe scenario, valid actually-used thresholds, projected_weight/stop_distance as decimal strings or null, and risk-scoped reasons. Preserve the classroom-demonstration/non-authorization semantics and actual manual-review meaning for blocked/error without adding a renderer or mandating new result keys or exact notice wording. Do not return formal recommendation fields. Each metric's nullability follows its own valid arithmetic operands; unrelated ticker/currency/threshold errors do not clear valid metrics. Omit unsafe raw values rather than stringify arbitrary objects. Repeating quotients are computable, not null; their display precision is not an acceptance threshold.

The return value is one plain JSON-compatible mapping. Required keys and meanings:

| Key | Meaning |
|---|---|
| `status` | One of `passed`, `blocked`, `not_applicable`, `error`. |
| `analysis_ticker` | The explicit analysis ticker argument as supplied; not a network-resolved identity. |
| `scenario` | Display-safe mapping of the scenario fields that were safely parsable; numeric values are decimal strings; unsafe/invalid raw values are omitted and the mapping may be empty. |
| `thresholds` | Display-safe mapping of only the valid threshold values actually used, as decimal strings; it may be empty when none are valid. The actual returned risk result must carry the classroom-demonstration/non-trade-authorization semantics; this is not merely a statement in the specification. It does not require a new specific result field, fixed wording, renderer, or display component. |
| `projected_weight`, `stop_distance` | Decimal strings when their own arithmetic operands are legal, otherwise `None`. |
| `reasons` | A list of short risk-scoped strings; blocked/error cases include at least one actual reason. |

C-08 does not generate the formal fields `gate_status`, `final_rating`, or `final_trade_decision`, and does not introduce SB-01 conclusion-text validation or formal-conclusion parsing. `model_proposal` is advisory and is not a formal-authority field; the risk result need not return it, and tests do not assert its absence or require an exact key-set match. The listed risk keys are required; tests do not require additional keys, exact key-set equality, exact decimal formatting, or exact notice wording. No `Decimal`/`Fraction` objects appear in the result.

## 5. Complete offline test specification

All scenarios call `evaluate(analysis_ticker=..., proposal=..., scenario=..., thresholds=..., asset_type=...)` with fixture B unless overridden: analysis_ticker=`AAPL`, asset_type=`stock`, proposal={rating:`Buy`, text:`caller scenario only`}, scenario={ticker:`AAPL`, portfolio_value:`100000`, current_position_value:`0`, proposed_buy_value:`30000`, entry_price:`100`, stop_loss_price:`95`, currency:`USD`}, and `thresholds=None` (whole threshold configuration omitted). Other required inputs remain legal when testing one negative. Compute or hand-record expected results independently, never using evaluator helpers as the oracle.

| ID / trace | Controlled input | Required assertions |
|---|---|---|
| R01-01 / FC01, IR-14 | B | passed; terminating metrics numerically 0.30 and 0.05; accurate safe input and default thresholds |
| R01-02 / FC01, IR-14 | buy=20000, stop=96; then concentration equality alone (buy=30000, stop=96); then stop equality alone (buy=20000, stop=95) | below/equal limits pass independently; metrics match independent decimal/fraction expectations |
| R01-03 / FC01, IR-14 | thresholds 0.40/0.10, buy=40000, stop=90 | equality passes with actual configured thresholds; same scenario under defaults blocks, demonstrating config is honored |
| R01-04 / FC02, IR-14 | buy=30001 only; stop=94 only; then both | blocked with the corresponding concentration/stop reason; both reasons retained for double breach; no new reason-priority protocol |
| R01-05 / FC02, IR-14 | (a) buy=30000.01, other B values; (b) `portfolio_value="10"`, `current_position_value="0"`, `proposed_buy_value="3.0000000000000001"`, `entry_price="100"`, `stop_loss_price="95"`, thresholds={`max_projected_weight:"0.3"`, `max_stop_distance:"0.05"`}; other fixture-B inputs legal | (a) exact weight=0.3000001 breaches 0.30 and blocks even if a normal display would appear equal; (b) exact weight is greater than 0.3 and status=blocked; this deliberately uses decimal strings, so the evaluator must not receive a float already rounded to 3.0 and be expected to recover lost precision; do not require a particular formatting precision or a new precision platform |
| R01-06 / FC03, IR-14 | remove each required scenario field in turn; `scenario=None`; ticker=MSFT | blocked with applicable missing/mismatch category; no model/context/network fill; no unhandled exception |
| R01-07 / FC03, IR-14 | portfolio 0/-1; position -1/100001; buy 0/-1; entry 0/-1; stop 0/-1/100/101; currency empty or absent | blocked with relevant field/category; no division error; do not create currency-code validation or FX rules |
| R01-08 / FC03, IR-14 | representative numeric bool, NaN, +Infinity, -Infinity and unparseable string; distribute across parser paths without a full Cartesian product | blocked, never silently zero/default-filled; no unsafe raw diagnostic |
| R01-09 / FC03, IR-14 | `thresholds=None`; `thresholds={}`; only a legal `max_projected_weight` (0.4); only a legal `max_stop_distance` (0.1); each key explicitly invalid as 0/negative/>1/`None`/bool/non-finite/unparseable; stop limit=1; weight limit=1 | `None` and `{}` use both defaults; with fixture B, the only-weight 0.4 and only-stop 0.1 cases pass while the missing key uses its default; an explicit invalid value blocks and that key does not fall back; weight limit=1 is legal; stop limit=1 is illegal |
| R01-10 / FC03, IR-14 | buy invalid but entry/stop legal; stop invalid but concentration operands legal; currency/ticker/threshold invalid with legal arithmetic operands | only affected arithmetic metric null; unaffected metric retained; non-arithmetic failure does not clear both; overall blocked |
| R01-11 / FC01/FC03, IR-14 | equivalent ordinary integer/string/Decimal/finite-float inputs; normalized ticker ` aapl `; legal repeating weight such as portfolio=3, position=0, buy=1 with limit=0.4 | equivalent supplied decimal values produce same decision; existing normalization reused; JSON-compatible result; repeating quotient remains non-null without demanding exact finite decimal equality to 1/3 |
| R01-12 / FC04, IR-14 | stock Buy and Overweight; stock Hold/Underweight/Sell with `scenario=None`; existing legal crypto case with each representative legal rating and `scenario=None` | stock Buy/Overweight evaluate; other legal non-applicable cases return not_applicable and do not require unused scenario validation |
| R01-13 / FC04, IR-14 | `proposal=None`, missing rating, `REVIEW`, and an unknown rating string; applicable `scenario=None`; proposal claims approval or provides different numbers | invalid rating/applicable missing scenario blocked; valid scenario outcome unchanged by prose; no formal result generated |
| R01-14 / FC04, IR-14 | inject one controlled unexpected failure into a narrow internal evaluation boundary after ordinary invalid-input validation | complete error result with safe reason, never passed; no escaping exception or raw traceback; fault injection need not be a production hook |
| R01-15 / FC01–04, IR-14 | representative passed/blocked/not_applicable/error results; malformed raw object with distinctive unsafe string conversion; snapshot caller inputs | standard JSON serialization succeeds without default=str; no Decimal/Fraction in outputs; no unsafe raw echo; input data not mutated; no `gate_status`, `final_rating`, or `final_trade_decision` formal fields generated; no exact key-set equality or `model_proposal` absence assertion required |

FC identifiers in this table abbreviate FR-04-FCnn. Actual tests cite full IDs and IR-14. Parameterized/shared tests are encouraged. Do not equate exact internal decision arithmetic with an exact finite representation for a repeating displayed quotient. Do not assert byte-identical decimal strings, fixed decimal places, exact prose, helper names, class counts, or one test function per row.

This specification uses R01-05(b) to verify the existing exact-arithmetic boundary; it does not add other precision cases or new guarantees. R01-09 covers empty/partial threshold mappings and per-key defaults.

Verify purity by narrow static inspection and, where useful, a dependency sentinel: no model, vendor, file save or hidden scenario lookup. Do not forbid normal imports/stdlib use, add exhaustive filesystem interception, or accidentally count pytest's own I/O as evaluator side effects. Relevant boundary/negative tests must fail if comparisons are relaxed, invalid thresholds defaulted, or model text replaces scenario input; no mutation-testing platform is required.

## 6. Verification and execution sequence

1. Human reviews this exact scope/interface and specific test expectations; record the actual approval/version before application implementation.
2. Human-maintained round setup enables only the declared code/test paths, commands and bounded outputs. Do not self-edit permission controls.
3. Write approved tests, then the narrow evaluator and local helpers. Preserve existing baseline files. Reference relevant ADR decisions/IR-14 in changed code and tests.
4. Run targeted offline behavior, inspect structural boundaries, then run the prior applicable offline regression suite. Return defects to implementation, preserving approved expectations.
5. Deliver actual evidence and residual limitations; do not mark FC05 or full FR-04 complete.

The round's contract-test selection is exactly `test/offline/test_fr04_risk.py`. CI reads the approved specification at commit P, extracts `test/offline/...py` paths from that committed text, and requires each changed code path to be named. The specification must name both implementation paths; do not add unrelated test paths, and the PR's existing contract-tests job remains the gate.

Proposed commands, subject to environment/permission approval, from the project root:

- `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider test/offline/test_fr04_risk.py`
- `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider`
- `ruff check --no-cache src/tradingagents/portfolio_risk.py test/offline/test_fr04_risk.py`

Use the existing suitable interpreter/environment, not an installation or upgrade. Default pytest excludes integration. A default suite pass is not a live/API-quality pass. No live tests are required here. Pytest temporary roots and any additional existing-suite output must be explicitly assigned a project-local location before execution; inspect relevant fixtures before approving command side effects. Record missing dependencies, skipped tests and baseline failures honestly; do not silently exempt failures or weaken regression. This plan does not authorize the commands until round approval and permissions agree.

The local checks above are development feedback; the PR's existing CI remains the gate. When applicable and authorized, retain the existing D4/CI checks for requirements schema, full Ruff, type-check against `mypy-baseline.txt`, dependency/import consistency, permissions, API surface, and the CI-selected security and contract tests. Do not redefine thresholds or duplicate these checks as separate acceptance; local results do not replace the PR `aggregate`. Do not expand `mypy-baseline.txt`, lower dependency requirements, or weaken existing assertions.

Before executing any command, confirm the existing interpreter and editable/installed package resolve `tradingagents` to this checkout; `test/conftest.py` blanks `TRADINGAGENTS_*` settings and redirects results, cache, memory and time-zone caches to temporary directories; and any extra captured output uses an authorized bounded project-local location such as `tmp/round-01/`. Use that location only for captured command output, not source/test files. This plan does not create it, modify `.gitignore`, install or upgrade packages, or commit generated output. The listed pytest commands disable bytecode and pytest cache; any additional command must state equivalent bytecode/cache bounds. Default pytest excludes integration; no live test is required for this core. Whether a formal semantic-evidence run is required is determined by the final diff and CI classification, not pre-claimed here; this plan adds no extra evaluation obligation.

### 6.1 Records and evidence

`docs/ai-use-log.yaml` and `docs/review-memo.md` are existing records that require separate explicit authorization; this plan does not grant write permission. `transcripts/` continues the existing raw-session process; the actual export file is determined by the real session and authorized task, and student annotations may use the existing commit method without a separate annotations file. No new validation directory, approval file, or round-summary file is a required deliverable; evidence can be tracked through the review memo, CI links, and authorized raw output. `docs/bug-diary.md` and `docs/debt-register.md` are updated only if a corresponding event occurs and the path is authorized; do not fill templates with invented items. The two-file implementation permission is separate from any record-write permission; listing a path here does not authorize writing it.

Structural evidence: exact changed-file scope, relevant ADR/IR references, pure evaluator boundary, JSON-safe projection and no formal-authority writes. Behavioral evidence: table above. Regression evidence: prior applicable offline suite and actual failures/skips. Reuse evidence across FCs rather than creating redundant checks.

## 7. Preconditions and unresolved items

D1's scenario formulas, applicability and demonstration defaults are specified; OQ-02 fixes the two threshold key names. This plan proposes implementing those established contracts, not a new financial policy. OQ-01/04 do not block the isolated core because entry/file transport and CLI save/display are excluded. OQ-08/12/13/15/16 concern later integrations and are not resolved here. OQ-07, selected role, exact command/output permissions, and actual permission loading require human setup before execution.

The user-confirmed per-key threshold rule is an execution decision recorded in this plan; it does not approve the plan, tests, ADR, or implementation, and it does not close unrelated OQs.

D2/structural owner and relevant safety-critical ADR use require approval for this scoped implementation. Because `src/tradingagents/portfolio_risk.py` is safety-critical, the implementation PR must include the real applicable `ADR:` reference and human approval; this plan supplies neither. The tests' actual callable detail must match IF-08; do not create an unapproved alternative API. Existing AGENTS, rules and D4 remain binding. `.opencode/permissions.jsonc` still requires explicit loading and a human-maintained round configuration; this plan does not claim effective enforcement. Missing startup/AI-use/session-record/CI prerequisites must be reported and addressed through authorized governance work; do not create those files within the two-file application scope. Applicable merge gates remain mandatory; this round has no push/PR/merge grant.

After this Draft 2 is reviewed, the sequence is: final specification commit P → real non-author human pre-approval in the same PR → permissions/environment readiness → tests and implementation → verification and authorized records → PR gates and applicable evidence → final human review → authorized merge. T is the first implementation commit; H is the current candidate. Do not modify the approved specification to fill status or results; material scope, interface or expectation changes require reapproval of the affected version. Permission/CI maintenance is a separate prerequisite task and must not be mixed into this two-file implementation.

## 8. Approval and completion record

| Item | Current state |
|---|---|
| Scope/specification | Proposed for review; this file was requested, not application implementation |
| Working baseline | `31bcf7808c7a471c581ae49c06d1352802235d90` on `round-01-portfolio-risk`; historical tag remains earlier |
| Plan version | Draft 2; approval must bind to this exact content or a later explicit revision/commit |
| Specific test approval | Pending; no approver or approval time recorded |
| Safety-critical ADR/implementation approval | Pending for this round |
| Permission/environment/output readiness | Pending verification and scoped setup |
| Test execution / results | Not run; no application/test code written by this planning task |
| FC01–FC04 completion | Not established |
| FC05 / full FR-04 / integrated IR-14 | Excluded and not accepted |

After real approval, record its time, approved content/version, scope, and evidence location in the same PR or an explicitly authorized existing record. Keep the approved specification unchanged; do not update it to fill approval status or execution results. Reconfirm affected approval only if expectations, interfaces or scope change; unrelated approved work needs no repeated approval. Completion requires the approved core assertions and applicable regression/structural checks to pass with actual evidence. Environment blocks and skips are not passes, and no risk pass is trade authorization.
