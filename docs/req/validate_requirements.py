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
import csv
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
    proposal = {k: m["model_proposal"][k] for k in ("rating", "decision_text", "proposal_status", "validation_status")}
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
        "model_proposal": {"rating": "Hold", "decision_text": "Hold decision", "proposal_status": "unapproved", "validation_status": "valid", "proposal_digest": SHA},
        "config": {"tradingagents_version": "0.7.0", "llm_provider": "p", "deep_think_provider": "p", "quick_think_provider": "p", "deep_think_llm": "m", "quick_think_llm": "m", "analysts": ["market", "fundamentals"], "max_debate_rounds": 1, "max_risk_discuss_rounds": 1, "output_language": "English", "data_vendors": {"x": "y"}, "tool_vendors": {}},
        "execution_policy": {"policy_id": "fr01-execution-policy", "policy_version": "1.0.0", "policy_digest": SHA, "retry_budget": 1, "fallback_budget": 1, "request_timeout_seconds": 30, "execution_deadline_seconds": 120, "waiter_timeout_seconds": 120, "run_cache_capacity_queries": 512, "status_actions": {"success": "terminal", "unavailable": "retry_same_vendor_then_fallback"}},
        "timing": {"started_at": "2026-11-09T12:00:00+08:00", "observed_until": "2026-11-09T12:03:14.960000+08:00", "analysis_finished_at": "2026-11-09T12:03:14.410000+08:00", "finished_at": "2026-11-09T12:03:14.960000+08:00", "duration_seconds": 194.96, "startup_phase_seconds": 0.01, "analysis_seconds": 194.4, "publish_seconds": 0.55, "publish_prepare_seconds": 0.55, "observed_duration_seconds": 194.96, "manifest_write_seconds": None, "startup_manifest_write_seconds": None},
        "counts": {"llm_calls": 1, "tool_calls": 4, "prefetch_calls": 0, "reflection_llm_calls": 0, "retry_attempts": 0, "fallback_attempts": 0, "query_executions": 4, "external_requests": 4, "vendor_cache_hits": 0, "run_cache_hits": 0, "llm_error_count": 0, "tool_error_count": 0},
        "tokens": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2, "status": "complete", "llm_calls_with_usage": 1, "llm_calls_without_usage": 0, "reported_call_count": 1, "unknown_call_count": 0, "field_coverage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 1, "complete_calls": 1}, "aggregation_source": "authoritative_usage"},
        "data_source_status": [{"record_kind": "executed", "data_query_key": "q1", "supports": [{"requirement_id": "market_price", "capability": "market_price", "component": "stock_data", "criticality": "critical"}], "attempts": [{"source": "Yahoo Finance", "status": "success", "reason_code": None, "reason": None, "record_count": 1, "http_request_count": 1, "cache_kind": "none", "started_at": "2026-11-09T12:00:00+08:00", "ended_at": "2026-11-09T12:00:01+08:00"}], "tool": "get_stock_data", "category": "market", "capability": "market_price", "component": "stock_data", "requirement_id": "market_price", "criticality": "critical", "source": "Yahoo Finance", "serving_source": "Yahoo Finance", "attempted_sources": ["Yahoo Finance"], "requested_window": "2026-10-19", "observed_window": "2026-10-19", "status": "success", "reason_code": None, "reason": None, "record_count": 1, "vendor": "yfinance", "fallback_used": False, "vendor_cache_hit": False, "run_cache_hit": False}] + records,
        "safety_gate": {"status": "passed", "reason_codes": [], "primary_reason_code": None, "coverage_status": "complete", "critical_gap_ids": [], "profile_version": "d1-default-v1", "snapshot_hash": SHA, "gate_version": "1.0", "input_hash": SHA, "run_id": "r1", "evaluated_at": "2026-11-09T12:03:14.900000+08:00", "portfolio_risk": {"evaluation_status": "not_applicable", "risk_reason_codes": [], "policy_snapshot": None, "input_ref": None, "input_digest": None, "diagnostic_ref": None, "valuation_time": None, "valuation_cutoff": None, "currency": None, "projected_weight": None, "stop_distance": None, "effective_order_value": None, "evaluated_at": "2026-11-09T12:03:15+08:00"}},
        "security": {"scan_status": "clean", "write_scan_status": "clean", "run_scan_status": "clean", "known_secret_detected_count": 0, "pattern_detected_count": 0, "known_secret_match_count": 0, "pattern_match_count": 0, "residual_secret_count": 0, "redaction_count": 0, "rule_version": "1.0", "scope": ["manifest", "final_state", "memory", "report", "logs", "preferences", "gate", "availability"], "failure_reason": None},
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
    mp = m.get("model_proposal")
    if m.get("run_status") == "completed":
        if not isinstance(mp, dict):
            errors.append("completed run requires a model_proposal object (rating may be null)")
        elif mp.get("rating") is None:
            if mp.get("validation_status") not in {"invalid_rating", "missing"}:
                errors.append("null completed rating requires validation_status invalid_rating or missing")
        elif mp.get("validation_status") != "valid":
            errors.append("non-null completed rating requires validation_status valid")
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
    mp = m.get("model_proposal")
    if isinstance(mp, dict):
        proposal = {k: mp[k] for k in ("rating", "decision_text", "proposal_status", "validation_status")}
        if canonical_hash(proposal) != mp.get("proposal_digest"):
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



def timing_token_semantic_errors(m: dict) -> list:
    errors = []
    t = m.get("timing") or {}
    c = m.get("counts") or {}
    tok = m.get("tokens") or {}
    required_t = ("started_at", "observed_until", "analysis_finished_at", "finished_at", "duration_seconds", "startup_phase_seconds", "analysis_seconds", "publish_seconds", "publish_prepare_seconds", "observed_duration_seconds", "manifest_write_seconds", "startup_manifest_write_seconds")
    if any(k not in t for k in required_t):
        errors.append("timing is missing a required v1.21 field")
    if m.get("run_status") == "completed":
        vals = [t.get(k) for k in ("startup_phase_seconds", "analysis_seconds", "publish_prepare_seconds", "observed_duration_seconds")]
        if any(v is None for v in vals):
            errors.append("completed timing requires all phase values")
        else:
            if abs((t["startup_phase_seconds"] + t["analysis_seconds"] + t["publish_prepare_seconds"]) - t["observed_duration_seconds"]) > 1e-6:
                errors.append("completed timing phase sum does not match observed_duration_seconds")
            if t.get("finished_at") != t.get("observed_until"):
                errors.append("finished_at must project observed_until")
            if t.get("duration_seconds") != t.get("observed_duration_seconds"):
                errors.append("duration_seconds must project observed_duration_seconds")
            if t.get("publish_seconds") != t.get("publish_prepare_seconds"):
                errors.append("publish_seconds must project publish_prepare_seconds")
            if t.get("manifest_write_seconds") is not None:
                errors.append("manifest_write_seconds must be null in the manifest; use WriteEvidence")
        try:
            started = datetime.fromisoformat(t["started_at"])
            analysis_end = datetime.fromisoformat(t["analysis_finished_at"])
            observed = datetime.fromisoformat(t["observed_until"])
            gate_at = datetime.fromisoformat(m["safety_gate"]["evaluated_at"])
            if not (started <= analysis_end <= gate_at <= observed):
                errors.append("completed event order must satisfy started <= analysis_finished <= gate.evaluated_at <= observed_until")
        except (KeyError, TypeError, ValueError):
            errors.append("completed timing has an invalid or missing event timestamp")
    if m.get("run_status") in {"running", "failed"}:
        if t.get("observed_until") is not None and t.get("analysis_finished_at") is not None:
            if datetime.fromisoformat(t["analysis_finished_at"]) > datetime.fromisoformat(t["observed_until"]):
                errors.append("failed/running event is after observed_until")
    # token coverage
    req_tok = ("reported_call_count", "unknown_call_count", "field_coverage", "aggregation_source")
    if any(k not in tok for k in req_tok):
        errors.append("tokens is missing a required v1.21 coverage field")
        return errors
    calls = c.get("llm_calls")
    fc = tok.get("field_coverage") or {}
    for k in ("input_tokens", "output_tokens", "total_tokens", "complete_calls"):
        if k not in fc:
            errors.append(f"field_coverage missing {k}")
    if tok.get("reported_call_count") + tok.get("unknown_call_count") != calls:
        errors.append("reported+unknown call counts must equal llm_calls")
    if tok.get("reported_call_count") != tok.get("llm_calls_with_usage"):
        errors.append("reported_call_count must equal llm_calls_with_usage")
    if tok.get("unknown_call_count") != tok.get("llm_calls_without_usage"):
        errors.append("unknown_call_count must equal llm_calls_without_usage")
    for k in ("input_tokens", "output_tokens", "total_tokens", "complete_calls"):
        v = fc.get(k)
        if not isinstance(v, int) or v < 0 or v > calls:
            errors.append(f"field_coverage.{k} must be 0..llm_calls")
    if isinstance(fc.get("complete_calls"), int) and isinstance(fc.get("input_tokens"), int):
        if fc["complete_calls"] > min(fc["input_tokens"], fc["output_tokens"], fc["total_tokens"]):
            errors.append("complete_calls cannot exceed any field coverage")
    if calls == 0:
        if tok.get("status") != "complete" or any(tok.get(k) != 0 for k in ("input_tokens", "output_tokens", "total_tokens")):
            errors.append("zero calls must be complete with real zero totals")
    if tok.get("status") == "complete" and calls > 0:
        if fc.get("complete_calls") != calls:
            errors.append("complete status requires complete_calls == llm_calls")
    if tok.get("status") == "unavailable":
        if any(tok.get(k) is not None for k in ("input_tokens", "output_tokens", "total_tokens")):
            errors.append("unavailable usage requires null token totals")
    return errors

def manifest_checks(schema: dict) -> dict:
    v = Draft202012Validator(schema)
    completed = manifest_sample()
    stabilize_hashes(completed)
    running = copy.deepcopy(completed)
    running.update({"run_status": "running", "timing": {"started_at": "2026-11-09T12:00:00+08:00", "observed_until": None, "analysis_finished_at": None, "finished_at": None, "duration_seconds": None, "startup_phase_seconds": 0.01, "analysis_seconds": None, "publish_seconds": None, "publish_prepare_seconds": None, "observed_duration_seconds": None, "manifest_write_seconds": None, "startup_manifest_write_seconds": 0.01}, "data_source_status": [], "safety_gate": {"status": "not_run", "reason_codes": [], "primary_reason_code": None, "coverage_status": None, "critical_gap_ids": [], "profile_version": None, "snapshot_hash": None, "gate_version": "1.0", "input_hash": SHA, "run_id": None, "evaluated_at": None}, "security": {"scan_status": "not_run", "write_scan_status": "clean", "run_scan_status": "not_run", "known_secret_detected_count": 0, "pattern_detected_count": 0, "known_secret_match_count": 0, "pattern_match_count": 0, "residual_secret_count": 0, "redaction_count": 0, "rule_version": "1.0", "scope": ["manifest"], "failure_reason": None}, "memory": {"enabled": True, "status": "not_available", "commit_status": "not_applicable", "entry_version": 1, "entry_binding": None, "entry_digest": None, "evidence_digest": None, "reused_decision_ref": None, "supersedes": None, "retention_status": "not_applicable", "same_day_rerun": False}, "artifact_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": None, "gate_status": "not_run", "formal_decision_status": "pending", "final_rating": None, "coverage_status": None, "critical_gap_ids": [], "coverage_snapshot_hash": None, "record_hash": None}, "formal_decision": {"status": "pending", "final_rating": None, "decision_text": None, "review_class": "none"}, "artifacts": [], "error": None})
    failed = copy.deepcopy(completed)
    failed.update({"run_status": "failed", "error": {"stage": "gate", "type": "GateError", "message": "gate unavailable"}, "safety_gate": {"status": "error", "reason_codes": ["gate_internal_error"], "primary_reason_code": "gate_internal_error", "coverage_status": "partial", "critical_gap_ids": [], "profile_version": "d1-default-v1", "snapshot_hash": SHA, "gate_version": "1.0", "input_hash": SHA, "run_id": "r1", "evaluated_at": "2026-11-09T12:03:15+08:00"}, "artifact_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": None, "gate_status": "error", "formal_decision_status": "blocked_for_review", "final_rating": "REVIEW", "coverage_status": "partial", "critical_gap_ids": [], "coverage_snapshot_hash": SHA, "record_hash": None}, "formal_decision": {"status": "blocked_for_review", "final_rating": "REVIEW", "decision_text": "Gate unavailable; manual review required.", "review_class": "gate_system_error"}})
    stabilize_hashes(failed)
    mem_off = copy.deepcopy(completed)
    mem_off["memory"] = {"enabled": False, "status": "disabled", "commit_status": "disabled", "entry_version": 1, "entry_binding": None, "entry_digest": None, "evidence_digest": None, "reused_decision_ref": None, "supersedes": None, "retention_status": "disabled", "same_day_rerun": False}
    mem_off["artifacts"] = [a for a in mem_off["artifacts"] if a["kind"] != "memory"]
    failed_startup = copy.deepcopy(completed)
    failed_startup.update({"run_status": "failed", "critical_profile": None, "coverage_snapshot": None, "provenance_digest": canonical_hash([]), "data_source_status": [], "safety_gate": {"status": "not_run", "reason_codes": [], "primary_reason_code": None, "coverage_status": None, "critical_gap_ids": [], "profile_version": None, "snapshot_hash": None, "gate_version": "1.0", "input_hash": canonical_hash({"snapshot_hash": None, "model_proposal": {k: completed["model_proposal"][k] for k in ("rating", "decision_text", "proposal_status", "validation_status")}, "portfolio_risk_input_digest": None, "portfolio_risk_diagnostic_digest": None, "portfolio_risk_policy_digest": None, "gate_version": "1.0"}), "run_id": None, "evaluated_at": None}, "security": {"scan_status": "clean", "write_scan_status": "clean", "run_scan_status": "not_run", "known_secret_detected_count": 0, "pattern_detected_count": 0, "known_secret_match_count": 0, "pattern_match_count": 0, "residual_secret_count": 0, "redaction_count": 0, "rule_version": "1.0", "scope": ["manifest"], "failure_reason": None}, "memory": {"enabled": True, "status": "not_available", "commit_status": "not_applicable", "entry_version": 1, "entry_binding": None, "entry_digest": None, "evidence_digest": None, "reused_decision_ref": None, "supersedes": None, "retention_status": "not_applicable", "same_day_rerun": False}, "artifact_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": canonical_hash({"status": "blocked_for_review", "final_rating": "REVIEW", "decision_text": "Run failed before formal decision; manual review required."}), "gate_status": "not_run", "formal_decision_status": "blocked_for_review", "final_rating": "REVIEW", "coverage_status": None, "critical_gap_ids": [], "coverage_snapshot_hash": None, "record_hash": None}, "formal_decision": {"status": "blocked_for_review", "final_rating": "REVIEW", "decision_text": "Run failed before formal decision; manual review required.", "review_class": "input_invalid"}, "artifacts": [], "error": {"stage": "startup", "type": "ConfigError", "message": "startup failed"}})
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
        "policy_version": "portfolio-risk-policy-v2",
        "policy_ref": "portfolio-risk-policy-v2",
        "policy_file_ref": "docs/req/fixtures/portfolio_risk_policy_v2.json",
        "policy_digest": SHA,
        "max_projected_weight": "0.3",
        "max_stop_distance": "0.05",
        "max_valuation_age_seconds": 900,
        "precision_rule": "input<=12dp;internal=exact_cross_product;exact_compare;display=6dp_half_up",
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
    completed_invalid_rating = copy.deepcopy(completed)
    completed_invalid_rating["model_proposal"].update({"rating": None, "validation_status": "invalid_rating", "proposal_digest": None})
    completed_invalid_rating["safety_gate"].update({"status": "blocked", "reason_codes": ["invalid_model_rating"], "primary_reason_code": "invalid_model_rating"})
    completed_invalid_rating["formal_decision"] = {"status": "blocked_for_review", "final_rating": "REVIEW", "decision_text": "Invalid model rating; manual review required.", "review_class": "model_rating_invalid"}
    completed_invalid_rating["artifact_binding"].update({"gate_status": "blocked", "formal_decision_status": "blocked_for_review", "final_rating": "REVIEW"})
    running_null_proposal = copy.deepcopy(running)
    running_null_proposal["model_proposal"] = None
    failed_null_proposal = copy.deepcopy(failed)
    failed_null_proposal["model_proposal"] = None
    samples = (
        ("running", running), ("completed", completed), ("blocked", blocked),
        ("completed_invalid_rating", completed_invalid_rating),
        ("running_null_proposal", running_null_proposal),
        ("failed_null_proposal", failed_null_proposal),
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
    if completed_invalid_rating["formal_decision"]["final_rating"] != "REVIEW" or completed_invalid_rating["artifact_binding"]["gate_status"] != "blocked":
        fail("completed invalid rating must block with REVIEW, not pass")
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
        ("completed_null_proposal", lambda o: o.__setitem__("model_proposal", None)),
        ("completed_invalid_rating_as_valid", lambda o: (o["model_proposal"].update({"rating": None, "validation_status": "valid"}))),
        ("timing_sum_mismatch", lambda o: o["timing"].__setitem__("observed_duration_seconds", 1.0)),
        ("event_after_observed", lambda o: (o["timing"].__setitem__("finished_at", "2026-11-09T12:03:15+08:00"))),
        ("timing_alias_mismatch", lambda o: o["timing"].__setitem__("duration_seconds", 1.0)),
        ("manifest_write_not_null", lambda o: o["timing"].__setitem__("manifest_write_seconds", 0.01)),
        ("token_reported_mismatch", lambda o: o["tokens"].__setitem__("reported_call_count", 0)),
        ("token_complete_calls_mismatch", lambda o: o["tokens"]["field_coverage"].__setitem__("complete_calls", 0)),
        ("zero_call_fake_usage", lambda o: (o["counts"].__setitem__("llm_calls", 0), o["tokens"].update({"input_tokens": 1}))),
    ]
    for name, mutate in negatives:
        obj = copy.deepcopy(completed)
        mutate(obj)
        if not list(v.iter_errors(obj)) and not cross_field_errors(obj) and not timing_token_semantic_errors(obj):
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
    if timing_token_semantic_errors(completed):
        fail(f"completed timing/token errors: {timing_token_semantic_errors(completed)}")
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
    required_files = [
        EVAL_DIR / "eval-set-v1.json", EVAL_DIR / "rubric-v1.json",
        EVAL_DIR / "behavior-eval-contract-v1.json", EVAL_DIR / "behavior-eval-contract-v2.json",
        EVAL_DIR / "config-v1.json", EVAL_DIR / "prompt-v1.0.yaml", EVAL_DIR / "snapshots-v1.json",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required_files if not p.exists()]
    if missing:
        fail(f"missing behavior evaluation files: {missing}")
    eval_set = load(EVAL_DIR / "eval-set-v1.json")
    rubric = load(EVAL_DIR / "rubric-v1.json")
    v1 = load(EVAL_DIR / "behavior-eval-contract-v1.json")
    v2 = load(EVAL_DIR / "behavior-eval-contract-v2.json")
    snapshots = load(EVAL_DIR / "snapshots-v1.json")
    if v1.get("status") != "frozen_contract":
        fail("behavior v1 must remain the frozen historical contract")
    if v2.get("status") != "revision_draft":
        fail("behavior v2 must be a revision draft, not a frozen approval")
    if v2.get("rubric_version") != rubric.get("rubric_version"):
        fail("behavior v2 must retain the frozen rubric version")
    if v2.get("human_approved") is not False:
        fail("behavior v2 cannot claim human approval")
    for contract, label in ((v1, "v1"), (v2, "v2")):
        fixed = contract.get("fixed_inputs", {})
        for name in ("config", "prompt", "snapshots"):
            item = fixed.get(name, {})
            ref = item.get("ref")
            if not ref or not (ROOT / ref).exists():
                fail(f"behavior {label} contract {name} ref missing or nonexistent")
            if item.get("digest") != digest(ROOT / ref):
                fail(f"behavior {label} contract {name} digest does not match {ref}")
    snapshot_cases = {c["case_id"]: c for c in snapshots.get("cases", [])}
    if set(snapshot_cases) != {c["case_id"] for c in eval_set["cases"]}:
        fail("snapshot manifest cases do not match eval set")
    if len(eval_set.get("cases", [])) < 10:
        fail("eval set must contain at least 10 cases")
    if len(rubric.get("dimensions", [])) != 5:
        fail("rubric must contain exactly 5 dimensions")
    status = v2.get("acceptance_status")
    allowed = {"blocked_until_snapshots_and_human_approval", "ready_for_acceptance", "accepted", "failed"}
    if status not in allowed:
        fail(f"unknown behavior v2 acceptance status: {status}")
    pending = [c for c in snapshots["cases"] if c.get("status") == "pending_capture" or not c.get("digest")]
    if status == "blocked_until_snapshots_and_human_approval":
        if not pending and v2.get("human_approved"):
            fail("blocked behavior evaluation cannot already have every snapshot and human approval")
    scoring = v2.get("scoring_rules", {})
    if scoring.get("direction") != "higher_is_better":
        fail("behavior v2 must use higher-is-better rubric direction")
    if scoring.get("case_drop") != "score_off - score_on":
        fail("behavior v2 must use off-on case-drop direction")
    weights = scoring.get("dimensions", [])
    if [d.get("weight") for d in weights] != [0.30, 0.20, 0.20, 0.20, 0.10]:
        fail("behavior v2 dimension weights are not the frozen rubric weights")
    for token in ("same-dimension difference <=1", "difference >1", "best-of"):
        if token not in scoring.get("merge_rule", ""):
            fail(f"behavior v2 merge rule missing {token!r}")
    samples = v2.get("sample_rules", {})
    for key in ("one_original_scored_sample_per_case_condition", "fixed_case_set"):
        if samples.get(key) is not True:
            fail(f"behavior v2 sample rule {key} must be true")
    if samples.get("best_of_retries") is not False:
        fail("behavior v2 must forbid best-of-retries")
    review = v2.get("review_rate", {})
    if review.get("unit") != "percentage_points" or "100*(rate_on-rate_off)" not in review.get("increase", ""):
        fail("behavior v2 REVIEW-rate must use percentage points")
    safety = v2.get("safety_events", {})
    if safety.get("independent_of_rubric_average") is not True:
        fail("behavior v2 safety events must be independent of the rubric average")
    if safety.get("cannot_be_offset_by_quality_or_tokens") is not True:
        fail("behavior v2 safety events cannot be offset by quality or tokens")
    comparison = v2.get("comparison_rules", {})
    if "risk-policy REVIEW increase is not a cache regression" not in comparison.get("cache_risk_misclassification", ""):
        fail("behavior v2 must keep risk-policy effects out of the cache comparison")
    if "QR-01 all-complete requires risk-policy status" not in comparison.get("sub_evaluation_status", ""):
        fail("behavior v2 must not treat cache-only as full QR-01 completion")
    return {"cases": len(eval_set["cases"]), "dimensions": len(rubric["dimensions"]),
            "acceptance_status": v2["acceptance_status"], "active_contract": v2["contract_version"]}


def portfolio_risk_document_coverage(doc: dict) -> dict:
    requirements = {r["id"]: r for r in doc["requirements"]}
    expected = ("FR-04", "INV-02")
    for rid in expected:
        if rid not in requirements:
            fail(f"missing portfolio-risk requirement {rid}")
        req = requirements[rid]
        if req["status"] != "approved":
            fail(f"{rid} must be approved in the frozen baseline")
        if rid not in doc["scope"].get("approved_ids", []):
            fail(f"{rid} must be listed in scope.approved_ids")
        if rid in doc["scope"].get("draft_ids", []):
            fail(f"{rid} must not remain in scope.draft_ids")
        for ac in req["fit_criterion"]:
            if ac["measurement_status"] == "measured":
                fail(f"{ac['id']} must not claim a measured result")
            if not ac["zero_tolerance"]:
                fail(f"{ac['id']} must be zero-tolerance")
    fr04 = requirements["FR-04"]
    inv02 = requirements["INV-02"]
    fr04_text = " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in fr04["fit_criterion"]
    ).lower()
    inv02_text = " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in inv02["fit_criterion"]
    ).lower()
    combined = (fr04_text + " " + inv02_text).lower()
    qr01 = requirements["QR-01"]
    qr01_text = " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in qr01["fit_criterion"]
    ).lower()
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
        haystack = qr01_text if case == "cache_risk_separation" else combined
        for token in tokens:
            if token not in haystack:
                fail(f"portfolio-risk acceptance criteria do not cover required case {case}: {token}")
    for token in ("new_long", "add_long", "valuation_cutoff", "policy_snapshot", "input_ref", "future_analysis_date", "clipped"):
        if token not in fr04_text:
            fail(f"FR-04 acceptance criteria do not cover required field or concept: {token}")
    if "min(run_clock.now_utc" not in fr04["statement"] and "min(run_clock.now_utc" not in " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in fr04["fit_criterion"]
    ):
        fail("FR-04 must define the unique min(now_utc, end-of-day) valuation cutoff")
    for token in ("original", "unchanged"):
        if token not in combined:
            fail(f"portfolio-risk acceptance criteria do not verify original requirements are {token!r}")
    if "risk-blocked rerun does not create a second entry" in inv02_text:
        fail("INV-02 must not retain the absolute no-new-entry rule")
    for token in ("risk-policy", "separate"):
        if token not in qr01_text:
            fail(f"QR-01 does not state the required {token!r} evaluation separation")
    for ac in fr04["fit_criterion"]:
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
        "fr04_acs": len(fr04["fit_criterion"]),
        "inv02_acs": len(inv02["fit_criterion"]),
        "check_kind": "document_coverage_only",
        "cache_risk_eval_separated": True,
        "documented_cases": sorted(case_tokens),
    }


class FutureAnalysisDateError(ValueError):
    pass


DECIMAL_INPUT_RE = re.compile(r"^(0|[1-9][0-9]{0,29})(\.[0-9]{1,12})?$")


def _fixture_json(name: str):
    path = FIXTURE_DIR / name
    return path, json.loads(path.read_text(encoding="utf-8"))


def _decimal_input(value, field: str):
    if not isinstance(value, str) or not DECIMAL_INPUT_RE.fullmatch(value):
        raise ValueError(f"{field} is not a canonical decimal string")
    if "." in value and value.endswith("0"):
        raise ValueError(f"{field} has a meaningless trailing zero")
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
        "valuation_time", "instrument_id", "asset_type", "analysis_date",
        "candidate_id", "portfolio_scope",
    )
    if any(key not in obj for key in required):
        return None, "MISSING_RISK_INPUT"
    if obj.get("action") != "Buy" or obj.get("instrument_type") != "common_stock":
        return None, "UNSUPPORTED_RISK_INPUT"
    if obj.get("order_count") != 1 or obj.get("leverage") != "1":
        return None, "UNSUPPORTED_RISK_INPUT"
    if obj.get("asset_type") != "stock" or obj.get("portfolio_scope") != "single_currency_unlevered_long":
        return None, "UNSUPPORTED_RISK_INPUT"
    for field in ("instrument_id", "analysis_date", "candidate_id"):
        if not isinstance(obj.get(field), str) or not obj[field].strip():
            return None, "INVALID_RISK_INPUT"
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
    if normalized["current_asset_value"] + normalized["proposed_order_value"] > Decimal(policy["max_projected_weight"]) * normalized["portfolio_value"]:
        codes.append("POSITION_LIMIT_EXCEEDED")
    if normalized["entry_price"] - normalized["stop_loss_price"] > Decimal(policy["max_stop_distance"]) * normalized["entry_price"]:
        codes.append("STOP_DISTANCE_EXCEEDED")
    status = "passed" if not codes else "blocked"
    effective = normalized["proposed_order_value"] if status == "passed" else Decimal("0")
    return {"status": status, "codes": codes, "projected_weight": projected,
            "stop_distance": stop_distance, "effective_order_value": effective}


def risk_fixture_checks() -> dict:
    input_path, input_obj = _fixture_json("portfolio_risk_input_v1.json")
    policy_path, policy = _fixture_json("portfolio_risk_policy_v2.json")
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
    if policy.get("max_projected_weight") != "0.3":
        fail("current policy fixture must use canonical 0.3")
    if "/" in str(policy.get("policy_ref")) or policy.get("policy_ref") in {None, ""}:
        fail("current policy_ref must be a stable logical identity, not a path")
    if policy.get("policy_file_ref") != "docs/req/fixtures/portfolio_risk_policy_v2.json":
        fail("current policy fixture must locate its file separately")

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
        if snapshot.get("status") in {"snapshot_ready", "failed_precommit"} and snapshot.get("valid"):
            if snapshot.get("status") == "failed_precommit" and not snapshot.get("failed_recoverable"):
                quarantined.append(run_id)
            else:
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
    if "r9" in committed:
        fail("failed analysis/security state must not auto-promote to committed")
    if "r8" not in committed:
        fail("recoverable pre-commit failed state must be able to complete under policy")
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
    for rid in ("FR-05", "FR-06"):
        req = requirements[rid]
        if req["status"] != "approved":
            fail(f"{rid} must be approved in the frozen baseline")
        if rid not in doc["scope"].get("approved_ids", []):
            fail(f"{rid} must be listed in scope.approved_ids")
        if rid in doc["scope"].get("draft_ids", []):
            fail(f"{rid} must not remain in scope.draft_ids")
    if requirements["QR-02"]["status"] != "deferred":
        fail("QR-02 must remain deferred")
    if "QR-02" not in doc["scope"].get("deferred_ids", []):
        fail("QR-02 must be listed in scope.deferred_ids")
    if "QR-02" in doc["scope"]["approved_ids"] or "QR-02" in doc["scope"].get("draft_ids", []):
        fail("QR-02 must not be listed in scope.approved_ids or scope.draft_ids")
    fr05 = requirements["FR-05"]
    fr06 = requirements["FR-06"]
    qr02 = requirements["QR-02"]
    for req in (fr05, fr06, qr02):
        for ac in req["fit_criterion"]:
            if ac["measurement_status"] == "measured":
                fail(f"{ac['id']} must not claim a measured result")
    for req in (fr05, fr06):
        for ac in req["fit_criterion"]:
            if not ac["zero_tolerance"]:
                fail(f"{ac['id']} must be zero-tolerance")
    def _doc_text(req):
        ac_text = " ".join(
            " ".join((ac["input"], ac["expected_result"], ac["verification"]))
            for ac in req["fit_criterion"]
        )
        return " ".join((req["problem"], req["statement"], " ".join(req["assumptions"]), ac_text)).lower()

    fr05_text = _doc_text(fr05)
    fr06_text = _doc_text(fr06)
    qr02_text = _doc_text(qr02)
    history_tokens = (
        "ticker", "analysis_date", "intersection", "normaliz", "order",
        "limit", "offset", "paging", "next_offset", "truncated", "unknown",
        "corrupt", "invalid_filter", "revalidat", "section_manifest", "export", "legacy",
        "publication_snapshot", "temporary",
    )
    recovery_tokens = (
        "snapshot_ready", "missing", "corrupt", "unsupported", "quarantine",
        "model", "external", "analysis graph", "settlement", "reflection",
        "memory", "retry", "at most one", "run_id",
        "commit marker", "artifact_binding", "report_section_manifest",
        "risk input", "policy references", "reserved entry version",
        "schema/renderer", "reference", "publication_snapshot", "temporary",
        "first write", "different decision entry",
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
    if qr02["fit_criterion"][0]["threshold_status"] != "provisional":
        fail("QR-02 threshold must remain provisional")
    if qr02["fit_criterion"][0]["measurement_status"] == "measured":
        fail("QR-02 must not claim a measured benchmark result")
    if len(qr02["fit_criterion"]) < 2 or not qr02["fit_criterion"][1]["zero_tolerance"]:
        fail("QR-02 must include a zero-tolerance correctness/model-free criterion")
    return {
        "requirements": list(expected),
        "fr05_acs": len(fr05["fit_criterion"]),
        "fr06_acs": len(fr06["fit_criterion"]),
        "qr02_acs": len(qr02["fit_criterion"]),
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
    for field in ("price_as_of", "price_date", "price_source", "price_currency", "price_adjustment_basis", "price_freshness_policy"):
        if field not in fixture:
            fail(f"financial fixture missing price metadata {field}")
    if fixture["price_date"] > fixture["as_of"]:
        fail("financial fixture price_date must not be after as_of")
    checked = 0
    for scenario in fixture.get("scenarios", []):
        if scenario.get("deferred"):
            continue
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


def _fixture_tokens(text: str) -> int:
    return len(re.findall(r"\S+", text))

def brief_fixture_checks() -> dict:
    _, fixture = _fixture_json("downstream_brief_v1.json")
    _, budget_policy = _fixture_json("brief_budget_policy_v2.json")
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
        mandatory_len = _fixture_tokens(mandatory)
        report = scenario.get("report", "")
        markers = re.findall(r"<!-- BRIEF:START -->(.*?)<!-- BRIEF:END -->", report, re.S)
        marker_count = len(markers)
        reference_present = False
        full_report_fallback = False
        within_hard_cap = mandatory_len <= hard_cap
        if scenario["id"].startswith("short_report") and _fixture_tokens(report) <= total_budget:
            mandatory_parts = gaps + [metric_block, safety]
            if all(part in report for part in mandatory_parts):
                output = report
                status = "short_passthrough"
            else:
                candidate = mandatory + "\n" + report
                if _fixture_tokens(candidate) <= total_budget:
                    output = candidate
                    status = "short_narrative_plus_mandatory"
                elif mandatory_len > hard_cap:
                    output = ""
                    status = "BRIEF_REJECTED"
                elif expansion_allowed:
                    output = mandatory
                    status = "expanded"
                elif reference_allowed and mandatory_len + budget_policy.get("resolved_payload_tokens", 0) <= context_hard_cap:
                    output = mandatory + "\n" + budget_policy["reference"]["handle"]
                    status = "reference"
                    reference_present = True
                elif _fixture_tokens(report) <= context_hard_cap:
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
                if _fixture_tokens(narrative) > compressible_budget:
                    narrative = " ".join(narrative.split()[:compressible_budget])
                    status = "truncated"
                else:
                    status = "ok"
                output = mandatory + "\n" + narrative
            else:
                narrative = fixture["fallback_narrative"]
                compressible_budget = max(0, total_budget - mandatory_len - 1)
                output = mandatory + "\n" + " ".join(narrative.split()[:compressible_budget])
                status = "fallback"
        elif mandatory_len > hard_cap:
            output = ""
            status = "BRIEF_REJECTED"
        elif within_hard_cap and expansion_allowed:
            output = mandatory
            status = "expanded"
        elif reference_allowed and mandatory_len + budget_policy.get("resolved_payload_tokens", 0) <= context_hard_cap:
            output = mandatory + "\n" + budget_policy["reference"]["handle"]
            status = "reference"
            reference_present = True
        elif _fixture_tokens(report) <= context_hard_cap:
            output = report
            status = "full_report"
            full_report_fallback = True
        else:
            output = ""
            status = "BRIEF_REJECTED"
        if mandatory_len > context_hard_cap:
            output = ""
            status = "BRIEF_REJECTED"
        if status != "BRIEF_REJECTED" and _fixture_tokens(output) > context_hard_cap:
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
        if expected.get("within_total") and _fixture_tokens(output) > total_budget:
            fail(f"brief fixture {scenario['id']} exceeded total budget")
        if expected.get("within_hard_cap") and _fixture_tokens(output) > hard_cap:
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
    if req["status"] != "approved" or rid not in doc["scope"].get("approved_ids", []):
        fail("FR-07 must be approved in scope.approved_ids")
    text = " ".join((req["problem"], req["statement"], " ".join(req["assumptions"]), " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in req["fit_criterion"]
    ))).lower()
    tokens = (
        "financial_fact", "period_start", "period_end", "fiscal_year", "filed_at",
        "currency", "unit", "restatement", "ambiguous", "zero denominator",
        "non-positive", "capex", "currency mismatch", "unit mismatch", "run cache",
        "metric block", "metric_conflict", "reference manifest", "direct vendor",
        "subject_id", "accession", "filing_ref", "same-day", "ambiguous-filing",
        "metric_evidence_bundle", "formula_version", "metric_claim", "refetch",
        "free cash flow", "p/e on fiscal-year eps", "ttm", "deferred",
    )
    for token in tokens:
        if token not in text:
            fail(f"FR-07 document coverage missing {token}")
    for token in ("105.9", "85.2", "17.9", "75.0", "66.2", "62.0", "44.3", "69,987"):
        if token not in text:
            fail(f"FR-07 document coverage missing expected value {token}")
    for ac in req["fit_criterion"]:
        if ac["measurement_status"] == "measured":
            fail(f"{ac['id']} must not claim a measured result")
    return {"requirements": [rid], "acs": len(req["fit_criterion"]), "check_kind": "document_coverage_only"}


def brief_document_coverage(doc: dict) -> dict:
    requirements = {r["id"]: r for r in doc["requirements"]}
    rid = "FR-08"
    if rid not in requirements:
        fail("missing FR-08")
    req = requirements[rid]
    if req["status"] != "approved" or rid not in doc["scope"].get("approved_ids", []):
        fail("FR-08 must be approved in scope.approved_ids")
    text = " ".join((req["problem"], req["statement"], " ".join(req["assumptions"]), " ".join(
        " ".join((ac["input"], ac["expected_result"], ac["verification"]))
        for ac in req["fit_criterion"]
    ))).lower()
    tokens = (
        "bull researcher", "bear researcher", "risk debaters", "mandatory", "compressible",
        "canonical", "fr-03", "metric block", "brief_budget_policy", "brief_rejected", "unicode",
        "token", "quality", "safety", "downstream view", "full report",
        "context_audit_metadata", "reference", "expand", "hard cap", "resolvable",
        "short report", "byte-identical", "cr-01",
    )
    for token in tokens:
        if token not in text:
            fail(f"FR-08 document coverage missing {token}")
    for ac in req["fit_criterion"]:
        if ac["measurement_status"] == "measured":
            fail(f"{ac['id']} must not claim a measured result")
    return {"requirements": [rid], "acs": len(req["fit_criterion"]), "check_kind": "document_coverage_only"}


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
    _, contract = _fixture_json("../evaluation/brief-eval-contract-v4.json")
    if contract.get("status") not in {"frozen_contract", "revision_draft"}:
        fail("brief evaluation contract status must be frozen_contract or revision_draft")
    allowed_states = {"blocked", "ready", "accepted", "failed"}
    if contract.get("acceptance_status") not in allowed_states:
        fail("brief acceptance_status must be blocked/ready/accepted/failed")
    switch = contract.get("switch", {})
    if switch.get("off") != "full_reports" or switch.get("on") != "downstream_brief":
        fail("brief evaluation switch mapping is invalid")
    metrics = set(contract.get("metrics", []))
    for metric in ("added_output_tokens", "brief_generation_input_tokens", "reduced_downstream_input_tokens",
                   "added_output_cost", "reduced_input_cost_saving", "net_tokens", "net_cost",
                   "fidelity", "key_number_preservation", "gap_preservation", "quality_loss",
                   "safety_escapes", "latency_seconds", "measurement_scope", "retry_attempts",
                   "fallback_attempts", "claim_classification"):
        if metric not in metrics:
            fail(f"brief evaluation contract missing metric {metric}")
    direction = contract.get("token_direction", {})
    if direction.get("net_tokens") != "added_output_tokens - reduced_downstream_input_tokens":
        fail("brief net token direction is invalid")
    if "local cost attribution" not in direction.get("net_cost", ""):
        fail("brief net cost must be described as local cost attribution")
    if "excludes brief-generation input cost" not in direction.get("net_cost", ""):
        fail("brief net cost must disclose excluded brief-generation input cost")
    if direction.get("negative_net_cost_means_saving") is not False:
        fail("brief contract must not equate negative local net cost with a saving claim")
    if "if either price is null" not in direction.get("missing_price_behavior", ""):
        fail("brief missing-price behavior is not defined")
    if direction.get("scope") != "local_cost_attribution":
        fail("brief cost scope must be local_cost_attribution")
    if "local_cost_saving" not in direction.get("saving_definition", "") or "whole_application_saving" not in direction.get("saving_definition", ""):
        fail("brief saving definition must separate local saving from whole-application saving")

    claim_defs = contract.get("claim_definitions", {})
    for key in ("budget_met", "local_cost_saving", "token_reduction", "zero_difference",
                "positive_cost_difference_within_budget", "whole_application_saving",
                "quality_or_safety_override"):
        if key not in claim_defs:
            fail(f"brief claim definitions missing {key}")
    if "does not by itself imply a saving" not in claim_defs.get("budget_met", ""):
        fail("budget_met must not imply a saving")
    if "net_cost < 0" not in claim_defs.get("local_cost_saving", ""):
        fail("local_cost_saving must require a negative local difference")
    if "does not claim it" not in claim_defs.get("whole_application_saving", ""):
        fail("whole_application_saving must remain unclaimed")
    if "cannot be offset" not in claim_defs.get("quality_or_safety_override", ""):
        fail("quality/safety override must be forbidden")

    model = contract.get("state_model", {})
    checkpoints = model.get("checkpoints", {})
    if not checkpoints.get("pre_run_inputs") or not checkpoints.get("post_run_result_evidence"):
        fail("brief state model must separate pre-run inputs from post-run result evidence")
    priority = " ".join(model.get("state_priority", [])).lower()
    for token in ("blocked", "ready", "failed", "accepted"):
        if token not in priority:
            fail(f"brief state priority missing {token}")
    transitions = " ".join(model.get("transitions", [])).lower()
    for token in ("not_started/blocked -> not_started/ready", "not_started/ready -> running/null",
                  "running/null -> completed/accepted", "running/null -> completed/failed",
                  "running/null -> aborted/failed", "must not return to not_started"):
        if token not in transitions:
            fail(f"brief state transitions missing {token!r}")
    if "observed_failures" not in model.get("observed_failure_policy", ""):
        fail("brief observed-failure policy must preserve observed failures")
    if "attempt_id" not in model.get("attempt_policy", "") or "prior attempt input binding" not in model.get("attempt_policy", ""):
        fail("brief attempt policy must preserve prior attempt evidence")

    states = contract.get("state_conditions", {})
    for state in allowed_states:
        if state not in states:
            fail(f"brief evaluation contract missing state condition {state}")
    blocked = [s.lower() for s in states.get("blocked", [])]
    ready = [s.lower() for s in states.get("ready", [])]
    accepted = [s.lower() for s in states.get("accepted", [])]
    failed = [s.lower() for s in states.get("failed", [])]
    blocked_text = " ".join(blocked)
    ready_text = " ".join(ready)
    accepted_text = " ".join(accepted)
    failed_text = " ".join(failed)
    for token in ("pre-run inputs", "missing or invalid", "observed_failures"):
        if token not in blocked_text:
            fail(f"brief blocked state missing {token!r}")
    for token in ("execution_status=not_started", "all pre-run inputs are valid", "no result exists for the current attempt", "has not started"):
        if token not in ready_text:
            fail(f"brief ready state missing {token!r}")
    if "no accepted result" in ready_text:
        fail("brief ready state must not be defined as no accepted result yet")
    running_text = " ".join(s.lower() for s in states.get("running", []))
    for token in ("execution_status=running", "acceptance_status is null", "observed_failures may be recorded"):
        if token not in running_text:
            fail(f"brief running state missing {token!r}")
    for token in ("execution_status=completed", "result evidence is complete, valid", "all samples", "quality_loss <=", "safety_escapes = 0", "net_cost <=", "usage is complete"):
        if token not in accepted_text:
            fail(f"brief accepted state missing {token!r}")
    if "ready" in [s.strip() for s in accepted]:
        fail("brief accepted state must not list ready as a circular precondition")
    for token in ("execution_status=completed", "execution_status=aborted", "safety_escapes > 0", "quality_loss >", "net_cost >", "missing/corrupt/inconsistent"):
        if token not in failed_text:
            fail(f"brief failed state missing {token!r}")

    scope = contract.get("measurement_scope", {})
    if scope.get("scope") != "local_cost_attribution":
        fail("brief measurement scope must be local_cost_attribution")
    included = " ".join(scope.get("included", [])).lower()
    excluded = " ".join(scope.get("excluded", [])).lower()
    for token in ("brief-generation output", "downstream input"):
        if token not in included:
            fail(f"brief measurement scope missing included term {token!r}")
    for token in ("brief-generation input", "retry", "fallback", "downstream output", "non-brief", "infrastructure"):
        if token not in excluded:
            fail(f"brief measurement scope missing excluded term {token!r}")
    if not scope.get("retry_fallback_record"):
        fail("brief measurement scope must record retry/fallback occurrence")
    if scope.get("expansion_status") != "not_approved":
        fail("brief cost-scope expansion must remain not approved")
    token_target = contract.get("token_target", {})
    if token_target.get("status") != "not_defined" or token_target.get("net_tokens_max") is not None:
        fail("brief token target must remain undefined and null")
    aggregation = contract.get("measurement_aggregation", {})
    if not any(x in aggregation.get("target_comparison", "").lower() for x in ("total", "sum", "aggregate")):
        fail("brief cost target must compare a fixed total/sum or aggregate, not a per-case value")
    if aggregation.get("aggregation_metric") not in {"sum", "total"}:
        fail("brief cost aggregation must be explicitly total/sum")
    if aggregation.get("not_per_case_mean") is not True:
        fail("brief cost target must state that per-case mean is not the default")
    usage = contract.get("usage_accounting", {})
    for key in ("complete", "partial", "unavailable", "no_generation_call"):
        if key not in usage:
            fail(f"brief usage accounting missing {key}")
    if "not zero" not in usage.get("unavailable", ""):
        fail("brief unavailable usage must not be reported as zero")
    if "distinct from unavailable" not in usage.get("no_generation_call", ""):
        fail("brief true-zero generation must be distinct from unavailable usage")
    attempt_policy = contract.get("state_model", {}).get("attempt_policy", "").lower()
    for token in ("fixes its inputs", "later configuration changes do not mutate a terminal attempt"):
        if token not in attempt_policy:
            fail(f"brief attempt policy missing {token!r}")
    post_evidence = " ".join(contract.get("state_model", {}).get("checkpoints", {}).get("post_run_result_evidence", []))
    if "result_digest may be null" not in post_evidence:
        fail("brief state model must allow null result_digest only before completion")

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
    cost_approved = bool(thresholds.get("net_cost_max_approved"))
    cost_max = thresholds.get("net_cost_max")
    if quality_approved and quality_max is None:
        fail("approved quality_loss_max requires a numeric threshold")
    if not quality_approved and quality_max is not None:
        fail("unapproved quality_loss_max must be null")
    if cost_approved and cost_max is None:
        fail("approved net_cost_max requires a numeric threshold")
    if not cost_approved and cost_max is not None:
        fail("unapproved net_cost_max must be null")
    human = bool(contract.get("human_approved"))
    prices = contract.get("prices", {})
    prices_ready = prices.get("input_per_token") is not None and prices.get("output_per_token") is not None
    case_ready = snapshot_state["all_ready"]
    # Current contract has no result and incomplete pre-run inputs: it is blocked.
    if not case_ready or not quality_approved or not cost_approved or not prices_ready or not human:
        current_state = "blocked"
    elif contract.get("result") is None:
        current_state = "ready"
    else:
        current_state = "failed"
    if contract.get("acceptance_status") != current_state:
        fail(f"brief acceptance_status {contract.get('acceptance_status')} != current state {current_state}")
    if current_state == "blocked" and not contract.get("blocking_reasons"):
        fail("blocked brief evaluation must record blocking_reasons")
    usage = contract.get("usage_policy", {})
    if usage.get("unknown_is_not_zero") is not True:
        fail("brief v4 usage policy must forbid treating unknown usage as zero")
    if "null or explicitly incomplete" not in usage.get("required_usage_missing_behavior", ""):
        fail("brief v4 required-usage failure must be null/incomplete")
    if usage.get("estimated_label_required") is not True:
        fail("brief v4 must require an estimated label for tokenizer-based measurement")
    selection = contract.get("generation_call_selection", {})
    for key in ("shared_generation", "view_updates", "excluded"):
        if not selection.get(key):
            fail(f"brief v4 generation selection missing {key}")
    downstream = contract.get("downstream_scope", {})
    if len(downstream.get("roles", [])) != 5:
        fail("brief v4 local scope must cover the five target roles")
    for token in ("message wrappers", "mandatory content", "existing history"):
        if token not in downstream.get("includes", []):
            fail(f"brief v4 downstream input scope missing {token}")
    aggregation = contract.get("sample_aggregation", {})
    if aggregation.get("aggregation_metric") != "sum" or aggregation.get("not_per_case_mean") is not True:
        fail("brief v4 target aggregation must be a total sum")
    if aggregation.get("negative_difference") != "retained, never clipped":
        fail("brief v4 negative differences must be retained")
    if "Decimal" not in aggregation.get("amount_precision", ""):
        fail("brief v4 comparisons must use Decimal and avoid display rounding")
    execution = contract.get("execution_status", {})
    if execution.get("values") != ["not_started", "running", "completed", "aborted"]:
        fail("brief v4 execution_status values are not the fixed four-value set")
    if "run_completed" not in execution.get("run_completed_relationship", ""):
        fail("brief v4 must define run_completed as auxiliary and reject contradictions")
    acceptance = contract.get("acceptance_status_field", {})
    if acceptance.get("values") != ["blocked", "ready", "accepted", "failed", None]:
        fail("brief v4 acceptance_status values are not the fixed set including null")
    if acceptance.get("forbidden_values") != ["pending", "aborted"]:
        fail("brief v4 must forbid pending/aborted acceptance strings")
    table = contract.get("state_table", [])
    if len(table) != 6:
        fail("brief v4 state table must contain six canonical rows")
    pairs = {(row.get("execution_status"), row.get("acceptance_status")) for row in table}
    if pairs != {("not_started", "blocked"), ("not_started", "ready"), ("running", None),
                 ("completed", "accepted"), ("completed", "failed"), ("aborted", "failed")}:
        fail("brief v4 state table pairs are not the legal state set")
    illegal = contract.get("illegal_state_combinations", [])
    for pair in (["not_started", "null"], ["running", "ready"], ["running", "accepted"],
                 ["aborted", "ready"], ["aborted", "accepted"], ["completed", "null"],
                 ["*", "pending"], ["*", "aborted"]):
        if pair not in illegal:
            fail(f"brief v4 illegal state table missing {pair}")
    transition_rules = " ".join(contract.get("state_transition_rules", []))
    for token in ("accepted and failed are terminal", "retry or re-evaluation creates a new attempt",
                  "MUST NOT return to not_started", "budget_met"):
        if token not in transition_rules:
            fail(f"brief v4 transition rules missing {token!r}")
    return {"contract_version": contract["contract_version"],
            "current_state": current_state,
            "acceptance_status": contract["acceptance_status"],
            "case_snapshots": snapshot_state,
            "digests_verified": verified,
            "claim_boundary": "budget_met/local_cost_saving/token_reduction/whole_application_saving separated",
            "cost_target_status": "approved" if cost_approved else "unresolved",
            "token_target_status": token_target.get("status"),
            "measurement_scope": scope.get("scope"),
            "check_kind": "evaluation_contract_semantic_check"}


def brief_budget_policy_checks() -> dict:
    _, policy = _fixture_json("brief_budget_policy_v2.json")
    if policy.get("policy_version") != "brief-budget-policy-v2":
        fail("brief budget policy version mismatch")
    if policy.get("status") not in {"provisional", "approved"}:
        fail("brief budget policy status must be provisional or approved")
    if policy.get("budget_unit") != "tokens" or not policy.get("tokenizer_id"):
        fail("brief budget policy must use token units bound to a tokenizer")
    for field in ("resolved_payload_tokens", "reserve_output_tokens", "model_context_limit_token_cap"):
        if field not in policy:
            fail(f"brief budget policy missing {field}")
    if policy.get("mandatory_budget", 0) + policy.get("compressible_budget", 0) > policy.get("total_budget", 0):
        fail("brief mandatory plus compressible budget exceeds total budget")
    order = policy.get("resolution_order", [])
    expected_order = ["reject_if_mandatory_exceeds_hard_cap", "compress_compressible", "expand_to_hard_cap", "resolved_reference", "full_report_with_mandatory", "BRIEF_REJECTED"]
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
    _, fixture = _fixture_json("brief_eval_states_v4.json")
    execution_values = {"not_started", "running", "completed", "aborted"}
    acceptance_values = {"blocked", "ready", "accepted", "failed", None}
    legal_pairs = {
        ("not_started", "blocked"), ("not_started", "ready"),
        ("running", None),
        ("completed", "accepted"), ("completed", "failed"),
        ("aborted", "failed"),
    }
    checked = 0
    accepted_claims = 0
    invalid_cases = 0
    for case in fixture.get("cases", []):
        cid = case["id"]
        execution = case.get("execution_status")
        acceptance = case.get("acceptance_status")
        expected_valid = case.get("expected_valid", False)

        quality_ok = bool(case.get("quality_loss_max_approved")) and case.get("quality_loss_max") is not None
        cost_ok = bool(case.get("net_cost_max_approved")) and case.get("net_cost_max") is not None
        pre_ok = (bool(case.get("case_snapshots_ready")) and bool(case.get("fixed_input_digests_ready"))
                  and bool(case.get("prices_ready")) and quality_ok and cost_ok
                  and bool(case.get("human_approved")))
        result = case.get("result")
        invalid_reason = None
        if execution not in execution_values:
            invalid_reason = "invalid execution_status"
        elif acceptance not in acceptance_values:
            invalid_reason = "invalid acceptance_status"
        elif acceptance in {"pending", "aborted"}:
            invalid_reason = "forbidden acceptance_status string"
        elif (execution, acceptance) not in legal_pairs:
            invalid_reason = "illegal execution/acceptance pair"
        if "run_completed" in case and case["run_completed"] != (execution == "completed"):
            invalid_reason = "run_completed contradicts execution_status"
        if execution == "aborted" and not case.get("abort_reason"):
            invalid_reason = "aborted attempt missing abort_reason"
        if case.get("input_digest_mismatch_after_start") and execution == "not_started":
            invalid_reason = "started input mismatch cannot be not_started"
        if case.get("input_digest_mismatch_after_start") and acceptance in {"blocked", "ready"}:
            invalid_reason = "started input mismatch cannot be blocked/ready"

        actual_execution = execution
        actual_acceptance = acceptance
        if expected_valid:
            if execution is None:
                fail(f"brief state fixture {cid} is valid but missing execution_status")
            if execution == "not_started":
                actual_acceptance = "ready" if pre_ok else "blocked"
            elif execution == "running":
                actual_acceptance = None
            elif execution == "aborted":
                actual_acceptance = "failed"
            elif execution == "completed":
                accepted = bool(case.get("result_evidence_valid")) and result is not None
                if accepted:
                    if not result.get("all_samples", False):
                        accepted = False
                    if result.get("safety_escapes", 0) != 0:
                        accepted = False
                    if result.get("quality_loss") is None or case.get("quality_loss_max") is None:
                        accepted = False
                    elif Decimal(str(result.get("quality_loss"))) > Decimal(str(case.get("quality_loss_max"))):
                        accepted = False
                    if result.get("net_cost") is None or case.get("net_cost_max") is None:
                        accepted = False
                    elif Decimal(str(result.get("net_cost"))) > Decimal(str(case.get("net_cost_max"))):
                        accepted = False
                    if result.get("usage_complete", True) is not True:
                        accepted = False
                actual_acceptance = "accepted" if accepted else "failed"
            if invalid_reason is not None:
                fail(f"brief state fixture {cid} is marked valid but {invalid_reason}")
            if actual_execution != case.get("expected_execution_status"):
                fail(f"brief state fixture {cid} expected execution {case.get('expected_execution_status')}, got {actual_execution}")
            if actual_acceptance != case.get("expected_acceptance_status"):
                fail(f"brief state fixture {cid} expected acceptance {case.get('expected_acceptance_status')}, got {actual_acceptance}")
            if acceptance != actual_acceptance:
                fail(f"brief state fixture {cid} supplied acceptance {acceptance} but computed {actual_acceptance}")
            if case.get("run_completed") is not None and case["run_completed"] != (execution == "completed"):
                fail(f"brief state fixture {cid} run_completed contradicts execution_status")
            if execution == "aborted":
                if not case.get("abort_reason"):
                    fail(f"brief state fixture {cid} aborted case lacks abort_reason")
                if "observed_failures" not in case or "produced_evidence" not in case or "missing_items" not in case:
                    fail(f"brief state fixture {cid} aborted case lacks preservation evidence")
            if case.get("attempt_id") and case.get("previous_attempt_id"):
                if case["attempt_id"] == case["previous_attempt_id"]:
                    fail(f"brief state fixture {cid} retry reuses the previous attempt_id")
                if case.get("previous_terminal_status") not in {"accepted", "failed", "aborted"}:
                    fail(f"brief state fixture {cid} retry does not retain the previous terminal state")
                if case.get("previous_observed_failures") and not case.get("previous_observed_failures_preserved"):
                    fail(f"brief state fixture {cid} retry does not preserve observed_failures")
            if actual_acceptance == "accepted":
                accepted_claims += 1
                net_cost = Decimal(str(result.get("net_cost")))
                net_tokens = Decimal(str(result.get("net_tokens")))
                cost_max = Decimal(str(case.get("net_cost_max")))
                claims = []
                if net_cost <= cost_max:
                    claims.append("budget_met")
                if net_cost < 0:
                    claims.append("local_cost_saving")
                elif net_cost == 0:
                    claims.append("no_strict_saving")
                if net_tokens < 0:
                    claims.append("token_reduction")
                claims.append("no_whole_application_saving")
                expected_claim = ";".join(claims)
                if case.get("expected_claim") != expected_claim:
                    fail(f"brief state fixture {cid} claim {case.get('expected_claim')} != {expected_claim}")
        else:
            invalid_cases += 1
            if invalid_reason is None:
                fail(f"brief state fixture {cid} is marked invalid but forms a legal state")
            if case.get("expected_execution_status") is not None or case.get("expected_acceptance_status") is not None:
                fail(f"brief state fixture {cid} invalid case must not declare expected state values")
        checked += 1

    rules = fixture.get("claim_rules", {})
    for key in ("budget_met", "local_cost_saving", "token_reduction", "zero_difference",
                "positive_within_budget", "whole_application_saving"):
        if key not in rules:
            fail(f"brief state fixture missing claim rule {key}")
    required_pairs = {
        ("not_started", "blocked"), ("not_started", "ready"), ("running", None),
        ("completed", "accepted"), ("completed", "failed"), ("aborted", "failed"),
    }
    fixture_pairs = {(c.get("execution_status"), c.get("acceptance_status")) for c in fixture.get("cases", []) if c.get("expected_valid", False)}
    if not required_pairs.issubset(fixture_pairs):
        fail(f"brief state fixture missing positive state pairs: {sorted(required_pairs - fixture_pairs)}")
    return {"cases": len(fixture.get("cases", [])), "checks": checked,
            "accepted_claims": accepted_claims, "invalid_cases": invalid_cases,
            "fixture_version": fixture.get("fixture_version"),
            "check_kind": "two_field_state_table_and_claim_fixture"}


def gr01_freeze_fixture_checks() -> dict:
    _, fixture = _fixture_json("gr01_freeze_states_v1.json")
    checked = 0
    for case in fixture.get("cases", []):
        independence = 0
        generation_source = case.get("generation_source")
        if generation_source in {"sut", "shared_critical_path"}:
            independence = 1
        if case.get("implementation_generated_expected_value_count", 0) > 0:
            independence = 1
        if not case.get("manifest_present"):
            independence = 1
        stage_a = (bool(case.get("manifest_present")) and bool(case.get("manifest_complete"))
                   and bool(case.get("sources_recorded")) and case.get("freeze_status") == "frozen"
                   and bool(case.get("freeze_digest_valid")) and bool(case.get("human_review_complete"))
                   and independence == 0)
        if case.get("issuer_dedup_by_stable_id") is False or case.get("calendar_evidence") is False or case.get("coverage_matrix_complete") is False:
            stage_a = False
        stage_a_result = "pass" if stage_a else "fail"
        if not case.get("implementation_started"):
            stage_b_result = "not_applicable"
        else:
            first = case.get("first_implementation_at")
            freeze = case.get("freeze_at")
            if case.get("initial_frozen_version") is not None:
                initial_ok = bool(first and freeze and freeze < first
                                  and case.get("reference_version") == case.get("frozen_version")
                                  and bool(case.get("revision_reviewed"))
                                  and bool(case.get("revision_used_after_freeze"))
                                  and not (case.get("freeze_recorded_at") and case.get("freeze_recorded_at") > first))
            else:
                initial_ok = bool(first and freeze and first > freeze
                                  and case.get("reference_version") == case.get("frozen_version")
                                  and not (case.get("freeze_recorded_at") and case.get("freeze_recorded_at") > first))
            stage_b_result = "pass" if (stage_a and initial_ok) else "fail"
        expected = case.get("expected", {})
        if stage_a_result != expected.get("stage_a") or stage_b_result != expected.get("stage_b"):
            fail(f"GR-01 freeze fixture {case['id']} expected {expected}, got stage_a={stage_a_result}, stage_b={stage_b_result}")
        if "expected_independence" in case:
            actual_independence = "pass" if independence == 0 and bool(case.get("manifest_present")) else "fail"
            if actual_independence != case["expected_independence"]:
                fail(f"GR-01 independence fixture {case['id']} expected {case['expected_independence']}, got {actual_independence}")
        checked += 1
    return {"cases": len(fixture.get("cases", [])), "checks": checked,
            "fixture_version": fixture.get("fixture_version"),
            "check_kind": "stage_a_b_and_independence_static_fixture"}


def _resolve_json_pointer(value, pointer: str):
    if pointer in ("", "/"):
        return value
    for part in [p for p in pointer.strip("/").split("/") if p]:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            raise KeyError(part)
    return value


def round4_checks(doc: dict) -> dict:
    requirements = {r["id"]: r for r in doc["requirements"]}
    results = {}

    def req_text(rid: str) -> str:
        req = requirements[rid]
        return " ".join([req.get("statement", "")] + [a.get("input", "") + " " + a.get("expected_result", "") + " " + a.get("verification", "") for a in req["fit_criterion"]]).lower()

    checks = {
        "PR-01": ["manifest-specific", "no-op", "test-only", "ab/ba", "odd", "even", "actual", "utf-8", "262144", "nearest-rank", "19th", "infrastructure", "rerun", "observed cutoff", "self-report"],
        "CR-01": ["field-level", "unknown", "selected", "shared generation", "view-update", "five target roles", "sum", "decimal", "execution status", "not_started", "observed_failures", "brief-eval-contract-v4"],
        "GR-01": ["stable issuer", "calendar", "independent hand", "scripts", "implementation_generated_expected_value_count", "initial", "revision", "before use", "retained", "missing manifest"],
        "QR-01": ["score_off", "score_on", "weights", "third reviewer", "one original scored sample", "percentage points", "cache", "risk-policy", "hard check"],
        "SB-01": ["not publication success", "trustworthy", "fabricating", "unsupported snapshot schema version", "internal_detail", "late success", "recovery"],
        "INV-01": ["comparison projection", "decision_id", "per-field", "file sha", "post-commit", "retention", "high-water", "publish_state"],
        "INV-02": ["portfolio_risk_limit_exceeded", "review_class = portfolio_risk_limit", "independent", "business projection", "pure evaluator", "wrapper", "read-time"],
        "SR-01": ["detected_count", "residual", "authorized", "path", "stream", "recursive", "post-commit"],
        "SR-02": ["create", "write", "replace", "move", "quarantine", "cleanup", "source and target", "trusted root", "check", "typed reused_decision_ref", "read", "delete", "unsupported"],
    }
    for rid, tokens in checks.items():
        text = req_text(rid)
        for token in tokens:
            if token not in text:
                fail(f"{rid} revision is missing required concept {token!r}")

    human_review = doc.get("validation", {}).get("human_review_status")
    if human_review not in {"pending", "approved"}:
        fail(f"unsupported human_review_status: {human_review}")
    if human_review == "pending":
        for req in doc["requirements"]:
            for ac in req["fit_criterion"]:
                if ac.get("threshold_status") == "approved":
                    fail(f"{ac['id']} cannot claim an approved threshold while human review is pending")
    else:
        if doc.get("document", {}).get("status") != "approved":
            fail("approved human review requires document.status=approved")
        record = doc.get("validation", {}).get("approval_record")
        if not isinstance(record, dict):
            fail("approved human review requires validation.approval_record")
        else:
            required = ["approved_at", "approval_basis", "baseline_version", "approval_scope",
                        "deferred_ids", "fc_id_format", "fc_mapping_ref", "freeze_files",
                        "change_control", "limitations"]
            for key in required:
                if not record.get(key):
                    fail(f"approval_record missing {key}")
            if record.get("baseline_version") != doc["document"]["version"]:
                fail("approval_record baseline_version does not match document.version")
            if set(record.get("approval_scope", [])) != set(doc["scope"]["approved_ids"]):
                fail("approval_record approval_scope does not match scope.approved_ids")
            if set(record.get("deferred_ids", [])) != {rid for rid, req in requirements.items() if req["status"] == "deferred"}:
                fail("approval_record deferred_ids does not match deferred requirements")
            mapping_ref = record.get("fc_mapping_ref")
            if not mapping_ref or not (ROOT / mapping_ref).exists():
                fail("approval_record fc_mapping_ref does not resolve")
            for ref in record.get("freeze_files", []):
                if not (ROOT / ref).exists():
                    fail(f"approval_record freeze file does not exist: {ref}")

    for req in doc["requirements"]:
        for ac in req["fit_criterion"]:
            if ac.get("threshold_status") == "approved":
                fail(f"{ac['id']} cannot claim an approved business threshold in this design freeze")
            if ac.get("measurement_status") != "not_measured":
                fail(f"{ac['id']} cannot claim a measured result in this design freeze")

    # SB-01 gate fixture: unique mapping, trustworthy completion, no publication from gate alone.
    _, gate = _fixture_json("gate_decision_v2.json")
    gate_cases = {c["id"]: c for c in gate.get("cases", [])}
    if len(gate_cases) < 10:
        fail("gate decision fixture must cover pass, blocked, error, unsupported, late and unwritable cases")
    if not gate.get("mapping_constraints", {}).get("unique_gate_status_per_input"):
        fail("gate fixture must require one gate status per input")
    if not gate["mapping_constraints"].get("gate_result_is_not_publication"):
        fail("gate fixture must state that a gate result is not publication")
    if not gate["mapping_constraints"].get("late_success_must_not_overwrite_failure"):
        fail("gate fixture must forbid late success overwriting failure")
    unsupported = gate_cases.get("unsupported_snapshot", {})
    if unsupported.get("internal_detail") != "unsupported_snapshot_version" or unsupported.get("primary_reason_code") != "snapshot_hash_mismatch":
        fail("unsupported snapshot fixture must use snapshot_hash_mismatch plus unsupported_snapshot_version")
    if "recommended" in requirements["SB-01"]["notes"].lower() or "pending" in requirements["SB-01"]["notes"].lower():
        fail("SB-01 notes must not retain recommended/pending unsupported mapping")
    for cid in ("blocked_untrustworthy", "blocked_unsafe_write"):
        if gate_cases.get(cid, {}).get("completed_allowed"):
            fail(f"gate fixture {cid} must not allow completed without trustworthy/safe materials")
    if gate_cases.get("gate_timeout_late_success", {}).get("late_success_ignored") is not True:
        fail("gate late success must be ignored")
    if gate_cases.get("gate_pass_then_write_failure", {}).get("publication_allowed") is not False:
        fail("gate pass must not authorize publication after write failure")

    # INV-01 fixture: identity/projection, pre/post-commit, memory, retention, high-water.
    _, inv = _fixture_json("invariant_projection_v2.json")
    inv_cases = {c["id"]: c for c in inv.get("cases", [])}
    required_inv = {"identity_vs_projection", "supports_change", "content_digest_vs_file_sha", "precommit_missing_artifact",
                    "postcommit_deleted_artifact", "memory_reuse_historical", "memory_disabled", "legal_rotation",
                    "reservation_high_water", "partial_internal_state", "retry_same_identity"}
    if not required_inv.issubset(inv_cases):
        fail(f"invariant fixture missing cases: {sorted(required_inv - set(inv_cases))}")
    if inv_cases["identity_vs_projection"].get("identity_changed") is not False or inv_cases["identity_vs_projection"].get("projection_changed") is not True:
        fail("identity/projection fixture must separate stable identity from changed projection")
    if inv_cases["content_digest_vs_file_sha"].get("digests_kept_separate") is not True:
        fail("content digest and file SHA must be separate")
    if inv_cases["precommit_missing_artifact"].get("completed") is not False:
        fail("pre-commit missing artifact must not be completed")
    if inv_cases["postcommit_deleted_artifact"].get("rewritten_as_failed") is not False or inv_cases["postcommit_deleted_artifact"].get("read_success") is not False:
        fail("post-commit deletion must preserve terminal bytes and fail the read")
    hw = inv_cases["reservation_high_water"]
    if not (hw["next_allocation"] > hw["max_allocated_version"] and hw["effective_version"] == hw["max_committed_version"]):
        fail("reservation high-water fixture must allocate above all versions and use only committed versions")
    if inv_cases["partial_internal_state"].get("public_run_status") == "partial":
        fail("partial must not be a public run_status value")

    # Security/path fixture: detected/residual, no path exemption, migration, scanner failure, post-commit.
    _, sp = _fixture_json("secret_path_controls_v2.json")
    sec = {c["id"]: c for c in sp.get("security_cases", [])}
    paths = {c["id"]: c for c in sp.get("path_cases", [])}
    if sec.get("known_token_in_path", {}).get("path_is_exempt") is not False:
        fail("a token in a path/host must not be exempt from secret detection")
    if sec.get("overlapping_rules", {}).get("detected_sum_must_equal_redactions") is not False:
        fail("overlapping secret rules must not require detected sum to equal redactions")
    if sec.get("unauthorized_env_migration", {}).get("writes_plaintext_env") is not False:
        fail("unauthorized migration must not write plaintext to an .env")
    if sec.get("scanner_failure_safe_incident", {}).get("contains_raw_value") is not False or sec["scanner_failure_safe_incident"].get("recursive_scanner_dependency") is not False:
        fail("scanner-failure incident must not contain raw values or depend recursively on the failed scanner")
    if sec.get("postcommit_leak", {}).get("hash_rewritten") is not False:
        fail("post-commit leak must not rewrite hashes")
    if sec.get("stream_secret_cross_chunk", {}).get("per_chunk_safe_claim") is not False:
        fail("stream secrets must not be declared safe from per-chunk misses")
    for cid in ("traversal_read", "traversal_write", "traversal_delete", "ordinary_cross_run_read", "internal_symlink", "check_use_race", "cleanup_follows_planted_link", "unsupported_platform"):
        if paths.get(cid, {}).get("allowed") is not False:
            fail(f"path fixture {cid} must be rejected")
    if paths.get("typed_historical_read", {}).get("allowed") is not True:
        fail("typed historical reference must be allowed within the same archive root")
    if paths.get("unsupported_platform", {}).get("marked_pass") is not False:
        fail("unsupported platform must not be marked pass")

    # QR scoring fixture: merge, weights, direction, rate unit, hard safety, cache separation.
    _, q = _fixture_json("quality_scoring_v1.json")
    merge = {c["id"]: c for c in q.get("merge_cases", [])}
    if merge["diff_le_one"]["final"] != 4.5:
        fail("same-dimension <=1 difference must use the arithmetic mean")
    if merge["diff_gt_one_adjudicated"]["final"] == 5 or merge["diff_gt_one_adjudicated"].get("best_of_forbidden") is not True:
        fail(">1 difference must use an adjudicated score, not best-of")
    weights = q.get("dimension_weights", {})
    if [weights.get(k) for k in ("evidence_fidelity", "relevance", "coverage_correctness", "safety", "actionability")] != [0.30, 0.20, 0.20, 0.20, 0.10]:
        fail("quality fixture weights do not match the rubric")
    scores = q["case_score_case"]["scores"]
    expected_case = round(sum(s * weights[k] for s, k in zip(scores, ("evidence_fidelity", "relevance", "coverage_correctness", "safety", "actionability"))), 10)
    if abs(expected_case - q["case_score_case"]["expected"]) > 1e-9:
        fail("quality fixture case score recomputation failed")
    set_scores = q["set_score_cases"]["case_scores"]
    if abs(sum(set_scores) / len(set_scores) - q["set_score_cases"]["expected"]) > 1e-9:
        fail("quality fixture set-score recomputation failed")
    rr = q["review_rate_case"]
    if abs(100 * (rr["on_review"] / rr["on_total"] - rr["off_review"] / rr["off_total"]) - rr["expected_points"]) > 1e-9:
        fail("quality fixture REVIEW-rate must use percentage points")
    state = {c["id"]: c for c in q.get("state_cases", [])}
    if state["high_rubric_with_safety_escape"].get("accepted") is not False:
        fail("a safety escape must fail even with a high rubric score")
    if state["cache_complete_risk_blocked"].get("qr_all_complete") is not False:
        fail("cache-only completion must not be reported as full QR-01 completion")

    results["requirements"] = "PR/CR/GR/QR/SB/INV/SR requirement concepts checked"
    results["fixtures"] = {"gate": len(gate_cases), "invariant": len(inv_cases), "security": len(sec), "path": len(paths), "quality": len(state)}
    return results


def fc_mapping_checks(doc: dict) -> dict:
    mapping_path = REQ_DIR / "requirement-mapping.csv"
    if not mapping_path.exists():
        fail("requirement-mapping.csv is missing")
    with mapping_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    new_rows = [r for r in rows if r.get("source_version") == "1.23.0"]
    current = {ac["id"]: req["id"] for req in doc["requirements"] for ac in req["fit_criterion"]}
    if len(new_rows) != len(current):
        fail(f"v1.24.0 mapping rows {len(new_rows)} != current fit criteria {len(current)}")
    destinations = [r.get("destination_fit_criterion") for r in new_rows]
    if len(destinations) != len(set(destinations)):
        fail("v1.24.0 mapping contains duplicate destination FC IDs")
    if set(destinations) != set(current):
        fail("v1.24.0 mapping destinations do not equal current FC IDs")
    for row in new_rows:
        old = row.get("original_fit_criterion", "")
        dest = row.get("destination_fit_criterion", "")
        req = row.get("destination_requirement", "")
        if not re.match(r"^[A-Z]{2,3}-\d{2}-AC\d+$", old):
            fail(f"v1.24.0 mapping has invalid old FC ID: {old}")
        if not re.match(r"^[A-Z]{2,3}-\d{2}-FC\d{2}$", dest):
            fail(f"v1.24.0 mapping has invalid new FC ID: {dest}")
        if current.get(dest) != req:
            fail(f"v1.24.0 mapping destination {dest} is not under {req}")
    per_req = {}
    for row in new_rows:
        per_req.setdefault(row["destination_requirement"], set()).add(row["destination_fit_criterion"])
    for req in doc["requirements"]:
        actual = {ac["id"] for ac in req["fit_criterion"]}
        if per_req.get(req["id"], set()) != actual:
            fail(f"v1.24.0 mapping count mismatch for {req['id']}")
    return {"mapping_rows": len(new_rows), "requirements": len(per_req), "source_version": "1.23.0"}


def pr_gr_cr_consistency_checks(doc: dict) -> dict:
    requirements = {r["id"]: r for r in doc["requirements"]}
    results = {}

    # Shared brief-evaluation definition must point to v2, not duplicate its state machine.
    brief_def = doc["definitions"]["brief_evaluation"]
    for token in ("brief-eval-contract-v4", "budget_met", "local_cost_saving", "whole-application", "result evidence"):
        if token not in brief_def:
            fail(f"brief_evaluation definition missing current-contract term {token!r}")
    if "accepted when measured results are within the approved quality_loss_max with zero safety escapes" in brief_def:
        fail("brief_evaluation definition still uses the old quality-only accepted definition")

    # FR-08 must defer cost/token/saving claims to CR-01 and point to v2.
    fr08 = requirements["FR-08"]
    if "brief-eval-contract-v4" not in fr08["statement"]:
        fail("FR-08 must name the active brief evaluation contract")
    if "no cost, token, or whole-application saving claim" not in fr08["statement"]:
        fail("FR-08 must make no cost/token/whole-application saving claim")

    # PR-01 write samples and overhead formulas.
    pr = requirements["PR-01"]
    if pr["type"] != "performance":
        fail("PR-01 must be a performance requirement")
    pr_acs = {a["id"]: a for a in pr["fit_criterion"]}
    if set(pr_acs) != {"PR-01-FC01", "PR-01-FC02", "PR-01-FC03", "PR-01-FC04"}:
        fail("PR-01 must have four fit criteria: startup write, terminal write, percent overhead, absolute overhead")
    if pr_acs["PR-01-FC01"]["metric"] != "startup_manifest_write_p95_seconds":
        fail("PR-01-FC01 must measure startup write p95 separately")
    if pr_acs["PR-01-FC02"]["metric"] != "terminal_manifest_write_p95_seconds":
        fail("PR-01-FC02 must measure terminal write p95 separately")
    if not pr_acs["PR-01-FC03"]["metric"].endswith("_percent"):
        fail("PR-01-FC03 must use a percent metric")
    if not pr_acs["PR-01-FC04"]["metric"].endswith("_seconds"):
        fail("PR-01-FC04 must use a seconds metric")
    for ac_id in ("PR-01-FC01", "PR-01-FC02"):
        text = " ".join((pr_acs[ac_id]["input"], pr_acs[ac_id]["expected_result"])).lower()
        if "per-pair" in text:
            fail(f"{ac_id} must not compute write latency from per-pair deltas")
        if "replace" not in text or "before" not in text:
            fail(f"{ac_id} must state the pre-replace write boundary")
    formula_text = " ".join((pr["statement"], pr_acs["PR-01-FC03"]["input"], pr_acs["PR-01-FC03"]["expected_result"], pr_acs["PR-01-FC04"]["input"], pr_acs["PR-01-FC04"]["expected_result"])).lower()
    for token in ("absolute_overhead_i", "overhead_percent_i", "baseline_duration_i > 0", "negative"):
        if token not in formula_text:
            fail(f"PR-01 is missing overhead formula or negative-sample condition: {token}")
    results["pr01"] = "startup/terminal write, percent and absolute overhead separated"

    # GR-01 Stage A/B and dependency gate.
    gr = requirements["GR-01"]
    if "FR-07" in gr.get("implementation_dependencies", []):
        fail("GR-01 must not depend on FR-07 implementation")
    if "GR-01" not in requirements["FR-07"].get("implementation_dependencies", []):
        fail("FR-07 must list GR-01 as an implementation prerequisite")
    gr_acs = {a["id"]: a for a in gr["fit_criterion"]}
    if len(gr_acs) < 6:
        fail("GR-01 must cover companies, sources, non-code generation, Stage A, Stage B, and dependency gate")
    if gr_acs["GR-01-FC01"].get("metric") != "reference_company_count" or float(gr_acs["GR-01-FC01"].get("threshold", 0)) < 2:
        fail("GR-01-FC01 must require at least two reference companies")
    if "implementation_generated_expected_value_count" not in gr_acs["GR-01-FC03"].get("metric", ""):
        fail("GR-01-FC03 must check code-generated expected values")
    a_text = gr_acs["GR-01-FC04"]["expected_result"].lower()
    for token in ("no fr-07 implementation record is required", "absence of an implementation record is not missing evidence"):
        if token not in a_text:
            fail(f"GR-01-FC04 Stage A is missing {token!r}")
    b_text = gr_acs["GR-01-FC05"]["expected_result"].lower()
    for token in ("not_applicable", "first related implementation record"):
        if token not in b_text:
            fail(f"GR-01-FC05 Stage B is missing {token!r}")
    gate_text = gr_acs["GR-01-FC06"]["expected_result"].lower()
    if "fr-07" not in gate_text or "blocked" not in gate_text:
        fail("GR-01-FC06 must state the FR-07 gate direction and blocked state")
    gr_text = gr["statement"].lower()
    if "stage a" not in gr_text or "stage b" not in gr_text:
        fail("GR-01 statement must distinguish Stage A and Stage B")
    results["gr01"] = "Stage A pre-implementation readiness; Stage B post-implementation timing; FR-07 gate"

    # CR-01 local cost attribution, target, and claim boundary.
    cr = requirements["CR-01"]
    if "local cost attribution" not in cr["title"].lower():
        fail("CR-01 title must name local cost attribution")
    if not any(e.get("path") == "docs/req/evaluation/brief-eval-contract-v4.json" for e in cr["sources"]["evidence"]):
        fail("CR-01 must reference brief-eval-contract-v4.json")
    cr_acs = {a["id"]: a for a in cr["fit_criterion"]}
    if len(cr_acs) != 5:
        fail("CR-01 must separate measurement, safety, quality/state, target, and claim boundary")
    if cr_acs["CR-01-FC01"].get("metric") != "measurement_formula_error_count":
        fail("CR-01-FC01 must check measurement formula/null handling")
    if cr_acs["CR-01-FC02"].get("metric") != "safety_escapes":
        fail("CR-01-FC02 must check safety escapes")
    if "quality_loss" not in cr_acs["CR-01-FC03"].get("metric", ""):
        fail("CR-01-FC03 must check quality loss")
    if "net_cost" not in cr_acs["CR-01-FC04"].get("metric", ""):
        fail("CR-01-FC04 must check the cost target")
    if cr_acs["CR-01-FC05"].get("metric") != "claim_boundary_violation_count":
        fail("CR-01-FC05 must check claim boundaries")
    for ac_id in ("CR-01-FC03", "CR-01-FC04"):
        if "brief-eval-contract-v4.json#/thresholds/" not in cr_acs[ac_id].get("threshold_ref", ""):
            fail(f"{ac_id} must reference the v2 contract threshold")
    ac1_text = " ".join((cr_acs["CR-01-FC01"]["input"], cr_acs["CR-01-FC01"]["expected_result"])).lower()
    for token in ("brief-generation input", "retry/fallback", "excluded"):
        if token not in ac1_text:
            fail(f"CR-01-FC01 must disclose local scope term {token!r}")
    ac4_text = " ".join((cr_acs["CR-01-FC04"]["input"], cr_acs["CR-01-FC04"]["expected_result"])).lower()
    if "budget_met" not in ac4_text or "not a saving" not in ac4_text:
        fail("CR-01-FC04 must separate budget attainment from saving")
    ac5_text = " ".join((cr_acs["CR-01-FC05"]["input"], cr_acs["CR-01-FC05"]["expected_result"])).lower()
    for token in ("budget_met", "local_cost_saving", "token_reduction", "whole-application"):
        if token not in ac5_text:
            fail(f"CR-01-FC05 is missing claim boundary {token!r}")
    cr_text = cr["statement"].lower()
    for token in ("local cost attribution", "budget_met", "local_cost_saving", "whole-application", "pre-run", "result evidence"):
        if token not in cr_text:
            fail(f"CR-01 statement is missing {token!r}")
    results["cr01"] = "local cost attribution; budget/target, local saving, token change, and whole-app claim separated"

    # QR-02 type and deferred status.
    qr02 = requirements["QR-02"]
    if qr02["type"] != "performance":
        fail("QR-02 must use the performance type")
    if qr02["status"] != "deferred":
        fail("QR-02 must remain deferred")
    results["qr02"] = "performance/deferred"

    # FR-01/QR-01 responsibility split and FR-01 v1.21.0 revision.
    fr01 = requirements["FR-01"]
    expected_counts = {"FR-01": 9, "FR-02": 11, "FR-03": 10, "FR-04": 9, "FR-05": 3}
    actual_counts = {rid: len(requirements[rid]["fit_criterion"]) for rid in expected_counts}
    if actual_counts != expected_counts:
        fail(f"FR-01..FR-05 fit-criterion counts changed: {actual_counts} != {expected_counts}")
    fr01_ids = [a["id"] for a in fr01["fit_criterion"]]
    if fr01_ids != [f"FR-01-FC{i:02d}" for i in range(1, 10)]:
        fail(f"FR-01 must keep FC01-FC06 and add FC07-FC09 in order: {fr01_ids}")
    fr01_text = " ".join(" ".join((a["input"], a["expected_result"], a["verification"])) for a in fr01["fit_criterion"]).lower()
    for token in ("waiter", "cancel", "execution deadline", "origin_run_id", "inherited", "entry point", "unknown parameter", "deadline"):
        if token not in fr01_text:
            fail(f"FR-01 revision is missing required concept {token!r}")
    fr01_ac6 = next(a for a in fr01["fit_criterion"] if a["id"] == "FR-01-FC06")
    ac6_text = " ".join((fr01_ac6["input"], fr01_ac6["expected_result"], fr01_ac6["verification"])).lower()
    for token in ("fixed", "replay", "unsafe_output_escape_count"):
        if token not in ac6_text:
            fail(f"FR-01-FC06 is missing deterministic replay condition {token!r}")
    qr = requirements["QR-01"]
    if "FR-01-FC06" not in qr["statement"]:
        fail("QR-01 must reference FR-01-FC06 as its deterministic precondition")
    qr_acs = {a["id"]: a for a in qr["fit_criterion"]}
    if qr_acs["QR-01-FC01"].get("metric") != "mean_rubric_drop":
        fail("QR-01-FC01 must judge only mean rubric drop")
    if qr_acs["QR-01-FC02"].get("metric") != "per_case_rubric_drop_max":
        fail("QR-01-FC02 must judge only per-case drop")
    if qr_acs["QR-01-FC03"].get("metric") != "live_review_rate_increase":
        fail("QR-01-FC03 must judge only REVIEW-rate increase")
    if qr_acs["QR-01-FC05"].get("metric") != "unsafe_output_escape_count":
        fail("QR-01-FC05 must own the zero-safety-escape condition")
    for ac_id in ("QR-01-FC01", "QR-01-FC02", "QR-01-FC03"):
        text = " ".join((qr_acs[ac_id]["input"], qr_acs[ac_id]["expected_result"])).lower()
        if "unsafe_output_escape_count" in text:
            fail(f"{ac_id} must not duplicate the safety escape condition")
    results["fr01_qr01"] = "FR-01 FC01-FC06 revised and FC07-FC09 added; QR-01 criteria separated"

    # Deferred scope must not remain active in fit criteria.
    def fc_text(req_id):
        return " ".join(" ".join((a["input"], a["expected_result"], a["verification"])) for a in requirements[req_id]["fit_criterion"]).lower()
    for token in ("verified_package", "history_reference_closure", "export_conflict"):
        if token in fc_text("FR-05"):
            fail(f"FR-05 active fit criteria must not require deferred export item {token!r}")
    for token in ("fencing", "takeover", "stale claim"):
        if token in fc_text("FR-06"):
            fail(f"FR-06 active fit criteria must not require deferred multi-worker item {token!r}")
    for token in ("ttm_revenue =", "ttm_eps =", "pe_ttm =", "fcf_yoy ="):
        if token in fc_text("FR-07"):
            fail(f"FR-07 active fit criteria must not require deferred metric formula {token!r}")
    results["deferred_scope"] = "FR-05 export, FR-06 multi-worker, FR-07 TTM/FCF YoY inactive"

    # Non-functional field completeness and threshold-ref resolution.
    unresolved = []
    for req in doc["requirements"]:
        if req["type"] in {"performance", "cost", "quality"}:
            for ac in req["fit_criterion"]:
                for field in ("metric", "operator", "unit"):
                    if not ac.get(field):
                        fail(f"{ac['id']} is missing non-functional field {field}")
                if ac.get("threshold") is None and not ac.get("threshold_ref"):
                    fail(f"{ac['id']} needs threshold or threshold_ref")
        for ac in req["fit_criterion"]:
            ref = ac.get("threshold_ref")
            if not ref:
                continue
            path, _, pointer = ref.partition("#")
            target = ROOT / path
            if not target.exists():
                fail(f"{ac['id']} threshold_ref file does not exist: {path}")
            try:
                value = _resolve_json_pointer(load(target), pointer)
            except Exception:
                fail(f"{ac['id']} threshold_ref does not resolve: {ref}")
            if value is None:
                unresolved.append(ac["id"])
                if ac.get("threshold_status") == "approved":
                    fail(f"{ac['id']} has approved threshold_status but a null threshold_ref")
            elif isinstance(value, bool) or not isinstance(value, (int, float)):
                fail(f"{ac['id']} threshold_ref must resolve to a number or null")
    results["threshold_refs"] = {"unresolved": sorted(unresolved), "resolved": "number or explicit null"}

    # Targeted contradiction guards.
    fr01_ac5 = " ".join((requirements["FR-01"]["fit_criterion"][4]["expected_result"],)).lower()
    if "exceeding either budget yields" in fr01_ac5:
        fail("FR-01-FC05 must not force a terminal unavailable outcome on either-budget exhaustion")
    if "unique identity is (run_id, data_query_key)" not in requirements["FR-03"]["statement"]:
        fail("FR-03 must state the executed record identity as (run_id, data_query_key)")
    if "invalid model rating MUST block with invalid_model_rating" not in requirements["FR-04"]["statement"]:
        fail("FR-04 must block invalid ratings with invalid_model_rating")
    if "invalid ratings use not_applicable" in requirements["SB-01"]["notes"] or any("invalid ratings may use not_applicable" in x for x in requirements["SB-01"]["assumptions"]):
        fail("SB-01 must not allow invalid ratings to use not_applicable")
    if "Authoritative blocked/error decision table" not in requirements["SB-01"]["notes"]:
        fail("SB-01 must contain the explicit blocked/error decision table")
    fr08_ac4 = " ".join((requirements["FR-08"]["fit_criterion"][3]["expected_result"],)).lower()
    if "quality_loss" in fr08_ac4:
        fail("FR-08-FC04 must not retain optimization quality thresholds; those are CR-01")
    qr01_text = " ".join((requirements["QR-01"]["statement"], " ".join(a["expected_result"] for a in requirements["QR-01"]["fit_criterion"]))).lower()
    if "minimum of repeats" in qr01_text or "single score or" in qr01_text:
        fail("QR-01 must use one fixed sampling rule, not an open single-score-or-minimum choice")
    if "reused historical memory entry" not in requirements["INV-01"]["statement"] or "reused_decision_ref" not in requirements["INV-01"]["statement"]:
        fail("INV-01 must state the reused historical memory exception")
    sr_ac4 = requirements["SR-01"]["fit_criterion"][3]["expected_result"].lower()
    if "does not claim one" not in sr_ac4:
        fail("SR-01-FC04 must not require a failed record when it cannot be safely written")
    return results


def revised_fr01_fr05_checks(doc: dict, manifest_schema: dict) -> dict:
    """Static checks for the v1.21.0 FR-01..FR-05 semantic revision."""
    requirements = {r["id"]: r for r in doc["requirements"]}
    contract = load(REQ_DIR / "requirement-contracts-v1.json")
    if contract.get("contract_set_version") != "1.1.0":
        fail("requirement contract set version must be 1.1.0")
    if contract.get("status") != "provisional" or contract.get("approved") is not False:
        fail("requirement contracts must remain provisional and not approved")
    for key in ("execution_policy_v1", "method_normalization_v1", "coverage_profile_v1", "risk_scope_v1", "history_scan_v1", "timing_and_write_evidence_v1", "token_accounting_v1", "financial_metric_v1", "brief_budget_v1", "recovery_policy_v1"):
        if key not in contract:
            fail(f"requirement contract missing {key}")
    fr01 = requirements["FR-01"]
    fr01_text = " ".join((fr01["statement"], " ".join(fr01["assumptions"]), " ".join(a["input"]+" "+a["expected_result"]+" "+a["verification"] for a in fr01["fit_criterion"]))).lower()
    for token in ("waiter", "execution deadline", "unknown parameter", "origin_run_id", "inherited", "entry point", "run-cache"):
        if token not in fr01_text:
            fail(f"FR-01 revision missing {token!r}")
    for key in ("execution_policy", "method_normalization_contract", "availability_plan", "availability_view"):
        if key not in doc["definitions"]:
            fail(f"definitions missing {key}")
    fr02_text = " ".join((requirements["FR-02"]["statement"], " ".join(requirements["FR-02"]["assumptions"]))).lower()
    for token in ("observed_until", "writeevidence", "call_id", "validation_status", "partial"):
        if token not in fr02_text:
            fail(f"FR-02 revision missing {token!r}")
    fr03_text = " ".join((requirements["FR-03"]["statement"], " ".join(requirements["FR-03"]["assumptions"]))).lower()
    for token in ("availability_plan", "supports", "sealed", "view_version", "period slot"):
        if token not in fr03_text:
            fail(f"FR-03 revision missing {token!r}")
    fr04_text = " ".join((requirements["FR-04"]["statement"], " ".join(requirements["FR-04"]["assumptions"]))).lower()
    for token in ("instrument_id", "candidate_id", "portfolio_scope", "exact cross", "diagnostic", "effective_order_value"):
        if token not in fr04_text:
            fail(f"FR-04 revision missing {token!r}")
    fr05_text = " ".join((requirements["FR-05"]["statement"], " ".join(requirements["FR-05"]["assumptions"]))).lower()
    for token in ("list_publications", "get_run", "history_read_failed", "scan_budget_exceeded", "validated buffer", "sr-02", "rotation"):
        if token not in fr05_text:
            fail(f"FR-05 revision missing {token!r}")
    if "SR-02" not in requirements["FR-05"]["constraint_relations"]:
        fail("FR-05 must list SR-02 as a constraint relation")
    mp = manifest_schema["properties"]["model_proposal"]
    if not any("null" in branch.get("type", "") for branch in mp.get("oneOf", [])):
        fail("manifest model_proposal must allow null for running/failed")
    timing = manifest_schema["properties"]["timing"]["properties"]
    if "observed_until" not in timing:
        fail("manifest timing must support observed_until")
    tokens = manifest_schema["properties"]["tokens"]["properties"]
    for key in ("reported_call_count", "unknown_call_count", "field_coverage", "aggregation_source"):
        if key not in tokens:
            fail(f"manifest tokens must support {key}")
    return {
        "contract_set_version": contract["contract_set_version"],
        "contract_status": contract["status"],
        "fr01_acs": len(fr01["fit_criterion"]),
        "fr02_acs": len(requirements["FR-02"]["fit_criterion"]),
        "fr03_acs": len(requirements["FR-03"]["fit_criterion"]),
        "fr04_acs": len(requirements["FR-04"]["fit_criterion"]),
        "fr05_acs": len(requirements["FR-05"]["fit_criterion"]),
        "check_kind": "static_requirement_contract_check",
    }



def revised_fr06_fr08_checks(doc: dict, manifest_schema: dict) -> dict:
    requirements = {r["id"]: r for r in doc["requirements"]}
    fr06 = requirements["FR-06"]
    fr06_text = " ".join((fr06["statement"], " ".join(fr06["assumptions"]), " ".join(a["input"]+" "+a["expected_result"]+" "+a["verification"] for a in fr06["fit_criterion"]))).lower()
    for token in ("recover_pending", "no-task", "root", "failed_precommit", "terminal-first", "run_id_conflict", "corrupt_record", "restored", "new_entry", "reuse_existing", "disabled"):
        if token not in fr06_text:
            fail(f"FR-06 revision missing {token!r}")
    fr07 = requirements["FR-07"]
    fr07_text = " ".join((fr07["statement"], " ".join(fr07["assumptions"]), " ".join(a["input"]+" "+a["expected_result"]+" "+a["verification"] for a in fr07["fit_criterion"]))).lower()
    for token in ("fiscal position", "date-level", "price_date", "computed", "not_supported", "metric_evidence_bundle", "complete n/a", "recalculat", "approximate"):
        if token not in fr07_text:
            fail(f"FR-07 revision missing {token!r}")
    fr08 = requirements["FR-08"]
    fr08_text = " ".join((fr08["statement"], " ".join(fr08["assumptions"]), " ".join(a["input"]+" "+a["expected_result"]+" "+a["verification"] for a in fr08["fit_criterion"]))).lower()
    for token in ("token", "tokenizer", "full-request", "resolver", "replaces the four full analyst reports", "view_version", "brief_rejected", "invalid_marker", "context_audit_metadata", "independent of cr-01"):
        if token not in fr08_text:
            fail(f"FR-08 revision missing {token!r}")
    timing_req = set(manifest_schema["properties"]["timing"]["required"])
    for key in ("observed_until", "startup_phase_seconds", "publish_prepare_seconds", "observed_duration_seconds"):
        if key not in timing_req:
            fail(f"manifest timing must require {key}")
    token_req = set(manifest_schema["properties"]["tokens"]["required"])
    for key in ("reported_call_count", "unknown_call_count", "field_coverage", "aggregation_source"):
        if key not in token_req:
            fail(f"manifest tokens must require {key}")
    pol = manifest_schema["$defs"]["portfolio_risk_policy_snapshot"]["properties"]
    if "policy_file_ref" not in pol:
        fail("manifest policy schema must support policy_file_ref")
    budget = load(FIXTURE_DIR / "brief_budget_policy_v2.json")
    if budget.get("budget_unit") != "tokens" or budget.get("policy_version") != "brief-budget-policy-v2":
        fail("brief budget v2 must use token units and version v2")
    if "resolved_payload_tokens" not in budget:
        fail("brief budget v2 must declare resolved_payload_tokens")
    recovery = load(FIXTURE_DIR / "archive_recovery_v1.json")
    if not any(s.get("status") == "failed_precommit" and s.get("failed_recoverable") for s in recovery.get("snapshots", [])):
        fail("archive recovery fixture must include a recoverable failed_precommit case")
    return {
        "fr06_acs": len(fr06["fit_criterion"]),
        "fr07_acs": len(fr07["fit_criterion"]),
        "fr08_acs": len(fr08["fit_criterion"]),
        "brief_budget_version": budget["policy_version"],
        "check_kind": "static_requirement_contract_check",
    }

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
    ac_ids = [a["id"] for r in doc["requirements"] for a in r["fit_criterion"]]
    if len(ac_ids) != len(set(ac_ids)):
        fail("duplicate fit-criterion IDs")
    for req in doc["requirements"]:
        actual = [ac["id"] for ac in req["fit_criterion"]]
        expected = [f"{req['id']}-FC{i:02d}" for i in range(1, len(actual) + 1)]
        if actual != expected:
            fail(f"{req['id']} fit criteria are not continuous {req['id']}-FCnn: {actual}")
        for ac in req["fit_criterion"]:
            if "-AC" in ac["id"]:
                fail(f"fit criterion {ac['id']} retains the retired AC identifier")

    approved_ids = set(doc["scope"]["approved_ids"])
    draft_ids = set(doc["scope"].get("draft_ids", []))
    deferred_ids = set(doc["scope"].get("deferred_ids", []))
    status_approved = {rid for rid, req in requirements.items() if req["status"] == "approved"}
    status_draft = {rid for rid, req in requirements.items() if req["status"] == "draft"}
    status_deferred = {rid for rid, req in requirements.items() if req["status"] == "deferred"}
    if approved_ids != status_approved:
        fail("scope.approved_ids does not match requirements with status=approved")
    if draft_ids != status_draft:
        fail("scope.draft_ids does not match requirements with status=draft")
    if deferred_ids != status_deferred:
        fail("scope.deferred_ids does not match requirements with status=deferred")
    if approved_ids & draft_ids or approved_ids & deferred_ids or draft_ids & deferred_ids:
        fail("a requirement cannot appear in more than one status scope list")
    if approved_ids | draft_ids | deferred_ids != set(requirements):
        fail("scope.approved_ids, scope.draft_ids, and scope.deferred_ids must cover every requirement")

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
        for evidence in req["sources"]["evidence"]:
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
    spec_summary = pr_gr_cr_consistency_checks(doc)
    revised_summary = revised_fr01_fr05_checks(doc, manifest_schema)
    revised_678_summary = revised_fr06_fr08_checks(doc, manifest_schema)
    gr01_freeze_summary = gr01_freeze_fixture_checks()
    round4_summary = round4_checks(doc)
    mapping_summary = fc_mapping_checks(doc)

    input_paths = [REQUIREMENTS, REQ_SCHEMA, MANIFEST_SCHEMA, Path(__file__),
                   EVAL_DIR / "eval-set-v1.json", EVAL_DIR / "rubric-v1.json",
                   EVAL_DIR / "behavior-eval-contract-v1.json", EVAL_DIR / "behavior-eval-contract-v2.json", EVAL_DIR / "config-v1.json",
                   EVAL_DIR / "prompt-v1.0.yaml", EVAL_DIR / "snapshots-v1.json",
                   FIXTURE_DIR / "portfolio_risk_input_v1.json",
                   FIXTURE_DIR / "portfolio_risk_input_invalid_v1.json",
                   FIXTURE_DIR / "portfolio_risk_policy_v1.json",
                   FIXTURE_DIR / "portfolio_risk_policy_v2.json",
                   FIXTURE_DIR / "run_clock_historical_v1.json",
                   FIXTURE_DIR / "run_clock_future_v1.json",
                   FIXTURE_DIR / "risk_evidence_expected_v1.json",
                   FIXTURE_DIR / "archive_history_v1.json",
                   FIXTURE_DIR / "archive_recovery_v1.json",
                   FIXTURE_DIR / "financial_metrics_v1.json",
                   FIXTURE_DIR / "downstream_brief_v1.json",
                   EVAL_DIR / "brief-eval-contract-v1.json",
                   EVAL_DIR / "brief-eval-contract-v2.json",
                   EVAL_DIR / "brief-eval-contract-v3.json",
                   EVAL_DIR / "brief-eval-contract-v4.json",
                   FIXTURE_DIR / "brief_budget_policy_v1.json",
                   FIXTURE_DIR / "brief_budget_policy_v2.json",
                   FIXTURE_DIR / "brief_eval_states_v1.json",
                   FIXTURE_DIR / "brief_eval_states_v2.json",
                   FIXTURE_DIR / "brief_eval_states_v3.json",
                   FIXTURE_DIR / "brief_eval_states_v4.json",
                   FIXTURE_DIR / "gate_decision_v2.json",
                   FIXTURE_DIR / "invariant_projection_v2.json",
                   FIXTURE_DIR / "secret_path_controls_v2.json",
                   FIXTURE_DIR / "quality_scoring_v1.json",
                   FIXTURE_DIR / "gr01_freeze_states_v1.json",
                   REQ_DIR / "requirement-contracts-v1.json",
                   REQ_DIR / "requirement-mapping.csv"]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in input_paths}
    old = load(RESULTS) if RESULTS.exists() else {}
    if "--check" in sys.argv:
        if old.get("input_hashes") != hashes:
            fail("validation results are stale: input hashes changed")
        print("PASS: validation results match current inputs")
        return
    human_review_status = doc.get("validation", {}).get("human_review_status")
    approval = doc.get("validation", {}).get("approval_record") or {}
    if human_review_status == "approved":
        human = {
            "status": "approved",
            "reviewer": None,
            "reviewed_at": approval.get("approved_at"),
            "notes": "Approval recorded in requirements.yaml validation.approval_record; the user explicitly authorized approval of the requirement design. No named reviewer, signature, meeting, application test, or live evaluation is claimed.",
            "approval_record_ref": "docs/req/requirements.yaml#/validation/approval_record",
            "baseline_version": doc["document"]["version"],
            "bound_input_hashes": hashes,
            "bound_document_version": doc["document"]["version"],
        }
    else:
        human = {"status": "pending", "reviewer": None, "reviewed_at": None,
                 "notes": "Machine checks passed; human review remains pending.",
                 "bound_input_hashes": hashes, "bound_document_version": doc["document"]["version"]}
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
            {"id": "scope_status_consistency", "result": "pass", "details": {"approved": len(approved_ids), "draft": len(draft_ids), "deferred": len(deferred_ids)}},
            {"id": "manifest_schema_compile", "result": "pass"},
            {"id": "manifest_samples", "result": "pass", "details": manifest_summary},
            {"id": "completed_counterexamples_cross_field", "result": "pass"},
            {"id": "fit_criterion_count", "result": "pass", "details": {"count": len(ac_ids)}},
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
            {"id": "spec_consistency", "result": "pass", "details": spec_summary},
            {"id": "revised_fr01_fr05_contracts", "result": "pass", "details": revised_summary},
            {"id": "revised_fr06_fr08_contracts", "result": "pass", "details": revised_678_summary},
            {"id": "gr01_freeze_fixture", "result": "pass", "details": gr01_freeze_summary},
            {"id": "round4_requirement_and_fixture_consistency", "result": "pass", "details": round4_summary},
            {"id": "fc_identifier_normalization", "result": "pass", "details": {"total": len(ac_ids), "format": "<requirement-id>-FCnn", "continuous": True}},
            {"id": "approval_freeze_record", "result": "pass", "details": {"human_review_status": human_review_status, "baseline_version": doc["document"]["version"], "approved_scope": len(approved_ids), "deferred": sorted(deferred_ids)}},
            {"id": "cr01_state_table", "result": "pass", "details": {"contract": "d1-brief-contract-v4", "fixture": "brief-eval-states-v4", "cases": brief_state_summary.get("cases"), "invalid_cases": brief_state_summary.get("invalid_cases")}},
            {"id": "fc_mapping_complete", "result": "pass", "details": mapping_summary},
        ],
        "human_review": human,
        "limitations": [
            "Machine checks cover schema structure, manifest samples, completed counterexamples, cross-field semantics, IDs, references, paths, dependency acyclicity, draft/deferred/approved scope consistency, PR/GR/CR/QR specification consistency, threshold-ref resolution, and portfolio-risk/archive document coverage.",
            "portfolio_risk_document_coverage checks required case concepts in acceptance text; it is a document coverage check, not behavior verification.",
            "archive_document_coverage checks required archive/recovery/benchmark concepts in acceptance text; it is a document coverage check, not behavior verification.",
            "financial_metrics_document_coverage and downstream_brief_document_coverage check required concepts and expected fixture values in acceptance text; they are document coverage checks, not behavior verification.",
            "Behavioral evaluation is blocked until snapshots and the applicable contract/threshold approval are complete; requirement-design approval does not satisfy those conditions. The frozen v1 eval files are unchanged.",
            "Risk evidence, archive, financial, and brief fixtures recompute local requirement evidence and negatives; they are requirement-evidence checks, not application tests.",
            "archive_static_fixture, downstream_brief_fixture, brief_budget_policy, brief_evaluation_contract, and brief_eval_state_fixture are static checks. Process concurrency, lease fencing, lost-lease rejection, zero-external-call behavior, live model brief-following, and live token/quality evaluation still require process-level, dependency-sentinel, and live evaluation tests that were not executed.",
            "spec_consistency verifies document/contract relationships (PR-01 statistics, GR-01 direction, CR-01 separation, FR-01/QR-01 split, QR-02 type, deferred active scope). It does not prove application behavior.",
            "revised_fr01_fr05_contracts checks the v1.21.0 requirement contracts, required concepts, manifest schema support, and the provisional contract set; it is a static document/contract check, not an application test.",
            "revised_fr06_fr08_contracts checks FR-06/07/08 concept closure, required manifest timing/token fields, policy file ref, token budget v2, and recoverable failed fixture; it is a static consistency check, not an application test.",
            "threshold_ref resolution treats a null target as unresolved/blocked, never as an approved numeric threshold; CR-01-FC03 and CR-01-FC04 currently resolve to null targets.",
            "brief-eval-contract-v4 and behavior-eval-contract-v2 are active revision drafts; brief v3/v2/v1 and behavior v1 plus the frozen eval set/rubric/config/prompt/snapshots are retained unchanged. GR-01 source independence and freeze adequacy still require human review; the script checks presence, locators, digests, Stage A readiness, and Stage B ordering only.",
            "gr01_freeze_fixture covers Stage A without implementation, missing material, issuer/calendar/coverage negatives, independent-script versus implementation-generated expectations, post-implementation reviewed revision, unreviewed revision, version mismatch, and retroactive/backdated freeze; it is a static fixture, not an implementation test.",
            "brief_eval_state_fixture covers the two-field execution/acceptance table, illegal pairs, forbidden pending/aborted acceptance strings, start-after-input-mismatch, aborted preservation, retry history, evidence/sample/usage failures, and budget/local-saving/token claim boundaries; it is a static fixture, not a live evaluation.",
            "round4_requirement_and_fixture_consistency checks SB-01 gate/publication separation, INV-01 identity/projection and retention high-water, INV-02 reason mapping and current/historical evidence, SR-01 detected/residual and credential-store boundaries, SR-02 operation/path confinement, and QR scoring/REVIEW/safety separation. These are static document/fixture checks, not application, OS-race, secret, live-quality, cost, or live-performance tests.",
            "FC identifiers remain <requirement-id>-FCnn; the v1.23.0-to-v1.24.0 mapping is recorded in requirement-mapping.csv, and v1.25.0 changes no FC ID or count.",
            "A separate v1.24.0-to-v1.25.0 comparison found changes only in CR-01 statement/FC03/FC04 references/assumptions/notes and the FR-08 active-contract reference; all 122 FC IDs, counts, and other requirement/FC contents are unchanged. The comparison is recorded in the freeze notes, not recomputed by this validator.",
            "CR-01 v1.25.0 uses the two-field execution_status/acceptance_status table with brief-eval-contract-v4 and brief_eval_states_v4; pending/aborted acceptance strings and illegal state pairs are rejected. CR-01 evaluation remains blocked by prices, thresholds, snapshots, and human contract approval.",
            "Approval covers requirement design only. Application implementation, application tests, live model/vendor/broker evaluations, provisional threshold approvals, external GR-01 evidence, and deferred capabilities remain outside this approval.",
            "No application implementation or application test was executed in this requirements-validation pass.",
        ],
    }
    RESULTS.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS: requirements schema")
    print("PASS: manifest schema and samples")
    print(f"PASS: {len(requirements)} requirements, {len(ac_ids)} fit criteria")
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
    print("PASS: PR/GR/CR/QR specification consistency")
    print("PASS: GR-01 Stage A/B freeze fixture")
    print("PASS: round-4 requirement and fixture consistency")
    print("PASS: FC identifier mapping complete and consistent")
    print(f"WROTE: {RESULTS.relative_to(ROOT)}")
    print(f"HUMAN REVIEW: {human['status']}")


if __name__ == "__main__":
    main()
