# FR-10 local semantic checks — 2026-11-25

**Latest status:** All four candidate cases now have complete real model replies and pass the local five-gate checker. The separate final-stage S04 rerun is recorded below. Earlier incomplete/replay results remain as dated progression, not the latest status. See the [evidence index](../evidence/fr10-local-20261125/index.md).

User-authorized local maintenance, after observing false negatives in the earlier
live evaluation. The checker and tests are now executable files in the submission
under `scripts/` and `test/offline/`; see the [current test entry](../ci/fr10-report-checks.md).
They do not replace the frozen D1–D5 rubric or change a GitHub workflow.
No application code, model prompt, independent numerical oracle, threshold,
historical result, or approval record was changed.

## Five bounded checks

| Gate | What is checked | Negative example |
|---|---|---|
| Injection | The first captured system prompt has all ten independent expected values/statuses | Remove the supplied metric table |
| Values | Each explicit metric-table assertion has the expected number and unit; canonical prose assertions must not contradict it | Replace quarterly YoY with QoQ; substitute a ratio unit |
| Period and units | At least one complete period/span assertion per metric; explicit contradictory dates/spans fail | Label YTD cash flow as a quarter |
| Sources | Source aliases resolve to the actual captured program table/legend; fabricated aliases/accessions fail | Replace `S13,S14` with another metric's sources or `S999` |
| Unavailable and basis | `n/a` and its reason are retained; affirmative numeric TTM/quarterly-FCF claims fail | Invent a value for missing comparison or ineligible price |

Common metric labels, Unicode minus signs, currency prefixes, and Markdown
formatting are accepted. A repeated shorter summary may refer to an earlier
complete metric table. “TTM P/E was not computed” is not a TTM assertion.
A gross-profit dollar amount is not interpreted as a gross-margin percentage.
Baseline and candidate use the same report-completion check. Tool-intent-only
responses are incomplete, not numerical FR-10 failures and not passes.

These are deterministic checks of explicit report assertions, not a general NLP
truth/completeness evaluator. Arbitrary paraphrased contradictions may still need
human review. They do not prove investment quality or task-wide equivalence.

## Executed results

- New checker tests: **32 passed**, covering real complete replies and deliberately
  wrong values, periods, units, sources, unavailable values and basis assertions.
- Replay of saved live candidate responses: **FM-S01/S02/S03 each pass 5/5**;
  **FM-S04 incomplete** (only tool-call intent, no final report).
- Baseline completion: FM-S01 incomplete; FM-S02 complete. No paired S01 quality
  comparison can be inferred from the incomplete baseline.
- Combined new and existing evaluator/FR-10/Round-04 scorer suites:
  **70 passed, 1 failed**. The failure is the old requirements-inventory assertion
  expecting 7 active requirements/37 criteria; current main has 5/28, with 9/37
  deferred. This task does not edit that unrelated registry or assertion.
- Ruff check and format checks are run on the two new Python files.
- **Zero new model requests**, no GitHub workflow changes, no remote publication.

The fixture contains exact saved response text and prompts, plus original file
hashes. It does not fabricate a completed S04. The S04 positive/negative unit test
is expressly synthetic and is not counted as real model acceptance.

## Reproduction

From the repository root, using an environment with the existing dev dependencies:

```powershell
python -B -m pytest test/offline/test_fr10_local_gates.py -q -p no:cacheprovider
python -B scripts/fr10_local_gates.py --evidence 'D:\CityU\cs5351\project\fr10-acceptance-20261125-01' --output '<new-local-result.json>'
```

The CLI creates a new result file exclusively, preserving earlier evidence. Its
JSON explicitly states `formal_acceptance: not_claimed`. Local results are in
`D:\CityU\cs5351\project\fr10-local-gates-20261125-01\replay-final.json`.
Completing the real S04 final report and the missing paired baseline report is
still necessary before claiming the original six-response evaluation completed.

## S04 replay correction — final-report stage

The local preparation command now explicitly selects `capture_stage=final_report`.
It captures the application's existing `WRAP_UP` path with frozen statement
material and the same S04 program metric table. That path does not bind tools.
The original initial-turn capture remains available for tool-selection tests;
GitHub workflows and the normal application remain unchanged.

Added four offline checks for final-stage selection, one model invocation with
no tool binding, preservation of all ten metrics and `price_not_completed`, and
rejection of an unknown stage. New/local checks plus selected existing projection
and scorer regressions: **38 passed, 9 deselected**. No skipped test is counted as
passed. The first attempt hit a temporary-directory setup error; rerunning with
the established workspace TEMP/TMP succeeded. Ruff lint passed; the two new/local
files pass formatting. The old evaluator has existing whole-file formatting
issues, which were not mass-reformatted in this narrow change.

Real installed-candidate offline capture succeeded and is saved at:
`D:\CityU\cs5351\project\fr10-local-gates-20261125-01\s04-final-report-prepared.json`.
It contains prepared messages and import origins, **not a new model response**.
The actual saved S04 remains incomplete until a real final-report request is run.

## S04 real final-report rerun — 2026-11-25

One real `deepseek-flash` request was made to the official DeepSeek endpoint,
with thinking disabled, no tools and zero retries. It finished with `stop` and
returned a complete visible report. API usage: input 3,032, output 4,050, total
7,082 tokens; latency 17.33 seconds. The local five-gate checker passed 5/5.

The report explicitly keeps FY P/E `n/a: price_not_completed`, explains that the
price completed one second after the cutoff and is ineligible, and retains the
other nine computed metrics. No application change was needed. Exact request,
response metadata, full report and result are saved under:
`D:\CityU\cs5351\project\fr10-local-gates-20261125-01\s04-live-final-report\`.

The three earlier complete candidate responses and this separate final-stage S04
response now all pass the local checker. This is not a claim that the original
frozen D1-D5 run or paired baseline S01 completed, nor a GitHub CI result. The old
incomplete S04 response and historical failed results remain unchanged.


## Executable submission update

The corrected checker, optional final-stage capture helper, both test modules and
both required fixture files are installed at their normal repository paths in
the revised archive. Evidence snapshots remain as history. The report-check
module now has 33 checks including the saved real final-stage S04, and the
finalization module has four, totaling 37 runnable offline checks.
