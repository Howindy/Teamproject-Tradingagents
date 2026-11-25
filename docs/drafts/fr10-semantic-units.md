# FR-10 语义检查单元：评审草稿

日期：2026-11-25。状态：**实现后补充、评审草稿、待双方确认**。

发布准备已同步 main 的 PR #25（`a4af0db`）；使用标准 pytest 入口复验两套草稿，
28 passed（2.76秒）。本轮评审不要求对方采用这些问题或安排具体分工。

本文没有审批人、历史预批准、正式门禁通过或真实模型质量通过的含义。
不改动 main、生产提示词、现有评分规则、固定参考集、阈值或 CI 工作流。
本分支用于独立 Draft PR，实际提交、发布和审批状态以 GitHub 记录为准。

## 后续真实运行结果（2026-11-25）

本草稿的 14 项测试以及原合计 28 项仍是离线构造样例，不改变其性质。
后续另有真实模型执行：FR-10 的四个候选案例均已取得完整真实报告，
并通过 `fr10-local-gates-v1` 的五项本地检查。前三例复查保存的真实回答；
S04 首次仅有工具调用意图，改用原程序最终报告路径单独补跑后通过。

具体报告、API 用量、检查结果及版本见
[真实运行证据索引](../evidence/fr10-local-20261125/index.md)。
这是新增的本地真实回答验证，不把旧构造样例改称真实模型测试，
也不表示原冻结 D1–D5 或 GitHub 正式工作流通过。

## 检查对象

FR-10 提供确定性指标，财务分析员仍可能把数值、期间或可用性解释错。
这些单元描述“报告应保留什么、明确错误应如何识别”。

参考答案来自已有独立参考集 `docs/ci/financial-metrics-cases.json`，不是从当前
calculator 的输出反推。题目是在实现后根据这些已知要求整理的，属于回归检查，
不是未见数据集，也不能提供无偏的泛化表现结论。

## 七个单元

| 单元 | 检查问题 | 正确示例应保留 | 反例 / 既有评分器预期 |
|---|---|---|---|
| SU-01 | 季度同比和环比是否混淆 | AAPL 同比9.6%，环比-1.4% | 把同比写成-1.4% → critical failure |
| SU-02 | 缺值是否被补零 | XOM 毛利率n/a，missing_input | 毛利率0.0% → critical failure |
| SU-03 | 缺比较期是否拿其他期间替代 | 同比n/a，missing_comparison；环比仍-1.4% | 拿环比填同比 → critical failure |
| SU-04 | 累计现金流是否冒充单季 | FCF 72281 USD millions，九个月YTD | 称为Quarterly FCF → critical failure |
| SU-05 | 截止后价格是否被使用 | P/E n/a，price_not_completed；保留其他指标 | 仍声称P/E 33.4x → critical failure |
| SU-06 | 是否捏造申报来源 | 沿用输入的可定位来源 | 添加未知SEC accession → critical failure |
| SU-07 | 是否遗漏已有指标 | current_ratio 0.9x及期间/来源 | 整行遗漏 → needs_review |

详细问题、预期要点及反例在 [JSON 草稿](fr10-semantic-units.json) 中。
这些是全套基本面报告中的局部关注点；现有评分器仍检查完整参考案例。

## 程序如何检查

`test/offline/test_fr10_semantic_units_draft.py` 直接调用现有
`scripts/financial_metrics_eval.py::score_candidate_case`，不再实现第二套评分器。

每个单元有两种受控输入：

1. **正例**：复用现有测试的 `_good_report` 模板，按独立参考值生成合成报告，
   检查既有五维评分均无异议。
2. **反例**：只添加一个错误断言或删除一个指标行，检查对应 critical reason
   或 needs-review reason 确实出现。

因此共有 **14 个离线测试，实测14 passed（2.41秒），Ruff通过**。
这证明检查器能识别这些明确的构造样例，**不证明真实LLM写过这些回答或已通过评估**。
JSON 中的 `question` 是评估场景说明，本轮没有发送给模型，也未加入生产提示词。

## 当前限制与讨论范围

- 正例和反例是人工规则构造的测试文本，没有模型请求、供应商调用或 token/cost 结论。
- 使用既有套件及评分器，不新增通过门槛，不替代原有四案例正式语义评估。
- 现有评分器对否定句可能误判，例如“TTM P/E is not calculated”。本草稿未修改该行为，
  也没有将明确样例通过写成“任意自然语言都能正确判断”。
- 是否采用这些问题、是否与原单元重复、最终放入哪份评估材料，仍待双方讨论。
- 文件在 `codex/fr10-semantic-unit-draft` 独立评审分支，不直接合入 main。
  测试位于标准 offline 目录，发布分支后现有 pytest/CI 可能自动收集；这不代表
  新增了专用语义状态检查，也不代表已完成真实模型评估。

本地重跑：

```powershell
& 'C:\Users\24968\AppData\Local\Temp\opencode\financial-metrics-feature\venv\Scripts\python.exe' -B -m pytest test/offline/test_fr10_semantic_units_draft.py -q -p no:cacheprovider
```
