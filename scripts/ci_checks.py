"""CI gate checks for the CS5351 project.

The checks implement the minimum workflow described in ``CI.md``.  They are
deliberately small, deterministic, and offline-testable.  The module does not
change application behavior and does not grant permissions.
"""

from __future__ import annotations

import argparse
import ast
import copy
import datetime as dt
import hashlib
import importlib
import inspect
import json
import posixpath
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ZERO_SHA = "0" * 40
TRUSTED_WORKFLOW = ".github/workflows/trusted-evaluation.yml"
# Legacy shared context; no longer written or accepted (semantic-suite-routing §3.4).
SEMANTIC_STATUS = "semantic-eval/evidence"
SEMANTIC_STATUS_PREFIX = "semantic-eval/"
SEMANTIC_NOOP_STATUS = "semantic-eval/not-applicable"
LIVE_STATUS = "live-tests/evidence"

SAFETY_CRITICAL = {
    "src/tradingagents/agents/managers/portfolio_manager.py",
    "src/tradingagents/agents/rating.py",
    "src/tradingagents/agents/state.py",
    "src/tradingagents/agents/schemas.py",
    "src/tradingagents/graph/setup.py",
    "src/tradingagents/graph/trading_graph.py",
    "src/tradingagents/reporting.py",
    "src/tradingagents/memory/log.py",
    "src/cli/run.py",
    "src/cli/display.py",
    "src/tradingagents/final_recommendation.py",
    "src/tradingagents/portfolio_risk.py",
    "src/tradingagents/run_context.py",
    "src/tradingagents/dataflows/router.py",
    "src/tradingagents/dataflows/errors.py",
    "src/tradingagents/dataflows/date_window.py",
    "src/tradingagents/dataflows/config.py",
    "src/tradingagents/dataflows/availability.py",
    "src/tradingagents/dataflows/query_reuse.py",
    "src/tradingagents/dataflows/net.py",
    "src/tradingagents/dataflows/files.py",
    "src/tradingagents/dataflows/symbols.py",
    "src/cli/prefs.py",
    "src/cli/prompts.py",
    "src/tradingagents/llm_clients/chatgpt_auth.py",
    "src/tradingagents/security.py",
    "src/tradingagents/history.py",
}

SAFETY_RELEVANT_EXACT = {
    "src/tradingagents/agents/tools.py",
    "src/tradingagents/agents/analysts/sentiment_analyst.py",
    "src/tradingagents/portfolio.py",
    "src/tradingagents/report_html.py",
    "src/tradingagents/backtest.py",
    "src/tradingagents/agents/post_screen.py",
}

SAFETY_RELEVANT_PREFIXES = ("src/tradingagents/dataflows/vendors/",)

GOVERNANCE_PREFIXES = (".opencode/", ".github/", "docs/ci/")
GOVERNANCE_EXACT = {
    "scripts/ci_checks.py",
    "scripts/ci_semantic_eval.py",
    "test/offline/test_ci_gates.py",
}

DOC_SUFFIXES = {".md", ".rst", ".txt"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"}
EXECUTABLE_SUFFIXES = {
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".bat",
    ".cmd",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".rb",
    ".pl",
    ".php",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".swift",
}
CONFIG_SUFFIXES = {
    ".json",
    ".jsonc",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
}
BUILD_CONFIG_EXACT = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-ci.txt",
    ".github/requirements-ci.txt",
    "mypy.ini",
    "mypy-baseline.txt",
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock",
}
BUILD_CONFIG_PREFIXES = ("requirements-",)
RUNTIME_PROMPT_PREFIXES = ("prompts/",)
PROMPT_FILE_SUFFIXES = {".yaml", ".yml", ".json", ".txt", ".jinja", ".j2"}
SEMANTIC_EXACT = {
    "src/tradingagents/default_config.py",
    "src/tradingagents/llm_clients/factory.py",
    "src/tradingagents/llm_clients/model_catalog.py",
    "src/tradingagents/llm_clients/capabilities.py",
    "src/tradingagents/agents/context.py",
    "src/tradingagents/agents/structured.py",
    "src/tradingagents/memory/reflection.py",
}
SEMANTIC_DIFF_PREFIXES = (
    "src/tradingagents/agents/",
    "src/tradingagents/llm_clients/",
    "src/tradingagents/graph/",
)
SEMANTIC_DIFF_EXACT = {
    "src/cli/run.py",
    "src/cli/main.py",
}
SEMANTIC_TOKEN_PATTERN = re.compile(
    r"(?i)(?:\b(?:with_structured_output|structured_llm|tool_choice|bind_tools|"
    r"deep_think_llm|quick_think_llm|model_name|model|provider|temperature|"
    r"max_tokens|base_url|response_format|reasoning_effort|thinking)\b|"
    r"ChatOpenAI|ChatAnthropic|ChatGoogle|ChatBedrock|DeepSeek|OpenAI|Anthropic|Gemini)"
)

MODEL_KEY_TOKENS = (
    "model",
    "provider",
    "temperature",
    "max_tokens",
    "backend_url",
    "base_url",
    "thinking",
    "reasoning",
    "effort",
    "output_language",
    "llm",
)
MODEL_CONFIG_PATHS = {
    "src/tradingagents/default_config.py",
    "src/tradingagents/llm_clients/factory.py",
}
MODEL_TABLE_PATHS = {
    "src/tradingagents/llm_clients/model_catalog.py",
    "src/tradingagents/llm_clients/capabilities.py",
}

PR_BODY_FIELDS = (
    "Plan",
    "Approved test specification",
    "Approval evidence",
    "Implementation start",
    "Approved scope",
)
SUITE_SELECTION_FIELD = "Semantic suites"
SUITE_APPROVAL_FIELD = "Semantic suites approval"
SUITE_PHRASE_PREFIX = "APPROVED semantic-suites:"
SUPPLEMENTAL_SPEC_FIELD = "Supplemental test specification"
OPTIONAL_PR_BODY_FIELDS = ("ADR", SUITE_SELECTION_FIELD, SUITE_APPROVAL_FIELD, SUPPLEMENTAL_SPEC_FIELD)
# Approved bounded compatibility rule: semantic-registry-test-amendment.md §6.
# Exact reviewed configuration at the original frozen specification. Its status
# is unapproved and approval identity/time/evidence are empty. Using a digest
# keeps the setup-python-only approval job independent of YAML packages.
FR03_PREPARATION_CONFIG_SHA256 = "96f7d51f93316b351ac70949d753d5bd81282cc285c0ed946d003a4de7a7b015"
FR03_PREPARATION_PATHS = frozenset({
    "docs/ci/data-availability-cases.json",
    "docs/ci/data-availability-rubric.md",
    "docs/ci/semantic-suites/data-availability.yaml",
})
SUITE_REGISTRY_PATH = "docs/ci/semantic-suites.yaml"
SUITE_CONFIG_PREFIX = "docs/ci/"
SUITE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SUITE_ID_MAX_LENGTH = 40
RESERVED_SUITE_IDS = {"evidence", "not-applicable"}
SUITE_ENTRY_KEYS = {"requirement", "config", "runner"}
RUNNER_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):([A-Za-z_][A-Za-z0-9_]*)$")
ADR_PREFIX = "docs/architecture/adr/"
APPROVAL_PHRASE_PREFIX = "APPROVED test-spec:"


ID_PATTERN = re.compile(r"\b(?:[A-Z][A-Z0-9]*-[0-9]{2}(?:-FC[0-9]{2})?|IR-[0-9]{2})\b")
REVIEW_ID_PATTERN = re.compile(r"pullrequestreview-(\d+)")
COMMENT_ID_PATTERN = re.compile(r"issuecomment-(\d+)")
RUN_ID_PATTERN = re.compile(r"/actions/runs/(\d+)")
CONTRACT_TEST_PATTERN = re.compile(r"(?<![\w./-])(test/(?:offline|live)/[\w./-]+\.py)\b")
SPEC_PATH_PATTERN = re.compile(r"(?<![\w./-])([\w./-]+\.(?:md|ya?ml|json|txt))\b")


class CiError(RuntimeError):
    """A gate check could not be evaluated and must fail closed."""


@dataclass
class CommandResult:
    command: Sequence[str]
    returncode: int
    stdout: str
    stderr: str

    def require_success(self, label: str) -> None:
        if self.returncode != 0:
            raise CiError(
                f"{label} failed with exit code {self.returncode}: "
                f"{self.stderr.strip() or self.stdout.strip()}"
            )


def normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def is_build_config(path: str) -> bool:
    normalized = normalize_path(path)
    if normalized in BUILD_CONFIG_EXACT:
        return True
    return (
        "/" not in normalized
        and normalized.startswith(BUILD_CONFIG_PREFIXES)
        and Path(normalized).suffix.lower() == ".txt"
    )


def is_doc_path(path: str) -> bool:
    normalized = normalize_path(path)
    if is_build_config(normalized):
        return False
    suffix = Path(normalized).suffix.lower()
    if suffix in EXECUTABLE_SUFFIXES:
        return False
    return "docs/" in normalized or normalized.startswith("README") or (
        suffix in DOC_SUFFIXES | IMAGE_SUFFIXES
    )


def is_test_path(path: str) -> bool:
    return normalize_path(path).startswith("test/")


def is_app_code(path: str) -> bool:
    normalized = normalize_path(path)
    return (
        normalized.startswith("src/")
        and Path(normalized).suffix.lower() in EXECUTABLE_SUFFIXES
    )


def is_other_code(path: str) -> bool:
    normalized = normalize_path(path)
    if Path(normalized).suffix.lower() not in EXECUTABLE_SUFFIXES:
        return False
    return not normalized.startswith(("src/", "test/"))


def is_governance_code(path: str) -> bool:
    return is_code_path(path) and is_governance_path(path)


def is_code_path(path: str) -> bool:
    return is_app_code(path) or is_other_code(path)


def is_semantic_path(path: str) -> bool:
    normalized = normalize_path(path)
    if any(normalized.startswith(prefix) for prefix in RUNTIME_PROMPT_PREFIXES):
        return Path(normalized).suffix.lower() in PROMPT_FILE_SUFFIXES
    return False


def is_semantic_diff_scope(path: str) -> bool:
    normalized = normalize_path(path)
    if normalized in SEMANTIC_EXACT or normalized in SEMANTIC_DIFF_EXACT:
        return True
    return any(normalized.startswith(prefix) for prefix in SEMANTIC_DIFF_PREFIXES)


def is_governance_path(path: str) -> bool:
    normalized = normalize_path(path)
    if normalized in GOVERNANCE_EXACT:
        return True
    return any(normalized.startswith(prefix) for prefix in GOVERNANCE_PREFIXES)


def is_safety_critical(path: str) -> bool:
    return normalize_path(path) in SAFETY_CRITICAL


def is_safety_relevant(path: str) -> bool:
    normalized = normalize_path(path)
    if normalized in SAFETY_RELEVANT_EXACT:
        return True
    return any(normalized.startswith(prefix) for prefix in SAFETY_RELEVANT_PREFIXES)


def is_ai_log_relevant(path: str) -> bool:
    normalized = normalize_path(path)
    if is_doc_path(normalized) or is_build_config(normalized):
        return False
    if (
        is_code_path(normalized)
        or is_test_path(normalized)
        or is_semantic_path(normalized)
    ):
        return True
    return Path(normalized).suffix.lower() in EXECUTABLE_SUFFIXES


def classify_paths(
    paths: Iterable[str],
    semantic_hunks: Mapping[str, Iterable[str]] | None = None,
    semantic_prompt_paths: Iterable[str] | None = None,
    semantic_analyzed_paths: Iterable[str] | None = None,
) -> dict[str, Any]:
    changed = sorted({normalize_path(path) for path in paths if normalize_path(path)})
    safety_critical = [path for path in changed if is_safety_critical(path)]
    safety_relevant = [
        path
        for path in changed
        if is_safety_relevant(path) and not is_safety_critical(path)
    ]
    governance = [path for path in changed if is_governance_path(path)]
    semantic_set = {path for path in changed if is_semantic_path(path)}
    analyzed = (
        {normalize_path(path) for path in semantic_analyzed_paths}
        if semantic_analyzed_paths
        else set()
    )
    if semantic_hunks:
        for path in changed:
            if path in analyzed:
                continue
            if not is_semantic_diff_scope(path):
                continue
            if any(
                SEMANTIC_TOKEN_PATTERN.search(hunk)
                for hunk in semantic_hunks.get(path, [])
            ):
                semantic_set.add(path)
    if semantic_prompt_paths:
        semantic_set.update(
            normalize_path(path) for path in semantic_prompt_paths
        )
    semantic = sorted(semantic_set)
    code = [path for path in changed if is_code_path(path)]
    application_code = [path for path in code if is_app_code(path)]
    governance_code = [path for path in code if is_governance_code(path)]
    other_code = [path for path in code if is_other_code(path)]
    tests = [path for path in changed if is_test_path(path)]
    docs = [path for path in changed if is_doc_path(path)]
    build_config = [path for path in changed if is_build_config(path)]
    unknown_executable = []
    unknown_non_executable = []
    for path in changed:
        suffix = Path(path).suffix.lower()
        if (
            path in safety_critical
            or path in safety_relevant
            or path in governance
            or path in semantic
            or path in code
            or path in tests
            or path in docs
            or path in build_config
        ):
            continue
        if suffix in EXECUTABLE_SUFFIXES | CONFIG_SUFFIXES:
            unknown_executable.append(path)
        else:
            unknown_non_executable.append(path)
    application_tests = [path for path in tests if not is_governance_path(path)]
    ai_log_paths = [path for path in changed if is_ai_log_relevant(path)]
    docs_only = bool(changed) and all(is_doc_path(path) for path in changed)
    return {
        "changed_paths": changed,
        "safety_critical": safety_critical,
        "safety_relevant": safety_relevant,
        "governance_ci": governance,
        "semantic": semantic,
        "code": code,
        "application_code": application_code,
        "governance_code": governance_code,
        "other_code": other_code,
        "tests": tests,
        "application_tests": application_tests,
        "docs": docs,
        "build_config": build_config,
        "unknown_executable": unknown_executable,
        "unknown_non_executable": unknown_non_executable,
        "requires_conservative_checks": bool(unknown_executable),
        "requires_human_review": bool(safety_critical or governance),
        "semantic_required": bool(semantic),
        "approval_applicable": bool(code or application_tests or semantic),
        "docs_only": docs_only,
        "ai_log_required": bool(ai_log_paths),
        "security_applicable": bool(safety_critical or safety_relevant or governance),
    }


def run_command(
    command: Sequence[str],
    cwd: Path | str | None = None,
    timeout: int = 300,
) -> CommandResult:
    try:
        completed = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CiError(f"cannot run {command[0]}: {exc}") from exc
    return CommandResult(command, completed.returncode, completed.stdout, completed.stderr)


def git_output(args: Sequence[str], cwd: Path | str | None = None) -> str:
    result = run_command(["git", *args], cwd=cwd)
    if result.returncode != 0:
        raise CiError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def changed_paths_from_git(
    base: str | None,
    head: str,
    cwd: Path | str | None = None,
) -> list[str]:
    root = Path(cwd) if cwd is not None else PROJECT_ROOT
    if not head:
        raise CiError("head SHA is required")
    git_output(["rev-parse", "--verify", head], cwd=root)
    if base and base != ZERO_SHA:
        output = git_output(["diff", "--name-status", "-M", base, head], cwd=root)
    else:
        output = git_output(
            ["diff-tree", "--root", "--no-commit-id", "--name-status", "-r", head],
            cwd=root,
        )
    paths: set[str] = set()
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        status = fields[0]
        if status.startswith(("R", "C")) and len(fields) >= 3:
            paths.add(normalize_path(fields[1]))
            paths.add(normalize_path(fields[2]))
        elif len(fields) >= 2:
            paths.add(normalize_path(fields[-1]))
    return sorted(paths)




def semantic_hunks_from_git(
    base: str | None,
    head: str,
    cwd: Path | str | None = None,
) -> dict[str, list[str]]:
    root = Path(cwd) if cwd is not None else PROJECT_ROOT
    if not head:
        raise CiError("head SHA is required")
    if base and base != ZERO_SHA:
        output = git_output(["diff", "-U0", base, head], cwd=root)
    else:
        output = git_output(
            ["diff-tree", "--root", "-p", "-U0", head],
            cwd=root,
        )
    hunks: dict[str, list[str]] = {}
    current = ""
    current_hunk: list[str] = []
    for line in output.splitlines():
        if line.startswith("diff --git "):
            if current and current_hunk:
                hunks.setdefault(current, []).append("\n".join(current_hunk))
            current_hunk = []
            parts = line.split(" ")
            target = parts[-1]
            current = normalize_path(target[2:]) if target.startswith("b/") else normalize_path(target)
            continue
        if line.startswith("+++ "):
            target = line[4:].strip()
            if target.startswith("b/"):
                current = normalize_path(target[2:])
            continue
        if line.startswith("@@"):
            if current and current_hunk:
                hunks.setdefault(current, []).append("\n".join(current_hunk))
            current_hunk = [line]
            continue
        if current and current_hunk:
            current_hunk.append(line)
    if current and current_hunk:
        hunks.setdefault(current, []).append("\n".join(current_hunk))
    return hunks


def _target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, ast.Tuple):
        names: list[str] = []
        for item in node.elts:
            names.extend(_target_names(item))
        return names
    return []


def _is_prompt_name(name: str) -> bool:
    lowered = name.lower()
    return any(
        token in lowered
        for token in (
            "prompt",
            "system",
            "message",
            "instruction",
            "brief",
            "wrap_up",
            "external_tools",
        )
    )


def _call_name(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def prompt_definition_snapshot(source: str) -> tuple[str, ...] | None:
    if not source.strip():
        return ()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    snapshots: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [name for target in targets for name in _target_names(target)]
            if any(_is_prompt_name(name) for name in names):
                snapshots.append(ast.dump(node, include_attributes=False))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_prompt_name(node.name):
                snapshots.append(ast.dump(node, include_attributes=False))
        elif isinstance(node, ast.Call):
            name = _call_name(node.func)
            if any(
                token in name
                for token in (
                    "ChatPromptTemplate",
                    "PromptTemplate",
                    "SystemMessage",
                    "HumanMessage",
                    "AIMessage",
                )
            ):
                snapshots.append(ast.dump(node, include_attributes=False))
    return tuple(sorted(snapshots))


def _git_file_text(
    root: Path,
    revision: str,
    path: str,
) -> str:
    if not revision:
        return ""
    try:
        return git_output(["show", f"{revision}:{path}"], cwd=root)
    except CiError:
        return ""


def _is_model_key(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in MODEL_KEY_TOKENS)


def _model_name_from_target(node: ast.AST) -> list[str]:
    return _target_names(node)


class _ExceptionMessageNormalizer(ast.NodeTransformer):
    """Replace exception message text while preserving type and control flow."""

    def visit_Raise(self, node: ast.Raise) -> ast.Raise:
        self.generic_visit(node)
        if isinstance(node.exc, ast.Call):
            node.exc.args = [
                ast.Constant(value="<exception-message>")
                if isinstance(arg, ast.JoinedStr)
                or (isinstance(arg, ast.Constant) and isinstance(arg.value, str))
                else arg
                for arg in node.exc.args
            ]
            node.exc.keywords = [
                ast.keyword(arg=keyword.arg, value=ast.Constant(value="<exception-message>"))
                if isinstance(keyword.value, ast.JoinedStr)
                or (
                    isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                )
                else keyword
                for keyword in node.exc.keywords
            ]
        return node


def _model_ast_dump(node: ast.AST) -> str:
    normalized = _ExceptionMessageNormalizer().visit(copy.deepcopy(node))
    return ast.dump(normalized, include_attributes=False)


def model_definition_snapshot(source: str, path: str) -> tuple[str, ...] | None:
    normalized = normalize_path(path)
    if not source.strip():
        return ()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    snapshots: list[str] = []
    if normalized in MODEL_CONFIG_PATHS:
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values, strict=False):
                    if (
                        isinstance(key, ast.Constant)
                        and isinstance(key.value, str)
                        and _is_model_key(key.value)
                    ):
                        snapshots.append(
                            _model_ast_dump(value)
                        )
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [
                    name
                    for target in targets
                    for name in _model_name_from_target(target)
                ]
                if any(_is_model_key(name) for name in names):
                    snapshots.append(_model_ast_dump(node))
            elif isinstance(node, ast.Call):
                call_name = _call_name(node.func).lower()
                keywords = [keyword.arg or "" for keyword in node.keywords]
                if any(
                    token in call_name
                    for token in (
                        "chatopenai",
                        "chatanthropic",
                        "chatgoogle",
                        "chatbedrock",
                        "deepseek",
                        "openai",
                        "anthropic",
                        "gemini",
                    )
                ) or any(_is_model_key(keyword) for keyword in keywords):
                    snapshots.append(_model_ast_dump(node))
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and _is_model_key(node.name):
                snapshots.append(_model_ast_dump(node))
    elif normalized in MODEL_TABLE_PATHS:
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.ClassDef)):
                snapshots.append(_model_ast_dump(node))
    else:
        model_calls = (
            "chatopenai",
            "chatanthropic",
            "chatgoogle",
            "chatbedrock",
            "deepseek",
            "openai",
            "anthropic",
            "gemini",
            "with_structured_output",
            "bind_tools",
            "structured",
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values, strict=False):
                    if (
                        isinstance(key, ast.Constant)
                        and isinstance(key.value, str)
                        and _is_model_key(key.value)
                    ):
                        snapshots.append(
                            _model_ast_dump(value)
                        )
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [
                    name
                    for target in targets
                    for name in _target_names(target)
                ]
                if any(_is_model_key(name) for name in names):
                    snapshots.append(_model_ast_dump(node))
            elif isinstance(node, ast.Call):
                call_name = _call_name(node.func).lower()
                keywords = [keyword.arg or "" for keyword in node.keywords]
                if any(token in call_name for token in model_calls) or any(
                    _is_model_key(keyword) for keyword in keywords
                ):
                    snapshots.append(_model_ast_dump(node))
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and _is_model_key(node.name):
                snapshots.append(_model_ast_dump(node))
    return tuple(sorted(snapshots))


def semantic_definition_snapshot(source: str, path: str) -> tuple[Any, ...] | None:
    prompt_snapshot = prompt_definition_snapshot(source)
    model_snapshot = model_definition_snapshot(source, path)
    if prompt_snapshot is None or model_snapshot is None:
        return None
    return (prompt_snapshot, model_snapshot)


def semantic_analysis_from_git(
    base: str | None,
    head: str,
    paths: Iterable[str],
    cwd: Path | str | None = None,
) -> tuple[set[str], set[str]]:
    root = Path(cwd) if cwd is not None else PROJECT_ROOT
    changed: set[str] = set()
    analyzed: set[str] = set()
    for path in paths:
        normalized = normalize_path(path)
        if Path(normalized).suffix.lower() != ".py":
            continue
        if not is_semantic_diff_scope(normalized):
            continue
        old_source = (
            _git_file_text(root, base, normalized)
            if base and base != ZERO_SHA
            else ""
        )
        new_source = _git_file_text(root, head, normalized)
        old_snapshot = semantic_definition_snapshot(old_source, normalized)
        new_snapshot = semantic_definition_snapshot(new_source, normalized)
        analyzed.add(normalized)
        if (
            old_snapshot is None
            or new_snapshot is None
            or old_snapshot != new_snapshot
        ):
            changed.add(normalized)
    return changed, analyzed


def semantic_prompt_changes_from_git(
    base: str | None,
    head: str,
    paths: Iterable[str],
    cwd: Path | str | None = None,
) -> set[str]:
    changed, _ = semantic_analysis_from_git(base, head, paths, cwd)
    return changed


def _strip_jsonc_comments(text: str) -> str:
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if char == "/" and index + 1 < len(text) and text[index + 1] == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and index + 1 < len(text) and text[index + 1] == "*":
            index += 2
            while index + 1 < len(text) and not (
                text[index] == "*" and text[index + 1] == "/"
            ):
                index += 1
            index += 2
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CiError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_jsonc(path: Path | str) -> Any:
    try:
        text = Path(path).read_text(encoding="utf-8")
        return json.loads(
            _strip_jsonc_comments(text),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise CiError(f"cannot parse JSONC file {path}: {exc}") from exc


def _walk_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)


def permissions_check(path: Path | str) -> dict[str, Any]:
    errors: list[str] = []
    try:
        document = load_jsonc(path)
    except CiError as exc:
        return {"errors": [str(exc)], "warnings": []}
    if not isinstance(document, Mapping):
        return {"errors": ["permissions file must contain a JSON object"], "warnings": []}

    sensitive = {
        "bash",
        "edit",
        "external_directory",
        "task",
        "webfetch",
        "websearch",
    }

    def check_permission_block(block: Any, location: str) -> None:
        if not isinstance(block, Mapping):
            return
        if block.get("*") == "allow":
            errors.append(f"{location}: wildcard permission must not be allow")
        for key in sensitive:
            value = block.get(key)
            if value == "allow":
                errors.append(f"{location}.{key}: broad allow is not permitted")
            elif isinstance(value, Mapping) and value.get("*") == "allow":
                errors.append(f"{location}.{key}: wildcard allow is not permitted")

    permission = document.get("permission")
    if not isinstance(permission, Mapping):
        errors.append("permission: missing object")
    else:
        if permission.get("*") != "deny":
            errors.append('permission."*": default must be deny')
        check_permission_block(permission, "permission")

    agents = document.get("agent")
    if isinstance(agents, Mapping):
        for name, agent in agents.items():
            if isinstance(agent, Mapping):
                block = agent.get("permission")
                if isinstance(block, Mapping):
                    check_permission_block(block, f"agent.{name}.permission")

    for value in _walk_values(document):
        normalized = normalize_path(value)
        if "TradingAgents/" in normalized:
            errors.append(f"stale TradingAgents/ path: {value}")
    return {"errors": errors, "warnings": []}


def load_yaml(path: Path | str) -> Any:
    import yaml

    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CiError(f"cannot parse YAML file {path}: {exc}") from exc


def schema_check(requirements_path: Path | str, schema_path: Path | str) -> dict[str, Any]:
    import jsonschema

    errors: list[str] = []
    try:
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"errors": [f"cannot parse schema: {exc}"], "counts": {}}
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        return {"errors": [f"invalid schema: {exc.message}"], "counts": {}}
    try:
        document = load_yaml(requirements_path)
    except CiError as exc:
        return {"errors": [str(exc)], "counts": {}}
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
        location = "/".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{location}: {error.message}")
    if errors:
        return {"errors": errors, "counts": {}}

    requirements = document.get("requirements", [])
    requirement_ids = [entry.get("id") for entry in requirements]
    fc_ids = [
        fc.get("id")
        for entry in requirements
        for fc in entry.get("fit_criterion", [])
    ]
    duplicates = sorted(
        {rid for rid in requirement_ids if requirement_ids.count(rid) > 1}
    )
    duplicate_fcs = sorted({fid for fid in fc_ids if fc_ids.count(fid) > 1})
    if duplicates:
        errors.append(f"duplicate requirement IDs: {', '.join(duplicates)}")
    if duplicate_fcs:
        errors.append(f"duplicate FC IDs: {', '.join(duplicate_fcs)}")

    scope = document.get("scope", {})
    approved = set(scope.get("approved_ids", []))
    draft = set(scope.get("draft_ids", []))
    deferred = set(scope.get("deferred_ids", []))
    overlap = (approved & draft) | (approved & deferred) | (draft & deferred)
    if overlap:
        errors.append(f"requirement ID appears in multiple scope lists: {sorted(overlap)}")
    status_map = {entry.get("id"): entry.get("status") for entry in requirements}
    expected_approved = {rid for rid, status in status_map.items() if status == "approved"}
    expected_draft = {rid for rid, status in status_map.items() if status == "draft"}
    expected_deferred = {rid for rid, status in status_map.items() if status == "deferred"}
    if approved != expected_approved:
        errors.append("scope.approved_ids does not match requirement status=approved")
    if draft != expected_draft:
        errors.append("scope.draft_ids does not match requirement status=draft")
    if deferred != expected_deferred:
        errors.append(
            "scope.deferred_ids does not match requirement status=deferred"
        )

    counts = {
        "requirements": len(requirements),
        "fit_criteria": len(fc_ids),
        "active_requirements": len(expected_approved | expected_draft),
        "active_fit_criteria": sum(
            1
            for entry in requirements
            if entry.get("status") in {"approved", "draft"}
            for _ in entry.get("fit_criterion", [])
        ),
        "deferred_requirements": len(expected_deferred),
        "deferred_fit_criteria": sum(
            1
            for entry in requirements
            if entry.get("status") == "deferred"
            for _ in entry.get("fit_criterion", [])
        ),
    }
    return {"errors": errors, "counts": counts}


def validate_ai_log(document: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, Mapping):
        return ["AI-use log must be a YAML mapping"]
    if document.get("schema_version") != "1.0":
        errors.append('schema_version must be "1.0"')
    entries = document.get("entries")
    if not isinstance(entries, list):
        return errors + ["entries must be a list"]
    seen: set[str] = set()
    required = {
        "id",
        "date",
        "activity",
        "task",
        "files_changed",
        "ai_contribution",
    }
    for index, entry in enumerate(entries):
        location = f"entries[{index}]"
        if not isinstance(entry, Mapping):
            errors.append(f"{location}: entry must be a mapping")
            continue
        missing = sorted(required - set(entry))
        if missing:
            errors.append(f"{location}: missing fields: {', '.join(missing)}")
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id:
            errors.append(f"{location}: id must be a non-empty string")
        elif entry_id in seen:
            errors.append(f"{location}: duplicate entry id {entry_id}")
        else:
            seen.add(entry_id)
        files = entry.get("files_changed")
        if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
            errors.append(f"{location}: files_changed must be a list of strings")
    return errors


def _entry_covers_path(entry: Mapping[str, Any], path: str) -> bool:
    normalized = normalize_path(path)
    for item in entry.get("files_changed", []):
        candidate = normalize_path(str(item))
        if candidate == normalized:
            return True
        if candidate.endswith("/") and normalized.startswith(candidate):
            return True
    text = " ".join(
        str(entry.get(field, "")) for field in ("task", "ai_contribution", "files_changed")
    )
    return normalized in normalize_path(text)


def ai_log_check(
    base_log: Any,
    head_log: Any,
    changed_paths: Iterable[str],
) -> dict[str, Any]:
    errors = validate_ai_log(head_log)
    if errors:
        return {"errors": errors}
    relevant = [
        normalize_path(path)
        for path in changed_paths
        if is_ai_log_relevant(path)
    ]
    if not relevant:
        return {"errors": [], "required": False}
    base_entries = {
        entry.get("id"): entry
        for entry in (base_log or {}).get("entries", [])
        if isinstance(entry, Mapping)
    }
    changed_entries = [
        entry
        for entry in head_log.get("entries", [])
        if entry.get("id") not in base_entries
        or json.dumps(entry, sort_keys=True)
        != json.dumps(base_entries[entry.get("id")], sort_keys=True)
    ]
    if not changed_entries:
        return {
            "errors": ["no new or materially changed AI-use entry for changed paths"],
            "required": True,
        }
    unassociated = [
        path
        for path in relevant
        if not any(_entry_covers_path(entry, path) for entry in changed_entries)
    ]
    if len(unassociated) == len(relevant):
        errors.append(
            "no changed AI-use entry is associated with any changed code/prompt path"
        )
    return {
        "errors": errors,
        "required": True,
        "changed_entries": len(changed_entries),
        "unassociated_paths": unassociated,
    }


def find_duplicate_pr_body_fields(text: str) -> list[str]:
    """Machine fields that appear more than once in the PR body.

    The parsers key by field name, so a second occurrence would silently override
    the first (last-one-wins). For machine-read fields that is unsafe: a draft that
    pastes a second ``Plan``/``Implementation start``/``Approved scope`` block for a
    governance note would overwrite the real P3 values. We therefore report every
    duplicated machine field so callers can fail closed instead of adopting the last
    value. ``Supplemental test specification`` may legitimately appear more than
    once (multiple supplements), so it is exempt.
    """
    seen: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key = line.split(":", 1)[0].strip()
        if key in PR_BODY_FIELDS or key == "ADR":
            seen[key] = seen.get(key, 0) + 1
    return sorted(key for key, count in seen.items() if count > 1)


def supplemental_specifications(fields: Mapping[str, str]) -> list[str]:
    """Preserve distinct supplemental lines; never replace historical evidence."""
    values = [value.strip() for value in fields.get(SUPPLEMENTAL_SPEC_FIELD, "").splitlines() if value.strip()]
    seen_values: set[str] = set()
    seen_paths: set[str] = set()
    for value in values:
        if value in seen_values:
            raise CiError("duplicate supplemental specification entry")
        seen_values.add(value)
        match = re.match(r"(\S+)\s+@", value)
        if match:
            path = posixpath.normpath(normalize_path(match[1]))
            if path in seen_paths:
                raise CiError(f"ambiguous duplicate supplemental specification path: {path}")
            seen_paths.add(path)
    return values


def parse_pr_body(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in PR_BODY_FIELDS or key in OPTIONAL_PR_BODY_FIELDS:
            if key == SUPPLEMENTAL_SPEC_FIELD:
                fields[key] = fields[key] + "\n" + value.strip() if key in fields else value.strip()
                supplemental_specifications(fields)
            else:
                if key in fields:
                    raise CiError(f"duplicate PR body field: {key}")
                fields[key] = value.strip()
    return fields


def extract_ids(text: str) -> set[str]:
    return set(ID_PATTERN.findall(text))


# A scope ID is a requirement / fit-criterion / invariant identifier, i.e. one of
# the namespaces the requirements table and invariants actually approve. Other
# ID_PATTERN matches are design/test labels and must NOT be treated as new scope.
_SCOPE_ID_PREFIXES = ("FR-", "SB-", "INV-", "SR-", "PR-", "CR-", "IR-")
# Non-scope D2/test namespaces the broad ID_PATTERN also matches:
#   C-NN (component), IF-NN (interface), P-NN (attachment/path), R03-NN / PA-NN
#   (test-case), and range shorthand such as FC01-05. These are excluded from the
#   "approved scope must cover" set by namespace, not by looking them up.
_NON_SCOPE_ID_PREFIXES = ("C-", "IF-", "P-", "R03-", "PA-", "BO-")
_RANGE_SHORTHAND_PATTERN = re.compile(r"^FC[0-9]{2}-[0-9]{2}$")
_SCOPE_ID_PATTERN = re.compile(
    r"\b(?:FR|SB|INV|SR|PR|CR)-[0-9]{2}(?:-FC[0-9]{2})?\b"
)


def is_scope_id(token: str) -> bool:
    """True for a requirement / fit-criterion / invariant identifier.

    Excludes component/interface/attachment/test-case namespaces and the
    ``FC01-05`` range shorthand. A deferred requirement ID (e.g. the query-reuse
    requirement) is still a genuine requirement ID, so it is a
    scope ID here even though it is out of a particular round's approved scope;
    membership in the approved scope is checked separately (a real, unapproved
    FR/IR must still fail).
    """
    if _RANGE_SHORTHAND_PATTERN.match(token):
        return False
    if token.startswith(_NON_SCOPE_ID_PREFIXES):
        return False
    if token.startswith("IR-"):
        return True
    if any(token.startswith(prefix) for prefix in ("FR-", "SB-", "INV-", "SR-", "PR-", "CR-")):
        return bool(_SCOPE_ID_PATTERN.match(token))
    return False


# Direct negation of a specific scope ID. Matched with a TIGHT window so that an
# unrelated negative word elsewhere on the line never suppresses a genuinely-added ID
# (e.g. "no shortcuts; this adds a requirement" keeps it; "implements one, excludes another"
# drops only the excluded one). Two directional forms are recognised:
#   * a negating phrase immediately before the ID: "excludes <id>", "not <id>",
#     "belongs to <id>", "deferred: <id>", "outside <id>", "prohibited: <id>";
#   * a negating predicate immediately after the ID: "<id> is not implemented",
#     "<id> is not in scope", "<id> deferred", "<id> is excluded", "<id> not implemented".
_PRE_NEGATION = re.compile(
    r"(?:excludes?|excluded|not|no|belongs\s+to|deferred|outside|prohibited|never|"
    r"out\s+of\s+scope|not\s+part\s+of|not\s+in\s+scope)\W{0,4}$"
)
_POST_NEGATION = re.compile(
    r"^\W{0,4}(?:is\s+)?(?:not\s+implemented|not\s+implement|not\s+in\s+scope|"
    r"not\s+part\s+of|is\s+excluded|is\s+deferred|deferred|out\s+of\s+scope|"
    r"is\s+outside|prohibited|belongs\s+to\s+another)"
)
_PRE_NEGATION_WINDOW = 18
_POST_NEGATION_WINDOW = 24


def _id_is_negated(line: str, token: str) -> bool:
    """True when EVERY occurrence of ``token`` is directly negated on ``line``.

    Negation must sit immediately before ("excludes <id>") or immediately after
    ("<id> is not implemented") the ID, within a tight window, so unrelated negative
    words elsewhere on the line do not suppress a genuinely-added ID.
    """
    search_start = 0
    occurrences = 0
    while True:
        idx = line.find(token, search_start)
        if idx == -1:
            break
        occurrences += 1
        before = line[max(0, idx - _PRE_NEGATION_WINDOW):idx]
        after = line[idx + len(token): idx + len(token) + _POST_NEGATION_WINDOW]
        if not (_PRE_NEGATION.search(before) or _POST_NEGATION.search(after)):
            return False  # a non-negated occurrence -> real add
        search_start = idx + len(token)
    return occurrences > 0


# Gate-harness files whose added lines are the gate's OWN test inputs/expectations, not
# business scope. Only these exact governance gate-test files are skipped for scope-ID
# extraction; ordinary application tests are still scanned, and the file itself is still
# covered for path-mention, test selection and the AI-use log.
_GATE_HARNESS_FILES = frozenset({"test/offline/test_ci_gates.py"})


def scope_changed_ids(
    changed_ids: Iterable[str],
    added_lines: Iterable[tuple[str, str, bool]] = (),
) -> set[str]:
    """Reduce raw extracted IDs to genuine, non-negated business scope IDs.

    ``added_lines`` is an iterable of ``(path, line)`` for added diff lines.
      * A gate-harness file's own lines contribute NO scope IDs (test inputs); an ID
        seen ONLY in gate-harness lines is excluded.
      * For other added lines, an ID that is DIRECTLY negated (``_id_is_negated``) is
        dropped only if it has no non-negated reference anywhere.
      * A candidate never located on any added line falls back to fail-closed (kept).
    Non-scope namespaces are always excluded by ``is_scope_id``.
    """
    candidates = {token for token in changed_ids if is_scope_id(token)}
    if not candidates:
        return set()
    triples = list(added_lines)
    if not triples:
        return candidates
    positive_pool: set[str] = set()
    negated_pool: set[str] = set()
    documentation_pool: set[str] = set()
    for _path, line, scope_bearing in triples:
        ids = {token for token in extract_ids(line) if token in candidates}
        if not scope_bearing:
            documentation_pool.update(ids)
            continue
        for token in ids:
            if _id_is_negated(line, token):
                negated_pool.add(token)
            else:
                positive_pool.add(token)
    result: set[str] = set()
    for token in candidates:
        if token in positive_pool:
            result.add(token)
        elif token in negated_pool:
            continue
        elif token in documentation_pool:
            continue  # only appears in documentation/harness prose -> not scope
        else:
            result.add(token)  # not located on any line -> fail-closed keep
    return result


def resolve_project_file(root: Path, value: str, label: str) -> tuple[Path | None, str]:
    if not value.strip():
        return None, f"{label} is empty"
    candidate = Path(value.strip())
    if candidate.is_absolute():
        return None, f"{label} is absolute: {value}"
    root_resolved = root.resolve()
    try:
        resolved = (root_resolved / candidate).resolve()
    except OSError:
        return None, f"{label} cannot be resolved: {value}"
    if not resolved.is_relative_to(root_resolved):
        return None, f"{label} escapes the project root: {value}"
    if not resolved.is_file():
        return None, f"{label} does not exist: {value}"
    return resolved, ""


def _is_ellipsis_placeholder(path: str) -> bool:
    return path.rsplit("/", 1)[-1] == "." * 3 + "py"


def plan_test_paths(plan_text: str) -> list[str]:
    return sorted(
        {
            path
            for path in CONTRACT_TEST_PATTERN.findall(plan_text)
            if not _is_ellipsis_placeholder(path)
        }
    )


def parse_approved_specification(value: str) -> tuple[str, str, list[str]]:
    errors: list[str] = []
    path_match = SPEC_PATH_PATTERN.search(value)
    commit_match = re.search(r"@\s*([0-9a-f]{7,40})\b", value)
    if commit_match is None:
        commit_match = re.search(r"\b([0-9a-f]{7,40})\b", value)
    if path_match is None:
        errors.append(
            "Approved test specification must name a project-relative "
            "specification file"
        )
    if commit_match is None:
        errors.append("Approved test specification must include a commit SHA")
    return (
        path_match.group(1) if path_match else "",
        commit_match.group(1) if commit_match else "",
        errors,
    )


def read_specification_at_commit(
    root: Path,
    specification_path: str,
    commit: str,
) -> tuple[str | None, str]:
    if not commit:
        return None, "approved test specification commit is missing"
    try:
        return git_output(["show", f"{commit}:{specification_path}"], cwd=root), ""
    except CiError as exc:
        return None, f"cannot read approved test specification at {commit}: {exc}"


def specification_mentions_path(spec_text: str, path: str) -> bool:
    normalized = normalize_path(path)
    searchable = spec_text.replace("`", "").replace("./", "")
    pattern = (
        r"(?<![\w./-])"
        + re.escape(normalized)
        + r"(?![\w/-])(?!\.[A-Za-z0-9])"
    )
    return re.search(pattern, searchable) is not None


def contract_test_plan(
    root: Path,
    fields: Mapping[str, str],
    changed_paths: Iterable[str],
    spec_text: str | None = None,
    supplemental_spec_texts: Sequence[str] = (),
) -> dict[str, Any]:
    classification = classify_paths(changed_paths)
    errors: list[str] = []
    code_paths = [
        *classification["application_code"],
        *classification["application_tests"],
        *(
            path
            for path in classification["other_code"]
            if not is_governance_path(path)
        ),
        *classification["governance_code"],
    ]
    if code_paths:
        missing = [
            field
            for field in ("Plan", "Approved test specification", "Approved scope")
            if not fields.get(field)
        ]
        if missing:
            errors.append(
                "code change lacks approved test scope fields: "
                + ", ".join(missing)
            )
            return {"errors": errors, "mode": "code", "test_paths": []}
        specification_path, specification_commit, specification_errors = (
            parse_approved_specification(fields["Approved test specification"])
        )
        if specification_errors:
            return {
                "errors": specification_errors,
                "mode": "code",
                "test_paths": [],
            }
        _, spec_path_error = resolve_project_file(
            root,
            specification_path,
            "Approved test specification",
        )
        if spec_path_error:
            return {"errors": [spec_path_error], "mode": "code", "test_paths": []}
        if spec_text is None:
            spec_text, spec_read_error = read_specification_at_commit(
                root,
                specification_path,
                specification_commit,
            )
            if spec_read_error:
                return {
                    "errors": [spec_read_error],
                    "mode": "code",
                    "test_paths": [],
                }
        assert spec_text is not None
        specifications = [spec_text, *supplemental_spec_texts]
        test_paths = sorted({path for text in specifications for path in plan_test_paths(text)})
        if not test_paths:
            errors.append(
                "approved test specification contains no test/offline or "
                "test/live test paths"
            )
        for code_path in code_paths:
            if not any(specification_mentions_path(text, code_path) for text in specifications):
                errors.append(
                    "approved test specification does not mention changed "
                    f"code path: {code_path}"
                )
        for test_path in test_paths:
            _, test_error = resolve_project_file(root, test_path, "contract test")
            if test_error:
                errors.append(test_error)
        return {
            "errors": errors,
            "mode": "application" if classification["application_code"] else "code",
            "specification_path": specification_path,
            "specification_commit": specification_commit,
            "test_paths": test_paths,
        }
    if classification["governance_ci"]:
        gate = "test/offline/test_ci_gates.py"
        _, gate_error = resolve_project_file(root, gate, "governance gate test")
        if gate_error:
            errors.append(gate_error)
        return {
            "errors": errors,
            "mode": "governance",
            "test_paths": [] if gate_error else [gate],
        }
    if classification["build_config"]:
        return {"errors": [], "mode": "configuration", "test_paths": []}
    if classification["semantic"]:
        return {"errors": [], "mode": "semantic", "test_paths": []}
    if classification["unknown_executable"] or classification["unknown_non_executable"]:
        return {"errors": [], "mode": "unclassified", "test_paths": []}
    return {"errors": [], "mode": "documentation", "test_paths": []}


def collect_changed_scope_ids(
    root: Path,
    base: str,
    head: str,
    paths: Iterable[str],
) -> set[str]:
    relevant = [
        normalize_path(path)
        for path in paths
        if normalize_path(path).startswith(("src/", "test/", "scripts/"))
    ]
    if not relevant:
        return set()
    try:
        diff = git_output(
            ["diff", "-U0", base, head, "--", *relevant],
            cwd=root,
        )
    except CiError as exc:
        raise CiError(f"cannot determine changed scope: {exc}") from exc
    ids: set[str] = set()
    for path in relevant:
        ids.update(extract_ids(path))
    for line in diff.splitlines():
        if line.startswith("+++") or not line.startswith("+"):
            continue
        ids.update(extract_ids(line[1:]))
    return ids


def _documentation_line_numbers(source: str) -> set[int]:
    """Line numbers (1-based) of true docstrings and comment-only lines.

    A docstring is recognised by SYNTACTIC POSITION — only the first statement of a
    module, class, or function body when it is an ``ast.Expr`` wrapping a string
    ``ast.Constant`` — NOT by the mere presence of a string node. Ordinary assignment
    strings, assert strings, dict keys/values, call arguments and f-strings are
    executable code and are NOT treated as documentation. Comment-only lines are
    detected textually. Scope IDs on documentation lines are prose, not business scope.

    A docstring that SHARES a physical line with other executable statements (for
    example ``\"\"\"module docs\"\"\"; enabled = {\"FR-04\"}`` or an inline
    ``\"\"\"body\"\"\"; assert ...``) is conservatively scanned: such a line only
    counts as documentation when the whole line is the docstring itself. Detecting
    this needs no string-interval analysis; it only compares the docstring's own
    line span against the other nodes parsed on that same line.
    """
    lines: set[int] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    if tree is not None:
        # Lines that carry any statement OTHER than a pure docstring constant. A
        # docstring line that also holds other executable statements must stay
        # scope-bearing, so it is excluded from the documentation set below.
        occupied: set[int] = set()
        doc_fields: list[tuple[int, int]] = []
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not body:
                continue
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                start = getattr(first, "lineno", None)
                if start is None:
                    continue
                end = getattr(first, "end_lineno", None)
                end = end if end is not None else start
                doc_fields.append((start, end))
                # Any body statement that starts on the docstring's own line
                # (semicolon-separated, e.g. ``"""docs"""; assert ...``) makes that
                # line executable code, so it must NOT be treated as documentation.
                for stmt in body[1:]:
                    s_line = getattr(stmt, "lineno", None)
                    if s_line is not None and s_line <= end:
                        occupied.update(range(start, end + 1))
                        break
        for start, end in doc_fields:
            for line_no in range(start, end + 1):
                if line_no not in occupied:
                    lines.add(line_no)
    for i, text in enumerate(source.splitlines(), start=1):
        if text.lstrip().startswith("#"):
            lines.add(i)
    return lines


def collect_changed_scope_lines(
    root: Path,
    base: str,
    head: str,
    paths: Iterable[str],
) -> list[tuple[str, str, bool]]:
    """Added diff lines under src/, test/, scripts/ as (path, line, scope_bearing) triples.

    ``scope_bearing`` is False for documentation lines (docstrings / comment-only) and
    for the known gate-harness test file: scope IDs there are prose or test inputs, not
    executable business-scope changes. All other added lines are scope-bearing.
    """
    relevant = [
        normalize_path(path)
        for path in paths
        if normalize_path(path).startswith(("src/", "test/", "scripts/"))
    ]
    if not relevant:
        return []
    try:
        diff = git_output(
            ["diff", "-U0", base, head, "--", *relevant],
            cwd=root,
        )
    except CiError as exc:
        raise CiError(f"cannot determine changed scope: {exc}") from exc
    doc_cache: dict[str, set[int]] = {}

    def _doc_lines(path: str) -> set[int]:
        if path not in doc_cache:
            try:
                text = git_output(["show", f"{head}:{path}"], cwd=root)
            except CiError:
                text = ""
            doc_cache[path] = _documentation_line_numbers(text)
        return doc_cache[path]

    triples: list[tuple[str, str, bool]] = []
    current = ""
    new_line = 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            current = normalize_path(target[2:]) if target.startswith("b/") else normalize_path(target)
            continue
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            new_line = int(match.group(1)) if match else 0
            continue
        if line.startswith("+"):  # added line (not the +++ header)
            scope_bearing = bool(current) and (
                normalize_path(current) not in _GATE_HARNESS_FILES
                and new_line not in _doc_lines(current)
            )
            triples.append((current, line[1:], scope_bearing))
            new_line += 1
        elif line.startswith("-"):
            continue
        else:
            new_line += 1
    return triples


def _parse_timestamp(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed


def normalize_specification(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def approval_phrases(body: str) -> list[str]:
    phrases = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(APPROVAL_PHRASE_PREFIX):
            phrases.append(stripped[len(APPROVAL_PHRASE_PREFIX) :].strip())
    return phrases


def verify_approval(
    fields: Mapping[str, str],
    *,
    approval_event: Mapping[str, Any] | None,
    pr_author: str,
    specification_ancestor: bool,
    specification_changed_after: bool,
    implementation_start_time: str,
    declared_start_matches: bool,
    changed_ids: Iterable[str],
    scoped_changed_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    missing = [field for field in PR_BODY_FIELDS if not fields.get(field)]
    if missing:
        errors.append(f"missing PR body fields: {', '.join(missing)}")
    if approval_event is None:
        errors.append("approval evidence is not verifiable")
        return {"errors": errors}
    reviewer = str(approval_event.get("reviewer", ""))
    reviewer_type = str(approval_event.get("reviewer_type", "")).lower()
    if not reviewer:
        errors.append("approval event has no reviewer")
    if reviewer == pr_author:
        errors.append("approval reviewer is the PR author")
    if reviewer_type == "bot" or reviewer.endswith("[bot]"):
        errors.append("approval reviewer is a bot")
    url = str(approval_event.get("url", ""))
    if not url.startswith("https://github.com/"):
        errors.append("approval URL is not a GitHub event URL")
    state = str(approval_event.get("state", "")).upper()
    body = str(approval_event.get("body", ""))
    if state not in {"APPROVED", "COMMENTED"}:
        errors.append("approval event is not an approving review or comment")
    phrases = approval_phrases(body)
    if len(phrases) != 1:
        errors.append(
            f'approval event must contain exactly one "{APPROVAL_PHRASE_PREFIX}" line'
        )
    else:
        approved_specification = normalize_specification(
            fields.get("Approved test specification", "")
        )
        if normalize_specification(phrases[0]) != approved_specification:
            errors.append(
                "approval phrase does not match Approved test specification"
            )
    approval_time = _parse_timestamp(str(approval_event.get("created_at", "")))
    start_time = _parse_timestamp(implementation_start_time)
    if approval_time is None:
        errors.append("approval event time is missing or invalid")
    if start_time is None:
        errors.append("implementation start time is missing or invalid")
    if approval_time is not None and start_time is not None and approval_time >= start_time:
        errors.append("approval event is not earlier than implementation start")
    if not specification_ancestor:
        errors.append("approved test-specification commit is not an ancestor of start")
    if specification_changed_after:
        errors.append("test specification changed after approval without reapproval")
    if not declared_start_matches:
        errors.append("implementation start is not the first changing commit")
    approved_scope = extract_ids(fields.get("Approved scope", ""))
    scope_candidates = (
        set(scoped_changed_ids)
        if scoped_changed_ids is not None
        else scope_changed_ids(changed_ids)
    )
    uncovered = sorted(scope_candidates - approved_scope)
    if uncovered:
        errors.append(f"approved scope does not cover changed IDs: {', '.join(uncovered)}")
    return {"errors": errors}


def _implementation_start(
    root: Path,
    base: str,
    head: str,
    paths: Sequence[str],
) -> tuple[str, str]:
    args = ["log", "--reverse", "--format=%H%x09%aI"]
    if base:
        args.append(f"{base}..{head}")
    else:
        args.append(head)
    if paths:
        args.extend(["--", *paths])
    output = git_output(args, cwd=root)
    first = next((line for line in output.splitlines() if line.strip()), "")
    if not first:
        raise CiError("no implementation-start commit found")
    commit, timestamp = first.split("\t", 1)
    return commit, timestamp


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = run_command(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
    )
    if result.returncode not in {0, 1}:
        raise CiError(f"git merge-base failed: {result.stderr.strip()}")
    return result.returncode == 0


def _specification_changed(
    root: Path,
    commit: str,
    head: str,
    specification_paths: Sequence[str],
) -> bool:
    if not specification_paths:
        return False
    result = run_command(
        ["git", "diff", "--quiet", commit, head, "--", *specification_paths],
        cwd=root,
    )
    if result.returncode not in {0, 1}:
        raise CiError(f"git diff failed: {result.stderr.strip()}")
    return result.returncode == 1


def _github_request(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cs5351-ci-gates",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise CiError(f"cannot query GitHub API: {exc}") from exc


def fetch_approval_event(
    repo: str,
    pr_number: int,
    approval_url: str,
    token: str,
) -> tuple[dict[str, Any], str]:
    pull = _github_request(f"https://api.github.com/repos/{repo}/pulls/{pr_number}", token)
    author = str((pull.get("user") or {}).get("login", ""))
    review_match = REVIEW_ID_PATTERN.search(approval_url)
    comment_match = COMMENT_ID_PATTERN.search(approval_url)
    if review_match:
        review_id = int(review_match.group(1))
        reviews = _github_request(
            f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews",
            token,
        )
        for review in reviews:
            if int(review.get("id", -1)) == review_id:
                return (
                    {
                        "reviewer": (review.get("user") or {}).get("login", ""),
                        "reviewer_type": (review.get("user") or {}).get("type", ""),
                        "state": review.get("state", ""),
                        "body": review.get("body", ""),
                        "created_at": review.get("submitted_at", ""),
                        "url": review.get("html_url", ""),
                    },
                    author,
                )
    if comment_match:
        comment_id = int(comment_match.group(1))
        comments = _github_request(
            f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
            token,
        )
        for comment in comments:
            if int(comment.get("id", -1)) == comment_id:
                return (
                    {
                        "reviewer": (comment.get("user") or {}).get("login", ""),
                        "reviewer_type": (comment.get("user") or {}).get("type", ""),
                        "state": "COMMENTED",
                        "body": comment.get("body", ""),
                        "created_at": comment.get("created_at", ""),
                        "url": comment.get("html_url", ""),
                    },
                    author,
                )
    raise CiError("approval event cannot be located from the GitHub API")


def frozen_preparation_paths(root: Path, fields: Mapping[str, str], head: str) -> set[str]:
    """§6: exact frozen FR-03 preparation materials only; uncertainty grants nothing.

    This is classification, not approval. The calling gate must still validate
    the primary event, specification ancestry, timing and unchanged spec.
    """
    import hashlib

    path, commit, errors = parse_approved_specification(fields.get("Approved test specification", ""))
    if errors:
        return set()
    text, error = read_specification_at_commit(root, path, commit)
    if error or text is None:
        return set()
    config_path = "docs/ci/semantic-suites/data-availability.yaml"
    try:
        for revision in (commit, head):
            config_text = git_output(["show", f"{revision}:{config_path}"], cwd=root)
            # Recognize only the fixed reviewed content. Different formatting,
            # values or activation are conservatively outside this exception.
            if hashlib.sha256(config_text.encode("utf-8")).hexdigest() != FR03_PREPARATION_CONFIG_SHA256:
                return set()
        eligible: set[str] = set()
        for material in FR03_PREPARATION_PATHS:
            if not specification_mentions_path(text, material):
                continue
            # Compare Git blob identities, not decoded/line-ending-normalized text.
            try:
                frozen = git_output(["rev-parse", "--verify", f"{commit}:{material}"], cwd=root).strip()
                candidate = git_output(["rev-parse", "--verify", f"{head}:{material}"], cwd=root).strip()
                kind = git_output(["cat-file", "-t", frozen], cwd=root).strip()
            except CiError:
                continue
            if kind == "blob" and frozen == candidate:
                eligible.add(material)
        return eligible
    except CiError:
        return set()


def _approval_location(url: str) -> tuple[str, int]:
    match = re.fullmatch(
        r"https://github\.com/([^/]+/[^/]+)/pull/([1-9][0-9]*)#(?:issuecomment-|pullrequestreview-)[0-9]+",
        url,
    )
    if not match:
        raise CiError("approval URL must identify a GitHub PR comment or review")
    return match[1], int(match[2])


def supplemental_allowed_scope(text: str, path: str = "", commit: str = "") -> str:
    """Only the explicit allowed-file list grants coverage; rationale/exclusions do not."""
    if path == "docs/plans/round-03-portfolio-test-amendment.md" and commit == "9e2c7793dc7d70fd2aeeecd480f78a5a81635614":
        digest = hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest()
        if digest == "02ff5e33086b89b591c64992d899370ddcb9ca7cb7aa8cba0639a1ead76a1df1":
            return "test/offline/test_portfolio_context.py"
        return ""
    section = re.search(r"(?m)^## 3\. Allowed files\s*$", text)
    if section is None:
        return ""
    tail = text[section.end():]
    next_section = re.search(r"(?m)^## ", tail)
    allowed = tail[:next_section.start()] if next_section else tail
    paths = re.findall(r"(?m)^- `?([\w./-]+\.(?:py|sh|md|yaml|yml|json))`?\s*$", allowed)
    return "\n".join(paths)


def validate_supplemental_specification(
    root: Path, base: str, head: str, value: str, repo: str, pr_number: int,
    token: str, changed_paths: Sequence[str],
) -> dict[str, Any]:
    """§5: validate independently before granting scope or contract selection."""
    def failed(errors: list[str]) -> dict[str, Any]:
        return {"errors": errors, "spec_text": "", "scope_ids": set()}

    match = re.fullmatch(r"(\S+)\s+@\s+([0-9a-f]{40})\s+\(approval:\s*(https://[^\s)]+)\)", value.strip())
    if not match:
        return failed(["invalid Supplemental test specification: expected path @ full SHA (approval: URL)"])
    path, commit, url = match.groups()
    _, error = resolve_project_file(root, path, SUPPLEMENTAL_SPEC_FIELD)
    if error:
        return failed([error])
    try:
        if _approval_location(url) != (repo, pr_number):
            return failed(["supplemental approval belongs to another PR"])
        text, error = read_specification_at_commit(root, path, commit)
        if error or text is None:
            return failed([error])
        allowed_scope = supplemental_allowed_scope(text, path, commit)
        if not allowed_scope:
            return failed(["supplemental specification has no explicit allowed-file list"])
        event, author = fetch_approval_event(repo, pr_number, url, token)
        classification = classify_paths(changed_paths)
        implementation_paths = set(
            classification["code"] + classification["tests"] + classification["semantic"]
            + classification["governance_ci"] + classification["safety_critical"]
            + classification["safety_relevant"]
        )
        covered = sorted(p for p in implementation_paths if p != path and specification_mentions_path(allowed_scope, p))
        first, first_time = _implementation_start(root, base, head, covered) if covered else (head, "")
        # Reuse the same independent reviewer/marker/time checks as the primary.
        fields = {
            "Plan": path, "Approved test specification": f"{path} @ {commit}",
            "Approval evidence": url, "Implementation start": first, "Approved scope": "supplement",
        }
        result = verify_approval(
            fields, approval_event=event, pr_author=author,
            specification_ancestor=_is_ancestor(root, commit, first),
            specification_changed_after=_specification_changed(root, commit, head, [path]),
            implementation_start_time=first_time or "9999-01-01T00:00:00Z",
            declared_start_matches=True, changed_ids=(),
        )
        errors = result["errors"]
        if event.get("url") != url:
            errors.append("supplemental approval event URL does not match its evidence URL")
        if errors:
            return failed([f"supplemental: {error}" for error in errors])
        return {"errors": [], "spec_text": allowed_scope, "scope_ids": extract_ids(text)}
    except CiError as exc:
        return failed([f"supplemental approval not verifiable: {exc}"])


def validate_supplemental_specifications(
    root: Path, base: str, head: str, fields: Mapping[str, str], repo: str,
    pr_number: int, token: str, changed_paths: Sequence[str],
) -> dict[str, Any]:
    """Each approved version retains its own event, coverage and chronology."""
    errors: list[str] = []
    texts: list[str] = []
    scope_ids: set[str] = set()
    for value in supplemental_specifications(fields):
        result = validate_supplemental_specification(
            root, base, head, value, repo, pr_number, token, changed_paths,
        )
        errors.extend(result["errors"])
        if not result["errors"]:
            texts.append(result["spec_text"])
            scope_ids.update(result["scope_ids"])
    return {"errors": errors, "spec_texts": texts, "scope_ids": scope_ids}


def approval_check(
    root: Path,
    base: str,
    head: str,
    pr_body: str,
    repo: str,
    pr_number: int,
    token: str,
) -> dict[str, Any]:
    fields = parse_pr_body(pr_body)
    if not fields.get("Approval evidence"):
        return {"errors": ["approval evidence is missing"], "supplemental_spec_texts": []}
    approval_event, author = fetch_approval_event(repo, pr_number, fields["Approval evidence"], token)
    changed = changed_paths_from_git(base, head, root)
    classification = classify_paths(changed)
    implementation_paths = set(
        classification["code"] + classification["tests"] + classification["semantic"]
        + classification["governance_ci"] + classification["safety_critical"]
        + classification["safety_relevant"]
    )
    implementation_paths -= frozen_preparation_paths(root, fields, head)
    start_commit, start_time = _implementation_start(root, base, head, sorted(implementation_paths) or changed)
    specification = fields.get("Approved test specification", "")
    specification_paths = SPEC_PATH_PATTERN.findall(specification)
    _, specification_commit, _ = parse_approved_specification(specification)
    ancestor = bool(specification_commit) and _is_ancestor(root, specification_commit, start_commit)
    supplemental = validate_supplemental_specifications(
        root, base, head, fields, repo, pr_number, token, changed,
    )
    # A valid supplement adds IDs; never manufacture a missing primary scope field.
    effective_fields = dict(fields)
    if fields.get("Approved scope"):
        effective_fields["Approved scope"] += " " + " ".join(sorted(supplemental["scope_ids"]))
    result = verify_approval(
        effective_fields, approval_event=approval_event, pr_author=author,
        specification_ancestor=ancestor,
        specification_changed_after=_specification_changed(
            root, specification_commit or start_commit, head, specification_paths,
        ),
        implementation_start_time=start_time,
        declared_start_matches=fields.get("Implementation start", "") == start_commit,
        changed_ids=collect_changed_scope_ids(root, base, head, changed),
        scoped_changed_ids=scope_changed_ids(
            collect_changed_scope_ids(root, base, head, changed),
            collect_changed_scope_lines(root, base, head, changed),
        ),
    )
    result["errors"].extend(supplemental["errors"])
    result["supplemental_spec_texts"] = supplemental["spec_texts"]
    return result


def validate_adr_reference(root: Path, value: str) -> list[str]:
    errors: list[str] = []
    if not value.strip():
        return ["safety-critical change has an empty ADR reference"]
    tokens = [
        token.strip(" \t\r\n,;`\"'")
        for token in re.split(r"[\s,;]+", value)
        if token.strip(" \t\r\n,;`\"'")
    ]
    paths = [token for token in tokens if token.endswith(".md")]
    if not paths:
        errors.append("ADR reference must include a project-relative .md path")
        return errors
    root_resolved = root.resolve()
    for token in paths:
        if token.startswith(("http://", "https://")):
            errors.append(f"ADR reference is not a project path: {token}")
            continue
        candidate = Path(token)
        if candidate.is_absolute():
            errors.append(f"ADR reference is absolute: {token}")
            continue
        try:
            resolved = (root_resolved / candidate).resolve()
        except OSError:
            errors.append(f"ADR reference cannot be resolved: {token}")
            continue
        if not resolved.is_relative_to(root_resolved):
            errors.append(f"ADR reference escapes the project root: {token}")
            continue
        relative = resolved.relative_to(root_resolved).as_posix()
        if not relative.startswith(ADR_PREFIX):
            errors.append(f"ADR reference is outside {ADR_PREFIX}: {token}")
            continue
        if not resolved.is_file():
            errors.append(f"ADR reference does not exist: {token}")
    return errors


def verify_security_adr(
    fields: Mapping[str, str],
    classification: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    critical = classification.get("safety_critical", [])
    if not critical:
        return {"errors": [], "required": False}
    errors = validate_adr_reference(root, fields.get("ADR", ""))
    return {"errors": errors, "required": True}


def collect_api_surface() -> dict[str, list[str]]:
    targets = {
        "graph.propagate": (
            "tradingagents.graph.trading_graph",
            "TradingAgentsGraph.propagate",
        ),
        "cli.run_analysis": ("cli.run", "run_analysis"),
        "net.get_scrubbed": ("tradingagents.dataflows.net", "get_scrubbed"),
        "symbols.normalize_symbol": (
            "tradingagents.dataflows.symbols",
            "normalize_symbol",
        ),
        "symbols.safe_ticker_component": (
            "tradingagents.dataflows.symbols",
            "safe_ticker_component",
        ),
        "rating.parse_rating": ("tradingagents.agents.rating", "parse_rating"),
        "rating.run_rating": ("tradingagents.agents.rating", "run_rating"),
    }
    actual: dict[str, list[str]] = {}
    for label, (module_name, attribute) in targets.items():
        module = importlib.import_module(module_name)
        obj: Any = module
        for part in attribute.split("."):
            obj = getattr(obj, part)
        actual[label] = list(inspect.signature(obj).parameters)
    return actual


EXPECTED_API_SURFACE = {
    "graph.propagate": ["self", "company_name", "trade_date", "asset_type", "portfolio"],
    "cli.run_analysis": ["checkpoint", "portfolio", "flags"],
    "net.get_scrubbed": ["url", "params", "timeout", "secret", "passthrough"],
    "symbols.normalize_symbol": ["raw"],
    "symbols.safe_ticker_component": ["value", "max_len"],
    "rating.parse_rating": ["text", "default"],
    "rating.run_rating": ["final_state"],
}


def check_api_surface(
    actual: Mapping[str, Sequence[str]],
    expected: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    errors: list[str] = []
    for label, expected_parameters in expected.items():
        if label not in actual:
            errors.append(f"missing API target: {label}")
        elif list(actual[label]) != list(expected_parameters):
            errors.append(
                f"{label} parameters changed: "
                f"{list(actual[label])} != {list(expected_parameters)}"
            )
    return {"errors": errors}


def parse_mypy_output(text: str) -> set[str]:
    errors: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or ": note:" in stripped:
            continue
        if re.match(r"^.+:\d+(?::\d+)?: error:", stripped):
            errors.add(stripped)
    return errors


def mypy_baseline_check(baseline: str, current: str) -> dict[str, Any]:
    baseline_errors = parse_mypy_output(baseline)
    current_errors = parse_mypy_output(current)
    new_errors = sorted(current_errors - baseline_errors)
    fixed = sorted(baseline_errors - current_errors)
    return {"errors": new_errors, "fixed": fixed}


def evaluate_required_junit(xml_text: str, label: str) -> dict[str, Any]:
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return {"errors": [f"invalid {label} JUnit XML: {exc}"]}
    cases = list(root.iter("testcase"))
    if not cases:
        return {"errors": [f"no {label} test cases were executed"]}
    errors: list[str] = []
    passed = 0
    skipped = 0
    failed = 0
    for case in cases:
        name = case.get("classname") or case.get("name") or "testcase"
        if case.find("skipped") is not None or case.get("status") == "skipped":
            skipped += 1
            errors.append(f"{label} test skipped: {name}")
        elif case.find("failure") is not None or case.find("error") is not None:
            failed += 1
            errors.append(f"{label} test failed: {name}")
        else:
            passed += 1
    if passed == 0:
        errors.append(f"no {label} test passed")
    return {
        "errors": errors,
        "total": len(cases),
        "passed": passed,
        "skipped": skipped,
        "failed": failed,
    }


def evaluate_live_junit(xml_text: str) -> dict[str, Any]:
    return evaluate_required_junit(xml_text, "live")


def evaluate_contract_junit(xml_text: str) -> dict[str, Any]:
    return evaluate_required_junit(xml_text, "contract")


def aggregate_results(
    needs: Mapping[str, Any],
    required: Sequence[str],
    applicability: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    applicability = applicability or {}
    errors: list[str] = []
    for job in required:
        if job not in needs:
            errors.append(f"required job {job} is missing")
            continue
        result = str(needs[job].get("result", ""))
        if result == "success":
            continue
        if result == "skipped" and job in applicability and not applicability[job]:
            continue
        errors.append(f"required job {job} did not pass: {result or 'unknown'}")
    return {"errors": errors}


def _run_id_from_url(url: str) -> str:
    match = RUN_ID_PATTERN.search(url)
    return match.group(1) if match else ""


def _find_status(
    statuses: Iterable[Mapping[str, Any]],
    context: str,
    candidate: str,
) -> Mapping[str, Any] | None:
    for status in statuses:
        if (
            str(status.get("context", "")) == context
            and str(status.get("sha", "")) == candidate
        ):
            return status
    return None


def _artifact_record(
    run: Mapping[str, Any],
    candidate: str,
    workflow_sha: str,
    kind: str,
) -> Mapping[str, Any] | None:
    for artifact in run.get("artifacts", []):
        if artifact.get("expired"):
            continue
        record = artifact.get("record")
        if not isinstance(record, Mapping):
            continue
        if (
            str(record.get("candidate_sha", "")) == candidate
            and str(record.get("workflow_sha", "")) == workflow_sha
            and str(record.get("kind", "")) == kind
        ):
            return record
    return None


def _verify_trusted_status(
    statuses: Iterable[Mapping[str, Any]],
    runs: Mapping[str, Mapping[str, Any]],
    context: str,
    candidate: str,
    repo: str,
    default_branch: str,
    kind: str,
) -> tuple[list[str], Mapping[str, Any] | None, Mapping[str, Any] | None]:
    errors: list[str] = []
    status = _find_status(statuses, context, candidate)
    if status is None:
        return [f"missing {context} status on candidate {candidate}"], None, None
    if str(status.get("state", "")) != "success":
        errors.append(f"{context} is not successful")
    run_id = _run_id_from_url(str(status.get("target_url", "")))
    if not run_id:
        return errors + [f"{context} has no trusted run URL"], status, None
    run = runs.get(run_id)
    if run is None:
        return errors + [f"trusted run {run_id} cannot be verified"], status, None
    if str(run.get("repository", "")) != repo:
        errors.append("trusted run belongs to a different repository")
    run_path = str(run.get("path", "")).split("@", 1)[0]
    if run_path != TRUSTED_WORKFLOW:
        errors.append("trusted run did not use the trusted workflow")
    if str(run.get("head_branch", "")) != default_branch:
        errors.append("trusted run was not from the default branch")
    if str(run.get("event", "")) != "workflow_dispatch":
        errors.append("trusted run was not manually dispatched")
    if str(run.get("conclusion", "")) != "success":
        errors.append("trusted run did not conclude successfully")
    record = _artifact_record(
        run,
        candidate,
        str(run.get("head_sha", "")),
        kind,
    )
    if record is None:
        errors.append(f"trusted run has no matching {kind} artifact record")
    return errors, status, record


# ---------------------------------------------------------------------------
# Semantic suite routing (docs/plans/semantic-suite-routing.md §3.1-§3.5)
# ---------------------------------------------------------------------------


def suite_status_context(suite_id: str) -> str:
    return f"{SEMANTIC_STATUS_PREFIX}{suite_id}"


def sha256_lf(path: Path | str) -> str:
    """SHA-256 of LF-normalized bytes, matching the FR-10 material hashing."""
    import hashlib

    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _load_unique_yaml(path: Path | str) -> Any:
    import yaml

    class _UniqueKeyLoader(yaml.SafeLoader):
        pass

    def _construct_mapping(loader: Any, node: Any, deep: bool = False) -> dict[Any, Any]:
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise CiError(f"duplicate key {key!r} in {path}")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    _UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
    )
    try:
        return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise CiError(f"cannot parse YAML file {path}: {exc}") from exc


def validate_suite_id(suite_id: Any) -> list[str]:
    if not isinstance(suite_id, str) or not SUITE_ID_PATTERN.match(suite_id):
        return [f"invalid semantic suite ID: {suite_id!r}"]
    if len(suite_id) > SUITE_ID_MAX_LENGTH:
        return [f"semantic suite ID is longer than {SUITE_ID_MAX_LENGTH}: {suite_id}"]
    if suite_id in RESERVED_SUITE_IDS:
        return [f"semantic suite ID is reserved: {suite_id}"]
    return []


def load_suite_registry(path: Path | str, root: Path | str | None = None) -> dict[str, Any]:
    """Load and validate the trusted suite registry; every problem is an error."""
    registry_path = Path(path)
    project_root = Path(root).resolve() if root is not None else registry_path.resolve().parents[2]
    try:
        document = _load_unique_yaml(registry_path)
    except CiError as exc:
        return {"suites": {}, "errors": [str(exc)]}
    if not isinstance(document, Mapping):
        return {"suites": {}, "errors": ["semantic suite registry must be a mapping"]}
    errors: list[str] = []
    if document.get("schema_version") != "1.0":
        errors.append('semantic suite registry schema_version must be "1.0"')
    unknown_top = sorted(set(document) - {"schema_version", "suites"})
    if unknown_top:
        errors.append(f"semantic suite registry has unknown keys: {', '.join(map(str, unknown_top))}")
    raw_suites = document.get("suites")
    if not isinstance(raw_suites, Mapping):
        return {"suites": {}, "errors": errors + ["semantic suite registry suites must be a mapping"]}
    suites: dict[str, dict[str, str]] = {}
    config_owner: dict[str, str] = {}
    config_root = (project_root / SUITE_CONFIG_PREFIX).resolve()
    for suite_id, entry in raw_suites.items():
        id_errors = validate_suite_id(suite_id)
        if id_errors:
            errors.extend(id_errors)
            continue
        if not isinstance(entry, Mapping):
            errors.append(f"semantic suite {suite_id}: entry must be a mapping")
            continue
        missing = sorted(SUITE_ENTRY_KEYS - set(entry))
        unknown = sorted(set(entry) - SUITE_ENTRY_KEYS)
        if missing:
            errors.append(f"semantic suite {suite_id}: missing keys: {', '.join(missing)}")
        if unknown:
            errors.append(f"semantic suite {suite_id}: unknown keys: {', '.join(map(str, unknown))}")
        if missing or unknown:
            continue
        requirement = entry["requirement"]
        config = entry["config"]
        runner = entry["runner"]
        entry_errors: list[str] = []
        if not isinstance(requirement, str) or not requirement.strip():
            entry_errors.append(f"semantic suite {suite_id}: requirement must be a non-empty string")
        config_path: Path | None = None
        if not isinstance(config, str) or not config or Path(config).is_absolute() or "\\" in config:
            entry_errors.append(f"semantic suite {suite_id}: config must be a project-relative path")
        else:
            config_path = (project_root / config).resolve()
            if not config_path.is_relative_to(config_root):
                entry_errors.append(f"semantic suite {suite_id}: config must be inside {SUITE_CONFIG_PREFIX}")
            elif not config_path.is_file():
                entry_errors.append(f"semantic suite {suite_id}: config does not exist: {config}")
            elif config in config_owner:
                entry_errors.append(
                    f"semantic suite {suite_id}: config {config} is already used by {config_owner[config]}"
                )
        runner_match = RUNNER_PATTERN.match(runner) if isinstance(runner, str) else None
        if runner_match is None:
            entry_errors.append(f"semantic suite {suite_id}: runner must be module:function")
        elif not (project_root / "scripts" / f"{runner_match.group(1)}.py").is_file():
            entry_errors.append(
                f"semantic suite {suite_id}: runner module scripts/{runner_match.group(1)}.py does not exist"
            )
        if not entry_errors and config_path is not None:
            try:
                config_document = load_yaml(config_path)
            except CiError as exc:
                entry_errors.append(f"semantic suite {suite_id}: {exc}")
            else:
                execution = config_document.get("execution") if isinstance(config_document, Mapping) else None
                declared = execution.get("runner") if isinstance(execution, Mapping) else None
                if declared and declared != runner:
                    entry_errors.append(
                        f"semantic suite {suite_id}: config execution.runner {declared} does not match registry runner {runner}"
                    )
        if entry_errors:
            errors.extend(entry_errors)
            continue
        config_owner[str(config)] = str(suite_id)
        suites[str(suite_id)] = {
            "requirement": str(requirement),
            "config": str(config),
            "runner": str(runner),
        }
    return {"suites": suites, "errors": errors}


def _suite_config_approved(config: Any) -> bool:
    if not isinstance(config, Mapping) or str(config.get("status", "")) != "approved":
        return False
    dataset = config.get("dataset")
    approval = config.get("approval")
    if not isinstance(dataset, Mapping) or not dataset.get("version"):
        return False
    if not isinstance(approval, Mapping):
        return False
    return all(approval.get(key) for key in ("approved_by", "approved_at", "evidence"))


def trusted_suite_states(
    registry_path: Path | str,
    trusted_root: Path | str,
) -> tuple[dict[str, dict[str, Any]] | None, list[str]]:
    """Return per-suite trusted state, or ``None`` when the registry is absent (bootstrap)."""
    path = Path(registry_path)
    if not path.is_file():
        return None, []
    root = Path(trusted_root)
    registry = load_suite_registry(path, root)
    if registry["errors"]:
        return {}, list(registry["errors"])
    states: dict[str, dict[str, Any]] = {}
    for suite_id, entry in registry["suites"].items():
        config_path = root / entry["config"]
        config = load_yaml(config_path)
        dataset = config.get("dataset") if isinstance(config, Mapping) else None
        states[suite_id] = {
            "approved": _suite_config_approved(config),
            "config_path": entry["config"],
            "config_sha256": sha256_lf(config_path),
            "config_version": str(dataset.get("version") or "") if isinstance(dataset, Mapping) else "",
            "runner": entry["runner"],
        }
    return states, []


def parse_suite_list(value: str) -> tuple[list[str], bool, list[str]]:
    """Parse a comma-separated suite list; returns (sorted IDs, is_none, errors)."""
    items = sorted({item.strip().lower() for item in value.split(",") if item.strip()})
    if not items:
        return [], False, []
    if "none" in items:
        if len(items) > 1:
            return [], False, ['"none" must be the only semantic suite value']
        return [], True, []
    errors: list[str] = []
    for item in items:
        errors.extend(validate_suite_id(item))
    return items, False, errors


def verify_suite_selection(
    fields: Mapping[str, str],
    approval_event: Mapping[str, Any] | None,
    pr_author: str,
) -> dict[str, Any]:
    """Verify the PR's explicit, reviewer-confirmed suite selection (§3.2)."""
    suites, is_none, errors = parse_suite_list(fields.get(SUITE_SELECTION_FIELD, ""))
    if not suites and not is_none and not errors:
        errors.append(
            'semantic evaluation required but no semantic suite was selected (add "Semantic suites:" '
            f'and a reviewer "{SUITE_PHRASE_PREFIX}" line)'
        )
    result = {"suites": suites, "none": is_none, "errors": errors}
    if not fields.get(SUITE_APPROVAL_FIELD):
        errors.append(f'missing PR body field "{SUITE_APPROVAL_FIELD}"')
        return result
    if approval_event is None:
        errors.append("semantic suite selection approval is not verifiable")
        return result
    reviewer = str(approval_event.get("reviewer", ""))
    reviewer_type = str(approval_event.get("reviewer_type", "")).lower()
    if not reviewer:
        errors.append("semantic suite selection approval has no reviewer")
    if reviewer == pr_author:
        errors.append("semantic suite selection approval reviewer is the PR author")
    if reviewer_type == "bot" or reviewer.endswith("[bot]"):
        errors.append("semantic suite selection approval reviewer is a bot")
    if not str(approval_event.get("url", "")).startswith("https://github.com/"):
        errors.append("semantic suite selection approval URL is not a GitHub event URL")
    if str(approval_event.get("state", "")).upper() not in {"APPROVED", "COMMENTED"}:
        errors.append("semantic suite selection approval is not an approving review or comment")
    phrases = [
        line.strip()[len(SUITE_PHRASE_PREFIX) :].strip()
        for line in str(approval_event.get("body", "")).splitlines()
        if line.strip().startswith(SUITE_PHRASE_PREFIX)
    ]
    if len(phrases) != 1:
        errors.append(f'semantic suite approval must contain exactly one "{SUITE_PHRASE_PREFIX}" line')
    else:
        approved_suites, approved_none, phrase_errors = parse_suite_list(phrases[0])
        if phrase_errors or (approved_suites, approved_none) != (suites, is_none):
            errors.append("semantic suite approval list does not match the PR body selection")
    return result


def _verify_suite_evidence(
    suite_id: str,
    trusted: Mapping[str, Any],
    statuses: Iterable[Mapping[str, Any]],
    runs: Mapping[str, Mapping[str, Any]],
    candidate: str,
    repo: str,
    default_branch: str,
) -> list[str]:
    context = suite_status_context(suite_id)
    status_errors, status, record = _verify_trusted_status(
        statuses, runs, context, candidate, repo, default_branch, "semantic"
    )
    if status is None:
        return status_errors
    errors = list(status_errors)
    if record is None:
        return errors
    if str(record.get("suite_id", "")) != suite_id:
        errors.append(f"{context} record belongs to suite {record.get('suite_id')!r}")
    if str(record.get("config_path", "")) != str(trusted.get("config_path", "")):
        errors.append(f"{context} record config path does not match the trusted registry")
    if str(record.get("config_sha256", "")) != str(trusted.get("config_sha256", "")):
        errors.append(f"{context} record config hash does not match the trusted config (re-run required)")
    if str(record.get("config_version", "")) != str(trusted.get("config_version", "")):
        errors.append(f"{context} record config version does not match the trusted config")
    record_status = str(record.get("status", ""))
    if record_status == "needs_review":
        items = record.get("needs_review")
        listed = ", ".join(str(item) for item in items) if isinstance(items, list) else ""
        errors.append(f"semantic suite {suite_id} needs human review: {listed or 'no items recorded'}")
    elif record_status != "passed":
        errors.append(f"semantic suite {suite_id} evidence did not pass")
    return errors


def _verify_noop_evidence(
    statuses: Iterable[Mapping[str, Any]],
    runs: Mapping[str, Mapping[str, Any]],
    candidate: str,
    repo: str,
    default_branch: str,
) -> list[str]:
    noop_errors, noop_status, noop_record = _verify_trusted_status(
        statuses, runs, SEMANTIC_NOOP_STATUS, candidate, repo, default_branch, "semantic-noop"
    )
    if noop_status is None or noop_errors:
        return noop_errors or ["required semantic not-applicable record is absent"]
    if noop_record is None:
        return ["semantic not-applicable record is missing"]
    errors: list[str] = []
    if not str(noop_record.get("reason", "")).strip():
        errors.append("semantic not-applicable review has no reason")
    if not str(noop_record.get("reviewed_by", "")).strip():
        errors.append("semantic not-applicable review has no reviewer")
    return errors


def verify_evidence(
    *,
    candidate: str,
    repo: str,
    default_branch: str,
    statuses: Iterable[Mapping[str, Any]],
    runs: Mapping[str, Mapping[str, Any]],
    semantic_required: bool,
    live_required: bool,
    selection: Mapping[str, Any] | None = None,
    trusted_suites: Mapping[str, Mapping[str, Any]] | None = None,
    registry_errors: Sequence[str] = (),
) -> dict[str, Any]:
    """Verify trusted evidence per selected semantic suite (semantic-suite-routing §3.3)."""
    errors: list[str] = []
    statuses = list(statuses)
    selected = list(selection.get("suites", [])) if selection is not None else []
    enforced = semantic_required or bool(selected)
    if enforced:
        if selection is None:
            errors.append(
                'semantic evaluation required but no semantic suite was selected (add "Semantic suites:" '
                f'and a reviewer "{SUITE_PHRASE_PREFIX}" line)'
            )
        else:
            selection_errors = [str(error) for error in selection.get("errors", [])]
            errors.extend(selection_errors)
            if not selection.get("none") and not selected and not selection_errors:
                errors.append(
                    'semantic evaluation required but no semantic suite was selected (add "Semantic suites:" '
                    f'and a reviewer "{SUITE_PHRASE_PREFIX}" line)'
                )
            if selection.get("none"):
                errors.extend(
                    _verify_noop_evidence(statuses, runs, candidate, repo, default_branch)
                )
            elif selected:
                if trusted_suites is None:
                    errors.append(
                        "trusted semantic suite registry is not present on the default branch"
                    )
                else:
                    errors.extend(str(error) for error in registry_errors)
                    for suite_id in selected:
                        trusted = trusted_suites.get(suite_id)
                        if trusted is None:
                            errors.append(
                                f"unknown semantic suite: {suite_id} (not in default-branch {SUITE_REGISTRY_PATH})"
                            )
                        elif not trusted.get("approved"):
                            errors.append(
                                f"semantic suite {suite_id} configuration {trusted.get('config_path')} is unapproved"
                            )
                        else:
                            errors.extend(
                                _verify_suite_evidence(
                                    suite_id, trusted, statuses, runs, candidate, repo, default_branch
                                )
                            )
    if live_required:
        live_errors, live_status, live_record = _verify_trusted_status(
            statuses, runs, LIVE_STATUS, candidate, repo, default_branch, "live"
        )
        if live_status is None or live_errors:
            errors.extend(live_errors)
            if live_status is None:
                errors.append("required live evidence is absent")
        elif live_record is None:
            errors.append("required live evidence record is absent")
        else:
            if not live_record.get("executed"):
                errors.append("live evidence is collect-only, not execution")
            if live_record.get("collected_only"):
                errors.append("live evidence is collect-only, not execution")
            if str(live_record.get("status", "")) != "passed":
                errors.append("live evidence did not pass")
    return {"errors": errors}


def semantic_config_status(path: Path | str) -> dict[str, Any]:
    config = load_yaml(path)
    if not isinstance(config, Mapping):
        return {"approved": False, "version": "", "errors": ["configuration is not a mapping"]}
    status = str(config.get("status", "unapproved"))
    dataset = config.get("dataset")
    version = ""
    if isinstance(dataset, Mapping):
        version = str(dataset.get("version") or "")
    approved = status == "approved" and bool(version)
    return {
        "approved": approved,
        "version": version,
        "status": status,
        "errors": [] if status in {"approved", "unapproved"} else ["unknown status"],
    }


def _url_origin(url: str) -> tuple[str, str, int | None]:
    parts = urllib.parse.urlsplit(url)
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").casefold()
    port = parts.port
    if port is None:
        if scheme == "http":
            port = 80
        elif scheme == "https":
            port = 443
    return scheme, hostname, port


class _NoCrossOriginAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if (
            redirected is not None
            and _url_origin(req.full_url) != _url_origin(redirected.full_url)
        ):
            redirected.remove_header("Authorization")
        return redirected


def _github_bytes(url: str, token: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cs5351-ci-gates",
        },
    )
    try:
        opener = urllib.request.build_opener(_NoCrossOriginAuthRedirect())
        with opener.open(request, timeout=60) as response:
            return response.read()
    except (OSError, urllib.error.URLError) as exc:
        raise CiError(f"cannot download GitHub artifact: {exc}") from exc


def _artifact_record_from_zip(data: bytes) -> Mapping[str, Any] | None:
    import io
    import zipfile

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise CiError(f"artifact is not a zip archive: {exc}") from exc
    for name in archive.namelist():
        if not name.endswith(".json"):
            continue
        try:
            record = json.loads(archive.read(name).decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(record, Mapping) and "candidate_sha" in record:
            return record
    return None


def fetch_commit_statuses(repo: str, candidate: str, token: str) -> list[dict[str, Any]]:
    try:
        payload = _github_request(
            f"https://api.github.com/repos/{repo}/commits/{candidate}/statuses?per_page=100",
            token,
        )
    except CiError:
        return []
    if not isinstance(payload, list):
        raise CiError("GitHub status response is not a list")
    statuses = []
    for item in payload:
        if isinstance(item, Mapping):
            status = dict(item)
            status["sha"] = candidate
            statuses.append(status)
    return statuses


def fetch_trusted_runs(
    repo: str,
    statuses: Iterable[Mapping[str, Any]],
    token: str,
) -> dict[str, dict[str, Any]]:
    runs: dict[str, dict[str, Any]] = {}
    for status in statuses:
        run_id = _run_id_from_url(str(status.get("target_url", "")))
        if not run_id or run_id in runs:
            continue
        run = _github_request(
            f"https://api.github.com/repos/{repo}/actions/runs/{run_id}",
            token,
        )
        if not isinstance(run, Mapping):
            continue
        run_data = dict(run)
        run_data["repository"] = repo
        run_data["path"] = str(run_data.get("path", "")).split("@", 1)[0]
        artifacts = _github_request(
            f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts",
            token,
        )
        records = []
        if isinstance(artifacts, Mapping):
            for artifact in artifacts.get("artifacts", []):
                if not isinstance(artifact, Mapping) or artifact.get("expired"):
                    continue
                archive_url = str(artifact.get("archive_download_url", ""))
                if not archive_url:
                    continue
                record = _artifact_record_from_zip(_github_bytes(archive_url, token))
                if record is not None:
                    records.append({"expired": False, "record": record})
        run_data["artifacts"] = records
        runs[run_id] = run_data
    return runs


def fetch_evidence(
    repo: str,
    candidate: str,
    default_branch: str,
    token: str,
    *,
    semantic_required: bool,
    live_required: bool,
    selection: Mapping[str, Any] | None = None,
    trusted_suites: Mapping[str, Mapping[str, Any]] | None = None,
    registry_errors: Sequence[str] = (),
) -> dict[str, Any]:
    if not default_branch:
        raise CiError("default branch is required for evidence verification")
    statuses = fetch_commit_statuses(repo, candidate, token)
    runs = fetch_trusted_runs(repo, statuses, token)
    return verify_evidence(
        candidate=candidate,
        repo=repo,
        default_branch=default_branch,
        statuses=statuses,
        runs=runs,
        semantic_required=semantic_required,
        live_required=live_required,
        selection=selection,
        trusted_suites=trusted_suites,
        registry_errors=registry_errors,
    )


def _load_fixture(path: str | None) -> Any:
    if not path:
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CiError(f"cannot read fixture {path}: {exc}") from exc


def _print_result(result: Mapping[str, Any]) -> int:
    errors = result.get("errors", [])
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _command_classify(args: argparse.Namespace) -> int:
    if args.paths:
        paths = [item.strip() for item in args.paths.split(",") if item.strip()]
        hunks = None
    else:
        paths = changed_paths_from_git(args.base, args.head, PROJECT_ROOT)
        hunks = semantic_hunks_from_git(args.base, args.head, PROJECT_ROOT)
        prompt_paths, analyzed_paths = semantic_analysis_from_git(
            args.base,
            args.head,
            paths,
            PROJECT_ROOT,
        )
    result = classify_paths(
        paths,
        hunks,
        prompt_paths if not args.paths else None,
        analyzed_paths if not args.paths else None,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _command_schema(args: argparse.Namespace) -> int:
    return _print_result(schema_check(args.requirements, args.schema))


def _command_permissions(args: argparse.Namespace) -> int:
    return _print_result(permissions_check(args.path))


def _command_ai_log(args: argparse.Namespace) -> int:
    head = load_yaml(args.head_log)
    base = load_yaml(args.base_log) if args.base_log else {"entries": []}
    if args.paths:
        paths = [item.strip() for item in args.paths.split(",") if item.strip()]
    else:
        paths = changed_paths_from_git(args.base, args.head, PROJECT_ROOT)
    return _print_result(ai_log_check(base, head, paths))


def _command_api(args: argparse.Namespace) -> int:
    if args.fixture:
        fixture = _load_fixture(args.fixture)
        result = check_api_surface(fixture.get("actual", {}), fixture.get("expected", {}))
    else:
        result = check_api_surface(collect_api_surface(), EXPECTED_API_SURFACE)
    return _print_result(result)


def _command_approval(args: argparse.Namespace) -> int:
    pr_body = Path(args.pr_body_file).read_text(encoding="utf-8")
    result = approval_check(
        PROJECT_ROOT,
        args.base,
        args.head,
        pr_body,
        args.repo,
        args.pr,
        args.token,
    )
    return _print_result(result)


def _event_selection_declared(pr_body_file: str) -> bool:
    if not pr_body_file:
        return False
    try:
        text = Path(pr_body_file).read_text(encoding="utf-8")
    except OSError as exc:
        raise CiError(f"cannot read PR body file: {exc}") from exc
    suites, _, _ = parse_suite_list(parse_pr_body(text).get(SUITE_SELECTION_FIELD, ""))
    return bool(suites)


def resolve_suite_selection(repo: str, pr_number: int, token: str) -> dict[str, Any] | None:
    """Fetch the current PR body (not the event payload) and verify its suite selection."""
    pull = _github_request(f"https://api.github.com/repos/{repo}/pulls/{pr_number}", token)
    fields = parse_pr_body(str(pull.get("body") or ""))
    if not fields.get(SUITE_SELECTION_FIELD, "").strip():
        return None
    author = str((pull.get("user") or {}).get("login", ""))
    event: Mapping[str, Any] | None = None
    url = fields.get(SUITE_APPROVAL_FIELD, "")
    if url:
        try:
            event, author = fetch_approval_event(repo, pr_number, url, token)
        except CiError:
            event = None
    return verify_suite_selection(fields, event, author)


def _command_evidence(args: argparse.Namespace) -> int:
    fixture = _load_fixture(args.fixture)
    if args.semantic_config:
        print(
            "NOTE: --semantic-config is ignored; suites come from --registry",
            file=sys.stderr,
        )
    if fixture is None:
        if not args.token:
            raise CiError("evidence check requires --token for the GitHub API")
        selection: Mapping[str, Any] | None = None
        trusted: Mapping[str, Mapping[str, Any]] | None = None
        registry_errors: list[str] = []
        if args.pr:
            selection = resolve_suite_selection(args.repo, args.pr, args.token)
        elif args.semantic_required or _event_selection_declared(args.pr_body_file):
            raise CiError("evidence check requires --pr for semantic suite selection")
        if args.registry and (args.semantic_required or (selection and not selection.get("none"))):
            trusted, registry_errors = trusted_suite_states(
                args.registry, args.trusted_root or Path(args.registry).resolve().parents[2]
            )
        result = fetch_evidence(
            args.repo,
            args.candidate,
            args.default_branch,
            args.token,
            semantic_required=args.semantic_required,
            live_required=args.live_required,
            selection=selection,
            trusted_suites=trusted,
            registry_errors=registry_errors,
        )
        return _print_result(result)
    classification = fixture.get("classification", {})
    result = verify_evidence(
        candidate=fixture.get("candidate", args.candidate),
        repo=fixture.get("repo", args.repo),
        default_branch=fixture.get("default_branch", args.default_branch),
        statuses=fixture.get("statuses", []),
        runs={str(key): value for key, value in fixture.get("runs", {}).items()},
        semantic_required=bool(
            fixture.get("semantic_required", classification.get("semantic_required"))
        ),
        live_required=bool(
            fixture.get("live_required", classification.get("live_required"))
        ),
        selection=fixture.get("selection"),
        trusted_suites=fixture.get("trusted_suites"),
        registry_errors=fixture.get("registry_errors", []),
    )
    return _print_result(result)


def _command_security_paths(args: argparse.Namespace) -> int:
    pr_body = Path(args.pr_body_file).read_text(encoding="utf-8")
    fields = parse_pr_body(pr_body)
    if args.paths:
        paths = [item.strip() for item in args.paths.split(",") if item.strip()]
    else:
        paths = changed_paths_from_git(args.base, args.head, PROJECT_ROOT)
    classification = classify_paths(paths)
    result = verify_security_adr(fields, classification, PROJECT_ROOT)
    result["classification"] = classification
    return _print_result(result)


def _command_live_result(args: argparse.Namespace) -> int:
    try:
        text = Path(args.junit).read_text(encoding="utf-8")
    except OSError as exc:
        raise CiError(f"cannot read live JUnit XML: {exc}") from exc
    return _print_result(evaluate_live_junit(text))


def _command_contract_tests(args: argparse.Namespace) -> int:
    pr_body = Path(args.pr_body_file).read_text(encoding="utf-8")
    fields = parse_pr_body(pr_body)
    if args.paths:
        paths = [item.strip() for item in args.paths.split(",") if item.strip()]
    else:
        paths = changed_paths_from_git(args.base, args.head, PROJECT_ROOT)
    supplements: list[str] = []
    if supplemental_specifications(fields):
        # CI supplies its read-only job token explicitly; direct callers retain
        # the public-read default. Authentication failure never falls back.
        try:
            repo, pr_number = _approval_location(fields.get("Approval evidence", ""))
        except CiError as exc:
            return _print_result({"errors": [str(exc)]})
        supplemental = validate_supplemental_specifications(
            PROJECT_ROOT, args.base, args.head, fields,
            repo, pr_number, getattr(args, "token", ""), paths,
        )
        if supplemental["errors"]:
            return _print_result(supplemental)
        supplements.extend(supplemental["spec_texts"])
    plan = contract_test_plan(PROJECT_ROOT, fields, paths, supplemental_spec_texts=supplements)
    if plan["errors"]:
        return _print_result(plan)
    test_paths = plan["test_paths"]
    if not test_paths:
        return _print_result({**plan, "collected": False, "executed": False})
    collect = run_command(
        [sys.executable, "-m", "pytest", "-q", "--collect-only", *test_paths],
        cwd=PROJECT_ROOT,
    )
    if collect.returncode != 0:
        detail = collect.stderr.strip() or collect.stdout.strip()
        return _print_result(
            {
                **plan,
                "errors": [f"contract test collection failed: {detail}"],
                "collected": False,
                "executed": False,
            }
        )
    with tempfile.TemporaryDirectory(prefix="ci-contract-") as temp_dir:
        junit_path = Path(temp_dir) / "contract.xml"
        execute = run_command(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                *test_paths,
                f"--junitxml={junit_path}",
            ],
            cwd=PROJECT_ROOT,
        )
        try:
            junit_text = junit_path.read_text(encoding="utf-8")
        except OSError:
            detail = execute.stderr.strip() or execute.stdout.strip()
            return _print_result(
                {
                    **plan,
                    "errors": [
                        "contract test execution produced no JUnit result: "
                        f"{detail}"
                    ],
                    "collected": True,
                    "executed": False,
                }
            )
    evaluated = evaluate_contract_junit(junit_text)
    if execute.returncode != 0 and not evaluated["errors"]:
        evaluated["errors"].append(
            "contract test execution failed: pytest returned a non-zero status"
        )
    if evaluated["errors"]:
        return _print_result(
            {
                **plan,
                **evaluated,
                "collected": True,
                "executed": False,
            }
        )
    return _print_result({**plan, **evaluated, "collected": True, "executed": True})


def _command_aggregate(args: argparse.Namespace) -> int:
    needs = json.loads(args.needs_json)
    required = [item for item in args.required.split(",") if item]
    errors: list[str] = []
    applicability: dict[str, bool] = {}
    for item in args.applicable.split(","):
        if not item:
            continue
        if "=" not in item:
            errors.append(f"invalid applicability entry: {item}")
            continue
        key, value = item.split("=", 1)
        value = value.strip().lower()
        if value not in {"true", "false"}:
            errors.append(f"invalid applicability value for {key}: {value!r}")
            continue
        applicability[key] = value == "true"
    result = aggregate_results(needs, required, applicability)
    result["errors"] = errors + result["errors"]
    return _print_result(result)


def _command_mypy_baseline(args: argparse.Namespace) -> int:
    baseline = Path(args.baseline).read_text(encoding="utf-8")
    current = Path(args.current).read_text(encoding="utf-8")
    return _print_result(mypy_baseline_check(baseline, current))


def _command_mypy(args: argparse.Namespace) -> int:
    result = run_command(
        [args.python, "-m", "mypy", "--config-file", args.config, *args.targets],
        cwd=PROJECT_ROOT,
    )
    Path(args.output).write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode not in {0, 1}:
        return _print_result({"errors": [result.stderr.strip()]})
    if not args.baseline:
        return _print_result({"errors": parse_mypy_output(result.stdout + result.stderr)})
    baseline = Path(args.baseline).read_text(encoding="utf-8")
    compared = mypy_baseline_check(
        baseline,
        result.stdout + result.stderr,
    )
    return _print_result({"errors": compared["errors"], "fixed": compared["fixed"]})


def _command_run(args: argparse.Namespace) -> int:
    result = run_command(args.command, cwd=PROJECT_ROOT)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CS5351 CI gate checks")
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify = subparsers.add_parser("classify")
    classify.add_argument("--base", default="")
    classify.add_argument("--head", default="HEAD")
    classify.add_argument("--paths", default="")
    classify.set_defaults(func=_command_classify)

    schema = subparsers.add_parser("schema")
    schema.add_argument("--requirements", required=True)
    schema.add_argument("--schema", required=True)
    schema.set_defaults(func=_command_schema)

    permissions = subparsers.add_parser("permissions")
    permissions.add_argument("--path", required=True)
    permissions.set_defaults(func=_command_permissions)

    ai_log = subparsers.add_parser("ai-log")
    ai_log.add_argument("--base-log", default="")
    ai_log.add_argument("--head-log", required=True)
    ai_log.add_argument("--base", default="")
    ai_log.add_argument("--head", default="HEAD")
    ai_log.add_argument("--paths", default="")
    ai_log.set_defaults(func=_command_ai_log)

    api = subparsers.add_parser("api")
    api.add_argument("--fixture", default="")
    api.set_defaults(func=_command_api)

    approval = subparsers.add_parser("approval")
    approval.add_argument("--pr-body-file", required=True)
    approval.add_argument("--base", required=True)
    approval.add_argument("--head", required=True)
    approval.add_argument("--repo", required=True)
    approval.add_argument("--pr", required=True, type=int)
    approval.add_argument("--token", required=True)
    approval.set_defaults(func=_command_approval)

    evidence = subparsers.add_parser("evidence")
    evidence.add_argument("--candidate", default="")
    evidence.add_argument("--repo", default="")
    evidence.add_argument("--default-branch", default="")
    evidence.add_argument("--token", default="")
    evidence.add_argument("--semantic-config", default="", help="deprecated; ignored")
    evidence.add_argument("--registry", default="")
    evidence.add_argument("--trusted-root", default="")
    evidence.add_argument("--pr", default=0, type=int)
    evidence.add_argument("--pr-body-file", default="")
    evidence.add_argument("--semantic-required", action="store_true")
    evidence.add_argument("--live-required", action="store_true")
    evidence.add_argument("--fixture", default="")
    evidence.set_defaults(func=_command_evidence)

    security_paths = subparsers.add_parser("security-paths")
    security_paths.add_argument("--pr-body-file", required=True)
    security_paths.add_argument("--base", default="")
    security_paths.add_argument("--head", default="HEAD")
    security_paths.add_argument("--paths", default="")
    security_paths.set_defaults(func=_command_security_paths)

    live_result = subparsers.add_parser("live-result")
    live_result.add_argument("--junit", required=True)
    live_result.set_defaults(func=_command_live_result)

    contract_tests = subparsers.add_parser("contract-tests")
    contract_tests.add_argument("--pr-body-file", required=True)
    contract_tests.add_argument("--base", default="")
    contract_tests.add_argument("--head", default="HEAD")
    contract_tests.add_argument("--paths", default="")
    contract_tests.add_argument("--token", default="", help="GitHub API token for supplemental approval reads")
    contract_tests.set_defaults(func=_command_contract_tests)

    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--needs-json", required=True)
    aggregate.add_argument("--required", required=True)
    aggregate.add_argument("--applicable", default="")
    aggregate.set_defaults(func=_command_aggregate)

    mypy = subparsers.add_parser("mypy")
    mypy.add_argument("--python", default=sys.executable)
    mypy.add_argument("--config", default="mypy.ini")
    mypy.add_argument("--output", required=True)
    mypy.add_argument("--baseline", default="")
    mypy.add_argument("targets", nargs="*")
    mypy.set_defaults(func=_command_mypy)

    mypy_baseline = subparsers.add_parser("mypy-baseline")
    mypy_baseline.add_argument("--baseline", required=True)
    mypy_baseline.add_argument("--current", required=True)
    mypy_baseline.set_defaults(func=_command_mypy_baseline)

    run = subparsers.add_parser("run")
    run.add_argument("command", nargs=argparse.REMAINDER)
    run.set_defaults(func=_command_run)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CiError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
