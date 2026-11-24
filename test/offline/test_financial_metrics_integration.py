"""FR-10 FC09/FC10, ADR 002: real analyst/entries, FR-03 and Round 4 isolation.

Reuse Round 3's external vendor/model fixtures; no internal metric or graph path
is replaced. Financial facts are the independent synthetic AAPL/XOM projection.
"""

import copy

import pytest
from langchain_core.messages import HumanMessage
from pydantic import Field

from test.offline import test_fr03_integration as fr03
from test.offline.test_financial_metrics import projected
from tradingagents.agents.analysts.fundamentals_analyst import TOOLS, create_fundamentals_analyst
from tradingagents.agents.analysts.turn import WRAP_UP
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.financials.models import FinancialInputs
from tradingagents.financials.wiring import build_metrics_factory
from tradingagents.graph import trading_graph
from tradingagents.run_context import RunContext, current


class RecordingModel(fr03.ScriptedModel):
    prompts: list = Field(default_factory=list)

    def _generate(self, messages, **kwargs):
        self.prompts.append(messages[0].content)
        return super()._generate(messages, **kwargs)


@pytest.fixture
def external(monkeypatch, tmp_path):
    return fr03.offline.__wrapped__(monkeypatch, tmp_path)


def factory_and_reads(*, failure=False, unsupported=False):
    reads = []

    class Data:
        def fetch(self, ticker, as_of):
            reads.append((ticker, as_of))
            if failure:
                raise RuntimeError("synthetic external data failure")
            if unsupported:
                return FinancialInputs(ticker, issues=("not_supported:fixture",))
            return projected("aapl")

    return build_metrics_factory({}, data_factory=lambda clock: Data()), reads


def graph_for(tmp_path, monkeypatch, factory=None, *, debug=False, analysts=("fundamentals",)):
    model = RecordingModel(structured=True)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config.update(results_dir=str(tmp_path / "results"), data_cache_dir=str(tmp_path / "cache"),
                  memory_log_path=str(tmp_path / "memory.md"))
    monkeypatch.setattr(trading_graph, "create_tier_client", lambda *a, **k: fr03._Client(model))
    graph = trading_graph.TradingAgentsGraph(config=config, selected_analysts=analysts,
                                            debug=debug, metrics_factory=factory)
    return graph, model


def financial_prompts(model):
    return [p for p in model.prompts if "analyzing fundamental information" in p]


def test_first_tool_and_wrapup_keep_one_metric_table():
    factory, reads = factory_and_reads()
    model = RecordingModel()
    node = create_fundamentals_analyst(model, metrics_factory=factory)
    state = {"company_of_interest": "AAPL", "trade_date": "2025-08-05",
             "asset_type": "stock", "messages": [HumanMessage(content="Analyze AAPL")],
             "portfolio_risk_result": {"status": "blocked", "reasons": ["risk sentinel"]},
             "gate_status": "blocked", "final_rating": "REVIEW", "reasons": ["gate sentinel"]}
    before = copy.deepcopy(state)
    with factory.analysis_scope():
        result = node(state)
        assert {c["name"] for c in result["messages"][0].tool_calls} == {t.name for t in TOOLS}
        wrap = node({**state, "messages": [*state["messages"], *result["messages"],
                                         HumanMessage(content=WRAP_UP)]})
    assert wrap["fundamentals_report"]
    assert set(wrap) == {"messages", "fundamentals_report"}
    assert len(reads) == 1
    assert state == before
    assert len(financial_prompts(model)) == 2
    for prompt in financial_prompts(model):
        assert prompt.count("Program financial metrics (") == 1
        assert "| pe_fy | 33.4 x |" in prompt
        assert "matching metric and period" in prompt


@pytest.mark.parametrize("debug", [False, True])
def test_program_entry_two_runs_isolated_and_fr03_unchanged(tmp_path, monkeypatch, external, debug):
    factory, reads = factory_and_reads()
    graph, model = graph_for(tmp_path, monkeypatch, factory, debug=debug)
    with RunContext() as parent:
        first, signal = graph.propagate("NVDA", fr03.TRADE_DATE)
        assert current() is parent
        second, _ = graph.propagate("NVDA", fr03.TRADE_DATE)
        assert current() is parent
    assert len(reads) == 2
    assert all("Program financial metrics (" in p for p in financial_prompts(model))
    plain, plain_model = graph_for(tmp_path / "plain", monkeypatch)
    baseline, baseline_signal = plain.propagate("NVDA", fr03.TRADE_DATE)
    assert not any("Program financial metrics (" in p for p in financial_prompts(plain_model))
    assert signal == baseline_signal
    assert first["data_availability_summary"] == second["data_availability_summary"] == baseline["data_availability_summary"]
    assert first["research_availability_summary"] is not None
    for key in ("research_availability_summary", "trader_investment_plan", "final_trade_decision",
                "final_rating", "gate_status", "reasons", "portfolio_risk_result"):
        assert first.get(key) == baseline.get(key)
    assert not any("metric" in key for key in first)  # no infrastructure/bundle in graph state


@pytest.mark.parametrize("failure,unsupported", [(True, False), (False, True)])
def test_unavailable_metrics_do_not_abort_or_replace_availability(tmp_path, monkeypatch, external, failure, unsupported):
    factory, reads = factory_and_reads(failure=failure, unsupported=unsupported)
    graph, model = graph_for(tmp_path, monkeypatch, factory)
    state, signal = graph.propagate("NVDA", fr03.TRADE_DATE)
    assert state["fundamentals_report"] and signal
    assert state["data_availability_summary"] is not None
    assert len(reads) == 1
    prompts = financial_prompts(model)
    assert all("FR-10" in p for p in prompts)
    assert not any("| pe_fy | 33.4 x |" in p for p in prompts)


def test_omitted_fundamentals_never_fetches(tmp_path, monkeypatch, external):
    factory, reads = factory_and_reads()
    graph, _ = graph_for(tmp_path, monkeypatch, factory, analysts=("news",))
    graph.propagate("NVDA", fr03.TRADE_DATE)
    assert reads == []


def test_cli_uses_stream_metric_scope_without_changing_runcontext(tmp_path, monkeypatch, external):
    import cli.main as main
    import cli.run as cli_run
    from cli.models import AnalystType

    factory, reads = factory_and_reads()
    graph, model = graph_for(tmp_path, monkeypatch, factory)
    monkeypatch.setattr(cli_run, "TradingAgentsGraph", lambda *a, **k: graph)
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags=None: {
        "ticker": "NVDA", "analysis_date": fr03.TRADE_DATE,
        "analysts": [AnalystType.FUNDAMENTALS], "asset_type": "stock"})
    monkeypatch.setattr(cli_run, "_build_run_config", lambda *a: graph.config)
    monkeypatch.setattr(cli_run, "Live", fr03._NullLive)
    monkeypatch.setattr(cli_run, "create_layout", lambda: None)
    monkeypatch.setattr(cli_run, "update_display", lambda *a, **k: None)
    monkeypatch.setattr(main.typer, "prompt", lambda *a, **k: "N")
    with RunContext() as parent:
        for _ in range(2):
            cli_run.run_analysis(flags={"save": False, "show": False, "html": False})
            assert current() is parent
    assert len(reads) == 2
    assert all("Program financial metrics (" in p for p in financial_prompts(model))


def test_stream_close_restores_metric_and_fr03_scopes(tmp_path, monkeypatch, external):
    factory, reads = factory_and_reads()
    graph, _ = graph_for(tmp_path, monkeypatch, factory)
    initial = graph.create_run_state("NVDA", fr03.TRADE_DATE)
    with RunContext() as parent, factory.analysis_scope():
        prior = factory(initial)
        stream = graph.stream_run(initial, **graph.propagator.get_graph_args())
        for _, chunk in stream:
            if chunk and chunk.get("fundamentals_report"):
                break
        stream.close()
        assert factory(initial) is prior
        assert current() is parent
    assert len(reads) == 2


def test_interleaved_streams_keep_independent_metric_caches(tmp_path, monkeypatch, external):
    factory, reads = factory_and_reads()
    graph, _ = graph_for(tmp_path, monkeypatch, factory)
    initial = graph.create_run_state("NVDA", fr03.TRADE_DATE)
    streams = [graph.stream_run(initial, **graph.propagator.get_graph_args()) for _ in range(2)]
    try:
        with RunContext() as parent:
            # Pause both streams after their first analyst model turn.
            for stream in streams:
                next(stream)
                assert current() is parent
            for stream in streams:
                list(stream)
                assert current() is parent
    finally:
        for stream in streams:
            stream.close()
    assert len(reads) == 2


def test_program_entry_error_preserves_primary_and_restores_scope(tmp_path, monkeypatch, external):
    factory, reads = factory_and_reads()
    graph, _ = graph_for(tmp_path, monkeypatch, factory)
    initial = graph.create_run_state("NVDA", fr03.TRADE_DATE)

    def fail(*args, **kwargs):
        factory(initial)
        raise RuntimeError("primary producer error")

    monkeypatch.setattr(graph.graph, "invoke", fail)
    with RunContext() as parent, factory.analysis_scope():
        prior = factory(initial)
        with pytest.raises(RuntimeError, match="primary producer error"):
            graph.propagate("NVDA", fr03.TRADE_DATE)
        assert factory(initial) is prior
        assert current() is parent
    assert len(reads) == 2


def test_config_opt_in_and_disabled_prompt_unchanged():
    assert DEFAULT_CONFIG["fr10_sec_enabled"] is False
    assert build_metrics_factory(DEFAULT_CONFIG) is None
    # No new material or whitespace is inserted when no resolver is configured.
    model = RecordingModel()
    node = create_fundamentals_analyst(model)
    node({"company_of_interest": "AAPL", "trade_date": "2025-08-05", "messages": []})
    assert "FR-10" not in financial_prompts(model)[0]
    assert "Program financial metrics (" not in financial_prompts(model)[0]


def test_crypto_metrics_are_explicitly_unsupported_without_fetch():
    factory, reads = factory_and_reads()
    model = RecordingModel()
    node = create_fundamentals_analyst(model, metrics_factory=factory)
    with factory.analysis_scope():
        node({"company_of_interest": "BTC-USD", "trade_date": "2025-08-05",
              "asset_type": "crypto", "messages": []})
    assert reads == []
    assert "not_supported" in financial_prompts(model)[0]
