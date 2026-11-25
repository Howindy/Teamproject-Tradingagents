"""S04 replay finalization, using the existing analyst no-tools wrap-up path.

No provider calls. Expectations are unchanged: P/E is unavailable; the other nine
metrics remain present. These wiring tests are not a completed real S04 report.
"""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FinalOnlyModel(BaseChatModel):
    calls: int = 0
    captured: list = []

    @property
    def _llm_type(self):
        return "offline-final-report-check"

    def bind_tools(self, tools, **kwargs):
        raise AssertionError("Final-report replay must not bind tools")

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls += 1
        self.captured = messages
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content="FINAL_REPORT_FIXTURE"))]
        )


def test_s04_uses_existing_final_path_with_all_metrics_and_no_tool_binding():
    from tradingagents.agents.analysts.turn import WRAP_UP

    analyst = load(
        "local_final_analyst", ROOT / "src/tradingagents/agents/analysts/fundamentals_analyst.py"
    )
    records = json.loads(
        (ROOT / "test/fixtures/fr10-live-replay-20261125.json").read_text(encoding="utf-8")
    )["records"]
    case = json.loads((ROOT / "docs/ci/financial-metrics-cases.json").read_text(encoding="utf-8"))[
        "cases"
    ][3]
    system = next(m["content"] for m in records[3]["prompts"] if m["role"] == "system")
    metrics = "Program financial metrics" + system.split("Program financial metrics", 1)[1]
    llm = FinalOnlyModel()
    node = analyst.create_fundamentals_analyst(
        llm, metrics_factory=lambda state: SimpleNamespace(text=metrics, reason=None)
    )
    result = node(
        {
            "trade_date": case["as_of"],
            "company_of_interest": case["ticker"],
            "messages": [
                HumanMessage(content=case["task"] + "\n" + case["statement_material"]),
                HumanMessage(content=WRAP_UP),
            ],
        }
    )
    assert llm.calls == 1
    assert result["fundamentals_report"] == "FINAL_REPORT_FIXTURE"
    assert llm.captured[-1].content == WRAP_UP
    assert "none; your tool rounds are spent" in llm.captured[0].content
    for row in case["expected_rows"]:
        assert row["metric_id"] in llm.captured[0].content
    assert "price_not_completed" in llm.captured[0].content
    assert "n/a" in llm.captured[0].content
    assert case["statement_material"] in llm.captured[-2].content


@pytest.mark.parametrize("stage", ["initial", "final_report"])
def test_capture_stage_is_forwarded_without_a_model_call(stage):
    scripts = str(ROOT / "scripts")
    sys.path.insert(0, scripts)
    try:
        evaluator = load("final_replay_evaluator", ROOT / "scripts/financial_metrics_eval.py")
    finally:
        sys.path.remove(scripts)
    with patch.object(
        evaluator.subprocess,
        "run",
        return_value=SimpleNamespace(
            returncode=0, stdout=json.dumps({"status": "ok", "capture_stage": stage}), stderr=""
        ),
    ) as run:
        result = evaluator._run_prompt_capture_subprocess(
            checkout_root=ROOT,
            mode="candidate",
            case={},
            reference_data={},
            python_executable=sys.executable,
            capture_stage=stage,
        )
    assert result["capture_stage"] == stage
    assert json.loads(run.call_args.kwargs["input"])["capture_stage"] == stage


def test_final_path_cannot_be_selected_by_an_unknown_stage():
    scripts = str(ROOT / "scripts")
    sys.path.insert(0, scripts)
    try:
        evaluator = load("invalid_replay_evaluator", ROOT / "scripts/financial_metrics_eval.py")
    finally:
        sys.path.remove(scripts)
    with pytest.raises(evaluator.CiError, match="unsupported prompt capture stage"):
        evaluator._run_prompt_capture_subprocess(
            checkout_root=ROOT,
            mode="candidate",
            case={},
            reference_data={},
            python_executable=sys.executable,
            capture_stage="pretend_passed",
        )
