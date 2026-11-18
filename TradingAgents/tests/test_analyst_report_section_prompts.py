"""Analyst prompts: the retired FR-08 section contract stays retired.

The model deliberately returns fixed text regardless of its prompt. These tests
check instruction delivery and invocation counts, not real model compliance.
Malformed or arbitrary text must be returned as-is, never trigger an
analyst-side formatting-repair invocation.
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable

from tradingagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst
from tradingagents.agents.analysts.market_analyst import create_market_analyst
from tradingagents.agents.analysts.news_analyst import create_news_analyst
from tradingagents.agents.analysts.turn import WRAP_UP

pytestmark = pytest.mark.unit

ANALYSTS = (
    (create_market_analyst, "market_report"),
    (create_news_analyst, "news_report"),
    (create_fundamentals_analyst, "fundamentals_report"),
)


class FixedReportModel(Runnable):
    """A local Runnable compatible with both take_turn branches."""

    def __init__(self, response):
        self.response = response
        self.calls = []
        self.bound_tools = []

    def bind_tools(self, tools, **kwargs):
        self.bound_tools.append(tuple(tools))
        return self

    def invoke(self, input, config=None, **kwargs):
        self.calls.append(input.to_messages())
        return AIMessage(content=self.response)


def _run(factory, report_key, wrap_up, response):
    model = FixedReportModel(response)
    state = {
        "company_of_interest": "DEMO",
        "asset_type": "stock",
        "trade_date": "2026-10-19",
        "messages": [HumanMessage(content=WRAP_UP)] if wrap_up else [],
    }
    result = factory(model)(state)
    assert len(model.calls) == 1
    assert len(model.bound_tools) == (0 if wrap_up else 1)
    assert result[report_key] == response
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == response
    system = "\n".join(message.content for message in model.calls[0] if message.type == "system")
    return system


@pytest.mark.parametrize("factory,report_key", ANALYSTS, ids=["market", "news", "fundamentals"])
@pytest.mark.parametrize("wrap_up", [False, True], ids=["normal-final", "tool-budget-wrap-up"])
def test_retired_section_contract_is_absent_from_final_report_prompt(factory, report_key, wrap_up):
    system = _run(factory, report_key, wrap_up, "Ordinary report text.")
    assert "FR08-SECTION" not in system
    assert "Risks: <main supported risks" not in system
    assert "Markdown table" in system


@pytest.mark.parametrize("factory,report_key", ANALYSTS, ids=["market", "news", "fundamentals"])
@pytest.mark.parametrize("wrap_up", [False, True], ids=["normal-final", "tool-budget-wrap-up"])
def test_arbitrary_report_text_still_does_not_add_format_repair_call(factory, report_key, wrap_up):
    _run(factory, report_key, wrap_up, "Unstructured final report without any marked section.")
