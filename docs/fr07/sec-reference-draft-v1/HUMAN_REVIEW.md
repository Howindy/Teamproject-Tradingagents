# 人工复核清单（全部待签核，未冻结）

每个方框均未完成。数字可由下列公式独立复算；computed 是参考候选结果，不是人审通过。
原始 HTML 的 #id 可在浏览器定位或在文本中搜索；companyfacts JSON pointer 是另一份 SEC 结构化证据。

## 先核对发行人、财历及价格

- [ ] **发行人身份**：sources/aapl-submissions.json 与 aapl-companyfacts.json 的 cik/name 应为 0000320193 / Apple；XOM 对应为 0000034088 / Exxon Mobil。两个稳定 CIK 不同，均非 NVDA。
- [ ] **Apple 财历**：inspection/aapl-2024-10k.text.txt:170,435,782；inspection/aapl-2025q3-10q.text.txt:277。预期：9 月最后一个星期六结束；2024/2025 各 52 周，2023 为 53 周、额外周在 Q1。季度比较为各自 Q3，不是自然季度标签。
- [ ] **XOM 财历**：inspection/xom-2024-10k.text.txt:9 与 annual revenue 的 XBRL context；预期 2024-01-01..2024-12-31、2023-01-01..2023-12-31。inspection/xom-2025q2-10q.text.txt:97-98 及 Q2/Q1 context 分别为 Apr1..Jun30、Jan1..Mar31。这是源期间证据，不只是名称。
- [ ] **52/53 周及闰年可比性**：selection_plan.json 的 annual_comparability；接受按明确披露的完整财年比较、保留实际天数差异，不做周数调整，也不因 364/371 或 365/366 天不同就自动失败。
- [ ] **EPS 单位**：AAPL 年报 #f-411、XOM 年报 #f-124；各自 usdPerShare 单位是 USD/shares、scale=0；不得按金额 millions 再缩放。预期 6.08、7.84 USD/share。
- [ ] **Capex 原始符号**：Apple Q3 10-Q #f-329、现金流 text:230,253；XOM Q2 #f-230、现金流 text:195,205。预期 XBRL 正值 9,473M、12,181M；表格括号表示投资支出。FCF 从 CFO 扣正向支付，不能任意 abs()。XOM 不用更宽的 capex-and-exploration 指标替代此 PP&E 项。
- [ ] **已完成价格**：price_records.json 与 sources/*-prices-actions.json 指定 timestamp/quote.close 索引。预期实际交易日 2025-08-04，USD；AAPL 203.35、XOM 107.37（仅展示到分，计算保留原始序列化小数），volume 非零，固定截止为次日 00:00 America/New_York，前一正常交易日已完成。
- [ ] **价格口径与证据充分性**：核对 price_records.json 中未使用 adjclose；查 sources/*-share-basis-through-retrieval.json 的请求区间、events，年 EPS 结束至取数日没有返回 split events。确认普通股价格与 EPS 同一每股基础、历史会话与新鲜度规则充分。如事件源或历史完成证明不足，将 P/E 改为 n/a 并保留缺口，不能直接签核。此为 2026 年取数的历史重建，不宣称 2025 年已保存 intraday 快照。
- [ ] **收入定义差异**：XOM Total revenues and other income 含其他收益；Apple 为 Total net sales。同一公司的比较保持概念一致，不把两家收入定义或 XOM 归属股东净利/合并净利混同。

## 二十条指标候选逐项核对

### [ ] aapl.revenue_yoy_q
- 看：`expected_metrics.json` 中 reference_id=`aapl.revenue_yoy_q`；公式 `(current/prior_same_fiscal_quarter - 1)*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-03-30", "period_end": "2025-06-28", "fiscal_year": 2025, "fiscal_quarter": 3, "span": "quarter"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `aapl.rev.q3.2025`：`sources/aapl-2025q3-10q.htm#f-59`，context `c-19`；原文 `94,036`，scale=6，原始 ix sign=+，基础值 `94036000000 USD`；`2025-03-30..2025-06-28`，FY=2025 Q=3，quarter；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax/units/USD/110`。选中原因：Current FY2025 Q3 separately reported three-month Total net sales.
- 核对 `aapl.rev.q3.2024`：`sources/aapl-2025q3-10q.htm#f-60`，context `c-20`；原文 `85,777`，scale=6，原始 ix sign=+，基础值 `85777000000 USD`；`2024-03-31..2024-06-29`，FY=2024 Q=3，quarter；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax/units/USD/98`。选中原因：Same filing's prior-year three-month June 29 2024 column, same fiscal Q3; NOT filing fy=2025 copied to prior fact.
- 操作数按顺序：`['94036000000', '85777000000']`；预期：**9.6 %**；精确分数（含百分比/FCF 显示 scale）：`825900/85777`。

### [ ] aapl.revenue_yoy_a
- 看：`expected_metrics.json` 中 reference_id=`aapl.revenue_yoy_a`；公式 `(current_fy/prior_fy - 1)*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2023-10-01", "period_end": "2024-09-28", "fiscal_year": 2024, "fiscal_quarter": null, "span": "annual"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `aapl.rev.fy2024`：`sources/aapl-2024-10k.htm#f-378`，context `c-1`；原文 `391,035`，scale=6，原始 ix sign=+，基础值 `391035000000 USD`；`2023-10-01..2024-09-28`，FY=2024 Q=None，annual；filed=2024-11-01，accession=0000320193-24-000123。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax/units/USD/99`。选中原因：FY2024 full-year consolidated Total net sales from annual income statement.
- 核对 `aapl.rev.fy2023`：`sources/aapl-2024-10k.htm#f-379`，context `c-19`；原文 `383,285`，scale=6，原始 ix sign=+，基础值 `383285000000 USD`；`2022-09-25..2023-09-30`，FY=2023 Q=None，annual；filed=2024-11-01，accession=0000320193-24-000123。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax/units/USD/87`。选中原因：FY2023 full-year comparative, with explicitly disclosed 53-week calendar.
- 操作数按顺序：`['391035000000', '383285000000']`；预期：**2.0 %**；精确分数（含百分比/FCF 显示 scale）：`155000/76657`。

### [ ] aapl.revenue_qoq
- 看：`expected_metrics.json` 中 reference_id=`aapl.revenue_qoq`；公式 `(current/immediately_preceding_fiscal_quarter - 1)*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-03-30", "period_end": "2025-06-28", "fiscal_year": 2025, "fiscal_quarter": 3, "span": "quarter"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `aapl.rev.q3.2025`：`sources/aapl-2025q3-10q.htm#f-59`，context `c-19`；原文 `94,036`，scale=6，原始 ix sign=+，基础值 `94036000000 USD`；`2025-03-30..2025-06-28`，FY=2025 Q=3，quarter；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax/units/USD/110`。选中原因：Current FY2025 Q3 separately reported three-month Total net sales.
- 核对 `aapl.rev.q2.2025`：`sources/aapl-2025q2-10q.htm#f-62`，context `c-20`；原文 `95,359`，scale=6，原始 ix sign=+，基础值 `95359000000 USD`；`2024-12-29..2025-03-29`，FY=2025 Q=2，quarter；filed=2025-05-02，accession=0000320193-25-000057。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax/units/USD/106`。选中原因：Directly reported immediately preceding FY2025 Q2; no subtraction or nearest-column substitution.
- 操作数按顺序：`['94036000000', '95359000000']`；预期：**-1.4 %**；精确分数（含百分比/FCF 显示 scale）：`-132300/95359`。

### [ ] aapl.gross_margin
- 看：`expected_metrics.json` 中 reference_id=`aapl.gross_margin`；公式 `gross_profit/revenue*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-03-30", "period_end": "2025-06-28", "fiscal_year": 2025, "fiscal_quarter": 3, "span": "quarter"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `aapl.gross.q3.2025`：`sources/aapl-2025q3-10q.htm#f-75`，context `c-19`；原文 `43,718`，scale=6，原始 ix sign=+，基础值 `43718000000 USD`；`2025-03-30..2025-06-28`，FY=2025 Q=3，quarter；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/GrossProfit/units/USD/331`。选中原因：Gross margin amount (not percentage), same consolidated quarter as revenue.
- 核对 `aapl.rev.q3.2025`：`sources/aapl-2025q3-10q.htm#f-59`，context `c-19`；原文 `94,036`，scale=6，原始 ix sign=+，基础值 `94036000000 USD`；`2025-03-30..2025-06-28`，FY=2025 Q=3，quarter；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax/units/USD/110`。选中原因：Current FY2025 Q3 separately reported three-month Total net sales.
- 操作数按顺序：`['43718000000', '94036000000']`；预期：**46.5 %**；精确分数（含百分比/FCF 显示 scale）：`1092950/23509`。

### [ ] aapl.operating_margin
- 看：`expected_metrics.json` 中 reference_id=`aapl.operating_margin`；公式 `operating_income/revenue*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-03-30", "period_end": "2025-06-28", "fiscal_year": 2025, "fiscal_quarter": 3, "span": "quarter"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `aapl.operating.q3.2025`：`sources/aapl-2025q3-10q.htm#f-91`，context `c-19`；原文 `28,202`，scale=6，原始 ix sign=+，基础值 `28202000000 USD`；`2025-03-30..2025-06-28`，FY=2025 Q=3，quarter；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/OperatingIncomeLoss/units/USD/227`。选中原因：Operating income, same quarter and currency/scale.
- 核对 `aapl.rev.q3.2025`：`sources/aapl-2025q3-10q.htm#f-59`，context `c-19`；原文 `94,036`，scale=6，原始 ix sign=+，基础值 `94036000000 USD`；`2025-03-30..2025-06-28`，FY=2025 Q=3，quarter；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax/units/USD/110`。选中原因：Current FY2025 Q3 separately reported three-month Total net sales.
- 操作数按顺序：`['28202000000', '94036000000']`；预期：**30.0 %**；精确分数（含百分比/FCF 显示 scale）：`705050/23509`。

### [ ] aapl.net_margin
- 看：`expected_metrics.json` 中 reference_id=`aapl.net_margin`；公式 `reported_net_income/revenue*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-03-30", "period_end": "2025-06-28", "fiscal_year": 2025, "fiscal_quarter": 3, "span": "quarter"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `aapl.net.q3.2025`：`sources/aapl-2025q3-10q.htm#f-107`，context `c-19`；原文 `23,434`，scale=6，原始 ix sign=+，基础值 `23434000000 USD`；`2025-03-30..2025-06-28`，FY=2025 Q=3，quarter；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/NetIncomeLoss/units/USD/331`。选中原因：Net income, same quarter and consolidated reporting scope.
- 核对 `aapl.rev.q3.2025`：`sources/aapl-2025q3-10q.htm#f-59`，context `c-19`；原文 `94,036`，scale=6，原始 ix sign=+，基础值 `94036000000 USD`；`2025-03-30..2025-06-28`，FY=2025 Q=3，quarter；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax/units/USD/110`。选中原因：Current FY2025 Q3 separately reported three-month Total net sales.
- 操作数按顺序：`['23434000000', '94036000000']`；预期：**24.9 %**；精确分数（含百分比/FCF 显示 scale）：`585850/23509`。

### [ ] aapl.current_ratio
- 看：`expected_metrics.json` 中 reference_id=`aapl.current_ratio`；公式 `current_assets/current_liabilities`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": null, "period_end": "2025-06-28", "fiscal_year": null, "fiscal_quarter": null, "span": "instant"}`；输入币种 USD；输出 `x`；舍入 `ROUND_HALF_UP`／`0.1x`。
- 核对 `aapl.current_assets`：`sources/aapl-2025q3-10q.htm#f-179`，context `c-22`；原文 `122,491`，scale=6，原始 ix sign=+，基础值 `122491000000 USD`；`None..2025-06-28`，FY=None Q=None，instant；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/AssetsCurrent/units/USD/136`。选中原因：Current balance at June 28 2025, not the comparison year-end balance.
- 核对 `aapl.current_liabilities`：`sources/aapl-2025q3-10q.htm#f-201`，context `c-22`；原文 `141,120`，scale=6，原始 ix sign=+，基础值 `141120000000 USD`；`None..2025-06-28`，FY=None Q=None，instant；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/LiabilitiesCurrent/units/USD/136`。选中原因：Same June 28 2025 instant as current assets.
- 操作数按顺序：`['122491000000', '141120000000']`；预期：**0.9 x**；精确分数（含百分比/FCF 显示 scale）：`122491/141120`。

### [ ] aapl.liabilities_to_assets
- 看：`expected_metrics.json` 中 reference_id=`aapl.liabilities_to_assets`；公式 `total_liabilities/total_assets*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": null, "period_end": "2025-06-28", "fiscal_year": null, "fiscal_quarter": null, "span": "instant"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `aapl.liabilities`：`sources/aapl-2025q3-10q.htm#f-209`，context `c-22`；原文 `265,665`，scale=6，原始 ix sign=+，基础值 `265665000000 USD`；`None..2025-06-28`，FY=None Q=None，instant；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/Liabilities/units/USD/136`。选中原因：Total liabilities, same June 28 2025 balance date.
- 核对 `aapl.assets`：`sources/aapl-2025q3-10q.htm#f-189`，context `c-22`；原文 `331,495`，scale=6，原始 ix sign=+，基础值 `331495000000 USD`；`None..2025-06-28`，FY=None Q=None，instant；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/Assets/units/USD/138`。选中原因：Total assets, same June 28 2025 balance date.
- 操作数按顺序：`['265665000000', '331495000000']`；预期：**80.1 %**；精确分数（含百分比/FCF 显示 scale）：`5313300/66299`。

### [ ] aapl.fcf_reported_span
- 看：`expected_metrics.json` 中 reference_id=`aapl.fcf_reported_span`；公式 `operating_cash_flow - positive_reported_PP&E_payments`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2024-09-29", "period_end": "2025-06-28", "fiscal_year": 2025, "fiscal_quarter": 3, "span": "ytd"}`；输入币种 USD；输出 `USD_millions`；舍入 `ROUND_HALF_UP`／`exact source USD millions`。
- 核对 `aapl.cfo.ytd`：`sources/aapl-2025q3-10q.htm#f-321`，context `c-1`；原文 `81,754`，scale=6，原始 ix sign=+，基础值 `81754000000 USD`；`2024-09-29..2025-06-28`，FY=2025 Q=3，ytd；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/NetCashProvidedByUsedInOperatingActivities/units/USD/129`。选中原因：Cash generated by operating activities for nine months; do not label a single quarter.
- 核对 `aapl.capex.ytd`：`sources/aapl-2025q3-10q.htm#f-329`，context `c-1`；原文 `9,473`，scale=6，原始 ix sign=+，基础值 `9473000000 USD`；`2024-09-29..2025-06-28`，FY=2025 Q=3，ytd；filed=2025-08-01，accession=0000320193-25-000073。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/PaymentsToAcquirePropertyPlantAndEquipment/units/USD/100`。选中原因：Positive PaymentsToAcquirePropertyPlantAndEquipment XBRL amount; cash-flow row prints parentheses as investing outflow. Subtract positive payment, not arbitrary abs().
- 操作数按顺序：`['81754000000', '9473000000']`；预期：**72281 USD_millions**；精确分数（含百分比/FCF 显示 scale）：`72281`。

### [ ] aapl.pe_fy
- 看：`expected_metrics.json` 中 reference_id=`aapl.pe_fy`；公式 `completed_close/annual_diluted_eps; NOT TTM`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2023-10-01", "period_end": "2024-09-28", "fiscal_year": 2024, "fiscal_quarter": null, "span": "annual"}`；输入币种 USD；输出 `x`；舍入 `ROUND_HALF_UP`／`0.1x`。
- 核对 `aapl.eps.fy2024`：`sources/aapl-2024-10k.htm#f-411`，context `c-1`；原文 `6.08`，scale=0，原始 ix sign=+，基础值 `6.08 USD/shares`；`2023-10-01..2024-09-28`，FY=2024 Q=None，annual；filed=2024-11-01，accession=0000320193-24-000123。
  - 再核 SEC 结构化事实：`sources/aapl-companyfacts.json` 的 `/facts/us-gaap/EarningsPerShareDiluted/units/USD~1shares/320`。选中原因：Annual diluted EPS; usdPerShare unit definition is USD divided by shares; scale zero, not millions.
- 价格：`sources\aapl-prices-actions.json` 的 `/chart/result/0/indicators/quote/0/close/210`，raw close=`203.35000610351562`；price_date=2025-08-04；与上面的年度 EPS 相除，不用 TTM。
- 操作数按顺序：`['203.35000610351562', '6.08']`；预期：**33.4 x**；精确分数（含百分比/FCF 显示 scale）：`10167500305175781/304000000000000`。

### [ ] xom.revenue_yoy_q
- 看：`expected_metrics.json` 中 reference_id=`xom.revenue_yoy_q`；公式 `(current/prior_same_fiscal_quarter - 1)*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-04-01", "period_end": "2025-06-30", "fiscal_year": 2025, "fiscal_quarter": 2, "span": "quarter"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `xom.rev.q2.2025`：`sources/xom-2025q2-10q.htm#f-51`，context `c-19`；原文 `81,506`，scale=6，原始 ix sign=+，基础值 `81506000000 USD`；`2025-04-01..2025-06-30`，FY=2025 Q=2，quarter；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Revenues/units/USD/122`。选中原因：Current Q2 three-month Total revenues and other income, not six-month column.
- 核对 `xom.rev.q2.2024`：`sources/xom-2025q2-10q.htm#f-52`，context `c-20`；原文 `93,060`，scale=6，原始 ix sign=+，基础值 `93060000000 USD`；`2024-04-01..2024-06-30`，FY=2024 Q=2，quarter；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Revenues/units/USD/112`。选中原因：Prior-year Q2 comparative from the same filing/concept; source fy=2025 belongs to filing, not this fact.
- 操作数按顺序：`['81506000000', '93060000000']`；预期：**-12.4 %**；精确分数（含百分比/FCF 显示 scale）：`-57770/4653`。

### [ ] xom.revenue_yoy_a
- 看：`expected_metrics.json` 中 reference_id=`xom.revenue_yoy_a`；公式 `(current_fy/prior_fy - 1)*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2024-01-01", "period_end": "2024-12-31", "fiscal_year": 2024, "fiscal_quarter": null, "span": "annual"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `xom.rev.fy2024`：`sources/xom-2024-10k.htm#f-76`，context `c-1`；原文 `349,585`，scale=6，原始 ix sign=+，基础值 `349585000000 USD`；`2024-01-01..2024-12-31`，FY=2024 Q=None，annual；filed=2025-02-19，accession=0000034088-25-000010。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Revenues/units/USD/117`。选中原因：Reported FY2024 Revenues, same concept as comparative and quarter.
- 核对 `xom.rev.fy2023`：`sources/xom-2024-10k.htm#f-77`，context `c-18`；原文 `344,582`，scale=6，原始 ix sign=+，基础值 `344582000000 USD`；`2023-01-01..2023-12-31`，FY=2023 Q=None，annual；filed=2025-02-19，accession=0000034088-25-000010。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Revenues/units/USD/105`。选中原因：Reported full calendar FY2023 Revenues.
- 操作数按顺序：`['349585000000', '344582000000']`；预期：**1.5 %**；精确分数（含百分比/FCF 显示 scale）：`250150/172291`。

### [ ] xom.revenue_qoq
- 看：`expected_metrics.json` 中 reference_id=`xom.revenue_qoq`；公式 `(current/immediately_preceding_fiscal_quarter - 1)*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-04-01", "period_end": "2025-06-30", "fiscal_year": 2025, "fiscal_quarter": 2, "span": "quarter"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `xom.rev.q2.2025`：`sources/xom-2025q2-10q.htm#f-51`，context `c-19`；原文 `81,506`，scale=6，原始 ix sign=+，基础值 `81506000000 USD`；`2025-04-01..2025-06-30`，FY=2025 Q=2，quarter；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Revenues/units/USD/122`。选中原因：Current Q2 three-month Total revenues and other income, not six-month column.
- 核对 `xom.rev.q1.2025`：`sources/xom-2025q1-10q.htm#f-45`，context `c-1`；原文 `83,130`，scale=6，原始 ix sign=+，基础值 `83130000000 USD`；`2025-01-01..2025-03-31`，FY=2025 Q=1，quarter；filed=2025-05-05，accession=0000034088-25-000024。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Revenues/units/USD/119`。选中原因：Immediately preceding Q1, directly reported with same Revenues concept.
- 操作数按顺序：`['81506000000', '83130000000']`；预期：**-2.0 %**；精确分数（含百分比/FCF 显示 scale）：`-16240/8313`。

### [ ] xom.gross_margin
- 看：`expected_metrics.json` 中 reference_id=`xom.gross_margin`；公式 `gross_profit/revenue*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-04-01", "period_end": "2025-06-30", "fiscal_year": 2025, "fiscal_quarter": 2, "span": "quarter"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `xom.rev.q2.2025`：`sources/xom-2025q2-10q.htm#f-51`，context `c-19`；原文 `81,506`，scale=6，原始 ix sign=+，基础值 `81506000000 USD`；`2025-04-01..2025-06-30`，FY=2025 Q=2，quarter；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Revenues/units/USD/122`。选中原因：Current Q2 three-month Total revenues and other income, not six-month column.
- 预期：**n/a / missing_input**；缺少 `['xom.gross.q2.2025']`。查目标 XOM 10-Q 主损益表和 companyfacts：无直接标准 GrossProfit/OperatingIncomeLoss，不能用税前利润或分部利润替代。Apple 的两项有正例。

### [ ] xom.operating_margin
- 看：`expected_metrics.json` 中 reference_id=`xom.operating_margin`；公式 `operating_income/revenue*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-04-01", "period_end": "2025-06-30", "fiscal_year": 2025, "fiscal_quarter": 2, "span": "quarter"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `xom.rev.q2.2025`：`sources/xom-2025q2-10q.htm#f-51`，context `c-19`；原文 `81,506`，scale=6，原始 ix sign=+，基础值 `81506000000 USD`；`2025-04-01..2025-06-30`，FY=2025 Q=2，quarter；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Revenues/units/USD/122`。选中原因：Current Q2 three-month Total revenues and other income, not six-month column.
- 预期：**n/a / missing_input**；缺少 `['xom.operating.q2.2025']`。查目标 XOM 10-Q 主损益表和 companyfacts：无直接标准 GrossProfit/OperatingIncomeLoss，不能用税前利润或分部利润替代。Apple 的两项有正例。

### [ ] xom.net_margin
- 看：`expected_metrics.json` 中 reference_id=`xom.net_margin`；公式 `reported_net_income/revenue*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-04-01", "period_end": "2025-06-30", "fiscal_year": 2025, "fiscal_quarter": 2, "span": "quarter"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `xom.net.q2.2025`：`sources/xom-2025q2-10q.htm#f-107`，context `c-19`；原文 `7,082`，scale=6，原始 ix sign=+，基础值 `7082000000 USD`；`2025-04-01..2025-06-30`，FY=2025 Q=2，quarter；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/NetIncomeLoss/units/USD/223`。选中原因：Net income attributable to ExxonMobil; preserve row scope in net margin definition.
- 核对 `xom.rev.q2.2025`：`sources/xom-2025q2-10q.htm#f-51`，context `c-19`；原文 `81,506`，scale=6，原始 ix sign=+，基础值 `81506000000 USD`；`2025-04-01..2025-06-30`，FY=2025 Q=2，quarter；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Revenues/units/USD/122`。选中原因：Current Q2 three-month Total revenues and other income, not six-month column.
- 操作数按顺序：`['7082000000', '81506000000']`；预期：**8.7 %**；精确分数（含百分比/FCF 显示 scale）：`354100/40753`。

### [ ] xom.current_ratio
- 看：`expected_metrics.json` 中 reference_id=`xom.current_ratio`；公式 `current_assets/current_liabilities`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": null, "period_end": "2025-06-30", "fiscal_year": null, "fiscal_quarter": null, "span": "instant"}`；输入币种 USD；输出 `x`；舍入 `ROUND_HALF_UP`／`0.1x`。
- 核对 `xom.current_assets`：`sources/xom-2025q2-10q.htm#f-164`，context `c-6`；原文 `85,108`，scale=6，原始 ix sign=+，基础值 `85108000000 USD`；`None..2025-06-30`，FY=None Q=None，instant；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/AssetsCurrent/units/USD/133`。选中原因：June 30 2025 Total current assets.
- 核对 `xom.current_liabilities`：`sources/xom-2025q2-10q.htm#f-180`，context `c-6`；原文 `68,161`，scale=6，原始 ix sign=+，基础值 `68161000000 USD`；`None..2025-06-30`，FY=None Q=None，instant；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/LiabilitiesCurrent/units/USD/133`。选中原因：June 30 2025 Total current liabilities.
- 操作数按顺序：`['85108000000', '68161000000']`；预期：**1.2 x**；精确分数（含百分比/FCF 显示 scale）：`85108/68161`。

### [ ] xom.liabilities_to_assets
- 看：`expected_metrics.json` 中 reference_id=`xom.liabilities_to_assets`；公式 `total_liabilities/total_assets*100`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": null, "period_end": "2025-06-30", "fiscal_year": null, "fiscal_quarter": null, "span": "instant"}`；输入币种 USD；输出 `%`；舍入 `ROUND_HALF_UP`／`0.1 pp`。
- 核对 `xom.liabilities`：`sources/xom-2025q2-10q.htm#f-192`，context `c-6`；原文 `177,635`，scale=6，原始 ix sign=+，基础值 `177635000000 USD`；`None..2025-06-30`，FY=None Q=None，instant；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Liabilities/units/USD/133`。选中原因：June 30 2025 Total liabilities.
- 核对 `xom.assets`：`sources/xom-2025q2-10q.htm#f-172`，context `c-6`；原文 `447,597`，scale=6，原始 ix sign=+，基础值 `447597000000 USD`；`None..2025-06-30`，FY=None Q=None，instant；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/Assets/units/USD/147`。选中原因：June 30 2025 Total assets.
- 操作数按顺序：`['177635000000', '447597000000']`；预期：**39.7 %**；精确分数（含百分比/FCF 显示 scale）：`17763500/447597`。

### [ ] xom.fcf_reported_span
- 看：`expected_metrics.json` 中 reference_id=`xom.fcf_reported_span`；公式 `operating_cash_flow - positive_reported_PP&E_payments`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2025-01-01", "period_end": "2025-06-30", "fiscal_year": 2025, "fiscal_quarter": 2, "span": "ytd"}`；输入币种 USD；输出 `USD_millions`；舍入 `ROUND_HALF_UP`／`exact source USD millions`。
- 核对 `xom.cfo.ytd`：`sources/xom-2025q2-10q.htm#f-228`，context `c-1`；原文 `24,503`，scale=6，原始 ix sign=+，基础值 `24503000000 USD`；`2025-01-01..2025-06-30`，FY=2025 Q=2，ytd；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/NetCashProvidedByUsedInOperatingActivities/units/USD/116`。选中原因：Six-month Net cash provided by operating activities.
- 核对 `xom.capex.ytd`：`sources/xom-2025q2-10q.htm#f-230`，context `c-1`；原文 `12,181`，scale=6，原始 ix sign=+，基础值 `12181000000 USD`；`2025-01-01..2025-06-30`，FY=2025 Q=2，ytd；filed=2025-08-04，accession=0000034088-25-000042。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/PaymentsToAcquirePropertyPlantAndEquipment/units/USD/152`。选中原因：Positive PaymentsToAcquirePropertyPlantAndEquipment XBRL amount; Additions to property, plant and equipment shown as outflow in cash-flow statement. Not the broader management capex-and-exploration measure.
- 操作数按顺序：`['24503000000', '12181000000']`；预期：**12322 USD_millions**；精确分数（含百分比/FCF 显示 scale）：`12322`。

### [ ] xom.pe_fy
- 看：`expected_metrics.json` 中 reference_id=`xom.pe_fy`；公式 `completed_close/annual_diluted_eps; NOT TTM`，版本 `fr07-independent-direct-reference-v1`。
- 期间：`{"period_start": "2024-01-01", "period_end": "2024-12-31", "fiscal_year": 2024, "fiscal_quarter": null, "span": "annual"}`；输入币种 USD；输出 `x`；舍入 `ROUND_HALF_UP`／`0.1x`。
- 核对 `xom.eps.fy2024`：`sources/xom-2024-10k.htm#f-124`，context `c-1`；原文 `7.84`，scale=0，原始 ix sign=+，基础值 `7.84 USD/shares`；`2024-01-01..2024-12-31`，FY=2024 Q=None，annual；filed=2025-02-19，accession=0000034088-25-000010。
  - 再核 SEC 结构化事实：`sources/xom-companyfacts.json` 的 `/facts/us-gaap/EarningsPerShareDiluted/units/USD~1shares/214`。选中原因：Annual diluted EPS, USD/shares, scale zero.
- 价格：`sources\xom-prices-actions.json` 的 `/chart/result/0/indicators/quote/0/close/146`，raw close=`107.37000274658203`；price_date=2025-08-04；与上面的年度 EPS 相除，不用 TTM。
- 操作数按顺序：`['107.37000274658203', '7.84']`；预期：**13.7 x**；精确分数（含百分比/FCF 显示 scale）：`1533857182094029/112000000000000`。

## 十二个受控反例（不是应用测试通过记录）

- [ ] `controlled_variants\currency_mismatch.json`：原记录 `aapl.rev.q3.2024`；改动 `{'operation': 'currency', 'after': 'EUR'}`；预期 `{'outcome': 'n/a', 'reason': 'currency_mismatch'}`。Do not invent FX conversion; this override is not a real SEC disclosure. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\current_only_without_q4.json`：原记录 `xom.rev.q1.2025`；改动 `{'operation': 'target_fiscal_position', 'after': [2025, 1]}`；预期 `{'outcome': 'n/a', 'reason': 'missing_quarter'}`。This controlled input subset has current XOM FY2025 Q1 but no directly reported FY2024 Q4 quarter. Annual-minus-YTD remains forbidden; not a claim that no such fact exists anywhere. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\future_disclosure.json`：原记录 `xom.rev.q2.2025`；改动 `{'operation': 'analysis_as_of', 'after': '2025-08-03'}`；预期 `{'outcome': 'exclude', 'reason': 'future_filing_excluded'}`。Real filed_at 2025-08-04 exceeds controlled as_of; latest visible Q1 ends 2025-03-31. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\future_price.json`：原记录 `aapl.price`；改动 `{'operation': 'analysis_as_of', 'after': '2025-08-03'}`；预期 `{'outcome': 'exclude', 'reason': 'future_price_excluded'}`。2025-08-04 close cannot be used on 2025-08-03; 2025-08-01 is the preceding completed row. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\missing_yoy_comparison.json`：原记录 `aapl.rev.q3.2024`；改动 `{'operation': 'remove_record', 'after': None}`；预期 `{'outcome': 'n/a', 'reason': 'missing_comparison'}`。Preserve current-quarter ref and missing prior-year role; never neighboring column. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\non_positive_eps.json`：原记录 `xom.eps.fy2024`；改动 `{'operation': 'value', 'after': '-1'}`；预期 `{'outcome': 'n/a', 'reason': 'non_positive_eps'}`。No positive P/E from non-positive annual EPS. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\non_positive_growth_base.json`：原记录 `aapl.rev.q3.2024`；改动 `{'operation': 'value', 'after': '0'}`；预期 `{'outcome': 'n/a', 'reason': 'non_positive_base'}`。No numeric growth from a zero base; retain current fact ref. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\price_basis_mismatch.json`：原记录 `aapl.price`；改动 `{'operation': 'adjustment_basis', 'after': 'unverified_hypothetical_pre_split_basis'}`；预期 `{'outcome': 'n/a', 'reason': 'basis_mismatch'}`。Preserve real close; deliberately remove compatible per-share basis evidence. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\unit_mismatch.json`：原记录 `aapl.rev.q3.2024`；改动 `{'operation': 'unit', 'after': 'shares'}`；预期 `{'outcome': 'n/a', 'reason': 'unit_mismatch'}`。Change currency amount dimension to shares; no valid unit conversion exists. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\unknown_capex_sign.json`：原记录 `xom.capex.ytd`；改动 `{'operation': 'raw_sign_rule', 'after': 'unknown'}`；预期 `{'outcome': 'n/a', 'reason': 'unknown_capex_sign'}`。Source payment-positive rule deliberately removed; do not blindly abs(). 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\wrong_previous_quarter_as_yoy.json`：原记录 `aapl.rev.q3.2024`；改动 `{'operation': 'replace_record', 'after': 'aapl.rev.q2.2025'}`；预期 `{'outcome': 'n/a', 'reason': 'fiscal_period_mismatch'}`。Prior fiscal-year Q3 cannot be replaced by current-year Q2. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。
- [ ] `controlled_variants\ytd_as_quarter.json`：原记录 `aapl.rev.q3.2025`；改动 `{'operation': 'replace_record', 'after': 'aapl.rev.ytd.2025'}`；预期 `{'outcome': 'n/a', 'reason': 'missing_quarter'}`。Same end date does not make nine months into one quarter. 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。

## 最后核对与签核

- [ ] source_manifest.json 每份 URL、取数日期、申报号（另见 filing_metadata.json）、实际字节数和 SHA-256；不是 URL 字符串的哈希。
- [ ] 参考脚本不导入 TradingAgents，不复用未来应用选数器；所有候选事实由明确 filing/#id 钉选，计算为 Decimal 与 Fraction 双重复核。
- [ ] coverage.json 十项指标均至少一个正例；对未补齐的真实 restatement/same-day filing、直接 Q4 正例、当日未知 cutoff、负号 capex 来源等逐项判断是否必须补齐后才可冻结。
- [ ] 复核人与证据独立性、覆盖充分性、价格口径签核记录目前为空；不把本清单、数字匹配或静态 fixture 当作人工通过。
- [ ] 人审后另建签核与冻结版本/时间/摘要，保留本候选及历史材料；不得倒签或事后修改期望值来迎合实现。
