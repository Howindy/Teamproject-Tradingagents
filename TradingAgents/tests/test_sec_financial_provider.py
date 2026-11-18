"""Offline tests for the general SEC companyfacts adapter.

The SEC payload is the saved Microsoft companyfacts snapshot; no network, no
model and no TradingAgents data-vendor call is made. Price inputs are injected.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from tradingagents.dataflows.errors import NoMarketDataError
from tradingagents.dataflows.vendors import sec_edgar
from tradingagents.dataflows.vendors.yahoo import market as yahoo_market
from tradingagents.financials import sec_provider
from tradingagents.financials.metrics import calculate_metrics
from tradingagents.financials.models import EvaluationClock, PriceRecord
from tradingagents.financials.sec_provider import SecCompanyFactsProvider
from tradingagents.financials.wiring import build_metrics_factory

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).resolve().parents[2] / "docs/fr07/sec-msft-evidence/msft-companyfacts-projection.json"
MSFT_CIK = "0000789019"
CLOCK = EvaluationClock(
    as_of=date(2025, 8, 5),
    cutoff=datetime(2025, 8, 5, 0, 0, tzinfo=ZoneInfo("America/New_York")),
    today=date(2026, 11, 18),
)


@pytest.fixture
def msft(monkeypatch):
    facts = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setattr(sec_edgar, "company_facts", lambda ticker: (MSFT_CIK, facts))
    monkeypatch.setattr(
        sec_provider,
        "_price",
        lambda ticker, as_of, clock, eps_end: (
            PriceRecord(
                value=Decimal("530.3970336914062"),
                currency="USD",
                unit="USD/shares",
                price_date=date(2025, 8, 4),
                completed_at=datetime(2025, 8, 4, 20, 0, tzinfo=ZoneInfo("America/New_York")),
                expected_latest_session=date(2025, 8, 4),
                freshness_policy="previous completed session at cutoff",
                source_ref="test://msft/close/2025-08-04",
                share_basis="common_shares",
                basis_evidence=("test://basis",),
                completion_evidence="session closed",
            ),
            None,
        ),
    )
    return SecCompanyFactsProvider(CLOCK)


def test_comparative_fact_carries_its_own_fiscal_position(msft):
    inputs = msft.fetch("MSFT", CLOCK.as_of)
    by_period = {(str(f.period_start), str(f.period_end)): f for f in inputs.facts if f.metric == "revenue"}
    current = by_period[("2025-01-01", "2025-03-31")]
    prior = by_period[("2024-01-01", "2024-03-31")]
    assert (current.fiscal_year, current.fiscal_quarter) == (2025, 3)
    assert (prior.fiscal_year, prior.fiscal_quarter) == (2024, 3)
    # The carrying 10-Q is FY2025; the prior-period annotation must not copy it.
    assert prior.disclosure and dict(prior.disclosure)["fy"] == "2025"


def test_filings_after_the_analysis_date_are_excluded(msft):
    inputs = msft.fetch("MSFT", CLOCK.as_of)
    assert inputs.facts
    assert all(f.filed_at <= CLOCK.as_of for f in inputs.facts)
    accessions = {f.accession for f in inputs.facts}
    assert "0001193125-26-323660" not in accessions  # FY2026 10-K filed 2026-07-29
    assert "0001193125-26-191507" not in accessions  # 2026 Q3 10-Q


def test_fourth_quarter_is_not_derived_from_the_annual_figure(msft):
    inputs = msft.fetch("MSFT", CLOCK.as_of)
    quarters = [f for f in inputs.facts if f.metric == "revenue" and f.span == "quarter"]
    assert max(f.period_end for f in quarters) == date(2025, 3, 31)
    assert not any(f.span == "quarter" and f.period_end == date(2025, 6, 30) for f in inputs.facts)


def test_ytd_spans_stay_ytd(msft):
    inputs = msft.fetch("MSFT", CLOCK.as_of)
    ytd = [f for f in inputs.facts if f.metric == "cfo" and f.span == "ytd"]
    assert ytd
    assert all(f.span != "quarter" for f in ytd)


def test_annual_fiscal_year_labels_follow_the_june_year_end(msft):
    inputs = msft.fetch("MSFT", CLOCK.as_of)
    annual = {f.period_end: f.fiscal_year for f in inputs.facts if f.metric == "revenue" and f.span == "annual"}
    assert annual[date(2025, 6, 30)] == 2025
    assert annual[date(2024, 6, 30)] == 2024


def test_end_to_end_metrics_match_independent_hand_calculation(msft):
    bundle = calculate_metrics(msft.fetch("MSFT", CLOCK.as_of), CLOCK)
    got = {row.metric_id: row.display for row in bundle.rows}
    assert got == {
        "revenue_yoy_q": "13.3",
        "revenue_yoy_a": "14.9",
        "revenue_qoq": "0.6",
        "gross_margin": "68.7",
        "operating_margin": "45.7",
        "net_margin": "36.9",
        "current_ratio": "1.4",
        "liabilities_to_assets": "44.5",
        "fcf_reported_span": "71611",
        "pe_fy": "38.9",
    }
    assert all(row.status == "computed" for row in bundle.rows)
    # 281,724 / 245,122 - 1 = 14.9% for the June fiscal year.
    assert bundle.rows[1].exact_fraction


def test_completed_session_at_the_midnight_cutoff_is_selected(monkeypatch):
    class FakeYF:
        def __init__(self, ticker):
            self.ticker = ticker

        def get_history_metadata(self):
            return {"currency": "USD", "exchangeTimezoneName": "America/New_York"}

        @property
        def splits(self):
            import pandas as pd

            return pd.Series(dtype=float, index=pd.DatetimeIndex([]))

    import pandas as pd

    index = pd.DatetimeIndex(
        [datetime(2025, 8, 1, tzinfo=ZoneInfo("America/New_York")),
         datetime(2025, 8, 4, tzinfo=ZoneInfo("America/New_York")),
         datetime(2025, 8, 5, tzinfo=ZoneInfo("America/New_York"))]
    )
    closes = pd.Series([518.98, 530.39, 522.58], index=index)
    monkeypatch.setattr(yahoo_market, "yf", SimpleNamespace(Ticker=FakeYF))
    monkeypatch.setattr(yahoo_market, "get_closes", lambda ticker, start, end: closes)
    price, reason = sec_provider._price("MSFT", CLOCK.as_of, CLOCK, date(2025, 6, 30))
    assert reason is None
    assert price.price_date == date(2025, 8, 4)  # 8/5 close is after the midnight cutoff
    assert price.unit == "USD/shares"
    assert price.currency == "USD"


def test_split_after_annual_eps_marks_the_basis_incompatible(monkeypatch):
    class FakeYF:
        def __init__(self, ticker):
            self.ticker = ticker

        def get_history_metadata(self):
            return {"currency": "USD", "exchangeTimezoneName": "America/New_York"}

        @property
        def splits(self):
            import pandas as pd

            stamps = [datetime(2025, 7, 15, tzinfo=ZoneInfo("America/New_York"))]
            return pd.Series([2.0], index=pd.DatetimeIndex(stamps))

    import pandas as pd

    index = pd.DatetimeIndex([datetime(2025, 8, 4, tzinfo=ZoneInfo("America/New_York"))])
    closes = pd.Series([530.39], index=index)
    monkeypatch.setattr(yahoo_market, "yf", SimpleNamespace(Ticker=FakeYF))
    monkeypatch.setattr(yahoo_market, "get_closes", lambda ticker, start, end: closes)
    price, reason = sec_provider._price("MSFT", CLOCK.as_of, CLOCK, date(2025, 6, 30))
    assert reason is None
    assert price.share_basis != "common_shares"
    inputs = msft_inputs_with(price)
    row = next(r for r in calculate_metrics(inputs, CLOCK).rows if r.metric_id == "pe_fy")
    assert (row.status, row.reason) == ("n/a", "basis_mismatch")


def msft_inputs_with(price):
    facts = json.loads(FIXTURE.read_text(encoding="utf-8"))
    original = sec_edgar.company_facts
    sec_edgar.company_facts = lambda ticker: (MSFT_CIK, facts)
    try:
        import dataclasses

        inputs = SecCompanyFactsProvider(CLOCK).fetch("MSFT", CLOCK.as_of)
        return dataclasses.replace(inputs, price=price)
    finally:
        sec_edgar.company_facts = original


def test_non_us_filer_is_explicitly_not_supported(monkeypatch):
    def raise_missing(ticker):
        raise NoMarketDataError(ticker, ticker, "not a US SEC filer")

    monkeypatch.setattr(sec_edgar, "company_facts", raise_missing)
    inputs = SecCompanyFactsProvider(CLOCK).fetch("0700.HK", CLOCK.as_of)
    assert inputs.facts == ()
    assert inputs.issues[0].startswith("not_supported")


def _synthetic_january_filer():
    """One annual boundary only, January year-end, 10-Q comparatives.

    The retired implementation labelled the annual end 2025-01-31 as fiscal
    year 2025 (calendar year of the period end) and derived quarters by dividing
    the fiscal year evenly, which also needed two annual boundaries to work.
    """

    def fact(start, end, val, accn, fy, fp, form, filed):
        row = {"end": end, "val": val, "accn": accn, "fy": fy, "fp": fp, "form": form, "filed": filed}
        if start:
            row["start"] = start
        return row

    def inst(end, val, accn, fy, fp, form, filed):
        return {"end": end, "val": val, "accn": accn, "fy": fy, "fp": fp, "form": form, "filed": filed}

    us_gaap = {}

    def add(tag, unit, rows):
        us_gaap.setdefault(tag, {}).setdefault("units", {}).setdefault(unit, []).extend(rows)

    annual = "ACC-10K-FY2024"
    add("RevenueFromContractWithCustomerExcludingAssessedTax", "USD", [
        fact("2024-02-01", "2025-01-31", 1200, annual, 2024, "FY", "10-K", "2025-03-05"),
        fact("2023-02-01", "2024-01-31", 1000, annual, 2024, "FY", "10-K", "2025-03-05"),
    ])
    add("GrossProfit", "USD", [fact("2024-02-01", "2025-01-31", 600, annual, 2024, "FY", "10-K", "2025-03-05")])
    add("OperatingIncomeLoss", "USD", [fact("2024-02-01", "2025-01-31", 240, annual, 2024, "FY", "10-K", "2025-03-05")])
    add("NetIncomeLoss", "USD", [fact("2024-02-01", "2025-01-31", 120, annual, 2024, "FY", "10-K", "2025-03-05")])
    add("EarningsPerShareDiluted", "USD/shares", [
        fact("2024-02-01", "2025-01-31", 2.0, annual, 2024, "FY", "10-K", "2025-03-05"),
        fact("2023-02-01", "2024-01-31", 1.8, annual, 2024, "FY", "10-K", "2025-03-05"),
    ])
    add("NetCashProvidedByUsedInOperatingActivities", "USD", [
        fact("2024-02-01", "2025-01-31", 150_000_000, annual, 2024, "FY", "10-K", "2025-03-05"),
    ])
    add("PaymentsToAcquirePropertyPlantAndEquipment", "USD", [
        fact("2024-02-01", "2025-01-31", 30_000_000, annual, 2024, "FY", "10-K", "2025-03-05"),
    ])
    for tag, value in (("Assets", 5000), ("AssetsCurrent", 2000), ("Liabilities", 3000), ("LiabilitiesCurrent", 1000)):
        add(tag, "USD", [inst("2025-01-31", value, annual, 2024, "FY", "10-K", "2025-03-05")])

    for quarter, (end, start, prior_start, prior_end, revenue, prior, gross, operating,
                  net, eps) in enumerate((
        ("2024-04-30", "2024-02-01", "2023-02-01", "2023-04-30", 300, 250, 150, 60, 30, 0.50),
        ("2024-07-31", "2024-05-01", "2023-05-01", "2023-07-31", 310, 260, 155, 62, 31, 0.52),
        ("2024-10-31", "2024-08-01", "2023-08-01", "2023-10-31", 320, 270, 160, 64, 32, 0.54),
    ), start=1):
        accn = f"ACC-10Q-Q{quarter}"
        filed = {"2024-04-30": "2024-06-05", "2024-07-31": "2024-09-05", "2024-10-31": "2024-12-05"}[end]
        fp = f"Q{quarter}"
        add("RevenueFromContractWithCustomerExcludingAssessedTax", "USD", [
            fact(start, end, revenue, accn, 2024, fp, "10-Q", filed),
            fact(prior_start, prior_end, prior, accn, 2024, fp, "10-Q", filed),
        ])
        add("GrossProfit", "USD", [fact(start, end, gross, accn, 2024, fp, "10-Q", filed)])
        add("OperatingIncomeLoss", "USD", [fact(start, end, operating, accn, 2024, fp, "10-Q", filed)])
        add("NetIncomeLoss", "USD", [fact(start, end, net, accn, 2024, fp, "10-Q", filed)])
        add("EarningsPerShareDiluted", "USD/shares", [
            fact(start, end, eps, accn, 2024, fp, "10-Q", filed),
        ])
        add("AssetsCurrent", "USD", [inst(end, 1900 + quarter * 50, accn, 2024, fp, "10-Q", filed)])
        add("LiabilitiesCurrent", "USD", [inst(end, 950 + quarter * 10, accn, 2024, fp, "10-Q", filed)])
    return {"cik": 1, "entityName": "Synthetic January Filer", "facts": {"us-gaap": us_gaap}}


def test_single_annual_boundary_january_year_end_uses_declared_fiscal_labels(monkeypatch):
    """Regression for calendar-year labelling and equal-division quarters."""
    facts = _synthetic_january_filer()
    monkeypatch.setattr(sec_edgar, "company_facts", lambda ticker: ("0000000001", facts))
    monkeypatch.setattr(
        sec_provider,
        "_price",
        lambda ticker, as_of, clock, eps_end: (None, "missing_price"),
    )
    clock = EvaluationClock(
        as_of=date(2025, 3, 10),
        cutoff=datetime(2025, 3, 10, 0, 0, tzinfo=ZoneInfo("America/New_York")),
        today=date(2026, 11, 18),
    )
    inputs = SecCompanyFactsProvider(clock).fetch("JAN", clock.as_of)
    revenue = {(str(f.period_start), str(f.period_end)): f for f in inputs.facts if f.metric == "revenue"}

    # Fiscal year comes from the filing's declared fy, not the period end's year.
    assert revenue[("2024-02-01", "2025-01-31")].fiscal_year == 2024
    assert revenue[("2023-02-01", "2024-01-31")].fiscal_year == 2023
    # Quarters are declared by the filing (fy=2024, fp=Q1..Q3); the comparative
    # quarter is one fiscal year back, not a copy of fy=2024.
    for start, end, year, quarter in (
        ("2024-02-01", "2024-04-30", 2024, 1),
        ("2023-02-01", "2023-04-30", 2023, 1),
        ("2024-08-01", "2024-10-31", 2024, 3),
        ("2023-08-01", "2023-10-31", 2023, 3),
    ):
        assert (revenue[(start, end)].fiscal_year, revenue[(start, end)].fiscal_quarter) == (year, quarter)

    bundle = calculate_metrics(inputs, clock)
    got = {row.metric_id: row.display for row in bundle.rows}
    assert got["revenue_yoy_a"] == "20.0"   # 1200 / 1000 - 1
    assert got["revenue_yoy_q"] == "18.5"   # 320 / 270 - 1 (FY2023 Q3)
    assert got["revenue_qoq"] == "3.2"      # 320 / 310 - 1
    # The latest balance date is the annual 2025-01-31 instant, not the Q3 one.
    assert got["current_ratio"] == "2.0"    # 2000 / 1000
    assert got["fcf_reported_span"] == "120"


def test_configuration_selects_the_general_sec_adapter():
    assert build_metrics_factory({"fr07_sec_enabled": False, "fr07_reference_root": ""}) is None
    factory = build_metrics_factory({"fr07_sec_enabled": True})
    data = factory._data_factory(CLOCK)
    assert isinstance(data, SecCompanyFactsProvider)
