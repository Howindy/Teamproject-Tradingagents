# ADR 003 — Context supplied to each LLM turn

Status: records the implemented role-local design in ADR 001 D-10c and ADR 002 D-203. Scope: model requests during an analysis.

## Decision and rationale

The graph selects a role and its node assembles the request from the current state. The design retained the existing role templates after comparing full reports with downstream briefs and a shared context assembler. Researchers need the original reports and the same research-start availability snapshot. The fundamentals analyst needs period-specific numbers before its first call. Supplying evidence at those two points preserves the existing tool protocol and model call count. Downstream briefs remain deferred under FR-07.

| Turn | Identity, standing instructions and current task | Evidence, history and state |
|---|---|---|
| Tool-using analyst | Analyst role, instrument, analysis date, language instruction and report task in the role prompt | Prior messages and tool results. Fundamentals includes the optional FR-10 table, preserving periods, units and unavailable reasons across tool turns. |
| Sentiment analyst | Instrument-specific sentiment report task | Prefetched news and social results are supplied to the role. |
| Bull, Bear and Research Manager | Argue the assigned side or adjudicate the debate | Researchers receive full reports and debate history. The manager receives the debate. All three receive the FR-03 summary fixed at research start. |
| Trader and risk debaters | Build a trade plan or challenge it from the assigned risk perspective | The trader receives portfolio context and the investment plan. Risk debaters receive reports, the trade plan and risk discussion history. |
| Portfolio Manager | Produce the advisory proposal | Portfolio context, research and trader plans, risk debate and selected past lessons. FR-04 and SB-01 run in code after this turn. |

## Assembly, limits and interruption

Each node selects its own state fields and renders the role instructions and current task. Tool analysts bind the allowed tools and append message history in order. At the tool-round limit, the wrap-up turn removes tool bindings and renders earlier calls and replies as text. The amounts and provenance of FR-10 evidence are reused from the analysis-local resolver. FR-03 research turns read the stored stage snapshot. These choices preserve evidence across turns without global deduplication or relevance ranking.

The application has no global input-token cap, compaction threshold or automatic history compression. The optional provider output limit defaults to unset. The default tool-round limit is 20 and measures tool iterations. There is no post-compaction reinjection step. Role instructions and applicable evidence are supplied during ordinary prompt assembly. Long requests follow the existing provider error path. Each new public analysis starts fresh. Persisted decisions or reflections may supply selected lessons to a later analysis.

## Consequences and reopening conditions

Full histories can exceed a provider context window. A requirement for bounded input size, resumable model conversations or downstream briefs would reopen D-10c and require a decision on evidence retention and instruction reinjection. The present architecture defines no numeric compression threshold.

Implementation references: [analyst turn](../../../src/tradingagents/agents/analysts/turn.py), [fundamentals prompt](../../../src/tradingagents/agents/analysts/fundamentals_analyst.py), [graph assembly](../../../src/tradingagents/graph/setup.py), [defaults](../../../src/tradingagents/default_config.py) and [client options](../../../src/tradingagents/llm_clients/factory.py).
