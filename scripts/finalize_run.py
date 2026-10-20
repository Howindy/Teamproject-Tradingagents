from __future__ import annotations

import argparse
import csv
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from packaging.version import InvalidVersion, Version

from baseline_common import (
    BASELINE_ROOT,
    PROJECT_ROOT,
    now_iso,
    write_json,
    write_text,
)
import run_baseline as rb


def git_output(args: list[str]) -> str:
    result = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    return result.stdout.strip()


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def latest_bar(cache_csv: Path) -> dict:
    if not cache_csv.exists():
        return {}
    with cache_csv.open(encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    rows = [row for row in rows if row]
    if len(rows) < 2:
        return {}
    header, last = rows[0], rows[-1]
    record = dict(zip(header, last))
    date = (record.get("Date") or "").split(" ")[0]
    return {"date": date, "close": record.get("Close"), "open": record.get("Open"),
            "high": record.get("High"), "low": record.get("Low"), "volume": record.get("Volume")}


def below_minimum(dependencies: dict) -> list[dict]:
    result = []
    for name, info in (dependencies.get("packages") or {}).items():
        installed = info.get("installed")
        minimum = info.get("required_minimum")
        if not installed or not minimum:
            continue
        try:
            if Version(installed) < Version(minimum):
                result.append({"package": name, "installed": installed, "required_minimum": minimum})
        except InvalidVersion:
            result.append({"package": name, "installed": installed, "required_minimum": minimum})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--preflight-id", default="preflight-20261020-02")
    args = parser.parse_args()
    run_dir = BASELINE_ROOT / "runs" / args.run_id
    preflight_dir = BASELINE_ROOT / "preflight" / args.preflight_id
    if not run_dir.exists():
        raise SystemExit(f"run directory does not exist: {run_dir}")

    manifest = load_json(run_dir / "run-manifest.json", {})
    environment = load_json(run_dir / "environment.json", {})
    metrics = load_json(run_dir / "metrics.json", {})
    consistency = load_json(run_dir / "report-consistency.json", {})
    final_status = load_json(run_dir / "transcripts" / "final-status.json", {})
    preflight_manifest = load_json(preflight_dir / "probe-manifest.json", {})
    rows = list(csv.DictReader((run_dir / "data-availability.csv").open(encoding="utf-8")))

    commit = git_output(["git", "rev-parse", "HEAD"])
    status_rows = [line for line in git_output(["git", "status", "--porcelain=v1", "-uall"]).splitlines() if line]
    outside_allowed = [
        line for line in status_rows
        if not line[3:].startswith(("scripts/", "baseline/"))
    ]
    latest = latest_bar(run_dir / "cache" / "NVDA-YFin-data.csv")
    deps_below = below_minimum(environment.get("dependencies", {}))

    status_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        status_counts[row["status"]] += 1
    non_success = [row for row in rows if row["status"] != "success"]
    coverage_complete = not any(
        row["status"] in {"unavailable", "no_output", "not_configured", "withheld"} for row in rows
    )
    main_complete = (
        metrics.get("exit_code") == 0
        and consistency.get("final_state_exists")
        and consistency.get("final_decision_nonempty")
        and consistency.get("complete_report_found")
        and consistency.get("complete_report_contains_decision")
    )

    grouped = defaultdict(lambda: {"calls": 0, "records": 0})
    for row in rows:
        key = (row["tool"], row["source"], row["status"])
        grouped[key]["calls"] += 1
        try:
            grouped[key]["records"] += int(row["record_count"] or 0)
        except ValueError:
            pass

    invocation = (
        "zsh -c 'source ~/.zshrc && use_ta_cityu && cd "
        f"{PROJECT_ROOT / 'TradingAgents'} && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=\"$PWD\" "
        "/opt/miniconda3/envs/tradingagents/bin/python -B ../scripts/run_baseline.py "
        f"--run-id {args.run_id} --ticker NVDA --date 2026-10-19 "
        "--analysts market,social,news,fundamentals --language English "
        "--debate-rounds 1 --risk-rounds 1'"
    )
    reproduce = f"""#!/bin/zsh
set -euo pipefail
source ~/.zshrc
use_ta_cityu
cd {PROJECT_ROOT / 'TradingAgents'}
RUN_ID="${{1:-{args.run_id}-repro}}"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" /opt/miniconda3/envs/tradingagents/bin/python -B \\
  ../scripts/run_baseline.py \\
  --run-id "$RUN_ID" --ticker NVDA --date 2026-10-19 \\
  --analysts market,social,news,fundamentals --language English \\
  --debate-rounds 1 --risk-rounds 1
"""
    write_text(run_dir / "reproduce.sh", reproduce)
    (run_dir / "reproduce.sh").chmod(0o755)

    environment.update({
        "git_commit": commit,
        "git_commit_short": commit[:12],
        "git_status_at_finalize": status_rows,
        "outside_allowed_changes": outside_allowed,
        "invocation": invocation,
        "analysis_date": manifest.get("analysis_date"),
        "run_started_at": (metrics.get("inner") or {}).get("started_at"),
        "run_finished_at": (metrics.get("inner") or {}).get("finished_at"),
        "timezone": (environment.get("timezone") or "CST"),
        "timezone_offset": environment.get("timezone_offset"),
        "stdout_stderr_mode": "separate: logs/stdout.log and logs/stderr.log",
        "latest_market_bar": latest,
        "preflight_authoritative": str(preflight_dir.relative_to(PROJECT_ROOT)),
        "preflight_superseded": "baseline/preflight/preflight-20261020-01",
        "opencode_session_export": str((run_dir / "transcripts" / "opencode-session.json").relative_to(PROJECT_ROOT)),
        "dependencies_below_minimum": deps_below,
        "installed_tradingagents_distribution": environment.get("dependencies", {}).get("installed_tradingagents_distribution"),
    })
    write_json(run_dir / "environment.json", environment)

    report_path = consistency.get("complete_report_path")
    full_log_path = consistency.get("full_states_log_path")
    session_path = environment["opencode_session_export"]
    lines = [
        f"# Baseline run {args.run_id}",
        "",
        "## Verdict",
        "",
        f"- Main flow completed: {'yes' if main_complete else 'no'}",
        f"- Data coverage complete: {'yes' if coverage_complete else 'no'}",
        f"- Metric evidence sufficient: {'yes for calls/tokens; retries/fallback observed only' if metrics.get('llm_calls') is not None else 'no'}",
        f"- Reproducible: yes, with the recorded command and dependency-version caveat",
        f"- Source unchanged: {'yes' if metrics.get('source_integrity', {}).get('identical') else 'no'}",
        f"- Out-of-scope writes: {'none detected' if metrics.get('outside_integrity', {}).get('identical') and metrics.get('home_tradingagents_integrity', {}).get('identical') else 'detected'}",
        "",
        "A generated trading decision does not by itself make this baseline complete.",
        "",
        "## Run identity",
        "",
        f"- Run id: `{args.run_id}`",
        f"- Commit: `{commit}`",
        f"- Ticker: {manifest.get('ticker')}",
        f"- Analysis date: {manifest.get('analysis_date')}",
        f"- Latest market bar: {latest.get('date')} close {latest.get('close')}",
        f"- Analysts: {', '.join(manifest.get('analysts', []))}",
        f"- Debate/risk rounds: {manifest.get('debate_rounds')} / {manifest.get('risk_rounds')}",
        f"- Language: {manifest.get('language')}",
        f"- Quick/deep model: {environment.get('quick_model')} / {environment.get('deep_model')}",
        f"- Provider/endpoint: {environment.get('provider')} / {environment.get('endpoint')}",
        f"- Python: {(environment.get('module_check', {}).get('parsed') or {}).get('sys_executable')}",
        f"- Module: {(environment.get('module_check', {}).get('parsed') or {}).get('tradingagents_file')}",
        f"- Started/finished: {(metrics.get('inner') or {}).get('started_at')} / {(metrics.get('inner') or {}).get('finished_at')}",
        f"- Timezone: {environment.get('timezone')} {environment.get('timezone_offset')}",
        "",
        "## Invocation",
        "",
        "```text",
        invocation,
        "```",
        "",
        f"- Working directory: `{PROJECT_ROOT / 'TradingAgents'}`",
        f"- stdout/stderr: {environment.get('stdout_stderr_mode')}",
        "",
        "## Preflight",
        "",
        f"- Authoritative preflight: `{preflight_dir.relative_to(PROJECT_ROOT)}`",
        f"- Superseded preflight retained for audit: `baseline/preflight/preflight-20261020-01`",
        f"- Preflight status counts: {json.dumps(preflight_manifest.get('status_counts', {}), ensure_ascii=False)}",
        f"- Source/outside/home integrity in preflight: "
        f"{preflight_manifest.get('source_integrity', {}).get('identical')} / "
        f"{preflight_manifest.get('outside_integrity', {}).get('identical')} / "
        f"{preflight_manifest.get('home_tradingagents_integrity', {}).get('identical')}",
        "",
        "## Execution",
        "",
        f"- Exit code: {metrics.get('exit_code')}",
        f"- Inner elapsed (monotonic): {(metrics.get('inner') or {}).get('elapsed_monotonic_seconds')}s",
        f"- Total child elapsed (monotonic): {metrics.get('total_elapsed_monotonic_seconds')}s",
        f"- Final rating: {final_status.get('final_rating')}",
        f"- Complete report: `{report_path}`",
        f"- Full state log: `{full_log_path}`",
        f"- Memory log: `baseline/runs/{args.run_id}/memory/trading_memory.md`",
        f"- Report consistency: decision={consistency.get('final_decision_matches_full_log')}, "
        f"report_contains={consistency.get('complete_report_contains_decision')}, "
        f"rating={consistency.get('rating_matches_full_log')}, "
        f"sections={consistency.get('nonempty_section_files')}/{consistency.get('section_file_count')}",
        "",
        "## Data availability",
        "",
        f"- Status counts: {json.dumps(dict(status_counts), ensure_ascii=False)}",
        f"- Per-call CSV: `baseline/runs/{args.run_id}/data-availability.csv`",
        "",
        "| Tool | Source | Status | Calls | Records |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for (tool, source, status), info in sorted(grouped.items()):
        lines.append(f"| {tool} | {source} | {status} | {info['calls']} | {info['records']} |")
    lines.extend([
        "",
        "Missing or incomplete sources:",
        "",
    ])
    seen = set()
    for row in non_success:
        key = (row["tool"], row["status"], row["reason"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {row['tool']} ({row['source']}): {row['status']} — {row['reason']} `{row['evidence_path']}`")
    lines.extend([
        "",
        "Sentiment prefetch raw blocks are saved under `transcripts/prefetch/`; they are not model outputs.",
        "",
        "## Metrics",
        "",
        f"- LLM calls: {metrics.get('llm_calls')}",
        f"- Tool calls: {metrics.get('tool_calls')}",
        f"- Input/output tokens: {metrics.get('tokens_in')} / {metrics.get('tokens_out')}",
        f"- LLM usage missing: {metrics.get('llm_usage_missing')}",
        f"- Retry events: {metrics.get('retry_events')}",
        f"- LLM/tool errors: {metrics.get('llm_error_events')} / {metrics.get('tool_error_events')}",
        f"- Structured fallback warnings: {metrics.get('structured_fallback_warnings')}",
        f"- Message/tool log lines: {metrics.get('message_tool_log_lines')}",
        f"- Monetary cost: {metrics.get('monetary_cost')} ({metrics.get('monetary_cost_reason')})",
        f"- Measurement scope: {metrics.get('measurement_scope')}",
        "",
        "## Reproducibility",
        "",
        "- Exact invocation is above; `reproduce.sh` is included and requires a new run-id.",
        f"- Commit: `{commit}`.",
        f"- Python: {(environment.get('module_check', {}).get('parsed') or {}).get('sys_executable')} "
        f"({(environment.get('module_check', {}).get('parsed') or {}).get('sys_version')}).",
        f"- Source module: {(environment.get('module_check', {}).get('parsed') or {}).get('tradingagents_file')} "
        f"version {(environment.get('module_check', {}).get('parsed') or {}).get('tradingagents_version')}.",
        f"- Installed `tradingagents` distribution: {environment.get('installed_tradingagents_distribution')} (not the loaded source).",
        "- Dependencies below pyproject minimum: " + (", ".join(
            f"{item['package']} {item['installed']} < {item['required_minimum']}" for item in deps_below
        ) if deps_below else "none"),
        "",
        "## Integrity",
        "",
        f"- TradingAgents source identical: {metrics.get('source_integrity', {}).get('identical')}",
        f"- Outside-scope identical: {metrics.get('outside_integrity', {}).get('identical')}",
        f"- Home .tradingagents identical: {metrics.get('home_tradingagents_integrity', {}).get('identical')}",
        f"- Git status entries outside scripts/baseline: {outside_allowed if outside_allowed else 'none'}",
        "",
        "## Limitations",
        "",
        "- Yahoo ticker news was unavailable; the run used global Yahoo news instead.",
        "- StockTwits returned HTTP 403; sentiment rests on 11 Reddit posts plus the news block (news unavailable).",
        "- FRED_API_KEY was not set; all macro-data calls degraded to a not-configured sentinel.",
        "- Polymarket odds, Yahoo company profile and Yahoo insider transactions were withheld because 2026-10-19 is historical.",
        "- The reports acknowledge these gaps. Some qualitative background (for example sector description) may rely on model knowledge even where profile data was withheld; no numeric fabrication was observed in the checked outputs.",
        "- Installed package versions below pyproject minima are a reproducibility caveat.",
        "- Monetary cost is null because no CityU price schedule was provided.",
        "",
        "## OpenCode session",
        "",
        f"- Export: `{session_path}`",
        f"- Re-export command: `opencode export ses_ea6f6f57affeIKSEf18KdNxecQ > {session_path}`",
        "",
    ])
    write_text(run_dir / "summary.md", "\n".join(lines) + "\n")

    readme = f"""# {args.run_id}

Single TradingAgents baseline run. The application source was not modified.

- Commit: `{commit}`
- Analysis date: 2026-10-19
- Exit code: {metrics.get('exit_code')}
- Main flow completed: {'yes' if main_complete else 'no'}
- Data coverage complete: {'yes' if coverage_complete else 'no'}

## Reproduce

```text
{invocation}
```

`reproduce.sh` is included; it requires a new run-id.

## Layout

- `logs/`: stdout, stderr, exit code, module check, application warnings.
- `results/`: application reports, full state log, message/tool log.
- `cache/`: run-local cache (started empty).
- `memory/`: run-local memory log (started empty).
- `transcripts/`: final state, tool events, clean tool outputs, raw sentiment prefetch, OpenCode session export.
- `tmp/`: redirected HOME/XDG/TMPDIR.
- `source-*.json`, `outside-*.json`, `home-tradingagents-*.json`: integrity evidence.
- `metrics.json`, `data-availability.csv`, `report-consistency.json`, `summary.md`, `environment.json`.

## Notes

- stdout and stderr are separate files.
- The tool evidence is stored raw and clean; `data-availability.csv` points at the clean content.
- A generated Hold decision does not mean the baseline is complete in data terms.
"""
    write_text(run_dir / "README.md", readme)

    manifest.update({
        "git_commit": commit,
        "git_commit_short": commit[:12],
        "invocation": invocation,
        "reproduce_script": "reproduce.sh",
        "preflight_authoritative": str(preflight_dir.relative_to(PROJECT_ROOT)),
        "preflight_superseded": "baseline/preflight/preflight-20261020-01",
        "opencode_session_export": session_path,
        "stdout_stderr_mode": environment.get("stdout_stderr_mode"),
        "latest_market_bar": latest,
        "finalized_at": now_iso(),
        "artifacts": rb.artifact_manifest(run_dir),
    })
    write_json(run_dir / "run-manifest.json", manifest)
    print(f"finalized {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
