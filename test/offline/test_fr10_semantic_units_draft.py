"""Local post-implementation semantic-scorer examples; not live-model acceptance.

The positive reports are synthetic fixtures built from the pre-existing independent
reference. Negative reports deliberately corrupt one claim. No LLM is invoked and
no new rule, threshold, production prompt or CI workflow is introduced.
"""

import json
from pathlib import Path

import pytest

from test_financial_metrics_evaluation import _good_report, fm_eval

ROOT = Path(__file__).resolve().parents[2]
DRAFT = json.loads((ROOT / "docs/drafts/fr10-semantic-units.json").read_text(encoding="utf-8"))
REFERENCE = json.loads((ROOT / DRAFT["reference_path"]).read_text(encoding="utf-8"))
CASES = {case["case_id"]: case for case in REFERENCE["cases"]}


def prompts_for(case):
    """Controlled ten-row input, independent of the candidate calculator."""
    rows = []
    for row in case["expected_rows"]:
        value = (f"{row['expected_display']} {row['unit']}" if row["status"] == "computed"
                 else f"n/a: {row['reason']}")
        rows.append(f"| {row['metric_id']} | {value} |")
    return [{"role": "system", "content": "\n".join(rows)}]


def score(unit, report):
    case = CASES[unit["reference_case"]]
    return fm_eval.score_candidate_case(case, prompts_for(case), report, REFERENCE["reference_data"])


@pytest.mark.parametrize("unit", DRAFT["units"], ids=lambda unit: unit["id"])
def test_draft_reference_example_has_no_scorer_objection(unit):
    """Synthetic positive control: scorer accepts the independently specified report fixture."""
    assert DRAFT["status"] == "draft_pending_review"
    verdict = score(unit, _good_report(CASES[unit["reference_case"]]))
    assert verdict["passed_checks"] == 5
    assert verdict["critical_failures"] == []
    assert verdict["needs_review_reasons"] == []


@pytest.mark.parametrize("unit", DRAFT["units"], ids=lambda unit: unit["id"])
def test_draft_single_claim_counterexample_is_rejected_or_reviewed(unit):
    """Constructed counterexamples exercise the existing scorer, not a second evaluator."""
    report = _good_report(CASES[unit["reference_case"]])
    mutation = unit["counterexample"]
    if mutation["operation"] == "append":
        report += "\n" + mutation["text"]
    else:
        assert mutation["operation"] == "remove_metric_row"
        marker = f"| {mutation['metric_id']} |"
        assert marker in report
        report = "\n".join(line for line in report.splitlines() if not line.startswith(marker))
    verdict = score(unit, report)
    if unit["expected_outcome"] == "critical_failure":
        assert unit["expected_reason"] in verdict["critical_failures"]
    else:
        assert unit["expected_outcome"] == "needs_review"
        assert verdict["critical_failures"] == []
        assert unit["expected_reason"] in verdict["needs_review_reasons"]
