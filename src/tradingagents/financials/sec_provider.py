"""Generic SEC companyfacts -> FR-10 facts adapter (ADR 002 D-201/D-202; IR-09).

Reuses ``dataflows/vendors/sec_edgar`` for CIK resolution, the shared run cache
and the SEC request path; period/fiscal selection is derived from the raw facts
here, not read from the frozen reference package. This module performs no model
call and computes nothing: it only normalizes evidence for ``financials.metrics``.

Fiscal position comes from the filing's own XBRL labels: every fact carries the
``fy``/``fp`` of the filing that reported it, and the filing's period end is the
latest instant date it reports. A fact's own fiscal year is
``filing_fy - years_between(fact.end, filing_period_end)``, so a comparative is
identified by the period it covers, never by copying the carrying filing's label.
"""

from collections import defaultdict
from datetime import UTC, date
from decimal import Decimal

from tradingagents.dataflows.vendors import sec_edgar
from tradingagents.financials.models import FinancialFact, FinancialInputs, PriceRecord

# metric -> ((concept, preference rank), ...), reusing the existing statement
# tag mapping and adding the balance/cash concepts FR-07 needs.
CONCEPTS = {
    "revenue": (("RevenueFromContractWithCustomerExcludingAssessedTax", 0), ("Revenues", 1), ("SalesRevenueNet", 2)),
    "gross_profit": (("GrossProfit", 0),),
    "operating_income": (("OperatingIncomeLoss", 0),),
    "net_income": (("NetIncomeLoss", 0), ("NetIncomeLossAvailableToCommonStockholdersBasic", 1)),
    "diluted_eps": (("EarningsPerShareDiluted", 0),),
    "cfo": (("NetCashProvidedByUsedInOperatingActivities", 0),
            ("NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", 1)),
    "capex": (("PaymentsToAcquirePropertyPlantAndEquipment", 0), ("PaymentsToAcquireProductiveAssets", 1)),
    "assets": (("Assets", 0),),
    "current_assets": (("AssetsCurrent", 0),),
    "liabilities": (("Liabilities", 0),),
    "current_liabilities": (("LiabilitiesCurrent", 0),),
}
_QUARTER = (60, 115)
_YTD = ((150, 200), (240, 290))
_ANNUAL = (340, 380)
# 52/53-week filers shift their period ends by days, not months; the anniversary
# match allows that drift but never a neighbouring quarter.
_ANNIVERSARY_TOLERANCE_DAYS = 10
_PERIOD_FOCUS = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}


def _span_of(fact):
    if "start" not in fact:
        return "instant"
    days = (date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])).days
    if _QUARTER[0] <= days <= _QUARTER[1]:
        return "quarter"
    if any(low <= days <= high for low, high in _YTD):
        return "ytd"
    if _ANNUAL[0] <= days <= _ANNUAL[1]:
        return "annual"
    return None


def _years_back(period_end, fact_end):
    """Whole-year offset from ``fact_end`` to the filing's ``period_end``.

    Returns 0..3 when some anniversary lands within the 52/53-week drift, else
    None. This is a year offset, not a quarter heuristic: the quarter itself
    comes from the filing's declared ``fp``.
    """
    for offset in range(4):
        try:
            anniversary = period_end.replace(year=period_end.year - offset)
        except ValueError:  # 29 February
            anniversary = period_end.replace(year=period_end.year - offset, day=28)
        if abs((fact_end - anniversary).days) <= _ANNIVERSARY_TOLERANCE_DAYS:
            return offset
    return None


def _filing_labels(us_gaap):
    """accession -> (fiscal_year, period_focus, filing_period_end) from raw facts.

    ``fy``/``fp`` are the carrying filing's explicit XBRL labels. Its period end
    is the latest instant date it reports (a balance always carries one); when a
    filing reports no instant, the latest duration end is used instead.
    """
    filings = {}
    for entries in CONCEPTS.values():
        for concept, _ in entries:
            units = (us_gaap.get(concept) or {}).get("units", {})
            for rows in units.values():
                for fact in rows:
                    accn = fact.get("accn")
                    if not accn:
                        continue
                    slot = filings.setdefault(
                        accn, {"fy": None, "fp": None, "ends": set(), "instants": set()}
                    )
                    slot["ends"].add(fact["end"])
                    if "start" not in fact:
                        slot["instants"].add(fact["end"])
                    if slot["fy"] is None and fact.get("fy") is not None:
                        slot["fy"] = fact["fy"]
                    if slot["fp"] is None and fact.get("fp"):
                        slot["fp"] = fact["fp"]
    labels = {}
    for accn, slot in filings.items():
        if slot["fy"] is None or slot["fp"] not in {*_PERIOD_FOCUS, "FY"}:
            continue  # no declared fiscal position: do not guess one
        period_end = max(slot["instants"] or slot["ends"])
        labels[accn] = (int(slot["fy"]), slot["fp"], date.fromisoformat(period_end))
    return labels


def _fiscal_position(fact, label):
    """(fiscal_year, quarter) for a fact under its filing's declared labels."""
    fiscal_year, period_focus, period_end = label
    offset = _years_back(period_end, date.fromisoformat(fact["end"]))
    if offset is None:
        return None, None
    return fiscal_year - offset, _PERIOD_FOCUS.get(period_focus)


def _facts_for_concept(us_gaap, as_of, labels, cik):
    facts = []
    for metric, entries in CONCEPTS.items():
        for concept, rank in entries:
            units = (us_gaap.get(concept) or {}).get("units", {})
            for unit, unit_facts in units.items():
                currency, _, per_share = unit.partition("/")
                if not currency or (per_share and per_share != "shares"):
                    continue
                by_period = defaultdict(list)
                for fact in unit_facts:
                    # SEC companyfacts provides dates, not disclosure times. A
                    # same-day filing is not known at the midnight cutoff; filter
                    # before deduplication so it cannot hide a prior visible fact.
                    if fact.get("filed", "") >= as_of:
                        continue
                    if fact.get("accn") not in labels:
                        continue
                    span = _span_of(fact)
                    if span is None:
                        continue
                    fiscal_year, fiscal_quarter = _fiscal_position(fact, labels[fact["accn"]])
                    if span in ("quarter", "ytd") and (fiscal_year is None or fiscal_quarter is None):
                        continue  # unprovable fiscal position: never guess
                    by_period[(fact.get("start"), fact["end"], span, fiscal_year, fiscal_quarter)].append(fact)
                for (start, end, span, fiscal_year, fiscal_quarter), candidates in by_period.items():
                    # The same period reported with the same value in several
                    # filings (including an 8-K recap) is one identity: take the
                    # latest visible disclosure. Differing values are kept so the
                    # calculator returns ambiguous_filing rather than guessing.
                    if len({str(fact["val"]) for fact in candidates}) == 1:
                        candidates = [max(candidates, key=lambda f: f["filed"])]
                    for fact in candidates:
                        facts.append(
                            FinancialFact(
                                fact_id=f"{cik}:{concept}:{start or 'instant'}:{end}:{fact['accn']}",
                                subject_id=cik,
                                metric=metric,
                                value=Decimal(str(fact["val"])),
                                unit=unit,
                                currency=currency,
                                period_start=date.fromisoformat(start) if start else None,
                                period_end=date.fromisoformat(end),
                                fiscal_year=fiscal_year,
                                fiscal_quarter=fiscal_quarter,
                                span=span,
                                filed_at=date.fromisoformat(fact["filed"]),
                                accession=fact["accn"],
                                filing_ref=f"sec://CIK{cik}/{fact['accn']}",
                                concept=concept,
                                source_ref=f"sec://CIK{cik}/companyfacts#/{concept}/{unit}/{end}",
                                calendar_id=cik,
                                calendar_evidence=(
                                    "fiscal year/period from the carrying filing's declared"
                                    " fy/fp and the covered period's year offset",
                                ),
                                sign_rule="positive_outflow" if metric == "capex" else "as_reported",
                                share_basis="common_shares" if metric == "diluted_eps" else "",
                                basis_evidence=(f"sec://CIK{cik}/companyfacts#/{concept}/{unit}/{end}",)
                                if metric == "diluted_eps"
                                else (),
                                concept_rank=rank,
                                disclosure=tuple(
                                    sorted({k: str(fact[k]) for k in ("fy", "fp", "form", "accn", "filed", "end")
                                            if k in fact}.items())
                                ),
                            )
                        )
    return facts


def _price(ticker, as_of, clock, eps_period_end):
    """Completed close at the fixed cutoff, through the data layer, or a reason."""
    from tradingagents.dataflows.vendors.yahoo.market import completed_close

    row = completed_close(
        ticker, as_of.isoformat(), clock.cutoff, split_floor=eps_period_end.isoformat()
    )
    if row is None:
        return None, "missing_price"
    if not row["currency"] or not row["unit"]:
        return None, "price_currency_unconfirmed"
    if row.get("freshness_status") == "stale_price":
        return None, "stale_price"
    # A latest returned bar is not proof that it is the latest exchange
    # session. Do not self-certify stale vendor data as fresh (FR-10-FC06).
    if not row.get("expected_latest_session") or not row.get("freshness_evidence"):
        return None, "price_availability_unknown"
    basis = "common_shares"
    evidence = [f"yahoo://{ticker}/history-metadata currency={row['currency']}"]
    if row["splits_between"]:
        basis = "split_adjusted_quote_vs_unadjusted_eps"
        evidence.append(f"splits after annual EPS: {row['splits_between']}")
    price_date = date.fromisoformat(row["price_date"])
    return PriceRecord(
        value=Decimal(str(row["value"])),
        currency=row["currency"],
        unit=row["unit"],
        price_date=price_date,
        completed_at=row["completed_at"].astimezone(UTC),
        expected_latest_session=date.fromisoformat(row["expected_latest_session"]),
        freshness_policy=row["freshness_evidence"],
        source_ref=row["source_ref"],
        share_basis=basis,
        basis_evidence=tuple(evidence),
        completion_evidence=f"regular session {price_date.isoformat()} closed 16:00 {row['exchange_timezone']}",
    ), None


class SecCompanyFactsProvider:
    """``FinancialDataProvider`` over the shared SEC companyfacts/submissions cache."""

    def __init__(self, clock):
        self._clock = clock

    def fetch(self, ticker, as_of):
        from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError

        try:
            cik, companyfacts = sec_edgar.company_facts(ticker)
        except NoMarketDataError:
            return FinancialInputs(subject_id=ticker.upper(), issues=("not_supported:not_a_us_sec_filer",))
        except VendorUnavailableError:
            return FinancialInputs(subject_id=ticker.upper(), issues=("data_entry_failure:sec_unavailable",))
        us_gaap = (companyfacts.get("facts") or {}).get("us-gaap") or {}
        if not us_gaap:
            return FinancialInputs(subject_id=cik, issues=("not_supported:no_us_gaap_facts",))
        labels = _filing_labels(us_gaap)
        facts = _facts_for_concept(us_gaap, as_of.isoformat(), labels, cik)
        if not facts:
            return FinancialInputs(subject_id=cik, issues=("not_supported:no_visible_fr07_facts",))
        eps = [f for f in facts if f.metric == "diluted_eps" and f.span == "annual"]
        price, reason = (
            _price(ticker, as_of, self._clock, max(f.period_end for f in eps)) if eps else (None, "missing_input")
        )
        return FinancialInputs(
            subject_id=cik,
            facts=tuple(facts),
            price=price,
            issues=((reason,) if reason else ()),
        )
