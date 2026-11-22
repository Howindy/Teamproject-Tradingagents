"""Offline contract tests for the SB-01 deterministic final recommendation core.

Traceability: SB-01-FC01 through SB-01-FC04; core IR-01 and IR-02 responsibility.
Frozen specification: ``docs/plans/round-02.md`` at
``8ad99c25ea1acd77b6e019fbe3c357899e8fc535`` (R02-01 through R02-11).

The callable under test is the approved IF-09 interface,
``tradingagents.final_recommendation.evaluate(proposal, availability, risk,
asset_type)``. Inputs are hand-authored consumer fixtures. They are not a
production FR-03 producer and do not claim current-run sourcing. Expected
values come from D1 SB-01 and the approved round table; the implementation
under test is never used as its own oracle.
"""

from __future__ import annotations

import ast
import copy
import importlib
import inspect
import json

import pytest

from tradingagents.final_recommendation import evaluate

pytestmark = pytest.mark.unit

LEGAL_RATINGS = ("Buy", "Overweight", "Hold", "Underweight", "Sell")
APPLICABLE_STOCK_RATINGS = ("Buy", "Overweight")
REQUIRED_FIELDS = (
    "model_proposal",
    "gate_status",
    "reasons",
    "final_rating",
    "final_trade_decision",
)
ORIGINAL_TEXT = "MODEL-ORIGINAL: retain this conclusion"

# AST import prefixes that would make the pure core depend on model, data,
# graph, storage, or risk-recomputation code. This is a narrow structural
# check, not a general dependency scanner.
FORBIDDEN_IMPORT_PREFIXES = (
    "tradingagents.dataflows",
    "tradingagents.graph",
    "tradingagents.memory",
    "tradingagents.reporting",
    "tradingagents.run_context",
    "tradingagents.history",
    "tradingagents.portfolio_risk",
)


class _Missing:
    """Marker for an argument the caller did not supply."""


_MISSING = _Missing()


class _UnsafeText:
    """An arbitrary object that records any ``str``/``repr`` conversion."""

    SENTINEL = "UNSAFE_STRING_SENTINEL"

    def __init__(self):
        self.str_calls = 0
        self.repr_calls = 0

    def __str__(self):
        self.str_calls += 1
        return self.SENTINEL

    def __repr__(self):
        self.repr_calls += 1
        return self.SENTINEL


def _proposal(rating="Buy", text=ORIGINAL_TEXT):
    """A controlled model proposal with an unrelated field that must not copy."""
    return {
        "rating": rating,
        "text": text,
        "unrelated_field": "DO-NOT-COPY",
    }


def _necessary_item(*, status="available", reason="", label="global news"):
    """One controlled D2-shaped necessary item."""
    return {
        "id": "global_news",
        "method": "get_news",
        "label": label,
        "object": "AAPL",
        "range": "2026-11-01..2026-11-20",
        "status": status,
        "reason": reason,
    }


def _availability():
    """Controlled complete FR-03-shaped summary (fixture B)."""
    return {
        "basic_completeness": "complete",
        "applicability_note": "",
        "observations": [
            {
                "method": "get_news",
                "object": "AAPL",
                "status": "available",
                "reason": "",
            }
        ],
        "necessary_items": [_necessary_item()],
        "supplementary_limitations": [],
    }


def _risk(status="passed", **overrides):
    """A controlled FR-04-shaped risk result."""
    data = {"status": status}
    data.update(overrides)
    return data


def _call(
    *,
    proposal=_MISSING,
    availability=_MISSING,
    risk=_MISSING,
    asset_type="stock",
    positional=False,
):
    """Call the fixed four-parameter interface by keyword or position."""
    if proposal is _MISSING:
        proposal = _proposal()
    if availability is _MISSING:
        availability = _availability()
    if risk is _MISSING:
        risk = _risk()
    if positional:
        return evaluate(proposal, availability, risk, asset_type)
    return evaluate(
        proposal=proposal,
        availability=availability,
        risk=risk,
        asset_type=asset_type,
    )


def _assert_required_shape(result):
    """Required fields and clean JSON-compatible field types."""
    assert isinstance(result, dict)
    for field in REQUIRED_FIELDS:
        assert field in result, field
    assert result["gate_status"] in {"passed", "blocked", "error"}
    assert isinstance(result["reasons"], list)
    assert all(isinstance(reason, str) for reason in result["reasons"])
    assert isinstance(result["final_rating"], str)
    assert isinstance(result["final_trade_decision"], str)
    assert result["final_trade_decision"].strip()

    model_proposal = result["model_proposal"]
    assert model_proposal is None or isinstance(model_proposal, dict)
    if isinstance(model_proposal, dict):
        assert "rating" in model_proposal
        assert "text" in model_proposal
        assert model_proposal["rating"] is None or isinstance(
            model_proposal["rating"], str
        )
        assert model_proposal["text"] is None or isinstance(
            model_proposal["text"], str
        )


def _reasons_text(result):
    """Lower-case SB-01 top-level reasons only."""
    return " | ".join(result["reasons"]).lower()


def _notice_text(result):
    """Lower-case program-generated formal conclusion only."""
    return result["final_trade_decision"].lower()


def _assert_reasons_mention(result, *tokens):
    text = _reasons_text(result)
    lowered = tuple(token.lower() for token in tokens)
    assert any(token in text for token in lowered), (tokens, result["reasons"])


def _assert_notice_mentions(result, *tokens):
    text = _notice_text(result)
    lowered = tuple(token.lower() for token in tokens)
    assert any(token in text for token in lowered), (
        tokens,
        result["final_trade_decision"],
    )


def _assert_both_mention(result, *tokens):
    """The actual explanation must appear in reasons and in the notice."""
    _assert_reasons_mention(result, *tokens)
    _assert_notice_mentions(result, *tokens)


def _assert_reason_in_both(result, sentinel):
    """A supplied controlled cause must survive in reasons and in the notice."""
    lowered = sentinel.lower()
    assert lowered in _reasons_text(result), (sentinel, result["reasons"])
    assert lowered in _notice_text(result), (
        sentinel,
        result["final_trade_decision"],
    )


def _assert_notice_excludes(result, original_text):
    """A non-empty original proposal must not be appended to the formal notice."""
    if isinstance(original_text, str) and original_text.strip():
        assert original_text not in result["final_trade_decision"]


def _assert_model_proposal_retained(result, *, rating=_MISSING, text=_MISSING):
    projected = result["model_proposal"]
    assert isinstance(projected, dict)
    if rating is not _MISSING:
        assert projected["rating"] == rating
    if text is not _MISSING:
        assert projected["text"] == text
    return projected


def _assert_manual_review(result):
    assert result["final_rating"] == "REVIEW"
    assert result["reasons"]
    assert result["final_trade_decision"].strip()
    lowered = result["final_trade_decision"].lower()
    assert "review" in lowered or "manual" in lowered


def _assert_passed(result, *, rating, text=ORIGINAL_TEXT):
    _assert_required_shape(result)
    assert result["gate_status"] == "passed"
    assert result["final_rating"] == rating
    assert result["final_trade_decision"] == text


def _assert_blocked(result, *, reasons_tokens=(), notice_tokens=_MISSING):
    _assert_required_shape(result)
    assert result["gate_status"] == "blocked"
    _assert_manual_review(result)
    if reasons_tokens:
        _assert_reasons_mention(result, *reasons_tokens)
    if notice_tokens is _MISSING:
        notice_tokens = reasons_tokens
    if notice_tokens:
        _assert_notice_mentions(result, *notice_tokens)


def _assert_json_compatible(result):
    """Standard JSON serialization without an implicit encoder."""
    payload = json.dumps(result, allow_nan=False)
    assert json.loads(payload) == result
    return payload


def _assert_no_duplicate_status_fields(result):
    assert "status" not in result
    assert "gate_reasons" not in result
    assert "present" not in result
    if isinstance(result["model_proposal"], dict):
        assert "present" not in result["model_proposal"]


def _assert_no_shared_containers(result, proposal, availability, risk):
    """Returned containers must not alias caller-owned mutable containers."""
    if isinstance(result["model_proposal"], dict):
        assert result["model_proposal"] is not proposal
    assert result["reasons"] is not availability.get("necessary_items")
    assert result["reasons"] is not availability.get("supplementary_limitations")
    if isinstance(risk, dict):
        assert result["reasons"] is not risk.get("reasons")


def _imported_modules(tree):
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = f"tradingagents.{base}" if base else "tradingagents"
            names.append(base)
            if base == "tradingagents":
                names.extend(
                    f"tradingagents.{alias.name}" for alias in node.names
                )
    return names


def _inject_internal_failure(monkeypatch):
    """Inject one failure at the tentative private C-09 decision boundary.

    The C-09 core does not exist yet. ``_evaluate_impl`` is a tentative name
    borrowed from the C-08 shape; it is not a production naming contract. Before
    implementation acceptance, confirm this patch still occurs after ordinary
    input validation. If the implementation names the boundary differently,
    move the patch to that boundary without changing the approved behavior
    assertions (error/REVIEW, safe notice, preserved safe proposal, and no raw
    exception text). No production fault-injection hook is added.
    """
    import tradingagents.final_recommendation as module

    def boom(*_args, **_kwargs):
        raise RuntimeError("INJECTED_INTERNAL_FAILURE")

    monkeypatch.setattr(module, "_evaluate_impl", boom)


def _invalid_availability(case):
    if case == "none":
        return None
    if case == "non_mapping_list":
        return ["complete"]
    if case == "non_mapping_string":
        return "complete"

    availability = _availability()
    if case == "missing_completeness":
        del availability["basic_completeness"]
    elif case == "illegal_completeness":
        availability["basic_completeness"] = "maybe"
    elif case == "missing_necessary_items":
        del availability["necessary_items"]
    elif case == "non_list_necessary_items":
        availability["necessary_items"] = {"id": "global_news"}
    elif case == "non_mapping_item":
        availability["necessary_items"] = ["available"]
    elif case == "illegal_item_status":
        availability["necessary_items"] = [_necessary_item(status="unknown")]
    elif case == "wrong_type_item_status":
        availability["necessary_items"] = [_necessary_item(status=None)]
    elif case == "wrong_type_item_reason":
        availability["necessary_items"] = [
            _necessary_item(status="no_data", reason=123)
        ]
    elif case == "missing_applicability_note":
        del availability["applicability_note"]
    elif case == "wrong_type_applicability_note":
        availability["applicability_note"] = 123
    elif case == "complete_with_non_available_item":
        availability["necessary_items"] = [
            _necessary_item(),
            _necessary_item(
                status="no_data", reason="CONTRADICTION_SENTINEL: no rows"
            ),
        ]
    elif case == "incomplete_without_gap":
        availability["basic_completeness"] = "incomplete"
        availability["necessary_items"] = []
    elif case == "incomplete_gap_without_reason":
        availability["basic_completeness"] = "incomplete"
        availability["necessary_items"] = [
            _necessary_item(status="no_data", reason="")
        ]
    elif case == "incomplete_gap_null_reason":
        availability["basic_completeness"] = "incomplete"
        availability["necessary_items"] = [
            _necessary_item(status="no_data", reason=None)
        ]
    else:  # pragma: no cover - guarded by the parameter list
        raise AssertionError(case)
    return availability


def _risk_for_case(case):
    if case == "passed":
        return _risk("passed")
    if case == "blocked":
        return _risk("blocked", reasons=["RISK_BLOCK_SENTINEL"])
    if case == "error":
        return _risk("error", reasons=["RISK_ERROR_SENTINEL"])
    if case == "none":
        return None
    if case == "non_mapping_string":
        return "passed"
    if case == "non_mapping_list":
        return ["passed"]
    if case == "missing_status":
        return {}
    if case == "wrong_type_status":
        return {"status": 123}
    if case == "illegal_status":
        return {"status": "unknown"}
    if case == "not_applicable":
        return {"status": "not_applicable"}
    if case == "case_variant":
        return {"status": "PASSED"}
    raise AssertionError(case)


# ---------------------------------------------------------------------------
# R02-01: five legal ratings, original values retained, positional/keyword.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("positional", [False, True], ids=["keyword", "positional"])
@pytest.mark.parametrize("rating", LEGAL_RATINGS)
def test_r02_01_legal_rating_passes_and_preserves_model_values(rating, positional):
    """R02-01 / SB-01-FC01, IR-01 core."""
    proposal = _proposal(rating=rating, text=ORIGINAL_TEXT)
    risk = _risk("passed") if rating in APPLICABLE_STOCK_RATINGS else None

    result = _call(proposal=proposal, risk=risk, positional=positional)

    _assert_passed(result, rating=rating, text=ORIGINAL_TEXT)
    projected = result["model_proposal"]
    assert projected is not None
    assert projected["rating"] == rating
    assert projected["text"] == ORIGINAL_TEXT
    assert "unrelated_field" not in projected
    _assert_no_duplicate_status_fields(result)


# ---------------------------------------------------------------------------
# R02-02: missing/invalid proposals are ordinary blocked input, never guessed.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        "none",
        "non_mapping_list",
        "non_mapping_string",
        "missing_rating",
        "null_rating",
        "review_rating",
        "unknown_rating",
        "text_claims_rating",
        "non_string_rating",
    ],
)
def test_r02_02_invalid_proposal_blocks_without_fabrication(case):
    """R02-02 / SB-01-FC04, IR-01 core."""
    unrelated = "DO-NOT-COPY"
    unsafe = None
    if case == "none":
        proposal = None
    elif case == "non_mapping_list":
        proposal = ["Buy", ORIGINAL_TEXT]
    elif case == "non_mapping_string":
        proposal = f"Rating: Buy\n{ORIGINAL_TEXT}"
    elif case == "missing_rating":
        proposal = {"text": ORIGINAL_TEXT, "unrelated_field": unrelated}
    elif case == "null_rating":
        proposal = {"rating": None, "text": ORIGINAL_TEXT, "unrelated_field": unrelated}
    elif case == "review_rating":
        proposal = {
            "rating": "REVIEW",
            "text": ORIGINAL_TEXT,
            "unrelated_field": unrelated,
        }
    elif case == "unknown_rating":
        proposal = {
            "rating": "Strong Buy",
            "text": ORIGINAL_TEXT,
            "unrelated_field": unrelated,
        }
    elif case == "text_claims_rating":
        proposal = {
            "text": f"Rating: Buy\n{ORIGINAL_TEXT}",
            "unrelated_field": unrelated,
        }
    elif case == "non_string_rating":
        unsafe = _UnsafeText()
        proposal = {
            "rating": unsafe,
            "text": ORIGINAL_TEXT,
            "unrelated_field": unrelated,
        }
    else:  # pragma: no cover - guarded by the parameter list
        raise AssertionError(case)

    result = _call(proposal=proposal)

    _assert_blocked(result, reasons_tokens=("rating", "proposal", "recommendation"))
    assert result["final_rating"] not in LEGAL_RATINGS

    if not isinstance(proposal, dict):
        assert result["model_proposal"] is None
    else:
        projected = _assert_model_proposal_retained(result, text=proposal["text"])
        assert "unrelated_field" not in projected
        if case in {
            "missing_rating",
            "null_rating",
            "text_claims_rating",
            "non_string_rating",
        }:
            assert projected["rating"] is None
        else:
            assert projected["rating"] == proposal["rating"]
        _assert_notice_excludes(result, proposal["text"])

    if unsafe is not None:
        assert unsafe.str_calls == 0
        assert unsafe.repr_calls == 0
        payload = _assert_json_compatible(result)
        assert unsafe.SENTINEL not in payload


# ---------------------------------------------------------------------------
# R02-03: valid text is never trimmed; invalid text is ordinary blocked input.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "  leading and trailing  ",
        "line one\nline two\nline three",
        "Unicode: \u4e70\u5165 caf\u00e9 \u2014 na\u00efve",
        "trailing newline\n",
    ],
    ids=["whitespace", "multiline", "unicode", "trailing-newline"],
)
def test_r02_03_valid_text_is_preserved_exactly(text):
    """R02-03 / SB-01-FC01, SB-01-FC04."""
    result = _call(proposal=_proposal("Buy", text))

    _assert_passed(result, rating="Buy", text=text)
    assert result["model_proposal"]["text"] == text


@pytest.mark.parametrize(
    "case", ["missing", "null", "non_string", "empty", "whitespace"]
)
def test_r02_03_invalid_text_is_ordinary_blocked_not_error(case):
    """R02-03 / SB-01-FC01, SB-01-FC04."""
    unsafe = None
    if case == "missing":
        proposal = {"rating": "Buy", "unrelated_field": "DO-NOT-COPY"}
    elif case == "null":
        proposal = {"rating": "Buy", "text": None}
    elif case == "non_string":
        unsafe = _UnsafeText()
        proposal = {"rating": "Buy", "text": unsafe}
    elif case == "empty":
        proposal = {"rating": "Buy", "text": ""}
    elif case == "whitespace":
        proposal = {"rating": "Buy", "text": "  \n\t  "}
    else:  # pragma: no cover - guarded by the parameter list
        raise AssertionError(case)

    result = _call(proposal=proposal)

    _assert_blocked(
        result,
        reasons_tokens=("text", "conclusion", "recommendation", "proposal"),
    )
    assert result["gate_status"] == "blocked"
    if case in {"missing", "null", "non_string"}:
        _assert_model_proposal_retained(result, rating="Buy", text=None)
    else:
        _assert_model_proposal_retained(
            result, rating="Buy", text=proposal["text"]
        )
        assert proposal["text"].strip() == ""
        assert result["final_trade_decision"].strip()
        assert result["final_trade_decision"] != proposal["text"]

    if unsafe is not None:
        assert unsafe.str_calls == 0
        assert unsafe.repr_calls == 0
        assert unsafe.SENTINEL not in _assert_json_compatible(result)


# ---------------------------------------------------------------------------
# R02-04: exact stock/crypto boundary; no guessing or alias policy.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rating", ["Hold", "Underweight", "Sell"])
def test_r02_04_legal_stock_non_applicable_ratings_do_not_require_risk(rating):
    """R02-04 / SB-01-FC01, SB-01-FC03, SB-01-FC04, IR-02 core."""
    result = _call(proposal=_proposal(rating), risk=None)

    _assert_passed(result, rating=rating)


@pytest.mark.parametrize("rating", LEGAL_RATINGS)
def test_r02_04_legal_crypto_ratings_do_not_require_risk(rating):
    """R02-04 / SB-01-FC01, SB-01-FC03, SB-01-FC04, IR-02 core."""
    result = _call(
        proposal=_proposal(rating),
        risk=None,
        asset_type="crypto",
    )

    _assert_passed(result, rating=rating)


@pytest.mark.parametrize(
    "asset_type",
    [None, 123, "", "Stock", "STOCK", "stocks", "equity", "crypto ", ["stock"]],
)
def test_r02_04_invalid_asset_type_blocks_without_guessing(asset_type):
    """R02-04 / SB-01-FC04, IR-02 core."""
    result = _call(asset_type=asset_type, risk=_risk("passed"))

    _assert_blocked(
        result,
        reasons_tokens=(
            "asset",
            "instrument",
            "market",
            "type",
            "unsupported",
            "invalid",
        ),
    )
    assert result["gate_status"] == "blocked"
    _assert_model_proposal_retained(result, rating="Buy", text=ORIGINAL_TEXT)
    _assert_notice_excludes(result, ORIGINAL_TEXT)


# ---------------------------------------------------------------------------
# R02-05: incomplete necessary data blocks with the supplied actual reason.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status, reason, sentinel",
    [
        ("no_data", "NO_DATA_SENTINEL: no rows returned", "NO_DATA_SENTINEL"),
        (
            "unavailable",
            "UNAVAILABLE_SENTINEL: provider failed",
            "UNAVAILABLE_SENTINEL",
        ),
        (
            "withheld",
            "WITHHELD_SENTINEL: historical policy",
            "WITHHELD_SENTINEL",
        ),
        (
            "not_attempted",
            "NOT_ATTEMPTED_SENTINEL: query not started",
            "NOT_ATTEMPTED_SENTINEL",
        ),
    ],
    ids=["no-data", "unavailable", "withheld", "not-attempted"],
)
def test_r02_05_incomplete_necessary_gap_blocks_with_supplied_reason(
    status, reason, sentinel
):
    """R02-05 / SB-01-FC02, IR-02 core."""
    availability = _availability()
    availability["basic_completeness"] = "incomplete"
    availability["necessary_items"] = [_necessary_item(status=status, reason=reason)]

    result = _call(availability=availability)

    _assert_blocked(
        result,
        reasons_tokens=(
            "necessary",
            "data",
            "incomplete",
            "missing",
            "required",
            "unavailable",
        ),
    )
    assert result["gate_status"] == "blocked"
    _assert_reasons_mention(result, "global news", "get_news", "global_news")
    _assert_reason_in_both(result, sentinel)
    _assert_model_proposal_retained(result, rating="Buy", text=ORIGINAL_TEXT)
    _assert_notice_excludes(result, ORIGINAL_TEXT)


# ---------------------------------------------------------------------------
# R02-06: supplementary-only limitations do not block; not_applicable keeps its
# note but cannot bypass an applicable risk condition.
# ---------------------------------------------------------------------------


def test_r02_06_supplementary_limitation_alone_does_not_block():
    """R02-06 / SB-01-FC02."""
    availability = _availability()
    availability["supplementary_limitations"] = [
        _necessary_item(
            status="unavailable",
            reason="SUPPLEMENTARY_SENTINEL: ticker news failed",
        )
    ]

    result = _call(availability=availability)

    _assert_passed(result, rating="Buy")


def test_r02_06_not_applicable_note_is_retained_and_does_not_alone_block():
    """R02-06 / SB-01-FC02."""
    note = "NOT_APPLICABLE_SENTINEL: basic necessity list does not apply"
    availability = {
        "basic_completeness": "not_applicable",
        "applicability_note": note,
        "observations": [],
        "necessary_items": [],
        "supplementary_limitations": [],
    }

    result = _call(
        proposal=_proposal("Buy"),
        availability=availability,
        risk=None,
        asset_type="crypto",
    )

    _assert_passed(result, rating="Buy", text=ORIGINAL_TEXT)
    assert any(note in reason for reason in result["reasons"])


def test_r02_06_not_applicable_does_not_bypass_applicable_risk():
    """R02-06 / SB-01-FC02, SB-01-FC03, IR-02 core."""
    availability = {
        "basic_completeness": "not_applicable",
        "applicability_note": "NOT_APPLICABLE_SENTINEL: basic list does not apply",
        "observations": [],
        "necessary_items": [],
        "supplementary_limitations": [],
    }

    result = _call(
        proposal=_proposal("Buy"),
        availability=availability,
        risk=None,
        asset_type="stock",
    )

    _assert_blocked(result, reasons_tokens=("risk",))
    assert result["gate_status"] == "blocked"
    _assert_both_mention(
        result,
        "missing",
        "invalid",
        "not pass",
        "did not pass",
        "confirm",
        "fail",
    )
    _assert_model_proposal_retained(result, rating="Buy", text=ORIGINAL_TEXT)
    _assert_notice_excludes(result, ORIGINAL_TEXT)


# ---------------------------------------------------------------------------
# R02-07: invalid or contradictory consumed availability fields block.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        "none",
        "non_mapping_list",
        "non_mapping_string",
        "missing_completeness",
        "illegal_completeness",
        "missing_necessary_items",
        "non_list_necessary_items",
        "non_mapping_item",
        "illegal_item_status",
        "wrong_type_item_status",
        "wrong_type_item_reason",
        "missing_applicability_note",
        "wrong_type_applicability_note",
        "complete_with_non_available_item",
        "incomplete_without_gap",
        "incomplete_gap_without_reason",
        "incomplete_gap_null_reason",
    ],
)
def test_r02_07_missing_or_invalid_consumed_data_fields_block(case):
    """R02-07 / SB-01-FC04, IR-02 core."""
    result = _call(availability=_invalid_availability(case))

    _assert_blocked(
        result,
        reasons_tokens=(
            "data",
            "availability",
            "summary",
            "complete",
            "necessary",
            "contradiction",
            "unconfirmable",
            "invalid",
            "missing",
            "applicability",
            "note",
            "status",
            "reason",
            "item",
        ),
    )
    assert result["gate_status"] == "blocked"
    _assert_model_proposal_retained(result, rating="Buy", text=ORIGINAL_TEXT)
    _assert_notice_excludes(result, ORIGINAL_TEXT)


# ---------------------------------------------------------------------------
# R02-08: only risk.status == "passed" satisfies stock Buy/Overweight.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rating", APPLICABLE_STOCK_RATINGS)
@pytest.mark.parametrize(
    "case",
    [
        "passed",
        "blocked",
        "error",
        "none",
        "non_mapping_string",
        "non_mapping_list",
        "missing_status",
        "wrong_type_status",
        "illegal_status",
        "not_applicable",
        "case_variant",
    ],
)
def test_r02_08_only_passed_risk_satisfies_stock_buy_or_overweight(rating, case):
    """R02-08 / SB-01-FC03, IR-02 core."""
    result = _call(proposal=_proposal(rating), risk=_risk_for_case(case))

    if case == "passed":
        _assert_passed(result, rating=rating)
    else:
        _assert_blocked(result, reasons_tokens=("risk",))
        assert result["gate_status"] == "blocked"
        _assert_both_mention(
            result,
            "block",
            "fail",
            "confirm",
            "not pass",
            "did not pass",
            "missing",
            "invalid",
            "illegal",
            "not applicable",
            "not_applicable",
            "unavailable",
            "error",
            "wrong",
            "type",
            "malformed",
            "mapping",
        )
        _assert_model_proposal_retained(result, rating=rating, text=ORIGINAL_TEXT)
        _assert_notice_excludes(result, ORIGINAL_TEXT)


def test_r02_08_risk_reasons_stay_out_of_the_top_level_result():
    """R02-08 / SB-01-FC03, IR-02 core."""
    risk = {
        "status": "blocked",
        "reasons": ["RISK_REASON_SENTINEL"],
        "projected_weight": "0.99",
    }
    before = copy.deepcopy(risk)

    result = _call(risk=risk)

    _assert_blocked(result, reasons_tokens=("risk",))
    _assert_both_mention(
        result,
        "block",
        "fail",
        "confirm",
        "not pass",
        "did not pass",
    )
    assert "RISK_REASON_SENTINEL" not in result["reasons"]
    assert "RISK_REASON_SENTINEL" not in result["final_trade_decision"]
    _assert_model_proposal_retained(result, rating="Buy", text=ORIGINAL_TEXT)
    _assert_notice_excludes(result, ORIGINAL_TEXT)
    assert risk == before


# ---------------------------------------------------------------------------
# R02-09: model text cannot override program inputs or decide the rating.
# ---------------------------------------------------------------------------


def test_r02_09_model_claims_cannot_override_data_or_risk_inputs():
    """R02-09 / SB-01-FC02, SB-01-FC03, SB-01-FC04."""
    availability = _availability()
    availability["basic_completeness"] = "incomplete"
    availability["necessary_items"] = [
        _necessary_item(status="no_data", reason="DATA_STILL_MISSING_SENTINEL")
    ]
    proposal = _proposal(
        "Buy",
        "Data is complete and the risk check passed. Rating: Buy",
    )

    result = _call(proposal=proposal, availability=availability, risk=None)

    _assert_blocked(result, reasons_tokens=("data",))
    _assert_both_mention(result, "data_still_missing_sentinel")
    _assert_both_mention(result, "risk")
    _assert_both_mention(
        result,
        "missing",
        "incomplete",
        "not pass",
        "did not pass",
        "confirm",
        "fail",
    )
    _assert_model_proposal_retained(result, rating="Buy", text=proposal["text"])
    _assert_notice_excludes(result, proposal["text"])


def test_r02_09_structured_rating_wins_over_conflicting_text_label():
    """R02-09 / SB-01-FC01, SB-01-FC04."""
    text = f"Rating: Sell\n{ORIGINAL_TEXT}"

    result = _call(proposal=_proposal("Hold", text), risk=None)

    _assert_passed(result, rating="Hold", text=text)
    assert result["model_proposal"]["rating"] == "Hold"
    assert result["final_rating"] == "Hold"
    assert result["final_rating"] != "Sell"
    assert text in result["final_trade_decision"]


def test_r02_09_data_and_risk_problems_are_both_explained_without_order():
    """R02-09 / SB-01-FC02, SB-01-FC03, SB-01-FC04."""
    availability = _availability()
    availability["basic_completeness"] = "incomplete"
    availability["necessary_items"] = [
        _necessary_item(
            status="unavailable",
            reason="DATA_GAP_SENTINEL: provider down",
        )
    ]

    result = _call(
        availability=availability,
        risk=_risk("error", reasons=["RISK_ERROR_SENTINEL"]),
    )

    _assert_blocked(result, reasons_tokens=("data",))
    _assert_both_mention(result, "data_gap_sentinel")
    _assert_both_mention(result, "risk")
    _assert_both_mention(
        result,
        "fail",
        "confirm",
        "not pass",
        "did not pass",
        "unavailable",
        "incomplete",
        "error",
    )
    _assert_model_proposal_retained(result, rating="Buy", text=ORIGINAL_TEXT)
    _assert_notice_excludes(result, ORIGINAL_TEXT)
    assert result["gate_status"] == "blocked"


# ---------------------------------------------------------------------------
# R02-10: a handled internal exception is error/REVIEW, not blocked.
# ---------------------------------------------------------------------------


def test_r02_10_internal_exception_becomes_error_review(monkeypatch):
    """R02-10 / SB-01-FC04, IR-02 core."""
    proposal = _proposal()
    availability = _availability()
    risk = _risk("passed")

    _inject_internal_failure(monkeypatch)
    result = evaluate(
        proposal=proposal,
        availability=availability,
        risk=risk,
        asset_type="stock",
    )

    _assert_required_shape(result)
    assert result["gate_status"] == "error"
    assert result["final_rating"] == "REVIEW"
    assert result["reasons"]
    _assert_manual_review(result)
    _assert_both_mention(result, "check", "internal", "error", "fail")

    payload = _assert_json_compatible(result)
    lowered = payload.lower()
    assert "injected_internal_failure" not in lowered
    assert "traceback" not in lowered
    _assert_model_proposal_retained(result, rating="Buy", text=ORIGINAL_TEXT)
    _assert_notice_excludes(result, ORIGINAL_TEXT)


# ---------------------------------------------------------------------------
# R02-11: JSON contract, input isolation, safe strings, and core purity.
# ---------------------------------------------------------------------------


def _assert_contract_for_result(result, gate):
    _assert_required_shape(result)
    assert result["gate_status"] == gate
    _assert_no_duplicate_status_fields(result)
    if gate == "passed":
        assert result["final_rating"] in LEGAL_RATINGS
    else:
        assert result["final_rating"] == "REVIEW"
        assert result["reasons"]
    _assert_json_compatible(result)


def test_r02_11_representative_results_are_json_safe_and_do_not_alias_inputs(
    monkeypatch,
):
    """R02-11 / SB-01-FC01 through SB-01-FC04, IR-01/IR-02 core."""
    # Passed output with a controlled applicability note.
    proposal = _proposal("Buy", ORIGINAL_TEXT)
    availability = _availability()
    availability["applicability_note"] = (
        "APPLICABILITY_NOTE_SENTINEL: complete basic list"
    )
    risk = _risk("passed", reasons=["RISK_PASS_SENTINEL"])
    proposal_before = copy.deepcopy(proposal)
    availability_before = copy.deepcopy(availability)
    risk_before = copy.deepcopy(risk)

    passed = _call(proposal=proposal, availability=availability, risk=risk)

    assert proposal == proposal_before
    assert availability == availability_before
    assert risk == risk_before
    _assert_contract_for_result(passed, "passed")
    _assert_no_shared_containers(passed, proposal, availability, risk)
    assert passed["final_trade_decision"] == ORIGINAL_TEXT
    _assert_model_proposal_retained(passed, rating="Buy", text=ORIGINAL_TEXT)
    assert isinstance(passed["model_proposal"], dict)
    passed["model_proposal"]["text"] = "MUTATED"
    passed["reasons"].append("MUTATED")
    assert proposal == proposal_before
    assert availability == availability_before
    assert risk == risk_before

    # Blocked output.
    blocked_availability = _availability()
    blocked_availability["basic_completeness"] = "incomplete"
    blocked_availability["necessary_items"] = [
        _necessary_item(status="no_data", reason="BLOCK_REASON_SENTINEL")
    ]
    blocked_risk = _risk("blocked", reasons=["RISK_BLOCK_SENTINEL"])
    blocked_proposal = _proposal("Buy", ORIGINAL_TEXT)
    blocked_before = copy.deepcopy(
        (blocked_proposal, blocked_availability, blocked_risk)
    )

    blocked = _call(
        proposal=blocked_proposal,
        availability=blocked_availability,
        risk=blocked_risk,
    )

    assert (blocked_proposal, blocked_availability, blocked_risk) == blocked_before
    _assert_contract_for_result(blocked, "blocked")
    _assert_no_shared_containers(
        blocked, blocked_proposal, blocked_availability, blocked_risk
    )
    _assert_model_proposal_retained(blocked, rating="Buy", text=ORIGINAL_TEXT)
    _assert_notice_excludes(blocked, ORIGINAL_TEXT)
    blocked["reasons"].append("MUTATED")
    assert (blocked_proposal, blocked_availability, blocked_risk) == blocked_before

    # Error output via the approved narrow internal injection.
    error_proposal = _proposal("Buy", ORIGINAL_TEXT)
    error_availability = _availability()
    error_risk = _risk("passed")
    error_before = copy.deepcopy((error_proposal, error_availability, error_risk))

    _inject_internal_failure(monkeypatch)
    error = evaluate(
        proposal=error_proposal,
        availability=error_availability,
        risk=error_risk,
        asset_type="stock",
    )

    assert (error_proposal, error_availability, error_risk) == error_before
    _assert_contract_for_result(error, "error")
    _assert_no_shared_containers(
        error, error_proposal, error_availability, error_risk
    )
    _assert_model_proposal_retained(error, rating="Buy", text=ORIGINAL_TEXT)
    _assert_notice_excludes(error, ORIGINAL_TEXT)
    error["reasons"].append("MUTATED")
    assert (error_proposal, error_availability, error_risk) == error_before


def test_r02_11_wrong_type_proposal_values_are_not_stringified():
    """R02-11 / SB-01-FC01 through SB-01-FC04, IR-01 core."""
    unsafe_rating = _UnsafeText()
    unsafe_text = _UnsafeText()
    unrelated = _UnsafeText()
    proposal = {
        "rating": unsafe_rating,
        "text": unsafe_text,
        "unrelated": unrelated,
    }

    result = _call(proposal=proposal)

    _assert_blocked(
        result,
        reasons_tokens=("rating", "text", "proposal", "recommendation"),
    )
    projected = result["model_proposal"]
    assert projected is not None
    assert projected["rating"] is None
    assert projected["text"] is None
    assert "unrelated" not in projected
    for unsafe in (unsafe_rating, unsafe_text, unrelated):
        assert unsafe.str_calls == 0
        assert unsafe.repr_calls == 0
    payload = _assert_json_compatible(result)
    assert _UnsafeText.SENTINEL not in payload
    assert _UnsafeText.SENTINEL.lower() not in _reasons_text(result)
    assert _UnsafeText.SENTINEL.lower() not in _notice_text(result)


def test_r02_11_core_has_no_model_data_storage_or_risk_recomputation(monkeypatch):
    """R02-11 / SB-01-FC01 through SB-01-FC04, IR-01/IR-02 core purity."""
    import tradingagents.final_recommendation as module

    tree = ast.parse(inspect.getsource(module))
    for name in _imported_modules(tree):
        for prefix in FORBIDDEN_IMPORT_PREFIXES:
            assert not (name == prefix or name.startswith(prefix + ".")), name

    def forbidden(*_args, **_kwargs):
        raise AssertionError("the pure core called an external boundary")

    for module_name, attribute in (
        ("tradingagents.portfolio_risk", "evaluate"),
        ("tradingagents.agents.rating", "parse_rating"),
        ("tradingagents.agents.rating", "extract_rating"),
        ("tradingagents.dataflows.router", "route_to_vendor"),
        ("tradingagents.dataflows.config", "get_config"),
    ):
        target = importlib.import_module(module_name)
        if hasattr(target, attribute):
            monkeypatch.setattr(target, attribute, forbidden)

    result = _call()

    _assert_passed(result, rating="Buy")
