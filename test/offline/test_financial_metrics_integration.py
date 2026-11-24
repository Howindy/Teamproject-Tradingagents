"""FR-10 FC09/FC10, ADR 002: real analyst/entries, FR-03 and Round 4 isolation.

Reuse Round 3's external vendor/model fixtures; no internal metric or graph path
is replaced. Financial facts are the independent synthetic AAPL/XOM projection.
"""

import copy
import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

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


@pytest.mark.parametrize("case_index", range(4))
def test_actual_trusted_probe_uses_current_calculator_and_prompt(case_index):
    """FC01-FC10: original trusted projection/driver, real installed candidate, no API."""
    from test.offline.test_financial_metrics import DATA
    from test.offline.test_financial_metrics_evaluation import fm_eval

    case = DATA["cases"][case_index]
    captured = fm_eval._run_prompt_capture_subprocess(
        checkout_root=Path(__file__).resolve().parents[2], mode="candidate",
        case=case, reference_data=DATA["reference_data"], python_executable=sys.executable,
    )
    block = captured["metric_block"]
    rows = [line for line in block.splitlines() if line.startswith("| ")][1:]
    assert len(rows) == 10
    for expected, line in zip(case["expected_rows"], rows, strict=True):
        value = (f"{expected['expected_display']} {expected['unit']}" if expected["status"] == "computed"
                 else f"n/a: {expected['reason']}")
        assert line.startswith(f"| {expected['metric_id']} | {value} |"), line
        period = expected["period"]
        assert period["period_end"] in line and period["span"] in line
        for fid in expected["input_fact_ids"]:
            fact = DATA["reference_data"]["selected_facts"][fid]
            assert fact["filing_file"] + "#" + fact["inline_element_id"] in block
    assert captured["prompts"][0]["content"].count(block) == 1


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


def test_second_analysis_uses_changed_financial_facts(tmp_path, monkeypatch, external):
    """FC09: different vendor data on the same reusable graph must replace the old value."""
    reads = []

    class ChangingData:
        def fetch(self, ticker, as_of):
            reads.append(ticker)
            inputs = projected("aapl")
            return replace(inputs, price=replace(inputs.price, value=Decimal("60.8") * len(reads)))

    factory = build_metrics_factory({}, data_factory=lambda _: ChangingData())
    graph, model = graph_for(tmp_path, monkeypatch, factory)
    graph.propagate("NVDA", fr03.TRADE_DATE)
    first = list(financial_prompts(model))
    graph.propagate("NVDA", fr03.TRADE_DATE)
    second = financial_prompts(model)[len(first):]
    assert len(reads) == 2 and first and second
    assert all("| pe_fy | 10.0 x |" in p for p in first)
    assert all("| pe_fy | 20.0 x |" in p and "| pe_fy | 10.0 x |" not in p for p in second)


def test_initialization_failure_reused_and_next_analysis_recovers(tmp_path, monkeypatch, external):
    """FC10: constructor failure is once per analysis, not once per analyst turn."""
    attempts = []

    def data_factory(clock):
        attempts.append(clock)
        if len(attempts) == 1:
            raise RuntimeError("synthetic initialization failure")
        return type("Data", (), {"fetch": lambda self, ticker, as_of: projected("aapl")})()

    factory = build_metrics_factory({}, data_factory=data_factory)
    graph, model = graph_for(tmp_path, monkeypatch, factory)
    first, _ = graph.propagate("NVDA", fr03.TRADE_DATE)
    first_prompts = list(financial_prompts(model))
    assert first["fundamentals_report"]
    assert len(attempts) == 1 and len(first_prompts) >= 2
    assert all("n/a: data_entry_failure" in p for p in first_prompts)
    second, _ = graph.propagate("NVDA", fr03.TRADE_DATE)
    assert len(attempts) == 2 and second["fundamentals_report"]
    assert all("| pe_fy | 33.4 x |" in p for p in financial_prompts(model)[len(first_prompts):])


def test_bad_provider_payload_is_unavailable_not_analysis_failure(tmp_path, monkeypatch, external):
    """FC10: a structurally invalid external payload must not abort the baseline graph."""
    factory = build_metrics_factory({}, data_factory=lambda _: type(
        "BadData", (), {"fetch": lambda *a: {"facts": "not FinancialInputs"}})())
    graph, model = graph_for(tmp_path, monkeypatch, factory)
    state, _ = graph.propagate("NVDA", fr03.TRADE_DATE)
    assert state["fundamentals_report"]
    assert all("invalid_financial_input" in p for p in financial_prompts(model))
