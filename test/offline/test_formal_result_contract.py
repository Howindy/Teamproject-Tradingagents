"""IF-19 / IR-03: a formal consumer must reject incomplete or inconsistent results."""

import pytest

from tradingagents.agents.rating import run_rating


def formal_result():
    return {
        "model_proposal": {"rating": "Buy", "text": "Rating: Buy"},
        "gate_status": "blocked",
        "final_rating": "REVIEW",
        "final_trade_decision": "Manual review required",
        "reasons": ["risk blocked"],
    }


def test_business_review_is_deliverable():
    assert run_rating(formal_result()) == "REVIEW"


@pytest.mark.parametrize("field", list(formal_result()))
def test_missing_formal_field_is_an_execution_error(field):
    state = formal_result()
    del state[field]
    with pytest.raises((ValueError, RuntimeError)):
        run_rating(state)


@pytest.mark.parametrize(
    "change",
    [
        {"final_trade_decision": "  "},
        {"gate_status": "passed"},
        {"final_rating": "Buy"},
        {"reasons": []},
    ],
)
def test_malformed_formal_result_is_an_execution_error(change):
    with pytest.raises((ValueError, RuntimeError)):
        run_rating(formal_result() | change)


@pytest.mark.parametrize(
    "change",
    [
        {"gate_status": "unknown"},
        {"gate_status": "error", "final_rating": "Buy"},
        {"model_proposal": {"rating": 7, "text": None}},
        {"model_proposal": {"rating": "Buy"}},
        {"reasons": ["  "]},
        {"reasons": "risk blocked"},
    ],
)
def test_if19_field_types_and_status_domain(change):
    with pytest.raises((ValueError, RuntimeError)):
        run_rating(formal_result() | change)


def test_blocked_illegal_advisory_rating_still_delivers_review():
    state = formal_result() | {"model_proposal": {"rating": "Undecided", "text": None}}
    assert run_rating(state) == "REVIEW"


def test_formal_rating_is_never_recovered_by_parsing(monkeypatch):
    from tradingagents.agents import rating

    monkeypatch.setattr(
        rating, "parse_rating", lambda *a: pytest.fail("formal rating was reparsed")
    )
    state = formal_result()
    del state["final_rating"]
    with pytest.raises((ValueError, RuntimeError)):
        run_rating(state)


@pytest.mark.parametrize("consumer", ["display", "report"])
def test_missing_field_rejected_before_formal_display_or_report(consumer, tmp_path, capsys):
    from cli.display import display_complete_report
    from tradingagents.reporting import write_report_tree

    state = formal_result()
    del state["gate_status"]
    with pytest.raises((ValueError, RuntimeError)):
        if consumer == "display":
            display_complete_report(state)
        else:
            write_report_tree(state, "AAPL", tmp_path)
    assert state["final_trade_decision"] not in capsys.readouterr().out
    assert not list(tmp_path.rglob("*.md"))
