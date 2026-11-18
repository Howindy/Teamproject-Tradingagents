"""Exactly one live DeepSeek request: fundamentals wrap-up with the FR-07 block.

No bull/bear/risk/trader roles, no tools, no retries, thinking disabled. Reads
the API key only from the named dotenv entry; never prints or saves it.
"""

import io
import json
import os
import re
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(r"D:\CityU\cs5351\project\Teamproject-Tradingagents-fr08")
sys.path.insert(0, str(REPO / "TradingAgents"))

from dotenv.parser import parse_stream  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from langchain_core.runnables import Runnable  # noqa: E402

import tradingagents.dataflows.vendors.sec_edgar as sec_edgar  # noqa: E402
from tradingagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst  # noqa: E402
from tradingagents.agents.analysts.turn import WRAP_UP  # noqa: E402
from tradingagents.dataflows.config import set_config  # noqa: E402
from tradingagents.default_config import build_default_config  # noqa: E402
from tradingagents.financials.metrics import calculate_metrics, render_metrics  # noqa: E402
from tradingagents.financials.models import EvaluationClock  # noqa: E402
from tradingagents.financials.sec_provider import SecCompanyFactsProvider  # noqa: E402

OUT = Path(__file__).resolve().parent
MODEL = "deepseek-flash"
ENDPOINT = "https://api.deepseek.com"


def designated_key():
    matches = []
    with Path(r"D:\CityU\cs5351\project\.env").open(encoding="utf-8-sig") as handle:
        for line in handle:
            if re.match(r"^\s*(?:export\s+)?DEEPSEEK_API_KEY\s*=", line):
                bindings = list(parse_stream(io.StringIO(line)))
                if len(bindings) != 1 or bindings[0].error or bindings[0].key != "DEEPSEEK_API_KEY":
                    raise SystemExit("designated credential entry invalid")
                matches.append(bindings[0].value)
    if len(matches) != 1 or not matches[0]:
        raise SystemExit("designated credential missing or ambiguous")
    return matches[0]


def fixed_statement_excerpt():
    """Already-obtained figures, labelled as tool output text (no new fetch)."""
    facts = json.loads((OUT / "msft-companyfacts.json").read_text(encoding="utf-8"))
    gaap = facts["facts"]["us-gaap"]
    wanted = {
        "RevenueFromContractWithCustomerExcludingAssessedTax": "Revenue",
        "GrossProfit": "Gross profit",
        "OperatingIncomeLoss": "Operating income",
        "NetIncomeLoss": "Net income",
        "AssetsCurrent": "Current assets",
        "LiabilitiesCurrent": "Current liabilities",
        "Liabilities": "Total liabilities",
        "Assets": "Total assets",
        "EarningsPerShareDiluted": "Diluted EPS",
        "NetCashProvidedByUsedInOperatingActivities": "Operating cash flow",
        "PaymentsToAcquirePropertyPlantAndEquipment": "Payments for PP&E",
    }
    lines = ["[get_income_statement / get_balance_sheet / get_cashflow returned]",
             "MSFT filings as filed, USD millions unless stated; cumulative XBRL facts:"]
    for concept, label in wanted.items():
        for unit, rows in (gaap.get(concept) or {}).get("units", {}).items():
            for row in rows:
                if row.get("filed", "") > "2025-08-05":
                    continue
                if row.get("end") not in {"2025-03-31", "2025-06-30"}:
                    continue
                if concept in {"AssetsCurrent", "LiabilitiesCurrent", "Liabilities", "Assets"} and "start" in row:
                    continue
                if concept not in {"AssetsCurrent", "LiabilitiesCurrent", "Liabilities", "Assets"} and not row.get("start"):
                    continue
                lines.append(f"- {label} [{unit}] {row.get('start', 'instant')}..{row['end']}: "
                             f"{row['val']} (accession {row['accn']}, filed {row['filed']})")
    return "\n".join(lines)


class OneShotModel(Runnable):
    def __init__(self, client):
        self.client = client
        self.records = []

    def invoke(self, value, config=None, **kwargs):
        from langchain_core.messages import AIMessage

        messages = value.to_messages()
        roles = {"human": "user", "ai": "assistant", "system": "system"}
        payload = [{"role": roles[m.type], "content": m.content} for m in messages]
        started = time.perf_counter()
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=payload,
            temperature=0,
            max_tokens=8192,
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )
        latency = time.perf_counter() - started
        choice = response.choices[0] if response.choices else None
        text = getattr(getattr(choice, "message", None), "content", None)
        usage = response.usage.model_dump() if response.usage else None
        record = {
            "request_index": len(self.records) + 1,
            "model": response.model,
            "response_id": response.id,
            "finish_reason": getattr(choice, "finish_reason", None),
            "usage": usage,
            "reasoning_tokens": ((usage or {}).get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "visible_content_nonempty": isinstance(text, str) and bool(text.strip()),
            "tool_calls_returned": bool(getattr(getattr(choice, "message", None), "tool_calls", None)),
            "latency_seconds": latency,
            "latency_ms": round(latency * 1000, 1),
            "prompt_chars": sum(len(m["content"]) for m in payload),
            "max_tokens": 8192,
            "max_retries": 0,
            "thinking": "disabled",
        }
        (OUT / "live").mkdir(exist_ok=True)
        (OUT / "live" / "provider_metadata.json").write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )
        if isinstance(text, str):
            (OUT / "live" / "raw_response.md").write_text(text, encoding="utf-8")
        self.records.append(record)
        if len(self.records) > 1:
            raise RuntimeError("single-request budget exceeded")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError(f"empty response: {record}")
        return AIMessage(content=text)


def main():
    from openai import OpenAI

    set_config(build_default_config())
    clock = EvaluationClock(
        as_of=date(2025, 8, 5),
        cutoff=datetime(2025, 8, 5, 0, 0, tzinfo=ZoneInfo("America/New_York")),
        today=date.today(),
    )
    source = SecCompanyFactsProvider(clock)
    inputs = source.fetch("MSFT", clock.as_of)
    bundle = calculate_metrics(inputs, clock)
    assert render_metrics(bundle) == json.loads(
        (OUT / "selected_metrics.json").read_text(encoding="utf-8")
    )["rendered_text"], "metric table changed since evidence capture"

    def factory(state):
        return type("R", (), {"text": render_metrics(bundle)})()

    state = {
        "company_of_interest": "MSFT",
        "asset_type": "stock",
        "trade_date": "2025-08-05",
        "instrument_context": "The instrument to analyze is `MSFT`. Preserve this exact ticker.",
        "messages": [
            HumanMessage(content="MSFT"),
            HumanMessage(content=fixed_statement_excerpt()),
            HumanMessage(content=WRAP_UP),
        ],
    }

    client = OpenAI(
        api_key=designated_key(),
        base_url=ENDPOINT,
        max_retries=0,
        timeout=120.0,
    )
    model = OneShotModel(client)
    node = create_fundamentals_analyst(model, metrics_factory=factory)
    result = node(state)

    # Persist the exact prompt facts needed for review, never the credential.
    (OUT / "live" / "statement_material.txt").write_text(fixed_statement_excerpt(), encoding="utf-8")
    (OUT / "live" / "metric_block.txt").write_text(render_metrics(bundle), encoding="utf-8")
    (OUT / "live" / "report.md").write_text(result["fundamentals_report"], encoding="utf-8")
    print(json.dumps(model.records, indent=2))
    print(result["fundamentals_report"][:2000])


if __name__ == "__main__":
    main()
