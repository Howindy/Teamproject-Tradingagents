from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from types import SimpleNamespace

from baseline_common import (
    BASELINE_ROOT,
    PROJECT_ROOT,
    classify_output,
    count_records,
    now_iso,
    reason_for,
    sha256_file,
    write_csv,
    write_json,
    write_text,
)
import run_baseline as rb


def extract_content(raw: str) -> str:
    if not raw.startswith("content="):
        return raw
    match = re.match(r"^content=(.*) name='[^']*' tool_call_id=", raw, re.S)
    if not match:
        return raw
    try:
        value = ast.literal_eval(match.group(1))
        return value if isinstance(value, str) else str(value)
    except (ValueError, SyntaxError):
        return raw


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            items.append(json.loads(line))
        except ValueError:
            continue
    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args_in = parser.parse_args()
    run_dir = BASELINE_ROOT / "runs" / args_in.run_id
    if not run_dir.exists():
        raise SystemExit(f"run directory does not exist: {run_dir}")

    events = load_jsonl(run_dir / "transcripts" / "tool-events.jsonl")
    starts = {str(event.get("run_id")): event for event in events if event.get("type") == "tool_start"}
    provenance = []
    clean_events = []
    for event in events:
        if event.get("type") != "tool_end":
            clean_events.append(event)
            continue
        raw_path = run_dir / event.get("output_path", "")
        raw = raw_path.read_text(encoding="utf-8", errors="replace") if raw_path.exists() else ""
        clean = extract_content(raw)
        clean_path = run_dir / "transcripts" / "tool-outputs-clean" / f"{event['seq']:04d}_{event['tool']}.txt"
        write_text(clean_path, clean)
        event = dict(event)
        event["raw_output_path"] = event.get("output_path")
        event["clean_output_path"] = str(clean_path.relative_to(run_dir))
        event["output_chars_clean"] = len(clean)
        clean_events.append(event)
        provenance.append({
            "seq": event["seq"],
            "tool": event["tool"],
            "raw_output_path": event["raw_output_path"],
            "clean_output_path": event["clean_output_path"],
            "method": "extracted content field from captured ToolMessage repr",
        })
    write_text(
        run_dir / "transcripts" / "tool-events-clean.jsonl",
        "\n".join(json.dumps(event, ensure_ascii=False, default=str) for event in clean_events) + "\n",
    )
    write_json(run_dir / "transcripts" / "evidence-provenance.json", {
        "generated_at": now_iso(),
        "note": "Raw callback payloads are retained; clean content is extracted for counts and evidence paths.",
        "items": provenance,
    })

    rows = []
    for event in clean_events:
        if event.get("type") != "tool_end":
            continue
        tool = event.get("tool") or "unknown"
        start = starts.get(str(event.get("run_id")), {})
        category, source = rb.TOOL_META.get(tool, ("other", "unknown"))
        clean_path = run_dir / event.get("clean_output_path", "")
        text = clean_path.read_text(encoding="utf-8", errors="replace") if clean_path.exists() else ""
        status = classify_output(text) if text else "no_output"
        rows.append({
            "phase": "run",
            "category": category,
            "tool": tool,
            "source": source,
            "requested_window": rb.parse_time_window(start.get("input", ""), "2026-10-19"),
            "status": status,
            "record_count": count_records(text, status),
            "reason": reason_for(status, text),
            "evidence_path": str(clean_path.relative_to(PROJECT_ROOT)),
            "elapsed_ms": "",
            "notes": "LangChain tool callback; content extracted from ToolMessage repr",
        })

    prefetch = load_jsonl(run_dir / "transcripts" / "prefetch-events.jsonl")
    seen = set()
    for event in prefetch:
        tool = event.get("name") or "unknown"
        seen.add(tool)
        category, source = rb.TOOL_META.get(tool, ("social", "unknown"))
        path = run_dir / event.get("output_path", "")
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        status = classify_output(text) if text else "no_output"
        rows.append({
            "phase": "run",
            "category": category,
            "tool": tool,
            "source": source,
            "requested_window": event.get("window") or "2026-10-19",
            "status": status,
            "record_count": count_records(text, status),
            "reason": reason_for(status, text),
            "evidence_path": str(path.relative_to(PROJECT_ROOT)) if path.exists() else "",
            "elapsed_ms": "",
            "notes": "prefetched into the sentiment analyst prompt",
        })

    called = {row["tool"] for row in rows}
    for category, tool, source in rb.EXPECTED_TOOLS:
        if tool in called:
            continue
        if tool == "get_macro_indicators":
            status = "not_configured"
            reason = "FRED_API_KEY is not set; no call was made"
            notes = ""
        else:
            status = "not_attempted"
            reason = "tool was not called in this run"
            notes = "historical analysis date; live-only odds would be withheld if called" if tool == "get_prediction_markets" else ""
        rows.append({
            "phase": "run",
            "category": category,
            "tool": tool,
            "source": source,
            "requested_window": "2026-10-19",
            "status": status,
            "record_count": 0,
            "reason": reason,
            "evidence_path": "",
            "elapsed_ms": "",
            "notes": notes,
        })

    write_csv(run_dir / "data-availability.csv", rows, rb.FIELDNAMES)
    manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
    metric = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    consistency = json.loads((run_dir / "report-consistency.json").read_text(encoding="utf-8"))
    args = SimpleNamespace(
        run_id=args_in.run_id,
        ticker=manifest.get("ticker", "NVDA"),
        date=manifest.get("analysis_date", "2026-10-19"),
        analysts=",".join(manifest.get("analysts", [])),
        language=manifest.get("language", "English"),
        debate_rounds=manifest.get("debate_rounds", 1),
        risk_rounds=manifest.get("risk_rounds", 1),
    )
    rb.write_run_docs(
        run_dir, args, manifest, metric, rows, consistency,
        metric["source_integrity"], metric["outside_integrity"], metric["home_tradingagents_integrity"],
    )
    summary_path = run_dir / "summary.md"
    summary = summary_path.read_text(encoding="utf-8")
    summary += (
        "\n## Evidence provenance\n\n"
        "- Tool evidence is saved twice: the raw captured `ToolMessage` payload and a clean content-only file.\n"
        "- `data-availability.csv` points at `transcripts/tool-outputs-clean/`; raw files remain under `transcripts/tool-outputs/`.\n"
        "- Sentiment prefetch blocks are raw returns of the app's prefetch functions, not the model's report.\n"
        "- This rebuild did not call any model or rerun the analysis.\n"
    )
    write_text(summary_path, summary)
    manifest["finished_at"] = now_iso()
    manifest["evidence_rebuild"] = {
        "generated_at": now_iso(),
        "method": "extracted content from ToolMessage repr; counts recomputed from clean content",
        "clean_event_log": "transcripts/tool-events-clean.jsonl",
        "provenance": "transcripts/evidence-provenance.json",
    }
    manifest["artifacts"] = rb.artifact_manifest(run_dir)
    write_json(run_dir / "run-manifest.json", manifest)
    print(f"rebuilt {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
