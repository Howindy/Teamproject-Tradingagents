"""The data tools the analysts call.

Each dated tool takes the run's ``trade_date`` from graph state (``InjectedState``)
and never serves data past it, whatever date the model asks for.
"""

from contextvars import ContextVar
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from tradingagents.dataflows.availability import (
    observe_supported_call,
    record_prefetch_rejection,
)
from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.date_window import as_of, as_of_window
from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError
from tradingagents.dataflows.router import no_data_available, route_to_vendor, vendor_unavailable
from tradingagents.dataflows.vendors.fred import DEFAULT_LOOKBACK_DAYS
from tradingagents.dataflows.vendors.polymarket import DEFAULT_LIMIT as DEFAULT_MARKET_LIMIT
from tradingagents.dataflows.vendors.yahoo.snapshot import build_verified_market_snapshot
from tradingagents.run_context import current as current_run

# The explicit supported-path identity for the shared news executor. The P-09 tool
# path is the default; the P-13 sentiment-prefetch caller sets it for its call via a
# context-local value (no model-visible parameter, so the public tool schema is
# unchanged). The same business query reached through both paths shares one query
# identity; both path associations are kept.
_NEWS_PATH: ContextVar[str] = ContextVar("tradingagents_news_path", default="P-09")


def _registry():
    """The active run's availability registry, or ``None`` outside a run scope."""
    ctx = current_run()
    return ctx.registry if ctx is not None else None


def _effective_global_news_defaults(look_back_days, limit):
    """Resolve the OMITTED/None global-news values from active config exactly as the
    producers do (None-only; an explicit 0 is kept). Used only for the observation's
    effective parameters; the original fetch keeps the original arguments."""
    if look_back_days is None or limit is None:
        cfg = get_config()
        if look_back_days is None:
            look_back_days = cfg["global_news_lookback_days"]
        if limit is None:
            limit = cfg["global_news_article_limit"]
    return look_back_days, limit


@tool
def get_stock_data(
    symbol: Annotated[str, InjectedState("company_of_interest")],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve stock price data (OHLCV) for the instrument under analysis.
    Uses the configured core_stock_apis vendor.
    Args:
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted dataframe containing the price data for the instrument over the date range.
    """
    try:
        start_date, end_date = as_of_window(start_date, end_date, trade_date)
    except ValueError as e:
        # Preserve the original text return; record only a private note with a scope.
        record_prefetch_rejection(
            _registry(), "get_stock_data",
            {"symbol": symbol, "start_date": start_date, "end_date": end_date})
        return str(e)
    params = {"symbol": symbol, "start_date": start_date, "end_date": end_date}
    return observe_supported_call(
        _registry(), "get_stock_data", params, "P-01",
        lambda: route_to_vendor("get_stock_data", symbol, start_date, end_date))


@tool
def get_indicators(
    symbol: Annotated[str, InjectedState("company_of_interest")],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[str, "The current trading date you are trading on, YYYY-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"] = 30,
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve a single technical indicator for the instrument under analysis.
    Uses the configured technical_indicators vendor.
    Args:
        indicator (str): A single technical indicator name, e.g. 'rsi', 'macd'. Call this tool once per indicator.
        curr_date (str): The current trading date you are trading on, YYYY-mm-dd
        look_back_days (int): How many days to look back, default is 30
    Returns:
        str: A formatted dataframe containing the technical indicators for the instrument and indicator.
    """
    # LLMs sometimes pass multiple indicators as a comma-separated string;
    # split and process each individually.
    curr_date = as_of(curr_date, trade_date)
    indicators = [i.strip().lower() for i in indicator.split(",") if i.strip()]
    reg = _registry()
    results = []
    for ind in indicators:
        params = {"symbol": symbol, "indicator": ind, "as_of": curr_date,
                  "look_back_days": look_back_days}

        def _fetch(_ind=ind):
            try:
                return route_to_vendor("get_indicators", symbol, _ind, curr_date, look_back_days)
            except ValueError as e:
                return str(e)

        # One observation per split indicator execution; the final joined string
        # is never classified once.
        results.append(observe_supported_call(reg, "get_indicators", params, "P-03", _fetch))
    return "\n\n".join(results)


@tool
def get_verified_market_snapshot(
    symbol: Annotated[str, InjectedState("company_of_interest")],
    curr_date: Annotated[str, "the current trading date, YYYY-mm-dd"],
    look_back_days: Annotated[
        int, "number of recent trading rows to include for sanity-checking"
    ] = 30,
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """Deterministic verification snapshot for exact market-data claims.

    Returns the latest OHLCV row on or before curr_date, common technical
    indicators, and recent closes. Call this before making exact claims about
    price levels, Bollinger bands, RSI, MACD, moving averages, support /
    resistance, or historical comparisons, and treat it as the source of truth.
    """
    # An exception out of a tool would end the run.
    as_of_date = as_of(curr_date, trade_date)
    params = {"symbol": symbol, "as_of": as_of_date, "look_back_days": look_back_days}

    def _build():
        try:
            return build_verified_market_snapshot(symbol, as_of_date, look_back_days)
        except VendorUnavailableError as exc:
            return vendor_unavailable("get_verified_market_snapshot", exc)
        except NoMarketDataError as exc:
            return no_data_available(exc)

    return observe_supported_call(
        _registry(), "get_verified_market_snapshot", params, "P-02", _build,
        source_hint="Yahoo")


@tool
def get_fundamentals(
    ticker: Annotated[str, InjectedState("company_of_interest")],
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve comprehensive fundamental data for the instrument under analysis.
    Uses the configured fundamental_data vendor.
    Args:
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing comprehensive fundamental data
    """
    ticker, as_of_date = ticker, as_of(curr_date, trade_date)
    params = {"ticker": ticker, "as_of": as_of_date}
    return observe_supported_call(
        _registry(), "get_fundamentals", params, "P-04",
        lambda: route_to_vendor("get_fundamentals", ticker, as_of_date))


@tool
def get_balance_sheet(
    ticker: Annotated[str, InjectedState("company_of_interest")],
    freq: Annotated[str, "reporting frequency: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"] = None,
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve balance sheet data for the instrument under analysis.
    Uses the configured fundamental_data vendor.
    Args:
        freq (str): Reporting frequency: annual/quarterly (default quarterly)
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing balance sheet data
    """
    as_of_date = as_of(curr_date, trade_date)
    params = {"ticker": ticker, "freq": freq, "as_of": as_of_date}
    return observe_supported_call(
        _registry(), "get_balance_sheet", params, "P-06",
        lambda: route_to_vendor("get_balance_sheet", ticker, freq, as_of_date))


@tool
def get_cashflow(
    ticker: Annotated[str, InjectedState("company_of_interest")],
    freq: Annotated[str, "reporting frequency: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"] = None,
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve cash flow statement data for the instrument under analysis.
    Uses the configured fundamental_data vendor.
    Args:
        freq (str): Reporting frequency: annual/quarterly (default quarterly)
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing cash flow statement data
    """
    as_of_date = as_of(curr_date, trade_date)
    params = {"ticker": ticker, "freq": freq, "as_of": as_of_date}
    return observe_supported_call(
        _registry(), "get_cashflow", params, "P-07",
        lambda: route_to_vendor("get_cashflow", ticker, freq, as_of_date))


@tool
def get_income_statement(
    ticker: Annotated[str, InjectedState("company_of_interest")],
    freq: Annotated[str, "reporting frequency: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"] = None,
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve income statement data for the instrument under analysis.
    Uses the configured fundamental_data vendor.
    Args:
        freq (str): Reporting frequency: annual/quarterly (default quarterly)
        curr_date (str): Current date you are trading at, yyyy-mm-dd
    Returns:
        str: A formatted report containing income statement data
    """
    as_of_date = as_of(curr_date, trade_date)
    params = {"ticker": ticker, "freq": freq, "as_of": as_of_date}
    return observe_supported_call(
        _registry(), "get_income_statement", params, "P-05",
        lambda: route_to_vendor("get_income_statement", ticker, freq, as_of_date))


def observe_news(ticker, start_date, end_date, trade_date, path_id):
    """Shared internal news executor used by P-09 (the get_news tool) and P-13 (the
    sentiment prefetch). It performs the existing window/date handling, forms the
    effective params, and records ONE observation associated with the explicit
    ``path_id`` (never inferred from the call stack). The original value/exception
    is preserved. FR-01 is not implemented here: the same query called twice still
    fetches twice, but both path associations are kept on one logical query."""
    try:
        eff_start, eff_end = as_of_window(start_date, end_date, trade_date)
    except ValueError as e:
        # Preserve the original text return; record only a private note with a scope.
        record_prefetch_rejection(
            _registry(), "get_news",
            {"ticker": ticker, "start_date": start_date, "end_date": end_date})
        return str(e)
    params = {"ticker": ticker, "start_date": eff_start, "end_date": eff_end}
    return observe_supported_call(
        _registry(), "get_news", params, path_id,
        lambda: route_to_vendor("get_news", ticker, eff_start, eff_end))


@tool
def get_news(
    ticker: Annotated[str, InjectedState("company_of_interest")],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve news data for the instrument under analysis.
    Uses the configured news_data vendor.
    Args:
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted string containing news data
    """
    return observe_news(ticker, start_date, end_date, trade_date, _NEWS_PATH.get())


@tool
def get_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int | None, "Days to look back; omit to use the configured default"] = None,
    limit: Annotated[int | None, "Max articles to return; omit to use the configured default"] = None,
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve global news data.
    Uses the configured news_data vendor. Defaults for look_back_days and
    limit come from DEFAULT_CONFIG (global_news_lookback_days,
    global_news_article_limit); pass explicit values to override.

    Args:
        curr_date (str): Current date in yyyy-mm-dd format
        look_back_days (int): Number of days to look back; omit to inherit config
        limit (int): Maximum number of articles to return; omit to inherit config

    Returns:
        str: A formatted string containing global news data
    """
    as_of_date = as_of(curr_date, trade_date)
    eff_lookback, eff_limit = _effective_global_news_defaults(look_back_days, limit)
    params = {"as_of": as_of_date, "look_back_days": eff_lookback, "limit": eff_limit}
    return observe_supported_call(
        _registry(), "get_global_news", params, "P-10",
        lambda: route_to_vendor("get_global_news", as_of_date, look_back_days, limit))


@tool
def get_insider_transactions(
    ticker: Annotated[str, InjectedState("company_of_interest")],
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve insider transaction information about a company.
    Uses the configured news_data vendor.
    Returns:
        str: A report of insider transaction data
    """
    eff_trade_date = trade_date or None
    params = {"ticker": ticker, "trade_date": eff_trade_date}
    return observe_supported_call(
        _registry(), "get_insider_transactions", params, "P-08",
        lambda: route_to_vendor("get_insider_transactions", ticker, eff_trade_date))


@tool
def get_macro_indicators(
    indicator: Annotated[
        str,
        "Macro indicator: a friendly alias such as 'cpi', 'core_pce', "
        "'unemployment', 'fed_funds_rate', '10y_treasury', 'yield_curve', "
        "'real_gdp', 'vix', euro-area aliases such as 'ecb_deposit_rate', "
        "'euro_hicp', 'euro_core_hicp', 'euro_real_gdp', 'germany_10y', "
        "'france_10y', 'eur_usd', or a raw FRED series ID such as 'CPIAUCSL'.",
    ],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format; the end of the window"],
    look_back_days: Annotated[
        int | None, "Trailing window length in days; omit for a 1-year window"
    ] = None,
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve a macroeconomic indicator time series from FRED (Federal Reserve
    Economic Data): policy rates, Treasury yields, inflation, labor, and growth,
    for the US and, through FRED's mirrored series, the euro area.
    Returns the series title, units, frequency, the latest value, the change
    over the window, and a recent observation table. Uses the configured
    macro_data vendor.

    Args:
        indicator (str): Friendly alias or raw FRED series ID
        curr_date (str): Current date in yyyy-mm-dd format
        look_back_days (int): Trailing window length; omit for a 1-year window

    Returns:
        str: A formatted markdown report of the macro series
    """
    as_of_date = as_of(curr_date, trade_date)
    eff_lookback = DEFAULT_LOOKBACK_DAYS if look_back_days is None else look_back_days
    params = {"indicator": indicator, "as_of": as_of_date, "look_back_days": eff_lookback}
    return observe_supported_call(
        _registry(), "get_macro_indicators", params, "P-11",
        lambda: route_to_vendor("get_macro_indicators", indicator, as_of_date, look_back_days),
        source_hint="FRED")


@tool
def get_prediction_markets(
    topic: Annotated[
        str,
        "Event topic/keyword, e.g. 'Fed rate cut', 'recession 2026', "
        "'US election', or a sector/company event.",
    ],
    limit: Annotated[int | None, "Max markets to return; omit for a default of 6"] = None,
    trade_date: Annotated[str, InjectedState("trade_date")] = "",
) -> str:
    """
    Retrieve live, market-implied probabilities for forward-looking events from
    prediction markets (Polymarket): Fed decisions, recession, elections,
    geopolitics, crypto. Returns the most-traded open markets matching the
    topic, each with its implied probability, traded volume, resolution date,
    and recent move. Uses the configured prediction_markets vendor.

    Args:
        topic (str): Event keyword(s) to search
        limit (int): Max markets to return; omit for a default of 6

    Returns:
        str: A formatted markdown report of matching prediction markets
    """
    eff_trade_date = trade_date or None
    eff_limit = DEFAULT_MARKET_LIMIT if limit is None else limit
    params = {"topic": topic, "limit": eff_limit, "trade_date": eff_trade_date}
    return observe_supported_call(
        _registry(), "get_prediction_markets", params, "P-12",
        lambda: route_to_vendor("get_prediction_markets", topic, limit, eff_trade_date),
        source_hint="Polymarket")
