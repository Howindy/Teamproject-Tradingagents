#!/bin/zsh
set -euo pipefail
source ~/.zshrc
use_ta_cityu
cd /Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/TradingAgents
RUN_ID="${1:-baseline-20261020-01-repro}"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" /opt/miniconda3/envs/tradingagents/bin/python -B \
  ../scripts/run_baseline.py \
  --run-id "$RUN_ID" --ticker NVDA --date 2026-10-19 \
  --analysts market,social,news,fundamentals --language English \
  --debate-rounds 1 --risk-rounds 1
