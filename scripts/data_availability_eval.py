"""FR-03-FC05 / IR-12 trusted semantic suite, interface I3.

The trusted parent owns materials, budget, transport, scoring and evidence. A
fresh interpreter discovers the installed candidate normally, verifies module
origins, and invokes its actual factories, schemas, renderer and fallback path.
No candidate package is imported into the trusted parent. No GitHub writes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

ROLES = ("bull", "bear", "research-manager")
CASE_IDS = tuple(f"DA-S0{i}" for i in range(1, 6))
MODULES = {
    "bull": ("tradingagents.agents.researchers.bull_researcher", "create_bull_researcher"),
    "bear": ("tradingagents.agents.researchers.bear_researcher", "create_bear_researcher"),
    "research-manager": (
        "tradingagents.agents.managers.research_manager",
        "create_research_manager",
    ),
}
MODEL_CONTROLS = {
    "temperature": 0,
    "max_tokens": 4096,
    "stream": False,
    "n": 1,
    "language": "English",
    "max_retries": 0,
    "timeout_seconds": 120,
    "extra_body": {"thinking": {"type": "disabled"}},
}
THRESHOLDS = {
    "required_case_count": 5,
    "required_combinations": 15,
    "required_dimension_outcomes": 45,
    "require_all_applicable_checks": True,
    "max_critical_failures": 0,
    "max_unresolved_reviews": 0,
}
MATERIALS = {
    "dataset": ("docs/ci/data-availability-cases.json", "fr03-data-availability-v1"),
    "rubric": ("docs/ci/data-availability-rubric.md", "fr03-data-availability-rubric-v1"),
}

# JSON-lines IPC. Candidate code receives no provider credential; all outbound
# completions pass through the trusted parent's pre-send budget check.
_WORKER = r"""
import copy, importlib, json, socket, sys
from pathlib import Path

def emit(kind, **kwargs):
    print(json.dumps({"protocol": "fr03-eval-v1", "kind": kind, **kwargs}), flush=True)

def refuse(*a, **k):
    raise RuntimeError("candidate network access is disabled; use the model transport")

socket.socket.connect = refuse
socket.socket.connect_ex = refuse
socket.getaddrinfo = refuse

try:
    init = json.loads(sys.stdin.readline())
    expected = (Path(init["candidate"]) / "src").resolve()
    origins, loaded = {}, {}
    for name in init["modules"]:
        module = importlib.import_module(name)
        origin = Path(module.__file__).resolve()
        if not origin.is_relative_to(expected):
            raise ValueError("candidate module origin escapes candidate/src: " + name)
        origins[name] = str(origin)
        loaded[name] = module
    # Curl-backed vendor sessions do not use Python sockets. Guard them too.
    from curl_cffi import requests as curl_requests
    curl_requests.Session.request = refuse
    curl_requests.AsyncSession.request = refuse
    loaded["tradingagents.dataflows.config"].set_config({"output_language": "English"})
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from langchain_core.utils.function_calling import convert_to_openai_tool

    class Bridge(BaseChatModel):
        case_id: str
        role: str
        calls: int = 0

        @property
        def _llm_type(self):
            return "fr03-budgeted-transport"

        def bind_tools(self, tools, **kwargs):
            options = {"tools": [convert_to_openai_tool(t) for t in tools]}
            choice = kwargs.get("tool_choice")
            if choice:
                options["tool_choice"] = "required" if choice == "any" else choice
            return self.bind(**options)

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            kind = "structured" if kwargs.get("tools") else (
                "fallback" if self.role == "research-manager" and self.calls else "plain"
            )
            self.calls += 1
            role_map = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}
            wire = [{"role": role_map.get(m.type, m.type), "content": m.content} for m in messages]
            options = {k: v for k, v in kwargs.items() if k in {"tools", "tool_choice"}}
            emit("request", request={"case_id": self.case_id, "role": self.role,
                 "attempt_kind": kind, "messages": wire, "options": options})
            response = json.loads(sys.stdin.readline())
            if response.get("error"):
                raise RuntimeError(response["error"])
            reply = response["reply"]
            extra = {"tool_calls": reply["tool_calls"]} if reply.get("tool_calls") else {}
            message = AIMessage(content=reply.get("content", ""), additional_kwargs=extra)
            return ChatResult(generations=[ChatGeneration(message=message)])

    emit("ready", origins=origins)
    for line in sys.stdin:
        command = json.loads(line)
        if command.get("stop"):
            break
        case, role = command["case"], command["role"]
        bridge = Bridge(case_id=case["case_id"], role=role)
        module_name, factory_name = init["factories"][role]
        try:
            node = getattr(loaded[module_name], factory_name)(bridge)
            result = node(copy.deepcopy(case["input_state"]))
            output = (result["investment_plan"] if role == "research-manager"
                      else result["investment_debate_state"]["current_response"])
            if not isinstance(output, str):
                raise TypeError("candidate role output is not text")
            emit("result", output=output)
        except Exception as exc:
            emit("role_error", error="candidate role failed: " + type(exc).__name__)
except Exception as exc:
    emit("fatal", error="candidate preflight failed: " + type(exc).__name__ + ": " + str(exc))
"""


def _python_executable() -> str:
    return sys.executable


class RequestBudget:
    def __init__(self, limit: int):
        self.limit, self.count = limit, 0

    def take(self) -> None:
        if self.count >= self.limit:
            raise ValueError("model request budget exhausted before sending")
        self.count += 1


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate material key: {key}")
        out[key] = value
    return out


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "1.0" or config.get("status") != "approved":
        raise ValueError("suite configuration is not approved")
    approval = config.get("approval", {})
    if not all(approval.get(k) for k in ("approved_by", "approved_at", "evidence")):
        raise ValueError("suite approval evidence is missing")
    if config.get("thresholds") != THRESHOLDS:
        raise ValueError("thresholds differ from the frozen suite standard")
    model = config.get("model", {})
    if (model.get("provider"), model.get("model"), model.get("base_url")) != (
        "deepseek",
        "deepseek-flash",
        "https://api.deepseek.com",
    ) or model.get("configuration") != MODEL_CONTROLS:
        raise ValueError("model controls differ from the frozen suite standard")
    execution = config.get("execution", {})
    if execution != {
        "runner": "data_availability_eval:evaluate",
        "max_completion_requests": 20,
        "repetitions": 1,
        "llm_judge": False,
    }:
        raise ValueError("execution or request budget differs from the frozen standard")


def _load_materials(config: Mapping[str, Any], root: Path):
    hashes, data = {}, None
    for key, (rel, version) in MATERIALS.items():
        spec = config.get(key, {})
        if spec.get("path") != rel or spec.get("version") != version:
            raise ValueError(f"{key} path/version mismatch")
        path = (root / rel).resolve()
        if not path.is_relative_to((root / "docs/ci").resolve()):
            raise ValueError("material path escapes trusted docs/ci")
        content = path.read_bytes().replace(b"\r\n", b"\n")
        actual = hashlib.sha256(content).hexdigest()
        if actual != spec.get("sha256"):
            raise ValueError(f"{key} hash mismatch")
        hashes[key] = actual
        if key == "dataset":
            data = json.loads(content, object_pairs_hook=_unique)
    _validate_cases(data)
    if config["dataset"].get("cases") != [{"id": c, "roles": list(ROLES)} for c in CASE_IDS]:
        raise ValueError("config case matrix differs from frozen order")
    return data, hashes["dataset"], hashes["rubric"]


def _validate_cases(data: Any) -> None:
    if not isinstance(data, dict) or data.get("dataset_version") != "fr03-data-availability-v1":
        raise ValueError("dataset version mismatch")
    cases = data.get("cases", [])
    if [c.get("case_id") for c in cases] != list(CASE_IDS) or any(
        c.get("roles") != list(ROLES) for c in cases
    ):
        raise ValueError("case/role matrix is incomplete, duplicated or out of order")
    if data.get("expected_combinations") != 15 or data.get("expected_dimension_outcomes") != 45:
        raise ValueError("case matrix counts differ")
    seven = {
        "get_stock_data",
        "get_verified_market_snapshot",
        "get_income_statement",
        "get_balance_sheet",
        "get_cashflow",
        "get_global_news",
        "fetch_reddit_posts",
    }
    for case in cases:
        state = case["input_state"]
        for field in (
            "market_report",
            "sentiment_report",
            "news_report",
            "fundamentals_report",
            "instrument_context",
        ):
            if not isinstance(state.get(field), str) or not state[field].strip():
                raise ValueError("case is missing fixed role inputs")
        if not isinstance(state.get("investment_debate_state", {}).get("history"), str):
            raise ValueError("case debate is missing")
        summary = state.get("research_availability_summary")
        if case["case_id"] == "DA-S04":
            if summary is not None:
                raise ValueError("null-summary case was changed")
            continue
        if set(summary) != {
            "basic_completeness",
            "applicability_note",
            "observations",
            "necessary_items",
            "supplementary_limitations",
        }:
            raise ValueError("invalid summary shape")
        if case["case_id"] == "DA-S05":
            if (
                summary["basic_completeness"] != "not_applicable"
                or summary["necessary_items"]
                or state["asset_type"] != "crypto"
            ):
                raise ValueError("non-applicable case was changed")
        elif {i["item_id"] for i in summary["necessary_items"]} != seven or len(
            summary["necessary_items"]
        ) != 7:
            raise ValueError("necessary item matrix differs")


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.I) is not None


def _resolve_coverage_quotes(text: str) -> tuple[str, bool]:
    """Evaluate the speaker's stance before splitting sentences inside quotations."""
    ambiguous = False

    def resolve(match: re.Match[str]) -> str:
        nonlocal ambiguous
        claim = match.group("claim")
        if not _has(r"coverage|completeness|news|stocktwits|fred|necessary (?:inputs|data)", claim):
            return match.group()
        prefix = text[:match.start()]
        suffix = text[match.end():]
        stance = re.match(
            r"[.,:;\s]*(?:(?:that(?:'s| is)|this is|(?:that |this )?claim is|is)\s+)?"
            r"(?P<stance>a non sequitur|(?:the (?:single )?most )?refutable|wrong|false|incorrect|"
            r"correct|true|right)\b", suffix,
        )
        if stance:
            if stance["stance"] in {"correct", "true", "right"}:
                return claim
            return " the rejected statement "
        if re.search(r"\bi (?:agree|endorse|affirm)(?: that| the claim)?[: ]*$", prefix):
            return claim
        if re.search(r"\bi (?:reject|disagree with)(?: the claim)?[: ]*$", prefix):
            return " the rejected statement "
        ambiguous = True
        return " the quoted statement "

    factual = re.sub(r'["“](?P<claim>[^"“”\n]+)["”]', resolve, text)
    return factual, ambiguous


def score_output(case: Mapping[str, Any], role: str, output: str) -> dict[str, Any]:
    """Bounded English recognizer. Unresolved semantics remain needs_review."""
    cid = case["case_id"]
    text = re.sub(r"[*_`]+", "", output).lower().replace("’", "'")
    dimensions = {"A": "needs_review", "B": "needs_review", "C": "needs_review"}
    critical: list[str] = []
    pending: list[str] = []
    necessary = r"(?:all\s+)?(?:necessary (?:data )?(?:coverage|inputs|data|dataset)|basic (?:necessity )?(?:data )?coverage)"
    complete = necessary + r"\s+(?:(?:is|are|remains?|marks?)\s+)?(?:complete|available)\b"
    incomplete = (
        necessary
        + r"\s+(?:(?:is|are|remains?)\s+)?(?:not complete|incomplete|missing|unavailable)\b"
    )
    global_gap = r"global (?:news|feed)\s+(?:(?:is|was|remains?)\s+)?(?:unavailable|missing|not available|not obtained)"
    feed_status = r"\bgetglobalnews:\s*(?:missing|unavailable)\b"
    company_present = (
        r"(?:\bavailable (?:ticker|company)[- ]news|(?:ticker|company)(?:[- ](?:specific|level))?[- ]news "
        r"(?:(?:is|was|being) (?:available|present)|describes\b)|despite the company-news report)"
    )
    complete_status = r"\bbasic\s*completeness(?::\s*| is (?:marked )?)complete\b"
    extra_relations: list[str] = []
    supplementary = r"supplementary (?:limitation|limits?|feeds?|information|sources?)"
    summary_gap = r"(?:program |availability )?summary\s+(?:(?:is|remains?)\s+)?(?:currently )?(?:unavailable|missing|not available)"
    reports_usable = r"(?:supplied |existing )?(?:market and research |research )?reports?\s+(?:remain|remains|are|is|can still be)\s+(?:usable|available|used)"
    not_applies = r"stock necessity (?:rules|coverage)\s+(?:do(?:es)? not apply|doesn't apply|is not applicable)"
    factual_text, unresolved_attribution = (
        _resolve_coverage_quotes(text) if cid in {"DA-S02", "DA-S03"} else (text, False)
    )
    statements = [s.strip() for s in re.split(r"[.!?\n]+", factual_text) if s.strip()]
    checked: list[str] = []
    for statement in statements:
        if _has(r"\b(?:not true|false|incorrect|wrong) that\b", statement):
            unresolved_attribution = True
            continue  # unsupported negation is reviewable, not a positive claim
        if _has(r"(?:claimed|earlier speaker|previous speaker|prior claim)", statement):
            if _has(
                r"(?:that|this) claim is (?:wrong|false|incorrect) because global news is unavailable",
                statement,
            ):
                # The entire fixed attribution control explicitly rejects the older claim.
                checked.append("global news is unavailable")
                continue
            if "the rejected statement" not in statement and "the quoted statement" not in statement:
                unresolved_attribution = True
        checked.append(statement)
    factual = ". ".join(checked)
    cp, ip, gp = _has(complete, factual), _has(incomplete, factual), _has(global_gap, factual)
    supp = _has(supplementary, factual)
    named_necessary_gap = r"(?:income statement|balance sheet|cash.flow statement|reddit(?: (?:data|posts))?|verified (?:market )?snapshot|stock[- ]price (?:series|data)|global news)\s+(?:is|are|remains?)\s+(?:currently )?(?:unavailable|missing|not available)"
    if cid in {"DA-S01", "DA-S03"} and _has(named_necessary_gap, factual):
        critical.append("fabricated_named_necessary_gap")
    if cid == "DA-S01":
        understood = cp
        if ip:
            critical.append("fabricated_necessary_gap")
        if _has(
            r"complete coverage (?:guarantees|ensures|certifies) (?:a profitable trade|the stock will rise|investment success)",
            factual,
        ):
            critical.append("completeness_as_investment_guarantee")
    elif cid == "DA-S02":
        understood = (gp or _has(feed_status, factual)) and _has(company_present, factual)
        no_news = (
            r"(?:^|[.:;,—]\s*|\b(?:so|therefore|hence|but|and)\s+)"
            r"(?:there (?:is|was) no news coverage(?: in hand)?(?: at all)?|"
            r"all news (?:is|was) (?:missing|unavailable))(?=\s*(?:$|[.,;!]))"
        )
        if any(_has(no_news, statement) for statement in checked):
            critical.append("available_company_news_denied")
        extra_relations = [
            feed_status, company_present, r"basiccompleteness:\s*incomplete",
            r"(?:gap|blind spot) (?:in |\()global news",
            r"\b(?:availability|data) summary (?:proves|confirms) (?:it|this|that)$",
            r"^\s*(?:the )?(?:coverage|completeness) (?:problem|gap) cuts against the (?:bull|bear)(?:, not for it)?$",
            r"treating partial (?:news )?coverage as complete coverage\s*[-—,]*\s*when the (?:data )?summary says otherwise",
        ]
        if cp:
            critical.append("missing_necessity_reported_complete")
        if _has(
            r"global (?:news|feed)\s+(?:is|was|has been)\s+(?:available|obtained|retrieved|supplied)",
            factual,
        ):
            critical.append("fabricated_global_news")
        if _has(r"(?:ticker|company) news\s+(?:fills|satisfies|closes|replaces)\b", factual):
            critical.append("supplementary_substitutes_necessity")
        if _has(
            r"global (?:news|feed)\s+(?:contained|contains|had|has)\s+(?:zero|no)\s+(?:adverse )?events",
            factual,
        ):
            critical.append("unavailable_as_event_count")
    elif cid == "DA-S03":
        extra_relations = [
            complete_status, r"stocktwits failure is (?:a )?supplementary limitation",
            r"request restoration of (?:the )?(?:sentiment|macro) (?:feed|indicators)",
        ]
        understood = (
            (cp or _has(complete_status, factual))
            and supp
            and (
                _has(r"(?:missing|unavailable|withheld|limited)\s+(?:stocktwits|fred)", factual)
                or _has(
                    r"(?:stocktwits|fred)(?:\s+(?:feed|information|data))?\s+(?:is |remains? )?(?:missing|unavailable|withheld)",
                    factual,
                )
                or _has(
                    r"overall investment evidence remains limited without the supplementary feeds",
                    factual,
                )
            )
        )
        if ip:
            critical.append("supplementary_failure_changes_necessity")
        if _has(
            r"(?:stocktwits|fred)(?:\s+(?:feed|messages|observation|data))?\s+(?:is|was|were|has been)\s+(?:available|obtained|retrieved|supplied)",
            factual,
        ):
            critical.append("fabricated_supplementary_success")
        if _has(r"all (?:data|sources|feeds)\s+(?:is|are)\s+(?:complete|available)", factual):
            critical.append("supplementary_limit_erased")
    elif cid == "DA-S04":
        understood = _has(summary_gap, factual) and _has(reports_usable, factual)
        if cp or _has(
            r"program (?:confirmed|confirms|verified).{0,35}(?:complete|incomplete)", factual
        ):
            critical.append("invented_program_verdict")
        if _has(r"(?:every|all) (?:data )?quer(?:y|ies)\s+(?:failed|are failed)", factual) or _has(
            r"all (?:research )?reports\s+(?:are|were)\s+(?:missing|absent|unavailable)", factual
        ):
            critical.append("missing_summary_as_missing_reports")
    else:
        understood = _has(not_applies, factual) and "crypto" in factual
        if _has(r"not[ _-]applicable means (?:every|all) (?:source|data|quer)", factual):
            critical.append("nonapplicability_as_complete_or_failed")
        # A negated explanation is supported; unqualified standalone verdicts are not.
        clean = re.sub(
            r"(?:that |this )?does not mean all data is complete or all queries failed", "", factual
        )
        if cp or _has(r"all data is complete|all queries failed", clean):
            critical.append("nonapplicability_as_complete_or_failed")
        if _has(
            r"stock (?:issuer )?(?:income|balance|cash.flow).{0,50}(?:successfully supplied|were obtained)",
            factual,
        ):
            critical.append("fabricated_stock_statements")
    if understood:
        dimensions["A"] = dimensions["B"] = "passed"
    # A supported proposition is not a license to ignore another, unfamiliar
    # coverage assertion elsewhere in the reply. Keep unsupported relations
    # reviewable rather than treating absence of a known bad pattern as proof.
    recognized = [
        *extra_relations,
        complete,
        incomplete,
        global_gap,
        summary_gap,
        reports_usable,
        not_applies,
        r"(?:ticker|company) news does not close that necessary gap",
        r"(?:missing|unavailable|withheld|limited)\s+(?:stocktwits|fred)",
        r"(?:stocktwits|fred)(?:\s+(?:feed|information|data))?\s+(?:is |remains? )?(?:missing|unavailable|withheld)",
        r"overall investment evidence remains limited without the supplementary feeds",
        r"does not (?:mean all data is complete or all queries failed|confirm coverage|establish a profitable trade)",
        r"that alone does not establish a profitable trade",
    ]
    availability_subject = r"coverage|completeness|global (?:news|feed)|(?:ticker|company)[- ]news|stocktwits|fred|summary|queries|(?:all|every) (?:data|sources?|feeds?)|stock necessity|(?:income statement|balance sheet|cash.flow statement|reddit|snapshot|stock.price).{0,35}(?:missing|unavailable|not available)"
    clauses = [
        clause for statement in checked for clause in re.split(r";|\bbut\b|\bhowever\b", statement)
    ]
    for statement in clauses:
        if (
            _has(availability_subject, statement)
            and not any(_has(pattern, statement) for pattern in recognized)
            and not critical
        ):
            dimensions["B"] = "needs_review"
            pending.append("unrecognized_availability_relation")
    if unresolved_attribution:
        dimensions["B"] = "needs_review"
        pending.append("unresolved_attribution")
    if critical:
        dimensions["B"] = "failed"
    positive = _has(
        r"improving (?:adoption interest|demand)|(?:price strength|rise) from 100 to 105", text
    )
    concern = _has(r"margin pressure|narrow leadership|volatility", text)
    if not output.strip():
        dimensions["C"] = "failed"
    elif role == "research-manager":
        sections = list(
            re.finditer(r"(?:^|\n)\s*(recommendation|rationale|strategic actions)\s*:\s*", text)
        )
        values = {
            item.group(1): text[
                item.end() : sections[i + 1].start() if i + 1 < len(sections) else len(text)
            ].strip()
            for i, item in enumerate(sections)
        }
        if (
            len(sections) != 3
            or set(values) != {"recommendation", "rationale", "strategic actions"}
            or values.get("recommendation")
            not in {"buy", "overweight", "hold", "underweight", "sell"}
            or not all(values.values())
        ):
            dimensions["C"] = "failed"
        elif (
            _has(
                r"improving (?:adoption interest|demand)|(?:price strength|rise) from 100 to 105",
                values["rationale"],
            )
            and _has(r"margin pressure|narrow leadership|volatility", values["rationale"])
            and _has(
                r"monitor|limit|allocate|review|reduce|increase|maintain|wait|trim|avoid",
                values["strategic actions"],
            )
        ):
            dimensions["C"] = "passed"
    elif positive and concern and _has(r"but|while|although|despite|however|yet", text):
        dimensions["C"] = "passed"
    elif "program data-availability summary:" in text:
        dimensions["C"] = "failed"
    for name, value in dimensions.items():
        if value == "needs_review":
            pending.append(f"dimension_{name}_unresolved")
    status = (
        "failed" if "failed" in dimensions.values() else "needs_review" if pending else "passed"
    )
    return {
        "case_id": cid,
        "role": role,
        "status": status,
        "dimensions": dimensions,
        "critical_failures": critical,
        "needs_review": list(dict.fromkeys(pending)),
        "output_excerpt": output,
        "recognized_case_meaning": bool(understood),
    }


def aggregate_scores(scores: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [(s["case_id"], s["role"]) for s in scores]
    matrix = [(cid, role) for cid in CASE_IDS for role in ROLES]
    errors = [] if keys == matrix else ["executed matrix is incomplete, duplicated or out of order"]
    pending = [
        f"{s['case_id']}:{s['role']}:{reason}" for s in scores for reason in s["needs_review"]
    ]
    critical = sum(len(s["critical_failures"]) for s in scores)
    failed = any(s["status"] == "failed" for s in scores)
    return {
        "status": "failed" if errors or failed else "needs_review" if pending else "passed",
        "errors": errors,
        "needs_review": pending,
        "expected_combinations": 15,
        "executed_combinations": len(scores),
        "expected_dimensions": 45,
        "passed_dimensions": sum(v == "passed" for s in scores for v in s["dimensions"].values()),
        "critical_failures": critical,
    }


class _CandidateWorker:
    def __init__(self, candidate: Path):
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in {"PYTHONPATH", "PYTHONHOME"} and not k.endswith(("API_KEY", "TOKEN"))
        }
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.process = subprocess.Popen(
            [_python_executable(), "-u", "-c", _WORKER],
            cwd=candidate.parent,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        assert self.process.stderr is not None
        self.stdin = self.process.stdin
        self.stdout = self.process.stdout
        self.stderr = self.process.stderr
        self.events: queue.Queue = queue.Queue()

        def read():
            for line in self.stdout:
                self.events.put(line)
            self.events.put(None)

        threading.Thread(target=read, daemon=True).start()

        # Drain warnings so a full pipe cannot deadlock the candidate. Raw stderr
        # is not copied into evidence (provider diagnostics can contain secrets).
        def drain():
            for _line in self.stderr:
                pass

        threading.Thread(target=drain, daemon=True).start()
        modules = [
            "tradingagents",
            "tradingagents.dataflows.availability",
            "tradingagents.dataflows.config",
            "tradingagents.agents.context",
            "tradingagents.agents.schemas",
            "tradingagents.agents.structured",
            *[pair[0] for pair in MODULES.values()],
        ]
        self.send({"candidate": str(candidate), "modules": modules, "factories": MODULES})

    def send(self, value):
        self.stdin.write(json.dumps(value) + "\n")
        self.stdin.flush()

    def receive(self):
        try:
            line = self.events.get(timeout=150)
        except queue.Empty as exc:
            raise ValueError("candidate worker timed out") from exc
        if line is None:
            raise ValueError("candidate worker exited without a protocol response")
        event = json.loads(line)
        if event.get("protocol") != "fr03-eval-v1":
            raise ValueError("unexpected candidate protocol")
        if event["kind"] in {"fatal", "role_error"}:
            raise ValueError(event["error"])
        return event

    def close(self):
        with suppress(OSError, ValueError):
            self.send({"stop": True})
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        for stream in (self.stdin, self.stdout, self.stderr):
            stream.close()


def _model_request(request: Mapping[str, Any], config: Mapping[str, Any]) -> Mapping[str, Any]:
    """One non-streaming, zero-retry call to the sole approved provider."""
    import urllib.request

    options = config["model"]["configuration"]
    body = {k: options[k] for k in ("temperature", "max_tokens", "stream", "n")}
    body.update(options["extra_body"])
    body.update(model=config["model"]["model"], messages=request["messages"], **request["options"])
    wire = urllib.request.Request(
        config["model"]["base_url"] + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["DEEPSEEK_API_KEY"],
            "Content-Type": "application/json",
        },
    )

    # Do not follow redirects with a provider credential to another origin.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    with urllib.request.build_opener(NoRedirect()).open(
        wire, timeout=options["timeout_seconds"]
    ) as response:
        data = json.load(response)
    choice = data["choices"][0]
    return {
        **choice["message"],
        "finish_reason": choice["finish_reason"],
        "usage": data.get("usage", {}),
    }


def evaluate(
    config: Mapping[str, Any],
    candidate_sha: str,
    *,
    output_dir: Path,
    model_transport: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """I3 entry. Approval/model authorization remain external human gates."""
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    details: dict[str, Any] = {
        "schema_version": "1.0",
        "candidate_sha": candidate_sha,
        "errors": [],
        "needs_review": [],
        "request_count": 0,
        "dataset_sha256": "",
        "rubric_sha256": "",
        "attempts": [],
        "cases": [],
        "import_origins": {},
    }
    budget = RequestBudget(20)
    worker = None
    scores = []
    try:
        _validate_config(config)
        root = Path.cwd().resolve()
        data, dataset_sha, rubric_sha = _load_materials(config, root)
        details.update(dataset_sha256=dataset_sha, rubric_sha256=rubric_sha)
        candidate = root / "candidate"
        if not re.fullmatch(r"[0-9a-f]{40}", candidate_sha):
            raise ValueError("candidate must be an exact full SHA")
        actual = subprocess.check_output(
            ["git", "-C", str(candidate), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if actual != candidate_sha:
            raise ValueError("candidate HEAD does not match candidate_sha")
        if model_transport is None and not os.environ.get("DEEPSEEK_API_KEY", "").strip():
            raise ValueError("DEEPSEEK_API_KEY is missing")
        worker = _CandidateWorker(candidate)
        ready = worker.receive()
        if ready["kind"] != "ready":
            raise ValueError("candidate did not complete import preflight")
        details["import_origins"] = ready["origins"]
        for case in data["cases"]:
            for role in ROLES:
                worker.send({"case": copy.deepcopy(case), "role": role})
                combination_attempts: list[dict[str, Any]] = []
                while True:
                    event = worker.receive()
                    if event["kind"] == "result":
                        if not combination_attempts:
                            raise ValueError("candidate returned output without a model request")
                        scored = score_output(case, role, event["output"])
                        scores.append(scored)
                        details["cases"].append({**scored, "attempts": combination_attempts})
                        break
                    if event["kind"] != "request":
                        raise ValueError("unexpected candidate event")
                    req = event["request"]
                    if (req.get("case_id"), req.get("role")) != (case["case_id"], role):
                        raise ValueError("candidate request identity mismatch")
                    kinds = [a["request"]["attempt_kind"] for a in combination_attempts]
                    allowed = (
                        ["structured", "plain"]
                        if not kinds and role == "research-manager"
                        else ["plain"]
                        if not kinds
                        else ["fallback"]
                        if kinds == ["structured"] and role == "research-manager"
                        else []
                    )
                    if req.get("attempt_kind") not in allowed:
                        raise ValueError("candidate exceeded the approved role/fallback schedule")
                    req["model"] = copy.deepcopy(config["model"])
                    attempt = {"request": req}
                    details["attempts"].append(attempt)
                    combination_attempts.append(attempt)
                    try:
                        budget.take()
                        response = (
                            model_transport(req)
                            if model_transport is not None
                            else _model_request(req, config)
                        )
                        if not isinstance(response, Mapping):
                            raise ValueError("model response is not a mapping")
                        # Preserve the actual model reply, not arbitrary HTTP
                        # headers or diagnostic metadata supplied by a transport.
                        response = {
                            k: response[k]
                            for k in ("content", "tool_calls", "finish_reason", "usage")
                            if k in response
                        }
                        attempt["response"] = dict(response)
                        if response.get("finish_reason") not in {"stop", "tool_calls"}:
                            raise ValueError(
                                "model response was truncated or has invalid finish reason"
                            )
                        if not isinstance(response.get("content", ""), str):
                            raise ValueError("model response content is invalid")
                        worker.send({"reply": dict(response)})
                    except Exception as exc:
                        # Do not record raw provider exceptions/headers or secret values.
                        attempt["error"] = "model attempt failed: " + type(exc).__name__
                        raise ValueError(attempt["error"]) from exc
        summary = aggregate_scores(scores)
        details["candidate_summary"] = summary
        details["status"] = summary["status"]
        details["errors"] = summary["errors"]
        details["needs_review"] = summary["needs_review"]
    except Exception as exc:
        details["status"] = "failed"
        details["errors"].append(
            str(exc) if isinstance(exc, ValueError) else "evaluation failed: " + type(exc).__name__
        )
        details["candidate_summary"] = aggregate_scores(scores)
    finally:
        if worker is not None:
            worker.close()
    details["request_count"] = budget.count
    details["unexecuted_combinations"] = [
        {"case_id": cid, "role": role}
        for cid in CASE_IDS
        for role in ROLES
        if not any(s["case_id"] == cid and s["role"] == role for s in scores)
    ]
    encoded = (json.dumps(details, ensure_ascii=False, indent=2) + "\n").encode()
    # Never overwrite earlier attempts or follow a pre-existing filename symlink.
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=out, prefix="data-availability-details-", suffix=".json", delete=False
    ) as handle:
        handle.write(encoded)
        path = Path(handle.name)
    return {
        **details,
        "details_path": str(path),
        "details_sha256": hashlib.sha256(encoded).hexdigest(),
    }
