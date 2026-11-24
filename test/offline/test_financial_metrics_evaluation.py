"""Offline tests for FR-10 preparation infrastructure (P01-P07).

These tests validate requirements/projection consistency, deterministic scoring,
subprocess package-discovery origin checks, fail-closed prerequisite/execution
gates, and preparation-scope boundaries using controlled fake candidates and
mocked external model transports.  They do not claim PR 2 feature migration or
live model quality.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
CASES_PATH = ROOT / "docs" / "ci" / "financial-metrics-cases.json"
RUBRIC_PATH = ROOT / "docs" / "ci" / "financial-metrics-rubric.md"
SEMANTIC_CFG_PATH = ROOT / "docs" / "ci" / "semantic_eval.yaml"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(SCRIPTS))
ci_checks = _load_module("ci_checks", SCRIPTS / "ci_checks.py")
ci_semantic_eval = _load_module("ci_semantic_eval", SCRIPTS / "ci_semantic_eval.py")
fm_eval = _load_module("financial_metrics_eval", SCRIPTS / "financial_metrics_eval.py")


def _approved_config() -> dict[str, Any]:
    cfg = copy.deepcopy(ci_checks.load_yaml(SEMANTIC_CFG_PATH))
    cfg["status"] = "approved"
    cfg["approval"] = {
        "approved_by": "human-reviewer",
        "approved_at": "2026-11-23T12:00:00Z",
        "evidence": ["https://github.com/Howindy/Teamproject-Tradingagents/pull/14#issuecomment-1"],
    }
    return cfg


def _good_report(case: dict[str, Any]) -> str:
    facts = json.loads(CASES_PATH.read_text(encoding="utf-8"))["reference_data"]["selected_facts"]
    rows_md = ["| metric_id | value | period | source |", "|---|---|---|---|"]
    for row in case["expected_rows"]:
        mid = row["metric_id"]
        if row["status"] == "computed":
            unit = row["unit"]
            val = row["expected_display"]
            if unit == "%":
                cell = f"{val}%"
            elif unit == "x":
                cell = f"{val}x"
            else:
                cell = f"{val} USD_millions"
            refs = sorted({facts[fid]["accession"] for fid in row["input_fact_ids"] if fid in facts})
            rows_md.append(f"| {mid} | {cell} | {row['period']} | SEC 10-Q/10-K {'; '.join(refs)} |")
        else:
            rows_md.append(f"| {mid} | n/a ({row['reason']}) | {row['period']} | n/a |")

    if case["issuer"] == "aapl":
        period_note = "2025 Q3 fiscal results, FY2024 vs FY2023 annual comparison, and nine-month YTD 2025 cash flow."
    else:
        period_note = "2025 Q2 fiscal results, FY2024 vs FY2023 annual comparison, and six-month YTD 2025 cash flow."

    extra = ""
    if case["case_id"] == "FM-S03":
        extra = " Quarterly revenue_yoy_q is n/a (missing_comparison) because prior-year Q3 is absent; revenue_qoq remains -1.4%."
    elif case["case_id"] == "FM-S04":
        extra = " Fiscal-year pe_fy is n/a (price_not_completed) because the 2025-08-04 close is not eligible after the 2025-08-05 cutoff."

    return (
        f"Fundamental Analysis for {case['company_name']} ({case['ticker']}) as of {case['as_of']}.\n\n"
        f"Based on disclosed SEC 10-Q and 10-K filings, {period_note} "
        "All computed figures follow the program financial metrics table and unavailable rows are kept explicitly as n/a without zero-fill or proxy substitution."
        " Growth and sequential decline describe different comparisons and must not be conflated. "
        "Profitability reflects disclosed margins, not proxies for absent concepts. Liquidity is indicated "
        "by current assets relative to current liabilities; leverage reflects liabilities relative to assets. "
        "Cash generation is the reported YTD operating flow less PP&E payments. Valuation uses fiscal-year "
        "earnings and an eligible completed price, not trailing earnings. Limitations include missing "
        "inputs and the historical disclosure cutoff; these ratios alone are not a trade authorization."
        + extra
        + "\n\n"
        + "\n".join(rows_md)
        + "\n"
    )


def _baseline_report(case: dict[str, Any]) -> str:
    return (
        f"Baseline Fundamental Analysis for {case['company_name']} ({case['ticker']}) as of {case['as_of']}.\n\n"
        "Summary of disclosed SEC financial statements and market context with standard task sections and qualifications.\n\n"
        "| item | detail |\n|---|---|\n| issuer | "
        + case["ticker"]
        + " |\n"
    )


def _init_git_repo(repo_dir: Path, files: dict[str, str]) -> str:
    repo_dir.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        target = repo_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo_dir, check=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True).strip()


def _synthetic_candidate_files(*, include_financials: bool = True) -> dict[str, str]:
    files = {
        "src/tradingagents/__init__.py": '__version__ = "0.7.0"\n',
        "src/tradingagents/agents/__init__.py": "",
        "src/tradingagents/agents/analysts/__init__.py": "",
        "src/tradingagents/agents/analysts/fundamentals_analyst.py": (
            "def create_fundamentals_analyst(llm, metrics_factory=None):\n"
            "    def node(state):\n"
            "        block = ''\n"
            "        if metrics_factory is not None:\n"
            "            res = metrics_factory(state)\n"
            "            if res is not None:\n"
            "                block = res.text\n"
            "        from langchain_core.messages import SystemMessage, HumanMessage\n"
            "        msgs = [SystemMessage(content='Program metrics:\\n' + block), HumanMessage(content=str(state['messages'][0][1]))]\n"
            "        llm.invoke(msgs)\n"
            "        return {'fundamentals_report': 'done'}\n"
            "    return node\n"
        ),
    }
    if include_financials:
        files.update({
            "src/tradingagents/financials/__init__.py": "",
            "src/tradingagents/financials/models.py": (
                "from dataclasses import dataclass\n"
                "@dataclass(frozen=True)\n"
                "class EvaluationClock:\n"
                "    as_of: object\n"
                "    cutoff: object\n"
                "    today: object\n"
                "@dataclass(frozen=True)\n"
                "class FinancialFact:\n"
                "    fact_id: str\n"
                "    subject_id: str\n"
                "    metric: str\n"
                "    value: object\n"
                "    unit: str\n"
                "    currency: str\n"
                "    period_start: object\n"
                "    period_end: object\n"
                "    fiscal_year: object\n"
                "    fiscal_quarter: object\n"
                "    span: str\n"
                "    filed_at: object\n"
                "    accession: str\n"
                "    filing_ref: str\n"
                "    concept: str\n"
                "    source_ref: str\n"
                "    calendar_id: str = ''\n"
                "    sign_rule: str = 'unknown'\n"
                "    share_basis: str = ''\n"
                "    basis_evidence: tuple = ()\n"
                "    concept_rank: int = 0\n"
                "    disclosure: tuple = ()\n"
                "@dataclass(frozen=True)\n"
                "class PriceRecord:\n"
                "    value: object\n"
                "    currency: str\n"
                "    unit: str\n"
                "    price_date: object\n"
                "    completed_at: object\n"
                "    expected_latest_session: object\n"
                "    freshness_policy: str\n"
                "    source_ref: str\n"
                "    share_basis: str\n"
                "    basis_evidence: tuple\n"
                "    completion_evidence: str\n"
                "@dataclass(frozen=True)\n"
                "class FinancialInputs:\n"
                "    subject_id: str\n"
                "    facts: tuple = ()\n"
                "    price: object = None\n"
            ),
            "src/tradingagents/financials/metrics.py": "",
            "src/tradingagents/financials/service.py": "",
            "src/tradingagents/financials/wiring.py": (
                "from datetime import datetime\n"
                "def build_metrics_factory(config, *, data_factory=None):\n"
                "    def factory(state):\n"
                "        prov = data_factory(None)\n"
                "        inputs = prov.fetch(state['company_of_interest'], datetime.fromisoformat(state['trade_date']).date())\n"
                "        fact_ids = {f.fact_id for f in inputs.facts}\n"
                "        is_xom = state['company_of_interest'] == 'XOM'\n"
                "        is_s03 = 'aapl.rev.q3.2024' not in fact_ids and not is_xom\n"
                "        is_s04 = inputs.price.completed_at.isoformat() > '2025-08-05T04:00:00+00:00'\n"
                "        if is_xom:\n"
                "            rows = [\n"
                "                '| revenue_yoy_q | -12.4 % |',\n"
                "                '| revenue_yoy_a | 1.5 % |',\n"
                "                '| revenue_qoq | -2.0 % |',\n"
                "                '| gross_margin | n/a: missing_input |',\n"
                "                '| operating_margin | n/a: missing_input |',\n"
                "                '| net_margin | 8.7 % |',\n"
                "                '| current_ratio | 1.2 x |',\n"
                "                '| liabilities_to_assets | 39.7 % |',\n"
                "                '| fcf_reported_span | 12322 USD_millions |',\n"
                "                '| pe_fy | 13.7 x |',\n"
                "            ]\n"
                "        else:\n"
                "            rows = [\n"
                "                '| revenue_yoy_q | n/a: missing_comparison |' if is_s03 else '| revenue_yoy_q | 9.6 % |',\n"
                "                '| revenue_yoy_a | 2.0 % |',\n"
                "                '| revenue_qoq | -1.4 % |',\n"
                "                '| gross_margin | 46.5 % |',\n"
                "                '| operating_margin | 30.0 % |',\n"
                "                '| net_margin | 24.9 % |',\n"
                "                '| current_ratio | 0.9 x |',\n"
                "                '| liabilities_to_assets | 80.1 % |',\n"
                "                '| fcf_reported_span | 72281 USD_millions |',\n"
                "                '| pe_fy | n/a: price_not_completed |' if is_s04 else '| pe_fy | 33.4 x |',\n"
                "            ]\n"
                "        return type('R', (), {'text': '\\n'.join(rows)})()\n"
                "    return factory\n"
            ),
        })
    return files


def _install_site_pth(tmp_path: Path, name: str, src_dir: Path) -> str:
    """Create a lightweight launcher using standard site-packages .pth discovery (no PYTHONPATH)."""
    import langchain_core

    deps_site = Path(langchain_core.__file__).resolve().parents[1]
    venv_dir = tmp_path / f"venv_{name}"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", "--system-site-packages", str(venv_dir)], check=True)
    py_candidates = list(venv_dir.glob("Scripts/python.exe")) + list(venv_dir.glob("bin/python"))
    assert py_candidates, "venv python not found"
    sp_candidates = list(venv_dir.glob("Lib/site-packages")) + list(venv_dir.glob("lib/python*/site-packages"))
    assert sp_candidates, "venv site-packages not found"
    (sp_candidates[0] / "00_candidate_pkg.pth").write_text(str(src_dir.resolve()) + "\n", encoding="utf-8")
    (sp_candidates[0] / "zz_runtime_deps.pth").write_text(str(deps_site) + "\n", encoding="utf-8")
    return str(py_candidates[0])


def test_p01_requirements_inventory_includes_fr10_and_rejects_duplicates(tmp_path: Path):
    """P01 / FR-10: registry passes schema with 14/65 and 7/37 active counts."""
    result = ci_checks.schema_check(
        ROOT / "docs" / "req" / "requirements.yaml",
        ROOT / "docs" / "req" / "req-schema.json",
    )
    assert result["errors"] == []
    assert result["counts"] == {
        "requirements": 14,
        "fit_criteria": 65,
        "active_requirements": 7,
        "active_fit_criteria": 37,
        "deferred_requirements": 7,
        "deferred_fit_criteria": 28,
    }

    doc = yaml.safe_load((ROOT / "docs" / "req" / "requirements.yaml").read_text(encoding="utf-8"))
    fr10 = next(r for r in doc["requirements"] if r["id"] == "FR-10")
    assert fr10["status"] == "approved"
    assert [fc["id"] for fc in fr10["fit_criterion"]] == [
        f"FR-10-FC{i:02d}" for i in range(1, 11)
    ]

    bad = copy.deepcopy(doc)
    bad["requirements"].append(copy.deepcopy(fr10))
    bad_path = tmp_path / "dup.yaml"
    bad_path.write_text(yaml.safe_dump(bad), encoding="utf-8")
    bad_res = ci_checks.schema_check(bad_path, ROOT / "docs" / "req" / "req-schema.json")
    assert any("duplicate" in err for err in bad_res["errors"])


def test_p02_fixed_projection_provenance_and_mutation_detection(tmp_path: Path):
    """P02 / FR-10-FC01, FR-10-FC02, FR-10-FC03, FR-10-FC06: lossless projection & hash gate."""
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    assert payload["provenance"]["source_commit"] == "7e676fb00fff319930685a9fa059265f3061aeff"
    assert payload["provenance"]["reference_version"] == "fr07-sec-reference-v1"
    assert len(payload["provenance"]["source_blobs"]) == 14
    assert len(payload["reference_data"]["selected_facts"]) == 30
    assert len(payload["reference_data"]["expected_metrics"]) == 20

    cases_by_id = {c["case_id"]: c for c in payload["cases"]}
    assert tuple(cases_by_id) == ("FM-S01", "FM-S02", "FM-S03", "FM-S04")
    assert "aapl.rev.q3.2024" not in cases_by_id["FM-S03"]["fact_ids"]
    s03_yoy = next(r for r in cases_by_id["FM-S03"]["expected_rows"] if r["metric_id"] == "revenue_yoy_q")
    assert s03_yoy["status"] == "n/a" and s03_yoy["reason"] == "missing_comparison"
    s04_pe = next(r for r in cases_by_id["FM-S04"]["expected_rows"] if r["metric_id"] == "pe_fy")
    assert s04_pe["status"] == "n/a" and s04_pe["reason"] == "price_not_completed"

    # Hash mismatch in trusted config must fail before any model call.
    cfg = _approved_config()
    cfg["dataset"]["sha256"] = "0" * 64
    res = fm_eval.evaluate(cfg, "a" * 40, output_dir=tmp_path / "out")
    assert res["status"] == "failed"
    assert res["request_count"] == 0
    assert any("dataset hash mismatch" in e for e in res["errors"])

    # Git LF and Windows CRLF checkouts bind the same frozen text; content
    # mutations still change the digest (no JSON reserialization/whitespace trim).
    lf = CASES_PATH.read_bytes().replace(b"\r\n", b"\n")
    lf_path, crlf_path = tmp_path / "lf.json", tmp_path / "crlf.json"
    lf_path.write_bytes(lf)
    crlf_path.write_bytes(lf.replace(b"\n", b"\r\n"))
    expected_hash = _approved_config()["dataset"]["sha256"]
    assert fm_eval.sha256_file(lf_path) == expected_hash
    assert fm_eval.sha256_file(crlf_path) == expected_hash
    crlf_path.write_bytes(crlf_path.read_bytes().replace(b"94036000000", b"94036000001", 1))
    assert fm_eval.sha256_file(crlf_path) != expected_hash


def test_p03_scorer_passes_valid_and_rejects_critical_ambiguous_and_dim5_regressions():
    """P03 / FR-10-FC02, FR-10-FC03, FR-10-FC06, FR-10-FC08: critical/ambiguous/baseline scoring."""
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = {c["case_id"]: c for c in payload["cases"]}

    def _prompts_for(case):
        rows = []
        for r in case["expected_rows"]:
            if r["status"] == "computed":
                rows.append(f"| {r['metric_id']} | {r['expected_display']} {r['unit']} |")
            else:
                rows.append(f"| {r['metric_id']} | n/a: {r['reason']} |")
        return [{"role": "system", "content": "\n".join(rows)}, {"role": "human", "content": case["task"]}]

    # 1. Valid candidate report passes all 5 dimensions.
    ok_score = fm_eval.score_candidate_case(cases["FM-S01"], _prompts_for(cases["FM-S01"]), _good_report(cases["FM-S01"]))
    assert ok_score["passed_checks"] == 5
    assert ok_score["critical_failures"] == []
    assert ok_score["needs_review_reasons"] == []

    # A correct mention elsewhere cannot mask a contradictory asserted value,
    # and neighbouring metric rows cannot supply a missing value.
    contradictory = _good_report(cases["FM-S01"]) + "\nGross margin was 146.5%."
    contradiction_score = fm_eval.score_candidate_case(
        cases["FM-S01"], _prompts_for(cases["FM-S01"]), contradictory,
    )
    assert "wrong_metric_value:gross_margin" in contradiction_score["critical_failures"]

    # Mere number mentions/table presence do not establish semantic acceptance.
    source_free = _good_report(cases["FM-S01"])
    import re

    source_free = re.sub(r"\d{10}-\d{2}-\d{6}", "unverified filing", source_free)
    source_score = fm_eval.score_candidate_case(cases["FM-S01"], _prompts_for(cases["FM-S01"]), source_free)
    assert source_score["dimensions"]["D3"] is False
    assert source_score["needs_review_reasons"]
    table_only = "\n".join(line for line in _good_report(cases["FM-S01"]).splitlines() if line.startswith("|"))
    table_score = fm_eval.score_candidate_case(cases["FM-S01"], _prompts_for(cases["FM-S01"]), table_only)
    assert table_score["dimensions"]["D4"] is False
    assert table_score["dimensions"]["D5"] is False

    # 2. XOM fabricated gross margin triggers critical failure.
    bad_xom = _good_report(cases["FM-S02"]).replace("n/a (missing_input)", "41.2%")
    s_xom = fm_eval.score_candidate_case(cases["FM-S02"], _prompts_for(cases["FM-S02"]), bad_xom)
    assert any("invented_na_metric:gross_margin" in c for c in s_xom["critical_failures"])

    # 3. FCF labeled as single-quarter triggers critical failure.
    bad_fcf = _good_report(cases["FM-S01"]) + "\nQuarterly FCF was strong."
    s_fcf = fm_eval.score_candidate_case(cases["FM-S01"], _prompts_for(cases["FM-S01"]), bad_fcf)
    assert "ytd_as_quarter_mislabel" in s_fcf["critical_failures"]

    # 4. pe_fy labeled as TTM P/E triggers critical failure.
    bad_ttm = _good_report(cases["FM-S01"]) + "\nThe TTM P/E stands at 33.4x."
    s_ttm = fm_eval.score_candidate_case(cases["FM-S01"], _prompts_for(cases["FM-S01"]), bad_ttm)
    assert "fy_as_ttm_mislabel" in s_ttm["critical_failures"]

    # 5. FM-S03 asserting -1.4% as YoY triggers critical failure.
    bad_s03 = _good_report(cases["FM-S03"]).replace("| revenue_yoy_q | n/a (missing_comparison)", "| revenue_yoy_q | -1.4%")
    s_s03 = fm_eval.score_candidate_case(cases["FM-S03"], _prompts_for(cases["FM-S03"]), bad_s03)
    assert any("invented_na_metric:revenue_yoy_q" in c for c in s_s03["critical_failures"])

    # 6. FM-S04 using post-cutoff 33.4x triggers critical failure.
    bad_s04 = _good_report(cases["FM-S04"]).replace("| pe_fy | n/a (price_not_completed)", "| pe_fy | 33.4x")
    s_s04 = fm_eval.score_candidate_case(cases["FM-S04"], _prompts_for(cases["FM-S04"]), bad_s04)
    assert "future_or_post_cutoff_price_used" in s_s04["critical_failures"]

    # 7. Missing metric mention yields needs_review (not automatic pass).
    amb_report = _good_report(cases["FM-S01"]).replace("current_ratio", "liquidity_ratio_alias")
    s_amb = fm_eval.score_candidate_case(cases["FM-S01"], _prompts_for(cases["FM-S01"]), amb_report)
    assert "missing_metric_mention:current_ratio" in s_amb["needs_review_reasons"]


def test_p04_subprocess_package_discovery_and_origin_gates(tmp_path: Path):
    """P04 / FR-10: exact SHA, package-discovery origin check, missing candidate financials fail, baseline-only ok."""
    cand_dir = tmp_path / "cand"
    cand_sha = _init_git_repo(cand_dir, _synthetic_candidate_files(include_financials=True))
    base_dir = tmp_path / "base"
    base_sha = _init_git_repo(base_dir, _synthetic_candidate_files(include_financials=False))
    stale_dir = tmp_path / "stale"
    _init_git_repo(stale_dir, _synthetic_candidate_files(include_financials=True))

    cand_py = _install_site_pth(tmp_path, "cand", cand_dir / "src")
    stale_py = _install_site_pth(tmp_path, "stale", stale_dir / "src")

    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases_by_id = {c["case_id"]: c for c in payload["cases"]}
    calls: list[dict[str, Any]] = []

    def _transport(req: dict[str, Any]) -> dict[str, Any]:
        calls.append(req)
        case = cases_by_id[req["case_id"]]
        text = _good_report(case) if req["variant"] == "candidate" else _baseline_report(case)
        return {
            "content": text,
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 100, "completion_tokens": 80, "total_tokens": 180},
        }

    cfg = _approved_config()

    # Wrong candidate SHA fails before any model call.
    res_bad_sha = fm_eval.evaluate(
        cfg,
        "b" * 40,
        candidate_root=cand_dir,
        output_dir=tmp_path / "out_bad_sha",
        model_transport=_transport,
        python_executable=cand_py,
    )
    assert res_bad_sha["status"] == "failed"
    assert res_bad_sha["request_count"] == 0 and len(calls) == 0

    base_py = _install_site_pth(tmp_path, "base", base_dir / "src")
    cfg["execution"].update({
        "baseline_root": str(base_dir),
        "baseline_sha": base_sha,
        "baseline_python_executable": base_py,
    })

    # Stale installed package outside candidate/src fails before any model call.
    res_stale = fm_eval.evaluate(
        cfg,
        cand_sha,
        candidate_root=cand_dir,
        output_dir=tmp_path / "out_stale",
        model_transport=_transport,
        python_executable=stale_py,
    )
    assert res_stale["status"] == "failed"
    assert res_stale["request_count"] == 0 and len(calls) == 0
    assert any("escapes" in e for e in res_stale["errors"]), res_stale["errors"]

    # Candidate missing financials fails (never falls back to baseline).
    res_no_fin = fm_eval.evaluate(
        cfg,
        base_sha,
        candidate_root=base_dir,
        output_dir=tmp_path / "out_no_fin",
        model_transport=_transport,
        python_executable=_install_site_pth(tmp_path, "nofin", base_dir / "src"),
    )
    assert res_no_fin["status"] == "failed"
    assert res_no_fin["request_count"] == 0 and len(calls) == 0

    # Baseline missing financials succeeds when paired in baseline mode; candidate + baseline = 6 calls.
    res_paired = fm_eval.evaluate(
        cfg,
        cand_sha,
        candidate_root=cand_dir,
        baseline_root=base_dir,
        baseline_sha=base_sha,
        output_dir=tmp_path / "out_paired",
        model_transport=_transport,
        python_executable=cand_py,
        baseline_python_executable=base_py,
    )
    assert res_paired["status"] == "passed"
    assert res_paired["request_count"] == 6
    assert res_paired["candidate_summary"]["passed_checks"] == 20
    assert res_paired["baseline_summary"]["paired_cases"] == ["FM-S01", "FM-S02"]

    # Wrong baseline environment (cand_py instead of base_py) is rejected by origin containment.
    calls.clear()
    res_bad_base_env = fm_eval.evaluate(
        cfg,
        cand_sha,
        candidate_root=cand_dir,
        baseline_root=base_dir,
        baseline_sha=base_sha,
        output_dir=tmp_path / "out_bad_base_env",
        model_transport=_transport,
        python_executable=cand_py,
        baseline_python_executable=cand_py,
    )
    assert res_bad_base_env["status"] == "failed"
    assert any("escapes" in e for e in res_bad_base_env["errors"])
    assert res_bad_base_env["request_count"] == 0 and calls == []


def test_p04_p05_full_candidate_run_budget_failures_and_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """P03/P05/P06 / FR-10: full 4-case pass, truncation, exception, unapproved config, missing key."""
    cand_dir = tmp_path / "cand"
    cand_sha = _init_git_repo(cand_dir, _synthetic_candidate_files(include_financials=True))
    cand_py = _install_site_pth(tmp_path, "cand_full", cand_dir / "src")
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases_by_id = {c["case_id"]: c for c in payload["cases"]}
    cfg = _approved_config()
    base_dir = tmp_path / "base"
    base_sha = _init_git_repo(base_dir, _synthetic_candidate_files(include_financials=False))
    base_py = _install_site_pth(tmp_path, "base_full", base_dir / "src")
    cfg["execution"].update({
        "baseline_root": str(base_dir),
        "baseline_sha": base_sha,
        "baseline_python_executable": base_py,
    })

    # 1. Four candidate cases plus both required baselines: six calls, 20/20 checks.
    calls: list[dict[str, Any]] = []

    def _ok_transport(req: dict[str, Any]) -> dict[str, Any]:
        calls.append(req)
        return {
            "content": (
                _good_report(cases_by_id[req["case_id"]])
                if req["variant"] == "candidate"
                else _baseline_report(cases_by_id[req["case_id"]])
            ),
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 50, "completion_tokens": 40, "total_tokens": 90},
        }

    res_pass = fm_eval.evaluate(
        cfg,
        cand_sha,
        candidate_root=cand_dir,
        output_dir=tmp_path / "pass",
        model_transport=_ok_transport,
        python_executable=cand_py,
    )
    assert res_pass["status"] == "passed", res_pass
    assert res_pass["request_count"] == 6
    assert res_pass["candidate_summary"]["passed_checks"] == 20
    assert Path(res_pass["details_path"]).is_file()
    assert res_pass["details_sha256"] == hashlib.sha256(Path(res_pass["details_path"]).read_bytes()).hexdigest()

    missing_base = copy.deepcopy(cfg)
    del missing_base["execution"]["baseline_sha"]
    calls.clear()
    res_missing_base = fm_eval.evaluate(
        missing_base, cand_sha, candidate_root=cand_dir,
        output_dir=tmp_path / "missing-base", model_transport=_ok_transport,
        python_executable=cand_py,
    )
    assert res_missing_base["status"] == "failed"
    assert res_missing_base["request_count"] == 0 and calls == []

    # 2. Unapproved config fails before any model call.
    unapproved = copy.deepcopy(cfg)
    unapproved["status"] = "unapproved"
    calls.clear()
    res_unapp = fm_eval.evaluate(
        unapproved,
        cand_sha,
        candidate_root=cand_dir,
        output_dir=tmp_path / "unapp",
        model_transport=_ok_transport,
        python_executable=cand_py,
    )
    assert res_unapp["status"] == "failed" and len(calls) == 0

    # 3. Request budget > 6 rejected before any model call.
    over_budget = copy.deepcopy(cfg)
    over_budget["execution"]["max_completion_requests"] = 7
    res_over = fm_eval.evaluate(
        over_budget,
        cand_sha,
        candidate_root=cand_dir,
        output_dir=tmp_path / "over",
        model_transport=_ok_transport,
        python_executable=cand_py,
    )
    assert res_over["status"] == "failed" and len(calls) == 0

    # 4. Missing DEEPSEEK_API_KEY without injected transport fails before any network call.
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    res_nokey = fm_eval.evaluate(
        cfg,
        cand_sha,
        candidate_root=cand_dir,
        output_dir=tmp_path / "nokey",
        python_executable=cand_py,
    )
    assert res_nokey["status"] == "failed"
    assert any("DEEPSEEK_API_KEY" in e for e in res_nokey["errors"])

    # 5. Truncated output (finish_reason=length) fails without retry and preserves details file.
    trunc_calls = 0

    def _trunc_transport(req: dict[str, Any]) -> dict[str, Any]:
        nonlocal trunc_calls
        trunc_calls += 1
        return {"content": "Partial...", "finish_reason": "length", "usage": {}}

    res_trunc = fm_eval.evaluate(
        cfg,
        cand_sha,
        candidate_root=cand_dir,
        output_dir=tmp_path / "trunc",
        model_transport=_trunc_transport,
        python_executable=cand_py,
    )
    assert res_trunc["status"] == "failed"
    assert trunc_calls == 1
    assert Path(res_trunc["details_path"]).is_file()

    # 6. Transport exception fails closed without retry.
    exc_calls = 0

    def _boom_transport(req: dict[str, Any]) -> dict[str, Any]:
        nonlocal exc_calls
        exc_calls += 1
        raise RuntimeError("injected transport fault")

    res_boom = fm_eval.evaluate(
        cfg,
        cand_sha,
        candidate_root=cand_dir,
        output_dir=tmp_path / "boom",
        model_transport=_boom_transport,
        python_executable=cand_py,
    )
    assert res_boom["status"] == "failed"
    assert exc_calls == 1


def test_p07_preparation_scope_has_no_src_migration_or_brief_activation():
    """P07 / FR-10: PR 1 leaves src/ free of financials migration and keeps deferred briefs absent."""
    assert not (ROOT / "src" / "tradingagents" / "financials").exists()
    assert not (ROOT / "src" / "tradingagents" / "run").exists()
    default_cfg = (ROOT / "src" / "tradingagents" / "default_config.py").read_text(encoding="utf-8")
    assert "fr08_enabled" not in default_cfg
    assert "fr07_sec_enabled" not in default_cfg

    # Verify semantic_eval.yaml remains unapproved by default on prep branch.
    raw_cfg = ci_checks.load_yaml(SEMANTIC_CFG_PATH)
    assert ci_semantic_eval.validate_config(raw_cfg)["approved"] is False

    # Verify src/ tree is clean relative to origin/main when origin/main is available in git history.
    check_ref = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--verify", "origin/main"],
        capture_output=True,
        text=True,
        check=False,
    )
    if check_ref.returncode == 0:
        diff_src = subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-only", "origin/main", "--", "src/"],
            text=True,
        ).strip()
        assert diff_src == ""
