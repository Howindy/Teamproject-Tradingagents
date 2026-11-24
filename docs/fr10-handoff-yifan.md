# FR-10 当前实现情况与 Round-04B 讨论材料

日期：2026-11-25。本文供双方及各自的 AI 阅读、核对和讨论，不安排对方的实施步骤，
不决定采用哪一方的代码或方案，也不是新的审批、最终验收或合并授权。

## 当前状态

**此分支已有 FR-10 计算模块、SEC/价格适配器和真实运行入口接入。**
Round-04B-v3 中引用的 `0b9de969` 是较早版本，与当前实现存在下表列出的差异。
这些差异可用于讨论两个工作分支的重叠范围；具体整合方式尚未由双方确定。

- 分支：`feat/financial-metrics-integration`，现有 PR：[#19](https://github.com/Howindy/Teamproject-Tradingagents/pull/19)。
- 功能交接版本：`2fbd1cf`（完整 SHA 可通过 `git rev-parse 2fbd1cf` 获取）。
- 已包含 main 的 Round 3 合并版本 `5718bac`。
- 本文后续文档提交不会改变上述功能交接版本。
- 当前仍未合并 main，也没有当前功能候选的正式语义评估通过结论。

编号说明：这里的 **FR-10** 是确定性财务指标；个人旧财务 FR-07 是其历史
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

## 当前实现与 Round-04A 的接口关系

以下是本分支已经采用的实现边界，不是双方已达成的约定，也不限制另一方的设计。

1. **不新增图节点或边。** 本分支没有接入 04A 的风险检查和最终推荐节点。
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
本分支在这两个文件中的插入点是可选 `metrics_factory` 参数、财务分析员参数传递和
作用域清理。04A 描述的插入点是后置节点、场景和正式交付逻辑。目前没有完成双方最终
实现的联合合并或组合验证，因此这里不作“合并一定无冲突”的结论。

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

## 已知限制及与 Round-04B-v3 的差异

### 1. trusted probe 的财历证据兼容

当前 `scripts/financial_metrics_eval.py` 的 candidate probe 构造 FinancialFact 时传
`calendar_id` 和 `disclosure`，**没有传 `calendar_evidence`**。当前计算器检查后者，
缺失会得到 `incomparable_period`。现有单元 fixture 传了该证据，因此其通过不能代表
trusted probe 兼容。现有冻结材料能否提供足够证据、证据应在哪一层投影，以及两边
接口如何匹配，尚未在本分支完成验证或修正。

### 2. 数值来源精度约定不同

当前 SEC 共享 JSON 入口仍使用普通 JSON 数字解析；如果 04B 采用
`parse_float=Decimal` 的保真要求，本分支目前尚不满足这项约定，相关缓存读写兼容也未验证。
当前 Yahoo helper 明确 `auto_adjust=False`，其报价经 `Decimal(str(value))` 进入核心。
这不等于获得交易所原始精确十进制词法。

04B-v3 写明“来源只提供 float 时不可用”；本分支则允许 Yahoo 浮点报价在适配层转换，
但核心拒绝直接 float。因此两份方案在此处存在真实差异。严格拒绝该来源会限制当前
Yahoo P/E 路径；接受转换则存在原始精度边界。这是待讨论的取舍，本文不指定采用哪一种。

### 3. 当前测试覆盖范围

当前代码不是十项 FC 全部边界均已验收。04B 的 B01–B12 与现有测试尚未完成逐项
覆盖映射；真实 probe、各项财期/单位/符号边界、低 Decimal precision、工厂初始化异常
和坏数据的完整覆盖仍未确认。当前两次运行测试使用相同参考事实，验证了分别读取，
没有验证“第二次换成不同值后输出相应变化”。

当前正常 scope 内的 provider.fetch 故障结果会复用；data_factory 初始化异常由分析员
降级；初始化失败是否只尝试一次尚未验证。这与 04B 要求故障结果复用的覆盖范围有关。

### 4. 历史准备测试、语义评估与 CI 单独说明

P07 准备阶段测试仍有当前工作树“无 financials”的假设；04B 提出了固定到历史快照
的修改方案，本分支未修改该测试。现有语义 baseline 注入及否定句评分问题也没有在本次
接入中修复。当前没有 candidate-bound 真实语义证据，旧 pilot 和 463 项本地测试
不属于这类证据。

用户此前提出暂停 CI，但本次没有关闭、修改或绕过任何 CI。推送可能触发现有检查；
本说明没有核验最新远端检查结果。04B 文档仍包含完整门禁流程，与此前讨论的流程安排
尚未统一；本文不决定是否启用或停用。

## 尚未确定的讨论事项

- 当前分支与 04B 的实现如何整合、分别由谁处理，尚未共同确定。
- 市场价格的精度边界与 SEC 披露数字的保真约定，尚未统一。
- 真实 probe 兼容、完整测试覆盖及 04A 联合验证，尚未完成。
- 门禁、语义评估和最终合并安排仍属单独讨论事项，本文不代替任何一方作决定。
