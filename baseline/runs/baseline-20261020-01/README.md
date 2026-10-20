# baseline-20261020-01

Single TradingAgents baseline run. The application source was not modified.

- Commit: `cea61c5452b1f9b988e490b8de347aaba4874f36`
- Analysis date: 2026-10-19
- Exit code: 0
- Main flow completed: yes
- Data coverage complete: no

## Reproduce

```text
zsh -c 'source ~/.zshrc && use_ta_cityu && cd /Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/TradingAgents && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" /opt/miniconda3/envs/tradingagents/bin/python -B ../scripts/run_baseline.py --run-id baseline-20261020-01 --ticker NVDA --date 2026-10-19 --analysts market,social,news,fundamentals --language English --debate-rounds 1 --risk-rounds 1'
```

`reproduce.sh` is included; it requires a new run-id.

## Layout

- `logs/`: stdout, stderr, exit code, module check, application warnings.
- `results/`: application reports, full state log, message/tool log.
- `cache/`: run-local cache (started empty).
- `memory/`: run-local memory log (started empty).
- `transcripts/`: final state, tool events, clean tool outputs, raw sentiment prefetch, OpenCode session export.
- `tmp/`: redirected HOME/XDG/TMPDIR.
- `source-*.json`, `outside-*.json`, `home-tradingagents-*.json`: integrity evidence.
- `metrics.json`, `data-availability.csv`, `report-consistency.json`, `summary.md`, `environment.json`.

## Notes

- stdout and stderr are separate files.
- The tool evidence is stored raw and clean; `data-availability.csv` points at the clean content.
- A generated Hold decision does not mean the baseline is complete in data terms.
