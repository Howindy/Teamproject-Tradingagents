# Semantic suite registry and approval-gate maintenance

## 1. Status and approval boundary

Draft for independent review. This document does not establish approval,
implementation success, model execution authorization or merge authorization.

The original FR-03 suite specification remains unchanged:

docs/plans/round-03-semantic-evaluation.md @ 1440c1ca2ae0806ce3b4b09c20634cfa213e63da

Original approval evidence:

https://github.com/Howindy/Teamproject-Tradingagents/pull/18#issuecomment-7133438544

This maintenance specification covers only the additional work below.
It does not retroactively approve existing implementation.

## 2. Observed problems

A. T16 compares the complete registry with a dictionary containing only
financial-metrics. A valid additional suite therefore fails the test.

B. The inspected approval gate supports only one primary specification.
It cannot independently validate this supplemental maintenance approval
or use its approved test scope for contract-test selection.

C. The inspected gate includes governance_ci paths when finding the first
implementation commit. The FR-03 specification commit also introduced
fixed evaluation materials under docs/ci, before the original approval.

The existing chronology must be preserved:

- Specification/materials: 1440c1ca2ae0806ce3b4b09c20634cfa213e63da
- Original non-author approval: 2026-11-24T13:51:24Z
- Runner/tests: 2982819d91784d29448671995dcf5937fc61ad27

No timestamp, historical approval or existing commit is to be rewritten.

## 3. Allowed files

Executable changes, only where required by sections 4-6:

- scripts/ci_checks.py
- test/offline/test_ci_gates.py

Maintenance documentation and actual activity records:

- docs/ci/README.md
- docs/ai-use-log.yaml
- docs/review-memo.md

The original frozen suite specification, dataset, rubric and configuration
remain unchanged.

Excluded: src/, runtime prompts, workflows, dependencies, permissions,
FR-10 configuration/materials and baseline evidence.

## 4. Registry compatibility change

Change T16 from whole-registry equality to exact equality of the
financial-metrics entry.

Preserve:

- Registry validation with no errors.
- Exact FR-10 requirement/config/runner mapping.
- Original LF-normalized FR-10 configuration hash.
- Original unapproved status and trusted configuration-state checks.
- T18 validation of every registered suite's config, runner mapping and
  entry-point signature.

Do not require exactly two suites, skip T16 or weaken unrelated assertions.

Independent tests:

R1. Correct FR-10-only registry passes.
R2. Correct FR-10 plus a valid additional suite passes.
R3. Missing FR-10 entry fails.
R4. Changed FR-10 requirement, config or runner fails.
R5. Invalid additional registration remains rejected.
R6. FR-10 hash/status protection remains effective.

## 5. Supplemental approval support

Support this exact additional PR field:

Supplemental test specification: <path> @ <full SHA> (approval: <URL>)

Preserve the primary specification, approval and implementation chronology.
The supplemental specification only adds independently approved coverage.

Validate independently:

- Real GitHub approval event from a non-author, non-bot reviewer.
- Exactly matching APPROVED test-spec marker.
- Immutable specification and valid ancestry.
- Approval before the first related implementation/test change.
- No unapproved change to the supplemental specification.

Only valid supplemental specifications may add scope or contract tests.
The new specification's own creation is not its implementation start.
Existing runner changes must not be retroactively covered by this supplement.

Independent tests:

S1. Primary approval plus a valid supplement accepts covered later changes.
S2. Missing, mismatched, author/bot or late approval fails.
S3. Changed specification or invalid ancestry fails.
S4. Invalid supplements add no scope or selected tests.
S5. Primary checks remain mandatory.
S6. Contract selection includes approved supplemental tests and rejects
    executable changes outside the combined valid specifications.
S7. Ambiguous duplicate primary fields are rejected.

## 6. Implementation-start classification

Exclude a preparation material change from implementation-start calculation
only when ALL the following conditions hold:

1. The path is one of these three exact FR-03 suite material paths:
   - docs/ci/data-availability-cases.json
   - docs/ci/data-availability-rubric.md
   - docs/ci/semantic-suites/data-availability.yaml
2. The path is explicitly identified in the primary approved specification
   as a preparation material.
3. The material exists at the immutable primary specification commit and
   its Git blob is identical at the evaluated candidate.
4. The suite configuration at that specification commit and candidate
   remains unapproved, with no approval identity, approval time or approval
   evidence recorded.
5. The exception excludes only these material paths from the start-path
   set. It never excludes other paths changed in the same commit.

This is a bounded compatibility rule for the existing FR-03 preparation
sequence. Do not generalize it to all docs/ci files, all YAML/JSON/Markdown,
or all files labelled unapproved.

Never exempt:

- Executable code or tests.
- Workflow or permission changes.
- Shared suite registry/routing changes.
- Configuration activation or approval-record changes.
- Materials absent from the approved specification commit.
- Materials whose contents differ from the approved specification commit.

If any condition cannot be established, retain the path in the normal
implementation-start calculation. Do not silently accept it.

Preserve all other primary approval checks, including the real approval
event, its timing, specification ancestry, unchanged specification,
declared start SHA and approved scope.

Independent tests:

C1. The exact three frozen preparation materials, followed by approval and
    later executable implementation, do not move implementation start
    earlier than the first actual implementation change.
C2. Executable implementation before approval still fails.
C3. A commit containing both exempt materials and executable code counts
    as implementation because the code path remains included.
C4. A material differing from its frozen specification blob is not exempt.
C5. An approved/activated configuration is not exempt.
C6. Shared registry, workflow and permission changes are not exempt.
C7. A material not named in the approved specification is not exempt.
C8. A missing or unverifiable frozen material is not exempt.
C9. Declaring an incorrect implementation-start SHA still fails.
C10. Existing PRs without these exact preparation paths retain their
     implementation-start behavior.

Any broader reusable material-classification mechanism requires a separate
reviewed specification.


## 7. Verification

Use the existing project environment. No dependency installation or live
model/vendor requests.

Run targeted positive/negative gate tests, then:

python -m pytest -q -p no:cacheprovider test/offline/test_ci_gates.py test/offline/test_data_availability_evaluation.py test/offline/test_financial_metrics_evaluation.py
python -m ruff check scripts/ci_checks.py test/offline/test_ci_gates.py
python -m pytest -q -p no:cacheprovider
git diff --check

Complete applicable project type/schema/dependency checks.
Record actual commands, versions, results, failures and skips.
Offline mocks are not evidence of real model quality.

## 8. Approval and delivery order

1. Review and finalize this maintenance specification, including the exact
   section-6 classification rule, before freezing it.
2. Commit the specification separately and obtain non-author approval
   binding its full commit SHA.
3. Implement only the approved maintenance scope.
4. Preserve original approvals and add the real supplemental evidence.
5. Update actual AI-use and review records.
6. Verify locally, push and inspect fresh PR CI.
7. Keep evaluation configuration unapproved; real model execution and merge
   remain separately authorized actions.

Any material scope or expectation change requires approval of the revised
immutable version before the affected implementation.
