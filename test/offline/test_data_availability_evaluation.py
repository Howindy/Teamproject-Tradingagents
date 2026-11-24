"""FR-03-FC05 / IR-12: DA-T01–DA-T16 trusted-suite offline controls.

Synthetic candidate packages exercise transport and result plumbing. They do not
establish real model quality or replace the candidate feature's integration tests.
All reply oracles below are independent literals, not scorer-generated answers.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import ci_semantic_eval  # noqa: E402
import data_availability_eval as suite  # noqa: E402

GOOD = {
    "DA-S01": "The program marks necessary data coverage complete; that alone does not establish a profitable trade.",
    "DA-S02": "Global news is unavailable. The available ticker news does not close that necessary gap.",
    "DA-S03": "All necessary inputs are available; the missing StockTwits feed remains a supplementary limitation.",
    "DA-S04": "The program summary is currently unavailable, so it does not confirm coverage. The supplied market and research reports remain usable.",
    "DA-S05": "Stock necessity rules do not apply to this crypto analysis; that does not mean all data is complete or all queries failed.",
}
ARGUMENT = " Improving demand and improving adoption interest support a constructive case, but margin pressure, volatility and narrow leadership justify caution."


def reply(case_id, role, rating="Hold"):
    rationale = GOOD[case_id] + ARGUMENT
    if role == "research-manager":
        return f"**Recommendation**: {rating}\n\n**Rationale**: {rationale}\n\n**Strategic Actions**: Monitor demand and limit allocation while reviewing risk."
    return rationale


@pytest.fixture
def materials(tmp_path, monkeypatch):
    for name in (
        "data-availability-cases.json",
        "data-availability-rubric.md",
        "semantic-suites/data-availability.yaml",
    ):
        path = tmp_path / "docs/ci" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / "docs/ci" / name).read_bytes())
    config = yaml.safe_load(
        (tmp_path / "docs/ci/semantic-suites/data-availability.yaml").read_text()
    )
    config["status"] = "approved"
    config["approval"] = {
        "approved_by": "offline-fixture-reviewer",
        "approved_at": "2026-11-24T14:00:00Z",
        "evidence": ["https://example.invalid/offline-test-only"],
    }
    monkeypatch.chdir(tmp_path)
    return tmp_path, config


@pytest.fixture
def cases():
    return json.loads((ROOT / "docs/ci/data-availability-cases.json").read_text())["cases"]


def _git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def candidate(materials, monkeypatch):
    """DA-T04/12/16: installed synthetic candidate with real Pydantic parsing."""
    root, config = materials
    cand = root / "candidate"
    src = cand / "src/tradingagents"
    files = {
        "__init__.py": "",
        "agents/__init__.py": "",
        "agents/researchers/__init__.py": "",
        "agents/managers/__init__.py": "",
        "dataflows/__init__.py": "",
        "dataflows/config.py": "def set_config(config):\n    pass\n",
        "dataflows/availability.py": "def research_block(summary):\n    return 'CANDIDATE_PROGRAM_BLOCK: ' + str(summary)\n",
        "agents/context.py": "def get_language_instruction():\n    return ''\n",
        "agents/schemas.py": (
            "from pydantic import BaseModel\n"
            "from typing import Literal\n"
            "class ResearchPlan(BaseModel):\n"
            "    recommendation: Literal['Buy', 'Overweight', 'Hold', 'Underweight', 'Sell']\n"
            "    rationale: str\n    strategic_actions: str\n"
            "def render_research_plan(p):\n"
            "    return '**Recommendation**: '+p.recommendation+'\\n\\n**Rationale**: '+p.rationale+'\\n\\n**Strategic Actions**: '+p.strategic_actions\n"
        ),
        "agents/structured.py": (
            "def bind_structured(llm, schema, name):\n    return llm.with_structured_output(schema)\n"
            "def invoke_structured_or_freetext(bound, plain, prompt, render, name):\n"
            "    try:\n        result=bound.invoke(prompt)\n"
            "        if result is None: raise ValueError('no parsed result')\n"
            "        return render(result)\n"
            "    except Exception:\n        return plain.invoke(prompt).content\n"
        ),
    }
    for role in ("bull", "bear"):
        files[f"agents/researchers/{role}_researcher.py"] = (
            "from tradingagents.dataflows.availability import research_block\n"
            f"def create_{role}_researcher(llm):\n"
            "    def node(state):\n"
            "        prompt=research_block(state['research_availability_summary'])+'\\n'+state['market_report']\n"
            "        return {'investment_debate_state': {'current_response': llm.invoke(prompt).content}}\n"
            "    return node\n"
        )
    files["agents/managers/research_manager.py"] = (
        "from tradingagents.dataflows.availability import research_block\n"
        "from tradingagents.agents.schemas import ResearchPlan, render_research_plan\n"
        "from tradingagents.agents.structured import bind_structured, invoke_structured_or_freetext\n"
        "def create_research_manager(llm):\n"
        "    bound=bind_structured(llm, ResearchPlan, 'Research Manager')\n"
        "    def node(state):\n"
        "        prompt=research_block(state['research_availability_summary'])+'\\n'+state['investment_debate_state']['history']\n"
        "        return {'investment_plan': invoke_structured_or_freetext(bound,llm,prompt,render_research_plan,'Research Manager')}\n"
        "    return node\n"
    )
    for name, value in files.items():
        path = src / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    _git(cand, "init", "-q")
    _git(
        cand,
        "-c",
        "user.name=Offline Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "add",
        "src",
    )
    _git(
        cand,
        "-c",
        "user.name=Offline Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "offline candidate",
    )
    env = root / "environment"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", "--system-site-packages", str(env)],
        check=True,
    )
    sites = list(env.glob("lib/python*/site-packages")) + list(env.glob("Lib/site-packages"))
    import langchain_core

    (sites[0] / "00_candidate.pth").write_text(str(cand / "src") + "\n")
    (sites[0] / "zz_dependencies.pth").write_text(
        str(Path(langchain_core.__file__).resolve().parents[1]) + "\n"
    )
    executable = next(p for p in (env / "bin/python", env / "Scripts/python.exe") if p.exists())
    monkeypatch.setattr(suite, "_python_executable", lambda: str(executable))
    return cand, _git(cand, "rev-parse", "HEAD"), config


def transport(request):
    text = reply(request["case_id"], request["role"])
    if request["attempt_kind"] == "structured":
        return {
            "content": "",
            "tool_calls": [
                {
                    "id": "fixture",
                    "type": "function",
                    "function": {
                        "name": "ResearchPlan",
                        "arguments": json.dumps(
                            {
                                "recommendation": "Hold",
                                "rationale": GOOD[request["case_id"]] + ARGUMENT,
                                "strategic_actions": "Monitor demand and limit allocation while reviewing risk.",
                            }
                        ),
                    },
                }
            ],
            "finish_reason": "tool_calls",
            "usage": {},
        }
    return {"content": text, "finish_reason": "stop", "usage": {}}


def test_t01_signature_and_import_on_main():
    assert ci_semantic_eval.check_runner_signature(suite.evaluate) == []
    spec = importlib.util.spec_from_file_location(
        "fr03_import_check", ROOT / "scripts/data_availability_eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (
        inspect.signature(module.evaluate).parameters["output_dir"].kind
        == inspect.Parameter.KEYWORD_ONLY
    )


@pytest.mark.parametrize("mutation", ["unapproved", "version", "threshold", "model", "budget"])
def test_t02_preflight_config(materials, mutation):
    root, config = materials
    if mutation == "unapproved":
        config["status"] = "unapproved"
    if mutation == "version":
        config["dataset"]["version"] = "other"
    if mutation == "threshold":
        config["thresholds"]["max_critical_failures"] = 1
    if mutation == "model":
        config["model"]["configuration"]["max_retries"] = 2
    if mutation == "budget":
        config["execution"]["max_completion_requests"] = 21
    result = suite.evaluate(
        config, "0" * 40, output_dir=root / "out", model_transport=lambda _: pytest.fail("request")
    )
    assert result["status"] == "failed" and result["request_count"] == 0


def test_t03_hashes_and_line_endings(materials):
    root, config = materials
    for key in ("dataset", "rubric"):
        path = root / config[key]["path"]
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert suite._load_materials(config, root)[0]["dataset_version"] == "fr03-data-availability-v1"
    for key in ("dataset", "rubric"):
        path = root / config[key]["path"]
        original = path.read_bytes()
        path.write_bytes(original + b"mutation")
        with pytest.raises(ValueError, match="hash"):
            suite._load_materials(config, root)
        path.write_bytes(original)


def test_t04_candidate_sha_and_missing_module(materials):
    root, config = materials
    result = suite.evaluate(
        config, "0" * 40, output_dir=root / "out", model_transport=lambda _: pytest.fail("request")
    )
    assert result["status"] == "failed" and result["request_count"] == 0


def test_t05_complete_run_and_framework_result(candidate, monkeypatch):
    root, sha, config = candidate
    requests = []

    def record(req):
        requests.append(req)
        assert "CANDIDATE_PROGRAM_BLOCK" in req["messages"][0]["content"]
        return transport(req)

    result = suite.evaluate(config, sha, output_dir=root.parent / "out", model_transport=record)
    assert result["status"] == "passed", result
    assert result["request_count"] == len(requests) == 15
    assert result["candidate_summary"]["passed_dimensions"] == 45
    assert len({(r["case_id"], r["role"]) for r in requests}) == 15
    assert (
        ci_semantic_eval.normalize_runner_result(result, output_dir=root.parent / "out")[0]
        == "passed"
    )
    assert (
        hashlib.sha256(Path(result["details_path"]).read_bytes()).hexdigest()
        == result["details_sha256"]
    )


@pytest.mark.parametrize(
    "case_id,claim",
    [
        ("DA-S01", "The necessary dataset is incomplete."),
        ("DA-S01", "The income statement is missing."),
        ("DA-S01", "Complete coverage guarantees the stock will rise."),
        (
            "DA-S02",
            "Global news is unavailable, but ticker news fills that requirement, so necessary coverage is complete.",
        ),
        ("DA-S02", "The global feed contained zero adverse events."),
        (
            "DA-S03",
            "Basic necessity coverage is incomplete because StockTwits could not be fetched.",
        ),
        ("DA-S04", "A missing summary proves every data query failed."),
        ("DA-S04", "The program confirmed the necessary data is complete."),
        ("DA-S05", "Not applicable means every source succeeded."),
    ],
)
@pytest.mark.parametrize("role", ["bull", "bear", "research-manager"])
def test_t06_to_t09_critical_contradictions(cases, case_id, claim, role):
    case = next(c for c in cases if c["case_id"] == case_id)
    scored = suite.score_output(case, role, reply(case_id, role) + " " + claim)
    assert scored["status"] == "failed", scored
    assert scored["critical_failures"]


@pytest.mark.parametrize(
    "case_id,claim",
    [
        (
            "DA-S02",
            "Necessary coverage is not complete: global news is missing despite the company-news report.",
        ),
        (
            "DA-S02",
            "The earlier speaker claimed all necessary news was available; that claim is wrong because global news is unavailable. The available ticker news does not close that necessary gap.",
        ),
        (
            "DA-S03",
            "Necessary inputs are complete, but overall investment evidence remains limited without the supplementary feeds.",
        ),
    ],
)
def test_t10_polarity_scope_and_attribution(cases, case_id, claim):
    case = next(c for c in cases if c["case_id"] == case_id)
    assert suite.score_output(case, "bull", claim + ARGUMENT)["status"] == "passed"


def test_t10_unfamiliar_expression_blocks(cases):
    result = suite.score_output(cases[1], "bull", "The news situation is handled." + ARGUMENT)
    assert result["status"] == "needs_review"


def test_t10_good_statement_does_not_hide_unknown_coverage_claim(cases):
    result = suite.score_output(
        cases[1], "bull", reply("DA-S02", "bull") + " Every feed was accessible."
    )
    assert result["status"] == "needs_review"


def test_t04_wrong_sha_stale_origin_and_missing_module(candidate, monkeypatch):
    cand, sha, config = candidate
    for name, supplied in (("wrong-sha", "0" * 40),):
        result = suite.evaluate(
            config,
            supplied,
            output_dir=cand.parent / name,
            model_transport=lambda _: pytest.fail("preflight must not send"),
        )
        assert result["status"] == "failed" and result["request_count"] == 0
    good_python = suite._python_executable()
    monkeypatch.setattr(suite, "_python_executable", lambda: sys.executable)
    result = suite.evaluate(
        config,
        sha,
        output_dir=cand.parent / "stale",
        model_transport=lambda _: pytest.fail("stale origin must not send"),
    )
    assert result["status"] == "failed" and result["request_count"] == 0
    monkeypatch.setattr(suite, "_python_executable", lambda: good_python)
    (cand / "src/tradingagents/dataflows/availability.py").unlink()
    result = suite.evaluate(
        config,
        sha,
        output_dir=cand.parent / "missing-module",
        model_transport=lambda _: pytest.fail("missing module must not send"),
    )
    assert result["status"] == "failed" and result["request_count"] == 0


def test_t13_missing_secret_does_not_call_live_transport(candidate, monkeypatch):
    cand, sha, config = candidate
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(suite, "_model_request", lambda *a: pytest.fail("no live call"))
    result = suite.evaluate(config, sha, output_dir=cand.parent / "missing-secret")
    assert result["status"] == "failed" and result["request_count"] == 0
    assert any("DEEPSEEK_API_KEY" in error for error in result["errors"])


@pytest.mark.parametrize("text", ["", "Program data-availability summary: complete"])
def test_t11_empty_and_summary_echo(cases, text):
    assert suite.score_output(cases[0], "bull", text)["status"] == "failed"


def test_t11_manager_format_and_ratings(cases):
    assert (
        suite.score_output(cases[0], "research-manager", GOOD["DA-S01"] + ARGUMENT)["status"]
        == "failed"
    )
    for rating in ("Buy", "Overweight", "Hold", "Underweight", "Sell"):
        assert (
            suite.score_output(
                cases[0], "research-manager", reply("DA-S01", "research-manager", rating)
            )["status"]
            == "passed"
        )


def test_t12_structured_fallback_max_twenty(candidate):
    root, sha, config = candidate

    def fallback(req):
        if req["attempt_kind"] == "structured":
            return {"content": "unparsed structured attempt", "finish_reason": "stop", "usage": {}}
        return transport(req)

    result = suite.evaluate(config, sha, output_dir=root.parent / "out", model_transport=fallback)
    assert result["status"] == "passed", result
    assert result["request_count"] == 20
    details = json.loads(Path(result["details_path"]).read_text())
    assert sum(a["request"]["attempt_kind"] == "fallback" for a in details["attempts"]) == 5


@pytest.mark.parametrize("failure", ["exception", "truncated"])
def test_t13_technical_failures(candidate, failure):
    root, sha, config = candidate
    calls = []

    def broken(req):
        calls.append(req)
        if failure == "exception":
            raise TimeoutError("offline synthetic timeout")
        return {"content": "partial", "finish_reason": "length", "usage": {}}

    result = suite.evaluate(config, sha, output_dir=root.parent / "out", model_transport=broken)
    assert result["status"] == "failed" and len(calls) == result["request_count"] == 1
    assert Path(result["details_path"]).exists()


def test_t13_budget_never_sends_twenty_first():
    budget = suite.RequestBudget(20)
    for _ in range(20):
        budget.take()
    with pytest.raises(ValueError, match="budget"):
        budget.take()
    assert budget.count == 20


def test_t14_matrix_missing_duplicate_and_pending(materials, cases):
    root, config = materials
    data, _, _ = suite._load_materials(config, root)
    for bad_cases in (cases[:-1], cases + [cases[0]]):
        bad = copy.deepcopy(data)
        bad["cases"] = bad_cases
        with pytest.raises(ValueError, match="matrix"):
            suite._validate_cases(bad)
    scores = [suite.score_output(cases[0], "bull", reply("DA-S01", "bull"))]
    assert suite.aggregate_scores(scores)["status"] == "failed"


def test_t15_details_even_on_preflight_failure(materials):
    root, config = materials
    config["status"] = "unapproved"
    out = root / "output"
    result = suite.evaluate(
        config, "0" * 40, output_dir=out, model_transport=lambda _: pytest.fail("request")
    )
    path = Path(result["details_path"])
    assert path.is_relative_to(out) and path.exists()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == result["details_sha256"]
    assert "details_sha256" not in json.loads(path.read_text())
    assert result["errors"] and result["needs_review"] == []


def test_t16_registry_and_frozen_materials():
    registry = yaml.safe_load((ROOT / "docs/ci/semantic-suites.yaml").read_text())
    assert registry["suites"]["data-availability"] == {
        "requirement": "FR-03",
        "config": "docs/ci/semantic-suites/data-availability.yaml",
        "runner": "data_availability_eval:evaluate",
    }
    assert registry["suites"]["financial-metrics"]["runner"] == "financial_metrics_eval:evaluate"
    config = yaml.safe_load((ROOT / "docs/ci/semantic-suites/data-availability.yaml").read_text())
    assert config["status"] == "approved"
    assert config["approval"] == {
        "approved_by": "espino2233",
        "approved_at": "2026-11-24T17:16:24Z",
        "evidence": ["https://github.com/Howindy/Teamproject-Tradingagents/pull/20#issuecomment-7138946184"],
    }


def test_t11_manager_rationale_must_weigh_the_debate(cases):
    text = (
        "**Recommendation**: Hold\n\n**Rationale**: "
        + GOOD["DA-S01"]
        + "\n\n**Strategic Actions**: Monitor improving demand but limit allocation for margin pressure."
    )
    assert suite.score_output(cases[0], "research-manager", text)["status"] == "needs_review"


def test_t14_aggregate_failure_and_review_precedence(cases):
    scores = [
        suite.score_output(case, role, reply(case["case_id"], role))
        for case in cases
        for role in suite.ROLES
    ]
    assert suite.aggregate_scores(scores)["status"] == "passed"
    pending = copy.deepcopy(scores)
    pending[0]["status"] = pending[0]["dimensions"]["A"] = "needs_review"
    pending[0]["needs_review"] = ["unresolved"]
    assert suite.aggregate_scores(pending)["status"] == "needs_review"
    pending[1]["status"] = pending[1]["dimensions"]["B"] = "failed"
    assert suite.aggregate_scores(pending)["status"] == "failed"


def test_t15_prior_details_are_not_overwritten(materials):
    root, config = materials
    config["status"] = "unapproved"
    first = suite.evaluate(
        config, "0" * 40, output_dir=root / "out", model_transport=lambda _: None
    )
    before = Path(first["details_path"]).read_bytes()
    second = suite.evaluate(
        config, "0" * 40, output_dir=root / "out", model_transport=lambda _: None
    )
    assert first["details_path"] != second["details_path"]
    assert Path(first["details_path"]).read_bytes() == before


@pytest.mark.parametrize(
    "stance,expected",
    [
        ("That claim is wrong.", "passed"),
        ("That claim is correct.", "failed"),
        ("", "needs_review"),
    ],
)
def test_scope_of_quoted_news_contradiction(cases, stance, expected):
    text = f'{GOOD["DA-S02"]} The previous speaker said: "Necessary coverage is complete." {stance}'
    result = suite.score_output(cases[1], "bear", text + ARGUMENT)
    assert result["dimensions"] == {"A": "passed", "B": expected, "C": "passed"}


@pytest.mark.parametrize(
    "statement,a,b",
    [
        ("Global news is missing. Company news is available.", "passed", "passed"),
        ("Global news is missing.", "needs_review", "needs_review"),
        ("Global news is missing, so all news is unavailable.", "needs_review", "failed"),
        ("Global news is missing. Company news is available. There is no news coverage.",
         "passed", "failed"),
    ],
)
def test_global_and_company_scope(cases, statement, a, b):
    result = suite.score_output(cases[1], "bull", statement + ARGUMENT)
    assert result["dimensions"] == {"A": a, "B": b, "C": "passed"}


def test_rejected_quote_does_not_hide_later_contradiction(cases):
    statement = (
        'The earlier speaker said "basic coverage incomplete" is wrong. '
        "All necessary inputs are available; the missing StockTwits feed remains "
        "a supplementary limitation. Basic coverage is incomplete."
    )
    result = suite.score_output(cases[2], "bull", statement + ARGUMENT)
    assert result["dimensions"]["B"] == "failed"


@pytest.mark.parametrize(
    "qualifier",
    [
        "There is no news coverage of global events.",
        "It does not follow that all news is unavailable.",
    ],
)
def test_limited_or_negated_news_claim_is_not_a_blanket_denial(cases, qualifier):
    result = suite.score_output(cases[1], "bull", GOOD["DA-S02"] + " " + qualifier + ARGUMENT)
    assert "available_company_news_denied" not in result["critical_failures"]
