# FR-04 Runtime Policy Fragment

## POL-FR04-01 — Limits and applicability

- Status: pending human decision.
- Proposed scope: unleveraged new-long stock Buy/Overweight only.
- Provisional maximum projected weight: 30%.
- Provisional maximum long stop distance: 5%.
- Exact boundary passes; a representable value above it blocks.
- Policy is versioned and cannot be changed by model text.
- The projected-weight denominator is unchanged only for a purchase funded from
  cash already included in `portfolio_value`; external funding requires a
  separately approved denominator rule.

## POL-FR04-02 — Fail-closed validation

Required typed values: portfolio value, current asset value, proposed order
value, entry price, stop price, trade type, policy version, provenance, and
timestamp/freshness metadata.

Missing, boolean, negative, NaN, infinite, zero-denominator, inconsistent,
stale/unprovenanced, or unsupported values do not default to approval.

Authoritative values remain typed through finalization. Rendered Markdown and
model prose are display-only and are never parsed to recover numeric inputs.

## POL-FR04-03 — Proposed results

| Trigger | Proposed effective response | Code |
|---|---|---|
| Hold, Underweight, or Sell with no positive new-long order | Preserve valid model rating; evaluator is not applicable | NOT_APPLICABLE |
| Applicable and within both limits | Preserve valid model rating | None |
| Projected weight above limit | REVIEW; zero effective value | POSITION_LIMIT_EXCEEDED |
| Stop distance above limit | REVIEW; zero effective value | STOP_DISTANCE_EXCEEDED |
| Missing required input | REVIEW; zero effective value | MISSING_REQUIRED_INPUT |
| Invalid numeric input | REVIEW; zero effective value | INVALID_NUMERIC_INPUT |
| Inconsistent portfolio context | REVIEW; zero effective value | INCONSISTENT_PORTFOLIO_CONTEXT |
| Invalid new-long stop | REVIEW; zero effective value | INVALID_LONG_STOP |
| Unsupported trade type | REVIEW; zero effective value | UNSUPPORTED_TRADE_TYPE |
| Internal evaluator error | REVIEW; zero effective value; surface error | PORTFOLIO_RISK_INTERNAL_ERROR |

Violation codes accumulate where safe. Narrative cannot suppress a code. Final
state vocabulary remains pending team approval.
