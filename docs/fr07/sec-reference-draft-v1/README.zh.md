# GR-01 Stage A：SEC 独立参考候选 v1（待人工复核，未冻结）

## 本轮状态

这是独立参考准备，不是 FR-07 应用实现。未启动 TradingAgents、未调用 LLM、
未改分析员/FR-08/数据入口/运行图，未提交或推送。旧 `docs/fr07/` 复核脚本、
NVDA 样例和反例草稿原样保留；本轮全部材料位于本子目录。

- **来源**：直接 SEC companyfacts/submissions JSON、六份 SEC 10-K/10-Q HTML；
  历史收盘和公司行动另用 Yahoo Finance 公共 chart 数据。14 份实际下载内容均保留。
- **发行人**：Apple CIK **0000320193**；Exxon Mobil CIK **0000034088**。
  用 SEC submissions、companyfacts 和实际 XBRL context 的 issuer 标识交叉确认，均非 NVDA。
- **分析日期**：2025-08-05；固定参考 cutoff **2025-08-05 00:00 America/New_York（−04:00）**。
  实际取数为 retrievals.jsonl 中的 2026 年 UTC 日期，不倒签为 2025 年现场快照。
- **结果**：30 条明确钉选的财务事实，20 条指标候选（18 数值＋2 n/a），十项指标均有正例；
  12 个以真实记录为底稿的受控反例，原始证据与变体分开。
- **状态**：`pending_human_review_not_frozen`。没有人工签核、没有冻结时间，
  **不能宣称 GR-01 Stage A 已通过，也未开始 FR-07 应用实现**。

## 两家公司与财历依据

### Apple：52／53 周财年

- 年报：`sources/aapl-2024-10k.htm`，accession **0000320193-24-000123**，
  2024-11-01 filed，FY2024 ended 2024-09-28。
- 可读投影：`inspection/aapl-2024-10k.text.txt:170,435,782`：
  财年为 **9 月最后一个星期六结束的 52 或 53 周**；FY2024 为 52 周，FY2023 为 53 周，
  额外周发生在 FY2023 第一季度。
- 本期 Q3 报告：**0000320193-25-000073**，2025-08-01 filed，
  `sources/aapl-2025q3-10q.htm`；其 Note 1 的可读投影 **:277** 明确 FY2025、FY2024 均为 52 周。
- 同一份 Q3 损益表的 **Three Months Ended** 比较 2025-03-30..2025-06-28 与
  2024-03-31..2024-06-29，均为各自 FY Q3，不拿 Nine Months Ended 累计值替代。
- 立即前一季由 **0000320193-25-000057**、2025-05-02 filed 的 Q2 10-Q 直接提供
  2024-12-29..2025-03-29 单季收入，非相减推导。

### Exxon Mobil：自然年

- 年报：`sources/xom-2024-10k.htm`，accession **0000034088-25-000010**，
  2025-02-19 filed；封面（可读投影 **:9**）为 fiscal year ended December 31, 2024。
- 进一步核对年度损益表 `#f-76`、`#f-77` 的 **实际 XBRL contexts**：
  2024-01-01..2024-12-31 与 2023-01-01..2023-12-31。不是只凭 fiscalYearEnd 标签认定自然年。
- 本期 Q2：**0000034088-25-000042**，2025-08-04 filed，
  `inspection/xom-2025q2-10q.text.txt:97–98` 的 Three Months Ended June 30，
  context 为 2025-04-01..2025-06-30；上年同季为 2024-04-01..2024-06-30。
- 立即前一季来自 **0000034088-25-000024**、2025-05-05 filed 的 Q1 10-Q，
  context 为 2025-01-01..2025-03-31。

**可比性说明**：年度是各自明确披露的完整财年。Apple 364/371 天以及 Exxon 闰年
366/365 天均保留，不机械要求相同天数，不用“日期很接近”代替财历证据，也不擅自做周数调整。

## 十项指标及独立候选结果

下表金额除 EPS/股价外按原表 **USD millions** 展示；百分比 half-up 到 0.1 个百分点，
比率到 0.1x；FCF 为已披露 span 的确切差。复算使用原始基础 USD 数值和 Decimal，
另用 Fraction 整数半入交叉验证。所有数值仍需人工审阅。

| 指标／公式 | Apple | Exxon Mobil |
|---|---|---|
| 季度营收同比 `(本期/去年同财季−1)×100` | 94,036 / 85,777 − 1 → **+9.6%** | 81,506 / 93,060 − 1 → **−12.4%** |
| 年度营收同比 `(本财年/上财年−1)×100` | 391,035 / 383,285 − 1 → **+2.0%** | 349,585 / 344,582 − 1 → **+1.5%** |
| 季度营收环比 `(本季/立即前季−1)×100` | 94,036 / 95,359 − 1 → **−1.4%** | 81,506 / 83,130 − 1 → **−2.0%** |
| 毛利率 `GrossProfit/营收` | 43,718 / 94,036 → **46.5%** | **n/a: missing_input**，无直接标准 GrossProfit |
| 营业利润率 `OperatingIncomeLoss/营收` | 28,202 / 94,036 → **30.0%** | **n/a: missing_input**，无直接标准 OperatingIncomeLoss |
| 净利率 `NetIncomeLoss/营收` | 23,434 / 94,036 → **24.9%** | 7,082 / 81,506 → **8.7%** |
| 流动比率 `流动资产/流动负债` | 122,491 / 141,120 → **0.9x** | 85,108 / 68,161 → **1.2x** |
| 负债占资产 `总负债/总资产` | 265,665 / 331,495 → **80.1%** | 177,635 / 447,597 → **39.7%** |
| 已披露期间 FCF `CFO−正向PP&E支付` | 九个月 81,754 − 9,473 → **72,281** | 六个月 24,503 − 12,181 → **12,322** |
| 财年口径 P/E `完成收盘/年度稀释EPS` | 203.35 / 6.08 → **33.4x** | 107.37 / 7.84 → **13.7x** |

P/E 上表股价仅为了可读性展示到分；实际复算保留原始 JSON 序列化小数：
203.35000610351562、107.37000274658203，不先用二进制 float 或擅自改价。
展示精度下结果与到分价格相同。源 JSON 的浮点序列化尾数不是新增市场精度。

Exxon `Revenues` 是 **Total revenues and other income**，包含其他收益；
Apple 为 Total net sales。各自的同比/环比保持同一概念。Exxon 净利采用源
`NetIncomeLoss` 行 **attributable to ExxonMobil**，不是含非控制权益的 7,354。
这种发行人口径差异明确保存，不跨发行人假装经济定义完全相同。
Exxon 缺失两项不能用税前利润、分部利润或随意相减的支出行猜填；Apple 提供两项正例。

## EPS、capex 与股价的重点证据

### EPS

- Apple 2024 10-K `#f-411`：**6.08**，`unitRef=usdPerShare`，`scale=0`。
- Exxon 2024 10-K `#f-124`：**7.84**，同为 USD/shares、scale=0。
- `selected_facts.json` 保存完整 unit XML（USD ÷ shares）及 companyfacts
  的 `units["USD/shares"]` pointer。**不能像原 NVDA fixture 那样标作 USD_millions。**

### Capex

- Apple Q3 `#f-329`：原始 XBRL 正数 **9,473×10^6 USD**，现金流表
  “Payments for acquisition of property, plant and equipment” 显示括号，位置见 text:230,253。
- Exxon Q2 `#f-230`：原始 XBRL 正数 **12,181×10^6 USD**，
  “Additions to property, plant and equipment” 在投资支出中以括号显示，位置见 text:195,205。
- 两条均是 `PaymentsToAcquirePropertyPlantAndEquipment`；参考规则是扣除该**正向支付额**，
  不做任意 `abs()`。保留 XBRL sign、scale、原文 row，避免把表格展示负号与 fact 数值符号混淆。
- CFO/capex 各自 start/end、span 完全相同；Apple 为九个月，Exxon 为六个月，均不叫单季度 FCF。

### 已完成收盘与每股口径

- 来源：`sources/*-prices-actions.json`，Yahoo 公共 daily chart；实际日期 **2025-08-04**，
  currency=USD，symbol、交易所、volume、timestamp、quote.close 的明确索引均在 `price_records.json`。
- 选的是 **quote.close，不是 adjclose**。后者数值不同，含股息调整，不能与未相应调整的 EPS 混用。
- 固定 cutoff 为次日纽约时间 00:00；8 月 4 日正常交易日的常规日收盘在截止前完成。
  本参考新鲜度规则限定为该午夜截止前的上一已完成正常交易日，不接受任意旧价格。
- 另保存 `sources/*-share-basis-through-retrieval.json`，查询覆盖年度 EPS 结束之后至本次取数日；
  返回的公司行动中无拆股记录。为审查历史价可能被后来拆股调整的问题，检查范围不只停在 2025 年分析日。
- 这构成**待审每股基础正例**，仍须人工核对事件源覆盖与历史会话/完成证据充分性。
  若复核认为事件源/完成性不足，P/E 应改记相应 n/a 并另补足正例，不能靠能相除就签核。
- 价格是 2026 年下载的历史重建，**不宣称 2025 年真实保存的 intraday point-in-time 快照**；
  不实现股票拆分或 FX 调整算法。额外访问 Nasdaq 交易时段网页曾超时，未把未取到的网页当成证据。

## 原始数据、显式选数与独立性

1. `fetch_source.py` 只负责显式 URL 下载，无应用导入、重试或模型；`retrievals.jsonl`
   和 `source_manifest.json` 保存 URL、实际保存文件、字节数、UTC 取数日期、响应头与内容 SHA-256。
   默认 User-Agent 使用明确标注的 placeholder contact，没有冒称真实联系方式；本轮保存的 14 个请求均为 HTTP 200。
2. `inspection/` 是原始 HTML 的离线文本/XBRL 投影；原件保留。投影自身也进入 manifest 哈希，
   checker 从原 HTML 重建并逐项比对，不只相信派生 JSON。
3. `selection_plan.json` 钉选具体 accession、文件与 inline `#id`，逐条写为什么是本季、
   去年同财季或前一季。参考脚本不复用应用通用 latest-fact 选取逻辑。
4. 对比列的 `companyfacts.fy/fp` 仍保留为 carrying_filing 字段。例：Apple 2024 Q3
   比较值在 2025 Q3 文件里，raw fy=2025；参考事实明确标为 **FY2024 Q3**，不复制 filing 标签。
5. `build_reference.py` 只按固定 ID 读取并交叉核 SEC companyfacts 与 HTML；
   Decimal/Fraction 算术产生可独立审阅答案，没有导入 FR-07 应用，也没有依据应用输出改期望。
   钉选到某份披露不等于实现了“跨所有 filing 自动选最新/消歧”的生产算法。

## 真实记录受控反例及覆盖限制

`controlled_variants/` 中 12 个独立文件保存完整底稿、原始 fact/price ID、
改动字段、预期排除或 n/a、理由，并明确 `is_real_disclosure=false`。
这些受控改动不是新 SEC 申报，也未覆盖写入原始证据。

重点反例：

- 用 Apple FY2025 Q2 的 95,359 冒充 FY2024 Q3 的 85,777：应 fiscal_period_mismatch，不能得到伪同比 −1.4%。
- 用 Apple 九个月累计 313,695 冒充季度 94,036：应 missing_quarter，不得因 end 相同就接受。
- 分析日退至 2025-08-03：Exxon Q2 的真实 filed_at=2025-08-04，应排除；已披露 Q1 为 2025-03-31。
- 单位或币种被受控改为 shares/EUR：预期 unit_mismatch/currency_mismatch，不自动 FX 或猜 scale。
- 保留真实价格但改成未验证的假设拆股基础：预期 basis_mismatch。
- 将 2025-08-04 价格放到 2025-08-03 分析日：排除未来价格，前一完成交易日实际为 2025-08-01。
- 删除同比比较、删除 sign 规则、非正基数/EPS、本参考子集缺直接 Q4 等反例，详见逐项清单。

一致性检查只验证这些变体确实对应原记录、输入前提与预期理由一致；
**没有 FR-07 应用，不能称其 n/a 行为已经由应用测试通过。**

尚未补齐的边界证据明确保留在 `coverage.json`：真实 restatement lineage／同日
accession 冲突、直接披露 Q4 正例、当日 cutoff 可见性未知、原始负号 capex 规则正例，
以及更多非交易日／当日未收盘价格服务场景。人工需判断这些是否应在初始冻结前补齐；
不把十个家族均有正例等同于整个 FR-07-FC01–FC10 完成。
`preparation_history/` 保存本轮准备阶段的初始表格／反例及元数据更正前版本，
不是活动参考输入；现用输入由 manifest 的文件指向与 `selection_plan.json` 决定。

## 人工从哪里开始

**首先打开 `HUMAN_REVIEW.md`**：

- 身份、财历、52/53 周与闰年、EPS、capex、股价口径各有未勾选检查项。
- 二十项指标逐项列出看哪个 HTML `#id`、companyfacts JSON pointer，核对哪个原数、期间、
  fiscal position、filed_at、币种/单位、公式/舍入，以及预期数字或 n/a。
- 十二个受控反例各列出原记录、具体改动与预期结果。
- 末尾保留人工独立性/充分性签核、覆盖缺口决策和冻结步骤，全部待人工完成。

表格辅助：`facts_review.csv`（30 行），`metrics_review.csv`（20 行），`metric_table.md`。

## 可重复的离线检查

从仓库根目录，使用现有环境，不重新下载：

```powershell
$py = 'D:\CityU\cs5351\project\.venv\Scripts\python.exe'
& $py -B docs/fr07/sec-reference-draft-v1/build_reference.py --check
& $py -B docs/fr07/sec-reference-draft-v1/validate_reference.py
& $py -B -m unittest discover -s docs/fr07/sec-reference-draft-v1 -p test_reference.py -v
```

首次生成使用的脚本保留，但生成入口采取独占创建，不覆盖旧快照/答案。
`reference_manifest.json` 的内容摘要排除自身 digest、人工审核字段和后续检查报告，
避免 self/review digest 循环；不是只对 URL 取哈希。**manifest 仍是 draft，frozen_at=null。**
检查成功只说明文件、引用、算术和覆盖声明的一致性，不表示人审完成或 Stage A 放行。

此前缺 `jsonschema` 的冻结需求验证器本轮未安装依赖或重写运行结果；
本子目录的独立检查使用 Python 标准库，不依赖 TradingAgents 或 jsonschema。
保留性报告为 `preservation_after.json`；本轮结果为 `validation.json`。
