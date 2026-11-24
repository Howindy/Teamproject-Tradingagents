# Round-04A 输出语义与场景检查：评审草稿

日期：2026-11-25。状态：**实现后补充、评审草稿、待双方确认**。

发布准备已同步 main 的 PR #25（`a4af0db`）；两套草稿使用标准 pytest 入口复验，
28 passed（2.76秒）。本说明供讨论，不代替另一方确认或安排实施。

范围是 Round-04A 的 FR-04、SB-01、INV-01，以及消费 FR-03 必要数据缺口的边界。
不重做 FR-10。没有模型请求、真实交易或正式语义评估结果，也没有倒填历史审批。

## 七个单元

| 单元 | 场景问题 | 正确结果 / 意义 | 反例关注点 |
|---|---|---|---|
| R4-SU-01 | 持仓占比30%、止损距离5%，恰好等于默认上限 | risk和gate均passed，正式Buy，原结论不改写 | 买入金额仅增加0.0000000001也应blocked，不靠显示舍入判断 |
| R4-SU-02 | 精确占比已略超过30%，模型仍称显示30%所以安全 | 正式REVIEW；超限原因保留在risk结果 | 模型文字不能代替精确计算 |
| R4-SU-03 | 入场100、止损90，距离10%超过5% | blocked/REVIEW，保留实际止损超限原因 | 模型要求忽略限制不会改变结果 |
| R4-SU-04 | 有Buy建议，但没有调用方提供的购买场景 | blocked/REVIEW，说明缺少scenario | 模型自行假设安全场景不等于收到合法输入 |
| R4-SU-05 | 风险通过，但必要财务数据缺失 | gate仍blocked，正式REVIEW并说明缺口 | 模型宣称资料齐全不能覆盖程序摘要 |
| R4-SU-06 | 风险计算内部异常，已有模型Buy建议 | risk=error，gate=blocked，正式REVIEW | 风险error不等于SB-01自身error，也不能沿用Buy |
| R4-SU-07 | 中间Buy与正式REVIEW不同，或正式字段互相矛盾 | 文件和记忆使用正式REVIEW；畸形结果在写入前拒绝 | 不能用中间建议覆盖已检查的保存结果 |

完整题目、固定输入、预期结果和反例在 [JSON 草稿](round04-semantic-units.json)。
期望依据是已定义的课堂阈值和输出契约，不是由被测函数计算后再填回。

## 实际检查方式

测试文件：`test/offline/test_round04_semantic_units_draft.py`。

- 前六项各有正常输入和反例，共12项。调用真实 `portfolio_risk.evaluate()` 和
  `final_recommendation.evaluate()`，检查数值、状态、正式评级、说明及输入不变。
- “模型反例”是人工编写的误导性建议文本。测试验证它不能覆盖程序结构化条件，
  **不代表真实LLM生成过这些句子**。
- 第七项有2项，调用实际 `record_decision()`、状态写入和记忆存储，比较正式结果；
  再确认矛盾字段被拒绝且已有记录不变。图构造使用既有的离线模型替身，没有模型调用。
- FR-04 详细原因属于 `portfolio_risk_result.reasons`，不要求被复制进SB-01顶层说明。
  初稿误把这两个位置混在一起，产生6项失败；核对既有契约后修正了测试读取位置，
  没有修改产品代码或隐藏失败。

**实测：本套14项与FR-10草稿14项共同运行，28 passed（2.60秒），Ruff通过。**

## 与正式语义门禁的区别

本地 `cfa79eb` 的公共登记中只有 financial-metrics 和 data-availability，
没有单独的 Round-04A 语义套件。本草稿没有新增登记、评分器、门槛或CI工作流。

这里检查的是风险、建议和正式输出的含义是否符合确定性契约，属于场景/输出验收。
它不能替代“真实模型读懂资料后是否提出合理建议”的语义质量评估，不能作为已执行
真实模型评估或已获批准的证据。测试源于已知要求，是实现后回归覆盖，不是盲测。

是否采用、是否与现有测试重复、最终放入哪份评估材料，仍待你和Yifan讨论。
当前与FR-10草稿共存于 `codex/fr10-semantic-unit-draft` 独立评审分支，发布和审批
状态以GitHub记录为准。现有CI可能收集这些offline测试，但本轮没有新增专用语义套件
或修改工作流；分支发布不等于正式语义评估通过。

本地重跑：

```powershell
& 'C:\Users\24968\AppData\Local\Temp\opencode\financial-metrics-feature\venv\Scripts\python.exe' -B -m pytest test/offline/test_round04_semantic_units_draft.py -q -p no:cacheprovider
```
