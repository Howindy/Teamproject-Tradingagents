# Contract-test GitHub authentication amendment

## 1. Status and immutable basis

Draft for independent test-specification pre-approval, 2026-11-25.
The human user explicitly authorized adding the narrowly scoped workflow
maintenance below and preparing its pre-approval. No non-author approval of
this document, authentication implementation, new passing CI or merge is
established by this draft.

Inspected feature head: `563218bd1647f4da6c9916ac4316c93a5ec4f9b0`.
The worktree was clean at inspection. Original specifications remain unchanged:

- Suite: `docs/plans/round-03-semantic-evaluation.md @ 1440c1ca2ae0806ce3b4b09c20634cfa213e63da`.
- Original suite approval: https://github.com/Howindy/Teamproject-Tradingagents/pull/18#issuecomment-7133438544
- Maintenance: `docs/plans/semantic-registry-test-amendment.md @ 2d10aa4a24eee3cced9cbe4835bb695de0ebaf2f`.
- Original maintenance approval: https://github.com/Howindy/Teamproject-Tradingagents/pull/18#issuecomment-7135347793
- Original runner/test implementation start: `2982819d91784d29448671995dcf5937fc61ad27`.
- Earlier maintenance commits: `e52ac47abebbc89489f7e5ddeeb88cd4559979c0` and
  `563218bd1647f4da6c9916ac4316c93a5ec4f9b0`.

This amendment adds one workflow-file allowance and concrete authentication
and approval-preservation tests. It does not retroactively approve earlier
work, replace either frozen specification or restart the original chronology.

## 2. Reproduced problem and selected repair

Run: https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/45432196161
Job: https://github.com/Howindy/Teamproject-Tradingagents/actions/runs/45432196161/job/138580265497

At the inspected head all four Python regression jobs, test-approval, static,
type, dependency, schema, security-path, AI-use-log, evidence and smoke checks
passed. Contract-tests failed before collection because its supplemental
approval API query returned HTTP 403 rate limit exceeded. Aggregate failed
as a consequence. Those results belong to that run only.

The contract job supplies no token, and its checker explicitly passes an empty
token. Public unauthenticated requests share the originating IP's rate limit.
Use the Actions-provided short-lived GITHUB_TOKEN for this existing read path,
with only contents: read and pull-requests: read in the contract job.

Do not disable supplemental approval validation, treat API errors as approval,
add retries-until-green, discover stored credentials, or add a personal token.
No runtime prompt, model, provider, evaluation threshold or product requirement
is changed. This is maintenance of existing approval enforcement.

## 3. Allowed files

The only NEW implementation-path allowance granted by this amendment is:

- .github/workflows/ci.yml

Limit that file's edits to the contract-tests job's two read permissions and
its contract-command step's token environment, nonempty-token check and argument.
No other job, event, checkout authority, action version or workflow is selected.
This narrowly supersedes the previous workflow exclusion for that job only.

Existing file allowances remain under the independently approved original
maintenance specification: `scripts/ci_checks.py` and
`test/offline/test_ci_gates.py` for the associated token forwarding and multiple
supplement handling; `docs/ci/README.md`, `docs/ai-use-log.yaml` and
`docs/review-memo.md` for accurate operation and activity records. Their
additional authentication behavior and tests are specified here for review,
but these prose references do not grant new historical path coverage.

Keep only the new workflow path in this section's bullet allow-list. This
separates the new file allowance from paths already covered by the earlier
maintenance approval and prevents a new event being compared with their old
first-changing commits.

No src/, other workflow, dependency/build manifest, permission file, original
frozen specification/material, FR-10 oracle/configuration, cache or baseline
evidence change is authorized. Read-only GitHub token scopes specified here
are the complete workflow-permission extension; no write scope is allowed.

## 4. Exact authentication behavior

After this version is frozen, approved and implementation is authorized:

1. Add an explicit contract-tests job permission mapping containing exactly
   `contents: read` and `pull-requests: read`. Preserve the job's PR-only condition.
2. On the existing contract-command step, set
   `GH_TOKEN: ${{ github.token }}`. Check that GH_TOKEN is nonempty before invoking
   the command, without printing it, then append `--token "$GH_TOKEN"` to that
   existing invocation. Do not distribute the token through global workflow env.
3. Add an optional `--token` argument to the contract-tests CLI, defaulting to
   the empty string for existing direct callers. Forward its value unchanged
   through every supplemental validation to the existing API helper. Legacy
   programmatic Namespace callers without that attribute remain supported.
4. Authenticated requests use the existing Bearer-header helper. The explicit
   empty-token direct-call path retains its existing public-read behavior; CI
   cannot silently fall back to it because of the nonempty-token precondition.
5. HTTP 401/403, invalid evidence and other API failures remain blocking before
   collection/execution. No anonymous retry, approval bypass or new success
   placeholder is allowed. Do not print tokens, headers or full argument objects.

No repository secret or PAT needs to be created. No additional model, vendor,
status-publication or artifact-publication capability is introduced.

## 5. Preserve both supplemental approvals

The current parser rejects all repeated recognized fields and the callers
validate one supplement. Preserve the existing maintenance approval and support
separate, repeated supplemental lines, one per independently frozen document:

```text
Supplemental test specification: docs/plans/semantic-registry-test-amendment.md @ 2d10aa4a24eee3cced9cbe4835bb695de0ebaf2f (approval: https://github.com/Howindy/Teamproject-Tradingagents/pull/18#issuecomment-7135347793)
Supplemental test specification: docs/plans/semantic-contract-auth-amendment.md @ <new full SHA> (approval: <real new approval URL>)
```

- Keep primary Plan, Approved test specification, Approval evidence,
  Implementation start and Approved scope unique and unchanged.
- Only Supplemental test specification may repeat. Preserve every distinct
  value; do not overwrite one with another. Reject duplicate identical entries
  and ambiguous repeated specification paths instead of silently choosing one.
- Validate each supplement independently: real same-PR event, non-author human,
  exact marker/version, valid ancestry, unchanged specification and approval
  before that supplement's own first related implementation change.
- Use each document's explicit section-3 allowed-file list for path coverage
  and its own related-change chronology. Historical references, exclusions and
  inherited-file prose do not create new coverage.
- The original maintenance supplement continues to govern its own first related
  changes. This new supplement's new-path chronology is the first change to
  .github/workflows/ci.yml. Do not reset either earlier start or invent a later one.
- The approval gate must report invalid supplements; an invalid supplement grants
  no scope or tests. Contract execution fails before collection if any supplied
  supplement is invalid. Primary validation remains mandatory in its own gate.
- Union only independently validated scope and selected test coverage. The
  combined plan must continue selecting the approved gate/FR-03/FR-10 tests;
  it cannot grant coverage to unrelated executable paths.

This amendment does not introduce a generic baseline/checkpoint exception for
already changed files. It preserves the existing file-based limits and exposes
their evidence boundary: automatic chronology checks prove the new workflow
file's first-changing commit, not the edit time of each later change to an
already-covered script. Human review must check the drafting checkpoint above,
the actual pre-implementation approval and the first authentication commit.

## 6. Implementation sequence and chronology

1. Create and review this document only. Freeze it as a standalone commit.
2. Obtain a real non-author approval comment binding its full SHA before any
   corresponding workflow, script or test edits. Record actual URL/time only.
3. Implement the workflow wiring, CLI forwarding, repeated-supplement support
   and related executable tests together. Deliver these executable changes in
   the same first authentication implementation commit after approval; do not
   implement or commit the token path separately before approval.
4. Add the second supplemental machine field only after its real event exists
   and at the time the compatible parser is delivered. The current parser will
   reject the second field; do not claim old code already understands it.
5. Keep the original primary fields and original supplemental line. Update
   actual AI-use/review records without rewriting historical results.
6. Run the checks below, push only with delivery authorization, and inspect a
   fresh final-candidate PR CI. Do not replace review with rerunning old jobs.

The specification commit must precede the approval, which must precede actual
implementation edits. Git author timestamps alone do not prove that sequence.
If new evidence contradicts this checkpoint, stop affected work and report it.

## 7. Concrete independent test specification

All new executable tests stay in the existing gate test file. Use synthetic
GitHub responses, literal synthetic tokens, real temporary Git histories and
controlled pytest execution seams. No live model or vendor requests. Do not
use a real token as a fixture or derive expected values from the checker.

| ID | Controlled scenario | Independent expected result |
|---|---|---|
| CA-T01 | Parse the real CI YAML and inspect contract job/step | Exactly the two read scopes; existing PR-only condition retained; step supplies github.token, checks nonempty GH_TOKEN and passes --token; no global token or write scopes |
| CA-T02 | Parse contract CLI with a literal token; run valid supplemental flow | The exact token reaches every approval query and the existing Bearer header; valid evidence reaches collection/execution |
| CA-T03 | Legacy CLI without token or Namespace without token attribute | Supported direct-call behavior retained; no empty Bearer header; workflow is still guarded against empty token |
| CA-T04 | Authenticated query raises 401 or 403 | Nonzero result before pytest collection/execution; no anonymous fallback, retry or token disclosure |
| CA-T05 | Valid primary plus old maintenance and new workflow supplements | Both events validated separately; correct original and new related-change chronology; valid combined scope/test selection |
| CA-T06 | Either supplement has wrong marker/SHA/PR, author/bot reviewer, missing event or late approval | Overall approval/contract flow blocked; invalid supplement contributes no scope or tests; earlier valid approval is not overwritten |
| CA-T07 | Duplicate primary or ADR fields; repeated identical supplement; ambiguous repeated spec path | Rejected; two distinct valid supplemental lines retained in order without last-one-wins |
| CA-T08 | New supplement merely mentions an unrelated code/test path outside section-3 bullets | Mention does not grant coverage or alter first-related-change selection |
| CA-T09 | Freeze original maintenance then implement it, freeze auth amendment later, approve it, then change workflow and auth scripts | Valid chronological chain accepted without resetting original primary or maintenance starts; auth approval after first workflow change instead fails |
| CA-T10 | Change either frozen specification after its approval, or break its ancestry | Rejected independently; no historical approval substitution |
| CA-T11 | No supplement, one legacy supplement, multiple supplements; existing no-selection/nonsemantic cases | Prior applicable behavior retained; no unnecessary token/API requirement introduced for a path that previously needed no query |
| CA-T12 | Python 3.12 isolated -I -S approval replay with two supplements; run existing gates | No new third-party dependency on approval path; primary/old/new invalid cases still block; original T16/T18 and security-path assertions retained |

Security-path must remain without review-query token injection; only the
contract-tests job receives the new wiring. Existing token-bearing test-approval
is unchanged. Do not weaken negative tests or mark API errors as passes.

## 8. Verification commands and environment limits

Use existing installed tools; no dependency installation is authorized. Use a
fresh OS temporary evidence directory, controlled HOME/TMPDIR/cache paths and
bytecode policy. Do not write test outputs into the working tree.

Planned normal checks when that environment is available:

```sh
python -m pytest -q -p no:cacheprovider test/offline/test_ci_gates.py test/offline/test_data_availability_evaluation.py test/offline/test_financial_metrics_evaluation.py
python -m ruff check scripts/ci_checks.py test/offline/test_ci_gates.py
python scripts/ci_checks.py mypy --output <fresh-temp>/mypy.txt --baseline mypy-baseline.txt
python scripts/ci_checks.py schema --requirements docs/req/requirements.yaml --schema docs/req/req-schema.json
python -m pip check
python -m pytest -q -p no:cacheprovider
git diff --check
```

Also inspect the real YAML job wiring and execute the isolated -I -S approval
replay using recorded real PR events against the checked Git candidate. Such
replay is local evidence, not final remote-CI evidence or a live model score.

The recovered local application environment currently lacks pytest, and Ruff/
mypy are unavailable. If still unavailable, record blocked commands explicitly.
Standalone gate tests with --confcutdir=test/offline are allowed unit evidence,
with no application stubs, but cannot be called default application regression.
Do not use the vanished iCloud environment as a prerequisite or claim it passed.
Do not install packages to satisfy this draft.

## 9. Final review and execution boundaries

A passing authenticated query is not approval by itself; the real event marker,
reviewer, version and chronology checks must still pass. The final workflow
must execute contract tests and aggregate normally, without a bypass.

Evaluation configuration stays unapproved. No model/vendor request, prompt
change, deployment, branch-protection change, secret creation, merge or final
product acceptance is authorized by this pre-approval.

## 10. Drafting activity

Codex prepared this specification after the user's explicit scope-extension
request. Read-only inspection confirmed clean head 563218b, the rate-limit log,
the hard-coded empty token, the absent workflow token/read scope and the
single-supplement parser limitation. No authentication code, executable test or
workflow modification is performed by this drafting stage. This section records
planning activity without inventing an independent verdict or raw transcript.
