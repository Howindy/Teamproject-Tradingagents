# Baseline run baseline-20261020-01

## Verdict

- Main flow completed: yes
- Data coverage complete: no
- Metric evidence sufficient: yes for calls/tokens/errors; retries and structured fallback were observed as 0
- Reproducible: yes, with the recorded command and dependency-version caveat
- Source unchanged: yes
- Out-of-scope writes: none detected

A generated trading decision does not by itself make this baseline complete.

## Run identity

- Run id: `baseline-20261020-01`
- Commit: `cea61c5452b1f9b988e490b8de347aaba4874f36`
- Ticker: NVDA
- Analysis date: 2026-10-19
- Latest market bar: 2026-10-19 close 217.08999633789062
- Analysts: market, social, news, fundamentals
- Debate/risk rounds: 1 / 1
- Language: English
- Quick/deep model: CS5351/DeepSeek-V4-Flash / CS5351/DeepSeek-V4-Flash
- Provider/endpoint: openai_compatible / https://llm.cs.cityu.edu.hk/v1
- Python: /opt/miniconda3/envs/tradingagents/bin/python
- Module: /Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/TradingAgents/tradingagents/__init__.py
- Started/finished: 2026-10-20T19:28:54+08:00 / 2026-10-20T19:32:09+08:00
- Timezone: CST +0800

## Invocation

```text
zsh -c 'source ~/.zshrc && use_ta_cityu && cd /Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/TradingAgents && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" /opt/miniconda3/envs/tradingagents/bin/python -B ../scripts/run_baseline.py --run-id baseline-20261020-01 --ticker NVDA --date 2026-10-19 --analysts market,social,news,fundamentals --language English --debate-rounds 1 --risk-rounds 1'
```

- Working directory: `/Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/TradingAgents`
- stdout/stderr: separate: logs/stdout.log and logs/stderr.log

## Preflight

- Authoritative preflight: `baseline/preflight/preflight-20261020-02`
- Superseded preflight retained for audit: `baseline/preflight/preflight-20261020-01`
- Preflight status counts: {"success": 7, "unavailable": 2, "withheld": 2, "not_configured": 1}
- Source/outside/home integrity in preflight: True / True / True

## Execution

- Exit code: 0
- Inner elapsed (monotonic): 194.41s
- Total child elapsed (monotonic): 195.383s
- Final rating: Hold
- Complete report: `baseline/runs/baseline-20261020-01/results/reports/NVDA_20261020_193209/complete_report.md`
- Full state log: `baseline/runs/baseline-20261020-01/results/NVDA/TradingAgentsStrategy_logs/full_states_log_2026-10-19.json`
- Memory log: `baseline/runs/baseline-20261020-01/memory/trading_memory.md`
- Report consistency: decision=True, report_contains=True, rating=True, sections=12/12

## Data availability

- Status counts: {"success": 20, "withheld": 4, "not_configured": 6, "unavailable": 4}
- Per-call CSV: `baseline/runs/baseline-20261020-01/data-availability.csv`

| Tool | Source | Status | Calls | Records |
| --- | --- | --- | ---: | ---: |
| get_balance_sheet | SEC EDGAR, Yahoo Finance | success | 2 | 12 |
| get_cashflow | SEC EDGAR, Yahoo Finance | success | 2 | 8 |
| get_fundamentals | Yahoo Finance | withheld | 1 | 0 |
| get_global_news | Yahoo Finance | success | 3 | 65 |
| get_income_statement | SEC EDGAR, Yahoo Finance | success | 2 | 12 |
| get_indicators | Yahoo Finance | success | 8 | 168 |
| get_insider_transactions | Yahoo Finance | withheld | 1 | 0 |
| get_macro_indicators | FRED | not_configured | 6 | 0 |
| get_news | Yahoo Finance | unavailable | 2 | 0 |
| get_prediction_markets | Polymarket | withheld | 2 | 0 |
| get_stock_data | Yahoo Finance | success | 1 | 118 |
| get_verified_market_snapshot | Yahoo Finance | success | 1 | 30 |
| sentiment_news | Yahoo Finance (prefetch) | unavailable | 1 | 0 |
| sentiment_reddit | Reddit (prefetch) | success | 1 | 11 |
| sentiment_stocktwits | StockTwits (prefetch) | unavailable | 1 | 0 |

Missing or incomplete sources:

- get_fundamentals (Yahoo Finance): withheld — withheld by the application's historical-date policy `baseline/runs/baseline-20261020-01/transcripts/tool-outputs-clean/0013_get_fundamentals.txt`
- get_insider_transactions (Yahoo Finance): withheld — withheld by the application's historical-date policy `baseline/runs/baseline-20261020-01/transcripts/tool-outputs-clean/0018_get_insider_transactions.txt`
- get_macro_indicators (FRED): not_configured — required credential is not set; app degrades or skips this source `baseline/runs/baseline-20261020-01/transcripts/tool-outputs-clean/0025_get_macro_indicators.txt`
- get_prediction_markets (Polymarket): withheld — withheld by the application's historical-date policy `baseline/runs/baseline-20261020-01/transcripts/tool-outputs-clean/0029_get_prediction_markets.txt`
- get_news (Yahoo Finance): unavailable — <Yahoo Finance news unavailable for 2026-10-12..2026-10-19: Yahoo search returns only a sample of recent articles about NVDA, so this is not an absence of news for NVDA> `baseline/runs/baseline-20261020-01/transcripts/tool-outputs-clean/0039_get_news.txt`
- sentiment_news (Yahoo Finance (prefetch)): unavailable — <Yahoo Finance news unavailable for 2026-10-12..2026-10-19: Yahoo search returns only a sample of recent articles about NVDA, so this is not an absence of news for NVDA> `baseline/runs/baseline-20261020-01/transcripts/prefetch/001_sentiment_news.txt`
- sentiment_stocktwits (StockTwits (prefetch)): unavailable — <stocktwits unavailable: HTTPError> `baseline/runs/baseline-20261020-01/transcripts/prefetch/002_sentiment_stocktwits.txt`

Sentiment prefetch raw blocks are saved under `transcripts/prefetch/`; they are not model outputs.

## Metrics

- LLM calls: 19
- Tool calls: 31
- Input/output tokens: 156541 / 27639
- LLM usage missing: 0
- Retry events: 0
- LLM/tool errors: 0 / 0
- Structured fallback warnings: 0
- Message/tool log lines: 80
- Monetary cost: None (no CityU per-token price was provided; token counts are the available cost proxy)
- Measurement scope: inner: run_analysis wall-clock, monotonic; total: child process wall-clock, monotonic

## Reproducibility

- Exact invocation is above; `reproduce.sh` is included and requires a new run-id.
- Commit: `cea61c5452b1f9b988e490b8de347aaba4874f36`.
- Python: /opt/miniconda3/envs/tradingagents/bin/python (3.12.14 | packaged by Anaconda, Inc. | (main, Aug 27 2026, 14:38:15) [Clang 20.1.8 ]).
- Source module: /Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/TradingAgents/tradingagents/__init__.py version 0.7.0.
- Installed `tradingagents` distribution: 0.4.0 (not the loaded source).
- Dependencies below pyproject minimum: langchain-core 1.6.3 < 1.6.5, langchain-anthropic 1.7.2 < 1.7.4, langchain-openai 1.6.2 < 1.6.6, langgraph 1.2.11 < 1.2.12, pandas 3.0.5 < 3.0.6

## Integrity

- TradingAgents source identical: True
- Outside-scope identical: True
- Home .tradingagents identical: True
- Git status entries outside scripts/baseline: none

## Limitations

- Yahoo ticker news was unavailable; the run used global Yahoo news instead.
- StockTwits returned HTTP 403; sentiment rests on 11 Reddit posts plus the news block (news unavailable).
- FRED_API_KEY was not set; all macro-data calls degraded to a not-configured sentinel.
- Polymarket odds, Yahoo company profile and Yahoo insider transactions were withheld because 2026-10-19 is historical.
- The reports acknowledge these gaps. Some qualitative background (for example sector description) may rely on model knowledge even where profile data was withheld; no numeric fabrication was observed in the checked outputs.
- Installed package versions below pyproject minima are a reproducibility caveat.
- Monetary cost is null because no CityU price schedule was provided.
- stdout/stderr were redirected, so the Rich Live progress screen is not replayed; final status lines, reports, and logs are present.
- The OpenCode export is a snapshot taken during the run; re-export after the session ends to include the final summary message.

## OpenCode session

- Export: `baseline/runs/baseline-20261020-01/transcripts/opencode-session.json`
- Re-export command: `opencode export ses_ea6f6f57affeIKSEf18KdNxecQ > baseline/runs/baseline-20261020-01/transcripts/opencode-session.json`

