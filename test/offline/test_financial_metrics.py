"""FR-10-FC01–FC08: independent frozen reference and failure cases (ADR 002)."""

import json
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tradingagents.financials.metrics import calculate_metrics, render_metrics
from tradingagents.financials.models import (
    EvaluationClock,
    FinancialFact,
    FinancialInputs,
    PriceRecord,
    decimal_value,
)
from tradingagents.financials.service import LocalReferenceDataProvider
from tradingagents.financials.wiring import MetricProviderFactory, build_metrics_factory

DATA = json.loads((Path(__file__).resolve().parents[2] / "docs/ci/financial-metrics-cases.json").read_text(encoding="utf-8"))
CLOCK = EvaluationClock(date(2025, 8, 5), datetime(2025, 8, 5, tzinfo=ZoneInfo("America/New_York")), date(2026, 11, 24))


def projected(issuer):
    """Project independently pinned facts without calling the calculator."""
    ref = DATA["reference_data"]
    rows = [(k, v) for k, v in ref["selected_facts"].items() if v["issuer"] == issuer]
    facts = []
    for fid, r in rows:
        concept = r["concept"].split(":")[-1]
        metric, rank = LocalReferenceDataProvider._CONCEPTS[concept]
        facts.append(FinancialFact(
            fact_id=fid, subject_id=str(r["subject_id"]).zfill(10), metric=metric,
            value=Decimal(r["value"]), unit=r["unit"], currency=r["currency"],
            period_start=date.fromisoformat(r["period_start"]) if r["period_start"] else None,
            period_end=date.fromisoformat(r["period_end"]), fiscal_year=r["fiscal_year"],
            fiscal_quarter=r["fiscal_quarter"], span=r["span"],
            filed_at=date.fromisoformat(r["filed_at"]), accession=r["accession"],
            filing_ref=r["filing_file"] + "#" + r["inline_element_id"], concept=concept,
            source_ref=r["companyfacts_file"] + "#" + r["companyfacts_pointer"],
            calendar_id=issuer, calendar_evidence=("independent-calendar",),
            sign_rule="positive_outflow" if metric == "capex" else "as_reported",
            share_basis="common_shares" if metric == "diluted_eps" else "",
            basis_evidence=("independent-eps-basis",) if metric == "diluted_eps" else (),
            concept_rank=rank,
        ))
    p = ref["price_records"][issuer]
    price = PriceRecord(
        Decimal(p["value"]), p["currency"], p["unit"], date.fromisoformat(p["actual_price_date"]),
        datetime.fromisoformat("2025-08-04T20:00:00+00:00"), date(2025, 8, 4),
        p["freshness_policy"], p["source_file"] + "#" + p["json_pointer"],
        "common_shares", ("independent-price-basis",), p["completion_evidence"],
    )
    return FinancialInputs(facts[0].subject_id, tuple(facts), price)


@pytest.mark.parametrize("issuer,expected", [
    ("aapl", ["9.6", "2.0", "-1.4", "46.5", "30.0", "24.9", "0.9", "80.1", "72281", "33.4"]),
    ("xom", ["-12.4", "1.5", "-2.0", "n/a", "n/a", "8.7", "1.2", "39.7", "12322", "13.7"]),
])
def test_fr10_frozen_ten_rows(issuer, expected):
    bundle = calculate_metrics(projected(issuer), CLOCK)
    assert [row.display for row in bundle.rows] == expected
    oracle = [r for r in DATA["reference_data"]["expected_metrics"] if r["issuer"] == issuer]
    for row, expected_row in zip(bundle.rows, oracle, strict=True):
        assert row.metric_id == expected_row["metric_id"]
        assert row.status == expected_row["status"]
        assert row.reason == expected_row.get("reason")
        assert row.input_fact_ids == tuple(expected_row["input_fact_ids"])
    assert len(bundle.to_dict()["rows"]) == 10
    assert render_metrics(bundle)


def test_fr10_missing_comparison_and_post_cutoff_price():
    inputs = projected("aapl")
    missing = replace(inputs, facts=tuple(f for f in inputs.facts if f.fact_id != "aapl.rev.q3.2024"))
    rows = {r.metric_id: r for r in calculate_metrics(missing, CLOCK).rows}
    assert (rows["revenue_yoy_q"].status, rows["revenue_yoy_q"].reason) == ("n/a", "missing_comparison")
    assert rows["revenue_qoq"].display == "-1.4"
    later = replace(inputs.price, completed_at=datetime.fromisoformat("2025-08-05T04:00:01+00:00"))
    rows = {r.metric_id: r for r in calculate_metrics(replace(inputs, price=later), CLOCK).rows}
    assert (rows["pe_fy"].status, rows["pe_fy"].reason) == ("n/a", "price_not_completed")


def test_historical_same_day_disclosure_requires_time_evidence():
    inputs = projected("aapl")
    amended = tuple(replace(f, filed_at=CLOCK.as_of, public_at=None)
                    if f.fact_id == "aapl.rev.q3.2025" else f for f in inputs.facts)
    bundle = calculate_metrics(replace(inputs, facts=amended), CLOCK)
    assert "availability_unknown:aapl.rev.q3.2025" in bundle.issues
    assert all("aapl.rev.q3.2025" not in row.input_fact_ids for row in bundle.rows)


def _mutate(inputs, fact_id, **changes):
    return replace(inputs, facts=tuple(replace(f, **changes) if f.fact_id == fact_id else f for f in inputs.facts))


def _row(inputs, metric):
    return next(r for r in calculate_metrics(inputs, CLOCK).rows if r.metric_id == metric)


def test_comparison_units_and_bases_are_not_guessed():
    inputs = projected("aapl")
    for changes, reason in [({"unit": "shares"}, "unit_mismatch"),
                            ({"currency": "EUR"}, "currency_mismatch"),
                            ({"value": Decimal("0")}, "non_positive_base")]:
        row = _row(_mutate(inputs, "aapl.rev.q3.2024", **changes), "revenue_yoy_q")
        assert (row.status, row.reason) == ("n/a", reason)
    eps = _row(_mutate(inputs, "aapl.eps.fy2024", value=Decimal("-1")), "pe_fy")
    assert (eps.status, eps.reason) == ("n/a", "non_positive_eps")
    mismatch = _row(replace(inputs, price=replace(inputs.price, share_basis="unverified_pre_split")), "pe_fy")
    assert (mismatch.status, mismatch.reason) == ("n/a", "basis_mismatch")
    stale = _row(replace(inputs, price=replace(inputs.price, expected_latest_session=date(2025, 8, 1))), "pe_fy")
    assert (stale.status, stale.reason) == ("n/a", "stale_price")


def test_unknown_capex_sign_and_negative_fcf():
    inputs = projected("xom")
    row = _row(_mutate(inputs, "xom.capex.ytd", sign_rule="unknown"), "fcf_reported_span")
    assert (row.status, row.reason) == ("n/a", "unknown_capex_sign")
    row = _row(_mutate(inputs, "xom.cfo.ytd", value=Decimal("5000000000")), "fcf_reported_span")
    assert row.status == "computed" and row.display == "-7181"


def test_previous_quarter_not_substituted_for_yoy_or_q4():
    inputs = projected("aapl")
    q2 = next(f for f in inputs.facts if f.fact_id == "aapl.rev.q2.2025")
    wrong = _mutate(inputs, "aapl.rev.q3.2024", value=q2.value, period_start=q2.period_start,
                    period_end=q2.period_end, fiscal_year=q2.fiscal_year, fiscal_quarter=q2.fiscal_quarter)
    row = _row(wrong, "revenue_yoy_q")
    assert (row.status, row.reason) == ("n/a", "missing_comparison")
    xom = projected("xom")
    missing = replace(xom, facts=tuple(f for f in xom.facts if f.fact_id != "xom.rev.q1.2025"))
    row = _row(missing, "revenue_qoq")
    assert (row.status, row.reason) == ("n/a", "missing_quarter")


@pytest.mark.parametrize("value", [True, 1.25, float("nan")])
def test_fr10_rejects_binary_or_boolean_authority(value):
    with pytest.raises(ValueError):
        decimal_value(value)


def _counted_factory():
    """ADR 002 / IR-05: fake only the external data source, not the metric path."""
    calls = []

    class Data:
        def fetch(self, ticker, as_of):
            calls.append((ticker, as_of))
            return projected("aapl")

    return MetricProviderFactory(lambda clock: Data()), calls


def test_metric_scope_reuses_only_inside_one_analysis():
    factory, calls = _counted_factory()
    state = {"company_of_interest": "AAPL", "trade_date": "2025-08-05"}
    for _ in range(2):
        with factory.analysis_scope():
            first = factory(state)
            assert factory(state) is first
            assert first.bundle.rows[-1].display == "33.4"
    assert len(calls) == 2
    # An unscoped caller must not accidentally create persistent cross-run reuse.
    factory(state)
    factory(state)
    assert len(calls) == 4


def test_metric_scope_nested_exception_restores_prior_context():
    from contextvars import ContextVar

    factory, calls = _counted_factory()
    state = {"company_of_interest": "AAPL", "trade_date": "2025-08-05"}
    existing_context = ContextVar("test_existing_research_context", default=None)
    sentinel = object()
    token = existing_context.set(sentinel)
    try:
        with factory.analysis_scope():
            outer = factory(state)
            with pytest.raises(RuntimeError, match="primary analysis failure"), factory.analysis_scope():
                assert factory(state) is not outer
                raise RuntimeError("primary analysis failure")
            assert factory(state) is outer
            assert existing_context.get() is sentinel
        with factory.analysis_scope():
            assert factory(state) is not outer
        assert len(calls) == 3
    finally:
        existing_context.reset(token)


def test_metric_scopes_concurrent_same_ticker_date_are_independent():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    factory, calls = _counted_factory()
    barrier = Barrier(2)
    state = {"company_of_interest": "AAPL", "trade_date": "2025-08-05"}

    def run():
        with factory.analysis_scope():
            first = factory(state)
            barrier.wait(timeout=5)
            assert factory(state) is first
            return first

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: run(), range(2)))
    assert results[0] is not results[1]
    assert len(calls) == 2


def test_disabled_or_unrequested_metrics_do_not_fetch():
    factory, calls = _counted_factory()
    assert build_metrics_factory({}) is None
    with factory.analysis_scope():
        assert factory({"trade_date": "2025-08-05"}) is None
    assert calls == []
