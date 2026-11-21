from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def _load_ci_checks():
    spec = importlib.util.spec_from_file_location(
        "ci_checks_approval_probe",
        SCRIPTS / "ci_checks.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ci_checks = _load_ci_checks()


def test_docs_path_does_not_require_code_approval_or_ai_log():
    result = ci_checks.classify_paths(["docs/ci-gate-positive-note.md"])

    assert result["docs_only"] is True
    assert result["approval_applicable"] is False
    assert result["ai_log_required"] is False
    assert result["code"] == []
    assert result["tests"] == []
    assert result["semantic_required"] is False


def test_script_path_requires_code_approval_and_ai_log():
    result = ci_checks.classify_paths(["scripts/local_analysis_helper.py"])

    assert result["docs_only"] is False
    assert result["approval_applicable"] is True
    assert result["ai_log_required"] is True
    assert result["code"] == ["scripts/local_analysis_helper.py"]
    assert result["tests"] == []
    assert result["semantic_required"] is False
