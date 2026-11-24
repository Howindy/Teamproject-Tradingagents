"""FR-10-FC01/FC06: SEC and price boundaries with synthetic inputs (ADR 002)."""

from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from tradingagents.dataflows.errors import NoMarketDataError
from tradingagents.dataflows.vendors import sec_edgar
from tradingagents.dataflows.vendors.yahoo import market
from tradingagents.financials.sec_provider import _facts_for_concept, _price, _span_of, _years_back


def test_sec_structured_helpers_reuse_existing_cache_without_tool_observation(monkeypatch):
    monkeypatch.setattr(sec_edgar, "cik_for", lambda ticker: "0000320193")
    calls = []
    monkeypatch.setattr(sec_edgar, "_cached_json", lambda url, name: calls.append((url, name)) or {"fixture": True})
    assert sec_edgar.company_facts("AAPL") == ("0000320193", {"fixture": True})
    assert sec_edgar.submissions("AAPL") == ("0000320193", {"fixture": True})
    assert calls[0][1] == "CIK0000320193.json"
    assert calls[1][1] == "CIK0000320193-submissions.json"
    monkeypatch.setattr(sec_edgar, "cik_for", lambda ticker: None)
    with pytest.raises(NoMarketDataError):
        sec_edgar.company_facts("NOPE")


def test_fiscal_anniversaries_and_span_classification():
    assert _years_back(date(2025, 1, 31), date(2024, 1, 31)) == 1
    assert _years_back(date(2025, 1, 31), date(2024, 10, 31)) is None
    assert _span_of({"start": "2025-02-01", "end": "2025-04-30"}) == "quarter"
    assert _span_of({"start": "2025-02-01", "end": "2025-07-31"}) == "ytd"


def test_same_day_filing_cannot_hide_prior_visible_fact():
    old = {"start": "2025-01-01", "end": "2025-03-31", "filed": "2025-05-01",
           "accn": "old", "val": 100, "fy": 2025, "fp": "Q1"}
    same_day = {**old, "filed": "2025-08-05", "accn": "late"}
    data = {"Revenues": {"units": {"USD": [old, same_day]}}}
    labels = {"old": (2025, "Q1", date(2025, 3, 31)),
              "late": (2025, "Q1", date(2025, 3, 31))}
    facts = _facts_for_concept(data, "2025-08-05", labels, "0000000001")
    assert len(facts) == 1
    assert facts[0].accession == "old"


def test_daily_close_is_not_eligible_before_completion_and_split_failure_is_closed(monkeypatch):
    zone = ZoneInfo("America/New_York")
    closes = pd.Series([100.0, 110.0], index=pd.DatetimeIndex(["2025-08-04", "2025-08-05"]))
    monkeypatch.setattr(market, "get_closes", lambda *args: closes)
    monkeypatch.setattr(market.yf, "Ticker", lambda _: SimpleNamespace(
        get_history_metadata=lambda: {"exchangeTimezoneName": "America/New_York", "currency": "USD"},
        splits=pd.Series(dtype=float),
    ))
    result = market.completed_close("AAPL", "2025-08-05", datetime(2025, 8, 5, 0, tzinfo=zone))
    assert result["price_date"] == "2025-08-04"
    assert result["value"] == 100.0
    assert result["completed_at"] == datetime(2025, 8, 4, 16, tzinfo=zone)

    class FailedSplits:
        def get_history_metadata(self):
            return {"currency": "USD"}

        @property
        def splits(self):
            raise RuntimeError("injected")

    monkeypatch.setattr(market.yf, "Ticker", lambda _: FailedSplits())
    assert market.completed_close("AAPL", "2025-08-05", datetime(2025, 8, 5, tzinfo=zone)) is None


def test_vendor_cannot_self_certify_stale_close_as_latest(monkeypatch):
    from tradingagents.financials.models import EvaluationClock

    clock = EvaluationClock(date(2025, 8, 5), datetime(2025, 8, 5, tzinfo=ZoneInfo("America/New_York")), date(2026, 11, 24))
    monkeypatch.setattr(market, "completed_close", lambda *args, **kwargs: {
        "price_date": "2025-07-01", "currency": "USD", "unit": "USD/shares",
    })
    price, reason = _price("AAPL", clock.as_of, clock, date(2024, 9, 28))
    assert price is None
    assert reason == "price_availability_unknown"
