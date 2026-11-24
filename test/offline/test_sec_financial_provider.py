"""FR-10-FC01/FC06: SEC and price boundaries with synthetic inputs (ADR 002)."""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from tradingagents.dataflows.errors import NoMarketDataError
from tradingagents.dataflows.vendors import sec_edgar
from tradingagents.dataflows.vendors.yahoo import market
from tradingagents.financials.sec_provider import _facts_for_concept, _price, _span_of, _years_back


@pytest.fixture
def yahoo_daily_history(monkeypatch):
    """FC06: distinct raw/adjusted prices expose the actual vendor request."""
    def install(dates, prices):
        history = pd.DataFrame({"Close": prices}, index=pd.DatetimeIndex(dates))
        requests = []

        def read_history(**kwargs):
            requests.append(kwargs)
            # Simulate the dividend-adjusted default while preserving the raw close.
            return history if kwargs.get("auto_adjust") is False else history * 0.9

        ticker = SimpleNamespace(
            history=read_history,
            get_history_metadata=lambda: {
                "exchangeTimezoneName": "America/New_York", "currency": "USD",
            },
            splits=pd.Series(dtype=float),
        )
        monkeypatch.setattr(market.yf, "Ticker", lambda _: ticker)
        return requests

    return install


def test_sec_structured_helpers_reuse_existing_cache_without_tool_observation(monkeypatch):
    monkeypatch.setattr(sec_edgar, "cik_for", lambda ticker: "0000320193")
    calls = []
    monkeypatch.setattr(sec_edgar, "_cached_json", lambda url, name: calls.append((url, name)) or {"fixture": True})
    monkeypatch.setattr(sec_edgar, "_cached_exact_json", lambda url, name: calls.append((url, name)) or {"fixture": True})
    assert sec_edgar.company_facts("AAPL") == ("0000320193", {"fixture": True})
    assert sec_edgar.submissions("AAPL") == ("0000320193", {"fixture": True})
    assert calls[0][1] == "CIK0000320193-raw-v1.json"
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


def test_daily_close_is_not_eligible_before_completion_and_split_failure_is_closed(monkeypatch, yahoo_daily_history):
    zone = ZoneInfo("America/New_York")
    requests = yahoo_daily_history(["2025-08-04", "2025-08-05"], [100.0, 110.0])
    result = market.completed_close("AAPL", "2025-08-05", datetime(2025, 8, 5, 0, tzinfo=zone))
    assert result["price_date"] == "2025-08-04"
    assert result["value"] == 100.0
    assert result["completed_at"] == datetime(2025, 8, 4, 16, tzinfo=zone)
    assert len(requests) == 1
    assert requests[0]["auto_adjust"] is False

    class FailedSplits:
        def history(self, **kwargs):
            return pd.DataFrame({"Close": [100.0]}, index=pd.DatetimeIndex(["2025-08-04"]))

        def get_history_metadata(self):
            return {"exchangeTimezoneName": "America/New_York", "currency": "USD"}

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


@pytest.mark.parametrize("as_of,dates,expected_reason", [
    ("2025-08-05", ["2025-08-04", "2025-08-05"], None),
    ("2025-08-04", ["2025-08-01"], None),
    ("2025-09-02", ["2025-08-29"], "price_availability_unknown"),
    ("2025-08-05", ["2025-07-01"], "stale_price"),
    ("2025-08-05", ["2025-08-05"], "missing_price"),
])
def test_real_price_adapter_path_handles_cutoff_weekend_holiday_and_staleness(
    yahoo_daily_history, as_of, dates, expected_reason,
):
    """FC06: run the helper and SEC price adapter together, with no network."""
    from tradingagents.financials.models import EvaluationClock

    yahoo_daily_history(dates, [100.0] * len(dates))
    day = date.fromisoformat(as_of)
    clock = EvaluationClock(day, datetime.combine(day, datetime.min.time(), ZoneInfo("America/New_York")), date(2026, 11, 24))
    price, reason = _price("AAPL", day, clock, date(2024, 9, 28))
    assert reason == expected_reason
    if expected_reason is None:
        assert price.value == 100
        assert price.price_date == date.fromisoformat(dates[0])
        assert price.expected_latest_session == price.price_date
        assert price.completed_at <= clock.cutoff
    else:
        assert price is None


@pytest.mark.parametrize("as_of,dates,expected_display,expected_reason", [
    ("2025-08-05", ["2025-08-04"], "16.4", None),
    ("2025-09-02", ["2025-08-29"], "n/a", "price_availability_unknown"),
    ("2025-08-05", ["2025-07-01"], "n/a", "stale_price"),
])
def test_fiscal_pe_uses_raw_daily_close_or_preserves_adapter_reason(
    yahoo_daily_history, as_of, dates, expected_display, expected_reason,
):
    """FC06: price helper -> SEC adapter -> calculator, independent 100/6.08 oracle."""
    from tradingagents.financials.metrics import calculate_metrics
    from tradingagents.financials.models import EvaluationClock, FinancialFact, FinancialInputs

    yahoo_daily_history(dates, [100.0])
    day = date.fromisoformat(as_of)
    clock = EvaluationClock(day, datetime.combine(day, datetime.min.time(), ZoneInfo("America/New_York")), date(2026, 11, 24))
    eps = FinancialFact(
        fact_id="annual-eps", subject_id="0000320193", metric="diluted_eps",
        value="6.08", unit="USD/shares", currency="USD",
        period_start=date(2023, 10, 1), period_end=date(2024, 9, 28),
        fiscal_year=2024, fiscal_quarter=None, span="annual",
        filed_at=date(2024, 11, 1), accession="fixture-filing",
        filing_ref="fixture://annual", concept="EarningsPerShareDiluted",
        source_ref="fixture://eps", share_basis="common_shares",
        calendar_id="fixture-aapl-calendar",
        calendar_evidence=("fixture FY2024 ends 2024-09-28",),
        basis_evidence=("fixture annual EPS on common-share basis",),
    )
    price, reason = _price("AAPL", day, clock, eps.period_end)
    inputs = FinancialInputs(eps.subject_id, (eps,), price, (reason,) if reason else ())
    pe = next(row for row in calculate_metrics(inputs, clock).rows if row.metric_id == "pe_fy")
    assert (pe.display, pe.reason) == (expected_display, expected_reason)
    assert pe.input_fact_ids == (eps.fact_id,)
    if price is not None:
        assert price.source_ref in pe.sources


def test_sec_fractional_fact_retains_raw_digits_on_cold_and_cached_reads(tmp_path, monkeypatch):
    """FC07: exact SEC decimal text survives the transport/cache/adapter boundary."""
    digits = "6.12345678901234567890123456789"
    raw = ('{"facts":{"us-gaap":{"EarningsPerShareDiluted":{"units":{"USD/shares":['
           '{"start":"2023-10-01","end":"2024-09-28","filed":"2024-11-01",'
           '"accn":"annual","fy":2024,"fp":"FY","val":' + digits + '}]}}}}}')
    calls = []
    response = SimpleNamespace(text=raw, raise_for_status=lambda: None)
    monkeypatch.setattr(sec_edgar.requests, "get", lambda *a, **k: calls.append(a[0]) or response)
    monkeypatch.setattr(sec_edgar, "cik_for", lambda _: "0000320193")
    monkeypatch.setattr(sec_edgar, "get_config", lambda: {"data_cache_dir": str(tmp_path)})
    # An older generic cache may already have rounded away digits. It must not
    # be mistaken for an exact raw SEC snapshot.
    old_cache = tmp_path / "sec_edgar" / "CIK0000320193.json"
    old_cache.parent.mkdir()
    old_cache.write_text('{"rounded":6.123456789012345}', encoding="utf-8")
    for _ in range(2):
        cik, payload = sec_edgar.company_facts("AAPL")
        facts = _facts_for_concept(payload["facts"]["us-gaap"], "2025-08-05",
                                   {"annual": (2024, "FY", date(2024, 9, 28))}, cik)
        assert len(facts) == 1
        assert facts[0].value == Decimal(digits)
    assert len(calls) == 1
    assert old_cache.read_text(encoding="utf-8") == '{"rounded":6.123456789012345}'


def test_exact_sec_cache_does_not_publish_malformed_json(tmp_path, monkeypatch):
    """FC07/FC10: unreadable source stays an explicit vendor failure, never cached as success."""
    from tradingagents.dataflows.errors import VendorUnavailableError

    monkeypatch.setattr(sec_edgar, "cik_for", lambda _: "0000320193")
    monkeypatch.setattr(sec_edgar, "get_config", lambda: {"data_cache_dir": str(tmp_path)})
    monkeypatch.setattr(sec_edgar.requests, "get", lambda *a, **k: SimpleNamespace(
        text="not json", raise_for_status=lambda: None))
    with pytest.raises(VendorUnavailableError):
        sec_edgar.company_facts("AAPL")
    assert not list(tmp_path.rglob("*.json"))


def test_january_fiscal_year_comparative_is_not_carrying_filing_year():
    """FC01: January-end fiscal Q3 comparative must be one FY earlier, never calendar Q4."""
    from tradingagents.financials.sec_provider import _filing_labels

    current = {"start": "2024-08-01", "end": "2024-10-31", "filed": "2024-12-01",
               "accn": "jan-fy", "val": 120, "fy": 2025, "fp": "Q3"}
    comparison = {**current, "start": "2023-08-01", "end": "2023-10-31", "val": 100}
    data = {"Revenues": {"units": {"USD": [current, comparison]}}}
    facts = _facts_for_concept(data, "2025-01-01", _filing_labels(data), "fixture-jan")
    by_end = {f.period_end: f for f in facts}
    assert (by_end[date(2024, 10, 31)].fiscal_year, by_end[date(2024, 10, 31)].fiscal_quarter) == (2025, 3)
    assert (by_end[date(2023, 10, 31)].fiscal_year, by_end[date(2023, 10, 31)].fiscal_quarter) == (2024, 3)
    assert dict(by_end[date(2023, 10, 31)].disclosure)["fy"] == "2025"
