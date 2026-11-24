"""Deterministic SB-01 final recommendation check.

Architecture: ADR 001 D-01/D-02; IR-01 and IR-02; IF-09; SB-01-FC01 through
SB-01-FC04. C-09 is a pure consumer of the caller-provided proposal,
availability summary, risk result, and asset type. It decides and generates the
formal result and never calls a model, data source, risk evaluator, graph,
storage, or manifest path.
"""

from __future__ import annotations

from collections.abc import Mapping

__all__ = ["evaluate"]

_LEGAL_RATINGS = frozenset({"Buy", "Overweight", "Hold", "Underweight", "Sell"})
_APPLICABLE_STOCK_RATINGS = frozenset({"Buy", "Overweight"})
_LEGAL_ASSET_TYPES = frozenset({"stock", "crypto"})
_LEGAL_COMPLETENESS = frozenset({"complete", "incomplete", "not_applicable"})
_LEGAL_NECESSITY_STATUSES = frozenset(
    {"available", "no_data", "unavailable", "withheld", "not_attempted"}
)
_REVIEW = "REVIEW"


def validate_formal_result(state):
    """Validate IF-19 before a consumer returns, displays or persists the decision."""
    required = {"model_proposal", "gate_status", "final_rating", "final_trade_decision", "reasons"}
    if not isinstance(state, Mapping) or not required.issubset(state):
        raise ValueError("Incomplete formal recommendation")
    proposal = state["model_proposal"]
    if proposal is not None and (
        not isinstance(proposal, Mapping) or not {"rating", "text"}.issubset(proposal)
        or any(proposal[k] is not None and not isinstance(proposal[k], str) for k in ("rating", "text"))
    ):
        raise ValueError("Invalid formal recommendation proposal")
    gate, rating = state["gate_status"], state["final_rating"]
    if gate not in ("passed", "blocked", "error") or not isinstance(rating, str):
        raise ValueError("Invalid formal gate or rating")
    if (gate == "passed" and rating not in _LEGAL_RATINGS) or (gate != "passed" and rating != _REVIEW):
        raise ValueError("Formal rating conflicts with gate status")
    if not isinstance(state["final_trade_decision"], str) or not state["final_trade_decision"].strip():
        raise ValueError("Empty formal decision")
    reasons = state["reasons"]
    if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
        raise ValueError("Invalid formal reasons")
    if gate != "passed" and not any(reason.strip() for reason in reasons):
        raise ValueError("Missing formal review reason")


def _dedupe(reasons):
    """Return a new list with duplicate reason strings removed, order preserved."""
    seen = set()
    result = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            result.append(reason)
    return result


def _project_proposal(proposal):
    """Project only rating/text, using None for missing or non-string fields."""
    if not isinstance(proposal, Mapping):
        return None
    rating = proposal.get("rating")
    text = proposal.get("text")
    return {
        "rating": rating if isinstance(rating, str) else None,
        "text": text if isinstance(text, str) else None,
    }


def _proposal_conditions(proposal, model_proposal):
    """Validate the original proposal fields without parsing its text."""
    if not isinstance(proposal, Mapping):
        return None, None, ["model proposal is missing or is not a mapping"]

    reasons = []
    rating = model_proposal["rating"]
    text = model_proposal["text"]

    if not isinstance(rating, str):
        reasons.append("model rating is missing or is not a legal five-tier rating")
        valid_rating = None
    elif rating not in _LEGAL_RATINGS:
        if rating == _REVIEW:
            reasons.append("model rating REVIEW is not a legal tradeable rating")
        else:
            reasons.append("model rating is not one of the legal five-tier ratings")
        valid_rating = None
    else:
        valid_rating = rating

    if not isinstance(text, str):
        reasons.append("model conclusion is missing or is not a string")
        valid_text = None
    elif not text.strip():
        reasons.append("model conclusion is empty or whitespace-only")
        valid_text = None
    else:
        valid_text = text

    return valid_rating, valid_text, reasons


def _asset_conditions(asset_type):
    """Accept exactly stock or crypto; no aliasing, trimming, or case folding."""
    if isinstance(asset_type, str) and asset_type in _LEGAL_ASSET_TYPES:
        return True, []
    return False, ["asset type is missing or is not exactly stock or crypto"]


def _safe_item_label(item):
    """Use a supplied safe label/method/id, never an arbitrary object's text."""
    for key in ("label", "method", "id"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return "necessary item"


def _availability_conditions(availability):
    """Validate only the consumed availability fields and derive data reasons.

    Returns ``(blocking_reasons, notes)``. Notes are non-blocking explanations
    worth retaining, such as a legal not_applicable applicability note.
    """
    if not isinstance(availability, Mapping):
        return ["data availability summary is missing or is not a mapping"], []

    reasons = []
    completeness = availability.get("basic_completeness")
    if not isinstance(completeness, str) or completeness not in _LEGAL_COMPLETENESS:
        reasons.append(
            "data availability basic completeness is missing or illegal"
        )

    note = availability.get("applicability_note")
    if not isinstance(note, str):
        reasons.append(
            "data availability applicability note is missing or invalid"
        )

    items = availability.get("necessary_items")
    if not isinstance(items, list):
        reasons.append("data necessary items are missing or are not a list")
        items = []

    validated_items = []
    for item in items:
        if not isinstance(item, Mapping):
            reasons.append("data necessary item is malformed")
            continue
        status = item.get("status")
        reason = item.get("reason")
        if not isinstance(status, str) or status not in _LEGAL_NECESSITY_STATUSES:
            reasons.append("data necessary item status is missing or illegal")
            continue
        if not isinstance(reason, str):
            reasons.append("data necessary item reason is missing or invalid")
            continue
        validated_items.append((item, status, reason))

    if reasons:
        # A damaged summary does not also supply a trusted applicability note.
        return _dedupe(reasons), []

    if completeness == "not_applicable":
        notes = [note] if isinstance(note, str) and note.strip() else []
        return [], notes

    non_available = [
        (item, status, reason)
        for item, status, reason in validated_items
        if status != "available"
    ]

    if completeness == "complete":
        for item, status, reason in non_available:
            label = _safe_item_label(item)
            detail = (
                f"data is marked complete but necessary item {label} "
                f"has status {status}"
            )
            if reason.strip():
                detail += f" ({reason.strip()})"
            reasons.append(detail)
        return _dedupe(reasons), []

    if not non_available:
        reasons.append(
            "data is marked incomplete but no non-available necessary item is identified"
        )
        return _dedupe(reasons), []

    for item, status, reason in non_available:
        label = _safe_item_label(item)
        if not reason.strip():
            reasons.append(
                f"data is incomplete but necessary item {label} has no usable reason"
            )
        else:
            reasons.append(
                f"necessary data is missing for {label} "
                f"(status {status}): {reason.strip()}"
            )
    return _dedupe(reasons), []


def _risk_conditions(risk, rating, asset_type, asset_valid):
    """Check only the applicable risk outcome; never inspect metrics or reasons."""
    if not asset_valid:
        return []
    if asset_type != "stock" or rating not in _APPLICABLE_STOCK_RATINGS:
        return []
    if not isinstance(risk, Mapping):
        return ["risk result is missing or is not a mapping"]
    status = risk.get("status")
    if not isinstance(status, str):
        return ["risk check status is missing or invalid"]
    if status != "passed":
        return [f"risk check did not pass: {status}"]
    return []


def _manual_review_notice(reasons):
    """Build a program-generated notice from safe, already-validated reasons."""
    parts = []
    for reason in reasons:
        part = reason.strip().rstrip(".")
        if part:
            parts.append(part)
    detail = "; ".join(parts) or "the final recommendation check did not pass"
    return f"Manual review required: {detail}."


def _blocked_result(model_proposal, reasons):
    safe_reasons = _dedupe(reasons) or [
        "final recommendation check did not pass"
    ]
    return {
        "model_proposal": model_proposal,
        "gate_status": "blocked",
        "reasons": safe_reasons,
        "final_rating": _REVIEW,
        "final_trade_decision": _manual_review_notice(safe_reasons),
    }


def _error_result(model_proposal):
    reasons = ["final recommendation check could not complete safely"]
    return {
        "model_proposal": model_proposal,
        "gate_status": "error",
        "reasons": reasons,
        "final_rating": _REVIEW,
        "final_trade_decision": _manual_review_notice(reasons),
    }


def _passed_result(model_proposal, rating, text, notes):
    return {
        "model_proposal": model_proposal,
        "gate_status": "passed",
        "reasons": list(notes),
        "final_rating": rating,
        "final_trade_decision": text,
    }


def _evaluate_impl(
    model_proposal,
    proposal_rating,
    proposal_text,
    proposal_reasons,
    asset_reasons,
    data_reasons,
    data_notes,
    risk_reasons,
):
    """Assemble the single formal result from already-validated conditions.

    This private boundary runs only after ordinary input projection and
    validation in ``evaluate``. It performs no input parsing or external calls.
    """
    blocking = _dedupe(
        [*proposal_reasons, *asset_reasons, *data_reasons, *risk_reasons]
    )
    notes = list(data_notes)
    if blocking:
        return _blocked_result(model_proposal, [*blocking, *notes])
    return _passed_result(model_proposal, proposal_rating, proposal_text, notes)


def evaluate(proposal, availability, risk, asset_type):
    """Run the deterministic SB-01 final check over caller-supplied inputs.

    Architecture: ADR 001 D-01/D-02; IR-01 and IR-02; IF-09; SB-01-FC01 through
    SB-01-FC04. The check is pure and adds no model, data, storage, or risk
    recomputation. Ordinary input or condition failures are blocked; only an
    unexpected exception inside this module becomes error.
    """
    model_proposal = None
    try:
        model_proposal = _project_proposal(proposal)
        (
            proposal_rating,
            proposal_text,
            proposal_reasons,
        ) = _proposal_conditions(proposal, model_proposal)
        asset_valid, asset_reasons = _asset_conditions(asset_type)
        data_reasons, data_notes = _availability_conditions(availability)
        risk_reasons = _risk_conditions(
            risk,
            proposal_rating,
            asset_type,
            asset_valid,
        )
        return _evaluate_impl(
            model_proposal=model_proposal,
            proposal_rating=proposal_rating,
            proposal_text=proposal_text,
            proposal_reasons=proposal_reasons,
            asset_reasons=asset_reasons,
            data_reasons=data_reasons,
            data_notes=data_notes,
            risk_reasons=risk_reasons,
        )
    except Exception:
        return _error_result(model_proposal)
