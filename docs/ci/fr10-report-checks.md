# FR-10 report checks included in the submission

The corrected checks are executable repository files, not only archived evidence
snapshots. They are automatically collected from the ordinary offline test tree.
GitHub workflows, application code and the independent numerical reference are
unchanged by this packaging update.

## Executable files

- [Checker](../../scripts/fr10_local_gates.py): injection, values/units, periods,
  sources and unavailable/basis assertions.
- [Report regression tests](../../test/offline/test_fr10_local_gates.py): the
  three original complete real replies, the separate real S04 final report,
  and deliberate wrong-value/period/source/unavailability counterexamples.
- [Final-stage replay tests](../../test/offline/test_fr10_final_report_replay.py):
  the existing analyst wrap-up path, without binding tools or making paid calls.
- [Capture helper](../../scripts/financial_metrics_eval.py): optional
  `capture_stage="final_report"`; the original initial-turn mode is preserved.
- Fixtures: [original replies](../../test/fixtures/fr10-live-replay-20261125.json)
  and [real final S04](../../test/fixtures/fr10-s04-final-report-20261125.json).

## Run from the unpacked project root

Use a Python environment with this project's existing development dependencies:

```powershell
python -B -m pytest test/offline/test_fr10_local_gates.py test/offline/test_fr10_final_report_replay.py -q -p no:cacheprovider
```

There are **37 checks**: 33 report/checker regressions and four final-stage wiring
checks. This command is offline: it rechecks saved real answers and controlled
counterexamples, and does not call DeepSeek again. The actual prior live calls,
reports, usage and versioned results are available in the
[evidence index](../evidence/fr10-local-20261125/index.md).

The original incomplete S04 and unsuccessful frozen evaluation remain historical
evidence. This submission's report checks do not change the frozen D1-D5 rubric,
configuration approvals or remote workflow enforcement; those are distinct
records. No unexecuted GitHub check or independent human approval is asserted.

## Submission verification

Executed from the unpacked revised project root on 2026-11-25: **37 passed in
2.79 seconds**. See the [actual console output](../evidence/fr10-local-20261125/formal-tests-package-test-output.txt).
No paid model call was made during this packaging verification.
