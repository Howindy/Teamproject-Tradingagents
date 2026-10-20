from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

from baseline_common import (
    BASELINE_ROOT,
    MODULE_CHECK_CODE,
    PROJECT_ROOT,
    REPO_ROOT,
    classify_output,
    compare_snapshots,
    count_records,
    dependency_report,
    ensure_new_dir,
    env_summary,
    find_files,
    monotonic,
    now_iso,
    preview,
    reason_for,
    sha256_file,
    snapshot_project_outside_allowed,
    snapshot_tree,
    validate_id,
    write_csv,
    write_json,
    write_text,
)

FIELDNAMES = [
    "phase",
    "category",
    "tool",
    "source",
    "requested_window",
    "status",
    "record_count",
    "reason",
    "evidence_path",
    "elapsed_ms",
    "notes",
]

TOOL_META = {
    "get_stock_data": ("market", "Yahoo Finance"),
    "get_indicators": ("technical", "Yahoo Finance"),
    "get_verified_market_snapshot": ("market", "Yahoo Finance"),
    "get_fundamentals": ("fundamentals", "Yahoo Finance"),
    "get_balance_sheet": ("fundamentals", "SEC EDGAR, Yahoo Finance"),
    "get_cashflow": ("fundamentals", "SEC EDGAR, Yahoo Finance"),
    "get_income_statement": ("fundamentals", "SEC EDGAR, Yahoo Finance"),
    "get_insider_transactions": ("fundamentals", "Yahoo Finance"),
    "get_news": ("news", "Yahoo Finance"),
    "get_global_news": ("news", "Yahoo Finance"),
    "get_macro_indicators": ("macro", "FRED"),
    "get_prediction_markets": ("prediction", "Polymarket"),
    "sentiment_news": ("social", "Yahoo Finance (prefetch)"),
    "sentiment_stocktwits": ("social", "StockTwits (prefetch)"),
    "sentiment_reddit": ("social", "Reddit (prefetch)"),
}

EXPECTED_TOOLS = [
    ("market", "get_stock_data", "Yahoo Finance"),
    ("technical", "get_indicators", "Yahoo Finance"),
    ("market", "get_verified_market_snapshot", "Yahoo Finance"),
    ("fundamentals", "get_fundamentals", "Yahoo Finance"),
    ("fundamentals", "get_balance_sheet", "SEC EDGAR, Yahoo Finance"),
    ("fundamentals", "get_cashflow", "SEC EDGAR, Yahoo Finance"),
    ("fundamentals", "get_income_statement", "SEC EDGAR, Yahoo Finance"),
    ("fundamentals", "get_insider_transactions", "Yahoo Finance"),
    ("news", "get_news", "Yahoo Finance"),
    ("news", "get_global_news", "Yahoo Finance"),
    ("macro", "get_macro_indicators", "FRED"),
    ("prediction", "get_prediction_markets", "Polymarket"),
    ("social", "sentiment_news", "Yahoo Finance (prefetch)"),
    ("social", "sentiment_stocktwits", "StockTwits (prefetch)"),
    ("social", "sentiment_reddit", "Reddit (prefetch)"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ticker", default="NVDA")
    parser.add_argument("--date", default="2026-10-19")
    parser.add_argument("--analysts", default="market,social,news,fundamentals")
    parser.add_argument("--language", default="English")
    parser.add_argument("--debate-rounds", type=int, default=1)
    parser.add_argument("--risk-rounds", type=int, default=1)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--inner", action="store_true")
    return parser.parse_args()


def build_child_env(run_dir: Path, args: argparse.Namespace) -> dict:
    env = os.environ.copy()
    previous = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(REPO_ROOT) + (os.pathsep + previous if previous else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["TRADINGAGENTS_RESULTS_DIR"] = str(run_dir / "results")
    env["TRADINGAGENTS_CACHE_DIR"] = str(run_dir / "cache")
    env["TRADINGAGENTS_MEMORY_LOG_PATH"] = str(run_dir / "memory" / "trading_memory.md")
    env["TRADINGAGENTS_CHECKPOINT_ENABLED"] = "false"
    env["TRADINGAGENTS_OUTPUT_LANGUAGE"] = args.language
    env["TRADINGAGENTS_MAX_DEBATE_ROUNDS"] = str(args.debate_rounds)
    env["TRADINGAGENTS_MAX_RISK_ROUNDS"] = str(args.risk_rounds)
    env["TRADINGAGENTS_NO_UPDATE_CHECK"] = "1"
    env["HOME"] = str(run_dir / "tmp" / "home")
    env["TMPDIR"] = str(run_dir / "tmp")
    env["XDG_CACHE_HOME"] = str(run_dir / "tmp" / "xdg-cache")
    env["XDG_CONFIG_HOME"] = str(run_dir / "tmp" / "xdg-config")
    env["XDG_DATA_HOME"] = str(run_dir / "tmp" / "xdg-data")
    env["CI"] = "1"
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    return env


def module_check(env: dict, run_dir: Path) -> dict:
    result = subprocess.run(
        [sys.executable, "-B", "-c", MODULE_CHECK_CODE],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    write_text(run_dir / "logs" / "module-check.stdout.txt", result.stdout)
    write_text(run_dir / "logs" / "module-check.stderr.txt", result.stderr)
    parsed = None
    for line in reversed(result.stdout.splitlines()):
        try:
            parsed = json.loads(line)
            break
        except ValueError:
            continue
    return {
        "returncode": result.returncode,
        "parsed": parsed,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def run_orchestrator(args: argparse.Namespace) -> int:
    run_id = validate_id(args.run_id, "run-id")
    ticker = args.ticker.strip().upper()
    analysts = [item.strip() for item in args.analysts.split(",") if item.strip()]
    run_dir = BASELINE_ROOT / "runs" / run_id
    ensure_new_dir(run_dir)
    for name in ("logs", "results", "cache", "memory", "tmp", "transcripts",
                 "transcripts/tool-outputs", "transcripts/prefetch"):
        (run_dir / name).mkdir(parents=True, exist_ok=True)
    (run_dir / "tmp" / "home").mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable, "-B", "-u", str(Path(__file__).resolve()),
        "--inner",
        "--run-id", run_id,
        "--ticker", ticker,
        "--date", args.date,
        "--analysts", ",".join(analysts),
        "--language", args.language,
        "--debate-rounds", str(args.debate_rounds),
        "--risk-rounds", str(args.risk_rounds),
        "--project-root", str(PROJECT_ROOT),
    ]
    child_env = build_child_env(run_dir, args)
    source_before = snapshot_tree(REPO_ROOT)
    outside_before = snapshot_project_outside_allowed(PROJECT_ROOT)
    real_home = Path(os.environ.get("HOME", str(Path.home()))).expanduser()
    home_before = snapshot_tree(real_home / ".tradingagents")
    write_json(run_dir / "source-before.json", source_before)
    write_json(run_dir / "outside-before.json", outside_before)
    write_json(run_dir / "home-tradingagents-before.json", home_before)

    env_info = env_summary(child_env)
    env_info["dependencies"] = dependency_report()
    env_info["command"] = command
    env_info["cwd"] = str(REPO_ROOT)
    env_info["project_root"] = str(PROJECT_ROOT)
    env_info["python_runtime"] = {
        "executable": sys.executable,
        "version": sys.version,
        "platform": sys.platform,
    }
    check = module_check(child_env, run_dir)
    env_info["module_check"] = check
    write_json(run_dir / "environment.json", env_info)
    write_text(run_dir / "environment.txt", json.dumps(env_info, indent=2, ensure_ascii=False, default=str) + "\n")

    parsed = (check.get("parsed") or {})
    expected_file = str((REPO_ROOT / "tradingagents" / "__init__.py").resolve())
    if check.get("returncode") != 0 or parsed.get("tradingagents_file") != expected_file:
        finish_without_run(run_dir, args, command, source_before, outside_before, home_before, check)
        return 3

    manifest = {
        "run_id": run_id,
        "ticker": ticker,
        "analysis_date": args.date,
        "analysts": analysts,
        "language": args.language,
        "debate_rounds": args.debate_rounds,
        "risk_rounds": args.risk_rounds,
        "started_at": now_iso(),
        "started_monotonic": monotonic(),
        "command": command,
        "cwd": str(REPO_ROOT),
        "environment": env_info,
        "paths": {
            "results": str(run_dir / "results"),
            "cache": str(run_dir / "cache"),
            "memory": str(run_dir / "memory"),
            "home": str(run_dir / "tmp" / "home"),
            "tmp": str(run_dir / "tmp"),
        },
    }
    write_json(run_dir / "run-manifest.json", manifest)

    stdout_path = run_dir / "logs" / "stdout.log"
    stderr_path = run_dir / "logs" / "stderr.log"
    t0 = monotonic()
    with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
        proc = subprocess.Popen(
            command,
            cwd=str(REPO_ROOT),
            env=child_env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=subprocess.DEVNULL,
        )
        exit_code = proc.wait()
    total_elapsed = monotonic() - t0
    write_text(run_dir / "logs" / "exit-code.txt", f"{exit_code}\n")

    source_after = snapshot_tree(REPO_ROOT)
    outside_after = snapshot_project_outside_allowed(PROJECT_ROOT)
    home_after = snapshot_tree(real_home / ".tradingagents")
    source_integrity = compare_snapshots(source_before, source_after)
    outside_integrity = compare_snapshots(outside_before, outside_after)
    home_integrity = compare_snapshots(home_before, home_after)
    write_json(run_dir / "source-after.json", source_after)
    write_json(run_dir / "source-integrity.json", source_integrity)
    write_json(run_dir / "outside-after.json", outside_after)
    write_json(run_dir / "outside-integrity.json", outside_integrity)
    write_json(run_dir / "home-tradingagents-after.json", home_after)
    write_json(run_dir / "home-tradingagents-integrity.json", home_integrity)

    inner_metrics = json.loads((run_dir / "metrics-inner.json").read_text(encoding="utf-8")) \
        if (run_dir / "metrics-inner.json").exists() else {}
    data_rows = build_formal_rows(run_dir, ticker, args.date)
    write_csv(run_dir / "data-availability.csv", data_rows, FIELDNAMES)
    metric = build_metrics(run_dir, inner_metrics, exit_code, total_elapsed, source_integrity,
                           outside_integrity, home_integrity)
    write_json(run_dir / "metrics.json", metric)
    consistency = build_consistency(run_dir)
    write_json(run_dir / "report-consistency.json", consistency)
    write_run_docs(run_dir, args, manifest, metric, data_rows, consistency,
                   source_integrity, outside_integrity, home_integrity)

    manifest.update({
        "finished_at": now_iso(),
        "elapsed_monotonic_seconds": round(total_elapsed, 3),
        "exit_code": exit_code,
        "source_integrity": source_integrity,
        "outside_integrity": outside_integrity,
        "home_tradingagents_integrity": home_integrity,
        "artifacts": artifact_manifest(run_dir),
    })
    write_json(run_dir / "run-manifest.json", manifest)

    if not source_integrity.get("identical") or not outside_integrity.get("identical") or not home_integrity.get("identical"):
        return 4
    return exit_code


def finish_without_run(run_dir, args, command, source_before, outside_before, home_before, check):
    source_after = snapshot_tree(REPO_ROOT)
    outside_after = snapshot_project_outside_allowed(PROJECT_ROOT)
    real_home = Path(os.environ.get("HOME", str(Path.home()))).expanduser()
    home_after = snapshot_tree(real_home / ".tradingagents")
    source_integrity = compare_snapshots(source_before, source_after)
    outside_integrity = compare_snapshots(outside_before, outside_after)
    home_integrity = compare_snapshots(home_before, home_after)
    write_json(run_dir / "source-after.json", source_after)
    write_json(run_dir / "source-integrity.json", source_integrity)
    write_json(run_dir / "outside-after.json", outside_after)
    write_json(run_dir / "outside-integrity.json", outside_integrity)
    write_json(run_dir / "home-tradingagents-after.json", home_after)
    write_json(run_dir / "home-tradingagents-integrity.json", home_integrity)
    write_text(run_dir / "logs" / "exit-code.txt", "3\n")
    write_json(run_dir / "run-manifest.json", {
        "run_id": args.run_id,
        "ticker": args.ticker,
        "analysis_date": args.date,
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "exit_code": 3,
        "command": command,
        "cwd": str(REPO_ROOT),
        "error": "module check failed; formal run was not started",
        "module_check": check,
        "source_integrity": source_integrity,
        "outside_integrity": outside_integrity,
        "home_tradingagents_integrity": home_integrity,
        "artifacts": artifact_manifest(run_dir),
    })
    write_text(run_dir / "summary.md", "# Baseline not started\n\nThe module check failed, so no model was called.\n")
    write_text(run_dir / "README.md", "# Baseline run\n\nFormal run was not started because the module check failed.\n")


def parse_time_window(input_text: str, default: str) -> str:
    try:
        data = json.loads(input_text)
    except (ValueError, TypeError):
        return default
    if not isinstance(data, dict):
        return default
    if data.get("start_date") and data.get("end_date"):
        return f"{data['start_date']}..{data['end_date']}"
    for key in ("as_of_date", "curr_date", "trade_date"):
        if data.get(key):
            return f"as of {data[key]}"
    return default


def build_formal_rows(run_dir: Path, ticker: str, analysis_date: str) -> list[dict]:
    rows: list[dict] = []
    events_path = run_dir / "transcripts" / "tool-events.jsonl"
    events = []
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    starts = {}
    for event in events:
        if event.get("type") == "tool_start":
            starts[str(event.get("run_id"))] = event
    for event in events:
        if event.get("type") != "tool_end":
            continue
        tool = event.get("tool") or "unknown"
        start = starts.get(str(event.get("run_id")), {})
        category, source = TOOL_META.get(tool, ("other", "unknown"))
        output_path = event.get("output_path")
        text = ""
        evidence = ""
        if output_path:
            path = run_dir / output_path
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")
                evidence = path.relative_to(PROJECT_ROOT).as_posix()
        status = classify_output(text) if text else "no_output"
        rows.append({
            "phase": "run",
            "category": category,
            "tool": tool,
            "source": source,
            "requested_window": parse_time_window(start.get("input", ""), analysis_date),
            "status": status,
            "record_count": count_records(text, status),
            "reason": reason_for(status, text),
            "evidence_path": evidence,
            "elapsed_ms": "",
            "notes": "LangChain tool callback",
        })

    prefetch_path = run_dir / "transcripts" / "prefetch-events.jsonl"
    prefetch_events = []
    if prefetch_path.exists():
        for line in prefetch_path.read_text(encoding="utf-8").splitlines():
            try:
                prefetch_events.append(json.loads(line))
            except ValueError:
                continue
    seen = set()
    for event in prefetch_events:
        tool = event.get("name") or "unknown"
        seen.add(tool)
        category, source = TOOL_META.get(tool, ("social", "unknown"))
        output_path = event.get("output_path")
        text = ""
        evidence = ""
        if output_path:
            path = run_dir / output_path
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")
                evidence = path.relative_to(PROJECT_ROOT).as_posix()
        status = classify_output(text) if text else "no_output"
        rows.append({
            "phase": "run",
            "category": category,
            "tool": tool,
            "source": source,
            "requested_window": event.get("window") or analysis_date,
            "status": status,
            "record_count": count_records(text, status),
            "reason": reason_for(status, text),
            "evidence_path": evidence,
            "elapsed_ms": "",
            "notes": "prefetched into the sentiment analyst prompt",
        })

    called = {row["tool"] for row in rows}
    for category, tool, source in EXPECTED_TOOLS:
        if tool in called:
            continue
        if tool == "get_macro_indicators" and not os.environ.get("FRED_API_KEY"):
            status = "not_configured"
            reason = "FRED_API_KEY is not set; no call was made"
        else:
            status = "not_attempted"
            reason = "tool was not called in this run"
        notes = ""
        if tool == "get_prediction_markets":
            notes = "historical analysis date; live-only odds would be withheld if called"
        rows.append({
            "phase": "run",
            "category": category,
            "tool": tool,
            "source": source,
            "requested_window": analysis_date,
            "status": status,
            "record_count": 0,
            "reason": reason,
            "evidence_path": "",
            "elapsed_ms": "",
            "notes": notes,
        })
    return rows


def build_metrics(run_dir, inner, exit_code, total_elapsed, source_integrity,
                  outside_integrity, home_integrity) -> dict:
    stdout_path = run_dir / "logs" / "stdout.log"
    stderr_path = run_dir / "logs" / "stderr.log"
    app_log = run_dir / "logs" / "app.log"
    message_log = list((run_dir / "results").rglob("message_tool.log"))
    message_lines = 0
    if message_log:
        message_lines = len(message_log[0].read_text(encoding="utf-8", errors="replace").splitlines())
    warnings = ""
    for path in (stderr_path, app_log):
        if path.exists():
            warnings += path.read_text(encoding="utf-8", errors="replace")
    structured_fallback = sum(
        1 for line in warnings.splitlines()
        if "structured-output invocation failed" in line or "falling back to free-text" in line
    )
    return {
        "run_id": run_dir.name,
        "measurement_scope": "inner: run_analysis wall-clock, monotonic; total: child process wall-clock, monotonic",
        "exit_code": exit_code,
        "inner": inner,
        "total_elapsed_monotonic_seconds": round(total_elapsed, 3),
        "llm_calls": inner.get("llm_calls"),
        "tool_calls": inner.get("tool_calls"),
        "tokens_in": inner.get("tokens_in"),
        "tokens_out": inner.get("tokens_out"),
        "llm_usage_missing": inner.get("llm_usage_missing"),
        "retry_events": inner.get("retry_events"),
        "llm_error_events": inner.get("llm_error_events"),
        "tool_error_events": inner.get("tool_error_events"),
        "structured_fallback_warnings": structured_fallback,
        "message_tool_log_lines": message_lines,
        "monetary_cost": None,
        "monetary_cost_reason": "no CityU per-token price was provided; token counts are the available cost proxy",
        "ui_rounded_estimate": None,
        "stdout_bytes": stdout_path.stat().st_size if stdout_path.exists() else None,
        "stderr_bytes": stderr_path.stat().st_size if stderr_path.exists() else None,
        "source_integrity": source_integrity,
        "outside_integrity": outside_integrity,
        "home_tradingagents_integrity": home_integrity,
    }


def build_consistency(run_dir: Path) -> dict:
    final_state_path = run_dir / "transcripts" / "final_state.json"
    final_status_path = run_dir / "transcripts" / "final-status.json"
    final_state = json.loads(final_state_path.read_text(encoding="utf-8")) if final_state_path.exists() else {}
    final_status = json.loads(final_status_path.read_text(encoding="utf-8")) if final_status_path.exists() else {}
    complete_reports = find_files(run_dir / "results", "complete_report.md")
    logs = find_files(run_dir / "results", "full_states_log_*.json")
    full_log = json.loads(logs[-1].read_text(encoding="utf-8")) if logs else {}
    report_text = complete_reports[-1].read_text(encoding="utf-8", errors="replace") if complete_reports else ""
    final_decision = final_state.get("final_trade_decision") or full_log.get("final_trade_decision") or ""
    final_rating = final_status.get("final_rating") or full_log.get("final_rating")
    section_files = []
    for pattern in ("1_analysts/*.md", "2_research/*.md", "3_trading/*.md", "4_risk/*.md", "5_portfolio/*.md"):
        section_files.extend(find_files(run_dir / "results", pattern))
    nonempty_sections = [str(path) for path in section_files if path.stat().st_size > 0]
    return {
        "final_state_exists": final_state_path.exists(),
        "final_status_exists": final_status_path.exists(),
        "complete_report_found": bool(complete_reports),
        "complete_report_path": str(complete_reports[-1].relative_to(PROJECT_ROOT)) if complete_reports else None,
        "full_states_log_found": bool(logs),
        "full_states_log_path": str(logs[-1].relative_to(PROJECT_ROOT)) if logs else None,
        "final_decision_nonempty": bool(final_decision.strip()),
        "final_rating": final_rating,
        "final_decision_matches_full_log": bool(final_decision and final_decision == (full_log.get("final_trade_decision") or "")),
        "complete_report_contains_decision": bool(final_decision and final_decision.strip() in report_text),
        "rating_matches_full_log": bool(final_rating and final_rating == full_log.get("final_rating")),
        "section_file_count": len(section_files),
        "nonempty_section_files": len(nonempty_sections),
        "section_files": [str(path.relative_to(PROJECT_ROOT)) for path in section_files],
    }


def status_counts(rows: list[dict]) -> dict:
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts


def write_run_docs(run_dir, args, manifest, metric, rows, consistency,
                   source_integrity, outside_integrity, home_integrity):
    counts = status_counts(rows)
    non_success = [row for row in rows if row["status"] != "success"]
    coverage_complete = not any(
        row["status"] in {"unavailable", "no_output", "not_configured", "withheld"} for row in rows
    )
    main_complete = (
        metric.get("exit_code") == 0
        and consistency.get("final_state_exists")
        and consistency.get("final_decision_nonempty")
        and consistency.get("complete_report_found")
    )
    lines = [
        f"# Baseline run {args.run_id}",
        "",
        f"- Ticker: {args.ticker.upper()}",
        f"- Analysis date: {args.date}",
        f"- Analysts: {', '.join(args.analysts.split(','))}",
        f"- Language: {args.language}",
        f"- Debate rounds: {args.debate_rounds}; risk rounds: {args.risk_rounds}",
        f"- Exit code: {metric.get('exit_code')}",
        f"- Total elapsed (monotonic): {metric.get('total_elapsed_monotonic_seconds')}s",
        f"- Main flow completed: {'yes' if main_complete else 'no'}",
        f"- Data coverage complete: {'yes' if coverage_complete else 'no'}",
        f"- Source integrity: {'identical' if source_integrity.get('identical') else 'MISMATCH'}",
        f"- Outside-scope integrity: {'identical' if outside_integrity.get('identical') else 'MISMATCH'}",
        f"- Home .tradingagents integrity: {'identical' if home_integrity.get('identical') else 'MISMATCH'}",
        "",
        "## Metrics",
        "",
        f"- LLM calls: {metric.get('llm_calls')}",
        f"- Tool calls: {metric.get('tool_calls')}",
        f"- Tokens in/out: {metric.get('tokens_in')} / {metric.get('tokens_out')}",
        f"- LLM usage missing: {metric.get('llm_usage_missing')}",
        f"- Retry events: {metric.get('retry_events')}",
        f"- LLM errors: {metric.get('llm_error_events')}; tool errors: {metric.get('tool_error_events')}",
        f"- Structured fallback warnings: {metric.get('structured_fallback_warnings')}",
        f"- Monetary cost: null ({metric.get('monetary_cost_reason')})",
        "",
        "## Data availability",
        "",
        f"- Status counts: {json.dumps(counts, ensure_ascii=False)}",
    ]
    for row in non_success:
        lines.append(
            f"- {row['category']} / {row['tool']} ({row['source']}): {row['status']} — {row['reason']}"
        )
    lines.extend([
        "",
        "## Report consistency",
        "",
        f"- Final state captured: {consistency.get('final_state_exists')}",
        f"- Final decision nonempty: {consistency.get('final_decision_nonempty')}",
        f"- Complete report found: {consistency.get('complete_report_found')}",
        f"- Decision matches full state log: {consistency.get('final_decision_matches_full_log')}",
        f"- Complete report contains decision: {consistency.get('complete_report_contains_decision')}",
        f"- Rating matches full state log: {consistency.get('rating_matches_full_log')}",
        f"- Section files: {consistency.get('nonempty_section_files')}/{consistency.get('section_file_count')} nonempty",
        "",
        "## Reproducibility",
        "",
        f"- Command: `{' '.join(manifest.get('command', []))}`",
        f"- Working directory: {manifest.get('cwd')}",
        f"- Module path: {(manifest.get('environment', {}).get('module_check', {}).get('parsed', {}) or {}).get('tradingagents_file')}",
        f"- Python: {(manifest.get('environment', {}).get('module_check', {}).get('parsed', {}) or {}).get('sys_executable')}",
        f"- Commit recorded separately in environment.json.",
        "",
        "## Limitations",
        "",
        "- FRED_API_KEY was not set, so macro data is unavailable unless the run did not request it.",
        "- 2026-10-19 is historical: live-only Polymarket odds and live company/insider/profile data are withheld by the application.",
        "- StockTwits and Reddit serve recent items and may not cover the full historical window; an unavailable sentinel is not proof of silence.",
        "- Some installed packages are below the versions declared in pyproject.toml; this is recorded in environment.json.",
        f"- A generated trading decision alone does not make this baseline complete; main_flow={main_complete}, data_coverage_complete={coverage_complete}.",
        "",
    ])
    write_text(run_dir / "summary.md", "\n".join(lines) + "\n")

    readme = [
        f"# {args.run_id}",
        "",
        "Single TradingAgents baseline run. The application source was not modified.",
        "",
        "## Command",
        "",
        "```text",
        " ".join(manifest.get("command", [])),
        "```",
        "",
        "## Layout",
        "",
        "- `logs/`: stdout, stderr, exit code, module check, application warnings.",
        "- `results/`: application reports and full state log.",
        "- `cache/`: run-local data cache (started empty).",
        "- `memory/`: run-local memory log (started empty).",
        "- `transcripts/`: final state, tool events, raw sentiment prefetch blocks.",
        "- `tmp/`: redirected HOME/XDG/TMPDIR.",
        "- `source-*.json`, `outside-*.json`, `home-tradingagents-*.json`: integrity evidence.",
        "- `metrics.json`, `data-availability.csv`, `report-consistency.json`, `summary.md`.",
        "",
        "## Notes",
        "",
        f"- Exit code: {metric.get('exit_code')}",
        f"- Main flow completed: {'yes' if main_complete else 'no'}",
        f"- Data coverage complete: {'yes' if coverage_complete else 'no'}",
    ]
    write_text(run_dir / "README.md", "\n".join(readme) + "\n")


def artifact_manifest(run_dir: Path) -> list[dict]:
    artifacts = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "run-manifest.json":
            continue
        artifacts.append({
            "path": str(path.relative_to(run_dir)),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return artifacts


def run_inner(args: argparse.Namespace) -> int:
    run_dir = BASELINE_ROOT / "runs" / args.run_id
    if not run_dir.exists():
        raise SystemExit(f"run directory does not exist: {run_dir}")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(REPO_ROOT))
    os.chdir(REPO_ROOT)

    import tradingagents
    expected = (REPO_ROOT / "tradingagents" / "__init__.py").resolve()
    if Path(tradingagents.__file__).resolve() != expected:
        raise SystemExit(f"refusing to run: loaded {tradingagents.__file__} instead of {expected}")

    from langchain_core.outputs import LLMResult
    from tradingagents.agents.rating import run_rating
    from tradingagents.agents.analysts import sentiment_analyst
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    import cli.prefs as prefs
    import cli.run as cli_run
    from cli.stats_handler import StatsCallbackHandler

    prefs._PREFS_PATH = run_dir / "tmp" / "home" / ".tradingagents" / "cli_prefs.json"
    log_handler = logging.FileHandler(run_dir / "logs" / "app.log", encoding="utf-8")
    log_handler.setLevel(logging.WARNING)
    log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(log_handler)
    logging.getLogger().setLevel(logging.WARNING)

    state_holder = {}
    prefetch_events = []
    prefetch_lock = threading.Lock()
    prefetch_counter = [0]

    def record_prefetch(name, window, args_tuple, output):
        with prefetch_lock:
            prefetch_counter[0] += 1
            index = prefetch_counter[0]
        path = run_dir / "transcripts" / "prefetch" / f"{index:03d}_{name}.txt"
        write_text(path, str(output))
        event = {
            "name": name,
            "window": window,
            "args": repr(args_tuple),
            "output_path": str(path.relative_to(run_dir)),
            "output_chars": len(str(output)),
            "captured_at": now_iso(),
        }
        with prefetch_lock:
            prefetch_events.append(event)

    original_get_news = sentiment_analyst.get_news
    original_news_func = original_get_news.func
    original_stocktwits = sentiment_analyst.fetch_stocktwits_messages
    original_reddit = sentiment_analyst.fetch_reddit_posts

    def wrapped_news(ticker, start_date, end_date, trade_date=""):
        output = original_news_func(ticker, start_date, end_date, trade_date)
        record_prefetch("sentiment_news", f"{start_date}..{end_date}", (ticker, start_date, end_date), output)
        return output

    def wrapped_stocktwits(ticker, *fn_args, **fn_kwargs):
        output = original_stocktwits(ticker, *fn_args, **fn_kwargs)
        window = f"{fn_kwargs.get('start_date')}..{fn_kwargs.get('end_date')}"
        record_prefetch("sentiment_stocktwits", window, (ticker, fn_args, fn_kwargs), output)
        return output

    def wrapped_reddit(ticker, *fn_args, **fn_kwargs):
        output = original_reddit(ticker, *fn_args, **fn_kwargs)
        window = f"{fn_kwargs.get('start_date')}..{fn_kwargs.get('end_date')}"
        record_prefetch("sentiment_reddit", window, (ticker, fn_args, fn_kwargs), output)
        return output

    sentiment_analyst.get_news = SimpleNamespace(func=wrapped_news)
    sentiment_analyst.fetch_stocktwits_messages = wrapped_stocktwits
    sentiment_analyst.fetch_reddit_posts = wrapped_reddit

    class RecordingStatsHandler(StatsCallbackHandler):
        instances = []

        def __init__(self):
            super().__init__()
            self.events = []
            self.lock = threading.Lock()
            self.seq = 0
            self.tool_names = {}
            self.retry_events = 0
            self.llm_error_events = 0
            self.tool_error_events = 0
            self.usage_missing = 0
            self.tool_outputs = []
            RecordingStatsHandler.instances.append(self)

        def _add(self, payload):
            with self.lock:
                self.seq += 1
                payload["seq"] = self.seq
                payload["ts"] = now_iso()
                self.events.append(payload)

        def on_llm_start(self, serialized, prompts, **kwargs):
            super().on_llm_start(serialized, prompts, **kwargs)
            self._add({
                "type": "llm_start",
                "model": (serialized or {}).get("name") or kwargs.get("name"),
                "prompts": len(prompts),
                "prompt_chars": sum(len(p or "") for p in prompts),
            })

        def on_chat_model_start(self, serialized, messages, **kwargs):
            super().on_chat_model_start(serialized, messages, **kwargs)
            self._add({
                "type": "llm_start",
                "model": (serialized or {}).get("name") or kwargs.get("name"),
                "prompts": len(messages),
                "prompt_chars": sum(len(str(message)) for batch in messages for message in batch),
            })

        def on_llm_end(self, response: LLMResult, **kwargs):
            super().on_llm_end(response, **kwargs)
            usage = None
            try:
                generation = response.generations[0][0]
                message = getattr(generation, "message", None)
                usage = getattr(message, "usage_metadata", None)
                if not usage:
                    llm_output = getattr(response, "llm_output", None) or {}
                    usage = llm_output.get("token_usage") or llm_output.get("usage")
            except (IndexError, TypeError, AttributeError):
                usage = None
            if not usage:
                self.usage_missing += 1
            self._add({"type": "llm_end", "usage": usage})

        def on_llm_error(self, error, **kwargs):
            self.llm_error_events += 1
            self._add({"type": "llm_error", "error": f"{type(error).__name__}: {error}"})

        def on_retry(self, retry_state, **kwargs):
            self.retry_events += 1
            self._add({"type": "retry"})

        def on_tool_start(self, serialized, input_str, **kwargs):
            super().on_tool_start(serialized, input_str, **kwargs)
            tool = (serialized or {}).get("name") or kwargs.get("name") or "unknown"
            run_id = str(kwargs.get("run_id"))
            self.tool_names[run_id] = tool
            self._add({
                "type": "tool_start",
                "tool": tool,
                "run_id": run_id,
                "input": input_str,
            })

        def on_tool_end(self, output, **kwargs):
            run_id = str(kwargs.get("run_id"))
            tool = self.tool_names.get(run_id) or kwargs.get("name") or "unknown"
            output_str = str(output)
            with self.lock:
                self.seq += 1
                seq = self.seq
                self.events.append({
                    "type": "tool_end",
                    "tool": tool,
                    "run_id": run_id,
                    "seq": seq,
                    "ts": now_iso(),
                    "output_chars": len(output_str),
                })
                self.tool_outputs.append((seq, tool, output_str))

        def on_tool_error(self, error, **kwargs):
            self.tool_error_events += 1
            self._add({"type": "tool_error", "error": f"{type(error).__name__}: {error}"})

    cli_run.StatsCallbackHandler = RecordingStatsHandler

    original_record = TradingAgentsGraph.record_decision

    def wrapped_record(self, company_name, trade_date, final_state):
        state_holder["final_state"] = final_state
        write_json(run_dir / "transcripts" / "final_state.json", final_state)
        try:
            rating = run_rating(final_state)
        except Exception as exc:
            rating = f"ERROR: {type(exc).__name__}: {exc}"
        write_json(run_dir / "transcripts" / "final-status.json", {
            "company": company_name,
            "trade_date": trade_date,
            "final_rating": rating,
            "final_trade_decision": final_state.get("final_trade_decision"),
            "run_settings": self.run_settings(),
            "captured_at": now_iso(),
        })
        return original_record(self, company_name, trade_date, final_state)

    TradingAgentsGraph.record_decision = wrapped_record

    started = now_iso()
    t0 = monotonic()
    error = None
    try:
        cli_run.run_analysis(
            checkpoint=False,
            portfolio=None,
            flags={
                "ticker": args.ticker,
                "date": args.date,
                "analysts": args.analysts,
                "save": True,
                "show": False,
                "html": True,
            },
        )
        exit_code = 0
    except BaseException as exc:
        error = f"{type(exc).__name__}: {exc}"
        write_text(run_dir / "logs" / "inner-traceback.txt", traceback.format_exc())
        exit_code = 1
    finally:
        elapsed = monotonic() - t0
        stats = RecordingStatsHandler.instances[-1] if RecordingStatsHandler.instances else None
        if stats is not None:
            event_path = run_dir / "transcripts" / "tool-events.jsonl"
            with event_path.open("w", encoding="utf-8") as handle:
                for event in stats.events:
                    if event.get("type") == "tool_end":
                        output_path = run_dir / "transcripts" / "tool-outputs" / \
                            f"{event['seq']:04d}_{event['tool']}.txt"
                        match = next((item for item in stats.tool_outputs if item[0] == event["seq"]), None)
                        if match:
                            write_text(output_path, match[2])
                            event["output_path"] = str(output_path.relative_to(run_dir))
                    handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            write_text(
                run_dir / "transcripts" / "prefetch-events.jsonl",
                "\n".join(json.dumps(event, ensure_ascii=False, default=str) for event in prefetch_events) + "\n",
            )
            final_status_path = run_dir / "transcripts" / "final-status.json"
            final_status = json.loads(final_status_path.read_text(encoding="utf-8")) if final_status_path.exists() else {}
            metrics = {
                "run_id": args.run_id,
                "started_at": started,
                "finished_at": now_iso(),
                "elapsed_monotonic_seconds": round(elapsed, 3),
                "exit_code": exit_code,
                "error": error,
                "llm_calls": stats.llm_calls,
                "tool_calls": stats.tool_calls,
                "tokens_in": stats.tokens_in,
                "tokens_out": stats.tokens_out,
                "llm_usage_missing": stats.usage_missing,
                "retry_events": stats.retry_events,
                "llm_error_events": stats.llm_error_events,
                "tool_error_events": stats.tool_error_events,
                "tool_event_count": len(stats.tool_outputs),
                "prefetch_event_count": len(prefetch_events),
                "final_state_captured": "final_state" in state_holder,
                "final_rating": final_status.get("final_rating"),
                "final_decision_preview": preview((state_holder.get("final_state") or {}).get("final_trade_decision")),
                "module_file": str(Path(tradingagents.__file__).resolve()),
                "module_version": getattr(tradingagents, "__version__", None),
            }
        else:
            write_text(
                run_dir / "transcripts" / "prefetch-events.jsonl",
                "\n".join(json.dumps(event, ensure_ascii=False, default=str) for event in prefetch_events) + "\n",
            )
            metrics = {
                "run_id": args.run_id,
                "started_at": started,
                "finished_at": now_iso(),
                "elapsed_monotonic_seconds": round(elapsed, 3),
                "exit_code": exit_code,
                "error": error or "no stats handler instance was created",
                "llm_calls": None,
                "tool_calls": None,
                "tokens_in": None,
                "tokens_out": None,
                "llm_usage_missing": None,
                "retry_events": None,
                "llm_error_events": None,
                "tool_error_events": None,
                "tool_event_count": None,
                "prefetch_event_count": len(prefetch_events),
                "final_state_captured": "final_state" in state_holder,
            }
        write_json(run_dir / "metrics-inner.json", metrics)
    return exit_code


def main() -> int:
    args = parse_args()
    if args.inner:
        return run_inner(args)
    return run_orchestrator(args)


if __name__ == "__main__":
    raise SystemExit(main())
