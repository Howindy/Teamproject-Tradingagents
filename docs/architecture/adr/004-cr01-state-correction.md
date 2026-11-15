# ADR 004 — CR-01 execution/acceptance state correction

Status: **requirements correction recorded; architecture design unchanged**
Date: 2026-11-15
D1 basis: `docs/req/requirements.yaml` v1.25.0 (CR-01 local correction only)
Supersedes in part: CR-01 lifecycle/state wording in ADR 003
Related: `docs/req/evaluation/brief-eval-contract-v4.json`, `docs/req/fixtures/brief_eval_states_v4.json`

## Context

ADR 003 described CR-01 lifecycle as one four-value set and allowed wording such as an aborted or pending acceptance state. The CR-01 requirement now uses two explicit authorities:

- `execution_status`: `not_started`, `running`, `completed`, `aborted`;
- `acceptance_status`: `blocked`, `ready`, `accepted`, `failed`, or `null` only while running.

The correction removes the ambiguous four-state/pending-aborted wording without changing CR-01's optimization target, local cost formula, quality/safety rules, thresholds, evidence requirements, or deferred scope.

## Decision

CR-01 uses the following state table:

| execution_status | Preconditions | acceptance_status | Meaning |
|---|---|---|---|
| `not_started` | pre-run material missing/invalid | `blocked` | not started; required inputs absent |
| `not_started` | all preconditions valid, no result | `ready` | not started and ready to run |
| `running` | attempt started | `null` | in progress; no acceptance conclusion yet |
| `completed` | all applicable conditions pass with valid bound evidence | `accepted` | terminal success for this attempt |
| `completed` | any condition fails or evidence missing/corrupt/inconsistent | `failed` | terminal failure for this attempt |
| `aborted` | started then stopped | `failed` | terminal failed attempt with abort reason and retained evidence |

`pending` and `aborted` are forbidden `acceptance_status` values. `run_completed`, if present, is auxiliary only and must equal `execution_status=completed`. A started attempt never returns to `not_started`, `ready`, or `blocked`; an input-digest mismatch after start ends `aborted/failed` or `completed/failed`. `accepted` and `failed` are terminal for the current attempt; retry creates a new attempt and preserves prior evidence and observed failures.

## Consequences

- The active evaluation contract is `brief-eval-contract-v4.json`; v3 and earlier remain historical.
- The state fixture is `brief_eval_states_v4.json`; v3 and earlier remain historical.
- Architecture components, planned tests, rounds, and monitoring responsibilities are unchanged. Only the CR-01 state expression and its current references are synchronized.
- CR-01 remains blocked until prices, targets, snapshots, and human evaluation-contract approval exist. Requirement-design approval does not approve those business conditions.
- No implementation, test, live evaluation, threshold approval, or measured result is claimed.
