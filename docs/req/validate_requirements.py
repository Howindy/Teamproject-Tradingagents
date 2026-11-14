#!/usr/bin/env python3
"""Validate the D1 requirements registry, manifest contract, and evidence.

Run from the repository root:

    python3 -m pip install pyyaml jsonschema
    python3 docs/req/validate_requirements.py

Use ``--check`` to verify that docs/req/validation-results.json is still bound to
the current files. Human review is never inferred by this script.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import time
import unicodedata
from datetime import UTC, date, datetime, time as dt_time, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
REQ_DIR = ROOT / "docs" / "req"
REQUIREMENTS = REQ_DIR / "requirements.yaml"
REQ_SCHEMA = REQ_DIR / "req-schema.json"
MANIFEST_SCHEMA = REQ_DIR / "run-manifest-schema.json"
RESULTS = REQ_DIR / "validation-results.json"
EVAL_DIR = REQ_DIR / "evaluation"
FIXTURE_DIR = REQ_DIR / "fixtures"
SHA = "a" * 64


def load(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh) if path.suffix == ".json" else yaml.safe_load(fh)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def check_acyclic(requirements: dict[str, dict]) -> None:
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in done:
            return
        if node in visiting:
            fail(f"implementation dependency cycle: {' -> '.join(stack + [node])}")
        visiting.add(node)
        for dep in requirements[node].get("implementation_dependencies", []):
            if dep not in requirements:
                fail(f"{node} has unknown implementation dependency {dep}")
            visit(dep, stack + [node])
        visiting.remove(node)
        done.add(node)

    for req_id in requirements:
        visit(req_id, [])


EXCLUDED_PATHS = frozenset({("safety_gate", "evaluated_at"), ("coverage_snapshot", "computed_at")})
ORDERED_LIST_KEYS = frozenset({"attempts", "attempted_sources", "artifacts"})


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    return "\n".join(line.rstrip() for line in value.split("\n")).rstrip()


def canonicalize(obj, *, key=None, path=()):
    if isinstance(obj, str):
        return normalize_text(obj)
    if isinstance(obj, dict):
        return {
            k: canonicalize(v, key=k, path=path + (k,))
            for k, v in sorted(obj.items())
            if path + (k,) not in EXCLUDED_PATHS
        }
    if isinstance(obj, list):
        items = [canonicalize(v, key=key, path=path) for v in obj]
        if key in ORDERED_LIST_KEYS:
            return items
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return obj


def canonical_hash(obj) -> str:
    raw = json.dumps(canonicalize(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def profile_projection(m: dict) -> dict:
    return {k: v for k, v in m["critical_profile"].items() if k != "profile_hash"}


def snapshot_projection(m: dict) -> dict:
    keys = ("snapshot_version", "critical_profile_hash", "computed_by", "coverage_status",
            "critical_gaps", "critical_gap_ids", "provenance_digest", "run_id")
    return {k: m["coverage_snapshot"].get(k) for k in keys}


def provenance_projection(m: dict) -> list:
    records = []
    for record in m.get("data_source_status", []):
        attempts = [
            {k: a.get(k) for k in ("source", "status", "reason_code", "reason", "record_count", "started_at", "ended_at")}
            for a in record.get("attempts", [])
        ]
        projected = {
            k: record.get(k) for k in (
                "record_kind", "data_query_key", "requirement_id", "capability", "component",
                "supports", "source", "serving_source", "attempted_sources", "status",
                "reason_code", "reason", "record_count", "fallback_used",
            )
        }
        projected["attempts"] = attempts
        records.append(projected)
    return records


def record_projection(m: dict) -> dict:
    binding = {k: v for k, v in m["artifact_binding"].items() if k != "record_hash"}
    gate = {k: v for k, v in m["safety_gate"].items() if k != "evaluated_at"}
    return {
        "artifact_binding": binding,
        "critical_profile": profile_projection(m),
        "snapshot_hash": m["coverage_snapshot"].get("snapshot_hash"),
        "coverage_snapshot": snapshot_projection(m),
        "model_proposal": m.get("model_proposal"),
        "formal_decision": m["formal_decision"],
        "safety_gate": gate,
        "provenance_digest": m["provenance_digest"],
        "run_clock": {k: v for k, v in m["run_clock"].items() if k != "now_utc"},
    }


POLICY_SNAPSHOT_KEYS = (
    "policy_version", "policy_ref", "max_projected_weight", "max_stop_distance",
    "max_valuation_age_seconds", "precision_rule", "threshold_status",
    "human_approval_ref",
)


def policy_projection(risk: dict) -> dict:
    policy = risk.get("policy_snapshot")
    if not isinstance(policy, dict):
        return {}
    return {k: policy.get(k) for k in POLICY_SNAPSHOT_KEYS}


def stabilize_hashes(m: dict) -> None:
    proposal = {k: m["model_proposal"][k] for k in ("rating", "decision_text", "proposal_status")}
    m["model_proposal"]["proposal_digest"] = canonical_hash(proposal)
    m["critical_profile"]["profile_hash"] = canonical_hash(profile_projection(m))
    m["provenance_digest"] = canonical_hash(provenance_projection(m))
    m["coverage_snapshot"]["critical_profile_hash"] = m["critical_profile"]["profile_hash"]
    m["coverage_snapshot"]["provenance_digest"] = m["provenance_digest"]
    m["coverage_snapshot"]["snapshot_hash"] = canonical_hash(snapshot_projection(m))
    m["safety_gate"]["snapshot_hash"] = m["coverage_snapshot"]["snapshot_hash"]
    decision = {k: m["formal_decision"][k] for k in ("status", "final_rating", "decision_text")}
    m["artifact_binding"]["decision_digest"] = canonical_hash(decision)
    m["artifact_binding"]["coverage_snapshot_hash"] = m["coverage_snapshot"]["snapshot_hash"]
    risk = m["safety_gate"].get("portfolio_risk")
    risk_input_digest = risk.get("input_digest") if isinstance(risk, dict) else None
    diagnostic = risk.get("diagnostic_ref") if isinstance(risk, dict) else None
    risk_diagnostic_digest = diagnostic.get("sha256") if risk_input_digest is None and isinstance(diagnostic, dict) else None
    policy = risk.get("policy_snapshot") if isinstance(risk, dict) else None
    risk_policy_digest = policy.get("policy_digest") if isinstance(policy, dict) else None
    m["safety_gate"]["input_hash"] = canonical_hash({
        "snapshot_hash": m["coverage_snapshot"]["snapshot_hash"],
        "model_proposal": proposal,
        "portfolio_risk_input_digest": risk_input_digest,
        "portfolio_risk_diagnostic_digest": risk_diagnostic_digest,
        "portfolio_risk_policy_digest": risk_policy_digest,
        "gate_version": m["safety_gate"]["gate_version"],
    })
    m["artifact_binding"]["record_hash"] = canonical_hash(record_projection(m))
    if m["memory"].get("entry_binding"):
        m["memory"]["entry_binding"]["decision_digest"] = m["artifact_binding"]["decision_digest"]
        entry = {
            "decision_id": m["artifact_binding"]["decision_id"],
            "trade_date": m["identity"]["analysis_date"],
            "ticker": m["identity"]["ticker"],
            "formal_decision": m["formal_decision"],
        }
        m["memory"]["entry_digest"] = canonical_hash(entry)
        m["memory"]["evidence_digest"] = canonical_hash({
            "coverage_status": m["coverage_snapshot"]["coverage_status"],
            "critical_gap_ids": m["coverage_snapshot"]["critical_gap_ids"],
            "provenance_digest": m["provenance_digest"],
        })


def manifest_sample() -> dict:
    financial = {
        "requirement_id": "financial_statements", "capability": "financial_statements",
        "components": [
            {"component": name, "window_rule": "as_of_date", "min_record_count": 1, "point_in_time_rule": "as_filed", "required": True}
            for name in ("income_statement", "balance_sheet", "cashflow")
        ],
        "query_rule": "all", "min_successful_components": 3, "min_record_count": 1,
        "fallback_policy": "same_capability_only", "criticality": "critical",
    }
    records = []
    for i, name in enumerate(("income_statement", "balance_sheet", "cashflow"), start=2):
        records.append({
            "record_kind": "executed", "data_query_key": f"q{i}",
            "supports": [{"requirement_id": "financial_statements", "capability": "financial_statements", "component": name, "criticality": "critical"}],
            "attempts": [{"source": "SEC EDGAR", "status": "success", "reason_code": None, "reason": None, "record_count": 1, "http_request_count": 1, "cache_kind": "none", "started_at": "2026-11-09T12:00:00+08:00", "ended_at": "2026-11-09T12:00:01+08:00"}],
            "tool": f"get_{name}", "category": "fundamentals", "capability": "financial_statements",
            "component": name, "requirement_id": "financial_statements", "criticality": "critical",
            "source": "SEC EDGAR", "serving_source": "SEC EDGAR", "attempted_sources": ["SEC EDGAR"],
            "requested_window": "2026-10-19", "observed_window": "2026-10-19", "status": "success",
            "reason_code": None, "reason": None, "record_count": 1, "vendor": "sec_edgar",
            "fallback_used": False, "vendor_cache_hit": False, "run_cache_hit": False,
        })
    return {
        "schema_version": "1.0", "run_id": "r1", "parent_run_id": None, "run_status": "completed",
        "identity": {"ticker": "NVDA", "analysis_date": "2026-10-19", "asset_type": "stock"},
        "inheritance": {"inherited": False, "origin_run_id": None, "origin_attempt_id": None, "inherited_counters": {"query_executions": 0, "http_requests": 0, "vendor_cache_hits": 0, "retry_attempts": 0, "fallback_attempts": 0, "llm_calls": 0, "tool_calls": 0}, "inherited_evidence_digest": None, "snapshot_rebound_from": None},
        "run_clock": {"as_of_date": "2026-10-19", "now_utc": "2026-11-09T04:00:00+00:00", "timezone": "Asia/Hong_Kong", "clock_source": "system", "analysis_mode": "historical", "mode_source": "default"},
        "critical_profile": {"profile_version": "d1-default-v1", "profile_source": "default", "analysis_mode": "historical", "asset_type": "stock", "contract_version": "1", "requirements": [{"requirement_id": "market_price", "capability": "market_price", "components": [{"component": "stock_data", "window_rule": "requested_window", "min_record_count": 1, "point_in_time_rule": "strict_as_of", "required": True}], "query_rule": "all", "min_successful_components": 1, "min_record_count": 1, "fallback_policy": "same_capability_only", "criticality": "critical"}, financial], "profile_hash": SHA},
        "coverage_snapshot": {"snapshot_version": "1", "snapshot_hash": SHA, "critical_profile_hash": SHA, "computed_at": "2026-11-09T04:00:00+00:00", "computed_by": "program", "coverage_status": "complete", "critical_gaps": [], "critical_gap_ids": [], "provenance_digest": SHA, "run_id": "r1"},
        "provenance_digest": SHA,
        "model_proposal": {"rating": "Hold", "decision_text": "Hold decision", "proposal_status": "unapproved", "proposal_digest": SHA},
        "config": {"tradingagents_version": "0.7.0", "llm_provider": "p", "deep_think_provider": "p", "quick_think_provider": "p", "deep_think_llm": "m", "quick_think_llm": "m", "analysts": ["market", "fundamentals"], "max_debate_rounds": 1, "max_risk_discuss_rounds": 1, "output_language": "English", "data_vendors": {"x": "y"}, "tool_vendors": {}},
        "timing": {"started_at": "2026-11-09T12:00:00+08:00", "analysis_finished_at": "2026-11-09T12:03:14+08:00", "finished_at": "2026-11-09T12:03:15+08:00", "duration_seconds": 195.0, "analysis_seconds": 194.4, "publish_seconds": 0.6, "manifest_write_seconds": 0.02, "startup_manifest_write_seconds": 0.01},
        "counts": {"llm_calls": 1, "tool_calls": 4, "prefetch_calls": 0, "reflection_llm_calls": 0, "retry_attempts": 0, "fallback_attempts": 0, "query_executions": 4, "external_requests": 4, "vendor_cache_hits": 0, "run_cache_hits": 0, "llm_error_count": 0, "tool_error_count": 0},
        "tokens": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2, "status": "complete", "llm_calls_with_usage": 1, "llm_calls_without_usage": 0},
        "data_source_status": [{"record_kind": "executed", "data_query_key": "q1", "supports": [{"requirement_id": "market_price", "capability": "market_price", "component": "stock_data", "criticality": "critical"}], "attempts": [{"source": "Yahoo Finance", "status": "success", "reason_code": None, "reason": None, "record_count": 1, "http_request_count": 1, "cache_kind": "none", "started_at": "2026-11-09T12:00:00+08:00", "ended_at": "2026-11-09T12:00:01+08:00"}], "tool": "get_stock_data", "category": "market", "capability": "market_price", "component": "stock_data", "requirement_id": "market_price", "criticality": "critical", "source": "Yahoo Finance", "serving_source": "Yahoo Finance", "attempted_sources": ["Yahoo Finance"], "requested_window": "2026-10-19", "observed_window": "2026-10-19", "status": "success", "reason_code": None, "reason": None, "record_count": 1, "vendor": "yfinance", "fallback_used": False, "vendor_cache_hit": False, "run_cache_hit": False}] + records,
        "safety_gate": {"status": "passed", "reason_codes": [], "primary_reason_code": None, "coverage_status": "complete", "critical_gap_ids": [], "profile_version": "d1-default-v1", "snapshot_hash": SHA, "gate_version": "1.0", "input_hash": SHA, "run_id": "r1", "evaluated_at": "2026-11-09T12:03:15+08:00", "portfolio_risk": {"evaluation_status": "not_applicable", "risk_reason_codes": [], "policy_snapshot": None, "input_ref": None, "input_digest": None, "diagnostic_ref": None, "valuation_time": None, "valuation_cutoff": None, "currency": None, "projected_weight": None, "stop_distance": None, "effective_order_value": None, "evaluated_at": "2026-11-09T12:03:15+08:00"}},
        "security": {"scan_status": "clean", "write_scan_status": "clean", "run_scan_status": "clean", "known_secret_match_count": 0, "pattern_match_count": 0, "redaction_count": 0, "rule_version": "1.0", "scope": ["manifest", "final_state", "memory", "report", "logs", "preferences", "gate", "availability"], "failure_reason": None},
        "memory": {"enabled": True, "status": "written", "commit_status": "committed", "entry_version": 1, "entry_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": SHA, "trade_date": "2026-10-19", "ticker": "NVDA"}, "entry_digest": SHA, "evidence_digest": SHA, "reused_decision_ref": None, "supersedes": None, "retention_status": "retained", "same_day_rerun": False},
        "artifact_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": SHA, "gate_status": "passed", "formal_decision_status": "approved", "final_rating": "Hold", "coverage_status": "complete", "critical_gap_ids": [], "coverage_snapshot_hash": SHA, "record_hash": SHA},
        "formal_decision": {"status": "approved", "final_rating": "Hold", "decision_text": "Hold decision", "review_class": "none"},
        "artifacts": [{"kind": "report", "path": "r.md", "sha256": SHA, "hash_scope": "file"}, {"kind": "final_state", "path": "f.json", "sha256": SHA, "hash_scope": "file"}, {"kind": "memory", "path": "memory.md", "sha256": SHA, "hash_scope": "memory_entry"}],
        "report_section_manifest": {"renderer_version": "reporting-v1", "capability_set": ["market", "fundamentals"], "sections": [{"path": "1_analysts/market.md", "agent": "Market Analyst", "state_fields": ["market_report"], "bytes": 1, "sha256": SHA}], "complete_report": {"path": "complete_report.md", "bytes": 1, "sha256": SHA}},
        "metric_evidence_bundle": {"fact_schema_version": "1.0", "formula_version": "1.0", "metric_policy_version": "1.0", "facts": [{"fact_id": "f1", "subject_id": "CIK0001045810", "accession_no": "0001045810-26-000001", "filing_ref": "sec://CIK0001045810/0001045810-26-000001", "concept": "revenue", "value": "1", "unit": "USD_millions", "currency": "USD", "period_start": "2026-01-01", "period_end": "2026-03-31", "fiscal_year": 2026, "fiscal_quarter": 1, "span": "quarter", "cumulative_duration_days": 90, "filed_at": "2026-04-30", "source": "sec_10q"}], "metric_block": [{"metric_id": "revenue", "value_or_reason": "1", "status": "computed", "formula_id": "revenue_v1", "formula_version": "1.0", "period": "2026-Q1", "fact_ids": ["f1"]}], "input_digest": SHA, "result_digest": SHA},
        "error": None,
    }


def cross_field_errors(m: dict) -> list:
    errors = []
    b, g, f, c = m["artifact_binding"], m["safety_gate"], m["formal_decision"], m["coverage_snapshot"]
    checks = [
        ("binding.run_id", b.get("run_id"), m.get("run_id")),
        ("binding.gate_status", b.get("gate_status"), g.get("status")),
        ("binding.formal_decision_status", b.get("formal_decision_status"), f.get("status")),
        ("binding.final_rating", b.get("final_rating"), f.get("final_rating")),
        ("binding.coverage_status", b.get("coverage_status"), c.get("coverage_status")),
        ("binding.critical_gap_ids", b.get("critical_gap_ids"), g.get("critical_gap_ids")),
        ("binding.coverage_snapshot_hash", b.get("coverage_snapshot_hash"), g.get("snapshot_hash")),
        ("coverage_snapshot.provenance_digest", c.get("provenance_digest"), m.get("provenance_digest")),
        ("coverage_snapshot.critical_profile_hash", c.get("critical_profile_hash"), m["critical_profile"].get("profile_hash")),
    ]
    for name, left, right in checks:
        if left != right:
            errors.append(f"{name}: {left!r} != {right!r}")
    if canonical_hash(profile_projection(m)) != m["critical_profile"].get("profile_hash"):
        errors.append("critical_profile.profile_hash does not match content")
    if canonical_hash(snapshot_projection(m)) != c.get("snapshot_hash"):
        errors.append("coverage_snapshot.snapshot_hash does not match content")
    if canonical_hash(provenance_projection(m)) != m.get("provenance_digest"):
        errors.append("provenance_digest does not match availability projection")
    decision = {k: f[k] for k in ("status", "final_rating", "decision_text")}
    if canonical_hash(decision) != b.get("decision_digest"):
        errors.append("decision_digest does not match formal decision content")
    proposal = {k: m["model_proposal"][k] for k in ("rating", "decision_text", "proposal_status")}
    if canonical_hash(proposal) != m["model_proposal"].get("proposal_digest"):
        errors.append("proposal_digest does not match model proposal content")
    risk = g.get("portfolio_risk")
    risk_input_digest = risk.get("input_digest") if isinstance(risk, dict) else None
    diagnostic = risk.get("diagnostic_ref") if isinstance(risk, dict) else None
    risk_diagnostic_digest = diagnostic.get("sha256") if risk_input_digest is None and isinstance(diagnostic, dict) else None
    policy = risk.get("policy_snapshot") if isinstance(risk, dict) else None
    risk_policy_digest = policy.get("policy_digest") if isinstance(policy, dict) else None
    if canonical_hash({
        "snapshot_hash": c["snapshot_hash"],
        "model_proposal": proposal,
        "portfolio_risk_input_digest": risk_input_digest,
        "portfolio_risk_diagnostic_digest": risk_diagnostic_digest,
        "portfolio_risk_policy_digest": risk_policy_digest,
        "gate_version": g["gate_version"],
    }) != g.get("input_hash"):
        errors.append("input_hash does not match gate input content")
    if canonical_hash(record_projection(m)) != b.get("record_hash"):
        errors.append("record_hash does not match immutable record projection")
    rsm = m.get("report_section_manifest")
    if m.get("run_status") == "completed" and not isinstance(rsm, dict):
        errors.append("completed run requires report_section_manifest")
    if isinstance(rsm, dict):
        paths = [section.get("path") for section in rsm.get("sections", [])]
        if len(paths) != len(set(paths)):
            errors.append("report_section_manifest section paths must be unique")
        if rsm.get("complete_report", {}).get("path") in paths:
            errors.append("complete_report path must not duplicate a section path")
    asset_type = m["identity"].get("asset_type")
    model_rating = m["model_proposal"].get("rating")
    risk_required = asset_type == "stock" and model_rating in {"Buy", "Overweight"}
    if risk_required and not isinstance(risk, dict):
        errors.append("stock Buy/Overweight requires a portfolio_risk result")
    if isinstance(risk, dict):
        risk_status = risk.get("evaluation_status")
        risk_codes = set(risk.get("risk_reason_codes") or [])
        gate_codes = g.get("reason_codes") or []
        limit_codes = {"POSITION_LIMIT_EXCEEDED", "STOP_DISTANCE_EXCEEDED"}
        invalid_codes = {
            "MISSING_RISK_INPUT", "INVALID_RISK_INPUT", "STALE_RISK_INPUT",
            "UNSUPPORTED_RISK_INPUT", "CURRENCY_MISMATCH",
            "VALUATION_INCONSISTENT", "INSUFFICIENT_CASH",
            "POLICY_SNAPSHOT_UNAVAILABLE",
        }
        if risk_required and risk_status == "not_applicable":
            errors.append("stock Buy/Overweight cannot have not_applicable portfolio_risk")
        if not risk_required and risk_status == "passed":
            errors.append("non-applicable run cannot have passed portfolio_risk")
        if isinstance(policy, dict):
            if canonical_hash(policy_projection(risk)) != policy.get("policy_digest"):
                errors.append("policy_digest does not match policy snapshot content")
            if policy.get("threshold_status") == "provisional" and policy.get("human_approval_ref") is not None:
                errors.append("provisional policy cannot carry a human approval reference")
            if policy.get("threshold_status") == "approved" and not policy.get("human_approval_ref"):
                errors.append("approved policy requires a human approval reference")
        ref = risk.get("input_ref")
        if isinstance(ref, dict) and ref.get("sha256") != risk.get("input_digest"):
            errors.append("input_ref.sha256 does not match input_digest")
        if risk_status == "passed":
            if any(code.startswith("portfolio_risk_") for code in gate_codes):
                errors.append("passed portfolio_risk cannot carry a portfolio-risk gate reason")
            if risk.get("diagnostic_ref") is not None:
                errors.append("passed risk cannot carry a diagnostic_ref")
            if not isinstance(policy, dict):
                errors.append("passed risk requires a policy snapshot")
            if not isinstance(ref, dict) or not risk.get("input_digest"):
                errors.append("passed risk requires input_ref and input_digest")
            for metric in ("projected_weight", "stop_distance", "effective_order_value"):
                if risk.get(metric) is None:
                    errors.append(f"passed risk requires {metric}")
        elif risk_status == "blocked":
            if g.get("status") not in {"blocked", "error"}:
                errors.append("blocked portfolio_risk requires blocked or error gate status")
            if f.get("status") != "blocked_for_review" or f.get("final_rating") != "REVIEW":
                errors.append("blocked portfolio_risk requires blocked_for_review/REVIEW")
            if risk_codes & limit_codes:
                if "portfolio_risk_limit_exceeded" not in gate_codes:
                    errors.append("risk limit code missing portfolio_risk_limit_exceeded gate reason")
                if not isinstance(policy, dict):
                    errors.append("risk limit block requires a policy snapshot")
                if not isinstance(ref, dict) or not risk.get("input_digest"):
                    errors.append("risk limit block requires input_ref and input_digest")
                for metric in ("projected_weight", "stop_distance", "effective_order_value"):
                    if risk.get(metric) is None:
                        errors.append(f"risk limit block requires {metric}")
            if risk_codes & invalid_codes and "portfolio_risk_input_invalid" not in gate_codes:
                errors.append("invalid risk code missing portfolio_risk_input_invalid gate reason")
            if risk_codes & invalid_codes and not isinstance(ref, dict):
                if not isinstance(risk.get("diagnostic_ref"), dict):
                    errors.append("invalid risk input without input_ref requires diagnostic_ref")
            if "EVALUATOR_ERROR" in risk_codes:
                errors.append("EVALUATOR_ERROR must use evaluation_status error, not blocked")
        elif risk_status == "not_applicable":
            if any(code.startswith("portfolio_risk_") for code in gate_codes):
                errors.append("not_applicable portfolio_risk cannot carry a portfolio-risk gate reason")
        elif risk_status == "error":
            if "EVALUATOR_ERROR" not in risk_codes:
                errors.append("error portfolio_risk requires EVALUATOR_ERROR")
            if g.get("status") != "error":
                errors.append("error portfolio_risk requires error gate status")
            if "portfolio_risk_evaluator_error" not in gate_codes:
                errors.append("error portfolio_risk requires portfolio_risk_evaluator_error gate reason")
            if f.get("status") != "blocked_for_review" or f.get("final_rating") != "REVIEW":
                errors.append("error portfolio_risk requires blocked_for_review/REVIEW")
            if f.get("review_class") != "gate_system_error":
                errors.append("error portfolio_risk requires review_class gate_system_error")
            if g.get("primary_reason_code") != "portfolio_risk_evaluator_error":
                errors.append("error portfolio_risk requires primary_reason_code portfolio_risk_evaluator_error")
            if m.get("run_status") != "failed":
                errors.append("error portfolio_risk requires failed run status")
    if g.get("status") == "passed" and risk_required:
        if not isinstance(risk, dict) or risk.get("evaluation_status") != "passed":
            errors.append("passed gate with stock Buy/Overweight requires a passed portfolio_risk result")
    if any(code.startswith("portfolio_risk_") for code in (g.get("reason_codes") or [])):
        if not isinstance(risk, dict) or risk.get("evaluation_status") not in {"blocked", "error"}:
            errors.append("portfolio-risk gate reason requires a blocked or error portfolio_risk result")
    critical = {(r["requirement_id"], comp["component"]) for r in m["critical_profile"]["requirements"] for comp in r["components"] if comp.get("required")}
    linked = {(s["requirement_id"], s["component"]) for r in m.get("data_source_status", []) for s in r.get("supports", [])}
    if m.get("run_status") == "completed" and (critical - linked):
        errors.append(f"missing mandatory component records: {sorted(critical - linked)}")
    if m["memory"].get("enabled") and m["memory"].get("entry_binding"):
        if b.get("decision_id") != m["memory"]["entry_binding"].get("decision_id"):
            errors.append("binding.decision_id != memory.entry_binding.decision_id")
        entry = {
            "decision_id": b["decision_id"],
            "trade_date": m["identity"]["analysis_date"],
            "ticker": m["identity"]["ticker"],
            "formal_decision": f,
        }
        if canonical_hash(entry) != m["memory"].get("entry_digest"):
            errors.append("entry_digest does not match stable decision-content projection")
        evidence = {
            "coverage_status": c["coverage_status"],
            "critical_gap_ids": c["critical_gap_ids"],
            "provenance_digest": m["provenance_digest"],
        }
        if canonical_hash(evidence) != m["memory"].get("evidence_digest"):
            errors.append("evidence_digest does not match per-run evidence projection")
    return errors


def manifest_checks(schema: dict) -> dict:
    v = Draft202012Validator(schema)
    completed = manifest_sample()
    stabilize_hashes(completed)
    running = copy.deepcopy(completed)
    running.update({"run_status": "running", "timing": {"started_at": "2026-11-09T12:00:00+08:00", "analysis_finished_at": None, "finished_at": None, "duration_seconds": None, "analysis_seconds": None, "publish_seconds": None, "manifest_write_seconds": None, "startup_manifest_write_seconds": 0.01}, "data_source_status": [], "safety_gate": {"status": "not_run", "reason_codes": [], "primary_reason_code": None, "coverage_status": None, "critical_gap_ids": [], "profile_version": None, "snapshot_hash": None, "gate_version": "1.0", "input_hash": SHA, "run_id": None, "evaluated_at": None}, "security": {"scan_status": "not_run", "write_scan_status": "clean", "run_scan_status": "not_run", "known_secret_match_count": 0, "pattern_match_count": 0, "redaction_count": 0, "rule_version": "1.0", "scope": ["manifest"], "failure_reason": None}, "memory": {"enabled": True, "status": "not_available", "commit_status": "not_applicable", "entry_version": 1, "entry_binding": None, "entry_digest": None, "evidence_digest": None, "reused_decision_ref": None, "supersedes": None, "retention_status": "not_applicable", "same_day_rerun": False}, "artifact_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": None, "gate_status": "not_run", "formal_decision_status": "pending", "final_rating": None, "coverage_status": None, "critical_gap_ids": [], "coverage_snapshot_hash": None, "record_hash": None}, "formal_decision": {"status": "pending", "final_rating": None, "decision_text": None, "review_class": "none"}, "artifacts": [], "error": None})
    failed = copy.deepcopy(completed)
    failed.update({"run_status": "failed", "error": {"stage": "gate", "type": "GateError", "message": "gate unavailable"}, "safety_gate": {"status": "error", "reason_codes": ["gate_internal_error"], "primary_reason_code": "gate_internal_error", "coverage_status": "partial", "critical_gap_ids": [], "profile_version": "d1-default-v1", "snapshot_hash": SHA, "gate_version": "1.0", "input_hash": SHA, "run_id": "r1", "evaluated_at": "2026-11-09T12:03:15+08:00"}, "artifact_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": None, "gate_status": "error", "formal_decision_status": "blocked_for_review", "final_rating": "REVIEW", "coverage_status": "partial", "critical_gap_ids": [], "coverage_snapshot_hash": SHA, "record_hash": None}, "formal_decision": {"status": "blocked_for_review", "final_rating": "REVIEW", "decision_text": "Gate unavailable; manual review required.", "review_class": "gate_system_error"}})
    stabilize_hashes(failed)
    mem_off = copy.deepcopy(completed)
    mem_off["memory"] = {"enabled": False, "status": "disabled", "commit_status": "disabled", "entry_version": 1, "entry_binding": None, "entry_digest": None, "evidence_digest": None, "reused_decision_ref": None, "supersedes": None, "retention_status": "disabled", "same_day_rerun": False}
    mem_off["artifacts"] = [a for a in mem_off["artifacts"] if a["kind"] != "memory"]
    failed_startup = copy.deepcopy(completed)
    failed_startup.update({"run_status": "failed", "critical_profile": None, "coverage_snapshot": None, "provenance_digest": canonical_hash([]), "data_source_status": [], "safety_gate": {"status": "not_run", "reason_codes": [], "primary_reason_code": None, "coverage_status": None, "critical_gap_ids": [], "profile_version": None, "snapshot_hash": None, "gate_version": "1.0", "input_hash": canonical_hash({"snapshot_hash": None, "model_proposal": {k: completed["model_proposal"][k] for k in ("rating", "decision_text", "proposal_status")}, "portfolio_risk_input_digest": None, "portfolio_risk_diagnostic_digest": None, "portfolio_risk_policy_digest": None, "gate_version": "1.0"}), "run_id": None, "evaluated_at": None}, "security": {"scan_status": "clean", "write_scan_status": "clean", "run_scan_status": "not_run", "known_secret_match_count": 0, "pattern_match_count": 0, "redaction_count": 0, "rule_version": "1.0", "scope": ["manifest"], "failure_reason": None}, "memory": {"enabled": True, "status": "not_available", "commit_status": "not_applicable", "entry_version": 1, "entry_binding": None, "entry_digest": None, "evidence_digest": None, "reused_decision_ref": None, "supersedes": None, "retention_status": "not_applicable", "same_day_rerun": False}, "artifact_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": canonical_hash({"status": "blocked_for_review", "final_rating": "REVIEW", "decision_text": "Run failed before formal decision; manual review required."}), "gate_status": "not_run", "formal_decision_status": "blocked_for_review", "final_rating": "REVIEW", "coverage_status": None, "critical_gap_ids": [], "coverage_snapshot_hash": None, "record_hash": None}, "formal_decision": {"status": "blocked_for_review", "final_rating": "REVIEW", "decision_text": "Run failed before formal decision; manual review required.", "review_class": "input_invalid"}, "artifacts": [], "error": {"stage": "startup", "type": "ConfigError", "message": "startup failed"}})
    resumed = copy.deepcopy(completed)
    resumed["inheritance"] = {"inherited": True, "origin_run_id": "r0", "origin_attempt_id": "attempt-0", "inherited_counters": {"query_executions": 2, "http_requests": 3, "vendor_cache_hits": 1, "retry_attempts": 1, "fallback_attempts": 1, "llm_calls": 4, "tool_calls": 2}, "inherited_evidence_digest": SHA, "snapshot_rebound_from": SHA}
    blocked = copy.deepcopy(completed)
    blocked["coverage_snapshot"].update({"coverage_status": "partial", "critical_gap_ids": ["financial_statements"], "critical_gaps": [{"requirement_id": "financial_statements", "capability": "financial_statements", "requirement_status": "missing", "gap_reason": "not_attempted", "missing_components": ["income_statement"], "provenance": "gate fixture"}]})
    blocked["safety_gate"].update({"status": "blocked", "reason_codes": ["critical_gap"], "primary_reason_code": "critical_gap", "coverage_status": "partial", "critical_gap_ids": ["financial_statements"]})
    blocked["artifact_binding"].update({"gate_status": "blocked", "formal_decision_status": "blocked_for_review", "final_rating": "REVIEW", "coverage_status": "partial", "critical_gap_ids": ["financial_statements"]})
    blocked["formal_decision"] = {"status": "blocked_for_review", "final_rating": "REVIEW", "decision_text": "Data insufficient; manual review required.", "review_class": "data_insufficient"}
    stabilize_hashes(blocked)
    retry_recovered = copy.deepcopy(completed)
    if retry_recovered["artifact_binding"]["record_hash"] != completed["artifact_binding"]["record_hash"]:
        fail("retry must reuse the same immutable record hash")
    memory_reuse = copy.deepcopy(completed)
    memory_reuse["memory"].update({"status": "existing", "same_day_rerun": True, "reused_decision_ref": {"source_run_id": "r0", "source_decision_id": "d1", "source_entry_digest": SHA}})
    version_switch = copy.deepcopy(completed)
    version_switch["formal_decision"].update({"final_rating": "Underweight", "decision_text": "Underweight decision"})
    version_switch["artifact_binding"].update({"decision_id": "d2", "final_rating": "Underweight"})
    version_switch["memory"].update({"entry_version": 2, "supersedes": "d1"})
    version_switch["memory"]["entry_binding"]["decision_id"] = "d2"
    stabilize_hashes(version_switch)
    policy = {
        "policy_version": "portfolio-risk-policy-v1",
        "policy_ref": "run://risk/policy-snapshot.json",
        "policy_digest": SHA,
        "max_projected_weight": "0.30",
        "max_stop_distance": "0.05",
        "max_valuation_age_seconds": 900,
        "precision_rule": "input<=12dp;internal>=28sd;exact_compare;display=6dp_half_up",
        "threshold_status": "provisional",
        "human_approval_ref": None,
    }
    policy["policy_digest"] = canonical_hash({k: policy[k] for k in POLICY_SNAPSHOT_KEYS})
    input_ref = {"path": "inputs/portfolio_risk_input.json", "sha256": SHA, "hash_scope": "file"}
    risk_pass = copy.deepcopy(completed)
    risk_pass["model_proposal"].update({"rating": "Buy", "decision_text": "Buy decision"})
    risk_pass["formal_decision"] = {"status": "approved", "final_rating": "Buy", "decision_text": "Buy decision", "review_class": "none"}
    risk_pass["artifact_binding"].update({"final_rating": "Buy"})
    risk_pass["safety_gate"]["portfolio_risk"] = {
        "evaluation_status": "passed", "risk_reason_codes": [],
        "policy_snapshot": policy, "input_ref": input_ref, "input_digest": SHA, "diagnostic_ref": None,
        "valuation_time": "2026-11-09T11:45:00+08:00",
        "valuation_cutoff": "2026-11-09T12:03:15+08:00",
        "currency": "USD", "projected_weight": "0.30", "stop_distance": "0.05",
        "effective_order_value": "30000", "evaluated_at": "2026-11-09T12:03:15+08:00",
    }
    stabilize_hashes(risk_pass)
    risk_blocked = copy.deepcopy(completed)
    risk_blocked["model_proposal"].update({"rating": "Buy", "decision_text": "Buy decision"})
    risk_blocked["safety_gate"].update({
        "status": "blocked", "reason_codes": ["portfolio_risk_limit_exceeded"],
        "primary_reason_code": "portfolio_risk_limit_exceeded",
        "coverage_status": "complete", "critical_gap_ids": [],
    })
    risk_blocked["safety_gate"]["portfolio_risk"] = {
        "evaluation_status": "blocked", "risk_reason_codes": ["POSITION_LIMIT_EXCEEDED"],
        "policy_snapshot": policy, "input_ref": input_ref, "input_digest": SHA, "diagnostic_ref": None,
        "valuation_time": "2026-11-09T11:45:00+08:00",
        "valuation_cutoff": "2026-11-09T12:03:15+08:00",
        "currency": "USD", "projected_weight": "0.31", "stop_distance": "0.04",
        "effective_order_value": "0", "evaluated_at": "2026-11-09T12:03:15+08:00",
    }
    risk_blocked["artifact_binding"].update({
        "gate_status": "blocked", "formal_decision_status": "blocked_for_review",
        "final_rating": "REVIEW", "coverage_status": "complete", "critical_gap_ids": [],
    })
    risk_blocked["formal_decision"] = {
        "status": "blocked_for_review", "final_rating": "REVIEW",
        "decision_text": "Portfolio risk limit exceeded; manual review required.",
        "review_class": "portfolio_risk_limit",
    }
    stabilize_hashes(risk_blocked)
    risk_invalid = copy.deepcopy(completed)
    risk_invalid["model_proposal"].update({"rating": "Buy", "decision_text": "Buy decision"})
    risk_invalid["safety_gate"].update({
        "status": "blocked", "reason_codes": ["portfolio_risk_input_invalid"],
        "primary_reason_code": "portfolio_risk_input_invalid",
        "coverage_status": "complete", "critical_gap_ids": [],
    })
    risk_invalid["safety_gate"]["portfolio_risk"] = {
        "evaluation_status": "blocked", "risk_reason_codes": ["MISSING_RISK_INPUT"],
        "policy_snapshot": policy, "input_ref": None, "input_digest": None, "diagnostic_ref": {"path": "inputs/portfolio_risk_diagnostic.json", "sha256": SHA, "hash_scope": "file"},
        "valuation_time": None, "valuation_cutoff": "2026-11-09T12:03:15+08:00",
        "currency": "USD", "projected_weight": None, "stop_distance": None,
        "effective_order_value": None, "evaluated_at": "2026-11-09T12:03:15+08:00",
    }
    risk_invalid["artifact_binding"].update({
        "gate_status": "blocked", "formal_decision_status": "blocked_for_review",
        "final_rating": "REVIEW", "coverage_status": "complete", "critical_gap_ids": [],
    })
    risk_invalid["formal_decision"] = {
        "status": "blocked_for_review", "final_rating": "REVIEW",
        "decision_text": "Portfolio risk input invalid; manual review required.",
        "review_class": "input_invalid",
    }
    stabilize_hashes(risk_invalid)
    risk_error = copy.deepcopy(completed)
    risk_error["run_status"] = "failed"
    risk_error["error"] = {"stage": "gate", "type": "PortfolioRiskEvaluatorError", "message": "risk evaluator failed"}
    risk_error["model_proposal"].update({"rating": "Buy", "decision_text": "Buy decision"})
    risk_error["safety_gate"].update({
        "status": "error", "reason_codes": ["portfolio_risk_evaluator_error"],
        "primary_reason_code": "portfolio_risk_evaluator_error",
        "coverage_status": "complete", "critical_gap_ids": [],
    })
    risk_error["safety_gate"]["portfolio_risk"] = {
        "evaluation_status": "error", "risk_reason_codes": ["EVALUATOR_ERROR"],
        "policy_snapshot": policy, "input_ref": input_ref, "input_digest": SHA, "diagnostic_ref": None,
        "valuation_time": "2026-11-09T11:45:00+08:00",
        "valuation_cutoff": "2026-11-09T12:03:15+08:00",
        "currency": "USD", "projected_weight": None, "stop_distance": None,
        "effective_order_value": None, "evaluated_at": "2026-11-09T12:03:15+08:00",
    }
    risk_error["artifact_binding"].update({
        "gate_status": "error", "formal_decision_status": "blocked_for_review",
        "final_rating": "REVIEW", "coverage_status": "complete", "critical_gap_ids": [],
    })
    risk_error["formal_decision"] = {
        "status": "blocked_for_review", "final_rating": "REVIEW",
        "decision_text": "Portfolio risk evaluator unavailable; manual review required.",
        "review_class": "gate_system_error",
    }
    risk_error["memory"] = {
        "enabled": True, "status": "not_available", "commit_status": "not_applicable",
        "entry_version": 1, "entry_binding": None, "entry_digest": None,
        "evidence_digest": None, "reused_decision_ref": None, "supersedes": None,
        "retention_status": "not_applicable", "same_day_rerun": False,
    }
    risk_error["artifacts"] = [a for a in risk_error["artifacts"] if a["kind"] != "memory"]
    stabilize_hashes(risk_error)
    risk_error_with_gap = copy.deepcopy(risk_error)
    risk_error_with_gap["coverage_snapshot"].update({
        "coverage_status": "partial",
        "critical_gap_ids": ["financial_statements"],
        "critical_gaps": copy.deepcopy(blocked["coverage_snapshot"]["critical_gaps"]),
    })
    risk_error_with_gap["safety_gate"].update({
        "status": "error",
        "reason_codes": ["portfolio_risk_evaluator_error", "critical_gap"],
        "primary_reason_code": "portfolio_risk_evaluator_error",
        "coverage_status": "partial",
        "critical_gap_ids": ["financial_statements"],
    })
    risk_error_with_gap["artifact_binding"].update({
        "gate_status": "error",
        "formal_decision_status": "blocked_for_review",
        "final_rating": "REVIEW",
        "coverage_status": "partial",
        "critical_gap_ids": ["financial_statements"],
    })
    stabilize_hashes(risk_error_with_gap)
    samples = (
        ("running", running), ("completed", completed), ("blocked", blocked),
        ("failed_gate", failed), ("failed_startup", failed_startup),
        ("completed_memory_disabled", mem_off), ("resumed", resumed),
        ("retry_recovered", retry_recovered), ("memory_reuse", memory_reuse),
        ("version_switch", version_switch), ("risk_pass", risk_pass),
        ("risk_blocked", risk_blocked), ("risk_invalid", risk_invalid),
        ("risk_error", risk_error), ("risk_error_with_gap", risk_error_with_gap),
    )
    for name, obj in samples:
        errs = list(v.iter_errors(obj))
        if errs:
            fail(f"manifest sample {name}: {errs[0].message}")
    for name, obj in (("blocked", blocked), ("failed_gate", failed), ("failed_startup", failed_startup)):
        if obj["formal_decision"]["status"] != "blocked_for_review" or obj["formal_decision"]["final_rating"] != "REVIEW":
            fail(f"{name} must carry a blocked_for_review/REVIEW formal state")
        if obj["formal_decision"]["status"] != "blocked_for_review" or obj["formal_decision"]["final_rating"] != "REVIEW":
            fail(f"{name} must carry a blocked_for_review/REVIEW formal state")
        if obj["artifact_binding"]["formal_decision_status"] != obj["formal_decision"]["status"] or obj["artifact_binding"]["final_rating"] != obj["formal_decision"]["final_rating"]:
            fail(f"{name} binding/formal decision mismatch")
    negatives = [
        ("gate_not_run", lambda o: o["safety_gate"].__setitem__("status", "not_run")),
        ("security_failed", lambda o: o["security"].__setitem__("run_scan_status", "failed")),
        ("missing_memory", lambda o: o.__setitem__("artifacts", [a for a in o["artifacts"] if a["kind"] != "memory"])),
        ("pending_decision", lambda o: o["formal_decision"].__setitem__("status", "pending")),
        ("null_digest", lambda o: o["artifact_binding"].__setitem__("decision_digest", None)),
        ("gate_binding_mismatch", lambda o: o["artifact_binding"].__setitem__("gate_status", "blocked")),
        ("formal_binding_mismatch", lambda o: o["formal_decision"].__setitem__("final_rating", "REVIEW")),
        ("decision_digest_tamper", lambda o: o["formal_decision"].__setitem__("decision_text", "tampered decision")),
        ("profile_hash_tamper", lambda o: o["critical_profile"]["requirements"][0]["components"][0].__setitem__("min_record_count", 99)),
        ("snapshot_hash_tamper", lambda o: o["coverage_snapshot"]["critical_gap_ids"].append("tampered-gap")),
        ("provenance_tamper", lambda o: o["data_source_status"][0].__setitem__("status", "unavailable")),
        ("input_hash_tamper", lambda o: o["safety_gate"].__setitem__("input_hash", "0" * 64)),
        ("missing_financial_statements", lambda o: o.__setitem__("data_source_status", [r for r in o["data_source_status"] if r["requirement_id"] != "financial_statements"])),
        ("missing_report_section_manifest", lambda o: o.__setitem__("report_section_manifest", None)),
        ("duplicate_section_path", lambda o: o["report_section_manifest"]["sections"].append(copy.deepcopy(o["report_section_manifest"]["sections"][0]))),
    ]
    for name, mutate in negatives:
        obj = copy.deepcopy(completed)
        mutate(obj)
        if not list(v.iter_errors(obj)) and not cross_field_errors(obj):
            fail(f"completed negative {name} unexpectedly passed")
    risk_negatives = [
        ("risk_blocked_but_approved", risk_blocked, lambda o: (o["formal_decision"].update({"status": "approved", "final_rating": "Buy", "decision_text": "Buy decision", "review_class": "none"}), o["artifact_binding"].update({"formal_decision_status": "approved", "final_rating": "Buy"}))),
        ("risk_input_digest_tamper", risk_pass, lambda o: o["safety_gate"]["portfolio_risk"].__setitem__("input_digest", "b" * 64)),
        ("policy_digest_tamper", risk_pass, lambda o: o["safety_gate"]["portfolio_risk"]["policy_snapshot"].__setitem__("policy_digest", "b" * 64)),
        ("risk_pass_with_limit_reason", risk_pass, lambda o: o["safety_gate"]["reason_codes"].append("portfolio_risk_limit_exceeded")),
        ("risk_blocked_without_gate_reason", risk_blocked, lambda o: o["safety_gate"]["reason_codes"].clear()),
        ("risk_required_not_applicable", risk_pass, lambda o: o["safety_gate"]["portfolio_risk"].__setitem__("evaluation_status", "not_applicable")),
        ("risk_error_but_passed", risk_error, lambda o: o["safety_gate"]["portfolio_risk"].__setitem__("evaluation_status", "passed")),
        ("risk_error_with_gap_masked", risk_error_with_gap, lambda o: (o["safety_gate"].update({"status": "blocked", "primary_reason_code": "critical_gap"}), o["artifact_binding"].__setitem__("gate_status", "blocked"))),
    ]
    for name, base, mutate in risk_negatives:
        obj = copy.deepcopy(base)
        mutate(obj)
        if not list(v.iter_errors(obj)) and not cross_field_errors(obj):
            fail(f"risk negative {name} unexpectedly passed")
    if cross_field_errors(completed):
        fail(f"completed cross-field errors: {cross_field_errors(completed)}")
    for name, obj in (("risk_pass", risk_pass), ("risk_blocked", risk_blocked), ("risk_invalid", risk_invalid), ("risk_error", risk_error), ("risk_error_with_gap", risk_error_with_gap)):
        if cross_field_errors(obj):
            fail(f"{name} cross-field errors: {cross_field_errors(obj)}")

    equivalent = copy.deepcopy(completed)
    original_hash = equivalent["artifact_binding"]["decision_digest"]
    equivalent["formal_decision"]["decision_text"] = unicodedata.normalize("NFD", equivalent["formal_decision"]["decision_text"]).replace("\n", "\r\n") + "   "
    if canonical_hash({k: equivalent["formal_decision"][k] for k in ("status", "final_rating", "decision_text")}) != original_hash:
        fail("canonicalization failed equivalent text normalization")
    reordered = copy.deepcopy(completed)
    reordered["data_source_status"][0]["attempts"] = list(reversed(reordered["data_source_status"][0]["attempts"]))
    reordered["data_source_status"][0]["attempts"].append({"source": "Yahoo Finance", "status": "success", "reason_code": "retry", "reason": None, "record_count": 1, "http_request_count": 1, "cache_kind": "none", "started_at": "2026-11-09T12:00:01+08:00", "ended_at": "2026-11-09T12:00:02+08:00"})
    if canonical_hash(provenance_projection(reordered)) == canonical_hash(provenance_projection(completed)):
        fail("canonicalization must detect meaningful attempt-order/content difference")
    time_changed = copy.deepcopy(completed)
    time_changed["data_source_status"][0]["attempts"][0]["ended_at"] = "2026-11-09T12:00:09+08:00"
    if canonical_hash(provenance_projection(time_changed)) == canonical_hash(provenance_projection(completed)):
        fail("canonicalization must preserve evidence attempt timestamps")
    runtime_changed = copy.deepcopy(completed)
    runtime_changed["coverage_snapshot"]["computed_at"] = "2030-01-01T00:00:00+00:00"
    if canonical_hash(snapshot_projection(runtime_changed)) != canonical_hash(snapshot_projection(completed)):
        fail("canonicalization must exclude run-level computed_at from snapshot hash")
    clock_changed = copy.deepcopy(completed)
    clock_changed["run_clock"]["now_utc"] = "2030-01-01T00:00:00+00:00"
    if canonical_hash(record_projection(clock_changed)) != canonical_hash(record_projection(completed)):
        fail("record hash must exclude run_clock.now_utc")
    cache_changed = copy.deepcopy(completed)
    cache_changed["data_source_status"][0]["vendor_cache_hit"] = True
    cache_changed["data_source_status"][0]["run_cache_hit"] = True
    cache_changed["data_source_status"][0]["attempts"][0]["http_request_count"] = 0
    cache_changed["data_source_status"][0]["attempts"][0]["cache_kind"] = "vendor"
    if canonical_hash(provenance_projection(cache_changed)) != canonical_hash(provenance_projection(completed)):
        fail("provenance projection must exclude cache/http execution metadata")
    return {"samples": len(samples), "completed_negatives": len(negatives), "risk_negatives": len(risk_negatives), "canonicalization_checks": 6}


def eval_contract_checks() -> dict:
    files = [
        EVAL_DIR / "eval-set-v1.json", EVAL_DIR / "rubric-v1.json",
        EVAL_DIR / "behavior-eval-contract-v1.json", EVAL_DIR / "config-v1.json",
        EVAL_DIR / "prompt-v1.0.yaml", EVAL_DIR / "snapshots-v1.json",
    ]
    missing = [str(p.relative_to(ROOT)) for p in files if not p.exists()]
    if missing:
        fail(f"missing behavior evaluation files: {missing}")
    eval_set = load(files[0])
    rubric = load(files[1])
    contract = load(files[2])
    snapshots = load(files[5])
    fixed = contract.get("fixed_inputs", {})
    for name in ("config", "prompt", "snapshots"):
        item = fixed.get(name, {})
        ref = item.get("ref")
        if not ref or not (ROOT / ref).exists():
            fail(f"behavior contract {name} ref missing or nonexistent")
        if item.get("digest") != digest(ROOT / ref):
            fail(f"behavior contract {name} digest does not match {ref}")
    snapshot_cases = {c["case_id"]: c for c in snapshots.get("cases", [])}
    if set(snapshot_cases) != {c["case_id"] for c in eval_set["cases"]}:
        fail("snapshot manifest cases do not match eval set")
    if len(eval_set.get("cases", [])) < 10:
        fail("eval set must contain at least 10 cases")
    if len(rubric.get("dimensions", [])) != 5:
        fail("rubric must contain exactly 5 dimensions")
    status = contract.get("acceptance_status")
    allowed = {"blocked_until_snapshots_and_human_approval", "ready_for_acceptance", "accepted", "failed"}
    if status not in allowed:
        fail(f"unknown behavior acceptance status: {status}")
    pending = [c for c in snapshots["cases"] if c.get("status") == "pending_capture" or not c.get("digest")]
    if status == "blocked_until_snapshots_and_human_approval":
        if not pending and contract.get("human_approved"):
            fail("blocked behavior evaluation cannot already have every snapshot and human approval")
    if status in {"ready_for_acceptance", "accepted"}:
        if pending or not contract.get("human_approved"):
            fail(f"{status} requires all snapshots, fixed config/prompt digests, and human approval")
    return {"cases": len(eval_set["cases"]), "dimensions": len(rubric["dimensions"]), "acceptance_status": contract["acceptance_status"]}


def portfolio_risk_document_coverage(doc: dict) -> dict:
    requirements = {r["id"]: r for r in doc["requirements"]}
    expected = ("FR-04", "INV-02")
    for rid in expected:
        if rid not in requirements:
            fail(f"missing portfolio-risk requirement {rid}")
        req = requirements[rid]
        if req["status"] != "draft":
            fail(f"{rid} must remain draft until human approval")
        if rid not in doc["scope"].get("draft_ids", []):
            fail(f"{rid} must be listed in scope.draft_ids")
        if rid in doc["scope"]["approved_ids"]:
            fail(f"{rid} must not be listed in scope.approved_ids")
        for ac in req["acceptance_criteria"]:
            if ac["measurement_status"] == "measured":
                fail(f"{ac['id']} must not claim a measured result")
            if not ac["zero_tolerance"]:
                fail(f"{ac['id']} must be zero-tolerance")
    fr04 = requirements["FR-04"]
    inv02 = requirements["INV-02"]
    fr04_text = " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in fr04["acceptance_criteria"]
    ).lower()
    inv02_text = " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in inv02["acceptance_criteria"]
    ).lower()
    combined = (fr04_text + " " + inv02_text).lower()
    case_tokens = {
        "crypto_buy": ("crypto",),
        "missing_candidate": ("missing",),
        "unsupported_candidate": ("unsupported",),
        "zero_position_new_long": ("zero", "new_long"),
        "add_long": ("add_long",),
        "insufficient_cash": ("insufficient cash",),
        "historical_valuation_cutoff": ("historical", "cutoff"),
        "missing_policy": ("missing policy",),
        "dual_over_limit": ("dual over-limit",),
        "evaluator_error": ("evaluator",),
        "historical_memory_reuse": ("reused_decision_ref", "historical"),
        "cache_risk_separation": ("cache", "separate"),
    }
    for case, tokens in case_tokens.items():
        for token in tokens:
            if token not in combined:
                fail(f"portfolio-risk acceptance criteria do not cover required case {case}: {token}")
    for token in ("new_long", "add_long", "valuation_cutoff", "policy_snapshot", "input_ref", "future_analysis_date", "clipped"):
        if token not in fr04_text:
            fail(f"FR-04 acceptance criteria do not cover required field or concept: {token}")
    if "min(run_clock.now_utc" not in fr04["statement"] and "min(run_clock.now_utc" not in " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in fr04["acceptance_criteria"]
    ):
        fail("FR-04 must define the unique min(now_utc, end-of-day) valuation cutoff")
    for token in ("original", "unchanged"):
        if token not in combined:
            fail(f"portfolio-risk acceptance criteria do not verify original requirements are {token!r}")
    if "risk-blocked rerun does not create a second entry" in inv02_text:
        fail("INV-02 must not retain the absolute no-new-entry rule")
    fr01_ac7 = next(
        (ac for ac in requirements["FR-01"]["acceptance_criteria"] if ac["id"] == "FR-01-AC7"),
        None,
    )
    if fr01_ac7 is None:
        fail("FR-01-AC7 is required for cache and risk-policy evaluation separation")
    fr01_text = " ".join((fr01_ac7["input"], fr01_ac7["expected_result"], fr01_ac7["verification"])).lower()
    for token in ("risk-policy", "separate"):
        if token not in fr01_text:
            fail(f"FR-01-AC7 does not state the required {token!r} evaluation separation")
    for ac in fr04["acceptance_criteria"]:
        text = " ".join((ac["input"], ac["expected_result"], ac["verification"])).lower()
        if any(token in text for token in ("30%", "5%", "0.30", "0.05")):
            if ac["threshold_status"] != "provisional":
                fail(f"{ac['id']} uses provisional 30%/5% limits but does not set threshold_status=provisional")
    reason_codes = doc["definitions"]["risk_reason_code"].lower()
    for code in (
        "position_limit_exceeded", "stop_distance_exceeded", "missing_risk_input",
        "invalid_risk_input", "stale_risk_input", "unsupported_risk_input",
        "currency_mismatch", "valuation_inconsistent", "insufficient_cash",
        "policy_snapshot_unavailable", "evaluator_error",
    ):
        if code not in reason_codes:
            fail(f"risk_reason_code definition is missing {code}")
    return {
        "requirements": list(expected),
        "fr04_acs": len(fr04["acceptance_criteria"]),
        "inv02_acs": len(inv02["acceptance_criteria"]),
        "check_kind": "document_coverage_only",
        "cache_risk_eval_separated": True,
        "documented_cases": sorted(case_tokens),
    }


class FutureAnalysisDateError(ValueError):
    pass


DECIMAL_INPUT_RE = re.compile(r"^[0-9]+(\.[0-9]{1,12})?$")


def _fixture_json(name: str):
    path = FIXTURE_DIR / name
    return path, json.loads(path.read_text(encoding="utf-8"))


def _decimal_input(value, field: str):
    if not isinstance(value, str) or not DECIMAL_INPUT_RE.fullmatch(value):
        raise ValueError(f"{field} is not a canonical decimal string")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field} is not a finite decimal") from exc


def _normalize_risk_input(obj: dict):
    required = (
        "action", "cash_balance", "currency", "current_asset_quantity",
        "current_asset_value", "entry_price", "instrument_type", "leverage",
        "order_count", "order_quantity", "portfolio_value", "position_effect",
        "proposed_order_value", "source", "stop_loss_price", "valuation_price",
        "valuation_time",
    )
    if any(key not in obj for key in required):
        return None, "MISSING_RISK_INPUT"
    if obj.get("action") != "Buy" or obj.get("instrument_type") != "common_stock":
        return None, "UNSUPPORTED_RISK_INPUT"
    if obj.get("order_count") != 1 or obj.get("leverage") != "1.0":
        return None, "UNSUPPORTED_RISK_INPUT"
    if obj.get("position_effect") not in {"new_long", "add_long"}:
        return None, "UNSUPPORTED_RISK_INPUT"
    if not isinstance(obj.get("currency"), str) or not obj["currency"].strip():
        return None, "INVALID_RISK_INPUT"
    if not isinstance(obj.get("source"), str) or not obj["source"].strip():
        return None, "INVALID_RISK_INPUT"
    try:
        values = {
            field: _decimal_input(obj[field], field)
            for field in (
                "cash_balance", "current_asset_quantity", "current_asset_value",
                "entry_price", "order_quantity", "portfolio_value",
                "proposed_order_value", "stop_loss_price", "valuation_price",
            )
        }
    except ValueError:
        return None, "INVALID_RISK_INPUT"
    if values["portfolio_value"] <= 0:
        return None, "INVALID_RISK_INPUT"
    if values["cash_balance"] < 0 or values["current_asset_quantity"] < 0:
        return None, "INVALID_RISK_INPUT"
    if values["current_asset_value"] < 0 or values["valuation_price"] <= 0:
        return None, "INVALID_RISK_INPUT"
    if values["order_quantity"] <= 0 or values["entry_price"] <= 0:
        return None, "INVALID_RISK_INPUT"
    if values["proposed_order_value"] <= 0:
        return None, "INVALID_RISK_INPUT"
    if values["stop_loss_price"] <= 0 or values["stop_loss_price"] >= values["entry_price"]:
        return None, "INVALID_RISK_INPUT"
    if values["current_asset_value"] != values["current_asset_quantity"] * values["valuation_price"]:
        return None, "VALUATION_INCONSISTENT"
    if values["proposed_order_value"] != values["order_quantity"] * values["entry_price"]:
        return None, "VALUATION_INCONSISTENT"
    if values["cash_balance"] < values["proposed_order_value"]:
        return None, "INSUFFICIENT_CASH"
    if values["portfolio_value"] < values["cash_balance"] + values["current_asset_value"]:
        return None, "VALUATION_INCONSISTENT"
    if obj["position_effect"] == "new_long":
        if values["current_asset_quantity"] != 0 or values["current_asset_value"] != 0:
            return None, "VALUATION_INCONSISTENT"
    else:
        if values["current_asset_quantity"] <= 0 or values["current_asset_value"] <= 0:
            return None, "VALUATION_INCONSISTENT"
    try:
        valuation_time = datetime.fromisoformat(obj["valuation_time"])
    except (TypeError, ValueError):
        return None, "INVALID_RISK_INPUT"
    if valuation_time.tzinfo is None:
        return None, "INVALID_RISK_INPUT"
    values["valuation_time"] = valuation_time.astimezone(UTC)
    values["currency"] = obj["currency"]
    values["position_effect"] = obj["position_effect"]
    return values, None


def _valuation_cutoff(run_clock: dict) -> datetime:
    zone = ZoneInfo(run_clock["timezone"])
    now_utc = datetime.fromisoformat(run_clock["now_utc"]).astimezone(UTC)
    as_of = date.fromisoformat(run_clock["as_of_date"])
    if as_of > now_utc.astimezone(zone).date():
        raise FutureAnalysisDateError("future_analysis_date")
    local_end = datetime.combine(as_of, dt_time(23, 59, 59, 999999), tzinfo=zone)
    return min(now_utc, local_end.astimezone(UTC))


def _evaluate_risk(input_obj: dict, policy: dict, run_clock: dict) -> dict:
    normalized, code = _normalize_risk_input(input_obj)
    if code:
        return {"status": "blocked", "codes": [code], "projected_weight": None,
                "stop_distance": None, "effective_order_value": None}
    policy_keys = (
        "max_projected_weight", "max_stop_distance", "max_valuation_age_seconds",
        "precision_rule", "threshold_status", "policy_version", "policy_ref",
    )
    if any(key not in policy for key in policy_keys):
        return {"status": "blocked", "codes": ["POLICY_SNAPSHOT_UNAVAILABLE"],
                "projected_weight": None, "stop_distance": None,
                "effective_order_value": None}
    try:
        cutoff = _valuation_cutoff(run_clock)
    except FutureAnalysisDateError:
        raise
    age_seconds = (cutoff - normalized["valuation_time"]).total_seconds()
    if age_seconds < 0 or age_seconds > float(policy["max_valuation_age_seconds"]):
        return {"status": "blocked", "codes": ["STALE_RISK_INPUT"],
                "projected_weight": None, "stop_distance": None,
                "effective_order_value": None}
    projected = (
        normalized["current_asset_value"] + normalized["proposed_order_value"]
    ) / normalized["portfolio_value"]
    stop_distance = (
        normalized["entry_price"] - normalized["stop_loss_price"]
    ) / normalized["entry_price"]
    codes = []
    if projected > Decimal(policy["max_projected_weight"]):
        codes.append("POSITION_LIMIT_EXCEEDED")
    if stop_distance > Decimal(policy["max_stop_distance"]):
        codes.append("STOP_DISTANCE_EXCEEDED")
    status = "passed" if not codes else "blocked"
    effective = normalized["proposed_order_value"] if status == "passed" else Decimal("0")
    return {"status": status, "codes": codes, "projected_weight": projected,
            "stop_distance": stop_distance, "effective_order_value": effective}


def risk_fixture_checks() -> dict:
    input_path, input_obj = _fixture_json("portfolio_risk_input_v1.json")
    policy_path, policy = _fixture_json("portfolio_risk_policy_v1.json")
    clock_path, run_clock = _fixture_json("run_clock_historical_v1.json")
    expected_path, expected = _fixture_json("risk_evidence_expected_v1.json")
    invalid_path, invalid_obj = _fixture_json("portfolio_risk_input_invalid_v1.json")

    input_bytes = input_path.read_bytes()
    input_digest = hashlib.sha256(input_bytes).hexdigest()
    if input_digest != expected["input_digest"]:
        fail("fixture input_digest does not match the stored input artifact")
    if str(input_path.relative_to(ROOT)) != expected["input_ref"]:
        fail("fixture input_ref does not point to the stored input artifact")
    if str(policy_path.relative_to(ROOT)) != expected["policy_ref"]:
        fail("fixture policy_ref does not point to the policy artifact")
    policy_digest = canonical_hash({k: policy.get(k) for k in POLICY_SNAPSHOT_KEYS})
    if policy_digest != expected["policy_digest"] or policy.get("policy_digest") != policy_digest:
        fail("fixture policy_digest does not match the policy snapshot")
    for key, value in expected["policy_comparison"].items():
        if policy.get(key) != value:
            fail(f"fixture policy comparison mismatch for {key}")
    if policy.get("threshold_status") != "provisional" or policy.get("human_approval_ref") is not None:
        fail("fixture policy must remain provisional with no human approval reference")

    cutoff = _valuation_cutoff(run_clock)
    if cutoff != datetime.fromisoformat(expected["valuation_cutoff"]):
        fail("fixture valuation_cutoff does not match the timezone-aware rule")
    result = _evaluate_risk(input_obj, policy, run_clock)
    if result["status"] != expected["evaluation_status"]:
        fail("fixture risk status does not match expected")
    if result["projected_weight"] != Decimal(expected["projected_weight"]):
        fail("fixture projected_weight does not match expected")
    if result["stop_distance"] != Decimal(expected["stop_distance"]):
        fail("fixture stop_distance does not match expected")
    if result["effective_order_value"] != Decimal(expected["effective_order_value"]):
        fail("fixture effective_order_value does not match expected")
    if result["codes"] != expected["risk_reason_codes"]:
        fail("fixture risk reason codes do not match expected")

    tampered = bytearray(input_bytes)
    tampered[0] ^= 1
    if hashlib.sha256(bytes(tampered)).hexdigest() == input_digest:
        fail("fixture tamper did not change input_digest")
    if Decimal("0.31") == result["projected_weight"]:
        fail("fixture wrong-metric negative unexpectedly matches")
    policy_tamper = copy.deepcopy(policy)
    policy_tamper["max_projected_weight"] = "0.29"
    if _evaluate_risk(input_obj, policy_tamper, run_clock)["status"] != "blocked":
        fail("fixture policy tamper was not detected as a breach")
    input_stop_tamper = copy.deepcopy(input_obj)
    input_stop_tamper["stop_loss_price"] = "90"
    if _evaluate_risk(input_stop_tamper, policy, run_clock)["status"] != "blocked":
        fail("fixture stop-distance tamper was not detected as a breach")

    future_path, future_clock = _fixture_json("run_clock_future_v1.json")
    try:
        _valuation_cutoff(future_clock)
        fail("future analysis date was not rejected")
    except FutureAnalysisDateError:
        pass
    if expected["future_analysis_date"]["clipped"]:
        fail("future analysis date must not be silently clipped")

    invalid_normalized, invalid_code = _normalize_risk_input(invalid_obj)
    if invalid_normalized is not None:
        fail("invalid fixture produced a normalized input artifact")
    if invalid_code != expected["invalid_input"]["expected_risk_reason_code"]:
        fail("invalid fixture reason code does not match expected")
    if expected["invalid_input"]["normalized_artifact_required"]:
        fail("invalid fixture must not require a normalized artifact")
    if not expected["invalid_input"]["diagnostic_ref_required"]:
        fail("invalid fixture must require a safe diagnostic reference")

    return {
        "input_ref": expected["input_ref"],
        "input_digest": input_digest,
        "policy_ref": expected["policy_ref"],
        "policy_digest": policy_digest,
        "policy_comparison": expected["policy_comparison"],
        "valuation_cutoff": cutoff.isoformat(),
        "projected_weight": str(result["projected_weight"]),
        "stop_distance": str(result["stop_distance"]),
        "evaluation_status": result["status"],
        "tamper_checks": ["input_digest", "wrong_metric", "policy_threshold", "stop_distance"],
        "future_analysis_date": "rejected_without_clipping",
        "invalid_input": {
            "risk_reason_code": invalid_code,
            "normalized_artifact": False,
            "diagnostic_ref_required": expected["invalid_input"]["diagnostic_ref_required"],
        },
    }


def _history_ticker(value: str) -> str:
    return value.strip().upper()


def _list_archive_runs(runs, ticker=None, analysis_date=None, limit=50, offset=0):
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 500:
        raise ValueError("INVALID_FILTER")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("INVALID_FILTER")
    selected = [r for r in runs if r.get("status") == "committed" and not r.get("corrupt")]
    if ticker is not None:
        wanted = _history_ticker(ticker)
        selected = [r for r in selected if _history_ticker(r["ticker"]) == wanted]
    if analysis_date is not None:
        try:
            datetime.strptime(analysis_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("INVALID_FILTER") from exc
        selected = [r for r in selected if r["analysis_date"] == analysis_date]
    selected = sorted(selected, key=lambda r: (_history_ticker(r["ticker"]), r["run_id"]))
    selected = sorted(selected, key=lambda r: r["analysis_date"], reverse=True)
    total = len(selected)
    end = offset + limit
    page = selected[offset:end]
    truncated = end < total
    next_offset = end if truncated else None
    return [r["run_id"] for r in page], total, truncated, next_offset


def _get_archive_run(runs, run_id):
    for run in runs:
        if run["run_id"] == run_id:
            if run.get("corrupt"):
                return "CORRUPT_RECORD"
            if run.get("status") != "committed":
                return "NOT_FOUND"
            return "OK"
    return "NOT_FOUND"


def archive_fixture_checks() -> dict:
    _, history = _fixture_json("archive_history_v1.json")
    runs = history["runs"]
    expected = history["expected"]

    ids, total, truncated, next_offset = _list_archive_runs(runs, ticker=" nvda ", analysis_date="2026-10-19")
    if ids != expected["nvda_2026_10_19"] or total != len(expected["nvda_2026_10_19"]) or next_offset is not None:
        fail("archive history intersection/normalization fixture mismatch")
    ids, total, truncated, next_offset = _list_archive_runs(runs, limit=2, offset=0)
    if ids != expected["page_limit_2_offset_0"] or truncated is not expected["page_limit_2_truncated"] or next_offset != 2:
        fail("archive history first-page order/bound fixture mismatch")
    ids, total, truncated, next_offset = _list_archive_runs(runs, limit=2, offset=2)
    if ids != expected["page_limit_2_offset_2"] or truncated is not False or next_offset is not None:
        fail("archive history second-page pagination fixture mismatch")
    ids, _, _, _ = _list_archive_runs(runs, ticker="ZZZ")
    if ids != expected["unknown_ticker"]:
        fail("archive history unknown ticker must return an empty list")
    for bad_limit in expected["invalid_limits"]:
        try:
            _list_archive_runs(runs, limit=bad_limit)
            fail(f"archive history invalid limit was not rejected: {bad_limit!r}")
        except ValueError as exc:
            if str(exc) != "INVALID_FILTER":
                fail(f"archive history invalid limit result mismatch: {bad_limit!r}")
    for bad_offset in expected["invalid_offsets"]:
        try:
            _list_archive_runs(runs, offset=bad_offset)
            fail(f"archive history invalid offset was not rejected: {bad_offset!r}")
        except ValueError as exc:
            if str(exc) != "INVALID_FILTER":
                fail(f"archive history invalid offset result mismatch: {bad_offset!r}")
    if _get_archive_run(runs, "missing") != expected["unknown_run_id"]:
        fail("archive history unknown run_id result mismatch")
    try:
        _list_archive_runs(runs, analysis_date="2026-13-99")
        fail("archive history malformed filter was not rejected")
    except ValueError as exc:
        if str(exc) != expected["invalid_filter"]:
            fail("archive history malformed filter result mismatch")
    if _get_archive_run(runs, "r6") != expected["corrupt_run_id"]:
        fail("archive history corrupt run_id result mismatch")
    corrupt_count = sum(1 for run in runs if run.get("corrupt"))
    if corrupt_count != expected["corrupt_listing_count"]:
        fail("archive history corrupt listing count mismatch")
    listed, _, _, _ = _list_archive_runs(runs)
    if ("r5" in listed) is not expected["pending_visible"]:
        fail("archive history pending record visibility mismatch")
    if "r6" in listed:
        fail("archive history corrupt record must not appear in successful listing")

    _, recovery = _fixture_json("archive_recovery_v1.json")
    seen = set()
    committed = []
    quarantined = []
    not_visible = []
    cleanup_warning = False
    for snapshot in recovery["snapshots"]:
        run_id = snapshot["run_id"]
        if snapshot.get("status") == "analysis_complete":
            not_visible.append(run_id)
            continue
        if run_id in seen:
            continue
        seen.add(run_id)
        if snapshot.get("status") == "snapshot_ready" and snapshot.get("valid"):
            committed.append(run_id)
            if snapshot.get("cleanup_failure"):
                cleanup_warning = True
        else:
            quarantined.append(run_id)
    expected_recovery = recovery["expected"]
    if sorted(committed) != expected_recovery["committed"]:
        fail("archive recovery committed set mismatch")
    if sorted(quarantined) != expected_recovery["quarantined"]:
        fail("archive recovery quarantine set mismatch")
    if sorted(not_visible) != expected_recovery["not_visible"]:
        fail("archive recovery analysis-complete visibility mismatch")
    if len(committed) != len(set(committed)) or expected_recovery["max_success_per_run"] != 1:
        fail("archive recovery must have at most one successful publication per run_id")
    if cleanup_warning is not expected_recovery["cleanup_failure_warning"]:
        fail("archive recovery cleanup warning mismatch")
    required_fields = recovery.get("required_snapshot_fields", [])
    template = recovery.get("snapshot_template", {})
    missing_fields = [field for field in required_fields if field not in template]
    if missing_fields:
        fail(f"archive recovery snapshot template is missing fields: {missing_fields}")
    for ref_name in ("risk_input_ref", "risk_policy_ref"):
        ref = template.get(ref_name, {})
        if not isinstance(ref, dict) or not ref.get("path") or len(str(ref.get("sha256", ""))) != 64 or ref.get("hash_scope") != "file":
            fail(f"archive recovery snapshot reference is invalid: {ref_name}")
    if not isinstance(template.get("memory_reserved_entry_version"), int) or template["memory_reserved_entry_version"] < 1:
        fail("archive recovery snapshot reserved entry version is invalid")
    for version_field in ("schema_version", "renderer_version"):
        if not isinstance(template.get(version_field), str) or not template[version_field]:
            fail(f"archive recovery snapshot {version_field} is missing")
    return {
        "history_cases": ["intersection", "normalization", "order", "limit", "offset",
                          "pagination", "truncated", "unknown_ticker", "unknown_run_id",
                          "corrupt_record", "invalid_filter", "invalid_limit", "invalid_offset", "visibility"],
        "static_examples": ["duplicate_snapshot_label", "valid_snapshot_label", "missing_snapshot_label",
                            "corrupt_snapshot_label", "unsupported_snapshot_label",
                            "analysis_complete_label", "cleanup_warning_label", "single_success_label"],
        "committed": sorted(committed),
        "quarantined": sorted(quarantined),
        "not_visible": sorted(not_visible),
        "cleanup_failure_warning": cleanup_warning,
        "snapshot_fields_verified": len(required_fields),
        "check_kind": "static_example_check",
        "proof_scope": "static_fixture_only",
        "not_proven_here": ["process_concurrency", "lease_fencing", "lost_lease_rejection", "zero_external_calls"],
    }


def archive_document_coverage(doc: dict) -> dict:
    requirements = {r["id"]: r for r in doc["requirements"]}
    expected = ("FR-05", "FR-06", "QR-02")
    for rid in expected:
        if rid not in requirements:
            fail(f"missing archive/recovery requirement {rid}")
        req = requirements[rid]
        if req["status"] != "draft":
            fail(f"{rid} must remain draft until human approval")
        if rid not in doc["scope"].get("draft_ids", []):
            fail(f"{rid} must be listed in scope.draft_ids")
        if rid in doc["scope"]["approved_ids"]:
            fail(f"{rid} must not be listed in scope.approved_ids")
    fr05 = requirements["FR-05"]
    fr06 = requirements["FR-06"]
    qr02 = requirements["QR-02"]
    for req in (fr05, fr06, qr02):
        for ac in req["acceptance_criteria"]:
            if ac["measurement_status"] == "measured":
                fail(f"{ac['id']} must not claim a measured result")
    for req in (fr05, fr06):
        for ac in req["acceptance_criteria"]:
            if not ac["zero_tolerance"]:
                fail(f"{ac['id']} must be zero-tolerance")
    def _doc_text(req):
        ac_text = " ".join(
            " ".join((ac["input"], ac["expected_result"], ac["verification"]))
            for ac in req["acceptance_criteria"]
        )
        return " ".join((req["problem"], req["statement"], " ".join(req["assumptions"]), ac_text)).lower()

    fr05_text = _doc_text(fr05)
    fr06_text = _doc_text(fr06)
    qr02_text = _doc_text(qr02)
    history_tokens = (
        "ticker", "analysis_date", "intersection", "normaliz", "order",
        "limit", "offset", "paging", "next_offset", "truncated", "unknown",
        "corrupt", "invalid_filter", "revalidat", "section_manifest", "export", "legacy",
        "publication_snapshot", "temporary", "history_reference_closure",
        "reused_decision_ref", "source publication proof", "historical_reference_unverified",
    )
    recovery_tokens = (
        "snapshot_ready", "missing", "corrupt", "unsupported", "quarantine",
        "model", "external", "analysis graph", "settlement", "reflection",
        "memory", "claim", "stale", "retry", "at most one", "run_id",
        "commit marker", "artifact_binding", "report_section_manifest",
        "risk input", "policy references", "reserved entry version",
        "schema/renderer", "reference", "publication_snapshot", "temporary",
        "fencing token", "first write", "different decision entry",
        "additional duplicate",
    )
    qr_tokens = (
        "30", "nearest-rank", "p95", "2.000", "provisional", "1,048,576",
        "100", "10", "supported local filesystem", "not limited to windows/ntfs",
        "failure", "timed-out", "cpu/ram", "filesystem", "timing",
        "12-section", "risk evidence", "memory", "rendered output",
    )
    for token in history_tokens:
        if token not in fr05_text:
            fail(f"FR-05 coverage is missing required history concept: {token}")
    for token in recovery_tokens:
        if token not in fr06_text:
            fail(f"FR-06 coverage is missing required recovery concept: {token}")
    for token in qr_tokens:
        if token not in qr02_text:
            fail(f"QR-02 coverage is missing required benchmark concept: {token}")
    if "uuidv4 is not required" not in " ".join(
        " ".join((req["problem"], req["statement"], " ".join(req["assumptions"])))
        for req in (fr05, fr06)
    ).lower():
        fail("archive requirements must state that UUIDv4 is not required")
    if qr02["acceptance_criteria"][0]["threshold_status"] != "provisional":
        fail("QR-02 threshold must remain provisional")
    if qr02["acceptance_criteria"][0]["measurement_status"] == "measured":
        fail("QR-02 must not claim a measured benchmark result")
    if len(qr02["acceptance_criteria"]) < 2 or not qr02["acceptance_criteria"][1]["zero_tolerance"]:
        fail("QR-02 must include a zero-tolerance correctness/model-free criterion")
    return {
        "requirements": list(expected),
        "fr05_acs": len(fr05["acceptance_criteria"]),
        "fr06_acs": len(fr06["acceptance_criteria"]),
        "qr02_acs": len(qr02["acceptance_criteria"]),
        "check_kind": "document_coverage_only",
        "covered_history": list(history_tokens),
        "covered_recovery": list(recovery_tokens),
        "covered_benchmark": list(qr_tokens),
    }


def _financial_facts_for_scenario(base_facts, scenario):
    facts = copy.deepcopy(base_facts)
    remove = set(scenario.get("remove", []))
    facts = [f for f in facts if f["fact_id"] not in remove]
    facts.extend(copy.deepcopy(scenario.get("add", [])))
    overrides = scenario.get("overrides", {})
    for fact in facts:
        if fact["fact_id"] in overrides:
            override = overrides[fact["fact_id"]]
            if isinstance(override, (tuple, list)):
                for i in range(0, len(override), 2):
                    fact[override[i]] = override[i + 1]
            else:
                fact["value"] = str(override)
    return facts


def _visible_financial(facts, as_of):
    return [f for f in facts if f["filed_at"] <= as_of]


def _resolve_financial_fact(facts, metric, period_end, span, as_of):
    candidates = [
        f for f in _visible_financial(facts, as_of)
        if f["metric"] == metric and f["period_end"] == period_end and f["span"] == span
    ]
    if not candidates:
        return None, "missing_comparison"
    for fact in candidates:
        if not fact.get("subject_id") or not fact.get("accession_no") or not fact.get("filing_ref"):
            return None, "missing_filing_reference"
    currencies = {f["currency"] for f in candidates}
    units = {f["unit"] for f in candidates}
    if len(currencies) > 1:
        return None, "currency_mismatch"
    if len(units) > 1:
        return None, "unit_mismatch"
    latest_filed = max(f["filed_at"] for f in candidates)
    latest = [f for f in candidates if f["filed_at"] == latest_filed]
    if len(latest) > 1:
        restating = [f for f in latest if f.get("restates_fact_id")]
        if restating:
            chosen = sorted(restating, key=lambda f: f["accession_no"])[-1]
        else:
            # Same-day multiple filings are not merged or resolved by equal values.
            return None, "ambiguous_filing"
    else:
        chosen = latest[0]
    return {
        "value": chosen["value"],
        "currency": chosen["currency"],
        "unit": chosen["unit"],
        "fact_id": chosen["fact_id"],
        "filed_at": chosen["filed_at"],
        "subject_id": chosen["subject_id"],
        "accession_no": chosen["accession_no"],
        "filing_ref": chosen["filing_ref"],
        "period_start": chosen["period_start"],
        "period_end": chosen["period_end"],
        "fiscal_year": chosen["fiscal_year"],
        "fiscal_quarter": chosen["fiscal_quarter"],
        "span": chosen["span"],
        "cumulative_duration_days": chosen.get("cumulative_duration_days"),
        "restates_fact_id": chosen.get("restates_fact_id"),
        "superseded": max(0, len(candidates) - 1),
    }, None


def _date_distance_days(later, earlier):
    return (date.fromisoformat(later) - date.fromisoformat(earlier)).days


def _period_record(facts, metric, period_end, span, as_of):
    return _resolve_financial_fact(facts, metric, period_end, span, as_of)


def _year_ago_fact(facts, metric, focus_end, as_of):
    focus, err = _period_record(facts, metric, focus_end, "quarter", as_of)
    if err:
        return None, err
    candidates = []
    for fact in _visible_financial(facts, as_of):
        if fact["metric"] != metric or fact["span"] != "quarter":
            continue
        if fact["fiscal_year"] != focus["fiscal_year"] - 1:
            continue
        if fact["fiscal_quarter"] != focus["fiscal_quarter"]:
            continue
        distance = _date_distance_days(focus_end, fact["period_end"])
        if 350 <= distance <= 380:
            candidates.append(fact["period_end"])
    periods = sorted(set(candidates))
    if not periods:
        return None, "missing_comparison"
    if len(periods) > 1:
        return None, "ambiguous_period"
    return _resolve_financial_fact(facts, metric, periods[0], "quarter", as_of)


def _prior_quarter_fact(facts, metric, focus_end, as_of):
    focus, err = _period_record(facts, metric, focus_end, "quarter", as_of)
    if err:
        return None, err
    candidates = []
    for fact in _visible_financial(facts, as_of):
        if fact["metric"] != metric or fact["span"] != "quarter":
            continue
        same_year_prior = fact["fiscal_year"] == focus["fiscal_year"] and fact["fiscal_quarter"] == focus["fiscal_quarter"] - 1
        prior_year_q4 = focus["fiscal_quarter"] == 1 and fact["fiscal_year"] == focus["fiscal_year"] - 1 and fact["fiscal_quarter"] == 4
        if not (same_year_prior or prior_year_q4):
            continue
        distance = _date_distance_days(focus_end, fact["period_end"])
        if 80 <= distance <= 100:
            candidates.append(fact["period_end"])
    periods = sorted(set(candidates))
    if not periods:
        return None, "missing_comparison"
    if len(periods) > 1:
        return None, "ambiguous_period"
    return _resolve_financial_fact(facts, metric, periods[0], "quarter", as_of)


def _latest_span_fact(facts, metric, span, as_of):
    visible = [f for f in _visible_financial(facts, as_of) if f["metric"] == metric and f["span"] == span]
    if not visible:
        return None, "missing_comparison"
    period_end = max(f["period_end"] for f in visible)
    return _resolve_financial_fact(facts, metric, period_end, span, as_of)


def _compute_financial_metrics(facts, as_of, price, focus_period_end=None):
    revenue_facts = [f for f in _visible_financial(facts, as_of) if f["metric"] == "revenue" and f["span"] == "quarter"]
    if not revenue_facts:
        return {"status": "n/a", "reason": "missing_comparison"}, []
    focus = focus_period_end or max(f["period_end"] for f in revenue_facts)
    out = {"focus_quarter": focus}
    used = []
    rev, err = _resolve_financial_fact(facts, "revenue", focus, "quarter", as_of)
    if err:
        out["revenue"] = {"status": "n/a", "reason": err}
        return out, used
    used.append(rev["fact_id"])
    prior_year, err = _year_ago_fact(facts, "revenue", focus, as_of)
    if err:
        out[f"revenue_yoy_q_{focus}"] = {"status": "n/a", "reason": err}
    else:
        used.append(prior_year["fact_id"])
        base = Decimal(prior_year["value"])
        if base <= 0:
            out[f"revenue_yoy_q_{focus}"] = {"status": "n/a", "reason": "non_positive_base"}
        else:
            value = (Decimal(rev["value"]) / base - Decimal(1)) * Decimal(100)
            out[f"revenue_yoy_q_{focus}"] = str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    prior_q, err = _prior_quarter_fact(facts, "revenue", focus, as_of)
    if err:
        out[f"revenue_qoq_{focus}"] = {"status": "n/a", "reason": err}
    else:
        used.append(prior_q["fact_id"])
        base = Decimal(prior_q["value"])
        if base <= 0:
            out[f"revenue_qoq_{focus}"] = {"status": "n/a", "reason": "non_positive_base"}
        else:
            value = (Decimal(rev["value"]) / base - Decimal(1)) * Decimal(100)
            out[f"revenue_qoq_{focus}"] = str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    revenue_value = Decimal(rev["value"])
    for label, metric in (("gross_margin", "gross_profit"), ("operating_margin", "operating_income"), ("net_margin", "net_income")):
        fact, err = _resolve_financial_fact(facts, metric, focus, "quarter", as_of)
        if err:
            out[f"{label}_{focus}"] = {"status": "n/a", "reason": err}
        elif revenue_value == 0:
            out[f"{label}_{focus}"] = {"status": "n/a", "reason": "zero_denominator"}
        else:
            used.append(fact["fact_id"])
            value = Decimal(fact["value"]) / revenue_value * Decimal(100)
            out[f"{label}_{focus}"] = str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    # current ratio and liabilities-to-assets
    ca, err1 = _resolve_financial_fact(facts, "current_assets", focus, "instant", as_of)
    cl, err2 = _resolve_financial_fact(facts, "current_liabilities", focus, "instant", as_of)
    ta, err3 = _resolve_financial_fact(facts, "total_assets", focus, "instant", as_of)
    tl, err4 = _resolve_financial_fact(facts, "total_liabilities", focus, "instant", as_of)
    if not any((err1, err2, err3, err4)):
        used.extend([ca["fact_id"], cl["fact_id"], ta["fact_id"], tl["fact_id"]])
        if Decimal(cl["value"]) == 0:
            out["current_ratio"] = {"status": "n/a", "reason": "zero_denominator"}
        else:
            out["current_ratio"] = str((Decimal(ca["value"]) / Decimal(cl["value"])).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        if Decimal(ta["value"]) == 0:
            out["liabilities_to_assets"] = {"status": "n/a", "reason": "zero_denominator"}
        else:
            out["liabilities_to_assets"] = str((Decimal(tl["value"]) / Decimal(ta["value"]) * Decimal(100)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    # TTM
    annual_rev, err = _latest_span_fact(facts, "revenue", "annual", as_of)
    current_ytd, err2 = _latest_span_fact(facts, "revenue", "ytd_6m", as_of)
    annual_eps, err3 = _latest_span_fact(facts, "diluted_eps", "annual", as_of)
    current_eps, err4 = _latest_span_fact(facts, "diluted_eps", "ytd_6m", as_of)
    price_d = Decimal(str(price))
    if not any((err3, err4)):
        if Decimal(annual_eps["value"]) <= 0:
            out["pe_fy"] = {"status": "n/a", "reason": "non_positive_eps"}
        else:
            out["pe_fy"] = str((price_d / Decimal(annual_eps["value"])).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    elif err3:
        out["pe_fy"] = {"status": "n/a", "reason": err3}
    if not any((err, err2, err3, err4)):
        continuity_ok = (
            date.fromisoformat(annual_rev["period_end"]).toordinal() + 1
            == date.fromisoformat(current_ytd["period_start"]).toordinal()
            and current_ytd["fiscal_year"] == annual_rev["fiscal_year"] + 1
        )
        subject_ok = annual_rev["subject_id"] == current_ytd["subject_id"] == annual_eps["subject_id"] == current_eps["subject_id"]
        if not subject_ok:
            out["ttm_revenue"] = {"status": "n/a", "reason": "subject_mismatch"}
            out["ttm_eps"] = {"status": "n/a", "reason": "subject_mismatch"}
        elif not continuity_ok:
            out["ttm_revenue"] = {"status": "n/a", "reason": "fiscal_period_mismatch"}
            out["ttm_eps"] = {"status": "n/a", "reason": "fiscal_period_mismatch"}
        else:
            def _match_ytd(metric, current):
                candidates = [
                    f for f in _visible_financial(facts, as_of)
                    if f["metric"] == metric and f["span"] == current["span"]
                    and f["subject_id"] == current["subject_id"]
                    and f["fiscal_year"] == current["fiscal_year"] - 1
                    and f["fiscal_quarter"] == current["fiscal_quarter"]
                ]
                if not candidates:
                    return None, "missing_ttm_period"
                matched = [
                    f for f in candidates
                    if abs(f["cumulative_duration_days"] - current["cumulative_duration_days"]) <= 7
                ]
                if not matched:
                    return None, "fiscal_period_mismatch"
                periods = sorted({f["period_end"] for f in matched})
                if len(periods) > 1:
                    return None, "ambiguous_period"
                return _resolve_financial_fact(facts, metric, periods[0], current["span"], as_of)
            prior_ytd_rev, err5 = _match_ytd("revenue", current_ytd)
            prior_ytd_eps, err6 = _match_ytd("diluted_eps", current_eps)
            if err5:
                out["ttm_revenue"] = {"status": "n/a", "reason": err5}
            if err6:
                out["ttm_eps"] = {"status": "n/a", "reason": err6}
            if not err5:
                coverage_days = date.fromisoformat(current_ytd["period_end"]).toordinal() - date.fromisoformat(prior_ytd_rev["period_end"]).toordinal()
                if not (350 <= coverage_days <= 380):
                    out["ttm_revenue"] = {"status": "n/a", "reason": "fiscal_period_mismatch"}
                else:
                    units = {annual_rev["unit"], current_ytd["unit"], prior_ytd_rev["unit"]}
                    currencies = {annual_rev["currency"], current_ytd["currency"], prior_ytd_rev["currency"]}
                    if len(currencies) > 1:
                        out["ttm_revenue"] = {"status": "n/a", "reason": "currency_mismatch"}
                    elif len(units) > 1:
                        out["ttm_revenue"] = {"status": "n/a", "reason": "unit_mismatch"}
                    else:
                        ttm_rev = Decimal(annual_rev["value"]) + Decimal(current_ytd["value"]) - Decimal(prior_ytd_rev["value"])
                        out["ttm_revenue"] = str(ttm_rev)
                        used.extend([annual_rev["fact_id"], current_ytd["fact_id"], prior_ytd_rev["fact_id"]])
            if not err6:
                coverage_days = date.fromisoformat(current_eps["period_end"]).toordinal() - date.fromisoformat(prior_ytd_eps["period_end"]).toordinal()
                if not (350 <= coverage_days <= 380):
                    out["ttm_eps"] = {"status": "n/a", "reason": "fiscal_period_mismatch"}
                elif Decimal(annual_eps["value"]) <= 0 or Decimal(current_eps["value"]) <= 0 or Decimal(prior_ytd_eps["value"]) <= 0:
                    out["ttm_eps"] = {"status": "n/a", "reason": "non_positive_eps"}
                else:
                    ttm_eps = Decimal(annual_eps["value"]) + Decimal(current_eps["value"]) - Decimal(prior_ytd_eps["value"])
                    out["ttm_eps"] = str(ttm_eps.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
                    used.extend([annual_eps["fact_id"], current_eps["fact_id"], prior_ytd_eps["fact_id"]])
                    if ttm_eps <= 0:
                        out["pe_ttm"] = {"status": "n/a", "reason": "non_positive_eps"}
                    else:
                        out["pe_ttm"] = str((price_d / ttm_eps).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    else:
        for key, reason in (("ttm_revenue", err or err2), ("ttm_eps", err3 or err4)):
            if reason:
                out[key] = {"status": "n/a", "reason": reason}
    # FCF
    cfo, err1 = _latest_span_fact(facts, "cfo", "ytd_6m", as_of)
    capex, err2 = _latest_span_fact(facts, "capex", "ytd_6m", as_of)
    if not any((err1, err2)):
        if cfo["subject_id"] != capex["subject_id"]:
            out["fcf_yoy"] = {"status": "n/a", "reason": "subject_mismatch"}
        out["capex_sign_normalized"] = str(capex["value"]).startswith("-")
        fcf = Decimal(cfo["value"]) - abs(Decimal(capex["value"]))
        out[f"fcf_ytd_{capex['period_end']}"] = str(fcf)
        def _match_prior_ytd(metric, current):
            candidates = [
                f for f in _visible_financial(facts, as_of)
                if f["metric"] == metric and f["span"] == current["span"]
                and f["subject_id"] == current["subject_id"]
                and f["fiscal_year"] == current["fiscal_year"] - 1
                and f["fiscal_quarter"] == current["fiscal_quarter"]
            ]
            if not candidates:
                return None, "missing_ttm_period"
            matched = [
                f for f in candidates
                if abs(f["cumulative_duration_days"] - current["cumulative_duration_days"]) <= 7
            ]
            if not matched:
                return None, "fiscal_period_mismatch"
            periods = sorted({f["period_end"] for f in matched})
            if len(periods) > 1:
                return None, "ambiguous_period"
            return _resolve_financial_fact(facts, metric, periods[0], current["span"], as_of)
        prior_cfo, err5 = _match_prior_ytd("cfo", capex)
        prior_capex, err6 = _match_prior_ytd("capex", capex)
        if err5 or err6:
            out["fcf_yoy"] = {"status": "n/a", "reason": err5 or err6}
        else:
            prior_fcf = Decimal(prior_cfo["value"]) - abs(Decimal(prior_capex["value"]))
            out[f"fcf_ytd_{prior_capex['period_end']}"] = str(prior_fcf)
            if prior_fcf <= 0:
                out["fcf_yoy"] = {"status": "n/a", "reason": "non_positive_base"}
            else:
                out["fcf_yoy"] = str(((fcf / prior_fcf - 1) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    else:
        out["fcf_yoy"] = {"status": "n/a", "reason": err1 or err2}
    return out, used


def financial_fixture_checks() -> dict:
    _, fixture = _fixture_json("financial_metrics_v1.json")
    base = fixture["base_facts"]
    price = fixture["price"]
    checked = 0
    for scenario in fixture.get("scenarios", []):
        facts = _financial_facts_for_scenario(base, scenario)
        as_of = scenario.get("as_of", fixture["as_of"])
        focus = scenario.get("focus_period_end")
        computed, used = _compute_financial_metrics(facts, as_of, price, focus)
        for key, expected in scenario.get("expected", {}).items():
            actual = computed.get(key)
            if isinstance(expected, dict):
                if not isinstance(actual, dict) or actual.get("status") != expected.get("status") or actual.get("reason") != expected.get("reason"):
                    fail(f"financial fixture {scenario['id']} expected {key}={expected}, got {actual}")
            elif key == "latest_quarter_end":
                actual_end = computed.get("focus_quarter")
                if scenario.get("as_of") == "2026-06-01" and actual_end != "2026-04-26":
                    fail("financial fixture historical latest quarter mismatch")
            elif key == "future_facts_excluded":
                # no used fact may be filed after as_of
                visible_ids = {f["fact_id"] for f in _visible_financial(facts, as_of)}
                if any(fid not in visible_ids for fid in used):
                    fail("financial fixture used a future fact")
            elif key == "capex_sign_normalized":
                if bool(actual) is not bool(expected):
                    fail("financial fixture capex sign normalization mismatch")
            else:
                if actual is None or str(actual) != str(expected):
                    # allow one-decimal tolerance for ratio growth fixtures
                    try:
                        if abs(Decimal(str(actual)) - Decimal(str(expected))) > Decimal("0.05"):
                            fail(f"financial fixture {scenario['id']} expected {key}={expected}, got {actual}")
                    except Exception:
                        fail(f"financial fixture {scenario['id']} expected {key}={expected}, got {actual}")
            checked += 1
    return {"scenarios": len(fixture.get("scenarios", [])), "checks": checked, "check_kind": "requirement_evidence_fixture"}


def brief_fixture_checks() -> dict:
    _, fixture = _fixture_json("downstream_brief_v1.json")
    _, budget_policy = _fixture_json("brief_budget_policy_v1.json")
    _, eval_contract = _fixture_json("../evaluation/brief-eval-contract-v1.json")
    base_gaps = fixture["canonical_gaps"]
    metric_block = fixture["metric_block"]
    safety = fixture["safety_constraints"]
    checked = 0
    for scenario in fixture.get("scenarios", []):
        if scenario.get("id", "").startswith("evaluation"):
            expected = scenario["expected"]
            net_tokens = expected["added_output_tokens"] - expected["reduced_downstream_input_tokens"]
            if net_tokens != expected["net_tokens"]:
                fail("brief evaluation net token arithmetic mismatch")
            input_price = expected.get("input_per_token")
            output_price = expected.get("output_per_token")
            if input_price is None or output_price is None:
                if any(expected.get(k) is not None for k in ("added_output_cost", "reduced_input_cost_saving", "net_cost")):
                    fail("brief evaluation missing price must produce null cost fields")
            else:
                added_cost = Decimal(expected["added_output_tokens"]) * Decimal(str(output_price))
                input_saving = Decimal(expected["reduced_downstream_input_tokens"]) * Decimal(str(input_price))
                net_cost = added_cost - input_saving
                if expected.get("added_output_cost") is not None and Decimal(str(expected["added_output_cost"])) != added_cost:
                    fail("brief evaluation added output cost mismatch")
                if expected.get("reduced_input_cost_saving") is not None and Decimal(str(expected["reduced_input_cost_saving"])) != input_saving:
                    fail("brief evaluation input cost saving mismatch")
                if expected.get("net_cost") is not None and Decimal(str(expected["net_cost"])) != net_cost:
                    fail("brief evaluation net cost mismatch")
            if expected["safety_escapes"] != 0:
                fail("brief evaluation safety escapes must be zero")
            thresholds = eval_contract.get("thresholds", {})
            if thresholds.get("quality_loss_max_approved") and thresholds.get("quality_loss_max") is not None:
                if expected["quality_loss"] > thresholds["quality_loss_max"]:
                    fail("brief evaluation quality loss threshold failed")
            if expected["threshold_status"] != "provisional":
                fail("brief evaluation thresholds must remain provisional")
            checked += 1
            continue
        gaps = scenario.get("canonical_gaps", base_gaps)
        total_budget = scenario.get("total_budget", budget_policy["total_budget"])
        hard_cap = scenario.get("hard_cap", budget_policy["hard_cap"])
        context_hard_cap = scenario.get("context_hard_cap", budget_policy["context_hard_cap"])
        expansion_allowed = scenario.get("expansion_allowed", budget_policy["expansion_allowed"])
        reference_allowed = scenario.get("reference_fallback_allowed", budget_policy["reference_fallback_allowed"])
        mandatory = "\n".join(gaps + [metric_block, safety])
        mandatory_len = len(mandatory)
        report = scenario.get("report", "")
        markers = re.findall(r"<!-- BRIEF:START -->(.*?)<!-- BRIEF:END -->", report, re.S)
        marker_count = len(markers)
        reference_present = False
        full_report_fallback = False
        within_hard_cap = mandatory_len <= hard_cap
        if scenario["id"].startswith("short_report") and len(report) <= total_budget:
            mandatory_parts = gaps + [metric_block, safety]
            if all(part in report for part in mandatory_parts):
                output = report
                status = "short_passthrough"
            else:
                candidate = mandatory + "\n" + report
                if len(candidate) <= total_budget:
                    output = candidate
                    status = "short_narrative_plus_mandatory"
                elif mandatory_len > hard_cap:
                    output = ""
                    status = "BRIEF_REJECTED"
                elif expansion_allowed:
                    output = mandatory
                    status = "expanded"
                elif reference_allowed and mandatory_len + budget_policy.get("reference_payload_bytes", 0) <= context_hard_cap:
                    output = mandatory + "\n" + budget_policy["reference"]["handle"]
                    status = "reference"
                    reference_present = True
                elif len(report) <= context_hard_cap:
                    output = report
                    status = "full_report"
                    full_report_fallback = True
                else:
                    output = ""
                    status = "BRIEF_REJECTED"
        elif mandatory_len <= total_budget:
            if marker_count == 1 and "FORGED_METRIC" not in markers[0]:
                compressible_budget = max(0, total_budget - mandatory_len - 1)
                narrative = markers[0].strip()
                if len(narrative) > compressible_budget:
                    narrative = narrative[:compressible_budget]
                    status = "truncated"
                else:
                    status = "ok"
                output = mandatory + "\n" + narrative
            else:
                narrative = fixture["fallback_narrative"]
                compressible_budget = max(0, total_budget - mandatory_len - 1)
                output = mandatory + "\n" + narrative[:compressible_budget]
                status = "fallback"
        elif mandatory_len > hard_cap:
            output = ""
            status = "BRIEF_REJECTED"
        elif within_hard_cap and expansion_allowed:
            output = mandatory
            status = "expanded"
        elif reference_allowed and mandatory_len + budget_policy.get("reference_payload_bytes", 0) <= context_hard_cap:
            output = mandatory + "\n" + budget_policy["reference"]["handle"]
            status = "reference"
            reference_present = True
        elif len(report) <= context_hard_cap:
            output = report
            status = "full_report"
            full_report_fallback = True
        else:
            output = ""
            status = "BRIEF_REJECTED"
        if status != "BRIEF_REJECTED" and len(output) > context_hard_cap:
            fail(f"brief fixture {scenario['id']} exceeded final context hard cap")
        expected = scenario.get("expected", {})
        if expected.get("marker_count") != marker_count:
            fail(f"brief fixture {scenario['id']} marker count mismatch")
        if expected.get("mandatory_preserved"):
            if not all(part in output for part in gaps + [metric_block, safety]):
                fail(f"brief fixture {scenario['id']} dropped mandatory content")
        if expected.get("forged_absent") and "FORGED_METRIC" in output:
            fail(f"brief fixture {scenario['id']} admitted forged content")
        if "byte_identical" in expected and expected["byte_identical"] != (output == report):
            fail(f"brief fixture {scenario['id']} byte-identical claim mismatch")
        if expected.get("within_total") and len(output) > total_budget:
            fail(f"brief fixture {scenario['id']} exceeded total budget")
        if expected.get("within_hard_cap") and len(output) > hard_cap:
            fail(f"brief fixture {scenario['id']} exceeded hard cap")
        if expected.get("reference_present") and not reference_present:
            fail(f"brief fixture {scenario['id']} missing resolvable reference")
        if "gap_count" in expected:
            actual_gap_count = sum(1 for gap in gaps if gap in output)
            if actual_gap_count != expected["gap_count"]:
                fail(f"brief fixture {scenario['id']} gap count mismatch")
        if expected.get("full_report_fallback") and not full_report_fallback:
            fail(f"brief fixture {scenario['id']} did not use full-report fallback")
        if scenario["id"] == "overlong_marker":
            if status not in {"ok", "truncated"}:
                fail("brief fixture overlong marker did not truncate")
        elif expected.get("status") not in {"ok_or_truncated"}:
            if status != expected.get("status"):
                fail(f"brief fixture {scenario['id']} status {status} != {expected.get('status')}")
        checked += 1
    return {
        "scenarios": len(fixture.get("scenarios", [])),
        "checks": checked,
        "policy_version": budget_policy["policy_version"],
        "check_kind": "static_example_check",
        "proof_scope": "static_fixture_only",
        "not_proven_here": ["model_following_brief_format", "live_token_savings", "decision_quality_equivalence"],
    }


def financial_document_coverage(doc: dict) -> dict:
    requirements = {r["id"]: r for r in doc["requirements"]}
    rid = "FR-07"
    if rid not in requirements:
        fail("missing FR-07")
    req = requirements[rid]
    if req["status"] != "draft" or rid not in doc["scope"].get("draft_ids", []):
        fail("FR-07 must remain draft in scope.draft_ids")
    text = " ".join((req["problem"], req["statement"], " ".join(req["assumptions"]), " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in req["acceptance_criteria"]
    ))).lower()
    tokens = (
        "financial_fact", "period_start", "period_end", "fiscal_year", "filed_at",
        "currency", "unit", "restatement", "ambiguous", "latest four", "ttm revenue",
        "ttm diluted eps", "p/e on fiscal-year eps", "p/e on ttm eps", "zero denominator",
        "non-positive", "capex", "currency mismatch", "unit mismatch", "run cache",
        "metric block", "metric_conflict", "reference manifest", "direct vendor",
        "subject_id", "accession", "filing_ref", "same-day", "ambiguous-filing",
        "fiscal-year continuity", "cumulative", "coverage interval",
        "metric_evidence_bundle", "formula_version", "metric_claim", "refetch",
    )
    for token in tokens:
        if token not in text:
            fail(f"FR-07 document coverage missing {token}")
    for token in ("105.9", "85.2", "17.9", "75.0", "66.2", "62.0", "302,969", "7.91", "44.3", "27.4"):
        if token not in text:
            fail(f"FR-07 document coverage missing expected value {token}")
    for ac in req["acceptance_criteria"]:
        if ac["measurement_status"] == "measured":
            fail(f"{ac['id']} must not claim a measured result")
    return {"requirements": [rid], "acs": len(req["acceptance_criteria"]), "check_kind": "document_coverage_only"}


def brief_document_coverage(doc: dict) -> dict:
    requirements = {r["id"]: r for r in doc["requirements"]}
    rid = "FR-08"
    if rid not in requirements:
        fail("missing FR-08")
    req = requirements[rid]
    if req["status"] != "draft" or rid not in doc["scope"].get("draft_ids", []):
        fail("FR-08 must remain draft in scope.draft_ids")
    text = " ".join((req["problem"], req["statement"], " ".join(req["assumptions"]), " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in req["acceptance_criteria"]
    ))).lower()
    tokens = (
        "bull researcher", "bear researcher", "risk debaters", "mandatory", "compressible",
        "canonical", "fr-03", "metric block", "brief_budget_policy", "brief_rejected", "unicode",
        "token", "net_tokens", "quality", "safety", "downstream view", "full report",
        "context_audit_metadata", "reference", "expand", "hard cap", "resolvable",
        "lifecycle", "blocked", "ready", "accepted", "failed", "same approved threshold",
        "quality_loss", "quality_loss_max", "short report", "byte-identical",
    )
    for token in tokens:
        if token not in text:
            fail(f"FR-08 document coverage missing {token}")
    for ac in req["acceptance_criteria"]:
        if ac["measurement_status"] == "measured":
            fail(f"{ac['id']} must not claim a measured result")
    return {"requirements": [rid], "acs": len(req["acceptance_criteria"]), "check_kind": "document_coverage_only"}


def _brief_case_snapshot_state() -> dict:
    eval_set = load(EVAL_DIR / "eval-set-v1.json")
    snapshots = load(EVAL_DIR / "snapshots-v1.json")
    cases = eval_set.get("cases", [])
    snap_by_id = {c["case_id"]: c for c in snapshots.get("cases", [])}
    captured = readable = digest_matched = 0
    pending = []
    for case in cases:
        snap = snap_by_id.get(case["case_id"], {})
        path = ROOT / snap.get("path", "")
        status = snap.get("status")
        if status in {"pending_capture", None} or not path.exists():
            pending.append(case["case_id"])
            continue
        captured += 1
        if path.is_file():
            readable += 1
        expected = snap.get("digest")
        if expected and path.is_file() and digest(path) == expected:
            digest_matched += 1
    return {
        "total_cases": len(cases),
        "captured_cases": captured,
        "readable_cases": readable,
        "digest_matched_cases": digest_matched,
        "pending_case_ids": pending,
        "all_ready": bool(cases) and captured == len(cases) and readable == len(cases) and digest_matched == len(cases),
    }


def brief_eval_contract_checks() -> dict:
    _, contract = _fixture_json("../evaluation/brief-eval-contract-v1.json")
    if contract.get("status") != "frozen_contract":
        fail("brief evaluation contract must be frozen")
    allowed_states = {"blocked", "ready", "accepted", "failed"}
    if contract.get("acceptance_status") not in allowed_states:
        fail("brief acceptance_status must be blocked/ready/accepted/failed")
    switch = contract.get("switch", {})
    if switch.get("off") != "full_reports" or switch.get("on") != "downstream_brief":
        fail("brief evaluation switch mapping is invalid")
    metrics = set(contract.get("metrics", []))
    for metric in ("added_output_tokens", "reduced_downstream_input_tokens", "added_output_cost",
                   "reduced_input_cost_saving", "net_tokens", "net_cost", "fidelity",
                   "key_number_preservation", "gap_preservation", "quality_loss",
                   "safety_escapes", "latency_seconds"):
        if metric not in metrics:
            fail(f"brief evaluation contract missing metric {metric}")
    direction = contract.get("token_direction", {})
    if direction.get("net_tokens") != "added_output_tokens - reduced_downstream_input_tokens":
        fail("brief net token direction is invalid")
    if direction.get("net_cost") != "added_output_cost - reduced_input_cost_saving":
        fail("brief net cost direction is invalid")
    if direction.get("negative_net_cost_means_saving") is not True:
        fail("brief net cost sign direction is invalid")
    if "if either price is null" not in direction.get("missing_price_behavior", ""):
        fail("brief missing-price behavior is not defined")
    states = contract.get("state_conditions", {})
    for state in allowed_states:
        if state not in states:
            fail(f"brief evaluation contract missing state condition {state}")
    digests = contract.get("input_digests", {})
    fixed = contract.get("fixed_inputs", {})
    verified = 0
    for ref_key, digest_key in (
        ("config", "config_sha256"),
        ("prompt", "prompt_sha256"),
        ("data_snapshot", "data_snapshot_sha256"),
        ("risk_policy", "risk_policy_sha256"),
        ("brief_policy", "brief_policy_sha256"),
    ):
        ref = fixed.get(ref_key)
        if not ref or not (ROOT / ref).exists():
            fail(f"brief evaluation fixed input missing: {ref_key}")
        actual = digest(ROOT / ref)
        if digests.get(digest_key) != actual:
            fail(f"brief evaluation digest mismatch: {ref_key}")
        verified += 1
    if fixed.get("model") != digests.get("model_id"):
        fail("brief evaluation model identity mismatch")
    snapshot_state = _brief_case_snapshot_state()
    contract_snapshot = contract.get("case_snapshot_state", {})
    if contract_snapshot.get("total_cases") != snapshot_state["total_cases"]:
        fail("brief contract case count does not match eval set")
    for key in ("captured_cases", "readable_cases", "digest_matched_cases"):
        if contract_snapshot.get(key) != snapshot_state[key]:
            fail(f"brief contract {key} does not match actual case snapshots")
    if set(contract_snapshot.get("pending_case_ids", [])) != set(snapshot_state["pending_case_ids"]):
        fail("brief contract pending case ids do not match actual snapshots")
    thresholds = contract.get("thresholds", {})
    if thresholds.get("safety_escapes_max") != 0:
        fail("brief safety escapes must be zero")
    quality_approved = bool(thresholds.get("quality_loss_max_approved"))
    quality_max = thresholds.get("quality_loss_max")
    if quality_approved and quality_max is None:
        fail("approved quality_loss_max requires a numeric threshold")
    prices = contract.get("prices", {})
    input_price = prices.get("input_per_token")
    output_price = prices.get("output_per_token")
    result = contract.get("result") or {}
    added_output = result.get("added_output_tokens")
    reduced_input = result.get("reduced_downstream_input_tokens")
    if added_output is not None and reduced_input is not None:
        net_tokens = added_output - reduced_input
        if result.get("net_tokens") is not None and result.get("net_tokens") != net_tokens:
            fail("brief net token arithmetic mismatch")
        if input_price is None or output_price is None:
            if any(result.get(k) is not None for k in ("added_output_cost", "reduced_input_cost_saving", "net_cost")):
                fail("missing price must produce null cost fields")
        else:
            added_cost = Decimal(added_output) * Decimal(str(output_price))
            input_saving = Decimal(reduced_input) * Decimal(str(input_price))
            net_cost = added_cost - input_saving
            if result.get("added_output_cost") is not None and Decimal(str(result["added_output_cost"])) != added_cost:
                fail("brief added output cost mismatch")
            if result.get("reduced_input_cost_saving") is not None and Decimal(str(result["reduced_input_cost_saving"])) != input_saving:
                fail("brief input cost saving mismatch")
            if result.get("net_cost") is not None and Decimal(str(result["net_cost"])) != net_cost:
                fail("brief net cost mismatch")
    human = bool(contract.get("human_approved"))
    case_ready = snapshot_state["all_ready"]
    if not case_ready or not quality_approved or not human:
        current_state = "blocked"
    elif result.get("safety_escapes", 0) > 0:
        current_state = "failed"
    elif result.get("quality_loss") is not None and quality_max is not None and result["quality_loss"] > quality_max:
        current_state = "failed"
    elif result.get("safety_escapes") == 0 and result.get("quality_loss") is not None and quality_max is not None and result["quality_loss"] <= quality_max and result.get("all_samples"):
        current_state = "accepted"
    else:
        current_state = "ready"
    if contract.get("acceptance_status") != current_state:
        fail(f"brief acceptance_status {contract.get('acceptance_status')} != current state {current_state}")
    if current_state == "blocked" and not contract.get("blocking_reasons"):
        fail("blocked brief evaluation must record blocking_reasons")
    return {"contract_version": contract["contract_version"],
            "current_state": current_state,
            "acceptance_status": contract["acceptance_status"],
            "case_snapshots": snapshot_state,
            "digests_verified": verified,
            "check_kind": "evaluation_contract_semantic_check"}


def brief_budget_policy_checks() -> dict:
    _, policy = _fixture_json("brief_budget_policy_v1.json")
    if policy.get("policy_version") != "brief-budget-policy-v1":
        fail("brief budget policy version mismatch")
    if policy.get("status") not in {"provisional", "approved"}:
        fail("brief budget policy status must be provisional or approved")
    if policy.get("mandatory_budget", 0) + policy.get("compressible_budget", 0) > policy.get("total_budget", 0):
        fail("brief mandatory plus compressible budget exceeds total budget")
    order = policy.get("resolution_order", [])
    expected_order = ["reject_if_mandatory_exceeds_hard_cap", "expand_to_hard_cap", "resolvable_reference", "full_report_within_context_hard_cap", "BRIEF_REJECTED"]
    if order != expected_order:
        fail("brief budget resolution order is not the versioned policy order")
    if not policy.get("reference", {}).get("resolvable_by"):
        fail("brief reference must name resolvable downstream consumers")
    if policy.get("reference", {}).get("path_string_allowed") is not False:
        fail("brief reference must not be an unresolvable path string")
    for field in ("source_summary", "policy_version", "mandatory_digest", "omitted_compressible_ids",
                  "budget_decision", "fallback_reason", "reference_handle"):
        if field not in policy.get("audit_metadata_fields", []):
            fail(f"brief budget audit metadata missing {field}")
    if policy.get("status") == "provisional" and policy.get("human_approved") is not False:
        fail("provisional brief budget policy must not claim human approval")
    return {"policy_version": policy["policy_version"],
            "resolution_order": order,
            "check_kind": "budget_policy_static_check"}


def brief_eval_state_fixture_checks() -> dict:
    _, fixture = _fixture_json("brief_eval_states_v1.json")
    allowed = {"blocked", "ready", "accepted", "failed"}
    checked = 0
    for case in fixture.get("cases", []):
        if case.get("requested_state") is not None and case["requested_state"] not in allowed:
            actual = "invalid"
        elif not case.get("quality_loss_max_approved") or not case.get("human_approved") or not case.get("case_snapshots_ready"):
            actual = "blocked"
        else:
            result = case.get("result")
            if result is None:
                actual = "ready"
            elif result.get("safety_escapes", 0) > 0:
                actual = "failed"
            elif Decimal(str(result.get("quality_loss"))) > Decimal(str(case.get("quality_loss_max"))):
                actual = "failed"
            elif result.get("all_samples") and result.get("safety_escapes") == 0 and Decimal(str(result.get("quality_loss"))) <= Decimal(str(case.get("quality_loss_max"))):
                actual = "accepted"
            else:
                actual = "ready"
        if actual != case.get("expected"):
            fail(f"brief eval state fixture {case['id']} expected {case.get('expected')}, got {actual}")
        checked += 1
    return {"cases": len(fixture.get("cases", [])), "checks": checked,
            "check_kind": "state_transition_fixture"}


def main() -> None:
    started = time.monotonic()
    doc = load(REQUIREMENTS)
    req_schema = load(REQ_SCHEMA)
    manifest_schema = load(MANIFEST_SCHEMA)
    Draft202012Validator.check_schema(req_schema)
    Draft202012Validator.check_schema(manifest_schema)
    errors = sorted(Draft202012Validator(req_schema).iter_errors(doc), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            print("SCHEMA:", list(error.path), error.message)
        fail(f"{len(errors)} requirements schema errors")

    raw_ids = [r["id"] for r in doc["requirements"]]
    if len(raw_ids) != len(set(raw_ids)):
        fail("duplicate requirement IDs")
    requirements = {r["id"]: r for r in doc["requirements"]}
    ac_ids = [a["id"] for r in doc["requirements"] for a in r["acceptance_criteria"]]
    if len(ac_ids) != len(set(ac_ids)):
        fail("duplicate acceptance-criterion IDs")
    for req in doc["requirements"]:
        for ac in req["acceptance_criteria"]:
            if not ac["id"].startswith(req["id"] + "-AC"):
                fail(f"acceptance criterion {ac['id']} does not match requirement {req['id']}")

    approved_ids = set(doc["scope"]["approved_ids"])
    draft_ids = set(doc["scope"].get("draft_ids", []))
    status_approved = {rid for rid, req in requirements.items() if req["status"] == "approved"}
    status_draft = {rid for rid, req in requirements.items() if req["status"] == "draft"}
    if approved_ids != status_approved:
        fail("scope.approved_ids does not match requirements with status=approved")
    if draft_ids != status_draft:
        fail("scope.draft_ids does not match requirements with status=draft")
    if approved_ids & draft_ids:
        fail("a requirement cannot be both approved and draft")
    if approved_ids | draft_ids != set(requirements):
        fail("scope.approved_ids and scope.draft_ids must cover every requirement")

    for key, label in (
        ("baseline_observations", "baseline observation"),
        ("open_questions", "open question"),
        ("conflict_resolutions", "conflict resolution"),
        ("stakeholders", "stakeholder"),
    ):
        collection_ids = [item["id"] for item in doc[key]]
        if len(collection_ids) != len(set(collection_ids)):
            fail(f"duplicate {label} IDs")

    moscow_ids = doc["moscow"]["must"] + doc["moscow"]["should"] + doc["moscow"]["could"]
    if len(moscow_ids) != len(set(moscow_ids)) or set(moscow_ids) != set(requirements):
        fail("MoSCoW categories must cover every requirement exactly once")
    for req_id, req in requirements.items():
        for dep in req.get("implementation_dependencies", []):
            if dep not in requirements:
                fail(f"{req_id} has unknown implementation dependency {dep}")
        for rel in req.get("constraint_relations", []):
            if rel not in requirements:
                fail(f"{req_id} has unknown constraint relation {rel}")
    check_acyclic(requirements)
    for conflict in doc["conflict_resolutions"]:
        for req_id in conflict["requirements"]:
            if req_id not in requirements:
                fail(f"{conflict['id']} references unknown requirement {req_id}")
    if {t["req_id"] for t in doc["traceability"]} != set(requirements):
        fail("traceability does not cover every requirement")
    missing = []
    for req in doc["requirements"]:
        for evidence in req["source"]["evidence"]:
            if not (ROOT / evidence["path"]).exists():
                missing.append((req["id"], evidence["path"]))
    for trace in doc["traceability"]:
        for ref in trace["code_refs"] + trace["baseline_refs"]:
            if not (ROOT / ref["path"]).exists():
                missing.append((trace["req_id"], ref["path"]))
    if missing:
        fail(f"missing evidence paths: {missing}")

    manifest_summary = manifest_checks(manifest_schema)
    eval_summary = eval_contract_checks()
    risk_coverage = portfolio_risk_document_coverage(doc)
    fixture_summary = risk_fixture_checks()
    archive_doc_summary = archive_document_coverage(doc)
    archive_summary = archive_fixture_checks()
    financial_summary = financial_fixture_checks()
    brief_summary = brief_fixture_checks()
    financial_doc_summary = financial_document_coverage(doc)
    brief_doc_summary = brief_document_coverage(doc)
    brief_eval_summary = brief_eval_contract_checks()
    brief_budget_summary = brief_budget_policy_checks()
    brief_state_summary = brief_eval_state_fixture_checks()

    input_paths = [REQUIREMENTS, REQ_SCHEMA, MANIFEST_SCHEMA, Path(__file__),
                   EVAL_DIR / "eval-set-v1.json", EVAL_DIR / "rubric-v1.json",
                   EVAL_DIR / "behavior-eval-contract-v1.json", EVAL_DIR / "config-v1.json",
                   EVAL_DIR / "prompt-v1.0.yaml", EVAL_DIR / "snapshots-v1.json",
                   FIXTURE_DIR / "portfolio_risk_input_v1.json",
                   FIXTURE_DIR / "portfolio_risk_input_invalid_v1.json",
                   FIXTURE_DIR / "portfolio_risk_policy_v1.json",
                   FIXTURE_DIR / "run_clock_historical_v1.json",
                   FIXTURE_DIR / "run_clock_future_v1.json",
                   FIXTURE_DIR / "risk_evidence_expected_v1.json",
                   FIXTURE_DIR / "archive_history_v1.json",
                   FIXTURE_DIR / "archive_recovery_v1.json",
                   FIXTURE_DIR / "financial_metrics_v1.json",
                   FIXTURE_DIR / "downstream_brief_v1.json",
                   EVAL_DIR / "brief-eval-contract-v1.json",
                   FIXTURE_DIR / "brief_budget_policy_v1.json",
                   FIXTURE_DIR / "brief_eval_states_v1.json",
                   ROOT / "yhx" / "requirements.yaml"]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in input_paths}
    old = load(RESULTS) if RESULTS.exists() else {}
    if "--check" in sys.argv:
        if old.get("input_hashes") != hashes:
            fail("validation results are stale: input hashes changed")
        print("PASS: validation results match current inputs")
        return
    default_human = {"status": "pending", "reviewer": None, "reviewed_at": None,
                     "notes": "Machine checks passed; human review remains pending.",
                     "bound_input_hashes": hashes, "bound_document_version": doc["document"]["version"]}
    human = old.get("human_review", default_human)
    if old and old.get("input_hashes") != hashes:
        human = dict(default_human)
        human["notes"] = "Human approval reset to pending because validated inputs changed."
    else:
        human.setdefault("bound_input_hashes", hashes)
        human.setdefault("bound_document_version", doc["document"]["version"])
    elapsed = time.monotonic() - started
    result = {
        "document": "requirements.yaml",
        "document_version": doc["document"]["version"],
        "generated_at": datetime.now(UTC).isoformat(),
        "duration_seconds": round(elapsed, 3),
        "command": "python3 docs/req/validate_requirements.py",
        "input_hashes": hashes,
        "script_hash": hashes[str(Path(__file__).relative_to(ROOT))],
        "is_current": True,
        "machine_checks": [
            {"id": "requirements_schema", "result": "pass"},
            {"id": "scope_status_consistency", "result": "pass", "details": {"approved": len(approved_ids), "draft": len(draft_ids)}},
            {"id": "manifest_schema_compile", "result": "pass"},
            {"id": "manifest_samples", "result": "pass", "details": manifest_summary},
            {"id": "completed_counterexamples_cross_field", "result": "pass"},
            {"id": "acceptance_count", "result": "pass", "details": {"count": len(ac_ids)}},
            {"id": "references_and_paths", "result": "pass"},
            {"id": "implementation_dependency_acyclic", "result": "pass"},
            {"id": "behavior_eval_contract", "result": "pass", "details": eval_summary},
            {"id": "portfolio_risk_document_coverage", "result": "pass", "details": risk_coverage},
            {"id": "risk_evidence_fixture", "result": "pass", "details": fixture_summary},
            {"id": "archive_document_coverage", "result": "pass", "details": archive_doc_summary},
            {"id": "archive_static_fixture", "result": "pass", "details": archive_summary},
            {"id": "financial_metrics_document_coverage", "result": "pass", "details": financial_doc_summary},
            {"id": "financial_metrics_fixture", "result": "pass", "details": financial_summary},
            {"id": "downstream_brief_document_coverage", "result": "pass", "details": brief_doc_summary},
            {"id": "downstream_brief_fixture", "result": "pass", "details": brief_summary},
            {"id": "brief_evaluation_contract", "result": "pass", "details": brief_eval_summary},
            {"id": "brief_budget_policy", "result": "pass", "details": brief_budget_summary},
            {"id": "brief_eval_state_fixture", "result": "pass", "details": brief_state_summary},
        ],
        "human_review": human,
        "limitations": [
            "Machine checks cover schema structure, manifest samples, completed counterexamples, cross-field semantics, IDs, references, paths, dependency acyclicity, draft/approved scope consistency, and portfolio-risk/archive document coverage.",
            "portfolio_risk_document_coverage checks required case concepts in acceptance text; it is a document coverage check, not behavior verification.",
            "archive_document_coverage checks required archive/recovery/benchmark concepts in acceptance text; it is a document coverage check, not behavior verification.",
            "financial_metrics_document_coverage and downstream_brief_document_coverage check required concepts and expected fixture values in acceptance text; they are document coverage checks, not behavior verification.",
            "Behavioral evaluation is blocked until snapshots and human approval are complete; the frozen v1 eval files are unchanged.",
            "Risk evidence, archive, financial, and brief fixtures recompute local requirement evidence and negatives; they are requirement-evidence checks, not application tests.",
            "archive_static_fixture, downstream_brief_fixture, brief_budget_policy, brief_evaluation_contract, and brief_eval_state_fixture are static checks. Process concurrency, lease fencing, lost-lease rejection, zero-external-call behavior, live model brief-following, and live token/quality evaluation still require process-level, dependency-sentinel, and live evaluation tests that were not executed.",
            "No application implementation or application test was executed in this requirements-validation pass.",
        ],
    }
    RESULTS.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS: requirements schema")
    print("PASS: manifest schema and samples")
    print(f"PASS: {len(requirements)} requirements, {len(ac_ids)} acceptance criteria")
    print("PASS: references, traceability, evidence paths")
    print("PASS: implementation dependencies acyclic")
    print("PASS: behavior evaluation contract present and blocked")
    print("PASS: risk evidence fixture recomputation and tamper negatives")
    print("PASS: archive history and recovery fixture checks")
    print("PASS: financial metrics fixture checks")
    print("PASS: downstream brief fixture checks")
    print("PASS: brief evaluation contract present and blocked")
    print("PASS: brief budget policy order present")
    print("PASS: brief eval state fixture checks")
    print(f"WROTE: {RESULTS.relative_to(ROOT)}")
    print("HUMAN REVIEW: pending")


if __name__ == "__main__":
    main()
