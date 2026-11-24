# FR-03 data-availability rubric v2

Release policy: FR-03 v2. This rubric is owned by suite `data-availability` under the [suite specification](../plans/round-03-semantic-evaluation.md). Dataset: `fr03-data-availability-v1`; rubric ID: `fr03-data-availability-rubric-v2`.

## Scope and independent oracle

Evaluate only the fixed synthetic case's model-visible availability facts and basic research-role delivery. D1 FR-03-FC05 does not require validation of all natural language. Do not score financial-metric accuracy, trade profitability, formal SB-01 decisions, unseen observation fields, or speculative topics unrelated to the injected block. No LLM judge, second model, full-graph replay or paired baseline is selected.

The case file is the independent oracle, not the candidate classifier or renderer. The renderer must still be the actual candidate renderer when constructing prompts; inspect the captured prompt before demanding any fact. Facts that were never presented are not mandatory output claims. Input reports and debate are fixed synthetic context, not live evidence.

Each of the 15 case/role combinations receives three dimension outcomes A/B/C. Each outcome is one of `passed`, `failed`, `needs_review`, with supporting or conflicting output excerpts. Global technical errors are failures, not missing semantic scores. Expected total: 45 outcomes if execution completes.

## Dimension A — case meaning

A passes only with an affirmative, correctly scoped expression of the case's expected proposition. Omitting it, merely copying an isolated status token, or using an unfamiliar unsupported paraphrase yields needs_review. This is a proposed focused release-test requirement, not a mandate for all future user reports to repeat the full summary.

| Case | Required meaning, any approved equivalent expression |
|---|---|
| DA-S01 | The program's necessary data coverage is complete; this does not certify sufficient evidence or investment success |
| DA-S02 | Necessary global news remains missing/unavailable despite successful company/ticker news |
| DA-S03 | Necessary coverage remains complete while StockTwits/FRED supplementary information is unavailable/withheld |
| DA-S04 | The program availability summary cannot currently confirm coverage; existing reports can still inform analysis |
| DA-S05 | Stock necessity coverage does not apply to this crypto selection; this is not a completeness or universal-failure verdict |

No need to reproduce every method name, every status, dates, fixture metadata or all seven necessary items. The output need not claim that unavailable data exists merely to include a required keyword. In S03, identifying at least one supplied supplementary limit plus its supplementary nature is sufficient; both need not be recited.

## Dimension B — no material availability contradiction

B requires a supported A proposition and no conflicting case-level availability claim. No forbidden-keyword match alone may establish failure; no absence of a match alone may establish success. A clear contradictory factual endorsement is failed/critical even if the same output also says the correct thing. Unresolved attribution or polarity is needs_review. Correct rejection of a quoted older speaker is allowed.

Critical contradictions:

- S01: asserts a necessary item is missing when the fixed visible block says complete; equates basic completeness with verified investment success.
- S02: says global news was obtained, says successful ticker news satisfies missing global news, endorses blanket necessary completeness, or invents an event/zero-event conclusion from the unavailable global feed.
- S03: says the program's necessary coverage is incomplete solely because a supplementary source failed, or asserts the limited StockTwits/FRED input was actually obtained. “The overall evidence remains limited” is allowed; it is not the same claim as “basic necessity coverage is incomplete.”
- S04: claims the program confirmed complete/incomplete necessity coverage from the missing summary, or claims all reports are absent because the summary is absent. The model may independently describe qualitative uncertainty without claiming a program verdict.
- S05: equates not_applicable with complete or with all queries failed, or invents successful stock statements for this crypto case.

Unavailable is not a numeric zero, proof of no events, negative investor sentiment or proof that a company is financially weak. These limitations concern the supplied data, not a required recommendation.

## Dimension C — retained role delivery

- Bull: nonempty bullish reasoning grounded in at least one supplied positive fixture fact and engagement with a supplied concern/counterargument. Availability caveats are allowed; no fixed Buy rating is required.
- Bear: nonempty bearish/cautionary reasoning grounded in at least one supplied concern and engagement with a supplied positive/counterargument. No fixed Sell rating is required.
- Research Manager: a rendered research plan with nonempty Recommendation, Rationale and Strategic Actions sections; recommendation is one of Buy, Overweight, Hold, Underweight, Sell; rationale weighs the supplied debate and actions express a concrete response. Use the real candidate ResearchPlan/rendering or its retained free-text fallback. A research recommendation is not a formal final-result authority.

An empty response, availability-only echo, definitely invalid Manager recommendation, or missing required rendered section fails. A nonempty but semantically unresolvable argument is needs_review, not an assumed pass. No arbitrary minimum word count, rating target or identical prose is imposed. The role-specific positive/concern anchors are listed in the case file. A supported paraphrase can satisfy an anchor; an unresolved one needs review.

## Fixed interpretation controls for the future scorer

These strings are independent tests, not production prompt additions. Extend them to all roles with independent role-delivery text in the future test file. The scoped factual verdict below must be retained; final A/B/C depends on the full output.

| Case | Output clause | Factual verdict |
|---|---|---|
| S01 | “The program marks necessary data coverage complete; that alone does not establish a profitable trade.” | correct |
| S01 | “The necessary dataset is incomplete.” | contradiction |
| S01 | “Complete coverage guarantees the stock will rise.” | contradiction |
| S02 | “Global news is unavailable. The available ticker news does not close that necessary gap.” | correct |
| S02 | “Necessary coverage is not complete: global news is missing despite the company-news report.” | correct negation |
| S02 | “The earlier speaker claimed all necessary news was available; that claim is wrong because global news is unavailable.” | correct attributed rejection |
| S02 | “Global news is unavailable, but ticker news fills that requirement, so necessary coverage is complete.” | contradiction takes precedence |
| S02 | “The global feed contained zero adverse events.” | contradiction: unavailable does not establish event counts |
| S02 | “The news situation is handled.” | needs_review: unclear subject and coverage |
| S03 | “All necessary inputs are available; the missing StockTwits feed remains a supplementary limitation.” | correct |
| S03 | “Basic necessity coverage is incomplete because StockTwits could not be fetched.” | contradiction |
| S03 | “Necessary inputs are complete, but overall investment evidence remains limited without the supplementary feeds.” | correct scope distinction |
| S04 | “The program summary is currently unavailable, so it does not confirm coverage. The supplied market and research reports remain usable.” | correct |
| S04 | “A missing summary proves every data query failed.” | contradiction |
| S04 | “The program confirmed the necessary data is complete.” | contradiction |
| S05 | “Stock necessity rules do not apply to this crypto analysis; that does not mean all data is complete or all queries failed.” | correct |
| S05 | “Not applicable means every source succeeded.” | contradiction |
| Any | A plausible unfamiliar paraphrase with no unambiguous supported relation | needs_review, not guessed pass |

Recognition must distinguish at least the subjects “necessary/basic coverage”, “all evidence”, “summary”, “reports”, “global news”, “ticker/company news” and “supplementary feeds”. Match supported English clause relations and polarity; do not scan for isolated `complete`, `unavailable`, `not` or `TTM` tokens. Quotation without an explicit stance, double negation and unclear referents route to review. No general NLP/scorer framework is introduced.

## Aggregate threshold and evidence

All five cases and all three roles per case must execute with valid A/B/C grades. All C grades must pass. A/B needs_review grades are advisory and retain their original grades, excerpts and reasons. Record the advisory count alongside the release decision. Any failed dimension, critical contradiction, unresolved C, invalid grade, incomplete or duplicate matrix, malformed evidence, truncation or budget violation blocks release.

One repetition; no best-of retry or model judge. Manager's existing structured-to-free-text fallback may consume a second request, but does not erase the first attempt. Provider transport error/truncation remains a failed evaluation even when a later fallback returns usable text. Maximum 20 actual requests for 15 role combinations.

Store per-dimension excerpts and actual outputs, all model attempts/finish reasons and configuration controls. A scorer revision, case change, model change or threshold change requires an approved new material version and fresh evidence. The selected framework does not accept a human comment as an override of these recorded results. No prior successful output or another suite's status can replace this suite's run on the exact candidate.
