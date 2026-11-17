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
