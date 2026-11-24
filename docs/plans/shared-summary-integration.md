# Shared-summary integration — SS-PREP-1

## 1. Status, evidence and approval boundary

**Proposed; human plan/test approval pending.** This checkpoint submits this plan and a factual AI-use entry only. No requirements activation, application/test implementation, model request, dependency installation, workflow dispatch, merge or acceptance is authorized by publication. Stop after the Draft PR; each subsequent checkpoint ends for human inspection.

Frozen inputs inspected on 2026-11-24:

| Input | Immutable reference / finding |
|---|---|
| Team main | `5c6e2caed5e4baceb136b5544ba5e283c0822cdb`; D1 v1.49.0, 13 requirements / 55 FCs, six active / 27 FCs; FR-07 remains deferred |
| Personal implementation | `origin/haoxi @ 7e676fb00fff319930685a9fa059265f3061aeff`; old `TradingAgents/tradingagents/run/` and `TradingAgents/tests/` paths; read-only reuse source, not an approval |
| Round 3 | `origin/round-03-fr03 @ 9e2c7793dc7d70fd2aeeecd480f78a5a81635614`; `docs/plans/round-03.md` and portfolio-test amendment, run-context / research-summary design; no claim that this proposed branch is integrated main |
| Financial PR | [PR #14](https://github.com/Howindy/Teamproject-Tradingagents/pull/14), inspected at `88d47e712f7eac6e6babc8d2e1b0dc87d17c4b17`; open, not merged; FR-10 and financial evaluation belong to the other session |
| Course | `C:\Users\24968\Downloads\CS5351-2026-2027-project.pdf`, physical pp. 6, 7, 10 read locally: unique module ownership, negative/independent tests, three-tier verification, co-evolving rules, genuine review/raw sessions, src/test layout, approval-before-code, six blocking gates and safety-critical human review/ADR |

Round 3 amendment records original P3 `d83abc909d6d7b40a7e7fabaff26ef971b9dbc2d` and user-supplied original non-author approval on PR #13; this plan does not deny that history or treat it as summary approval. The amendment's supplemental approval/CI enforcement remains separately pending in that document.

Read project `AGENTS.md`, `Prompt.md`, D1/schema, blueprint, ADR 001, invariants, trace matrix, runtime policy, state/memory, permissions, evaluation table, D3/D4 governance, human-only rules and CI inputs. The checked-in permission configuration requires explicit loading; file existence is not evidence of effective enforcement. Do not edit it or `.opencode/rules.md` to expand access. Before implementation the human must confirm the exact maintenance/implementation paths and command/output permissions below; OQ-07 is not closed by this plan.

Workspace: `D:\CityU\cs5351\project\Teamproject-Tradingagents-summary-prep`; branch `prep/shared-summary-integration`, created from fetched origin/main. Session moved here and cwd/root/branch rechecked. Original haoxi and financial-prep worktrees remain intact. Raw session export is not available yet; do not reconstruct a transcript from this summary.

## 2. Proposed D1 decision and numbering

Reactivate current **FR-07** for planned delivery, replacing its same-analyst-call / Unicode-character policy with **one separate LLM request over the four settled full reports**, strict structured JSON validation, deterministic rendering, protected program material, length validation and one reusable result for five roles. This is an explicit change request, not an interpretation that the current D1 already permits it. Obtain team approval and align D1/D2/D4 before dependent code.

Lineage: personal summary **FR-08 -> team FR-07** (already documented in D1 v1.33.0 history). Personal financial FR-07 is a different historical meaning; its new team requirement is FR-10 in PR #14. Preserve history and old fixture wire identifier `fr08-summary-v1` for compatibility; neither that identifier nor old config prefixes create a new active FR-08. New tests cite current FR-07 FCs. Do not import financial code, its old requirement, recovery, history, manifest or CR-01 acceptance.

Proposed replacement of the five FCs (IDs retained; wording changes require approval):

| FC | Proposed acceptance |
|---|---|
| FR-07-FC01 | At post-analyst join, one request sees all four complete settled report texts, returns exact schema, and is validated/rendered in program code. No analyst same-call summary changes, tools, repair call or summary-specific retry. Structure validation is not semantic truth verification. Empty/absent reports select deterministic fallback without a request. |
| FR-07-FC02 | Bull, Bear, Aggressive, Conservative and Neutral receive the same selected shared report material once per prompt, instead of four report blocks. Preserve their instructions, plans and debate history; other roles keep original report inputs. No hidden full-report copy bypasses replacement. |
| FR-07-FC03 | Budget uses the explicit deterministic token proxy defined in §4, including rendered labels/separators/protected text. Equality is allowed. Invalid/oversized/model-failed summaries fall back without clipping, retry or analysis termination. Invalid budget/counter setup disables the brief at the integration boundary, retaining full reports. No product default or whole-request token cap is approved here. |
| FR-07-FC04 | The caller supplies program evidence; FR-03 alone produces availability/completeness. All five roles receive the complete fixed research-start program block, once, also on every fallback. Preserve structured state and reasons/limitations; never reconstruct it from report keywords or LLM output. Missing FR-03 uses its fixed unavailable text, not fabricated completeness. |
| FR-07-FC05 | One result is reused across repeated debate calls; independent runs never share it. Full reports and saved reports remain unchanged. Disabled analysts are not called for a summary. Protected overflow rejects only the brief and restores full reports plus complete program material; ordinary analysis continues. No manifest/history/recovery prerequisite or extra data fetch. |

FR-03 is the functional producer dependency for final integration, not a prerequisite to migrate/test the standalone core with controlled program inputs. Remove FR-02 as a direct implementation dependency: this feature needs no new run identity, precise statistics or manifest. Existing callbacks remain intact. Do not remove the genuine dependency on actual FR-03 integration from final acceptance. If only this activation lands on today's main: seven active / 32 FCs, six deferred / 23 FCs, total 13/55; if PR #14 lands too: eight active / 42 FCs, six deferred / 23 FCs, total 14/65. Recalculate from actual merged D1, never overwrite FR-10 or hard-code counts in gates.

## 3. Reuse, ownership and authority

Reuse source `TradingAgents/tradingagents/run/{brief,summary,assembler,wiring,counter}.py` and the four existing summary/delivery/wiring test modules listed in §6. No wholesale cherry-pick: that branch also changes financial features and uses an obsolete source/test layout.

Keep one small replaceable assembly seam, `src/tradingagents/run/assembler.py`. It takes settled reports, **caller-supplied protected material**, explicit budget/counter and injected summary callable, and returns immutable selected material with mode/reason/counts. Financial table/citations are an optional opaque string, default empty: no FR-10 import, calculation, source lookup or metrics factory is required. Adapt the old metrics-specific argument internally if needed; do not invent a universal evidence framework. Missing optional finance input is not a failed summary.

| Primary owner | Responsibility / excluded authority |
|---|---|
| `run/summary.py` | Strict JSON parsing, fixed category/source rendering, one injected call, memoized success/fallback; no provider SDK, availability judgment or formal decision |
| `run/brief.py` | Protected-first reservation, complete-text measurement, deterministic fallback extraction; no financial arithmetic or completeness inference |
| `run/counter.py` | Named/versioned deterministic counter, not provider usage |
| `run/assembler.py` | Sole replaceable shared-material assembly; consumes program results, never owns risk, final decisions or registry |
| `run/wiring.py` | Explicit config/model envelope adapter; no global model or cross-run cache |
| Existing C-07 availability module (Round 3) | Sole five-field FR-03 summary and deterministic program-block renderer; no second implementation in summary modules |
| Existing C-10 first-research wrapper | Stage timing and publication of serializable material; reuse Yifan's final seam, do not introduce a competing top-level assembler node by default |
| Existing FR-04/SB-01 and entries/writers | Retain risk/final-result authority and pass-through contracts; the summary never writes proposal, risk result, gate, formal rating, reasons or decision |

Schema reuse: root exactly `schema_version`, `risks`, `triggers`, `conclusions`, `uncertainties`; each item exactly nonempty `text` and nonempty allowed `sources` list. Reject duplicate keys, NaN/Infinity, fences, unknown versions/source IDs, wrong types, all-empty categories and forged protected markers. Individual empty categories are allowed. Render category order Risks/Triggers/Conclusions/Uncertainties; normalize item whitespace and canonicalize source order market/news/sentiment/fundamentals. A source label is attribution, not verified support.

Scope of reuse: settle inputs once at analyst join, create/use one run-owned adapter and publish immutable text/metadata. Repeated reads, including concurrent reads, reuse the result and cached failures. Although the old core supports content-keyed multiple entries, integration must not regenerate after later observations or per role. Drop it at run end; keep locks, callables and adapter out of graph state/checkpoints. Only JSON-compatible delivered text/mode/reason/counts are stored. Preserve fresh-run/no-resume policy when it exists on synchronized main; do not add a new resume subsystem here.

The old `wiring._summary_model` merely extracts `.content`: it does **not** prove retries/tools/truncation/usage handling. Migration must supply a tested adapter that disables automatic retries and tools, rejects truncated or unusable envelopes/tool calls, and records available finish/usage metadata before validating text. Provider failure details/raw responses never enter consumer prompts or ordinary warnings; use fixed safe reasons. Preserve callback behavior without inventing FR-02 collectors or zero-filling unknown usage.

## 4. Budget, fallback and failure contract

**Chosen delivery budget unit: deterministic whitespace-token proxy**, `len(text.split())`, with explicit counter/model/policy identities. Keep `budget_unit: tokens` in the reused core contract but label every setting/evidence field as proxy tokens, not real tokenizer tokens. This makes the migrated implementation honest about its existing counter; it is not a claim of API-token accuracy. Do not adopt a new tokenizer dependency in this round. A later real-tokenizer change needs an explicit version/config/evaluation decision.

Policy retains M (protected reservation), C (narrative ceiling), T=M+C (initial total), H>=T (hard cap); no expansion, reference resolver or full-request context management. Count the actual assembled text including protection delimiters, labels, sources and separators, not an additive estimate. Protected material may exceed M if the complete delivery still fits T/H; never clip it to M. The old 4000/600 defaults and 1531/150/1381 test boundary are historical settings/fixtures, not approved production defaults. Explicit legal budget configuration is required; absent/invalid config uses full reports nonblockingly.

| Condition | Selected material / requests |
|---|---|
| Valid in-budget JSON | Protected material plus rendered narrative; exactly one summary request |
| Provider/model failure, invalid envelope/schema or oversized narrative | Same protected material plus deterministic extraction from original reports; no repair/retry; one attempted request retained in usage |
| Empty report / disabled analyst / no complete report set | Existing absence handling and deterministic extraction, no summary request; do not run the disabled analyst |
| Protected block alone exceeds T or H | `rejected` means brief rejected only: full reports/absence placeholders plus **complete** program material; zero summary requests; no clipped brief, hard analysis failure or new REVIEW |
| Invalid config/counter or assembly error at integration boundary | Fixed safe warning/reason; full reports/absence placeholders plus complete program material; configuration exceptions remain explicit in standalone core tests, boundary catches only brief preparation, not unrelated graph errors |
| Upstream data unavailable | Do not refetch or pretend success. Use settled reports/absence notices and the actual FR-03 missing/limitation block. Preserve original data exceptions where the existing flow propagates them; nonblocking summary fallback must not swallow primary analysis errors |
| FR-03 missing | Its fixed `program summary currently unavailable` block; no fabricated complete status, model call to recover availability, or use of financial success as completeness |

The full-report fallback is deliberately outside the brief cap; otherwise protection and nonblocking behavior conflict. It is **not** a guarantee of request-size safety. Normal instructions/history/plans are not managed by this feature.

Keep separate accounting: delivered proxy counts; any optional estimated API-token count with estimator identity; and actual provider-reported input/output/cached/reasoning usage, unknown fields null. Record summary request attempts, finish reason, latency, fallback frequency, downstream call count and provider usage including the extra summarizer. An API failure may still incur usage; do not label it free. No measured savings, CR-01 cost acceptance or semantic equivalence is established by proxy reduction. No actual model request is authorized by this plan approval alone.

## 5. FR-03 coordination with Round 3

Round 3 IF-24 obtains `research_availability_summary` once after analyst/memory join and supplies a local state copy to the **same first Bull call**. Later Bull/Bear and Research Manager read that fixed mapping. It remains five fields (`basic_completeness`, `applicability_note`, `observations`, `necessary_items`, `supplementary_limitations`) or null; C-07 alone computes it. Terminal `data_availability_summary` is separately prepared by entries and can differ.

Proposed coordinated integration, to be confirmed against Yifan's merged implementation:

1. Preserve first-research timing. Obtain/store the one FR-03 research snapshot using the existing wrapper; deterministic renderer supplies its entire program block, including observations, necessity gaps/reasons, supplementary limitations and applicability note. Do not extract only gap strings and discard the remainder.
2. That wrapper invokes the one assembly seam before calling Bull, using the same local state carrying snapshot and selected material. State publication alone is insufficient for first-call visibility. No new independent registry snapshot, data query or availability calculation inside the assembler.
3. One consumer-material helper in `agents/context.py` selects shared brief or full-report fallback and adds the **same** fixed program block once. If already contained in the protected block, the research consumer must not append its old standalone copy too. Select one explicit ownership path, not string-search removal/deduplication after prompt construction. Research Manager keeps full reports and its existing single FR-03 block; it is not a sixth brief consumer.
4. The three risk debaters receive that same frozen research-stage material, not freshly resampled availability or a second copy. They are advisory consumers, not the deterministic FR-04 risk check. Later check-time availability still belongs to the designated risk/check orchestration; terminal delivery still belongs to entries. Neither stage overwrites the research snapshot or causes summary regeneration.
5. Null and all fallback paths use the same renderer/unavailable block. Oversized program data remains intact even if this forces full-report fallback. Model text cannot replace program state. Repeated debates and extra observations add no summarizer request.

This changes D2's current no-compression/no-new-summary-call decisions; amend them explicitly with ADR 001 compatibility and a focused summary ADR before code. Current FR-03 producer/IF-06/IF-24 timing and SB-01/IF-09 authority stay intact. Do not assign C-21/IF-26, which PR #14 uses for finance; choose unused IDs only after synchronization. No new final-result or risk-check node is part of this work.

## 6. Exact proposed file scope and migration map

**This checkpoint changes only** `docs/plans/shared-summary-integration.md` and `docs/ai-use-log.yaml`. Everything below is a proposed later allowlist requiring the applicable checkpoint authorization, not immediate edit permission.

### A. Requirement/architecture alignment checkpoint

| Exact path | Bounded change |
|---|---|
| `docs/req/requirements.yaml` | FR-07 wording/FC01–05/dependencies/lineage, affected scope and current validation metadata; preserve FR-10 and past approvals |
| `architecture-blueprint.md` | Summary component ownership/seam, new-call exception and affected flow/non-goals; reconcile real active/deferred counts |
| `docs/architecture/adr/001-graph-internal-final-check.md` | Narrow first-research integration exception without changing formal authority |
| `docs/architecture/adr/003-shared-summary-integration.md` (new) | Single independent summary, proxy budget, nonblocking fallback, protected data and single injection ownership; confirm slot is still unused |
| `docs/architecture/invariants.md` | Preserve IR-01–05/07/11–14; amend only summary-related no-compression wording and test links |
| `docs/architecture/trace-matrix.md` | FR-07 FC mapping to migrated files/tests, partial versus final evidence |
| `docs/architecture/runtime-policy-catalog.md` | Local summary failure/fallback policy; no changed risk/formal policy |
| `docs/architecture/memory-design.md` | Serializable brief fields vs ephemeral adapter, original reports and memory behavior unchanged |
| `docs/architecture/evaluation-table.md` | Summary option rationale, prompt quality remains separately pending |
| `docs/code-governance/structural-constraints.md` | Unique summary module owners |
| `docs/code-governance/verification-constraints.md` | FR-07 FC scenarios and affected IR checks; retain previous gates |
| `AGENTS.md`, `Prompt.md`, `.agent/rules.md`, `CI.md`, `docs/ci/README.md` | Only affected active/deferred statements, summary timing and CI operation; no blanket workflow rewrite |

Human-only `.opencode/rules.md` and human-maintained permission setup are **not** agent edit paths. If their effective scope/wording blocks activation, present exact amendments to the human before dependent work; do not self-edit them. No automatic edits to schema, dependency manifests, prior frozen plans, finance ADR or source evidence.

### B. Core migration and directional tests

| New team path | Reused personal source / bounded adaptation |
|---|---|
| `src/tradingagents/run/__init__.py` | Minimal package marker, no service registry |
| `src/tradingagents/run/brief.py` | Old same-relative core; generic caller protection, unchanged extraction and whole-text validation |
| `src/tradingagents/run/summary.py` | Old same-relative core/schema/cache; cite current FR-07 and approved ADR |
| `src/tradingagents/run/counter.py` | Old proxy counter with honest unit documentation |
| `src/tradingagents/run/assembler.py` | Old seam; explicit generic program inputs and safe boundary fallback, no mandatory finance factory |
| `src/tradingagents/run/wiring.py` | Old config seam; tested one-attempt provider adapter, explicit budgets; construction must not cache across runs |
| `test/offline/test_downstream_brief.py` | Old `TradingAgents/tests/test_downstream_brief.py`; existing deterministic policy/negative tests |
| `test/offline/test_structured_summary.py` | Old corresponding JSON/cache/parallel/boundary tests |
| `test/offline/test_brief_delivery.py` | Old corresponding rendering/full-text/protected regression tests |

Tests reuse approved saved NVDA reports at `baseline/runs/baseline-20261020-01/results/NVDA/2026-10-19/reports/` and `transcripts/final_state.json` under that run, read-only. Replace obsolete `tests.*` imports with repository-compatible fixtures/imports; do not change `test/conftest.py` or relax its network blocking. Do not migrate unrelated old analyst marker/financial tests. Direct imported helpers may be moved into the approved test modules rather than importing a nonexistent legacy package.

### C. Final synchronized-main graph and regression checkpoint

Exact proposed application paths: `src/tradingagents/agents/context.py`, `src/tradingagents/agents/state.py`, `src/tradingagents/agents/researchers/bull_researcher.py`, `src/tradingagents/agents/researchers/bear_researcher.py`, `src/tradingagents/agents/risk_mgmt/aggressive_debator.py`, `src/tradingagents/agents/risk_mgmt/conservative_debator.py`, `src/tradingagents/agents/risk_mgmt/neutral_debator.py`, `src/tradingagents/graph/setup.py`, `src/tradingagents/graph/trading_graph.py`, `src/tradingagents/default_config.py`.

Exact test paths: `test/offline/test_downstream_wiring.py` (migrate and strengthen old test), `test/offline/test_graph_end_to_end.py` (only fixture/import/explicit schedule adaptations for added summary call). Reuse existing `test/offline/test_fr04_risk.py`, `test/offline/test_sb01_final_check.py`, `test/offline/test_reporting.py`, `test/offline/test_prompt_integrity.py`, `test/offline/test_layering.py` unchanged as selected regressions. FR-03 integration tests are run in full regression when they actually exist on main; not listed as missing required tests today.

No planned change to `src/cli/run.py`, `reporting.py`, Research Manager, Portfolio Manager, FR-04/SB-01 cores or availability producer: preserve their authority and use the existing research wrapper/context helper. If synchronized main makes any such edit necessary, stop that integration slice and approve the exact changed path/assertions first. Config key names/default enablement must be reconciled with actual main at this checkpoint; use neutral shared-summary names rather than implying financial coupling. Graph object reuse must initialize a new adapter/material per analysis.

### D. Semantic preparation / delivery checkpoint (separate specific approval)

Proposed exact paths: `docs/ci/shared-summary-cases.json`, `docs/ci/shared-summary-rubric.md`, `docs/ci/shared-summary-semantic-eval.yaml`, `scripts/shared_summary_eval.py`, `test/offline/test_shared_summary_evaluation.py`, `README.md`, and conditional compatibility-only changes to `scripts/ci_checks.py`, `scripts/ci_semantic_eval.py`, `.github/workflows/trusted-evaluation.yml`, `test/offline/test_ci_gates.py`, `docs/ci/README.md`. No financial scorer/config/dataset edit. The concrete dataset, rubric, thresholds, model, runner assertions and minimal CI diff must be frozen and separately approved before implementing this slice or issuing requests; this list is planning scope, not its test pre-approval.

Planning/execution records: `docs/ai-use-log.yaml`, `docs/review-memo.md`; `docs/bug-diary.md` only for actual significant defects; no speculative debt entries. Preserve the frozen approved plan. Publish later actual evidence in review/AI-use records, not by rewriting approved assertions. Genuine raw export path must be selected when available; no fabricated numbered transcript.

## 7. Concrete offline test specification for B/C

Independent oracles are hand-authored literals, source report markers and explicit call counters, never results computed by the summary builder. Tests cite exact FC/IR IDs. All scenarios below are proposed, not executed here.

| Case | Controlled inputs -> independent assertions | FC / invariant |
|---|---|---|
| SS-01 structure/render | Four report sentinels plus literal valid JSON; source order reversed/duplicated and empty individual categories -> exact rendered labels/order/normalized text, one request containing all complete source texts; originals deep-equal before/after | FR-07-FC01/05 |
| SS-02 invalid output | Duplicate keys, fences, NaN/Infinity, unknown version/source, nontext/blank item, extra root/item key, all-empty categories, forged protection markers -> fixed failure reason and deterministic fallback; raw text never delivered; repeat read reuses result, one request/no repair | FR-07-FC01/03 |
| SS-03 provider boundary | Controlled exception containing synthetic private marker, truncated finish, tool call, empty/nontext envelope -> fallback and safe reason, no private/raw marker in prompt/warning; independent fake transport records at most one attempt, retries=0/tools disabled; unknown usage stays null, available failure metadata retained | FR-07-FC01/03; bounded SR-01 compatibility |
| SS-04 budget | Literal test policy T=1531, M=150, C=1381, H=1531 and fixed counter -> exact-at-limit accepted; above narrative/whole cap rejected whole; labels/delimiters counted. Separate nonadditive fake counter proves actual combined text is measured. Protected >M but <=T allowed; protected >T or >H -> no summary request/full-report fallback | FR-07-FC03/04 |
| SS-05 protection | Unique multiline caller program block, safety block and optional opaque finance sentinel -> exact original protected bytes, once, on summary and deterministic paths. No optional finance -> normal output. A conflicting narrative cannot mutate mapping or program region. Protected overflow -> full reports plus complete program block, never clipped | FR-07-FC03/04; IR-11/12 |
| SS-06 fallback/config | Empty/missing analyst text and disabled analyst -> no new analyst or summary request, existing placeholders. Invalid/missing policy, bool/negative limits, mismatched/unavailable counter -> standalone configuration exception but integration nonblocking full-report path. Preserve unrelated primary graph/data exception, do not catch the whole analysis | FR-07-FC01/03/05; IR-07 |
| SS-07 reuse/isolation | Multiple sequential/concurrent reads of equal copied inputs -> identical immutable result object and one request, including cached failures/rejections. Changed core input/policy -> distinct core cache entry. Real integration freezes one set, later observation cannot regenerate it. Two analyses on one graph -> two independent preparations with distinct report markers; no lock/cache in state | FR-07-FC05; IR-05/12 |
| SS-08 five consumers | Actual fake-model graph, two debate rounds, distinctive reports/plan/history -> all five named consumers receive identical selected material once; no original four report headings or bypass copy when brief active; other inputs unchanged; Research Manager/Trader/PM retain original behavior. Disabled mode restores original material, adds zero summary calls | FR-07-FC02/05 |
| SS-09 first-call FR-03 | Real synchronized wrapper and fixed C-07 renderer with incomplete necessity + supplementary limitation + observation markers -> first Bull same invocation, later Bull/Bear and risk roles see complete same block once; Research Manager keeps its normal block once. Null -> fixed unavailable text. An intentionally update-only variant or doubled append must fail the prompt assertions | FR-07-FC04; FR-03-FC05 compatibility; IR-11/12 |
| SS-10 timing/authority | Later controlled FR-03 observation makes terminal block differ; research material stays fixed. Real collector integration when available; deterministic risk/final outputs never sourced from summary. Snapshot/check/report responsibilities unchanged, no extra fetch or risk/check rerun; marker capture detects model narrative replacing program status | FR-07-FC04/05; bounded IR-01/02/11–14 compatibility, not global invariant acceptance |
| SS-11 saves/fallback | Real graph with summary success, invalid-model fallback and protected-overflow fallback; request report save into tmp output -> full analyst report bytes unchanged in state and saved files. No raw JSON/summary replaces report files, returned tuple shape and existing memory behavior retained; model failure never forces REVIEW | FR-07-FC03/05; bounded IR-04/07/13 compatibility |

SS-01–07 live in the three B test files; SS-08–11 in `test/offline/test_downstream_wiring.py` with existing graph regression fixtures as needed. Strengthen old test's weak `graph is not None` report assertion into actual byte/marker comparisons. Old five-role test count/counter is evidence of an earlier design only, not acceptance of main. Do not weaken prior assertions merely because migration fails.

## 8. Fixed semantic evaluation recommendation — not execution approval

Reuse the four **saved full reports**, historical gap/counterevidence checks and prior NVDA observations. `TradingAgents/docs/fr08-structured-summary.md` records one pilot and an inherited **wrong ATR stop calculation**: it is a known faithfulness-vs-correctness limitation, not proof of quality or savings. `docs/architecture/evaluation-logbook.md` EL-11–16 records character-based size estimates and design exploration, not provider savings. Personal `docs/req/evaluation/README.md` and `brief-eval-contract-v4.json` are blocked draft contracts; the ten-case set has nine pending snapshots. Do not revive their cost thresholds or pretend those missing cases exist. Independently reviewed expected checks must not be generated from the candidate summary.

Existing local evaluation records were subsequently located and read, without executing their scripts or changing artifacts. Root prefix is `C:\Users\24968\AppData\Local\Temp\opencode\`:

| Local evidence | Reuse and limits |
|---|---|
| `fr08-summary-comparison-deepseek-01/scored_comparison.md`, `comparison_costs.json` | Earlier one-call summary comparison: five-item retention checklist, 1292 delivered proxy tokens; provider 8294 input / 1977 output, zero downstream requests. Reported 5/5 retention is not correctness: ATR error inherited; omitted macro conditions and sharpened invalidation interpretation remain. Proxy break-even estimates are not billed savings. |
| `fr08-shared-summary-live-01/plan.json`, `live/review_scored.md` | Later actual SharedSummaryBrief plus one full Bear / one brief Bear comparison: three historical requests total, no analyst/vendor reruns. Delivered 1390 proxy tokens, protected 150. Summary API 8643/2397 tokens; full Bear 8878/1912; brief Bear 3094/1640. Reasoning usage unknown/null. One-consumer total is higher after summary cost; reuse break-even is extrapolation, not five-role or multi-round measurement. |
| `fr08-shared-summary-live-01/inputs/review_checklist.json` | Existing frozen seven-item checklist: confirmation/unmet status; ATR details; financing vs demand; long-vs-short trend counterevidence; missing sources/low confidence; macro trigger conditions; ambiguous invalidation must not be strengthened. Plan records SHA-256 `a1af1e3ed855adb9d9944d46efd7266419426e5116703d630d68d09f66da36d1`; verify bytes before later fixture projection. |
| Both experiments' `inputs/original/`, `inputs/bodies/`, protection and prior review copies | Reuse preserved reports rather than regenerate them. Legacy FR08-SECTION removal happened only on recorded external copies with offsets/hashes; retain provenance and do not silently strip arbitrary current reports. These local paths are not portable CI evidence until reviewed lossless projection is committed. |

The later review explicitly finds ATR retained in the summary but omitted by **both** Bear outputs, plus ambiguous invalidation strengthened and positive sentiment counterevidence lost. Do not attribute every downstream omission to compression, repeat the earlier five-item score as a general quality pass, or claim historical request authorization permits any new request. All prior attempt locks and artifacts remain untouched.

Small proposed fixed set, no analyst/vendor reruns: SS-S01 saved NVDA pilot report bodies and the existing seven-item checklist (numbers/conditions/uncertainty), SS-S02 frozen adversarial variant with explicit negation/unmet trigger/conflicting reports, SS-S03 frozen missing-data/disabled-report variant (zero-request fallback), SS-S04 oversized/invalid structured output via offline replay (zero real request). Mark synthetic variants as synthetic, preserve source provenance/digests and keep checklist out of runtime prompt. Reuse the existing original checklist as review input, recording corrections and extra counterevidence checks rather than silently treating erroneous source arithmetic as ground truth. Baseline reports remain independent saved-report regression inputs; do not conflate them with the later pilot's generated Feature reports.

Proposed summary-specific rubric: source-supported claim attribution; material condition/number/unit/date fidelity; uncertainty/negation/counterevidence retention; no unsupported synthesis; protected-data integrity and truthful fallback. Critical escapes (program block lost/overridden, invented completeness, leaked synthetic secret, formal authority bypass) must not be offset by other scores. Numeric quality thresholds, mandatory expected propositions, rater/adjudication rules, exact model/settings/token output limit, budget and hashes remain **pending concrete human approval**, not invented accepted standards. Separate source-faithfulness from independently verified source correctness; do not score a summary by a financial metric calculator or automatically reward repeating the wrong ATR calculation.

Suggested request cap for the later proposal: **two summarizer requests total** (one each SS-S01/02), SS-S03/04 offline; no LLM judge, repeated sampling, full downstream A/B run or vendor fetch. Human rubric review consumes saved outputs. This is a proposed cap, not authorization to spend it. A matched downstream decision/usage experiment can be separately proposed only if the team needs benefit claims; it is not required to invent a savings claim here. Missing case/output/usage or an aborted request is retained, not excluded to improve denominators. Save raw complete response and envelope metadata only in reviewed bounded evidence, never prompts or public secrets.

Common CI stays the existing framework: schema, Ruff, mypy baseline, dependency/import/clean-install, regression matrix, exact human test pre-approval, approved contract tests, safety-path ADR/API/permission checks, AI-use and `ci / aggregate`. Prompt creation under the new `run/summary.py` path must be detected: current semantic detector's documented roots do not cover this new folder. Propose only a narrow reviewed path/AST addition with positive prompt-change and negative comment/control-flow cases in the existing gate tests; no generic analyzer. Actual five-role context/graph prompt changes also require semantic evidence. No self-issued not-applicable override for this feature.

Use independent `shared-summary-*` cases/rubric/config and a dedicated `shared_summary_eval:evaluate` runner. Do **not** overwrite `docs/ci/semantic_eval.yaml` with summary configuration once PR #14 owns its financial configuration, or pass the financial scorer as a quality oracle. Reuse trusted candidate/workflow SHA verification, approved config hashes, protected environment, details artifact and status validation. Inspect the synchronized workflow: if its single config path cannot select a separate summary config, approve only an explicit config/profile selection and matching evidence validation, with wrong-profile/hash/missing-evidence negatives. This is an identified possible compatibility need, not approval for a second CI pipeline or finance tool rewrite. Different feature evidence must not satisfy the wrong profile just because it uses the same status name. If a candidate changes both prompts, every applicable profile must be satisfied or the PRs remain separate.

Production/merge semantic evidence must be bound to the actual candidate SHA using the trusted default-branch runner; a local two-call pilot is not automatically a trusted CI pass. The necessary reviewed runner/profile support must first be available in trusted main. Coordinate that dependency with the team rather than dispatching an untrusted branch workflow or treating credentials as implicitly available. API execution requires specific evaluation approval **and** separate execution authorization and candidate/protected-environment review. None occurs in this checkpoint.

## 9. Shared-file coordination and PR/checkpoint sequence

PR #14 currently touches these paths also proposed here: `docs/req/requirements.yaml`, `architecture-blueprint.md`, `docs/architecture/adr/001-graph-internal-final-check.md`, `docs/architecture/invariants.md`, `docs/architecture/trace-matrix.md`, `docs/architecture/runtime-policy-catalog.md`, `docs/architecture/memory-design.md`, `docs/architecture/evaluation-table.md`, `docs/code-governance/structural-constraints.md`, `docs/code-governance/verification-constraints.md`, `docs/ai-use-log.yaml`, `docs/review-memo.md`, `docs/ci/README.md`, and conditionally `scripts/ci_semantic_eval.py`, `.github/workflows/trusted-evaluation.yml`, `test/offline/test_ci_gates.py`. Its `docs/ci/semantic_eval.yaml` is a coordination collision to **avoid**, not this plan's edit path. Potential later finance graph/config/context edits must be assessed from its actual next diff, not guessed or copied now.

Round 3 overlaps state/setup/graph/context-facing research inputs and governance. Do not merge/cherry-pick its in-progress application work now or build a second FR-03 producer. Send the approved seam/timing assumptions to Yifan; fetch latest main before final integration and compare actual wrapper/state/schema/signatures. Reapprove only materially changed paths/interfaces/assertions, not unchanged core tests.

1. **Now — plan Draft PR:** only this plan and AI-use entry. Freeze full commit SHA; non-author team member reviews it and posts §11 marker. Stop. No test/application implementation or true approval is claimed.
2. **Requirements/architecture alignment:** after approval and scoped maintenance authorization, make A changes, schema/consistency-check and show diff. Stop for inspection before core migration. Have the human reconcile human-only rule/permission scope. Ordinary plan approval does not prove ADR safety approval.
3. **Core migration + directional tests:** B only, author controlled tests first, run SS-01–07 and static checks, retain failures and unchanged source provenance. No graph hookup or real calls. Stop for inspection.
4. **Graph + regression:** synchronize actual main with Yifan; confirm §5/§6C seam, prepare actual five-role/first-call/fallback tests then minimal integration. Run full applicable offline regression and structural checks, report limits. Stop for inspection; runtime prompt changes cannot reach production without semantic gate.
5. **Semantic evaluation + final delivery:** submit the concrete D proposal first; after its human test/config approval implement bounded runner/CI compatibility, then wait for actual request authorization. Run only the approved cap; report raw outputs, rubric, actual usage/fallback, CI and real human verdict. No automatic merge or next round.

Prefer **two PRs total including this one**: PR 1 holds plan/requirements/architecture and independently testable core preparation if approved; PR 2 holds synchronized graph/prompt integration and evaluated delivery. Real reasons are changing Yifan/main interfaces and trusted-default-branch evaluator compatibility, not artificial per-file splitting. Do not merge prompt-bearing core preparation without its applicable semantic gate; if new `summary.py` prompt is included in PR 1, it needs its own approved evaluation or remains unmerged until evaluated. If dependencies settle soon, keep this Draft PR and complete all checkpoints in it instead; checkpoints are human stops, not a mandate for extra PRs. A trusted tooling prerequisite may require main maintenance, but never imply that merging a plan alone installs trusted code.

## 10. Commands, environment, evidence and limitations

Planning commands allowed now: read/fetch/show/diff/status/worktree/branch verification; document checks; commit/push only the two checkpoint paths and create Draft PR. No dependency installation. No model/vendor request. Do not access `.env`, credential files or unrelated coursework. Git authentication may use existing normal Git tooling/browser session; never print secrets. Preserve old worktrees and untracked evidence.

Future B/C execution: cwd this worktree (or explicitly approved clean verification environment pinned to its `src`), existing interpreter >=3.11 with verified import origin; disable bytecode and keep generated logs/JUnit/cache in the approved bounded `C:\Users\24968\AppData\Local\Temp\opencode\shared-summary-prep\` output area or pytest-owned temp directories. No shared finance outputs or baseline regeneration. The currently discovered Python 3.13.15 has yaml/jsonschema and PDF support but **no pytest**; choose an existing suitable environment with human confirmation, not silently install packages or claim a test pass.

Planned commands, not executed test results:

```text
python -m pytest -q test/offline/test_downstream_brief.py test/offline/test_structured_summary.py test/offline/test_brief_delivery.py
python -m pytest -q test/offline/test_downstream_wiring.py test/offline/test_graph_end_to_end.py test/offline/test_fr04_risk.py test/offline/test_sb01_final_check.py test/offline/test_reporting.py test/offline/test_prompt_integrity.py test/offline/test_layering.py
python -m pytest -q
python -m ruff check .
python scripts/ci_checks.py mypy --output <approved-temp>/mypy-current.txt --baseline mypy-baseline.txt
python -m pip check
python scripts/ci_checks.py schema --requirements docs/req/requirements.yaml --schema docs/req/req-schema.json
python scripts/ci_checks.py permissions
python scripts/ci_checks.py api
git diff --check
```

CI contract extraction reads literal test paths in the approved spec; existing paths above are deliberately selected regressions, and new B/C test paths must exist by their implementation checkpoint. §6D's new evaluator test is a separately approved later slice; do not point a core-only PR at this broad specification without a bounded approved test-spec selector that excludes that not-yet-implemented slice. Before implementation, freeze a scoped version of this plan (or a separately approved exact subset specification) consistent with actual changed paths and the existing gate; no fake missing-test success or gate relaxation.

Default pytest excludes integration/live; no `-m integration` run is authorized. Full prior offline suites are required for code changes; missing dependency, Windows/environment failures and skips remain explicit, not exemptions or passes. Record command/interpreter/dependency/import versions, candidate/test/spec/input hashes, FC/IR case mapping, expected/actual result, exit status and stdout/JUnit evidence. Remote aggregate, branch protection and individual jobs must be verified, not inferred from workflow files or historical PR successes.

## 11. Human handoff / exact gate syntax

Approval is pending; implementation start, approval URL/reviewer/time and final verdict are **not yet available**. The PR author cannot satisfy the non-author pre-approval gate. A genuine team member other than that author must review the immutable plan and post exactly:

```text
APPROVED test-spec: docs/plans/shared-summary-integration.md @ <FULL_PLAN_COMMIT_SHA>
```

The placeholder must be replaced with the real full commit SHA returned at this checkpoint. This approves only the defined scope and specific offline B/C expectations, subject to prerequisites and per-checkpoint human stops; D's concrete semantic specification/execution still needs separate approval. If the team wants B-only first, freeze/approve a precise bounded specification before coding so contract selection does not require nonexistent later tests. Approval must precede the actual first relevant implementation commit and be ancestral/verifiable by the current gate. Any changed material scope/expectation needs affected-version reapproval.

Future implementation PR body uses the actual `Plan`, `Approved test specification`, `Approval evidence`, `Implementation start`, `Approved scope`, and applicable `ADR` fields. No fabricated URL/start commit, agent-authored approval or inherited PR #12/#14 approval. Safety-critical first-call/program-data/state/graph edits additionally require the approved relevant ADR and real human safety review; the exact test-spec marker alone does not replace it. Final per-PR review ends in actual `APPROVE`, `CHANGES REQUIRED` or `REJECT`, distinct from this pre-approval. Wait for the human; do not implement, dispatch evaluation, merge or declare product acceptance after creating the Draft PR.
