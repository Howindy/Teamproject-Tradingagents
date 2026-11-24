"""Source-preserving FR-10 inputs (ADR 002 D-201/D-202; IR-05)."""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal

FORMULA_VERSION = "fr07-direct-v1"
METRIC_IDS = (
    "revenue_yoy_q", "revenue_yoy_a", "revenue_qoq", "gross_margin", "operating_margin",
    "net_margin", "current_ratio", "liabilities_to_assets", "fcf_reported_span", "pe_fy",
)


def decimal_value(value) -> Decimal:
    """Never accept a binary float as authoritative financial input."""
    if isinstance(value, bool | float):
        raise ValueError("binary_float_or_boolean_input")
    number = value if isinstance(value, Decimal) else Decimal(value)
    if not number.is_finite():
        raise ValueError("non_finite_input")
    return number


def json_value(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [json_value(item) for item in value]
    return value


def digest(value) -> str:
    return hashlib.sha256(json.dumps(json_value(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class EvaluationClock:
    as_of: date
    cutoff: datetime
    today: date

    def __post_init__(self):
        if self.cutoff.tzinfo is None or self.cutoff.utcoffset() is None:
            raise ValueError("cutoff_must_be_timezone_aware")
        if self.cutoff.date() != self.as_of:
            raise ValueError("cutoff_date_must_match_as_of")
        if self.as_of > self.today:
            raise ValueError("future_analysis_date")


@dataclass(frozen=True)
class FinancialFact:
    fact_id: str
    subject_id: str
    metric: str
    value: Decimal
    unit: str
    currency: str
    period_start: date | None
    period_end: date
    fiscal_year: int | None
    fiscal_quarter: int | None
    span: str
    filed_at: date
    accession: str
    filing_ref: str
    concept: str
    source_ref: str
    calendar_id: str = ""
    calendar_evidence: tuple[str, ...] = ()
    sign_rule: str = "unknown"
    share_basis: str = ""
    basis_evidence: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    lineage_evidence: tuple[str, ...] = ()
    public_at: datetime | None = None
    concept_rank: int = 0
    # Original fields are immutable key/value pairs, never rewritten to canonical FY.
    disclosure: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "value", decimal_value(self.value))
        # IF-26 allows source evidence in the original disclosure projection.
        # Preserve its cited statement context rather than invent fiscal labels
        # or require a second copy of evidence already supplied by the provider.
        if not self.calendar_evidence:
            disclosed = dict(self.disclosure)
            required = ("filing_file", "inline_element_id", "inline_context_ref",
                        "fiscal_annotation_method", "selection_rationale")
            matches = all(disclosed.get(key) == str(getattr(self, key)) for key in (
                "period_start", "period_end", "fiscal_year", "fiscal_quarter", "span"))
            if (self.calendar_id and len(disclosed) == len(self.disclosure)
                    and all(disclosed.get(key) for key in required) and matches
                    and self.filing_ref == f"{disclosed['filing_file']}#{disclosed['inline_element_id']}"):
                object.__setattr__(self, "calendar_evidence", (
                    f"{self.filing_ref}; context={disclosed['inline_context_ref']}; "
                    f"{disclosed['fiscal_annotation_method']}; {disclosed['selection_rationale']}",
                ))


@dataclass(frozen=True)
class PriceRecord:
    value: Decimal
    currency: str
    unit: str
    price_date: date
    completed_at: datetime | None
    expected_latest_session: date | None
    freshness_policy: str
    source_ref: str
    share_basis: str
    basis_evidence: tuple[str, ...]
    completion_evidence: str

    def __post_init__(self):
        object.__setattr__(self, "value", decimal_value(self.value))


@dataclass(frozen=True)
class FinancialInputs:
    subject_id: str
    facts: tuple[FinancialFact, ...] = ()
    price: PriceRecord | None = None
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class MetricResult:
    metric_id: str
    status: str
    value: Decimal | None
    display: str
    reason: str | None
    unit: str
    period: tuple[tuple[str, str | int | None], ...] = ()
    input_fact_ids: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    missing_input_roles: tuple[str, ...] = ()
    formula_id: str = ""
    formula_version: str = FORMULA_VERSION
    rounding: str = "ROUND_HALF_UP"
    exact_fraction: str | None = None


@dataclass(frozen=True)
class MetricBundle:
    subject_id: str
    as_of: str
    rows: tuple[MetricResult, ...]
    facts: tuple[FinancialFact, ...] = ()
    price: PriceRecord | None = None
    issues: tuple[str, ...] = ()
    input_digest: str = ""
    result_digest: str = ""
    formula_version: str = FORMULA_VERSION
    limitations: tuple[str, ...] = field(default=(
        "Historical filing visibility is date-level, not an intraday point-in-time guarantee.",
        "Source/calendar/basis evidence comes from the injected data boundary, not model prose.",
        "TTM, FCF YoY and quarter-by-subtraction are not computed.",
    ))

    def to_dict(self) -> dict:
        return json_value(asdict(self))
