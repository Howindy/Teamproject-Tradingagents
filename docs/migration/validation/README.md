# Migration Validation Evidence

This directory contains selected, non-secret validation evidence from the
`TradingAgents/` -> `src/` / `test/` migration.

## Prior execution

Files named `prior-*` were copied from the migration working evidence directory
and preserve their original execution time:

`/var/folders/16/vlln_1rs23j4vw_lyshq37pc0000gn/T/opencode/migration-20261118`

They are prior evidence, not reruns from the finalization pass. The copied files
are text logs only; virtual environments, build caches, binary artifacts and
the rest of the temporary directory were not copied.

## Current execution

Files named `current-*` were produced during the finalization verification on
2026-11-18. They use the same isolated editable install and existing dependency
environment without upgrading or downloading dependencies.

Environment:

- Application dependencies: `/opt/miniconda3/envs/tradingagents` (Python 3.12.14)
- Pytest runner: `/opt/miniconda3/envs/vhis` (pytest 9.1.1)
- Isolated project editable environment:
  `/var/folders/16/vlln_1rs23j4vw_lyshq37pc0000gn/T/opencode/migration-20261118/editable-venv`

No available environment contained both the application dependencies and
pytest. Pytest was exposed from the existing `vhis` environment for the test
run; project imports came from the installed editable package, not from adding
`src/` to `PYTHONPATH`. Packaging was independently verified by building,
installing and importing the non-editable wheel from outside the repository.

## Evidence files

- `prior-*`: migration-start and prior migration results.
- `current-pytest-offline.txt`: current offline pytest run.
- `current-collect-offline.txt`: current offline collection.
- `current-collect-live.txt`: current live collection; no live call.
- `current-collection-compare.txt`: normalized node comparison.
- `current-test-structure.txt`: test function/assert counts.
- `current-integrity.txt`: source, CLI, resource and test integrity.
- `current-import-editable.txt`: editable import path.
- `current-import-wheel.txt`: non-editable wheel import and resource checks.
- `current-cli-help-*.txt`: CLI entry points after installation.
- `current-build.txt`, `current-wheel-list.txt`, `current-sdist-list.txt`:
  packaging evidence.
- `current-pip-check-*.txt`: existing dependency-version drift.
- `current-ruff.txt`: Ruff availability check; Ruff was not available.
- `current-ci-static.txt`, `current-docker-static.txt`: static checks only.
- `current-summary.txt`: consolidated results and limitations.

No credentials, API responses, transcripts, virtual environments, build caches
or complete historical evidence are included.
