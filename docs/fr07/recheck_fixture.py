"""Independent pre-implementation arithmetic audit, NOT the FR-07 application.

Only explicitly named fixture operands are read. No period/version selection,
normalization, vendor/model call, analyst injection or production module import
is implemented here. Results cannot make GR-01 Stage A pass without published
sources, two non-NVDA issuers and human review. Expected displays below are fixed
review literals, not generated from a future implementation under test.
"""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "docs/req/fixtures/financial_metrics_v1.json"
REQUIREMENTS = REPO / "docs/req/requirements.yaml"

# id, explicit fact IDs, formula shape, independently recorded expected display,
# output unit, existing fixture scenario/key (None means FR-07 FC01/04/05 text).
CASES = (
    ("revenue_yoy_q_2026-07-26", "revenue_q_2026_07_26", "revenue_q_2025_07_27",
     "growth", "105.9", "%", "nvda_latest"),
    ("revenue_yoy_q_2026-04-26", "revenue_q_2026_04_26", "revenue_q_2025_04_27",
     "growth", "85.2", "%", "nvda_q1_yoy"),
    ("revenue_qoq_2026-07-26", "revenue_q_2026_07_26", "revenue_q_2026_04_26",
     "growth", "17.9", "%", "nvda_latest"),
    ("gross_margin_2026-07-26", "gross_profit_q_2026_07_26", "revenue_q_2026_07_26",
     "percentage", "75.0", "%", "nvda_latest"),
    ("operating_margin_2026-07-26", "operating_income_q_2026_07_26", "revenue_q_2026_07_26",
     "percentage", "66.2", "%", "nvda_latest"),
    ("net_margin_2026-07-26", "net_income_q_2026_07_26", "revenue_q_2026_07_26",
     "percentage", "62.0", "%", "nvda_latest"),
    ("revenue_yoy_a", "revenue_a_2026_01_25", "revenue_a_2025_01_26",
     "growth", "65.5", "%", None),
    ("current_ratio", "current_assets_q_2026_07_26", "current_liabilities_q_2026_07_26",
     "ratio", "4.6", "x", "nvda_latest"),
    ("liabilities_to_assets", "total_liabilities_q_2026_07_26", "total_assets_q_2026_07_26",
     "percentage", "28.5", "%", "nvda_latest"),
    ("fcf_reported_ytd_6m", "cfo_ytd_2026_07_26", "capex_ytd_2026_07_26",
     "difference", "69987", "USD_millions", None),
    ("pe_fy_arithmetic_only", "@price", "diluted_eps_a_2026_01_25",
     "ratio", "44.3", "x", None),
    ("restated_revenue_yoy_q", "revenue_q_2026_07_26", "@restated_revenue",
     "growth", "105.6", "%", None),
)


def independent_arithmetic(a: str, b: str, shape: str) -> tuple[str, str, str]:
    """Two independent stdlib arithmetic representations; no application reuse."""
    with localcontext() as context:
        context.prec = 60
        x, y = Decimal(a), Decimal(b)
        rational_x, rational_y = Fraction(a), Fraction(b)
        if shape == "growth":
            value = (x / y - 1) * 100
            rational = (rational_x / rational_y - 1) * 100
            expression = f"({a} / {b} - 1) * 100"
        elif shape == "percentage":
            value = x / y * 100
            rational = rational_x / rational_y * 100
            expression = f"{a} / {b} * 100"
        elif shape == "ratio":
            value = x / y
            rational = rational_x / rational_y
            expression = f"{a} / {b}"
        elif shape == "difference":
            value = x - y
            rational = rational_x - rational_y
            expression = f"{a} - {b}"
        else:
            raise ValueError("unknown_audit_formula")
        resolution = Decimal("1") if shape == "difference" else Decimal("0.1")
        display = format(value.quantize(resolution, rounding=ROUND_HALF_UP), "f")
        # Check half-up independently using exact integer fraction arithmetic.
        scaled = abs(rational) * (1 if shape == "difference" else 10)
        rounded = scaled.numerator // scaled.denominator
        if (scaled.numerator % scaled.denominator) * 2 >= scaled.denominator:
            rounded += 1
        signed = -rounded if rational < 0 else rounded
        exact_display = str(signed) if shape == "difference" else f"{'-' if signed < 0 else ''}{abs(signed) // 10}.{abs(signed) % 10}"
        if display != exact_display:
            raise AssertionError("decimal_and_exact_fraction_rounding_disagree")
        return display, str(rational), expression


def audit(path: Path = FIXTURE) -> dict:
    raw = path.read_bytes()
    fixture = json.loads(raw)
    facts = {fact["fact_id"]: fact for fact in fixture["base_facts"]}
    if len(facts) != len(fixture["base_facts"]):
        raise ValueError("duplicate_fixture_fact_ids")
    scenarios = {scenario["id"]: scenario for scenario in fixture["scenarios"]}
    rows = []
    for metric, numerator, denominator, shape, expected, unit, scenario in CASES:
        a = fixture["price"] if numerator == "@price" else facts[numerator]["value"]
        if denominator == "@restated_revenue":
            b = scenarios["restatement"]["add"][0]["value"]
        else:
            b = facts[denominator]["value"]
        display, rational, expression = independent_arithmetic(a, b, shape)
        existing = scenarios[scenario]["expected"][metric] if scenario else None
        refs = [
            {"fixture_pointer": f"/base_facts/{fixture['base_facts'].index(facts[fact_id])}",
             "fact": facts[fact_id]}
            for fact_id in (numerator, denominator) if not fact_id.startswith("@")
        ]
        if numerator == "@price":
            refs.append({"fixture_pointer": "/price", "value": fixture["price"],
                         "warning": "Completion, freshness policy and EPS-compatible basis not established."})
        if denominator == "@restated_revenue":
            refs.append({"scenario": "restatement", "fact": scenarios["restatement"]["add"][0]})
        rows.append({
            "audit_case": metric, "formula": expression, "exact_rational_result": rational,
            "rounding": "ROUND_HALF_UP", "resolution": "1 source unit" if shape == "difference" else "0.1",
            "unit": unit, "independently_recorded_expected_display": expected,
            "arithmetic_display": display, "arithmetic_matches_expected": display == expected,
            "existing_fixture_expected": existing,
            "existing_fixture_matches": existing is None or existing == display,
            "input_locators": refs,
            "published_fact_verification": "not_established",
            "production_metric_status": "not_computed; pre-implementation arithmetic audit only",
        })
    return {
        "audit_version": "fr07-stage-a-preparation-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "fixture": str(path), "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "requirements_sha256": hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest(),
        "rows": rows,
        "arithmetic_pass": all(row["arithmetic_matches_expected"] and row["existing_fixture_matches"] for row in rows),
        "stage_a": "BLOCKED", "human_review": "pending",
        "application_implementation_started": False,
        "stage_a_blockers": [
            "No actual complete independently reviewed frozen reference manifest found.",
            "At least two distinct non-NVDA issuers and evidenced fiscal calendars are absent.",
            "Per-value published source snapshots/locators/content hashes and independent derivations are absent.",
            "Metric/period/negative-case coverage adequacy lacks human review.",
            "Freeze version/time/content digest and reviewer record are absent.",
        ],
        "fixture_issues": [
            "All diluted_eps rows declare USD_millions rather than a verified currency-per-share unit; do not silently repair.",
            "Positive and negative capex cases lack source sign conventions; negative value alone cannot authorize abs().",
            "Price freshness policy is provisional_fixture_only; completion, cutoff and EPS-compatible basis are not established.",
            "Filing locators are fixture identifiers, not reviewed published filing snapshots with content digests.",
            "Issuer-calendar comparability evidence and per-fact normalization/lineage rules are incomplete.",
            "Several current-scope price/unit/source negatives exist only inside deferred TTM scenarios.",
        ],
        "limitation": "Matching arithmetic validates fixture numbers only, not real filings, selection, injection, recovery or FR-07 acceptance.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.fixture)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(text)
    else:
        print(text, end="")
    # Success here is arithmetic only. Stage A remains explicitly blocked.
    return 0 if result["arithmetic_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
