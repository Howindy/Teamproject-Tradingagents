"""Controlled semantic-evaluation entry for the trusted CI workflow.

The entry fails closed unless a human-approved dataset, rubric, threshold, and
model configuration exist.  A reviewed not-applicable determination is an
explicit alternative, but it must carry a human reviewer and reason.

Semantic mode evaluates exactly one suite registered in the trusted
``docs/ci/semantic-suites.yaml``; its configuration and runner come only from
that registry (docs/plans/semantic-suite-routing.md §3.4-§3.5).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ci_checks import (
    CiError,
    load_suite_registry,
    load_yaml,
    sha256_lf,
    suite_status_context,
    validate_suite_id,
)

RESULT_STATUSES = {"passed", "failed", "needs_review"}


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
    details_path: str = "",
    details_sha256: str = "",
    dataset_sha256: str = "",
    rubric_sha256: str = "",
    request_count: int | None = None,
    candidate_summary: Mapping[str, Any] | None = None,
    baseline_summary: Mapping[str, Any] | None = None,
    suite: Mapping[str, str] | None = None,
    needs_review: Sequence[str] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
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
    if details_path:
        record["details_path"] = details_path
    if details_sha256:
        record["details_sha256"] = details_sha256
    if dataset_sha256:
        record["dataset_sha256"] = dataset_sha256
    if rubric_sha256:
        record["rubric_sha256"] = rubric_sha256
    if request_count is not None:
        record["request_count"] = request_count
    if candidate_summary is not None:
        record["candidate_summary"] = dict(candidate_summary)
    if baseline_summary is not None:
        record["baseline_summary"] = dict(baseline_summary)
    if suite is not None:
        record.update(
            {
                "suite_id": suite["suite_id"],
                "config_path": suite["config_path"],
                "config_sha256": suite["config_sha256"],
                "runner": suite["runner"],
            }
        )
    if needs_review is not None:
        record["needs_review"] = list(needs_review)
    return record


def load_runner(root: Path | str, runner: str) -> Any:
    """Import a registered runner from the trusted ``scripts/`` directory only."""
    import importlib.util

    module_name, separator, function_name = runner.partition(":")
    if not separator or not module_name or not function_name or "." in module_name:
        raise CiError("runner must use module:function syntax with a scripts/ module")
    path = (Path(root) / "scripts" / f"{module_name}.py").resolve()
    if not path.is_file():
        raise CiError(f"runner module {path} does not exist")
    module = sys.modules.get(module_name)
    module_file = getattr(module, "__file__", None)
    if module is None or not module_file or Path(module_file).resolve() != path:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise CiError(f"cannot load runner module {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    function = getattr(module, function_name, None)
    if not callable(function):
        raise CiError(f"runner {runner} is not callable")
    return function


def check_runner_signature(function: Any) -> list[str]:
    """Suite contract I3: evaluate(config, candidate_sha, *, output_dir, model_transport=None)."""
    import inspect

    try:
        parameters = inspect.signature(function).parameters
    except (TypeError, ValueError) as exc:
        return [f"runner signature cannot be inspected: {exc}"]
    errors: list[str] = []
    positional = [
        p
        for p in parameters.values()
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(positional) < 2:
        errors.append("runner must accept (config, candidate_sha) positionally")
    for name in ("output_dir", "model_transport"):
        parameter = parameters.get(name)
        if parameter is None or parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
            errors.append(f"runner must accept keyword argument {name}")
    transport = parameters.get("model_transport")
    if transport is not None and transport.default is not None:
        errors.append("runner model_transport must default to None")
    return errors


def normalize_runner_result(
    result: Any, *, output_dir: Path | None = None
) -> tuple[str, list[str], list[str]]:
    """Return (status, needs_review items, errors) per suite contract I3; fail closed."""
    if not isinstance(result, Mapping):
        return "failed", [], ["semantic evaluation runner did not return a mapping"]
    raw_errors = result.get("errors")
    if isinstance(raw_errors, list) and all(isinstance(e, str) for e in raw_errors):
        runner_errors = list(raw_errors)
        errors: list[str] = []
    else:
        runner_errors = []
        errors = ["runner errors must be a list of strings"]
    status = result.get("status")
    if not isinstance(status, str) or status not in RESULT_STATUSES:
        errors.append(f"runner returned invalid status: {status!r}")
        status = "failed"
    summary = result.get("candidate_summary")
    legacy_items = summary.get("needs_review") if isinstance(summary, Mapping) else None
    items = result.get("needs_review", legacy_items)
    if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
        errors.append("runner needs_review must be a list of strings")
        items = []
    else:
        items = list(items)
    if legacy_items is not None:
        if not isinstance(legacy_items, list) or not all(isinstance(i, str) for i in legacy_items):
            errors.append("runner candidate_summary.needs_review must be a list of strings")
        else:
            items = list(dict.fromkeys([*items, *legacy_items]))
    count = result.get("request_count")
    if type(count) is not int or count < 0:
        errors.append("runner request_count must be a non-negative integer")
    for field in ("dataset_sha256", "rubric_sha256", "details_path", "details_sha256"):
        if not isinstance(result.get(field), str) or not result[field].strip():
            errors.append(f"runner {field} must be a nonempty string")
    if output_dir is not None and isinstance(result.get("details_path"), str):
        try:
            details = Path(result["details_path"]).resolve()
            if not details.is_relative_to(output_dir.resolve()):
                errors.append("runner details_path must be inside output_dir")
            elif hashlib.sha256(details.read_bytes()).hexdigest() != result.get("details_sha256"):
                errors.append("runner details_sha256 does not match details file")
        except (OSError, ValueError) as exc:
            errors.append(f"runner details file is unavailable: {exc}")
    if errors or (runner_errors and status == "passed"):
        status = "failed"
    elif items and status == "passed":
        status = "needs_review"
    return str(status), items, [*runner_errors, *errors]


def resolve_suite(registry_path: str, suite_id: str) -> dict[str, Any]:
    """Validate a suite ID against the trusted registry before any runner import."""
    errors = validate_suite_id(suite_id)
    if errors:
        raise CiError("; ".join(errors))
    registry_file = Path(registry_path)
    if not registry_file.is_file():
        raise CiError(f"semantic suite registry {registry_path} does not exist")
    root = registry_file.resolve().parents[2]
    registry = load_suite_registry(registry_file, root)
    if registry["errors"]:
        raise CiError("semantic suite registry is invalid: " + "; ".join(registry["errors"]))
    entry = registry["suites"].get(suite_id)
    if entry is None:
        raise CiError(f"unknown semantic suite: {suite_id}")
    return {"root": root, "suite_id": suite_id, **entry}


def status_description(record: Mapping[str, Any] | None) -> tuple[str, str]:
    """Commit-status state and description for a trusted evidence record."""
    if not isinstance(record, Mapping):
        return "failure", "required evidence is missing or failed"
    status = str(record.get("status", ""))
    if status in {"passed", "not_applicable"}:
        return "success", f"evidence recorded for {record.get('candidate_sha', '')}"
    if status == "needs_review":
        items = record.get("needs_review")
        count = len(items) if isinstance(items, list) else 0
        return "failure", f"needs_review: {count} pending items"
    return "failure", "failed"


def _command_check_suite(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate a registered semantic suite ID")
    parser.add_argument("--registry", required=True)
    parser.add_argument("--suite", required=True)
    args = parser.parse_args(argv)
    try:
        suite = resolve_suite(args.registry, args.suite)
    except CiError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(suite_status_context(suite["suite_id"]))
    return 0


def _command_describe(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Describe an evidence record for a commit status")
    parser.add_argument("--record", required=True)
    args = parser.parse_args(argv)
    record: Any = None
    try:
        record = json.loads(Path(args.record).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        record = None
    state, description = status_description(record)
    print(f"{state}\t{description}")
    return 0


def _run_suite(args: argparse.Namespace) -> int:
    suite = resolve_suite(args.registry, args.suite)
    config_path = suite["root"] / suite["config"]
    config = load_yaml(config_path)
    validation = validate_config(config)
    if validation["errors"]:
        return emit({"errors": validation["errors"]})
    if not validation["approved"]:
        return emit(
            {
                "errors": [
                    f"semantic evaluation blocked: suite {suite['suite_id']} configuration "
                    "is unapproved; provide an approved configuration or a reviewed "
                    "not-applicable record"
                ]
            }
        )
    suite_fields = {
        "suite_id": suite["suite_id"],
        "config_path": suite["config"],
        "config_sha256": sha256_lf(config_path),
        "runner": suite["runner"],
    }
    function = load_runner(suite["root"], suite["runner"])
    signature_errors = check_runner_signature(function)
    if signature_errors:
        raise CiError("; ".join(signature_errors))
    if args.details_output:
        output_dir = Path(args.details_output).parent
    else:
        import tempfile

        output_dir = Path(tempfile.mkdtemp(prefix="semantic-suite-"))
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        result: Any = function(config, args.candidate, output_dir=output_dir)
    except Exception as exc:  # runner contract: an exception is a failed evaluation
        result = {"status": "failed", "errors": [f"runner raised: {exc}"]}
    status, needs_review, errors = normalize_runner_result(result, output_dir=output_dir)
    result_map: Mapping[str, Any] = result if isinstance(result, Mapping) else {}
    details_path = str(result_map.get("details_path") or "")
    details_sha = str(result_map.get("details_sha256") or "")
    if args.details_output:
        target_details = Path(args.details_output)
        source_details: Path | None = None
        try:
            if details_path:
                source = Path(details_path).resolve()
                if source.is_relative_to(output_dir.resolve()) and source.is_file():
                    source_details = source
        except (OSError, ValueError):
            pass  # Already reported as a runner contract error above.
        if source_details is not None:
            if source_details != target_details.resolve():
                target_details.write_bytes(source_details.read_bytes())
        else:
            serialized = json.dumps(result_map, indent=2, sort_keys=True, default=str).encode("utf-8")
            target_details.write_bytes(serialized)
            details_sha = hashlib.sha256(serialized).hexdigest()
        details_path = str(target_details)
    record = build_record(
        candidate=args.candidate,
        workflow_sha=args.workflow_sha,
        run_id=args.run_id,
        kind="semantic",
        status=status,
        config_version=str((config.get("dataset") or {}).get("version", "")),
        reason="; ".join(errors) if status != "passed" else "",
        details_path=details_path,
        details_sha256=details_sha,
        dataset_sha256=str(result_map.get("dataset_sha256") or ""),
        rubric_sha256=str(result_map.get("rubric_sha256") or ""),
        request_count=result_map.get("request_count") if type(result_map.get("request_count")) is int else None,
        candidate_summary=result_map.get("candidate_summary") if isinstance(result_map.get("candidate_summary"), Mapping) else None,
        baseline_summary=result_map.get("baseline_summary") if isinstance(result_map.get("baseline_summary"), Mapping) else None,
        suite=suite_fields,
        needs_review=needs_review,
    )
    Path(args.output).write_text(json.dumps(record, indent=2), encoding="utf-8")
    if status != "passed":
        return emit({"errors": [f"semantic suite {suite['suite_id']} did not pass: {status}"]})
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "check-suite":
        return _command_check_suite(arguments[1:])
    if arguments and arguments[0] == "describe":
        return _command_describe(arguments[1:])
    parser = argparse.ArgumentParser(description="Trusted semantic evaluation")
    parser.add_argument("--registry", default="")
    parser.add_argument("--suite", default="")
    parser.add_argument("--config", default="", help="legacy; accepted only with --not-applicable")
    parser.add_argument("--runner", default="", help="legacy; rejected")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--workflow-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--details-output", default="")
    parser.add_argument("--not-applicable", action="store_true")
    parser.add_argument("--reason", default="")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--approval-evidence", default="")
    args = parser.parse_args(arguments)

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
        if args.runner or not args.suite or not args.registry:
            raise CiError("select a registered suite with --registry and --suite")
        return _run_suite(args)
    except CiError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
