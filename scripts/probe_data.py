from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path

from baseline_common import (
    BASELINE_ROOT,
    PROJECT_ROOT,
    REPO_ROOT,
    classify_output,
    compare_snapshots,
    count_records,
    ensure_new_dir,
    env_summary,
    find_files,
    monotonic,
    now_iso,
    preview,
    reason_for,
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


class Tee:
    def __init__(self, stream, path):
        self.stream = stream
        self.path = path
        self.handle = open(path, "a", encoding="utf-8")

    def write(self, data):
        self.stream.write(data)
        self.handle.write(data)
        self.handle.flush()

    def flush(self):
        self.stream.flush()
        self.handle.flush()

    def isatty(self):
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-id", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    return parser.parse_args()


def add_row(rows, check_dir, evidence_dir, *, category, tool, source, window, text, elapsed, notes="", records=None):
    status = classify_output(text)
    index = len(rows) + 1
    safe_name = tool.replace("/", "_")
    evidence = evidence_dir / f"{index:02d}_{safe_name}.txt"
    write_text(evidence, text or "")
    rel = evidence.relative_to(PROJECT_ROOT).as_posix()
    rows.append({
        "phase": "preflight",
        "category": category,
        "tool": tool,
        "source": source,
        "requested_window": window,
        "status": status,
        "record_count": records if records is not None else count_records(text, status),
        "reason": reason_for(status, text),
        "evidence_path": rel,
        "elapsed_ms": round(elapsed * 1000, 1),
        "notes": notes,
    })


def main() -> int:
    args = parse_args()
    check_id = validate_id(args.check_id, "check-id")
    ticker = args.ticker.strip().upper()
    analysis_date = args.date
    check_dir = BASELINE_ROOT / "preflight" / check_id
    ensure_new_dir(check_dir)
    for name in ("cache", "logs", "evidence", "results", "memory", "tmp", "home", "transcripts"):
        (check_dir / name).mkdir(parents=True, exist_ok=True)
    sys.stdout = Tee(sys.stdout, check_dir / "logs" / "stdout.log")
    sys.stderr = Tee(sys.stderr, check_dir / "logs" / "stderr.log")

    real_home = Path(os.environ.get("HOME", str(Path.home()))).expanduser()
    source_before = snapshot_tree(REPO_ROOT)
    outside_before = snapshot_project_outside_allowed(PROJECT_ROOT)
    home_before = snapshot_tree(real_home / ".tradingagents")
    write_json(check_dir / "source-before.json", source_before)
    write_json(check_dir / "outside-before.json", outside_before)
    write_json(check_dir / "home-tradingagents-before.json", home_before)

    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["TRADINGAGENTS_CACHE_DIR"] = str(check_dir / "cache")
    os.environ["TRADINGAGENTS_RESULTS_DIR"] = str(check_dir / "results")
    os.environ["TRADINGAGENTS_MEMORY_LOG_PATH"] = str(check_dir / "memory" / "trading_memory.md")
    os.environ["TRADINGAGENTS_CHECKPOINT_ENABLED"] = "false"
    os.environ["TRADINGAGENTS_NO_UPDATE_CHECK"] = "1"
    os.environ["CI"] = "1"
    os.environ["HOME"] = str(check_dir / "home")
    os.environ["TMPDIR"] = str(check_dir / "tmp")
    os.environ["XDG_CACHE_HOME"] = str(check_dir / "tmp" / "xdg-cache")
    os.environ["XDG_CONFIG_HOME"] = str(check_dir / "tmp" / "xdg-config")
    os.environ["XDG_DATA_HOME"] = str(check_dir / "tmp" / "xdg-data")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(REPO_ROOT))

    log_path = check_dir / "logs" / "probe.log"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.WARNING)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.WARNING)

    rows: list[dict] = []
    errors: list[str] = []
    module_paths: dict = {}
    started = now_iso()
    total_start = monotonic()
    exit_code = 0

    try:
        import tradingagents
        from tradingagents.dataflows.config import run_config
        from tradingagents.dataflows.vendors.fred import get_macro_data
        from tradingagents.dataflows.vendors.polymarket import get_prediction_markets
        from tradingagents.dataflows.vendors.reddit import fetch_reddit_posts, subreddits_for
        from tradingagents.dataflows.vendors.sec_edgar import (
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        )
        from tradingagents.dataflows.vendors.stocktwits import fetch_stocktwits_messages
        from tradingagents.dataflows.vendors.yahoo.fundamentals import get_fundamentals
        from tradingagents.dataflows.vendors.yahoo.market import get_YFin_data_online
        from tradingagents.dataflows.vendors.yahoo.news import get_news_yfinance
        from tradingagents.dataflows.vendors.yahoo.ohlcv import load_ohlcv
        from tradingagents.dataflows.vendors.yahoo.snapshot import build_verified_market_snapshot
        from tradingagents.default_config import DEFAULT_CONFIG
        import cli
        import cli.main

        module_paths = {
            "tradingagents_file": str(Path(tradingagents.__file__).resolve()),
            "tradingagents_version": getattr(tradingagents, "__version__", None),
            "cli_file": str(Path(cli.__file__).resolve()),
            "cli_main_file": str(Path(cli.main.__file__).resolve()),
            "expected_repo": str(REPO_ROOT),
        }
        expected = (REPO_ROOT / "tradingagents" / "__init__.py").resolve()
        if Path(tradingagents.__file__).resolve() != expected:
            raise RuntimeError(f"refusing to run: loaded {tradingagents.__file__} instead of {expected}")

        config = dict(DEFAULT_CONFIG)
        config["data_cache_dir"] = str(check_dir / "cache")
        config["results_dir"] = str(check_dir / "results")
        config["memory_log_path"] = str(check_dir / "memory" / "trading_memory.md")
        config["checkpoint_enabled"] = False

        start_date = (__import__("datetime").datetime.strptime(analysis_date, "%Y-%m-%d")
                      - __import__("datetime").timedelta(days=7)).strftime("%Y-%m-%d")
        window = f"{start_date}..{analysis_date}"

        def timed(fn, *fn_args, **fn_kwargs):
            t0 = monotonic()
            try:
                value = fn(*fn_args, **fn_kwargs)
                return value, None, monotonic() - t0
            except Exception as exc:
                text = f"EXCEPTION {type(exc).__name__}: {exc}"
                return text, exc, monotonic() - t0

        with run_config(config):
            value, exc, elapsed = timed(load_ohlcv, ticker, analysis_date, False)
            if exc is None:
                try:
                    text = (
                        f"# Yahoo OHLCV probe for {ticker}\n"
                        f"# Requested as-of: {analysis_date}\n"
                        f"# Total records: {len(value)}\n"
                        f"# First row: {value.iloc[0].to_dict() if len(value) else None}\n"
                        f"# Latest row: {value.iloc[-1].to_dict() if len(value) else None}\n\n"
                        + value.tail(10).to_csv(index=False)
                    )
                except Exception as late:
                    text = f"EXCEPTION while formatting OHLCV: {type(late).__name__}: {late}"
            else:
                text = value
            add_row(rows, check_dir, check_dir / "evidence", category="market", tool="yahoo_ohlcv",
                    source="Yahoo Finance", window=f"5y..{analysis_date}", text=text,
                    elapsed=elapsed, notes="full 5-year download filtered to as-of date")

            value, exc, elapsed = timed(build_verified_market_snapshot, ticker, analysis_date, 30)
            text = value if exc is None else value
            add_row(rows, check_dir, check_dir / "evidence", category="market", tool="yahoo_snapshot",
                    source="Yahoo Finance", window=f"30 rows..{analysis_date}", text=text,
                    elapsed=elapsed, notes="deterministic snapshot used by the market analyst",
                    records=30)

            value, exc, elapsed = timed(get_news_yfinance, ticker, start_date, analysis_date)
            add_row(rows, check_dir, check_dir / "evidence", category="news", tool="yahoo_news",
                    source="Yahoo Finance", window=window, text=value, elapsed=elapsed,
                    notes="ticker news window used by news and sentiment analysts")

            value, exc, elapsed = timed(get_YFin_data_online, ticker, start_date, analysis_date)
            add_row(rows, check_dir, check_dir / "evidence", category="market", tool="yahoo_stock_range",
                    source="Yahoo Finance", window=window, text=value, elapsed=elapsed,
                    notes="range request as the market analyst would call it")

            for freq in ("quarterly",):
                value, exc, elapsed = timed(get_balance_sheet, ticker, freq, analysis_date)
                add_row(rows, check_dir, check_dir / "evidence", category="fundamentals", tool="sec_balance_sheet",
                        source="SEC EDGAR", window=f"as filed by {analysis_date}", text=value,
                        elapsed=elapsed, notes=f"freq={freq}")
                value, exc, elapsed = timed(get_cashflow, ticker, freq, analysis_date)
                add_row(rows, check_dir, check_dir / "evidence", category="fundamentals", tool="sec_cashflow",
                        source="SEC EDGAR", window=f"as filed by {analysis_date}", text=value,
                        elapsed=elapsed, notes=f"freq={freq}")
                value, exc, elapsed = timed(get_income_statement, ticker, freq, analysis_date)
                add_row(rows, check_dir, check_dir / "evidence", category="fundamentals", tool="sec_income_statement",
                        source="SEC EDGAR", window=f"as filed by {analysis_date}", text=value,
                        elapsed=elapsed, notes=f"freq={freq}")

            value, exc, elapsed = timed(get_fundamentals, ticker, analysis_date)
            add_row(rows, check_dir, check_dir / "evidence", category="fundamentals", tool="yahoo_profile",
                    source="Yahoo Finance", window=f"as of {analysis_date}", text=value,
                    elapsed=elapsed, notes="live profile is expected to be withheld for a historical date")

            value, exc, elapsed = timed(fetch_stocktwits_messages, ticker, 30, 10.0, start_date, analysis_date)
            add_row(rows, check_dir, check_dir / "evidence", category="social", tool="stocktwits",
                    source="StockTwits", window=window, text=value, elapsed=elapsed,
                    notes="public cashtag stream; no credential required")

            subreddits = subreddits_for(ticker)
            value, exc, elapsed = timed(fetch_reddit_posts, ticker, subreddits, start_date=start_date,
                                        end_date=analysis_date)
            add_row(rows, check_dir, check_dir / "evidence", category="social", tool="reddit",
                    source="Reddit", window=window, text=value, elapsed=elapsed,
                    notes="public RSS search; no credential required")

            if os.environ.get("FRED_API_KEY"):
                value, exc, elapsed = timed(get_macro_data, "cpi", analysis_date)
                add_row(rows, check_dir, check_dir / "evidence", category="macro", tool="fred",
                        source="FRED", window=f"1y..{analysis_date}", text=value, elapsed=elapsed,
                        notes="FRED_API_KEY is set")
            else:
                add_row(rows, check_dir, check_dir / "evidence", category="macro", tool="fred",
                        source="FRED", window=f"1y..{analysis_date}",
                        text="FRED_API_KEY is not set; no request attempted.", elapsed=0.0,
                        notes="not configured")

            value, exc, elapsed = timed(get_prediction_markets, "Fed rate cut", 6, analysis_date)
            add_row(rows, check_dir, check_dir / "evidence", category="prediction", tool="polymarket",
                    source="Polymarket", window=f"live as of {analysis_date}", text=value,
                    elapsed=elapsed, notes="historical date: live-only odds are expected to be withheld")

    except Exception as exc:
        exit_code = 1
        errors.append(f"{type(exc).__name__}: {exc}")
        write_text(check_dir / "logs" / "fatal.txt", traceback.format_exc())
    finally:
        total_elapsed = monotonic() - total_start
        source_after = snapshot_tree(REPO_ROOT)
        outside_after = snapshot_project_outside_allowed(PROJECT_ROOT)
        home_after = snapshot_tree(real_home / ".tradingagents")
        source_integrity = compare_snapshots(source_before, source_after)
        outside_integrity = compare_snapshots(outside_before, outside_after)
        home_integrity = compare_snapshots(home_before, home_after)
        write_json(check_dir / "source-after.json", source_after)
        write_json(check_dir / "source-integrity.json", source_integrity)
        write_json(check_dir / "outside-after.json", outside_after)
        write_json(check_dir / "outside-integrity.json", outside_integrity)
        write_json(check_dir / "home-tradingagents-after.json", home_after)
        write_json(check_dir / "home-tradingagents-integrity.json", home_integrity)
        write_csv(check_dir / "data-availability.csv", rows, FIELDNAMES)

        status_counts: dict[str, int] = {}
        for row in rows:
            status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
        for label, integrity in (("source", source_integrity), ("outside", outside_integrity),
                                 ("home_tradingagents", home_integrity)):
            if not integrity.get("identical"):
                exit_code = max(exit_code, 2)
                errors.append(f"{label} integrity mismatch")

        manifest = {
            "check_id": check_id,
            "ticker": ticker,
            "analysis_date": analysis_date,
            "started_at": started,
            "finished_at": now_iso(),
            "elapsed_monotonic_seconds": round(total_elapsed, 3),
            "exit_code": exit_code,
            "errors": errors,
            "module_paths": module_paths,
            "environment": env_summary(),
            "status_counts": status_counts,
            "source_integrity": source_integrity,
            "outside_integrity": outside_integrity,
            "home_tradingagents_integrity": home_integrity,
            "paths": {
                "cache": str(check_dir / "cache"),
                "results": str(check_dir / "results"),
                "memory": str(check_dir / "memory"),
                "home": str(check_dir / "home"),
                "tmp": str(check_dir / "tmp"),
            },
        }
        write_json(check_dir / "probe-manifest.json", manifest)

        lines = [
            f"# Preflight {check_id}",
            "",
            f"- Ticker: {ticker}",
            f"- Analysis date: {analysis_date}",
            f"- Started: {started}",
            f"- Finished: {now_iso()}",
            f"- Exit code: {exit_code}",
            f"- Elapsed (monotonic): {total_elapsed:.3f}s",
            f"- Source integrity: {'identical' if source_integrity.get('identical') else 'MISMATCH'}",
            f"- Outside-scope integrity: {'identical' if outside_integrity.get('identical') else 'MISMATCH'}",
            f"- Home .tradingagents integrity: {'identical' if home_integrity.get('identical') else 'MISMATCH'}",
            "",
            "| Tool | Source | Window | Status | Records | Evidence |",
            "| --- | --- | --- | --- | ---: | --- |",
        ]
        for row in rows:
            lines.append(
                f"| {row['tool']} | {row['source']} | {row['requested_window']} | "
                f"{row['status']} | {row['record_count']} | {row['evidence_path']} |"
            )
        if errors:
            lines.extend(["", "## Errors", ""] + [f"- {item}" for item in errors])
        write_text(check_dir / "summary.md", "\n".join(lines) + "\n")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
