"""Independent reference preparation from explicitly pinned, saved public sources.

No TradingAgents imports; no general latest-period/filing selector. Every input
is an explicit inline-XBRL element ID in selection_plan.json. This is a review
candidate, NOT an application metric service or a GR-01 approval/freeze.
"""

import argparse
import hashlib
import json
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
METRICS = ("revenue_yoy_q", "revenue_yoy_a", "revenue_qoq", "gross_margin", "operating_margin",
           "net_margin", "current_ratio", "liabilities_to_assets", "fcf_reported_span", "pe_fy")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_or_check(name, value, check):
    target = ROOT / name
    if check:
        if load(target) != value:
            raise AssertionError(f"saved_reference_mismatch:{name}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False, default=str)
            handle.write("\n")


def fixed(value):
    return format(value, "f")


def selected_facts(plan):
    filings, facts = {}, {}
    for stem, spec in plan["filings"].items():
        issuer = spec["issuer"]
        submission = load(ROOT / f"sources/{issuer}-submissions.json")
        assert str(submission["cik"]).zfill(10) == plan["issuers"][issuer]["cik"]
        recent = submission["filings"]["recent"]
        index = recent["accessionNumber"].index(spec["accession"])
        filings[stem] = {
            "accession": spec["accession"], "form": recent["form"][index],
            "filed_at": recent["filingDate"][index], "accepted_at": recent["acceptanceDateTime"][index],
            "report_date": recent["reportDate"][index], "document": f"sources/{stem}.htm",
            "document_sha256": sha(ROOT / f"sources/{stem}.htm"),
            "submissions_pointer": f"/filings/recent/*/{index}",
        }
    for issuer, spec in plan["issuers"].items():
        companyfacts = load(ROOT / f"sources/{issuer}-companyfacts.json")
        assert str(companyfacts["cik"]).zfill(10) == spec["cik"]
        inspections = {stem: load(ROOT / f"inspection/{stem}.inline.json")
                       for stem, filing in plan["filings"].items() if filing["issuer"] == issuer}
        for identifier, stem, element_id, fiscal_year, fiscal_quarter, span, rationale in spec["facts"]:
            inspection = inspections[stem]
            assert inspection["source_sha256"] == filings[stem]["document_sha256"]
            matches = [f for f in inspection["facts"] if f["id"] == element_id]
            assert len(matches) == 1
            node = matches[0]
            context = node["context"]
            assert not context["dimensions"] and context["identifier"].zfill(10) == spec["cik"]
            end = context.get("endDate", context.get("instant"))
            start = context.get("startDate")
            assert filings[stem]["filed_at"] <= plan["as_of_date"]
            amount = Decimal(node["display_text"].replace(",", "").replace(" ", ""))
            amount *= Decimal(10) ** int(node["scale"])
            if node["sign"] == "-":
                amount = -amount
            concept = node["name"].split(":", 1)[1]
            per_share = concept == "EarningsPerShareDiluted"
            unit = "USD/shares" if per_share else "USD"
            assert "iso4217:USD" in node["unit_xml"]
            if per_share:
                assert "shares" in node["unit_xml"] and node["scale"] == "0"
            raw_array = companyfacts["facts"]["us-gaap"][concept]["units"][unit]
            candidates = [(i, f) for i, f in enumerate(raw_array)
                          if f["accn"] == filings[stem]["accession"] and f["end"] == end
                          and f.get("start") == start and Decimal(str(f["val"])) == amount]
            assert len(candidates) == 1, (identifier, candidates)
            source_index, cf = candidates[0]
            assert cf["filed"] == filings[stem]["filed_at"]
            # Fiscal annotations are explicitly pinned in the review plan, NOT
            # copied from cf.fy/fp (which describe the carrying filing).
            facts[identifier] = {
                "fact_id": identifier, "issuer": issuer, "subject_id": spec["cik"],
                "concept": node["name"], "value": fixed(amount), "unit": unit, "currency": "USD",
                "period_start": start, "period_end": end, "span": span,
                "duration_days_inclusive": (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 if start else None,
                "fiscal_year": fiscal_year, "fiscal_quarter": fiscal_quarter,
                "fiscal_annotation_method": "explicit reviewer-readable plan + statement column/calendar evidence; not filing fy/fp copy",
                "selection_rationale": rationale, "filed_at": cf["filed"],
                "accession": cf["accn"], "form": cf["form"], "carrying_filing_fy": cf.get("fy"),
                "carrying_filing_fp": cf.get("fp"), "raw_companyfacts_record": {k: str(v) if isinstance(v, Decimal) else v for k, v in cf.items()},
                "companyfacts_file": f"sources/{issuer}-companyfacts.json",
                "companyfacts_pointer": f"/facts/us-gaap/{concept}/units/{unit.replace('/', '~1')}/{source_index}",
                "filing_file": f"sources/{stem}.htm", "inline_element_id": element_id,
                "inline_context_ref": node["context_ref"], "inline_unit_ref": node["unit_ref"],
                "raw_unit_xml": node["unit_xml"], "raw_display": node["display_text"],
                "raw_scale": node["scale"], "raw_ix_sign": node["sign"],
                "statement_row": node["statement_row"], "restatement_lineage": None,
                "lineage_note": "Pinned to this disclosure; no general latest-version or restatement resolution is inferred.",
            }
    return filings, facts


def price_records(plan):
    records = {}
    for issuer in plan["issuers"]:
        path = ROOT / f"sources/{issuer}-prices-actions.json"
        data = load(path)["chart"]["result"][0]
        meta = data["meta"]
        assert meta["currency"] == "USD" and meta["instrumentType"] == "EQUITY"
        assert meta["symbol"].lower() == issuer
        historical_dates = [datetime.fromtimestamp(t, UTC).astimezone(ZoneInfo("America/New_York")).date().isoformat()
                            for t in data["timestamp"]]
        index = historical_dates.index(plan["price_policy"]["price_date"])
        assert index == len(historical_dates) - 1
        close = data["indicators"]["quote"][0]["close"][index]
        assert isinstance(close, Decimal) and close > 0
        extended_path = ROOT / f"sources/{issuer}-share-basis-through-retrieval.json"
        extended = load(extended_path)["chart"]["result"][0]
        assert not extended.get("events", {}).get("splits", {})
        records[issuer] = {
            "price_id": f"{issuer}.close.2025-08-04", "issuer": issuer,
            "value": fixed(close), "display_only_2dp": fixed(close.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "currency": "USD", "unit": "USD/shares", "actual_price_date": historical_dates[index],
            "price_as_of": plan["as_of_date"], "cutoff": plan["run_clock_cutoff"],
            "timestamp_raw": data["timestamp"][index], "volume": data["indicators"]["quote"][0]["volume"][index],
            "exchange_timezone": meta["exchangeTimezoneName"], "exchange": meta.get("fullExchangeName", meta.get("exchangeName")),
            "source_file": str(path.relative_to(ROOT)),
            "json_pointer": f"/chart/result/0/indicators/quote/0/close/{index}",
            "timestamp_pointer": f"/chart/result/0/timestamp/{index}",
            "adjclose_not_used": str(data["indicators"]["adjclose"][0]["adjclose"][index]),
            "completion_evidence": plan["price_policy"]["completion"],
            "freshness_policy": plan["price_policy"]["freshness"],
            "share_basis_evidence": {"event_snapshot": str(extended_path.relative_to(ROOT)),
                "split_events": {}, "request_covers_eps_end_through_retrieval": True,
                "basis": "common shares, no returned split events across interval; no split/FX conversion"},
            "limitation": "Retrospective daily-history evidence, not an intraday point-in-time quote captured in 2025. Completion/calendar and split-feed adequacy require human review.",
        }
    return records


def arithmetic(a, b, kind):
    with localcontext() as ctx:
        ctx.prec = 60
        x, y = Decimal(a), Decimal(b)
        fx, fy = Fraction(a), Fraction(b)
        if kind == "growth":
            value, fraction = (x / y - 1) * 100, (fx / fy - 1) * 100
        elif kind == "percent":
            value, fraction = x / y * 100, fx / fy * 100
        elif kind == "fcf":
            value, fraction = (x - y) / Decimal(1000000), (fx - fy) / 1000000
        else:
            value, fraction = x / y, fx / fy
        digits = 0 if kind == "fcf" else 1
        display = fixed(value.quantize(Decimal("1") if not digits else Decimal("0.1"), rounding=ROUND_HALF_UP))
        # Exact rational independent half-up cross-check (not binary floats).
        scaled = abs(fraction) * (10 if digits else 1)
        rounded = scaled.numerator // scaled.denominator + int(2 * (scaled.numerator % scaled.denominator) >= scaled.denominator)
        if fraction < 0:
            rounded = -rounded
        expected = str(rounded) if not digits else f"{'-' if rounded < 0 else ''}{abs(rounded)//10}.{abs(rounded)%10}"
        assert display == expected
        return display, str(fraction)


def metrics(facts, prices):
    rows = []
    for issuer, quarter in (("aapl", "q3"), ("xom", "q2")):
        rev = f"{issuer}.rev.{quarter}.2025"
        definitions = [
            ("revenue_yoy_q", rev, f"{issuer}.rev.{quarter}.2024", "growth", "(current/prior_same_fiscal_quarter - 1)*100"),
            ("revenue_yoy_a", f"{issuer}.rev.fy2024", f"{issuer}.rev.fy2023", "growth", "(current_fy/prior_fy - 1)*100"),
            ("revenue_qoq", rev, f"{issuer}.rev.{'q2' if issuer=='aapl' else 'q1'}.2025", "growth", "(current/immediately_preceding_fiscal_quarter - 1)*100"),
            ("gross_margin", f"{issuer}.gross.{quarter}.2025", rev, "percent", "gross_profit/revenue*100"),
            ("operating_margin", f"{issuer}.operating.{quarter}.2025", rev, "percent", "operating_income/revenue*100"),
            ("net_margin", f"{issuer}.net.{quarter}.2025", rev, "percent", "reported_net_income/revenue*100"),
            ("current_ratio", f"{issuer}.current_assets", f"{issuer}.current_liabilities", "ratio", "current_assets/current_liabilities"),
            ("liabilities_to_assets", f"{issuer}.liabilities", f"{issuer}.assets", "percent", "total_liabilities/total_assets*100"),
            ("fcf_reported_span", f"{issuer}.cfo.ytd", f"{issuer}.capex.ytd", "fcf", "operating_cash_flow - positive_reported_PP&E_payments"),
            ("pe_fy", f"{issuer}.price", f"{issuer}.eps.fy2024", "ratio", "completed_close/annual_diluted_eps; NOT TTM"),
        ]
        for metric_id, left, right, kind, formula in definitions:
            a = prices[issuer] if left.endswith(".price") else facts.get(left)
            b = facts.get(right)
            known = [key for key in (left, right) if key in facts]
            period = b if metric_id == "pe_fy" else a or b
            row = {"reference_id": f"{issuer}.{metric_id}", "issuer": issuer, "metric_id": metric_id,
                   "formula_id": metric_id, "formula": formula, "formula_version": "fr07-independent-direct-reference-v1",
                   "input_currency": "USD", "output_currency": "USD" if kind == "fcf" else None,
                   "output_scale": 6 if kind == "fcf" else 0,
                   "rounding": "ROUND_HALF_UP", "resolution": "exact source USD millions" if kind == "fcf" else "0.1 pp" if kind in ("growth", "percent") else "0.1x",
                   "unit": "USD_millions" if kind == "fcf" else "%" if kind in ("growth", "percent") else "x",
                   "input_fact_ids": known, "missing_input_roles": [],
                   "period": {k: period.get(k) for k in ("period_start", "period_end", "fiscal_year", "fiscal_quarter", "span")},
                   "selection_rationales": [facts[key]["selection_rationale"] for key in known],
                   "human_review_status": "pending"}
            if a is None or b is None:
                row.update(status="n/a", reason="missing_input", expected_display="n/a",
                           missing_input_roles=[left if a is None else right],
                           source_absence_evidence="XOM saved target 10-Q and companyfacts do not provide the selected us-gaap GrossProfit/OperatingIncomeLoss concepts; no proxy substituted. Apple supplies positive coverage.")
            else:
                assert a["currency"] == b["currency"] == "USD"
                if metric_id != "pe_fy":
                    assert a["unit"] == b["unit"] == "USD"
                    if metric_id in ("gross_margin", "operating_margin", "net_margin", "fcf_reported_span"):
                        assert a["period_start"] == b["period_start"] and a["period_end"] == b["period_end"] and a["span"] == b["span"]
                else:
                    assert a["unit"] == b["unit"] == "USD/shares"
                    row["price_id"] = a["price_id"]
                display, exact = arithmetic(a["value"], b["value"], kind)
                row.update(status="computed", reason=None, expected_display=display,
                           exact_rational_result=exact, input_values=[a["value"], b["value"]])
            rows.append(row)
    return rows


def counterexamples(facts, prices):
    """Controlled changes are separate from the immutable original sources."""
    specifications = [
        ("wrong_previous_quarter_as_yoy", "aapl.rev.q3.2024", "replace_record", "aapl.rev.q2.2025", "fiscal_period_mismatch", "Prior fiscal-year Q3 cannot be replaced by current-year Q2."),
        ("ytd_as_quarter", "aapl.rev.q3.2025", "replace_record", "aapl.rev.ytd.2025", "missing_quarter", "Same end date does not make nine months into one quarter."),
        ("missing_yoy_comparison", "aapl.rev.q3.2024", "remove_record", None, "missing_comparison", "Preserve current-quarter ref and missing prior-year role; never neighboring column."),
        ("future_disclosure", "xom.rev.q2.2025", "analysis_as_of", "2025-08-03", "future_filing_excluded", "Real filed_at 2025-08-04 exceeds controlled as_of; latest visible Q1 ends 2025-03-31."),
        ("unit_mismatch", "aapl.rev.q3.2024", "unit", "shares", "unit_mismatch", "Change currency amount dimension to shares; no valid unit conversion exists."),
        ("currency_mismatch", "aapl.rev.q3.2024", "currency", "EUR", "currency_mismatch", "Do not invent FX conversion; this override is not a real SEC disclosure."),
        ("price_basis_mismatch", "aapl.price", "adjustment_basis", "unverified_hypothetical_pre_split_basis", "basis_mismatch", "Preserve real close; deliberately remove compatible per-share basis evidence."),
        ("future_price", "aapl.price", "analysis_as_of", "2025-08-03", "future_price_excluded", "2025-08-04 close cannot be used on 2025-08-03; 2025-08-01 is the preceding completed row."),
        ("unknown_capex_sign", "xom.capex.ytd", "raw_sign_rule", "unknown", "unknown_capex_sign", "Source payment-positive rule deliberately removed; do not blindly abs()."),
        ("non_positive_growth_base", "aapl.rev.q3.2024", "value", "0", "non_positive_base", "No numeric growth from a zero base; retain current fact ref."),
        ("non_positive_eps", "xom.eps.fy2024", "value", "-1", "non_positive_eps", "No positive P/E from non-positive annual EPS."),
        ("current_only_without_q4", "xom.rev.q1.2025", "target_fiscal_position", [2025, 1], "missing_quarter", "This controlled input subset has current XOM FY2025 Q1 but no directly reported FY2024 Q4 quarter. Annual-minus-YTD remains forbidden; not a claim that no such fact exists anywhere."),
    ]
    rows = []
    for name, target, operation, after, reason, note in specifications:
        original = prices[target.split(".")[0]] if target.endswith(".price") else facts[target]
        rows.append({"id": name, "base_record_id": target, "base_record": original,
                     "controlled_override": {"operation": operation, "after": after},
                     "is_real_disclosure": False, "expected": {"outcome": "exclude" if reason.endswith("excluded") else "n/a", "reason": reason},
                     "independent_rationale": note,
                     "draft_lineage": "docs/fr07/counterexamples.draft.json; translated to explicitly pinned real source records",
                     "application_test_executed": False})
    return rows


def main(check=False):
    plan = load(ROOT / "selection_plan.json")
    filings, facts = selected_facts(plan)
    prices = price_records(plan)
    rows = metrics(facts, prices)
    coverage = {metric: {"computed": [r["reference_id"] for r in rows if r["metric_id"] == metric and r["status"] == "computed"],
                         "n/a": [r["reference_id"] for r in rows if r["metric_id"] == metric and r["status"] == "n/a"]}
                for metric in METRICS}
    assert all(coverage[m]["computed"] for m in METRICS)
    write_or_check("selected_facts.json", facts, check)
    write_or_check("filing_metadata.json", filings, check)
    write_or_check("price_records.json", prices, check)
    write_or_check("expected_metrics.json", rows, check)
    write_or_check("coverage.json", {"metrics": coverage, "all_ten_have_positive_reference": True,
                                   "controlled_cases_count": 12,
                                   "unfilled_edge_scenarios": ["Real restatement lineage/same-day accession conflict", "Directly reported Q4 positive", "Current-day cutoff unknown availability", "Verified negative-sign capex source positive", "Non-trading-day/unfinished-session service behavior beyond this fixed historical cutoff"],
                                   "human_adequacy_review": "pending; not full FR-07 acceptance"}, check)
    for case in counterexamples(facts, prices):
        write_or_check(f"controlled_variants/{case['id']}.json", case, check)
    if not check:
        lines = ["# Independent reference arithmetic (pending human review)", "", "Ordered operands are USD base units; use the named formula in expected_metrics.json (FCF subtracts, growth divides then subtracts one). FCF displayed in source USD millions. P/E uses full serialized Decimal close.", "", "| Reference | Ordered input operands (not a formula) | Expected | Status |", "|---|---|---|---|"]
        for row in rows:
            values = " ; ".join(row.get("input_values", [])) or row["missing_input_roles"][0]
            lines.append(f"| {row['reference_id']} | {values} | {row['expected_display']} {row['unit']} | {row['status']} |")
        with (ROOT / "metric_table.md").open("x", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    print("CHECK" if check else "BUILT", "facts", len(facts), "metrics", len(rows),
          "computed", sum(r["status"] == "computed" for r in rows), "n/a", sum(r["status"] == "n/a" for r in rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    main(parser.parse_args().check)
