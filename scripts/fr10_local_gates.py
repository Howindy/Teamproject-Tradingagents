"""Local FR-10 report checks, version 1; no network or workflow integration.

Check explicit metric-table assertions against the existing independent oracle.
These bounded checks do not certify every free-form financial claim. Historical
evaluation outputs and the frozen D1-D5 evaluator are deliberately not rewritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from decimal import Decimal
from pathlib import Path

VERSION = "fr10-local-gates-v1"
ROOT = Path(__file__).resolve().parents[1]
ALIASES = {
    "revenue_yoy_q": ("revenue yoy (q)", "revenue yoy (quarter)", "quarterly revenue yoy"),
    "revenue_yoy_a": ("revenue yoy (a)", "revenue yoy (annual)", "annual revenue yoy"),
    "revenue_qoq": ("revenue qoq", "sequential revenue"),
    "gross_margin": ("gross margin",),
    "operating_margin": ("operating margin",),
    "net_margin": ("net margin", "reported net margin"),
    "current_ratio": ("current ratio",),
    "liabilities_to_assets": ("liabilities-to-assets", "liabilities / assets"),
    "fcf_reported_span": ("fcf (reported span)", "reported-span fcf", "free cash flow"),
    "pe_fy": ("p/e (fy)", "fy p/e", "fiscal-year p/e"),
}


def normalize(text: str) -> str:
    return (
        unicodedata.normalize("NFKC", text)
        .replace("−", "-")
        .replace("**", "")
        .replace("`", "")
        .lower()
    )


def table_rows(text: str) -> list[list[str]]:
    return [
        [normalize(cell.strip()) for cell in line.strip().strip("|").split("|")]
        for line in text.splitlines()
        if line.strip().startswith("|")
    ]


def metric_rows(text: str, mid: str) -> list[tuple[str, str]]:
    """Only exact label cells; a gross-profit dollar row is not a margin ratio."""
    result = []
    for cells in table_rows(text):
        for index, cell in enumerate(cells[:-1]):
            if cell in (mid, *ALIASES[mid]):
                value = cells[index + 1]
                if mid.endswith("margin") and "$" in value:
                    continue
                result.append((value, " | ".join(cells[index + 2 :])))
    return result


def numeric_value(cell: str, unit: str) -> Decimal | None:
    """Parse an entire value cell, never accidentally consume dates/source IDs."""
    units = {
        "%": r"(?:%|percent)",
        "x": r"(?:x|times)",
        "USD_millions": r"(?:usd[_ ]millions|m|million(?:s)?(?: usd)?)",
    }
    match = re.fullmatch(r"\s*\$?([+-]?\d[\d,]*(?:\.\d+)?)\s*" + units[unit] + r"\s*", cell)
    return Decimal(match[1].replace(",", "")) if match else None


def report_usable(text: str) -> bool:
    """Same report-completion check for baseline and candidate."""
    lower = normalize(text)
    return len(text.split()) >= 40 and "|" in text and "---" in text and "dsml" not in lower


def score(case: dict, prompts: list[dict], text: str) -> dict:
    """Five small gates for FR-10's injection/values/basis/sources/n-a boundary."""
    checks = dict.fromkeys(
        ("injection", "values", "period_units", "sources", "unavailable_basis"), True
    )
    errors: list[str] = []

    def fail(gate: str, reason: str) -> None:
        checks[gate] = False
        errors.append(reason)

    if not report_usable(text):
        return {
            "case_id": case["case_id"],
            "status": "incomplete",
            "checks": dict.fromkeys(checks, False),
            "errors": ["final_report_not_available"],
            "passed_checks": 0,
        }
    system = "\n".join(m["content"] for m in prompts if m["role"] == "system")
    legend = set(re.findall(r"^\[(S\d+)\]\s+\S+", system, re.M))
    lower = normalize(text)
    for row in case["expected_rows"]:
        mid = row["metric_id"]
        injected = metric_rows(system, mid)
        found = metric_rows(text, mid)
        if len(injected) != 1:
            fail("injection", f"missing_injected_row:{mid}")
        elif row["status"] == "computed":
            if numeric_value(injected[0][0], row["unit"]) != Decimal(row["expected_display"]):
                fail("injection", f"wrong_injected_value:{mid}")
        elif row["reason"] not in injected[0][0] or "n/a" not in injected[0][0]:
            fail("injection", f"wrong_injected_unavailable:{mid}")
        if not found:
            fail("values", f"missing_metric:{mid}")
            continue
        expected_refs = set(re.findall(r"\bs\d+\b", injected[0][1])) if injected else set()
        source_resolved = row["status"] != "computed"
        period_resolved = False
        for value, context in found:
            if row["status"] == "computed":
                if numeric_value(value, row["unit"]) != Decimal(row["expected_display"]):
                    fail("values", f"wrong_or_unparseable_value:{mid}")
                refs = set(re.findall(r"\bs\d+\b", context))
                if refs and (
                    refs != expected_refs or any(ref.upper() not in legend for ref in refs)
                ):
                    fail("sources", f"unresolved_source:{mid}")
                source_resolved |= bool(expected_refs) and refs == expected_refs
            elif "n/a" not in value or row["reason"] not in value + " " + context:
                fail("unavailable_basis", f"invented_or_unexplained_unavailable:{mid}")
            period = row["period"]
            dates = {
                str(period[key]).lower()
                for key in ("period_start", "period_end")
                if period.get(key)
            }
            asserted_dates = set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", context))
            if asserted_dates and not dates.issubset(asserted_dates):
                fail("period_units", f"wrong_period:{mid}")
            explicit_spans = set(re.findall(r"/\s*(quarter|annual|ytd|instant)\b", context))
            if explicit_spans - {period["span"]}:
                fail("period_units", f"wrong_span:{mid}")
            period_resolved |= dates.issubset(asserted_dates) and period["span"] in context
        # A shorter repeated summary need not restate every source/date, but at
        # least one complete assertion must resolve them for each metric.
        if not period_resolved:
            fail("period_units", f"unresolved_period:{mid}")
        if not source_resolved:
            fail("sources", f"unresolved_source:{mid}")

    # Scope negation to the basis phrase: a disclaimer elsewhere cannot excuse an
    # affirmative numeric TTM/quarterly-FCF claim. No broad keyword blacklist.
    for line in lower.splitlines():
        for phrase in (r"ttm\s+p/?e", r"quarterly\s+fcf", r"single-quarter\s+fcf"):
            if re.search(phrase + r"\s*(?:(?:is|=|:)\s*)?\$?[+-]?\d", line):
                fail("unavailable_basis", "unsupported_basis_assertion")
        # Explicit canonical assertions outside tables are also checked. This
        # catches an appended contradiction even if its summary table is right.
        if not line.lstrip().startswith("|"):
            for row in case["expected_rows"]:
                match = re.search(
                    r"\b" + row["metric_id"] + r"\s*(?:is|=|:)\s*([+-]?\d[\d,]*(?:\.\d+)?)", line
                )
                if match and (
                    row["status"] != "computed"
                    or Decimal(match[1].replace(",", "")) != Decimal(row["expected_display"])
                ):
                    fail("values", f"contradictory_prose:{row['metric_id']}")
    unknown_refs = {r.upper() for r in re.findall(r"\bs\d+\b", lower)} - legend
    if unknown_refs:
        fail("sources", "invented_source_alias")
    allowed_accessions = set(re.findall(r"\b\d{10}-\d{2}-\d{6}\b", case["statement_material"]))
    if set(re.findall(r"\b\d{10}-\d{2}-\d{6}\b", text)) - allowed_accessions:
        fail("sources", "invented_accession")
    return {
        "case_id": case["case_id"],
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "errors": sorted(set(errors)),
        "passed_checks": sum(checks.values()),
    }


def replay(evidence: Path) -> dict:
    dataset = json.loads(
        (ROOT / "docs/ci/financial-metrics-cases.json").read_text(encoding="utf-8")
    )
    results = []
    records = []
    for index, case in enumerate(dataset["cases"], 1):
        capture = evidence / f"captures/candidate-{case['case_id']}.json"
        report = evidence / f"reports/{index:02d}-candidate-{case['case_id']}.md"
        prompts = json.loads(capture.read_text(encoding="utf-8"))["prompts"]
        results.append(score(case, prompts, report.read_text(encoding="utf-8")))
        for path in (capture, report):
            records.append(
                {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            )
    baseline = []
    for index, cid in enumerate(("FM-S01", "FM-S02"), 5):
        path = evidence / f"reports/{index:02d}-baseline-{cid}.md"
        baseline.append(
            {"case_id": cid, "report_usable": report_usable(path.read_text(encoding="utf-8"))}
        )
        records.append({"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return {
        "version": VERSION,
        "mode": "offline_replay_of_saved_live_responses",
        "new_model_calls": 0,
        "cases": results,
        "baseline_completion": baseline,
        "inputs": records,
        "formal_acceptance": "not_claimed",
        "limitation": "Bounded table checks; incomplete final-report replays remain unresolved. This is not the frozen D1-D5 run.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--prepare-s04",
        action="store_true",
        help="Capture final-report prompts offline; do not call a model",
    )
    parser.add_argument("--candidate-root", type=Path)
    parser.add_argument("--python-executable")
    args = parser.parse_args()
    if args.prepare_s04:
        from financial_metrics_eval import _run_prompt_capture_subprocess

        if not args.candidate_root or not args.python_executable:
            parser.error("--prepare-s04 requires --candidate-root and --python-executable")
        dataset = json.loads(
            (ROOT / "docs/ci/financial-metrics-cases.json").read_text(encoding="utf-8")
        )
        case = next(case for case in dataset["cases"] if case["case_id"] == "FM-S04")
        capture = _run_prompt_capture_subprocess(
            checkout_root=args.candidate_root,
            mode="candidate",
            case=case,
            reference_data=dataset["reference_data"],
            python_executable=args.python_executable,
            capture_stage="final_report",
        )
        result = {
            "version": VERSION,
            "case_id": "FM-S04",
            "mode": "offline_final_report_preparation",
            "new_model_calls": 0,
            "capture": capture,
            "messages": [
                {
                    "role": {"human": "user", "ai": "assistant"}.get(m["role"], m["role"]),
                    "content": m["content"],
                }
                for m in capture["prompts"]
            ],
            "formal_acceptance": "not_claimed",
        }
    else:
        result = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(
        json.dumps(
            {
                "mode": result["mode"],
                "case_status": result.get("cases", "prepared_without_model_call"),
            },
            indent=2,
        )
    )
