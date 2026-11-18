# GR-01 Stage A 冻结准备度复核

## 明确结论

**可以提交人工确认并冻结。** 就 GR-01 Stage A 的参考材料要求，未发现需要
再取数据、再加公司或再计算一套答案才能解决的阻塞缺口。

这不是已冻结或 Stage A 已通过的声明：仍须由用户确认来源独立性、财历/覆盖充分性
和价格口径，然后记录真实复核人与日期，并在确认后写入冻结版本、时间和摘要。
本轮没有代签，没有改变 `frozen_at=null`，没有开始 FR-07 应用实现。

本复核只针对现有候选的内容摘要：

`f1598a62aedffc28f5aeca54e1408ed508de5567e93d78569177db75980e0b9f`

原始 manifest、快照、答案、反例及原有记录均不修改。本文件是针对此候选的
补充评估，不重新定义 GR-01 的验收条件，不把后续应用验收要求升级成 Stage A 门槛。

## 按 Stage A 条款判断

| 条款 | 现有证据 | 判断 |
|---|---|---|
| GR-01-FC01：至少两个非 NVDA 稳定 issuer、真实财历、期间、指标及关键期间覆盖 | `reference_manifest.json:11–21`；`selected_facts.json`；`coverage.json`；Apple 10-K 财历段与 Exxon 年度 context | 满足提交人工确认的材料条件。两个不同 CIK、十项均有正例，非 revenue-only 或 all-n/a |
| GR-01-FC02：每个期望值/n/a 有可定位来源及独立派生、单位/舍入和实际内容哈希 | `source_manifest.json`、原 SEC HTML/companyfacts、`expected_metrics.json`、`facts_review.csv`、`metrics_review.csv`、`HUMAN_REVIEW.md` | 已有完整审阅链；Exxon 两项缺失不猜填，Apple 提供正例；P/E 复核见下 |
| GR-01-FC03：答案不由待测实现或共享关键处理路径生成 | `build_reference.py` 明确钉选 filing/#id，独立 Decimal/Fraction；`test_reference.py` 的无应用导入检查 | 本候选没有 FR-07 应用生成的期望值；独立性最终由人审确认，不能只靠计数为零 |
| GR-01-FC04：manifest、来源/派生、冻结版本/时间/摘要及人工复核 | `reference_manifest.json`、内容摘要、`validation.json`、人工清单 | 技术材料可提交；人工确认与正式冻结是下一步动作，不是尚缺另一套数据。当前不虚报通过 |

GR-01-FC05 的 Stage B 在应用实现开始后检查首次冻结先后顺序，本轮不要求提前
存在实现记录；FC06 的门槛方向仍保持：人审并冻结之前不开始应用实现。

## P/E 专项复核：日期与每股基础

### 收盘日期、截止和字段

- `price_records.json:9–21,37–49`：两只股票的 **actual_price_date 均为 2025-08-04**，
  `price_as_of=2025-08-05`，固定 cutoff 为 `2025-08-05T00:00:00-04:00`。
- 原数据：`sources/aapl-prices-actions.json` 中
  `/chart/result/0/indicators/quote/0/close/210`，以及 Exxon 对应文件的
  `/chart/result/0/indicators/quote/0/close/146`。
- 预期收盘展示值为 **203.35 USD**、**107.37 USD**。计算保留 JSON 原始十进制
  尾数，不把其当作额外市场精度；不是使用其他日期或 `regularMarketPrice`。
- `timestamp_raw=1754314200` 是该**日线 bar 的起始时间**：2025-08-04 13:30 UTC，
  即纽约 09:30。不能误称它是收盘时刻或把该 close 当成 09:30 已知价格。
  采用的是已结束历史常规交易日日线的 `quote.close`，日期为 8 月 4 日；纽约午夜
  cutoff 在该日 16:00 常规收盘之后。此为历史日级重建，不声称当时已保存 intraday PIT 快照。
- `price_records.json` 已写明只接受此固定截止前上一已完成常规交易日的新鲜度规则。
  原文件亦有非零 volume；字段选择和样本日期均与该规则一致。

### EPS、币种和调整基础

- `selected_facts.json` 的 `aapl.eps.fy2024`：
  `sources/aapl-2024-10k.htm#f-411`，年度 **6.08 USD/shares**。
- `xom.eps.fy2024`：`sources/xom-2024-10k.htm#f-124`，年度 **7.84 USD/shares**。
- 两者 unit XML 是 USD 除以 shares、scale=0；不是百万美元，不是季度/TTM EPS。
  两份价格的 meta.currency 也都是 USD。
- 取 `quote.close`，**未取 `adjclose`**；后者分别为 202.21827697753906 和
  102.73530578613281，不能不经处理就与上述财年 EPS 相除。
- 两份 `sources/*-share-basis-through-retrieval.json` 已保留覆盖年度 EPS 结束日至
  本次取数日的公司行动请求。返回日期范围为：Apple 2024-09-30..2026-11-17，
  Exxon 2024-12-31..2026-11-17，均无返回的拆股事件；因此没有已知需要跨拆股统一
  调整而尚未处理的价格/EPS 基础。这里依赖已保存事件源的覆盖，需你在人审中接受其充分性，
  不是另行声称证明了所有数据商绝无遗漏。
- 对照年度 EPS 与上述已完成收盘，预期 **Apple 33.4x，Exxon 13.7x**。

结论：现有 P/E 正例已具备可人工复核的日期、字段、币种、EPS 单位与基础证据，
不因“尚待人工确认”就自动改成 n/a，也无需重取相同数据。人审若发现事件源或
完成证据确有缺陷，再按 GR-01-FC02 针对具体缺陷处理；本轮未发现这种矛盾。

## 十项和关键期间场景

`coverage.json:2–74` 覆盖全部十项：季度/年度营收同比、季度营收环比、三种利润率、
流动比率、负债资产比、已披露期间 FCF、财年 P/E。
Apple 十项都有数值正例；Exxon 八项有数值、毛利率与营业利润率为有出处的 n/a。
总共 18 数值＋2 n/a，已避免只有缺失情形却没有正例。

| 关键期间或错误场景 | 直接复用的现有证据 |
|---|---|
| 去年同财季、立即前季的单季度 | `selection_plan.json`、`selected_facts.json` 的两家公司 current/prior-year/prior-quarter 三条 revenue；`expected_metrics.json` 的 YoY/QoQ |
| 不能拿上季度当去年同季 | `controlled_variants/wrong_previous_quarter_as_yoy.json` |
| 单季与累计不可混用 | `controlled_variants/ytd_as_quarter.json`；Apple 九个月与 Exxon 六个月 CFO/capex 原始 context |
| 未来披露不可见 | `controlled_variants/future_disclosure.json`：真实 filed_at=2025-08-04，受控 as_of=2025-08-03，应排除 |
| 缺去年同季／缺直接 Q4 不可补算 | `controlled_variants/missing_yoy_comparison.json`、`current_only_without_q4.json` |
| 年度财历差异及 52/53 周／闰年 | Apple 年报 text:435,782（2024 为 52、2023 为 53 周）；Exxon 2024/2023 的 Jan1..Dec31 contexts（366/365 天），保存实际覆盖差异，不按近日期匹配 |
| instant 余额与 duration 不混用 | 两公司 current_assets/current_liabilities/assets/liabilities 的实际 instant context；与 quarter/ytd/annual 各自分开 |
| 单位／币种／价格基础不兼容 | `controlled_variants/unit_mismatch.json`、`currency_mismatch.json`、`price_basis_mismatch.json` |
| 未来价格不可用 | `controlled_variants/future_price.json` |
| 符号、非正增长基数、非正 EPS | `controlled_variants/unknown_capex_sign.json`、`non_positive_growth_base.json`、`non_positive_eps.json`；源 capex 支出规则及原始 sign/scale 已保存 |

这些是 Stage A 参考输入与预期，不是已经执行 FR-07 应用行为测试。

## 原 coverage 中的“未补齐边界”是否阻止本次冻结

`coverage.json:78–83` 的五项属于前轮保守记录，**不能直接等同于 Stage A 五个阻塞项**。

- 真实重述／同日 accession 冲突：后续 FR-07-FC03 的选数/冲突行为验收应覆盖；
  GR-01-FC01 并未要求必须收集一个真实冲突申报才能冻结这套十项参考。
- 直接 Q4 正例：目前已有季度正例和缺 Q4 的禁止倒推反例；Stage A 未规定必须四个季度
  都有正例。无需为此扩大样本。
- 当日 cutoff 可见性未知：这是后续 FR-07-FC06 的运行时边界。当前固定历史日期已有
  披露可见性正例与未来披露反例，不构成本套参考缺失。
- 原始负号 capex 正例：已经有两家公司可核实的正向支付规则与未知 sign 反例；
  Stage A 没有要求 capex 正负两种数据商编码都必须来自真实公司才可冻结。
- 更多非交易日／未收盘价格服务场景：后续 FR-07-FC04 应补对应行为测试；本次 P/E
  已有截止前上一完成收盘正例和未来价格反例，不必为此重新取数。

因此，本次不新增证据采集或公司。上述项目保留为后续应用测试计划，不被删除，
也不把 Stage A 准备度结论扩大成 FR-07 全部验收完成。

## 本轮检查和下一步

本轮只对已有文件执行只读一致性检查，结果通过：14 个来源快照、30 条事实、
20 条指标、十项正例家族和 12 个受控反例前提均与原 manifest 相符，候选摘要未变。
未重取数据，未运行 TradingAgents 或 LLM，未改旧资料，未冻结、提交或推送。

你需核对的最小集合：

1. 本文件的 P/E 专项与上述四个价格/事件 JSON、两个年报 EPS 元素。
2. `coverage.json`、`expected_metrics.json` 或 `metrics_review.csv`，确认十项定义与期间。
3. `HUMAN_REVIEW.md` 的身份/财历、来源独立性及逐项数字；完整出处已在那里列明。
4. 确认接受上述 Stage A 覆盖充分性和历史日级价格口径。

收到你的明确确认后，下一步才记录人审确认与实际冻结版本/时间/摘要；
冻结完成后才开始 FR-07 应用实现。
