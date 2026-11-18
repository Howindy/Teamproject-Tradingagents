# FR-07 实现前检查与独立参考准备

## 当前结论：Stage A 阻塞，尚未开始应用实现

工作区为 `Teamproject-Tradingagents-fr08`，分支
`haoxi-fr08-downstream-brief`。未发现 AGENTS.md；已有未提交 FR-08
实现、文档和测试保留，不创建工作区，不提交、不推送，不请求真实模型或数据商。

本轮按照用户要求先检查冻结前置条件。`docs/req/requirements.yaml`
FR-07 statement 和 GR-01 statement 明确：**GR-01 Stage A 必须在第一份
FR-07 应用实现之前通过，文档和独立参考准备不算应用实现。**
因此本目录只有独立算术复核和待审准备材料，没有新增应用计算服务、
选数器或财务分析员提示词注入，不宣称已完成用户要求的 FR-07 核心或接入。

已核对：

- `docs/req/requirements.yaml` FR-07-FC01–FC10、GR-01-FC01–FC06。
- `docs/req/fixtures/financial_metrics_v1.json` 的 53 个基础事实及 scenarios。
- `docs/req/fixtures/gr01_freeze_states_v1.json`。
- `docs/architecture/open-decisions.md` 的 OQ-14，仍为 open/blocking。
- 现有 SEC、fundamentals units/lookahead 测试和 fundamentals 提示词工厂。
- `dataflows/router.py`、`dataflows/vendors/sec_edgar.py`。

### 没有找到可用的 Stage A 记录

当前仓库中只找到规则验证器、静态样例和 reference pending 文档；
`gr01_freeze_states_v1.json` 的 `manifest_present=true`、`human_review_complete=true`
是测试场景输入，不是现实 manifest 或人工签核。其示例中的 AAPL/MSFT
CIK 也不等于已经准备这两家公司的参考材料。

缺少的实际证据：

1. 至少 **两家非 NVDA、稳定 issuer ID 不同**的公司及明确期间。
2. 两者不同财历的公开证据，包含年结、自然季度或 52/53 周口径说明；不是只有标签。
3. 每个期望值或 n/a 结论的公开源文件/内容投影、可定位段落/事实、版本或取用日期、内容哈希。
4. 独立派生公式、操作数、期间、币种、单位/scale、half-up 精度及全指标/关键期间反例覆盖矩阵。
5. 来源独立性、财历可比性与覆盖充分性的人工复核记录。
6. 实际冻结版本、冻结时间与不包含自身 digest 的内容摘要；冻结必须早于首次应用实现。

本文件不能批准这些材料，不能用“实现生成期望值数量为零”将缺失 manifest 变成通过。
不代选公司、不编造申报出处、不回填或倒签冻结时间。Stage B 尚不适用。

## 独立复核现有数字

以下只证明 **给定样例数值的算术**，不证明这些数字是真实 SEC 披露。
百分比保留 0.1 个百分点，比率保留 0.1x，half-up；FCF 保留来源金额单位。
期望字符串先固定在独立脚本中；脚本不导入应用、不调用应用路径生成自己的答案。
Decimal（60 位工作精度）与精确 Fraction 整数半入计算交叉复核展示值。

| 项目 | 固定操作数／公式 | 独立期望 |
|---|---|---|
| FY2027 Q2 营收同比 | (96,221 / 46,743 − 1) × 100 | **+105.9%** |
| FY2027 Q1 营收同比 | (81,615 / 44,062 − 1) × 100 | +85.2% |
| FY2027 Q2 营收环比 | (96,221 / 81,615 − 1) × 100 | +17.9% |
| Q2 毛利率 | 72,142 / 96,221 × 100 | 75.0% |
| Q2 营业利润率 | 63,734 / 96,221 × 100 | 66.2% |
| Q2 净利率 | 59,688 / 96,221 × 100 | 62.0% |
| FY2026 年度营收同比 | (215,938 / 130,497 − 1) × 100 | +65.5% |
| 流动比率 | 197,412 / 43,019 | 4.6x |
| 负债占资产比例 | 91,288 / 320,272 × 100 | 28.5% |
| FY2027 六个月已披露 FCF | 74,421 − 4,434 | 69,987 USD_millions |
| 财年 P/E 纯算术 | 217.09 / 4.90 | 44.3x（**输入语义尚不合格**） |
| 明确重述比较基数的算术 | (96,221 / 46,800 − 1) × 100 | +105.6% |

JSON 复核输出逐项保留 fixture JSON pointer、fact 全字段、公式、精确分数、
预期字面值、实际算术展示值和 fixture 内既有期望。年度同比、FCF、P/E 的
独立期望同时对应 FR-07-FC01/04/05；不因为有些历史 scenario 整体标为 deferred
就把 TTM/FCF YoY 带回当前范围。

### 样例不能直接作为权威取数验收输入的问题

- **EPS 单位错误/未证实：** 所有 diluted_eps 样例仍写 `USD_millions`，
  不是经证实的 `USD/share`。44.3x 只能证明除法，不能证明可发布 P/E。
- **价格证据不足：** `price_source=fixture_completed_close` 只是标签；
  `price_freshness_policy=provisional_fixture_only` 没有完成/可见截止、有效期规则和
  价格是否最新的可验证记录；annual EPS 没有与价格匹配的每股调整基础。
- **Capex sign 缺失：** 负数 capex 场景期待 69,987，但没有源符号规则；
  按当前 FR-07 必须先有负值代表 outflow 的证据，不能直接 `abs()`。
  正数情形的减法也不能替代对符号语义的来源审查。
- **申报出处未独立验证：** fixture accession/`sec://` 标识不是本轮已验证的
  公开文件快照，不具有逐行发布内容哈希或人审。
- **期间证据不足：** 财年/季度标签和 duration 存在，但还缺发行人财历、
  可比性证据与规范化规则。instant 样例含 start/duration 字段；原始值应保留，
  不能靠应用默认猜出 canonical identity。
- **反例覆盖缺口：** currency/unit/missing accession 的一些现有 scenarios
  只测试 deferred TTM；需另补当前直接指标的反例，不能计作当前范围已覆盖。

冻结 fixture **不原地修改**。任何补充或更正都应是另一个待审参考版本，保留旧值、
变化理由、原始出处和影响范围；人工复核后再冻结。

## 待审反例与选数预期（不是已通过的实现测试）

其中 12 个反例另以 `counterexamples.draft.json` 记录可审阅的操作数变更、
预期和禁止替代项。其状态明确为未冻结、未执行的准备材料，不是通过报告。

| 输入变体 | 预期行为／需要保留的证据 |
|---|---|
| 删去 `revenue_q_2025_07_27` | 当前季度仍在，YoY=`n/a: missing_comparison`；保留当前 fact 引用和 missing_input_roles；不得用 2025-04-27 或六个月累计替代 |
| 只留下当前 `revenue_ytd_2026_07_26` | 单季指标 `n/a: missing_quarter`；不可把六个月当季度；不可相减倒推 |
| as_of=2026-06-01 | 排除 2026-08-26 才披露的 Q2；最新可见 Q1 为 2026-04-26；Q1 YoY +85.2%（财历可比性仍须证据） |
| FY2027 Q1 缺 FY2026 Q4 单季数 | QoQ=`n/a: missing_quarter`；不可跳回 Q3，也不可 annual−Q1..Q3 |
| 相近日期同值、同 fiscal position | 事实保留区分，无法判定则 ambiguous_period；不按日期近或值相等归并 |
| 同日两个无 lineage 的 accession | ambiguous_filing；按文件顺序取最后一个不合格 |
| 后来披露、明确 restates_fact_id 的 46,800 | 披露前不可见，披露后该期间使用新版本并保留 lineage；同比算术 +105.6% |
| 旧季度被较晚重述 | 当前期间仍按 fiscal year/quarter 选，不按 filed_at 将旧期当最新期 |
| 单位 USD_millions vs USD_thousands，未证明 scale 归一规则 | unit_mismatch；不能按数值大小猜单位 |
| 金额币种或价格/EPS 币种不同 | currency_mismatch；不增加 FX 算法 |
| annual EPS 单位不对或 split basis 未验证 | unit_mismatch 或 basis_mismatch；不得只因除法有结果就发 P/E |
| 价格未来、未完成、超出明确 freshness、截止时可见性不明 | 按对应原因 n/a；非交易日/当前未收盘可以用价格服务确认的上一完成收盘，但标实际 price_date |
| capex=-4,434，源 sign 未知 | n/a；只有来源规则证明负值代表支出，才规范成正向 outflow，FCF=69,987 |
| CFO=5、已验证支出 capex=10 | FCF=-5 合法；负利润和负 FCF 不应单纯因负数拒绝 |
| 零营收／零分母、非正增长基数、非正 EPS | zero_denominator / non_positive_base / non_positive_eps，保留已知输入 |
| 总资产<=0、流动负债<0 | invalid-input-domain；负利润不属于这一拒绝条件 |
| 52/53 周／闰年比较 | 有明确财历/覆盖证据可以比较；不能机械要求同天数，也不能只凭日期接近放行 |
| 当日披露但无法证明 cutoff 前公开 | availability_unknown；历史日级过滤不宣称 intraday PIT |

## Stage A 通过后的最小实现连接计划

这是计划，不是已接入路径：

1. 先做标准化事实和价格记录、纯 Decimal 计算、统一短表渲染；依赖注入接收本地快照，
   不导入 vendor，不从 Markdown 表格反解析权威事实。仅发 computed/n/a，不发 approximate。
2. 复用 `sec_edgar.py` 已有 `_STATEMENTS` concept 映射，但不能复用会压扁 accession、
   每条 unit 和 fiscal identity 的 `_as_of()` 返回值作为完整证据。
3. 团队入口现有 `route_to_vendor()` 返回文本，尚未找到能完整交付结构化事实、run_clock、
   FR-01 cache/query/provenance/counters 的稳定服务；先由注入入口交本地记录。
   后续在统一入口增加结构化 SEC query，财报工具共享同一原始快照，不能另建直连 SEC 通道。
4. 用户本轮指定**财务分析员第一次模型调用之前**准备短表；Stage A 通过后可在
   `create_fundamentals_analyst` 的调用方注入 run-owned metric provider，在现有
   system prompt partial 位置放结果表。保留 TOOLS 元组，模型无需主动调新工具。
   应对重复工具轮次复用已准备的结果，而不是每次重新取数。
5. 用不调用工具的假模型捕获真实 factory 输入，验证短表首轮可见，并确认报告状态不被改写。
   现阶段**未做此注入证明**，不将原先 FR-08 的提示词捕获误说为 FR-07 通过。
6. FR-08 全部保持原样；未来将相同短表传入 `SharedSummaryBrief` 的调用方 `metric_block`。
7. 正式 publication/recovery、模型关闭时仍有指标块、structured claim conflict、完整
   n/a 与缺包/坏包区分仍需团队后续接入；恢复必须读既存 bundle 而非重算或重新取数。

## 独立运行

仓库根目录，使用现有 Python 环境：

```powershell
& 'D:\CityU\cs5351\project\.venv\Scripts\python.exe' -B .\docs\fr07\recheck_fixture.py
& 'D:\CityU\cs5351\project\.venv\Scripts\python.exe' -B -m unittest discover -s .\docs\fr07 -p 'test_recheck_fixture.py' -v
```

可用 `--output <新的外部JSON路径>` 保存复核结果；独占创建，不覆盖旧文件。
退出码 0 **只表示算术与固定期望匹配**，输出中的 `stage_a` 仍为 BLOCKED。
这不是应用指标渲染入口，不应接给模型或作为已验证 financial metric bundle 发布。

## 本轮离线验证结果

- 独立算术核对：12/12 与固定期望匹配；对应现有 fixture 的数值期望也一致。
- 独立准备脚本测试：5/5 通过，覆盖 +105.9%、负利润/负 FCF、正负 half-up，
  并确认算术通过不产生 Stage A 通过声明。
- SEC、fundamentals units/lookahead、FR-08 summary/delivery/builder、分析员提示词和
  graph end-to-end 相关现有回归：**127 passed**，未运行无关 ranking 草稿。
- 独立准备脚本 Ruff：通过。
- `docs/req/validate_requirements.py --check`：当前共享虚拟环境缺少 `jsonschema`，
  在 import 阶段失败，**未运行成功**；未安装依赖或改写 requirements/validation-results。
  即使该静态验证器通过，也不会替代实际 Stage A 的来源和人工复核。

结果与本轮保留性哈希放在仓库外：
`C:\Users\24968\AppData\Local\Temp\opencode\fr07-stage-a-audit-01`。
已有 FR-08 源码、测试、文档和先前试跑产物均不修改。
