"""Generate review aids and a DRAFT manifest. Does not approve or freeze sources."""

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def save(name, obj):
    with (ROOT / name).open("x", encoding="utf-8") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aids():
    plan, facts, prices, rows = (load(n) for n in ("selection_plan.json", "selected_facts.json", "price_records.json", "expected_metrics.json"))
    retrievals = [json.loads(line) for line in (ROOT / "retrievals.jsonl").read_text().splitlines()]
    for entry in retrievals:
        assert entry["sha256"] == digest(ROOT / entry["saved_file"])
        entry["publisher"] = "U.S. Securities and Exchange Commission" if "sec.gov/" in entry["url"] else "Yahoo Finance (price and corporate-action history)"
    save("source_manifest.json", {"retrieval_time_semantics": "request-start UTC; response Date retained separately",
                                  "sources": retrievals})
    columns = ("fact_id", "subject_id", "concept", "raw_display", "raw_ix_sign", "raw_scale", "value", "unit", "currency",
               "fiscal_year", "fiscal_quarter", "span", "period_start", "period_end", "duration_days_inclusive", "filed_at",
               "accession", "carrying_filing_fy", "carrying_filing_fp", "filing_file", "inline_element_id", "inline_context_ref",
               "companyfacts_file", "companyfacts_pointer", "selection_rationale")
    with (ROOT / "facts_review.csv").open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for fact in facts.values():
            writer.writerow({key: fact.get(key) for key in columns})
    columns = ("reference_id", "metric_id", "status", "reason", "formula_id", "formula_version", "formula", "input_values",
               "input_fact_ids", "period", "input_currency", "unit", "output_scale", "rounding", "resolution", "expected_display", "missing_input_roles")
    with (ROOT / "metrics_review.csv").open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), (dict, list)) else row.get(key) for key in columns})
    review = ["# 人工复核清单（全部待签核，未冻结）", "",
              "每个方框均未完成。数字可由下列公式独立复算；computed 是参考候选结果，不是人审通过。",
              "原始 HTML 的 #id 可在浏览器定位或在文本中搜索；companyfacts JSON pointer 是另一份 SEC 结构化证据。", "",
              "## 先核对发行人、财历及价格", "",
              "- [ ] **发行人身份**：sources/aapl-submissions.json 与 aapl-companyfacts.json 的 cik/name 应为 0000320193 / Apple；XOM 对应为 0000034088 / Exxon Mobil。两个稳定 CIK 不同，均非 NVDA。",
              "- [ ] **Apple 财历**：inspection/aapl-2024-10k.text.txt:170,435,782；inspection/aapl-2025q3-10q.text.txt:277。预期：9 月最后一个星期六结束；2024/2025 各 52 周，2023 为 53 周、额外周在 Q1。季度比较为各自 Q3，不是自然季度标签。",
              "- [ ] **XOM 财历**：inspection/xom-2024-10k.text.txt:9 与 annual revenue 的 XBRL context；预期 2024-01-01..2024-12-31、2023-01-01..2023-12-31。inspection/xom-2025q2-10q.text.txt:97-98 及 Q2/Q1 context 分别为 Apr1..Jun30、Jan1..Mar31。这是源期间证据，不只是名称。",
              "- [ ] **52/53 周及闰年可比性**：selection_plan.json 的 annual_comparability；接受按明确披露的完整财年比较、保留实际天数差异，不做周数调整，也不因 364/371 或 365/366 天不同就自动失败。",
              "- [ ] **EPS 单位**：AAPL 年报 #f-411、XOM 年报 #f-124；各自 usdPerShare 单位是 USD/shares、scale=0；不得按金额 millions 再缩放。预期 6.08、7.84 USD/share。",
              "- [ ] **Capex 原始符号**：Apple Q3 10-Q #f-329、现金流 text:230,253；XOM Q2 #f-230、现金流 text:195,205。预期 XBRL 正值 9,473M、12,181M；表格括号表示投资支出。FCF 从 CFO 扣正向支付，不能任意 abs()。XOM 不用更宽的 capex-and-exploration 指标替代此 PP&E 项。",
              "- [ ] **已完成价格**：price_records.json 与 sources/*-prices-actions.json 指定 timestamp/quote.close 索引。预期实际交易日 2025-08-04，USD；AAPL 203.35、XOM 107.37（仅展示到分，计算保留原始序列化小数），volume 非零，固定截止为次日 00:00 America/New_York，前一正常交易日已完成。",
              "- [ ] **价格口径与证据充分性**：核对 price_records.json 中未使用 adjclose；查 sources/*-share-basis-through-retrieval.json 的请求区间、events，年 EPS 结束至取数日没有返回 split events。确认普通股价格与 EPS 同一每股基础、历史会话与新鲜度规则充分。如事件源或历史完成证明不足，将 P/E 改为 n/a 并保留缺口，不能直接签核。此为 2026 年取数的历史重建，不宣称 2025 年已保存 intraday 快照。",
              "- [ ] **收入定义差异**：XOM Total revenues and other income 含其他收益；Apple 为 Total net sales。同一公司的比较保持概念一致，不把两家收入定义或 XOM 归属股东净利/合并净利混同。", "", "## 二十条指标候选逐项核对", ""]
    for row in rows:
        review.extend([f"### [ ] {row['reference_id']}",
                       f"- 看：`expected_metrics.json` 中 reference_id=`{row['reference_id']}`；公式 `{row['formula']}`，版本 `{row['formula_version']}`。",
                       f"- 期间：`{json.dumps(row['period'], ensure_ascii=False)}`；输入币种 USD；输出 `{row['unit']}`；舍入 `{row['rounding']}`／`{row['resolution']}`。"])
        for identifier in row["input_fact_ids"]:
            fact = facts[identifier]
            review.append(f"- 核对 `{identifier}`：`{fact['filing_file']}#{fact['inline_element_id']}`，context `{fact['inline_context_ref']}`；原文 `{fact['raw_display']}`，scale={fact['raw_scale']}，原始 ix sign={fact['raw_ix_sign']}，基础值 `{fact['value']} {fact['unit']}`；`{fact['period_start']}..{fact['period_end']}`，FY={fact['fiscal_year']} Q={fact['fiscal_quarter']}，{fact['span']}；filed={fact['filed_at']}，accession={fact['accession']}。")
            review.append(f"  - 再核 SEC 结构化事实：`{fact['companyfacts_file']}` 的 `{fact['companyfacts_pointer']}`。选中原因：{fact['selection_rationale']}")
        if row["metric_id"] == "pe_fy":
            price = prices[row["issuer"]]
            review.append(f"- 价格：`{price['source_file']}` 的 `{price['json_pointer']}`，raw close=`{price['value']}`；price_date={price['actual_price_date']}；与上面的年度 EPS 相除，不用 TTM。")
        if row["status"] == "n/a":
            review.append(f"- 预期：**n/a / {row['reason']}**；缺少 `{row['missing_input_roles']}`。查目标 XOM 10-Q 主损益表和 companyfacts：无直接标准 GrossProfit/OperatingIncomeLoss，不能用税前利润或分部利润替代。Apple 的两项有正例。")
        else:
            review.append(f"- 操作数按顺序：`{row['input_values']}`；预期：**{row['expected_display']} {row['unit']}**；精确分数（含百分比/FCF 显示 scale）：`{row['exact_rational_result']}`。")
        review.append("")
    review.extend(["## 十二个受控反例（不是应用测试通过记录）", ""])
    for path in sorted((ROOT / "controlled_variants").glob("*.json")):
        case = load(str(path.relative_to(ROOT)))
        review.append(f"- [ ] `{path.relative_to(ROOT)}`：原记录 `{case['base_record_id']}`；改动 `{case['controlled_override']}`；预期 `{case['expected']}`。{case['independent_rationale']} 对照 selected_facts.json/price_records.json 确认原始记录和 SEC 文件未修改。")
    review.extend(["", "## 最后核对与签核", "",
                   "- [ ] source_manifest.json 每份 URL、取数日期、申报号（另见 filing_metadata.json）、实际字节数和 SHA-256；不是 URL 字符串的哈希。",
                   "- [ ] 参考脚本不导入 TradingAgents，不复用未来应用选数器；所有候选事实由明确 filing/#id 钉选，计算为 Decimal 与 Fraction 双重复核。",
                   "- [ ] coverage.json 十项指标均至少一个正例；对未补齐的真实 restatement/same-day filing、直接 Q4 正例、当日未知 cutoff、负号 capex 来源等逐项判断是否必须补齐后才可冻结。",
                   "- [ ] 复核人与证据独立性、覆盖充分性、价格口径签核记录目前为空；不把本清单、数字匹配或静态 fixture 当作人工通过。",
                   "- [ ] 人审后另建签核与冻结版本/时间/摘要，保留本候选及历史材料；不得倒签或事后修改期望值来迎合实现。", ""])
    with (ROOT / "HUMAN_REVIEW.md").open("x", encoding="utf-8") as handle:
        handle.write("\n".join(review))
    print("Review aids generated: 30 fact rows, 20 metric rows, 12 controlled variants.")


def manifest():
    excluded = {"reference_manifest.json", "validation.json", "preservation_after.json"}
    files = {str(path.relative_to(ROOT)).replace("\\", "/"): digest(path)
             for path in ROOT.rglob("*") if path.is_file() and path.name not in excluded
             and "__pycache__" not in path.parts}
    candidate = {
        "reference_version": "sec-reference-draft-v1", "status": "pending_human_review_not_frozen",
        "created_at_utc": datetime.now(UTC).isoformat(), "frozen_at": None,
        "stage_a": "NOT_PASSED_PENDING_HUMAN_REVIEW_AND_GAP_RESOLUTION", "stage_b": "not_applicable",
        "application_implementation_started": False, "implementation_generated_expected_value_count": 0,
        "independence": "Explicit SEC filing/#id pins + independent reference-only Decimal/Fraction scripts; no application imports. Business/source independence still needs human review.",
        "issuers": [{"cik": "0000320193", "ticker": "AAPL", "calendar": "52/53-week last Saturday September"},
                    {"cik": "0000034088", "ticker": "XOM", "calendar": "January 1..December 31"}],
        "source_manifest": "source_manifest.json", "facts": "selected_facts.json", "prices": "price_records.json",
        "expected_metrics": "expected_metrics.json", "coverage": "coverage.json", "human_checklist": "HUMAN_REVIEW.md",
        "requirements_sha256": digest(ROOT.parents[2] / "docs/req/requirements.yaml"),
        "files": files,
        "digest_projection": "Canonical sorted compact JSON of root fields except manifest_content_sha256 and human_review. File list excludes this manifest and subsequent validation/preservation reports; no self/review digest cycle.",
        "human_review": {"status": "pending", "reviewer": None, "reviewed_at": None, "evidence": None},
    }
    projection = {k: v for k, v in candidate.items() if k != "human_review"}
    candidate["manifest_content_sha256"] = hashlib.sha256(json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    save("reference_manifest.json", candidate)
    print("Draft manifest generated; NOT frozen, human review pending.")


if __name__ == "__main__":
    import sys
    {"aids": aids, "manifest": manifest}[sys.argv[1]]()
