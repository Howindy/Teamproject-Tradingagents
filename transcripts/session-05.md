# TradingAgents baseline 运行前检查计划

**Session ID:** ses_ea6f8475cffenDuQuTG4wlbaJj
**Created:** 10/20/2026, 7:17:20 PM
**Updated:** 10/20/2026, 7:17:42 PM

---

## User

我想从当前版本的 TradingAgents 跑一次 baseline，作为后续项目改进的起点。这轮先验证原版能否跑通、数据覆盖情况和运行成本，不改应用功能。

项目根目录：
/Users/ichihann/Desktop/CS5351/Teamproject-tradingagents

请先检查环境和代码，给我一个简短的执行计划，等我确认后再开始正式运行或调用付费模型。

目录边界

TradingAgents/ 下所有文件必须保持不变，包括源码、配置、提示词、测试和依赖文件。也不要在里面生成 .env、日志、缓存、__pycache__、.pyc 或安装产物。

你为这次测试写的脚本统一放在：
/Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/scripts/

所有运行结果和中间文件统一放在：
/Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/baseline/

除了 scripts/ 和 baseline/，不要修改项目内其他位置，也不要改全局配置或提交、推送 Git。已有结果不要覆盖，每次运行用独立的 run-id。

API 和 Python 环境

CityU 配置在 ~/.zshrc 的 use_ta_cityu 函数里，需要先加载 ~/.zshrc，再调用 use_ta_cityu，然后在同一个 zsh 进程里启动测试，让 Python 继承环境变量。不要只在一个独立终端加载配置，再从另一个进程运行。

请先检查这个函数的配置逻辑和已有 Python 环境，但不要把函数全文或密钥打印出来。~/.zshrc 只读，不修改。

配置加载后，确认实际使用的：
- API endpoint；
- quick/deep 模型；
- Python 可执行文件和依赖；
- TradingAgents 模块的实际加载路径。

我希望 quick/deep 都使用 CS5351/DeepSeek-V4-Flash，API 使用现有 CityU 配置。不要擅自换服务或模型。凭据只记录是否已设置，不记录值，也不要用 set -x 或完整环境变量列表暴露密钥。

使用现有依赖，不自动安装或升级。如果缺依赖，先告诉我。

测试前的检查

当前预期 commit 是：
cea61c5452b1f9b988e490b8de347aaba4874f36

请核实实际 commit 和工作区状态。如果不同，先报告，不自动切换或清理。

给 TradingAgents/ 做一份运行前文件清单，包含隐藏文件、未跟踪文件和被忽略文件，记录内容哈希、符号链接和执行权限。运行后再比对，确认没有任何新增、删除或修改。

还要检查应用有哪些写入路径，把结果、缓存、memory、checkpoint 和临时文件全部通过现有配置重定向到 baseline/。如果 use_ta_cityu 设置了相关路径，在加载它之后覆盖成本次路径。

设置 PYTHONDONTWRITEBYTECODE=1，并用 python -B 运行，避免生成 Python 缓存。确保运行的是这个目录里的源码，而不是环境中另一份已安装版本。

本次运行场景

- 股票：NVDA
- 四类分析师全部启用：market、social、news、fundamentals
- 研究辩论 1 轮
- 风险讨论 1 轮
- 输出语言 English
- 完整分析先只跑一次，不因结果不好自动重跑

这次优先观察近期数据覆盖。请结合运行时的日期、时区、交易日和数据源能力，建议一个明确的分析日期，在计划里说明理由，等我确认后固定下来。

如果选当天，说明市场是否开盘、行情是否收盘，区分分析日期和最新可用行情日期。如果选历史日期，保留原有日期保护，不要为了获取更多数据绕过 withheld 规则。

正式运行前，安排少量不调用 LLM 的数据源检查，看看 Yahoo 行情和新闻、SEC EDGAR、StockTwits、Reddit、FRED、Polymarket 是否可用。探测结果单独存放，不要污染正式运行的缓存或 memory。

如果缺 FRED_API_KEY 等配置，在完整运行前告诉我，由我决定补配置还是接受缺失。对于 403、缺凭据或明确的历史数据限制，不要反复重试，也不要自动购买或切换服务。

运行和证据保存

可以按下面的结构组织，文件名有必要时可以调整，但请保持清楚：

scripts/
    run_baseline.py
    其他必要的采集或校验脚本

baseline/
    preflight/<check-id>/
    runs/<run-id>/
        README.md
        run-manifest.json
        environment.txt
        source-before.json
        source-after.json
        source-integrity.json
        data-availability.csv
        metrics.json
        summary.md
        logs/
        results/
        cache/
        memory/
        tmp/
        transcripts/

脚本应支持指定股票、分析日期和 run-id，遇到同名运行目录就拒绝覆盖。正式运行的 cache 和 memory 从空目录开始，不加载其他运行的记忆或 checkpoint。

请保存这些信息：

1. 复现说明：完整命令、工作目录、commit、Python 路径和版本、依赖版本、实际应用模块路径、模型和脱敏配置、分析日期、开始结束时间及其时区。

2. 完整 stdout/stderr、退出码，以及应用生成的报告、最终状态和工具日志。说明 stdout/stderr 是分开保存还是合并保存。

3. 数据可用性表：每类数据的工具、来源、请求窗口、返回状态、可核实的记录数、缺失原因和证据位置。区分获取失败、未配置、主动屏蔽、空结果和没有尝试。

情绪分析师内部预取的数据也要考虑进去。如果不改源码就无法保存社交数据原文，请如实说明，不要把模型报告当作原始取数证据。

4. 指标：用单调时钟测量总耗时，说明测量范围；保存能准确取得的 LLM 调用数、工具调用数、输入/输出 token、重试和回退次数。

拿不到的精确指标填 null 并说明原因。界面上的四舍五入数字可以作为估算单列，但不要当作精确最终结果。不要为了补指标修改应用源码。

5. 保存这次完整 OpenCode 会话，保留我的批准、纠偏及理由。如果你不能直接导出，就告诉我怎么从 OpenCode 导出，并指出应保存到哪个 transcripts/ 目录。不要用应用运行日志代替 OpenCode 会话，也不要事后编造原始记录。

结束后请检查

- 各阶段是否都有非空输出，主流程是否正常退出；
- 单独报告和最终状态是否一致；
- 哪些数据实际拿到了，哪些没有，为什么；
- 报告是否承认数据缺失；
- 有没有结构化输出回退、异常或进度显示问题；
- TradingAgents/ 的运行前后文件清单是否完全一致；
- scripts/ 和 baseline/ 之外是否出现了本轮新增或修改的文件。

如果发生越界写入，先停止并报告，不要用 git reset、git clean 或删除文件来掩盖问题。

最后在 summary.md 里分别说明：主流程是否完成、数据覆盖是否完整、指标证据是否充分、能否复现、源码是否保持不变，以及还存在什么限制。

不要只因为生成了最终交易建议就说 baseline 完整，也不要用模型知识补造缺失数据。

现在先做只读检查，告诉我准备怎样运行、选哪个分析日期、还缺什么配置，以及会写入哪些路径，等我确认。 

---

## Assistant (Build · CityU DeepSeek-V4-Flash · 3.8s)

I'll start by doing read-only checks on the environment and code. Let me explore the project structure first.






**Tool: bash**

**Input:**
```json
{
  "command": "cd /Users/ichihann/Desktop/CS5351/Teamproject-tradingagents && git rev-parse HEAD && echo \"---STATUS---\" && git status --short && echo \"---BRANCH---\" && git branch --show-current"
}
```

**Output:**
```
cea61c5452b1f9b988e490b8de347aaba4874f36
---STATUS---
---BRANCH---
main

```

**Tool: bash**

**Input:**
```json
{
  "command": "ls -la /Users/ichihann/Desktop/CS5351/Teamproject-tradingagents"
}
```

**Output:**
```
total 0
drwxr-xr-x   4 ichihann  staff  128 10月 20 19:10 .
drwxr-xr-x@ 26 ichihann  staff  832 10月 20 17:48 ..
drwxr-xr-x  14 ichihann  staff  448 10月 20 19:17 .git
drwxr-xr-x  20 ichihann  staff  640 10月 20 18:51 TradingAgents

```

**Tool: bash**

**Input:**
```json
{
  "command": "ls -la /Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/TradingAgents 2>/dev/null || echo \"NO TradingAgents dir\""
}
```

**Output:**
```
total 272
drwxr-xr-x  20 ichihann  staff    640 10月 20 18:51 .
drwxr-xr-x   4 ichihann  staff    128 10月 20 19:10 ..
-rw-r--r--   1 ichihann  staff    133 10月 20 14:24 .dockerignore
-rw-r--r--   1 ichihann  staff    203 10月 20 14:24 .env.enterprise.example
-rw-r--r--   1 ichihann  staff   3015 10月 20 14:24 .env.example
drwxr-xr-x   4 ichihann  staff    128 10月 20 14:25 .github
-rw-r--r--   1 ichihann  staff   4670 10月 20 14:24 .gitignore
drwxr-xr-x   9 ichihann  staff    288 10月 20 14:25 assets
-rw-r--r--   1 ichihann  staff  50340 10月 20 14:24 CHANGELOG.md
drwxr-xr-x  13 ichihann  staff    416 10月 20 19:16 cli
-rw-r--r--   1 ichihann  staff    726 10月 20 14:24 docker-compose.yml
-rw-r--r--   1 ichihann  staff    712 10月 20 14:24 Dockerfile
-rw-r--r--   1 ichihann  staff  11357 10月 20 14:24 LICENSE
-rw-r--r--   1 ichihann  staff    655 10月 20 14:24 main.py
-rw-r--r--   1 ichihann  staff   2477 10月 20 14:24 pyproject.toml
-rw-r--r--   1 ichihann  staff  27258 10月 20 14:24 README.md
-rw-r--r--   1 ichihann  staff    147 10月 20 14:24 requirements.txt
drwxr-xr-x  91 ichihann  staff   2912 10月 20 14:25 tests
drwxr-xr-x  14 ichihann  staff    448 10月 20 19:16 tradingagents
-rw-r--r--   1 ichihann  staff    458 10月 20 14:30 UPSTREAM.md

```

---

## Assistant (Build · CityU DeepSeek-V4-Flash · 4.0s)

Commit matches. Working tree clean. Let me explore the structure more, check the zshrc config logic, and understand the code.






**Tool: bash**

**Input:**
```json
{
  "command": "cd /Users/ichihann/Desktop/CS5351/Teamproject-tradingagents && ls -la TradingAgents/tradingagents && echo \"---CLI---\" && ls -la TradingAgents/cli && echo \"---MAIN---\" && cat TradingAgents/main.py"
}
```

**Output:**
```
total 112
-rw-r--r--   1 ichihann  staff    610 10月 20 14:24 __init__.py
drwxr-xr-x  14 ichihann  staff    448 10月 20 19:16 .
drwxr-xr-x  20 ichihann  staff    640 10月 20 18:51 ..
drwxr-xr-x  15 ichihann  staff    480 10月 20 19:16 agents
drwxr-xr-x   3 ichihann  staff     96 10月 20 14:25 assets
-rw-r--r--   1 ichihann  staff   9445 10月 20 14:24 backtest.py
drwxr-xr-x  11 ichihann  staff    352 10月 20 19:16 dataflows
-rw-r--r--   1 ichihann  staff  11200 10月 20 14:24 default_config.py
drwxr-xr-x   9 ichihann  staff    288 10月 20 19:16 graph
drwxr-xr-x  15 ichihann  staff    480 10月 20 19:16 llm_clients
drwxr-xr-x   6 ichihann  staff    192 10月 20 19:16 memory
-rw-r--r--   1 ichihann  staff   2979 10月 20 14:24 portfolio.py
-rw-r--r--   1 ichihann  staff  14821 10月 20 14:24 report_html.py
-rw-r--r--   1 ichihann  staff   5685 10月 20 14:24 reporting.py
---CLI---
total 264
-rw-r--r--   1 ichihann  staff      0 10月 20 14:24 __init__.py
drwxr-xr-x  13 ichihann  staff    416 10月 20 19:16 .
drwxr-xr-x  20 ichihann  staff    640 10月 20 18:51 ..
-rw-r--r--   1 ichihann  staff  23542 10月 20 14:24 display.py
-rw-r--r--   1 ichihann  staff   8780 10月 20 14:24 main.py
-rw-r--r--   1 ichihann  staff    359 10月 20 14:24 models.py
-rw-r--r--   1 ichihann  staff   4013 10月 20 14:24 prefs.py
-rw-r--r--   1 ichihann  staff  31060 10月 20 14:24 prompts.py
-rw-r--r--   1 ichihann  staff  22177 10月 20 14:24 run.py
-rw-r--r--   1 ichihann  staff  16289 10月 20 14:24 selections.py
drwxr-xr-x   3 ichihann  staff     96 10月 20 14:25 static
-rw-r--r--   1 ichihann  staff   2354 10月 20 14:24 stats_handler.py
-rw-r--r--   1 ichihann  staff   8855 10月 20 14:24 updates.py
---MAIN---
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

# DEFAULT_CONFIG already applies TRADINGAGENTS_* env-var overrides
# (llm_provider, deep_think_llm, quick_think_llm, backend_url, etc.),
# so users can switch models or endpoints purely via .env without
# editing this script. Override individual keys here only when you
# want a hard-coded value that should ignore the environment.
config = DEFAULT_CONFIG.copy()

# Initialize with custom config
ta = TradingAgentsGraph(debug=True, config=config)

# forward propagate
_, decision = ta.propagate("NVDA", "2026-09-01")
print(decision)

```

**Tool: bash**

**Input:**
```json
{
  "command": "grep -n \"use_ta_cityu\" ~/.zshrc"
}
```

**Output:**
```
33:use_ta_cityu() {

```

**Tool: bash**

**Input:**
```json
{
  "command": "cd /Users/ichihann/Desktop/CS5351/Teamproject-tradingagents && cat TradingAgents/requirements.txt && echo \"---PYPROJECT---\" && cat TradingAgents/pyproject.toml"
}
```

**Output:**
```
# The dependencies are declared in pyproject.toml. From the repository root this
# installs TradingAgents with them, the same as `pip install .`
.
---PYPROJECT---
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "tradingagents"
dynamic = ["version"]
description = "TradingAgents: Multi-Agents LLM Financial Trading Framework"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "cryptography>=42.0",
    "langchain-core>=1.6.5",
    "langchain-anthropic>=1.7.4",
    "langchain-google-genai>=4.4.0",
    "langchain-openai>=1.6.6",
    "langgraph>=1.2.12",
    "langgraph-checkpoint-sqlite>=3.1.1",
    "markdown-it-py>=4.0",
    "packaging>=24.0",
    "pandas>=3.0.6",
    "python-dotenv>=1.0.0",
    "pytz>=2025.2",
    "questionary>=2.1.0",
    "requests>=2.32.4",
    "rich>=14.0.0",
    "typer>=0.21.0",
    "stockstats>=0.6.5",
    "typing-extensions>=4.14.0",
    "yfinance>=1.7.0",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.16",
    "pytest>=8.0",
    "pytest-subtests>=0.13",
]
# Amazon Bedrock support (AWS SigV4 auth + boto3). Optional so the core install
# stays lean: pip install "tradingagents[bedrock]".
bedrock = [
    "langchain-aws>=1.7.9",
]

[project.scripts]
tradingagents = "cli.main:app"

[tool.setuptools.dynamic]
version = {attr = "tradingagents.__version__"}

[tool.setuptools.packages.find]
include = ["tradingagents*", "cli*"]

[tool.setuptools.package-data]
cli = ["static/*"]
tradingagents = ["assets/*.svg"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers -m \"not integration\""
markers = [
    "unit: fast isolated unit tests",
    "integration: tests requiring external services; run only when asked for, with -m integration",
    "smoke: quick sanity-check tests",
]
filterwarnings = [
    "ignore::DeprecationWarning",
]

[tool.ruff]
line-length = 100
target-version = "py311"
extend-exclude = ["results"]

[tool.ruff.lint]
# Standard "good defaults" rule set (pyflakes + pycodestyle + isort + bugbear +
# pyupgrade + comprehensions/simplify). Line length (E501) and layout are owned
# by the formatter; whole-repo `ruff format` adoption is deferred until the
# open-PR backlog clears, to avoid mass merge conflicts.
select = ["E", "W", "F", "I", "B", "UP", "C4", "SIM"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"**/__init__.py" = ["F401"]   # intentional re-exports

[tool.ruff.lint.isort]
# Keep multiple aliased names from one module in a single combined import block
# (e.g. the vendor imports in router.py) instead of one statement per name.
combine-as-imports = true

```

---

## Assistant (Build · CityU DeepSeek-V4-Flash · 13.6s)

Let me read the zshrc config function (without printing secrets) and understand the CLI structure and key parts of the code. Let me read the config function carefully.





**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/ichihann/.zshrc",
  "offset": 33,
  "limit": 70
}
```

**Error:**
```
The user rejected permission to use this specific tool call.
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/TradingAgents/cli/run.py"
}
```

**Output:**
```
<path>/Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/TradingAgents/cli/run.py</path>
<type>file</type>
<content>
1: """Running one analysis from the CLI: build the graph, stream it into the live view, save the report."""
2: 
3: import os
4: import sys
5: import time
6: import webbrowser
7: from functools import wraps
8: from pathlib import Path
9: 
10: import typer
11: from rich.live import Live
12: 
13: from cli.display import (
14:     ANALYST_ORDER,
15:     AnalystWallTimeTracker,
16:     classify_message_type,
17:     console,
18:     create_layout,
19:     display_complete_report,
20:     message_buffer,
21:     update_analyst_statuses,
22:     update_display,
23:     update_research_team_status,
24: )
25: from cli.selections import depth_from_env, get_user_selections, unattended_gaps
26: from cli.stats_handler import StatsCallbackHandler
27: from tradingagents.agents.rating import is_review, run_rating
28: from tradingagents.dataflows.symbols import safe_ticker_component
29: from tradingagents.default_config import DEFAULT_CONFIG
30: from tradingagents.graph.analyst_execution import (
31:     build_analyst_execution_plan,
32: )
33: from tradingagents.graph.trading_graph import TradingAgentsGraph
34: 
35: 
36: def _run_directory(config: dict, ticker: str, trade_date: str) -> Path:
37:     """Where this run writes, with the ticker validated as a path component.
38: 
39:     Every other path that interpolates a ticker checks it first; a value of
40:     ".." here would place the run outside the results directory.
41:     """
42:     return Path(config["results_dir"]) / safe_ticker_component(ticker) / trade_date
43: 
44: 
45: def _announce_checkpoint_state(graph, ticker: str, trade_date: str) -> None:
46:     """Say whether this run resumed a saved one, where the user can see it.
47: 
48:     The graph logs this, but nothing in the CLI configures logging and the live
49:     view owns the screen, so a resume was invisible.
50:     """
51:     if getattr(graph, "_resuming", False):
52:         message_buffer.add_message(
53:             "System", f"Resuming the saved run for {ticker} on {trade_date}"
54:         )
55:     else:
56:         message_buffer.add_message("System", f"Starting fresh for {ticker} on {trade_date}")
57: 
58: 
59: def _build_run_config(selections: dict, checkpoint: bool | None) -> dict:
60:     """Assemble the run config from interactive selections, honoring env precedence.
61: 
62:     Round counts and checkpoint follow "explicit env/flag wins": an env-applied
63:     value on DEFAULT_CONFIG is preserved unless the user overrode it on the CLI.
64:     """
65:     config = DEFAULT_CONFIG.copy()
66:     # Research depth sets both round counts, but an explicit env override
67:     # (TRADINGAGENTS_MAX_DEBATE_ROUNDS / _MAX_RISK_ROUNDS) wins over the
68:     # interactive selection — leave the env-applied value in place (#977).
69:     rounds = (("TRADINGAGENTS_MAX_DEBATE_ROUNDS", "max_debate_rounds"),
70:               ("TRADINGAGENTS_MAX_RISK_ROUNDS", "max_risk_discuss_rounds"))
71:     depth_was_asked = not depth_from_env()
72:     for env_var, key in rounds:
73:         if not os.environ.get(env_var):
74:             config[key] = selections["research_depth"]
75:         elif depth_was_asked:
76:             # The depth question appeared (it is skipped only when both are
77:             # set), so say which half of the answer the environment overrode.
78:             console.print(
79:                 f"[green]✓ {key} from environment:[/green] {config[key]} "
80:                 f"(set by {env_var}, so the research depth you chose does not apply to it)"
81:             )
82:     config["quick_think_llm"] = selections["quick_think_llm"]
83:     config["deep_think_llm"] = selections["deep_think_llm"]
84:     config["backend_url"] = selections["backend_url"]
85:     config["llm_provider"] = selections["llm_provider"].lower()
86:     # Provider-specific thinking configuration. Only the main provider's is
87:     # asked; a tier on another provider keeps its configured value (#1440).
88:     for key in ("google_thinking_level", "openai_reasoning_effort", "anthropic_effort"):
89:         if selections.get(key) is not None:
90:             config[key] = selections[key]
91:     config["output_language"] = selections.get("output_language", "English")
92:     # --checkpoint/--no-checkpoint overrides only when explicitly given; omitting
93:     # the flag preserves TRADINGAGENTS_CHECKPOINT_ENABLED / the default (#976).
94:     if checkpoint is not None:
95:         config["checkpoint_enabled"] = checkpoint
96:     return config
97: 
98: 
99: def run_analysis(checkpoint: bool | None = None, portfolio=None, flags=None):
100:     flags = flags or {}
101:     # With no terminal nothing can answer a prompt: name every question still
102:     # open before any model is called, rather than stopping at the first one.
103:     if not (sys.stdin and sys.stdin.isatty()):
104:         gaps = unattended_gaps(flags)
105:         if gaps:
106:             console.print("[red]No terminal to answer the setup questions. Set:[/red]")
107:             for gap in gaps:
108:                 console.print(f"  {gap}")
109:             raise typer.Exit(code=1)
110: 
111:     selections = get_user_selections(flags)
112: 
113:     config = _build_run_config(selections, checkpoint)
114: 
115:     stats_handler = StatsCallbackHandler()
116: 
117:     # Normalize analyst selection to predefined order (selection is a 'set', order is fixed)
118:     selected_set = {analyst.value for analyst in selections["analysts"]}
119:     selected_analyst_keys = [a for a in ANALYST_ORDER if a in selected_set]
120:     analyst_execution_plan = build_analyst_execution_plan(selected_analyst_keys)
121:     analyst_wall_time_tracker = AnalystWallTimeTracker(analyst_execution_plan)
122: 
123:     graph = TradingAgentsGraph(
124:         selected_analyst_keys,
125:         config=config,
126:         debug=True,
127:         callbacks=[stats_handler],
128:     )
129: 
130:     message_buffer.init_for_analysis(selected_analyst_keys)
131: 
132:     # Track start time for elapsed display
133:     start_time = time.time()
134: 
135:     results_dir = _run_directory(config, selections["ticker"], selections["analysis_date"])
136:     results_dir.mkdir(parents=True, exist_ok=True)
137:     report_dir = results_dir / "reports"
138:     report_dir.mkdir(parents=True, exist_ok=True)
139:     log_file = results_dir / "message_tool.log"
140:     log_file.touch(exist_ok=True)
141: 
142:     def save_message_decorator(obj, func_name):
143:         func = getattr(obj, func_name)
144: 
145:         @wraps(func)
146:         def wrapper(*args, **kwargs):
147:             func(*args, **kwargs)
148:             timestamp, message_type, content = obj.messages[-1]
149:             content = content.replace("\n", " ")  # Replace newlines with spaces
150:             with open(log_file, "a", encoding="utf-8") as f:
151:                 f.write(f"{timestamp} [{message_type}] {content}\n")
152:         return wrapper
153: 
154:     def save_tool_call_decorator(obj, func_name):
155:         func = getattr(obj, func_name)
156: 
157:         @wraps(func)
158:         def wrapper(*args, **kwargs):
159:             func(*args, **kwargs)
160:             timestamp, tool_name, args = obj.tool_calls[-1]
161:             args_str = ", ".join(f"{k}={v}" for k, v in args.items())
162:             with open(log_file, "a", encoding="utf-8") as f:
163:                 f.write(f"{timestamp} [Tool Call] {tool_name}({args_str})\n")
164:         return wrapper
165: 
166:     def save_report_section_decorator(obj, func_name):
167:         func = getattr(obj, func_name)
168: 
169:         @wraps(func)
170:         def wrapper(section_name, content):
171:             func(section_name, content)
172:             if section_name in obj.report_sections and obj.report_sections[section_name] is not None:
173:                 content = obj.report_sections[section_name]
174:                 if content:
175:                     file_name = f"{section_name}.md"
176:                     text = "\n".join(str(item) for item in content) if isinstance(content, list) else content
177:                     with open(report_dir / file_name, "w", encoding="utf-8") as f:
178:                         f.write(text)
179:         return wrapper
180: 
181:     message_buffer.add_message = save_message_decorator(message_buffer, "add_message")
182:     message_buffer.add_tool_call = save_tool_call_decorator(message_buffer, "add_tool_call")
183:     message_buffer.update_report_section = save_report_section_decorator(message_buffer, "update_report_section")
184: 
185:     layout = create_layout()
186: 
187:     # The alternate screen keeps a layout taller than the window from redrawing
188:     # by scrolling; the final report prints after this block, on the normal screen.
189:     with Live(layout, refresh_per_second=4, screen=True):
190:         # Initial display
191:         update_display(layout, stats_handler=stats_handler, start_time=start_time)
192: 
193:         message_buffer.add_message("System", f"Selected ticker: {selections['ticker']}")
194:         if selections["asset_type"] != "stock":
195:             message_buffer.add_message("System", f"Detected asset type: {selections['asset_type']}")
196:         message_buffer.add_message(
197:             "System", f"Analysis date: {selections['analysis_date']}"
198:         )
199:         message_buffer.add_message(
200:             "System",
201:             f"Selected analysts: {', '.join(analyst.value for analyst in selections['analysts'])}",
202:         )
203:         update_display(layout, stats_handler=stats_handler, start_time=start_time)
204: 
205:         # The analysts start together.
206:         for spec in analyst_execution_plan.specs:
207:             message_buffer.update_agent_status(spec.agent_node, "in_progress")
208:             analyst_wall_time_tracker.mark_started(spec.key)
209:         update_display(layout, stats_handler=stats_handler, start_time=start_time)
210: 
211:         spinner_text = (
212:             f"Analyzing {selections['ticker']} on {selections['analysis_date']}..."
213:         )
214:         update_display(layout, spinner_text, stats_handler=stats_handler, start_time=start_time)
215: 
216:         # The same initial state propagate() builds, with the resolved
217:         # instrument identity; the graph's Memory Log step settles past
218:         # decisions and loads their lessons alongside the analysts.
219:         init_agent_state = graph.create_run_state(
220:             selections["ticker"], selections["analysis_date"], selections["asset_type"], portfolio
221:         )
222:         # Pass callbacks to graph config for tool execution tracking
223:         # (LLM tracking is handled separately via LLM constructor)
224:         args = graph.propagator.get_graph_args(callbacks=[stats_handler])
225: 
226:         # Recompile with a checkpointer and inject the thread_id so --checkpoint
227:         # actually saves and resumes on the CLI path (#1249); a no-op when
228:         # checkpointing is disabled. Torn down in the finally below.
229:         checkpoint_tid = graph.begin_checkpoint(
230:             selections["ticker"], selections["analysis_date"], selections["asset_type"], portfolio
231:         )
232:         if checkpoint_tid is not None:
233:             args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = checkpoint_tid
234:             _announce_checkpoint_state(graph, selections["ticker"], selections["analysis_date"])
235: 
236:         # Stream the analysis. On resume, feed None so LangGraph continues the
237:         # interrupted run instead of re-appending the initial state (#1249); the
238:         # try/finally tears the checkpointer down even if the stream raises.
239:         trace = []
240:         try:
241:             for messages, chunk in graph.stream_run(graph.checkpoint_input(init_agent_state), **args):
242:                 for message in messages:
243:                     msg_id = getattr(message, "id", None)
244:                     if msg_id is not None:
245:                         if msg_id in message_buffer._processed_message_ids:
246:                             continue
247:                         message_buffer._processed_message_ids.add(msg_id)
248: 
249:                     msg_type, content = classify_message_type(message)
250:                     if content and content.strip():
251:                         message_buffer.add_message(msg_type, content)
252: 
253:                     if hasattr(message, "tool_calls") and message.tool_calls:
254:                         for tool_call in message.tool_calls:
255:                             if isinstance(tool_call, dict):
256:                                 message_buffer.add_tool_call(tool_call["name"], tool_call["args"])
257:                             else:
258:                                 message_buffer.add_tool_call(tool_call.name, tool_call.args)
259: 
260:                 if chunk is None:   # a step inside an analyst's graph: messages only
261:                     update_display(layout, stats_handler=stats_handler, start_time=start_time)
262:                     continue
263: 
264:                 update_analyst_statuses(
265:                     message_buffer,
266:                     chunk,
267:                     wall_time_tracker=analyst_wall_time_tracker,
268:                 )
269: 
270:                 # Research Team - Handle Investment Debate State
271:                 if chunk.get("investment_debate_state"):
272:                     debate_state = chunk["investment_debate_state"]
273:                     bull_hist = debate_state.get("bull_history", "").strip()
274:                     bear_hist = debate_state.get("bear_history", "").strip()
275:                     judge = (chunk.get("investment_plan") or "").strip()
276: 
277:                     # Only update status when there's actual content
278:                     if bull_hist or bear_hist:
279:                         update_research_team_status("in_progress")
280:                     if bull_hist:
281:                         message_buffer.update_report_section(
282:                             "investment_plan", f"### Bull Researcher Analysis\n{bull_hist}"
283:                         )
284:                     if bear_hist:
285:                         message_buffer.update_report_section(
286:                             "investment_plan", f"### Bear Researcher Analysis\n{bear_hist}"
287:                         )
288:                     if judge:
289:                         message_buffer.update_report_section(
290:                             "investment_plan", f"### Research Manager Decision\n{judge}"
291:                         )
292:                         update_research_team_status("completed")
293:                         message_buffer.update_agent_status("Trader", "in_progress")
294: 
295:                 # Trading Team
296:                 if chunk.get("trader_investment_plan"):
297:                     message_buffer.update_report_section(
298:                         "trader_investment_plan", chunk["trader_investment_plan"]
299:                     )
300:                     if message_buffer.agent_status.get("Trader") != "completed":
301:                         message_buffer.update_agent_status("Trader", "completed")
302:                         message_buffer.update_agent_status("Aggressive Analyst", "in_progress")
303: 
304:                 # Risk Management Team - Handle Risk Debate State
305:                 if chunk.get("risk_debate_state"):
306:                     risk_state = chunk["risk_debate_state"]
307:                     agg_hist = risk_state.get("aggressive_history", "").strip()
308:                     con_hist = risk_state.get("conservative_history", "").strip()
309:                     neu_hist = risk_state.get("neutral_history", "").strip()
310:                     judge = (chunk.get("final_trade_decision") or "").strip()
311: 
312:                     if agg_hist:
313:                         if message_buffer.agent_status.get("Aggressive Analyst") != "completed":
314:                             message_buffer.update_agent_status("Aggressive Analyst", "in_progress")
315:                         message_buffer.update_report_section(
316:                             "final_trade_decision", f"### Aggressive Analyst Analysis\n{agg_hist}"
317:                         )
318:                     if con_hist:
319:                         if message_buffer.agent_status.get("Conservative Analyst") != "completed":
320:                             message_buffer.update_agent_status("Conservative Analyst", "in_progress")
321:                         message_buffer.update_report_section(
322:                             "final_trade_decision", f"### Conservative Analyst Analysis\n{con_hist}"
323:                         )
324:                     if neu_hist:
325:                         if message_buffer.agent_status.get("Neutral Analyst") != "completed":
326:                             message_buffer.update_agent_status("Neutral Analyst", "in_progress")
327:                         message_buffer.update_report_section(
328:                             "final_trade_decision", f"### Neutral Analyst Analysis\n{neu_hist}"
329:                         )
330:                     if judge and message_buffer.agent_status.get("Portfolio Manager") != "completed":
331:                         message_buffer.update_agent_status("Portfolio Manager", "in_progress")
332:                         message_buffer.update_report_section(
333:                             "final_trade_decision", f"### Portfolio Manager Decision\n{judge}"
334:                         )
335:                         message_buffer.update_agent_status("Aggressive Analyst", "completed")
336:                         message_buffer.update_agent_status("Conservative Analyst", "completed")
337:                         message_buffer.update_agent_status("Neutral Analyst", "completed")
338:                         message_buffer.update_agent_status("Portfolio Manager", "completed")
339: 
340:                 update_display(layout, stats_handler=stats_handler, start_time=start_time)
341: 
342:                 trace.append(chunk)
343: 
344:             # Streamed chunks are per-node deltas, not full state. Merge them
345:             # so every report field populated across the run is present.
346:             final_state = {}
347:             for chunk in trace:
348:                 final_state.update(chunk)
349: 
350:             # Clean run: log the decision, then drop this run's checkpoint so a
351:             # later run starts fresh. A mid-stream failure skips both, keeping
352:             # the checkpoint for resume.
353:             graph.record_decision(selections["ticker"], selections["analysis_date"], final_state)
354:             graph.clear_checkpoint_on_success(
355:                 selections["ticker"], selections["analysis_date"], selections["asset_type"], portfolio
356:             )
357:         finally:
358:             # Always restore the plain uncheckpointed graph, even on failure.
359:             graph.end_checkpoint()
360: 
361:         for agent in message_buffer.agent_status:
362:             message_buffer.update_agent_status(agent, "completed")
363: 
364:         message_buffer.add_message(
365:             "System", f"Completed analysis for {selections['analysis_date']}"
366:         )
367:         message_buffer.add_message("System", analyst_wall_time_tracker.format_summary())
368: 
369:         for section in message_buffer.report_sections:
370:             if section in final_state:
371:                 message_buffer.update_report_section(section, final_state[section])
372: 
373:         update_display(layout, stats_handler=stats_handler, start_time=start_time)
374: 
375:     # Post-analysis prompts (outside Live context for clean interaction)
376:     console.print("\n[bold cyan]Analysis Complete![/bold cyan]\n")
377: 
378:     # A decision nobody can read is not a position. Say so here rather than
379:     # leaving the run to look like a normal result.
380:     if is_review(run_rating(final_state)):
381:         console.print(
382:             "[yellow]No rating could be read from the final decision, so this run "
383:             "is recorded for review rather than as a position. Re-run, or read the "
384:             "decision text below and judge it yourself.[/yellow]\n"
385:         )
386:     console.print(f"[dim]{analyst_wall_time_tracker.format_summary()}[/dim]")
387: 
388:     _offer_reports(final_state, graph, selections["ticker"],
389:                    save=flags.get("save"), show=flags.get("show"), html=flags.get("html"))
390: 
391: 
392: def _yes(question: str) -> bool:
393:     return typer.prompt(question, default="Y").strip().upper() in ("Y", "YES", "")
394: 
395: 
396: def _graphical_browser():
397:     """A browser that opens a page in its own window on this machine, or None.
398: 
399:     Over SSH the page sits on the remote machine, and a terminal browser (lynx,
400:     w3m, elinks) would take over the terminal, so neither is offered.
401:     """
402:     if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
403:         return None
404:     try:
405:         browser = webbrowser.get()
406:     except webbrowser.Error:
407:         return None
408:     if type(browser) is webbrowser.GenericBrowser or isinstance(browser, webbrowser.Elinks):
409:         return None
410:     return browser
411: 
412: 
413: def _open_page(page: Path) -> None:
414:     """Offer to open the saved page in a browser window, and say where it is if opening fails."""
415:     browser = _graphical_browser()
416:     if browser is None or not _yes("Open it in your browser?"):
417:         return
418:     try:
419:         opened = browser.open(page.as_uri())
420:     except (webbrowser.Error, OSError):
421:         opened = False
422:     if not opened:
423:         console.print(f"  [dim]Could not open a browser; the page is at:[/dim] {page}")
424: 
425: 
426: def _offer_reports(final_state, graph, ticker, save=None, show=None, html=None):
427:     """Save the report tree and show it; ``save``/``show``/``html`` answer the questions when given.
428: 
429:     A saved report includes the HTML page unless ``html`` is False. Someone
430:     answering the save question at the prompt is also asked about the page and
431:     offered to open it; a run whose flags answer the save question asks neither.
432:     """
433:     asked = save is None
434:     if asked:
435:         save = typer.prompt("Save report?", default="Y").strip().upper() in ("Y", "YES", "")
436:     if save:
437:         # Under results_dir, not the working directory: in Docker the working
438:         # directory is inside the container and the report goes with it, while
439:         # results_dir is the mounted volume the rest of the run already writes to.
440:         save_path = graph.default_report_path(ticker)
441:         if asked:   # someone at the prompt may pick another folder
442:             save_path = Path(typer.prompt(
443:                 "Save path (press Enter for default)", default=str(save_path)
444:             ).strip())
445:         if html is None:
446:             html = _yes("Also save it as an HTML page?") if asked else True
447:         saved = False
448:         try:
449:             report_file = graph.save_reports(final_state, ticker, save_path, html=html)
450:             saved = True
451:             console.print(f"\n[green]✓ Report saved to:[/green] {save_path.resolve()}")
452:             console.print(f"  [dim]Complete report:[/dim] {report_file.name}")
453:         except Exception as e:
454:             console.print(f"[red]Error saving report: {e}[/red]")
455:         if saved and html:
456:             page = (save_path / "complete_report.html").resolve()
457:             console.print(f"  [dim]HTML report:[/dim] {page.name}")
458:             if asked:
459:                 _open_page(page)
460: 
461:     if show is None:
462:         show = typer.prompt("\nDisplay full report on screen?", default="Y").strip().upper() in ("Y", "YES", "")
463:     if show:
464:         display_complete_report(final_state)

(End of file - total 464 lines)
</content>
```

---

