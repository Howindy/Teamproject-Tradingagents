from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import stat
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT / "TradingAgents"
BASELINE_ROOT = PROJECT_ROOT / "baseline"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"

REQUIRED_DISTS = {
    "cryptography": "42.0",
    "langchain-core": "1.6.5",
    "langchain-anthropic": "1.7.4",
    "langchain-google-genai": "4.4.0",
    "langchain-openai": "1.6.6",
    "langgraph": "1.2.12",
    "langgraph-checkpoint-sqlite": "3.1.1",
    "markdown-it-py": "4.0",
    "packaging": "24.0",
    "pandas": "3.0.6",
    "python-dotenv": "1.0.0",
    "pytz": "2025.2",
    "questionary": "2.1.0",
    "requests": "2.32.4",
    "rich": "14.0.0",
    "typer": "0.21.0",
    "stockstats": "0.6.5",
    "typing-extensions": "4.14.0",
    "yfinance": "1.7.0",
}

KEY_FLAGS = (
    "OPENAI_COMPATIBLE_API_KEY",
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "FRED_API_KEY",
    "TYPESAFE_API_KEY",
    "SEC_EDGAR_USER_AGENT",
)

PATH_FLAGS = (
    "TRADINGAGENTS_RESULTS_DIR",
    "TRADINGAGENTS_CACHE_DIR",
    "TRADINGAGENTS_MEMORY_LOG_PATH",
    "TRADINGAGENTS_LLM_BACKEND_URL",
    "TRADINGAGENTS_LLM_PROVIDER",
    "TRADINGAGENTS_QUICK_THINK_LLM",
    "TRADINGAGENTS_DEEP_THINK_LLM",
    "TRADINGAGENTS_OUTPUT_LANGUAGE",
    "TRADINGAGENTS_MAX_DEBATE_ROUNDS",
    "TRADINGAGENTS_MAX_RISK_ROUNDS",
    "TRADINGAGENTS_CHECKPOINT_ENABLED",
    "TMPDIR",
    "HOME",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def monotonic() -> float:
    return time.perf_counter()


def validate_id(value: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}", value or ""):
        raise SystemExit(f"invalid {label}: {value!r}")
    return value


def ensure_new_dir(path: Path) -> Path:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing directory: {path}")
    path.mkdir(parents=True, exist_ok=False)
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(path: Path, rel: str, root: Path) -> dict:
    st = path.lstat()
    mode = stat.S_IMODE(st.st_mode)
    entry = {
        "path": rel,
        "mode": f"{mode:04o}",
        "executable": bool(mode & 0o111),
    }
    if stat.S_ISLNK(st.st_mode):
        entry.update({"type": "symlink", "target": os.readlink(path)})
    elif stat.S_ISDIR(st.st_mode):
        entry.update({"type": "dir"})
    elif stat.S_ISREG(st.st_mode):
        entry.update({
            "type": "file",
            "size": st.st_size,
            "sha256": sha256_file(path),
        })
    else:
        entry.update({"type": "other"})
    return entry


def summarize_entries(entries: list[dict]) -> dict:
    summary = {"files": 0, "dirs": 0, "symlinks": 0, "other": 0, "total": len(entries)}
    mapping = {"file": "files", "dir": "dirs", "symlink": "symlinks", "other": "other"}
    for entry in entries:
        key = mapping.get(entry.get("type"))
        if key:
            summary[key] += 1
    return summary


def snapshot_tree(root: Path) -> dict:
    root = Path(root)
    started = now_iso()
    entries: list[dict] = []
    if not root.exists():
        return {
            "root": str(root),
            "exists": False,
            "generated_at": started,
            "entries": entries,
            "summary": {"files": 0, "dirs": 0, "symlinks": 0, "other": 0, "total": 0},
        }

    def onerror(exc):
        entries.append({"path": getattr(exc, "filename", "?"), "type": "error", "error": str(exc)})

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        dirnames.sort()
        filenames.sort()
        base = Path(dirpath)
        for name in list(dirnames):
            path = base / name
            rel = path.relative_to(root).as_posix()
            entries.append(_entry(path, rel, root))
            if path.is_symlink():
                dirnames.remove(name)
        for name in filenames:
            path = base / name
            rel = path.relative_to(root).as_posix()
            entries.append(_entry(path, rel, root))

    entries.sort(key=lambda item: item.get("path", ""))
    summary = summarize_entries(entries)
    return {
        "root": str(root),
        "exists": True,
        "generated_at": started,
        "entries": entries,
        "summary": summary,
    }


def snapshot_project_outside_allowed(project_root: Path = PROJECT_ROOT) -> dict:
    project_root = Path(project_root)
    snapshot = snapshot_tree(project_root)
    filtered = []
    for entry in snapshot.get("entries", []):
        first = entry.get("path", "").split("/", 1)[0]
        if first in {".git", "scripts", "baseline"}:
            continue
        filtered.append(entry)
    snapshot["entries"] = filtered
    snapshot["summary"] = summarize_entries(filtered)
    snapshot["excluded"] = [".git", "scripts", "baseline"]
    return snapshot


def compare_snapshots(before: dict, after: dict) -> dict:
    before_map = {entry["path"]: entry for entry in before.get("entries", [])}
    after_map = {entry["path"]: entry for entry in after.get("entries", [])}
    added = sorted(set(after_map) - set(before_map))
    removed = sorted(set(before_map) - set(after_map))
    changed = []
    for path in sorted(set(before_map) & set(after_map)):
        old = before_map[path]
        new = after_map[path]
        fields = []
        for key in ("type", "mode", "executable", "size", "sha256", "target"):
            if old.get(key) != new.get(key):
                fields.append(key)
        if fields:
            changed.append({
                "path": path,
                "fields": fields,
                "before": {key: old.get(key) for key in fields},
                "after": {key: new.get(key) for key in fields},
            })
    return {
        "identical": not added and not removed and not changed,
        "added": added,
        "removed": removed,
        "changed": changed,
        "counts": {
            "before": before.get("summary", {}),
            "after": after.get("summary", {}),
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        },
    }


def write_json(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def safe_endpoint(value: str | None) -> str | None:
    if not value:
        return None
    parts = urlsplit(value)
    if not parts.scheme or not parts.hostname:
        return "<set but not a valid URL>"
    netloc = parts.hostname
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    return f"{parts.scheme}://{netloc}{parts.path}"


def env_summary(env: dict | None = None) -> dict:
    values = os.environ if env is None else env
    zone = datetime.now().astimezone()
    return {
        "generated_at": now_iso(),
        "python_executable": sys.executable,
        "provider": values.get("TRADINGAGENTS_LLM_PROVIDER"),
        "endpoint": safe_endpoint(values.get("TRADINGAGENTS_LLM_BACKEND_URL")),
        "quick_model": values.get("TRADINGAGENTS_QUICK_THINK_LLM"),
        "deep_model": values.get("TRADINGAGENTS_DEEP_THINK_LLM"),
        "output_language": values.get("TRADINGAGENTS_OUTPUT_LANGUAGE"),
        "max_debate_rounds": values.get("TRADINGAGENTS_MAX_DEBATE_ROUNDS"),
        "max_risk_rounds": values.get("TRADINGAGENTS_MAX_RISK_ROUNDS"),
        "checkpoint_enabled": values.get("TRADINGAGENTS_CHECKPOINT_ENABLED"),
        "timezone": zone.tzname(),
        "timezone_offset": zone.strftime("%z"),
        "keys": {name: bool(values.get(name)) for name in KEY_FLAGS},
        "paths": {name: values.get(name) for name in PATH_FLAGS},
    }


def dependency_report() -> dict:
    import importlib.metadata as metadata

    rows = {}
    for name, minimum in REQUIRED_DISTS.items():
        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            version = None
        rows[name] = {"installed": version, "required_minimum": minimum}
    try:
        installed_dist = metadata.version("tradingagents")
    except metadata.PackageNotFoundError:
        installed_dist = None
    return {"packages": rows, "installed_tradingagents_distribution": installed_dist}


MODULE_CHECK_CODE = r"""
import importlib.metadata as metadata
import json
import sys
import tradingagents
import cli
import cli.main
from tradingagents.dataflows.config import get_config

print(json.dumps({
    "sys_executable": sys.executable,
    "sys_version": sys.version,
    "cwd": __import__("os").getcwd(),
    "tradingagents_file": tradingagents.__file__,
    "tradingagents_version": getattr(tradingagents, "__version__", None),
    "cli_file": cli.__file__,
    "cli_main_file": cli.main.__file__,
    "config_results_dir": get_config().get("results_dir"),
    "config_cache_dir": get_config().get("data_cache_dir"),
    "config_memory_log_path": get_config().get("memory_log_path"),
    "sys_path": sys.path,
}, default=str))
"""


def count_records(text: str, status: str | None = None) -> int | None:
    if text is None:
        return None
    if status in {"not_configured", "not_attempted"}:
        return 0
    match = re.search(r"Total records:\s*(\d+)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"Total:\s*(\d+)\s+most-recent", text)
    if match:
        return int(match.group(1))
    if "Verified market data snapshot" in text:
        closes = re.findall(r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|", text, flags=re.MULTILINE)
        if closes:
            return len(closes)
    news = len(re.findall(r"^### ", text, flags=re.MULTILINE))
    if news:
        return news
    reddit = len(re.findall(r"^\s*\[\d{4}-\d{2}-\d{2}\]", text, flags=re.MULTILINE))
    if reddit:
        return reddit
    if text.lstrip().startswith("# ") and "SEC EDGAR facts" in text:
        data_lines = [
            line for line in text.splitlines()
            if line.strip() and not line.startswith("#") and not line.startswith(",")
        ]
        return len([line for line in data_lines if "," in line])
    if "values from" in text and re.search(r"^\d{4}-\d{2}-\d{2}:", text, flags=re.MULTILINE):
        values = re.findall(r"^\d{4}-\d{2}-\d{2}:\s*(.+)$", text, flags=re.MULTILINE)
        valid = [value for value in values if not value.lstrip().startswith("N/A")]
        return len(valid)
    table_rows = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if set(stripped.replace("|", "").strip()) <= {"-", ":", " "}:
            continue
        table_rows += 1
    if table_rows:
        return max(table_rows - 1, 0)
    if status in {"empty", "withheld", "unavailable"}:
        return 0
    return None


def classify_output(text: str | None) -> str:
    if text is None:
        return "no_output"
    low = text.lower()
    if "withheld" in low:
        return "withheld"
    if "fred_api_key" in low or "not set" in low or "not configured" in low:
        return "not_configured"
    if (
        "data_unavailable" in low
        or "no_data_available" in low
        or "unavailable" in low
        or "could not be retrieved" in low
        or "fetch failed" in low
        or "request failed" in low
    ):
        return "unavailable"
    if (
        "no news found" in low
        or "no global news found" in low
        or "<no " in low
        or "no open prediction markets" in low
        or "none of the" in low
        or "no reddit posts found" in low
    ):
        return "empty"
    return "success"


def preview(text: str | None, limit: int = 280) -> str:
    if not text:
        return ""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def reason_for(status: str, text: str | None) -> str:
    if status == "success":
        return ""
    if status == "not_attempted":
        return "tool was not called in this run"
    if status == "not_configured":
        return "required credential is not set; app degrades or skips this source"
    if status == "withheld":
        return "withheld by the application's historical-date policy"
    if status == "empty":
        return "the source answered but had no items in the requested window"
    if status == "unavailable":
        return preview(text, 220)
    if status == "no_output":
        return "no output was captured"
    return preview(text, 220)


def find_files(root: Path, pattern: str) -> list[Path]:
    root = Path(root)
    if not root.exists():
        return []
    return sorted(root.rglob(pattern))
