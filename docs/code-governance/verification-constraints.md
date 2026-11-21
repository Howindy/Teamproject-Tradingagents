# D4 Verification Constraints and Test Design

- Document status: Verification governance rules and test design, not a test execution report, acceptance proof, or permission-enforcement proof.
- Requirements baseline: [`docs/req/requirements.yaml`](../req/requirements.yaml) v1.48.0, independently verified as 13 requirements and 55 fit criteria: 9 active requirements with 40 FCs and 4 deferred requirements with 15 FCs.
- Structural schema: [`docs/req/req-schema.json`](../req/req-schema.json).
- Architecture baseline: [`architecture-blueprint.md`](../../architecture-blueprint.md) and [`ADR 001`](../architecture/adr/001-graph-internal-final-check.md).
- D2 cross-check inputs: [`invariants.md`](../architecture/invariants.md), [`trace-matrix.md`](../architecture/trace-matrix.md), [`runtime-policy-catalog.md`](../architecture/runtime-policy-catalog.md), [`memory-design.md`](../architecture/memory-design.md), [`permission-model.md`](../architecture/permission-model.md), and [`evaluation-table.md`](../architecture/evaluation-table.md).
- Engineering layout: [`pyproject.toml`](../../pyproject.toml), [`test/conftest.py`](../../test/conftest.py), and the [`CI workflow`](../../.github/workflows/ci.yml).
- This document is written in English. `V-*` identifiers are design-time verification intents, not existing test functions, test files, or execution results.

## 1. Scope, Baseline, and Exclusions

### 1.1 Active Scope

Active requirements: FR-01, FR-02, FR-03, FR-04, FR-05, SB-01, INV-01, SR-01, and SR-02, containing 40 FCs. Every active FC has at least one verification intent in Section 2. A complex FC may contain multiple parameterized scenarios under one intent.

### 1.2 Deferred Scope

| Requirement | Deferred FCs | Current Treatment |
|---|---|---|
| FR-06 | FR-06-FC01, FR-06-FC02, FR-06-FC03, FR-06-FC04, FR-06-FC05 | Not implemented, executed, or counted as passing; no recovery interface or test file is reserved |
| FR-07 | FR-07-FC01, FR-07-FC02, FR-07-FC03, FR-07-FC04, FR-07-FC05 | Brief replacement, character limits, and five-role replacement are not current acceptance |
| PR-01 | PR-01-FC01, PR-01-FC02 | No current manifest-performance measurement or threshold |
| CR-01 | CR-01-FC01, CR-01-FC02, CR-01-FC03 | No current usage/cost comparison or cost/quality target |

These FCs remain future conditions; this treatment is not a claim that the course explicitly exempts them. Activation requires a new requirements decision, reopening the affected D2 decisions, specific test approval, and implementation. Future FCs are never counted as current passes.

### 1.3 Document Boundaries

- This document adds no requirement, FC, IR, runtime policy, performance/cost/quality threshold, or monitoring platform.
- D2 `Proposed`, `Planned`, and `Pending verification` states remain unapproved, unimplemented, or unverified.
- Existing test files prove only that baseline assets exist; no new D2 acceptance has been executed or passed.
- No test was written or run for this document. No model or data API was called, and no dependency was installed.
- The only authorized write path is `docs/code-governance/verification-constraints.md`; this authorization does not extend to another D4 file.

### 1.4 Obsolete Metadata

Some D2 text may still mention obsolete batches or state that a trace matrix or permission model has not yet been created. The current artifacts exist and are used as current inputs. Only those factually obsolete metadata statements are disregarded. Real OQ decisions, Proposed/Planned/Pending states, interface gaps, and unimplemented mechanisms remain binding. Section 9 records them.

## 2. Active FC Coverage Design

Rules:

- A `V-*` identifier is a planned verification intent, not an existing test name.
- Proposed test files in the location column do not exist, are not approved, and are not authorized for creation by this document; existing files are baseline regression assets.
- All 40 active FC acceptance tests are offline-first. Live model/vendor tests cannot replace deterministic FC acceptance.
- The default approval/readiness state is `Not submitted` or `Not approved`; the rightmost column records additional dependencies.
- A single parameterized test may cover multiple FCs or IRs when its assertions clearly identify each covered ID. Coverage is judged by assertions and evidence, not by file or function count.
- AST scans, sentinels, barriers, watchdogs, and equivalent controlled techniques are verification methods, not production requirements. Any equivalent method may be used if it proves the same property; D1-required scenarios must remain present.

| FC ID | Scenario/Intent ID | Verification Target | Component/Interface | Inputs and Preconditions | Independent Expected Result | Verification Layer | offline/live | Proposed Test Location | Approval/Readiness |
|---|---|---|---|---|---|---|---|---|---|
| FR-01-FC01 | V-FR01-01 | Three sequential identical calls in one run execute the existing fetch once; normal, no-data, unavailable, and exception outcomes are reused equivalently | C-05 IF-04, C-06 | One RunContext; four isolated sub-scenarios; independent fetch counter | fetch=1 per scenario; three calls receive equivalent content or same-type/same-reason failure; no silent restart | Behavior/unit | offline | Proposed `test_fr01_query_reuse.py`; baseline `test_news_lookahead.py` | Not approved |
| FR-01-FC02 | V-FR01-02 | Positional/keyword, keyword-order, and explicit-default variants merge; different method/ticker/window do not | C-05 query key | Table-driven positive/negative pairs; independent expected same/different labels | Mergeable pairs produce fetch=1; non-mergeable pairs execute separately; no undeclared semantic equivalence | Behavior/unit | offline | Proposed `test_fr01_query_reuse.py` | Not approved |
| FR-01-FC03 | V-FR01-03 | Concurrent identical calls single-flight; normal/error completion releases waiters without hanging | C-05 single-flight | Three callers at a barrier; controlled completion/exception; test watchdog | fetch starts once; all callers receive the result or same failure; watchdog detects no timeout | Behavior/concurrency | offline | Proposed `test_fr01_query_reuse.py` | Not approved; no production deadline is added |
| FR-01-FC04 | V-FR01-04 | Two independent runs do not share reuse state; vendor-cache hits do not change the determination | C-05, C-03 | Two RunContexts; same parameters; distinguishable returns; two calls per run | total fetch=2; each run executes once; run B cannot read run A's reuse state | Behavior/integration | offline | Proposed `test_fr01_query_reuse.py` | Not approved |
| FR-01-FC05 | V-FR01-05 | Real P-09/P-13 internal paths share one fetch; mutable results remain isolated | C-05, C-06 shared news executor | Replace the underlying vendor; exercise the real tool and prefetch paths; one consumer mutates its result | fetch=1; both paths associate with one query; content matches the existing flow; mutation does not pollute another consumer | Behavior/integration | offline | Proposed `test_fr01_query_reuse.py`; baseline `test_graph_end_to_end.py` | Not approved; OQ-13 pending |
| FR-02-FC01 | V-FR02-01 | running/completed manifest lifecycle, timing, config, and confirmed file references are correct; no sensitive prompt/config is stored; `manifest_version`, `analysis`, `report`, and `result_files` follow the blueprint v1 contract | C-03, C-14 IF-10, C-18 | Writable temporary results root; controlled clock; offline fake model/data; actual file reads | parseable running record after start; completed record at normal finish; correct fields/timing; only confirmed files recorded; `result_files=[]` when none; `report=null` when no merged report; no guessed/old-scan file reference; no credentials/full config | Behavior/integration | offline | Proposed `test_fr02_manifest.py` | Not approved; no manifest implementation |
| FR-02-FC02 | V-FR02-02 | Consecutive same-ticker/date runs receive distinct run IDs, retain both manifests, and keep per-run counts isolated | C-03, C-14, C-04 | Two consecutive analyses with different independent call counts | distinct IDs/paths; second run does not overwrite first; each manifest's counts belong only to its run | Behavior/integration | offline | Proposed `test_fr02_manifest.py` | Not approved |
| FR-02-FC03 | V-FR02-03 | Duplicate callbacks/stream fragments do not double-count; complete usage sums exactly; any incomplete usage nulls both token totals; zero calls gives 0/0; prefetch is not a tool | C-04 IF-11 | Independent callback event record; success/failure, duplicate start/end, streaming, missing/invalid usage, reflection, parallel/subgraph cases | counts match independent record; token/usage_complete rules are exact; unfinished/unknown calls become null, not fabricated zero | Behavior/unit and integration | offline | Proposed `test_fr02_manifest.py`; baseline `test_analyst_execution.py` | Not approved; OQ-16 pending |
| FR-02-FC04 | V-FR02-04 | Five manifest scenarios have distinct outcomes and preserve original analysis behavior and valid old JSON | C-03, C-14 | (1) analysis exception with writable storage; (2) first running write fails; (3) terminal write fails; (4) serialization fails; (5) analysis and manifest both fail | (1) failed record with safe error, original analysis error; (2) analysis continues and terminal may be written directly; (3) normal result remains and old valid JSON is intact; (4) old valid file is intact; (5) original analysis error is not replaced. Manifest-handling failure warns; successful writes need no warning; no retry/rollback/forced terminal guarantee | Behavior/fault injection | offline | Proposed `test_fr02_manifest.py` | Not approved |
| FR-02-FC05 | V-FR02-05 | With normal storage, CLI and propagate use the same format and each analysis has one manifest; nested CLI delegation creates no second manifest; return shape and config allowlist remain | C-01, C-02, C-03, C-14 | Two real entries; CLI internally delegates to propagate; normal and failing analyses | when storage is normal, one manifest per analysis; required types valid; config follows `run_settings`; CLI/return shapes remain; storage failure is handled under FC04 and may leave missing/running files | Behavior/integration | offline | Proposed `test_fr02_manifest.py`; baseline `test_graph_end_to_end.py` | Not approved |
| FR-03-FC01 | V-FR03-01 | Fifteen paths/fourteen methods classify normal, empty, unavailable/not-configured, withheld, and exception outcomes; original return/exception and unknown source remain intact | C-06, C-20 IF-23, C-07 | Fixed producer fixtures per path; independent expected status table; P-03 per indicator | status/reason/object/range correct; non-empty error text is never available; source is known or null; original fetch semantics preserved | Behavior/unit and integration | offline | Proposed `test_fr03_availability.py`; baseline vendor tests | Not approved; OQ-12 producer branches pending |
| FR-03-FC02 | V-FR03-02 | Seven necessity items follow enabled analysts; targets come from actual request context; all available means complete; any gap means incomplete; unqueried items are not fabricated; no applicable/non-stock means not_applicable | C-07 IF-06 | All-success, single no-data/failure, unqueried, disabled analyst, no applicable item, non-stock; target-first matching | `necessary_items` match independent expected list; complete/incomplete/not_applicable correct; `not_attempted` only without a completed result; no automatic refetch. Multi-range/frequency targets for stock-data and statements remain pending | Behavior/unit | offline | Proposed `test_fr03_availability.py` | Not approved; target choice pending |
| FR-03-FC03 | V-FR03-03 | Supplementary failures are disclosed but do not change basic completeness; same-target fallback success may be available; different items do not substitute | C-07 IF-06, C-20 | Ticker news/StockTwits/FRED failures; same-target fallback; global-news success with ticker-news failure; Reddit fail/StockTwits success | `supplementary_limitations` appears; basic completeness unchanged; fallback status correct; no cross-item substitution | Behavior/unit | offline | Proposed `test_fr03_availability.py` | Not approved |
| FR-03-FC04 | V-FR03-04 | Target matching precedes last-accepted selection; another object/window/item cannot substitute; only accepted order determines the latest result; duplicate/different query/run isolation; no extra fetch | C-07 acceptance sequence | failure→success, success→failure, duplicate, concurrent, different windows, two runs, no completed result; data-call sentinel | each snapshot selects the last accepted matching result; no success preference; no duplicate gap; no cross-query/run contamination; no extra data request | Behavior/concurrency | offline | Proposed `test_fr03_availability.py` | Not approved; OQ-15 pending |
| FR-03-FC05 | V-FR03-05 | Real adapters feed the summary; research-start, check-time, and terminal-report times are correct; same-time consumers agree; report display is deterministic; later observations do not rerun research | C-06, C-07, C-10 IF-24, C-11 IF-18, C-01/C-02 | Real internal adapter paths; fake model; capture first Bull, later research, and report inputs | first Bull receives the block in the same call; later roles receive the same mapping; report uses terminal mapping; gaps/limitations visible; no research rerun or extra query | Behavior/integration | offline | Proposed `test_fr03_availability.py`; baseline `test_graph_end_to_end.py` | Not approved; OQ-13/OQ-15 pending |
| FR-04-FC01 | V-FR04-01 | Normal and equality boundaries pass exactly; one legal non-default threshold pair is honored; display rounding never decides | C-08 IF-08/IF-25 | Independent Fraction/Decimal expectations; default and one non-default legal threshold scenario; portfolio=100000, buy=30000, entry=100, stop=95 | projected/stop values exact; status=passed at/below boundaries; non-default legal thresholds affect the result; display rounding does not affect status | Behavior/unit | offline | Proposed `test_fr04_risk.py` | Not approved; OQ-02 key names decided |
| FR-04-FC02 | V-FR04-02 | Single/double over-limit block with accurate reasons; display-rounded equality cannot turn a real over-limit into pass; model text cannot change it | C-08 | Concentration over-limit, stop over-limit, both, display-rounding case; fake model text | status=blocked; both reasons retained for double breach; model text has no effect | Behavior/unit | offline | Proposed `test_fr04_risk.py` | Not approved |
| FR-04-FC03 | V-FR04-03 | Missing, invalid, non-finite, boolean, and invalid-threshold inputs block without auto-fill or numeric crash; metrics follow their own operands | C-08 | Ticker mismatch, portfolio<=0, negative/oversized position, buy<=0, invalid entry/stop/currency, invalid threshold | blocked with category reason; no default/model/network fill; no divide-by-zero/numeric escape; legal metrics remain independent of unrelated invalid fields | Behavior/unit | offline | Proposed `test_fr04_risk.py` | Not approved |
| FR-04-FC04 | V-FR04-04 | Applicability and evaluator-error behavior are correct without changing FR-04 judgment order | C-08, C-10 risk node | Legal applicable stock Buy/Overweight; other legal ratings; legal non-stock; missing/illegal input; model text; evaluator exception | legal applicable input returns computed passed or blocked; legal non-applicable returns not_applicable; missing/invalid input returns blocked; evaluator exception returns error and never passed. No full SB-01 matrix | Behavior/unit | offline | Proposed `test_fr04_risk.py` | Not approved |
| FR-04-FC05 | V-FR04-05 | Both entries compute consistently; final_state/CLI/report show the same risk result; FR-04 remains an independent structured result; blocked/error deterministic display requires manual review; missing input does not hard-fail | C-01, C-02, C-08, C-11; C-09 consumer separately | Same scenario through both entries; Buy/Overweight; missing, over-limit, error; manifest failure | entries agree; return shape remains; risk section/final_state agree; FR-04 writes no formal fields; blocked/error display says manual review; SB-01 may form REVIEW; manifest failure does not affect risk | Behavior/integration | offline | Proposed `test_fr04_risk.py`; baseline `test_graph_end_to_end.py` | Not approved; OQ-01/OQ-04 pending |
| FR-05-FC01 | V-FR05-01 | Only legal completed manifests with a legal merged-report reference are listed; `report:null` is legal but unlisted; missing required `report` key or malformed non-null object is skipped; deleted registered report remains listable with false availability | C-13 IF-12, C-14 | Temporary results; legal/illegal/missing-key/unsupported manifests; registered deleted report | list matches independent expected set; bad records warn without stopping; `report:null` not listed; missing-key invalid skipped; registered missing file remains `report_available=false` | Behavior/unit | offline | Proposed `test_fr05_history.py` | Not approved |
| FR-05-FC02 | V-FR05-02 | Ticker/date filters intersect; null filters do nothing; invalid parameters error; ordering is started_at descending then run_id ascending | C-13 IF-12 | Multiple tickers/dates/times; equal times; combined/no-match/invalid parameters | filtering/order matches independent table; no match=[]; invalid parameter error; no pagination/stable-snapshot promise | Behavior/unit | offline | Proposed `test_fr05_history.py` | Not approved |
| FR-05-FC03 | V-FR05-03 | `get_report` returns current UTF-8 without rewrite; `report:null`, unknown, no-manifest, and non-completed records are not found; missing key/malformed object is invalid record; missing/unreadable/invalid UTF-8 registered report is a read error; deleting unrelated section/memory/risk files does not affect the registered merged report | C-13 IF-13 | UTF-8 multi-line Markdown; unknown ID; deleted/unreadable/invalid UTF-8 report; missing report key; unrelated section/memory/risk deletions; later external edit | legal report returned unchanged; no empty-success fabrication; error classes correct; unrelated deletions do not affect read; current edited content returned | Behavior/unit | offline | Proposed `test_fr05_history.py` | Not approved |
| FR-05-FC04 | V-FR05-04 | Illegal run_id/traversal/absolute input/out-of-root reference/missing or unreadable root are distinguished; out-of-root sentinel is not read; legal in-root legacy layout is readable | C-13, C-15 IF-14/IF-15 | Temporary root, symlink, out-of-root sentinel, missing/unreadable root | illegal ID=parameter error; out-of-root=invalid record; missing root=empty history; unreadable root=history-read error; sentinel unread | Behavior/security | offline | Proposed `test_fr05_history.py`; baseline `test_safe_ticker_component.py` | Not approved |
| FR-05-FC05 | V-FR05-05 | A saved report registered by a completed manifest is discoverable/readable; propagate is not forced to save; query performs no write/model/vendor/graph/renderer/repair | C-13, C-11 IF-18, C-01/C-02 | Existing save flow plus completed manifest; no-report propagate; manifest save failure | registered report readable; no forced save; failure does not rerun/retro-register; dependency sentinels remain zero | Behavior/integration | offline | Proposed `test_fr05_history.py`; baseline `test_reporting.py` | Not approved |
| SB-01-FC01 | V-SB01-01 | Five legal ratings and valid non-whitespace conclusions with complete FR-03; applicable stock Buy/Overweight has passed FR-04; gate passes and retains model values without extra calls | C-09 IF-09, C-07/C-08 | Finite decision table; forbidden-call sentinel | gate=passed; final values derive from proposal; no invented pass reason; no model/data/risk recomputation | Behavior/unit | offline | Proposed `test_sb01_final_check.py` | Not approved |
| SB-01-FC02 | V-SB01-02 | Incomplete FR-03 blocks; supplementary-only failure does not; not_applicable is not complete and does not alone block; model text cannot override summary | C-09, C-07 | Controlled five-field summaries; missing necessity item, supplementary-only failure, not_applicable, model claims completeness | matching REVIEW/notice or continuation; necessary reason correct; supplementary alone does not trigger REVIEW | Behavior/unit | offline | Proposed `test_sb01_final_check.py` | Not approved |
| SB-01-FC03 | V-SB01-03 | For stock Buy/Overweight only risk `passed` satisfies; blocked/error/missing/illegal/wrong-not-applicable block; FR-04 is not recalled | C-09, C-08 | Risk-status table; fake model text; recomputation sentinel | only passed passes; other states produce REVIEW explaining risk; risk reasons remain in risk object | Behavior/unit | offline | Proposed `test_sb01_final_check.py` | Not approved |
| SB-01-FC04 | V-SB01-04 | Missing/illegal rating, model REVIEW, missing/wrong-type/empty/whitespace conclusion, missing or illegal FR-03 summary, contradiction, and internal exception produce distinct blocked/error REVIEW outcomes | C-09 | Parameterized negatives; exception injection; invalid conclusion and invalid-summary cases | missing/wrong-type/empty/whitespace conclusion is ordinary blocked; missing/illegal summary is blocked; other ordinary condition failures block; SB-01 internal exception is error; final=REVIEW; reasons match; no fabrication; valid conclusion is preserved without trimming | Behavior/unit | offline | Proposed `test_sb01_final_check.py` | Not approved |
| SB-01-FC05 | V-SB01-05 | CLI/propagate/report/final_state use one post-check result; returned signal equals `final_rating`; REVIEW formal text is the program notice; intermediate proposal never appears as final; return shape and manifest failure do not alter the check | C-09, C-10, C-01/C-02, C-11 | Two entries normal/blocked; model text with original recommendation; requested report; manifest failure | output/signal consistent; REVIEW notice; proposal separately labeled and not final; shape unchanged; manifest failure has no effect. INV-01 evidence may be reused without a duplicate system | Behavior/integration | offline | Proposed `test_sb01_final_check.py`; baseline `test_rating_integrity.py` | Not approved |
| INV-01-FC01 | V-INV01-01 | Return/CLI/report/final-state JSON use the same formal value; no reparse/replacement; formats may differ; manifest stores no rating | C-01/C-02, C-11, IF-19; C-03 | Passed and blocked/REVIEW; different proposal/notice markers; actual outputs | formal fields agree across outputs; proposal never substitutes; whole-file bytes are not compared; manifest rating is not required | Behavior/integration | offline | Proposed `test_inv01_output_consistency.py`; baseline `test_reporting.py` | Not approved |
| INV-01-FC02 | V-INV01-02 | New memory record uses formal rating/body; REVIEW is not overwritten by pre-check Buy/Hold; disabled/no-record forces nothing and changes nothing; saving adds no model call | C-12, C-01/C-02 | Memory enabled/disabled/no-new-record; passed/REVIEW; call sentinel | new entry matches formal; no forced record; history unchanged; no extra model call | Behavior/integration | offline | Proposed `test_inv01_output_consistency.py`; baseline `test_memory_log.py` | Not approved |
| INV-01-FC03 | V-INV01-03 | Normal settlement/reflection may update outcome/reflection but not the original rating/decision; no immutable/rotation/tamper claim | C-12, existing settlement/reflection | Existing decision plus normal outcome update | rating/body unchanged before/after; reflection may be added; reflection's own model call is not misclassified | Behavior/regression | offline | Proposed `test_inv01_output_consistency.py`; baseline `test_memory_log.py` | Not approved |
| SR-01-FC01 | V-SR01-01 | Manifest/report/final-state config summaries follow the allowlist and IF-21 exact matching; normal fields remain; report body is not scanned | C-15, C-18 IF-21, C-14, C-11 | API key/Authorization/password/endpoint/normal fields; one exact whole-value match; one credential substring inside a larger field; empty credential | credential fields absent; whole field omitted for whole-value or substring match; empty credential never matches; normal fields remain; no decoding/fuzzy/unknown detection or report-body scan | Behavior/security | offline | Proposed `test_sr01_credentials.py`; baseline `test_reporting.py` | Not approved |
| SR-01-FC02 | V-SR01-02 | Ordinary endpoints save/restore; userinfo/query/fragment/known-credential/unparseable endpoints are omitted; empty `?` or `#` separators count; re-entry required; `.env` unchanged | C-15 IF-16, CLI preferences | Real preference load/save path; safe and unsafe endpoints, including explicit empty query/fragment separators | safe save/restore; unsafe item omitted and re-entry requested; no masked pseudo-endpoint; empty separator is not silently stripped; other preferences remain | Behavior/security | offline | Proposed `test_sr01_credentials.py`; baseline `test_cli_prefs.py` | Not approved |
| SR-01-FC03 | V-SR01-03 | Supported error adapters replace known credentials with `***`; URL/request/response/exception-chain content is not re-exposed; safe category remains | C-15 IF-17; get_scrubbed paths | Mock request exceptions; known credential plus normal diagnostics | original credential absent; fixed marker; safe category retained; unknown tokens/encodings are not scanned | Behavior/security | offline | Proposed `test_sr01_credentials.py`; baseline `test_get_scrubbed.py` | Not approved |
| SR-01-FC04 | V-SR01-04 | Handling failure omits the field or uses a fixed safe message; manifest failure skips/warns; analysis/original error continues; no credential file or `.env` change | C-15, C-18, C-14 | Finite fault injection; manifest cannot be safely formed | no raw sensitive echo; analysis continues; original error wins; existing scrub/.env controls remain; no scan counter | Behavior/security | offline | Proposed `test_sr01_credentials.py` | Not approved |
| SR-02-FC01 | V-SR02-01 | Legal run_id/ticker creates an in-root manifest path; illegal identifiers create nothing out of root; FR-02 warns and continues; root is not switched | C-15 IF-14, C-14, C-01/C-02 | Empty/separator/`.`/`..`/traversal/absolute/prefix-collision cases; out-of-root write sentinel | legal path inside root; illegal value creates/writes nothing outside; warning then continue; ticker protection preserved | Behavior/security | offline | Proposed `test_sr02_paths.py`; baseline `test_safe_ticker_component.py` | Not approved |
| SR-02-FC02 | V-SR02-02 | In-root relative/absolute references are readable; traversal/prefix/symlink escapes are not; a legal in-root link is a positive case when the platform supports links; report prose does not control path | C-15 IF-15, C-13 | Temporary files/links; out-of-root read sentinel; path-bearing prose; supported platform link case | legal in-root link readable; escape/traversal not read; prose has no effect; errors follow FR-05; unsupported link environment is recorded unverified, no platform matrix required | Behavior/security | offline | Proposed `test_sr02_paths.py`; baseline `test_symbols.py` | Not approved |
| SR-02-FC03 | V-SR02-03 | FR-02 path failure warns/continues; FR-05 illegal reference rejects; no cwd/root switch; user out-of-root save retains behavior without history guarantee, copying, or widened authorization; diagnostics safe | C-01/C-02, C-14, C-13; C-15 | FR-02 path failure; illegal history reference; user out-of-root save | matching warning/error; root unchanged; out-of-root save does not auto-enter history; no recovery/cleanup; diagnostics contain no secret/body | Behavior/integration | offline | Proposed `test_sr02_paths.py`; baseline `test_safe_ticker_component.py` | Not approved |

## 3. Invariant Violation Detection Design

Every IR has at least one artificial violation whose test must fail. A normal-path pass alone is insufficient.

| IR ID | Related Requirements/FCs | Artificial Violation | Detection Method | Must-Fail Assertion | Verification Layer | Status |
|---|---|---|---|---|---|---|
| IR-01 | SB-01-FC01/FC04/FC05; INV-01-FC01 | A second component recomputes/replaces/parses a formal value, or a consumer derives formal from the proposal | Instrumented source markers through pass-through boundaries; AST/source check; graph integration | Failure if the value source is recomputed/re-parsed/replaced/fabricated. Ordinary assignment, merge, copy, or save of unchanged values must not be treated as a violation | Structure + behavior | Planned; not approved |
| IR-02 | SB-01-FC02–FC04; FR-04-FC04 | Incomplete data, non-passed risk, missing input, model REVIEW, invalid conclusion, or a handled SB-01 exception fails to produce REVIEW | Controlled summary/risk/exception tables | Failure if a violating case returns `passed`, fails to return REVIEW, or omits the required notice | Behavior | Planned; not approved |
| IR-03 | SB-01-FC05; INV-01-FC01 | Remove/corrupt a merged formal field, make its text blank, or let a consumer invent REVIEW from proposal/text | Formal-result contract negatives plus entry integration | Failure if no execution contract failure occurs, normal return/save happens, or a consumer creates REVIEW | Behavior + integration | Planned; not approved |
| IR-04 | INV-01-FC01–FC03 | Different formal values across report/final-state/memory, or reflection rewrites rating/body | Cross-output markers; settlement before/after | Failure if any actual output disagrees, a new memory entry is not formal, or reflection changes the decision | Behavior/integration | Planned; not approved |
| IR-05 | FR-02-FC02/FC05; FR-01-FC04; FR-03-FC04 | Reuse one run state across analyses; create a second manifest in nested CLI; read an old checkpoint | Two-run isolation, nested entry, checkpoint-enabled full-run | Failure on same run_id/state leakage, second manifest, or resume | Behavior + integration | Planned; not approved |
| IR-06 | FR-02-FC01/FC02/FC04/FC05 | Manifest failure propagates, changes formal/return, damages old JSON, fabricates a result file, or omits a confirmed file from `result_files` | Atomic write/serialization/failure injection; actual file reads | Failure if original result/error changes, old JSON is damaged, a file reference is fake, or a confirmed produced-file reference is omitted | Behavior/fault injection | Planned; not approved |
| IR-07 | FR-02-FC04; SB-01-FC05; INV-01-FC02/FC03; FR-05-FC05 | Treat final-state/memory/report failure as warning-only, rerun formal work, or roll back a successful artifact | Path-specific fault injection; before/after file comparison | Failure if run status is wrong, a successful file is rolled back, formal changes, or a false success is reported | Behavior/fault injection | Planned; not approved |
| IR-08 | FR-01-FC01–FC05; FR-03-FC05 | Execute one query twice, merge different windows, read across runs, or give waiters an observation-handling error | Independent fetch counter, concurrency barrier, two-run test, mutable result | Failure if fetch count exceeds one per scope, queries merge/leak, or a waiter receives the wrong outcome | Behavior/concurrency | Planned; not approved |
| IR-09 | FR-03-FC01/FC03/FC05; FR-01-FC05 | Duplicate/miss one of 15 observation sites, classify concatenated P-03 text, or replace the fetch outcome with observation handling | Static attachment table plus real internal paths and original-outcome sentinel | Failure on wrong site count/location, duplicate observation, or replaced return/exception | Structure + behavior | Planned; not approved |
| IR-10 | FR-03-FC01/FC02/FC04; FR-01-FC05 | Order by wall time, let another query clear a mark, skip target matching, or create a completed query from a pre-fetch rejection | Controlled interleaving, mark isolation, target filtering, P-03 early rejection | Failure on wrong accepted order, wrong-target selection, cleared mark, or fake query/sequence | Behavior/concurrency | Planned; not approved; OQ-15 |
| IR-11 | FR-03-FC02–FC05; SB-01-FC02 | Add/remove summary fields, rebuild completeness in a consumer, treat supplementary as necessity, or veto a mark twice | Five-field/type checks, consumer sentinel, seven-item truth table | Failure on field mismatch, consumer rebuild, supplementary affecting completeness, or duplicate mark veto | Structure + behavior | Planned; not approved |
| IR-12 | FR-03-FC05; D-10b | First Bull does not receive the block, a later round refreshes it, or null is replaced by a fabricated summary/rerun | Prompt capture, later-role capture, extra-call sentinel | Failure if the same call lacks the block, the stage mapping changes, research reruns, or null is fabricated | Behavior/integration | Planned; not approved; OQ-13 |
| IR-13 | FR-03-FC05; INV-01-FC01; SB-01-FC05 | Writer reads live registry/context, reruns SB-01 during terminal refresh, or Markdown/HTML use different inputs | Registry/context access sentinel, A/B save, same-input capture | Failure if writer accesses live state, formal changes, independent save reads another run, or inputs differ | Behavior/integration | Planned; not approved |
| IR-14 | FR-04-FC01–FC05 | Use float/display rounding at a boundary, fall back from an invalid explicit threshold, fill from model text, or write formal fields from FR-04 | Independent Fraction expectations, negative table, serialization check | Failure on wrong equality boundary, threshold fallback, invalid-value fill, non-JSON-compatible output, or formal-field write | Behavior/unit | Planned; not approved |
| IR-15 | FR-02-FC02/FC03/FC05 | Double-count callbacks, treat missing usage as zero, accumulate across runs, or let callback failure alter business output | Independent event table, two-run test, incomplete usage, callback exception | Failure on count/total mismatch, null-rule violation, cross-run contamination, or changed business result | Behavior/unit and integration | Planned; not approved; OQ-16 |
| IR-16 | FR-05-FC01–FC05 | List a bad record, confuse `report:null` with corrupt format, return not-found for a deleted registered report, repair/re-render, or trigger analysis | Real manifests/reports, missing `report` key, `report:null`, deleted report, read-only sentinel | Failure on wrong list membership/order, legal no-report listed, missing-key not invalid, deleted report collapsed to not-found, file mutation, or model/data call | Behavior/unit | Planned; not approved |
| IR-17 | SR-01-FC01–FC04 | Inject a known credential into a field/report/error, save an unsafe endpoint, or echo raw content on handling failure | Independent test secret, preference load/save, fault injection; whole-value and substring cases | Failure if the known value remains, the entire affected field is not omitted, an unsafe endpoint is saved/restored, or raw fallback/hard exit occurs | Behavior/security | Planned; not approved |
| IR-18 | SR-02-FC01–FC03; FR-05-FC04 | Use `..`/absolute run_id/prefix collision/symlink escape, let prose control a path, or switch root on FR-02 failure | Temporary root and out-of-root sentinel | Failure on out-of-root create/read, cwd/root switch, prose-controlled path, or missing legitimate warning/error | Behavior/security | Planned; not approved |

## 4. Three Verification Layers and offline/live Split

### 4.1 Coverage and Structure

- Every active FC has at least one verification intent and, in the eventual approved suite, at least one actual test assertion.
- Every IR has at least one violation test that must fail when the invariant is broken.
- One parameterized test may cover multiple FCs or IRs. Coverage is judged by assertions and identified IDs, not file/function count.
- AST scans, sentinels, barriers, watchdogs, and similar techniques are verification aids. Equivalent methods are acceptable when they prove the same property; D1-required scenarios remain mandatory.
- Test aids must not become production mechanisms. A watchdog does not create a production deadline, and a sentinel does not create a runtime monitor.
- D2 architecture-conformity checks and D1 product-behavior acceptance are labeled separately, but neither set is discarded.

Structural verification includes:

- Check that SB-01/C-09 is the sole decision/generation authority for formal business values. Entries, reducers, and writers may pass/merge/copy/save unchanged values; assignment count is not a violation.
- Check that consumers do not re-parse proposal text into formal values.
- Check that RunContext, stats, reuse, and availability registry do not enter graph state/checkpoint.
- Check that FR-04/SB-01 pure rules call no model or data source.
- Check the 15 observation attachment positions, per-indicator P-03, and shared P-09/P-13 executor.
- Check that policy/path/permission boundaries do not grant unauthorized writes or formal-value generation.
- Validate requirements YAML against `req-schema.json`.
- Check module imports/boundaries against D2 component responsibilities; do not treat application agent roles as file-access roles.

### 4.2 Regression

- Every round runs all previously applicable tests, not only new tests.
- Any regression blocks merge.
- When a new test conflicts with an old assertion, record the D1/D2 difference and resolve it by human review; do not delete the old test or weaken its assertion directly.
- The current default command is `pytest -q` from the project root. The current `pyproject.toml` adds `-ra --strict-markers -m "not integration"`, so the default excludes integration/live tests.
- CI currently runs `pytest -q` from the project root; this does not mean new D2 tests exist or pass.

### 4.3 Behavior

- Deterministic FC/IR tests prefer fake models, controlled vendor substitutes, temporary directories, fault injection, and fixed fixtures.
- Security boundaries use independent decision tables, not just a normal/200-text response.
- A default offline pytest pass does not prove live model/API quality.
- Each changed feature needs at least one negative test. Documentation-only changes need no application behavior test, but still need structural/regression/governance checks.

### 4.4 Offline/live

- All 40 active FCs can be verified offline; real internal paths remain through controlled substitutes.
- `conftest.py` blocks network by default; only tests marked `integration` bypass that block. The current suite has one integration marker; it was not run here.
- Live is only for future authorized real API/model quality checks. No fixed D2 evaluation set, scoring rule, or approved quality threshold was found, so no live quality gate is claimed.
- Live environment failure, missing credentials, skipping, or not running are not passes. Offline substitute success does not prove real model quality.
- Proposed live command: `pytest -q -m integration`. It is not a D2 fixed evaluation set and requires separate environment/authorization; it is not current pass evidence.

## 5. Independent Expected Results and Test Doubles

- Expected results come from D1 text/FCs, approved D2 contracts, or independently maintained tables, never from the implementation under test.
- FR-04 uses independent hand-calculated Fraction/Decimal expectations; implementation-returned metrics are not the oracle.
- FR-03 uses sourced producer fixtures and independent status tables; classifier output is not its own oracle.
- SB-01/INV-01 use independent decision tables and markers; formal expectations are not reverse-engineered from model text.
- Manifest/history tests use controlled clocks, temporary roots, and independent expected files; they do not trust self-reported success.
- Writer obligations and history-reader acceptance are separate. The reader validates only registration, filtering, ordering, and report-read fields; it does not validate every manifest field or `result_files` completeness.
- Integration tests may replace external models/vendors but must retain the real internal entries, connections, and consumers. Do not mock out the core logic and call that integration.
- If no independent expectation exists, design status is `Decision pending`/`Not ready`; implementation output must not fill the oracle.

## 6. Pre-Approval, Execution State, and Evidence

### 6.0 Test Traceability

The final approved suite must contain at least one actual test for every active FC and at least one violation test for every IR. Every new test must cite its verification object through its name, docstring, pytest marker, or equivalent machine-readable metadata: FC tests cite the exact FC ID; invariant tests cite the IR and related FC/requirement; multi-object tests list all. A `V-*` intent table without a locatable actual test does not satisfy coverage.

Security-critical code changes also require the corresponding ADR and human review; passing tests or ordinary PR approval does not replace that requirement.

### 6.1 Design Approval State

| State | Meaning |
|---|---|
| Not submitted | Only a test intent exists; no concrete design is ready for approval |
| Pending approval | Intent/file/assertion is submitted and waiting for human approval |
| Approved | Concrete test, file, and assertions are approved for implementation |
| Changes required | Assertion/scope/expectation must change before approval |
| Business decision pending | Expected behavior or requirement interpretation is unresolved |
| Approved for technical verification | Target, controlled inputs, and expected behavior are clear enough to approve a test that resolves an interface/propagation assumption; this is not final integration acceptance |

An unresolved interface does not automatically block test-design approval. A test may be approved for technical verification when its verification objective, controlled input, and expected result are explicit. Such approval does not mean the interface is confirmed, implementation exists, or final integration acceptance passed. A business behavior that is not yet decided keeps the final acceptance specification pending.

Approval strategy is not specific-test approval. Record the exact task file list, FC/IR IDs, expected results, and assertion scope.

### 6.2 Execution State

| State | Meaning |
|---|---|
| Not run | No execution record; not a pass |
| Passed | Actually executed in the recorded version/environment and all assertions passed |
| Failed | Executed and assertions failed |
| Skipped | Marker/condition skipped; not a pass |
| Environment blocked | Dependency, network/live environment, or permission unavailable |

Every changed test must be approved before implementation and retain traceable evidence. All current `V-*` items are `Not submitted`, `Not approved`, and `Not run`; no test-pass conclusion exists.

### 6.3 Execution Evidence

Future records must locate at least: commit/tree, test-file version, requirements version, FC/IR IDs, exact command, offline/live, environment, fixed fixture/eval set, expected, actual, exit code, evidence location, and approval record. Do not invent dates, approvers, or pass results.

If requirements, expectations, assertions, or scope change, reconfirm affected approvals; unrelated tests need no repeated approval. Implementation must not hide regression by deleting tests, weakening assertions, or relaxing thresholds. When an old test conflicts with approved new behavior, record the difference and adjust through review.

## 7. Fault Injection, Blocking Gates, and QA Handoff

### 7.1 Runtime Policy Fault Groups

| Fault Group | Related RPs | Injection and Independent Expectation | Related FC/IR | Status |
|---|---|---|---|---|
| Entry/run creation | RP-01–RP-05 | Pre-start invalid input creates no run; post-start failure preserves original error plus failed-manifest attempt; checkpoint config does not resume; unhandled failure creates no fake formal result | FR-02, INV-01; IR-05, IR-07 | Planned |
| Data fetch/path boundary | RP-06–RP-07 | normal/empty/withheld/unavailable/fallback; pre-fetch rejection leaves only a note, no query/sequence/tracking | FR-03; IR-09, IR-10 | Planned; OQ-12/OQ-15 |
| FR-01/observation | RP-08–RP-10 | single-flight, shared failure, mutable isolation; classifier exception becomes conservative unavailable; acceptance failure becomes query mark | FR-01/FR-03; IR-08, IR-09, IR-10 | Planned; OQ-13/OQ-15 |
| tracking/snapshot | RP-11–RP-12 | actual observation loss sets tracking error and later snapshots return None; one snapshot-construction failure affects only that call | FR-03; IR-10, IR-11 | Planned |
| research/summary | RP-13–RP-14 | no summary uses null/fixed text; incomplete/contradictory blocks; supplementary-only does not block | FR-03, SB-01; IR-11, IR-12 | Planned |
| FR-04 risk | RP-15–RP-17 | not_applicable/blocked/error; invalid input does not hard-fail; FR-04 writes no formal fields | FR-04; IR-14 | Planned |
| SB-01/formal contract | RP-18–RP-20 | passed/blocked/error distinct from missing formal; consumers do not create REVIEW | SB-01, INV-01; IR-01–IR-04 | Planned |
| Statistics | RP-21 | duplicate, missing usage, callback error, subgraph/parallel/reflection propagation; no fabricated counts | FR-02; IR-15 | Planned; OQ-16 |
| Manifest | RP-22 | dir/serialize/write/replace failure warns only; original result/exception and old JSON/ref truth remain | FR-02; IR-06 | Planned |
| final-state/memory/report | RP-23–RP-28 | path-specific failures; Markdown success/HTML failure; report preparation missing summary only; no rollback/recompute | FR-02, INV-01, FR-03; IR-07, IR-13 | Planned |
| memory/settlement | RP-29–RP-30 | disabled/same-day no-op is not failure; settlement/reflection degradation only notes; no new decision | INV-01; IR-04, IR-07 | Planned |
| History | RP-31 | parameter/not-found/invalid-record/read-error are distinct; `report:null` not-found; missing required `report` key is invalid record; bad record skipped with warning; no repair/re-render | FR-05; IR-16, IR-18 | Planned |
| Security/path | RP-32–RP-33 | credential omission/marker; unsafe endpoint not saved; out-of-root/illegal reference rejected; no authority expansion | SR-01/SR-02; IR-17, IR-18 | Planned |
| cleanup/interruption | RP-34–RP-35 | primary error wins; cleanup does not close twice; forced termination creates no terminal/recovery claim | INV-01, FR-02; IR-07 | Planned |

### 7.2 CI Blocking Gates

| Gate | Required Design | Current Evidence | Gap |
|---|---|---|---|
| Test pre-approval | Concrete tests approved before implementation; test file/FC/IR/assertions recorded | Local PR gate implements the explicit `APPROVED test-spec:` phrase, bot rejection, approved-spec commit, implementation-start, and changed-scope checks. The historical local gate suite recorded 57 passed; the current gate file statically contains 58 top-level test functions, but no execution result for that current version is recorded in this documentation sync. No real GitHub PR approval event is verified. | Logic is locally implemented and historically tested; current-version coverage and remote execution remain unconfirmed; actual human approval is still required |
| Lint | Every commit | `ci.yml` runs `ruff check .` on push/PR. The 16 historical findings were later repaired by commit `b56da53`; this documentation sync did not re-run full-repository Ruff. | CI step and local repair exist; current remote execution is unverified, and lint is not a test/permission gate |
| Type checking | Every commit | `mypy.ini` and an exact `mypy-baseline.txt` exist, and CI runs the baseline check. Historical local execution reported no diagnostics outside the baseline; it was not re-run for this document. | Local configuration and historical local evidence exist; current-version and remote execution are unverified |
| Dependency check | Every commit | CI runs `pip check`, an import smoke check, and a separate clean-install job. | Local configuration exists; remote execution is unverified. This is not a vulnerability audit, zero-warning claim, or new numeric threshold |
| Security PR checks | Contract, security, API surface, path-permission checks | Local PR `security-paths` runs permission-configuration, API-signature, ADR-reference, and selected security tests; classification also selects contract tests and governance tests. No runtime path-permission engine exists. | Static gates are locally configured; real PR execution, ADR applicability/human approval, and runtime enforcement remain unverified |
| Requirements schema | YAML validated against `req-schema.json` | The push/PR workflow runs the schema check locally, the Schema accepts `ci_status: integrated`, and current requirements metadata records that local integration. Historical local checks reported 0 errors for the earlier version. | Local workflow integration exists; actual GitHub execution and current-version coverage are unverified, and semantic correctness is not checked |
| Prompt/model evaluation | Fixed evaluation set replay and quality threshold | The manual trusted workflow, candidate-bound evidence check, and controlled semantic entry are locally implemented. `docs/ci/semantic_eval.yaml` remains unapproved and no dataset, rubric, threshold, model, or runner is approved. | No approved semantic standard; evaluation and trusted-environment enforcement are unverified; do not invent thresholds |
| Full regression | Every prior applicable test each round | CI runs the Python 3.11–3.14 regression matrix and `pytest -q`, excluding integration by default. Historical local execution recorded 1415 passed, 3 existing failures, 1 skip, 1 deselected, and 100 subtests passed at the 57-gate-test version; the current 58-function gate file was not executed in this documentation sync. | Local CI configuration exists; the historical result is not current-version coverage, known failures/skip remain, and remote execution is unverified |
| AI-use log | Code/prompt changes update the log | The local PR gate requires a substantive changed entry associated with a changed code/prompt path; historical gate tests covered blocking and exemption cases. CI scripts and executable governance code remain covered. | Logic is locally implemented and historically tested; current-version and remote PR execution are unverified |
| Branch protection | CI passes; security-critical paths require human review and ADR | The repository contains the local required-check name and a branch-protection checklist, but repository files cannot prove remote rules are enabled. | Human/repository setting confirmation remains pending; no remote enforcement is claimed |

Local workflow configuration is not proof of remote execution. Historical local gate tests are not current-version coverage, and this documentation sync did not create a new test result. CI is retrospective and cannot prevent arbitrary reads or local edits. Passing tests is not PR approval or security-review completion.

### 7.3 QA Handoff

- Future `docs/review-memo.md` records spec, architecture, tests, runtime evidence, security, and efficiency checks for each PR; its verdict is one of `APPROVE`, `CHANGES REQUIRED`, or `REJECT`.
- Important bugs link to `docs/bug-diary.md`, recording symptom, reproduction, root cause, exposed IR/FC gap, and regression test.
- Confirmed debt links to `docs/debt-register.md`, including missing evaluation sets, unimplemented CI gates, prompt rot, and guardrail debt.
- This document does not create those D4/D7 files and records no invented review.

## 8. Protected Project Semantics

- Portfolio Manager produces only an advisory `model_proposal`; SB-01 is the sole formal-result authority.
- Business REVIEW, execution contract failure, and file-save failure are different dimensions; REVIEW may belong to a `completed` run.
- Missing/invalid formal output: consumers must not create REVIEW, re-parse proposal, or substitute formal values.
- Manifest failure warns only; report/final-state/new-memory failures keep their path-specific policies and never recompute formal output.
- FR-01 reuses supported queries only within one run, covering sequential, concurrent, shared-failure, result-isolation, and real P-09/P-13 paths.
- FR-03 covers 15 path positions, status classification, seven necessity items, supplementary limitations, acceptance order, local failures, tracking error, target matching, and cross-run isolation.
- Research-start, check-time, and terminal-report summaries are used at their own times; refresh adds no query or model rerun.
- FR-04 uses caller scenario and exact boundaries; display rounding does not decide pass; model text cannot fill missing input.
- Actual outputs and new memory use the same formal result; reflection may update outcome/reflection but not the original rating/body.
- Every new analysis executes fully; no old checkpoint is read, restored, or deleted as evidence; existing checkpoint tests remain regression assets.
- The statistics handler is run-owned; covers duplicate callbacks, missing usage, subgraph/parallel/reflection propagation.
- FR-05 is read-only; does not repair, re-render, or trigger analysis.
- SR-01/SR-02 verify only the limited scope; no universal secret scanner, all-path operation, or all-platform protection is claimed.
- FR-06, FR-07, PR-01, CR-01, and context budget/compression/reinjection are outside current test obligations.

## 9. Open Items, Course Alignment, and Mechanism Gaps

### 9.1 D2 OQ Impact on Verification

| OQ | Impact | Current Treatment |
|---|---|---|
| OQ-01 | Purchase-scenario CLI/file shape affects FR-04-FC05 entry tests | Test logic contract first; parameter/input shape and file read/parse error contract remain pending before entry implementation; do not fix an unapproved API |
| OQ-02 | Threshold config key names affect FR-04 config/entry tests | Key names `max_projected_weight` and `max_stop_distance` are decided by the current user instruction for these names only; no other config mechanism is approved and no test is thereby approved |
| OQ-04 | CLI save/display order affects FR-02/FR-05/INV-01/SB-01 entry integration | Observe save-then-display/terminal-then-display behavior without inventing approval; pending before CLI entry implementation |
| OQ-07 | Coding-agent roles/whitelist affect permission-design verification, not application FCs | D3-stage confirmation/implementation; this document grants no permission |
| OQ-08 | Recursion reserve affects new-graph entry/full-run tests | Pending technical verification of a completed normal path; the four-step figure is not acceptance |
| OQ-12 | FR-03 producer empty payload/feed/CSV shapes | Unconfirmed shape stays unavailable; finite sourced fixtures pending; no generic recognizer/network probe |
| OQ-13 | P-09/P-13 shared executor and first-Bull wrapper | FR-01-FC05, FR-03-FC05, IR-12 remain pending; offline integration only, no framework redesign |
| OQ-15 | Acceptance order, pre-fetch note, tracking error, summary/report source | FR-03-FC04/FC05 and IR-10/IR-13 remain pending under existing contract; no new state/recovery/global veto |
| OQ-16 | Callback propagation and usage extraction | FR-02-FC03/FC05 and IR-15 remain pending; local same-config handoff only, not global collection |

A test may be approved for technical verification before OQ-13/OQ-15/OQ-16 is resolved when its objective, controlled inputs, and expected result are explicit. That approval confirms neither the interface nor final integration acceptance.

### 9.2 Course Alignment Gap

D2 currently defers context token caps, compaction thresholds, and compressed-constraint reinjection. The course expects context budgeting/compression/reinjection to be covered by D2 design. This remains a course-alignment clarification for human decision. This document does not modify D2, add implementation work, or claim deferred behavior satisfies the course requirement.

### 9.3 Permissions, CI, and Branch Protection

- [`permission-model.md`](../architecture/permission-model.md) is a design artifact. `.opencode/permissions.jsonc` exists and CI statically checks its configuration, but actual OpenCode loading, merged precedence, runtime access restriction, and effective enforcement remain unverified.
- `AGENTS.md`, `.opencode/rules.md`, `.agent/rules.md`, and D3 governance files exist; their automatic loading and protection effect were not verified by this check.
- Local CI now includes schema, Ruff, mypy-baseline, dependency/import, regression, clean-install, test-approval, contract-test, security-path/ADR, permission-configuration, API-signature, AI-use-log, trusted semantic evidence, and aggregate configuration. These are local workflow and script implementations, not proof of GitHub execution.
- The historical local gate suite recorded 57 passed and the full local offline record was 1415 passed, 3 existing failures, 1 skip, 1 deselected, and 100 subtests. The current gate file contains 58 top-level test functions; its execution and the current full-suite result are unconfirmed by this documentation sync.
- No approved semantic dataset, rubric, threshold, model, or runner exists.
- Branch protection and remote required checks cannot be confirmed from repository files and are not claimed.
- These are course-gate evidence and enforcement gaps, not application FC failures; this document records them without changing configuration.

### 9.4 No Invented Thresholds

This document adds no performance, cost, model-quality, token, latency, or security-scan threshold. Faithfulness/relevance remain quality examples, not course-mandated scores. Without a D1 or human-approved score, dataset, and threshold, the gate remains `Undefined`/`Decision pending`; no pass criterion is fabricated.

## 10. Completion Self-Check

This table records the original D4 authoring self-check, not the current workspace's later CI implementation, test inventory, or execution state. Later synchronization notes are in Sections 7.2 and 9.3.

| Check | Result |
|---|---|
| Active FC coverage | 40/40 active FCs appear in the coverage table; each has at least one `V-*` intent |
| IR violation detection | IR-01–IR-18, 18/18 rows, each has a constructed violation and must-fail assertion |
| Deferred FCs | All 15 are listed; not executed or counted as passing; activation requires approval |
| Three layers | Structure, regression, and behavior are defined |
| offline/live | Default network block and integration exclusion are explicit; live is not run and cannot replace FC acceptance |
| Pre-approval/evidence | Design approval, execution state, and evidence fields are separate; no invented approval or result |
| Regression block | All prior applicable tests must run; regression blocks merge |
| D2 semantics | Formal authority, save paths, FR-01/03/04, summary timing, checkpoint, stats, history, and security are included |
| OQ/gaps | OQ-01/02/04/07/08/12/13/15/16, context course gap, and CI/permission gaps are recorded |
| Scope control | Only this file was updated; D1/D2/source/tests/CI/permissions were not changed; no test or application was run |

This document contains no application acceptance conclusion. All new D2 behavior tests remain planned, unapproved, and unrun.
