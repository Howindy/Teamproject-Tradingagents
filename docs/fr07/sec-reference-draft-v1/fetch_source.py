"""Explicit public-source download only; no TradingAgents imports or LLM calls.

Exclusive writes preserve prior results, including failed HTTP bodies. No retries.
Run one explicit URL at a time; this script is not an application data path.
"""

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def fetch(url, name):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "data.sec.gov", "www.sec.gov", "www.annualreports.com", "investor.apple.com",
        "investor.exxonmobil.com", "query1.finance.yahoo.com", "stooq.com",
    }:
        raise ValueError("unapproved_public_source_host")
    target = ROOT / "sources" / name
    if target.exists():
        raise FileExistsError(target)
    agent = os.environ.get("SEC_EDGAR_USER_AGENT") or "FR07IndependentReference/1.0 (contact@example.com)"
    request = Request(url, headers={"User-Agent": agent, "Accept-Encoding": "identity"})
    at = datetime.now(UTC).isoformat()
    try:
        with urlopen(request, timeout=90) as response:
            data = response.read()
            status = response.status
            headers = {k: response.headers.get(k) for k in ("Content-Type", "Last-Modified", "ETag", "Date")}
            final_url = response.url
    except HTTPError as exc:
        data, status = exc.read(), exc.code
        headers, final_url = {"Content-Type": exc.headers.get("Content-Type")}, exc.url
    if status != 200:
        target = ROOT / "failed_downloads" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(data)
    record = {"url": url, "final_url": final_url, "retrieved_at_utc": at,
              "http_status": status, "saved_file": str(target.relative_to(ROOT)),
              "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
              "response_headers": headers, "method": "urllib GET, no retry, raw body bytes",
              "user_agent_source": "SEC_EDGAR_USER_AGENT" if os.environ.get("SEC_EDGAR_USER_AGENT") else "explicit placeholder contact; not a claimed real contact"}
    with (ROOT / "retrievals.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    print(json.dumps(record, indent=2))
    return status == 200


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("name")
    args = parser.parse_args()
    raise SystemExit(0 if fetch(args.url, args.name) else 1)
