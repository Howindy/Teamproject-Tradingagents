# FR-01 / CR-01 Risk List

Status: **personal draft / pending team review**

Likelihood and impact: L = low, M = medium, H = high. Status values: open,
mitigated (design in place, not yet verified), closed.

| ID | Risk | Likelihood | Impact | Trigger / early signal | Mitigation | Contingency | Status |
|---|---|---|---|---|---|---|---|
| R-01 | The team context-assembler design adopts a different policy for downstream report context | M | H | DMCB-OD-02 not approved | Present CR-01 as the always-on L3 policy within the team design; share EL-12 | Replace CR-01 with a literal-match quality requirement built on EL-07 | Open |
| R-03 | Analysts ignore the brief format | M | L | Fallback share high in `MON-CR01-02` | Deterministic fallback still bounds size and keeps gaps | Revise analyst prompt wording (versioned prompt) | Mitigated |
| R-04 | Briefs remove detail the debaters need; ratings drift | M | M | Offline review identifies lost evidence or misleading condensed context | Configurable limit; gaps and verified figures always kept | Raise the limit after review; any saving remains an estimate | Open |
| R-06 | The model keeps recomputing figures despite the tool and instruction | M | M | Literal-match share stays near 85% | Code-appended block gives downstream agents verified values regardless | Strengthen prompt; consider citation enforcement later | Mitigated |
| R-07 | SEC vendor text format changes | L | H | Parser tests fail on new output | Parser tests on recorded fixtures; version check of header lines; malformed tables give `n/a` | Update parser and fixtures via ADR change | Mitigated |
| R-08 | Reviewers reject approximate TTM EPS | L | L | Review comment | `pe_fy` always shown beside `pe_ttm` | Drop `pe_ttm` | Mitigated |
| R-09 | Coding agent writes both calculator and expected values, making tests circular | M | H | Expected values in tests match code output with no recorded source | References come from earnings releases or hand calculation, written by a team member into the task specification; source recorded beside each value | Reviewer rejects tests without a recorded source | Mitigated |
| R-10 | Look-ahead through price or late filings | L | H | Latest input date after analysis date | As-of filter in the adapter; two-date test (FR-01-AC5) | Block merge until fixed | Mitigated |
| R-13 | Generated code violates the module split (I/O inside the calculator) | M | M | Import audit test fails | Structural constraint in governance files; import-audit test as CI gate | Agent regenerates the module from the constraint | Mitigated |
| R-14 | Coding-agent token cost is high | M | L | Large session token counts | Small, scoped tasks; versioned prompts; record tokens per task (EL-P4) | Split tasks further | Open |
| R-15 | Team source layout decision (`src/` vs `TradingAgents/`) changes paths | M | L | Layout decision | Paths in docs given relative to the package root | Update trace matrix after the decision | Open |
| R-17 | Users see marker text in reports | L | L | Markers visible in a renderer | HTML-comment markers | Strip markers at display time in a later change | Mitigated |
