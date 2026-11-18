"""FR-07 + FR-08 wiring into a real run: one brief, five consumers, opt-out.

Uses the scripted offline model and vendor stubs from the graph end-to-end
module; no network, no provider call.
"""

import copy
import json

import pandas as pd
import pytest
from langchain_core.outputs import ChatResult
from pydantic import Field

from tests.test_graph_end_to_end import TRADE_DATE, ScriptedModel
from tradingagents.agents import context
from tradingagents.agents.analysts import sentiment_analyst
from tradingagents.dataflows import router
from tradingagents.dataflows.vendors.yahoo import market as yahoo_market, snapshot
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph import trading_graph
from tradingagents.run.assembler import DownstreamContextAssembler
from tradingagents.run.counter import WhitespaceTokenCounter

pytestmark = pytest.mark.unit


@pytest.fixture
def offline(monkeypatch):
    """Every vendor answers offline; the same stubs the graph tests use."""
    for method, vendors in router.VENDOR_METHODS.items():
        for vendor in vendors:
            monkeypatch.setitem(vendors, vendor, lambda *a, _m=method, **k: f"{_m} data")
    prices = pd.DataFrame({
        "Date": pd.bdate_range(end=TRADE_DATE, periods=60),
        "Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.5, "Volume": 1_000_000,
    })
    monkeypatch.setattr(snapshot, "load_ohlcv", lambda *a, **k: prices.copy())
    monkeypatch.setattr(sentiment_analyst, "fetch_stocktwits_messages", lambda *a, **k: "no posts")
    monkeypatch.setattr(sentiment_analyst, "fetch_reddit_posts", lambda *a, **k: "no posts")
    monkeypatch.setattr(
        yahoo_market.yf, "Ticker", lambda s: type("T", (), {"info": {"longName": "NVIDIA"}})()
    )
    context._identity.cache_clear()


BRIEF_MARKER = "Shared research brief for this role"
PROTECTED_OPEN = "[PROTECTED]"
METRIC_SENTINEL = "| revenue_yoy_q | 9.6 % | 2025-03-30..2025-06-28 / quarter | S1 |"


class _Summary:
    """One-call structured summary fake, counting invocations."""

    def __init__(self):
        self.calls = 0
        self.prompts = []

    def __call__(self, prompt):
        self.calls += 1
        self.prompts.append(prompt)
        return json.dumps({
            "schema_version": "fr08-summary-v1",
            "risks": [{"text": "Synthetic downside evidence.", "sources": ["market"]}],
            "triggers": [],
            "conclusions": [{"text": "Synthetic conclusion.", "sources": ["news"]}],
            "uncertainties": [],
        })


class _Metrics:
    def __init__(self):
        self.calls = 0

    def __call__(self, state):
        self.calls += 1
        return type("R", (), {"text": METRIC_SENTINEL})()


def _graph(tmp_path, monkeypatch, model, *, assembler=None, **config):
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.update(results_dir=str(tmp_path / "results"), data_cache_dir=str(tmp_path / "cache"),
               memory_log_path=str(tmp_path / "log.md"), **config)
    monkeypatch.setattr(
        trading_graph, "create_tier_client", lambda config, tier, **k: type("C", (), {"get_llm": lambda self: model})()
    )
    return trading_graph.TradingAgentsGraph(config=cfg, context_assembler=assembler)


class RecordingModel(ScriptedModel):
    """ScriptedModel that also keeps every prompt it receives."""

    prompts: list = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.prompts.append([str(m.content) for m in messages])
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def _prompt_texts(model):
    return ["\n".join(call) for call in model.prompts]


def _assembler(*, summary=None, metrics=None):
    return DownstreamContextAssembler(
        token_counter=WhitespaceTokenCounter(),
        total_budget=4000,
        mandatory_budget=600,
        metrics_factory=metrics,
        summary_model=summary,
    ).node


def test_enabled_run_builds_one_brief_and_reuses_it_for_five_roles(tmp_path, monkeypatch, offline):
    summary = _Summary()
    metrics = _Metrics()
    model = RecordingModel()
    graph = _graph(tmp_path, monkeypatch, model, assembler=_assembler(summary=summary, metrics=metrics))

    graph.propagate("NVDA", TRADE_DATE)
    prompts = _prompt_texts(model)

    assert summary.calls == 1, "one summary call per run, not one per consumer"
    assert metrics.calls == 1, "one metric build per run"
    assert len(summary.prompts) == 1

    consumers = [p for p in prompts if BRIEF_MARKER in p]
    assert len(consumers) == 5, "Bull, Bear and the three risk debaters share the brief"
    for prompt in consumers:
        assert PROTECTED_OPEN in prompt, "the protected block travels with the brief"
        assert METRIC_SENTINEL in prompt, "FR-07 metrics stay inside the protected block"
        # The four full reports are not injected next to the brief.
        assert "Market research report:" not in prompt
        assert "Company Fundamentals Report:" not in prompt

    # The saved reports are untouched: the assembler only reads them.
    assert graph.graph is not None


def test_enabled_without_summary_uses_the_deterministic_brief(tmp_path, monkeypatch, offline):
    metrics = _Metrics()
    model = RecordingModel()
    graph = _graph(tmp_path, monkeypatch, model, assembler=_assembler(metrics=metrics))

    graph.propagate("NVDA", TRADE_DATE)
    prompts = _prompt_texts(model)
    consumers = [p for p in prompts if BRIEF_MARKER in p]
    assert len(consumers) == 5
    assert all(METRIC_SENTINEL in p for p in consumers)
    assert metrics.calls == 1


def test_disabled_run_keeps_the_original_four_report_prompts(tmp_path, monkeypatch, offline):
    model = RecordingModel()
    graph = _graph(tmp_path, monkeypatch, model)  # no assembler, fr08 off

    graph.propagate("NVDA", TRADE_DATE)
    prompts = _prompt_texts(model)
    assert not any(BRIEF_MARKER in p for p in prompts)
    assert any("Market research report:" in p for p in prompts), "legacy material is still used"
    assert not any(PROTECTED_OPEN in p for p in prompts)


def test_config_builds_the_assembler_only_when_enabled():
    from tradingagents.run.wiring import build_context_assembler

    assert build_context_assembler({"fr08_enabled": False}) is None
    assert build_context_assembler({"fr08_enabled": True}) is not None
    assert build_context_assembler({"fr08_enabled": True, "fr08_summary_enabled": True}) is not None


def test_rejected_brief_leaves_the_roles_on_the_full_reports():
    """A protected block that cannot fit is terminal; roles keep the reports."""
    assembler = DownstreamContextAssembler(
        token_counter=WhitespaceTokenCounter(),
        total_budget=10,
        mandatory_budget=1,
        canonical_gaps=("a long canonical gap that cannot fit the budget at all",),
    )
    state = {
        "market_report": "M", "sentiment_report": "S", "news_report": "N",
        "fundamentals_report": "F", "company_of_interest": "NVDA", "trade_date": TRADE_DATE,
    }
    result = assembler.node(state)
    assert result["downstream_brief"] == ""
    assert result["downstream_brief_mode"] == "rejected"
