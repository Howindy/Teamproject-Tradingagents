# 给 Yifan / Round-04B 实施代理的 FR-10 交接说明

日期：2026-11-25。本文记录现有实现，不是新的审批、最终验收或合并授权。

## 先读这个结论

**FR-10 已有计算模块、SEC/价格适配器和真实运行入口接入，不需要从头实现。**
请将 Round-04B 调整为“复用当前实现、审查差异、补齐测试与兼容”，不要仅参考
`0b9de969` 或个人历史 `haoxi` 分支重新迁移一遍。

- 分支：`feat/financial-metrics-integration`，现有 PR：[#19](https://github.com/Howindy/Teamproject-Tradingagents/pull/19)。
- 功能交接版本：`2fbd1cf`（完整 SHA 可通过 `git rev-parse 2fbd1cf` 获取）。
- 已包含 main 的 Round 3 合并版本 `5718bac`。
- 本文后续文档提交不会改变上述功能交接版本。
- 当前仍未合并 main，也没有当前功能候选的正式语义评估通过结论。

历史编号要区分：这里的 **FR-10** 是确定性财务指标；个人旧财务 FR-07 是其历史
来源。当前团队 FR-07 是另一项摘要需求，本分支没有迁入该摘要功能。

## 版本进展

| 提交 | 已做内容 |
|---|---|
| `0b9de969` | 早期 A 阶段；还没有当前入口接入，不能代表完整现状 |
| `eeb3089` | 修正 P/E 价格读取、价格不可用原因，以及独立分析缓存作用域 |
| `00cf810` | 合并 `origin/main @ 5718bac`；唯一冲突是 AI-use log，保留双方记录 |
| `2fbd1cf` | 指标表接入财务分析员、图构造、程序入口和 CLI 使用的流式入口；配置及集成测试 |

## 实际运行链路

```text
配置 / 显式注入 data_factory
    → build_metrics_factory
    → TradingAgentsGraph → GraphSetup → Fundamentals Analyst
    → resolver(state)
    → FinancialDataProvider.fetch(ticker, as_of)
    → 确定性选期、十项计算、渲染
    → 原有 system prompt 增加程序指标材料
    → 原有 take_turn / 工具轮次 / wrap-up
```

FR-10 本身不增加摘要调用或其他模型请求，仍使用财务分析员原来的模型调用。
首次模型调用前已有指标表，同一次分析后续轮次复用；原来的五个财务工具保留。

现有文件职责：

- `src/tradingagents/financials/models.py`：事实、价格、时钟、指标及 bundle 契约。
- `metrics.py`：选期、十项计算、原因和表格渲染。
- `service.py`：provider 协议、分析内读取/计算复用；数据读取故障转不可用结果。
- `sec_provider.py`：SEC companyfacts/submissions 与价格适配。
- `wiring.py`：配置、时钟和 `MetricProviderFactory.analysis_scope()`。
- `dataflows/vendors/sec_edgar.py`、`dataflows/vendors/yahoo/market.py`：结构化读取辅助入口。
- `agents/analysts/fundamentals_analyst.py`：局部提示词注入，不写正式结果。
- `graph/setup.py`：传入可选 `metrics_factory`。
- `graph/trading_graph.py`：构造 resolver、管理指标作用域。
- `default_config.py`：默认关闭及环境变量覆盖。

## 与 Round-04A 的接口约定

这是本分支的实现边界，供另一方审阅确认；不代称另一方已经批准。

1. **不新增图节点或边。** 04A 可以继续接风险检查和最终推荐节点。
2. **不新增 AgentState 字段。** 指标只进入已有财务报告生产过程；provider、锁、
   Decimal、bundle 和缓存不写入图状态/checkpoint。
3. **不修改 RunContext。** `propagate()` 在现有 FR-03 RunContext 旁进入指标作用域；
   `stream_run()` 在复制的上下文中进入/退出作用域。正常结束、异常或提前关闭都会清理。
4. **不修改 CLI。** 现有 CLI 使用 `stream_run()`，因此直接获得上述隔离。
5. **不改变 FR-03 完整性。** 指标取数不登记为新的模型工具观察，指标 n/a 不增加必要项。
6. **不写 FR-04/SB-01/INV-01 的业务字段。** 不产生风险结果、gate status、正式评级或
   正式决策；指标缺失不额外 veto。模型报告内容改变可能间接改变建议，这是正常业务影响。
7. **只在 Fundamentals 使用程序指标。** 后续角色继续消费原有报告，不注入共享摘要。

共享修改主要在 `graph/setup.py` 和 `graph/trading_graph.py`；文本冲突仍可能发生。
后合入者保留可选 `metrics_factory` 参数、财务分析员参数传递和作用域清理，再保留
04A 的后置节点、场景和正式交付逻辑。不要用任一侧整文件覆盖另一侧。

更详细的现有接口与启动示例见 [fr10-integration.md](fr10-integration.md)。

## 已完成的本地验证

最终相关组合为 **463 passed，9.19 秒**；Ruff 和 diff 空白检查通过。十三个文件为：

```text
test/offline/test_financial_metrics.py
test/offline/test_sec_financial_provider.py
test/offline/test_financial_metrics_integration.py
test/offline/test_fr03_integration.py
test/offline/test_fr03_availability.py
test/offline/test_analyst_execution.py
test/offline/test_graph_end_to_end.py
test/offline/test_fr04_risk.py
test/offline/test_sb01_final_check.py
test/offline/test_portfolio_context.py
test/offline/test_checkpoint_lifecycle.py
test/offline/test_checkpoint_resume.py
test/offline/test_yahoo_rate_limit.py
```

覆盖首轮/tool/wrap-up、两次相同 ticker/date 分析、CLI、提前 close、交错流、主异常
恢复、默认关闭、未选 fundamentals、不支持资产及数据读取故障。FR-10 开关配对检查了
research/terminal availability 和原有决策输出；分析员测试检查风险/正式字段哨兵不变。

Windows 下初始临时目录导致 checkpoint/Yahoo SQLite 测试失败。设置测试专用
TEMP/TMP 后相关 70 项全部通过；没有靠 skip/xfail 或改应用代码处理。证据记录在
`docs/ai-use-log.yaml` 的 `AI-FM-FEATURE-B-001`。这不是全量测试、远端 CI 或真实模型质量结论。

## Round-04B 应优先补的实际缺口

### 1. trusted probe 的财历证据兼容

当前 `scripts/financial_metrics_eval.py` 的 candidate probe 构造 FinancialFact 时传
`calendar_id` 和 `disclosure`，**没有传 `calendar_evidence`**。当前计算器检查后者，
缺失会得到 `incomparable_period`。现有单元 fixture 传了该证据，因此其通过不能代表
trusted probe 兼容。应先用现有 probe 做离线 smoke，再从可定位的冻结材料处理证据
投影；不要虚构非空标记，也不要把真实证据要求简单删掉。尚未执行该修正。

### 2. 数值来源精度规则要区分 SEC 与市场报价

当前 SEC 共享 JSON 入口仍使用普通 JSON 数字解析；如果 04B 采用
`parse_float=Decimal` 的保真要求，还需实现并测试缓存读写兼容，避免影响已有 SEC 工具。
当前 Yahoo helper 明确 `auto_adjust=False`，其报价经 `Decimal(str(value))` 进入核心。
这不等于获得交易所原始精确十进制词法。

04B-v3 的“只要来源为 float 就不可用”会使正常 yfinance 价格难以用于 P/E。建议明确
允许有限市场浮点报价在适配层转换并披露精度边界，核心仍拒绝直接 float；若坚持拒绝，
必须接受当前 Yahoo P/E 不可用。这个需求选择需在实施前统一，不能只修改测试凑通过。

### 3. 审查补充测试，不要重写全部模块

当前代码不是十项 FC 全部边界均已验收。按 04B 的 B01–B12 对现有测试逐项比对，
只补实际缺项，尤其真实 probe、财期/单位/符号、低 Decimal precision、同图第二次用
不同外部事实、工厂初始化异常和坏数据等情况。当前测试使用相同参考事实验证两次读取，
不能代称“第二次不同值也已验证”。

当前正常 scope 内的 provider.fetch 故障结果会复用；data_factory 初始化异常由分析员
降级，但不应未经测试就宣称该类故障也只初始化一次。04B 若要求它也缓存，需补针对性测试。

### 4. 历史准备测试、语义评估与 CI 单独说明

P07 准备阶段测试的当前工作树“无 financials”假设需要按 04B 方案固定到历史快照；
本次未修改该测试。现有语义 baseline 注入及否定句评分问题也没有在本次接入中修复。
没有当前 candidate-bound 真实语义证据。不要将旧 pilot 或本地 463 passed 作为其替代。

用户此前提出暂停 CI，但本次没有关闭、修改或绕过任何 CI。推送可能触发现有检查；
其结果需要另外查看，不能声称全绿。若 04B 决定继续完整门禁，应先统一这个流程安排。

## 给实施代理的建议起步

1. 获取 `feat/financial-metrics-integration`，确认包含 `2fbd1cf` 和 main `5718bac`。
2. 对比本说明、真实代码和 04B，提交“已复用 / 待补齐 / 需决定”清单，避免重复开发。
3. 保留现有测试和原审批记录；04B 的补充批准与原功能计划批准分别记录，不重写历史。
4. 补实际缺口及离线验证；如果 04A 已合入，再做 FR-10 开关 × 风险结果的组合测试。
5. 对最终候选进行真实审核和适用验收后再合并，不把本文当作自动合并许可。
