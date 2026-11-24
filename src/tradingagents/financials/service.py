"""FR-10 provider and reuse boundary (ADR 002 D-201/D-203; IR-05).

The local SEC adapter is a replaceable example boundary. It directly reads saved
SEC companyfacts/submissions and price JSON only; it is not a second live vendor
path and does not touch TradingAgents' vendor router or network.
"""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Protocol

from tradingagents.financials.metrics import calculate_metrics, render_metrics, unavailable_bundle
from tradingagents.financials.models import (
    EvaluationClock,
    FinancialFact,
    FinancialInputs,
    MetricBundle,
    PriceRecord,
)


class FinancialDataProvider(Protocol):
    def fetch(self, ticker: str, as_of: date) -> FinancialInputs:
        ...


def _date(value):
    return date.fromisoformat(value) if value else None


def _instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
    return parsed if parsed is None or parsed.tzinfo else parsed.replace(tzinfo=UTC)


class LocalReferenceDataProvider:
    """Reference-only SEC snapshot adapter, replaceable by the team data service.

    Facts are pinned by the frozen selection plan; this is not a production
    latest-fact resolver. Unknown tickers return no facts and no invented data.
    """

    _CONCEPTS = {
        "RevenueFromContractWithCustomerExcludingAssessedTax": ("revenue", 0),
        "Revenues": ("revenue", 1),
        "GrossProfit": ("gross_profit", 0),
        "OperatingIncomeLoss": ("operating_income", 0),
        "NetIncomeLoss": ("net_income", 0),
        "AssetsCurrent": ("current_assets", 0),
        "LiabilitiesCurrent": ("current_liabilities", 0),
        "Liabilities": ("liabilities", 0),
        "Assets": ("assets", 0),
        "EarningsPerShareDiluted": ("diluted_eps", 0),
        "NetCashProvidedByUsedInOperatingActivities": ("cfo", 0),
        "PaymentsToAcquirePropertyPlantAndEquipment": ("capex", 0),
    }

    def __init__(self, reference_root: Path):
        self.root = Path(reference_root)
        plan = json.loads((self.root / "selection_plan.json").read_text(encoding="utf-8"))
        tickers = {"aapl": "AAPL", "xom": "XOM"}
        self.tickers = {value: key for key, value in tickers.items()}
        self.filings = plan["filings"]

    def fetch(self, ticker: str, as_of: date) -> FinancialInputs:
        issuer = self.tickers.get(ticker.upper())
        if issuer is None:
            return FinancialInputs(
                subject_id=ticker.upper(), issues=("not_supported:not_a_frozen_reference_issuer",)
            )
        selected = json.loads((self.root / "selected_facts.json").read_text(encoding="utf-8"))
        facts, issues = [], []
        cik = None
        for filing_stem, filing in self.filings.items():
            if filing["issuer"] != issuer:
                continue
            submissions = json.loads(
                (self.root / f"sources/{issuer}-submissions.json").read_text(encoding="utf-8")
            )
            recent = submissions["filings"]["recent"]
            cik = str(submissions["cik"]).zfill(10)
            index = recent["accessionNumber"].index(filing["accession"])
            filed_at = _date(recent["filingDate"][index])
            if filed_at > as_of:
                issues.append(f"future_filing_excluded:{filing_stem}")
                continue
            for identifier, row in selected.items():
                if row["issuer"] != issuer or row["filing_file"] != f"sources/{filing_stem}.htm":
                    continue
                concept = row["concept"].split(":", 1)[-1]
                metric, rank = self._CONCEPTS[concept]
                facts.append(
                    FinancialFact(
                        fact_id=identifier,
                        subject_id=cik,
                        metric=metric,
                        value=Decimal(row["value"]),
                        unit=row["unit"],
                        currency=row["currency"],
                        period_start=_date(row["period_start"]),
                        period_end=_date(row["period_end"]),
                        fiscal_year=row["fiscal_year"],
                        fiscal_quarter=row["fiscal_quarter"],
                        span=row["span"],
                        filed_at=_date(row["filed_at"]),
                        accession=row["accession"],
                        filing_ref=row["filing_file"] + "#" + row["inline_element_id"],
                        concept=concept,
                        source_ref=row["companyfacts_file"] + "#" + row["companyfacts_pointer"],
                        calendar_id=issuer,
                        calendar_evidence=("inspection/" + filing_stem + ".text.txt",),
                        sign_rule="positive_outflow" if metric == "capex" else "as_reported",
                        share_basis="common_shares" if metric == "diluted_eps" else "",
                        basis_evidence=(row["filing_file"] + "#" + row["inline_element_id"],)
                        if metric == "diluted_eps"
                        else (),
                        concept_rank=rank,
                        disclosure=tuple(
                            sorted(
                                {key: str(value) for key, value in row.items() if not isinstance(value, list)}.items()
                            )
                        ),
                    )
                )
        price = None
        prices = json.loads((self.root / "price_records.json").read_text(encoding="utf-8"))
        if issuer in prices:
            row = prices[issuer]
            price = self._price_record(issuer, row)
        return FinancialInputs(
            subject_id=cik or issuer.upper(), facts=tuple(facts), price=price, issues=tuple(issues)
        )

    def _price_record(self, issuer, row):
        """Derive session completion/latest-session evidence from the stored daily bars.

        The daily bar's timestamp is its session open. A regular US session ends
        16:00 New York the same date; use that, never the open, as the evidence
        that the close preceded the frozen cutoff.
        """
        from zoneinfo import ZoneInfo

        cutoff = _instant(row["cutoff"])
        source = json.loads(
            (self.root / row["source_file"]).read_text(encoding="utf-8"), parse_float=Decimal
        )
        chart = source["chart"]["result"][0]
        zone = ZoneInfo(row["exchange_timezone"])
        sessions = []
        for stamp, close in zip(chart["timestamp"], chart["indicators"]["quote"][0]["close"], strict=True):
            session_date = datetime.fromtimestamp(stamp, UTC).astimezone(zone).date()
            sessions.append((session_date, close))
        price_date = _date(row["actual_price_date"])
        # The frozen reference policy accepts the preceding completed session at
        # the fixed midnight cutoff. Recompute that expectation from saved bars.
        eligible = sorted({day for day, close in sessions if close is not None
                           and datetime.combine(day, datetime.min.time(), tzinfo=zone) < cutoff})
        expected = eligible[-1]
        completed = datetime.combine(expected, datetime.min.time().replace(hour=16), tzinfo=zone)
        if completed > cutoff or expected != price_date:
            raise ValueError("stored_price_does_not_fit_completion_policy")
        stored_close = dict(sessions).get(price_date)
        if stored_close is None or Decimal(row["value"]) != stored_close:
            raise ValueError("stored_price_value_mismatch")
        basis = row["share_basis_evidence"]["basis"]
        if "common shares" not in basis.lower() or not row["share_basis_evidence"]["request_covers_eps_end_through_retrieval"]:
            raise ValueError("stored_price_basis_unverified")
        return PriceRecord(
            Decimal(row["value"]),
            row["currency"],
            row["unit"],
            price_date,
            completed.astimezone(UTC),
            expected,
            row["freshness_policy"],
            row["source_file"] + "#" + row["json_pointer"],
            "common_shares",
            (row["share_basis_evidence"]["event_snapshot"], row["json_pointer"]),
            row["completion_evidence"] + f"; daily session expected {expected.isoformat()} closed 16:00 local",
        )


@dataclass(frozen=True)
class FinancialMetricResult:
    bundle: MetricBundle
    text: str
    mode: str
    reason: str | None = None


class FinancialMetricProvider:
    """Build once per distinct ticker/as-of/clock and reuse across analyst rounds."""

    def __init__(self, data: FinancialDataProvider | None, clock: EvaluationClock, *, enabled: bool = True):
        self._data, self._clock, self._enabled = data, clock, enabled
        self._cache = {}
        self._lock = Lock()

    def get(self, ticker: str, as_of: date) -> FinancialMetricResult:
        if as_of != self._clock.as_of:
            raise ValueError("metric_clock_as_of_mismatch")
        if not self._enabled:
            return FinancialMetricResult(
                unavailable_bundle(ticker.upper(), as_of.isoformat(), "fr07_disabled"),
                "",
                "disabled",
                "fr07_disabled",
            )
        with self._lock:
            if ticker.upper() not in self._cache:
                try:
                    inputs = (self._data.fetch(ticker, as_of) if self._data is not None
                              else FinancialInputs(ticker.upper(), issues=("data_entry_failure",)))
                except Exception:
                    inputs = FinancialInputs(subject_id=ticker.upper(), issues=("data_entry_failure",))
                if not isinstance(inputs, FinancialInputs):
                    bundle = unavailable_bundle(ticker.upper(), as_of.isoformat(), "invalid_financial_input")
                    self._cache[ticker.upper()] = FinancialMetricResult(
                        bundle, render_metrics(bundle), "unavailable", "invalid_financial_input")
                elif "data_entry_failure" in inputs.issues:
                    bundle = unavailable_bundle(ticker.upper(), as_of.isoformat(), "data_entry_failure")
                    self._cache[ticker.upper()] = FinancialMetricResult(
                        bundle, render_metrics(bundle), "unavailable", "data_entry_failure")
                elif inputs.issues and inputs.issues[0].startswith("not_supported"):
                    bundle = unavailable_bundle(ticker.upper(), as_of.isoformat(), "not_supported")
                    self._cache[ticker.upper()] = FinancialMetricResult(
                        bundle, "", "not_supported", "not_supported"
                    )
                else:
                    try:
                        bundle = calculate_metrics(inputs, self._clock)
                    except (TypeError, ValueError, ArithmeticError, AttributeError):
                        bundle = unavailable_bundle(ticker.upper(), as_of.isoformat(), "invalid_financial_input")
                    self._cache[ticker.upper()] = FinancialMetricResult(
                        bundle, render_metrics(bundle),
                        "unavailable" if "invalid_financial_input" in bundle.issues else "calculable",
                        "invalid_financial_input" if "invalid_financial_input" in bundle.issues else None,
                    )
            return self._cache[ticker.upper()]
