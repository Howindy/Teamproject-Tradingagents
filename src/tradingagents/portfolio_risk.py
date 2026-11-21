"""Deterministic FR-04 risk checks for a caller-supplied stock purchase scenario.

Architecture: ADR 001 D-11/D-12/D-12a; IR-14; FR-04-FC01 through FR-04-FC04.

C-08 is a pure evaluator. It parses the caller's structured scenario, compares
exact rational values, and returns one JSON-compatible mapping. It never calls a
model or data source, writes formal recommendation fields, or mutates inputs.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from decimal import Context, Decimal, localcontext
from fractions import Fraction

from tradingagents.dataflows.symbols import normalize_symbol

__all__ = ["evaluate"]

# Mirrors the five-tier vocabulary in tradingagents.agents.rating. It stays
# local so this pure risk module does not import the agent/model package.
_LEGAL_RATINGS = frozenset(
    {"Buy", "Overweight", "Hold", "Underweight", "Sell"}
)
_APPLICABLE_RATINGS = frozenset({"Buy", "Overweight"})

_SCENARIO_NUMERIC_FIELDS = (
    "portfolio_value",
    "current_position_value",
    "proposed_buy_value",
    "entry_price",
    "stop_loss_price",
)

_DEFAULT_MAX_PROJECTED_WEIGHT = Fraction(3, 10)
_DEFAULT_MAX_STOP_DISTANCE = Fraction(1, 20)

_MANUAL_REVIEW_NOTE = "manual review required"
_DEMONSTRATION_NOTE = "classroom demonstration only; a pass is not a trade authorization"
_ERROR_NOTE = "risk evaluator error"
_NOT_APPLICABLE_NOTE = "risk check is not applicable to this asset type or rating"
_INVALID_RATING_NOTE = "proposal rating is missing or illegal"


class _InvalidNumber(ValueError):
    """Internal marker for a value that is not a legal finite decimal number."""


def _to_fraction(value):
    """Convert one accepted numeric form to an exact rational value."""
    if isinstance(value, bool):
        raise _InvalidNumber
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise _InvalidNumber
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _InvalidNumber
        try:
            return Fraction(Decimal(str(value)))
        except (ArithmeticError, ValueError, TypeError) as exc:
            raise _InvalidNumber from exc
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise _InvalidNumber
        try:
            parsed = Decimal(text)
        except (ArithmeticError, ValueError, TypeError) as exc:
            raise _InvalidNumber from exc
        if not parsed.is_finite():
            raise _InvalidNumber
        return Fraction(parsed)
    raise _InvalidNumber


def _terminating_decimal_places(denominator):
    twos = 0
    fives = 0
    remaining = denominator
    while remaining % 2 == 0:
        twos += 1
        remaining //= 2
    while remaining % 5 == 0:
        fives += 1
        remaining //= 5
    if remaining != 1:
        return None
    return max(twos, fives)


def _format_fraction(value):
    """Format an exact rational as a display-safe decimal string."""
    if value == 0:
        return "0"

    sign = "-" if value < 0 else ""
    numerator = abs(value.numerator)
    denominator = value.denominator
    places = _terminating_decimal_places(denominator)

    if places is not None:
        scaled = numerator * (10**places) // denominator
        digits = str(scaled).rjust(places + 1, "0")
        if places == 0:
            return sign + digits
        integer = digits[:-places] or "0"
        fractional = digits[-places:].rstrip("0")
        if not fractional:
            return sign + integer
        return f"{sign}{integer}.{fractional}"

    # A repeating quotient is still computable; its display precision is not a
    # decision input (ADR 001 D-12a). A fresh local context keeps formatting
    # independent of any caller-modified global Decimal context.
    with localcontext(Context(prec=28)):
        decimal_value = Decimal(numerator) / Decimal(denominator)
    return sign + format(decimal_value, "f")


def _analyze_scenario(scenario, analysis_ticker):
    """Return safe display inputs, parsed values, errors, and operand legality."""
    safe: dict[str, str | Fraction] = {}
    values: dict[str, Fraction] = {}
    errors = []

    if not isinstance(scenario, Mapping):
        return safe, values, ["risk scenario is missing or is not a mapping"], False, False

    ticker = scenario.get("ticker")
    if isinstance(ticker, str) and ticker.strip():
        safe["ticker"] = ticker
        if isinstance(analysis_ticker, str) and analysis_ticker.strip():
            if normalize_symbol(ticker) != normalize_symbol(analysis_ticker):
                errors.append("scenario ticker does not match the analysis ticker")
        else:
            errors.append("analysis ticker is missing or invalid")
    else:
        errors.append("scenario ticker is missing or invalid")

    currency = scenario.get("currency")
    if isinstance(currency, str) and currency.strip():
        safe["currency"] = currency
    else:
        errors.append("scenario currency must be a non-empty label")

    for field in _SCENARIO_NUMERIC_FIELDS:
        if field not in scenario:
            errors.append(f"scenario {field} is missing")
            continue
        try:
            value = _to_fraction(scenario[field])
        except _InvalidNumber:
            errors.append(f"scenario {field} must be a finite decimal number")
            continue
        values[field] = value
        safe[field] = value

    portfolio = values.get("portfolio_value")
    current = values.get("current_position_value")
    buy = values.get("proposed_buy_value")
    entry = values.get("entry_price")
    stop = values.get("stop_loss_price")

    portfolio_ok = portfolio is not None and portfolio > 0
    if portfolio is not None and portfolio <= 0:
        errors.append("scenario portfolio_value must be greater than 0")

    current_ok = current is not None and current >= 0
    if current is not None and current < 0:
        errors.append("scenario current_position_value must be at least 0")
    if (
        portfolio_ok
        and current_ok
        and current is not None
        and portfolio is not None
        and current > portfolio
    ):
        errors.append("scenario current_position_value must not exceed portfolio_value")
        current_ok = False

    buy_ok = buy is not None and buy > 0
    if buy is not None and buy <= 0:
        errors.append("scenario proposed_buy_value must be greater than 0")

    entry_ok = entry is not None and entry > 0
    if entry is not None and entry <= 0:
        errors.append("scenario entry_price must be greater than 0")

    stop_ok = stop is not None and stop > 0
    if stop is not None and stop <= 0:
        errors.append(
            "scenario stop_loss_price must be greater than 0 and less than entry_price"
        )
    if entry_ok and entry is not None and stop is not None and stop >= entry:
        errors.append(
            "scenario stop_loss_price must be greater than 0 and less than entry_price"
        )
        stop_ok = False

    weight_legal = portfolio_ok and current_ok and buy_ok
    stop_legal = entry_ok and stop_ok
    return safe, values, errors, weight_legal, stop_legal


def _parse_thresholds(thresholds):
    """Apply the confirmed per-key threshold omission and invalid-value rules."""
    raw: Mapping[str, object]
    if thresholds is None:
        raw = {}
    elif isinstance(thresholds, Mapping):
        raw = thresholds
    else:
        return {}, ["risk thresholds must be a mapping or omitted"]

    used = {}
    errors = []
    for key, default in (
        ("max_projected_weight", _DEFAULT_MAX_PROJECTED_WEIGHT),
        ("max_stop_distance", _DEFAULT_MAX_STOP_DISTANCE),
    ):
        if key not in raw:
            used[key] = default
            continue
        try:
            value = _to_fraction(raw[key])
        except _InvalidNumber:
            errors.append(f"{key} must be a finite decimal threshold")
            continue
        legal = 0 < value <= 1 if key == "max_projected_weight" else 0 < value < 1
        if not legal:
            errors.append(f"{key} is outside the legal threshold range")
            continue
        used[key] = value
    return used, errors


def _breach_reasons(projected_weight, stop_distance, thresholds):
    """Return the exact post-validation threshold breaches, if any."""
    reasons = []
    if projected_weight > thresholds["max_projected_weight"]:
        reasons.append("projected weight exceeds the configured maximum")
    if stop_distance > thresholds["max_stop_distance"]:
        reasons.append("stop distance exceeds the configured maximum")
    return reasons


def _result(
    status,
    analysis_ticker,
    scenario,
    thresholds,
    projected_weight,
    stop_distance,
    reasons,
):
    return {
        "status": status,
        "analysis_ticker": analysis_ticker,
        "scenario": {
            key: value if isinstance(value, str) else _format_fraction(value)
            for key, value in scenario.items()
        },
        "thresholds": {
            key: _format_fraction(value) for key, value in thresholds.items()
        },
        "projected_weight": (
            _format_fraction(projected_weight) if projected_weight is not None else None
        ),
        "stop_distance": (
            _format_fraction(stop_distance) if stop_distance is not None else None
        ),
        "reasons": list(reasons),
    }


def _error_result(analysis_ticker):
    return {
        "status": "error",
        "analysis_ticker": analysis_ticker,
        "scenario": {},
        "thresholds": {},
        "projected_weight": None,
        "stop_distance": None,
        "reasons": [_ERROR_NOTE, _MANUAL_REVIEW_NOTE, _DEMONSTRATION_NOTE],
    }


def _proposal_rating(proposal):
    if not isinstance(proposal, Mapping):
        return None
    rating = proposal.get("rating")
    if isinstance(rating, str) and rating in _LEGAL_RATINGS:
        return rating
    return None


def _evaluate_stock_scenario(analysis_ticker, scenario, thresholds):
    safe_scenario, values, errors, weight_legal, stop_legal = _analyze_scenario(
        scenario, analysis_ticker
    )
    used_thresholds, threshold_errors = _parse_thresholds(thresholds)

    projected_weight = None
    if weight_legal:
        projected_weight = (
            values["current_position_value"] + values["proposed_buy_value"]
        ) / values["portfolio_value"]

    stop_distance = None
    if stop_legal:
        stop_distance = (
            values["entry_price"] - values["stop_loss_price"]
        ) / values["entry_price"]

    if errors or threshold_errors:
        reasons = errors + threshold_errors
        reasons.extend([_MANUAL_REVIEW_NOTE, _DEMONSTRATION_NOTE])
        return _result(
            "blocked",
            analysis_ticker,
            safe_scenario,
            used_thresholds,
            projected_weight,
            stop_distance,
            reasons,
        )

    breach_reasons = _breach_reasons(projected_weight, stop_distance, used_thresholds)
    if breach_reasons:
        breach_reasons.extend([_MANUAL_REVIEW_NOTE, _DEMONSTRATION_NOTE])
        return _result(
            "blocked",
            analysis_ticker,
            safe_scenario,
            used_thresholds,
            projected_weight,
            stop_distance,
            breach_reasons,
        )

    return _result(
        "passed",
        analysis_ticker,
        safe_scenario,
        used_thresholds,
        projected_weight,
        stop_distance,
        [_DEMONSTRATION_NOTE],
    )


def _evaluate_impl(analysis_ticker, proposal, scenario, thresholds, asset_type):
    rating = _proposal_rating(proposal)
    if rating is None:
        return _result(
            "blocked",
            analysis_ticker,
            {},
            {},
            None,
            None,
            [_INVALID_RATING_NOTE, _MANUAL_REVIEW_NOTE, _DEMONSTRATION_NOTE],
        )

    if asset_type != "stock" or rating not in _APPLICABLE_RATINGS:
        return _result(
            "not_applicable",
            analysis_ticker,
            {},
            {},
            None,
            None,
            [_NOT_APPLICABLE_NOTE, _DEMONSTRATION_NOTE],
        )

    return _evaluate_stock_scenario(analysis_ticker, scenario, thresholds)


def evaluate(analysis_ticker, proposal, scenario, thresholds, asset_type):
    """Evaluate a caller-supplied single-stock purchase/add-long scenario.

    Architecture: ADR 001 D-11/D-12/D-12a; IR-14; FR-04-FC01 through FC04.
    """
    safe_ticker = analysis_ticker if isinstance(analysis_ticker, str) else ""
    try:
        return _evaluate_impl(
            safe_ticker,
            proposal,
            scenario,
            thresholds,
            asset_type,
        )
    except Exception:
        return _error_result(safe_ticker)
