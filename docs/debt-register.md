# D4 Technical Debt Register

- Document status: Reusable technical-debt record template. No actual debt has been registered yet.
- Registered records: None yet.
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
