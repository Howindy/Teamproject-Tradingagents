# Semantic Suite Routing — CI Maintenance Plan

- Status: **Proposed — pending real human approval.** No approval, approver, timestamp or pass result is recorded here.
- Task type: separately authorized CI/governance maintenance (AGENTS.md "File and tool boundaries"). Not an application round; it changes no `src/` code, no requirement, no D2 contract and no scorer business rule.
- Base: `origin/main` @ `00833f4b281692c266bbd52c5955a4f40ec89493` (merge of PR #14), verified by fresh clone/fetch on 2026-11-24.
- Branch / worktree: `prep/semantic-suite-routing`, `D:\CityU\cs5351\project\Teamproject-Tradingagents-semantic-gates`.
- This document is the test specification for the implementation checkpoint. Approval phrase format is in §10.

## 1. Inputs read

`AGENTS.md`, `Prompt.md`, `.opencode/rules.md` (read only), `.agent/rules.md`, `CI.md` (§3 workflow structure, §4.4 semantic evaluation, CI self-protection), `docs/ci/README.md`, `docs/ci/semantic_eval.yaml`, `scripts/ci_checks.py`, `scripts/ci_semantic_eval.py`, `scripts/financial_metrics_eval.py` (`evaluate` return shape only), `.github/workflows/ci.yml`, `.github/workflows/trusted-evaluation.yml`, `test/offline/test_ci_gates.py` (evidence/workflow tests), `test/offline/test_financial_metrics_evaluation.py` (config-path use), `docs/plans/financial-metrics-integration.md`, and, on their remote branches, `docs/plans/shared-summary-integration.md` (`prep/shared-summary-integration` @ `7cc38da`) and the `round-03-fr03` diff (@ `7bf46d1`). Course sheet: CS5351 project PDF (fixed semantic evaluation for prompt/model changes; CI gates enforced by branch protection).

## 2. Current code path and confirmed problems

Current path (main @ `00833f4`):

1. `ci.yml/classify` → `ci_checks.py classify` → `classify_paths()` returns one boolean `semantic_required` (plus the `semantic` path list).
2. `ci.yml/evidence-check` (candidate checkout) → `ci_checks.py evidence --semantic-config docs/ci/semantic_eval.yaml [--semantic-required]` → `semantic_config_status()` + `fetch_evidence()` → `verify_evidence()`.
3. `trusted-evaluation.yml` (default-branch dispatch, protected env `trusted-evaluation`) → `ci_semantic_eval.py --config docs/ci/semantic_eval.yaml --runner "${{ inputs.semantic_runner }}"` → `run_approved_evaluation()` → writes `record.json`, uploads artifact `ci-evidence-<sha>-<mode>`, posts status `semantic-eval/evidence` (or `semantic-eval/not-applicable`) on the candidate SHA.

Confirmed problems (each verified against the code above):

| # | Problem | Location |
|---|---|---|
| P1 | One shared config. `docs/ci/semantic_eval.yaml` now holds FR-10-only content (financial dataset/rubric/thresholds), yet every semantic PR is checked against it. FR-03 (Yifan) and the shared summary have no place for their own standard. | `ci.yml:320`, `trusted-evaluation.yml:98,109` |
| P2 | One status context. Any passing `semantic-eval/evidence` satisfies every semantic PR; a financial-metrics pass would satisfy an FR-03 prompt change. A second suite run on the same SHA overwrites the first. | `ci_checks.py:32`, `verify_evidence()` |
| P3 | Runner is free text. `semantic_runner` is an arbitrary `module:function` dispatch input, imported without an allow-list; `execution.runner` in the config is not used. | `trusted-evaluation.yml` input, `run_approved_evaluation()` |
| P4 | Evidence binds only `dataset.version`, not the config content. A config edit that keeps the version (thresholds, model) is not detected. | `semantic_config_status()`, `build_record()` |
| P5 | Evidence-check reads the config from the **candidate** checkout, so a PR can edit the file that decides its own approval state. (The checker script also runs from the candidate; that is the existing, documented CI self-protection limitation and is not changed here.) | `ci.yml` evidence-check checkout |
| P6 | `needs_review` is flattened to `failed`; the pending items are only in the details artifact, and `reason` is built from `errors`, which is empty for needs_review. | `ci_semantic_eval.py main()` |
| P7 | No scope selection exists: no PR field, no reviewer confirmation of which suites cover the change. `not-applicable` is candidate-wide and can coexist with nothing selected. | `ci_checks.py`, PR body fields |
| P8 | Artifact names `ci-evidence-<sha>-semantic` and concurrency `trusted-evaluation-<sha>-semantic` would collide across suites. | `trusted-evaluation.yml` |
| P9 | The PR body is read from the event payload; GitHub re-runs reuse the original payload, so a body edit is not seen on re-run. | `ci.yml` (test-approval uses `github.event.pull_request.body`) |

Observed, outside this plan (reported to the FR-10 session, not changed here): `financial_metrics_eval.evaluate` requires `execution.baseline_root / baseline_sha / baseline_python_executable`, which neither the config nor the trusted workflow currently supplies; semantic mode would fail closed for financial-metrics until that session addresses it.

## 3. Design

Design method: attribute-driven design (ADD), applied briefly. Drivers: per-feature fixed evaluation and explicit PR selection (functional); Q1 isolation (one suite's pass never satisfies another), Q2 trust (config and runner come only from the default branch), Q3 modifiability (a new suite adds its own files and one registry line, no framework edit), Q4 parallel development (a suite unit can be built without waiting for this framework work), Q5 bounded cost (fixed request cap per suite); constraints: existing workflows, secret, protected environment, no new dependency, `.agent/rules.md` §1. Decomposition: two elements, the **framework** (§3.1–§3.4) and **suite units** (§3.5), joined only by the interfaces in §3.5.

Minimum change: one static registry file, one PR field plus one reviewer phrase, a `suite_id` workflow input, and per-suite status/record verification inside the existing `evidence-check` job. No new workflow, job, service, dependency, plugin loader or automatic path→suite mapping. The registry is a fixed allow-list read as data (it does not discover or load arbitrary code), which keeps it within `.agent/rules.md` §1's limit on generic registries.

### 3.1 Registry — `docs/ci/semantic-suites.yaml` (new)

```yaml
schema_version: "1.0"
suites:
  financial-metrics:
    requirement: "FR-10"
    config: "docs/ci/semantic_eval.yaml"
    runner: "financial_metrics_eval:evaluate"
```

Validation (`load_suite_registry()`, fail closed):

- suite ID matches `^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$`, ≤ 40 chars; `evidence` and `not-applicable` are reserved; duplicates rejected (duplicate-key YAML loader).
- `config` is project-relative, resolves inside `docs/ci/`, exists; each config path is used by at most one suite.
- `runner` is `module:function` whose module is a file in `scripts/` (no dotted packages, no candidate import path); if the config has `execution.runner`, it must equal the registry runner.
- unknown keys rejected; `requirement` required (traceability only, not used for routing).

The registry is read **only from the default branch** (trusted workflow root checkout; evidence-check's separate default-branch checkout, §3.4). A feature PR may propose an entry, but it takes effect only after merge to main.

**FR-10 migration:** the file stays at `docs/ci/semantic_eval.yaml`, byte-identical (git blob `4e0d13d967b48e4386804e3f5a32c88be6ae0f0f`; LF SHA-256 `20e15937f66a14617e9b613d1c42854dd2a1dd616771d84d40bc746d1423d9b7`), keeping `status: "unapproved"`, `dataset.version: fr10-sec-reference-projection-v1`, `rubric.version: fr10-eval-rubric-v1` and `approval: null` values. It becomes FR-10-dedicated by being bound to exactly one suite and no longer read as a shared default. Keeping the path avoids editing ADR 002, the blueprint, the evaluation table, the FR-10 plan and its test constant, which all cite it. New suites use `docs/ci/semantic-suites/<suite-id>.yaml` (convention, not enforced). Renaming the FR-10 file is a reviewer option that requires a revised plan.

### 3.2 PR fields and reviewer confirmation

New PR body fields (parsed by the existing `parse_pr_body()`):

```text
Semantic suites: financial-metrics, data-availability     (or: none)
Semantic suites approval: <GitHub review/comment URL>
```

The approval event at that URL (may be the same comment as the test-spec approval) must contain exactly one line:

```text
APPROVED semantic-suites: <same list>
```

Verification (`verify_suite_selection()`), reusing `fetch_approval_event()`'s author/bot/URL logic:

- the list is split on commas, trimmed, lower-cased, de-duplicated and sorted; `none` must stand alone; body list must equal the phrase list;
- reviewer is a real non-author, non-bot human; exactly one phrase line; URL is a GitHub review/comment of this PR;
- every listed ID exists in the default-branch registry;
- unlike test-spec approval, no "earlier than implementation start" rule: the selection covers final scope and may be confirmed after implementation;
- the PR body is fetched from `GET /repos/{repo}/pulls/{n}` at check time (fixes P9 for this field).

Course coupling: the approved test specification of a prompt-bearing feature should name its suite IDs; the human reviewer confirms coverage. CI does not parse plans for suite IDs (no new plan parser).

### 3.3 When the selection is enforced (decision table)

| `semantic_required` | `Semantic suites` field | Result |
|---|---|---|
| false | absent or `none` | Old path: no semantic check, no GitHub fetch for suites. Passes. |
| false | non-empty list | Selection is verified and every selected suite needs evidence (reviewer opted in). |
| true | absent / empty | **Block:** `semantic evaluation required but no semantic suite was selected (add "Semantic suites:" and a reviewer "APPROVED semantic-suites:" line)` |
| true | `none` | Requires a verified candidate-bound `semantic-eval/not-applicable` record (existing reviewed noop path). |
| true / false | list with unknown ID | **Block:** `unknown semantic suite: <id> (not in default-branch docs/ci/semantic-suites.yaml)` |
| true / false | selected suite whose trusted config is not approved | **Block:** `semantic suite <id> configuration <path> is unapproved` |
| any | list, but approval missing/mismatched/self/bot | **Block** with the specific reason |
| any | list | Each selected suite needs its own passing evidence (§3.4). A `not-applicable` record does not substitute for a selected suite. |

### 3.4 Workflow inputs, status names, artifacts and evidence

`trusted-evaluation.yml`:

- new input `suite_id` (string; required when `mode == semantic`); input `semantic_runner` removed.
- all inputs reach shell steps via `env:` (not `${{ }}` inside `run:`), and the suite ID is validated by `ci_semantic_eval.py` against the registry before any import, checkout use, or status context is built.
- semantic step: `ci_semantic_eval.py --registry docs/ci/semantic-suites.yaml --suite "$SUITE_ID" ...`; config and runner come only from the registry entry. `--config/--runner` semantic mode is rejected with `select a registered suite with --suite`; `--not-applicable` keeps its current arguments.
- status context: `semantic-eval/<suite-id>` (e.g. `semantic-eval/financial-metrics`); noop stays `semantic-eval/not-applicable`; live stays `live-tests/evidence`. The legacy `semantic-eval/evidence` is no longer written or accepted (no passing instance exists: the only config has never been approved).
- artifacts: `ci-evidence-<sha>-semantic-<suite-id>`, `ci-semantic-details-<sha>-<suite-id>`; concurrency group `trusted-evaluation-<sha>-<mode>-<suite-id>`.
- status description on failure includes the outcome: `needs_review: <n> pending items` or `failed`.
- existing `DEEPSEEK_API_KEY` secret, environment `trusted-evaluation`, default-branch check, double-checkout HEAD verification, `if: always()` failure records and status writes are kept. A suite needing a different secret needs its own workflow change (out of scope).

Evidence record (`record.json`) adds:

```json
{
  "kind": "semantic",
  "suite_id": "financial-metrics",
  "config_path": "docs/ci/semantic_eval.yaml",
  "config_sha256": "<LF-normalized SHA-256 of the trusted config>",
  "config_version": "<dataset.version, unchanged meaning>",
  "runner": "financial_metrics_eval:evaluate",
  "status": "passed | failed | needs_review",
  "needs_review": ["FM-S01:missing_metric_mention:...", "..."]
}
```

plus all existing fields (`candidate_sha`, `workflow_sha`, `run_id`, `details_sha256`, `dataset_sha256`, `rubric_sha256`, summaries). `needs_review` items are copied from the runner result (`candidate_summary.needs_review` or top-level `needs_review`); config hashing reuses the CRLF→LF normalization used by `financial_metrics_eval.sha256_file`.

`ci.yml/evidence-check`:

- adds a second checkout of the default branch into `trusted/` and passes `--registry trusted/docs/ci/semantic-suites.yaml --trusted-root trusted`; records its SHA in the job output. Suite configs are read and hashed from `trusted/` (fixes P5 for registry/config data). Adds `pull-requests: read` (PR body + approval event) and `--pr <number>`.
- per selected suite: status `semantic-eval/<id>` on the candidate, trusted run checks unchanged (`_verify_trusted_status`), plus record `suite_id == id`, `config_path` equals registry, `config_sha256` equals the current trusted config hash (stale after a main config change → rerun required), `status == passed`. `needs_review` → **block** `semantic suite <id> needs human review: <items>`; nothing in CI converts it to a pass — it goes to the existing human review (fix and re-evaluate, or the suite owner changes the scorer/config through its own approved PR).
- bootstrap: if the default branch has no registry and the selection is not enforced (first row of §3.3), pass exactly as today; if enforced, block `trusted semantic suite registry is not present on the default branch`. This lets this maintenance PR itself pass evidence-check before merge.
- `aggregate`, `classify` outputs and other jobs are unchanged. The checker code still runs from the candidate checkout (existing limitation; CI paths require human review via branch protection, CI.md "CI self-protection").

### 3.5 Suite unit contract (interfaces I1–I6, for parallel work)

This section is the stable boundary between the framework (owner: CI maintenance, this plan) and each suite unit (owner: the feature's author, e.g. Yifan for FR-03 Round 3). The framework calls only the runner entry point and does not interpret scorer business rules; a suite unit does not depend on status names or evidence verification. A change to I1–I6 after approval is a material revision of this plan.

**I1 — registry entry.** One entry per suite in `docs/ci/semantic-suites.yaml` with exactly `requirement`, `config`, `runner` (§3.1). A suite unit's PR adds only its own line to this shared file.

**I2 — suite configuration.** The structure already accepted by `ci_semantic_eval.validate_config()` on main, unchanged: `schema_version`, `status` (`unapproved` until a real approval), `dataset{version, path, sha256, cases}`, `rubric{version, path, sha256, definition}`, `thresholds`, `model{provider, model, base_url, configuration}`, `execution{runner, max_completion_requests}`, `approval{approved_by, approved_at, evidence}`. `execution.runner` equals the registry runner. Hashes are SHA-256 of LF-normalized bytes. Dataset content, rubric, thresholds, model settings and request cap are owned and justified by the suite unit; the framework adds no threshold.

**I3 — runner entry point.**

```python
def evaluate(
    config: Mapping[str, Any],
    candidate_sha: str,
    *,
    output_dir: Path,
    model_transport: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]: ...
```

Framework guarantees at call time (trusted workflow): working directory is the trusted default-branch checkout; the candidate is checked out at `candidate/` with `HEAD == candidate_sha` verified and installed with `pip install -e candidate[dev]`; `DEEPSEEK_API_KEY` is in the environment; `output_dir` exists and is writable; `model_transport` is not passed (it exists for offline test stubs only).

Runner obligations: verify dataset and rubric hashes against I2; never exceed `execution.max_completion_requests`; run candidate code only from `candidate/`; no network access other than the configured model provider; no GitHub status or API writes; return `failed` instead of raising for evaluation failures (an exception is recorded as `failed` by the framework).

Return mapping:

| Key | Required | Meaning |
|---|---|---|
| `status` | yes | exactly `passed`, `failed` or `needs_review` |
| `errors` | yes | `list[str]`, may be empty |
| `needs_review` | yes | top-level `list[str]` of `<case-id>:<reason>`, may be empty (the framework also reads FR-10's `candidate_summary.needs_review` for compatibility) |
| `request_count` | yes | integer number of model requests actually sent |
| `dataset_sha256`, `rubric_sha256` | yes | hashes actually verified |
| `details_path`, `details_sha256` | yes | details JSON written inside `output_dir` |
| `candidate_summary` | no | copied into the evidence record unchanged |

**I4 — file naming** (`<id>` hyphenated, `<id_>` with underscores): config `docs/ci/semantic-suites/<id>.yaml`; cases `docs/ci/<id>-cases.json`; rubric `docs/ci/<id>-rubric.md`; runner `scripts/<id_>_eval.py`; offline tests `test/offline/test_<id_>_evaluation.py`. FR-10 keeps its existing names (§3.1).

**I5 — dispatch and status** (framework-owned, stated for suite owners): trusted dispatch `mode=semantic`, `suite_id=<id>`; status `semantic-eval/<id>`; artifacts `ci-evidence-<sha>-semantic-<id>` and `ci-semantic-details-<sha>-<id>`.

**I6 — feature PR fields** (§3.2): `Semantic suites: <id>[, <id>...]`, `Semantic suites approval: <URL>`, reviewer line `APPROVED semantic-suites: <same list>`.

Provisional FR-03 suite ID: `data-availability`, to be confirmed by its owner. The ID itself is not part of the contract; choosing another valid ID needs no revision of this plan.

Parallel tracks and merge order:

| Stage | Framework track | Suite unit track (FR-03) |
|---|---|---|
| 0 | This plan, including I1–I6, approved | Owner reviews I1–I6 and confirms the suite ID |
| 1 | Implement §3.1–§3.4 and tests T01–T18 | Build the I4 files and offline tests with a stub `model_transport`, on its own branch from current main; self-check the config with main's existing `validate_config()`; no framework file edits |
| 2 | Framework PR merges first (registry contains only `financial-metrics`) | Suite unit PR merges next: own files plus one registry line. It contains `scripts/*.py`, so it needs its own test-specification approval |
| 3 | — | A separate change on main sets the suite config to `approved` with real approval evidence; then the Round 3 feature PR selects the suite and the trusted evaluation is dispatched |

The only waiting point is merge order (stage 2). A suite unit and the feature it evaluates stay in separate PRs, because the trusted workflow reads config and runner only from the default branch.

Excluded to control effort: shared scorer library, LLM-judge framework, automatic path-to-suite mapping, multi-suite single dispatch, per-suite secrets.

## 4. Exact files

Implementation checkpoint (after approval):

| File | Change |
|---|---|
| `docs/ci/semantic-suites.yaml` | Add registry with the single `financial-metrics` entry |
| `docs/ci/semantic_eval.yaml` | **Unchanged** (verified byte-identical by test) |
| `scripts/ci_checks.py` | `load_suite_registry`, `parse_suite_selection`, `verify_suite_selection`, per-suite `verify_evidence` path, PR fetch, CLI args `--registry --trusted-root --pr`; keep `--semantic-config` accepted only for the non-enforced path during bootstrap, then unused |
| `scripts/ci_semantic_eval.py` | `--registry/--suite`, config hash, record fields, `needs_review` preservation, legacy semantic-mode rejection |
| `.github/workflows/trusted-evaluation.yml` | `suite_id` input, drop `semantic_runner`, env-passed inputs, per-suite context/artifact/concurrency names |
| `.github/workflows/ci.yml` | `evidence-check` only: default-branch checkout, permissions, new args |
| `test/offline/test_ci_gates.py` | New tests §5 (including the T18 contract conformance check); adapt existing evidence/workflow tests to suite contexts (no assertion weakened: every old negative keeps a suite-scoped equivalent) |
| `docs/ci/README.md`, `CI.md` (§3 diagram, §4.4) | Operator instructions, field/phrase format, status names, migration note |
| `docs/ai-use-log.yaml`, `docs/review-memo.md` | Actual AI-use and per-PR review record |
| `docs/plans/semantic-suite-routing.md` | Freeze at the approved commit and keep byte-identical after approval. Record approval, implementation and verification events in the PR, AI-use log and review memo. A material specification revision needs a new fixed version and approval. |

Not changed: `src/**`, `scripts/financial_metrics_eval.py`, FR-10 dataset/rubric/config, `test/offline/test_financial_metrics_evaluation.py`, classifier detection rules, aggregate logic, `.opencode/**`, requirements and D2 documents.

This plan checkpoint changes only `docs/plans/semantic-suite-routing.md` and `docs/ai-use-log.yaml`.

## 5. Offline tests (approved test paths: `test/offline/test_ci_gates.py`, regression `test/offline/test_financial_metrics_evaluation.py`)

All use fixtures (statuses, runs, records, approval events, temporary registries); no network, no model call. Expected values are written in the tests, not produced by the code under test.

| ID | Scenario | Expected |
|---|---|---|
| T01 | single suite `financial-metrics` selected + approved selection + approved trusted config + passing matching record | `errors == []` |
| T02 | `data-availability` selected; only `semantic-eval/financial-metrics` passes | block: missing `semantic-eval/data-availability`; financial pass does not substitute |
| T03 | two suites selected; one passes, one has no status → block naming the missing one; both pass → `[]` | as stated |
| T04 | `semantic_required`, field absent; also field empty | block "no semantic suite was selected" |
| T05 | unknown suite ID selected | block "unknown semantic suite" before any status lookup |
| T06 | selected suite with unapproved trusted config but a passing status | block "configuration ... is unapproved" |
| T07 | selection approval: no URL; author self-approval; bot; zero or two phrase lines; phrase list ≠ body list; `none` mixed with IDs | each blocks with its reason; list order/case/whitespace differences are accepted |
| T08 | record mismatch: other `suite_id`; stale `config_sha256`; other candidate; `status: failed`; untrusted run path/branch/event | each blocks |
| T09 | record `status: needs_review` with two items | block; error contains both items; commit-status description builder reports `needs_review: 2 pending items` |
| T10 | `none` + verified noop → `[]`; `none` without noop → block; suites listed + noop only → block | as stated |
| T11 | only legacy `semantic-eval/evidence` passing | block (legacy context not accepted) |
| T12 | not semantic_required, field absent: no suite checks, no PR/registry fetch performed (fetch stub asserts not called); existing docs-only/live tests unchanged | `[]` |
| T13 | registry validation: bad/reserved/duplicate ID, config outside `docs/ci/` or missing, config shared by two suites, runner not in `scripts/`, runner ≠ config `execution.runner`, unknown key | each rejected |
| T14 | `ci_semantic_eval.py`: unknown `--suite` exits non-zero before importing any runner (import stub); unapproved config blocked; approved fixture config + stub runner → record has `suite_id`, `config_path`, LF `config_sha256` (CRLF copy hashes equal), `runner`; stub `needs_review` result → record `status: needs_review` with items, exit non-zero; legacy `--runner` semantic mode rejected; `--not-applicable` path unchanged | as stated |
| T15 | workflow structure (YAML parse): trusted workflow has `suite_id`, no `semantic_runner`; no `${{ inputs.* }}` inside `run:`; context and artifact names include the suite; `DEEPSEEK_API_KEY` only in trusted semantic/live steps; `ci.yml` evidence-check checks out the default branch, has `pull-requests: read`, no secrets | as stated |
| T16 | migration: `docs/ci/semantic_eval.yaml` LF SHA-256 equals `20e15937…d9b7`; `status == unapproved`; registry maps `financial-metrics` → that file and `financial_metrics_eval:evaluate` | as stated |
| T17 | bootstrap: default branch without registry + not enforced → `[]`; + enforced → block "registry is not present" | as stated |

| T18 | suite contract conformance (§3.5): for every registry entry, the trusted config passes `validate_config()` structure checks and `execution.runner` equals the registry runner; the runner callable accepts `(config, candidate_sha, *, output_dir, model_transport=None)` (signature inspection, no execution); a fixture runner returning a mapping without `status`, with a status outside `passed/failed/needs_review`, or with non-list `needs_review` makes `ci_semantic_eval.py` record `failed` and exit non-zero | as stated |

Negative coverage: T02–T11, T13, T14, T17, T18. Regression: the full `test/offline/test_ci_gates.py` and `test/offline/test_financial_metrics_evaluation.py`, then default `pytest -q`.

## 6. Commands and verification

From the worktree root, existing isolated Python 3.12 CI environment (no installs):

1. `python -m pytest -q test/offline/test_ci_gates.py test/offline/test_financial_metrics_evaluation.py`
2. `python -m ruff check .`
3. `python -m mypy` per `mypy.ini`, compared with `mypy-baseline.txt` via `ci_checks.py` (no new diagnostics)
4. `python scripts/ci_checks.py classify --base origin/main --head HEAD` (expect `semantic_required: false`, governance/code paths, approval applicable)
5. `python -m pytest -q` (default offline suite; known Windows lock-test failures reported, not waived)
6. `git diff --check`

Temporary outputs only under the OS temp directory. Remote: push, PR CI on Ubuntu; evidence-check on this PR exercises the bootstrap row (main has no registry). No `trusted-evaluation` dispatch and no model call in this work.

## 7. Impact on in-flight work

| Work | Current state | After this lands |
|---|---|---|
| FR-10 (financial-metrics session) | PR #14 merged; config unapproved; next PR (src integration) will be `semantic_required` | Declares `Semantic suites: financial-metrics` + reviewer line. Blocked until that session approves `docs/ci/semantic_eval.yaml` on main (its own PR) and resolves the baseline-input gap in §2. Dispatch uses `suite_id=financial-metrics`. Config values/path unchanged, so no rebase conflict on the config. |
| FR-03 (Yifan, `round-03-fr03` @ `7bf46d1`) | Classifier reports `semantic_required: true` (research_manager, bull/bear researcher prompts). Under current rules it is blocked anyway (only config is FR-10, unapproved). | Builds its suite unit against §3.5 (I1–I6) in parallel with the framework track; merges it after the framework PR, then approves its config on main, then selects `data-availability` (or its confirmed ID) in the Round 3 PR and gets evidence. Or, if the reviewer judges the prompt edits non-semantic, `Semantic suites: none` + reviewed not-applicable. No code conflict with this PR (no shared files). |
| Shared summary (PR #15, `prep/shared-summary-integration` @ `7cc38da`) | Docs-only; plan §6D foresaw "conditional compatibility" edits to the CI scripts/workflow for config selection | Those CI edits become unnecessary: slice D adds `docs/ci/semantic-suites/shared-summary.yaml`, its runner, and one registry entry. Its new `run/summary.py` prompt-path detection remains that session's classifier change. |
| Any PR with a reviewed noop | `semantic-eval/not-applicable` alone sufficed | Must also state `Semantic suites: none` with reviewer phrase. |
| Non-semantic PRs | — | Unchanged (§3.3 first row). |

Coordination: this PR touches `scripts/ci_checks.py`, `scripts/ci_semantic_eval.py`, both workflows, `test/offline/test_ci_gates.py`, `docs/ci/README.md`, `CI.md`. Other sessions should avoid those files until it merges, or rebase after.

## 8. Implementation and verification order

1. Human approves this plan at its commit (§10). Keep the approved plan byte-identical; record the actual approval reference and subsequent implementation events in the PR, AI-use log and review memo.
2. Tests first: add T01–T18 and adapt existing evidence tests; confirm the new ones fail against current code (record counts).
3. `scripts/ci_checks.py` registry + selection + per-suite evidence; then `scripts/ci_semantic_eval.py`.
4. Registry file; workflows (`trusted-evaluation.yml`, then `ci.yml` evidence-check).
5. Docs (`docs/ci/README.md`, `CI.md`), AI-use log, review memo.
6. Local verification §6; push; Draft → Ready only after remote PR CI result is inspected; report and stop for human review. No merge by the agent.

## 9. Prerequisites and risks

- Confirmed: base SHA; existing protected environment and secret names (from workflow text; remote settings not verified here); FR-10 config is unapproved.
- Unverified remote facts: branch protection, required checks, environment reviewers. Workflow text does not prove them.
- Residual risk: checker code runs from the candidate (unchanged). A human can approve a wrong selection; CI only checks it is explicit, attributable and consistent.
- Suite-specific secrets, automatic path→suite mapping, and multi-suite single dispatch are excluded.

## 10. Approval basis

- Plan/test-spec approval: **pending.** Expected phrase, exactly one line, by a non-author human on this PR:
  `APPROVED test-spec: docs/plans/semantic-suite-routing.md @ <full commit SHA of this plan>`
- Approved scope (for the implementation PR's `Approved scope` field): CI maintenance per §3–§5; IDs touched in changed lines: `FR-10` (registry traceability only).
- Implementation start: not started.
