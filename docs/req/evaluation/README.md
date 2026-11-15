# D1 Behavior Evaluation Contract

Status: **requirement design approved (D1 v1.24.0); frozen evaluation inputs; active draft contracts blocked; snapshots pending capture; evaluation/contract approval pending**

This directory makes the QR-01 live cache A/B and the CR-01 downstream-brief evaluation executable before behavioral acceptance.

## Files

- `eval-set-v1.json` — frozen 10-case evaluation set.
- `rubric-v1.json` — five-dimension rubric, anchors, rater and adjudication rules.
- `behavior-eval-contract-v1.json` — frozen historical thresholds and blocking rules for QR-01; retained unchanged.
- `behavior-eval-contract-v2.json` — active revision draft for QR-01 with scoring merge, adjudication, sample completeness, percentage-point REVIEW, hard safety events, and separate cache/risk-policy comparisons; blocked and not human-approved.
- `brief-eval-contract-v1.json` — historical frozen brief contract; retained unchanged.
- `brief-eval-contract-v2.json` — historical revision draft for CR-01; retained unchanged.
- `brief-eval-contract-v3.json` — active revision draft for CR-01; adds field-level usage, selected/shared generation, five-role actual input difference, total-sum aggregation, separate execution status, and claim boundaries; blocked and not human-approved.
- `config-v1.json` — fixed model/provider/config values.
- `prompt-v1.0.yaml` — fixed behavior-evaluation prompt and parameters.
- `snapshots-v1.json` — fixed snapshot manifest with per-case status/digest.
- `snapshots/<case_id>.json` — captured evidence for each case; not yet populated for the nine non-baseline cases.

## Required snapshot fields

Each case snapshot must record:

- case_id, ticker, analysis_date, asset_type;
- exact vendor responses or deterministic replay references for the tools used;
- source status and provenance;
- model/provider/config/prompt versions;
- capture time and capture command.

## Acceptance gate

Behavioral acceptance is blocked until:

1. every case has a captured snapshot;
2. the actual config and prompt files are fixed with digests;
3. the rubric version and eval-set version are recorded in the run;
4. human approval of the active behavior and brief contracts is recorded.

Deterministic fixed-replay fixtures require zero gate/coverage regression. Live
model sampling uses the separate quality thresholds in the contract, including
the allowed live REVIEW-rate delta. No QR-01 live A/B result may be claimed
complete before the blocked-state conditions are cleared. CR-01 additionally
requires an approved net_cost_max and prices; null thresholds are unresolved and
must not be treated as zero. Contract v3 fixes FR-02 field-level usage,
selected/shared generation, five-role actual input difference, total-sum
aggregation, Decimal comparison, and separate execution status. A true
zero-generation-call result is distinct from missing usage. Its measurement scope is local cost attribution,
not whole-application net cost. Budget attainment is not a saving claim; local
saving, token reduction, and whole-application saving are distinct. Token change
is measured without an approved token-improvement target. Retry/fallback
occurrences are recorded even when excluded from the local cost formula.
