# CI Artifact Download Redirect Fix

## 1. Status

- Status: Proposed test specification; pending human approval.
- Approval state: not approved; implementation must not start before the
  approval described in Section 8.
- Branch: `fix-ci-artifact-download`, based on `main`.
- Purpose: fix trusted-artifact download authentication across redirects.
- This is not a Round 1 plan and does not approve application work.
- The branch is for the CI fix only and does not start Round 1.

## 2. Problem evidence

- A trusted evaluation run completed successfully for candidate
  `9422688378f19ccc6e6628ded6291c1a8cb54007` and produced the expected
  `semantic-not-applicable` artifact.
- The PR `evidence-check` reported HTTP 401 while downloading the trusted
  artifact through `scripts/ci_checks.py::_github_bytes()`.
- The workflow declares `actions: read`, passes `${{ github.token }}` to the
  evidence command, and the code passes that token to the artifact download
  request.
- A local simulation with a fake token and local HTTP servers confirmed that
  the current default `urllib` redirect behavior forwards `Authorization` to a
  different host.
- The exact remote root cause still requires post-fix verification against a
  real trusted artifact. This specification does not claim that the remote
  cause is fully proven yet.

## 3. Code scope

Files intended to change in the implementation PR:

- `scripts/ci_checks.py`
- `test/offline/test_ci_gates.py`
- `docs/ai-use-log.yaml`

Only `scripts/ci_checks.py` and `test/offline/test_ci_gates.py` are code/test
paths for contract-test selection. The approved specification must name both
paths exactly.

No change is planned to:

- `.github/workflows/ci.yml`;
- token permissions or repository secrets;
- application source;
- semantic configuration;
- the trusted evaluation workflow;
- Round 1 files.

## 4. Proposed implementation

Modify only the artifact download path in `scripts/ci_checks.py`.

- Initial API request keeps `Authorization`.
- A custom redirect handler is used only by `_github_bytes()`.
- The handler computes an origin from:
  - lower-cased scheme;
  - normalized hostname (case-folded; a trailing-dot variant is not folded to
    the undotted host);
  - effective port, using default 80 for HTTP and 443 for HTTPS.
- If the redirect origin differs from the request origin, remove
  `Authorization` from the redirected request.
- If the origin is the same, keep `Authorization`.
- A removed header must not be reattached by later redirects in the same chain.
- The custom opener is constructed locally in `_github_bytes()` and is not
  installed as the process-wide urllib opener.
- No new dependency is introduced.
- Download failures continue to raise `CiError`; no empty-result or success
  fallback is added.
- Token permissions are not expanded, and no PAT is introduced.

No change is made to the initial GitHub API helpers' normal requests, except
that the artifact download path uses the safe local opener.

## 5. Regression tests

Add the following tests to `test/offline/test_ci_gates.py`. Tests use a fake
token, local temporary HTTP services, or controlled simulations, and do not
access external networks. No real artifact URL, real token, or signed URL is
used.

### 5.1 Same-origin redirect preserves authorization

- Test name:
  `test_github_bytes_preserves_authorization_on_same_origin_redirect`
- Setup:
  - One local server redirects a path to another path on the same
    scheme/host/effective port.
  - The second response records `Authorization` and returns fixed bytes.
- Expected:
  - `_github_bytes()` returns the exact fixed bytes.
  - The second request retains `Authorization`.

### 5.2 Cross-host redirect drops authorization and reads the body

- Test name:
  `test_github_bytes_drops_authorization_on_cross_origin_redirect_and_reads_body`
- Setup:
  - Server A on one temporary loopback host/port redirects to Server B on a
    different host name.
  - Server B records headers and returns fixed bytes.
  - A fake token is supplied.
- Expected:
  - `_github_bytes()` returns the exact fixed bytes.
  - Server B receives no `Authorization` header.
  - No real network is used.

### 5.3 Scheme and effective-port origin checks

- Test names:
  - `test_github_bytes_treats_scheme_change_as_cross_origin`
  - `test_github_bytes_treats_effective_port_change_as_cross_origin`
  - `test_github_bytes_treats_default_and_explicit_equivalent_ports_as_same_origin`
- Setup:
  - Use controlled redirect-handler inputs for scheme and default-port cases
    that cannot be safely bound as local servers.
  - Use local servers for an explicit non-default port change.
- Expected:
  - HTTP to HTTPS, or a different effective port, drops `Authorization`.
  - `https://host/...` and `https://host:443/...` are treated as the same
    origin and keep `Authorization`.
  - `http://host/...` and `http://host:80/...` are treated as the same origin
    and keep `Authorization`.

### 5.4 Multiple redirects do not reattach authorization

- Test name:
  `test_github_bytes_does_not_reattach_authorization_across_multiple_redirects`
- Setup:
  - Server A redirects across hosts to Server B.
  - Server B redirects again to a second path on the same origin.
  - Both target responses record headers.
- Expected:
  - The first cross-host target has no `Authorization`.
  - The later same-origin redirect still has no `Authorization`; the removed
    header is not reattached.
  - The final body is read completely.

### 5.5 Download failure raises `CiError`

- Test names:
  - `test_github_bytes_raises_ci_error_on_401`
  - `test_github_bytes_raises_ci_error_on_connection_failure`
- Setup:
  - One local server returns HTTP 401.
  - One attempt targets a closed temporary local port.
- Expected:
  - Both cases raise `CiError`.
  - The exception is not converted to empty bytes or a successful result.
  - No fallback pass is added.

### 5.6 `fetch_trusted_runs` does not swallow download failure

- Test name:
  `test_fetch_trusted_runs_propagates_artifact_download_failure`
- Setup:
  - Controlled fake run/artifact responses use a fake `archive_download_url`.
  - The download helper is made to raise `CiError`.
- Expected:
  - `fetch_trusted_runs()` propagates the failure.
  - It does not continue with an empty artifact record.
  - The evidence-check failure remains blocking.

### 5.7 Test environment requirements

- Set `NO_PROXY`/`no_proxy` for the temporary loopback hosts so the environment
  proxy cannot intercept the local tests.
- Use ephemeral ports only.
- Shut down and close every local server in fixture cleanup/finally blocks.
- Join server threads.
- Use only synthetic bytes and a clearly fake token.
- Do not read `.env`, credentials, real artifacts, or the network.

## 6. Old implementation versus fixed implementation

Validation sequence for the implementation PR:

1. Add the tests first or with the fix, then run them against the current
   pre-fix implementation in an isolated temporary copy/worktree.
2. The critical cross-host test and the multiple-redirect test must fail before
   the fix because the current implementation forwards `Authorization`.
3. Same-origin and download-failure tests may pass before the fix; they remain
   guards against regression.
4. Apply the local redirect handler fix.
5. Re-run the targeted tests. All must pass.
6. Run the existing gate test file and required checks for the implementation
   PR.

The old-implementation check must use a disposable copy outside the repository
or a temporary worktree that is removed afterward. It must not overwrite the
working tree or be committed.

### 6.1 Remote acceptance after local validation

Local regression success is necessary but not sufficient. After the fix is
committed in a new candidate commit, CI must use the normal workflow permissions
to actually download and verify the trusted artifact for that new candidate.
The `evidence-check` must consume the artifact record successfully and complete
without a 401 or other download error.

A successful trusted-evaluation producer run or successful local tests alone do
not prove that the remote 401 is resolved. PR #3 retains its original commit
`9422688378f19ccc6e6628ded6291c1a8cb54007` as a historical validation sample;
the new fix must not be validated by rerunning that old candidate code.

## 7. Evidence and selection

- `contract-tests` must select exactly:
  `test/offline/test_ci_gates.py`
- The approved specification must mention:
  - `scripts/ci_checks.py` as the changed code path;
  - `test/offline/test_ci_gates.py` as the changed test path and selected test
    path.
- The implementation PR must include an AI-use-log update that associates
  `scripts/ci_checks.py` and `test/offline/test_ci_gates.py` with the actual
  work. No log entry is created by this specification-only step.
- No approval, commit SHA, test pass, trusted artifact result, or remote CI
  result is invented here.

## 8. Approval flow and future PR fields

Before implementation begins, the human must commit this specification, review
it, and provide a trusted approval event in the same fix PR. The approval must
come from a non-author human, not a bot, and must occur after this specification
commit and before the first commit that changes implementation/test paths.

The future implementation PR body must contain:

```text
Plan: docs/plans/ci-artifact-download-fix.md
Approved test specification: docs/plans/ci-artifact-download-fix.md @ <SPEC_COMMIT_SHA>
Approval evidence: <GITHUB_REVIEW_OR_COMMENT_URL>
Implementation start: <FIRST_IMPLEMENTATION_COMMIT_SHA>
Approved scope: scripts/ci_checks.py; test/offline/test_ci_gates.py; artifact redirect tests
```

The exact approval line must be:

```text
APPROVED test-spec: docs/plans/ci-artifact-download-fix.md @ <SPEC_COMMIT_SHA>
```

`<SPEC_COMMIT_SHA>`, `<GITHUB_REVIEW_OR_COMMENT_URL>`, and
`<FIRST_IMPLEMENTATION_COMMIT_SHA>` remain placeholders until the real events
occur. They must not be fabricated.

The specification commit must be an ancestor of the implementation start. If
the specification or the test assertions change after approval, a new approval
is required.

## 9. Exclusions

This specification does not:

- broaden repository token permissions;
- use a personal access token;
- skip evidence verification;
- add a success fallback for failed downloads;
- change application behavior;
- start Round 1;
- claim that the remote 401 is fully explained before the fix is verified.
