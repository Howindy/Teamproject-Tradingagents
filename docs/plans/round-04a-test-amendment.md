# Round-04A supplemental test specification

## 1. Decision requested

Approve adapting the 58 existing offline cases in section 4 to the Round-04A formal-result contract. The implementation under review is `66b75ed224be739482c01cc6631d9c80ea825a09`; the frozen test commit is `8babc1ab7f97f9632e04a7544865ee70aacf95d0`. The original [Round-04A plan](round-04a.md) was approved at `838447f1a24edcf1633daa6061299140a1ba1582`. [Original approval on PR #24](https://github.com/Howindy/Teamproject-Tradingagents/pull/24#issuecomment-7142585900).

In the paired audit, all 58 cases passed on the test commit and failed on the implementation commit. Fourteen real graph cases produced a blocked gate and REVIEW. Thirteen HTML cases passed their original assertions when supplied with a complete formal result in memory. The candidate separately passed the 47 frozen acceptance cases and 181 core regressions. The FR-10 preparation check P07, mypy baseline maintenance and three Windows lock failures have separate review tracks.

## 2. Contract and permitted adjustments

FR-04-FC05, SB-01-FC05 and INV-01-FC01 through FC03 govern transport, formal authority and persistence. The Portfolio Manager produces the advisory proposal. SB-01 owns the formal result. Preserve the existing observations and side-effect assertions for FR-03, reporting, checkpointing, settlement and memory.

| Rule | Minimum adjustment |
|---|---|
| F — complete a fixture (37 cases) | Add the missing IF-19 fields at the existing producer or fixture boundary. A passed fixture carries `model_proposal` with rating and original text, `gate_status="passed"`, an explicit legal `final_rating`, the original nonblank `final_trade_decision` and `reasons=[]`. For the blocked CLI fixture use `gate_status="blocked"`, `final_rating="REVIEW"`, a formal notice and a substantive reason. Keep the original payloads, consumer calls and assertions listed below. Share a local fixture where cases already use one. |
| G — real graph outcome (14 cases) | Keep the original analyst selection, external responses, missing purchase scenario and actual graph/evaluators. For these stock Overweight proposals expect a blocked gate and formal REVIEW. Where the old test checked a proposal marker, distinguish the Overweight proposal from the checked signal, manual-review body or memory record. Preserve the independent FR-03 evidence and any necessary-data gaps. |
| P — PM output (2 cases) | Inspect `model_proposal.rating` and `model_proposal.text` at the PM node. Assert that the PM leaves the formal rating and decision to the final check. |
| E — invalid formal input (2 cases) | Update the superseded success or text-fallback expectation. Incomplete formal results must raise before successful delivery or persistence. |
| H — report header (2 cases) | State the expected rating independently in the fixture and assert that the report projects it. Keep both parameterized branches. |
| D — decision file (1 case) | Supply a complete checked result. The formal section file carries a rating line and the original decision body. Keep the exact body comparison after accounting for the rating line. |

Use literal expected values. Keep the actual validator, gates, writers and memory adapters on paths that currently exercise them. Preserve all other existing assertions, including those after the first failed assertion. A newly exposed failure on valid input requires diagnosis before changing its expectation.

## 3. Allowed files

- `test/offline/test_cli_display.py`
- `test/offline/test_cli_headless.py`
- `test/offline/test_cli_memory_log.py`
- `test/offline/test_fr03_integration.py`
- `test/offline/test_graph_end_to_end.py`
- `test/offline/test_memory_log.py`
- `test/offline/test_portfolio_context.py`
- `test/offline/test_rating_integrity.py`
- `test/offline/test_report_html.py`
- `test/offline/test_reporting.py`

## 4. Case inventory

Each identifier below is relative to its file under section 3. Parameter variants count separately. The rule column refers to section 2.

### test_cli_display.py (2)

| Case | Rule | Assertions to retain or replace |
|---|---|---|
| `test_the_state_log_keeps_non_ascii_readable` | F | Preserve the readable Chinese characters in the saved JSON, the absence of Unicode escape sequences for those characters and successful JSON decoding. |
| `test_the_state_log_names_each_field_as_the_state_does` | F | Keep the trader plan under its state key, preserve its original text and retain the checks against duplicate or obsolete decision keys. |

### test_cli_headless.py (5)

| Case | Rule | Assertions to retain or replace |
|---|---|---|
| `test_save_and_show_answer_the_questions_after_the_run` | F | Preserve explicit save/show choices, the created report path, suppressed display and the fail-on-prompt sentinel. |
| `test_a_saved_report_includes_the_html_page_unless_declined` | F | Preserve the HTML default, explicit opt-out, and Markdown output in both directories. |
| `test_an_interactive_run_asks_for_the_html_page_and_opens_it` | F | Preserve the interactive HTML/browser questions and the exact page URI opened. |
| `test_without_a_browser_window_the_page_is_not_offered_for_opening` | F | Preserve file creation and the absence of a browser question when a graphical browser is unavailable. |
| `test_a_page_the_browser_cannot_open_is_pointed_to` | F | Preserve the fallback message identifying the saved HTML file when opening it fails. |

### test_cli_memory_log.py (7)

| Case | Rule | Assertions to retain or replace |
|---|---|---|
| `test_record_decision_appends_a_pending_entry` | F | Supply a checked Buy at record_decision. Keep one pending NVDA record and the exact stored rating. |
| `test_record_decision_skips_a_run_without_a_decision` | E | Keep the empty state. Expect an execution error before persistence and an empty memory log. Disabled memory and duplicate-date no-op coverage remains in the frozen suite. |
| `test_cli_run_uses_the_memory_log_like_propagate` | F | Complete the final fake stream chunk. Keep the exact create-run-state then record-decision call sequence, ticker, date and recorded body. |
| `test_the_cli_run_does_not_announce_a_resume[prior-checkpoint]` | F | Complete the final fake chunk. Preserve the prior-checkpoint input and absence of any automatic resume announcement. |
| `test_the_cli_run_does_not_announce_a_resume[no-checkpoint]` | F | Use the same final-chunk change. Preserve the no-checkpoint input and the same no-resume assertion. |
| `test_a_run_without_checkpointing_says_nothing_about_resuming` | F | Keep the existing no-checkpoint configuration and the absence of both resume and fresh-run announcements. |
| `test_recording_a_run_writes_its_state_log` | F | Complete the state passed to the real recorder. Preserve the date-specific state-log path and the actual write. |

### test_fr03_integration.py (11)

| Case | Rule | Assertions to retain or replace |
|---|---|---|
| `test_r03_10_programmatic_terminal_summary_state_and_report` | G | Retain the real collector, five-field terminal summary, and Markdown/HTML assertions for completeness and necessary gaps. |
| `test_r03_10_independent_save_uses_passed_state_not_live_scope` | F | Complete state A only where required. Retain the active B scope, A-only report markers, unchanged A input and fail-on-live-registry assertions. |
| `test_r03_10_null_terminal_shows_unavailable_fixed_text` | G | Retain the independent report-stage unavailable literal, its distinction from research text and its presence in Markdown and HTML. |
| `test_r03_10_snapshot_failure_warns_without_changing_result` | G | Retain the controlled snapshot failure, warning and terminal-summary assertions. Verify the formal decision already reached at check time. |
| `test_r03_11_program_entry_no_resume_full_execution` | G | Keep the fresh programmatic run, populated reports, zero forbidden checkpoint calls and byte-identical seeded checkpoint. |
| `test_r03_11_cli_entry_no_resume` | G | Compare the recorded CLI body to the checked manual-review conclusion. Keep real streaming, checkpoint guards and byte-identical prior checkpoint. |
| `test_r03_12_compat_return_and_existing_behavior` | G | Preserve the return pair, ticker/date identity, saved JSON path and recorded decision. Expect the checked rating in the return and memory. |
| `test_r03_10_programmatic_terminal_ready_before_record_once` | G | Preserve one terminal snapshot, one record call and identity of the summary object already present at recording. |
| `test_r03_10_terminal_failure_record_gets_null_and_no_extra_calls` | G | Keep the null terminal summary, exactly one attempted terminal snapshot and the original call-count guards. The terminal failure cannot revise the checked outcome. |
| `test_r03_10_report_and_display_mapping_null_absent` | F | Supply complete formal fields in all three cases. Keep mapping/null/absent availability distinct and retain the independent Markdown, HTML and CLI expectations. |
| `test_r03_10_independent_save_ab_md_html_display` | F | Complete the two states while retaining distinct A/B markers, real independent saving and all Markdown, HTML and display isolation assertions. |

### test_graph_end_to_end.py (6)

| Case | Rule | Assertions to retain or replace |
|---|---|---|
| `test_a_full_run_reaches_a_logged_decision[free-text]` | G | Preserve the free-text model, report contents, real tool/vendor call set and one memory record. Verify the checked rating is recorded. |
| `test_a_full_run_reaches_a_logged_decision[structured]` | G | Preserve the structured model and the same tool/report/memory coverage. Check its Overweight proposal separately. |
| `test_an_interrupted_run_reexecutes_fully_instead_of_resuming` | G | Keep the injected interruption, original exception, second full model-call schedule and byte-identical prior checkpoint evidence. |
| `test_a_debug_run_prints_the_analysts_work_and_reaches_the_same_decision` | G | Keep debug streaming, nonempty reports and captured tool names. Check its formal signal. |
| `test_an_analyst_that_keeps_calling_tools_writes_its_report_at_the_limit` | G | Keep the exact tool-round count and the original final analyst report texts at the limit. |
| `test_a_settlement_failure_is_noted_and_the_run_goes_on` | G | Preserve the settlement failure, continued analysis and memory warning in both state and saved report. |

### test_memory_log.py (3)

| Case | Rule | Assertions to retain or replace |
|---|---|---|
| `TestPortfolioManagerInjection::test_pm_returns_rendered_markdown_with_rating` | P | Read the structured PM output from model_proposal. Keep the Overweight rating, summary, thesis, price target and time horizon checks. |
| `TestPortfolioManagerInjection::test_pm_falls_back_to_freetext_when_structured_unavailable` | P | Read the free-text proposal. Preserve the exact original Sell prose and its proposal rating. |
| `TestLegacyRemoval::test_full_pipeline_no_regression` | F | Complete the fake graph result. Keep real propagation/recording and one pending entry for the expected ticker. |

### test_portfolio_context.py (1)

| Case | Rule | Assertions to retain or replace |
|---|---|---|
| `test_completed_portfolio_run_preserves_old_checkpoint_without_auto_clear` | F | Complete only the fake terminal result. Preserve portfolio transport, fresh graph input, forbidden checkpoint operations and byte-identical seeded evidence. |

### test_rating_integrity.py (2)

| Case | Rule | Assertions to retain or replace |
|---|---|---|
| `test_the_cli_says_when_a_run_produced_no_usable_rating` | F | Supply a blocked REVIEW and a manual-review notice in the fake stream. Keep the real CLI summary path and its visible review message. |
| `test_a_state_without_the_typed_rating_reads_it_from_the_decision` | E | Supply a complete checked Hold with a conflicting Buy label and assert Hold. For decision-only and empty states, require an execution error. Keep direct text-parser tests independent. |

### test_report_html.py (13)

| Case | Rule | Assertions to retain or replace |
|---|---|---|
| `test_the_html_page_is_written_unless_declined` | F | Preserve HTML default/opt-out, generated files, document structure, ticker, rating, date and rendered market table. |
| `test_the_markdown_report_is_the_same_with_or_without_html` | F | Preserve Markdown equality across HTML on/off after removing only the generated timestamp. |
| `test_the_page_loads_nothing_and_runs_nothing` | F | Preserve the content-security policy and all existing prohibitions on scripts and remote or embedded assets. |
| `test_report_text_cannot_inject_markup_or_fetch_anything` | F | Retain the hostile input and every assertion about escaped markup, disallowed links and remote loads. |
| `test_header_values_are_escaped` | F | Keep the existing header input and exact escaping checks for ticker and model text. |
| `test_an_agent_s_own_headings_sit_below_its_heading` | F | Keep exactly one top-level heading and the agent heading hierarchy. |
| `test_run_details_show_each_value_as_its_own_field` | F | Preserve separate provider, model, analyst and vendor fields, their ordering and user-facing labels. |
| `test_the_contents_name_each_section_once_and_list_its_agents_beneath` | F | Preserve navigation hierarchy, section and agent anchors and the existing numbering checks. |
| `test_the_section_rail_opens_on_hover_and_keyboard_focus` | F | Preserve hover and keyboard-focus behavior and accessibility of navigation labels. |
| `test_the_sections_stay_within_reach` | F | Preserve the top anchor, reachable sections, fixed section rail and top link. |
| `test_the_page_heading_is_the_ticker_and_its_rating` | F | Preserve the exact visible ticker and Overweight rating in the page heading. |
| `test_the_header_carries_the_official_logo_unaltered` | F | Preserve the unmodified packaged logo, link, accessible label and placement. |
| `test_the_page_credits_its_maker_in_a_line_of_text` | F | Preserve footer wording, project and organization links, placement and absence of a second logo. |

### test_reporting.py (8)

| Case | Rule | Assertions to retain or replace |
|---|---|---|
| `test_write_report_tree_creates_files` | D | Retain all existing file paths, analyst/trader bodies and consolidated report checks. In decision.md assert the checked rating and exact formal body within the file separately. |
| `test_save_reports_explicit_path` | F | Preserve the caller-provided directory, complete report creation and returned Path. |
| `test_save_reports_defaults_under_results_dir` | F | Preserve results_dir, ticker-stamped reports directory and returned file. |
| `test_the_report_names_the_analysis_date_and_what_produced_it` | F | Preserve date, version, model tiers, analyst names, debate rounds and vendor metadata. |
| `test_a_partial_settings_dict_still_writes_the_report` | F | Retain the partial settings dictionary, successful write and provider in the report. |
| `test_the_report_header_names_the_rating[**Rating**: Overweight\n\nAdd on weakness.-Overweight]` | H | Supply explicit passed/Overweight fields. Preserve the Overweight header assertion and original passed conclusion. |
| `test_the_report_header_names_the_rating[Add on weakness.-REVIEW]` | H | Supply blocked/REVIEW, a reason and a formal manual-review notice. Retain the unlabelled source text in the proposal and the REVIEW header assertion. |
| `test_the_header_names_the_analysts_as_users_select_them` | F | Preserve display names, including sentiment, across Markdown and HTML and retain the field-level assertions. |

## 5. Verification after approval

Run each listed file with its original parameterization, then match the 58 case IDs above to passing results in JUnit. Running the files also exercises their unaffected neighbors. Run the frozen 47 integration and contract cases and the 181 core regressions unchanged. Finally run the repository's default pytest selection and compare node IDs against the audited candidate (1,986 passed, 62 failed, one skipped, one deselected). With the same environment and selection, resolving exactly these 58 would leave four known failures. Investigate any difference by case ID. Record the commit, command, environment, pass/fail/skip counts and evidence of assertions previously hidden behind failing fixtures.

## 6. Supplemental pre-approval

An independent human reviewer on PR #24 should verify the 58 named cases, the ten-file boundary, the independent expected values, and the assertions preserved in section 4. Freeze this document alone. Before any affected test edit, obtain the following marker in a PR comment, replacing the placeholder with the full commit SHA of this document.

```text
APPROVED test-spec: docs/plans/round-04a-test-amendment.md @ <full supplemental specification SHA>
```

After approval, record the actual comment URL, reviewer and time. Retain the primary specification, original approval event and original implementation start. Add the separate PR field below and later record the first supplemental test-change commit.

```text
Supplemental test specification: docs/plans/round-04a-test-amendment.md @ <full supplemental specification SHA> (approval: <actual PR #24 approval URL>)
```

Reapprove the affected specification before extending the file or case list, changing an oracle or relaxing a retained assertion. The existing ADR 001 approval continues to cover the frozen product behavior. A proposed change to formal authority, validation, output fallback or evaluator behavior requires separate contract and safety review. P07, the mypy baseline and Windows locking each require their own scope before changes. Final review and merge remain separate from this pre-approval.
