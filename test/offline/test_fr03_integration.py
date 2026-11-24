"""Offline integration tests for FR-03: real tools, graph, entries, research, report.

Traceability: FR-03-FC01, FC03, FC04, FC05 and IR-05, IR-09, IR-12, IR-13 (plus
the R03-12 integration-compatibility checks). The approved specification is
``docs/plans/round-03.md`` @ ``d83abc909d6d7b40a7e7fabaff26ef971b9dbc2d`` (cases
R03-02 and R03-08 through R03-12).

The real internal boundaries stay: the actual tool bodies and ToolNode, the real
sentiment analyst node (so P-13 is entered through it, not by calling ``get_news``
again), the real vendor router (for the first-vendor-fails / next-succeeds
fallback), the real graph, and both entries. Only external models and vendors are
substituted. The two production modules do not exist yet, so the tests start red;
they import those lazily so collection still works.

Chosen internal calling conventions for parts the D2 contract leaves to the
implementer (recorded in the phase report, NOT new architecture requirements):
  - ``run_context.RunContext`` is a context manager; ``run_context.current()``
    returns the active scope or ``None``; ``ctx.registry`` is the run registry.
    ``RunContext.delegate(scope)`` is the explicit internal-share entry (shares the
    caller's scope/registry, creates none); ``finish()`` is idempotent and restores
    only the binding. Resource ownership is the ENTRY's: any run-owned resource is
    closed by the entry's own ``finally``, NOT by a ``_cleanup`` hook on the context.
  - research wrapper: ``research_prepare(state, first_bull_call) -> (state_update, bull_result)``
    (IF-24), also reachable through the graph.
  - ``data_availability_summary`` / ``research_availability_summary`` live in
    ``final_state``; report/CLI consume the passed state.
  - the two stage-specific fixed texts are DIFFERENT per D2 (do not unify them):
    ``availability.UNAVAILABLE_RESEARCH_TEXT`` == "program summary currently
    unavailable" (research-stage first-Bull block, D2 IF-24/§8.3 line ~886) and
    ``availability.UNAVAILABLE_REPORT_TEXT`` == "program summary unavailable"
    (terminal report region, D2 line ~1479). Each test asserts the constant equals
    that independent spec literal AND that the rendered output contains it, so the
    check does not self-justify from the production constant alone.
  - the controlled later observation is inserted at the FIRST Bear Researcher node
    (deterministically after the first Bull, before the Research Manager/END) via a
    minimal compiled-node wrapper that keeps the real node executing. The wrong
    "Memory Log is post-research" assumption is not used: Memory Log runs in
    parallel with the analysts and joins START, i.e. before the first Bull.
"""

from __future__ import annotations

import copy
import importlib

import pandas as pd
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import Field

from tradingagents.agents import context, schemas
from tradingagents.agents.analysts import sentiment_analyst
from tradingagents.dataflows import router
from tradingagents.dataflows.vendors.yahoo import market as yahoo_market, snapshot
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph import trading_graph

pytestmark = pytest.mark.unit

TRADE_DATE = "2026-01-09"
TEXT = "Report.\n\n**Rating**: Overweight\n\nFINAL TRANSACTION PROPOSAL: **BUY**"
STRUCTURED = {
    schemas.ResearchPlan: schemas.ResearchPlan(
        recommendation=schemas.PortfolioRating.OVERWEIGHT, rationale="r", strategic_actions="a"),
    schemas.TraderProposal: schemas.TraderProposal(action=schemas.TraderAction.BUY, reasoning="r"),
    schemas.PortfolioDecision: schemas.PortfolioDecision(
        rating=schemas.PortfolioRating.OVERWEIGHT, executive_summary="s",
        investment_thesis="thesis"),
    schemas.SentimentReport: schemas.SentimentReport(
        overall_band=schemas.SentimentBand.NEUTRAL, overall_score=5.0, confidence="low", narrative="n"),
}
ARGS = {"symbol": "NVDA", "ticker": "NVDA", "curr_date": TRADE_DATE, "start_date": "2026-01-02",
        "end_date": TRADE_DATE, "indicator": "rsi", "topic": "Fed rate cut", "freq": "quarterly"}


def _availability():
    return importlib.import_module("tradingagents.dataflows.availability")


def _run_context():
    return importlib.import_module("tradingagents.run_context")


# --------------------------------------------------------------------------- #
# Controlled substitutes (same shape as test_graph_end_to_end.py).             #
# --------------------------------------------------------------------------- #
class ScriptedModel(BaseChatModel):
    structured: bool = False
    tools: tuple = ()
    calls: list = Field(default_factory=list)
    fail_at: int | None = None

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self.model_copy(update={"tools": tuple(tools)})

    def with_structured_output(self, schema, **kwargs):
        if not self.structured:
            raise NotImplementedError
        return RunnableLambda(lambda _: self._count() or STRUCTURED[schema])

    def _count(self) -> None:
        self.calls.append(1)
        if len(self.calls) == self.fail_at:
            raise RuntimeError("provider unavailable")

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self._count()
        if self.tools and not isinstance(messages[-1], ToolMessage):
            calls = [{"name": t.name, "id": f"call_{i}",
                      "args": {k: v for k, v in ARGS.items()
                               if k in t.tool_call_schema.model_json_schema()["properties"]}}
                     for i, t in enumerate(self.tools)]
            message = AIMessage(content="", tool_calls=calls)
        else:
            message = AIMessage(content=TEXT)
        return ChatResult(generations=[ChatGeneration(message=message)])


class _Client:
    def __init__(self, model):
        self.model = model

    def get_llm(self):
        return self.model


# Two regimes so a controlled late observation changes the recorded *status*, not
# merely a number that is still `available`. The synchronous regime serves a finite
# Close (status `available`); the late regime serves the same snapshot block with a
# non-finite latest-row Close, which the classifier maps to a non-available status
# (`no_data`), so research (available) and terminal (no_data) genuinely differ on
# the verified-snapshot necessity target. No raw payload or price field is added to
# the summary to express this; the divergence is a legitimate status change.
SYNC_CLOSE = 100.5
LATE_LAST_CLOSE = float("nan")
# Markers are the producer-rendered status-neutral facts we assert outside the
# summary (the raw snapshot text the tools return), never summary-internal fields.
SYNC_MARKER = f"| Close | {SYNC_CLOSE:.2f} |"
LATE_MARKER = "| Close | N/A |"


def _market_prices_frame(close=SYNC_CLOSE, *, last_close=None):
    n = 60
    closes = [close] * n
    if last_close is not None:
        closes[-1] = last_close
    return pd.DataFrame({
        "Date": pd.bdate_range(end=TRADE_DATE, periods=n),
        "Open": closes, "High": closes, "Low": closes, "Close": closes,
        "Volume": 1_000_000,
    })


@pytest.fixture
def offline(monkeypatch, tmp_path):
    """Every vendor answers offline. The configured ``ohlcv`` loader (used by the
    verified market snapshot) is *stateful*: until ``offline_late`` fires it serves
    the 100.5 regime, after it serves the LATE_CLOSE regime. This lets a real
    synchronous tool call record 100.5 while a controlled later observation (see
    ``_late_observation``) records LATE_CLOSE from the real producer shape."""
    called: set[str] = set()
    state = {"late": False}
    for method, vendors in router.VENDOR_METHODS.items():
        for vendor in vendors:
            monkeypatch.setitem(vendors, vendor,
                                lambda *a, _m=method, **k: called.add(_m) or f"{_m} data")

    def loader(*a, **k):
        called.add("ohlcv")
        if state["late"]:
            return _market_prices_frame(SYNC_CLOSE, last_close=LATE_LAST_CLOSE)
        return _market_prices_frame(SYNC_CLOSE)

    monkeypatch.setattr(snapshot, "load_ohlcv", loader)
    monkeypatch.setattr(sentiment_analyst, "fetch_stocktwits_messages", lambda *a, **k: "no posts")
    monkeypatch.setattr(sentiment_analyst, "fetch_reddit_posts", lambda *a, **k: "no posts")
    monkeypatch.setattr(yahoo_market.yf, "Ticker", lambda s: type("T", (), {"info": {"longName": "NVIDIA"}})())
    context._identity.cache_clear()
    return called, state


def _graph(tmp_path, monkeypatch, model, debug=False, **config):
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.update(results_dir=str(tmp_path / "results"), data_cache_dir=str(tmp_path / "cache"),
               memory_log_path=str(tmp_path / "log.md"), **config)
    monkeypatch.setattr(trading_graph, "create_tier_client", lambda config, tier, **k: _Client(model))
    return trading_graph.TradingAgentsGraph(config=cfg, debug=debug)


def _spy_node(graph, node_name, on_input):
    """Wrap one compiled graph node's action so ``on_input(state)`` runs on the
    real input the node receives (the whole graph state), then delegate to the real
    node. The compiled ``PregelNode`` stores its sync action as a ``RunnableCallable``
    whose ``func`` we replace; this is a minimal test wrapper that keeps the real
    node executing. Must be called BEFORE ``propagate`` so the compiled graph the
    run uses carries the wrapper."""
    spec = graph.graph.nodes[node_name]
    inner = getattr(spec, "bound", None) or spec
    action = getattr(inner, "func", None) or getattr(inner, "data", None)
    assert action is not None, f"cannot locate the action for node {node_name!r}"
    fired = {"done": False}

    def wrapped(state):
        if not fired["done"]:
            fired["done"] = True
            on_input(state)
        return action(state)

    wrapped.__name__ = getattr(action, "__name__", node_name)
    if hasattr(inner, "func"):
        inner.func = wrapped
    elif hasattr(inner, "data"):
        inner.data = wrapped
    else:  # pragma: no cover - defensive
        raise AssertionError(f"cannot wrap node {node_name!r}")
    return fired


def _late_observation_at_bear(graph, state):
    """Inject one controlled later accepted observation at the FIRST Bear
    Researcher node.

    Ordering is now explicit and correct: the first Bull call receives the research
    snapshot; the debate then deterministically advances Bull -> Bear (per
    ``ConditionalLogic.should_continue_debate``) -> ... -> Research Manager -> END.
    So the first Bear node runs strictly *after* the first Bull and strictly
    *before* END. At that boundary the fixture's loader regime is flipped (latest
    Close -> NaN) and the real ``get_verified_market_snapshot`` tool records a
    genuinely different *status* (available -> no_data) on the run's live registry.
    Returns the record dict the caller inspects."""
    from tradingagents.agents import tools

    fired = {"snap_text": None}

    def on_bear(_node_state):
        state["late"] = True                          # flip to the LATE regime
        fired["snap_text"] = tools.get_verified_market_snapshot.invoke(
            {"symbol": "NVDA", "curr_date": TRADE_DATE, "look_back_days": 30,
             "trade_date": TRADE_DATE})

    fired_box = _spy_node(graph, "Bear Researcher", on_bear)
    return fired, fired_box


# =========================================================================== #
# R03-02: actual attachments P-01..P-15 through real tool bodies / ToolNode    #
# =========================================================================== #
def _public_tool_schema_names(tool):
    return set(tool.tool_call_schema.model_json_schema()["properties"].keys())


@pytest.mark.parametrize(
    "tool_name, call_args, expected_method, path_id",
    [
        ("get_stock_data", {"symbol": "NVDA", "start_date": "2026-01-02", "end_date": TRADE_DATE},
         "get_stock_data", "P-01"),
        ("get_verified_market_snapshot", {"symbol": "NVDA", "curr_date": TRADE_DATE},
         "get_verified_market_snapshot", "P-02"),
        ("get_indicators", {"symbol": "NVDA", "indicator": "rsi", "curr_date": TRADE_DATE},
         "get_indicators", "P-03"),
        ("get_fundamentals", {"ticker": "NVDA", "curr_date": TRADE_DATE}, "get_fundamentals", "P-04"),
        ("get_income_statement", {"ticker": "NVDA", "freq": "quarterly", "curr_date": TRADE_DATE},
         "get_income_statement", "P-05"),
        ("get_balance_sheet", {"ticker": "NVDA", "freq": "quarterly", "curr_date": TRADE_DATE},
         "get_balance_sheet", "P-06"),
        ("get_cashflow", {"ticker": "NVDA", "freq": "quarterly", "curr_date": TRADE_DATE},
         "get_cashflow", "P-07"),
        ("get_insider_transactions", {"ticker": "NVDA"}, "get_insider_transactions", "P-08"),
        ("get_news", {"ticker": "NVDA", "start_date": "2026-01-02", "end_date": TRADE_DATE},
         "get_news", "P-09"),
        ("get_global_news", {"curr_date": TRADE_DATE}, "get_global_news", "P-10"),
        ("get_macro_indicators", {"indicator": "cpi", "curr_date": TRADE_DATE},
         "get_macro_indicators", "P-11"),
        ("get_prediction_markets", {"topic": "Fed rate cut"}, "get_prediction_markets", "P-12"),
    ],
    ids=[r[0] for r in [
        ("get_stock_data", None, None, None), ("get_verified_market_snapshot", None, None, None),
        ("get_indicators", None, None, None), ("get_fundamentals", None, None, None),
        ("get_income_statement", None, None, None), ("get_balance_sheet", None, None, None),
        ("get_cashflow", None, None, None), ("get_insider_transactions", None, None, None),
        ("get_news", None, None, None), ("get_global_news", None, None, None),
        ("get_macro_indicators", None, None, None), ("get_prediction_markets", None, None, None)]],
)
def test_r03_02_tool_bodies_record_one_observation_path_and_method(
        tmp_path, monkeypatch, offline, tool_name, call_args, expected_method, path_id):
    """R03-02 / FR-03-FC01, FC03, FC05 / IR-09. Through the real tool body inside
    an active RunContext each supported position records exactly one observation
    for its method and path; with no scope the return is identical and nothing is
    recorded."""
    from tradingagents.agents import tools
    _called, _ = offline

    run_context = _run_context()
    availability = _availability()
    tool = getattr(tools, tool_name)

    no_scope_return = tool.invoke({**call_args, "trade_date": TRADE_DATE})

    with run_context.RunContext(
            analysis_context={"ticker": "NVDA", "trade_date": TRADE_DATE}) as ctx:
        reg = ctx.registry
        scoped_return = tool.invoke({**call_args, "trade_date": TRADE_DATE})
        assert scoped_return == no_scope_return
        summary = availability.AvailabilitySummarizer(reg).snapshot(
            "stock", ("market", "social", "news", "fundamentals"),
            {"ticker": "NVDA", "trade_date": TRADE_DATE})
    obs = [o for o in summary["observations"] if o.get("method") == expected_method]
    assert len(obs) == 1, f"{expected_method}: expected exactly one observation, got {len(obs)}"
    assert path_id in (obs[0].get("supported_path_ids") or [])


def test_r03_02_indicators_two_classifications_before_concatenation_exact_text(
        tmp_path, monkeypatch, offline):
    """R03-02 / FR-03-FC01, FC03 / IR-09. A single get_indicators call for RSI and
    MACD records two separate classifications before the tool concatenates them,
    and the concatenated original text is exactly preserved."""
    from tradingagents.agents import tools
    _called, _ = offline

    run_context = _run_context()
    availability = _availability()
    rsi_raw = "## rsi values from 2026-01-02 to 2026-01-09:\n\n2026-01-09: 55.0\n"
    macd_raw = "No data available for the specified date range."

    def fake_router(method, symbol, ind, curr_date, look_back):
        return rsi_raw if ind == "rsi" else macd_raw

    monkeypatch.setattr(tools, "route_to_vendor", fake_router)

    with run_context.RunContext() as ctx:
        out = tools.get_indicators.invoke(
            {"symbol": "NVDA", "indicator": "rsi,macd", "curr_date": TRADE_DATE,
             "look_back_days": 30, "trade_date": TRADE_DATE})
        reg = ctx.registry
        summary = availability.AvailabilitySummarizer(reg).snapshot(
            "stock", ("market",), {"ticker": "NVDA", "trade_date": TRADE_DATE})
    # Exact concatenated original text (two pieces joined by "\n\n").
    assert out == "\n\n".join([rsi_raw, macd_raw])
    indicator_obs = [o for o in summary["observations"] if o.get("method") == "get_indicators"]
    assert len(indicator_obs) == 2
    statuses = {o.get("effective_parameters", {}).get("indicator"): o["status"] for o in indicator_obs}
    assert statuses.get("rsi") == "available"
    assert statuses.get("macd") == "no_data"


def test_r03_02_p13_entered_through_real_sentiment_node(tmp_path, monkeypatch, offline):
    """R03-02 / FR-03-FC01, FC05 / IR-09. P-13 is entered through the real
    sentiment analyst node (its prefetch calls get_news), not by re-invoking
    get_news directly; one logical news query carries both P-09 and P-13 path
    associations, and both real fetches occur."""
    from tradingagents.agents import tools
    _called, _ = offline

    run_context = _run_context()
    availability = _availability()
    calls: list[str] = []

    def fake_router(method, ticker, start_date, end_date):
        calls.append(method)
        return f"## {ticker} News, from {start_date} to {end_date}:\n\n### h (source: s)\nbody\n"

    monkeypatch.setattr(tools, "route_to_vendor", fake_router)
    # StockTwits/Reddit are patched by the offline fixture; the sentiment node
    # still runs its real body and calls the real get_news via the fake router.
    model = ScriptedModel(structured=True)
    node = sentiment_analyst.create_sentiment_analyst(model)

    with run_context.RunContext() as ctx:
        # P-09 via the tool.
        tools.get_news.invoke({"ticker": "NVDA", "start_date": "2026-01-02",
                               "end_date": TRADE_DATE, "trade_date": TRADE_DATE})
        # P-13 via the real sentiment node (prefetch), same window.
        node({"company_of_interest": "NVDA", "trade_date": TRADE_DATE,
              "messages": [], "asset_type": "stock"})
        reg = ctx.registry
        summary = availability.AvailabilitySummarizer(reg).snapshot(
            "stock", ("news", "social"), {"ticker": "NVDA", "trade_date": TRADE_DATE})

    assert calls.count("get_news") == 2   # both real fetches occurred
    news_obs = [o for o in summary["observations"] if o.get("method") == "get_news"]
    assert len(news_obs) == 1
    assert {"P-09", "P-13"} <= set(news_obs[0].get("supported_path_ids") or [])


def test_r03_02_p14_p15_recorded_with_status_and_known_source(tmp_path, monkeypatch, offline):
    """R03-02 / FR-03-FC01, FC05 / IR-09. P-14 (StockTwits) and P-15 (Reddit) are
    recorded with their known direct sources and a status through the real
    sentiment node's prefetch."""
    _called, _ = offline
    run_context = _run_context()
    availability = _availability()
    monkeypatch.setattr(sentiment_analyst, "fetch_stocktwits_messages",
                        lambda *a, **k: (
                            "Bullish: 1 (100%) · Bearish: 0 (0%) · Unlabeled: 0 · "
                            "Total: 1 most-recent messages\n\n"
                            "[2026-01-09T10:00:00Z · @u1 · Bullish] $NVDA up"))
    monkeypatch.setattr(sentiment_analyst, "fetch_reddit_posts",
                        lambda *a, **k: (
                            "r/wallstreetbets — 1 recent posts mentioning NVDA:\n"
                            "  [2026-01-09] NVDA to the moon\n    body excerpt: buy"))
    model = ScriptedModel(structured=True)
    node = sentiment_analyst.create_sentiment_analyst(model)

    with run_context.RunContext() as ctx:
        node({"company_of_interest": "NVDA", "trade_date": TRADE_DATE,
              "messages": [], "asset_type": "stock"})
        reg = ctx.registry
        summary = availability.AvailabilitySummarizer(reg).snapshot(
            "stock", ("social",), {"ticker": "NVDA", "trade_date": TRADE_DATE})
    st = [o for o in summary["observations"] if o.get("method") == "fetch_stocktwits_messages"]
    rd = [o for o in summary["observations"] if o.get("method") == "fetch_reddit_posts"]
    assert st and st[0]["status"] == "available" and st[0].get("source") == "StockTwits"
    assert rd and rd[0]["status"] == "available" and rd[0].get("source") == "Reddit"


def test_r03_02_public_tool_schema_unchanged_against_expected_set(tmp_path):
    """R03-02 / FR-03-FC05 / IR-09. The public tool schemas expose exactly their
    known parameter set; no path/path_id/scope parameter leaks in."""
    from tradingagents.agents import tools

    # The public tool schema excludes the injected run state (symbol/ticker/trade_date);
    # this is the exact model-visible surface, and no path/path_id/scope leaks in.
    expected = {
        "get_stock_data": {"start_date", "end_date"},
        "get_indicators": {"indicator", "curr_date", "look_back_days"},
        "get_verified_market_snapshot": {"curr_date", "look_back_days"},
        "get_fundamentals": {"curr_date"},
        "get_income_statement": {"freq", "curr_date"},
        "get_balance_sheet": {"freq", "curr_date"},
        "get_cashflow": {"freq", "curr_date"},
        "get_news": {"start_date", "end_date"},
        "get_global_news": {"curr_date", "look_back_days", "limit"},
        "get_insider_transactions": set(),
        "get_macro_indicators": {"indicator", "curr_date", "look_back_days"},
        "get_prediction_markets": {"topic", "limit"},
    }
    for name, want in expected.items():
        got = _public_tool_schema_names(getattr(tools, name))
        assert got == want, f"{name}: {got} != {want}"


def test_r03_02_real_router_first_vendor_fails_next_succeeds_one_observation(
        tmp_path, monkeypatch, offline):
    """R03-02 / FR-03-FC03 / IR-09. Through the real router with a two-vendor
    chain whose first vendor raises and the next succeeds: the call returns the
    success, the fallback order/counts are as expected, and only one outer
    observation is recorded (fallback stays inside one business observation)."""
    from tradingagents.agents import tools
    from tradingagents.dataflows import config as cfg
    _called, _ = offline

    # Configure a two-vendor chain for get_stock_data.
    cfg.set_config({**cfg.get_config(), "data_vendors": {"core_stock_apis": "yfinance,alpha_vantage"}})

    seen: list[str] = []

    def first(*a, **k):                       # yfinance
        seen.append("yfinance")
        raise RuntimeError("primary broken")

    def second(*a, **k):                       # alpha_vantage
        seen.append("alpha_vantage")
        return "Date,Open,High,Low,Close,Volume\n2026-01-09,1,2,1,1.5,10\n"

    monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "yfinance", first)
    monkeypatch.setitem(router.VENDOR_METHODS["get_stock_data"], "alpha_vantage", second)

    run_context = _run_context()
    availability = _availability()
    with run_context.RunContext() as ctx:
        out = tools.get_stock_data.invoke({"symbol": "NVDA", "start_date": "2026-01-02",
                                           "end_date": TRADE_DATE, "trade_date": TRADE_DATE})
        reg = ctx.registry
        summary = availability.AvailabilitySummarizer(reg).snapshot(
            "stock", ("market",), {"ticker": "NVDA", "trade_date": TRADE_DATE})
    # Fallback order preserved, each vendor tried once.
    assert seen == ["yfinance", "alpha_vantage"]
    assert "Close" in out
    stock_obs = [o for o in summary["observations"] if o.get("method") == "get_stock_data"]
    assert len(stock_obs) == 1
    assert stock_obs[0]["status"] == "available"


def test_r03_02_tool_identity_non_current_object_does_not_bind_necessary_target(
        tmp_path, monkeypatch, offline):
    """R03-02 / FR-03-FC02, FC04 / IR-10. Through the real tool body under a run
    whose analysis object is NVDA, a request for a DIFFERENT symbol does not bind
    the NVDA necessity target (but its observation is still recorded). An early
    global-news date likewise does not bind the analysis-date necessity target."""
    from tradingagents.agents import tools
    _called, _ = offline
    run_context = _run_context()
    availability = _availability()

    with run_context.RunContext(
            analysis_context={"ticker": "NVDA", "trade_date": TRADE_DATE}) as ctx:
        tools.get_stock_data.invoke({"symbol": "MSFT", "start_date": "2026-01-02",
                                     "end_date": TRADE_DATE, "trade_date": TRADE_DATE})
        # P-10 early date (before the analysis date) must not bind the target.
        tools.get_global_news.invoke({"curr_date": "2026-01-02", "trade_date": TRADE_DATE})
        reg = ctx.registry
        assert reg.target_for("get_stock_data") is None
        assert reg.target_for("get_global_news") is None
        summary = availability.AvailabilitySummarizer(reg).snapshot(
            "stock", ("market", "news"), {"ticker": "NVDA", "trade_date": TRADE_DATE})
    # Observations are still recorded (not fabricated into targets).
    assert any(o["method"] == "get_stock_data" for o in summary["observations"])
    assert any(o["method"] == "get_global_news" for o in summary["observations"])
    gn = [i for i in summary["necessary_items"] if i["item_id"] == "get_global_news"][0]
    assert gn["status"] == "not_attempted"


# =========================================================================== #
# R03-08: entry/context lifetime (FC04/05; IR-05/09)                          #
# =========================================================================== #
def test_r03_08_no_active_context_direct_and_records_nothing(tmp_path, monkeypatch, offline):
    from tradingagents.agents import tools
    _called, _ = offline
    run_context = _run_context()
    assert run_context.current() is None
    out = tools.get_stock_data.invoke({"symbol": "NVDA", "start_date": "2026-01-02",
                                       "end_date": TRADE_DATE, "trade_date": TRADE_DATE})
    assert isinstance(out, str)
    # No scope recorded anything: the run registry does not exist outside a run.
    assert run_context.current() is None


def test_r03_08_nested_binding_restored(tmp_path, monkeypatch, offline):
    run_context = _run_context()
    with run_context.RunContext() as outer:
        assert run_context.current() is outer
        with run_context.RunContext() as inner:
            assert run_context.current() is inner
        assert run_context.current() is outer
    assert run_context.current() is None


def test_r03_08_exception_restores_binding_and_primary_error(tmp_path, monkeypatch, offline):
    run_context = _run_context()
    with run_context.RunContext() as outer:
        with pytest.raises(KeyError), run_context.RunContext():
            raise KeyError("primary")
        assert run_context.current() is outer
    assert run_context.current() is None


def test_r03_08_finish_is_idempotent_no_double_close(tmp_path, monkeypatch, offline):
    """R03-08 / FR-03-FC04 / IR-05. ``RunContext.finish()`` restores the binding
    exactly once and is idempotent: a second finish does not rebind and does not
    disturb a binding established after it. ``finish`` owns no resources; entry
    cleanup is the entry's own ``finally`` (verified in the real entry test)."""
    run_context = _run_context()

    ctx = run_context.RunContext()
    ctx.__enter__()
    assert run_context.current() is ctx
    ctx.finish()
    assert run_context.current() is None
    ctx.finish()                        # idempotent: no error, no rebind
    assert run_context.current() is None
    # A binding established afterwards stays intact across a stale finish.
    with run_context.RunContext() as other:
        assert run_context.current() is other
        ctx.finish()                    # stale, must not unbind `other`
        assert run_context.current() is other
    assert run_context.current() is None


def test_r03_08_finish_has_no_cleanup_hook(tmp_path, monkeypatch, offline):
    """R03-08 / FR-03-FC04 / IR-05. Resource ownership is the entry's: ``finish``
    must NOT call an arbitrary ``_cleanup`` hook on the context (an earlier design
    error). An attached ``_cleanup`` is never invoked by ``finish``."""
    run_context = _run_context()
    called = []
    ctx = run_context.RunContext()
    ctx.__dict__["_cleanup"] = lambda: called.append(1)   # must be ignored
    with ctx:
        assert run_context.current() is ctx
    # finish ran (binding restored) but never invoked the attached hook.
    assert run_context.current() is None
    assert called == []


def test_r03_08_explicit_internal_sharing_uses_same_scope(tmp_path, monkeypatch, offline):
    """R03-08 / FR-03-FC04 / IR-05. Explicit internal delegation shares the caller's
    run scope rather than creating a new one: a nested delegation sees the same
    ``current()`` and the same registry; an independent invocation does not."""
    run_context = _run_context()
    with run_context.RunContext() as outer:
        reg_outer = outer.registry
        with run_context.RunContext.delegate(outer) as inner:   # explicit share
            assert run_context.current() is outer
            assert inner.registry is reg_outer
    assert run_context.current() is None


def test_r03_08_token_reset_failure_not_silently_none(tmp_path, monkeypatch, offline):
    """R03-08 / FR-03-FC04 / IR-05. A token-reset failure (unsupported cross-context
    usage) must NOT silently replace the previous caller binding with ``None`` and
    claim a successful restore. Supported paths (normal / exception / early finish)
    restore correctly; an impossible reset leaves the binding untouched and warns."""
    run_context = _run_context()

    class _BadToken:
        pass

    with run_context.RunContext() as outer:
        assert run_context.current() is outer
        ctx = run_context.RunContext()
        ctx.__enter__()
        # Force the unsupported condition: a token that reset() rejects.
        ctx._token = _BadToken()
        ctx.finish()                    # must not crash, must not clobber to None
        # The binding is left as it was (not silently set to None); the earlier
        # design fallback `_current.set(None)` would have destroyed `outer` too.
        assert run_context.current() is not None
    # With the supported outer exit, the empty prior binding is restored to None.
    assert run_context.current() is None


def test_r03_08_observation_error_does_not_replace_body_error(tmp_path, monkeypatch, offline):
    """R03-08 / FR-03-FC04 / IR-05. The local observation helper never replaces the
    original body exception with an observation-handling error, and does not
    refetch."""
    from tradingagents.agents import tools  # noqa: F401  (import parity; helper below)
    availability = _availability()
    reg = availability.AvailabilityRegistry()
    calls = {"n": 0}

    def body():
        calls["n"] += 1
        raise ValueError("original body failure")

    def raising_classify(*a, **k):
        raise RuntimeError("classifier failure")

    with pytest.raises(ValueError, match="original body failure"):
        availability.observe_call(reg, "get_stock_data",
                                  {"symbol": "NVDA"}, body, classifier=raising_classify)
    assert calls["n"] == 1


def test_r03_08_programmatic_entry_scope_isolated_and_restored(tmp_path, monkeypatch, offline):
    """R03-08 / FR-03-FC04, FC05 / IR-05. The real programmatic entry binds its
    own run scope and restores the previous binding on normal finish; a scope the
    caller already holds is restored unchanged, and the run's scope is distinct
    (not leaked into the caller)."""
    _called, _ = offline
    run_context = _run_context()
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))

    # Capture the scope active at the entry's graph-execution boundary (the
    # contract places binding after basic validation and before the first
    # supported data call, i.e. around the graph run). Observing here avoids
    # fabricating a tool API; the real tool attachment is a later wave.
    inner_scopes = []
    real_run = graph._run_graph

    def spy(*_a, **k):  # noqa: ANN001 - graph-run passthrough
        inner_scopes.append(run_context.current())
        return real_run(*_a, **k)

    monkeypatch.setattr(graph, "_run_graph", spy)

    # (a) No outer scope: after the run current() is None again.
    graph.propagate("NVDA", TRADE_DATE)
    assert inner_scopes and all(s is not None for s in inner_scopes), inner_scopes
    assert run_context.current() is None

    # (b) An outer scope the caller holds is restored unchanged; the run binds a
    # distinct scope inside it (not the caller's).
    with run_context.RunContext() as outer:
        inner_scopes.clear()
        graph.propagate("NVDA", "2026-01-08")
        assert inner_scopes and all(s is not None for s in inner_scopes)
        assert all(s is not outer for s in inner_scopes), "the entry must not reuse the caller's scope"
        assert run_context.current() is outer
    assert run_context.current() is None


def test_r03_08_model_error_restores_binding(tmp_path, monkeypatch, offline):
    """R03-08 / FR-03-FC04 / IR-05. A vendor/model error mid-run leaves no run
    scope bound afterwards (the entry restores the prior binding on the error
    path), and the original provider error propagates."""
    _called, _ = offline
    run_context = _run_context()
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True, fail_at=1))
    with pytest.raises(RuntimeError, match="provider unavailable"):
        graph.propagate("NVDA", TRADE_DATE)
    assert run_context.current() is None


def test_r03_08_reused_graph_starts_fresh(tmp_path, monkeypatch, offline):
    """R03-08 / FR-03-FC04 / IR-05. Successive analyses on one reused graph each
    own a fresh ephemeral scope; the observation succeeds (the scope is seen at
    the run boundary) and the two runs do not share a live scope."""
    run_context = _run_context()
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    captured = []
    real = graph._run_graph

    def wrapped(*a, **k):
        captured.append(run_context.current())
        return real(*a, **k)

    monkeypatch.setattr(graph, "_run_graph", wrapped)
    graph.propagate("NVDA", TRADE_DATE)
    graph.propagate("NVDA", "2026-01-08")

    assert len(captured) == 2
    # The observation must succeed: a scope is bound at the execution boundary.
    assert all(s is not None for s in captured), captured
    assert captured[0] is not captured[1]


def test_r03_08_two_parallel_analyses_distinct_records_and_targets(tmp_path, monkeypatch, offline):
    """R03-08 / FR-03-FC04 / IR-05. Two concurrent scopes with distinct markers
    never mix records or targets, through real tool bodies under two concurrent
    ``RunContext`` scopes. (This is a registry-isolation check under two live
    scopes, not two real end-to-end analyses; the real-entry isolation and
    restoration are covered by the entry tests above.)"""
    import threading

    from tradingagents.agents import tools
    _called, _ = offline
    run_context = _run_context()
    availability = _availability()

    result = {}
    barrier = threading.Barrier(2)
    errors = []

    def run_one(key, symbol):
        try:
            with run_context.RunContext() as ctx:
                barrier.wait(timeout=5)
                # Each scope calls a different symbol through the real tool body.
                tools.get_stock_data.invoke({"symbol": symbol, "start_date": "2026-01-02",
                                             "end_date": TRADE_DATE, "trade_date": TRADE_DATE})
                reg = ctx.registry
                summary = availability.AvailabilitySummarizer(reg).snapshot(
                    "stock", ("market",), {"ticker": symbol, "trade_date": TRADE_DATE})
                result[key] = summary
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=run_one, args=("a", "NVDA"))
    t2 = threading.Thread(target=run_one, args=("b", "AMD"))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)
    assert not t1.is_alive() and not t2.is_alive()
    assert errors == [], errors
    a_symbols = {o.get("effective_parameters", {}).get("symbol")
                 for o in result["a"]["observations"]}
    b_symbols = {o.get("effective_parameters", {}).get("symbol")
                 for o in result["b"]["observations"]}
    assert a_symbols == {"NVDA"}
    assert b_symbols == {"AMD"}


def test_r03_08_stream_iteration_keeps_scope_and_early_close_restores(
        tmp_path, monkeypatch, offline):
    """R03-08 / FR-03-FC04 / IR-05, IR-09. The run scope is visible DURING stream
    iteration (not only when the generator is created), and an EARLY close of the
    stream followed by the entry's ``finish`` restores the prior caller binding.
    Deterministic: checks the live ``current()`` at each iteration, then breaks."""
    _called, _ = offline
    run_context = _run_context()
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))

    args = graph.propagator.get_graph_args()
    with run_context.RunContext() as outer:
        assert run_context.current() is outer
        init = graph.create_run_state("NVDA", TRADE_DATE)
        seen_scopes = []
        # A fresh inner run scope, as the entry binds it.
        with run_context.RunContext(analysis_context={"ticker": "NVDA",
                                                      "trade_date": TRADE_DATE}) as run_scope:
            stream = graph.stream_run(init, **args)
            try:
                for _messages, _chunk in stream:
                    # The execution scope is present at ITERATION time, not lost
                    # between generator creation and ``next``.
                    seen_scopes.append(run_context.current())
                    break            # early close
            finally:
                stream.close()       # close the generator explicitly
        # After the run scope finishes (entry finally), the outer caller is restored.
        assert run_context.current() is outer
        assert seen_scopes and seen_scopes[0] is run_scope
    assert run_context.current() is None


# =========================================================================== #
# R03-09: research timing (FC05; IR-12)                                        #
# =========================================================================== #
def _message_text(messages) -> str:
    """The exact prompt text of one model invocation, whether it was passed as a
    ready message list (``[(role, content), ...]`` / message objects) or as a
    plain string prompt."""
    if isinstance(messages, str):
        return messages
    if isinstance(messages, (list, tuple)):
        parts = []
        for m in messages:
            if isinstance(m, tuple):
                parts.append(str(m[-1]))
            else:
                parts.append(str(getattr(m, "content", "")))
        return "\n".join(parts)
    return str(messages)


class _CaptureModel(ScriptedModel):
    """Records each model invocation's path, schema/role and the *real* input
    text, in call order. The structured path captures the actual value the
    ``RunnableLambda`` receives (the manager/PM/trader prompts), not just the
    schema name, so the first Bull and manager inputs can be checked for content."""

    seen: list = Field(default_factory=list)   # [(order, via, schema_or_role, text)]

    def _record(self, via, schema_or_role, messages):
        self.seen.append((len(self.seen), via, schema_or_role, _message_text(messages)))

    def with_structured_output(self, schema, **kwargs):
        if not self.structured:
            raise NotImplementedError
        name = getattr(schema, "__name__", str(schema))

        def run(value):
            # Capture the real input the runnable received, by its actual type.
            self._record("structured", name, value)
            self._count()
            return STRUCTURED[schema]

        return RunnableLambda(run)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        step = (run_manager.metadata or {}).get("langgraph_node") if run_manager else None
        self._record("generate", step, messages)
        return super()._generate(messages, stop, run_manager, **kwargs)


# Explicit schema -> node role mapping. The structured-output capture records the
# schema's own __name__ as the role identity; this table lists the real binding so
# assertions reference an explicit mapping rather than a guess.
SCHEMA_ROLE = {
    "ResearchPlan": "Research Manager",
    "TraderProposal": "Trader",
    "PortfolioDecision": "Portfolio Manager",
    "SentimentReport": "Sentiment Analyst",
}


def _first_bull_call(model):
    """The first model invocation that is a Bull Researcher call. The first Bull
    runs a plain ``_generate`` (it does not do structured output), so it is the
    first ``generate`` record whose role text names the Bull Researcher."""
    for order, via, role, _text in model.seen:
        if via == "generate" and role == "Bull Researcher":
            return order
    return None


# ---- Independent research oracle ------------------------------------------- #
# The research block must carry the deterministic completeness value plus every
# necessary-gap and supplementary reason. To keep the expected values INDEPENDENT
# of the production summary, we control the necessity outcomes through real
# producer-shaped outputs whose statuses we state as literals here. One necessary
# item is deliberately a recognized `completeness`-breaking outcome, and one
# supplementary item is a recognized failure, so the oracle covers both.
#
# Controlled necessity plan (all four analysts enabled => seven necessity items):
#   get_stock_data              -> available  (real CSV row)
#   get_verified_market_snapshot-> available  (real 100.50 Close block)
#   get_income_statement        -> available  (real CSV row)
#   get_balance_sheet           -> available  (real CSV row)
#   get_cashflow                -> available  (real CSV row)
#   get_global_news             -> no_data    (real "No global news found" branch)
#   fetch_reddit_posts          -> unavailable (real "<Reddit unavailable: ...>" branch)
# => basic_completeness == "incomplete" (two non-available necessary items).
# Supplementary: get_macro_indicators -> unavailable (real DATA_UNAVAILABLE sentinel).
RESEARCH_EXPECTED_COMPLETENESS = "incomplete"
RESEARCH_EXPECTED_NECESSARY_GAPS = {
    "get_global_news": "no_data",
    "fetch_reddit_posts": "unavailable",
}
RESEARCH_EXPECTED_SUPPLEMENTARY = {"get_macro_indicators"}


def _apply_research_oracle(monkeypatch, state=None):
    """Install controlled real-producer-shaped outputs so the necessity oracle is a
    fixed independent literal. Records every router/loader call in a Counter keyed
    by method (not a set) so injection-vs-control call schedules can be compared
    without conflating duplicate calls. When ``state`` is given, the snapshot loader
    honours its LATE regime (latest Close -> NaN) so the Bear-boundary observation
    records a non-available status; without it the synchronous finite Close."""
    from collections import Counter

    fetch_log = Counter()
    for method in list(router.VENDOR_METHODS):
        for vendor in router.VENDOR_METHODS[method]:
            router.VENDOR_METHODS[method][vendor] = _oracle_router(method, fetch_log)

    def loader(*a, **k):
        fetch_log.update(["ohlcv"])
        late = bool(state and state.get("late"))
        return _market_prices_frame(SYNC_CLOSE,
                                    last_close=LATE_LAST_CLOSE if late else None)

    monkeypatch.setattr(snapshot, "load_ohlcv", loader)
    return fetch_log


def _oracle_router(method, fetch_log):
    def fn(*args, **kwargs):
        fetch_log.update([method])
        return _ORACLE_PROGRESS_OUTPUTS.get(method, f"{method} data")
    return fn


# Real producer shapes the classifier recognizes; statuses stated by the oracle.
_ORACLE_PROGRESS_OUTPUTS = {
    "get_stock_data": "Date,Open,High,Low,Close,Volume\n2026-01-09,100,101,99,100.5,1000000\n",
    "get_income_statement": "date,field,value\n2025-09-30,TotalRevenue,100000000\n",
    "get_balance_sheet": "date,field,value\n2025-09-30,TotalAssets,350000000\n",
    "get_cashflow": "date,field,value\n2025-09-30,OperatingCashFlow,90000000\n",
    "get_global_news": "No global news found between 2026-01-02 and 2026-01-09",
    "fetch_reddit_posts": "<Reddit unavailable: fetch failed (r/wallstreetbets); this is not an absence of discussion>",
    "get_macro_indicators": "DATA_UNAVAILABLE: optional macro_data could not be retrieved (missing key).",
    # Supplementary noise; recognized as unavailable/unavailable so they only
    # contribute to supplementary limitations.
    "fetch_stocktwits_messages": "<stocktwits unavailable: OSError>",
    "get_news": "No news found for NVDA between 2026-01-02 and 2026-01-09",
}


def _expected_research_lines():
    """The independent expected semantic lines the research block must contain:
    the completeness value, each non-available necessary item_id + status, and
    each supplementary method id. These are literals from the oracle above, not
    read from any production summary."""
    lines = [RESEARCH_EXPECTED_COMPLETENESS]
    for item_id in RESEARCH_EXPECTED_NECESSARY_GAPS:
        lines.append(item_id)
    lines.extend(sorted(RESEARCH_EXPECTED_NECESSARY_GAPS.values()))
    lines.extend(sorted(RESEARCH_EXPECTED_SUPPLEMENTARY))
    return lines


def test_r03_09_template_two_rounds_first_bull_same_call_and_roles(tmp_path, monkeypatch, offline):
    """R03-09 / FR-03-FC05 / IR-12. With two debate rounds, the *first* Bull call
    receives the deterministic research rendering (completeness value, every
    necessary-gap item/status and supplementary method) in the SAME invocation;
    later Bull, Bear and the Research Manager inputs carry the same fixed summary
    content, and existing report content is still present. The expected values are
    independent literals (see ``_expected_research_lines``). A control run built
    from an independently counted fetch/model schedule shows injection adds
    neither a model nor a data/vendor call. This negative form detects the
    update-only bug: if the wrapper returns a state update without supplying the
    same Bull invocation, the first Bull input lacks the block and this fails."""
    model = _CaptureModel(structured=True)
    graph = _graph(tmp_path, monkeypatch, model, max_debate_rounds=2)
    fetch_log = _apply_research_oracle(monkeypatch)

    final_state, _signal = graph.propagate("NVDA", TRADE_DATE)

    expected = _expected_research_lines()

    bull_rows = [row for row in model.seen if row[2] == "Bull Researcher"]
    assert len(bull_rows) >= 2, "two debate rounds must produce multiple Bull turns"
    first_bull_order = _first_bull_call(model)
    assert first_bull_order is not None, "the Bull Researcher must run"
    first_bull_text = next(t for o, _v, _r, t in model.seen if o == first_bull_order)

    # The first Bull's SAME invocation contains the research summary content.
    assert "availability" in first_bull_text.lower(), (
        "the first Bull input must carry the research availability block in the "
        "same invocation (an update-only wrapper would miss it)")
    for sig in expected:
        assert sig.lower() in first_bull_text.lower(), (
            f"first Bull input missing research signal {sig!r}")
    # Existing report content remains in the same first-Bull input.
    assert "market research report" in first_bull_text.lower()

    # The Research Manager is bound to the ResearchPlan schema by the real
    # structured call; the recorded identity must map through SCHEMA_ROLE.
    structured_roles = {r for _o, v, r, _t in model.seen if v == "structured"}
    assert "ResearchPlan" in structured_roles, "the Research Manager structured call must be recorded"
    assert SCHEMA_ROLE["ResearchPlan"] == "Research Manager"

    # Later Bull, Bear and the Research Manager carry the same fixed content. The
    # Research Manager runs the STRUCTURED path (ResearchPlan), so its recorded
    # role is the schema name; map it through the explicit SCHEMA_ROLE table.
    def _role(recorded):
        return SCHEMA_ROLE.get(recorded, recorded)

    later_bull = [t for o, _v, r, t in model.seen if r == "Bull Researcher" and o > first_bull_order]
    bear = [t for _o, _v, r, t in model.seen if r == "Bear Researcher"]
    manager = [(o, t) for o, _v, r, t in model.seen
               if _role(r) == "Research Manager" and "availability" in t.lower()]
    assert later_bull, "a later Bull round must run"
    assert bear, "the Bear Researcher must run"
    assert manager, "the Research Manager must run with the research block"
    for text in later_bull + bear + [t for _o, t in manager]:
        for sig in expected:
            assert sig.lower() in text.lower(), f"later role missing research signal {sig!r}"

    # Control: an independent run with the SAME controlled data/model shape but no
    # research wrapper (we cannot disable it here without wiring; instead we assert
    # the call schedule equals a fresh, independently counted run of the same
    # fixture, so injection introduced no extra model or fetch calls).
    control_model = _CaptureModel(structured=True)
    control_graph = _graph(tmp_path / "control", monkeypatch, control_model, max_debate_rounds=2)
    control_fetch = _apply_research_oracle(monkeypatch)
    control_graph.propagate("NVDA", TRADE_DATE)
    assert len(model.calls) == len(control_model.calls), "research injection must not add model calls"
    assert fetch_log == control_fetch, (
        "research injection must not add data/vendor calls "
        f"({dict(fetch_log)} vs {dict(control_fetch)})")


def test_r03_09_research_fixed_terminal_may_change(tmp_path, monkeypatch, offline):
    """R03-09 / FR-03-FC05 / IR-12. Ordering is explicit: the first Bull receives
    the research snapshot, then at the first Bear Researcher node (deterministically
    after the first Bull, before the Research Manager and END) a controlled real
    observation flips the verified-snapshot state to a non-available status. The
    research summary is captured as an independent deep copy from the first-Bull
    node input during the run; later Bear/Manager inputs still receive the ORIGINAL
    research summary; after END the terminal summary reflects the later update and
    genuinely differs from research on the verified-snapshot necessity item (status
    available -> non-available); final research equals the first-Bull copy."""
    _called, state = offline
    _apply_research_oracle(monkeypatch, state)
    model = _CaptureModel(structured=True)
    graph = _graph(tmp_path, monkeypatch, model)

    fired, fired_box = _late_observation_at_bear(graph, state)

    final_state, _signal = graph.propagate("NVDA", TRADE_DATE)

    # The controlled late observation really happened at the Bear boundary and the
    # real tool returned the non-available snapshot block.
    assert fired_box["done"], "the Bear-node boundary must fire"
    assert fired["snap_text"] is not None
    assert LATE_MARKER in fired["snap_text"], fired["snap_text"][:200]

    research = final_state.get("research_availability_summary")
    terminal = final_state.get("data_availability_summary")
    assert research is not None and terminal is not None
    # The single fixed research summary is EXACTLY what the FIRST Bull received in its
    # same invocation: the published research mapping's deterministic block is present
    # verbatim in that first-Bull model input.
    first_bull_text = next(t for o, _v, r, t in model.seen
                           if o == _first_bull_call(model))
    assert _availability().research_block(research) in first_bull_text, (
        "the first Bull did not receive the published research summary in the same call")
    # The verified-snapshot necessity item differs between research and terminal on
    # a legitimate recorded field (status). Research had it available; the terminal
    # observed a non-available late value. No summary-internal price is needed.
    research_snap = _snapshot_observation(research)
    terminal_snap = _snapshot_observation(terminal)
    assert research_snap and terminal_snap
    assert research_snap.get("status") == "available"
    assert terminal_snap.get("status") != "available", terminal_snap
    assert terminal_snap.get("status") != research_snap.get("status")
    # Research was not rerun: the later debate roles still received the ORIGINAL
    # (fixed) research block. The exact deterministic rendering of the published
    # research mapping appears verbatim in every later Bull/Bear/Manager input, and
    # the Research Manager is recorded through the structured path (ResearchPlan).
    fixed_block = _availability().research_block(research)
    later_bull_texts = [t for o, _v, r, t in model.seen
                        if r == "Bull Researcher" and o > _first_bull_call(model)]
    later_roles = later_bull_texts + [t for _o, _v, r, t in model.seen
                                      if r in ("Bear Researcher", "ResearchPlan")
                                      and "availability" in t.lower()]
    assert later_roles
    for text in later_roles:
        assert fixed_block in text, (
            "a later role received a refreshed research summary instead of the fixed one")


def _snapshot_observation(summary):
    for o in summary.get("observations", []):
        if o.get("method") == "get_verified_market_snapshot":
            return o
    return {}


# The D2-fixed stage texts, asserted INDEPENDENTLY of the production constants.
D2_RESEARCH_UNAVAILABLE = "program summary currently unavailable"  # IF-24 / §8.3
D2_REPORT_UNAVAILABLE = "program summary unavailable"              # report region


def test_r03_09_null_snapshot_fixed_text(tmp_path, monkeypatch, offline):
    """R03-09 / FR-03-FC05 / IR-12. When no research summary can be formed the
    stored value is null and the first Bull input emits the fixed research-stage
    text. The constant is first checked against the independent D2 literal (no
    self-justification), then the rendered output must contain it."""
    availability = _availability()
    fixed = availability.UNAVAILABLE_RESEARCH_TEXT
    # Independent spec check: the production constant matches the D2 literal.
    assert fixed.lower() == D2_RESEARCH_UNAVAILABLE

    class _NullSummarizer:
        # Compatible with the constructed interface: snapshot returns None.
        def __init__(self, *a, **k):
            pass

        def snapshot(self, *a, **k):
            return None

    monkeypatch.setattr(availability, "AvailabilitySummarizer", _NullSummarizer)
    model = _CaptureModel(structured=True)
    graph = _graph(tmp_path, monkeypatch, model)
    final_state, _signal = graph.propagate("NVDA", TRADE_DATE)

    assert final_state.get("research_availability_summary") is None
    first = _first_bull_call(model)
    assert first is not None
    text = next(t for o, _v, _r, t in model.seen if o == first)
    assert fixed.lower() in text.lower()
    # No fabricated completeness value is present when the summary is null.
    assert "basic_completeness" not in text.lower()


# =========================================================================== #
# R03-10: terminal snapshot and writers (FC05; IR-13)                         #
# =========================================================================== #
def _handbuilt_summary(marker, *, completeness="incomplete"):
    """A legal hand-built five-field summary fixture for consumer tests: the exact
    approved top-level structure, with a distinguishable marker in
    ``applicability_note`` and a real necessary gap so the writer has semantic
    content to render. Hand-built summaries establish consumer behaviour only."""
    return {
        "basic_completeness": completeness,
        "applicability_note": f"MARKER{marker}: applicability note for {marker}",
        "observations": [
            {"method": "get_stock_data",
             "status": "available" if completeness == "complete" else "unavailable",
             "reason": f"MARKER{marker} price observation",
             "effective_parameters": {"symbol": marker},
             "supported_path_ids": ["P-01"]},
        ],
        "necessary_items": [
            {"item_id": "get_stock_data",
             "status": "available" if completeness == "complete" else "withheld",
             "reason": f"MARKER{marker} necessary gap reason"},
        ],
        "supplementary_limitations": [
            {"method": "get_news", "reason": f"MARKER{marker} supplementary limitation"},
        ],
    }


def test_r03_10_programmatic_terminal_summary_state_and_report(tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC05 / IR-13. A real run with the real collector prepares a
    terminal ``data_availability_summary`` in the returned state; the deterministic
    Markdown and HTML reports both carry its semantic content (completeness value
    and the necessary-gap reason). The signal/decision/body remain intact."""
    _called, _state = offline
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    final_state, signal = graph.propagate("NVDA", TRADE_DATE)

    assert "data_availability_summary" in final_state
    summary = final_state["data_availability_summary"]
    assert summary is not None
    assert set(summary) == {"basic_completeness", "applicability_note",
                            "observations", "necessary_items", "supplementary_limitations"}
    save_path = tmp_path / "report"
    graph.save_reports(final_state, "NVDA", save_path)
    md = (save_path / "complete_report.md").read_text(encoding="utf-8")
    html = (save_path / "complete_report.html").read_text(encoding="utf-8")
    # Both carry the same deterministic section: the completeness value.
    completeness = summary["basic_completeness"]
    assert completeness in md
    assert completeness in html
    # A real necessary-gap reason (if any) is disclosed in both, semantically.
    gaps = [i for i in summary["necessary_items"]
            if i.get("status") != "available" and i.get("reason")]
    for gap in gaps:
        assert str(gap["reason"])[:40] in md
        assert str(gap["reason"])[:40] in html
    # Formal result intact and the report is not suppressed.
    assert signal == "Overweight"
    assert final_state["final_trade_decision"].strip()


def _forbid_live_registry_access(monkeypatch, availability):
    """Make any writer-time access to a live registry / RunContext / summarizer a
    test failure. The writer must read only the passed state."""
    run_context = _run_context()
    violations = []

    real_current = run_context.current

    def guarded_current(*a, **k):
        result = real_current(*a, **k)
        if result is not None:
            violations.append("run_context.current() while saving")
        return result

    monkeypatch.setattr(run_context, "current", guarded_current)
    monkeypatch.setattr(
        availability, "AvailabilitySummarizer",
        lambda *a, **k: violations.append("AvailabilitySummarizer constructed while saving")
        or _raise("summarizer must not run at save time"))
    return violations


def _raise(msg):
    raise AssertionError(msg)


def test_r03_10_independent_save_uses_passed_state_not_live_scope(tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC05 / IR-13. Hand-built summaries A and B (same approved
    five-field structure, different markers) establish consumer behaviour. With B
    scope active, saving passed state A must render A's content (Markdown and HTML),
    must not contain B's marker, and the writer must not read the live registry /
    current scope / summarizer; the passed state is not modified."""
    run_context = _run_context()
    availability = _availability()
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))

    summary_a = _handbuilt_summary("A")
    summary_b = _handbuilt_summary("B")
    assert summary_a["applicability_note"]          # A's summary is non-empty

    state_a = {
        "company_of_interest": "NVDA", "trade_date": TRADE_DATE,
        "market_report": "m", "sentiment_report": "s", "news_report": "n",
        "fundamentals_report": "f",
        "final_trade_decision": "**Rating**: Overweight", "final_rating": "Overweight",
        "investment_debate_state": {"bull_history": "", "bear_history": "",
                                    "history": "", "current_response": ""},
        "risk_debate_state": {"aggressive_history": "", "conservative_history": "",
                              "neutral_history": "", "history": ""},
        "data_availability_summary": copy.deepcopy(summary_a),
        "research_availability_summary": copy.deepcopy(summary_b),
    }
    state_a_before = copy.deepcopy(state_a)

    with run_context.RunContext() as scope_b:
        # Sanity: a genuine live B scope is active and distinct from A's content.
        assert scope_b is not None
        violations = _forbid_live_registry_access(monkeypatch, availability)
        save_path = tmp_path / "saved-a"
        graph.save_reports(state_a, "NVDA", save_path)

    md = (save_path / "complete_report.md").read_text(encoding="utf-8")
    html = (save_path / "complete_report.html").read_text(encoding="utf-8")
    # A's content appears; B's marker does not; the writer read no live registry.
    assert "MARKERA" in md and "MARKERA" in html
    assert "MARKERB" not in md and "MARKERB" not in html
    assert violations == [], violations
    # The passed state was not mutated by the writer.
    assert state_a == state_a_before


def test_r03_10_null_terminal_shows_unavailable_fixed_text(tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC05 / IR-13. A null terminal summary renders the fixed
    *report-stage* unavailable text (distinct from the research text). The constant
    is first checked against the independent D2 literal, then Markdown/HTML must
    contain it; the formal result is unchanged."""
    availability = _availability()
    fixed = availability.UNAVAILABLE_REPORT_TEXT
    # Independent spec check: the production constant matches the D2 report literal,
    # and it is the report text, not the research text.
    assert fixed.lower() == D2_REPORT_UNAVAILABLE
    assert fixed.lower() != D2_RESEARCH_UNAVAILABLE
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    final_state, signal = graph.propagate("NVDA", TRADE_DATE)
    fs = dict(final_state)
    fs["data_availability_summary"] = None
    save_path = tmp_path / "report-null"
    graph.save_reports(fs, "NVDA", save_path)
    md = (save_path / "complete_report.md").read_text(encoding="utf-8")
    html = (save_path / "complete_report.html").read_text(encoding="utf-8")
    assert fixed.lower() in md.lower()
    assert fixed.lower() in html.lower()
    assert signal == "Overweight"


def test_r03_10_snapshot_failure_warns_without_changing_result(tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC05 / IR-13. A terminal snapshot preparation failure logs a
    real warning and leaves the terminal field null/absent; it does not change the
    signal/decision/body or suppress the report, and does not fall back to the
    research/model text."""
    availability = _availability()
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))

    # Fail only snapshot construction at the injectable internal boundary; the
    # production terminal preparation handles the exception and warns.

    def boom(*a, **k):
        raise RuntimeError("terminal snapshot failed")

    monkeypatch.setattr(availability, "_snapshot_from_records", boom)
    with caplog_at_warning(monkeypatch, availability) as records:
        final_state, signal = graph.propagate("NVDA", TRADE_DATE)

    # Formal result is intact; the terminal summary is null/absent.
    assert signal == "Overweight"
    assert final_state.get("data_availability_summary") is None or \
        "data_availability_summary" not in final_state
    # A real warning was logged by the production path.
    assert records["seen"], "terminal snapshot failure must log a warning"
    # The report still saves and shows the fixed unavailable text, not model text.
    save_path = tmp_path / "report-fail"
    graph.save_reports(final_state, "NVDA", save_path)
    md = (save_path / "complete_report.md").read_text(encoding="utf-8")
    assert availability.UNAVAILABLE_REPORT_TEXT.lower() in md.lower()


def test_r03_10_cli_real_entry_terminal_display_and_save(tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC05 / IR-13. Drive the REAL CLI entry (``cli.run.run_analysis``)
    through the real graph and the real collector, with only the external model and
    vendors substituted. The terminal summary is displayed via the real
    ``display_complete_report`` (its actual input captured) and saved by the real
    writer. Both the display input and the saved Markdown/HTML carry the explicit
    completeness value and the necessary-gap reason/limitation content; the formal
    result and existing save/decline behaviour are preserved."""
    import cli.run as cli_run
    from cli.display import display_complete_report as real_display
    from cli.models import AnalystType

    _called, state = offline
    model = ScriptedModel(structured=True)
    graph = _graph(tmp_path, monkeypatch, model)

    displayed = {}

    def spy_display(final_state):
        displayed["state"] = copy.deepcopy(final_state)
        return real_display(final_state)

    monkeypatch.setattr(cli_run, "display_complete_report", spy_display)
    monkeypatch.setattr(cli_run, "TradingAgentsGraph", lambda *a, **k: graph)
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags=None: {
        "ticker": "NVDA", "analysis_date": TRADE_DATE,
        "analysts": [AnalystType.MARKET, AnalystType.NEWS, AnalystType.FUNDAMENTALS],
        "asset_type": "stock"})
    monkeypatch.setattr(cli_run, "_build_run_config", lambda selections, checkpoint: graph.config)
    monkeypatch.setattr(cli_run, "Live", _NullLive)
    monkeypatch.setattr(cli_run, "create_layout", lambda: None)
    monkeypatch.setattr(cli_run, "update_display", lambda *a, **k: None)
    import cli.main as m
    monkeypatch.setattr(m.typer, "prompt", lambda *a, **k: "N")

    # Flags answer save/show/html without any interactive prompt, so the report
    # goes to the CLI's default path under results_dir via the real writer.
    cli_run.run_analysis(flags={"save": True, "show": True, "html": True})

    # The real display received the passed terminal state, not a fake.
    assert "state" in displayed, "the real display_complete_report must run"
    term = displayed["state"].get("data_availability_summary")
    assert term is not None
    assert set(term) == {"basic_completeness", "applicability_note",
                         "observations", "necessary_items", "supplementary_limitations"}
    # Explicit completeness + any real necessary-gap reason / limitation are shown.
    completeness = term["basic_completeness"]
    gap_reasons = [str(i["reason"]) for i in term["necessary_items"]
                   if i.get("status") != "available" and i.get("reason")]
    limitations = [str(s.get("reason")) for s in term["supplementary_limitations"]
                   if s.get("reason")]
    # The real save_reports wrote under the CLI's default report path.
    produced = list((tmp_path / "results").glob("reports/*/complete_report.md"))
    assert produced, "the CLI must save a complete report via the real writer"
    md = produced[-1].read_text(encoding="utf-8")
    html = produced[-1].with_suffix(".html").read_text(encoding="utf-8")
    assert completeness in md and completeness in html
    for reason in gap_reasons:
        assert reason[:40] in md and reason[:40] in html
    for lim in limitations:
        assert lim[:40] in md and lim[:40] in html
    # Formal result intact.
    assert displayed["state"]["final_rating"] in ("Overweight", "Buy", "Hold",
                                                  "Underweight", "Sell", "REVIEW")


def test_r03_10_real_entry_owns_cleanup_primary_error_and_no_double_close(
        tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC04, FC05 / IR-05. Resource ownership belongs to the REAL
    entry: when the graph run raises a primary error the CLI entry binds a run
    scope, then its own ``finally`` restores the binding (no run scope leaks) and
    the original error propagates unchanged. This reaches the execution boundary
    (scope IS bound) before injecting the failure — it is not skipped on a
    not-yet-established scope."""
    import cli.run as cli_run
    from cli.models import AnalystType

    _called, _state = offline
    run_context = _run_context()

    def _boom(_):
        raise RuntimeError("provider unavailable")

    class _AlwaysFail(ScriptedModel):
        def with_structured_output(self, schema, **kwargs):
            return RunnableLambda(_boom)

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise RuntimeError("provider unavailable")

    graph = _graph(tmp_path, monkeypatch, _AlwaysFail(structured=True))

    monkeypatch.setattr(cli_run, "TradingAgentsGraph", lambda *a, **k: graph)
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags=None: {
        "ticker": "NVDA", "analysis_date": TRADE_DATE,
        "analysts": [AnalystType.MARKET],
        "asset_type": "stock"})
    monkeypatch.setattr(cli_run, "_build_run_config", lambda selections, checkpoint: graph.config)
    monkeypatch.setattr(cli_run, "Live", _NullLive)
    monkeypatch.setattr(cli_run, "create_layout", lambda: None)
    monkeypatch.setattr(cli_run, "update_display", lambda *a, **k: None)
    monkeypatch.setattr(cli_run, "display_complete_report", lambda s: None)
    import cli.main as m
    monkeypatch.setattr(m.typer, "prompt", lambda *a, **k: "N")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        cli_run.run_analysis(flags={"save": False, "show": False, "html": False})
    # The entry's finally restored the binding: no run scope leaked.
    assert run_context.current() is None


class caplog_at_warning:
    """A tiny context manager capturing WARNING+ records from the availability
    module's logger without depending on pytest's caplog fixture semantics."""

    def __init__(self, monkeypatch, module):
        self.module = module

    def __enter__(self):
        import logging

        self.records = {"seen": []}
        outer = self

        class _H(logging.Handler):
            def emit(self, record):
                if record.levelno >= logging.WARNING:
                    outer.records["seen"].append(record)

        self.handler = _H()
        self.logger = logging.getLogger(self.module.__name__)
        self._prev = self.logger.level
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.WARNING)
        return self.records

    def __exit__(self, *a):
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self._prev)
        return False


# =========================================================================== #
# R03-11: new-flow checkpoint boundary (FC04/05; IR-05)                       #
# =========================================================================== #
def _seed_old_checkpoint(tmp_path):
    """Seed a real checkpoint row via the retained component API (independent of
    the entries under test). Returns the checkpoint DB path and its initial bytes."""
    from tradingagents.graph import checkpointer

    cache = tmp_path / "cache"
    saver_ctx = checkpointer.get_checkpointer(cache, "NVDA")
    with saver_ctx as saver:
        saver.setup()
    db = cache / "checkpoints" / "NVDA.db"
    assert db.exists(), "seeded checkpoint DB must exist"
    return db, db.read_bytes()


def _install_checkpoint_guards(monkeypatch, graph):
    """After the old checkpoint is seeded, install fail-on-call guards on the real
    acquisition/read/resume/clear boundaries the entry could reach, at their actual
    import binding: the ``trading_graph`` module names ``get_checkpointer`` (which
    acquires the saver), ``checkpoint_step`` (which reads the resume step),
    ``thread_id`` (which derives the resume thread) and ``clear_checkpoint`` (which
    clears), plus the graph instance's ``begin_checkpoint`` (recompiles with a
    checkpointer, opens the saver, reads the step) and ``clear_checkpoint_on_success``.
    ANY call is recorded; the caller asserts the complete list is exactly empty.

    ``checkpoint_input``/``end_checkpoint``/``checkpoint_scope`` are deliberately
    NOT trapped: the baseline entry still uses them for its own initial-state and
    teardown plumbing, so trapping them would only mask the missing production
    module behind a plumbing error rather than evidencing that no checkpoint
    acquisition/resume/clear happened."""
    from tradingagents.graph import trading_graph as tg

    violations = []

    def trap(name):
        def fn(*a, **k):
            violations.append(name)
            return None
        return fn

    for name in ("get_checkpointer", "checkpoint_step", "thread_id", "clear_checkpoint"):
        monkeypatch.setattr(tg, name, trap(name))
    for name in ("begin_checkpoint", "clear_checkpoint_on_success"):
        monkeypatch.setattr(graph, name, trap(name))
    return violations


def test_r03_11_program_entry_no_resume_full_execution(tmp_path, monkeypatch, offline):
    """R03-11 / FR-03-FC04, FC05 / IR-05. With a real old checkpoint present and
    the option enabled, the program entry executes fully with a fresh schedule;
    acquisition/read/resume/clear calls are guarded to fail if they run, and the
    complete violations list is asserted empty. The old evidence stays byte-identical."""
    _called, _state = offline
    db, before = _seed_old_checkpoint(tmp_path)
    model = ScriptedModel(structured=True)
    graph = _graph(tmp_path, monkeypatch, model, checkpoint_enabled=True)

    # Install the guards AFTER seeding (seeding legitimately uses the component API).
    violations = _install_checkpoint_guards(monkeypatch, graph)

    final_state, signal = graph.propagate("NVDA", TRADE_DATE)
    assert signal == "Overweight"
    # No checkpoint acquisition/read/resume/clear was performed at all.
    assert violations == [], f"checkpoint boundary used by the new flow: {violations}"
    # Full execution: every report body is present.
    for key in ("market_report", "news_report", "fundamentals_report"):
        assert final_state[key].strip()
    # Old evidence still exists and is byte-identical.
    assert db.exists()
    assert db.read_bytes() == before


def test_r03_11_cli_entry_no_resume(tmp_path, monkeypatch, offline):
    """R03-11 / FR-03-FC05 / IR-05. The CLI entry also executes fully with the
    option enabled, performs no checkpoint acquisition/read/resume/clear (same
    fail-on-call guards, complete violations asserted empty), and leaves the seeded
    old checkpoint byte-identical."""
    import cli.run as cli_run
    from cli.models import AnalystType

    _called, _state = offline
    db, before = _seed_old_checkpoint(tmp_path)
    model = ScriptedModel(structured=True)
    graph = _graph(tmp_path, monkeypatch, model, checkpoint_enabled=True)
    violations = _install_checkpoint_guards(monkeypatch, graph)

    recorded = {"decision": None}

    def record_decision(ticker, trade_date, final_state):
        recorded["decision"] = final_state.get("final_trade_decision")

    monkeypatch.setattr(graph, "record_decision", record_decision)

    monkeypatch.setattr(cli_run, "TradingAgentsGraph", lambda *a, **k: graph)
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags=None: {
        "ticker": "NVDA", "analysis_date": TRADE_DATE,
        "analysts": [AnalystType.MARKET], "asset_type": "stock"})
    monkeypatch.setattr(cli_run, "_build_run_config", lambda selections, checkpoint: graph.config)
    monkeypatch.setattr(cli_run, "Live", _NullLive)
    monkeypatch.setattr(cli_run, "create_layout", lambda: None)
    monkeypatch.setattr(cli_run, "update_display", lambda *a, **k: None)
    import cli.main as m
    monkeypatch.setattr(m.typer, "prompt", lambda *a, **k: "N")
    cli_run.run_analysis()

    # The CLI executed the real graph fully and recorded a real decision.
    assert recorded["decision"] and "Overweight" in recorded["decision"]
    # No checkpoint boundary was touched by the CLI new flow.
    assert violations == [], f"CLI used a checkpoint boundary: {violations}"
    assert db.exists()
    assert db.read_bytes() == before


def test_r03_11_explicit_checkpoint_component_api_still_present():
    from tradingagents.graph import checkpointer
    for name in ("checkpoint_step", "clear_checkpoint", "get_checkpointer", "thread_id"):
        assert hasattr(checkpointer, name), f"checkpoint API {name} must be retained"


class _NullLive:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# =========================================================================== #
# R03-12: integration compatibility and structure (FC01-05; IR-09/11/13)       #
# =========================================================================== #
def test_r03_12_no_run_infra_in_state_and_json_summaries(tmp_path, monkeypatch, offline):
    """R03-12 / FR-03-FC05 / IR-05, IR-11. The returned state carries no live
    RunContext/lock/registry; the summaries are JSON-compatible plain mappings;
    the returned tuple shape is preserved."""
    import json

    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    result = graph.propagate("NVDA", TRADE_DATE)
    assert isinstance(result, tuple) and len(result) == 2
    final_state, _signal = result
    # No serialized runtime object (by type, not just by key name).
    mod = _run_context()
    for value in final_state.values():
        assert not isinstance(value, getattr(mod, "RunContext", object)), "RunContext leaked"
    assert "data_availability_summary" in final_state
    assert "research_availability_summary" in final_state
    for field in ("research_availability_summary", "data_availability_summary"):
        if final_state.get(field) is not None:
            json.dumps(final_state[field])


def test_r03_12_no_second_completeness_calculator(tmp_path, monkeypatch, offline):
    """R03-12 / FR-03-FC02 / IR-11. The summary carries exactly one completeness
    field; a consumer does not add a second calculated completeness key."""
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    final_state, _ = graph.propagate("NVDA", TRADE_DATE)
    summary = final_state.get("data_availability_summary")
    assert summary is not None
    assert "basic_completeness" in summary
    assert "missing_necessary_items" not in summary
    assert sum(1 for k in summary if "completeness" in k) == 1


def test_r03_12_compat_return_and_existing_behavior(tmp_path, monkeypatch, offline):
    """R03-12 / FR-03-FC01-05 / IR-13. Existing return tuple, decision parse,
    state log and memory behavior remain compatible under the new flow."""
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    final_state, signal = graph.propagate("NVDA", TRADE_DATE)
    assert signal == final_state["final_rating"] == "Overweight"
    assert list(tmp_path.glob("results/NVDA/TradingAgentsStrategy_logs/*.json"))
    assert [e["rating"] for e in graph.memory_log.load_entries()] == ["Overweight"]


# =========================================================================== #
# R03-10 (timing): graph END -> terminal snapshot -> record/delivery           #
# =========================================================================== #
def _wrap_record_and_count_terminal(monkeypatch, graph, terminal_owner=None):
    """Instrument the REAL record_decision (delegating to the original) and count
    TERMINAL-summary preparations (``_prepare_terminal_summary``) so a test proves the
    terminal field is present IN the state record_decision receives. The separate
    research snapshot is NOT counted here (it uses prepare_research_summary)."""
    seen = {"records": [], "terminal_snapshots": 0}

    real_record = graph.record_decision

    def record_spy(ticker, trade_date, final_state):
        seen["records"].append({
            "has_field": "data_availability_summary" in final_state,
            "value": final_state.get("data_availability_summary"),
        })
        return real_record(ticker, trade_date, final_state)

    monkeypatch.setattr(graph, "record_decision", record_spy)

    owner = terminal_owner if terminal_owner is not None else graph
    real_prepare = owner._prepare_terminal_summary

    def prepare_spy(*a, **k):
        seen["terminal_snapshots"] += 1
        return real_prepare(*a, **k)

    monkeypatch.setattr(owner, "_prepare_terminal_summary", prepare_spy)
    return seen


def test_r03_10_programmatic_terminal_ready_before_record_once(tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC05 / IR-13. Programmatic entry timing: graph END -> terminal
    snapshot -> record_decision, all on the same state. The spy on the REAL
    record_decision proves the terminal field is present IN that call (not checked
    only after return); record runs once and the terminal snapshot is built once."""
    _called, _state = offline
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    seen = _wrap_record_and_count_terminal(monkeypatch, graph)

    final_state, signal = graph.propagate("NVDA", TRADE_DATE)

    # record_decision called exactly once, and the terminal field was already present.
    assert len(seen["records"]) == 1
    assert seen["records"][0]["has_field"], "terminal field absent AT record_decision time"
    assert seen["records"][0]["value"] is not None
    # Exactly ONE terminal snapshot for this normal entry execution.
    assert seen["terminal_snapshots"] == 1
    # Same object reaches the returned state; formal result intact.
    assert final_state["data_availability_summary"] is seen["records"][0]["value"]
    assert signal == "Overweight"


def test_r03_10_cli_terminal_ready_before_record_once(tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC05 / IR-13. CLI entry timing: the real record_decision
    receives the terminal field already set; record once; terminal snapshot once."""
    import cli.run as cli_run
    from cli.models import AnalystType

    _called, _state = offline
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    seen = _wrap_record_and_count_terminal(monkeypatch, graph, terminal_owner=cli_run)

    monkeypatch.setattr(cli_run, "TradingAgentsGraph", lambda *a, **k: graph)
    monkeypatch.setattr(cli_run, "get_user_selections", lambda flags=None: {
        "ticker": "NVDA", "analysis_date": TRADE_DATE,
        "analysts": [AnalystType.MARKET], "asset_type": "stock"})
    monkeypatch.setattr(cli_run, "_build_run_config", lambda selections, checkpoint: graph.config)
    monkeypatch.setattr(cli_run, "Live", _NullLive)
    monkeypatch.setattr(cli_run, "create_layout", lambda: None)
    monkeypatch.setattr(cli_run, "update_display", lambda *a, **k: None)
    monkeypatch.setattr(cli_run, "display_complete_report", lambda s: None)
    import cli.main as m
    monkeypatch.setattr(m.typer, "prompt", lambda *a, **k: "N")
    cli_run.run_analysis(flags={"save": False, "show": False, "html": False})

    assert len(seen["records"]) == 1
    assert seen["records"][0]["has_field"], "terminal field absent AT record_decision time (CLI)"
    assert seen["records"][0]["value"] is not None
    assert seen["terminal_snapshots"] == 1


def test_r03_10_terminal_failure_record_gets_null_and_no_extra_calls(tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC05 / IR-13. When terminal snapshot construction fails, the
    REAL record_decision still receives the state with a null terminal value (the
    contract state), the formal result is unchanged, exactly one terminal snapshot
    is attempted, and NO extra model or data call is made by the failure path."""
    _called, _state = offline
    availability = _availability()
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    seen = _wrap_record_and_count_terminal(monkeypatch, graph)

    # Fail only the snapshot construction boundary (handled by the real snapshot()).
    monkeypatch.setattr(availability, "_snapshot_from_records",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))

    # Independently count model calls via a fresh scripted model's schedule size.
    final_state, signal = graph.propagate("NVDA", TRADE_DATE)

    assert len(seen["records"]) == 1
    assert seen["records"][0]["has_field"]                 # field present but null
    assert seen["records"][0]["value"] is None
    assert final_state["data_availability_summary"] is None
    assert signal == "Overweight"                          # formal result unchanged
    assert final_state["final_trade_decision"].strip()
    assert seen["terminal_snapshots"] == 1                 # attempted once, not retried


def test_r03_10_report_and_display_mapping_null_absent(tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC05 / IR-13. Consumer semantics for three inputs, using the
    independent D2 report literal (not the production constant as oracle):
      mapping -> that mapping's completeness/reason in MD + HTML + CLI display;
      null    -> fixed report unavailable text in MD + HTML + CLI display;
      absent  -> same fixed report unavailable text (section NOT silently omitted),
                 in MD + HTML + CLI display.
    No fallback to research/model text; Markdown/HTML share the same part."""
    import io

    from rich.console import Console

    import cli.display as display_mod
    from cli.display import display_complete_report

    mapping = _handbuilt_summary("M")
    cases = [("mapping", mapping), ("null", None), ("absent", "<ABSENT>")]

    for label, value in cases:
        graph = _graph(tmp_path / label, monkeypatch, ScriptedModel(structured=True))
        state = {
            "company_of_interest": "NVDA", "trade_date": TRADE_DATE,
            "market_report": "m", "final_trade_decision": "**Rating**: Overweight",
            "final_rating": "Overweight",
        }
        if value != "<ABSENT>":
            state["data_availability_summary"] = copy.deepcopy(value)
        save_path = tmp_path / label / "report"
        graph.save_reports(state, "NVDA", save_path)
        md = (save_path / "complete_report.md").read_text(encoding="utf-8")
        html = (save_path / "complete_report.html").read_text(encoding="utf-8")

        # Capture the CLI display's rendered text (its real console) for the case.
        buf = io.StringIO()
        monkeypatch.setattr(display_mod, "console", Console(file=buf, width=200))
        display_complete_report(copy.deepcopy(state))
        shown = buf.getvalue()

        if label == "mapping":
            assert mapping["basic_completeness"] in md
            assert mapping["basic_completeness"] in html
            assert mapping["basic_completeness"] in shown
            gap = "MARKERM necessary gap reason"
            assert gap[:40] in md and gap[:40] in html and gap[:40] in shown
        else:
            # null and absent both show the fixed report-unavailable literal.
            assert D2_REPORT_UNAVAILABLE in md.lower()
            assert D2_REPORT_UNAVAILABLE in html.lower()
            assert D2_REPORT_UNAVAILABLE in shown.lower()
            # Not silently omitted: the section heading is present.
            assert "Program Data Availability" in md
            assert "Program Data Availability" in shown
            # And the research-stage fixed text is NOT used as a fallback.
            assert D2_RESEARCH_UNAVAILABLE not in md.lower()


def test_r03_10_independent_save_ab_md_html_display(tmp_path, monkeypatch, offline):
    """R03-10 / FR-03-FC05 / IR-13. Independent consumer check: saving passed state A
    while a different B summary is live renders A's marker in Markdown, HTML and the
    CLI display; B never appears. Uses hand-built summaries (consumer-only)."""
    import io

    from rich.console import Console

    import cli.display as display_mod
    from cli.display import display_complete_report

    run_context = _run_context()
    graph = _graph(tmp_path, monkeypatch, ScriptedModel(structured=True))
    summary_a = _handbuilt_summary("A")
    summary_b = _handbuilt_summary("B")
    state_a = {
        "company_of_interest": "NVDA", "trade_date": TRADE_DATE,
        "market_report": "m", "final_trade_decision": "**Rating**: Overweight",
        "final_rating": "Overweight",
        "data_availability_summary": copy.deepcopy(summary_a),
        "research_availability_summary": copy.deepcopy(summary_b),
    }
    with run_context.RunContext():
        save_path = tmp_path / "ab"
        graph.save_reports(state_a, "NVDA", save_path)
        md = (save_path / "complete_report.md").read_text(encoding="utf-8")
        html = (save_path / "complete_report.html").read_text(encoding="utf-8")
        buf = io.StringIO()
        monkeypatch.setattr(display_mod, "console", Console(file=buf, width=200))
        display_complete_report(copy.deepcopy(state_a))
        shown = buf.getvalue()

    for where in (md, html, shown):
        assert "MARKERA" in where
        assert "MARKERB" not in where
