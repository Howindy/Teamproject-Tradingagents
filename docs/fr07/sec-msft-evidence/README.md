# 参考集外公司证据：Microsoft（MSFT），as_of 2025-08-05

用途：验证通用 SEC 数据入口。公司、日期和指标都是本轮实际取数与计算的结果；
未修改任何冻结参考文件。**这不是新的 GR-01 参考集**，只是适配器证据。

## 数据来源与快照

| 文件 | 内容 |
|---|---|
| `msft-companyfacts.json` | SEC `companyfacts/CIK0000789019.json` 原始快照（5.4 MB），经 `sec_edgar.company_facts` 的共享缓存路径取得 |
| `msft-submissions.json` | SEC submissions 快照，用于 CIK/名称/申报元数据 |
| `capture.py` | 复现脚本：真实 SEC 缓存 → 适配器 → 计算器 → 保存证据 |
| `selected_facts.jsonl` | 程序实际选中的 1,228 条规范化事实（含期间、财年/财季、披露日、单位、申报号） |
| `selected_metrics.json` | 十项指标、每个指标的操作数事实、期间、公式与渲染文本 |

发行人：MICROSOFT CORP，CIK **0000789019**，SEC `fiscalYearEnd=0630`（6 月财年）。

## 实际算出的指标

| metric_id | 结果 | 期间 / span | 关键操作数 |
|---|---|---|---|
| revenue_yoy_q | **13.3%** | 2025-01-01..2025-03-31 / quarter | 70,066 / 61,858（FY2024 Q3 比较期，非申报年度标签） |
| revenue_yoy_a | **14.9%** | 2024-07-01..2025-06-30 / annual | 281,724 / 245,122 |
| revenue_qoq | **0.6%** | 2025-01-01..2025-03-31 / quarter | 70,066 / 69,632（FY2025 Q2，前一申报季度） |
| gross_margin | **68.7%** | 同上 quarter | 48,147 / 70,066 |
| operating_margin | **45.7%** | 同上 quarter | 32,000 / 70,066 |
| net_margin | **36.9%** | 同上 quarter | 25,824 / 70,066 |
| current_ratio | **1.4x** | at 2025-06-30 / instant | 191,131 / 141,218 |
| liabilities_to_assets | **44.5%** | at 2025-06-30 / instant | 275,524 / 619,003 |
| fcf_reported_span | **71,611 USD_millions** | 2024-07-01..2025-06-30 / annual | CFO 136,162 − PP&E 支付 64,551 |
| pe_fy | **38.9x** | FY2025 年度 EPS | 2025-08-04 收盘 530.397… ÷ EPS 13.64 |

**没有 `n/a`。** 一个容易误判的点：截至 2025-08-05，MSFT 最新**单季度**报告是
FY2025 Q3（2025-03-31）。Q4 只出现在 FY2025 10-K 的年度数里，因此没有被倒推为单季
——最新季度指标停在 Q3，符合“不得用年度减三个季度”的规则。

期间与 span 核对：
- 同比与环比的所有操作数都是 `span=quarter`，不存在拿九个月/年度累计冒充单季。
- 比较期事实的 `fiscal_year/quarter` 由**该事实自身覆盖的期间**推导
  （2024-01-01..2024-03-31 → FY2024 Q3），而不是复制承载申报的 `fy=2025`。
- 现金流与资产负债表分别只用 `annual`/`instant`，与季度指标分开。

## 单次真实模型请求

- 配置：`deepseek-flash`，`https://api.deepseek.com`，temperature 0，
  `max_tokens=8192`，`max_retries=0`，显式 `extra_body={"thinking":{"type":"disabled"}}`。
- 路径：`create_fundamentals_analyst` 的 **wrap-up** 分支（不绑定工具），输入为固定的
  已取得财报摘录 + FR-07 指标表。
- 结果：`finish_reason=stop`，非空可见文本，无工具调用，输入 2,364 / 输出 2,943 tokens，
  16.37 秒。推理 token 字段未报告（null，不记 0）。
- 一次 HTTP 422：客户端把 LangChain 的 `human` 角色直接发出，API 只接受 `user`；
  该请求没有产生任何生成内容。修正本地角色映射后只再发一次。
  记录在 `live/attempt-01-rejected.json`。

## 提示词与报告是否用了程序结果

`live/verification.json`（脚本 `verify_live.py`）逐项检查：

- 指标表 **在**真实请求的 system prompt 中（`live/prompt_capture.txt`）。
- 离线捕获的提示词字符数 **6,716 = 真实请求的 `prompt_chars` 6,716**，
  说明实际发送的提示词与捕获版本一致。
- 生成报告（`live/report.md`）引用了**全部十项**程序结果；
  自行对比 2025-03-31 的额外推导被明确标注 `unverified derivation`，
  TTM 被明确写成“deliberately not computed”。
