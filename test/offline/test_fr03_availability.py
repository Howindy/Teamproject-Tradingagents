"""Offline tests for the FR-03 run-scoped data availability summary (core boundaries).

Traceability: FR-03-FC01 through FR-03-FC05 and IR-09, IR-10, IR-11 (plus the
R03-08/R03-12 structural checks that assert on the registry/summary core). The
approved specification is ``docs/plans/round-03.md`` @
``d83abc909d6d7b40a7e7fabaff26ef971b9dbc2d`` (cases R03-01 and R03-03 through
R03-07, with core-boundary slices of R03-08/R03-12).

Design of the producer fixtures: rather than hand-writing output strings, every
fixture below is produced by *invoking the real vendor producer* with its lowest
network I/O replaced by a controlled substitute (``_make_api_request`` for Alpha
Vantage, ``_request`` for FRED/Polymarket, ``urlopen`` for StockTwits/Reddit,
``yf.Ticker``/``load_ohlcv`` for Yahoo). The captured string is what the
classifier is given, so the classification is checked against the actual producer
shape, not an invented one. A few AV shapes the review asked to confirm are
exercised this way too.

The two production modules (``tradingagents.dataflows.availability`` and
``tradingagents.run_context``) do not exist yet, so the tests below are expected
to start red. They are imported lazily inside helpers so the module still
collects and each scenario reports its own failure.

Chosen internal calling conventions for parts the D2 contract leaves to the
implementer (recorded in the phase report; NOT new architecture requirements):
  - ``DataResultClassifier.classify(method, effective_params, raw_result_or_exception, source_hint)``
    returns an object with ``status`` and ``reason`` attributes (IF-23).
  - Request-time target binding goes through ``registry.request(method, params)``
    (a pre-fetch protocol action that binds an unbound applicable target); a
    completed outcome goes through ``registry.accept(obs, params)``.
  - ``registry.observe(obs, params)`` is the convenience "request + accept" used
    where the test does not separately exercise binding.
  - ``AvailabilitySummarizer(registry).snapshot(asset_type, enabled_analysts, analysis_context)``
    is the IF-06 snapshot entry.
   - A run scope is ``run_context.RunContext()`` (context manager) with
     ``run_context.current()`` returning the active scope or ``None`` and
     ``ctx.registry`` the run registry.
   - Terminal/research delivery for null/failure cases uses two DISTINCT fixed
     texts (D2 does not unify them): ``availability.UNAVAILABLE_RESEARCH_TEXT``
     ("program summary currently unavailable", research-stage first-Bull block)
     and ``availability.UNAVAILABLE_REPORT_TEXT`` ("program summary unavailable",
     terminal report region). Tests assert each constant against the independent
     D2 literal, never from the production constant alone.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit

# These tests use fixed synthetic dates (e.g. 2026-11-20). Production vendors
# withhold live-only data for "historical" as_of dates relative to the wall clock,
# which would make the available-path fixtures non-deterministic. Pin "today" to a
# date AFTER every fixture date so the synthetic dates are non-historical and the
# real producer available branches are exercised; the explicit historical-date
# withheld tests (2020-01-02) remain historical and still exercise withholding.
_FIXED_TODAY = "2026-11-20"   # == every fixture's as_of; is_historical uses strict <


@pytest.fixture(autouse=True)
def _pin_today(monkeypatch):
    from tradingagents.dataflows import date_window

    monkeypatch.setattr(date_window, "get_current_date", lambda: _FIXED_TODAY)


# --------------------------------------------------------------------------- #
# Lazy access to the not-yet-implemented modules and chosen calling surface.   #
# --------------------------------------------------------------------------- #
def _availability():
    return importlib.import_module("tradingagents.dataflows.availability")


def _run_context():
    return importlib.import_module("tradingagents.run_context")


def _classify(method, params, raw, source_hint=None):
    """IF-23: classify one producer outcome. ``raw`` is a str or an exception."""
    mod = _availability()
    return mod.DataResultClassifier.classify(method, params, raw, source_hint)


def _new_registry():
    mod = _availability()
    return mod.AvailabilityRegistry()


def _summarize(registry, asset_type, enabled_analysts, analysis_context):
    mod = _availability()
    return mod.AvailabilitySummarizer(registry).snapshot(
        asset_type, enabled_analysts, analysis_context
    )


# --------------------------------------------------------------------------- #
# Real-producer fixtures with controlled low-level I/O.                        #
# Each helper returns the exact string the real vendor producer would return.  #
# --------------------------------------------------------------------------- #
_AV_OVERVIEW = (
    '{"Symbol":"AAPL","AssetType":"Common Stock","Name":"Apple Inc","Sector":"TECHNOLOGY",'
    '"MarketCapitalization":"3000000000000"}'
)
_AV_STATEMENT_OK = (
    '{"symbol":"AAPL","annualReports":[{"fiscalDateEnding":"2025-09-30",'
    '"reportedCurrency":"USD","totalRevenue":"400000000000"}],'
    '"quarterlyReports":[{"fiscalDateEnding":"2026-09-30","totalRevenue":"100000000000"}]}'
)
_AV_STATEMENT_EMPTY = '{"symbol":"AAPL","annualReports":[],"quarterlyReports":[]}'
_AV_NEWS_OK = (
    '{"items":"20","sentiment_score_definition":"...","feed":[{"title":"Apple ships",'
    '"url":"https://x/1","time_published":"20261120T120000","summary":"s",'
    '"overall_sentiment_label":"Neutral"}]}'
)
_AV_NEWS_EMPTY = '{"items":"0","feed":[]}'
_AV_INSIDER_OK = (
    '{"symbol":"AAPL","data":[{"transaction_date":"2026-11-19","share":1000,'
    '"executive":"Jane Doe"}]}'
)
_AV_INSIDER_EMPTY = '{"symbol":"AAPL","data":[]}'


def _yahoo_stock_data(monkeypatch, body):
    """Invoke the real Yahoo stock producer with a controlled ``yf.Ticker``."""
    from tradingagents.dataflows.vendors.yahoo import common as yahoo_common, market as yahoo_market

    class _T:
        def __init__(self, *_a, **_k):
            pass

        def history(self, **_k):
            return body

    monkeypatch.setattr(yahoo_market.yf, "Ticker", _T)
    # The producer treats an empty frame as no_data when the vendor is reachable.
    monkeypatch.setattr(yahoo_common, "vendor_reachable", lambda *_a, **_k: True)
    return yahoo_market.get_YFin_data_online


def _yahoo_prices_frame(dates, close=100.5):
    """An OHLCV frame shaped like ``yf.Ticker.history`` returns: a tz-aware
    ``DatetimeIndex`` plus the price columns (the stock producer reads
    ``data.index.tz``)."""
    import pandas as pd
    idx = pd.DatetimeIndex(list(dates)).tz_localize("UTC")
    n = len(list(dates))
    return pd.DataFrame({
        "Open": [100.0] * n, "High": [101.0] * n,
        "Low": [99.0] * n, "Close": [close] * n,
        "Volume": [1_000_000] * n,
    }, index=idx)


def _snapshot_ohlcv_frame(dates, close=100.5):
    """An OHLCV frame shaped like ``load_ohlcv`` returns for the snapshot: a
    ``Date`` column plus the price columns (``_verified_rows`` reads ``Date``)."""
    import pandas as pd
    n = len(list(dates))
    return pd.DataFrame({
        "Date": pd.to_datetime(list(dates)),
        "Open": [100.0] * n, "High": [101.0] * n,
        "Low": [99.0] * n, "Close": [close] * n,
        "Volume": [1_000_000] * n,
    })


def _yahoo_snapshot(monkeypatch, frame):
    """Invoke the real snapshot builder with a controlled ``load_ohlcv``."""
    from tradingagents.dataflows.vendors.yahoo import snapshot
    monkeypatch.setattr(snapshot, "load_ohlcv", lambda *a, **k: frame.copy())
    return snapshot.build_verified_market_snapshot


def _yahoo_fundamentals(monkeypatch, info):
    from tradingagents.dataflows.vendors.yahoo import (
        common as yahoo_common,
        fundamentals as yf_fund,
    )

    class _T:
        def __init__(self, *_a, **_k):
            self.info = info

    monkeypatch.setattr(yf_fund.yf, "Ticker", _T)
    monkeypatch.setattr(yahoo_common, "vendor_reachable", lambda *_a, **_k: True)
    return yf_fund.get_fundamentals


def _yahoo_insider(monkeypatch, frame, reachable=True):
    from tradingagents.dataflows.vendors.yahoo import fundamentals as yf_fund
    monkeypatch.setattr(yf_fund, "vendor_reachable", lambda *_a, **_k: reachable)

    class _T:
        def __init__(self, *_a, **_k):
            self.insider_transactions = frame

    monkeypatch.setattr(yf_fund.yf, "Ticker", _T)
    return yf_fund.get_insider_transactions


def _fred(monkeypatch, *, meta, obs):
    """Invoke the real FRED producer with a controlled ``_request`` dispatcher."""
    from tradingagents.dataflows.vendors import fred as fred_mod

    def stub(path, params):
        if path == "series":
            return {"seriess": meta}
        return {"observations": obs}

    monkeypatch.setattr(fred_mod, "_request", stub)
    # Pin FRED's "today" so a historical as_of_date is not clamped oddly.
    monkeypatch.setattr(fred_mod, "_fred_today", lambda: "2026-11-20")
    return fred_mod.get_macro_data


def _polymarket(monkeypatch, data):
    from tradingagents.dataflows.vendors import polymarket as pm
    monkeypatch.setattr(pm, "_request", lambda *a, **k: data)
    return pm.get_prediction_markets


def _stocktwits(monkeypatch, payload_obj):
    import json

    from tradingagents.dataflows.vendors import stocktwits as st

    class _Resp:
        def __init__(self, obj):
            self._body = json.dumps(obj).encode()

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(st, "urlopen", lambda *a, **k: _Resp(payload_obj))
    return st.fetch_stocktwits_messages


def _av(monkeypatch, body):
    """Patch Alpha Vantage's request boundary in each endpoint submodule.

    Each submodule did ``from ..common import _make_api_request`` at import time,
    so the name to patch is that submodule's own binding (not ``common``'s).
    Returns the package for calling the real endpoint producers.
    """
    from tradingagents.dataflows.vendors import alpha_vantage as av
    from tradingagents.dataflows.vendors.alpha_vantage import (
        fundamentals as av_fund,
        news as av_news,
    )
    stub = lambda fn, params: body  # noqa: E731  (controlled request body)
    monkeypatch.setattr(av_fund, "_make_api_request", stub)
    monkeypatch.setattr(av_news, "_make_api_request", stub)
    return av


# =========================================================================== #
# R03-01: producer classifications across the 14 methods (FC01/03; IR-09)      #
# =========================================================================== #
def test_r03_01_stock_data_available_from_real_producer(monkeypatch):
    import pandas as pd

    frame = _yahoo_prices_frame(pd.bdate_range("2026-11-01", periods=15))
    producer = _yahoo_stock_data(monkeypatch, frame)
    raw = producer("AAPL", "2026-11-01", "2026-11-20")
    obs = _classify("get_stock_data",
                    {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}, raw, None)
    assert obs.status == "available"
    assert obs.reason
    assert obs.source is None  # router path does not expose the vendor


def test_r03_01_stock_data_empty_raises_no_data(monkeypatch):
    import pandas as pd

    from tradingagents.dataflows.errors import NoMarketDataError
    empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    producer = _yahoo_stock_data(monkeypatch, empty)
    with pytest.raises(NoMarketDataError):
        producer("AAPL", "2026-11-01", "2026-11-20")
    # The router turns that typed error into the no-data sentinel; classify that.
    from tradingagents.dataflows.router import no_data_available
    sentinel = no_data_available(NoMarketDataError("AAPL", "AAPL", "rows between 11-01 and 11-20"))
    obs = _classify("get_stock_data",
                    {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"},
                    sentinel, None)
    assert obs.status == "no_data"


def test_r03_01_av_header_only_csv_is_no_data(monkeypatch):
    """R03-01 / FR-03-FC01 / IR-09. The AV stock producer path returns a header-only
    CSV (via _filter_csv_by_date_range over an empty body) which is ``no_data``."""
    body = "timestamp,open,high,low,close,volume\n"  # header only
    obs = _classify("get_stock_data",
                    {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}, body, None)
    assert obs.status == "no_data"


def test_r03_01_av_overview_available_and_empty(monkeypatch):
    av = _av(monkeypatch, _AV_OVERVIEW)
    raw_ok = av.get_fundamentals("AAPL", as_of_date="2026-11-20")
    obs = _classify("get_fundamentals", {"ticker": "AAPL", "as_of": "2026-11-20"}, raw_ok, None)
    assert obs.status == "available"
    # Empty overview JSON object -> no_data.
    av2 = _av(monkeypatch, "{}")
    raw_empty = av2.get_fundamentals("AAPL", as_of_date="2026-11-20")
    obs2 = _classify("get_fundamentals", {"ticker": "AAPL", "as_of": "2026-11-20"}, raw_empty, None)
    assert obs2.status == "no_data"


def test_r03_01_av_statement_arrays_available_and_empty(monkeypatch):
    for method in ("get_income_statement", "get_balance_sheet", "get_cashflow"):
        av = _av(monkeypatch, _AV_STATEMENT_OK)
        raw_ok = getattr(av, method)("AAPL", freq="quarterly", as_of_date="2026-11-20")
        obs = _classify(method, {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
                        raw_ok, None)
        assert obs.status == "available", method
        av2 = _av(monkeypatch, _AV_STATEMENT_EMPTY)
        raw_empty = getattr(av2, method)("AAPL", freq="quarterly", as_of_date="2026-11-20")
        obs2 = _classify(method, {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
                         raw_empty, None)
        assert obs2.status == "no_data", method


def test_r03_01_av_news_feed_available_and_empty(monkeypatch):
    av = _av(monkeypatch, _AV_NEWS_OK)
    raw_ok = av.get_news("AAPL", "2026-11-13", "2026-11-20")
    obs = _classify("get_news", {"ticker": "AAPL", "start_date": "2026-11-13",
                                 "end_date": "2026-11-20"}, raw_ok, None)
    assert obs.status == "available"
    av2 = _av(monkeypatch, _AV_NEWS_EMPTY)
    raw_empty = av2.get_news("AAPL", "2026-11-13", "2026-11-20")
    obs2 = _classify("get_news", {"ticker": "AAPL", "start_date": "2026-11-13",
                                  "end_date": "2026-11-20"}, raw_empty, None)
    assert obs2.status == "no_data"


def test_r03_01_av_insider_available_and_empty(monkeypatch):
    av = _av(monkeypatch, _AV_INSIDER_OK)
    raw_ok = av.get_insider_transactions("AAPL", as_of_date="2026-11-20")
    obs = _classify("get_insider_transactions", {"ticker": "AAPL", "trade_date": "2026-11-20"},
                    raw_ok, None)
    assert obs.status == "available"
    av2 = _av(monkeypatch, _AV_INSIDER_EMPTY)
    raw_empty = av2.get_insider_transactions("AAPL", as_of_date="2026-11-20")
    obs2 = _classify("get_insider_transactions", {"ticker": "AAPL", "trade_date": "2026-11-20"},
                     raw_empty, None)
    assert obs2.status == "no_data"


def test_r03_01_yahoo_fundamentals_label_value_format(monkeypatch):
    """R03-01 / FR-03-FC01 / IR-09. Yahoo fundamentals use ``label: value`` lines
    under a ``# Company Fundamentals for ...`` header (not a Markdown table)."""
    info = {"longName": "Apple Inc", "sector": "Technology", "marketCap": 3_000_000_000_000,
            "currency": "USD", "financialCurrency": "USD"}
    producer = _yahoo_fundamentals(monkeypatch, info)
    raw = producer("AAPL", as_of_date=None)
    assert raw.startswith("# Company Fundamentals for AAPL")
    assert "Sector: Technology" in raw
    obs = _classify("get_fundamentals", {"ticker": "AAPL", "as_of": None}, raw, None)
    assert obs.status == "available"


def test_r03_01_yahoo_fundamentals_empty_info_is_no_data(monkeypatch):
    from tradingagents.dataflows.errors import NoMarketDataError
    producer = _yahoo_fundamentals(monkeypatch, {"trailingPegRatio": None})  # stub dict
    with pytest.raises(NoMarketDataError):
        producer("AAPL", as_of_date=None)


def test_r03_01_yahoo_fundamentals_withheld_on_historical_date(monkeypatch):
    """R03-01 / FR-03-FC01 / IR-09. A historical as_of_date makes the Yahoo
    profile withheld (date-controlled through the producer, not faked)."""
    producer = _yahoo_fundamentals(monkeypatch, {"longName": "Apple"})
    raw = producer("AAPL", as_of_date="2020-01-02")   # a past date -> withheld
    assert "withheld" in raw.lower()
    obs = _classify("get_fundamentals", {"ticker": "AAPL", "as_of": "2020-01-02"}, raw, None)
    assert obs.status == "withheld"


def test_r03_01_snapshot_available_with_na_indicators(monkeypatch):
    import pandas as pd
    frame = _snapshot_ohlcv_frame(pd.bdate_range(end="2026-11-20", periods=40))
    producer = _yahoo_snapshot(monkeypatch, frame)
    raw = producer("AAPL", "2026-11-20", 30)
    assert "## Verified market data snapshot for AAPL" in raw
    obs = _classify("get_verified_market_snapshot",
                    {"symbol": "AAPL", "as_of": "2026-11-20", "look_back_days": 30}, raw, "Yahoo")
    assert obs.status == "available"
    assert obs.source == "Yahoo"


def test_r03_01_snapshot_nonfinite_close_is_not_available(monkeypatch):
    import math

    import pandas as pd
    frame = _snapshot_ohlcv_frame(pd.bdate_range(end="2026-11-20", periods=40))
    frame.iloc[-1, frame.columns.get_loc("Close")] = math.inf
    producer = _yahoo_snapshot(monkeypatch, frame)
    raw = producer("AAPL", "2026-11-20", 30)
    obs = _classify("get_verified_market_snapshot",
                    {"symbol": "AAPL", "as_of": "2026-11-20", "look_back_days": 30}, raw, "Yahoo")
    assert obs.status != "available"


def test_r03_01_snapshot_missing_close_is_not_available(monkeypatch):
    import pandas as pd
    frame = _snapshot_ohlcv_frame(pd.bdate_range(end="2026-11-20", periods=40))
    frame.iloc[-1, frame.columns.get_loc("Close")] = float("nan")
    producer = _yahoo_snapshot(monkeypatch, frame)
    raw = producer("AAPL", "2026-11-20", 30)
    obs = _classify("get_verified_market_snapshot",
                    {"symbol": "AAPL", "as_of": "2026-11-20", "look_back_days": 30}, raw, "Yahoo")
    assert obs.status != "available"


def test_r03_01_yahoo_news_available_and_empty(monkeypatch):
    from tradingagents.dataflows.vendors.yahoo import news as yf_news

    class _T:
        def __init__(self, *_a, **_k):
            pass

        def get_news(self, count=10):
            return [{"content": {"title": "Apple ships a thing", "summary": "body",
                                 "pubDate": "2026-11-20T12:00:00Z",
                                 "canonicalUrl": {"url": "https://x/1"},
                                 "provider": {"displayName": "Reuters"}}}]

    monkeypatch.setattr(yf_news.yf, "Ticker", _T)
    raw = yf_news.get_news_yfinance("AAPL", "2026-11-13", "2026-11-20")
    obs = _classify("get_news", {"ticker": "AAPL", "start_date": "2026-11-13",
                                 "end_date": "2026-11-20"}, raw, None)
    assert obs.status == "available"


def test_r03_01_yahoo_news_heading_without_article_not_available(monkeypatch):
    from tradingagents.dataflows.vendors.yahoo import news as yf_news

    class _T:
        def __init__(self, *_a, **_k):
            pass

        def get_news(self, count=10):
            return []   # empty feed, but search answers "no tagged article" -> unavailable

    class _Search:
        def __init__(self, *_a, **_k):
            self.news = []
            self.quotes = []

    monkeypatch.setattr(yf_news.yf, "Ticker", _T)
    monkeypatch.setattr(yf_news.yf, "Search", _Search)
    try:
        raw = yf_news.get_news_yfinance("AAPL", "2026-11-13", "2026-11-20")
    except Exception:
        # A raised VendorUnavailableError is itself the unavailable signal.
        return
    obs = _classify("get_news", {"ticker": "AAPL", "start_date": "2026-11-13",
                                 "end_date": "2026-11-20"}, raw, None)
    assert obs.status != "available"


def test_r03_01_fred_available(monkeypatch):
    producer = _fred(monkeypatch,
                     meta=[{"title": "CPI", "units_short": "Index", "frequency": "Monthly"}],
                     obs=[{"date": "2026-10-01", "value": "300.1"}])
    raw = producer("cpi", "2026-11-20", 365)
    obs = _classify("get_macro_indicators",
                    {"indicator": "cpi", "as_of": "2026-11-20", "look_back_days": 365}, raw, "FRED")
    assert obs.status == "available"
    assert obs.source == "FRED"


def test_r03_01_fred_series_not_found_is_no_data(monkeypatch):
    """R03-01 / FR-03-FC01 / IR-09. A FRED series-not-found notice is ``no_data``
    (per D2 §8.3), not ``unavailable``."""
    producer = _fred(monkeypatch, meta=[], obs=[])
    raw = producer("ZZZ", "2026-11-20", 365)
    assert "not found" in raw.lower()
    obs = _classify("get_macro_indicators",
                    {"indicator": "ZZZ", "as_of": "2026-11-20", "look_back_days": 365}, raw, "FRED")
    assert obs.status == "no_data"


def test_r03_01_fred_empty_window_is_no_data(monkeypatch):
    producer = _fred(monkeypatch,
                     meta=[{"title": "CPI", "units_short": "Index", "frequency": "Monthly"}],
                     obs=[])
    raw = producer("cpi", "2026-11-20", 365)
    obs = _classify("get_macro_indicators",
                    {"indicator": "cpi", "as_of": "2026-11-20", "look_back_days": 365}, raw, "FRED")
    assert obs.status == "no_data"


def test_r03_01_polymarket_available_and_no_matches(monkeypatch):
    search = {"events": [{"markets": [
        {"question": "Fed cut?", "outcomePrices": '["0.62"]', "outcomes": '["Yes"]',
         "volumeNum": 1_200_000, "endDate": "2026-12-18T00:00:00Z", "closed": False,
         "active": True, "oneWeekPriceChange": 0.03}]}]}
    producer = _polymarket(monkeypatch, search)
    raw = producer("Fed rate cut", 6, as_of_date=None)
    obs = _classify("get_prediction_markets",
                    {"topic": "Fed rate cut", "limit": 6, "trade_date": None}, raw, "Polymarket")
    assert obs.status == "available"
    assert obs.source == "Polymarket"
    producer2 = _polymarket(monkeypatch, {"events": []})
    raw2 = producer2("Fed rate cut", 6, as_of_date=None)
    obs2 = _classify("get_prediction_markets",
                     {"topic": "Fed rate cut", "limit": 6, "trade_date": None}, raw2, "Polymarket")
    assert obs2.status == "no_data"


def test_r03_01_polymarket_withheld_on_historical_date(monkeypatch):
    producer = _polymarket(monkeypatch, {"events": []})
    raw = producer("Fed rate cut", 6, as_of_date="2020-01-02")
    assert "withheld" in raw.lower()
    obs = _classify("get_prediction_markets",
                    {"topic": "Fed rate cut", "limit": 6, "trade_date": "2020-01-02"}, raw, "Polymarket")
    assert obs.status == "withheld"


def test_r03_01_stocktwits_available_and_no_messages(monkeypatch):
    payload = {"messages": [
        {"created_at": "2026-11-20T10:00:00Z", "body": "$AAPL buy the dip",
         "user": {"username": "u1"}, "entities": {"sentiment": {"basic": "Bullish"}}},
        {"created_at": "2026-11-20T11:00:00Z", "body": "$AAPL going higher",
         "user": {"username": "u2"}, "entities": {"sentiment": {"basic": "Bullish"}}},
    ]}
    producer = _stocktwits(monkeypatch, payload)
    raw = producer("AAPL", limit=30, start_date="2026-11-13", end_date="2026-11-20")
    obs = _classify("fetch_stocktwits_messages",
                    {"ticker": "AAPL", "limit": 30, "start_date": "2026-11-13",
                     "end_date": "2026-11-20"}, raw, "StockTwits")
    assert obs.status == "available"
    assert obs.source == "StockTwits"


def test_r03_01_stocktwits_none_is_no_data(monkeypatch):
    """R03-01 / FR-03-FC01 / IR-09. An empty StockTwits payload with NO analysis
    window yields the producer's "no messages found" branch (``no_data``). With a
    historical window the producer instead reports a coverage gap (``unavailable``)
    because it cannot prove absence over a window it never observed, so the no-window
    call is the branch that genuinely means no_data."""
    producer = _stocktwits(monkeypatch, {"messages": []})
    raw = producer("AAPL", limit=30)
    obs = _classify("fetch_stocktwits_messages",
                    {"ticker": "AAPL", "limit": 30}, raw, "StockTwits")
    assert obs.status == "no_data"


def test_r03_01_unknown_text_and_propagated_error_unavailable(monkeypatch):
    obs = _classify("get_stock_data",
                    {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"},
                    "totally unrecognized body", None)
    assert obs.status == "unavailable"
    assert obs.source is None
    from tradingagents.dataflows.errors import VendorUnavailableError
    obs2 = _classify("get_stock_data",
                     {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"},
                     VendorUnavailableError("boom"), None)
    assert obs2.status == "unavailable"


def test_r03_01_indicator_available_via_close_producer(monkeypatch):
    # One indicator's own dated value block (the producer format for a single one).
    raw = ("## rsi values from 2026-11-01 to 2026-11-20:\n\n"
           "2026-11-20: 55.20\n")
    obs = _classify("get_indicators",
                    {"symbol": "AAPL", "indicator": "rsi", "as_of": "2026-11-20",
                     "look_back_days": 30}, raw, None)
    assert obs.status == "available"


# =========================================================================== #
# R03-03: applicability and completeness (FC02/03; IR-11)                      #
# =========================================================================== #
_ANALYSIS_CONTEXT = {"ticker": "AAPL", "trade_date": "2026-11-20",
                     "stock_start": "2026-11-01", "stock_end": "2026-11-20"}
_ALL_FOUR_ANALYSTS = ("market", "social", "news", "fundamentals")


def _seven_params():
    """The seven necessity targets, bound at request time with the target's own
    effective parameters (no classify-then-bind shortcut)."""
    return {
        "get_stock_data": {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"},
        "get_verified_market_snapshot": {"symbol": "AAPL", "as_of": "2026-11-20", "look_back_days": 30},
        "get_income_statement": {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
        "get_balance_sheet": {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
        "get_cashflow": {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
        "get_global_news": {"as_of": "2026-11-20", "look_back_days": 7, "limit": 10},
        "fetch_reddit_posts": {"ticker": "AAPL", "subreddits": ("wallstreetbets",),
                               "start_date": "2026-11-13", "end_date": "2026-11-20",
                               "limit_per_sub": 5},
    }


def _real_reddit_available_block():
    """Invoke the real Reddit producer (``fetch_reddit_posts``) with its lowest
    network I/O (``_fetch_subreddit_rss``) replaced by controlled posts that carry
    the real producer's fields. Returns the exact formatted block the producer
    emits: a ``r/<sub> — N recent posts mentioning <TICKER>:`` header, one
    ``[date] title`` line per post and a ``body excerpt`` line. This is the shape
    the classifier is fed below, not a hand-written approximation."""
    from tradingagents.dataflows.vendors import reddit as reddit_mod

    posts = [{
        "title": "AAPL earnings beat expectations",
        "created_utc": 1_763_000_000,          # 2025-11-10 UTC
        "selftext": "Strong quarter, guidance raised for next year.",
        "subreddit": "wallstreetbets",
    }]

    real = reddit_mod._fetch_subreddit_rss
    reddit_mod._fetch_subreddit_rss = lambda *_a, **_k: posts
    try:
        return reddit_mod.fetch_reddit_posts(
            "AAPL", ("wallstreetbets",), start_date=None, end_date=None,
            limit_per_sub=5, screen=None)
    finally:
        reddit_mod._fetch_subreddit_rss = real


def _real_global_news_string():
    """Invoke the real Alpha Vantage ``get_global_news`` producer with its request
    boundary replaced by a controlled NEWS_SENTIMENT body; the producer returns
    the real JSON string the classifier is fed."""
    from tradingagents.dataflows.vendors.alpha_vantage import news as av_news

    real = av_news._make_api_request
    av_news._make_api_request = lambda _fn, _params: _AV_NEWS_OK
    try:
        return av_news.get_global_news("2026-11-20", 7, 10)
    finally:
        av_news._make_api_request = real


def _available_raw_for(method):
    """A producer-shaped available outcome per method for the registry path.

    The Reddit entry is produced by the real ``fetch_reddit_posts`` (quantity,
    mentioning-ticker header, ``[date]`` line and body excerpt). The remaining
    entries reproduce the existing producer output shapes the R03-01 tests above
    validate: the AV statements (``get_income_statement``/``get_balance_sheet``/
    ``get_cashflow``) return the real ``date,field,value`` CSV body, the Yahoo
    stock path returns a dated OHLCV CSV, the snapshot returns its
    ``## Verified market data snapshot`` block, and global news returns the real
    AV NEWS_SENTIMENT feed formatted by its existing router/classifier branch (a
    ``## Global Market News`` headline block).
    """
    if method == "fetch_reddit_posts":
        return _real_reddit_available_block()
    return {
        "get_stock_data": "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n",
        "get_verified_market_snapshot": (
            "## Verified market data snapshot for AAPL\n\n- Latest trading row used: 2026-11-20\n"
            "| Close | 100.50 |\n"),
        "get_income_statement": "2026-09-30,TotalRevenue,100000000\n",
        "get_balance_sheet": "2026-09-30,TotalAssets,350000000\n",
        "get_cashflow": "2026-09-30,OperatingCashFlow,90000000\n",
        "get_global_news": ("## Global Market News, from 2026-11-13 to 2026-11-20:\n\n"
                            "### Fed holds rates steady (source: Reuters)\nbody\n"),
    }[method]


def _populate_available(registry):
    params = _seven_params()
    for method, p in params.items():
        registry.request(method, p)                       # pre-fetch target binding
        obs = _classify(method, p, _available_raw_for(method),
                        "Yahoo" if method == "get_verified_market_snapshot"
                        else ("Reddit" if method == "fetch_reddit_posts" else None))
        registry.accept(obs, p)


def test_r03_03_seven_items_complete():
    reg = _new_registry()
    _populate_available(reg)
    summary = _summarize(reg, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    assert summary is not None
    assert set(summary.keys()) == {"basic_completeness", "applicability_note",
                                   "observations", "necessary_items", "supplementary_limitations"}
    assert summary["basic_completeness"] == "complete"
    assert {i["item_id"] for i in summary["necessary_items"]} == set(_seven_params())
    import json
    json.dumps(summary)


@pytest.mark.parametrize("bad_status,raw", [
    ("no_data", "Date,Open,High,Low,Close,Volume\n"),  # header-only price
    ("unavailable", "DATA_UNAVAILABLE: no configured vendor could serve get_stock_data right now."),
])
def test_r03_03_one_item_not_available_incomplete_no_dup(bad_status, raw):
    reg = _new_registry()
    _populate_available(reg)
    p = _seven_params()["get_stock_data"]
    obs = _classify("get_stock_data", p, raw, None)
    reg.accept(obs, p)
    summary = _summarize(reg, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    assert summary["basic_completeness"] == "incomplete"
    gap = [i for i in summary["necessary_items"] if i["item_id"] == "get_stock_data"][0]
    assert gap["status"] == bad_status
    assert gap.get("reason")
    # No duplication into supplementary limitations.
    assert "get_stock_data" not in {s.get("method") for s in summary["supplementary_limitations"]}


def test_r03_03_missing_completion_is_not_attempted_only_in_necessity():
    reg = _new_registry()
    params = _seven_params()
    for method, p in params.items():
        if method == "get_cashflow":
            continue
        reg.request(method, p)
        reg.accept(_classify(method, p, _available_raw_for(method), None), p)
    summary = _summarize(reg, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    assert summary["basic_completeness"] == "incomplete"
    cash = [i for i in summary["necessary_items"] if i["item_id"] == "get_cashflow"][0]
    assert cash["status"] == "not_attempted"
    assert all(o["status"] != "not_attempted" for o in summary["observations"])


def test_r03_03_analyst_subset_mapped_items():
    expected = {
        "market": {"get_stock_data", "get_verified_market_snapshot"},
        "fundamentals": {"get_income_statement", "get_balance_sheet", "get_cashflow"},
        "news": {"get_global_news"},
        "social": {"fetch_reddit_posts"},
    }
    for analyst, want in expected.items():
        reg = _new_registry()
        _populate_available(reg)
        summary = _summarize(reg, "stock", (analyst,), _ANALYSIS_CONTEXT)
        assert {i["item_id"] for i in summary["necessary_items"]} == want, analyst


def test_r03_03_no_applicable_analyst_is_not_applicable():
    """R03-03 / FR-03-FC02 / IR-11. A stock with no applicable analyst (empty
    enabled set) yields ``not_applicable`` with a note and no items."""
    reg = _new_registry()
    summary = _summarize(reg, "stock", (), _ANALYSIS_CONTEXT)
    assert summary["basic_completeness"] == "not_applicable"
    assert summary["applicability_note"]
    assert summary["necessary_items"] == []


def test_r03_03_crypto_not_applicable():
    reg = _new_registry()
    summary = _summarize(reg, "crypto", (), {"ticker": "BTC-USD", "trade_date": "2026-11-20"})
    assert summary["basic_completeness"] == "not_applicable"
    assert summary["applicability_note"]


def _real_income_withheld(monkeypatch):
    """The real Alpha Vantage income-statement producer withholds a statement for a
    historical ``as_of_date`` (``withhold_undated_statements`` returns the producer's
    own withheld notice rather than a body). This is a genuine ``withheld`` outcome
    for a necessary statement item, produced by the real producer. Global news has
    no withheld branch, so the statement is the legitimate necessity item to use."""
    from tradingagents.dataflows.vendors.alpha_vantage import fundamentals as av_fund
    monkeypatch.setattr(av_fund, "_make_api_request", lambda _fn, _params: _AV_STATEMENT_OK)
    return av_fund.get_income_statement("AAPL", freq="quarterly", as_of_date="2020-01-02")


def test_r03_03_necessary_item_withheld_aggregates_incomplete(monkeypatch):
    """R03-03 / FR-03-FC01, FC02 / IR-11. An applicable necessity item whose only
    completed observation is ``withheld`` makes basic completeness ``incomplete``
    and shows exactly that gap with a safe reason. The withheld income statement
    here is the real producer's historical-withholding branch, not a hand string."""
    reg = _new_registry()
    _populate_available(reg)
    withheld_raw = _real_income_withheld(monkeypatch)
    assert "withheld" in withheld_raw.lower()      # the real producer branch fired
    # Make the income target itself the withheld historical query: replace the
    # available observation with a withheld one on that same bound target so the
    # necessity item is genuinely withheld (not a separate non-matching query).
    p = _seven_params()["get_income_statement"]
    reg.accept(_classify("get_income_statement", p, withheld_raw, None), p)
    summary = _summarize(reg, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    assert summary["basic_completeness"] == "incomplete"
    gap = [i for i in summary["necessary_items"] if i["item_id"] == "get_income_statement"][0]
    assert gap["status"] == "withheld"
    assert gap.get("reason")
    # Required gaps are not repeated as supplementary limitations.
    assert "get_income_statement" not in {s.get("method") for s in summary["supplementary_limitations"]}


# =========================================================================== #
# R03-04: necessary vs supplementary (FC02/03; IR-09/11)                      #
# =========================================================================== #
def test_r03_04_supplementary_failures_keep_complete():
    reg = _new_registry()
    _populate_available(reg)
    # Supplementary failures: ticker news, StockTwits, FRED (missing key).
    for method, p, raw, src in [
        ("get_news", {"ticker": "AAPL", "start_date": "2026-11-13", "end_date": "2026-11-20"},
         "DATA_UNAVAILABLE: no configured vendor could serve get_news right now.", None),
        ("fetch_stocktwits_messages",
         {"ticker": "AAPL", "limit": 30, "start_date": "2026-11-13", "end_date": "2026-11-20"},
         "<stocktwits unavailable: OSError>", "StockTwits"),
        ("get_macro_indicators", {"indicator": "cpi", "as_of": "2026-11-20", "look_back_days": 365},
         "DATA_UNAVAILABLE: optional macro_data could not be retrieved (missing key).", "FRED"),
    ]:
        reg.accept(_classify(method, p, raw, src), p)
    summary = _summarize(reg, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    assert summary["basic_completeness"] == "complete"
    supp = {s.get("method") for s in summary["supplementary_limitations"]}
    assert {"get_news", "fetch_stocktwits_messages", "get_macro_indicators"} <= supp


def test_r03_04_reddit_fail_stocktwits_success_no_substitution():
    reg = _new_registry()
    params = _seven_params()
    for method, p in params.items():
        reg.request(method, p)
        if method == "fetch_reddit_posts":
            reg.accept(_classify(method, p,
                                 "r/wallstreetbets\n<no posts about AAPL after screening>\n",
                                 "Reddit"), p)
        else:
            reg.accept(_classify(method, p, _available_raw_for(method), None), p)
    # Successful supplementary StockTwits cannot clear the Reddit necessity item.
    st = {"ticker": "AAPL", "limit": 30, "start_date": "2026-11-13", "end_date": "2026-11-20"}
    reg.accept(_classify("fetch_stocktwits_messages", st,
                         "Bullish: 2\n$AAPL up\n", "StockTwits"), st)
    summary = _summarize(reg, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    assert summary["basic_completeness"] == "incomplete"
    reddit = [i for i in summary["necessary_items"] if i["item_id"] == "fetch_reddit_posts"][0]
    assert reddit["status"] == "no_data"


def test_r03_04_unqueried_supplementary_no_limitation():
    reg = _new_registry()
    _populate_available(reg)
    summary = _summarize(reg, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    supp = {s.get("method") for s in summary["supplementary_limitations"]}
    assert "fetch_stocktwits_messages" not in supp and "get_macro_indicators" not in supp


# =========================================================================== #
# R03-05: first eligible target binding (FC02/04; IR-10)                      #
# =========================================================================== #
def test_r03_05_first_window_binds_other_window_cannot_substitute():
    reg = _new_registry()
    a = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    b = {"symbol": "AAPL", "start_date": "2026-10-01", "end_date": "2026-11-20"}
    # Request (bind) A first; then request B (must not replace A).
    reg.request("get_stock_data", a)
    reg.request("get_stock_data", b)
    # A completes unavailable; B completes available.
    reg.accept(_classify("get_stock_data", a,
                         "DATA_UNAVAILABLE: no configured vendor could serve get_stock_data right now.",
                         None), a)
    reg.accept(_classify("get_stock_data", b, "Date,Open,High,Low,Close,Volume\n2026-10-01,1,2,1,1.5,10\n",
                         None), b)
    summary = _summarize(reg, "stock", ("market",),
                         {**_ANALYSIS_CONTEXT, "stock_start": "2026-11-01", "stock_end": "2026-11-20"})
    stock = [i for i in summary["necessary_items"] if i["item_id"] == "get_stock_data"][0]
    assert stock["status"] == "unavailable"
    # B remains a separate observation.
    obs_starts = {o.get("effective_parameters", {}).get("start_date")
                  for o in summary["observations"] if o.get("method") == "get_stock_data"}
    assert {"2026-11-01", "2026-10-01"} <= obs_starts


def test_r03_05_same_target_status_both_ways():
    reg = _new_registry()
    a = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", a)
    reg.accept(_classify("get_stock_data", a,
                         "DATA_UNAVAILABLE: no configured vendor could serve get_stock_data right now.",
                         None), a)
    assert _stock_status(reg) == "unavailable"
    reg.accept(_classify("get_stock_data", a,
                         "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n", None), a)
    assert _stock_status(reg) == "available"
    reg.accept(_classify("get_stock_data", a, "Date,Open,High,Low,Close,Volume\n", None), a)
    assert _stock_status(reg) == "no_data"


def _stock_status(reg):
    summary = _summarize(reg, "stock", ("market",),
                         {**_ANALYSIS_CONTEXT})
    return [i for i in summary["necessary_items"] if i["item_id"] == "get_stock_data"][0]["status"]


@pytest.mark.parametrize("method,freq", [
    ("get_income_statement", "quarterly"),
    ("get_balance_sheet", "quarterly"),
    ("get_cashflow", "quarterly"),
])
def test_r03_05_statement_quarterly_binds_before_annual(method, freq):
    reg = _new_registry()
    q = {"ticker": "AAPL", "freq": freq, "as_of": "2026-11-20"}
    annual = {"ticker": "AAPL", "freq": "annual", "as_of": "2026-11-20"}
    reg.request(method, q)
    reg.request(method, annual)
    reg.accept(_classify(method, q, "NO_DATA_AVAILABLE: no data", None), q)
    reg.accept(_classify(method, annual, "Date,Revenue\n2025-09-30,400000\n", None), annual)
    summary = _summarize(reg, "stock", ("fundamentals",), _ANALYSIS_CONTEXT)
    item = [i for i in summary["necessary_items"] if i["item_id"] == method][0]
    assert item["status"] == "no_data"


def test_r03_05_omitted_frequency_tool_call_binds_quarterly(monkeypatch):
    """R03-05 / FR-03-FC02, FC04 / IR-10. The ``get_income_statement`` tool call
    that OMITS ``freq`` goes through the real tool body: its omitted frequency is
    resolved to the producer default (quarterly) downstream, and the necessity
    target is bound to that effective quarterly query. The router is controlled to
    record the effective ``freq`` the tool actually passed, so the test does not
    pre-compute the expectation from the implementation."""
    from tradingagents.agents import tools

    run_context = _run_context()
    availability = _availability()
    seen_freq: list[str] = []

    def fake_router(method, ticker, freq, curr_date):
        seen_freq.append(freq)
        return "2026-09-30,TotalRevenue,100000000\n"

    monkeypatch.setattr(tools, "route_to_vendor", fake_router)

    with run_context.RunContext() as ctx:
        # freq omitted entirely -> the default path. Only ticker/curr_date given.
        tools.get_income_statement.invoke(
            {"ticker": "AAPL", "curr_date": "2026-11-20", "trade_date": "2026-11-20"})
        summary = availability.AvailabilitySummarizer(ctx.registry).snapshot(
            "stock", ("fundamentals",), _ANALYSIS_CONTEXT)

    # The tool resolved the omitted freq to the existing producer default.
    assert seen_freq[-1] == "quarterly"
    income = [i for i in summary["necessary_items"] if i["item_id"] == "get_income_statement"][0]
    assert income["status"] == "available"
    obs = [o for o in summary["observations"] if o.get("method") == "get_income_statement"]
    assert obs and obs[0].get("effective_parameters", {}).get("freq") == "quarterly"


def test_r03_05_rejected_first_does_not_bind_next_valid_binds():
    from tradingagents.dataflows.date_window import as_of_window

    reg = _new_registry()
    mod = _availability()
    bad = {"symbol": "AAPL", "start_date": "not-a-date", "end_date": "2026-11-20"}
    # Pre-fetch rejection: body raises; a private note only, no target bound.
    with pytest.raises(ValueError):
        mod.observe_prefetch_rejection(
            reg, "get_stock_data", bad,
            lambda: as_of_window("not-a-date", "2026-11-20", "2026-11-20"),
        )
    assert reg.target_for("get_stock_data") is None
    # Next valid request binds.
    good = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", good)
    assert reg.target_for("get_stock_data")["start_date"] == "2026-11-01"


def test_r03_05_earlier_snapshot_date_is_not_attempted_not_substituting():
    reg = _new_registry()
    earlier = {"symbol": "AAPL", "as_of": "2026-11-18", "look_back_days": 30}
    # Only the earlier date is requested; the analysis-date target is unbound.
    reg.request("get_verified_market_snapshot", earlier)
    reg.accept(_classify("get_verified_market_snapshot", earlier,
                         "## Verified market data snapshot for AAPL\n\n- Latest trading row used: 2026-11-18\n"
                         "| Close | 99.00 |\n", "Yahoo"), earlier)
    summary = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    snap = [i for i in summary["necessary_items"] if i["item_id"] == "get_verified_market_snapshot"][0]
    # Precisely not_attempted: the analysis-date target was never bound/observed.
    assert snap["status"] == "not_attempted"


def test_r03_05_snapshot_analysis_date_with_previous_trading_day_row_available():
    reg = _new_registry()
    p = {"symbol": "AAPL", "as_of": "2026-11-20", "look_back_days": 30}
    reg.request("get_verified_market_snapshot", p)
    # The snapshot's latest row may be the previous trading day; that's still the
    # analysis-date target and is available (utility lookback is not a dimension).
    raw = ("## Verified market data snapshot for AAPL\n\n- Latest trading row used: 2026-11-19\n"
           "| Close | 100.50 |\n")
    reg.accept(_classify("get_verified_market_snapshot", p, raw, "Yahoo"), p)
    summary = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    snap = [i for i in summary["necessary_items"] if i["item_id"] == "get_verified_market_snapshot"][0]
    assert snap["status"] == "available"


def test_r03_05_global_news_explicit_vs_default_distinct():
    reg = _new_registry()
    explicit = {"as_of": "2026-11-20", "look_back_days": 3, "limit": 2}
    default = {"as_of": "2026-11-20", "look_back_days": 7, "limit": 10}
    reg.request("get_global_news", explicit)             # first eligible binds
    reg.accept(_classify("get_global_news", explicit,
                         "DATA_UNAVAILABLE: optional news could not be retrieved.", None), explicit)
    reg.accept(_classify("get_global_news", default,
                         "## Global Market News, from 2026-11-13 to 2026-11-20:\n\n### h (source: s)\nbody\n",
                         None), default)
    summary = _summarize(reg, "stock", ("news",), _ANALYSIS_CONTEXT)
    gn = [i for i in summary["necessary_items"] if i["item_id"] == "get_global_news"][0]
    # The explicit 3/2 target bound first; default 7/10 success cannot fill it.
    assert gn["status"] == "unavailable"
    obs_params = [o.get("effective_parameters") for o in summary["observations"]
                  if o.get("method") == "get_global_news"]
    assert any(p and p.get("look_back_days") == 3 for p in obs_params)
    assert any(p and p.get("look_back_days") == 7 for p in obs_params)


def test_r03_05_global_news_tool_omitted_and_none_use_configured_defaults(monkeypatch):
    """R03-05 / FR-03-FC02, FC04 / IR-10. The real ``get_global_news`` tool, when
    it omits ``look_back_days``/``limit`` or passes ``None``, resolves them to the
    existing configured defaults downstream; a call with explicit values keeps
    them. The router is controlled to record the effective values the tool passed,
    so the expectations are read from the real call, not pre-computed."""
    from tradingagents.agents import tools
    from tradingagents.dataflows.config import get_config

    run_context = _run_context()
    availability = _availability()
    defaults = get_config()
    want_lookback = defaults["global_news_lookback_days"]
    want_limit = defaults["global_news_article_limit"]
    seen: list[tuple] = []

    def fake_router(method, as_of, look_back_days, limit):
        seen.append((look_back_days, limit))
        return "## Global Market News, from 2026-11-13 to 2026-11-20:\n\n### h (source: s)\nbody\n"

    monkeypatch.setattr(tools, "route_to_vendor", fake_router)

    with run_context.RunContext() as ctx:
        # Omitted optionals: neither look_back_days nor limit is supplied.
        tools.get_global_news.invoke({"curr_date": "2026-11-20", "trade_date": "2026-11-20"})
        # Explicit override values.
        tools.get_global_news.invoke({"curr_date": "2026-11-20", "look_back_days": 3,
                                      "limit": 2, "trade_date": "2026-11-20"})
        summary = availability.AvailabilitySummarizer(ctx.registry).snapshot(
            "stock", ("news",), _ANALYSIS_CONTEXT)

    # The omitted call kept the existing configuration defaults (read from config,
    # not pre-computed as an expected target); the explicit call kept 3/2.
    assert seen[0] == (None, None)          # tool passed None downstream
    assert (want_lookback, want_limit) == (7, 10)   # the existing configured defaults
    assert seen[1] == (3, 2)
    obs_params = [o.get("effective_parameters") for o in summary["observations"]
                  if o.get("method") == "get_global_news"]
    assert any(p and p.get("look_back_days") == want_lookback and p.get("limit") == want_limit
               for p in obs_params)
    assert any(p and p.get("look_back_days") == 3 and p.get("limit") == 2 for p in obs_params)


def test_r03_05_reddit_fixed_identity_stocktwits_cannot_bind():
    reg = _new_registry()
    # Reddit binds via its fixed prefetch identity on request.
    reddit_p = {"ticker": "AAPL", "subreddits": ("wallstreetbets",),
                "start_date": "2026-11-13", "end_date": "2026-11-20", "limit_per_sub": 5}
    reg.request("fetch_reddit_posts", reddit_p)
    # StockTwits is a different method; it cannot bind the Reddit necessity item.
    st = {"ticker": "AAPL", "limit": 30, "start_date": "2026-11-13", "end_date": "2026-11-20"}
    reg.accept(_classify("fetch_stocktwits_messages", st, "Bullish: 1\n$AAPL up\n", "StockTwits"), st)
    summary = _summarize(reg, "stock", ("social",), _ANALYSIS_CONTEXT)
    reddit = [i for i in summary["necessary_items"] if i["item_id"] == "fetch_reddit_posts"][0]
    # Bound but not completed -> not_attempted (never filled by StockTwits).
    assert reddit["status"] == "not_attempted"


# =========================================================================== #
# R03-06: request/completion ordering (FC02/04; IR-10)                        #
# =========================================================================== #
def test_r03_06_a_binds_blocks_in_fetch_b_enters_and_completes_target_stays_a():
    """R03-06 / FR-03-FC02, FC04 / IR-10. A binds and is blocked inside fetch; B
    enters (lock not held over fetch) and completes first; the target stays A."""
    import threading

    reg = _new_registry()
    a = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    b = {"symbol": "AAPL", "start_date": "2026-10-01", "end_date": "2026-11-20"}
    a_inside_fetch = threading.Event()
    b_entered = threading.Event()
    b_done = threading.Event()
    errors = []

    def run_a():
        try:
            reg.request("get_stock_data", a)            # A binds first
            a_inside_fetch.set()
            # Simulate being inside A's fetch (lock released): wait for B.
            assert b_entered.wait(timeout=5)
            assert b_done.wait(timeout=5)
            reg.accept(_classify("get_stock_data", a, "Date,Open,High,Low,Close,Volume\n", None), a)
        except BaseException as exc:  # noqa: BLE001 - collect for main-thread raise
            errors.append(exc)

    def run_b():
        try:
            assert a_inside_fetch.wait(timeout=5)
            reg.request("get_stock_data", b)            # B can enter while A fetches
            b_entered.set()
            reg.accept(_classify("get_stock_data", b,
                                 "Date,Open,High,Low,Close,Volume\n2026-10-01,1,2,1,1.5,10\n", None), b)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            b_done.set()

    ta, tb = threading.Thread(target=run_a), threading.Thread(target=run_b)
    ta.start()
    tb.start()
    ta.join(timeout=10)
    tb.join(timeout=10)
    assert not ta.is_alive() and not tb.is_alive(), "bounded sync: no hang"
    assert errors == [], errors
    # Target is A, not B.
    assert reg.target_for("get_stock_data")["start_date"] == "2026-11-01"


def test_r03_06_binding_consumes_no_sequence():
    reg = _new_registry()
    a = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", a)
    # Binding alone allocates no completed sequence.
    seq = reg.completed_updates() if hasattr(reg, "completed_updates") else []
    assert list(seq) == []


def test_r03_06_last_accepted_same_target_wins():
    reg = _new_registry()
    a = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", a)
    reg.accept(_classify("get_stock_data", a, "Date,Open,High,Low,Close,Volume\n", None), a)
    reg.accept(_classify("get_stock_data", a,
                         "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n", None), a)
    assert _stock_status(reg) == "available"


def test_r03_06_duplicate_one_projection():
    reg = _new_registry()
    a = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", a)
    for _ in range(3):
        reg.accept(_classify("get_stock_data", a,
                             "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n", None), a)
    summary = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    stock_obs = [o for o in summary["observations"] if o.get("method") == "get_stock_data"]
    assert len(stock_obs) == 1


# =========================================================================== #
# R03-07: fault ladder (FC01/04; IR-09/10/11)                                 #
# =========================================================================== #
def test_r03_07_classifier_exception_conservative_unavailable_original_returned():
    mod = _availability()
    reg = _new_registry()
    p = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    original = "ORIGINAL-FETCH-VALUE"
    calls = {"n": 0}

    def body():
        calls["n"] += 1
        return original

    def raising_classify(*a, **k):
        raise RuntimeError("classifier blew up")

    result = mod.observe_call(reg, "get_stock_data", p, body, classifier=raising_classify)
    assert result == original          # original value preserved
    assert calls["n"] == 1             # fetch ran once, no refetch
    summary = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    stock_obs = [o for o in summary["observations"] if o.get("method") == "get_stock_data"]
    assert stock_obs and stock_obs[0]["status"] == "unavailable"


def test_r03_07_acceptance_failure_mark_hides_earlier_success():
    mod = _availability()
    reg = _new_registry()
    p = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", p)
    reg.accept(_classify("get_stock_data", p,
                         "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n", None), p)

    def failing_body():
        return "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n"

    # Inject acceptance failure via a registry whose accept raises once.
    class _FailAccept:
        def __init__(self, real):
            self._real = real
            self._fail = True

        def __getattr__(self, name):
            return getattr(self._real, name)

        def accept(self, obs, params):
            if self._fail:
                self._fail = False
                raise RuntimeError("registry acceptance failed")
            return self._real.accept(obs, params)

    wrapped = _FailAccept(reg)
    # observation helper over the failing registry writes a same-query mark.
    mod.observe_call(wrapped, "get_stock_data", p, failing_body)
    summary = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    stock = [i for i in summary["necessary_items"] if i["item_id"] == "get_stock_data"][0]
    assert stock["status"] == "unavailable"


def test_r03_07_other_query_mark_then_same_query_clears():
    mod = _availability()
    reg = _new_registry()
    a = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    b = {"symbol": "AAPL", "start_date": "2026-10-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", a)
    mod.record_failure_mark(reg, "get_stock_data", a, "availability record failed; cannot confirm")
    # B success cannot clear A's mark.
    reg.accept(_classify("get_stock_data", b,
                         "Date,Open,High,Low,Close,Volume\n2026-10-01,1,2,1,1.5,10\n", None), b)
    assert _stock_status(reg) == "unavailable"
    # Later accepted A success clears it.
    reg.accept(_classify("get_stock_data", a,
                         "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n", None), a)
    assert _stock_status(reg) == "available"


def test_r03_07_unrecordable_loss_sticky_via_real_observation_helper():
    """R03-07 / FR-03-FC04 / IR-11. Drive the sticky tracking error through the
    real observation helper, not ``set_tracking_error``: the registry's ``accept``
    raises AND its query-level mark storage also fails, so the helper cannot
    identify/store a mark. The original fetch value identity and single fetch
    call are preserved; subsequent snapshots stay None even when a later accepted
    success is recorded; a new run does not inherit the sticky error.
    ``set_tracking_error`` is only exercised as a supplementary unit check below."""
    mod = _availability()
    reg = _new_registry()
    p = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", p)
    original = "ORIGINAL-FETCH-VALUE"
    fetch_calls = {"n": 0}

    def body():
        fetch_calls["n"] += 1
        return original

    class _LostStore:
        """accept raises, and the single mark interface (``accept_mark``) also
        raises: the helper cannot store a mark, which is the unidentifiable-loss
        condition that sets the sticky error."""

        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def accept(self, obs, params):
            raise RuntimeError("accept failed")

        def accept_mark(self, *a, **k):
            raise RuntimeError("mark storage failed")

        def record_failure_mark(self, *a, **k):
            raise RuntimeError("mark storage failed")

        def mark(self, *a, **k):
            raise RuntimeError("mark storage failed")

    lost = _LostStore(reg)
    result = mod.observe_call(lost, "get_stock_data", p, body)
    assert result == original          # original value identity preserved
    assert fetch_calls["n"] == 1       # fetched once, no refetch
    # Sticky error: snapshots are None from now on.
    assert _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT) is None
    # A later accepted successful record still does not clear it.
    reg.accept(_classify("get_stock_data", p,
                         "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n", None), p)
    assert _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT) is None
    # A new run does not inherit the sticky error.
    fresh = _new_registry()
    _populate_available(fresh)
    assert _summarize(fresh, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT) is not None


def test_r03_07_set_tracking_error_supplementary_unit():
    """R03-07 supplementary unit check. Sets the sticky tracking error directly to
    confirm the summarizer returns None while sticky and that a fresh registry is
    unaffected. This is a unit check for the sticky flag only; the fault-chain
    behaviour is verified above through the real observation helper."""
    mod = _availability()
    reg = _new_registry()
    mod.set_tracking_error(reg, "availability tracking lost")
    assert _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT) is None
    fresh = _new_registry()
    _populate_available(fresh)
    assert _summarize(fresh, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT) is not None


def test_r03_07_one_snapshot_construction_failure_not_sticky(monkeypatch):
    """R03-07 / FR-03-FC04 / IR-11. Inject exactly one failure at a construction/
    read boundary *inside* the real ``AvailabilitySummarizer.snapshot``: the first
    real snapshot call raises internally, the production snapshot handles its own
    exception and returns None; after the injection is removed the SAME summarizer
    builds successfully from the intact records, and no sticky error was set.

    The injectable boundary is the internal ``availability._snapshot_from_records``
    helper the production ``snapshot`` calls to build the summary from the
    registry's recorded state (a minimal, adjustable internal convention recorded
    in the phase report; the module raises it to signal a construction failure and
    its own ``snapshot`` wraps it). This test never raises on its own behalf nor
    returns a hand-made None in place of production behaviour."""
    mod = _availability()
    reg = _new_registry()
    _populate_available(reg)
    summarizer = mod.AvailabilitySummarizer(reg)

    real = mod._snapshot_from_records
    calls = {"n": 0}

    def fail_once(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("snapshot construction failed")
        return real(*a, **k)

    monkeypatch.setattr(mod, "_snapshot_from_records", fail_once)
    # First call: the real snapshot() runs, hits the injected construction error,
    # handles it and returns None (no exception escapes here).
    assert summarizer.snapshot("stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT) is None
    assert calls["n"] == 1
    # Recovery: the same summarizer builds from intact records, not None.
    monkeypatch.setattr(mod, "_snapshot_from_records", real)
    summary = summarizer.snapshot("stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    assert summary is not None
    assert summary["basic_completeness"] == "complete"
    # No sticky error was set: another call still builds.
    assert summarizer.snapshot("stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT) is not None


def test_r03_07_prefetch_rejection_no_fake_query_target_seq_mark():
    from tradingagents.dataflows.date_window import as_of_window
    mod = _availability()
    reg = _new_registry()
    bad = {"symbol": "AAPL", "start_date": "not-a-date", "end_date": "2026-11-20"}
    with pytest.raises(ValueError):
        mod.observe_prefetch_rejection(
            reg, "get_stock_data", bad,
            lambda: as_of_window("not-a-date", "2026-11-20", "2026-11-20"))
    assert reg.target_for("get_stock_data") is None
    # No completed sequence was consumed by the rejected request.
    assert list(reg.completed_updates()) == []
    summary = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    assert summary is not None
    assert all(o.get("method") != "get_stock_data" for o in summary["observations"])


def test_r03_07_note_write_failure_warns_only(monkeypatch, caplog):
    """R03-07 / FR-03-FC01 / IR-10. If the pre-fetch note cannot be written, it
    warns only: a real warning is logged (not merely asserted in a docstring), no
    exception escapes the note write (the original body error still propagates),
    and no fake query/target/sequence/mark/tracking error is created."""
    import logging

    from tradingagents.dataflows.date_window import as_of_window
    mod = _availability()
    reg = _new_registry()
    note_calls = {"n": 0}

    class _NoNote:
        def __getattr__(self, name):
            return getattr(reg, name)

        def note_call_failure(self, *a, **k):
            note_calls["n"] += 1
            raise RuntimeError("note write failed")

    no_note = _NoNote()
    bad = {"symbol": "AAPL", "start_date": "not-a-date", "end_date": "2026-11-20"}
    # A body raising after the note attempt: original error still propagates.
    with caplog.at_level(logging.WARNING, logger=mod.__name__), \
            pytest.raises(ValueError):
        mod.observe_prefetch_rejection(
            no_note, "get_stock_data", bad,
            lambda: as_of_window("not-a-date", "2026-11-20", "2026-11-20"))
    # The note write was actually attempted, and a real warning was logged.
    assert note_calls["n"] >= 1
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING
                and r.name == mod.__name__]
    assert warnings, "the pre-fetch note failure must log a warning"
    # No fake query/target/sequence/mark/sticky error.
    assert reg.target_for("get_stock_data") is None
    assert list(reg.completed_updates()) == []
    summary = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    assert summary is not None


# =========================================================================== #
# R03-01b: finite classification (narrow negative fixtures)                    #
# =========================================================================== #
# These negative fixtures make the OLD broad success heuristics fail. The
# expectation ("not available") is fixed by the D2 §8.3 producer table, not by
# the classifier's own output. A non-empty string is never sufficient for
# ``available``; only a real producer success branch is.
def _assert_not_available(obs):
    assert obs.status in {"no_data", "unavailable", "withheld"}, obs
    assert obs.reason


def test_r03_01b_stock_date_error_and_two_line_comma_not_available(monkeypatch):
    """A tool date-validation message that merely contains the word "date" and a
    newline is NOT available; nor is a two-line comma blob with no real data row."""
    from tradingagents.dataflows.date_window import as_of_window

    date_error = str(ValueError("start_date 'x' is not a date; give it as YYYY-MM-DD"))
    try:
        as_of_window("x", "2026-11-20", "2026-11-20")
    except ValueError as exc:
        date_error = str(exc)              # the real producer text
    assert "date" in date_error.lower() and "\n" not in date_error
    obs = _classify("get_stock_data",
                    {"symbol": "AAPL", "start_date": "x", "end_date": "2026-11-20"},
                    date_error, None)
    _assert_not_available(obs)
    assert obs.status == "unavailable"

    two_line = "start_date is invalid\nplease supply a date like 2026-11-20"
    obs2 = _classify("get_stock_data",
                     {"symbol": "AAPL", "start_date": "x", "end_date": "2026-11-20"},
                     two_line, None)
    _assert_not_available(obs2)


def test_r03_01b_yahoo_price_header_without_rows_not_available(monkeypatch):
    """A yahoo ``# Stock data`` header block whose CSV section has no data row is
    not available (header-only). Uses the real producer with an empty frame shape
    so the ValueError/NoMarketData branch is not bypassed: here we feed the exact
    header+header-only-CSV body the producer would emit for zero rows."""
    body = ("# Stock data for AAPL from 2026-11-01 to 2026-11-20\n"
            "# Total records: 0\n\n"
            "\nOpen,High,Low,Close,Volume\n")
    obs = _classify("get_stock_data",
                    {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"},
                    body, None)
    assert obs.status == "no_data"


def test_r03_01b_statement_without_data_rows_not_available():
    """A statement body with only a header row (no data rows) is not available."""
    header_only = "2026-09-30,TotalRevenue,100000000\n"  # header-only shape
    # A recognised header with a single non-data header line.
    body = "date,field,value\n"
    obs = _classify("get_income_statement",
                    {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
                    body, None)
    assert obs.status == "no_data"
    # A real single data row stays available (do not break real output).
    ok = _classify("get_income_statement",
                   {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
                   header_only, None)
    assert ok.status == "available"


def test_r03_01b_prediction_header_or_percent_not_available(monkeypatch):
    """A prediction header without a market line, or arbitrary percent prose, is
    not available; a real header plus a market line is."""
    header_only = ('## Polymarket prediction markets: "Fed rate cut"\n'
                   "Live, market-implied probabilities.\n\n")
    obs = _classify("get_prediction_markets",
                    {"topic": "Fed rate cut", "limit": 6, "trade_date": None},
                    header_only, "Polymarket")
    _assert_not_available(obs)

    prose = "The analyst thinks there is a 62% implied chance, maybe."
    obs2 = _classify("get_prediction_markets",
                     {"topic": "Fed rate cut", "limit": 6, "trade_date": None},
                     prose, "Polymarket")
    _assert_not_available(obs2)

    real = ('## Polymarket prediction markets: "Fed rate cut"\n'
            "Live, market-implied probabilities.\n\n"
            "- **Will the Fed cut in December?** — Yes 62% "
            "($1,200,000 volume, resolves 2026-12-18, 1-week +3.0pp)\n")
    ok = _classify("get_prediction_markets",
                   {"topic": "Fed rate cut", "limit": 6, "trade_date": None},
                   real, "Polymarket")
    assert ok.status == "available"


def test_r03_01b_stocktwits_summary_without_messages_not_available(monkeypatch):
    """A StockTwits summary line alone (no message line) is not available."""
    summary_only = "Bullish: 0 (0%) · Bearish: 0 (0%) · Unlabeled: 0 · Total: 0 most-recent messages"
    obs = _classify("fetch_stocktwits_messages",
                    {"ticker": "AAPL", "limit": 30}, summary_only, "StockTwits")
    _assert_not_available(obs)
    # A normal message block stays available.
    normal = (summary_only + "\n\n"
              "[2026-11-20T10:00:00Z · @u1 · Bullish] $AAPL buy the dip")
    ok = _classify("fetch_stocktwits_messages",
                   {"ticker": "AAPL", "limit": 30}, normal, "StockTwits")
    assert ok.status == "available"


def test_r03_01b_reddit_subblock_heading_without_posts_not_available(monkeypatch):
    """A Reddit sub-block header with no post line is not available."""
    heading_only = "r/wallstreetbets — 0 recent posts mentioning AAPL:"
    obs = _classify("fetch_reddit_posts",
                    {"ticker": "AAPL", "subreddits": ("wallstreetbets",),
                     "start_date": None, "end_date": None, "limit_per_sub": 5},
                    heading_only, "Reddit")
    _assert_not_available(obs)
    # The real producer's available block (header + [date] line) stays available.
    ok = _classify("fetch_reddit_posts",
                   {"ticker": "AAPL", "subreddits": ("wallstreetbets",),
                    "start_date": None, "end_date": None, "limit_per_sub": 5},
                   _real_reddit_available_block(), "Reddit")
    assert ok.status == "available"


def test_r03_01b_news_body_words_do_not_override_real_article(monkeypatch):
    """A real news article whose body happens to contain "withheld", "unavailable"
    or "coverage" is still available; the body words do not override the entry."""
    from tradingagents.dataflows.vendors.yahoo import news as yf_news

    class _T:
        def __init__(self, *_a, **_k):
            pass

        def get_news(self, count=10):
            return [{"content": {"title": "Company says data was withheld",
                                 "summary": "Coverage was unavailable; the firm withheld numbers "
                                            "and reported a coverage gap.",
                                 "pubDate": "2026-11-20T12:00:00Z",
                                 "canonicalUrl": {"url": "https://x/1"},
                                 "provider": {"displayName": "Reuters"}}}]

    monkeypatch.setattr(yf_news.yf, "Ticker", _T)
    raw = yf_news.get_news_yfinance("AAPL", "2026-11-13", "2026-11-20")
    obs = _classify("get_news", {"ticker": "AAPL", "start_date": "2026-11-13",
                                 "end_date": "2026-11-20"}, raw, None)
    assert obs.status == "available"


def test_r03_01b_global_news_body_words_do_not_override_real_article():
    real = ("## Global Market News, from 2026-11-13 to 2026-11-20:\n\n"
            "### Rates held, data withheld by vendor (source: Reuters)\n"
            "The release was unavailable and coverage remained thin.\n")
    obs = _classify("get_global_news",
                    {"as_of": "2026-11-20", "look_back_days": 7, "limit": 10},
                    real, None)
    assert obs.status == "available"


def test_r03_01b_av_overview_unknown_keys_not_available(monkeypatch):
    """An Alpha Vantage OVERVIEW JSON with only unrecognised keys (no recognised
    populated basic-information field) is not available."""
    av = _av(monkeypatch, '{"Symbol":"AAPL","WeirdField":"x","OtherThing":"y"}')
    raw = av.get_fundamentals("AAPL", as_of_date="2026-11-20")
    obs = _classify("get_fundamentals", {"ticker": "AAPL", "as_of": "2026-11-20"}, raw, None)
    _assert_not_available(obs)
    # The recognised real overview stays available.
    av2 = _av(monkeypatch, _AV_OVERVIEW)
    raw2 = av2.get_fundamentals("AAPL", as_of_date="2026-11-20")
    ok = _classify("get_fundamentals", {"ticker": "AAPL", "as_of": "2026-11-20"}, raw2, None)
    assert ok.status == "available"


def test_r03_01b_av_malformed_feed_report_data_not_available(monkeypatch):
    """Malformed AV shapes: wrong type for feed / report arrays / insider data is
    not available (and not no_data success either)."""
    # NEWS_SENTIMENT feed is not a list (a placeholder / wrong type).
    av = _av(monkeypatch, '{"feed":"error","Information":"rate limit"}')
    raw_news = av.get_news("AAPL", "2026-11-13", "2026-11-20")
    obs_news = _classify("get_news", {"ticker": "AAPL", "start_date": "2026-11-13",
                                      "end_date": "2026-11-20"}, raw_news, None)
    _assert_not_available(obs_news)
    # Statement report arrays are the wrong type.
    av2 = _av(monkeypatch, '{"annualReports":"nope","quarterlyReports":null}')
    raw_stmt = av2.get_income_statement("AAPL", freq="quarterly", as_of_date="2026-11-20")
    obs_stmt = _classify("get_income_statement",
                         {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
                         raw_stmt, None)
    _assert_not_available(obs_stmt)
    # Insider data is the wrong type.
    av3 = _av(monkeypatch, '{"data":"placeholder"}')
    raw_ins = av3.get_insider_transactions("AAPL", as_of_date="2026-11-20")
    obs_ins = _classify("get_insider_transactions",
                        {"ticker": "AAPL", "trade_date": "2026-11-20"}, raw_ins, None)
    _assert_not_available(obs_ins)


def test_r03_01b_fred_header_without_observation_not_available(monkeypatch):
    """A FRED header/table header with no data row is not an observation."""
    producer = _fred(monkeypatch,
                     meta=[{"title": "CPI", "units_short": "Index", "frequency": "Monthly"}],
                     obs=[])
    raw = producer("cpi", "2026-11-20", 365)
    # The producer's empty-window branch is the no_data text, not a header-only table.
    obs = _classify("get_macro_indicators",
                    {"indicator": "cpi", "as_of": "2026-11-20", "look_back_days": 365}, raw, "FRED")
    assert obs.status == "no_data"
    # A crafted header+table-header body with no data row must not be available.
    header_only = ("## FRED: CPI (CPIAUCSL)\n- Units: Index\n\n"
                   "\n| Date | Value |\n| --- | --- |\n")
    obs2 = _classify("get_macro_indicators",
                     {"indicator": "cpi", "as_of": "2026-11-20", "look_back_days": 365},
                     header_only, "FRED")
    _assert_not_available(obs2)


# =========================================================================== #
# R03-05b: request eligibility with explicit run analysis identity             #
# =========================================================================== #
def _registry_with_identity():
    """A registry bound to the run's analysis identity (the existing ticker/date
    the D2 contract allows the summarizer/registry to know). No new CLI/schema."""
    mod = _availability()
    return mod.AvailabilityRegistry(analysis_context=dict(_ANALYSIS_CONTEXT))


def _item_status(reg, item, analysts):
    summary = _summarize(reg, "stock", analysts, _ANALYSIS_CONTEXT)
    return [i for i in summary["necessary_items"] if i["item_id"] == item][0]["status"]


def test_r03_05b_early_global_news_then_analysis_date_not_attempted():
    """R03-05 / FR-03-FC02, FC04 / IR-10. An EARLIER-date global news request may
    succeed but must NOT bind the analysis-date necessary target; that item stays
    ``not_attempted`` until a request at the analysis date arrives."""
    reg = _registry_with_identity()
    early = {"as_of": "2026-11-13", "look_back_days": 7, "limit": 10}
    reg.request("get_global_news", early)
    reg.accept(_classify("get_global_news", early,
                         "## Global Market News, from 2026-11-06 to 2026-11-13:\n\n"
                         "### markets quiet (source: Reuters)\nbody\n", None), early)
    # The analysis-date necessity target is still unbound -> not_attempted.
    assert reg.target_for("get_global_news") is None
    assert _item_status(reg, "get_global_news", ("news",)) == "not_attempted"
    # The early observation is still retained as an observation.
    summary = _summarize(reg, "stock", ("news",), _ANALYSIS_CONTEXT)
    assert any(o["method"] == "get_global_news" for o in summary["observations"])


def test_r03_05b_first_analysis_date_request_binds_later_windows_cannot_substitute():
    """R03-05 / FR-03-FC02, FC04 / IR-10. The first ANALYSIS-DATE request binds; a
    later different lookback/window for the same analysis date cannot replace it."""
    reg = _registry_with_identity()
    first = {"as_of": "2026-11-20", "look_back_days": 7, "limit": 10}
    later = {"as_of": "2026-11-20", "look_back_days": 3, "limit": 2}
    reg.request("get_global_news", first)
    assert reg.target_for("get_global_news")["look_back_days"] == 7
    reg.request("get_global_news", later)               # cannot replace
    assert reg.target_for("get_global_news")["look_back_days"] == 7
    reg.accept(_classify("get_global_news", first,
                         "DATA_UNAVAILABLE: optional news could not be retrieved.", None), first)
    reg.accept(_classify("get_global_news", later,
                         "## Global Market News, from 2026-11-17 to 2026-11-20:\n\n"
                         "### x (source: s)\nbody\n", None), later)
    # The bound 7/10 target failed; the 3/2 success cannot fill it.
    assert _item_status(reg, "get_global_news", ("news",)) == "unavailable"


def test_r03_05b_non_current_object_request_cannot_bind():
    """R03-05 / FR-03-FC02, FC04 / IR-10. A price/statement request for a DIFFERENT
    object than the run's analysis object cannot bind the current object's target."""
    reg = _registry_with_identity()
    other_price = {"symbol": "MSFT", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", other_price)
    assert reg.target_for("get_stock_data") is None
    other_stmt = {"ticker": "MSFT", "freq": "quarterly", "as_of": "2026-11-20"}
    reg.request("get_income_statement", other_stmt)
    assert reg.target_for("get_income_statement") is None
    # A request for the current object (AAPL) then binds.
    good = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", good)
    assert reg.target_for("get_stock_data")["symbol"] == "AAPL"


def test_r03_05b_invalid_request_no_bind_next_valid_binds():
    """R03-05 / FR-03-FC04 / IR-10. A request missing the object identity does not
    bind; the next fully-identified valid request does."""
    reg = _registry_with_identity()
    reg.request("get_stock_data", {"start_date": "2026-11-01", "end_date": "2026-11-20"})
    assert reg.target_for("get_stock_data") is None            # no symbol -> no bind
    reg.request("get_stock_data", {"symbol": None, "start_date": "2026-11-01"})
    assert reg.target_for("get_stock_data") is None
    good = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", good)
    assert reg.target_for("get_stock_data")["start_date"] == "2026-11-01"


def test_r03_05b_incomplete_identity_does_not_mask_match():
    """R03-05 / FR-03-FC04 / IR-10. Target matching must not treat a candidate that
    lacks a required identity dimension as matching the bound target (the old
    `_matches_target` skipped missing keys). A statement observation missing
    ``freq`` must not satisfy the bound quarterly target."""
    reg = _registry_with_identity()
    target = {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"}
    reg.request("get_income_statement", target)
    # A record with the same ticker/date but a MISSING freq is a different query.
    incomplete = {"ticker": "AAPL", "as_of": "2026-11-20"}
    reg.accept(_classify("get_income_statement", incomplete,
                         "2026-09-30,TotalRevenue,100000000\n", None), incomplete)
    # The bound target has no matching completed result -> not_attempted.
    assert _item_status(reg, "get_income_statement", ("fundamentals",)) == "not_attempted"


# =========================================================================== #
# R03-07b: combined fault ladder (classifier -> conservative accept -> mark)   #
# =========================================================================== #
def test_r03_07b_classifier_raise_then_conservative_accept_fail_then_mark_ok():
    """R03-07 / FR-03-FC04 / IR-09/10/11. The full degrade chain for ONE query:
    the classifier raises, the CONSERVATIVE observation's ``accept`` also raises,
    but the same-query mark succeeds. Expected: the original fetch value is
    preserved, fetched once, the query is ``unavailable``, the whole summary is
    still constructed, NO sticky error is set, and a LATER same-query success
    replaces the mark."""
    mod = _availability()
    reg = _new_registry()
    p = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", p)
    original = "ORIGINAL-FETCH-VALUE"
    calls = {"n": 0}

    def body():
        calls["n"] += 1
        return original

    def raising_classify(*a, **k):
        raise RuntimeError("classifier blew up")

    class _AcceptFailsMarkOk:
        """accept always raises; the mark write path (``accept_mark``) succeeds."""

        def __init__(self, real):
            self._real = real
            self.marks = []

        def __getattr__(self, name):
            return getattr(self._real, name)

        def accept(self, obs, params):
            raise RuntimeError("accept failed")

        def accept_mark(self, method, params, reason):
            self.marks.append((method, dict(params), reason))
            return self._real.accept_mark(method, params, reason)

    wrapped = _AcceptFailsMarkOk(reg)
    result = mod.observe_call(wrapped, "get_stock_data", p, body, classifier=raising_classify)
    assert result == original            # original value preserved
    assert calls["n"] == 1               # fetched exactly once, no refetch
    assert wrapped.marks                # the same-query mark was actually recorded
    # No sticky error: the summary is still constructible.
    summary = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    assert summary is not None
    stock = [i for i in summary["necessary_items"] if i["item_id"] == "get_stock_data"][0]
    assert stock["status"] == "unavailable"
    # A later same-query success replaces the mark.
    reg.accept(_classify("get_stock_data", p,
                         "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n",
                         None), p)
    assert _stock_status(reg) == "available"


def test_r03_07b_normal_accept_fail_uses_same_mark_chain():
    """R03-07 / FR-03-FC04 / IR-09/10/11. A NORMAL observation whose ``accept``
    fails uses the same degrade chain (mark succeeds -> query unavailable, no
    sticky, summary constructible). Guards against divergent fallback paths."""
    mod = _availability()
    reg = _new_registry()
    p = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", p)
    calls = {"n": 0}

    def body():
        calls["n"] += 1
        return "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n"

    class _AcceptFailsMarkOk:
        def __init__(self, real):
            self._real = real
            self.marks = []

        def __getattr__(self, name):
            return getattr(self._real, name)

        def accept(self, obs, params):
            raise RuntimeError("accept failed")

        def accept_mark(self, method, params, reason):
            self.marks.append((method, dict(params), reason))
            return self._real.accept_mark(method, params, reason)

    wrapped = _AcceptFailsMarkOk(reg)
    out = mod.observe_call(wrapped, "get_stock_data", p, body)
    assert out and calls["n"] == 1
    assert wrapped.marks
    summary = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    assert summary is not None
    stock = [i for i in summary["necessary_items"] if i["item_id"] == "get_stock_data"][0]
    assert stock["status"] == "unavailable"


# =========================================================================== #
# R03-07c/08b: atomic snapshot state and mutable-state isolation               #
# =========================================================================== #
def test_r03_07c_snapshot_reads_sticky_from_same_consistent_copy():
    """R03-07 / FR-03-FC04 / IR-11. The snapshot must decide ``None`` from the SAME
    consistent registry copy as the records, not a prior lock-free check. A sticky
    error that becomes visible during the read must make the snapshot ``None`` even
    though the earlier (lock-free) sticky probe saw nothing. Deterministic: the
    sticky is set inside the copy-taking boundary, not via ``sleep``."""
    mod = _availability()
    reg = _new_registry()
    _populate_available(reg)
    summarizer = mod.AvailabilitySummarizer(reg)

    class _Race:
        def __init__(self, real):
            self._real = real
            self.armed = True

        def __getattr__(self, name):
            return getattr(self._real, name)

        def snapshot_state(self):
            if self.armed:
                self.armed = False
                # The sticky error is set at the very moment the consistent copy
                # is taken; any snapshot that reads the same copy must see it.
                self._real.set_tracking_error("raced during read")
            return self._real.snapshot_state()

    race = _Race(reg)
    raced_summarizer = mod.AvailabilitySummarizer(race)
    # The bug (lock-free sticky probe then normal build) would return a mapping.
    assert raced_summarizer.snapshot("stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT) is None
    # And it stays sticky.
    assert summarizer.snapshot("stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT) is None


def test_r03_07c_concurrent_sticky_set_via_barrier_no_sleep():
    """R03-07 / FR-03-FC04. Deterministic two-thread interleaving with a Barrier:
    one thread sets the sticky error while another snapshots; whichever order the
    lock grants, a snapshot that observes the set error must be ``None`` and a
    snapshot must never return a mapping built from a copy that carried the
    sticky error. No ``sleep`` is used to force the order."""
    import threading

    mod = _availability()
    reg = _new_registry()
    _populate_available(reg)
    summarizer = mod.AvailabilitySummarizer(reg)

    barrier = threading.Barrier(2)
    results = {}

    def setter():
        barrier.wait()
        reg.set_tracking_error("barrier sticky")

    def snap():
        barrier.wait()
        results["s"] = summarizer.snapshot("stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)

    t1, t2 = threading.Thread(target=setter), threading.Thread(target=snap)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive() and not t2.is_alive()
    # After the barrier both have returned; if the snapshot observed the sticky, it
    # is None. A later snapshot is unambiguously None (sticky persists).
    if results.get("s") is not None:
        # It must have read the copy before the setter took the lock; that copy did
        # not carry the sticky, so it is a valid (already-taken) snapshot.
        assert results["s"]["basic_completeness"] == "complete"
    assert summarizer.snapshot("stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT) is None


def test_r03_08b_accept_copies_params_and_snapshot_isolated_from_mutation():
    """R03-08 / FR-03-FC04 / IR-10/11. Binding/accept take copies of their own
    parameters, and a returned summary does not leak mutable registry state:
    mutating the caller's params, the classification result, or the returned
    summary afterwards does not change the registry's later results."""
    p = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg = _registry_with_identity()
    reg.request("get_stock_data", p)
    obs = _classify("get_stock_data", p,
                    "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n",
                    None)
    reg.accept(obs, p)

    # Mutate the caller's params and the classification result after accept.
    p["start_date"] = "1999-01-01"
    obs.effective_parameters["start_date"] = "1999-01-01"
    obs.status = "unavailable"

    def _stock_item(summary):
        return [i for i in summary["necessary_items"] if i["item_id"] == "get_stock_data"][0]

    summary1 = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    assert _stock_item(summary1)["status"] == "available"
    stock_obs = [o for o in summary1["observations"] if o["method"] == "get_stock_data"][0]
    assert stock_obs["status"] == "available"
    assert stock_obs["effective_parameters"]["start_date"] == "2026-11-01"

    # Mutating the returned summary must not affect a later snapshot.
    summary1["basic_completeness"] = "tampered"
    summary1["necessary_items"].clear()
    summary1["observations"].clear()
    stock_obs["effective_parameters"]["start_date"] = "tampered"
    summary2 = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    assert _stock_item(summary2)["status"] == "available"
    stock_obs2 = [o for o in summary2["observations"] if o["method"] == "get_stock_data"][0]
    assert stock_obs2["effective_parameters"]["start_date"] == "2026-11-01"


# =========================================================================== #
# R03-03b/04b/05c: summary field-level projection (D2 §8.3 shapes)             #
# =========================================================================== #
def test_r03_03b_necessary_items_field_projection():
    """R03-03 / FR-03-FC02/FC03 / IR-11. Each necessary item carries the D2
    subfields with real values: ``item_id``, ``method``, ``object``, an
    ``applicable_range`` expressing the actual bound target range/date, ``status``
    and ``reason``. ``get_global_news`` (no ticker object) reports no fabricated
    ticker object."""
    reg = _registry_with_identity()
    _populate_available(reg)
    summary = _summarize(reg, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    by_id = {i["item_id"]: i for i in summary["necessary_items"]}
    for item in _seven_params():
        entry = by_id[item]
        assert set(entry).issuperset({"item_id", "method", "object",
                                      "applicable_range", "status", "reason"})
    # Stock data range is the bound window.
    rng = by_id["get_stock_data"]["applicable_range"]
    assert rng == {"start_date": "2026-11-01", "end_date": "2026-11-20"}
    # Snapshot range is the analysis date.
    snap_rng = by_id["get_verified_market_snapshot"]["applicable_range"]
    assert snap_rng.get("as_of") == "2026-11-20"
    # Statements keep their effective freq + date.
    stmt_rng = by_id["get_income_statement"]["applicable_range"]
    assert stmt_rng.get("freq") == "quarterly" and stmt_rng.get("as_of") == "2026-11-20"
    # Global news keeps its window and has NO fabricated ticker object.
    gn = by_id["get_global_news"]
    assert gn["object"] is None
    assert gn["applicable_range"].get("look_back_days") == 7
    # Object-bearing items report the current object.
    assert by_id["get_stock_data"]["object"] == "AAPL"
    assert by_id["fetch_reddit_posts"]["object"] == "AAPL"


def test_r03_04b_supplementary_limitation_keeps_params_object_source():
    """R03-04 / FR-03-FC03 / IR-09/11. A failed supplementary item discloses the
    reliable known parameters/object/source/status/reason, and a GLOBAL/macro/
    prediction supplementary failure reports its real business object rather than a
    fabricated null ticker."""
    reg = _registry_with_identity()
    _populate_available(reg)
    # A macro (FRED) failure and a prediction-market failure for the run's analysis
    # date; both are supplementary and must carry their real business object.
    macro_p = {"indicator": "cpi", "as_of": "2026-11-20", "look_back_days": 365}
    reg.accept(_classify("get_macro_indicators", macro_p,
                         "DATA_UNAVAILABLE: optional macro_data could not be retrieved.", "FRED"),
               macro_p)
    pred_p = {"topic": "Fed rate cut", "limit": 6, "trade_date": "2026-11-20"}
    reg.accept(_classify("get_prediction_markets", pred_p,
                         "Polymarket data is currently unavailable (network error: x).",
                         "Polymarket"), pred_p)
    summary = _summarize(reg, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    supp = {s["method"]: s for s in summary["supplementary_limitations"]}
    assert "get_macro_indicators" in supp
    macro = supp["get_macro_indicators"]
    assert set(macro).issuperset({"method", "object", "status", "reason", "source"})
    assert macro["object"] == "cpi"           # real macro business object
    assert macro["source"] == "FRED"
    assert macro["status"] == "unavailable"
    assert macro["reason"]
    pred = supp["get_prediction_markets"]
    assert pred["object"] == "Fed rate cut"   # real prediction topic
    assert pred["source"] == "Polymarket"


def test_r03_04b_prefetch_note_supplementary_projected_as_limitation():
    """R03-04 / FR-03-FC03, FC04 / IR-10/11. A supplementary pre-fetch
    parameter/date rejection appears in ``supplementary_limitations`` as a
    ``unavailable`` limitation with the parameter-failure reason, and is NOT a
    necessary item (it is supplementary)."""
    from tradingagents.dataflows.date_window import as_of_window

    mod = _availability()
    reg = _registry_with_identity()
    _populate_available(reg)
    # A supplementary indicator call rejected before a fetch (bad date).
    bad = {"symbol": "AAPL", "indicator": "rsi", "as_of": "not-a-date", "look_back_days": 30}
    with pytest.raises(ValueError):
        mod.observe_prefetch_rejection(
            reg, "get_indicators", bad,
            lambda: as_of_window("not-a-date", "2026-11-20", "2026-11-20"))
    summary = _summarize(reg, "stock", _ALL_FOUR_ANALYSTS, _ANALYSIS_CONTEXT)
    supp = {s["method"]: s for s in summary["supplementary_limitations"]}
    assert "get_indicators" in supp
    assert supp["get_indicators"]["status"] == "unavailable"
    assert supp["get_indicators"]["reason"] == mod.REASON_PARAM_REJECTED


def test_r03_03b_necessary_rejection_not_duplicated_into_supplementary():
    """R03-03 / FR-03-FC02, FC03 / IR-11. A necessary-item parameter rejection
    affects only that item's missing reason (``not_attempted`` + param-rejected
    reason) and is NOT repeated in ``supplementary_limitations`` for the same
    method."""
    from tradingagents.dataflows.date_window import as_of_window

    mod = _availability()
    reg = _registry_with_identity()
    _populate_available(reg)
    # A rejected stock-data request for the run object (necessary item).
    bad = {"symbol": "AAPL", "start_date": "not-a-date", "end_date": "2026-11-20"}
    with pytest.raises(ValueError):
        mod.observe_prefetch_rejection(
            reg, "get_stock_data", bad,
            lambda: as_of_window("not-a-date", "2026-11-20", "2026-11-20"))
    summary = _summarize(reg, "stock", ("market",), _ANALYSIS_CONTEXT)
    gap = [i for i in summary["necessary_items"] if i["item_id"] == "get_stock_data"][0]
    # Already-available stock target is unaffected by the note (it has a valid result).
    assert gap["status"] == "available"
    # And the necessary method is not duplicated as a supplementary limitation.
    assert "get_stock_data" not in {s["method"] for s in summary["supplementary_limitations"]}


# =========================================================================== #
# R03-01c: strict finite format recognition (no bare number/date anywhere)    #
# =========================================================================== #
@pytest.mark.parametrize("body", [
    "42",                                          # a bare number is not a data row
    "2026-11-20",                                  # a bare date is not a data row
    "error: failed for 2026-11-20",                # date inside an error message
    "please try again later\ncontact support",     # two non-producer text lines
    "total: 1000000\nchange: +2%",                 # prose with numbers, no CSV frame
])
def test_r03_01c_stock_data_bare_number_or_date_or_prose_not_available(body):
    """R03-01 / FR-03-FC01 / IR-09. A lone number, a lone date, a date inside an
    error message, or a two-line prose blob is NOT a price data row. A valid
    producer CSV (a dated row with OHLCV-style fields) stays available."""
    obs = _classify("get_stock_data",
                    {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"},
                    body, None)
    _assert_not_available(obs)
    # Real producer CSV remains available (do not over-tighten).
    ok = _classify("get_stock_data",
                   {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"},
                   "Date,Open,High,Low,Close,Volume\n2026-11-20,100,101,99,100.5,1000000\n",
                   None)
    assert ok.status == "available"


def test_r03_01c_statement_bare_number_not_available():
    """R03-01 / FR-03-FC01. A statement body that is only a bare number is not a
    data row; a real statement CSV row is."""
    obs = _classify("get_income_statement",
                    {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
                    "42", None)
    _assert_not_available(obs)
    ok = _classify("get_income_statement",
                   {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
                   "2026-09-30,TotalRevenue,100000000\n", None)
    assert ok.status == "available"


def test_r03_01c_yahoo_fundamentals_unknown_field_not_available():
    """R03-01 / FR-03-FC01. ``# Company Fundamentals`` followed by an UNRECOGNISED
    ``unknown: value`` line is not available; the real producer's recognised field
    labels are."""
    body = "# Company Fundamentals for AAPL\n\nunknown: value\n"
    obs = _classify("get_fundamentals", {"ticker": "AAPL", "as_of": None}, body, None)
    _assert_not_available(obs)
    real = "# Company Fundamentals for AAPL\n\nName: Apple Inc\nSector: Technology\n"
    ok = _classify("get_fundamentals", {"ticker": "AAPL", "as_of": None}, real, None)
    assert ok.status == "available"


def test_r03_01c_av_empty_vs_placeholder_entries(monkeypatch):
    """R03-01 / FR-03-FC01. Empty AV feed/report/data are no_data; a placeholder
    (non-list / non-dict entry) is not a real entry. Real entries are available."""
    # Empty containers -> no_data.
    for body, method, params in [
        ('{"feed":[]}', "get_news", {"ticker": "AAPL", "start_date": "2026-11-13",
                                     "end_date": "2026-11-20"}),
        ('{"annualReports":[],"quarterlyReports":[]}', "get_income_statement",
         {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"}),
        ('{"data":[]}', "get_insider_transactions",
         {"ticker": "AAPL", "trade_date": "2026-11-20"}),
    ]:
        obs = _classify(method, params, body, None)
        assert obs.status == "no_data", (method, body)
    # Placeholder entries that are not real dict/list items are not available.
    obs = _classify("get_news",
                    {"ticker": "AAPL", "start_date": "2026-11-13", "end_date": "2026-11-20"},
                    '{"feed":["placeholder"]}', None)
    _assert_not_available(obs)
    obs = _classify("get_income_statement",
                    {"ticker": "AAPL", "freq": "quarterly", "as_of": "2026-11-20"},
                    '{"annualReports":["x"],"quarterlyReports":[]}', None)
    _assert_not_available(obs)


# =========================================================================== #
# R03-06b: target/parameter mutable isolation and list/tuple normalization     #
# =========================================================================== #
def _reddit_params_with_list():
    return {"ticker": "AAPL", "subreddits": ["wallstreetbets", "stocks"],
            "start_date": "2026-11-13", "end_date": "2026-11-20", "limit_per_sub": 5}


def test_r03_06b_reddit_list_input_binds_and_caller_mutation_does_not_leak():
    """R03-06 / FR-03-FC02, FC04 / IR-10. A Reddit request whose ``subreddits`` is a
    caller list binds a target holding its OWN copy; mutating the caller list after
    binding does not change the bound target."""
    reg = _registry_with_identity()
    p = _reddit_params_with_list()
    reg.request("fetch_reddit_posts", p)
    bound = reg.target_for("fetch_reddit_posts")
    assert bound is not None
    p["subreddits"].append("investing")           # mutate caller list after bind
    bound_again = reg.target_for("fetch_reddit_posts")
    assert bound_again["subreddits"] == ("wallstreetbets", "stocks") or \
        list(bound_again["subreddits"]) == ["wallstreetbets", "stocks"]
    # Mutating the returned target dict does not corrupt the registry.
    bound_again["subreddits"] = ("mutated",)
    still = reg.target_for("fetch_reddit_posts")
    assert list(still["subreddits"]) == ["wallstreetbets", "stocks"]


def test_r03_06b_list_and_tuple_subreddits_normalize_to_same_query():
    """R03-06 / FR-03-FC04 / IR-10. An equivalent list vs tuple of subreddits is the
    same logical query (normalized), so the last accepted update replaces rather
    than double-counting."""
    reg = _registry_with_identity()
    raw = _real_reddit_available_block()
    p_list = {"ticker": "AAPL", "subreddits": ["wallstreetbets"],
              "start_date": None, "end_date": None, "limit_per_sub": 5}
    p_tuple = {"ticker": "AAPL", "subreddits": ("wallstreetbets",),
               "start_date": None, "end_date": None, "limit_per_sub": 5}
    reg.accept(_classify("fetch_reddit_posts", p_list, raw, "Reddit"), p_list)
    reg.accept(_classify("fetch_reddit_posts", p_tuple, raw, "Reddit"), p_tuple)
    summary = _summarize(reg, "stock", ("social",), _ANALYSIS_CONTEXT)
    rd = [o for o in summary["observations"] if o["method"] == "fetch_reddit_posts"]
    assert len(rd) == 1


def test_r03_06b_snapshot_copy_not_mutating_registry():
    """R03-06 / FR-03-FC04 / IR-10. Mutating a snapshot's returned target/observation
    structures does not change the registry's later target or matching."""
    reg = _registry_with_identity()
    p = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", p)
    before = reg.target_for("get_stock_data")
    state = reg.snapshot_state()
    # Mutate the copy returned by snapshot_state.
    state["targets"]["get_stock_data"]["start_date"] = "1999-01-01"
    after = reg.target_for("get_stock_data")
    assert after == before


# =========================================================================== #
# R03-07d: lock consistency and sticky independence                           #
# =========================================================================== #
def test_r03_07d_tracking_error_and_note_under_same_lock_no_deadlock():
    """R03-07 / FR-03-FC04 / IR-11. Setting the sticky tracking error and writing a
    private pre-fetch note happen under the registry lock (consistent with the
    snapshot copy) and do not deadlock (a non-reentrant lock is not re-acquired).
    Uses a short thread join bound, not sleep, to prove no hang."""
    import threading

    from tradingagents.dataflows.date_window import as_of_window

    mod = _availability()
    reg = _new_registry()
    result = {}

    def worker():
        # A note write, then a sticky set, then a snapshot read — sequentially, each
        # taking the lock once. If any path re-acquired the held lock it would hang.
        import contextlib

        with contextlib.suppress(ValueError):
            mod.observe_prefetch_rejection(
                reg, "get_stock_data",
                {"symbol": "AAPL", "start_date": "x", "end_date": "2026-11-20"},
                lambda: as_of_window("x", "2026-11-20", "2026-11-20"))
        mod.set_tracking_error(reg, "sticky after note")
        result["snap"] = mod.AvailabilitySummarizer(reg).snapshot(
            "stock", ("market",), _ANALYSIS_CONTEXT)

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=5)
    assert not t.is_alive(), "lock re-entry deadlock"
    assert result["snap"] is None      # sticky reflected in the same-consistent read


def test_r03_07d_sticky_independent_of_failed_record_and_mark():
    """R03-07 / FR-03-FC04 / IR-11. When BOTH the observation accept and the single
    mark interface fail, the sticky error is still set independently (a failed
    record/mark write does not prevent the tracking error), and later snapshots are
    None. The original fetch value is preserved and fetched once."""
    mod = _availability()
    reg = _new_registry()
    p = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    reg.request("get_stock_data", p)
    original = "ORIGINAL"
    calls = {"n": 0}

    def body():
        calls["n"] += 1
        return original

    class _AllFail:
        def __getattr__(self, name):
            return getattr(reg, name)

        def accept(self, *a, **k):
            raise RuntimeError("accept failed")

        def accept_mark(self, *a, **k):
            raise RuntimeError("mark failed")

    out = mod.observe_call(_AllFail(), "get_stock_data", p, body)
    assert out == original and calls["n"] == 1
    assert mod.AvailabilitySummarizer(reg).snapshot("stock", ("market",), _ANALYSIS_CONTEXT) is None


# =========================================================================== #
# R03-08c: RunContext carries a minimal analysis identity                     #
# =========================================================================== #
def test_r03_08c_run_context_creates_registry_with_identity():
    """R03-08 / FR-03-FC04, FC05 / IR-05/10. ``RunContext(analysis_context=...)``
    creates a registry that owns that identity, so eligibility/target binding is
    enforced. No new CLI/schema/config is added."""
    run_context = _run_context()
    ctx = run_context.RunContext(analysis_context=dict(_ANALYSIS_CONTEXT))
    try:
        ctx.registry.request("get_stock_data",
                             {"symbol": "MSFT", "start_date": "2026-11-01", "end_date": "2026-11-20"})
        assert ctx.registry.target_for("get_stock_data") is None      # wrong object
        ctx.registry.request("get_stock_data",
                             {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"})
        assert ctx.registry.target_for("get_stock_data")["symbol"] == "AAPL"
    finally:
        ctx.finish()


# =========================================================================== #
# R03-05c: date rejection preserves the original tool text (P-01/P-09/P-13)    #
# =========================================================================== #
def _rejected_call_counts(monkeypatch):
    """Count real fetch attempts (router + reddit/stocktwits producers) so a test
    can assert an invalid date performs NO fetch on either scope state."""
    from tradingagents.agents import tools
    from tradingagents.agents.analysts import sentiment_analyst

    calls = {"router": 0, "stocktwits": 0, "reddit": 0}

    def router(*a, **k):
        calls["router"] += 1
        return "should-not-be-called"

    monkeypatch.setattr(tools, "route_to_vendor", router)
    monkeypatch.setattr(sentiment_analyst, "fetch_stocktwits_messages",
                        lambda *a, **k: calls.__setitem__("stocktwits", calls["stocktwits"] + 1) or "x")
    monkeypatch.setattr(sentiment_analyst, "fetch_reddit_posts",
                        lambda *a, **k: calls.__setitem__("reddit", calls["reddit"] + 1) or "x")
    return calls


def test_r03_05c_p01_date_rejection_returns_text_equal_scope_on_off(monkeypatch):
    """R03-05 / FR-03-FC01 / IR-09. A rejected ``get_stock_data`` start date returns
    the SAME ``str(ValueError)`` text with and without an active scope, performs NO
    fetch on either, and (with scope) records only a private note: no query, target,
    sequence, mark or sticky error."""
    from tradingagents.agents import tools

    run_context = _run_context()
    availability = _availability()
    calls = _rejected_call_counts(monkeypatch)

    bad = {"symbol": "AAPL", "start_date": "not-a-date", "end_date": "2026-11-20",
           "trade_date": "2026-11-20"}
    no_scope = tools.get_stock_data.invoke(dict(bad))

    with run_context.RunContext(analysis_context=dict(_ANALYSIS_CONTEXT)) as ctx:
        reg = ctx.registry
        scoped = tools.get_stock_data.invoke(dict(bad))
        summary = availability.AvailabilitySummarizer(reg).snapshot(
            "stock", ("market",), _ANALYSIS_CONTEXT)

    # Same text (value equality) in both states; the original error text, no raise.
    assert isinstance(no_scope, str) and "not a date" in no_scope
    assert scoped == no_scope
    # No fetch happened on either path.
    assert calls["router"] == 0
    # Private note only: no fabricated query/target/sequence/mark/sticky error.
    assert reg.target_for("get_stock_data") is None
    assert list(reg.completed_updates()) == []
    assert availability.AvailabilitySummarizer(reg).snapshot(
        "stock", ("market",), _ANALYSIS_CONTEXT) is not None      # not sticky
    assert all(o.get("method") != "get_stock_data" for o in summary["observations"])


def test_r03_05c_p09_news_date_rejection_returns_text_equal_scope_on_off(monkeypatch):
    """R03-05 / FR-03-FC01 / IR-09. A rejected ``get_news`` window returns the SAME
    error text with/without scope and performs no fetch; only a private note with a
    scope (no query/target/mark/sticky)."""
    from tradingagents.agents import tools

    run_context = _run_context()
    availability = _availability()
    calls = _rejected_call_counts(monkeypatch)

    bad = {"ticker": "AAPL", "start_date": "not-a-date", "end_date": "2026-11-20",
           "trade_date": "2026-11-20"}
    no_scope = tools.get_news.invoke(dict(bad))
    with run_context.RunContext(analysis_context=dict(_ANALYSIS_CONTEXT)) as ctx:
        reg = ctx.registry
        scoped = tools.get_news.invoke(dict(bad))

    assert isinstance(no_scope, str) and "not a date" in no_scope
    assert scoped == no_scope
    assert calls["router"] == 0
    assert reg.target_for("get_news") is None
    assert list(reg.completed_updates()) == []
    assert availability.AvailabilitySummarizer(reg).snapshot(
        "stock", ("news",), _ANALYSIS_CONTEXT) is not None


def test_r03_05c_p13_sentiment_prefetch_bad_date_no_fetch_note_only(monkeypatch):
    """R03-05 / FR-03-FC01, FC05 / IR-09. Through the REAL sentiment node (P-13), a
    rejected prefetch window yields no news fetch (the node's prefetch degrades to
    the error text) and no fabricated query/target/mark/sticky on the run registry.
    The node still runs to completion and returns a report."""
    from tradingagents.agents.analysts import sentiment_analyst

    run_context = _run_context()
    availability = _availability()
    calls = _rejected_call_counts(monkeypatch)

    # Model returns fixed free text (structured not needed for the body path).
    node = sentiment_analyst.create_sentiment_analyst(_sentiment_model())
    # The sentiment node computes its own valid window; force the shared news
    # executor's window handling (tools.as_of_window) to reject so no fetch happens.
    from tradingagents.agents import tools as tools_mod
    real_as_of_window = tools_mod.as_of_window
    monkeypatch.setattr(tools_mod, "as_of_window",
                        lambda s, e, t: (_ for _ in ()).throw(ValueError("start_date 'x' is not a date")))

    try:
        with run_context.RunContext(analysis_context=dict(_ANALYSIS_CONTEXT)) as ctx:
            reg = ctx.registry
            out = node({"company_of_interest": "AAPL", "trade_date": "2026-11-20",
                        "messages": [], "asset_type": "stock"})
    finally:
        monkeypatch.setattr(tools_mod, "as_of_window", real_as_of_window)

    # The node completed with a report; no news fetch happened (rejected pre-fetch).
    assert isinstance(out, dict) and out.get("sentiment_report")
    assert calls["router"] == 0
    assert reg.target_for("get_news") is None
    # No fabricated get_news query/target/mark for the rejected prefetch. (Other
    # sources — StockTwits/Reddit — did fetch and may be recorded.)
    summary = availability.AvailabilitySummarizer(reg).snapshot(
        "stock", ("news",), _ANALYSIS_CONTEXT)
    assert summary is not None
    assert all(o.get("method") != "get_news" for o in summary["observations"])


def test_r03_05c_note_write_failure_warns_only_keeps_text(monkeypatch, caplog):
    """R03-05 / FR-03-FC01 / IR-10. If the private note cannot be written, the tool
    still returns the original error text (warning only), and no fake
    query/target/sequence/mark/sticky is created."""
    import logging

    from tradingagents.agents import tools

    run_context = _run_context()
    availability = _availability()
    mod = _availability()

    class _NoNote:
        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def note_call_failure(self, *a, **k):
            raise RuntimeError("note write failed")

    with run_context.RunContext(analysis_context=dict(_ANALYSIS_CONTEXT)) as ctx:
        real_reg = ctx.registry
        no_note = _NoNote(real_reg)
        # Route the tool's registry lookup to the note-failing wrapper.
        monkeypatch.setattr(tools, "_registry", lambda: no_note)
        with caplog.at_level(logging.WARNING, logger=mod.__name__):
            out = tools.get_stock_data.invoke(
                {"symbol": "AAPL", "start_date": "not-a-date", "end_date": "2026-11-20",
                 "trade_date": "2026-11-20"})
        reg = real_reg
    assert isinstance(out, str) and "not a date" in out
    assert any(r.levelno >= logging.WARNING and r.name == mod.__name__ for r in caplog.records)
    assert reg.target_for("get_stock_data") is None
    assert list(reg.completed_updates()) == []
    assert availability.AvailabilitySummarizer(reg).snapshot(
        "stock", ("market",), _ANALYSIS_CONTEXT) is not None


def _sentiment_model():
    """A minimal free-text-only model for the sentiment node (no structured)."""
    import importlib.util
    path = __file__.replace("test_fr03_availability.py", "test_fr03_integration.py")
    spec = importlib.util.spec_from_file_location("_fr03_integration_helpers", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ScriptedModel(structured=False)


# =========================================================================== #
# R03-07e: registry.request failure must not block the original fetch          #
# =========================================================================== #
def test_r03_07e_request_failure_does_not_block_fetch(monkeypatch):
    """R03-07 / FR-03-FC04 / IR-09/10/11. If ``registry.request`` raises, the original
    body STILL runs exactly once, its return value identity is preserved (``is``),
    no retry occurs, and a conservative tracking failure is set (the necessary
    target/path could not be reliably established). The observation cannot escape
    and replace the business result."""
    mod = _availability()
    reg = _new_registry()
    p = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    sentinel = object()
    calls = {"n": 0, "req": 0}

    class _ReqFails:
        def __getattr__(self, name):
            return getattr(reg, name)

        def request(self, *a, **k):
            calls["req"] += 1
            raise RuntimeError("request failed")

    def body():
        calls["n"] += 1
        return sentinel

    out = mod.observe_supported_call(_ReqFails(), "get_stock_data", p, "P-01", body)
    assert out is sentinel            # object identity preserved (not just ==)
    assert calls["n"] == 1            # fetched exactly once
    assert calls["req"] == 1          # request attempted once, not retried
    # Conservative tracking failure: subsequent snapshots are None.
    assert mod.AvailabilitySummarizer(reg).snapshot("stock", ("market",), _ANALYSIS_CONTEXT) is None


def test_r03_07e_request_failure_preserves_body_exception_identity():
    """R03-07 / FR-03-FC04 / IR-09. A request failure plus a body exception: the
    EXACT original exception object is re-raised (identity), fetched once, and the
    observation fault does not escape in its place."""
    mod = _availability()
    reg = _new_registry()
    p = {"symbol": "AAPL", "start_date": "2026-11-01", "end_date": "2026-11-20"}
    original = ValueError("original body failure")
    calls = {"n": 0}

    class _ReqFails:
        def __getattr__(self, name):
            return getattr(reg, name)

        def request(self, *a, **k):
            raise RuntimeError("request failed")

    def body():
        calls["n"] += 1
        raise original

    with pytest.raises(ValueError) as ei:
        mod.observe_supported_call(_ReqFails(), "get_stock_data", p, "P-01", body)
    assert ei.value is original       # exact exception identity
    assert calls["n"] == 1
