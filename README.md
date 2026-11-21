# Teamproject-TradingAgents

This repository is a CS5351 project based on
[TradingAgents](https://github.com/TauricResearch/TradingAgents) v0.7.0.
The application source now lives under `src/`; there is no `TradingAgents/`
wrapper directory.

## Layout

```text
src/tradingagents/     application package
src/cli/               CLI package used by the `tradingagents` command
test/offline/          deterministic tests; network access is blocked
test/live/             tests that require a real external service
test/conftest.py       shared isolation and network-blocking fixtures
docs/                  requirements, architecture, governance and QA records
scripts/               baseline and evidence helper scripts
baseline/              historical baseline evidence
transcripts/           raw session records
```

Keep `import tradingagents`, `import cli` and the
`tradingagents = "cli.main:app"` console entry point.

## Install

From the repository root, using the existing supported Python environment:

```bash
python -m pip install .
```

For development and tests:

```bash
python -m pip install -e ".[dev]"
```

The project uses a `src/` layout. Do not run tests by adding `src/` to
`PYTHONPATH`; install the project or use an editable install so package
discovery and the console entry point are tested normally.

## Run

```bash
tradingagents --help
tradingagents --ticker NVDA --date 2026-09-01
```

The CLI is the supported interactive/headless entry point. The programmatic
entry point remains:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph

graph = TradingAgentsGraph()
state, decision = graph.propagate("NVDA", "2026-09-01")
print(decision)
```

Configuration is read from the current working directory's `.env` and
`.env.enterprise` files (when present). See `.env.example` and
`.env.enterprise.example`; neither file contains real credentials.

## Tests

Offline regression is the default:

```bash
pytest -q
```

The default configuration excludes tests marked `integration` and the test
fixtures block network access. The optional live suite is provided but is not
run by default:

```bash
pytest -q -m integration
```

Live tests require the applicable provider credentials and an authorized
environment. A skipped, blocked, or unrun live test is not a pass.

Lint uses the repository Ruff configuration:

```bash
ruff check .
```

## CI gates

The CI design and gate-test specification is [`CI.md`](CI.md), with operation
details in [`docs/ci/README.md`](docs/ci/README.md). CI is split by event:

- `push` runs the basic checks (`classify`, `requirements-schema`, `static`,
  `type-check`, `dependency-check`, `regression`, `smoke-install`).
- `pull_request` additionally runs applicable test pre-approval, contract tests,
  security-path, AI-use-log, semantic-evidence, and `ci / aggregate` checks.
  Pure documentation and build configuration do not require test pre-approval.
- A push result cannot satisfy the PR-only `ci / aggregate` check.
- Semantic evidence for prompt/model changes is produced by the manually
  dispatched [`trusted-evaluation.yml`](.github/workflows/trusted-evaluation.yml)
  in the protected `trusted-evaluation` environment. Live execution is optional
  and is not a merge gate.

Local gate commands, from the project root:

```bash
python scripts/ci_checks.py schema \
  --requirements docs/req/requirements.yaml \
  --schema docs/req/req-schema.json
python scripts/ci_checks.py permissions --path .opencode/permissions.jsonc
python scripts/ci_checks.py api
python scripts/ci_checks.py mypy --output mypy-current.txt --baseline mypy-baseline.txt
pytest -q test/offline/test_ci_gates.py
ruff check .
```

The CI-only tools are pinned in `.github/requirements-ci.txt`. They do not
change application runtime dependencies.

Current known limits:

- The 16 pre-existing Ruff findings recorded earlier were historical; commit
  `b56da53` repaired them, and the current local `ruff check .` passes.
- The current local `test/offline/test_ci_gates.py` verification passed 61 cases,
  as recorded in `CI.md`; this is not GitHub remote validation.
- Three pre-existing Windows-only cache-lock test failures remain on this host.
- No semantic dataset/threshold/model configuration is approved, and branch
  protection is not verified.
- GitHub Actions, remote required checks, live execution, and Docker remain
  unverified. Live execution is optional. Required gates remain blocked until
  the applicable items are resolved.

## Docker

The optional container configuration is at the repository root:

```bash
cp .env.example .env
docker compose run --rm tradingagents
```

Rebuild after source changes with `docker compose build`. Results, reports,
the memory log and caches live in the `tradingagents_data` volume, or in the
host directory selected by `TRADINGAGENTS_DATA_DIR`.

## Upstream and migration

The upstream version, import commit, license and attribution are recorded in
[`UPSTREAM.md`](UPSTREAM.md) and [`LICENSE`](LICENSE).

The migration from the imported layout is:

| Former path | Current path |
|---|---|
| `TradingAgents/tradingagents/` | `src/tradingagents/` |
| `TradingAgents/cli/` | `src/cli/` |
| `TradingAgents/tests/` | `test/offline/` and `test/live/` |
| `TradingAgents/pyproject.toml` | `pyproject.toml` |
| `TradingAgents/requirements.txt` | `requirements.txt` |
| `TradingAgents/README.md` | `README.md` |
| `TradingAgents/LICENSE` | `LICENSE` |
| `TradingAgents/.github/workflows/ci.yml` | `.github/workflows/ci.yml` |

Historical `baseline/` and `transcripts/` references are preserved as evidence
and are not rewritten by this migration. The current requirements and
architecture documents retain their original requirement, FC, IR and ADR
semantics; only current layout and command paths are updated.

Migration verification details are in
[`docs/migration/migration-report.md`](docs/migration/migration-report.md).
