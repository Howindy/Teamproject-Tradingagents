# FR-04 Open Decisions

All decisions remain open and require human approval before implementation.

| ID | Decision | Recommendation, not approval | Blocking |
|---|---|---|---|
| FR04-OD-01 | Are 30% and 5% accepted defaults? | Keep as configurable classroom defaults until evidence supports change | Yes |
| FR04-OD-02 | Who owns validated numeric inputs? | Deterministic entry adapter builds typed, timestamped caller RiskContext | Yes |
| FR04-OD-03 | REVIEW, HOLD, or BLOCKED? | Existing REVIEW rating plus separate blocked gate status/codes | Yes |
| FR04-OD-04 | Supported first-version trades? | Unleveraged new-long stock Buy/Overweight only | Yes |
| FR04-OD-05 | Exact finalized-record fields? | Policy version, metrics, limits, status, codes, proposal reference, effective result | Yes |
| FR04-OD-06 | Policy configuration bounds and migration? | Versioned catalog with explicit allowed ranges | Yes |
| FR04-OD-07 | Input freshness and portfolio fingerprint? | Require provenance, timestamp, and deterministic fingerprint | Yes |
| FR04-OD-08 | How does the projected-weight denominator change when an order uses external cash? | First version supports only purchases funded from cash already included in portfolio value; define external-cash accounting separately | Yes |
| FR04-OD-09 | Where do typed proposal and portfolio values live until finalization? | Extend graph/run state so typed values survive; keep Markdown display-only | Yes |

Implementation must not begin until the team closes all blocking decisions and
updates the canonical team D1/D2 accordingly.
