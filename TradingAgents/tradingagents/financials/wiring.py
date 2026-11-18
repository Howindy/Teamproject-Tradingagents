"""Composition point: turn run state into the FR-07 metric block.

This is the adapter a team data service replaces. Data providers implement only
``fetch(ticker, as_of) -> FinancialInputs``; they are independent of the router,
model and graph.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from tradingagents.financials.models import EvaluationClock
from tradingagents.financials.service import (
    FinancialDataProvider,
    FinancialMetricProvider,
    LocalReferenceDataProvider,
)

RUN_CLOCK_TIMEZONE = "America/New_York"


def run_clock(trade_date: str) -> EvaluationClock:
    """Date-level cutoff: 00:00 of the analysis date in run-clock time.

    A same-day close or same-day filing is therefore not assumed available,
    which is the conservative policy accepted for the frozen reference set.
    """
    as_of = date.fromisoformat(str(trade_date))
    cutoff = datetime.combine(as_of, time.min, tzinfo=ZoneInfo(RUN_CLOCK_TIMEZONE))
    return EvaluationClock(as_of=as_of, cutoff=cutoff, today=date.today())


class MetricProviderFactory:
    """One cached provider per analysis date, reused by every analyst turn."""

    def __init__(self, data_factory):
        self._data_factory = data_factory
        self._providers = {}

    def __call__(self, state):
        ticker = state.get("company_of_interest")
        if not ticker:
            return None
        clock = run_clock(state["trade_date"])
        if clock.as_of not in self._providers:
            self._providers[clock.as_of] = FinancialMetricProvider(
                self._data_factory(clock), clock
            )
        return self._providers[clock.as_of].get(str(ticker), clock.as_of)


def build_metrics_factory(config, *, data_factory=None):
    """None unless FR-07 input is configured; never silently fetches.

    ``fr07_sec_enabled`` selects the general SEC companyfacts adapter;
    ``fr07_reference_root`` selects the frozen reference snapshot. An explicit
    ``data_factory(clock)`` wins, which is the team-data-service injection point.
    """
    config = config or {}
    root = config.get("fr07_reference_root") or ""
    use_sec = bool(config.get("fr07_sec_enabled"))
    if data_factory is None and not root and not use_sec:
        return None

    def make_data(clock) -> FinancialDataProvider:
        if data_factory is not None:
            return data_factory(clock)
        if use_sec:
            from tradingagents.financials.sec_provider import SecCompanyFactsProvider

            return SecCompanyFactsProvider(clock)
        return LocalReferenceDataProvider(root)

    return MetricProviderFactory(make_data)
