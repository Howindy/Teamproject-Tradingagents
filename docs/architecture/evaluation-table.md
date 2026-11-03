# FR-01 / CR-01 Architecture Evaluation Fragment

Status: **personal draft / pending team review**
Implementation status: **design only; no candidate has been implemented**
Evidence basis: **TradingAgents v0.7.0 source inspection and recorded baseline
`baseline-20261020-01`**

## 1. FR-01 — where derived metrics are computed

| Candidate | Correct period selection | Determinism | Offline testability | Added model cost | Reaches downstream agents | Decision |
|---|---|---|---|---|---|---|
| Prompt instruction only | Not enforced | No | No | None | Only via model prose | Rejected |
| Model self-check / second model verifier | Not enforced | No | No | One or more calls | Only via model prose | Rejected |
| Derived columns inside vendor statement output | Enforced | Yes | Yes | None | Only if the analyst copies them | Rejected: mixes filed and derived data in a filed-values contract |
| New vendor method behind the router | Enforced for SEC only | Depends on fallback vendor | Partial | None | Only if the analyst copies them | Rejected: vendor fallback changes results silently |
| Tool only | Enforced | Yes | Yes | Tool-call tokens | Only if the model calls it | Rejected as sole path |
| Appended block only | Enforced | Yes | Yes | Block tokens downstream | Always | Rejected as sole path: analyst prose stays unverified |
| **Pure calculator + tool + appended block** | **Enforced** | **Yes** | **Yes** | **Tool-call and block tokens** | **Always** | **Proposed** |

## 2. FR-01 — evidence from the baseline

| Observation | Value | Consequence for design |
|---|---|---|
| Model-stated Q2 FY2027 revenue growth | +68.6% (filed: +105.9%) | Period matching must use end dates |
| Q4 columns in quarterly income table | None | Q4 comparisons must be `n/a`, never substituted |
| Duplicate end dates | 2010-07-31 / 2010-08-01, equal values | Merge equal duplicates; `n/a` on conflict |
| Year-to-date cash-flow columns | 37 | Free cash flow on the reported span |
| Two P/E definitions | 44.3x (FY EPS) vs 27.4x (TTM EPS) | Always report both, labeled |
| Model-produced percentages, fundamentals report | 41 of 48 | Large share of figures depends on model arithmetic |
| Model-stated growth figures checked by hand | 6 of 7 correct | Errors are infrequent but land in the most-cited figure |

## 3. CR-01 — how downstream context is reduced

| Candidate | Expected saving | Keeps data gaps | Keeps verified figures | Added model calls | Offline testable | Decision |
|---|---|---|---|---|---|---|
| Limit-triggered compression only | ~0 (threshold never reached) | Yes | Yes | 0 | Yes | Rejected for this problem |
| Fixed truncation | High | No (gaps usually near the end) | No | 0 | Yes | Rejected as primary |
| Dedicated LLM summarizer node | High | Not guaranteed | Not guaranteed | +3-4 per run | No | Rejected |
| Fundamentals report only | Highest | Partial | Yes | 0 | Yes | Rejected: drops price levels and events |
| **Analyst brief + deterministic extraction and fallback** | **29%-33% of total input (estimate)** | **Yes (enforced)** | **Yes (enforced)** | **0** | **Yes** | **Proposed** |

## 4. CR-01 — brief size options

Estimates from the baseline reports (45,219 characters), five consumers, a
1,500-character verified block, and 3.5-4 characters per token.

| Limit per report | Saving (tokens) | Share of baseline input | Detail kept | Status |
|---:|---:|---:|---|---|
| 1,000 | 49.6k-56.7k | 32%-36% | About 4 key figures per report | Not selected |
| **2,000** | **44.6k-51.0k** | **29%-33%** | **About 8 key figures plus gaps and triggers** | **Proposed, provisional** |
| 3,000 | 39.6k-45.3k | 25%-29% | Most section conclusions | Fallback if quality drops |
| 4,000 | 34.6k-39.6k | 22%-25% | Near-full conclusions | Not selected |

## 5. Non-functional measurement options considered

| Candidate metric | Baseline | Valid before/after comparison | Finding | Decision |
|---|---|---|---|---|
| Share of report numbers "derivable from evidence" | 0% unverified | No | Prototype accepted all 75 checked percentages, including the wrong +68.6%, and 1,000 of 1,000 random values (26,690 candidate ratios) | Rejected: cannot detect the error it targets |
| Accuracy of the new tool against references | n/a (tool absent) | No | Compares two different objects (model prose vs tool output) | Moved into FR-01 acceptance criteria |
| Share of citations to metric IDs | 100% uncited by construction | No | Baseline is fixed by definition | Deferred (citation enforcement) |
| Share of model-computed percentages (literal match) | 85% (fundamentals), 46% (decision) | Yes | False-match rate 6.1% on 1,000 random values | Historical observation only; not an acceptance gate |
| **Downstream and total input tokens** | **156,541 total (measured)** | **Yes** | **Direct cost metric; per-call attribution needed** | Historical cost context; no reduction threshold in this revision |
| Final-rating equality | Not measured | No as stated | Ratings vary between identical runs | No rating-comparison acceptance criterion in this revision |

## 6. Verification scope

FR-01 and CR-01 are verified offline using recorded fixtures, independent
reference values, and fake model/vendor dependencies. Cost estimates are not
measured savings; decision-quality equivalence has not been established.

## 7. Baseline integration impact

| Baseline fact | Change | Reason |
|---|---|---|
| Fundamentals analyst has statement tools only | Add `get_derived_metrics` | Give the analyst verified values while it writes |
| Analyst report is model text only | Append the verified block in code | Every downstream reader gets verified values |
| Five consumers call `report_or_absent` | Call `report_brief_or_absent` | One entry point applies the brief policy |
| Analyst prompts have no brief section | Add the brief block to market, news, fundamentals prompts | The analyst summarizes its own report in a call that already happens |

These are planned changes. They do not describe behavior already implemented.
