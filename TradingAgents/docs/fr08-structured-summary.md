# FR-08 structured summary: standalone handoff

## Status and scope

This is an **offline-verified standalone adapter**, not an enabled graph feature.
There is no shared ContextAssembler/material boundary in this worktree:
`agents/context.py` supplies identity/portfolio/absence prompt helpers, while the
downstream agents each interpolate their own four report fields. Graph scheduling
has a post-analyst fan-in in `graph/setup.py`, but no existing shared material
object to replace safely. No downstream role, graph, state schema, retrieval,
FR-07 metric calculation or provider module was modified for this change.

Market, News and Fundamentals no longer receive FR08-SECTION instructions. All
other prompt text, tool bindings and wrap-up behavior are preserved. Sentiment
is untouched. The unused legacy `report_sections.py` utility and parser fixtures
are retained for compatibility/historical artifacts; the active builder no longer
imports it, parses sections, or accepts `section_token_limit`. Section-preference
tests were retired; the recorded marker-free fallback hash regression remains.
The unrelated passage-ranking draft is unchanged and excluded from regression
runs because it describes an unimplemented interface.

## API

```python
from tradingagents.run.summary import SharedSummaryBrief

# Instantiate once PER RUN, after choosing a fixed tokenizer and model wrapper.
shared = SharedSummaryBrief(token_counter=counter, model=summary_model)

result = shared.get(
    reports={
        "market_report": market_text,
        "news_report": news_text,
        "sentiment_report": sentiment_text,
        "fundamentals_report": fundamentals_text,
    },
    canonical_gaps=caller_gaps,
    metric_block=caller_rendered_metrics_and_citations,
    safety_constraints=caller_safety,
    policy=caller_budget_policy,
    coverage_view_version=caller_coverage_version,
)
# shared(**same_inputs) is also supported.
if result.brief.status == "BRIEF_REJECTED":
    # Terminal: protected evidence cannot fit. Do not deliver clipped text.
    handle_rejection(result.brief.rejection_reason)
else:
    downstream_material = result.brief.text
```

Arguments and policy are those of `DownstreamBriefBuilder.build`; the builder's
optional `narrative=` argument now validates an already rendered narrative whole,
or preflights protected evidence with `narrative=""`. Omitting narrative retains
the original deterministic extraction, including deduplication/interleaving and
complete-sentence reduction. It does not rank passages with another model.

`result` is immutable and contains:

- `brief`: the existing `BriefResult` with status, text, token counts, protected
  content and terminal rejection reason.
- `mode`: `summary`, `deterministic_fallback` or `rejected`.
- `failure_reason`: stable summary/schema/budget/provider failure reason, or the
  terminal protected-block rejection. A valid summary has no failure reason.
- `raw_response`: original text for local diagnosis, including invalid or oversized
  outputs. **Do not send this raw field downstream.** Provider exception messages
  are deliberately not retained, since they may contain private details.

The cache is local to the adapter instance and content-based over the four
reports, all protected inputs, coverage version and validated policy settings.
Equivalent new dictionaries reuse the identical result object. Success,
deterministic fallback and protected-block rejection are memoized; concurrent
readers are serialized around generation. Changed reports/evidence/budget produce
a new entry and may invoke the model once for that distinct input. Dispose of
the adapter at run end; do not create one per agent or share one globally between
unrelated runs. Do not re-enter the same adapter from its injected model callable.

Empty report texts select deterministic fallback without a request. Missing report
keys or invalid policy/tokenizer configuration raise `BriefConfigurationError`;
configuration errors are not disguised as model failures. The caller must settle
all four reports before requesting material, including explicit absence notices
if an analyst was intentionally unavailable.

## Model boundary and schema

The model callable receives one prompt string containing the four **complete**
report texts encoded in a delimited JSON source object. It returns complete raw
JSON text or raises. The component has no SDK, provider, credentials, tools or
retry loop. A production wrapper must:

1. Use the team's configured model and explicitly disable automatic retries and
   tools. Preserve any required provider settings (for DeepSeek pilots this was
   `extra_body={"thinking": {"type": "disabled"}}`).
2. Save provider finish reason, usage (including reported reasoning tokens),
   visible-text status and latency **before** returning/validating content.
3. Raise on provider errors, truncation, returned tool calls or unusable response
   envelopes; return only complete visible response text. Do not repair or retry.
4. Account for the extra summarizer request in total provider usage. Keep provider
   tokens separate from proxy counters. Do not claim absent reasoning fields are 0.

Schema:

```json
{
  "schema_version": "fr08-summary-v1",
  "risks": [{"text": "A supported risk with its qualifications.", "sources": ["market"]}],
  "triggers": [],
  "conclusions": [],
  "uncertainties": []
}
```

All five root fields are required and no extras are accepted. All categories are
lists; each item has exactly nonempty text and a nonempty list of allowed report
IDs (`market`, `news`, `sentiment`, `fundamentals`). All-empty categories are
invalid. Duplicate JSON fields, nonstandard JSON constants, fences, unknown IDs,
invalid types and forged protected delimiters fail validation without repair.
Allowed empty individual categories do not render placeholder claims.

Rendering uses category order **Risks, Triggers, Conclusions, Uncertainties**,
preserves item order, and canonicalizes/deduplicates source labels in order
market/news/sentiment/fundamentals. Item whitespace is normalized to a single
line. Every rendered label/source/text token and the entire caller-derived
protected block are counted by the injected counter. JSON syntax is not delivered
to downstream agents. An over-budget summary is rejected whole, not trimmed;
the original deterministic builder supplies the cached fallback for that report
set. Invalid raw text never enters the fallback extraction input.

The caller's protected block remains code-derived from metrics/citations, gaps,
coverage and safety; the model neither constructs nor replaces it. Existing
protected-only hard-cap/initial-budget rejection remains terminal. A token counter
must stay deterministic and fixed for the adapter lifetime. The previous
**1,531 total / 150 protected / 1,381 narrative** whitespace-proxy setting is a
test fixture, **not a default policy or provider tokenizer**. Production callers
choose the budget and tokenizer identities through the existing policy.

**Structural validation is not claim verification.** An allowed source ID merely
establishes that a named report exists, not that it supports the statement. It
does not verify arithmetic, enforce completeness, resolve source errors or prove
that uncertainty/counterevidence was retained. Narrative cannot promote itself to
authoritative FR-07 evidence. The prompt uses general selection instructions, not
the NVDA evaluation checklist.

## Exact remaining teammate connection

1. At the team-owned post-analyst boundary, after all four report texts are
   settled (currently `GraphSetup.setup_graph` connects `first_steps` directly to
   `Bull Researcher`), call one run-owned adapter with reports and caller-derived
   evidence/budget. Keep the original report fields unchanged in stored state.
2. Carry the same `SummaryBriefResult` through the team's shared downstream
   material object/closure. Route `result.brief.text` as **one** research-material
   block to bull/bear researchers and aggressive/conservative/neutral risk
   consumers. Do not interpolate the same combined brief four times under four
   original report headings. Preserve each consumer's other context, history,
   portfolio, safety instructions and return/state behavior.
3. Reuse that result for repeated debate reads and fallback reads. Never instantiate
   a new adapter or call a new summarizer in each agent. Decide how to persist
   the material if cross-process checkpoint/resume reuse is required; the current
   adapter cache is deliberately in-process and does not change graph schemas.
4. Handle terminal rejection before invoking consumers. Record mode/failure reason
   and usage separately from final decisions. A teammate must own these boundary
   and consumer-wiring changes; they are intentionally not included here.

Runnable offline example (from the TradingAgents project root):

```powershell
python -B -m examples.fr08_summary_adapter
```

It uses a fake callable only, demonstrates two reads/one invocation, and prints
the delivered protected brief. No provider or vendor call is made.

## Verification and remaining acceptance

`tests/test_structured_summary.py` covers valid/invalid JSON, exact fields and
versions, source IDs, empty results, model failure, budget rejection including
rendered labels, exact 1,531-token boundary, nonadditive token counting, protected
content and report immutability, concurrent reuse and cached fallbacks. Delivery,
analyst prompt and existing graph regressions run offline with network blocking.

Offline results for this change:

- Focused summary/delivery/analyst/graph/portfolio/legacy-parser suite: **127 passed**.
- Broader suite, explicitly ignoring `tests/test_passage_ranking.py`: **1,440 passed,
  5 failed, 4 skipped, 1 deselected**, plus **100 passed subtests**.
- The five failures were rerun on the pristine detached baseline: **the same five
  failed** (two Windows private-file-mode assertions, two install-upgrade command
  tests, one yfinance cache-under-home test). They are not FR-08 regressions.
- Ruff on changed Python implementation/tests/example: **all checks passed**.
- Offline example: passed (two reads, one fake invocation).

JUnit reports, initial-file backups and preservation hashes are in
`C:\Users\24968\AppData\Local\Temp\opencode\fr08-structured-summary-offline-01`.
The first test attempt hit a default pytest temporary-directory permission error;
the successful runs used explicit fresh approved external `--basetemp` paths.
There were no paid API calls, commits or pushes.

The earlier NVDA one-call experiment remains **one pilot**, not a quality or
decision-equivalence guarantee. It retained additional details but inherited a
wrong ATR stop calculation. No new live comparison was run for this implementation.
Remaining acceptance is a matched comparison of downstream decisions using full
reports versus this structured brief, measuring **all provider usage including
the summarizer**, actual downstream invocation count, latency, failures and
quality. That work needs a separate authorization; estimated reuse break-even is
not observed downstream savings.
