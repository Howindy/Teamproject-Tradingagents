# Upstream Source

This CS5351 student project is based on TradingAgents.

- Original repository: https://github.com/TauricResearch/TradingAgents
- Imported version: v0.7.0
- Imported commit: e8f5503e9b86d5c2710b0c76b1f686703968c9df
- License: Apache License 2.0; see LICENSE.

Original code remains attributed to its respective authors.
Subsequent student modifications will be identified in modified files
and recorded in this repository's commit history.

## Current layout migration

The imported `TradingAgents/` wrapper was removed after the source and tests
were moved to the course layout:

- `TradingAgents/tradingagents/` -> `src/tradingagents/`
- `TradingAgents/cli/` -> `src/cli/`
- `TradingAgents/tests/` -> `test/offline/` and `test/live/`
- `TradingAgents/pyproject.toml` -> `pyproject.toml`
- `TradingAgents/.github/workflows/ci.yml` -> `.github/workflows/ci.yml`

Historical references under `baseline/`, `transcripts/`, and the historical
AI-use log entries keep their original paths. `docs/req/requirements.yaml`
source-evidence locators remain historical migration-era evidence and are not
rewritten by this layout change.
