# Teamproject-TradingAgents

CS5351 project built on [TradingAgents](https://github.com/TauricResearch/TradingAgents) v0.7.0.
The application is a multi-agent LLM stock/crypto research pipeline whose final
recommendation is decided by a deterministic, model-free blocking gate.

Repository: <https://github.com/Howindy/Teamproject-Tradingagents>

## Blocking-gate design

The project uses two complementary gate layers: one at runtime for the trading
decision, and one in CI for changes to the repository.

### 1. Runtime decision gate (SB-01)

```text
Analysts -> Bull/Bear debate -> Research Manager -> Trader
         -> Portfolio Manager (advisory model_proposal only)
         -> Portfolio Risk Check (deterministic, FR-04)
         -> Final Recommendation Check (deterministic, SB-01)
         -> END
```

The model may propose a rating and conclusion, but it cannot decide the formal
result. `FinalRecommendationChecker` is the sole formal authority and writes
`gate_status`, `reasons`, `final_rating`, and `final_trade_decision`. It is pure:
no model call, network call, storage access, or risk re-computation.

Gate rules:

- `model_proposal` must be a mapping containing a legal five-tier rating
  (`Buy`, `Overweight`, `Hold`, `Underweight`, `Sell`) and a non-blank text.
- Data availability must be a valid summary; an incomplete summary blocks.
- For an applicable stock `Buy`/`Overweight`, the FR-04 portfolio-risk result
  must be `passed`. The risk check compares exact rational values against the
  projected-weight and stop-distance limits; it never uses model text.
- On success the formal rating is the validated five-tier proposal. On any
  blocked condition or unexpected gate exception the result is `blocked` or
  `error`, the rating is `REVIEW`, and a program-generated manual-review notice
  is returned. A failed gate never produces a tradeable rating.
- Downstream entries, reports, final state, and memory consume the same formal
  fields unchanged. They may copy or persist them but must not re-parse model
  prose, re-compute risk, or invent `REVIEW`. The shared
  `validate_formal_result()` check rejects incomplete or inconsistent formal
  output as a contract failure rather than silently repairing it.

Key files: [`final_recommendation.py`](src/tradingagents/final_recommendation.py),
[`portfolio_risk.py`](src/tradingagents/portfolio_risk.py),
[`setup.py`](src/tradingagents/graph/setup.py), and the tests
[`test_sb01_final_check.py`](test/offline/test_sb01_final_check.py) /
[`test_fr04_risk.py`](test/offline/test_fr04_risk.py). Design authority:
[`architecture-blueprint.md`](architecture-blueprint.md), ADR
[`001-graph-internal-final-check.md`](docs/architecture/adr/001-graph-internal-final-check.md),
and [`invariants.md`](docs/architecture/invariants.md).

### 2. CI blocking gates (D7)

`push` runs the baseline gates:

- `classify` — separates documentation/build-only changes;
- `requirements-schema` — validates `docs/req/requirements.yaml` against
  `docs/req/req-schema.json`;
- `static` — `ruff check .`;
- `type-check` — mypy against an exact existing-diagnostic baseline;
- `dependency-check` — `pip check` and import smoke check;
- `regression` — offline pytest matrix;
- `smoke-install` — clean-install import check.

`pull_request` adds the change-control gates:

- test pre-approval bound to an exact approved test specification, approval
  event, and implementation-start commit;
- contract and security-path checks, including permission/API/ADR checks;
- AI-use-log update for code or runtime-prompt changes;
- trusted semantic evidence for prompt/model changes;
- a single required `ci / aggregate` check.

Prompt/model evaluation runs only through the manually dispatched
`trusted-evaluation.yml` from the default branch in the protected
`trusted-evaluation` environment; ordinary CI receives no model/data secrets.
Local workflow files cannot prove that GitHub required checks or branch
protection are enabled. See [`CI.md`](CI.md) and
[`docs/ci/README.md`](docs/ci/README.md).

## File map

```text
src/tradingagents/          application package
  agents/                   analysts, Bull/Bear, managers, risk debate, trader,
                            state/schemas, rating and structured-output helpers
  graph/                    LangGraph wiring, propagation, conditional logic,
                            checkpointer, analyst execution, TradingAgentsGraph
  dataflows/                router, config, net/files/symbols, availability
                            tracking, vendor adapters (Yahoo, Alpha Vantage,
                            SEC, FRED, Reddit, StockTwits, Polymarket)
  llm_clients/              provider clients, model catalog, capabilities
  financials/               FR-10 deterministic disclosed-metrics pipeline
  memory/                   decision log, settlement, reflection
  portfolio.py              caller-portfolio context
  portfolio_risk.py         FR-04 pure risk evaluator
  final_recommendation.py   SB-01 blocking gate and formal-result validation
  run_context.py            per-run, context-local scope (never in graph state)
  reporting.py              shared Markdown report tree writer
  report_html.py            self-contained HTML report renderer
  backtest.py               multi-ticker/date backtest runner
  default_config.py         defaults and environment overrides
src/cli/                    Typer CLI, live display, prompts, preferences
test/offline/               deterministic tests; network blocked
test/live/                  tests requiring real external services
test/conftest.py            shared isolation/network-blocking fixtures
scripts/                    baseline, data probing, evidence and CI gate scripts
docs/req/                   D1 requirements and schema
docs/architecture/          blueprint pointer, ADRs, invariants, trace matrix,
                            memory/permission/evaluation designs
docs/code-governance/       structural, verification and tool-manifest rules
docs/ci/                    CI operation notes, semantic suites, rubrics, cases
docs/plans/                 per-round plans and approval records
docs/migration/             import/migration evidence
baseline/                   historical baseline run evidence
transcripts/                raw session records (evidence, not application code)
.github/workflows/          push/PR gates and trusted evaluation workflow
.agent/ .opencode/          agent rules and permission configuration
pyproject.toml requirements.txt   packaging metadata, dependencies, test/lint config
mypy.ini mypy-baseline.txt        type-check scope and accepted diagnostic baseline
Dockerfile docker-compose.yml     optional containerized run
architecture-blueprint.md   authoritative D2 architecture document
AGENTS.md Prompt.md goal.md entry instructions, reading order and workflow
CI.md UPSTREAM.md           CI gate specification and upstream attribution
```

## Setup

```bash
python -m pip install -e ".[dev]"
cp .env.example .env      # then fill in the provider key you use
```

Configuration is read from `.env` and `.env.enterprise` in the working
directory. See [`.env.example`](.env.example) for supported providers.

## Run

```bash
tradingagents --help
tradingagents --ticker NVDA --date 2026-09-01
tradingagents --ticker NVDA --date 2026-09-01 --purchase-scenario scenario.json
```

`scenario.json` supplies the optional FR-04 purchase scenario (portfolio value,
current position, proposed buy, entry/stop prices, optional limits).

Programmatic entry:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph

graph = TradingAgentsGraph()
state, decision = graph.propagate("NVDA", "2026-09-01")
print(state["gate_status"], state["final_rating"], decision)
```

## Tests

```bash
pytest -q                  # offline default; integration excluded
pytest -q -m integration   # live suite; needs credentials and authorization
ruff check .
```

The fixtures block network access offline. A skipped, blocked, or unrun live
test is not a pass.

## More documentation

- [Requirements](docs/req/requirements.yaml) · [Architecture blueprint](architecture-blueprint.md)
- [Trace matrix](docs/architecture/trace-matrix.md) · [Verification constraints](docs/code-governance/verification-constraints.md)
- [Migration report](docs/migration/migration-report.md) · [Upstream](UPSTREAM.md) · [License](LICENSE)
