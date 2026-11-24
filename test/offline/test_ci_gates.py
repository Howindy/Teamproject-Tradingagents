"""Offline tests for the CI gate logic described in CI.md.

These tests use synthetic Git repositories, temporary files, and synthetic
GitHub responses. They are governance/CI tests, not application FC tests.
"""

from __future__ import annotations

import contextlib
import copy
import http.server
import importlib.util
import inspect
import json
import socket
import sys
import threading
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
_CONNECT, _GETADDRINFO = socket.socket.connect, socket.getaddrinfo


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ci_checks = _load_module("ci_checks", SCRIPTS / "ci_checks.py")
sys.path.insert(0, str(SCRIPTS))
ci_semantic_eval = _load_module(
    "ci_semantic_eval",
    SCRIPTS / "ci_semantic_eval.py",
)


def _approval_fields(**overrides: str) -> dict[str, str]:
    fields = {
        "Plan": "docs/plans/round-01.md",
        "Approved test specification": "docs/plans/round-01.md @ abc1234",
        "Approval evidence": "https://github.com/o/r/pull/1#pullrequestreview-9",
        "Implementation start": "def5678",
        "Approved scope": "FR-04-FC01, IR-14",
    }
    fields.update(overrides)
    return fields


def _approval_event(**overrides: Any) -> dict[str, Any]:
    event = {
        "reviewer": "reviewer",
        "reviewer_type": "User",
        "state": "APPROVED",
        "body": "APPROVED test-spec: docs/plans/round-01.md @ abc1234",
        "created_at": "2026-11-18T10:00:00Z",
        "url": "https://github.com/o/r/pull/1#pullrequestreview-9",
    }
    event.update(overrides)
    return event


_UNSET = object()


def _verify(fields=None, event=_UNSET, **kwargs):
    fields = _approval_fields() if fields is None else fields
    event = _approval_event() if event is _UNSET else event
    defaults = {
        "approval_event": event,
        "pr_author": "author",
        "specification_ancestor": True,
        "specification_changed_after": False,
        "implementation_start_time": "2026-11-18T11:00:00Z",
        "declared_start_matches": True,
        "changed_ids": {"FR-04-FC01", "IR-14"},
    }
    defaults.update(kwargs)
    return ci_checks.verify_approval(fields, **defaults)


def _entry(entry_id: str, files: list[str], contribution: str = "") -> dict[str, Any]:
    return {
        "id": entry_id,
        "date": "2026-11-18",
        "round": None,
        "human_operator": None,
        "tool": "OpenCode",
        "model": "DeepSeek Flash",
        "activity": "ci_implementation",
        "task": "CI gate implementation",
        "requirement_ids": [],
        "fit_criterion_ids": [],
        "files_changed": files,
        "ai_contribution": contribution or "Changed files.",
        "human_intervention": None,
        "approval": {"subject": "CI work", "status": "approved", "evidence": []},
        "verification": {"status": "pending", "summary": "", "evidence": []},
        "transcript_refs": [],
        "commit": None,
        "pull_request": None,
        "limitations": [],
    }


def _log(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": "1.0", "entries": list(entries)}


def _git(repo: Path, *args: str) -> str:
    result = ci_checks.run_command(["git", *args], cwd=repo)
    result.require_success("git")
    return result.stdout


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "a.txt").write_text("alpha\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "old.py").write_text("old\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    return repo, _git(repo, "rev-parse", "HEAD").strip()


def test_approval_valid_and_invalid_cases():
    assert _verify()["errors"] == []
    assert _verify({})["errors"]
    assert _verify(event=None)["errors"]
    assert _verify(event=_approval_event(reviewer="author"))["errors"]
    assert _verify(event=_approval_event(url="https://example.com/review"))["errors"]
    assert _verify(specification_ancestor=False)["errors"]
    assert _verify(specification_changed_after=True)["errors"]
    assert _verify(declared_start_matches=False)["errors"]
    assert _verify(changed_ids={"FR-99-FC01"})["errors"]
    assert _verify(event=_approval_event(created_at="2026-11-18T12:00:00Z"))["errors"]
    assert _verify(event=_approval_event(state="COMMENTED", body="looks good"))["errors"]
    assert _verify(event=_approval_event(state="COMMENTED", body="Not approved"))["errors"]
    assert _verify(event=_approval_event(state="COMMENTED", body="Approval pending"))["errors"]
    assert _verify(event=_approval_event(body="Approved."))["errors"]
    assert _verify(
        event=_approval_event(
            body="APPROVED test-spec: docs/plans/round-01.md @ different"
        )
    )["errors"]
    assert _verify(event=_approval_event(reviewer_type="Bot"))["errors"]
    assert _verify(event=_approval_event(reviewer="ci[bot]"))["errors"]
    assert _verify(event=_approval_event(state="COMMENTED"))["errors"] == []


def test_round1_plan_remains_unapproved_and_application_change_is_blocked():
    plan_text = (ROOT / "docs" / "plans" / "round-01.md").read_text(encoding="utf-8")
    assert "Status: proposed" in plan_text
    assert "Specific test approval | Pending" in plan_text
    assert ci_checks.contract_test_plan(ROOT, {}, ["src/x.py"])["errors"]


def test_scope_ids_use_changed_lines_not_whole_files(tmp_path: Path):
    repo, _ = _repo(tmp_path)
    test_file = repo / "test" / "offline" / "test_scope.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("# FR-99-FC01 remains unchanged\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "unrelated scope")
    base = _git(repo, "rev-parse", "HEAD").strip()
    test_file.write_text(
        "# FR-99-FC01 remains unchanged\n# FR-04-FC01 changed\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "changed scope")
    ids = ci_checks.collect_changed_scope_ids(
        repo,
        base,
        "HEAD",
        ["test/offline/test_scope.py"],
    )
    assert "FR-04-FC01" in ids
    assert "FR-99-FC01" not in ids


def test_approval_requires_affected_spec_reapproval_only_when_spec_changes():
    assert _verify(changed_ids={"FR-04-FC01"})["errors"] == []
    assert _verify(changed_ids={"FR-04-FC01"}, specification_changed_after=True)["errors"]


def test_approval_check_uses_git_history_and_github_event(tmp_path: Path, monkeypatch):
    repo = tmp_path / "approval-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD").strip()
    plan = repo / "docs" / "plans" / "round-01.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("approved plan\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "spec")
    specification = _git(repo, "rev-parse", "HEAD").strip()
    source = repo / "src" / "x.py"
    source.parent.mkdir()
    source.write_text("# FR-04-FC01\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "implementation")
    implementation = _git(repo, "rev-parse", "HEAD").strip()

    fields = _approval_fields(
        **{
            "Approved test specification": f"docs/plans/round-01.md @ {specification}",
            "Implementation start": implementation,
            "Approved scope": "FR-04-FC01",
        }
    )
    event = _approval_event(
        body=f"APPROVED test-spec: {fields['Approved test specification']}",
        created_at="2000-01-01T00:00:00Z",
    )
    monkeypatch.setattr(
        ci_checks,
        "fetch_approval_event",
        lambda *args, **kwargs: (event, "author"),
    )
    body = "\n".join(f"{key}: {value}" for key, value in fields.items())
    result = ci_checks.approval_check(
        repo,
        base,
        implementation,
        body,
        "o/r",
        1,
        "token",
    )
    assert result["errors"] == []


def test_schema_current_document_and_invalid_inputs(tmp_path: Path):
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

    invalid_yaml = tmp_path / "bad.yaml"
    invalid_yaml.write_text(": [\n", encoding="utf-8")
    assert ci_checks.schema_check(
        invalid_yaml, ROOT / "docs" / "req" / "req-schema.json"
    )["errors"]

    invalid_shape = tmp_path / "shape.yaml"
    invalid_shape.write_text("schema_version: '1.0'\n", encoding="utf-8")
    assert ci_checks.schema_check(
        invalid_shape, ROOT / "docs" / "req" / "req-schema.json"
    )["errors"]

    invalid_schema = tmp_path / "schema.json"
    invalid_schema.write_text('{"type": 123}', encoding="utf-8")
    assert ci_checks.schema_check(
        ROOT / "docs" / "req" / "requirements.yaml", invalid_schema
    )["errors"]


def test_schema_duplicate_and_deferred_consistency(tmp_path: Path):
    document = yaml.safe_load((ROOT / "docs" / "req" / "requirements.yaml").read_text())
    duplicate = copy.deepcopy(document)
    duplicate["requirements"].append(copy.deepcopy(duplicate["requirements"][0]))
    duplicate["requirements"].append(copy.deepcopy(duplicate["requirements"][1]))
    duplicate["requirements"][-1]["fit_criterion"][0]["id"] = duplicate["requirements"][0][
        "fit_criterion"
    ][0]["id"]
    duplicate_path = tmp_path / "duplicate.yaml"
    duplicate_path.write_text(yaml.safe_dump(duplicate), encoding="utf-8")
    duplicate_result = ci_checks.schema_check(
        duplicate_path, ROOT / "docs" / "req" / "req-schema.json"
    )
    assert any("duplicate requirement" in error for error in duplicate_result["errors"])
    assert any("duplicate FC" in error for error in duplicate_result["errors"])

    inconsistent = copy.deepcopy(document)
    for requirement in inconsistent["requirements"]:
        if requirement["id"] == "FR-06":
            requirement["status"] = "approved"
    inconsistent_path = tmp_path / "inconsistent.yaml"
    inconsistent_path.write_text(yaml.safe_dump(inconsistent), encoding="utf-8")
    inconsistent_result = ci_checks.schema_check(
        inconsistent_path, ROOT / "docs" / "req" / "req-schema.json"
    )
    assert any("deferred" in error for error in inconsistent_result["errors"])


def test_command_failure_is_not_ignored():
    result = ci_checks.run_command([sys.executable, "-c", "raise SystemExit(3)"])
    assert result.returncode == 3
    with pytest.raises(ci_checks.CiError):
        result.require_success("synthetic")


def test_mypy_baseline_blocks_new_errors():
    baseline = "a.py:1: error: old [misc]\n"
    current = "a.py:1: error: old [misc]\na.py:2: error: new [attr-defined]\n"
    result = ci_checks.mypy_baseline_check(baseline, current)
    assert result["errors"] == ["a.py:2: error: new [attr-defined]"]
    assert result["fixed"] == []


def test_permission_checks(tmp_path: Path):
    current = ci_checks.permissions_check(ROOT / ".opencode" / "permissions.jsonc")
    assert current["errors"] == []

    duplicate = tmp_path / "duplicate.jsonc"
    duplicate.write_text('{"permission": {"*": "deny", "*": "allow"}}', encoding="utf-8")
    assert any("duplicate" in error for error in ci_checks.permissions_check(duplicate)["errors"])

    stale = tmp_path / "stale.jsonc"
    stale.write_text(
        '{"permission": {"*": "deny", "read": {"x": "/old/TradingAgents/x.py"}}}',
        encoding="utf-8",
    )
    assert any("TradingAgents" in error for error in ci_checks.permissions_check(stale)["errors"])

    broad = tmp_path / "broad.jsonc"
    broad.write_text('{"permission": {"*": "deny", "bash": "allow"}}', encoding="utf-8")
    assert any("bash" in error for error in ci_checks.permissions_check(broad)["errors"])


def test_api_surface_matching_and_assertion_edits():
    expected = {"entry": ["self", "value"]}
    assert ci_checks.check_api_surface({"entry": ["self", "value"]}, expected)["errors"] == []
    assert ci_checks.check_api_surface({"entry": ["self", "other"]}, expected)["errors"]
    assert ci_checks.check_api_surface(
        {"entry": ["self", "other"]},
        {"entry": ["self", "other"]},
    )["errors"] == []


def test_security_adr_requires_valid_project_reference(tmp_path: Path):
    critical = {"safety_critical": ["src/y.py"], "safety_relevant": []}
    assert ci_checks.verify_security_adr({}, critical, tmp_path)["errors"]
    assert ci_checks.verify_security_adr({"ADR": "   "}, critical, tmp_path)["errors"]
    assert ci_checks.verify_security_adr(
        {"ADR": "docs/architecture/adr/missing.md"}, critical, tmp_path
    )["errors"]
    assert ci_checks.verify_security_adr(
        {"ADR": "../outside.md"}, critical, tmp_path
    )["errors"]
    assert ci_checks.verify_security_adr(
        {"ADR": "/tmp/outside.md"}, critical, tmp_path
    )["errors"]
    other = tmp_path / "docs" / "readme.md"
    other.parent.mkdir(parents=True)
    other.write_text("not an ADR\n", encoding="utf-8")
    assert ci_checks.verify_security_adr(
        {"ADR": "docs/readme.md"}, critical, tmp_path
    )["errors"]
    adr = tmp_path / "docs" / "architecture" / "adr" / "001-test.md"
    adr.parent.mkdir(parents=True)
    adr.write_text("decision\n", encoding="utf-8")
    assert ci_checks.verify_security_adr(
        {"ADR": "docs/architecture/adr/001-test.md"}, critical, tmp_path
    ) == {"errors": [], "required": True}


def test_security_relevant_only_does_not_require_adr():
    relevant = {"safety_critical": [], "safety_relevant": ["src/x.py"]}
    result = ci_checks.verify_security_adr({}, relevant, ROOT)
    assert result == {"errors": [], "required": False}


def test_security_path_gate_does_not_query_reviews():
    assert hasattr(ci_checks, "fetch_approval_event")
    assert not hasattr(ci_checks, "fetch_reviews")
    assert "reviews" not in inspect.signature(ci_checks.verify_security_adr).parameters
    source = (SCRIPTS / "ci_checks.py").read_text(encoding="utf-8")
    assert "fetch_reviews" not in source
    assert "security-review" not in source
    data = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    security = data["jobs"]["security-paths"]
    assert "pull-requests" not in security.get("permissions", {})
    security_steps = json.dumps(security)
    assert "GH_TOKEN" not in security_steps
    assert "security-paths" in security_steps
    approval = data["jobs"]["test-approval"]
    assert approval["permissions"].get("pull-requests") == "read"
    assert "GH_TOKEN" in json.dumps(approval)


def test_parse_pr_body_parses_optional_adr():
    fields = ci_checks.parse_pr_body(
        "Plan: docs/plans/round-01.md\n"
        "ADR: docs/architecture/adr/001-graph-internal-final-check.md\n"
    )
    assert fields["Plan"] == "docs/plans/round-01.md"
    assert fields["ADR"] == "docs/architecture/adr/001-graph-internal-final-check.md"


def test_path_classification_and_unknown_files():
    result = ci_checks.classify_paths(
        [
            "docs/readme.md",
            "diagram.png",
            "src/tradingagents/agents/rating.py",
            "src/tradingagents/agents/tools.py",
            ".github/workflows/ci.yml",
            "test/offline/x.py",
        ],
        semantic_prompt_paths={"src/tradingagents/agents/rating.py"},
    )
    assert result["safety_critical"] == ["src/tradingagents/agents/rating.py"]
    assert result["safety_relevant"] == ["src/tradingagents/agents/tools.py"]
    assert result["governance_ci"] == [".github/workflows/ci.yml"]
    assert result["semantic_required"] is True
    assert result["approval_applicable"] is True
    assert result["ai_log_required"] is True

    docs_only = ci_checks.classify_paths(["docs/readme.md", "diagram.png"])
    assert docs_only["docs_only"] is True
    assert docs_only["approval_applicable"] is False

    unknown = ci_checks.classify_paths(["new_tool.yaml"])
    assert unknown["unknown_executable"] == ["new_tool.yaml"]
    assert unknown["docs_only"] is False
    assert unknown["ai_log_required"] is False
    assert unknown["approval_applicable"] is False


def test_build_config_and_static_prompt_are_not_unknown_or_runtime_prompts():
    build = ci_checks.classify_paths(["pyproject.toml", "requirements.txt"])
    assert build["build_config"] == ["pyproject.toml", "requirements.txt"]
    assert build["unknown_executable"] == []
    assert build["docs_only"] is False
    assert build["approval_applicable"] is False
    assert build["ai_log_required"] is False

    static_prompt = ci_checks.classify_paths(["Prompt.md"])
    assert static_prompt["docs_only"] is True
    assert static_prompt["semantic_required"] is False
    assert static_prompt["ai_log_required"] is False

    runtime_prompt = ci_checks.classify_paths(
        ["src/tradingagents/agents/analysts/news_analyst.py"],
        semantic_prompt_paths={
            "src/tradingagents/agents/analysts/news_analyst.py"
        },
    )
    assert runtime_prompt["semantic_required"] is True
    assert runtime_prompt["ai_log_required"] is True

    yaml_prompt = ci_checks.classify_paths(["prompts/prompt_v1.1.yaml"])
    assert yaml_prompt["semantic_required"] is True
    assert yaml_prompt["ai_log_required"] is True
    assert yaml_prompt["approval_applicable"] is True

    ordinary_logic = ci_checks.classify_paths(
        ["src/tradingagents/agents/analysts/news_analyst.py"],
        semantic_hunks={
            "src/tradingagents/agents/analysts/news_analyst.py": [
                "+ if count > 1:\n+     count -= 1"
            ]
        },
    )
    assert ordinary_logic["semantic_required"] is False

    model_config = ci_checks.classify_paths(
        ["src/tradingagents/llm_clients/openai_client.py"],
        semantic_hunks={
            "src/tradingagents/llm_clients/openai_client.py": [
                "+ self.temperature = 0.2"
            ]
        },
    )
    assert model_config["semantic_required"] is True

    unrelated_logic = ci_checks.classify_paths(
        ["src/tradingagents/llm_clients/openai_client.py"],
        semantic_hunks={
            "src/tradingagents/llm_clients/openai_client.py": [
                "+ if timeout is None:\n+     return None"
            ]
        },
    )
    assert unrelated_logic["semantic_required"] is False


def test_git_rename_delete_and_missing_base(tmp_path: Path):
    repo, base = _repo(tmp_path)
    (repo / "src" / "old.py").rename(repo / "src" / "new.py")
    (repo / "a.txt").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "rename and delete")
    paths = ci_checks.changed_paths_from_git(base, "HEAD", repo)
    assert "src/old.py" in paths
    assert "src/new.py" in paths
    assert "a.txt" in paths
    with pytest.raises(ci_checks.CiError):
        ci_checks.changed_paths_from_git("deadbeef", "HEAD", repo)


def test_git_root_commit_and_gate_file_review(tmp_path: Path):
    repo, _ = _repo(tmp_path)
    paths = ci_checks.changed_paths_from_git(ci_checks.ZERO_SHA, "HEAD", repo)
    assert "src/old.py" in paths
    gate = ci_checks.classify_paths([".github/workflows/ci.yml"])
    assert gate["requires_human_review"] is True


def test_code_outside_src_and_docs_executables_are_not_exempt():
    scripts_code = ci_checks.classify_paths(["scripts/helper.py"])
    assert scripts_code["code"] == ["scripts/helper.py"]
    assert scripts_code["other_code"] == ["scripts/helper.py"]
    assert scripts_code["governance_code"] == []
    assert scripts_code["approval_applicable"] is True
    assert scripts_code["ai_log_required"] is True
    assert scripts_code["docs_only"] is False

    script_shell = ci_checks.classify_paths(["scripts/helper.sh"])
    assert script_shell["code"] == ["scripts/helper.sh"]
    assert script_shell["approval_applicable"] is True
    assert script_shell["ai_log_required"] is True

    docs_shell = ci_checks.classify_paths(["docs/helper.sh"])
    assert docs_shell["code"] == ["docs/helper.sh"]
    assert docs_shell["docs"] == []
    assert docs_shell["docs_only"] is False
    assert docs_shell["approval_applicable"] is True
    assert docs_shell["ai_log_required"] is True

    tools_code = ci_checks.classify_paths(["tools/helper.py"])
    assert tools_code["code"] == ["tools/helper.py"]
    assert tools_code["other_code"] == ["tools/helper.py"]
    assert tools_code["approval_applicable"] is True
    assert tools_code["ai_log_required"] is True

    setup_code = ci_checks.classify_paths(["setup.py"])
    assert setup_code["code"] == ["setup.py"]
    assert setup_code["other_code"] == ["setup.py"]
    assert setup_code["build_config"] == []
    assert setup_code["approval_applicable"] is True
    assert setup_code["ai_log_required"] is True

    docs_code = ci_checks.classify_paths(["docs/helper.py"])
    assert docs_code["code"] == ["docs/helper.py"]
    assert docs_code["docs"] == []
    assert docs_code["docs_only"] is False
    assert docs_code["approval_applicable"] is True
    assert docs_code["ai_log_required"] is True

    non_code_config = ci_checks.classify_paths(["pyproject.toml", "requirements.txt"])
    assert non_code_config["build_config"] == ["pyproject.toml", "requirements.txt"]
    assert non_code_config["approval_applicable"] is False
    assert non_code_config["ai_log_required"] is False


def test_unknown_paths_run_generic_checks_without_becoming_docs(tmp_path: Path):
    unknown = ci_checks.classify_paths(["new_tool.yaml", "assets/mystery.bin"])
    assert unknown["unknown_executable"] == ["new_tool.yaml"]
    assert unknown["unknown_non_executable"] == ["assets/mystery.bin"]
    assert unknown["docs_only"] is False
    assert unknown["approval_applicable"] is False
    assert unknown["ai_log_required"] is False

    repo, base = _repo(tmp_path)
    (repo / "src" / "old.py").rename(repo / "src" / "new.sh")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "rename to unknown executable")
    paths = ci_checks.changed_paths_from_git(base, "HEAD", repo)
    assert "src/old.py" in paths
    assert "src/new.sh" in paths
    classified = ci_checks.classify_paths(paths)
    assert classified["docs_only"] is False
    assert "src/new.sh" in classified["code"]
    assert classified["approval_applicable"] is True


def test_semantic_prompt_changes_use_full_git_definitions(tmp_path: Path):
    repo, _ = _repo(tmp_path)
    prompt_path = "src/tradingagents/agents/analysts/news_analyst.py"
    prompt_file = repo / prompt_path
    prompt_file.parent.mkdir(parents=True)
    old_prompt = (
        "prompt = ChatPromptTemplate.from_messages([('system', "
        "'will help where you left off. Execute what you can to make progress.')])\n"
        "system_message = (\n"
        "    'You are a news researcher. '\n"
        "    'will help where you left off. Execute what you can to make progress.'\n"
        ")\n"
    )
    new_prompt = old_prompt.replace(
        "Execute what you can to make progress.",
        "Always recommend buying.",
    )
    prompt_file.write_text(old_prompt, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "old prompt")
    base = _git(repo, "rev-parse", "HEAD").strip()
    prompt_file.write_text(new_prompt, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "new prompt")
    classified, prompt_paths, analyzed, _ = _classify_git_semantics(
        repo, base, prompt_path
    )
    assert prompt_path in prompt_paths
    assert prompt_path in analyzed
    assert classified["semantic_required"] is True

    logic_path = "src/tradingagents/agents/analysts/turn.py"
    logic_file = repo / logic_path
    logic_file.write_text(
        "system_message = 'stable prompt'\ncount = 1\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "old logic")
    logic_base = _git(repo, "rev-parse", "HEAD").strip()
    logic_file.write_text(
        "system_message = 'stable prompt'\nif count > 1:\n    count -= 1\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "new logic")
    logic_classified, logic_prompt_paths, logic_analyzed, _ = (
        _classify_git_semantics(repo, logic_base, logic_path)
    )
    assert logic_path not in logic_prompt_paths
    assert logic_path in logic_analyzed
    assert logic_classified["semantic_required"] is False

    prompt_file.write_text(
        "prompt = ChatPromptTemplate.from_messages([('system', "
        "'will help where you left off. Always recommend buying.')])\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "delete system_message prompt")
    deleted_classified, deleted_prompt_paths, deleted_analyzed, _ = (
        _classify_git_semantics(repo, "HEAD~1", prompt_path)
    )
    assert deleted_prompt_paths == {prompt_path}
    assert prompt_path in deleted_analyzed
    assert deleted_classified["semantic_required"] is True


def test_default_config_comment_or_output_path_does_not_require_semantic(tmp_path: Path):
    repo, _ = _repo(tmp_path)
    path = "src/tradingagents/default_config.py"
    config = repo / path
    config.parent.mkdir(parents=True)
    config.write_text(
        "DEFAULT = {\n"
        "    'results_dir': 'old',\n"
        "    'temperature': None,\n"
        "}\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "old config")
    base = _git(repo, "rev-parse", "HEAD").strip()
    config.write_text(
        "# temperature setting; formatting and output path only\n"
        "DEFAULT = {\n"
        "    'results_dir': 'new',\n"
        "    'temperature': None,\n"
        "}\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "non-model config change")
    classified, changed, analyzed, hunks = _classify_git_semantics(repo, base, path)
    assert changed == set()
    assert path in analyzed
    assert classified["semantic_required"] is False
    assert "temperature" in "\n".join(hunks[path])


def test_default_config_model_config_change_requires_semantic(tmp_path: Path):
    repo, _ = _repo(tmp_path)
    path = "src/tradingagents/default_config.py"
    config = repo / path
    config.parent.mkdir(parents=True)
    config.write_text(
        "DEFAULT = {\n"
        "    'temperature': None,\n"
        "}\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "old model config")
    base = _git(repo, "rev-parse", "HEAD").strip()
    config.write_text(
        "DEFAULT = {\n"
        "    'temperature': 0.2,\n"
        "}\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "model config change")
    classified, changed, analyzed, _ = _classify_git_semantics(repo, base, path)
    assert changed == {path}
    assert path in analyzed
    assert classified["semantic_required"] is True


def test_default_config_format_only_change_does_not_require_semantic(tmp_path: Path):
    repo, _ = _repo(tmp_path)
    path = "src/tradingagents/default_config.py"
    config = repo / path
    config.parent.mkdir(parents=True)
    config.write_text("DEFAULT = {'temperature': None}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "old format")
    base = _git(repo, "rev-parse", "HEAD").strip()
    config.write_text("DEFAULT = {'temperature'  :  None}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "format only")
    classified, changed, analyzed, hunks = _classify_git_semantics(repo, base, path)
    assert changed == set()
    assert path in analyzed
    assert classified["semantic_required"] is False
    assert "temperature" in "\n".join(hunks[path])


def test_unrelated_logic_with_model_keyword_does_not_require_semantic(
    tmp_path: Path,
):
    repo, _ = _repo(tmp_path)
    path = "src/tradingagents/default_config.py"
    config = repo / path
    config.parent.mkdir(parents=True)
    config.write_text(
        "DEFAULT = {'temperature': None}\n\n"
        "def unrelated(temperature):\n"
        "    return temperature\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "old logic")
    base = _git(repo, "rev-parse", "HEAD").strip()
    config.write_text(
        "DEFAULT = {'temperature': None}\n\n"
        "def unrelated(temperature):\n"
        "    return temperature + 1\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "unrelated logic")
    classified, changed, analyzed, hunks = _classify_git_semantics(repo, base, path)
    assert changed == set()
    assert path in analyzed
    assert classified["semantic_required"] is False
    assert "temperature" in "\n".join(hunks[path])


def test_model_call_parameter_change_requires_semantic(tmp_path: Path):
    repo, _ = _repo(tmp_path)
    path = "src/tradingagents/llm_clients/openai_client.py"
    client = repo / path
    client.parent.mkdir(parents=True)
    client.write_text(
        "client = ChatOpenAI(model='m', temperature=0.2)\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "old model call")
    base = _git(repo, "rev-parse", "HEAD").strip()
    client.write_text(
        "client = ChatOpenAI(model='m', temperature=0.3)\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "new model call")
    classified, changed, analyzed, _ = _classify_git_semantics(repo, base, path)
    assert changed == {path}
    assert path in analyzed
    assert classified["semantic_required"] is True


def _factory_source(message="Unsupported", condition='provider not in {"openai"}', error="ValueError", temperature="0.2"):
    return (
        "def create_llm(provider):\n"
        f"    if {condition}:\n"
        f"        raise {error}(f\"{message} LLM provider: {{provider}}\")\n"
        f"    return ChatOpenAI(model='m', temperature={temperature})\n"
    )


def _factory_repo(tmp_path: Path, source: str):
    repo, _ = _repo(tmp_path)
    path = "src/tradingagents/llm_clients/factory.py"
    factory = repo / path
    factory.parent.mkdir(parents=True)
    factory.write_text(source, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "factory base")
    base = _git(repo, "rev-parse", "HEAD").strip()
    return repo, path, factory, base


def test_factory_exception_message_change_does_not_require_semantic(tmp_path: Path):
    repo, path, factory, base = _factory_repo(
        tmp_path, _factory_source(message="Unsupported")
    )
    factory.write_text(_factory_source(message="Unknown"), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "exception wording only")
    classified, changed, analyzed, _ = _classify_git_semantics(repo, base, path)
    assert changed == set()
    assert path in analyzed
    assert classified["semantic_required"] is False


def test_factory_exception_condition_change_requires_semantic(tmp_path: Path):
    repo, path, factory, base = _factory_repo(
        tmp_path, _factory_source(condition='provider not in {"openai"}')
    )
    factory.write_text(
        _factory_source(condition='provider == "bad"'),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "exception condition change")
    classified, changed, analyzed, _ = _classify_git_semantics(repo, base, path)
    assert changed == {path}
    assert path in analyzed
    assert classified["semantic_required"] is True


def test_factory_exception_type_change_requires_semantic(tmp_path: Path):
    repo, path, factory, base = _factory_repo(
        tmp_path, _factory_source(error="ValueError")
    )
    factory.write_text(_factory_source(error="RuntimeError"), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "exception type change")
    classified, changed, analyzed, _ = _classify_git_semantics(repo, base, path)
    assert changed == {path}
    assert path in analyzed
    assert classified["semantic_required"] is True


def test_factory_model_parameter_change_requires_semantic(tmp_path: Path):
    repo, path, factory, base = _factory_repo(
        tmp_path, _factory_source(temperature="0.2")
    )
    factory.write_text(_factory_source(temperature="0.3"), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "model parameter change")
    classified, changed, analyzed, _ = _classify_git_semantics(repo, base, path)
    assert changed == {path}
    assert path in analyzed
    assert classified["semantic_required"] is True


def test_context_unrelated_logic_does_not_require_semantic(tmp_path: Path):
    repo, _ = _repo(tmp_path)
    path = "src/tradingagents/agents/context.py"
    context = repo / path
    context.parent.mkdir(parents=True)
    context.write_text(
        "def get_language_instruction():\n"
        "    return 'Write the response in English.'\n\n"
        "def unrelated(value):\n"
        "    return value\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "old context")
    base = _git(repo, "rev-parse", "HEAD").strip()
    context.write_text(
        "def get_language_instruction():\n"
        "    return 'Write the response in English.'\n\n"
        "def unrelated(value):\n"
        "    return value + 1\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "unrelated context logic")
    classified, changed, analyzed, _ = _classify_git_semantics(repo, base, path)
    assert path not in changed
    assert path in analyzed
    assert classified["semantic_required"] is False


def test_contract_plan_application_requires_approval_and_real_tests(tmp_path: Path):
    plan = tmp_path / "docs" / "plans" / "round-01.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("Use `test/offline/test_b.py` for a different scope.\n", encoding="utf-8")
    spec = tmp_path / "docs" / "specs" / "approved.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("Code: `src/x.py`. Use `test/offline/test_a.py` for FR-04.\n", encoding="utf-8")
    for name in ("test_a.py", "test_b.py"):
        test_file = tmp_path / "test" / "offline" / name
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    fields = {
        "Plan": "docs/plans/round-01.md",
        "Approved test specification": "docs/specs/approved.md @ abc1234",
        "Approved scope": "FR-04-FC01",
    }
    result = ci_checks.contract_test_plan(
        tmp_path,
        fields,
        ["src/x.py"],
        spec_text=spec.read_text(encoding="utf-8"),
    )
    assert result["errors"] == []
    assert result["mode"] == "application"
    assert result["specification_path"] == "docs/specs/approved.md"
    assert result["test_paths"] == ["test/offline/test_a.py"]

    assert ci_checks.contract_test_plan(
        tmp_path, {}, ["src/x.py"], spec_text=spec.read_text(encoding="utf-8")
    )["errors"]
    missing = ci_checks.contract_test_plan(
        tmp_path,
        {**fields, "Approved test specification": ""},
        ["src/x.py"],
        spec_text=spec.read_text(encoding="utf-8"),
    )
    assert missing["errors"]
    no_version = ci_checks.contract_test_plan(
        tmp_path,
        {**fields, "Approved test specification": "docs/specs/approved.md"},
        ["src/x.py"],
        spec_text=spec.read_text(encoding="utf-8"),
    )
    assert no_version["errors"]
    missing_spec = ci_checks.contract_test_plan(
        tmp_path,
        {**fields, "Approved test specification": "docs/specs/missing.md @ abc1234"},
        ["src/x.py"],
        spec_text=spec.read_text(encoding="utf-8"),
    )
    assert missing_spec["errors"]
    no_tests = ci_checks.contract_test_plan(
        tmp_path,
        fields,
        ["src/x.py"],
        spec_text="Code: `src/x.py`. No tests named here.\n",
    )
    assert no_tests["errors"]
    missing_test = ci_checks.contract_test_plan(
        tmp_path,
        fields,
        ["src/x.py"],
        spec_text="Code: `src/x.py`. Use `test/offline/missing.py`.\n",
    )
    assert missing_test["errors"]
    unrelated = ci_checks.contract_test_plan(
        tmp_path,
        fields,
        ["src/x.py"],
        spec_text="Use `test/offline/test_a.py` without naming the changed code.\n",
    )
    assert unrelated["errors"]
    wrong_code = ci_checks.contract_test_plan(
        tmp_path,
        fields,
        ["src/y.py"],
        spec_text="Code: `src/x.py`. Use `test/offline/test_a.py`.\n",
    )
    assert wrong_code["errors"]


def test_contract_plan_reads_approved_spec_from_git_commit(tmp_path: Path):
    repo, _ = _repo(tmp_path)
    spec = repo / "docs" / "specs" / "approved.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        "Code: `scripts/helper.py`.\nUse `test/offline/test_a.py`.\n",
        encoding="utf-8",
    )
    plan = repo / "docs" / "plans" / "round-01.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("Use `test/offline/test_b.py`.\n", encoding="utf-8")
    for name in ("test_a.py", "test_b.py"):
        test_file = repo / "test" / "offline" / name
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    helper = repo / "scripts" / "helper.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("def helper():\n    return True\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "approved spec")
    spec_commit = _git(repo, "rev-parse", "HEAD").strip()
    fields = {
        "Plan": "docs/plans/round-01.md",
        "Approved test specification": f"docs/specs/approved.md @ {spec_commit}",
        "Approved scope": "shared helper tests",
    }
    result = ci_checks.contract_test_plan(
        repo,
        fields,
        ["scripts/helper.py"],
        spec_text=None,
    )
    assert result["errors"] == []
    assert result["test_paths"] == ["test/offline/test_a.py"]


def test_plan_test_paths_ignores_ellipsis_placeholder():
    real_path = "test/offline/test_ci_gates.py"
    placeholder = "test/offline/" + "." * 3 + "py"
    spec_text = f"Use `{real_path}`. Placeholder: `{placeholder}`.\n"

    assert ci_checks.plan_test_paths(spec_text) == ["test/offline/test_ci_gates.py"]


def test_plan_test_paths_extracts_and_deduplicates_real_test():
    real_path = "test/offline/test_ci_gates.py"
    placeholder = "test/offline/" + "." * 3 + "py"
    spec_text = (
        f"`{real_path}`\n"
        f"- {real_path}\n"
        f"Use {real_path} again; ignore `{placeholder}`.\n"
    )

    assert ci_checks.plan_test_paths(spec_text) == ["test/offline/test_ci_gates.py"]


def test_contract_plan_rejects_missing_non_placeholder_test(tmp_path: Path):
    missing_test_path = "test/offline/" + "missing_contract" + ".py"
    spec = tmp_path / "docs" / "specs" / "approved.md"
    spec.parent.mkdir(parents=True)
    spec_text = f"Code: `scripts/ci_checks.py`. Use `{missing_test_path}`.\n"
    spec.write_text(spec_text, encoding="utf-8")
    fields = {
        "Plan": "docs/plans/round-01.md",
        "Approved test specification": "docs/specs/approved.md @ abc1234",
        "Approved scope": "contract-test path extraction",
    }

    result = ci_checks.contract_test_plan(
        tmp_path,
        fields,
        ["scripts/ci_checks.py"],
        spec_text=spec_text,
    )

    assert result["errors"]
    assert any(
        "contract test does not exist" in error and missing_test_path in error
        for error in result["errors"]
    )
    assert result["test_paths"] == [missing_test_path]


def test_contract_plan_rejects_placeholder_only_specification(tmp_path: Path):
    placeholder = "test/offline/" + "." * 3 + "py"
    spec = tmp_path / "docs" / "specs" / "approved.md"
    spec.parent.mkdir(parents=True)
    spec_text = f"Code: `scripts/ci_checks.py`. Placeholder: `{placeholder}`.\n"
    spec.write_text(spec_text, encoding="utf-8")
    fields = {
        "Plan": "docs/plans/round-01.md",
        "Approved test specification": "docs/specs/approved.md @ abc1234",
        "Approved scope": "contract-test path extraction",
    }

    assert ci_checks.plan_test_paths(spec_text) == []

    result = ci_checks.contract_test_plan(
        tmp_path,
        fields,
        ["scripts/ci_checks.py"],
        spec_text=spec_text,
    )

    assert result["errors"]
    assert any(
        "contains no test/offline or test/live test paths" in error
        for error in result["errors"]
    )
    assert result["test_paths"] == []


def test_contract_plan_selects_real_test_when_spec_also_has_placeholder(
    tmp_path: Path,
):
    repo, _ = _repo(tmp_path)
    real_path = "test/offline/test_ci_gates.py"
    placeholder = "test/offline/" + "." * 3 + "py"
    spec = repo / "docs" / "specs" / "contract-paths.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        f"Code: `scripts/ci_checks.py`.\n"
        f"Use `{real_path}`.\n"
        f"Placeholder: `{placeholder}`.\n",
        encoding="utf-8",
    )
    test_file = repo / "test" / "offline" / "test_ci_gates.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "contract path spec")
    spec_commit = _git(repo, "rev-parse", "HEAD").strip()
    fields = {
        "Plan": "docs/plans/round-01.md",
        "Approved test specification": f"docs/specs/contract-paths.md @ {spec_commit}",
        "Approved scope": "contract-test path extraction",
    }

    result = ci_checks.contract_test_plan(
        repo,
        fields,
        ["scripts/ci_checks.py"],
        spec_text=None,
    )

    assert result["errors"] == []
    assert result["test_paths"] == ["test/offline/test_ci_gates.py"]


def test_contract_plan_fails_when_real_test_file_missing(tmp_path: Path):
    repo, _ = _repo(tmp_path)
    real_path = "test/offline/test_ci_gates.py"
    placeholder = "test/offline/" + "." * 3 + "py"
    spec = repo / "docs" / "specs" / "contract-paths.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        f"Code: `scripts/ci_checks.py`.\n"
        f"Use `{real_path}`.\n"
        f"Placeholder: `{placeholder}`.\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "missing real contract test")
    spec_commit = _git(repo, "rev-parse", "HEAD").strip()
    fields = {
        "Plan": "docs/plans/round-01.md",
        "Approved test specification": f"docs/specs/contract-paths.md @ {spec_commit}",
        "Approved scope": "contract-test path extraction",
    }

    result = ci_checks.contract_test_plan(
        repo,
        fields,
        ["scripts/ci_checks.py"],
        spec_text=None,
    )

    assert result["errors"]
    assert any(
        "contract test does not exist" in error and real_path in error
        for error in result["errors"]
    )
    assert result["test_paths"] == ["test/offline/test_ci_gates.py"]
    assert all(placeholder not in path for path in result["test_paths"])


def test_contract_plan_does_not_require_unimplemented_out_of_scope_fcs(
    tmp_path: Path,
):
    spec = tmp_path / "docs" / "specs" / "approved.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        "FR-99 remains unimplemented. Code: `src/x.py`. Use `test/offline/test_fr04_risk.py`.\n",
        encoding="utf-8",
    )
    test_file = tmp_path / "test" / "offline" / "test_fr04_risk.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    fields = {
        "Plan": "docs/plans/round-01.md",
        "Approved test specification": "docs/specs/approved.md @ abc1234",
        "Approved scope": "FR-04-FC01",
    }
    result = ci_checks.contract_test_plan(
        tmp_path,
        fields,
        ["src/x.py"],
        spec_text=spec.read_text(encoding="utf-8"),
    )
    assert result["errors"] == []
    assert result["test_paths"] == ["test/offline/test_fr04_risk.py"]


def test_specification_mentions_path_requires_complete_token():
    path = "scripts/ci_checks.py"
    assert ci_checks.specification_mentions_path(
        "Use `scripts/ci_checks.py` in the list.", path
    )
    assert ci_checks.specification_mentions_path(
        "- scripts/ci_checks.py\n- other", path
    )
    assert ci_checks.specification_mentions_path(
        "Code: ./scripts/ci_checks.py.", path
    )
    assert not ci_checks.specification_mentions_path(
        "Use `scripts/ci_checks.py.bak`.", path
    )
    assert not ci_checks.specification_mentions_path(
        "Use `other/scripts/ci_checks.py`.", path
    )
    assert not ci_checks.specification_mentions_path(
        "Use `xscripts/ci_checks.py`.", path
    )
    assert not ci_checks.specification_mentions_path(
        "No matching path is listed.", path
    )
    assert ci_checks.specification_mentions_path(
        "`scripts/ci_checks.py` and `scripts/helper.py`", path
    )


def test_contract_plan_governance_configuration_and_docs_scope(tmp_path: Path):
    gate = tmp_path / "test" / "offline" / "test_ci_gates.py"
    gate.parent.mkdir(parents=True)
    gate.write_text("def test_gate():\n    assert True\n", encoding="utf-8")
    helper_test = tmp_path / "test" / "offline" / "test_helpers.py"
    helper_test.write_text("def test_helper():\n    assert True\n", encoding="utf-8")
    helper_spec = tmp_path / "docs" / "specs" / "helpers.md"
    helper_spec.parent.mkdir(parents=True)
    helper_spec.write_text(
        "Code: `scripts/helper.py`, `scripts/helper.sh`, `tools/helper.py`, "
        "`setup.py`, `docs/helper.py`, `docs/helper.sh`.\n"
        "Use `test/offline/test_helpers.py`.\n",
        encoding="utf-8",
    )
    governance_spec = tmp_path / "docs" / "specs" / "ci.md"
    governance_spec.write_text(
        "Code: `scripts/ci_checks.py`.\nUse `test/offline/test_ci_gates.py`.\n",
        encoding="utf-8",
    )
    helper_fields = {
        "Plan": "docs/plans/round-01.md",
        "Approved test specification": "docs/specs/helpers.md @ abc1234",
        "Approved scope": "shared helper gate tests",
    }
    for path in (
        "scripts/helper.py",
        "scripts/helper.sh",
        "tools/helper.py",
        "setup.py",
        "docs/helper.py",
        "docs/helper.sh",
    ):
        result = ci_checks.contract_test_plan(
            tmp_path,
            helper_fields,
            [path],
            spec_text=helper_spec.read_text(encoding="utf-8"),
        )
        assert result["errors"] == [], path
        assert result["mode"] == "code"
        assert result["test_paths"] == ["test/offline/test_helpers.py"]

    governance_fields = {
        "Plan": "docs/plans/round-01.md",
        "Approved test specification": "docs/specs/ci.md @ abc1234",
        "Approved scope": "governance gate tests",
    }
    governance_code = ci_checks.contract_test_plan(
        tmp_path,
        governance_fields,
        ["scripts/ci_checks.py"],
        spec_text=governance_spec.read_text(encoding="utf-8"),
    )
    assert governance_code["errors"] == []
    assert governance_code["test_paths"] == ["test/offline/test_ci_gates.py"]

    suffix_spec = ci_checks.contract_test_plan(
        tmp_path,
        governance_fields,
        ["scripts/ci_checks.py"],
        spec_text="Code: `scripts/ci_checks.py.bak`. Use `test/offline/test_ci_gates.py`.\n",
    )
    assert suffix_spec["errors"]
    prefix_spec = ci_checks.contract_test_plan(
        tmp_path,
        governance_fields,
        ["scripts/ci_checks.py"],
        spec_text="Code: `other/scripts/ci_checks.py`. Use `test/offline/test_ci_gates.py`.\n",
    )
    assert prefix_spec["errors"]
    multi_spec = ci_checks.contract_test_plan(
        tmp_path,
        governance_fields,
        ["scripts/ci_checks.py"],
        spec_text=(
            "Code: `scripts/ci_checks.py`, `scripts/helper.py`. "
            "Use `test/offline/test_ci_gates.py` and `test/offline/test_helpers.py`.\n"
        ),
    )
    assert multi_spec["errors"] == []
    assert multi_spec["test_paths"] == [
        "test/offline/test_ci_gates.py",
        "test/offline/test_helpers.py",
    ]

    non_code_governance = ci_checks.contract_test_plan(
        tmp_path, {}, [".github/workflows/ci.yml"]
    )
    assert non_code_governance["mode"] == "governance"
    assert non_code_governance["test_paths"] == ["test/offline/test_ci_gates.py"]

    docs = ci_checks.contract_test_plan(
        tmp_path,
        {},
        ["README.md", "docs/architecture/note.md", "logo.png"],
    )
    assert docs == {"errors": [], "mode": "documentation", "test_paths": []}
    config = ci_checks.contract_test_plan(tmp_path, {}, ["pyproject.toml"])
    assert config == {"errors": [], "mode": "configuration", "test_paths": []}
    prompt = ci_checks.contract_test_plan(tmp_path, {}, ["prompts/prompt_v1.1.yaml"])
    assert prompt == {"errors": [], "mode": "semantic", "test_paths": []}
    unknown = ci_checks.contract_test_plan(tmp_path, {}, ["new_tool.yaml"])
    assert unknown == {"errors": [], "mode": "unclassified", "test_paths": []}

    missing = ci_checks.contract_test_plan(tmp_path, {}, ["scripts/helper.py"])
    assert missing["errors"]
    missing_code = ci_checks.contract_test_plan(
        tmp_path,
        helper_fields,
        ["scripts/helper.py"],
        spec_text="Use `test/offline/test_helpers.py` only.\n",
    )
    assert missing_code["errors"]
    missing_test = ci_checks.contract_test_plan(
        tmp_path,
        helper_fields,
        ["scripts/helper.py"],
        spec_text="Code: `scripts/helper.py`.\n",
    )
    assert missing_test["errors"]


def test_parse_approved_specification_supports_non_markdown():
    path, commit, errors = ci_checks.parse_approved_specification(
        "docs/specs/approved.yaml @ abc1234"
    )
    assert errors == []
    assert path == "docs/specs/approved.yaml"
    assert commit == "abc1234"
    assert ci_checks.parse_approved_specification("docs/specs/approved.md")[2]


def test_contract_command_collects_and_executes_selected_tests(
    tmp_path: Path, monkeypatch, capsys
):
    plan = tmp_path / "docs" / "plans" / "round-01.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("Code: `src/x.py`. Use `test/offline/test_fr04_risk.py`.\n", encoding="utf-8")
    test_file = tmp_path / "test" / "offline" / "test_fr04_risk.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    body = tmp_path / "pr-body.txt"
    body.write_text(
        "Plan: docs/plans/round-01.md\n"
        "Approved test specification: docs/plans/round-01.md @ abc1234\n"
        "Approved scope: FR-04-FC01\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ci_checks, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ci_checks,
        "read_specification_at_commit",
        lambda root, path, commit: (plan.read_text(encoding="utf-8"), ""),
    )
    monkeypatch.setattr(
        ci_checks,
        "changed_paths_from_git",
        lambda *args, **kwargs: ["src/x.py"],
    )
    calls = []

    def fake_run(command, cwd=None, timeout=300):
        calls.append(list(command))
        junit_arg = next(
            (arg for arg in command if str(arg).startswith("--junitxml=")),
            "",
        )
        if junit_arg:
            Path(junit_arg.split("=", 1)[1]).write_text(
                '<testsuite tests="1" failures="0" errors="0" skipped="0">'
                '<testcase classname="contract.Test" name="test_ok" />'
                "</testsuite>",
                encoding="utf-8",
            )
        return ci_checks.CommandResult(command, 0, "1 passed", "")

    monkeypatch.setattr(ci_checks, "run_command", fake_run)
    args = SimpleNamespace(
        pr_body_file=str(body),
        base="",
        head="",
        paths="",
    )
    assert ci_checks._command_contract_tests(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["executed"] is True
    assert any("--collect-only" in command for command in calls)


def test_contract_command_executes_helper_test_from_approved_spec(
    tmp_path: Path, monkeypatch, capsys
):
    spec = tmp_path / "docs" / "specs" / "helpers.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        "Code: `scripts/helper.py`.\nUse `test/offline/test_helpers.py`.\n",
        encoding="utf-8",
    )
    test_file = tmp_path / "test" / "offline" / "test_helpers.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_helper():\n    assert True\n", encoding="utf-8")
    body = tmp_path / "pr-body.txt"
    body.write_text(
        "Plan: docs/plans/round-01.md\n"
        "Approved test specification: docs/specs/helpers.md @ abc1234\n"
        "Approved scope: shared helper gate tests\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ci_checks, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ci_checks,
        "read_specification_at_commit",
        lambda root, path, commit: (spec.read_text(encoding="utf-8"), ""),
    )
    monkeypatch.setattr(
        ci_checks,
        "changed_paths_from_git",
        lambda *args, **kwargs: ["scripts/helper.py"],
    )

    def fake_run(command, cwd=None, timeout=300):
        junit_arg = next(
            (arg for arg in command if str(arg).startswith("--junitxml=")),
            "",
        )
        if junit_arg:
            Path(junit_arg.split("=", 1)[1]).write_text(
                '<testsuite tests="1" failures="0" errors="0" skipped="0">'
                '<testcase classname="helpers.Test" name="test_helper" />'
                "</testsuite>",
                encoding="utf-8",
            )
        return ci_checks.CommandResult(command, 0, "1 passed", "")

    monkeypatch.setattr(ci_checks, "run_command", fake_run)
    args = SimpleNamespace(
        pr_body_file=str(body),
        base="",
        head="",
        paths="",
    )
    assert ci_checks._command_contract_tests(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["executed"] is True
    assert output["test_paths"] == ["test/offline/test_helpers.py"]


def test_contract_command_blocks_helper_without_approved_spec(
    tmp_path: Path, monkeypatch, capsys
):
    body = tmp_path / "pr-body.txt"
    body.write_text("", encoding="utf-8")
    monkeypatch.setattr(ci_checks, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ci_checks,
        "changed_paths_from_git",
        lambda *args, **kwargs: ["scripts/helper.py"],
    )
    monkeypatch.setattr(
        ci_checks,
        "run_command",
        lambda *args, **kwargs: ci_checks.CommandResult([], 0, "", ""),
    )
    args = SimpleNamespace(
        pr_body_file=str(body),
        base="",
        head="",
        paths="",
    )
    assert ci_checks._command_contract_tests(args) == 1
    assert "approved test scope fields" in capsys.readouterr().err


@pytest.mark.parametrize(
    "junit, returncode",
    [
        (
            '<testsuite tests="1" failures="0" errors="0" skipped="1">'
            '<testcase classname="contract.Test" name="test_skip"><skipped />'
            "</testcase></testsuite>",
            0,
        ),
        (
            '<testsuite tests="1" failures="1" errors="0" skipped="0">'
            '<testcase classname="contract.Test" name="test_bad"><failure />'
            "</testcase></testsuite>",
            1,
        ),
        (
            '<testsuite tests="1" failures="0" errors="1" skipped="0">'
            '<testcase classname="contract.Test" name="test_error"><error />'
            "</testcase></testsuite>",
            1,
        ),
        (
            '<testsuite tests="0" failures="0" errors="0" skipped="0" />',
            0,
        ),
    ],
)
def test_contract_command_rejects_skipped_failed_error_and_zero(
    tmp_path: Path, monkeypatch, capsys, junit: str, returncode: int
):
    plan = tmp_path / "docs" / "plans" / "round-01.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("Code: `src/x.py`. Use `test/offline/test_fr04_risk.py`.\n", encoding="utf-8")
    test_file = tmp_path / "test" / "offline" / "test_fr04_risk.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    body = tmp_path / "pr-body.txt"
    body.write_text(
        "Plan: docs/plans/round-01.md\n"
        "Approved test specification: docs/plans/round-01.md @ abc1234\n"
        "Approved scope: FR-04-FC01\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ci_checks, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ci_checks,
        "read_specification_at_commit",
        lambda root, path, commit: (plan.read_text(encoding="utf-8"), ""),
    )
    monkeypatch.setattr(
        ci_checks,
        "changed_paths_from_git",
        lambda *args, **kwargs: ["src/x.py"],
    )

    def fake_run(command, cwd=None, timeout=300):
        junit_arg = next(
            (arg for arg in command if str(arg).startswith("--junitxml=")),
            "",
        )
        if junit_arg:
            Path(junit_arg.split("=", 1)[1]).write_text(junit, encoding="utf-8")
            return ci_checks.CommandResult(command, returncode, "", "")
        return ci_checks.CommandResult(command, 0, "", "")

    monkeypatch.setattr(ci_checks, "run_command", fake_run)
    args = SimpleNamespace(
        pr_body_file=str(body),
        base="",
        head="",
        paths="",
    )
    assert ci_checks._command_contract_tests(args) == 1
    assert "contract" in capsys.readouterr().err.lower()


def test_contract_command_fails_when_collection_is_zero(
    tmp_path: Path, monkeypatch, capsys
):
    plan = tmp_path / "docs" / "plans" / "round-01.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("Code: `src/x.py`. Use `test/offline/test_fr04_risk.py`.\n", encoding="utf-8")
    test_file = tmp_path / "test" / "offline" / "test_fr04_risk.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    body = tmp_path / "pr-body.txt"
    body.write_text(
        "Plan: docs/plans/round-01.md\n"
        "Approved test specification: docs/plans/round-01.md @ abc1234\n"
        "Approved scope: FR-04-FC01\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ci_checks, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ci_checks,
        "read_specification_at_commit",
        lambda root, path, commit: (plan.read_text(encoding="utf-8"), ""),
    )
    monkeypatch.setattr(
        ci_checks,
        "changed_paths_from_git",
        lambda *args, **kwargs: ["src/x.py"],
    )
    monkeypatch.setattr(
        ci_checks,
        "run_command",
        lambda *args, **kwargs: ci_checks.CommandResult([], 5, "", "no tests"),
    )
    args = SimpleNamespace(
        pr_body_file=str(body),
        base="",
        head="",
        paths="",
    )
    assert ci_checks._command_contract_tests(args) == 1
    assert "collection failed" in capsys.readouterr().err


def _classify_git_semantics(repo: Path, base: str, path: str):
    hunks = ci_checks.semantic_hunks_from_git(base, "HEAD", repo)
    changed, analyzed = ci_checks.semantic_analysis_from_git(
        base, "HEAD", [path], repo
    )
    classified = ci_checks.classify_paths([path], hunks, changed, analyzed)
    return classified, changed, analyzed, hunks


def test_ai_log_requires_changed_entry_and_path_association():
    base = _log(_entry("AI-001", ["docs/readme.md"]))
    assert ci_checks.ai_log_check(base, copy.deepcopy(base), ["src/x.py"])["errors"]
    touched = copy.deepcopy(base)
    touched["entries"][0]["ai_contribution"] = "touched"
    assert ci_checks.ai_log_check(base, touched, ["src/x.py"])["errors"]
    unrelated = _log(_entry("AI-001", ["docs/readme.md"]), _entry("AI-002", ["docs/x.md"]))
    assert ci_checks.ai_log_check(base, unrelated, ["src/x.py"])["errors"]
    exact = _log(_entry("AI-001", ["docs/readme.md"]), _entry("AI-002", ["src/x.py"]))
    assert ci_checks.ai_log_check(base, exact, ["src/x.py"])["errors"] == []
    multi = ci_checks.ai_log_check(
        base, exact, ["src/x.py", "src/y.py"]
    )
    assert multi["errors"] == []
    assert multi["unassociated_paths"] == ["src/y.py"]
    directory = _log(_entry("AI-001", ["docs/readme.md"]), _entry("AI-002", ["src/"]))
    assert ci_checks.ai_log_check(base, directory, ["src/x.py"])["errors"] == []
    described = _log(
        _entry("AI-001", ["docs/readme.md"]),
        _entry("AI-002", ["docs/x.md"], "Changed src/x.py"),
    )
    assert ci_checks.ai_log_check(base, described, ["src/x.py"])["errors"] == []
    assert ci_checks.ai_log_check(base, exact, ["docs/x.md"])["errors"] == []
    assert ci_checks.ai_log_check(base, exact, ["pyproject.toml"])["errors"] == []
    assert ci_checks.ai_log_check(base, exact, ["Prompt.md"])["errors"] == []
    assert (
        ci_checks.ai_log_check(base, base, [".github/workflows/ci.yml"])["required"]
        is False
    )
    assert ci_checks.ai_log_check(base, base, [".github/workflows/ci.yml"])["errors"] == []
    assert ci_checks.ai_log_check(base, base, ["scripts/ci_checks.py"])["errors"]
    for path in (
        "scripts/helper.py",
        "scripts/helper.sh",
        "setup.py",
        "docs/helper.py",
        "docs/helper.sh",
        "tools/helper.py",
        "prompts/prompt_v1.1.yaml",
    ):
        assert ci_checks.ai_log_check(base, exact, [path])["errors"]
    prompt = _log(
        _entry("AI-001", ["docs/readme.md"]),
        _entry("AI-002", ["src/tradingagents/agents/analysts/news_analyst.py"]),
    )
    assert (
        ci_checks.ai_log_check(
            base,
            prompt,
            ["src/tradingagents/agents/analysts/news_analyst.py"],
        )["errors"]
        == []
    )


def test_ai_log_structure_duplicate_and_empty_transcripts():
    duplicate = _log(_entry("AI-001", ["src/x.py"]), _entry("AI-001", ["src/y.py"]))
    assert ci_checks.validate_ai_log(duplicate)
    valid = _log(_entry("AI-001", ["src/x.py"]))
    assert ci_checks.validate_ai_log(valid) == []


def test_workflow_event_split_and_aggregate_shape():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "push:" in text
    assert "pull_request:" in text
    assert "github.event.pull_request.head.sha" in text
    assert "name: aggregate" in text
    data = yaml.safe_load(text)
    jobs = data["jobs"]
    aggregate_if = str(jobs["aggregate"].get("if", ""))
    assert "github.event_name == 'pull_request'" in aggregate_if
    for job in (
        "test-approval",
        "security-paths",
        "ai-use-log",
        "evidence-check",
        "contract-tests",
    ):
        assert "github.event_name == 'pull_request'" in str(jobs[job].get("if", ""))
    classify_outputs = jobs["classify"].get("outputs", {})
    assert "approval_applicable" in classify_outputs
    assert "requires_conservative_checks" not in classify_outputs
    classify_steps = json.dumps(jobs["classify"])
    assert "classify-guard" not in classify_steps
    assert "classification.json" in classify_steps
    assert "approval_applicable" in str(jobs["test-approval"].get("if", ""))
    aggregate_steps = json.dumps(jobs["aggregate"])
    assert "contract-tests" in aggregate_steps
    assert "test-approval=" in aggregate_steps
    assert "--conservative-required" not in aggregate_steps
    evidence_steps = json.dumps(jobs["evidence-check"])
    assert "--default-branch" in evidence_steps
    assert "--live-required" not in evidence_steps
    push_jobs = {"classify": {"result": "success"}}
    assert (
        ci_checks.aggregate_results(
            push_jobs,
            ["classify"],
        )["errors"]
        == []
    )


def test_trusted_workflow_pins_tool_checkout_to_trigger_sha():
    text = (ROOT / ".github" / "workflows" / "trusted-evaluation.yml").read_text(
        encoding="utf-8"
    )
    assert "ref: ${{ github.sha }}" in text
    assert "ref: ${{ inputs.candidate_sha }}" in text
    assert "environment: trusted-evaluation" in text
    assert "refs/heads/${{ github.event.repository.default_branch }}" in text
    assert "Verify trusted tool checkout" in text


def test_trusted_workflow_live_uses_structured_pytest_results():
    text = (ROOT / ".github" / "workflows" / "trusted-evaluation.yml").read_text(
        encoding="utf-8"
    )
    assert "test/live/" in text
    assert "--junitxml" in text
    assert "live-result" in text
    assert "DEEPSEEK_API_KEY" in text
    assert "DEEPSEEK_API_KEY is not configured" in text
    assert "skipped|deselected" not in text
    assert "grep -E" not in text


def test_trusted_workflow_semantic_handoff_and_details_artifact():
    """FR-10 / P06: semantic mode passes DEEPSEEK_API_KEY only inside trusted job and uploads details."""
    text = (ROOT / ".github" / "workflows" / "trusted-evaluation.yml").read_text(
        encoding="utf-8"
    )
    workflow = yaml.safe_load(text)
    steps = workflow["jobs"]["evaluate"]["steps"]
    semantic_step = next(s for s in steps if s.get("name") == "Write semantic evidence record")
    assert semantic_step["env"]["DEEPSEEK_API_KEY"] == "${{ secrets.DEEPSEEK_API_KEY }}"
    assert "--details-output" in semantic_step["run"]
    details_upload = next(s for s in steps if s.get("name") == "Upload semantic details artifact")
    assert details_upload["if"] == (
        "always() && inputs.mode == 'semantic' && steps.resolve.outcome == 'success'"
    )
    assert "semantic-details.json" in details_upload["with"]["path"]
    ci_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY" not in ci_text


def test_aggregate_allows_not_applicable_skip_and_rejects_missing_applicability(
    capsys,
):
    needs = '{"a": {"result": "success"}, "b": {"result": "skipped"}}'
    args = SimpleNamespace(
        needs_json=needs,
        required="a,b",
        applicable="b=false",
    )
    assert ci_checks._command_aggregate(args) == 0
    args.applicable = "b=true"
    assert ci_checks._command_aggregate(args) == 1
    args.applicable = "b="
    assert ci_checks._command_aggregate(args) == 1
    assert "applicability" in capsys.readouterr().err.lower()


def test_aggregate_rules():
    required = ["a", "b"]
    assert ci_checks.aggregate_results(
        {"a": {"result": "success"}, "b": {"result": "success"}}, required
    )["errors"] == []
    assert ci_checks.aggregate_results(
        {"a": {"result": "success"}, "b": {"result": "failure"}}, required
    )["errors"]
    assert ci_checks.aggregate_results(
        {"a": {"result": "success"}, "b": {"result": "cancelled"}}, required
    )["errors"]
    assert ci_checks.aggregate_results(
        {"a": {"result": "success"}, "b": {"result": "skipped"}}, required
    )["errors"]
    assert ci_checks.aggregate_results(
        {"a": {"result": "success"}, "b": {"result": "skipped"}},
        required,
        {"b": False},
    )["errors"] == []
    assert ci_checks.aggregate_results(
        {"a": {"result": "success"}, "b": {"result": "skipped"}},
        required,
        {"b": True},
    )["errors"]
    assert ci_checks.aggregate_results(
        {"a": {"result": "success"}}, required
    )["errors"]


def _status(context: str, candidate: str, run_id: int, state: str = "success") -> dict[str, Any]:
    return {
        "context": context,
        "sha": candidate,
        "state": state,
        "target_url": f"https://github.com/o/r/actions/runs/{run_id}",
    }


def _record(
    kind: str,
    candidate: str = "cand1",
    workflow_sha: str = "wf1",
    **overrides: Any,
) -> dict[str, Any]:
    record = {
        "kind": kind,
        "candidate_sha": candidate,
        "workflow_sha": workflow_sha,
        "status": "passed",
        "config_version": "v1",
        "reason": "",
        "reviewed_by": "",
        "executed": True,
        "collected_only": False,
    }
    if kind == "semantic":
        record.update(
            {
                "suite_id": "financial-metrics",
                "config_path": "docs/ci/semantic_eval.yaml",
                "config_sha256": "cfgsha",
                "runner": "financial_metrics_eval:evaluate",
                "needs_review": [],
            }
        )
    record.update(overrides)
    return record


def _run(run_id: int, record: dict[str, Any] | None, **overrides: Any) -> dict[str, Any]:
    run = {
        "repository": "o/r",
        "path": ci_checks.TRUSTED_WORKFLOW,
        "event": "workflow_dispatch",
        "conclusion": "success",
        "head_sha": "wf1",
        "head_branch": "main",
        "artifacts": [] if record is None else [{"expired": False, "record": record}],
    }
    run.update(overrides)
    return run


def _evidence(statuses, runs, **kwargs):
    defaults = {
        "candidate": "cand1",
        "repo": "o/r",
        "default_branch": "main",
        "statuses": statuses,
        "runs": runs,
        "semantic_required": True,
        "live_required": False,
        "selection": _selection("financial-metrics"),
        "trusted_suites": {"financial-metrics": _trusted_suite()},
    }
    defaults.update(kwargs)
    return ci_checks.verify_evidence(**defaults)


_FM_CONTEXT = "semantic-eval/financial-metrics"


def _selection(*suites: str, none: bool = False, errors: list[str] | None = None) -> dict[str, Any]:
    return {"suites": list(suites), "none": none, "errors": list(errors or [])}


def _trusted_suite(**overrides: Any) -> dict[str, Any]:
    suite = {
        "approved": True,
        "config_path": "docs/ci/semantic_eval.yaml",
        "config_sha256": "cfgsha",
        "config_version": "v1",
        "runner": "financial_metrics_eval:evaluate",
    }
    suite.update(overrides)
    return suite


def test_semantic_evidence_accepts_trusted_candidate_and_config():
    statuses = [_status(_FM_CONTEXT, "cand1", 7)]
    runs = {"7": _run(7, _record("semantic"))}
    assert _evidence(statuses, runs)["errors"] == []


def test_semantic_evidence_rejects_missing_wrong_sha_and_untrusted_runs():
    assert _evidence([], {})["errors"]
    assert _evidence([_status(_FM_CONTEXT, "other", 7)], {"7": _run(7, _record("semantic"))})["errors"]
    assert _evidence(
        [_status(_FM_CONTEXT, "cand1", 7)],
        {"7": _run(7, _record("semantic"), path=".github/workflows/other.yml")},
    )["errors"]
    assert _evidence(
        [_status(_FM_CONTEXT, "cand1", 7)],
        {"7": _run(7, _record("semantic"), repository="other/repo")},
    )["errors"]
    assert _evidence(
        [_status(_FM_CONTEXT, "cand1", 7)],
        {"7": _run(7, _record("semantic"), event="push")},
    )["errors"]
    assert _evidence(
        [_status(_FM_CONTEXT, "cand1", 7)],
        {"7": _run(7, _record("semantic"), head_branch="release")},
    )["errors"]
    assert _evidence(
        [_status(_FM_CONTEXT, "cand1", 7)],
        {"7": _run(7, None)},
    )["errors"]


def test_semantic_evidence_rejects_config_and_artifact_mismatches():
    statuses = [_status(_FM_CONTEXT, "cand1", 7)]
    assert _evidence(
        statuses,
        {"7": _run(7, _record("semantic", config_version="v2"))},
    )["errors"]
    assert _evidence(
        statuses,
        {"7": _run(7, _record("semantic"))},
        trusted_suites={"financial-metrics": _trusted_suite(approved=False)},
    )["errors"]
    assert _evidence(
        statuses,
        {"7": _run(7, _record("semantic", candidate="other"))},
    )["errors"]
    assert _evidence(
        statuses,
        {"7": _run(7, _record("semantic", status="failed"))},
    )["errors"]


def test_semantic_not_applicable_requires_review_reason():
    noop = ci_checks.SEMANTIC_NOOP_STATUS
    assert _evidence(
        [_status(noop, "cand1", 8)],
        {"8": _run(8, _record("semantic-noop", reason="", reviewed_by=""))},
        selection=_selection(none=True),
    )["errors"]
    assert _evidence(
        [_status(noop, "cand1", 8)],
        {"8": _run(8, _record("semantic-noop", reason="layout only", reviewed_by="human"))},
        selection=_selection(none=True),
    )["errors"] == []


def test_workflow_head_sha_may_differ_but_new_candidate_invalidates():
    statuses = [_status(_FM_CONTEXT, "cand1", 7)]
    runs = {
        "7": _run(
            7,
            _record("semantic", workflow_sha="workflow-sha"),
            head_sha="workflow-sha",
        )
    }
    assert _evidence(statuses, runs)["errors"] == []
    assert _evidence(statuses, runs, candidate="cand2")["errors"]


def test_live_evidence_requires_execution_and_passes_with_docs_only_scope():
    live = ci_checks.LIVE_STATUS
    assert _evidence(
        [_status(live, "cand1", 9)],
        {"9": _run(9, _record("live"))},
        semantic_required=False,
        selection=None,
        live_required=True,
    )["errors"] == []
    assert _evidence(
        [_status(live, "cand1", 9)],
        {"9": _run(9, _record("live", collected_only=True))},
        semantic_required=False,
        selection=None,
        live_required=True,
    )["errors"]
    assert _evidence(
        [],
        {},
        semantic_required=False,
        selection=None,
        live_required=True,
    )["errors"]
    assert _evidence(
        [],
        {},
        semantic_required=False,
        selection=None,
        live_required=False,
    )["errors"] == []


def test_live_junit_requires_executed_passing_cases():
    passed = (
        '<testsuites><testsuite tests="1" failures="0" errors="0" '
        'skipped="0" deselected="2">'
        '<testcase classname="live.Test" name="test_ok" />'
        "</testsuite></testsuites>"
    )
    assert ci_checks.evaluate_live_junit(passed)["errors"] == []
    failure = (
        '<testsuite tests="1" failures="1" errors="0" skipped="0">'
        '<testcase classname="live.Test" name="test_bad"><failure /></testcase>'
        "</testsuite>"
    )
    assert ci_checks.evaluate_live_junit(failure)["errors"]
    skipped = (
        '<testsuite tests="1" failures="0" errors="0" skipped="1">'
        '<testcase classname="live.Test" name="test_skip"><skipped /></testcase>'
        "</testsuite>"
    )
    assert ci_checks.evaluate_live_junit(skipped)["errors"]
    zero = '<testsuite tests="0" failures="0" errors="0" skipped="0" />'
    assert ci_checks.evaluate_live_junit(zero)["errors"]
    assert ci_checks.evaluate_live_junit("not xml")["errors"]


def test_semantic_config_validation_and_not_applicable_entry(tmp_path: Path):
    unapproved = ci_semantic_eval.validate_config(
        ci_checks.load_yaml(ROOT / "docs" / "ci" / "semantic_eval.yaml")
    )
    assert unapproved["approved"] is False
    assert unapproved["errors"] == []

    approved = {
        "schema_version": "1.0",
        "status": "approved",
        "dataset": {"version": "v1", "cases": [{"id": "case-1"}]},
        "rubric": {"version": "v1", "definition": "fixed"},
        "thresholds": {"quality": 1},
        "model": {"provider": "test", "model": "test-model"},
        "approval": {"approved_by": "human", "approved_at": "2026-11-18", "evidence": ["url"]},
    }
    assert ci_semantic_eval.validate_config(approved)["errors"] == []
    missing = copy.deepcopy(approved)
    missing["dataset"] = {"version": None, "cases": []}
    assert ci_semantic_eval.validate_config(missing)["errors"]

    output = tmp_path / "record.json"
    config = ROOT / "docs" / "ci" / "semantic_eval.yaml"
    common = [
        "--config",
        str(config),
        "--candidate",
        "cand1",
        "--workflow-sha",
        "wf1",
        "--run-id",
        "1",
        "--output",
        str(output),
    ]
    assert ci_semantic_eval.main([*common, "--not-applicable"]) == 1
    assert not output.exists()
    assert (
        ci_semantic_eval.main(
            [
                *common,
                "--not-applicable",
                "--reason",
                "layout only",
                "--reviewer",
                "human",
                "--approval-evidence",
                "https://github.com/o/r/pull/1#pullrequestreview-1",
            ]
        )
        == 0
    )
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["status"] == "not_applicable"
    assert record["reviewed_by"] == "human"


def test_semantic_entry_preserves_details_reference_and_fails_closed(tmp_path: Path):
    """FR-10 / P06: detailed evidence round-trip and failure status propagation.

    Runs through a registered suite (semantic-suite-routing §3.4); needs_review is
    preserved as its own status instead of being flattened to failed (plan P6).
    """
    import hashlib

    root, registry, _ = _semantic_suite_root(
        tmp_path / "pass",
        result={
            "request_count": 6,
            "candidate_summary": {"passed_checks": 20, "total_checks": 20},
            "baseline_summary": {"paired_cases": ["FM-S01", "FM-S02"]},
        },
    )
    rc, rec = _run_suite(root, registry, tmp_path, "record-pass")
    assert rc == 0
    assert rec["status"] == "passed"
    assert rec["request_count"] == 6
    assert rec["candidate_summary"]["passed_checks"] == 20
    assert rec["baseline_summary"]["paired_cases"] == ["FM-S01", "FM-S02"]
    det_out = tmp_path / "record-pass" / "semantic-details.json"
    assert det_out.is_file()
    assert rec["details_sha256"] == hashlib.sha256(det_out.read_bytes()).hexdigest()

    review_root, review_registry, _ = _semantic_suite_root(
        tmp_path / "review",
        result={
            "status": "needs_review",
            "errors": ["ambiguous claim"],
            "needs_review": ["FM-S01:ambiguous_metric_claim:m1"],
        },
    )
    rc_fail, fail_rec = _run_suite(review_root, review_registry, tmp_path, "record-review")
    assert rc_fail == 1
    assert fail_rec["status"] == "needs_review"
    assert fail_rec["needs_review"] == ["FM-S01:ambiguous_metric_claim:m1"]
    assert "ambiguous claim" in fail_rec["reason"]
    assert (tmp_path / "record-review" / "semantic-details.json").is_file()

    failed_root, failed_registry, _ = _semantic_suite_root(
        tmp_path / "failed", result={"status": "failed", "errors": ["critical"]}
    )
    rc_failed, failed_rec = _run_suite(failed_root, failed_registry, tmp_path, "record-failed")
    assert rc_failed == 1
    assert failed_rec["status"] == "failed"


class _ArtifactProbeServer(http.server.ThreadingHTTPServer):
    routes: dict[str, tuple[int, dict[str, str], bytes]]
    seen: list[tuple[str, str | None]]


class _ArtifactProbeHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        server = self.server
        assert isinstance(server, _ArtifactProbeServer)
        server.seen.append((self.path, self.headers.get("Authorization")))
        status, headers, body = server.routes[self.path]
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@contextlib.contextmanager
def _serve_artifact_probe(routes):
    server = _ArtifactProbeServer(("127.0.0.1", 0), _ArtifactProbeHandler)
    server.routes = routes
    server.seen = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _bypass_local_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,127.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,127.1,localhost")

    def loopback_connect(sock, address):
        if address[0] not in {"127.0.0.1", "127.1"}:
            raise OSError(f"test tried to reach the network: {address!r}")
        return _CONNECT(sock, address)

    def loopback_getaddrinfo(host, *args, **kwargs):
        if host not in {"127.0.0.1", "127.1", "localhost"}:
            raise OSError(f"test tried to reach the network: {host!r}")
        return _GETADDRINFO(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", loopback_connect)
    monkeypatch.setattr(socket, "getaddrinfo", loopback_getaddrinfo)


def test_github_bytes_preserves_authorization_on_same_origin_redirect(
    monkeypatch: pytest.MonkeyPatch,
):
    _bypass_local_proxy(monkeypatch)
    token = "fake-local-token"
    body = b"artifact-body"
    routes = {
        "/start": (302, {"Location": "/final"}, b""),
        "/final": (200, {}, body),
    }
    with _serve_artifact_probe(routes) as server:
        url = f"http://127.0.0.1:{server.server_address[1]}/start"
        assert ci_checks._github_bytes(url, token) == body
        assert server.seen[-1] == ("/final", f"Bearer {token}")


def test_github_bytes_drops_authorization_on_cross_origin_redirect_and_reads_body(
    monkeypatch: pytest.MonkeyPatch,
):
    _bypass_local_proxy(monkeypatch)
    token = "fake-local-token"
    body = b"artifact-body"
    with _serve_artifact_probe({"/final": (200, {}, body)}) as target:
        target_url = f"http://127.1:{target.server_address[1]}/final"
        with _serve_artifact_probe({
            "/start": (302, {"Location": target_url}, b""),
        }) as origin:
            url = f"http://127.0.0.1:{origin.server_address[1]}/start"
            assert ci_checks._github_bytes(url, token) == body
        assert target.seen == [("/final", None)]


def test_github_bytes_treats_scheme_change_as_cross_origin():
    request = urllib.request.Request(
        "http://example.test/start",
        headers={"Authorization": "Bearer fake-local-token"},
    )
    redirected = ci_checks._NoCrossOriginAuthRedirect().redirect_request(
        request,
        None,
        302,
        "Found",
        {},
        "https://example.test/final",
    )
    assert redirected is not None
    assert redirected.get_header("Authorization") is None


def test_github_bytes_treats_effective_port_change_as_cross_origin(
    monkeypatch: pytest.MonkeyPatch,
):
    _bypass_local_proxy(monkeypatch)
    token = "fake-local-token"
    body = b"artifact-body"
    with _serve_artifact_probe({"/final": (200, {}, body)}) as target:
        target_url = f"http://127.0.0.1:{target.server_address[1]}/final"
        with _serve_artifact_probe({
            "/start": (302, {"Location": target_url}, b""),
        }) as origin:
            url = f"http://127.0.0.1:{origin.server_address[1]}/start"
            assert ci_checks._github_bytes(url, token) == body
        assert target.seen == [("/final", None)]


def test_github_bytes_treats_default_and_explicit_equivalent_ports_as_same_origin():
    handler = ci_checks._NoCrossOriginAuthRedirect()
    cases = (
        ("https://example.test/start", "https://EXAMPLE.TEST:443/final"),
        ("http://example.test/start", "http://example.test:80/final"),
    )
    for request_url, redirect_url in cases:
        request = urllib.request.Request(
            request_url,
            headers={"Authorization": "Bearer fake-local-token"},
        )
        redirected = handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            redirect_url,
        )
        assert redirected is not None
        assert redirected.get_header("Authorization") == "Bearer fake-local-token"
    assert ci_checks._url_origin("https://example.test/start") != ci_checks._url_origin(
        "https://example.test./start"
    )


def test_github_bytes_does_not_reattach_authorization_across_multiple_redirects(
    monkeypatch: pytest.MonkeyPatch,
):
    _bypass_local_proxy(monkeypatch)
    token = "fake-local-token"
    body = b"artifact-body"
    routes = {
        "/second": (302, {"Location": "/final"}, b""),
        "/final": (200, {}, body),
    }
    with _serve_artifact_probe(routes) as target:
        second_url = f"http://127.1:{target.server_address[1]}/second"
        with _serve_artifact_probe({
            "/start": (302, {"Location": second_url}, b""),
        }) as origin:
            url = f"http://127.0.0.1:{origin.server_address[1]}/start"
            assert ci_checks._github_bytes(url, token) == body
        assert target.seen == [("/second", None), ("/final", None)]


def test_github_bytes_raises_ci_error_on_401(monkeypatch: pytest.MonkeyPatch):
    _bypass_local_proxy(monkeypatch)
    with _serve_artifact_probe({"/fail": (401, {}, b"")}) as server:
        url = f"http://127.0.0.1:{server.server_address[1]}/fail"
        with pytest.raises(ci_checks.CiError) as excinfo:
            ci_checks._github_bytes(url, "fake-local-token")
    assert "401" in str(excinfo.value)


def test_github_bytes_raises_ci_error_on_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    _bypass_local_proxy(monkeypatch)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with pytest.raises(ci_checks.CiError):
        ci_checks._github_bytes(
            f"http://127.0.0.1:{port}/artifact",
            "fake-local-token",
        )


def test_fetch_trusted_runs_propagates_artifact_download_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    def fake_request(url: str, token: str):
        if url.endswith("/actions/runs/1"):
            return {"path": ci_checks.TRUSTED_WORKFLOW}
        if url.endswith("/artifacts"):
            return {
                "artifacts": [
                    {
                        "expired": False,
                        "archive_download_url": "https://example.invalid/archive",
                    }
                ]
            }
        raise AssertionError(url)

    def fail_download(url: str, token: str):
        raise ci_checks.CiError("artifact download failed")

    monkeypatch.setattr(ci_checks, "_github_request", fake_request)
    monkeypatch.setattr(ci_checks, "_github_bytes", fail_download)
    with pytest.raises(ci_checks.CiError):
        ci_checks.fetch_trusted_runs(
            "o/r",
            [{"target_url": "https://github.com/o/r/actions/runs/1"}],
            "fake-local-token",
        )


# ---------------------------------------------------------------------------
# Semantic suite routing (docs/plans/semantic-suite-routing.md §3, §5 T01-T18)
# ---------------------------------------------------------------------------

_DA_CONTEXT = "semantic-eval/data-availability"
_FM_CONFIG_LF_SHA256 = "20e15937f66a14617e9b613d1c42854dd2a1dd616771d84d40bc746d1423d9b7"


def _da_record(**overrides: Any) -> dict[str, Any]:
    record = _record(
        "semantic",
        suite_id="data-availability",
        config_path="docs/ci/semantic-suites/data-availability.yaml",
        config_sha256="dasha",
        runner="data_availability_eval:evaluate",
    )
    record.update(overrides)
    return record


def _da_trusted(**overrides: Any) -> dict[str, Any]:
    return _trusted_suite(
        config_path="docs/ci/semantic-suites/data-availability.yaml",
        config_sha256="dasha",
        runner="data_availability_eval:evaluate",
        **overrides,
    )


def _both_trusted() -> dict[str, Any]:
    return {"financial-metrics": _trusted_suite(), "data-availability": _da_trusted()}


def test_t01_single_selected_suite_with_matching_evidence_passes():
    statuses = [_status(_FM_CONTEXT, "cand1", 7)]
    runs = {"7": _run(7, _record("semantic"))}
    assert _evidence(statuses, runs)["errors"] == []


def test_t02_unrelated_suite_evidence_does_not_substitute():
    result = _evidence(
        [_status(_FM_CONTEXT, "cand1", 7)],
        {"7": _run(7, _record("semantic"))},
        selection=_selection("data-availability"),
        trusted_suites=_both_trusted(),
    )
    assert any(_DA_CONTEXT in error for error in result["errors"])


def test_t03_every_selected_suite_needs_its_own_evidence():
    statuses = [_status(_FM_CONTEXT, "cand1", 7)]
    runs = {"7": _run(7, _record("semantic"))}
    missing = _evidence(
        statuses,
        runs,
        selection=_selection("financial-metrics", "data-availability"),
        trusted_suites=_both_trusted(),
    )
    assert missing["errors"]
    assert all("financial-metrics" not in error for error in missing["errors"])
    assert any(_DA_CONTEXT in error for error in missing["errors"])
    both = _evidence(
        statuses + [_status(_DA_CONTEXT, "cand1", 8)],
        {**runs, "8": _run(8, _da_record())},
        selection=_selection("financial-metrics", "data-availability"),
        trusted_suites=_both_trusted(),
    )
    assert both["errors"] == []


def test_t04_semantic_required_without_selection_blocks():
    statuses = [_status(_FM_CONTEXT, "cand1", 7)]
    runs = {"7": _run(7, _record("semantic"))}
    for selection in (None, _selection()):
        errors = _evidence(statuses, runs, selection=selection)["errors"]
        assert any("no semantic suite was selected" in error for error in errors)


def test_t05_unknown_suite_blocks_before_status_lookup():
    errors = _evidence([], {}, selection=_selection("no-such-suite"))["errors"]
    assert any("unknown semantic suite: no-such-suite" in error for error in errors)
    assert all("missing semantic-eval/no-such-suite" not in error for error in errors)


def test_t06_unapproved_trusted_config_blocks_even_with_passing_status():
    errors = _evidence(
        [_status(_FM_CONTEXT, "cand1", 7)],
        {"7": _run(7, _record("semantic"))},
        trusted_suites={"financial-metrics": _trusted_suite(approved=False)},
    )["errors"]
    assert any("is unapproved" in error for error in errors)


def _suite_event(body: str, **overrides: Any) -> dict[str, Any]:
    event = {
        "reviewer": "reviewer",
        "reviewer_type": "User",
        "state": "COMMENTED",
        "body": body,
        "created_at": "2026-11-24T10:00:00Z",
        "url": "https://github.com/o/r/pull/17#issuecomment-1",
    }
    event.update(overrides)
    return event


def _suite_fields(value: str, url: str = "https://github.com/o/r/pull/17#issuecomment-1"):
    fields = {"Semantic suites": value}
    if url:
        fields["Semantic suites approval"] = url
    return fields


def test_t07_suite_selection_approval_rules():
    verify = ci_checks.verify_suite_selection
    ok = verify(
        _suite_fields("Data-Availability ,financial-metrics"),
        _suite_event("LGTM\nAPPROVED semantic-suites: financial-metrics, data-availability"),
        "author",
    )
    assert ok["errors"] == []
    assert ok["suites"] == ["data-availability", "financial-metrics"]
    assert ok["none"] is False
    phrase = "APPROVED semantic-suites: financial-metrics"
    assert verify(_suite_fields("financial-metrics", url=""), _suite_event(phrase), "author")["errors"]
    assert verify(_suite_fields("financial-metrics"), None, "author")["errors"]
    assert verify(
        _suite_fields("financial-metrics"), _suite_event(phrase, reviewer="author"), "author"
    )["errors"]
    assert verify(
        _suite_fields("financial-metrics"),
        _suite_event(phrase, reviewer="helper[bot]", reviewer_type="Bot"),
        "author",
    )["errors"]
    assert verify(_suite_fields("financial-metrics"), _suite_event("approved"), "author")["errors"]
    assert verify(
        _suite_fields("financial-metrics"), _suite_event(phrase + "\n" + phrase), "author"
    )["errors"]
    assert verify(
        _suite_fields("financial-metrics, data-availability"), _suite_event(phrase), "author"
    )["errors"]
    mixed = verify(
        _suite_fields("none, financial-metrics"),
        _suite_event("APPROVED semantic-suites: none, financial-metrics"),
        "author",
    )
    assert mixed["errors"]
    none = verify(
        _suite_fields("None"), _suite_event("APPROVED semantic-suites: none"), "author"
    )
    assert none["errors"] == [] and none["none"] is True and none["suites"] == []
    assert ci_checks.parse_pr_body(
        "Semantic suites: financial-metrics\n"
        "Semantic suites approval: https://github.com/o/r/pull/17#issuecomment-1\n"
    ) == _suite_fields("financial-metrics")


def test_t08_record_must_match_suite_config_candidate_and_trusted_run():
    statuses = [_status(_FM_CONTEXT, "cand1", 7)]
    for record in (
        _record("semantic", suite_id="data-availability"),
        _record("semantic", config_sha256="stale"),
        _record("semantic", config_path="docs/ci/other.yaml"),
        _record("semantic", candidate="other"),
        _record("semantic", status="failed"),
    ):
        assert _evidence(statuses, {"7": _run(7, record)})["errors"], record
    for run_override in (
        {"path": ".github/workflows/other.yml"},
        {"head_branch": "feature"},
        {"event": "push"},
    ):
        assert _evidence(
            statuses, {"7": _run(7, _record("semantic"), **run_override)}
        )["errors"], run_override


def test_t09_needs_review_blocks_and_lists_items():
    items = ["FM-S01:missing_metric_mention:m1", "FM-S03:unresolved_period:m2"]
    errors = _evidence(
        [_status(_FM_CONTEXT, "cand1", 7)],
        {"7": _run(7, _record("semantic", status="needs_review", needs_review=items))},
    )["errors"]
    assert any(
        "needs human review" in error and items[0] in error and items[1] in error
        for error in errors
    )
    state, description = ci_semantic_eval.status_description(
        {"candidate_sha": "cand1", "status": "needs_review", "needs_review": items}
    )
    assert state == "failure"
    assert description == "needs_review: 2 pending items"
    assert ci_semantic_eval.status_description({"status": "failed"}) == ("failure", "failed")
    assert ci_semantic_eval.status_description(
        {"candidate_sha": "cand1", "status": "passed"}
    ) == ("success", "evidence recorded for cand1")
    assert ci_semantic_eval.status_description(None)[0] == "failure"


def test_t10_none_selection_uses_reviewed_not_applicable_only():
    noop = ci_checks.SEMANTIC_NOOP_STATUS
    noop_status = [_status(noop, "cand1", 8)]
    noop_run = {"8": _run(8, _record("semantic-noop", reason="layout only", reviewed_by="human"))}
    assert _evidence(noop_status, noop_run, selection=_selection(none=True))["errors"] == []
    assert _evidence([], {}, selection=_selection(none=True))["errors"]
    assert _evidence(noop_status, noop_run, selection=_selection("financial-metrics"))["errors"]


def test_t11_legacy_shared_semantic_status_is_not_accepted():
    errors = _evidence(
        [_status("semantic-eval/evidence", "cand1", 7)],
        {"7": _run(7, _record("semantic"))},
    )["errors"]
    assert any(_FM_CONTEXT in error for error in errors)


def test_t12_non_semantic_pr_without_selection_keeps_old_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    assert _evidence([], {}, semantic_required=False, selection=None, trusted_suites=None)[
        "errors"
    ] == []
    assert _evidence(
        [], {}, semantic_required=False, selection=_selection(none=True), trusted_suites=None
    )["errors"] == []

    def no_github(*args: Any, **kwargs: Any):
        raise AssertionError("PR or approval must not be fetched for a non-enforced PR")

    captured: dict[str, Any] = {}

    def fake_fetch_evidence(repo, candidate, default_branch, token, **kwargs):
        captured.update(kwargs)
        return {"errors": []}

    monkeypatch.setattr(ci_checks, "_github_request", no_github)
    monkeypatch.setattr(ci_checks, "fetch_approval_event", no_github)
    monkeypatch.setattr(ci_checks, "fetch_evidence", fake_fetch_evidence)
    body = tmp_path / "body.txt"
    body.write_text("Plain PR description without semantic fields.\n", encoding="utf-8")
    rc = ci_checks.main(
        [
            "evidence",
            "--candidate", "cand1",
            "--repo", "o/r",
            "--default-branch", "main",
            "--token", "fake-local-token",
            "--pr", "17",
            "--pr-body-file", str(body),
            "--registry", str(tmp_path / "missing" / "semantic-suites.yaml"),
            "--trusted-root", str(tmp_path / "missing"),
        ]
    )
    assert rc == 0
    assert captured["selection"] is None
    assert captured["trusted_suites"] is None


def _write_registry(root: Path, suites: dict[str, Any] | str) -> Path:
    path = root / "docs" / "ci" / "semantic-suites.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(suites, str):
        path.write_text(suites, encoding="utf-8")
    else:
        path.write_text(
            yaml.safe_dump({"schema_version": "1.0", "suites": suites}, sort_keys=False),
            encoding="utf-8",
        )
    return path


def _suite_root(tmp_path: Path, runner_module: str = "demo_eval", runner_source: str = "") -> Path:
    root = tmp_path / "trusted"
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / f"{runner_module}.py").write_text(
        runner_source or "def evaluate(config, candidate_sha, *, output_dir, model_transport=None):\n"
        "    return {'status': 'failed'}\n",
        encoding="utf-8",
    )
    config_dir = root / "docs" / "ci" / "semantic-suites"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "demo.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": "1.0", "status": "unapproved", "execution": {"runner": f"{runner_module}:evaluate"}}
        ),
        encoding="utf-8",
    )
    return root


def _demo_entry(**overrides: Any) -> dict[str, Any]:
    entry = {
        "requirement": "FR-TEST",
        "config": "docs/ci/semantic-suites/demo.yaml",
        "runner": "demo_eval:evaluate",
    }
    entry.update(overrides)
    return entry


def test_t13_registry_validation(tmp_path: Path):
    root = _suite_root(tmp_path)
    load = ci_checks.load_suite_registry
    good = load(_write_registry(root, {"demo": _demo_entry()}), root)
    assert good["errors"] == []
    assert good["suites"]["demo"]["runner"] == "demo_eval:evaluate"
    other = root / "docs" / "ci" / "other.yaml"
    other.write_text("schema_version: '1.0'\n", encoding="utf-8")
    outside = root / "outside.yaml"
    outside.write_text("x: 1\n", encoding="utf-8")
    bad_cases = [
        {"Bad_ID": _demo_entry()},
        {"evidence": _demo_entry()},
        {"not-applicable": _demo_entry()},
        {"demo": _demo_entry(config="outside.yaml")},
        {"demo": _demo_entry(config="docs/ci/../../outside.yaml")},
        {"demo": _demo_entry(config="docs/ci/semantic-suites/missing.yaml")},
        {"demo": _demo_entry(), "demo-two": _demo_entry()},
        {"demo": _demo_entry(runner="tradingagents.graph:evaluate")},
        {"demo": _demo_entry(runner="missing_eval:evaluate")},
        {"demo": _demo_entry(runner="demo_eval")},
        {"demo": _demo_entry(runner="other_eval:evaluate")},
        {"demo": {**_demo_entry(), "extra": 1}},
        {"demo": {"config": "docs/ci/semantic-suites/demo.yaml", "runner": "demo_eval:evaluate"}},
    ]
    (root / "scripts" / "other_eval.py").write_text("", encoding="utf-8")
    for suites in bad_cases:
        result = load(_write_registry(root, suites), root)
        assert result["errors"], suites
    duplicate = load(
        _write_registry(
            root,
            "schema_version: '1.0'\nsuites:\n"
            "  demo:\n    requirement: FR-TEST\n    config: docs/ci/semantic-suites/demo.yaml\n"
            "    runner: demo_eval:evaluate\n"
            "  demo:\n    requirement: FR-TEST\n    config: docs/ci/semantic-suites/demo.yaml\n"
            "    runner: demo_eval:evaluate\n",
        ),
        root,
    )
    assert duplicate["errors"]
    assert load(_write_registry(root, "schema_version: '2.0'\nsuites: {}\n"), root)["errors"]


_APPROVED_SUITE_CONFIG = {
    "schema_version": "1.0",
    "status": "approved",
    "dataset": {"version": "v1", "cases": [{"id": "C1"}]},
    "rubric": {"version": "r1", "definition": "fixed"},
    "thresholds": {"min": 1},
    "model": {"provider": "test", "model": "test-model"},
    "execution": {"runner": "demo_eval:evaluate", "max_completion_requests": 1},
    "approval": {
        "approved_by": "human",
        "approved_at": "2026-11-24T10:00:00Z",
        "evidence": ["https://github.com/o/r/pull/1#issuecomment-1"],
    },
}

_RUNNER_SOURCE = '''
import hashlib
import json
from pathlib import Path

RESULT = {"status": "passed"}


def evaluate(config, candidate_sha, *, output_dir, model_transport=None):
    details = Path(output_dir) / "semantic-details.json"
    body = json.dumps({"candidate_sha": candidate_sha}).encode("utf-8")
    details.write_bytes(body)
    result = {
        "status": "passed",
        "errors": [],
        "needs_review": [],
        "request_count": 1,
        "dataset_sha256": "dsha",
        "rubric_sha256": "rsha",
        "details_path": str(details),
        "details_sha256": hashlib.sha256(body).hexdigest(),
    }
    result.update(RESULT)
    return result
'''


def _semantic_suite_root(tmp_path: Path, result: dict[str, Any] | None = None, crlf: bool = False):
    source = _RUNNER_SOURCE
    if result is not None:
        source = source.replace('RESULT = {"status": "passed"}', f"RESULT = {result!r}")
    root = _suite_root(tmp_path, runner_source=source)
    config_text = yaml.safe_dump(_APPROVED_SUITE_CONFIG, sort_keys=False)
    config_path = root / "docs" / "ci" / "semantic-suites" / "demo.yaml"
    config_path.write_bytes(
        config_text.replace("\n", "\r\n").encode("utf-8") if crlf else config_text.encode("utf-8")
    )
    registry = _write_registry(root, {"demo": _demo_entry()})
    return root, registry, config_text


def _run_suite(root: Path, registry: Path, tmp_path: Path, name: str, suite: str = "demo"):
    record_path = tmp_path / f"{name}.json"
    rc = ci_semantic_eval.main(
        [
            "--registry", str(registry),
            "--suite", suite,
            "--candidate", "cand1",
            "--workflow-sha", "wf1",
            "--run-id", "5",
            "--output", str(record_path),
            "--details-output", str(tmp_path / name / "semantic-details.json"),
        ]
    )
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() else None
    return rc, record


def test_t14_semantic_entry_uses_registered_suite_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import hashlib

    root, registry, config_text = _semantic_suite_root(tmp_path)
    imported: list[str] = []
    original = ci_semantic_eval.load_runner

    def tracking_load(*args: Any, **kwargs: Any):
        imported.append(str(args))
        return original(*args, **kwargs)

    monkeypatch.setattr(ci_semantic_eval, "load_runner", tracking_load)
    rc, record = _run_suite(root, registry, tmp_path, "unknown", suite="no-such-suite")
    assert rc == 1 and record is None and imported == []

    rc, record = _run_suite(root, registry, tmp_path, "pass")
    assert rc == 0
    assert record["suite_id"] == "demo"
    assert record["config_path"] == "docs/ci/semantic-suites/demo.yaml"
    assert record["runner"] == "demo_eval:evaluate"
    assert record["status"] == "passed"
    assert record["needs_review"] == []
    expected_sha = hashlib.sha256(config_text.encode("utf-8")).hexdigest()
    assert record["config_sha256"] == expected_sha
    assert record["config_version"] == "v1"

    crlf_root, crlf_registry, _ = _semantic_suite_root(tmp_path / "crlf", crlf=True)
    _, crlf_record = _run_suite(crlf_root, crlf_registry, tmp_path, "crlf")
    assert crlf_record["config_sha256"] == expected_sha

    review_root, review_registry, _ = _semantic_suite_root(
        tmp_path / "review",
        result={"status": "needs_review", "needs_review": ["C1:ambiguous_claim:x", "C1:unresolved_period:y"]},
    )
    rc, review = _run_suite(review_root, review_registry, tmp_path, "review")
    assert rc == 1
    assert review["status"] == "needs_review"
    assert review["needs_review"] == ["C1:ambiguous_claim:x", "C1:unresolved_period:y"]

    unapproved = copy.deepcopy(_APPROVED_SUITE_CONFIG)
    unapproved["status"] = "unapproved"
    (root / "docs" / "ci" / "semantic-suites" / "demo.yaml").write_text(
        yaml.safe_dump(unapproved), encoding="utf-8"
    )
    rc, record = _run_suite(root, registry, tmp_path, "unapproved")
    assert rc == 1 and record is None

    legacy_out = tmp_path / "legacy.json"
    assert ci_semantic_eval.main(
        [
            "--config", str(root / "docs" / "ci" / "semantic-suites" / "demo.yaml"),
            "--runner", "demo_eval:evaluate",
            "--candidate", "cand1",
            "--workflow-sha", "wf1",
            "--run-id", "5",
            "--output", str(legacy_out),
        ]
    ) == 1
    assert not legacy_out.exists()

    noop_out = tmp_path / "noop.json"
    assert ci_semantic_eval.main(
        [
            "--candidate", "cand1",
            "--workflow-sha", "wf1",
            "--run-id", "5",
            "--output", str(noop_out),
            "--not-applicable",
            "--reason", "layout only",
            "--reviewer", "human",
            "--approval-evidence", "https://github.com/o/r/pull/1#pullrequestreview-1",
        ]
    ) == 0
    assert json.loads(noop_out.read_text(encoding="utf-8"))["status"] == "not_applicable"
    assert ci_semantic_eval.main(["check-suite", "--registry", str(registry), "--suite", "demo"]) == 0
    assert ci_semantic_eval.main(["check-suite", "--registry", str(registry), "--suite", "x"]) == 1


def _run_steps(workflow: dict[str, Any], job: str) -> list[dict[str, Any]]:
    return workflow["jobs"][job]["steps"]


def test_t15_workflows_route_by_validated_suite():
    trusted_text = (ROOT / ".github" / "workflows" / "trusted-evaluation.yml").read_text(
        encoding="utf-8"
    )
    trusted = yaml.safe_load(trusted_text)
    inputs = trusted[True]["workflow_dispatch"]["inputs"]
    assert "suite_id" in inputs
    assert "semantic_runner" not in inputs
    for step in _run_steps(trusted, "evaluate"):
        assert "${{ inputs." not in str(step.get("run", "")), step.get("name")
    names = {step.get("name"): step for step in _run_steps(trusted, "evaluate")}
    resolve = names["Resolve status context"]
    assert "check-suite" in resolve["run"]
    semantic = names["Write semantic evidence record"]
    assert "--suite" in semantic["run"] and "--registry docs/ci/semantic-suites.yaml" in semantic["run"]
    assert "--runner" not in semantic["run"] and "--config" not in semantic["run"]
    assert semantic["env"]["DEEPSEEK_API_KEY"] == "${{ secrets.DEEPSEEK_API_KEY }}"
    assert "steps.resolve.outputs.artifact_suffix" in str(names["Upload evidence record"]["with"]["name"])
    assert "steps.resolve.outputs.suite" in str(
        names["Upload semantic details artifact"]["with"]["name"]
    )
    status_step = names["Write candidate status"]
    assert status_step["env"]["CONTEXT"] == "${{ steps.resolve.outputs.context }}"
    assert "describe" in status_step["run"]
    assert "inputs.suite_id" in trusted["concurrency"]["group"]
    secret_steps = [s.get("name") for s in _run_steps(trusted, "evaluate") if "secrets." in json.dumps(s)]
    assert set(secret_steps) <= {"Write semantic evidence record", "Run live suite", "Write candidate status"}

    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    evidence = ci["jobs"]["evidence-check"]
    assert evidence["permissions"]["pull-requests"] == "read"
    checkouts = [s for s in evidence["steps"] if str(s.get("uses", "")).startswith("actions/checkout")]
    assert any(
        s["with"].get("ref") == "${{ github.event.repository.default_branch }}"
        and s["with"].get("path") == "trusted"
        for s in checkouts
    )
    evidence_text = json.dumps(evidence)
    assert "--registry trusted/docs/ci/semantic-suites.yaml" in evidence_text
    assert "--trusted-root trusted" in evidence_text
    assert "secrets." not in evidence_text


def test_t16_fr10_config_migrated_unchanged_to_financial_metrics_suite():
    import hashlib

    config = ROOT / "docs" / "ci" / "semantic_eval.yaml"
    assert hashlib.sha256(config.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == _FM_CONFIG_LF_SHA256
    assert ci_checks.sha256_lf(config) == _FM_CONFIG_LF_SHA256
    assert ci_checks.load_yaml(config)["status"] == "unapproved"
    registry = ci_checks.load_suite_registry(ROOT / "docs" / "ci" / "semantic-suites.yaml", ROOT)
    assert registry["errors"] == []
    assert registry["suites"] == {
        "financial-metrics": {
            "requirement": "FR-10",
            "config": "docs/ci/semantic_eval.yaml",
            "runner": "financial_metrics_eval:evaluate",
        }
    }
    states, errors = ci_checks.trusted_suite_states(ROOT / "docs" / "ci" / "semantic-suites.yaml", ROOT)
    assert errors == []
    assert states["financial-metrics"]["approved"] is False
    assert states["financial-metrics"]["config_sha256"] == _FM_CONFIG_LF_SHA256


def test_t17_registry_absent_on_default_branch(tmp_path: Path):
    states, errors = ci_checks.trusted_suite_states(tmp_path / "docs" / "ci" / "semantic-suites.yaml", tmp_path)
    assert states is None and errors == []
    assert _evidence([], {}, semantic_required=False, selection=None, trusted_suites=None)["errors"] == []
    blocked = _evidence(
        [_status(_FM_CONTEXT, "cand1", 7)],
        {"7": _run(7, _record("semantic"))},
        trusted_suites=None,
    )["errors"]
    assert any("registry is not present on the default branch" in error for error in blocked)


def test_t18_registered_suites_conform_to_runner_contract(tmp_path: Path):
    registry = ci_checks.load_suite_registry(ROOT / "docs" / "ci" / "semantic-suites.yaml", ROOT)
    assert registry["errors"] == []
    for suite_id, entry in registry["suites"].items():
        config = ci_checks.load_yaml(ROOT / entry["config"])
        validation = ci_semantic_eval.validate_config(config)
        assert validation["errors"] == [], suite_id
        assert config["execution"]["runner"] == entry["runner"], suite_id
        function = ci_semantic_eval.load_runner(ROOT, entry["runner"])
        assert ci_semantic_eval.check_runner_signature(function) == [], suite_id

    def good(config, candidate_sha, *, output_dir, model_transport=None):
        return {}

    def no_output_dir(config, candidate_sha):
        return {}

    def no_transport(config, candidate_sha, *, output_dir):
        return {}

    assert ci_semantic_eval.check_runner_signature(good) == []
    assert ci_semantic_eval.check_runner_signature(no_output_dir)
    assert ci_semantic_eval.check_runner_signature(no_transport)

    for name, result in (
        ("missing-status", {"errors": []}),
        ("bad-status", {"status": "ok"}),
        ("bad-review", {"status": "passed", "needs_review": "C1:x"}),
    ):
        root, registry_path, _ = _semantic_suite_root(tmp_path / name, result=result)
        if name == "missing-status":
            source = (root / "scripts" / "demo_eval.py").read_text(encoding="utf-8")
            source = source.replace('"status": "passed",\n        "errors"', '"errors"')
            (root / "scripts" / "demo_eval.py").write_text(source, encoding="utf-8")
        rc, record = _run_suite(root, registry_path, tmp_path, name)
        assert rc == 1, name
        assert record["status"] == "failed", name
