"""Portfolio context: what the caller holds, threaded into the decision agents.

Decisions were made with no knowledge of the current book, so "add to a full
position" and "open a new one" read alike. The context is optional and carries
three distinct states: a position, a flat book, and no context at all. Nothing
may present the third as the second. The research team stays blind so the bull
and bear cases are not anchored by the caller's position.
"""

from __future__ import annotations

import json

import pytest

from tradingagents.agents.context import get_portfolio_context_from_state
from tradingagents.portfolio import PortfolioContext, load_portfolio

HOLDING = {
    "cash": 25000.0,
    "currency": "USD",
    "positions": [
        {"ticker": "AAPL", "quantity": 120, "average_price": 150.0},
        {"ticker": "MSFT", "quantity": 10},
    ],
}


@pytest.mark.unit
def test_position_in_the_analyzed_instrument_leads_the_render():
    text = PortfolioContext.model_validate(HOLDING).render("AAPL")
    assert "120" in text and "150" in text
    assert "MSFT" in text and "25,000" in text and "USD" in text


@pytest.mark.unit
def test_flat_book_says_no_position_rather_than_omitting_it():
    text = PortfolioContext.model_validate({"cash": 1000.0, "positions": []}).render("AAPL")
    assert "No current position in AAPL" in text


@pytest.mark.unit
def test_a_ticker_held_under_another_spelling_is_matched():
    text = PortfolioContext.model_validate({"positions": [{"ticker": "aapl", "quantity": 5}]}).render("AAPL")
    assert "No current position" not in text and "5" in text


@pytest.mark.unit
def test_absent_context_is_reported_as_not_provided():
    notice = get_portfolio_context_from_state({"company_of_interest": "AAPL"})
    assert "not provided" in notice.lower()
    assert "no position" not in notice.lower()  # missing must not read as flat


@pytest.mark.unit
def test_rendered_context_reaches_the_agents_from_state():
    block = get_portfolio_context_from_state({"portfolio_context": "Portfolio: flat", "company_of_interest": "AAPL"})
    assert block == "Portfolio: flat"


@pytest.mark.unit
def test_load_rejects_a_malformed_file_with_a_clear_error(tmp_path):
    bad = tmp_path / "p.json"
    bad.write_text(json.dumps({"positions": [{"quantity": 5}]}))
    with pytest.raises(ValueError, match="portfolio"):
        load_portfolio(bad)


@pytest.mark.unit
def test_load_reads_a_valid_file(tmp_path):
    good = tmp_path / "p.json"
    good.write_text(json.dumps(HOLDING))
    assert load_portfolio(good).positions[0].ticker == "AAPL"


# --- threading through the graph --------------------------------------------

def _bare_graph(tmp_path):
    from tradingagents.graph.propagation import Propagator
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.memory import TradingMemoryLog

    graph = object.__new__(TradingAgentsGraph)
    graph.config = {"memory_log_path": str(tmp_path / "m.md"), "max_debate_rounds": 1,
                    "max_risk_discuss_rounds": 1}
    graph.memory_log = TradingMemoryLog(graph.config)
    graph.propagator = Propagator()
    graph.selected_analysts = ["market"]
    graph.settle_pending = lambda t: None
    graph.resolve_instrument_context = lambda t, a="stock", d=None: ""
    graph._memory_as_of = lambda d: None
    return graph


@pytest.mark.unit
def test_create_run_state_renders_the_portfolio_once(tmp_path):
    graph = _bare_graph(tmp_path)
    state = graph.create_run_state("AAPL", "2026-08-14", portfolio=PortfolioContext.model_validate(HOLDING))
    assert "120" in state["portfolio_context"]
    assert graph.create_run_state("AAPL", "2026-08-14")["portfolio_context"] == ""


@pytest.mark.unit
def test_checkpoint_signature_changes_with_the_portfolio(tmp_path):
    graph = _bare_graph(tmp_path)
    none = graph._run_signature("stock")
    flat = graph._run_signature("stock", PortfolioContext())
    held = graph._run_signature("stock", PortfolioContext.model_validate(HOLDING))
    assert len({none, flat, held}) == 3


@pytest.mark.unit
@pytest.mark.parametrize("module, factory", [
    ("tradingagents.agents.trader.trader", "create_trader"),
    ("tradingagents.agents.managers.portfolio_manager", "create_portfolio_manager"),
    ("tradingagents.agents.risk_mgmt.aggressive_debator", "create_aggressive_debator"),
    ("tradingagents.agents.risk_mgmt.conservative_debator", "create_conservative_debator"),
    ("tradingagents.agents.risk_mgmt.neutral_debator", "create_neutral_debator"),
])
def test_decision_agents_see_the_portfolio(module, factory, monkeypatch):
    """The prompt each decision agent sends carries the portfolio block."""
    import importlib

    mod = importlib.import_module(module)
    seen = []

    class _LLM:
        def invoke(self, prompt, *a, **k):
            seen.append(prompt if isinstance(prompt, str) else json.dumps(str(prompt)))
            from langchain_core.messages import AIMessage
            return AIMessage("Rating: Hold\n\nnothing to do")

        def with_structured_output(self, *a, **k):
            raise NotImplementedError  # force the free-text path

    state = {
        "company_of_interest": "AAPL", "trade_date": "2026-08-14", "asset_type": "stock",
        "instrument_context": "", "market_report": "M", "sentiment_report": "S",
        "news_report": "N", "fundamentals_report": "F", "investment_plan": "P",
        "trader_investment_plan": "T", "past_context": "",
        "portfolio_context": "PORTFOLIO_BLOCK_MARKER",
        "investment_debate_state": {"history": "", "count": 0},
        "risk_debate_state": {"history": "", "latest_speaker": "", "count": 0,
                              "aggressive_history": "", "conservative_history": "", "neutral_history": "",
                              "current_aggressive_response": "", "current_conservative_response": "",
                              "current_neutral_response": ""},
    }
    node = getattr(mod, factory)(_LLM())
    node(state)
    assert any("PORTFOLIO_BLOCK_MARKER" in p for p in seen), f"{factory} prompt lacks the portfolio block"


@pytest.mark.unit
def test_research_team_stays_blind_to_the_portfolio():
    import inspect

    from tradingagents.agents.researchers import bear_researcher, bull_researcher
    for mod in (bull_researcher, bear_researcher):
        assert "portfolio_context" not in inspect.getsource(mod)


@pytest.mark.unit
def test_completed_portfolio_run_preserves_old_checkpoint_without_auto_clear(tmp_path, monkeypatch):
    """PA-01 (Round 3 A3 amendment): a completed portfolio-bearing run must NOT
    auto-clear an old checkpoint. Under the approved Round 3 default entry, the run
    executes fresh (non-None initial state carrying the portfolio), performs no
    checkpoint acquire/read/resume/clear, and leaves independently-seeded old
    checkpoint evidence byte-identical. The superseded assertion
    ``cleared == [written]`` is replaced: automatic clear is now asserted NEVER to
    happen, while the retained explicit checkpoint component API is still used to
    prepare (and later verify) real evidence independently of the entry.
    """
    import tradingagents.graph.trading_graph as tg
    from tradingagents.graph import checkpointer
    from tradingagents.run_context import RunContext, current as current_run

    graph = _bare_graph(tmp_path)
    graph.config.update({"checkpoint_enabled": True, "data_cache_dir": str(tmp_path),
                         "results_dir": str(tmp_path)})
    graph.debug = False
    graph._resuming = False
    graph.propagator.get_graph_args = lambda callbacks=None: {}
    graph._log_state = lambda *a, **k: None
    book = PortfolioContext.model_validate(HOLDING)

    # --- PA-01 step 2: seed a REAL old checkpoint via the retained component API,
    # independently of the entry under test; close the seeding resource, then
    # record the non-empty evidence set and its initial bytes. ``setup()`` creates
    # the per-ticker SQLite database (real, writable checkpoint schema).
    signature = graph._run_signature("stock", book)
    # thread_id only COMPUTES the deterministic identifier; it does not create a
    # thread or checkpoint. The real database evidence comes from setup() below.
    checkpointer.thread_id("AAPL", "2026-08-14", signature)
    with checkpointer.get_checkpointer(graph.config["data_cache_dir"], "AAPL") as saver:
        saver.setup()
    db = checkpointer._db_path(graph.config["data_cache_dir"], "AAPL")
    assert db.exists(), "seeding must create a real checkpoint database"
    seeded = {p: p.read_bytes() for p in sorted(db.parent.glob(f"{db.name}*"))}
    assert seeded, "seeding must produce at least one non-empty checkpoint evidence file"
    assert any(b for b in seeded.values()), "seeded checkpoint evidence must be non-empty"

    # --- PA-01 step 3: guard the acquisition/read/resume/clear bindings AFTER
    # seeding, at their actual import binding. Any call fails the test.
    violations = []

    def _trap(name):
        def fn(*a, **k):
            violations.append(name)
            raise AssertionError(f"default entry must not call {name}")
        return fn

    for name in ("get_checkpointer", "checkpoint_step", "thread_id", "clear_checkpoint"):
        monkeypatch.setattr(tg, name, _trap(name))
    for name in ("begin_checkpoint", "clear_checkpoint_on_success"):
        monkeypatch.setattr(graph, name, _trap(name))

    # --- PA-01 step 4/5: call the REAL ``propagate`` entry (not ``_run_graph``).
    # Only the internal graph executor is controlled; propagate, RunContext, terminal
    # preparation and record_decision all stay real.
    observed = {}

    class _Executor:
        def invoke(self, graph_input, **k):
            scope = current_run()
            observed["scope"] = scope
            observed["scope_is_none"] = scope is None
            observed["registry"] = scope.registry if scope is not None else None
            observed["input"] = graph_input
            return {"final_trade_decision": "Rating: Hold\n\nx", "final_rating": "Hold"}

    graph.graph = _Executor()

    before_binding = current_run()
    caller = RunContext()
    caller.__enter__()
    try:
        assert current_run() is caller
        result = graph.propagate("AAPL", "2026-08-14", "stock", portfolio=book)
        # After propagate returns, the caller binding is restored.
        assert current_run() is caller, "propagate must restore the caller binding"
    finally:
        caller.finish()
    # After the caller scope exits, the binding is restored to what it was BEFORE
    # this test entered it (do not assume it was None).
    assert current_run() is before_binding

    # Inside the executor: a real per-run scope existed, distinct from the caller,
    # and it owned a fresh registry with THIS run's identity.
    assert not observed["scope_is_none"], "the run scope must be active during execution"
    assert observed["scope"] is not caller, "the entry must bind its OWN scope, not the caller's"
    assert observed["registry"] is not None
    assert observed["registry"] is not caller.registry, "the run must own a fresh registry"
    assert observed["registry"]._analysis_context == {
        "ticker": "AAPL", "trade_date": "2026-08-14", "asset_type": "stock"}
    # The executor received a non-None FRESH initial state carrying the portfolio.
    assert observed["input"] is not None
    assert "120" in observed["input"]["portfolio_context"]

    # Save the REAL return value, then assert its shape and controlled values.
    assert isinstance(result, tuple) and len(result) == 2
    final_state, signal = result
    assert signal == "Hold"
    assert final_state["final_trade_decision"].startswith("Rating: Hold")

    # --- PA-01 step 6: automatic clear never called; all forbidden checkpoint calls
    # absent (complete violations list empty); every seeded file exists byte-identical.
    assert violations == [], f"forbidden checkpoint calls occurred: {violations}"
    for path, before in seeded.items():
        assert path.exists(), f"seeded evidence {path} was deleted"
        assert path.read_bytes() == before, f"seeded evidence {path} was modified"


@pytest.mark.unit
def test_research_layer_sizes_against_a_standard_allocation():
    """The research team is blind to the book, so its plan cannot promise
    position-relative sizing: it sizes against a standard allocation instead."""
    from tradingagents.agents.schemas import ResearchPlan

    description = ResearchPlan.model_fields["strategic_actions"].description
    assert "standard allocation" in description
    assert "does not see the caller's holdings" in description


@pytest.mark.unit
def test_partial_portfolio_states_only_what_it_was_given():
    """Cash omitted is not cash zero; the line is absent rather than invented."""
    text = PortfolioContext.model_validate({"positions": [{"ticker": "AAPL", "quantity": 5}]}).render("AAPL")
    assert "Cash" not in text
    assert "5" in text


@pytest.mark.unit
def test_cli_rejects_an_unusable_portfolio_file_before_running(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    import cli.main as m

    bad = tmp_path / "bad.json"
    bad.write_text('{"positions": [{"quantity": 5}]}')
    ran = []
    monkeypatch.setattr(m, "run_analysis", lambda **k: ran.append(k))

    result = CliRunner().invoke(m.app, ["--portfolio", str(bad)])

    assert result.exit_code == 1 and ran == []


@pytest.mark.unit
def test_cli_passes_a_valid_portfolio_into_the_run(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    import cli.main as m

    good = tmp_path / "good.json"
    good.write_text(json.dumps(HOLDING))
    ran = []
    monkeypatch.setattr(m, "run_analysis", lambda **k: ran.append(k))

    result = CliRunner().invoke(m.app, ["--portfolio", str(good)])

    assert result.exit_code == 0
    assert ran[0]["portfolio"].position_in("AAPL").quantity == 120
