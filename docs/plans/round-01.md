# Round 01 — Deterministic Portfolio Risk Core

## 1. Status and source baseline

Status: proposed execution and test specification for human review. The user requested writing this plan after checking its scope; this is not approval to implement the application or evidence that these tests passed. No application/test file is created by this plan.

Sources: [D1 v1.48.0](../req/requirements.yaml), [blueprint §8.4 and IF-08/IF-25](../../architecture-blueprint.md), [ADR 001 D-11/D-12/D-12a](../architecture/adr/001-graph-internal-final-check.md), [IR-14](../architecture/invariants.md), [trace matrix](../architecture/trace-matrix.md), [D4 V-FR04-01–04](../code-governance/verification-constraints.md), [structural constraints](../code-governance/structural-constraints.md), and project AGENTS/rules. Read the actual source artifacts before implementation; their Proposed status is not blanket approval.

## 2. Scope and exclusions

Implement C-08, a pure evaluator of the caller's single-stock purchase/add-long scenario. Target FR-04-FC01–FC04 and the corresponding core portion of IR-14. FC05 and the entry/graph/report portion of IR-14 remain unimplemented and unaccepted after this round. No whole-FR-04 completion claim is allowed.

Exclude CLI/file input, propagate signature changes, graph wiring/state integration, report/HTML rendering, SB-01, availability, RunContext/statistics, manifests, history, memory and checkpoint changes. Do not activate FR-06/FR-07/PR-01/CR-01. Do not add account/cash verification, FX, broker/order execution, financial-policy approval, hashes, evidence files, dependencies, or generic parsing/security frameworks.

## 3. Exact development scope

After implementation/test approval, only these application/test files may be created or changed:

- `src/tradingagents/portfolio_risk.py`: C-08 and small local helpers.
- `test/offline/test_fr04_risk.py`: offline core tests.

Read-only inputs include D1/D2/D3/D4, `src/tradingagents/dataflows/symbols.py`, relevant existing tests and `pyproject.toml`. Reuse the existing pure `normalize_symbol` rather than adding ticker rules. Do not change `portfolio.py`: its PortfolioContext is not an authoritative scenario source.

This plan's creation authorizes neither those code writes nor governance edits. Permission/rule changes, logging/transcript output files, and commands must be separately made available through the approved round setup; do not invent output locations. This file may be updated only within an explicitly authorized planning/approval-record task.

## 4. Interface and behavior

Use IF-08: `PortfolioRiskEvaluator.evaluate(analysis_ticker, proposal, scenario, thresholds, asset_type)` or its equally small implementation consistent with the approved D2 ownership. Do not add a second public API. Before coding, fix any necessary call-shape detail in the submitted test specification; do not infer a new entry API.

Inputs are explicit, not global. Proposal uses D2's rating/text mapping or null; rating determines applicability, while proposal prose and numbers never fill/override scenario values. Check legal rating, then applicability, then applicable scenario/threshold validation and exact calculation. Legal stock Hold/Underweight/Sell and legal non-stock ratings return not_applicable without requiring a scenario. Missing/illegal rating is blocked; applicable missing/invalid scenario is blocked; unexpected evaluator exception is error. Invalid business input must not escape as an analysis-hard-failure exception.

Scenario fields: ticker, portfolio_value > 0, 0 <= current_position_value <= portfolio_value, proposed_buy_value > 0, entry_price > 0, 0 < stop_loss_price < entry_price, and a non-empty common currency label. Reject bool, non-finite, missing and unparseable numeric values. Follow D2 number conversion for integers, ordinary decimal strings, Decimal and finite float. A finite float means its stable decimal string, not restoration of precision lost by its caller. JSON file token parsing is excluded with entry transport.

Default omitted thresholds: max_projected_weight=0.30 and max_stop_distance=0.05. Legal configured values satisfy 0 < weight_limit <= 1 and 0 < stop_limit < 1. Explicit invalid values do not fall back.

Compare exactly before display formatting:

- current_position_value + proposed_buy_value <= max_projected_weight * portfolio_value
- entry_price - stop_loss_price <= max_stop_distance * entry_price

Use local standard-library exact rational arithmetic as designed; no global Decimal-context change. Equality passes; either breach blocks; retain both reasons for a double breach.

Result follows D2: status, analysis_ticker, safe scenario, valid actually-used thresholds, projected_weight/stop_distance as decimal strings or null, and risk-scoped reasons. Preserve the classroom-demonstration/non-authorization semantics and actual manual-review meaning for blocked/error without adding a renderer or mandating new result keys or exact notice wording. Do not return formal recommendation fields. Each metric's nullability follows its own valid arithmetic operands; unrelated ticker/currency/threshold errors do not clear valid metrics. Omit unsafe raw values rather than stringify arbitrary objects. Repeating quotients are computable, not null; their display precision is not an acceptance threshold.

## 5. Complete offline test specification

All scenarios start with fixture B unless overridden: analysis_ticker=`AAPL`, asset_type=`stock`, proposal={rating:`Buy`, text:`caller scenario only`}, scenario={ticker:`AAPL`, portfolio_value:`100000`, current_position_value:`0`, proposed_buy_value:`30000`, entry_price:`100`, stop_loss_price:`95`, currency:`USD`}, omitted thresholds. Other required inputs remain legal when testing one negative. Compute or hand-record expected results independently, never using evaluator helpers as the oracle.

| ID / trace | Controlled input | Required assertions |
|---|---|---|
| R01-01 / FC01, IR-14 | B | passed; terminating metrics numerically 0.30 and 0.05; accurate safe input and default thresholds |
| R01-02 / FC01, IR-14 | buy=20000, stop=96; then concentration equality alone (buy=30000, stop=96); then stop equality alone (buy=20000, stop=95) | below/equal limits pass independently; metrics match independent decimal/fraction expectations |
| R01-03 / FC01, IR-14 | thresholds 0.40/0.10, buy=40000, stop=90 | equality passes with actual configured thresholds; same scenario under defaults blocks, demonstrating config is honored |
| R01-04 / FC02, IR-14 | buy=30001 only; stop=94 only; then both | blocked with the corresponding concentration/stop reason; both reasons retained for double breach; no new reason-priority protocol |
| R01-05 / FC02, IR-14 | buy=30000.01, other B values | exact weight=0.3000001 breaches 0.30 and blocks even if a normal display would appear equal; do not require a particular formatting precision |
| R01-06 / FC03, IR-14 | remove each required scenario field in turn; ticker=MSFT | blocked with applicable missing/mismatch category; no model/context/network fill; no unhandled exception |
| R01-07 / FC03, IR-14 | portfolio 0/-1; position -1/100001; buy 0/-1; entry 0/-1; stop 0/-1/100/101; currency empty or absent | blocked with relevant field/category; no division error; do not create currency-code validation or FX rules |
| R01-08 / FC03, IR-14 | representative numeric bool, NaN, +Infinity, -Infinity and unparseable string; distribute across parser paths without a full Cartesian product | blocked, never silently zero/default-filled; no unsafe raw diagnostic |
| R01-09 / FC03, IR-14 | weight limit 0/negative/>1/bool/non-finite/unparseable; stop limit 0/negative/1/>1/bool/non-finite/unparseable | blocked, explicit invalid config never replaced by defaults; weight limit=1 is separately legal, stop limit=1 illegal |
| R01-10 / FC03, IR-14 | buy invalid but entry/stop legal; stop invalid but concentration operands legal; currency/ticker/threshold invalid with legal arithmetic operands | only affected arithmetic metric null; unaffected metric retained; non-arithmetic failure does not clear both; overall blocked |
| R01-11 / FC01/FC03, IR-14 | equivalent ordinary integer/string/Decimal/finite-float inputs; normalized ticker ` aapl `; legal repeating weight such as portfolio=3, position=0, buy=1 with limit=0.4 | equivalent supplied decimal values produce same decision; existing normalization reused; JSON-compatible result; repeating quotient remains non-null without demanding exact finite decimal equality to 1/3 |
| R01-12 / FC04, IR-14 | stock Buy and Overweight; stock Hold/Underweight/Sell with absent scenario; existing legal crypto case with each representative legal rating | stock Buy/Overweight evaluate; other legal non-applicable cases return not_applicable and do not require unused scenario validation |
| R01-13 / FC04, IR-14 | absent/illegal rating; applicable missing scenario; proposal claims approval or provides different numbers | invalid rating/applicable missing scenario blocked; valid scenario outcome unchanged by prose; no formal result generated |
| R01-14 / FC04, IR-14 | inject one controlled unexpected failure into a narrow internal evaluation boundary after ordinary invalid-input validation | complete error result with safe reason, never passed; no escaping exception or raw traceback; fault injection need not be a production hook |
| R01-15 / FC01–04, IR-14 | representative passed/blocked/not_applicable/error results; malformed raw object with distinctive unsafe string conversion; snapshot caller inputs | standard JSON serialization succeeds without default=str; no Decimal/Fraction in outputs; no unsafe raw echo; input data not mutated; no formal gate/rating fields introduced |

FC identifiers in this table abbreviate FR-04-FCnn. Actual tests cite full IDs and IR-14. Parameterized/shared tests are encouraged. Do not equate exact internal decision arithmetic with an exact finite representation for a repeating displayed quotient. Do not assert byte-identical decimal strings, fixed decimal places, exact prose, helper names, class counts, or one test function per row.

Verify purity by narrow static inspection and, where useful, a dependency sentinel: no model, vendor, file save or hidden scenario lookup. Do not forbid normal imports/stdlib use, add exhaustive filesystem interception, or accidentally count pytest's own I/O as evaluator side effects. Relevant boundary/negative tests must fail if comparisons are relaxed, invalid thresholds defaulted, or model text replaces scenario input; no mutation-testing platform is required.

## 6. Verification and execution sequence

1. Human reviews this exact scope/interface and specific test expectations; record the actual approval/version before application implementation.
2. Human-maintained round setup enables only the declared code/test paths, commands and bounded outputs. Do not self-edit permission controls.
3. Write approved tests, then the narrow evaluator and local helpers. Preserve existing baseline files. Reference relevant ADR decisions/IR-14 in changed code and tests.
4. Run targeted offline behavior, inspect structural boundaries, then run the prior applicable offline regression suite. Return defects to implementation, preserving approved expectations.
5. Deliver actual evidence and residual limitations; do not mark FC05 or full FR-04 complete.

Proposed commands, subject to environment/permission approval, from the project root:

- `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider test/offline/test_fr04_risk.py`
- `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider`
- `ruff check --no-cache src/tradingagents/portfolio_risk.py test/offline/test_fr04_risk.py`

Use the existing suitable interpreter/environment, not an installation or upgrade. Default pytest excludes integration. A default suite pass is not a live/API-quality pass. No live tests are required here. Pytest temporary roots and any additional existing-suite output must be explicitly assigned a project-local location before execution; inspect relevant fixtures before approving command side effects. Record missing dependencies, skipped tests and baseline failures honestly; do not silently exempt failures or weaken regression. This plan does not authorize the commands until round approval and permissions agree.

Structural evidence: exact changed-file scope, relevant ADR/IR references, pure evaluator boundary, JSON-safe projection and no formal-authority writes. Behavioral evidence: table above. Regression evidence: prior applicable offline suite and actual failures/skips. Reuse evidence across FCs rather than creating redundant checks.

## 7. Preconditions and unresolved items

D1's scenario formulas, applicability and demonstration defaults are specified; OQ-02 fixes the two threshold key names. This plan proposes implementing those established contracts, not a new financial policy. OQ-01/04 do not block the isolated core because entry/file transport and CLI save/display are excluded. OQ-08/12/13/15/16 concern later integrations and are not resolved here. OQ-07, selected role, exact command/output permissions, and actual permission loading require human setup before execution.

D2/structural owner and relevant safety-critical ADR use require approval for this scoped implementation. The tests' actual callable detail must match IF-08; do not create an unapproved alternative API. Existing AGENTS, rules and D4 remain binding. Missing startup/AI-use/session-record/CI prerequisites must be reported and addressed through authorized governance work; do not create those files within the two-file application scope. Applicable merge gates remain mandatory; this round has no push/PR/merge grant.

## 8. Approval and completion record

| Item | Current state |
|---|---|
| Scope/specification | Proposed for review; this file was requested, not application implementation |
| Plan version | Draft 1; approval must bind to this exact content or a later explicit revision/commit |
| Specific test approval | Pending; no approver or approval time recorded |
| Safety-critical ADR/implementation approval | Pending for this round |
| Permission/environment/output readiness | Pending verification and scoped setup |
| Test execution / results | Not run; no application/test code written by this planning task |
| FC01–FC04 completion | Not established |
| FC05 / full FR-04 / integrated IR-14 | Excluded and not accepted |

After real approval, record its time, approved content/version, scope, and evidence location through an authorized plan update. Reconfirm affected approval only if expectations, interfaces or scope change; unrelated approved work needs no repeated approval. Completion requires the approved core assertions and applicable regression/structural checks to pass with actual evidence. Environment blocks and skips are not passes, and no risk pass is trade authorization.
