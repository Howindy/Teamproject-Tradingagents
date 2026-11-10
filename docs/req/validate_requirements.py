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
import sys
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
REQ_DIR = ROOT / "docs" / "req"
REQUIREMENTS = REQ_DIR / "requirements.yaml"
REQ_SCHEMA = REQ_DIR / "req-schema.json"
MANIFEST_SCHEMA = REQ_DIR / "run-manifest-schema.json"
RESULTS = REQ_DIR / "validation-results.json"
EVAL_DIR = REQ_DIR / "evaluation"
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
    m["safety_gate"]["input_hash"] = canonical_hash({
        "snapshot_hash": m["coverage_snapshot"]["snapshot_hash"],
        "model_proposal": proposal,
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
        "safety_gate": {"status": "passed", "reason_codes": [], "primary_reason_code": None, "coverage_status": "complete", "critical_gap_ids": [], "profile_version": "d1-default-v1", "snapshot_hash": SHA, "gate_version": "1.0", "input_hash": SHA, "run_id": "r1", "evaluated_at": "2026-11-09T12:03:15+08:00"},
        "security": {"scan_status": "clean", "write_scan_status": "clean", "run_scan_status": "clean", "known_secret_match_count": 0, "pattern_match_count": 0, "redaction_count": 0, "rule_version": "1.0", "scope": ["manifest", "final_state", "memory", "report", "logs", "preferences", "gate", "availability"], "failure_reason": None},
        "memory": {"enabled": True, "status": "written", "commit_status": "committed", "entry_version": 1, "entry_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": SHA, "trade_date": "2026-10-19", "ticker": "NVDA"}, "entry_digest": SHA, "evidence_digest": SHA, "reused_decision_ref": None, "supersedes": None, "retention_status": "retained", "same_day_rerun": False},
        "artifact_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": SHA, "gate_status": "passed", "formal_decision_status": "approved", "final_rating": "Hold", "coverage_status": "complete", "critical_gap_ids": [], "coverage_snapshot_hash": SHA, "record_hash": SHA},
        "formal_decision": {"status": "approved", "final_rating": "Hold", "decision_text": "Hold decision", "review_class": "none"},
        "artifacts": [{"kind": "report", "path": "r.md", "sha256": SHA, "hash_scope": "file"}, {"kind": "final_state", "path": "f.json", "sha256": SHA, "hash_scope": "file"}, {"kind": "memory", "path": "memory.md", "sha256": SHA, "hash_scope": "memory_entry"}],
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
    if canonical_hash({"snapshot_hash": c["snapshot_hash"], "model_proposal": proposal, "gate_version": g["gate_version"]}) != g.get("input_hash"):
        errors.append("input_hash does not match gate input content")
    if canonical_hash(record_projection(m)) != b.get("record_hash"):
        errors.append("record_hash does not match immutable record projection")
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
    failed_startup.update({"run_status": "failed", "critical_profile": None, "coverage_snapshot": None, "provenance_digest": canonical_hash([]), "data_source_status": [], "safety_gate": {"status": "not_run", "reason_codes": [], "primary_reason_code": None, "coverage_status": None, "critical_gap_ids": [], "profile_version": None, "snapshot_hash": None, "gate_version": "1.0", "input_hash": canonical_hash({"snapshot_hash": None, "model_proposal": {k: completed["model_proposal"][k] for k in ("rating", "decision_text", "proposal_status")}, "gate_version": "1.0"}), "run_id": None, "evaluated_at": None}, "security": {"scan_status": "clean", "write_scan_status": "clean", "run_scan_status": "not_run", "known_secret_match_count": 0, "pattern_match_count": 0, "redaction_count": 0, "rule_version": "1.0", "scope": ["manifest"], "failure_reason": None}, "memory": {"enabled": True, "status": "not_available", "commit_status": "not_applicable", "entry_version": 1, "entry_binding": None, "entry_digest": None, "evidence_digest": None, "reused_decision_ref": None, "supersedes": None, "retention_status": "not_applicable", "same_day_rerun": False}, "artifact_binding": {"run_id": "r1", "decision_id": "d1", "record_version": "1", "decision_digest": canonical_hash({"status": "blocked_for_review", "final_rating": "REVIEW", "decision_text": "Run failed before formal decision; manual review required."}), "gate_status": "not_run", "formal_decision_status": "blocked_for_review", "final_rating": "REVIEW", "coverage_status": None, "critical_gap_ids": [], "coverage_snapshot_hash": None, "record_hash": None}, "formal_decision": {"status": "blocked_for_review", "final_rating": "REVIEW", "decision_text": "Run failed before formal decision; manual review required.", "review_class": "input_invalid"}, "artifacts": [], "error": {"stage": "startup", "type": "ConfigError", "message": "startup failed"}})
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
    for name, obj in (("running", running), ("completed", completed), ("blocked", blocked), ("failed_gate", failed), ("failed_startup", failed_startup), ("completed_memory_disabled", mem_off), ("resumed", resumed), ("retry_recovered", retry_recovered), ("memory_reuse", memory_reuse), ("version_switch", version_switch)):
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
    ]
    for name, mutate in negatives:
        obj = copy.deepcopy(completed)
        mutate(obj)
        if not list(v.iter_errors(obj)) and not cross_field_errors(obj):
            fail(f"completed negative {name} unexpectedly passed")
    if cross_field_errors(completed):
        fail(f"completed cross-field errors: {cross_field_errors(completed)}")

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
    return {"samples": 10, "completed_negatives": len(negatives), "canonicalization_checks": 6}


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
    if set(doc["scope"]["approved_ids"]) != set(requirements):
        fail("scope.approved_ids does not match requirement IDs")
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

    input_paths = [REQUIREMENTS, REQ_SCHEMA, MANIFEST_SCHEMA, Path(__file__),
                   EVAL_DIR / "eval-set-v1.json", EVAL_DIR / "rubric-v1.json",
                   EVAL_DIR / "behavior-eval-contract-v1.json", EVAL_DIR / "config-v1.json",
                   EVAL_DIR / "prompt-v1.0.yaml", EVAL_DIR / "snapshots-v1.json"]
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
            {"id": "manifest_schema_compile", "result": "pass"},
            {"id": "manifest_samples", "result": "pass", "details": manifest_summary},
            {"id": "completed_counterexamples_cross_field", "result": "pass"},
            {"id": "acceptance_count", "result": "pass", "details": {"count": len(ac_ids)}},
            {"id": "references_and_paths", "result": "pass"},
            {"id": "implementation_dependency_acyclic", "result": "pass"},
            {"id": "behavior_eval_contract", "result": "pass", "details": eval_summary},
        ],
        "human_review": human,
        "limitations": [
            "Machine checks cover schema structure, manifest samples, completed counterexamples, cross-field semantics, IDs, references, paths, and dependency acyclicity.",
            "Behavioral evaluation is blocked until snapshots and human approval are complete.",
        ],
    }
    RESULTS.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS: requirements schema")
    print("PASS: manifest schema and samples")
    print(f"PASS: {len(requirements)} requirements, {len(ac_ids)} acceptance criteria")
    print("PASS: references, traceability, evidence paths")
    print("PASS: implementation dependencies acyclic")
    print("PASS: behavior evaluation contract present and blocked")
    print(f"WROTE: {RESULTS.relative_to(ROOT)}")
    print("HUMAN REVIEW: pending")


if __name__ == "__main__":
    main()
