"""One-off evidence capture for the general SEC adapter (MSFT, 2025-08-05).

Reads the public SEC companyfacts through the shared cached path, runs the
existing calculator and saves the selected facts and metric bundle. No model.
"""

import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "TradingAgents"))

from tradingagents.dataflows.config import set_config  # noqa: E402
from tradingagents.dataflows.vendors import sec_edgar  # noqa: E402
from tradingagents.default_config import build_default_config  # noqa: E402
from tradingagents.financials.metrics import calculate_metrics, render_metrics  # noqa: E402
from tradingagents.financials.models import EvaluationClock, json_value  # noqa: E402
from tradingagents.financials.sec_provider import SecCompanyFactsProvider  # noqa: E402

OUT = Path(__file__).resolve().parent
set_config(build_default_config())
CLOCK = EvaluationClock(
    as_of=date(2025, 8, 5),
    cutoff=datetime(2025, 8, 5, 0, 0, tzinfo=ZoneInfo("America/New_York")),
    today=date.today(),
)

ORIGINAL_SHA256 = "11071048a9cf1d23d9804f1a1c18783e8a6d50586e857c1e8a8bcce9081ddad6"
cik, _full = sec_edgar.company_facts("MSFT")
# The committed raw payload is trimmed to the concepts FR-07 reads; the
# untrimmed companyfacts digest above is recorded for audit.
facts = json.loads((OUT / "msft-companyfacts-projection.json").read_text(encoding="utf-8"))
provider = SecCompanyFactsProvider(CLOCK)
inputs = provider.fetch("MSFT", CLOCK.as_of)
bundle = calculate_metrics(inputs, CLOCK)

records = []
for row in bundle.rows:
    by_id = {fact.fact_id: fact for fact in inputs.facts}
    records.append({
        "metric_id": row.metric_id,
        "status": row.status,
        "value": json_value(row.value),
        "display": row.display,
        "reason": row.reason,
        "unit": row.unit,
        "period": dict(row.period),
        "formula": row.formula_id,
        "formula_version": row.formula_version,
        "rounding": row.rounding,
        "input_facts": [
            {
                "fact_id": fid,
                "concept": by_id[fid].concept,
                "value": json_value(by_id[fid].value),
                "span": by_id[fid].span,
                "period_start": json_value(by_id[fid].period_start),
                "period_end": json_value(by_id[fid].period_end),
                "fiscal_year": by_id[fid].fiscal_year,
                "fiscal_quarter": by_id[fid].fiscal_quarter,
                "filed_at": json_value(by_id[fid].filed_at),
                "accession": by_id[fid].accession,
                "carrying_filing_fy": dict(by_id[fid].disclosure).get("fy"),
                "carrying_filing_fp": dict(by_id[fid].disclosure).get("fp"),
            }
            for fid in row.input_fact_ids
        ],
    })

document = {
    "issuer": {"ticker": "MSFT", "cik": cik, "name": "MICROSOFT CORP", "fiscal_year_end": "0630"},
    "as_of": CLOCK.as_of.isoformat(),
    "cutoff": CLOCK.cutoff.isoformat(),
    "source": "SEC companyfacts via tradingagents.dataflows.vendors.sec_edgar",
    "companyfacts_projection_sha256": hashlib.sha256(
        (OUT / "msft-companyfacts-projection.json").read_bytes()
    ).hexdigest(),
    "companyfacts_original_sha256": ORIGINAL_SHA256,
    "price": json_value(asdict(inputs.price)) if inputs.price else None,
    "issues": list(inputs.issues),
    "selected_fact_count": len(inputs.facts),
    "metrics": records,
    "rendered_text": render_metrics(bundle),
}
(OUT / "selected_metrics.json").write_text(
    json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
)

with (OUT / "selected_facts.jsonl").open("w", encoding="utf-8") as handle:
    for fact in sorted(inputs.facts, key=lambda f: (f.metric, f.period_end, str(f.period_start))):
        handle.write(json.dumps(json_value(asdict(fact)), ensure_ascii=False) + "\n")

print(document["rendered_text"])
print()
print("selected facts:", len(inputs.facts), "issues:", inputs.issues)
for row in records:
    spans = {f["span"] for f in row["input_facts"]}
    print(f"{row['metric_id']:<22} {row['display']:>10} {row['unit']:<14} spans={sorted(spans)}")
