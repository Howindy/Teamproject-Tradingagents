"""FR-04-FC05, SB-01-FC05, INV-01-FC01 through FC03 and IR-14 at the public entries."""

import json
import re
from copy import deepcopy
from decimal import Decimal
from unittest.mock import Mock

import pytest
import test_fr03_integration as support
from bs4 import BeautifulSoup
from typer.testing import CliRunner

import cli.main as cli
import cli.run as cli_run
from cli.display import MessageBuffer
from cli.models import AnalystType
from tradingagents import final_recommendation, portfolio_risk
from tradingagents.agents import schemas
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.memory import settlement
from tradingagents.memory.log import TradingMemoryLog


@pytest.fixture
def market_graph(tmp_path, monkeypatch):
    config = deepcopy(support.DEFAULT_CONFIG)
    config.update(
        results_dir=str(tmp_path / "results"),
        data_cache_dir=str(tmp_path / "cache"),
        memory_log_path=str(tmp_path / "decisions.md"),
    )
    model = support.ScriptedModel(structured=True)
    monkeypatch.setattr(
        support.trading_graph, "create_tier_client", lambda *a, **k: support._Client(model)
    )
    monkeypatch.setitem(
        support.STRUCTURED,
        schemas.PortfolioDecision,
        schemas.PortfolioDecision(
            rating=schemas.PortfolioRating.BUY,
            executive_summary="proposal marker",
            investment_thesis="thesis",
        ),
    )
    for key in ("ticker", "symbol"):
        monkeypatch.setitem(support.ARGS, key, "AAPL")
    monkeypatch.setattr(support, "TRADE_DATE", "2025-01-15")
    for key in ("end_date", "curr_date"):
        monkeypatch.setitem(support.ARGS, key, support.TRADE_DATE)
    monkeypatch.setitem(support.ARGS, "start_date", "2025-01-02")
    for vendors in support.router.VENDOR_METHODS.values():
        for vendor in vendors:
            monkeypatch.setitem(
                vendors,
                vendor,
                lambda *a, **k: "Date,Open,High,Low,Close,Volume\n2025-01-15,100,101,99,100,1000",
            )
    monkeypatch.setattr(
        support.snapshot, "load_ohlcv", lambda *a, **k: support._market_prices_frame()
    )
    monkeypatch.setattr(
        support.yahoo_market.yf,
        "Ticker",
        lambda symbol: type("Ticker", (), {"info": {"longName": "Apple"}})(),
    )
    return TradingAgentsGraph(["market"], config=config)


DATE = "2025-01-15"
SCENARIO = {
    "ticker": "AAPL",
    "currency": "USD",
    "portfolio_value": 100000,
    "current_position_value": 0,
    "proposed_buy_value": 30000,
    "entry_price": 100,
    "stop_loss_price": 95,
}
LIMITS = {"max_projected_weight": "0.3", "max_stop_distance": "0.05"}


def cli_entry(market_graph, tmp_path, monkeypatch, payload):
    monkeypatch.setattr(cli_run, "unattended_gaps", lambda flags: [])
    monkeypatch.setattr(
        cli_run,
        "get_user_selections",
        lambda flags: {
            "ticker": flags["ticker"],
            "analysis_date": flags["date"],
            "analysts": [AnalystType.MARKET],
            "asset_type": "stock",
        },
    )
    monkeypatch.setattr(cli_run, "_build_run_config", lambda *a: market_graph.config)
    monkeypatch.setattr(cli_run, "TradingAgentsGraph", lambda *a, **k: market_graph)
    monkeypatch.setattr(cli_run, "message_buffer", MessageBuffer())
    monkeypatch.setattr(cli_run, "Live", support._NullLive)
    monkeypatch.setattr(cli_run, "update_display", lambda *a, **k: None)
    monkeypatch.setattr(cli_run, "_open_page", lambda *a: None)
    captured = []
    display = cli_run.display_complete_report

    def observe(state):
        captured.append(state)
        return display(state)

    monkeypatch.setattr(cli_run, "display_complete_report", observe)
    args = [
        "--ticker",
        "AAPL",
        "--date",
        DATE,
        "--analysts",
        "market",
        "--save",
        "--show",
        "--html",
    ]
    if payload is not None:
        path = tmp_path / "purchase.json"
        # The precision case exercises the actual JSON decoder with an unquoted decimal.
        path.write_text(json.dumps(payload).replace('"30000.0000000001"', "30000.0000000001"))
        args.extend(["--purchase-scenario", str(path)])
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == 0, (result.output, result.exception)
    (state,) = captured
    return state, result.output


@pytest.mark.parametrize("entry", ["program", "cli"])
@pytest.mark.parametrize(
    ("change", "risk_status", "thresholds", "weight", "stop", "reason"),
    [
        ({}, "passed", LIMITS, "0.3", "0.05", ""),
        (
            {"max_projected_weight": "0.25"},
            "blocked",
            LIMITS | {"max_projected_weight": "0.25"},
            "0.3",
            "0.05",
            "projected weight",
        ),
        (
            {"max_projected_weight": None},
            "blocked",
            {"max_stop_distance": "0.05"},
            "0.3",
            "0.05",
            "max_projected_weight",
        ),
        (
            {"max_stop_distance": 1},
            "blocked",
            {"max_projected_weight": "0.3"},
            "0.3",
            "0.05",
            "max_stop_distance",
        ),
        (
            {"proposed_buy_value": "30000.0000000001"},
            "blocked",
            LIMITS,
            "0.300000000000001",
            "0.05",
            "projected weight",
        ),
        (None, "blocked", LIMITS, None, None, "scenario"),
        ({}, "error", {}, None, None, "manual review"),
    ],
    ids=["equal", "override", "null", "illegal", "precision", "missing", "risk-error"],
)
def test_shared_purchase_payload(
    entry,
    change,
    risk_status,
    thresholds,
    weight,
    stop,
    reason,
    market_graph,
    tmp_path,
    monkeypatch,
):
    # Spy below each public evaluate() so any import alias still executes the real boundary.
    risk_call = Mock(wraps=portfolio_risk._evaluate_impl)
    final_call = Mock(wraps=final_recommendation._evaluate_impl)
    monkeypatch.setattr(portfolio_risk, "_evaluate_impl", risk_call)
    monkeypatch.setattr(final_recommendation, "_evaluate_impl", final_call)
    if risk_status == "error":
        risk_call.side_effect = ArithmeticError("controlled evaluator fault")
    payload = None if change is None else SCENARIO | change
    rating = "Buy" if risk_status == "passed" else "REVIEW"
    if entry == "program":
        kwargs = {} if payload is None else {"purchase_scenario": payload}
        state, signal = market_graph.propagate("AAPL", DATE, **kwargs)
        assert signal == rating
        report = market_graph.save_reports(state, "AAPL", tmp_path / "manual")
        displays = []
    else:
        state, output = cli_entry(market_graph, tmp_path, monkeypatch, payload)
        (report,) = tmp_path.glob("results/reports/*/complete_report.md")
        displays = [re.sub(r"[│┃]", " ", output)]
    risk_call.assert_called_once()
    final_call.assert_called_once()
    risk = state["portfolio_risk_result"]
    assert risk["status"] == risk_status
    assert risk["thresholds"] == thresholds
    assert (risk["projected_weight"], risk["stop_distance"]) == (weight, stop)
    assert state["gate_status"] == ("passed" if rating == "Buy" else "blocked")
    assert state["final_rating"] == rating
    proposal = state["model_proposal"]["text"]
    assert "proposal marker" in proposal
    body = state["final_trade_decision"]
    if rating == "Buy":
        assert body == proposal
    else:
        assert any(reason in item for item in risk["reasons"])
        assert "Manual review required" in body and "proposal marker" not in body
    (state_file,) = tmp_path.glob("results/AAPL/**/full_states_log_*.json")
    saved = json.loads(state_file.read_text())
    assert (saved["final_rating"], saved["final_trade_decision"]) == (rating, body)
    (row,) = market_graph.memory_log.load_entries()
    assert (row["rating"], row["decision"]) == (rating, body)
    page = BeautifulSoup(report.with_suffix(".html").read_text(), "html.parser")
    assert page.select_one(".masthead .rating").get_text(strip=True) == rating
    markdown = report.read_text()
    assert re.search(rf"(?mi)^.*rating[^\n]*\b{rating}\b", markdown)
    assert body in markdown
    displays.extend([markdown, page.get_text(" ", strip=True)])
    if rating == "REVIEW":
        assert body.startswith("Manual review required:")
        # Formal notice and model recommendation must occupy distinct report sections.
        for section in page.find_all("section"):
            if body in section.get_text(" ", strip=True):
                assert "proposal marker" not in section.get_text(" ", strip=True) or any(
                    re.search("proposal|advisory|intermediate", h.get_text(), re.I)
                    for h in section.find_all(["h3", "h4"])
                )
    for display in displays:
        words = re.sub(r"\s+([:;,.])", r"\1", " ".join(display.lower().split()))
        assert rating.lower() in words
        assert ("proposal marker" if rating == "Buy" else "manual review required") in words
        for line in body.splitlines():
            visible = line.replace("**", "").strip().lower()
            assert visible in words.replace("**", "")
        assert risk_status in words
        assert all(item.lower() in words for item in risk["reasons"])
        if risk["scenario"]:
            assert "usd" in words
            assert re.search(r"100[, ]?000", words)
        for value in [weight, stop, *thresholds.values()]:
            if value is not None:
                percentage = format(Decimal(value) * 100, ".1f")
                assert (
                    value in words
                    or percentage + "%" in words
                    or percentage.removesuffix(".0") + "%" in words
                )


@pytest.mark.parametrize("contents", [None, "{broken"])
def test_bad_cli_file_fails_before_analysis(tmp_path, monkeypatch, contents):
    path = tmp_path / "scenario.json"
    if contents is not None:
        path.write_text(contents)
    start = Mock()
    monkeypatch.setattr(cli, "run_analysis", start)
    result = CliRunner().invoke(cli.app, ["--purchase-scenario", str(path)])
    assert result.exit_code != 0
    assert "no such option" not in result.output.lower()
    start.assert_not_called()


def delivery_state():
    # A valid checked REVIEW with a conflicting advisory Buy, at the persistence boundary.
    return {
        "company_of_interest": "AAPL",
        "trade_date": DATE,
        "market_report": "",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
        "investment_plan": "",
        "trader_investment_plan": "",
        "investment_debate_state": dict.fromkeys(
            ("bull_history", "bear_history", "history", "current_response"), ""
        ),
        "risk_debate_state": dict.fromkeys(
            (
                "aggressive_history",
                "conservative_history",
                "neutral_history",
                "history",
                "judge_decision",
            ),
            "",
        ),
        "model_proposal": {"rating": "Buy", "text": "Rating: Buy (proposal marker)"},
        "gate_status": "blocked",
        "reasons": ["risk blocked"],
        "final_rating": "REVIEW",
        "final_trade_decision": "Manual review required: risk blocked.",
    }


@pytest.mark.parametrize("mode", ["enabled", "duplicate", "disabled"])
def test_conditional_memory_write(market_graph, monkeypatch, mode):
    state = delivery_state()
    if mode == "disabled":
        market_graph.memory_log = TradingMemoryLog({})
    log = market_graph.memory_log
    if mode == "duplicate":
        log.store_decision("AAPL", DATE, "historical body", rating="Hold")
    before = log.load_entries()
    model_calls = Mock(side_effect=AssertionError("saving called a model"))
    monkeypatch.setattr(support.ScriptedModel, "_count", model_calls)
    market_graph.record_decision("AAPL", DATE, state)
    if mode == "enabled":
        (row,) = log.load_entries()
        assert (row["rating"], row["decision"]) == ("REVIEW", state["final_trade_decision"])
    else:
        assert log.load_entries() == before
    model_calls.assert_not_called()


def test_settlement_preserves_checked_decision(market_graph, monkeypatch):
    state = delivery_state()
    market_graph.record_decision("AAPL", DATE, state)
    (before,) = market_graph.memory_log.load_entries()
    assert before["pending"]
    assert (before["rating"], before["decision"]) == ("REVIEW", state["final_trade_decision"])
    monkeypatch.setattr(settlement, "fetch_returns", lambda *a, **k: (0.05, 0.02, 5, "2025-01-23"))
    reflect = Mock(return_value="Subsequent evidence favored Buy.")
    monkeypatch.setattr(market_graph.reflector, "reflect_on_final_decision", reflect)
    result = market_graph.settle_all_pending()
    assert result.settled == [("AAPL", DATE)]
    (after,) = market_graph.memory_log.load_entries()
    reflect.assert_called_once()
    assert reflect.call_args.kwargs["final_decision"] == before["decision"]
    assert after["reflection"] == reflect.return_value and not after["pending"]
    assert (after["rating"], after["decision"]) == (before["rating"], before["decision"])


@pytest.mark.parametrize("failure", ["state", "memory"])
def test_save_failure_preserves_primary_exception_and_order(
    market_graph, monkeypatch, tmp_path, failure
):
    state = delivery_state()
    before = deepcopy(state)
    primary = OSError("controlled save failure")
    target, method = (
        (market_graph, "_log_state")
        if failure == "state"
        else (market_graph.memory_log, "store_decision")
    )
    monkeypatch.setattr(target, method, Mock(side_effect=primary))
    with pytest.raises(OSError) as caught:
        market_graph.record_decision("AAPL", DATE, state)
    assert caught.value is primary and state == before
    assert market_graph.memory_log.load_entries() == []
    assert bool(list(tmp_path.rglob("full_states_log_*.json"))) == (failure == "memory")


def test_stream_merge_losing_gate_stops_before_save(market_graph, tmp_path, monkeypatch):
    """IR-03: exercise the real debug/stream merge, including the final state writer."""
    market_graph.debug = True
    original_stream = market_graph.stream_run

    def without_gate(*args, **kwargs):
        for messages, state in original_stream(*args, **kwargs):
            if state is not None:
                state = dict(state)
                state.pop("gate_status", None)
            yield messages, state

    monkeypatch.setattr(market_graph, "stream_run", without_gate)
    with pytest.raises((ValueError, RuntimeError)):
        market_graph.propagate("AAPL", DATE)
    assert not list(tmp_path.rglob("full_states_log_*.json"))
    assert market_graph.memory_log.load_entries() == []


def test_terminal_summary_and_later_run_cannot_change_saved_decision(
    market_graph, tmp_path, monkeypatch
):
    """IR-05/13: keep the decision at check time and the report summary at delivery time."""
    late = support._handbuilt_summary("LATE")
    monkeypatch.setattr(market_graph, "_prepare_terminal_summary", lambda *a: deepcopy(late))
    monkeypatch.setattr(settlement, "fetch_returns", lambda *a, **k: (None, None, None, None))
    first, rating = market_graph.propagate("AAPL", DATE, purchase_scenario=dict(SCENARIO))
    assert rating == first["final_rating"] == "Buy"
    assert first["data_availability_summary"] == late
    second, rating = market_graph.propagate(
        "AAPL", DATE, purchase_scenario=SCENARIO | {"max_stop_distance": 1}
    )
    assert rating == second["final_rating"] == "REVIEW"
    path = market_graph.save_reports(first, "AAPL", tmp_path / "earlier")
    report = path.read_text()
    assert "MARKERLATE" in report and first["final_trade_decision"] in report
    assert second["final_trade_decision"] not in report


def test_internal_final_check_fault_delivers_error_gate(market_graph, monkeypatch):
    final_call = Mock(side_effect=ArithmeticError("controlled SB-01 fault"))
    monkeypatch.setattr(final_recommendation, "_evaluate_impl", final_call)
    state, rating = market_graph.propagate("AAPL", DATE, purchase_scenario=dict(SCENARIO))
    final_call.assert_called_once()
    assert state["portfolio_risk_result"]["status"] == "passed"
    assert state["gate_status"] == "error"
    assert rating == state["final_rating"] == "REVIEW"
    assert "manual review" in state["final_trade_decision"].lower()


def test_independent_report_failure_preserves_formal_fields(market_graph, tmp_path):
    state = delivery_state()
    before = deepcopy(state)
    occupied = tmp_path / "occupied"
    occupied.write_text("existing file")
    with pytest.raises(FileExistsError) as error:
        market_graph.save_reports(state, "AAPL", occupied)
    assert error.value.filename == str(occupied)
    assert occupied.read_text() == "existing file" and state == before


def test_checked_pass_preserves_proposal_spacing_in_state_and_saved_body(
    market_graph, monkeypatch, tmp_path
):
    summary = "First paragraph.\n\n\nSecond  paragraph."
    decision = support.STRUCTURED[schemas.PortfolioDecision].model_copy(
        update={"executive_summary": summary}
    )
    monkeypatch.setitem(support.STRUCTURED, schemas.PortfolioDecision, decision)
    state, signal = market_graph.propagate("AAPL", DATE, purchase_scenario=dict(SCENARIO))
    assert signal == "Buy"
    proposal = state["model_proposal"]["text"]
    assert summary in proposal
    assert state["final_trade_decision"] == proposal
    (saved,) = tmp_path.rglob("full_states_log_*.json")
    assert json.loads(saved.read_text())["final_trade_decision"] == proposal
