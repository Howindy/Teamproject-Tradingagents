"""Offline tests for the FR-04 deterministic portfolio risk core.

Traceability: FR-04-FC01 through FR-04-FC04 and IR-14. The approved round
specification is ``docs/plans/round-01.md`` (R01-01 through R01-15) at commit
``a8ec42ecdf4199f91d3001fc6e2b1e887a0c5e41``.

The evaluator under test is ``tradingagents.portfolio_risk.evaluate`` (IF-08).
Expected values are calculated independently with ``fractions.Fraction``; the
implementation under test is never used as its own oracle.
"""

from __future__ import annotations

import copy
import json
import math
from decimal import Decimal
from fractions import Fraction

import pytest

from tradingagents.portfolio_risk import evaluate

pytestmark = pytest.mark.unit

DEFAULT_WEIGHT = Fraction(3, 10)
DEFAULT_STOP = Fraction(1, 20)

SCENARIO_NUMERIC_FIELDS = (
    "portfolio_value",
    "current_position_value",
    "proposed_buy_value",
    "entry_price",
    "stop_loss_price",
)


class _Missing:
    """Marker for an argument the caller did not supply."""


_MISSING = _Missing()


def _proposal(rating="Buy", text="caller scenario only"):
    return {"rating": rating, "text": text}


def _scenario(**overrides):
    data = {
        "ticker": "AAPL",
        "portfolio_value": "100000",
        "current_position_value": "0",
        "proposed_buy_value": "30000",
        "entry_price": "100",
        "stop_loss_price": "95",
        "currency": "USD",
    }
    data.update(overrides)
    return data


def _call(
    *,
    analysis_ticker="AAPL",
    proposal=_MISSING,
    scenario=_MISSING,
    thresholds=_MISSING,
    asset_type="stock",
):
    """Call the approved IF-08 interface with an explicit thresholds value."""
    if proposal is _MISSING:
        proposal = _proposal()
    if scenario is _MISSING:
        scenario = _scenario()
    if thresholds is _MISSING:
        thresholds = None
    return evaluate(
        analysis_ticker=analysis_ticker,
        proposal=proposal,
        scenario=scenario,
        thresholds=thresholds,
        asset_type=asset_type,
    )


def _as_fraction(value):
    assert isinstance(value, str) and value.strip()
    return Fraction(value)


def _reason_text(result):
    return " | ".join(result["reasons"]).lower()


def _mentions(result, *tokens):
    text = _reason_text(result)
    return any(token in text for token in tokens)


def _assert_result_shape(result):
    assert isinstance(result, dict)
    for key in (
        "status",
        "analysis_ticker",
        "scenario",
        "thresholds",
        "projected_weight",
        "stop_distance",
        "reasons",
    ):
        assert key in result
    assert result["status"] in {"passed", "blocked", "not_applicable", "error"}
    assert isinstance(result["analysis_ticker"], str)
    assert isinstance(result["scenario"], dict)
    assert isinstance(result["thresholds"], dict)
    assert result["projected_weight"] is None or isinstance(result["projected_weight"], str)
    assert result["stop_distance"] is None or isinstance(result["stop_distance"], str)
    assert isinstance(result["reasons"], list)
    assert all(isinstance(reason, str) for reason in result["reasons"])
    if result["status"] in {"blocked", "error"}:
        assert result["reasons"], f"{result['status']} result must carry an actual reason"


def _assert_metric(result, key, expected):
    assert result[key] is not None, f"{key} should be computable for these operands"
    assert _as_fraction(result[key]) == expected


def _assert_threshold(result, key, expected):
    assert key in result["thresholds"], f"{key} was used and must be reported"
    assert _as_fraction(result["thresholds"][key]) == expected


def _assert_no_formal_fields(result):
    for key in ("gate_status", "final_rating", "final_trade_decision"):
        assert key not in result


def _assert_no_exotic_numbers(value):
    assert not isinstance(value, (Decimal, Fraction))
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_no_exotic_numbers(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_exotic_numbers(item)
    elif isinstance(value, float):
        assert math.isfinite(value)


def _assert_json_safe(result):
    payload = json.dumps(result)
    _assert_no_exotic_numbers(result)
    return payload


def _evaluate_with_injected_fault(monkeypatch, **overrides):
    """Raise once at the post-validation decision boundary.

    The private helper is an implementation detail, not a public contract or a
    production fault-injection hook. Patching it here keeps the injected failure
    inside the narrow step that runs only after valid input has passed ordinary
    scenario and threshold validation.
    """
    import tradingagents.portfolio_risk as risk

    def boom(*_args, **_kwargs):
        raise RuntimeError("INJECTED_DECISION_FAILURE")

    with monkeypatch.context() as patch:
        patch.setattr(risk, "_breach_reasons", boom)
        return _call(**overrides)


def test_r01_01_default_limits_pass_with_accurate_display_input():
    """R01-01 / FR-04-FC01, IR-14."""
    result = _call()

    _assert_result_shape(result)
    assert result["status"] == "passed"
    assert result["analysis_ticker"] == "AAPL"
    assert result["scenario"]["ticker"] == "AAPL"
    assert result["scenario"]["currency"] == "USD"

    expected_scenario = {
        "portfolio_value": Fraction(100000),
        "current_position_value": Fraction(0),
        "proposed_buy_value": Fraction(30000),
        "entry_price": Fraction(100),
        "stop_loss_price": Fraction(95),
    }
    for field in SCENARIO_NUMERIC_FIELDS:
        assert _as_fraction(result["scenario"][field]) == expected_scenario[field]

    _assert_threshold(result, "max_projected_weight", DEFAULT_WEIGHT)
    _assert_threshold(result, "max_stop_distance", DEFAULT_STOP)
    _assert_metric(result, "projected_weight", DEFAULT_WEIGHT)
    _assert_metric(result, "stop_distance", DEFAULT_STOP)


@pytest.mark.parametrize(
    "overrides, expected_weight, expected_stop",
    [
        (
            {"proposed_buy_value": "20000", "stop_loss_price": "96"},
            Fraction(1, 5),
            Fraction(1, 25),
        ),
        (
            {"proposed_buy_value": "30000", "stop_loss_price": "96"},
            Fraction(3, 10),
            Fraction(1, 25),
        ),
        (
            {"proposed_buy_value": "20000", "stop_loss_price": "95"},
            Fraction(1, 5),
            Fraction(1, 20),
        ),
    ],
    ids=["both-below", "weight-equality", "stop-equality"],
)
def test_r01_02_below_and_equal_limits_pass_independently(
    overrides, expected_weight, expected_stop
):
    """R01-02 / FR-04-FC01, IR-14."""
    result = _call(scenario=_scenario(**overrides))

    _assert_result_shape(result)
    assert result["status"] == "passed"
    _assert_metric(result, "projected_weight", expected_weight)
    _assert_metric(result, "stop_distance", expected_stop)


def test_r01_03_configured_thresholds_are_honored_at_equality():
    """R01-03 / FR-04-FC01, IR-14."""
    scenario = _scenario(proposed_buy_value="40000", stop_loss_price="90")
    configured = _call(
        scenario=scenario,
        thresholds={"max_projected_weight": "0.40", "max_stop_distance": "0.10"},
    )

    _assert_result_shape(configured)
    assert configured["status"] == "passed"
    _assert_threshold(configured, "max_projected_weight", Fraction(2, 5))
    _assert_threshold(configured, "max_stop_distance", Fraction(1, 10))
    _assert_metric(configured, "projected_weight", Fraction(2, 5))
    _assert_metric(configured, "stop_distance", Fraction(1, 10))

    defaulted = _call(
        scenario=_scenario(proposed_buy_value="40000", stop_loss_price="90"),
        thresholds=None,
    )
    assert defaulted["status"] == "blocked"
    assert _mentions(defaulted, "weight", "concentration", "projected")
    assert _mentions(defaulted, "stop")


def test_r01_04_single_and_double_breaches_block_with_matching_reasons():
    """R01-04 / FR-04-FC02, IR-14."""
    assert Fraction(30001, 100000) > DEFAULT_WEIGHT
    assert Fraction(6, 100) > DEFAULT_STOP

    concentration = _call(scenario=_scenario(proposed_buy_value="30001"))
    _assert_result_shape(concentration)
    assert concentration["status"] == "blocked"
    assert _mentions(concentration, "weight", "concentration", "projected")

    stop_only = _call(scenario=_scenario(stop_loss_price="94"))
    _assert_result_shape(stop_only)
    assert stop_only["status"] == "blocked"
    assert _mentions(stop_only, "stop")

    both = _call(
        scenario=_scenario(proposed_buy_value="30001", stop_loss_price="94")
    )
    _assert_result_shape(both)
    assert both["status"] == "blocked"
    assert _mentions(both, "weight", "concentration", "projected")
    assert _mentions(both, "stop")


def test_r01_05_display_rounded_breaches_still_block():
    """R01-05 / FR-04-FC02, IR-14."""
    expected_weight_a = Fraction("30000.01") / 100000
    assert expected_weight_a > DEFAULT_WEIGHT

    result_a = _call(scenario=_scenario(proposed_buy_value="30000.01"))
    _assert_result_shape(result_a)
    assert result_a["status"] == "blocked"
    assert result_a["projected_weight"] is not None
    assert _mentions(result_a, "weight", "concentration", "projected")

    expected_weight_b = Fraction("3.0000000000000001") / 10
    assert expected_weight_b > DEFAULT_WEIGHT

    result_b = _call(
        scenario=_scenario(
            portfolio_value="10",
            current_position_value="0",
            proposed_buy_value="3.0000000000000001",
            entry_price="100",
            stop_loss_price="95",
        ),
        thresholds={"max_projected_weight": "0.3", "max_stop_distance": "0.05"},
    )
    _assert_result_shape(result_b)
    assert result_b["status"] == "blocked"
    assert result_b["projected_weight"] is not None
    assert _mentions(result_b, "weight", "concentration", "projected")
    _assert_threshold(result_b, "max_projected_weight", Fraction(3, 10))
    _assert_threshold(result_b, "max_stop_distance", Fraction(1, 20))


@pytest.mark.parametrize(
    "field, tokens",
    [
        ("ticker", ("ticker", "object", "symbol")),
        ("portfolio_value", ("portfolio",)),
        ("current_position_value", ("position",)),
        ("proposed_buy_value", ("buy", "purchase")),
        ("entry_price", ("entry",)),
        ("stop_loss_price", ("stop",)),
        ("currency", ("currency",)),
    ],
    ids=[
        "ticker",
        "portfolio-value",
        "current-position",
        "proposed-buy",
        "entry-price",
        "stop-loss",
        "currency",
    ],
)
def test_r01_06_each_missing_scenario_field_blocks(field, tokens):
    """R01-06 / FR-04-FC03, IR-14."""
    scenario = _scenario()
    scenario.pop(field)

    result = _call(proposal=_proposal("Buy"), scenario=scenario)

    _assert_result_shape(result)
    assert result["status"] == "blocked"
    assert _mentions(result, *tokens)


def test_r01_06_missing_scenario_and_ticker_mismatch_block():
    """R01-06 / FR-04-FC03, IR-14."""
    missing_scenario = _call(proposal=_proposal("Buy"), scenario=None)
    _assert_result_shape(missing_scenario)
    assert missing_scenario["status"] == "blocked"

    mismatch = _call(proposal=_proposal("Buy"), scenario=_scenario(ticker="MSFT"))
    _assert_result_shape(mismatch)
    assert mismatch["status"] == "blocked"
    assert _mentions(mismatch, "ticker", "object", "symbol")


@pytest.mark.parametrize(
    "field, value, tokens",
    [
        ("portfolio_value", 0, ("portfolio",)),
        ("portfolio_value", -1, ("portfolio",)),
        ("current_position_value", -1, ("position",)),
        ("current_position_value", 100001, ("position",)),
        ("proposed_buy_value", 0, ("buy", "purchase")),
        ("proposed_buy_value", -1, ("buy", "purchase")),
        ("entry_price", 0, ("entry", "price")),
        ("entry_price", -1, ("entry", "price")),
        ("stop_loss_price", 0, ("stop",)),
        ("stop_loss_price", -1, ("stop",)),
        ("stop_loss_price", 100, ("stop",)),
        ("stop_loss_price", 101, ("stop",)),
        ("currency", "", ("currency",)),
    ],
)
def test_r01_07_out_of_range_scenario_values_block(field, value, tokens):
    """R01-07 / FR-04-FC03, IR-14."""
    result = _call(
        proposal=_proposal("Buy"),
        scenario=_scenario(**{field: value}),
    )

    _assert_result_shape(result)
    assert result["status"] == "blocked"
    assert _mentions(result, *tokens)


def test_r01_07_missing_currency_blocks():
    """R01-07 / FR-04-FC03, IR-14."""
    scenario = _scenario()
    scenario.pop("currency")

    result = _call(proposal=_proposal("Buy"), scenario=scenario)

    _assert_result_shape(result)
    assert result["status"] == "blocked"
    assert _mentions(result, "currency")


@pytest.mark.parametrize(
    "field, value, tokens",
    [
        ("proposed_buy_value", True, ("buy", "purchase", "bool", "boolean", "invalid")),
        ("portfolio_value", float("nan"), ("portfolio", "finite", "number", "invalid")),
        (
            "current_position_value",
            float("inf"),
            ("position", "finite", "number", "invalid"),
        ),
        ("entry_price", float("-inf"), ("entry", "price", "finite", "number", "invalid")),
        (
            "stop_loss_price",
            "UNPARSEABLE_RAW_SENTINEL",
            ("stop", "parse", "number", "invalid"),
        ),
    ],
    ids=["boolean", "nan", "positive-infinity", "negative-infinity", "unparseable"],
)
def test_r01_08_non_finite_bool_and_unparseable_values_block(field, value, tokens):
    """R01-08 / FR-04-FC03, IR-14."""
    result = _call(
        proposal=_proposal("Buy"),
        scenario=_scenario(**{field: value}),
    )

    _assert_result_shape(result)
    assert result["status"] == "blocked"
    assert _mentions(result, *tokens)
    _assert_no_exotic_numbers(result)
    if isinstance(value, str):
        assert value not in _reason_text(result)
        assert value not in json.dumps(result)


@pytest.mark.parametrize(
    "thresholds, expected_weight, expected_stop",
    [
        (None, DEFAULT_WEIGHT, DEFAULT_STOP),
        ({}, DEFAULT_WEIGHT, DEFAULT_STOP),
        ({"max_projected_weight": "0.4"}, Fraction(2, 5), DEFAULT_STOP),
        ({"max_stop_distance": "0.1"}, DEFAULT_WEIGHT, Fraction(1, 10)),
        ({"max_projected_weight": "1"}, Fraction(1, 1), DEFAULT_STOP),
    ],
    ids=["none", "empty", "only-weight", "only-stop", "weight-one"],
)
def test_r01_09_omitted_and_partial_thresholds_use_per_key_defaults(
    thresholds, expected_weight, expected_stop
):
    """R01-09 / FR-04-FC03, IR-14."""
    result = _call(thresholds=thresholds)

    _assert_result_shape(result)
    assert result["status"] == "passed"
    _assert_threshold(result, "max_projected_weight", expected_weight)
    _assert_threshold(result, "max_stop_distance", expected_stop)


@pytest.mark.parametrize(
    "key, value",
    [
        ("max_projected_weight", 0),
        ("max_projected_weight", -0.1),
        ("max_projected_weight", 1.1),
        ("max_projected_weight", None),
        ("max_projected_weight", True),
        ("max_projected_weight", float("nan")),
        ("max_projected_weight", float("inf")),
        ("max_projected_weight", "UNPARSEABLE_THRESHOLD_SENTINEL"),
        ("max_stop_distance", 0),
        ("max_stop_distance", -0.1),
        ("max_stop_distance", 1),
        ("max_stop_distance", 1.1),
        ("max_stop_distance", None),
        ("max_stop_distance", True),
        ("max_stop_distance", float("nan")),
        ("max_stop_distance", float("inf")),
        ("max_stop_distance", "UNPARSEABLE_THRESHOLD_SENTINEL"),
    ],
    ids=[
        "weight-zero",
        "weight-negative",
        "weight-over-one",
        "weight-none",
        "weight-bool",
        "weight-nan",
        "weight-infinity",
        "weight-unparseable",
        "stop-zero",
        "stop-negative",
        "stop-one",
        "stop-over-one",
        "stop-none",
        "stop-bool",
        "stop-nan",
        "stop-infinity",
        "stop-unparseable",
    ],
)
def test_r01_09_explicit_invalid_threshold_blocks_without_fallback(key, value):
    """R01-09 / FR-04-FC03, IR-14."""
    result = _call(thresholds={key: value})

    _assert_result_shape(result)
    assert result["status"] == "blocked"
    assert _mentions(result, "threshold", "limit", "maximum", "max", "config", "range")
    assert key not in result["thresholds"]


def test_r01_10_metric_nullability_follows_its_own_operands():
    """R01-10 / FR-04-FC03, IR-14."""
    buy_invalid = _call(scenario=_scenario(proposed_buy_value="0"))
    _assert_result_shape(buy_invalid)
    assert buy_invalid["status"] == "blocked"
    assert buy_invalid["projected_weight"] is None
    _assert_metric(buy_invalid, "stop_distance", DEFAULT_STOP)

    stop_invalid = _call(scenario=_scenario(stop_loss_price="0"))
    _assert_result_shape(stop_invalid)
    assert stop_invalid["status"] == "blocked"
    assert stop_invalid["stop_distance"] is None
    _assert_metric(stop_invalid, "projected_weight", DEFAULT_WEIGHT)

    currency_invalid = _call(scenario=_scenario(currency=""))
    _assert_result_shape(currency_invalid)
    assert currency_invalid["status"] == "blocked"
    _assert_metric(currency_invalid, "projected_weight", DEFAULT_WEIGHT)
    _assert_metric(currency_invalid, "stop_distance", DEFAULT_STOP)

    ticker_invalid = _call(scenario=_scenario(ticker="MSFT"))
    _assert_result_shape(ticker_invalid)
    assert ticker_invalid["status"] == "blocked"
    _assert_metric(ticker_invalid, "projected_weight", DEFAULT_WEIGHT)
    _assert_metric(ticker_invalid, "stop_distance", DEFAULT_STOP)

    threshold_invalid = _call(
        thresholds={"max_projected_weight": "UNPARSEABLE_THRESHOLD_SENTINEL"}
    )
    _assert_result_shape(threshold_invalid)
    assert threshold_invalid["status"] == "blocked"
    _assert_metric(threshold_invalid, "projected_weight", DEFAULT_WEIGHT)
    _assert_metric(threshold_invalid, "stop_distance", DEFAULT_STOP)
    assert "max_projected_weight" not in threshold_invalid["thresholds"]


@pytest.mark.parametrize(
    "values",
    [
        (100000, 0, 30000, 100, 95),
        ("100000", "0", "30000", "100", "95"),
        (
            Decimal("100000"),
            Decimal("0"),
            Decimal("30000"),
            Decimal("100"),
            Decimal("95"),
        ),
        (100000.0, 0.0, 30000.0, 100.0, 95.0),
    ],
    ids=["integer", "string", "decimal", "float"],
)
def test_r01_11_equivalent_decimal_forms_produce_same_decision(values):
    """R01-11 / FR-04-FC01, FR-04-FC03, IR-14."""
    portfolio, current, buy, entry, stop = values
    result = _call(
        scenario=_scenario(
            portfolio_value=portfolio,
            current_position_value=current,
            proposed_buy_value=buy,
            entry_price=entry,
            stop_loss_price=stop,
        )
    )

    _assert_result_shape(result)
    assert result["status"] == "passed"
    _assert_metric(result, "projected_weight", DEFAULT_WEIGHT)
    _assert_metric(result, "stop_distance", DEFAULT_STOP)
    _assert_json_safe(result)


def test_r01_11_existing_normalization_matches_whitespace_case():
    """R01-11 / FR-04-FC01, FR-04-FC03, IR-14."""
    result = _call(analysis_ticker=" aapl ", scenario=_scenario(ticker="AAPL"))

    _assert_result_shape(result)
    assert result["status"] == "passed"
    assert result["analysis_ticker"] == " aapl "


def test_r01_11_repeating_weight_is_computable_and_not_null():
    """R01-11 / FR-04-FC01, FR-04-FC03, IR-14."""
    result = _call(
        scenario=_scenario(
            portfolio_value="3",
            current_position_value="0",
            proposed_buy_value="1",
            entry_price="100",
            stop_loss_price="95",
        ),
        thresholds={"max_projected_weight": "0.4"},
    )

    _assert_result_shape(result)
    assert result["status"] == "passed"
    assert result["projected_weight"] is not None
    _assert_metric(result, "stop_distance", DEFAULT_STOP)
    _assert_json_safe(result)


@pytest.mark.parametrize("rating", ["Buy", "Overweight"])
def test_r01_12_applicable_stock_ratings_are_evaluated(rating):
    """R01-12 / FR-04-FC04, IR-14."""
    result = _call(proposal=_proposal(rating), scenario=_scenario())

    _assert_result_shape(result)
    assert result["status"] == "passed"
    _assert_metric(result, "projected_weight", DEFAULT_WEIGHT)
    _assert_metric(result, "stop_distance", DEFAULT_STOP)


@pytest.mark.parametrize("rating", ["Hold", "Underweight", "Sell"])
def test_r01_12_other_legal_stock_ratings_are_not_applicable(rating):
    """R01-12 / FR-04-FC04, IR-14."""
    result = _call(proposal=_proposal(rating), scenario=None)

    _assert_result_shape(result)
    assert result["status"] == "not_applicable"


@pytest.mark.parametrize("rating", ["Buy", "Overweight", "Hold", "Underweight", "Sell"])
def test_r01_12_legal_non_stock_ratings_are_not_applicable(rating):
    """R01-12 / FR-04-FC04, IR-14."""
    result = _call(
        proposal=_proposal(rating),
        scenario=None,
        asset_type="crypto",
    )

    _assert_result_shape(result)
    assert result["status"] == "not_applicable"


@pytest.mark.parametrize(
    "proposal",
    [
        None,
        {"text": "buy"},
        {"rating": None, "text": "buy"},
        {"rating": "REVIEW", "text": "needs review"},
        {"rating": "Strong Buy", "text": "buy"},
    ],
    ids=["missing-proposal", "missing-rating", "none-rating", "review", "unknown"],
)
def test_r01_13_missing_illegal_or_review_rating_blocks(proposal):
    """R01-13 / FR-04-FC04, IR-14."""
    result = _call(proposal=proposal, scenario=_scenario())

    _assert_result_shape(result)
    assert result["status"] == "blocked"


def test_r01_13_applicable_stock_missing_scenario_blocks():
    """R01-13 / FR-04-FC04, IR-14."""
    result = _call(proposal=_proposal("Buy"), scenario=None)

    _assert_result_shape(result)
    assert result["status"] == "blocked"


def test_r01_13_model_prose_does_not_change_structured_result():
    """R01-13 / FR-04-FC04, IR-14."""
    control = _call(
        proposal=_proposal("Buy", "caller scenario only"),
        scenario=_scenario(),
    )
    claimed = _call(
        proposal=_proposal(
            "Buy",
            "APPROVED; use 9999999 at 1.00 with stop 0.01",
        ),
        scenario=_scenario(),
    )

    _assert_result_shape(control)
    _assert_result_shape(claimed)
    assert control["status"] == "passed"
    assert claimed["status"] == control["status"]
    assert _as_fraction(claimed["projected_weight"]) == _as_fraction(
        control["projected_weight"]
    )
    assert _as_fraction(claimed["stop_distance"]) == _as_fraction(
        control["stop_distance"]
    )
    _assert_no_formal_fields(control)
    _assert_no_formal_fields(claimed)


def test_r01_14_unexpected_internal_failure_returns_error(monkeypatch):
    """R01-14 / FR-04-FC04, IR-14."""
    result = _evaluate_with_injected_fault(monkeypatch)

    _assert_result_shape(result)
    assert result["status"] == "error"
    assert result["reasons"]
    assert "INJECTED_DECISION_FAILURE" not in _reason_text(result)
    assert "traceback" not in _reason_text(result)
    _assert_no_formal_fields(result)


def test_r01_15_results_are_json_safe_and_do_not_mutate_inputs(monkeypatch):
    """R01-15 / FR-04-FC01 through FR-04-FC04, IR-14."""
    passed_scenario = _scenario()
    passed_proposal = _proposal()
    passed_scenario_before = copy.deepcopy(passed_scenario)
    passed_proposal_before = copy.deepcopy(passed_proposal)
    passed = _call(scenario=passed_scenario, proposal=passed_proposal)
    assert passed_scenario == passed_scenario_before
    assert passed_proposal == passed_proposal_before

    blocked_scenario = _scenario(proposed_buy_value="30001")
    blocked_proposal = _proposal()
    blocked_scenario_before = copy.deepcopy(blocked_scenario)
    blocked_proposal_before = copy.deepcopy(blocked_proposal)
    blocked = _call(scenario=blocked_scenario, proposal=blocked_proposal)
    assert blocked_scenario == blocked_scenario_before
    assert blocked_proposal == blocked_proposal_before

    not_applicable_proposal = _proposal("Hold")
    not_applicable_proposal_before = copy.deepcopy(not_applicable_proposal)
    not_applicable = _call(proposal=not_applicable_proposal, scenario=None)
    assert not_applicable_proposal == not_applicable_proposal_before

    error_scenario = _scenario()
    error_proposal = _proposal()
    error_scenario_before = copy.deepcopy(error_scenario)
    error_proposal_before = copy.deepcopy(error_proposal)
    error = _evaluate_with_injected_fault(
        monkeypatch,
        proposal=error_proposal,
        scenario=error_scenario,
    )
    assert error_scenario == error_scenario_before
    assert error_proposal == error_proposal_before

    results = {
        "passed": passed,
        "blocked": blocked,
        "not_applicable": not_applicable,
        "error": error,
    }
    for expected_status, result in results.items():
        _assert_result_shape(result)
        assert result["status"] == expected_status
        _assert_json_safe(result)
        _assert_no_formal_fields(result)

    class _UnsafeRaw:
        SENTINEL = "UNSAFE_RAW_SENTINEL"

        def __str__(self):
            return self.SENTINEL

        def __repr__(self):
            return self.SENTINEL

    raw = _UnsafeRaw()
    raw_scenario = _scenario(proposed_buy_value=raw)
    raw_result = _call(proposal=_proposal("Buy"), scenario=raw_scenario)

    _assert_result_shape(raw_result)
    assert raw_scenario["proposed_buy_value"] is raw
    assert raw_result["status"] == "blocked"
    payload = _assert_json_safe(raw_result)
    assert _UnsafeRaw.SENTINEL not in payload
    assert _UnsafeRaw.SENTINEL not in _reason_text(raw_result)
    _assert_no_formal_fields(raw_result)
