"""Round-04A local post-implementation examples; no live-model or CI-gate claim.

Expected outcomes are manually specified from the existing requirements and
classroom boundary examples. Use real risk/final evaluators and persistence;
only a controlled risk fault and the existing offline model fixture are injected.
"""

import copy
import json
from pathlib import Path

import pytest
import test_round04a_integration as support

from tradingagents import final_recommendation, portfolio_risk

ROOT = Path(__file__).resolve().parents[2]
DRAFT = json.loads((ROOT / "docs/drafts/round04-semantic-units.json").read_text(encoding="utf-8"))
DECISION_UNITS = [u for u in DRAFT["units"] if u.get("kind") != "delivery"]
DELIVERY_UNIT = next(u for u in DRAFT["units"] if u.get("kind") == "delivery")


def run_unit(unit, monkeypatch, *, counterexample=False):
    scenario = (DRAFT["base_scenario"] | unit["scenario_overrides"]
                if unit["scenario_overrides"] is not None else None)
    proposal = {"rating": "Buy", "text": "  Original company conclusion: consider Buy.  "}
    expected = unit["expected"]
    if counterexample:
        change = unit["counterexample"]
        if change["kind"] == "scenario_override":
            scenario = scenario | change["changes"]
            expected = change["expected"]
        else:
            assert change["kind"] == "proposal_text"
            proposal["text"] = change["text"]
    availability = {
        "basic_completeness": "incomplete" if unit["data_gap"] else "complete",
        "applicability_note": "", "necessary_items": [{
            "method": "get_income_statement", "status": "unavailable" if unit["data_gap"] else "available",
            "reason": "fixture source timeout" if unit["data_gap"] else "",
        }],
    }
    if unit.get("force_risk_error"):
        def injected_error(*args, **kwargs):
            raise ArithmeticError("synthetic risk failure")
        monkeypatch.setattr(portfolio_risk, "_evaluate_stock_scenario", injected_error)
    before = copy.deepcopy((proposal, scenario, availability))
    risk = portfolio_risk.evaluate("AAPL", proposal, scenario, None, "stock")
    result = final_recommendation.evaluate(proposal, availability, risk, "stock")
    assert (proposal, scenario, availability) == before
    return result, risk, proposal, expected


@pytest.mark.parametrize("counterexample", [False, True], ids=["reference", "counterexample"])
@pytest.mark.parametrize("unit", DECISION_UNITS, ids=lambda u: u["id"])
def test_draft_decision_meaning_matches_existing_contract(unit, counterexample, monkeypatch):
    """A conflicting model narrative does not replace structured risk or availability inputs."""
    result, risk, proposal, expected = run_unit(unit, monkeypatch, counterexample=counterexample)
    assert risk["status"] == expected["risk_status"]
    assert risk["projected_weight"] == expected["weight"]
    assert risk["stop_distance"] == expected["stop"]
    assert result["gate_status"] == expected["gate_status"]
    assert result["final_rating"] == expected["final_rating"]
    final_recommendation.validate_formal_result(result)
    if expected["gate_status"] == "passed":
        assert result["final_trade_decision"] == proposal["text"]
    else:
        assert result["final_trade_decision"] != proposal["text"]
        assert "manual review" in result["final_trade_decision"].lower()
        # D2 keeps detailed FR-04 reasons in the risk result, not flattened
        # into SB-01's own top-level reasons/decision text.
        explanation = ("\n".join(risk["reasons"]) if unit.get("reason_scope") == "risk"
                       else result["final_trade_decision"])
        for term in unit["reason_terms"]:
            assert term in explanation.lower()


@pytest.fixture
def delivery(tmp_path, monkeypatch):
    result, risk, _, _ = run_unit(DELIVERY_UNIT, monkeypatch)
    graph = support.market_graph.__wrapped__(tmp_path, monkeypatch)
    state = support.delivery_state() | result | {"portfolio_risk_result": risk}
    return graph, state, tmp_path


def test_draft_saved_result_and_memory_use_checked_recommendation(delivery):
    """R4-SU-07: real state writer and memory store keep the same formal result."""
    graph, state, directory = delivery
    graph.record_decision("AAPL", support.DATE, state)
    (path,) = directory.rglob("full_states_log_*.json")
    saved = json.loads(path.read_text(encoding="utf-8"))
    (memory,) = graph.memory_log.load_entries()
    assert state["model_proposal"]["rating"] == "Buy"
    assert saved["final_rating"] == memory["rating"] == "REVIEW"
    assert saved["final_trade_decision"] == memory["decision"] == state["final_trade_decision"]


def test_draft_contradictory_formal_fields_fail_before_overwriting(delivery):
    """R4-SU-07 counterexample: malformed blocked/Buy output cannot overwrite checked evidence."""
    graph, state, directory = delivery
    graph.record_decision("AAPL", support.DATE, state)
    (path,) = directory.rglob("full_states_log_*.json")
    before = path.read_bytes(), graph.memory_log.load_entries()
    bad = copy.deepcopy(state) | DELIVERY_UNIT["counterexample"]["changes"]
    with pytest.raises(ValueError):
        graph.record_decision("AAPL", support.DATE, bad)
    assert (path.read_bytes(), graph.memory_log.load_entries()) == before
