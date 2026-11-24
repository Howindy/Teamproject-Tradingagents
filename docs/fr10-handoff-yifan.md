# FR-10 当前实现情况与 Round-04B 讨论材料

日期：2026-11-25。本文供双方及各自的 AI 阅读、核对和讨论，不安排对方的实施步骤，
不决定采用哪一方的代码或方案，也不是新的审批、最终验收或合并授权。

## 当前状态

**此分支已有 FR-10 计算模块、SEC/价格适配器和真实运行入口接入。**
Round-04B-v3 中引用的 `0b9de969` 是较早版本，与当前实现存在下表列出的差异。
这些差异可用于讨论两个工作分支的重叠范围；具体整合方式尚未由双方确定。

- 分支：`feat/financial-metrics-integration`，现有 PR：[#19](https://github.com/Howindy/Teamproject-Tradingagents/pull/19)。
- 运行入口接入基准：`2fbd1cf`；后续离线适配修正见本分支最新提交和本文更新。
- 已包含 main 的 Round 3 合并版本 `5718bac`。
- 早期交接材料描述的是该接入基准；本说明下方记录了其后的修正，不代表已经最终验收。
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

入口接入阶段（`2fbd1cf`）相关组合为 **463 passed，9.19 秒**；Ruff 和 diff 空白检查通过。
该阶段十三个文件为：

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

## 2026-11-25 后续离线适配结果及限制

后续最终应用回归为 **511 passed，19.97 秒**：上述十三个文件加上 SEC 原有工具测试，
并包含补充的 probe、边界和异常测试。准备/评估相关四文件组合另为 **73 passed**；
两次运行有重叠，不相加。Ruff、API、依赖一致性和 diff 检查通过，未执行真实模型评估。

其后收到价格异常隔离反馈：原先 Yahoo 超时或非有限价格会向服务层传播，导致已取得的
SEC facts 被整组降级。该问题已在 `SecCompanyFactsProvider.fetch()` 的价格读取边界修正。
现在只令 FY P/E 为 `n/a: price_availability_unknown`，保留其他九项及已知 EPS 来源。
新增 timeout/Infinity/NaN 的真实 provider→service→calculator 测试，验证同分析复用失败、
下次分析价格恢复后十项均正常。此次四文件相关回归 **90 passed**，Ruff 通过；
未将历史 511 项重跑结果或真实模型验收归入本次结论。

### 1. trusted probe 的财历证据兼容

当前 `scripts/financial_metrics_eval.py` 的 candidate probe 构造 FinancialFact 时传
`calendar_id` 和 `disclosure`，没有单独传 `calendar_evidence`。现已在 FinancialFact
输入边界识别 disclosure 中原有的申报文件、行元素、context、财期标注方法和选值说明，
仅在来源及所有期间字段与对象一致时保留为可定位证据；没有推断新的财年或季度。
缺证据、错期间及错来源的负例仍返回 n/a。原 trusted driver 未修改，FM-S01–04 的
实际离线子进程已通过真实计算和提示词路径，逐项核对十行值、期间、原因和来源。
这项通过是输入/计算/注入兼容性证据，不是真实模型质量通过。

### 2. 数值来源精度约定不同

现已为 FR-10 的结构化 companyfacts 增加原始 JSON 文本缓存，并以
`parse_float=Decimal` 读取。新缓存名为 `CIK<CIK>-raw-v1.json`，不把旧的 float
反序列化缓存当作保真来源。冷读、缓存读及转换成 FinancialFact 的长小数测试一致。
原有财务工具的普通缓存与返回类型保留；两者共用 SEC 请求及错误处理路径。
当前 Yahoo helper 明确 `auto_adjust=False`，其报价经 `Decimal(str(value))` 进入核心。
这不等于获得交易所原始精确十进制词法。

本分支继续接受 Yahoo 市场浮点报价的适配转换，明确保留其输入精度边界；不因此关闭
正常 P/E。核心仍拒绝直接 float。它不声称恢复交易所原始价格词法，也不替另一方决定
是否采用相同的验收口径。

### 3. 当前测试覆盖范围

在原测试上补了不同外部数值的两次同股票/同日期运行、工厂初始化失败复用及下次恢复、
坏 payload、January 财年比较列、DST、单位/期间/分母、全缺失、正负 half-up 及
低 Decimal precision。低精度测试发现负 CapEx 取反受上下文精度影响，现用精确符号
转换修正。初始化失败在本分析内只尝试一次，与 fetch 失败一样复用降级结果。

这不意味着所有可能的金融数据异常均已覆盖，也不等于十项 FC 的最终人工验收。

### 4. 历史准备测试、语义评估与 CI 单独说明

P07 已将准备阶段范围断言绑定到固定 main `5718bacff6cafb9412a805878fe82e97f279a8bc`
的 Git tree/blob；当前候选仍检查没有引入 deferred brief。受控违规准备快照仍失败，
没有 skip、运行时 fetch 或修改 frozen cases/rubric/scorer。

语义 baseline 注入及否定句评分问题仍未在本轮修复。当前没有 candidate-bound 真实
语义证据，原 pilot 和离线测试均不属于这类证据。

用户此前提出暂停 CI，但本次没有关闭、修改或绕过任何 CI。推送可能触发现有检查；
本说明没有核验最新远端检查结果。04B 文档仍包含完整门禁流程，与此前讨论的流程安排
尚未统一；本文不决定是否启用或停用。

## 尚未确定的讨论事项

- 当前分支与 04B 的实现如何整合、分别由谁处理，尚未共同确定。
- 市场价格的精度边界与 SEC 披露数字的保真约定，尚未统一。
- 真实 probe 的离线兼容已补测；正式语义评估、04A 联合验证和最终验收尚未完成。
- 门禁、语义评估和最终合并安排仍属单独讨论事项，本文不代替任何一方作决定。
