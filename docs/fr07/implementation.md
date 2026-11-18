# FR-07 / FR-08 交付说明（离线验证完成）

## 状态

- GR-01 Stage A 参考集已按用户确认冻结：`docs/fr07/sec-reference-draft-v1/freeze_record.json`
  （版本 `fr07-sec-reference-v1`），冻结记录之后才记录应用实现起点
  （`implementation_start.json`）。
- FR-07 通用 SEC 数据入口、十项指标计算、财务分析员首轮提示词注入已完成。
- FR-08 结构化摘要与保护块交付已完成，保持独立适配器形态。
- 本轮真实请求：一次财务分析员 wrap-up（MSFT），证据见 `docs/fr07/sec-msft-evidence/`。
- 未提交任何密钥、`.env` 或缓存；未接入完整多角色运行。

## FR-07 文件

| 文件 | 职责 |
|---|---|
| `tradingagents/financials/models.py` | 不可变输入/输出契约；禁止二进制 float 作为权威数值 |
| `tradingagents/financials/metrics.py` | 纯函数选期与计算、`n/a` 原因、统一渲染 |
| `tradingagents/financials/service.py` | 可注入 `FinancialDataProvider`、本地参考快照适配器、run 级缓存 |
| `tradingagents/financials/sec_provider.py` | **通用 SEC 适配器** `SecCompanyFactsProvider` |
| `tradingagents/financials/wiring.py` | run clock 与 `metrics_factory` 组合点 |
| `dataflows/vendors/sec_edgar.py` | 新增 `company_facts()` / `submissions()`，共用 CIK 解析、缓存与请求路径 |
| `dataflows/vendors/yahoo/market.py` | 新增 `completed_close()`：已完成收盘 + 币种 + 每股单位 + 拆股事件 |
| `agents/analysts/fundamentals_analyst.py` | 首轮模型调用前注入指标表；保留原 TOOLS |
| `graph/setup.py`, `graph/trading_graph.py` | 把 `metrics_factory` 传入财务分析员 |
| `default_config.py` | `fr07_reference_root`、`fr07_sec_enabled` |
| `tests/test_financial_metrics.py` | 26 项：参考答案、反例、注入、复用、FR-07→FR-08 集成 |
| `tests/test_sec_financial_provider.py` | 11 项：通用适配器、期间/披露过滤、价格口径、财季回归 |

## 启用方式

默认关闭，旧行为不变。二选一：

```powershell
# 通用 SEC 适配器（任意美国申报公司）
$env:TRADINGAGENTS_FR07_SEC_ENABLED = "true"

# 或使用冻结参考快照
$env:TRADINGAGENTS_FR07_REFERENCE_ROOT = "<repo>\docs\fr07\sec-reference-draft-v1"
```

代码方式：

```python
from tradingagents.financials.wiring import build_metrics_factory

TradingAgentsGraph(..., metrics_factory=build_metrics_factory({"fr07_sec_enabled": True}))

# 团队数据服务替换点：
def data_factory(clock):          # clock: EvaluationClock
    return MyTeamDataProvider()   # FinancialDataProvider.fetch(ticker, as_of) -> FinancialInputs
```

## 财季/财年识别（本轮修正）

旧实现用“财年等分 + 20 天容差”推断财季，并把财年末的公历年份当财年编号，
在没有相邻财年边界时会直接丢弃季度事实。现在的规则：

- 每条原始事实天然带有**承载申报**的 `fy`/`fp`；申报的期间结束日取该申报报告的最新
  instant 日期（没有 instant 时取最晚的 duration 结束日）。
- 事实自身的财年 = `申报 fy − years_between(事实结束日, 申报期间结束日)`；
  年距必须落在周年日 ±10 天内（吸收 52/53 周漂移），否则不猜、跳过。
- 财季直接取申报声明的 `fp`（Q1–Q4）；`fp=FY` 的年报期间财季为空。
- 因此**比较期按其实际覆盖期间**取得 FY2024 Q3，而不是复制承载申报的 `fy=2025`。
- 无 `fy`/`fp` 的申报（例如部分 8-K 重述）不参与选期；同一期间同值多申报折叠为最新披露，
  不同值且无 lineage 保留，由计算器返回 `ambiguous_filing`。

回归用例 `test_single_annual_boundary_january_year_end_uses_declared_fiscal_labels`
用一家 1 月年结、仅有一个年度边界的合成申报暴露旧逻辑：旧代码会把 2025-01-31
标成 FY2025 且丢弃全部季度；新逻辑得到 FY2024 + Q1–Q3，并算出同比 20.0%、
环比 3.2%、季度同比 18.5%、FCF 120。

## 指标与 `n/a`

十项：季度/年度营收同比、季度营收环比、毛利率、营业利润率、净利率、流动比率、
负债占资产、已披露期间 FCF、财年 P/E。规则：

- 只选 `filed_at <= as_of`；as_of 当日的事实因无法证明 cutoff 前公开而排除（日期级可见性）。
- 季度只用 `span=quarter`；YTD 不作单季；不做年度减季度推导。
- 同比取上一财年同财季，环比取紧邻上一财季；缺期返回 `missing_comparison` / `missing_quarter`。
- 单位/币种/期间/财历不一致 → `unit_mismatch` / `currency_mismatch` /
  `fiscal_period_mismatch` / `incomparable_period`。
- 零分母、非正增长基数、非正 EPS → 对应 `n/a`；负利润、负 FCF 是合法值。
- capex 仅在来源 sign 规则支持时规范为正向流出，否则 `unknown_capex_sign`，不 `abs()`。
- P/E 只用年度稀释 EPS；要求已完成收盘、币种一致、`USD/shares`、每股基础双方均有证据；
  年度 EPS 之后出现拆股 → `basis_mismatch`，其余指标继续交付。
- 显示：百分比 0.1pp、比率 0.1x、FCF 为来源 USD millions 精确差，half-up。

## 正常分析路径

`TradingAgentsGraph` → `GraphSetup.setup_graph` → `create_fundamentals_analyst`。
财务分析员进入节点时先调用 `metrics_factory(state)`；同一 run/ticker 只读取并计算一次，
后续工具轮次与 wrap-up 复用同一文本。指标表写入 system prompt，并附带
“优先引用、保留单位/期间/n-a、表外推导须标注假设”的指令；原有财报工具不变。

## FR-07 结果进入 FR-08

`render_metrics(bundle)` 是一份纯文本，可直接作为 FR-08 的 `metric_block`：

```python
result = FinancialMetricProvider(SecCompanyFactsProvider(clock), clock).get("MSFT", as_of)
SharedSummaryBrief(...).get(..., metric_block=result.text)
```

`test_fr07_metric_block_is_preserved_verbatim_in_the_fr08_protected_material`
验证指标行、来源引用在保护块中原样保留且只出现一次，两条路径（结构化摘要与确定性回退）
都成立。

## 运行

```powershell
$py = 'D:\CityU\cs5351\project\.venv\Scripts\python.exe'
cd <repo>\TradingAgents
& $py -B -m pytest -q -p no:cacheprovider tests/test_financial_metrics.py tests/test_sec_financial_provider.py
& $py -B -m ruff check .
```

查看 MSFT 指标表（复用已保存快照，不联网）：

```powershell
& $py -B docs/fr07/sec-msft-evidence/capture.py
```

## 验证结果

- FR-07 新增测试：**37 passed**（26 + 11）。
- FR-08 新增测试：**56 passed**（`test_structured_summary.py`、`test_brief_delivery.py`、
  `test_downstream_brief.py`、`test_analyst_report_section_prompts.py` 合计）。
- 全量离线（无需 `--ignore`，ranking 草稿已移出 tests）：**1460 passed / 5 failed /
  4 skipped / 1 deselected / 100 subtests**；5 个失败与改动前基线一致（Windows 文件权限、
  升级命令、yfinance 缓存目录）。
- Ruff：通过。
- 冻结参考结果复验：Apple/Exxon 十项仍与 `expected_metrics.json` 一致；MSFT 十项与
  独立手算一致（营收同比 13.3%、年度 14.9%、环比 0.6%、毛利率 68.7%、营业 45.7%、
  净利 36.9%、流动比率 1.4x、负债资产 44.5%、FCF 71,611、P/E 38.9x）。

## 待团队接入

1. **统一数据服务**：`SecCompanyFactsProvider` 直接复用 SEC companyfacts/submissions
   缓存，尚未经过 `DataAccessService`，也不产生 FR-01 的 query/cache/HTTP/provenance
   计数器。接入点：实现 `FinancialDataProvider.fetch(ticker, as_of) -> FinancialInputs`。
2. **下游简报**：FR-08 目前是独立适配器，需等团队共享材料入口确定后再接入五个下游角色。
3. **保存与恢复**：metric bundle 的持久化、模型关闭时的强制块、结构化 claim 冲突、
   恢复时只读 bundle 不重算，仍未实现。
4. **价格基准**：只做已完成收盘与每股基础确认，不实现拆股/FX 调整算法。
