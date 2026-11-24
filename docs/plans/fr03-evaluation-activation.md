# FR-03 trusted evaluation activation and frozen A3 compatibility

## 1. Status and authorization boundary

This is a reviewable maintenance and evaluation-standard proposal, not an
approval event or execution result. The user requested final delivery of Round 3
and authorized configuration preparation on 2026-11-25. No non-author approval
of this proposal or I6 suite selection is claimed. Freeze this document before
future executable maintenance, then obtain the real approval on this PR.

Base: main `f24cde487f8119bb238e171614066da4b60e6915` (merged PR #18).
Feature: PR #13, Round 3. Preserve its P3/A3 specifications and real approvals.
Historical feature CI-maintenance changes are not retroactively pre-approved by
this proposal. No feature merge, production deployment or course acceptance is
included.

## 2. Concrete problems and intended behavior

A. Main's supplemental selector accepts only a section named `## 3. Allowed files`
with simple bullet paths. Frozen A3 instead has `## 3. Exact additional file and
edit scope` and one bold standalone path. Replaying PR #13's actual comments on
the main-synchronized feature rejects A3, and portfolio contract coverage fails.

B. The data-availability suite is registered on main but remains unapproved.
Trusted evaluation deliberately cannot execute until the real standard approval
is recorded there. The suite regression still asserts unapproved status and must
be adapted to the authorized activation without weakening material protection.

C. PR #13 needs real non-author I6 selection and final-candidate evidence. The
human reviewer must actually inspect the candidate; agents must not fabricate
this confirmation.

## 3. Allowed files

- `scripts/ci_checks.py`
- `test/offline/test_ci_gates.py`
- `docs/ci/semantic-suites/data-availability.yaml`
- `test/offline/test_data_availability_evaluation.py`
- `docs/ci/README.md`
- `docs/ai-use-log.yaml`
- `docs/review-memo.md`

This is the complete future executable/configuration scope. Dataset, rubric,
financial-metrics configuration, workflows, credentials, dependencies, runtime
application code, requirements and frozen historical specifications are excluded.
No permissions or environment-protection change is authorized.

## 4. Bounded A3 compatibility design and tests

Only this immutable legacy supplement may receive compatibility:

- Path: `docs/plans/round-03-portfolio-test-amendment.md`
- Specification commit: `9e2c7793dc7d70fd2aeeecd480f78a5a81635614`
- LF SHA256: `02ff5e33086b89b591c64992d899370ddcb9ca7cb7aa8cba0639a1ead76a1df1`
- Sole allowed path: `test/offline/test_portfolio_context.py`
- Original approval: https://github.com/Howindy/Teamproject-Tradingagents/pull/13#issuecomment-7106366447

Pass the parsed specification path/commit into the allowed-scope resolver, or use
an equivalent local identity check before the existing resolver. Only when all
three immutable identity checks match may the explicit legacy section contribute
the sole path above. Do not scan rationale, commands, exclusions, or all bold text
for arbitrary paths. Existing modern allowed-file behavior stays unchanged.
Reuse the ordinary independent-human, exact marker, same-PR URL, ancestry,
first-related-change timing and post-approval-content checks. Failure grants no
scope or tests. Do not alter implementation-start timestamps or reset history.

Write tests before implementing the compatibility change:

- AC-01: exact frozen A3 with its actual event shape contributes only the portfolio
  path; selected tests include the P3/A3 union and primary checks remain mandatory.
- AC-02: wrong specification path, full commit, or one changed byte is rejected.
- AC-03: copy the heading/path into a different supplement, add another path,
  change the allowed path, or mention another file in exclusions: no new coverage.
- AC-04: author/bot, wrong event URL/PR/phrase/SHA, late approval, changed frozen
  specification or invalid ancestry remains rejected independently.
- AC-05: all existing modern multi-supplement/authenticated/stdlib-lean checks
  continue passing; unrelated legacy documents remain unsupported.
- AC-06: replay the saved actual P3/A3 events on a clearly labeled isolated
  candidate, then verify real GitHub CI after synchronization. Replay is not a
  new approval and does not establish all historical editing chronology.

## 5. Evaluation standard and activation

Approve exactly the existing fixed standard, without tuning it to model output:

- Suite: `data-availability`; requirement FR-03-FC05 / IR-12, with FC02/FC03 and
  IR-11 fixture meaning.
- Dataset: `fr03-data-availability-v1`, 5 cases DA-S01..DA-S05, bull/bear/research-manager.
- Dataset LF SHA256: `f6ca5fc2c7eeb82deab34218eff19f84fb0d960bb37bea98929bc9c064ad84f2`.
- Rubric: `fr03-data-availability-rubric-v1`.
- Rubric LF SHA256: `173f020b0ed79d7b92e2805abe7506d87fb5a0f01247c214900691e1fe775ae6`.
- 15 case-role combinations, all 45 dimensions pass, zero critical failures,
  zero unresolved reviews. Ambiguity blocks; no threshold/rubric relaxation.
- deepseek / `deepseek-flash`, `https://api.deepseek.com`; English,
  temperature 0, max_tokens 4096, stream false, n=1, max_retries 0,
  timeout_seconds 120, extra_body.thinking.type=disabled.
- Runner: `data_availability_eval:evaluate`; repetitions 1; llm_judge false.
- One final-candidate run, at most 20 completion requests total. Normally 15;
  up to five extra Manager parsing fallbacks. No evaluator retries, request 21,
  automatic rerun, alternate model, live data fetch, or automatic budget increase.

Only after real human standard approval: set status to approved and record the
actual reviewer's identity, actual event time, and real approval URL. Remove the
obsolete draft-only comment. Never use placeholders or a test fixture approval.
Update only the suite status assertion in its existing material test: keep exact
registry and independent dataset/rubric/config-control assertions; verify the
active config has approved status and real nonempty approval metadata. Retain
negative tests proving unapproved/incomplete approval and mutated controls fail.
The financial-metrics config remains byte-identical and unapproved.

Activation tests:

- EA-01: unapproved or missing approval metadata still blocks before any request.
- EA-02: approved fixed config validates; exact hashes/matrix/controls/budget stay
  independently checked, and financial-metrics material remains unchanged.
- EA-03: existing mock positive, contradiction, ambiguous and five-fallback tests
  preserve expected results and request accounting. They are not quality evidence.

## 6. Delivery and genuine human steps

1. Freeze this plan; non-author reviewer posts `APPROVED test-spec:` binding its
   path and full commit. The reviewer also explicitly approves section 5's fixed
   standard and one run with the 20-request ceiling in a real comment/review.
2. Implement only sections 4/5, record actual tests and approvals, and submit this
   separate main-based maintenance PR for review/merge. Do not merge automatically.
3. Synchronize PR #13 with that trusted main. Complete required offline/CI checks
   and determine its final full candidate SHA. Keep P3/A3 fields unchanged.
4. A non-author reviewer inspects that candidate and posts on PR #13:
   `APPROVED semantic-suites: data-availability`.
   Set `Semantic suites: data-availability` and `Semantic suites approval:` to
   that real comment URL. Do not replace this with none/not-applicable.
5. Dispatch trusted-evaluation.yml from main: mode=semantic,
   suite_id=data-availability, candidate_sha=the reviewed full SHA. Environment
   trusted-evaluation retains required human reviewers and prevent_self_review.
   Use only its existing secret; never read or print local credentials.
6. Inspect completion, all 45 outcomes, request accounting, details/artifact hashes
   and semantic-eval/data-availability status. Failure or needs_review blocks;
   no repeat without separately authorized scope/budget. Any candidate edit needs
   fresh candidate-bound evidence and an applicable new execution authorization.
7. Rerun PR #13 CI on the same SHA after evidence is present. Finish independent
   implementation review; no automatic merge or final FR-03 acceptance.

## 7. Verification commands and evidence

Use isolated source/environment copies and existing dependencies. No dependency
installation is part of this proposal. Isolate HOME/TMPDIR/XDG caches and disable
bytecode/cache writes into original source. Raw results/JUnit live under a fresh
`/private/tmp/cs5351-fr03-activation-*` directory; record actual versions and limits.

- `python -m pytest -q -p no:cacheprovider test/offline/test_ci_gates.py test/offline/test_data_availability_evaluation.py test/offline/test_financial_metrics_evaluation.py`
- `python -m pytest -q -p no:cacheprovider`
- `python -m ruff check src test scripts`
- `python scripts/ci_checks.py mypy --output <new-temp-file> --baseline mypy-baseline.txt`
- `python scripts/ci_checks.py schema --requirements docs/req/requirements.yaml --schema docs/req/req-schema.json`
- `git diff --check`

Preserve missing-tool and platform failures/skips; do not edit unrelated tests,
add waivers, or regenerate mypy baseline. Remote clean-install/platform gates
remain necessary. Record actual commands, inputs, failures and evidence. Passing
mock or mechanical CI checks is not live semantic-quality approval.
