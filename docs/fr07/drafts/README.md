# Unimplemented drafts

`passage_ranking_unimplemented.py` proposes an LLM passage-ranking interface
(`DownstreamBriefBuilder.candidates`) that was never implemented. It was moved
out of `TradingAgents/tests/` so the delivered branch's test collection does not
fail on an import of a method that does not exist. It is not part of FR-07 or
FR-08 and must not be run.

The delivered brief path is deterministic extraction (`tradingagents/run/brief.py`)
plus the optional one-call structured summary (`tradingagents/run/summary.py`).
