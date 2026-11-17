# TradingAgents Layout Migration Report

- Date: 2026-11-18
- Scope: finalization and verification of the completed `TradingAgents/` ->
  `src/` / `test/` migration.
- Status: source migration complete; packaging and core behavior verified;
  overall finalization still has pending permission, lint, CI, Docker, and live
  verification items listed below.
- No application algorithm, runtime prompt, model-default configuration, safety
  boundary, or test assertion was changed during this finalization.
- No Git stage, commit, push, pull request, remote workflow, or GitHub setting
  change was performed.

## 1. Migration result

```text
src/tradingagents/    84 files
src/cli/              11 files
test/conftest.py      shared fixtures
test/offline/         87 test modules
test/live/            1 live test module
```

`TradingAgents/` is absent. The package names, internal package structure,
`import tradingagents`, `import cli`, and the
`tradingagents = "cli.main:app"` console entry remain unchanged.

## 2. Completeness method

The migration-start worktree was recorded before moving files. Git HEAD alone
was not used as the content baseline.

Evidence:

- `docs/migration/file-map.tsv`: per-file old path, new path, change type,
  original size and SHA-256.
- `docs/migration/validation/prior-git-status-before.txt`: pre-migration
  worktree status.
- `docs/migration/validation/prior-manifest-before.tsv`: prior manifest copy.
- `docs/migration/validation/current-integrity.txt`: current comparison.

Existing uncommitted work was not overwritten. The pre-existing deletion of
`D2.md` and other pre-existing worktree changes remain outside this migration's
edits.

### Source and resource integrity

- `src/tradingagents/**`: 84/84 files identical to the migration-start content.
- `src/cli/**`: 11/11 files identical.
- `src/tradingagents/assets/tauric-logo.svg`: identical.
- `src/cli/static/welcome.txt`: identical.
- All provider, vendor, application and CLI modules remain present.
- No test file was removed to hide a regression.

### Test integrity

- Test functions: 982 before, 982 after.
- Assert nodes: 1399 before, 1399 after.
- 82 migrated test files and `conftest.py` remain byte-identical.
- Four test files have path-only/docstring changes:
  - `test_version.py`
  - `test_layering.py`
  - `test_i18n_coverage.py`
  - `test_structured_agents.py`
- `test_deepseek_reasoning.py` was split into:
  - `test/offline/test_deepseek_reasoning.py`
  - `test/live/test_deepseek_live_structured_output.py`
- The live split preserves the class, helper, `integration` marker, skip
  condition and assertion. No live API call was made.

## 3. Collection and regression

| Check | Result |
|---|---|
| Offline collection before | 1362 collected, 1 deselected |
| Offline collection current | 1362 collected, 1 deselected |
| Normalized offline node set | identical; no missing or extra nodes |
| Live collection before | 1 test |
| Live collection current | 1 test |
| Offline pytest before | 1358 passed, 3 failed, 1 skipped, 1 deselected, 100 subtests passed |
| Offline pytest current | 1358 passed, 3 failed, 1 skipped, 1 deselected, 100 subtests passed |

The three failures are unchanged Windows-specific tests in
`test/offline/test_cache_writes.py`:

- `test_on_windows_the_lock_is_waited_for_while_another_writer_holds_it`
- `test_on_windows_a_lock_that_cannot_be_taken_is_reported_not_retried_forever`
- `test_on_windows_a_held_lock_is_reported_when_not_waiting`

They existed before migration and are retained without skip or assertion
changes. The one skip is `test_construction_when_extra_installed` because
`langchain_aws` is not installed. The skip and the unrun live test are not
passes.

Evidence:

- `validation/current-collect-offline.txt`
- `validation/current-collect-live.txt`
- `validation/current-collection-compare.txt`
- `validation/current-test-structure.txt`
- `validation/current-pytest-offline.txt`
- `validation/prior-pytest-before.txt`
- `validation/prior-pytest-after.txt`

## 4. Packaging and installation

Editable installation succeeded with `--no-deps --no-build-isolation` and
`PIP_NO_INDEX=1`. Import from outside the repository resolved to:

`src/tradingagents/__init__.py`

No available environment contained both the application dependencies and
pytest. The test process used the existing pytest 9.1.1 runner from the `vhis`
environment; the project itself was imported from the isolated editable
installation, not from a `src/` PYTHONPATH entry. Packaging was independently
checked with a non-editable wheel installed into a separate environment.

CLI help passed from both:

- `python -m cli.main --help`
- the installed `tradingagents --help` console script

A wheel and sdist were built with `python -m build --no-isolation`. The wheel
was installed into a separate non-editable environment and imported from
`/tmp`, resolving to that environment's `site-packages`, not the source tree.

Wheel checks:

- contains `tradingagents/...` and `cli/...`;
- no `src/` prefix;
- contains `tradingagents/assets/tauric-logo.svg`;
- contains `cli/static/welcome.txt`;
- resource reads returned True for both.

Sdist contains `src/tradingagents/...`, `src/cli/...`, `pyproject.toml`,
`README.md` and `LICENSE`; it does not include `baseline/`, `transcripts/` or
`docs/`.

Evidence:

- `validation/current-import-editable.txt`
- `validation/current-import-wheel.txt`
- `validation/current-cli-help-editable.txt`
- `validation/current-cli-help-console.txt`
- `validation/current-cli-help-wheel.txt`
- `validation/current-build.txt`
- `validation/current-wheel-list.txt`
- `validation/current-sdist-list.txt`
- `validation/current-wheel-install.txt`
- `validation/prior-build.txt`
- `validation/prior-wheel-install.txt`

## 5. Dependency and lint status

`pip check` after installing the project reports existing environment versions
below the declared minimums:

- `langchain-anthropic 1.7.2 < 1.7.4`
- `langchain-core 1.6.3 < 1.6.5`
- `langchain-openai 1.6.2 < 1.6.6`
- `langgraph 1.2.11 < 1.2.12`
- `pandas 3.0.5 < 3.0.6`

This is existing environment drift, not a migration-induced version change.
`pyproject.toml` minimums were not lowered and no dependency was upgraded or
downloaded.

Ruff was not available locally:

- no `ruff` executable on `PATH`;
- no `ruff` Python module in the checked environments;
- no local cache/tool copy found.

Ruff was therefore not run. The CI workflow installs `ruff>=0.16`, but no local
installation was attempted. Human authorization would be required to install a
compatible Ruff version for local lint verification.

Evidence:

- `validation/current-pip-check-editable.txt`
- `validation/current-pip-check-wheel.txt`
- `validation/current-ruff.txt`
- `validation/current-summary.txt`

## 6. CI and Docker static status

The root `.github/workflows/ci.yml` was statically checked:

- push and pull_request triggers;
- Python 3.11, 3.12, 3.13 and 3.14;
- 3.12 `America/New_York` timezone run;
- editable install with dev extras;
- `pytest -q`;
- clean install plus `import tradingagents, cli.main`;
- `ruff check .` after installing `ruff>=0.16`.

This is baseline CI migration only. The six course CI gates are not
implemented, release assets are not migrated, and the workflow was not executed
on GitHub.

Docker was statically checked only:

- root build context;
- root `pyproject.toml` and `src/` included;
- tests, docs, baseline, transcripts, scripts and CI excluded from the image
  context by `.dockerignore`;
- `pip install .` uses the root project;
- compose `.env` and the `~/.tradingagents` data volume remain valid;
- entrypoint remains `tradingagents`.

No image was downloaded or built.

Evidence:

- `validation/current-ci-static.txt`
- `validation/current-docker-static.txt`

## 7. Current old-path residuals

- `README.md` and `UPSTREAM.md` contain intentional old-to-new mapping text.
- Product URLs and User-Agent strings contain the upstream project name, not
  local paths.
- `docs/req/requirements.yaml` retains historical source-evidence locators by
  instruction.
- `baseline/`, `transcripts/` and historical AI-use-log entries are untouched.
- `docs/architecture/permission-model.md` and `.opencode/permissions.jsonc`
  still contain old paths and are human-maintained. See
  `docs/migration/permission-path-changes.md`.
- No old-path references remain in `src/`, `test/`, root `pyproject.toml`, root
  CI workflow or current scripts, apart from product-name/URL strings.

## 8. Pending work and responsibility

| Item | Status | Responsibility |
|---|---|---|
| Human update of `.opencode/permissions.jsonc` | Pending | Human owner |
| Human update of `docs/architecture/permission-model.md` | Pending | Human owner |
| Ruff / local lint verification | Not run; tool unavailable | Human decision/installation |
| Dependency version alignment | Existing drift; not changed | Human/dependency owner |
| CI on GitHub | Not run | Authorized GitHub operator |
| Docker image build | Not run | Authorized environment owner |
| Live API tests | Not run | Authorized live-test owner |
| Full course six-gate CI | Not implemented; out of scope | Separate approved CI governance work |
| FR-04 implementation/test approval | Not changed or approved | Separate round approval |

## 9. Conclusion

The source/test migration is complete and its package structure, core tests,
collection, installation, wheel/sdist packaging and resources have been
verified to the extent supported by the available environment.

Overall finalization is not complete while permission paths remain human-pending
and Ruff, GitHub CI, Docker and live verification are unrun.
