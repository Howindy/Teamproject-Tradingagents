# D4 Technical Debt Register

- Document status: Reusable technical-debt template with three evidence-backed open items registered on 2026-11-25. Recording an item does not approve the compromise or claim a mitigation has been executed.
- Registered records: DEBT-GUARDRAIL-001 (inactive CI enforcement), DEBT-EVALUATION-001 (FR-10 release-evaluation gap), and DEBT-GUARDRAIL-002 (unbounded-context course-alignment gap).
- Purpose: Track confirmed compromises and accumulated problems, their evidence, impact, temporary retention rationale, risk, handling, and review triggers.
- Related records: [Review memo](review-memo.md) and [Bug diary](bug-diary.md).

This file does not claim that the project has no debt, and it does not require every category to contain an item. Categories are classification labels, not quotas.

## 1. Recording rules

1. Register a debt item only when there is a real, evidence-backed compromise or accumulated problem. Do not invent an issue to fill a category.
2. Deferred requirements, unresolved decisions or technical assumptions, and planned but unexecuted work are not automatically technical debt. They become debt only when a confirmed compromise or accumulation exists.
3. Distinguish a bug from debt. A bug has an observed incorrect behavior requiring correction; debt is a known compromise retained with risk. A bug may also expose debt, and the records should link rather than duplicate details.
4. Record the evidence and why the compromise was accepted for now. Do not describe a proposed mitigation as completed.
5. Leave the owner blank if no human owner has been assigned. Do not infer ownership from a role, plan, or AI action.
6. Use the actual review, bug, requirement, FC, IR, ADR, and component references when they exist. If no relation is known, write `None known`.
7. Preserve earlier reasoning and status changes. Append review evidence instead of deleting the original compromise.
8. Use a stable ID such as `DEBT-<category-code>-<sequence>`, and use the same ID in review and bug records.

## 2. Debt categories

| Category code | Category | Short description |
|---|---|---|
| `PROMPT` | Prompt rot | Runtime prompts or instructions have become stale, contradictory, duplicated, or detached from the approved behavior, so the intended behavior is no longer reliably expressed. |
| `HALLUCINATED` | Hallucinated dependencies | Code, tests, plans, or prompts assume a package, API, service, field, or capability that does not actually exist or is not confirmed. |
| `UNTOUCHABLE` | Untouchable code | A region has become too risky, poorly understood, or entangled to change safely, leaving known problems unaddressed. |
| `HIDDEN` | Hidden dependencies | Behavior depends on undocumented coupling, global state, side effects, import order, test order, timing, or external state that is not explicit in the contract. |
| `BLOAT` | Agent-induced bloat | Accumulated generated or mechanical complexity, duplication, placeholder abstraction, or unnecessary code that increases maintenance cost without serving approved behavior. |
| `EVALUATION` | Evaluation debt | Acceptance or quality evidence is missing, non-independent, non-reproducible, or too weak to support the claims being made. |
| `GUARDRAIL` | Guardrail debt | A required safety, permission, path, credential, fail-closed, or CI control is incomplete or unverified while the affected work proceeds under an explicit limitation. |
| `HUMAN` | Human/cognitive debt | Review, approval, decision, or operational knowledge is concentrated, missing, stale, or difficult for another human to reconstruct and audit. |

A category description is guidance, not an additional requirement. Do not create a category-specific quality score, threshold, or mandatory inventory.

## 3. What is not automatically debt

- Deferred requirements such as FR-06, FR-07, PR-01, and CR-01.
- Open questions, pending technical verification, and unresolved business decisions.
- Tests that are planned but not yet approved or executed.
- Proposed architecture decisions labeled `Proposed`, `Planned`, or `Pending verification`.
- Environment gaps that are reported and block dependent work without any accepted compromise.

If one of these later creates a confirmed compromise that the team knowingly retains, record that compromise with its evidence and risk. Do not reclassify all deferred or pending work.

## 4. Debt record template

Copy this structure for each actual debt item. Replace angle-bracket placeholders with recorded evidence or an explicit `not recorded`/`not applicable` value.

### DEBT-`<category-code>`-`<sequence>`: `<short-title>`

#### Identification

| Field | Recorded value |
|---|---|
| Debt ID | `DEBT-<category-code>-<sequence>` |
| Discovery time | `<UTC timestamp with timezone, or "not recorded">` |
| Round | `<round/plan reference, or "not recorded">` |
| Category | `<PROMPT / HALLUCINATED / UNTOUCHABLE / HIDDEN / BLOAT / EVALUATION / GUARDRAIL / HUMAN>` |
| Current status | `<Open / Accepted for now / Mitigation planned / Mitigated / Resolved / Not debt after review>` |
| Related review memo | `<[RM-...](review-memo.md) link, or "none">` |
| Related bug record | `<[BUG-...](bug-diary.md) link, or "none">` |

#### Confirmed problem and evidence

- Problem: `<specific compromise or accumulated problem>`
- Evidence: `<code/test/output/review link or immutable reference>`
- Why this is debt rather than pending work: `<actual compromise already present or knowingly retained>`
- Scope of the compromise: `<files, components, prompts, tests, evidence, or workflow>`

Do not use this section for a hypothetical future issue. Keep unconfirmed concerns in the relevant plan or review record, not here as debt.

#### Impact and linkage

- Impact: `<maintenance, correctness, security, evaluation, delivery, or human-review impact>`
- Requirements / FCs affected: `<actual IDs, or "None known">`
- Invariants / ADR decisions affected: `<actual IR/ADR IDs, or "None known">`
- Runtime policies affected: `<actual RP IDs, or "None known">`
- Components or modules affected: `<actual components/modules, or "None known">`
- Other linked records: `<review, bug, plan, or external evidence link, or "None">`

#### Retention rationale and known risk

- Why it is being retained for now: `<actual constraint, tradeoff, or decision>`
- Who or what accepted the tradeoff: `<human decision/approval record, or "not recorded">`
- Known risk if it remains: `<specific risk and affected conditions>`
- Compensating control, if any: `<actual control and evidence, or "None">`
- Risk that is explicitly not covered: `<specific limitation>`

Retention is not approval of a permanent state. Do not invent an accepting authority.

#### Handling

- Recommended handling: `<smallest credible remediation or investigation>`
- Owner: `<human owner, or blank if not assigned>`
- Expected scope and dependencies: `<files, approvals, ADR, tests, or dependencies required>`
- Decision reference: `<approved plan/decision link, or "not decided">`
- Actual progress: `<work actually completed and evidence, or "None">`

#### Review trigger and status

- Review trigger or checkpoint: `<event, round boundary, requirement change, release gate, or "not scheduled">`
- Re-evaluation condition: `<evidence or condition that would change the decision>`
- Current status: `<Open / Accepted for now / Mitigation planned / Mitigated / Resolved / Not debt after review>`
- Status rationale: `<actual reason for the current state>`
- Follow-up evidence: `<link to review, test, bug, or remediation record, or "not yet available">`
- Closure or downgrade condition: `<what evidence would justify closing or reclassifying this item, or "not defined">`

For a `Resolved` or `Mitigated` state, cite actual evidence. For an open item, leave future evidence unfilled.

## 5. Registered debt — 2026-11-25

Baseline inspected: `a78aee443e4c3be127535dd86e3e50745b5da5de`, D1 v1.51.0. These items concern observed compromises in the delivered project and its evidence. Deferred features alone are not being reclassified as debt. No remediation, owner assignment, risk acceptance or human approval is created by writing this register.

### DEBT-GUARDRAIL-001 — CI enforcement inactive

| Field | Recorded value |
|---|---|
| Category | GUARDRAIL |
| First recorded here | 2026-11-25; actual deactivation time not established |
| Status | Open |
| Owner | Unassigned |
| Related reviews | RM-19-R1, RM-24-R1, RM-25-R1, RM-26-R1, RM-27-R1 in the [review memo](review-memo.md) |

**Confirmed condition and evidence.** A read-only GitHub API snapshot on 2026-11-25 returned `disabled_manually` for both `.github/workflows/ci.yml` and `.github/workflows/trusted-evaluation.yml`, and `protected=false` for main. The workflow files remain present. Merged changes therefore cannot be described as having passed enforced blocking controls solely because the intended workflow definitions exist. Sources: [workflow state](https://api.github.com/repos/Howindy/Teamproject-Tradingagents/actions/workflows), [main branch metadata](https://api.github.com/repos/Howindy/Teamproject-Tradingagents/branches/main), [CI design](../CI.md), and [verification constraints §9.3](code-governance/verification-constraints.md).

**Why this is debt.** This is a current execution-control gap while work has already reached main, not simply an unimplemented optional feature. It affects the course D7 requirements for required CI and safety-relevant review enforcement. It does not itself prove a runtime trading-safety failure.

**Retention and risk.** The user requested expedited integration without CI gating in the recorded workstream. The exact time, actor and repository-wide approval for disabling the workflows or protection have not been established. Formal acceptance of this risk: **not recorded**. Local checks and individual real reviews provide limited evidence, but do not block future noncompliant merges. A green historical run is not a substitute for current enforcement.

**Handling.** A repository maintainer should decide and restore the applicable workflows, required aggregate check and safety-path human-review policy. Verify the actual remote settings and one applicable PR execution. This entry does not authorize changes to GitHub settings or establish that a specific protection mechanism is available to the repository.

**Review trigger and closure.** Recheck before claiming course-compliant blocking gates or final release governance. Close only when actual settings and an applicable execution demonstrate enforcement; otherwise retain Open and describe the limitation. No reactivation, test run, owner or completion date is assigned here.

### DEBT-EVALUATION-001 — FR-10 formal semantic acceptance remains unestablished

| Field | Recorded value |
|---|---|
| Category | EVALUATION |
| First recorded here | 2026-11-25; earlier planning records already disclosed the gap |
| Status | Open |
| Owner | Unassigned |
| Related reviews | RM-19-R1, RM-25-R1 and RM-26-R1 |

**Confirmed condition and evidence.** Financial metrics and their fundamentals-prompt injection are on main, but [financial-metrics evaluation configuration](ci/semantic_eval.yaml) remains `status: unapproved`, with null approval identity/time and no execution-approval evidence. The [registered suite](ci/semantic-suites.yaml), [fixed cases](ci/financial-metrics-cases.json), [rubric](ci/financial-metrics-rubric.md), runner and offline scorer tests exist. The fixed Git dataset/rubric hashes match their configuration. Presence and integrity of those artifacts do not demonstrate a candidate-bound completed model evaluation.

**Why this is debt.** The implementation has been delivered while the formal quality-evidence step for the prompt-affecting change remains open. This is not merely a deferred future feature or a demand for an invented quality threshold. The existing plan proposes a maximum six-request replay and its existing scoring contract; this entry changes neither.

**Retention and risk.** Offline reference calculations, injection tests, fault-isolation tests and the 28 post-implementation regression examples provide useful deterministic evidence. They do not establish that a live analyst consistently uses the program evidence correctly. Earlier personal-branch pilots concern different code/input versions and are not substituted for the formal candidate. A team-approved permanent waiver is **not recorded**. No general model-quality or cost-saving guarantee is supported by the current evidence.

**Handling.** When authorized, obtain actual approval of the fixed evaluation configuration and bounded model execution, check the existing trusted-runner prerequisites, and run the existing suite against a fixed candidate and baseline. Preserve outputs, usage, finish reasons, scoring and failed/ambiguous claims. An unsuccessful or blocked replay remains unsuccessful or blocked; do not lower thresholds or relabel offline examples as a live pass.

**Review trigger and closure.** Recheck before asserting formal semantic acceptance or producing another prompt/model release. Closure requires locatable approval plus candidate/input/model-bound results meeting the approved contract and actual human review. Any unexecuted prerequisites remain open. No paid request, scoring change or approval-state change was made by this registration.

### DEBT-GUARDRAIL-002 — Unbounded context and incomplete course-budget design

| Field | Recorded value |
|---|---|
| Category | GUARDRAIL, with documentation/evaluation impact |
| First recorded here | 2026-11-25; previously disclosed in verification constraints §9.2 |
| Status | Open |
| Owner | Unassigned |
| Related review | RM-27-R1 |

**Confirmed condition and evidence.** [ADR 003](architecture/adr/003-llm-turn-context.md) records role-local prompt assembly without a global input-token cap, compaction threshold, automatic history compression or post-compaction reinjection. Provider output limits are optional and tool-round counts do not measure input tokens. [Verification constraints §9.2](code-governance/verification-constraints.md) explicitly identifies the course expectation for context budgeting, compression and constraint reinjection as unresolved.

**Why this is debt.** Retaining full reports and histories is a concrete architecture choice in the current application, with a known provider-context-window exposure and an unresolved D2 submission-design obligation. Deferred FR-07 alone is not the debt, and implementing the historical summary prototype is not imposed as its remedy. No overflow incident at the inspected revision is claimed.

**Retention and risk.** The implemented role templates preserve existing full-report behavior and normal-turn instructions/evidence. ADR 003 describes the existing provider-error path and reopening conditions. That disclosure improves accuracy but does not supply a numerical budget or a tested compaction/reinjection policy. Formal acceptance of the remaining course-alignment risk is **not recorded**. Long evidence/history may exceed a model's window; the current design offers no global size guarantee.

**Handling.** Ask the team to resolve the course/design obligation explicitly. If budgeting or compression is adopted, specify the actual model/token counter, budget, threshold, protected evidence and failure/reinjection behavior, and verify that behavior under the approved scope. If no implementation is undertaken, keep the documented limitation and do not claim the course design requirement is satisfied. Do not invent production thresholds or import the entire deferred summary feature solely to fill this entry.

**Review trigger and closure.** Revisit at final architecture review or when report/history size, supported models or context assembly changes. Close after the relevant design decision and supporting evidence address the stated obligation; retain Open if the gap remains. No product policy or code was changed during this maintenance.
