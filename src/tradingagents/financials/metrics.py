"""FR-10 fiscal selection and exact arithmetic (ADR 002 D-202; IR-01/IR-14)."""

from dataclasses import asdict
from decimal import Decimal, localcontext
from fractions import Fraction

from tradingagents.financials.models import (
    METRIC_IDS,
    EvaluationClock,
    FinancialInputs,
    MetricBundle,
    MetricResult,
    digest,
)


class _Unavailable(ValueError):
    def __init__(self, reason, known=(), missing=()):
        self.reason, self.known, self.missing = reason, tuple(known), tuple(missing)


def _period(fact):
    if fact is None:
        return ()
    return tuple((key, str(value) if key in ("period_start", "period_end") and value is not None else value)
                 for key, value in (("period_start", fact.period_start), ("period_end", fact.period_end),
                                    ("fiscal_year", fact.fiscal_year), ("fiscal_quarter", fact.fiscal_quarter), ("span", fact.span)))


class _Facts:
    def __init__(self, inputs, clock):
        self.facts, self.issues = [], list(inputs.issues)
        for fact in inputs.facts:
            if fact.subject_id != inputs.subject_id:
                self.issues.append(f"subject_mismatch:{fact.fact_id}")
                continue
            if fact.filed_at > clock.as_of:
                self.issues.append(f"future_filing_excluded:{fact.fact_id}")
                continue
            # Historical runs obey their analysis-date cutoff too, not only
            # runs whose as-of date happens to equal the machine's today.
            if fact.filed_at == clock.as_of and (
                fact.public_at is None or fact.public_at.tzinfo is None or fact.public_at > clock.cutoff
            ):
                self.issues.append(f"availability_unknown:{fact.fact_id}")
                continue
            if fact.period_end > clock.as_of:
                self.issues.append(f"future_period_excluded:{fact.fact_id}")
                continue
            self.facts.append(fact)

    def position(self, metric, annual=False):
        spans = ("annual",) if annual else ("quarter", "ytd")
        records = [f for f in self.facts if f.metric == metric and f.span in spans]
        if not records:
            raise _Unavailable("missing_input" if annual else "missing_quarter", missing=(metric,))
        if any(type(f.fiscal_year) is not int or (not annual and f.fiscal_quarter not in (1, 2, 3, 4)) for f in records):
            raise _Unavailable("ambiguous_period", records)
        return max((f.fiscal_year, 0 if annual else f.fiscal_quarter) for f in records)

    def choose(self, metric, *, position=None, span=None, end=None, exact=None, missing="missing_input"):
        records = [f for f in self.facts if f.metric == metric
                   and (position is None or (f.fiscal_year, 0 if span == "annual" else f.fiscal_quarter) == position)
                   and (span is None or f.span == span) and (end is None or f.period_end == end)]
        if exact is not None:
            records = [f for f in records if (f.period_start, f.period_end, f.span, f.fiscal_year, f.fiscal_quarter) ==
                       (exact.period_start, exact.period_end, exact.span, exact.fiscal_year, exact.fiscal_quarter)]
        if not records:
            raise _Unavailable(missing, missing=(metric,))
        identities = {(f.period_start, f.period_end, f.fiscal_year, f.fiscal_quarter, f.span) for f in records}
        if len(identities) != 1:
            raise _Unavailable("ambiguous_period", records)
        if any(not f.accession or not f.filing_ref or not f.source_ref for f in records):
            raise _Unavailable("missing_filing_reference", records)
        if any(not f.calendar_id or not f.calendar_evidence for f in records):
            raise _Unavailable("incomparable_period", records)
        for f in records:
            if f.span == "instant":
                if f.period_start is not None:
                    raise _Unavailable("ambiguous_period", records)
            elif f.period_start is None or f.period_start > f.period_end:
                raise _Unavailable("ambiguous_period", records)
        # Declared SEC concept aliases have a documented preference, never sum.
        priority = min(f.concept_rank for f in records)
        records = [f for f in records if f.concept_rank == priority]
        if len({(f.unit, f.currency) for f in records}) > 1:
            raise _Unavailable("currency_mismatch" if len({f.currency for f in records}) > 1 else "unit_mismatch", records)
        by_id = {}
        for f in records:
            if f.fact_id in by_id and f != by_id[f.fact_id]:
                raise _Unavailable("ambiguous_filing", records)
            by_id[f.fact_id] = f
        if len(by_id) == 1:
            return next(iter(by_id.values()))

        def descends(candidate, ancestor, visited):
            if candidate.fact_id in visited or not candidate.lineage_evidence:
                return False
            return any(key == ancestor.fact_id or (key in by_id and descends(by_id[key], ancestor, visited | {candidate.fact_id}))
                       for key in candidate.supersedes)

        winners = [f for f in by_id.values() if all(
            f == other or (f.filed_at >= other.filed_at and descends(f, other, set())) for other in by_id.values()
        )]
        if len(winners) != 1:
            raise _Unavailable("ambiguous_filing", records)
        return winners[0]


def _compatible(a, b, *, same_period=False):
    if a.subject_id != b.subject_id:
        raise _Unavailable("subject_mismatch", (a, b))
    if a.currency != b.currency:
        raise _Unavailable("currency_mismatch", (a, b))
    if a.unit != b.unit or a.unit != a.currency:
        raise _Unavailable("unit_mismatch", (a, b))
    if a.calendar_id != b.calendar_id:
        raise _Unavailable("incomparable_period", (a, b))
    if same_period and (a.period_start, a.period_end, a.span) != (b.period_start, b.period_end, b.span):
        raise _Unavailable("fiscal_period_mismatch", (a, b))


def _number(fraction, kind):
    # Exact rational half-up for the display; Decimal for the machine value.
    scaled = abs(fraction) * (1 if kind == "fcf" else 10)
    integer, remainder = divmod(scaled.numerator, scaled.denominator)
    integer += int(2 * remainder >= scaled.denominator)
    if fraction < 0:
        integer = -integer
    display = str(integer) if kind == "fcf" else f"{'-' if integer < 0 else ''}{abs(integer)//10}.{abs(integer)%10}"
    with localcontext() as context:
        context.prec = max(60, len(str(abs(fraction.numerator))) + len(str(fraction.denominator)) + 10)
        value = Decimal(fraction.numerator) / Decimal(fraction.denominator)
    return value, display


def calculate_metrics(inputs: FinancialInputs, clock: EvaluationClock) -> MetricBundle:
    """No I/O, model, report parsing, date-proximity match or quarter subtraction."""
    pool = _Facts(inputs, clock)
    rows = []
    for metric in METRIC_IDS:
        known, anchor, extra_sources = [], None, ()
        unit, kind = ("USD", "fcf") if metric == "fcf_reported_span" else ("x", "ratio") if metric in ("current_ratio", "pe_fy") else ("%", "percent")
        try:
            if metric in ("revenue_yoy_q", "revenue_qoq", "revenue_yoy_a", "gross_margin", "operating_margin", "net_margin"):
                annual = metric == "revenue_yoy_a"
                position = pool.position("revenue", annual)
                a = pool.choose("revenue", position=position, span="annual" if annual else "quarter", missing="missing_input" if annual else "missing_quarter")
                anchor, known = a, [a]
                year, quarter = position
                if metric in ("revenue_yoy_a", "revenue_yoy_q", "revenue_qoq"):
                    if metric == "revenue_qoq":
                        compare = (year, quarter - 1) if quarter > 1 else (year - 1, 4)
                    else:
                        compare = (year - 1, quarter)
                    b = pool.choose("revenue", position=compare, span="annual" if annual else "quarter", missing="missing_quarter" if metric == "revenue_qoq" else "missing_comparison")
                    known.append(b)
                    _compatible(a, b)
                    if b.value <= 0:
                        raise _Unavailable("non_positive_base", known)
                    if a.value < 0:
                        raise _Unavailable("invalid_input_domain", known)
                    fraction = (Fraction(a.value) / Fraction(b.value) - 1) * 100
                else:
                    b = pool.choose({"gross_margin": "gross_profit", "operating_margin": "operating_income", "net_margin": "net_income"}[metric], exact=a)
                    # Deterministic public order: numerator (profit line) then
                    # denominator (revenue), matching the independent reference.
                    known = [b, a]
                    _compatible(a, b, same_period=True)
                    if a.value == 0:
                        raise _Unavailable("zero_denominator", known)
                    if a.value < 0:
                        raise _Unavailable("invalid_input_domain", known)
                    fraction = Fraction(b.value) / Fraction(a.value) * 100
            elif metric in ("current_ratio", "liabilities_to_assets"):
                balances = [f for f in pool.facts if f.span == "instant" and f.metric in ("current_assets", "current_liabilities", "assets", "liabilities")]
                if not balances:
                    raise _Unavailable("missing_input", missing=("balance_sheet",))
                end = max(f.period_end for f in balances)
                left, right = ("current_assets", "current_liabilities") if metric == "current_ratio" else ("liabilities", "assets")
                a = pool.choose(left, span="instant", end=end)
                anchor, known = a, [a]
                b = pool.choose(right, span="instant", end=end)
                known.append(b)
                _compatible(a, b, same_period=True)
                if a.value < 0 or b.value < 0 or (right == "assets" and b.value == 0):
                    raise _Unavailable("invalid_input_domain", known)
                if b.value == 0:
                    raise _Unavailable("zero_denominator", known)
                fraction = Fraction(a.value) / Fraction(b.value) * (100 if metric == "liabilities_to_assets" else 1)
            elif metric == "fcf_reported_span":
                cfo = [f for f in pool.facts if f.metric == "cfo" and f.span in ("quarter", "ytd", "annual")]
                if not cfo:
                    raise _Unavailable("missing_input", missing=("cfo",))
                if any(type(f.fiscal_year) is not int for f in cfo):
                    raise _Unavailable("ambiguous_period", cfo)
                latest = max((f.fiscal_year, f.fiscal_quarter or 4) for f in cfo)
                current = [f for f in cfo if (f.fiscal_year, f.fiscal_quarter or 4) == latest]
                if len({(f.period_start, f.period_end, f.span) for f in current}) != 1:
                    raise _Unavailable("ambiguous_period", current)
                a = pool.choose("cfo", exact=current[0])
                anchor, known = a, [a]
                b = pool.choose("capex", exact=a)
                known.append(b)
                _compatible(a, b, same_period=True)
                if b.sign_rule == "positive_outflow" and b.value >= 0:
                    capex = b.value
                elif b.sign_rule == "negative_outflow" and b.value <= 0:
                    capex = b.value.copy_negate()  # exact sign change, independent of Decimal context
                else:
                    raise _Unavailable("unknown_capex_sign" if b.sign_rule == "unknown" else "capex_sign_mismatch", known)
                # Source statements report USD millions; the exact displayed
                # difference keeps that scale. Division by 10**6 is exact here.
                unit = f"{a.currency}_millions"
                fraction = (Fraction(a.value) - Fraction(capex)) / 1_000_000
            else:
                position = pool.position("diluted_eps", annual=True)
                a = pool.choose("diluted_eps", position=position, span="annual")
                anchor, known = a, [a]
                price = inputs.price
                if price is None:
                    # Preserve the price adapter's explicit reason, without
                    # deriving availability from model prose or other fields.
                    reason = next((issue for issue in inputs.issues if issue in {
                        "stale_price", "price_availability_unknown", "price_currency_unconfirmed",
                    }), "missing_price")
                    raise _Unavailable(reason, known, ("completed_close",))
                extra_sources = (price.source_ref,)
                if price.price_date > clock.as_of:
                    raise _Unavailable("future_price_excluded", known)
                if price.completed_at is None or price.completed_at.tzinfo is None or not price.completion_evidence:
                    raise _Unavailable("price_availability_unknown", known)
                if price.completed_at > clock.cutoff:
                    raise _Unavailable("price_not_completed", known)
                if price.expected_latest_session is None or not price.freshness_policy or not price.source_ref:
                    raise _Unavailable("price_availability_unknown", known)
                if price.price_date != price.expected_latest_session:
                    raise _Unavailable("stale_price", known)
                if a.currency != price.currency:
                    raise _Unavailable("currency_mismatch", known)
                if a.unit != f"{a.currency}/shares" or price.unit != a.unit:
                    raise _Unavailable("unit_mismatch", known)
                if not a.share_basis or a.share_basis != price.share_basis or not a.basis_evidence or not price.basis_evidence:
                    raise _Unavailable("basis_mismatch", known)
                if a.value <= 0:
                    raise _Unavailable("non_positive_eps", known)
                if price.value <= 0:
                    raise _Unavailable("invalid_input_domain", known)
                fraction = Fraction(price.value) / Fraction(a.value)
            value, display = _number(fraction, kind)
            rows.append(MetricResult(metric, "computed", value, display, None, unit, _period(anchor),
                                     tuple(f.fact_id for f in known), tuple(dict.fromkeys([f.filing_ref for f in known] + list(extra_sources))),
                                     formula_id=metric, exact_fraction=str(fraction)))
        except _Unavailable as exc:
            combined = tuple(dict.fromkeys([*known, *exc.known]))
            rows.append(MetricResult(metric, "n/a", None, "n/a", exc.reason, unit, _period(anchor or (combined[0] if combined else None)),
                                     tuple(f.fact_id for f in combined), tuple(dict.fromkeys([f.filing_ref for f in combined] + list(extra_sources))),
                                     exc.missing, formula_id=metric))
    input_digest = digest({"inputs": asdict(inputs), "clock": asdict(clock)})
    return MetricBundle(inputs.subject_id, clock.as_of.isoformat(), tuple(rows), inputs.facts, inputs.price,
                        tuple(pool.issues), input_digest, digest([asdict(row) for row in rows]))


def unavailable_bundle(subject, as_of, reason):
    rows = tuple(MetricResult(metric, "n/a", None, "n/a", reason, "", formula_id=metric,
                              missing_input_roles=("structured_financial_input",)) for metric in METRIC_IDS)
    return MetricBundle(subject, as_of, rows, issues=(reason,), result_digest=digest([asdict(row) for row in rows]))


def render_metrics(bundle: MetricBundle) -> str:
    """One renderer for analyst prompts and later caller-owned FR-08 metric_block."""
    sources = tuple(dict.fromkeys(source for row in bundle.rows for source in row.sources))
    labels = {source: f"S{index}" for index, source in enumerate(sources, 1)}
    lines = [f"Program financial metrics ({bundle.formula_version}); as_of={bundle.as_of}; issuer={bundle.subject_id}",
             "| metric_id | value / reason | period / span | sources |", "|---|---|---|---|"]
    for row in bundle.rows:
        period = dict(row.period)
        start, end = period.get("period_start"), period.get("period_end") or "n/a"
        where = f"{start + '..' if start else 'at '}{end} / {period.get('span') or 'n/a'}"
        result = f"{row.display} {row.unit}" if row.status == "computed" else f"n/a: {row.reason}"
        lines.append(f"| {row.metric_id} | {result} | {where} | {','.join(labels[s] for s in row.sources) or 'n/a'} |")
    lines.extend(f"[{labels[source]}] {source.replace(chr(92), '/')}" for source in sources)
    lines.append("Percentages: 0.1 percentage point; ratios: 0.1x; half-up. FCF is exact source-currency amount, not a derived quarter.")
    lines.extend(bundle.limitations)
    return "\n".join(lines)
