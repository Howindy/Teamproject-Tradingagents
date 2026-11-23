"""Trusted semantic-evaluation runner for FR-10 deterministic financial metrics.

This module runs only from the trusted default-branch tool checkout.  It loads
fixed independent cases from ``docs/ci/financial-metrics-cases.json``, verifies
configuration/material hashes and candidate/baseline Git SHAs before making any
external model call, captures real analyst prompts in a fresh subprocess using
normal installed-package discovery (never injecting ``PYTHONPATH`` or
prepending ``src/`` to ``sys.path``), enforces the six-request budget with
``deepseek-flash`` (thinking explicitly disabled, zero retries), and scores
reports deterministically with fail-closed critical and ambiguity rules.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ci_checks import CiError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = PROJECT_ROOT / "docs" / "ci" / "financial-metrics-cases.json"
DEFAULT_RUBRIC_PATH = PROJECT_ROOT / "docs" / "ci" / "financial-metrics-rubric.md"

EXPECTED_MODEL_PROVIDER = "deepseek"
EXPECTED_MODEL_NAME = "deepseek-flash"
EXPECTED_BASE_URL = "https://api.deepseek.com"
MAX_REQUEST_BUDGET = 6
EXPECTED_CANDIDATE_CASE_IDS = ("FM-S01", "FM-S02", "FM-S03", "FM-S04")
EXPECTED_BASELINE_CASE_IDS = ("FM-S01", "FM-S02")
METRIC_ORDER = (
    "revenue_yoy_q",
    "revenue_yoy_a",
    "revenue_qoq",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "current_ratio",
    "liabilities_to_assets",
    "fcf_reported_span",
    "pe_fy",
)

METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue_yoy_q": ("revenue_yoy_q", "quarterly revenue yoy", "yoy revenue (q)"),
    "revenue_yoy_a": ("revenue_yoy_a", "annual revenue yoy", "fy revenue yoy"),
    "revenue_qoq": ("revenue_qoq", "revenue qoq", "sequential revenue"),
    "gross_margin": ("gross_margin", "gross margin"),
    "operating_margin": ("operating_margin", "operating margin"),
    "net_margin": ("net_margin", "net margin", "reported net margin"),
    "current_ratio": ("current_ratio", "current ratio"),
    "liabilities_to_assets": ("liabilities_to_assets", "liabilities / assets", "liabilities-to-assets"),
    "fcf_reported_span": ("fcf_reported_span", "reported-span fcf", "free cash flow"),
    "pe_fy": ("pe_fy", "fiscal-year p/e", "fy p/e"),
}

_CHILD_DRIVER = r"""
import importlib
import json
import sys
from datetime import date, datetime
from pathlib import Path
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

payload = json.loads(sys.stdin.read())
checkout_root = Path(payload["checkout_root"]).resolve()
expected_src = (checkout_root / "src").resolve()
mode = payload["mode"]

def _check_origin(module_name: str):
    mod = importlib.import_module(module_name)
    file_path = getattr(mod, "__file__", None)
    if not file_path:
        raise RuntimeError(f"module {module_name} has no __file__")
    resolved = Path(file_path).resolve()
    if not resolved.is_relative_to(expected_src):
        raise RuntimeError(f"module {module_name} origin {resolved} escapes {expected_src}")
    return mod, str(resolved)

origins = {}
_, origins["tradingagents"] = _check_origin("tradingagents")
analyst_mod, origins["fundamentals_analyst"] = _check_origin(
    "tradingagents.agents.analysts.fundamentals_analyst"
)

class _CaptureLLM(BaseChatModel):
    prompts: list = []

    @property
    def _llm_type(self) -> str:
        return "fr10-prompt-capture"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.prompts = [
            {"role": getattr(m, "type", "message"), "content": str(m.content)}
            for m in messages
        ]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="CAPTURE_ONLY"))])

llm = _CaptureLLM()
case = payload["case"]
ref_data = payload["reference_data"]

if mode == "baseline":
    factory = getattr(analyst_mod, "create_fundamentals_analyst")
    node = factory(llm)
    state = {
        "trade_date": case["as_of"],
        "company_of_interest": case["ticker"],
        "messages": [("human", case["task"] + "\n\n" + case["statement_material"])],
    }
    node(state)
    print(json.dumps({
        "status": "ok",
        "mode": mode,
        "origins": origins,
        "prompts": llm.prompts,
        "metric_block": "",
    }))
    raise SystemExit(0)

for mod_name in (
    "tradingagents.financials",
    "tradingagents.financials.models",
    "tradingagents.financials.metrics",
    "tradingagents.financials.service",
    "tradingagents.financials.wiring",
):
    _, origins[mod_name] = _check_origin(mod_name)

models_mod = importlib.import_module("tradingagents.financials.models")
service_mod = importlib.import_module("tradingagents.financials.service")
wiring_mod = importlib.import_module("tradingagents.financials.wiring")
from decimal import Decimal

CONCEPT_MAP = {
    "RevenueFromContractWithCustomerExcludingAssessedTax": ("revenue", 0),
    "Revenues": ("revenue", 1),
    "GrossProfit": ("gross_profit", 0),
    "OperatingIncomeLoss": ("operating_income", 0),
    "NetIncomeLoss": ("net_income", 0),
    "AssetsCurrent": ("current_assets", 0),
    "LiabilitiesCurrent": ("current_liabilities", 0),
    "Liabilities": ("liabilities", 0),
    "Assets": ("assets", 0),
    "EarningsPerShareDiluted": ("diluted_eps", 0),
    "NetCashProvidedByUsedInOperatingActivities": ("cfo", 0),
    "PaymentsToAcquirePropertyPlantAndEquipment": ("capex", 0),
}

def _parse_date(v):
    return date.fromisoformat(v) if v else None

class _ProjectedProvider:
    def fetch(self, ticker: str, as_of: date):
        facts = []
        selected = ref_data["selected_facts"]
        cik = None
        for fid in case["fact_ids"]:
            row = selected[fid]
            cik = str(row["subject_id"]).zfill(10)
            concept = row["concept"].split(":", 1)[-1]
            metric, rank = CONCEPT_MAP[concept]
            facts.append(models_mod.FinancialFact(
                fact_id=fid,
                subject_id=cik,
                metric=metric,
                value=Decimal(row["value"]),
                unit=row["unit"],
                currency=row["currency"],
                period_start=_parse_date(row["period_start"]),
                period_end=_parse_date(row["period_end"]),
                fiscal_year=row["fiscal_year"],
                fiscal_quarter=row["fiscal_quarter"],
                span=row["span"],
                filed_at=_parse_date(row["filed_at"]),
                accession=row["accession"],
                filing_ref=f"{row['filing_file']}#{row['inline_element_id']}",
                concept=concept,
                source_ref=f"{row['companyfacts_file']}#{row['companyfacts_pointer']}",
                calendar_id=row["issuer"],
                sign_rule="positive_outflow" if metric == "capex" else "as_reported",
                share_basis="common_shares" if metric == "diluted_eps" else "",
                basis_evidence=(f"{row['filing_file']}#{row['inline_element_id']}",) if metric == "diluted_eps" else (),
                concept_rank=rank,
                disclosure=tuple(sorted((k, str(val)) for k, val in row.items() if not isinstance(val, list))),
            ))
        pr_raw = ref_data["price_records"][case["issuer"]]
        completed_at = datetime.fromisoformat("2025-08-04T20:00:00+00:00")
        price_date = _parse_date(pr_raw["actual_price_date"])
        if case.get("price_override"):
            ov = case["price_override"]
            if ov.get("completed_at"):
                completed_at = datetime.fromisoformat(ov["completed_at"])
            if ov.get("actual_price_date"):
                price_date = _parse_date(ov["actual_price_date"])
        price = models_mod.PriceRecord(
            value=Decimal(pr_raw["value"]),
            currency=pr_raw["currency"],
            unit=pr_raw["unit"],
            price_date=price_date,
            completed_at=completed_at,
            expected_latest_session=_parse_date(pr_raw["actual_price_date"]),
            freshness_policy=pr_raw["freshness_policy"],
            source_ref=f"{pr_raw['source_file']}#{pr_raw['json_pointer']}",
            share_basis="common_shares",
            basis_evidence=(pr_raw["share_basis_evidence"]["event_snapshot"], pr_raw["json_pointer"]),
            completion_evidence=pr_raw["completion_evidence"],
        )
        return models_mod.FinancialInputs(subject_id=cik or case["ticker"], facts=tuple(facts), price=price)

factory = wiring_mod.build_metrics_factory(
    {"fr07_sec_enabled": True},
    data_factory=lambda clock: _ProjectedProvider(),
)
captured_result = {"text": ""}
def wrapped_factory(state):
    res = factory(state)
    if res is not None:
        captured_result["text"] = res.text
    return res

create_fn = getattr(analyst_mod, "create_fundamentals_analyst")
node = create_fn(llm, metrics_factory=wrapped_factory)
state = {
    "trade_date": case["as_of"],
    "company_of_interest": case["ticker"],
    "messages": [("human", case["task"] + "\n\n" + case["statement_material"])],
}
node(state)
print(json.dumps({
    "status": "ok",
    "mode": mode,
    "origins": origins,
    "prompts": llm.prompts,
    "metric_block": captured_result["text"],
}))
"""


def sha256_file(path: Path) -> str:
    # Git stores these text materials with LF; Windows checkouts can use CRLF.
    # Normalize only that checkout conversion, not whitespace or JSON content.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _resolve_trusted_file(value: str | Path, default_path: Path, root: Path) -> Path:
    candidate = Path(value) if value else default_path
    candidate = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    root_resolved = root.resolve()
    if not candidate.is_relative_to(root_resolved):
        raise CiError(f"trusted evaluation file escapes root: {candidate}")
    if not candidate.is_file():
        raise CiError(f"trusted evaluation file does not exist: {candidate}")
    return candidate


def _verify_git_head(repo_root: Path, expected_sha: str, label: str) -> str:
    if not expected_sha or not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise CiError(f"{label} SHA must be a full 40-char hex SHA, got {expected_sha!r}")
    if not repo_root.is_dir():
        raise CiError(f"{label} directory does not exist: {repo_root}")
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if proc.returncode != 0:
        raise CiError(f"cannot inspect {label} HEAD: {proc.stderr.strip()}")
    actual = proc.stdout.strip()
    if actual != expected_sha:
        raise CiError(f"{label} HEAD {actual} does not match expected SHA {expected_sha}")
    return actual


def _load_and_verify_materials(
    config: Mapping[str, Any],
    *,
    trusted_root: Path,
) -> tuple[dict[str, Any], str, str]:
    dataset_cfg = config.get("dataset")
    rubric_cfg = config.get("rubric")
    model_cfg = config.get("model")
    exec_cfg = config.get("execution") or {}
    if not isinstance(dataset_cfg, Mapping) or not isinstance(rubric_cfg, Mapping) or not isinstance(model_cfg, Mapping):
        raise CiError("semantic configuration missing dataset, rubric, or model mapping")

    cases_path = _resolve_trusted_file(
        str(dataset_cfg.get("path") or ""),
        trusted_root / "docs" / "ci" / "financial-metrics-cases.json",
        trusted_root,
    )
    rubric_path = _resolve_trusted_file(
        str(rubric_cfg.get("path") or ""),
        trusted_root / "docs" / "ci" / "financial-metrics-rubric.md",
        trusted_root,
    )
    actual_cases_sha = sha256_file(cases_path)
    expected_cases_sha = str(dataset_cfg.get("sha256") or "")
    if expected_cases_sha and actual_cases_sha != expected_cases_sha:
        raise CiError(
            f"dataset hash mismatch: expected {expected_cases_sha}, got {actual_cases_sha}"
        )
    actual_rubric_sha = sha256_file(rubric_path)
    expected_rubric_sha = str(rubric_cfg.get("sha256") or "")
    if expected_rubric_sha and actual_rubric_sha != expected_rubric_sha:
        raise CiError(
            f"rubric hash mismatch: expected {expected_rubric_sha}, got {actual_rubric_sha}"
        )
    cases_payload = json.loads(cases_path.read_text(encoding="utf-8"))
    if cases_payload.get("dataset_version") != dataset_cfg.get("version"):
        raise CiError("dataset version mismatch between semantic config and cases file")

    configured_ids = tuple(
        str(item["id"] if isinstance(item, Mapping) else item)
        for item in (dataset_cfg.get("cases") or ())
    )
    payload_ids = tuple(str(c["case_id"]) for c in cases_payload.get("cases", ()))
    if configured_ids != EXPECTED_CANDIDATE_CASE_IDS or payload_ids != EXPECTED_CANDIDATE_CASE_IDS:
        raise CiError(
            f"case list mismatch: config={configured_ids}, payload={payload_ids}"
        )

    max_requests = int(exec_cfg.get("max_completion_requests", MAX_REQUEST_BUDGET))
    if max_requests <= 0 or max_requests > MAX_REQUEST_BUDGET:
        raise CiError(f"max_completion_requests exceeds cap ({max_requests} > {MAX_REQUEST_BUDGET})")

    provider = str(model_cfg.get("provider") or "")
    model_name = str(model_cfg.get("model") or "")
    if provider != EXPECTED_MODEL_PROVIDER or model_name != EXPECTED_MODEL_NAME:
        raise CiError(
            f"unapproved model configuration: provider={provider!r}, model={model_name!r}"
        )
    model_inner = model_cfg.get("configuration") or {}
    thinking = (model_inner.get("extra_body") or {}).get("thinking") or {}
    if thinking.get("type") != "disabled":
        raise CiError("model configuration must explicitly disable thinking")

    return cases_payload, actual_cases_sha, actual_rubric_sha


def _run_prompt_capture_subprocess(
    *,
    checkout_root: Path,
    mode: str,
    case: Mapping[str, Any],
    reference_data: Mapping[str, Any],
    python_executable: str,
    timeout: int = 60,
) -> dict[str, Any]:
    env = {
        key: val
        for key, val in os.environ.items()
        if key.upper() not in {"PYTHONPATH", "PYTHONHOME"}
    }
    child_input = json.dumps({
        "checkout_root": str(checkout_root),
        "mode": mode,
        "case": dict(case),
        "reference_data": dict(reference_data),
    })
    proc = subprocess.run(
        [python_executable, "-B", "-c", _CHILD_DRIVER],
        input=child_input,
        cwd=str(checkout_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise CiError(f"{mode} loader failed for {case['case_id']}: {detail}")
    try:
        parsed = json.loads(proc.stdout.strip())
    except json.JSONDecodeError as exc:
        raise CiError(f"{mode} loader returned invalid JSON: {exc}") from exc
    if parsed.get("status") != "ok":
        raise CiError(f"{mode} loader returned non-ok status: {parsed}")
    return parsed


def _build_deepseek_transport(
    api_key: str,
    model_cfg: Mapping[str, Any],
) -> Callable[[Mapping[str, Any]], dict[str, Any]]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise CiError(f"openai client unavailable for live semantic evaluation: {exc}") from exc

    cfg = model_cfg.get("configuration") or {}
    base_url = str(model_cfg.get("base_url") or EXPECTED_BASE_URL)
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        max_retries=int(cfg.get("max_retries", 0)),
        timeout=float(cfg.get("timeout_seconds", 120)),
    )

    def call(request_spec: Mapping[str, Any]) -> dict[str, Any]:
        response = client.chat.completions.create(
            model=str(model_cfg["model"]),
            messages=list(request_spec["messages"]),
            temperature=float(cfg.get("temperature", 0)),
            max_tokens=int(cfg.get("max_tokens", 4096)),
            stream=False,
            n=1,
            extra_body=dict(cfg.get("extra_body") or {"thinking": {"type": "disabled"}}),
        )
        choice = response.choices[0]
        content = getattr(getattr(choice, "message", None), "content", "") or ""
        usage = response.usage.model_dump() if getattr(response, "usage", None) else {}
        return {
            "content": content,
            "finish_reason": getattr(choice, "finish_reason", ""),
            "model": getattr(response, "model", ""),
            "response_id": getattr(response, "id", ""),
            "usage": usage,
        }

    return call


def _contains_metric_row(prompt_text: str, expected_row: Mapping[str, Any]) -> bool:
    metric_id = str(expected_row["metric_id"])
    if metric_id not in prompt_text:
        return False
    if expected_row["status"] == "computed":
        expected = str(expected_row["expected_display"])
        return expected in prompt_text
    reason = str(expected_row.get("reason") or "")
    return "n/a" in prompt_text and reason in prompt_text


def _find_metric_windows(report_lower: str, metric_id: str) -> list[str]:
    windows: list[str] = []
    aliases = METRIC_ALIASES.get(metric_id, (metric_id,))
    for alias in aliases:
        start = 0
        while True:
            idx = report_lower.find(alias, start)
            if idx == -1:
                break
            line_start = report_lower.rfind("\n", 0, idx)
            lo = line_start + 1 if line_start != -1 else max(0, idx - 60)
            hi = min(len(report_lower), idx + 220)
            windows.append(report_lower[lo:hi])
            start = idx + len(alias)
    return windows


def _extract_numeric_tokens(text: str) -> list[str]:
    return re.findall(r"-?\d[\d,]*(?:\.\d+)?", text)


def _norm_num(token: str) -> str:
    return token.replace(",", "")


def _asserts_numeric_for_na_metric(window: str, metric_id: str) -> bool:
    for alias in METRIC_ALIASES.get(metric_id, (metric_id,)):
        pattern = re.escape(alias) + r"[\s|:=`*-]+(-?\d[\d,]*(?:\.\d+)?)\s*(?:%|x|usd|million)"
        if re.search(pattern, window):
            return True
    return False


def score_candidate_case(
    case: Mapping[str, Any],
    captured_prompts: Sequence[Mapping[str, str]],
    response_text: str,
) -> dict[str, Any]:
    """Deterministically score one candidate report against independent expectations."""
    system_prompt = "\n".join(
        m.get("content", "") for m in captured_prompts if m.get("role") == "system"
    )
    report_lower = response_text.lower()
    expected_rows: Sequence[Mapping[str, Any]] = case["expected_rows"]

    critical_failures: list[str] = []
    needs_review_reasons: list[str] = []

    if not all(_contains_metric_row(system_prompt, row) for row in expected_rows):
        critical_failures.append("prompt_missing_metric_table")

    if re.search(r"ttm\s+p/?e|trailing\s+twelve[- ]month\s+p/?e", report_lower):
        critical_failures.append("fy_as_ttm_mislabel")
    if re.search(r"(?:single[- ]quarter|quarterly)\s+fcf|(?:q[1-4])\s+free\s+cash\s+flow", report_lower):
        critical_failures.append("ytd_as_quarter_mislabel")

    d1_ok = True
    d2_ok = True
    d3_ok = True
    per_metric: dict[str, str] = {}

    for row in expected_rows:
        mid = str(row["metric_id"])
        windows = _find_metric_windows(report_lower, mid)
        if not windows:
            d1_ok = False
            needs_review_reasons.append(f"missing_metric_mention:{mid}")
            per_metric[mid] = "missing"
            continue
        combined = "\n".join(windows)
        if row["status"] == "computed":
            target = str(row["expected_display"])
            target_comma = f"{int(target):,}" if target.isdigit() else target
            has_val = (target in combined) or (target_comma in combined)
            if not has_val:
                d1_ok = False
                nums = {_norm_num(n) for n in _extract_numeric_tokens(combined)}
                if nums:
                    critical_failures.append(f"wrong_metric_value:{mid}")
                    per_metric[mid] = "wrong_value"
                else:
                    needs_review_reasons.append(f"ambiguous_metric_claim:{mid}")
                    per_metric[mid] = "ambiguous"
            else:
                per_metric[mid] = "ok"
            unit = str(row.get("unit") or "")
            if (
                (unit == "%" and "%" not in combined and "percent" not in combined)
                or (unit == "x" and "x" not in combined and "times" not in combined)
                or (unit == "USD_millions" and "million" not in combined and "usd_millions" not in combined)
            ):
                d2_ok = False
        else:
            reason = str(row.get("reason") or "")
            has_na = any(
                marker in combined
                for marker in ("n/a", "not available", "unavailable", reason.lower())
            )
            if mid == "pe_fy" and case["case_id"] == "FM-S04" and (
                "33.4" in combined or ("eligible" in combined and "not eligible" not in combined)
            ):
                critical_failures.append("future_or_post_cutoff_price_used")
                d1_ok = False
                d3_ok = False
                per_metric[mid] = "post_cutoff_price_used"
            elif any(_asserts_numeric_for_na_metric(w, mid) for w in windows):
                critical_failures.append(f"invented_na_metric:{mid}")
                d1_ok = False
                per_metric[mid] = "invented"
            elif not has_na:
                d1_ok = False
                needs_review_reasons.append(f"ambiguous_na_claim:{mid}")
                per_metric[mid] = "ambiguous_na"
            else:
                if reason and reason.lower() not in combined and "unavailable" not in combined:
                    d2_ok = False
                per_metric[mid] = "na_ok"

    # Period/basis check (D2)
    if case["issuer"] == "aapl":
        if "2025" not in report_lower or ("ytd" not in report_lower and "nine" not in report_lower and "9-month" not in report_lower and "9 month" not in report_lower):
            d2_ok = False
    else:
        if "2025" not in report_lower or ("ytd" not in report_lower and "six" not in report_lower and "6-month" not in report_lower and "6 month" not in report_lower):
            d2_ok = False

    # Traceability/no-lookahead check (D3)
    if (
        case["case_id"] == "FM-S04"
        and re.search(r"completed\s+before\s+cutoff|eligible\s+price", report_lower)
        and "not eligible" not in report_lower
        and "after cutoff" not in report_lower
    ):
        d3_ok = False
        critical_failures.append("post_cutoff_price_claimed_eligible")
    if "sec" not in report_lower and "10-q" not in report_lower and "10-k" not in report_lower and "filing" not in report_lower and "accession" not in report_lower:
        d3_ok = False

    # D4: useful interpretation without treating n/a as zero
    d4_ok = (
        len(response_text.strip()) >= 120
        and not re.search(r"(?:gross|operating)\s+margin\s+(?:is|of|=)\s*0(?:\.0+)?%", report_lower)
        and d1_ok
    )
    # D5: retained ordinary fundamental task coverage (structured sections + markdown table)
    d5_ok = (
        "|" in response_text
        and "---" in response_text
        and len(response_text.split()) >= 40
    )

    dims = {
        "D1": d1_ok,
        "D2": d2_ok,
        "D3": d3_ok,
        "D4": d4_ok,
        "D5": d5_ok,
    }
    return {
        "case_id": case["case_id"],
        "dimensions": dims,
        "passed_checks": sum(1 for v in dims.values() if v),
        "total_checks": 5,
        "critical_failures": sorted(set(critical_failures)),
        "needs_review_reasons": sorted(set(needs_review_reasons)),
        "per_metric": per_metric,
    }


def score_baseline_d5(response_text: str) -> bool:
    return "|" in response_text and "---" in response_text and len(response_text.split()) >= 40


def evaluate(
    config: Mapping[str, Any],
    candidate_sha: str,
    *,
    trusted_root: Path | None = None,
    candidate_root: Path | None = None,
    baseline_root: Path | None = None,
    baseline_sha: str | None = None,
    output_dir: Path | None = None,
    model_transport: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    python_executable: str | None = None,
    baseline_python_executable: str | None = None,
) -> dict[str, Any]:
    """Execute the trusted FR-10 fixed semantic evaluation and return a structured record."""
    root = (trusted_root or PROJECT_ROOT).resolve()
    cand_root = (candidate_root or (root / "candidate")).resolve()
    out_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="fr10-semantic-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    py_exe = python_executable or sys.executable
    base_py_exe = baseline_python_executable or py_exe

    details: dict[str, Any] = {
        "schema_version": "1.0",
        "requirement_id": "FR-10",
        "candidate_sha": candidate_sha,
        "baseline_sha": baseline_sha or "",
        "recorded_at": dt.datetime.now(dt.UTC).isoformat(),
        "request_count": 0,
        "usage_totals": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "import_origins": {},
        "cases": [],
        "baseline_cases": [],
        "errors": [],
    }

    def _finalize(status: str) -> dict[str, Any]:
        details["status"] = status
        details_path = out_dir / "semantic-details.json"
        details_bytes = json.dumps(details, indent=2, sort_keys=True).encode("utf-8")
        details_path.write_bytes(details_bytes)
        details["details_path"] = str(details_path)
        details["details_sha256"] = hashlib.sha256(details_bytes).hexdigest()
        return details

    try:
        if str(config.get("status", "unapproved")) != "approved":
            raise CiError("semantic configuration is not approved")
        cases_payload, cases_sha, rubric_sha = _load_and_verify_materials(config, trusted_root=root)
        details["dataset_version"] = cases_payload["dataset_version"]
        details["dataset_sha256"] = cases_sha
        details["rubric_version"] = str((config.get("rubric") or {}).get("version") or "")
        details["rubric_sha256"] = rubric_sha
        details["model_config"] = {
            "provider": config["model"]["provider"],
            "model": config["model"]["model"],
            "base_url": config["model"].get("base_url", EXPECTED_BASE_URL),
            "configuration": config["model"].get("configuration", {}),
        }

        _verify_git_head(cand_root, candidate_sha, "candidate")
        if baseline_root is not None:
            if not baseline_sha:
                raise CiError("baseline_sha is required when baseline_root is supplied")
            _verify_git_head(baseline_root.resolve(), baseline_sha, "baseline")

        transport = model_transport
        if transport is None:
            api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
            if not api_key:
                raise CiError("DEEPSEEK_API_KEY is not configured; semantic evaluation cannot call model")
            transport = _build_deepseek_transport(api_key, config["model"])

        max_requests = int((config.get("execution") or {}).get("max_completion_requests", MAX_REQUEST_BUDGET))
        ref_data = cases_payload["reference_data"]
        cases_by_id = {c["case_id"]: c for c in cases_payload["cases"]}

        all_critical: list[str] = []
        all_needs_review: list[str] = []
        total_passed_checks = 0
        total_checks = 0
        d1_to_3_all_pass = True
        cand_d5: dict[str, bool] = {}

        for cid in EXPECTED_CANDIDATE_CASE_IDS:
            case = cases_by_id[cid]
            captured = _run_prompt_capture_subprocess(
                checkout_root=cand_root,
                mode="candidate",
                case=case,
                reference_data=ref_data,
                python_executable=py_exe,
            )
            details["import_origins"][f"candidate:{cid}"] = captured["origins"]

            if details["request_count"] >= max_requests:
                raise CiError(f"request budget exceeded before {cid}")
            details["request_count"] += 1

            messages = [
                {"role": "system" if m["role"] == "system" else "user", "content": m["content"]}
                for m in captured["prompts"]
            ]
            resp = transport({"case_id": cid, "variant": "candidate", "messages": messages})
            finish_reason = str(resp.get("finish_reason") or "")
            content = str(resp.get("content") or "")
            usage = resp.get("usage") or {}
            details["usage_totals"]["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            details["usage_totals"]["completion_tokens"] += int(usage.get("completion_tokens") or 0)
            details["usage_totals"]["total_tokens"] += int(usage.get("total_tokens") or 0)

            if finish_reason == "length":
                raise CiError(f"candidate output truncated for {cid}")
            if not content.strip():
                raise CiError(f"candidate output empty for {cid}")

            scored = score_candidate_case(case, captured["prompts"], content)
            scored["finish_reason"] = finish_reason
            scored["usage"] = usage
            scored["captured_prompt_chars"] = sum(len(m["content"]) for m in messages)
            scored["response_text"] = content
            details["cases"].append(scored)

            total_passed_checks += scored["passed_checks"]
            total_checks += scored["total_checks"]
            if not (scored["dimensions"]["D1"] and scored["dimensions"]["D2"] and scored["dimensions"]["D3"]):
                d1_to_3_all_pass = False
            cand_d5[cid] = scored["dimensions"]["D5"]
            all_critical.extend(f"{cid}:{c}" for c in scored["critical_failures"])
            all_needs_review.extend(f"{cid}:{r}" for r in scored["needs_review_reasons"])

        baseline_d5: dict[str, bool] = {}
        if baseline_root is not None:
            b_root = baseline_root.resolve()
            for cid in EXPECTED_BASELINE_CASE_IDS:
                case = cases_by_id[cid]
                captured = _run_prompt_capture_subprocess(
                    checkout_root=b_root,
                    mode="baseline",
                    case=case,
                    reference_data=ref_data,
                    python_executable=base_py_exe,
                )
                details["import_origins"][f"baseline:{cid}"] = captured["origins"]

                if details["request_count"] >= max_requests:
                    raise CiError(f"request budget exceeded before baseline {cid}")
                details["request_count"] += 1

                messages = [
                    {"role": "system" if m["role"] == "system" else "user", "content": m["content"]}
                    for m in captured["prompts"]
                ]
                resp = transport({"case_id": cid, "variant": "baseline", "messages": messages})
                finish_reason = str(resp.get("finish_reason") or "")
                content = str(resp.get("content") or "")
                usage = resp.get("usage") or {}
                details["usage_totals"]["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
                details["usage_totals"]["completion_tokens"] += int(usage.get("completion_tokens") or 0)
                details["usage_totals"]["total_tokens"] += int(usage.get("total_tokens") or 0)

                if finish_reason == "length":
                    raise CiError(f"baseline output truncated for {cid}")
                if not content.strip():
                    raise CiError(f"baseline output empty for {cid}")

                b_d5 = score_baseline_d5(content)
                baseline_d5[cid] = b_d5
                details["baseline_cases"].append({
                    "case_id": cid,
                    "d5_pass": b_d5,
                    "finish_reason": finish_reason,
                    "usage": usage,
                    "response_text": content,
                })

        d5_non_regression = all(
            cand_d5[cid] or not baseline_d5[cid]
            for cid in baseline_d5
        )
        thresholds = config.get("thresholds") or {}
        min_passed = int(thresholds.get("candidate_min_passed_checks", 18))
        pass_rate = (total_passed_checks / total_checks) if total_checks else 0.0

        details["candidate_summary"] = {
            "passed_checks": total_passed_checks,
            "total_checks": total_checks,
            "pass_rate": round(pass_rate, 4),
            "d1_to_3_all_pass": d1_to_3_all_pass,
            "d5_non_regression": d5_non_regression,
            "critical_failures": all_critical,
            "needs_review": all_needs_review,
        }
        details["baseline_summary"] = {
            "paired_cases": list(baseline_d5.keys()),
            "d5_pass": baseline_d5,
        }

        if all_critical:
            return _finalize("failed")
        if all_needs_review:
            return _finalize("needs_review")
        if not d1_to_3_all_pass or total_passed_checks < min_passed or not d5_non_regression:
            return _finalize("failed")
        return _finalize("passed")
    except Exception as exc:
        details["errors"].append(str(exc))
        return _finalize("failed")
