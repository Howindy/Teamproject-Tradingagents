"""Controlled semantic-evaluation entry for the trusted CI workflow.

The entry fails closed unless a human-approved dataset, rubric, threshold, and
model configuration exist.  A reviewed not-applicable determination is an
explicit alternative, but it must carry a human reviewer and reason.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ci_checks import CiError, load_yaml


def emit(result: Mapping[str, Any]) -> int:
    errors = result.get("errors", [])
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def validate_config(config: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(config, Mapping):
        return {"errors": ["semantic configuration must be a mapping"], "approved": False}
    required = {"schema_version", "status", "dataset", "rubric", "thresholds", "model", "approval"}
    missing = sorted(required - set(config))
    if missing:
        errors.append(f"missing configuration keys: {', '.join(missing)}")
    status = str(config.get("status", "unapproved"))
    if status not in {"approved", "unapproved"}:
        errors.append("status must be approved or unapproved")
    if errors:
        return {"errors": errors, "approved": False}

    approved = status == "approved"
    if not approved:
        return {
            "errors": [],
            "approved": False,
            "reason": "semantic configuration is unapproved",
        }

    dataset = config.get("dataset")
    rubric = config.get("rubric")
    thresholds = config.get("thresholds")
    model = config.get("model")
    approval = config.get("approval")
    if not isinstance(dataset, Mapping) or not dataset.get("version") or not dataset.get("cases"):
        errors.append("approved dataset requires version and cases")
    if not isinstance(rubric, Mapping) or not rubric.get("version") or not rubric.get("definition"):
        errors.append("approved rubric requires version and definition")
    if not isinstance(thresholds, Mapping) or not thresholds:
        errors.append("approved thresholds must be a non-empty mapping")
    if not isinstance(model, Mapping) or not model.get("provider") or not model.get("model"):
        errors.append("approved model requires provider and model")
    if not isinstance(approval, Mapping):
        errors.append("approval record is missing")
    else:
        for key in ("approved_by", "approved_at", "evidence"):
            if not approval.get(key):
                errors.append(f"approval.{key} is required for an approved configuration")
    return {"errors": errors, "approved": approved}


def build_record(
    *,
    candidate: str,
    workflow_sha: str,
    run_id: str,
    kind: str,
    status: str,
    config_version: str = "",
    reason: str = "",
    reviewed_by: str = "",
    approval_evidence: str = "",
) -> dict[str, Any]:
    return {
        "candidate_sha": candidate,
        "workflow_sha": workflow_sha,
        "run_id": run_id,
        "kind": kind,
        "status": status,
        "config_version": config_version,
        "reason": reason,
        "reviewed_by": reviewed_by,
        "approval_evidence": approval_evidence,
        "recorded_at": dt.datetime.now(dt.UTC).isoformat(),
    }


def run_approved_evaluation(
    config: Mapping[str, Any],
    candidate: str,
    runner: str,
) -> dict[str, Any]:
    if not runner:
        raise CiError("approved semantic configuration has no evaluation runner")
    module_name, separator, function_name = runner.partition(":")
    if not separator:
        raise CiError("runner must use module:function syntax")
    module = importlib.import_module(module_name)
    function = getattr(module, function_name)
    result = function(config, candidate)
    if not isinstance(result, Mapping):
        raise CiError("semantic evaluation runner did not return a mapping")
    return dict(result)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trusted semantic evaluation")
    parser.add_argument("--config", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--workflow-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--runner", default="")
    parser.add_argument("--not-applicable", action="store_true")
    parser.add_argument("--reason", default="")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--approval-evidence", default="")
    args = parser.parse_args(argv)

    try:
        if args.not_applicable:
            if not args.reason.strip():
                raise CiError("not-applicable determination requires a reason")
            if not args.reviewer.strip():
                raise CiError("not-applicable determination requires a reviewer")
            if not args.approval_evidence.strip():
                raise CiError("not-applicable determination requires approval evidence")
            record = build_record(
                candidate=args.candidate,
                workflow_sha=args.workflow_sha,
                run_id=args.run_id,
                kind="semantic-noop",
                status="not_applicable",
                reason=args.reason.strip(),
                reviewed_by=args.reviewer.strip(),
                approval_evidence=args.approval_evidence.strip(),
            )
            Path(args.output).write_text(json.dumps(record, indent=2), encoding="utf-8")
            return 0

        config = load_yaml(args.config)
        validation = validate_config(config)
        if validation["errors"]:
            return emit({"errors": validation["errors"]})
        if not validation["approved"]:
            return emit(
                {
                    "errors": [
                        "semantic evaluation blocked: configuration is unapproved; "
                        "provide an approved configuration or a reviewed not-applicable record"
                    ]
                }
            )
        result = run_approved_evaluation(config, args.candidate, args.runner)
        if str(result.get("status", "")) != "passed":
            return emit(
                {"errors": [f"semantic evaluation did not pass: {result.get('status')}"]}
            )
        record = build_record(
            candidate=args.candidate,
            workflow_sha=args.workflow_sha,
            run_id=args.run_id,
            kind="semantic",
            status="passed",
            config_version=str(config.get("dataset", {}).get("version", "")),
        )
        Path(args.output).write_text(json.dumps(record, indent=2), encoding="utf-8")
        return 0
    except CiError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
