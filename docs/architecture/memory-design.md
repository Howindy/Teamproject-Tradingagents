# FR-04 State and Memory Contribution

Status: **personal draft / pending team review**
Implementation status: **design only; no application code changed**

## State ownership

| State | Owner | Lifetime | Authority |
|---|---|---|---|
| Model proposal | Portfolio Manager / current run | Immutable after submission to gate | Advisory only |
| Structured Trader proposal | Trader adapter / current run | Retained through finalization | Candidate values only |
| RiskContext | Deterministic entry adapter / current run | Validated timestamped snapshot | Authoritative portfolio values |
| PortfolioRiskPolicy | `PolicyCatalog` | Versioned configuration | Authoritative limits |
| PortfolioRiskResult | Pure evaluator, then shared `SafetyGate` | Immutable finalized evidence | Authoritative risk calculation |
| Formal record | Shared `SafetyGate` | Persisted canonical record | Authoritative final result |

The current v0.7.0 baseline renders Trader and portfolio values to Markdown.
FR-04 requires typed state to remain available until finalization. Rendered text
is display-only and cannot become a numeric source of truth.

## Write policy

Only the shared finalization path creates the formal risk result. The evaluator
returns a value and performs no storage operation. `ArtifactPublisher` and
`MemoryService` may persist only the immutable finalized record.

Formal artifacts may retain policy version, normalized calculated metrics,
status, violation codes, original proposal reference, and effective final
result. They must not treat a blocked proposal as an executed position.

## Retrieval policy

Only the effective finalized result may be retrieved as the historical decision
for a later run. A blocked Buy or Overweight proposal may be retrieved only as
audit evidence and must never be presented as the prior effective decision.

Retrieval uses finalized-record identity, policy version, ticker, trade date,
record schema, and portfolio fingerprint. A mismatch invalidates the cached
risk result and requires deterministic re-evaluation.

## Persistence and retention

Memory stores the effective finalized rating/result, not a blocked Buy proposal
as the historical decision. Raw proposals remain audit-only.

The exact retention duration remains a team decision. Until approved, FR-04
introduces no automatic deletion policy. A future retention change must preserve
the evidence needed by active reviews and tests.

## Resume and versioning

On resume, a cached risk result is valid only when policy version, validated
portfolio fingerprint, candidate identity, and record schema still match. A
mismatch invalidates stale evidence and requires deterministic re-evaluation.

## Privacy

Stored records contain only the minimum normalized risk evidence required for
audit. API keys, `.env` content, credentials, raw provider secrets, unrelated
private positions, and full unredacted portfolio files are forbidden.

Exact persistence fields, retention duration, and deletion policy require team
approval. This fragment must be merged into the team's memory design.
