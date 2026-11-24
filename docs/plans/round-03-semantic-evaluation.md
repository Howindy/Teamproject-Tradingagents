# Round 3 — Data-availability semantic suite specification

- Status: **Draft for independent test-specification and evaluation-standard approval.** No suite approval or execution result is asserted.
- Suite ID: `data-availability`; requirement: FR-03.
- Interface authority: [PR #17 suite-unit contract I1–I6](https://github.com/Howindy/Teamproject-Tradingagents/blob/684ddb22460992831fc15348884778d76c505a32/docs/plans/semantic-suite-routing.md#35-suite-unit-contract-interfaces-i1i6-for-parallel-work), immutable revision `684ddb22460992831fc15348884778d76c505a32`.
- Framework approval: [comment 7127811834](https://github.com/Howindy/Teamproject-Tradingagents/pull/17#issuecomment-7127811834) approves that framework version and confirms this suite ID and I2/I3. It does **not** establish approval of this suite's new cases, scorer, thresholds, implementation or live requests.
- Planning inspection: local feature HEAD `30421f025fc075d40751bcc7a955fc8e91f939c8`, incorporating main `00833f4b281692c266bbd52c5955a4f40ec89493`. These are inspection inputs, not permanently pinned evaluation candidates.
- User scope for this drafting task: create suite-specific materials only; do not modify existing project files, framework controls or application code. Git operations, dependency installation and model execution are not selected.

## 1. Purpose, authority and exclusions

This suite supplies the unresolved research-prompt evaluation prerequisite in [frozen Round 3 P3](round-03.md), particularly its sections 7 and 10. The current [D1 FR-03](../req/requirements.yaml), [D2 necessity/research contract](../../architecture-blueprint.md), [ADR 001](../architecture/adr/001-graph-internal-final-check.md), [IR-11/IR-12](../architecture/invariants.md) and [D4](../code-governance/verification-constraints.md) remain read-only inputs. P3 and A3 are not rewritten.

Primary coverage is the model-facing portion of FR-03-FC05 / IR-12: the Bull, Bear and Research Manager receive and correctly use the program research-stage availability block while retaining their existing task. Necessary-versus-supplementary and non-applicability scenarios use FR-03-FC02/FC03 and IR-11 as independent fixture semantics; they do not re-prove the producer's implementation.

D1 explicitly does not require validation of all natural-language model claims. This suite therefore checks only the bounded availability propositions and basic role delivery below. It is not a universal hallucination detector, investment-quality benchmark or formal-decision validator. Its new quality criteria are proposed release-test criteria pending approval, not amendments to D1.

Excluded: registry computation, first-request binding, observation classification, parallel isolation, graph scheduling, checkpoint lifecycle, terminal reports and saves, SB-01 authority, FR-04 risk, FR-10 financial arithmetic, historical vendor visibility, and all deferred features. Existing controlled offline tests continue to cover those applicable boundaries. No fixed investment recommendation is required; incomplete input does not mandate Hold, Sell or formal REVIEW from these research roles.

## 2. Exact files and ownership

| Path | Drafting / later implementation responsibility |
|---|---|
| `docs/plans/round-03-semantic-evaluation.md` | This concrete pending execution/test specification; freeze before implementation |
| `docs/ci/semantic-suites/data-availability.yaml` | I2 suite configuration, unapproved; real LF-normalized dataset/rubric hashes |
| `docs/ci/data-availability-cases.json` | Five complete synthetic input states and independently authored expected propositions |
| `docs/ci/data-availability-rubric.md` | Fixed bounded scoring rules, positive/negative controls and ambiguity policy |
| `scripts/data_availability_eval.py` | **After this suite's own pre-approval only:** I3 runner; no framework responsibilities |
| `test/offline/test_data_availability_evaluation.py` | **After pre-approval only:** DA-T01–DA-T16 below with independent expected outputs |

This drafting checkpoint creates only the first four files. It does not create executable runner/test placeholders, modify the shared registry, alter AI-use/review logs or change any other existing file. The current task's “do not modify other files” restriction takes precedence over general log-maintenance instructions. This plan records the drafting activity without representing itself as a raw transcript or modifying those logs.

Later suite-unit delivery needs separately authorized changes to `docs/ci/semantic-suites.yaml` (only the I1 entry), `docs/ai-use-log.yaml` and `docs/review-memo.md`. Permission for those existing paths is not inferred here. The registry does not yet exist in the inspected local base; do not create a competing registry while framework work is in flight.

No `src/`, shared checker, workflow, FR-10 config, dependency, permission or frozen specification change is allowed. If the candidate fails the suite, report the precise result; do not edit candidate prompts or weaken the oracle in this verification task.

## 3. Fixed inputs and exact execution matrix

The [case file](../ci/data-availability-cases.json) is dataset `fr03-data-availability-v1`. Its five cases each run `bull`, `bear`, and `research-manager` exactly once, in case-file order and then that role order: **15 logical combinations**. Deep-copy each stored state before each role; never feed one generated result into another combination.

| Case | Controlled input | Independent availability proposition |
|---|---|---|
| DA-S01 | Stock; all seven necessary items available; no supplementary limits | Basic completeness is complete; this does not establish sufficient investment evidence or a profitable trade |
| DA-S02 | Stock; global news unavailable; successful ticker news; debate contains an explicitly identified prior overstatement | Necessary global-news gap remains; ticker news cannot fill it; do not endorse the prior blanket-coverage claim |
| DA-S03 | Stock; all necessary items available; StockTwits/FRED supplementary limits; debate contains a prior overstatement | Necessary coverage remains complete; supplementary observations remain limited, not invented as successful |
| DA-S04 | Stock; research summary null; reports remain usable | The program summary is currently unavailable; report content is not thereby absent, nor is completeness confirmed |
| DA-S05 | Crypto; non-applicable stock necessity summary; supplied market evidence remains usable | Stock necessity rules do not apply; not_applicable is neither complete nor universal query failure |

All prices and business statements are invented, explicitly labelled evaluation fixtures, and not real AAPL/BTC data. Necessary items use the seven D1/D2 method identities. Stock price windows, analysis dates, statement frequency, Reddit window and known-null global-news object are explicit. No fixture or expected answer is produced by the candidate summarizer/classifier. Observations are consumer inputs, not claims of an executed fetch.

The complete structured fixture is passed to the real candidate entry. The actual candidate renderer determines what part is visible in the prompt. In particular, available-item details/observations are not all repeated by the existing renderer; scoring must not demand claims about fields the role did not receive.

For DA-S02/03, the fixed debate contains an identified older speaker claim that conflicts with the summary. That is a deliberate contradiction control, not an instruction appended by the evaluator. The model must not endorse it as fact; quoting it to reject or qualify it is allowed.

## 4. Proposed quality standard and scorer boundary

The [rubric](../ci/data-availability-rubric.md) defines three dimensions per combination: A availability meaning, B absence of material contradictory availability claims, and C existing role delivery. Thus 15 combinations have **45 required dimension outcomes**. Every dimension must be `passed`; any definite critical contradiction fails the evaluation, and any unresolved interpretation blocks as `needs_review`.

The required coverage statements are case-level test proposals, not a new production requirement that every response restate the entire summary. One supported paraphrase is enough. No metric-by-metric recital, exact wording, arbitrary word-count threshold or particular recommendation is required. “All data is complete” cannot stand in for “all necessary data is complete” when supplementary limitations exist.

The future scorer is a small English, case-specific recognizer with explicit subject/predicate/polarity checks, contradiction precedence and positive evidence for each pass. It is not an LLM judge and cannot assume complete natural-language coverage. An unsupported paraphrase, unclear attribution or uncertain polarity returns `needs_review`, never a guessed pass. Merely not matching a forbidden phrase is insufficient to pass. A simple keyword hit is insufficient to fail: negation, quotation, attribution and scope must be considered. The exact accepted recognizer forms and independent control strings in the rubric are part of the approved scope; broadening those forms later is a scorer revision, not a run-time exemption.

Ambiguity is intentionally conservative and may block a semantically acceptable response. The selected framework does not implement post-hoc human output overrides. Keep the output and reasons, fix a genuine candidate defect under its own authorization or separately approve a justified scorer revision and rerun. Do not cherry-pick outputs or repeatedly run until green.

No paired baseline is selected. Claims are limited to these fixed cases, not statistical stability or overall before/after quality non-regression.

## 5. I3 runner contract and candidate isolation

The future entry point must be exactly:

```python
def evaluate(config, candidate_sha, *, output_dir, model_transport=None) -> dict:
    ...
```

Use the I3 type annotations in implementation. The framework provides trusted cwd, installed `candidate/` at the requested HEAD, a writable output directory and the model secret. At module import, use only safe stdlib/existing dependencies; do not import candidate-only FR-03 modules or execute requests. This must remain inspectable on main before FR-03 application code merges.

Before model access: validate configuration and fixed versions, verify LF-normalized dataset/rubric hashes, verify candidate HEAD, confirm module origins resolve inside `candidate/src`, enumerate exactly 15 unique combinations, and validate the complete fixtures. Never use a stale editable package, trusted main's application package, or a serialized copy of production prompts. Resolve paths relative to trusted cwd / `candidate/`, not developer-specific absolute locations.

Invoke the real candidate factories and their actual node functions: Bull and Bear researchers plus Research Manager. Retain candidate summary rendering, prompt construction, `ResearchPlan` binding/rendering, and normal structured/free-text fallback. Do not disable structured output to simplify the harness and do not add evaluation instructions to the prompt. Only the transport/model boundary may be substituted in offline tests. A checked candidate subprocess or equivalent import isolation must prevent already-imported trusted/stale modules from being reused.

`model_transport`, when supplied, is an offline-only deterministic seam: request mappings include case ID, role, attempt kind (`plain` / `structured` / `fallback`), actual messages/prompt, schema/options when applicable, and approved model controls. Responses carry actual content/tool output, finish reason and usage as available. Test responses must traverse candidate parsing and rendering, not replace the entire role result. No framework extension is needed for this seam. Its exact mapping is private to this suite and must be tested.

The runner may contact only the configured model provider, must not fetch any data/vendor input, and must never call GitHub APIs or publish statuses/artifacts. Missing secret, invalid candidate or invalid material fails before the first request. Do not record secrets or authorization headers. This suite is not a credential scanner.

## 6. Proposed model, request budget and outcomes

Model settings are in the config and remain proposals. They reuse the existing provider/secret convention, not FR-10's approval. English output is fixed using the application's existing configuration mechanism; no new instruction is inserted into prompts. Temperature zero is a setting, not a determinism guarantee.

- One run per case/role; no semantic-score retry, best-of selection or judge request.
- Normal execution: 15 completion requests.
- Research Manager may exercise its existing single free-text fallback for each of five cases; maximum **20** requests. Bull/Bear have no additional evaluator fallback.
- SDK/HTTP retries are disabled. Count every actually sent attempt, including failed attempts. Check the remaining budget before sending, never after exceeding it.
- Normal structured parsing failure may follow the candidate fallback, with both attempts retained. Provider transport failure or truncated output makes the evaluation failed even if candidate fallback later returns text. No partially observed/truncated attempt is silently erased. Offline tests distinguish parsing fallback from transport/truncation failure.
- Successful execution must complete all 15 combinations. A preflight failure may execute none; a mid-run fatal error may fail fast while preserving attempted/skipped combination metadata. It cannot be a partial pass.
- Status precedence: definite evaluation/technical failure → `failed`; otherwise any unresolved dimension → `needs_review`; otherwise all 45 passed → `passed`.

On every return path, write details inside the supplied output directory and return all I3 fields: `status`, `errors` (list), top-level `needs_review` (`<case-id>:<role>:<reason>` strings), integer `request_count`, `dataset_sha256`, `rubric_sha256`, `details_path`, `details_sha256`. If materials could not be verified, retain computed hashes when available and explicitly record verification failure; do not echo an expected hash as proof. An unavailable verified hash is an empty string on a failed result, never on a passed result. `candidate_summary` adds expected/executed combination counts, dimension totals and critical failures. The framework owns suite/config/workflow/status fields.

Details JSON includes candidate and module origins, immutable case IDs/roles, actual prompts/options/schema, raw replies, rendered role outputs, all attempts and usage, per-dimension verdicts with supporting/conflicting excerpts, errors and pending items. Write the file before computing its exact-byte details hash; do not place its own digest inside the hashed file. Dataset/rubric hashes alone use LF normalization as I2 requires. Record incomplete execution without manufacturing missing responses.

## 7. Concrete offline test specification

All tests belong to the single future suite test file in section 2; no real model/vendor calls. Expected results and positive/negative reply strings are literals independent of the scorer. Use temporary trusted/candidate fixtures and `model_transport`, with filesystem/cache outputs outside the original tree. Cite FR-03-FC05/IR-12; fixture semantics additionally cite FC02/FC03/IR-11.

| ID | Controlled scenario | Independent expected result |
|---|---|---|
| DA-T01 | Inspect runner without candidate modules installed/imported | I3 signature accepted; no side effects or model request at import |
| DA-T02 | Current draft config and independently altered fixed versions/types/thresholds | Unapproved config fails before requests; invalid or contradictory settings fail closed |
| DA-T03 | Valid materials, CRLF checkout copy, changed case number, changed rubric | LF-equivalent bytes retain hashes; either content mutation fails before requests |
| DA-T04 | Wrong candidate SHA, stale imported module, missing FR-03 module | Failed result and details; zero model requests; no fallback to main |
| DA-T05 | Five complete states with three roles and independent good replies | Exactly 15 combinations; 45 passed dimensions; 15 requests; all I3 fields and matching details hash |
| DA-T06 | DA-S02 claims successful ticker news fills unavailable global news | Critical failure for each role, even if correct phrases also occur |
| DA-T07 | DA-S03 says necessary coverage incomplete only because StockTwits failed | Critical failure; a correct qualified supplementary limitation instead passes |
| DA-T08 | DA-S04 fabricates confirmed completeness, or says all reports disappeared | Critical failure; correct unavailable-summary/usable-report distinction passes |
| DA-T09 | DA-S05 equates non-applicability to completeness or universal failure | Critical failure; correct domain-limited explanation passes |
| DA-T10 | “not complete”, attributed mistaken claim followed by explicit rejection, unfamiliar paraphrase | Evaluate polarity/attribution; approved controls pass/fail as rubric states; unresolved paraphrase → needs_review |
| DA-T11 | Empty output; availability-only echo; malformed Manager plan; missing evidence/counterpoint | No green result; definite format/delivery failure fails, semantic ambiguity blocks |
| DA-T12 | Manager structured success, parsing miss then fallback, five bounded fallbacks | Preserve real candidate path; one or two counted attempts per Manager case; at most 20 total; record every attempt |
| DA-T13 | Transport error, timeout, truncated reply, exhausted budget | Failed; no extra evaluator retry; never send request 21; preserve raw attempts/details |
| DA-T14 | One combination absent/duplicated; one dimension failed; one pending review | No partial pass; status precedence and top-level lists correct |
| DA-T15 | Writer/result contract and output path | Details stays under output_dir, verified exact-byte hash, required types, no self-hash recursion, no secret/headers in evidence |
| DA-T16 | Run suite on main without FR-03 code, then against checked candidate; regression | Main imports/signature inspection work; missing candidate fails gracefully; actual candidate prompt includes its own block; existing suite/framework/FR-03 tests remain unchanged |

Test valid recommendation variation using the same correct facts: Buy/Overweight/Hold/Underweight/Sell must not fail solely by rating choice. Tests for mocks are runner/scorer evidence only, never real semantic-quality evidence.

## 8. Commands, prerequisites and records

Draft checks now: parse YAML/JSON without duplicate keys, compare LF hashes, validate I2 structure using existing main `validate_config()`, check five IDs × three roles, verify fixture shape independently, verify relative links and ensure only the four new paths changed. These are material checks, not runner tests or semantic passes. Do not install dependencies.

After independent suite test-specification approval and task authorization, use the existing Python 3.12 environment from the suite worktree. Put HOME/TMPDIR/XDG caches, bytecode policy and JUnit/outputs in a fresh OS temporary directory. The planned commands are:

```sh
python -m pytest -q -p no:cacheprovider test/offline/test_data_availability_evaluation.py
python -m pytest -q -p no:cacheprovider test/offline/test_ci_gates.py test/offline/test_financial_metrics_evaluation.py
python -m ruff check scripts/data_availability_eval.py test/offline/test_data_availability_evaluation.py
python scripts/ci_checks.py mypy --output /private/tmp/fr03-semantic-mypy.txt --baseline mypy-baseline.txt
python -m pytest -q -p no:cacheprovider
git diff --check
```

Use new filenames if an output exists. Where a main-based suite worktree lacks FR-03 source, its full default regression is not proof of FR-03 behavior. Separately execute applicable FR-03 offline tests against a checked feature candidate in an isolated copy, without copying feature source into the trusted suite PR. Preserve platform failures/skips; do not change unrelated tests or disable their assertions.

The framework routing version, its actual deployed runner invocation, output schema validation and T18 compatibility must be checked when it lands. The stage-0 framework contract approval exists, but this suite's test-spec pre-approval, standard approval and model execution authorization remain pending. If implementation needs a contract change, return it to the framework owner; do not patch shared files here.

## 9. Approval, branch and deployment order

1. Review these four draft files as one material set. Freeze the suite specification and cases/rubric/config before executable implementation. A non-author reviewer approves the exact suite test specification; any later material change needs its own revised version/approval. No approval URL/SHA is invented here.
2. Build the runner and DA-T01–DA-T16 on a separate branch/worktree from current main. This drafting checkpoint in the existing feature workspace is not already that independent PR. Move only the authorized suite files into the suite branch; do not include Round 3 `src/` changes or user `tmp/`.
3. Framework PR merges first. Suite PR then adds its files and only its own I1 registry entry; `status` stays `unapproved`. Complete authorized AI-use/review records in that PR. Use the real suite plan approval in its own standard test-approval fields, not P3/A3 as substitute.
4. A separate authorized change on main records real evaluation-standard approval and sets this config to `approved`. Changing that field is not authorization to send model requests by itself. Restore/resume the paused evaluation explicitly with an approved maximum of 20 requests on the reviewed candidate.
5. Update the Round 3 feature branch to the compatible framework, determine its final full SHA and retain P3/A3 fields. Apply I6 exactly: `Semantic suites: data-availability`, `Semantic suites approval: <real URL>`; reviewer line `APPROVED semantic-suites: data-availability`. Do not add an incompatible marker format. Human coverage confirmation must actually concern the candidate; the framework's current marker does not itself encode that SHA.
6. Human dispatch from default branch: `mode=semantic`, `suite_id=data-availability`, `candidate_sha=<reviewed full SHA>`. Framework writes `semantic-eval/data-availability` and I5 artifacts; this runner does not. Any later candidate change requires fresh candidate-bound evidence.
7. Rerun the same candidate's PR CI, inspect actual results and finish independent review. A passed suite is not full FR-03 acceptance, governance approval or merge authorization. The new suite does not use `none`/not-applicable to bypass genuine research prompt changes.

## 10. Drafting activity and present evidence limits

This document and its three companion materials were drafted by Codex in response to the current request. The agent read project governance, D1/D2/D4, the existing role/summary/schema code and PR #17 at the specified contract revision. A read-only GitHub query established the framework approval comment and suite-ID confirmation; no suite pre-approval is inferred from it.

At creation: no runner or test implementation, model call, data-provider call, dependency installation, registry edit, Git commit/push or PR change is claimed. The four paths are an unapproved material proposal. Hashes establish internal content identity, not human approval. The exact model quality, scorer pass rate and request consumption remain unmeasured.
