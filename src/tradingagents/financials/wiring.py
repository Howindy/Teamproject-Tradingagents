"""FR-10 composition point (ADR 002 D-203; IR-05).

Entry integration must explicitly enter ``analysis_scope()`` for each analysis.
Without a scope, calls remain isolated and do not retain a provider cache.

This is the adapter a team data service replaces. Data providers implement only
``fetch(ticker, as_of) -> FinancialInputs``; they are independent of the router,
model and graph.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, time
from threading import Lock
from zoneinfo import ZoneInfo

from tradingagents.financials.metrics import unavailable_bundle
from tradingagents.financials.models import EvaluationClock
from tradingagents.financials.service import (
    FinancialDataProvider,
    FinancialMetricProvider,
    FinancialMetricResult,
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
    """Analysis-local reuse without rebinding the team's RunContext (IR-05)."""

    def __init__(self, data_factory):
        self._data_factory = data_factory
        self._scope = ContextVar("financial_metric_scope", default=None)

    @contextmanager
    def analysis_scope(self):
        """Give one analysis its own cache; restore any enclosing scope on exit."""
        token = self._scope.set(({}, Lock()))
        try:
            yield
        finally:
            self._scope.reset(token)

    def __call__(self, state):
        ticker = state.get("company_of_interest")
        if not ticker:
            return None
        clock = run_clock(state["trade_date"])
        if state.get("asset_type", "stock") != "stock":
            return FinancialMetricResult(
                unavailable_bundle(str(ticker), clock.as_of.isoformat(), "not_supported"),
                "", "not_supported", "not_supported",
            )
        scope = self._scope.get()
        if scope is None:
            provider = FinancialMetricProvider(self._data_factory(clock), clock)
        else:
            providers, lock = scope
            with lock:
                if clock.as_of not in providers:
                    providers[clock.as_of] = FinancialMetricProvider(self._data_factory(clock), clock)
                provider = providers[clock.as_of]
        return provider.get(str(ticker), clock.as_of)


def build_metrics_factory(config, *, data_factory=None):
    """None unless FR-10 input is configured; never silently fetches.

    ``fr10_sec_enabled`` selects the general SEC companyfacts adapter;
    ``fr10_reference_root`` selects the frozen reference snapshot. An explicit
    ``data_factory(clock)`` wins, which is the team-data-service injection point.
    """
    config = config or {}
    root = config.get("fr10_reference_root") or ""
    use_sec = bool(config.get("fr10_sec_enabled"))
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
