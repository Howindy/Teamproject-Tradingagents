# Project Covenant

## Purpose and authority

These rules govern incremental work on this application. Paths are relative to the project root containing `architecture-blueprint.md`. Read `AGENTS.md` for navigation, the current D1 for product semantics, D2 for architecture contracts, and `docs/code-governance/verification-constraints.md` for acceptance and evidence rules. This covenant adds no product requirement, numeric threshold, tool permission, or approval.

The course requires abstraction limits, dependency constraints, independent testing with at least one negative test per feature, an architecture decision and human approval for safety-critical changes, and rule updates within one sprint of a requirements change. These obligations apply through the bounded procedures below. This file is distinct from the human-only `.opencode/rules.md`; do not edit that file or any permission control to expand access.

## 1. Scope and abstraction limits

- Extend the existing application under `src/` and preserve its normal interfaces and unrelated behavior. Do not replace the baseline, introduce another source/test layout, or broadly reformat the application to implement a local feature.
- Implement only the active requirements selected by the approved round plan. FR-06, FR-07, PR-01, and CR-01 remain deferred unless a new explicit scope decision activates them. Do not reserve interfaces or add placeholder machinery for deferred work.
- Prefer existing modules, narrow functions, plain data structures, and explicit local adapters. Logical D2 components do not mandate separate classes, files, services, or agent processes. Give each architectural responsibility one primary module owner, as defined in the structural constraints or approved plan.
- Do not introduce generic registries, plugin frameworks, event buses, global dispatchers, universal numeric/security frameworks, cross-file transactions, immutable archives, or recovery platforms for requirements that do not need them.
- An abstraction must serve the current approved behavior and make responsibilities or interfaces clearer. Explain a consequential new abstraction in the plan; no arbitrary class-count, line-count, or nesting threshold is imposed.
- Preserve D2 authority boundaries: models propose, FR-04 evaluates the caller scenario, and SB-01 decides formal business values. Entries, reducers, reports, and memory may consume or project those values unchanged, but may not regenerate or substitute them.
- Keep run infrastructure out of serialized graph state/checkpoints. Retain the selected run isolation, summary timing, minimal history interface, and path-specific persistence policies. Refer to D2 rather than defining a second state vocabulary here.

## 2. Dependencies and environment

- Reuse existing declared dependencies and standard-library facilities when sufficient. A new dependency, version change, build-tool change, or lockfile change must be justified by the approved task and explicitly included in its file/operation scope.
- Explain the concrete need, existing alternatives, integration impact, and relevant validation before adopting a dependency. Do not invent package names or APIs, assume a package exists, or install a tool merely to make a draft plan executable.
- Respect the supported environment in the root `pyproject.toml`. Normal approved commands may use the existing interpreter, standard library, and installed packages; this does not authorize reading unrelated external files, changing global configuration, or installing dependencies.
- Network, live model/vendor calls, installation, background processes, and remote operations require the applicable task authorization. Use controlled offline substitutes for deterministic acceptance. Missing dependencies are a reported environment limitation, not a test pass.
- Do not add a vulnerability-score target, zero-warning threshold, or new dependency-audit platform through this covenant. Apply actual approved checks and report their limits honestly.

## 3. Round planning and permissions

- Specific work belongs in the selected round plan, initially `docs/plans/round-01.md` when created by an authorized task. This reference neither creates the plan nor approves it.
- The plan states included requirement/FC IDs and exclusions; exact files and D2 interfaces; test scenarios, controlled inputs, independent expectations and FC/IR links; structural/regression/behavioral scope; prerequisites; and actual approval evidence tied to the approved version.
- Obtain human approval of the execution plan and specific tests before the corresponding application implementation. Record approval only after it occurs; do not infer it from a template, a Proposed ADR, or an earlier round.
- Use only the intersection of task authorization, role/file limits, and actual tool permissions. A denied capability is not permission to use another tool to bypass it. Read-only review does not permit application edits.
- Do not self-edit requirements, governance, CI, dependency manifests, or permissions during ordinary implementation. A separately authorized maintenance task must name the affected files. Respect human-only rules, secrets, baseline evidence, and user changes.
- Unresolved business decisions block only dependent work. A clear, approved technical verification task may investigate an interface assumption without claiming final acceptance. Do not close OQs automatically or request repeated approval for unchanged work already within the approved scope.

## 4. Test independence and minimum negative coverage

- Each feature must have at least one negative test exercising a relevant invalid input, forbidden behavior, boundary failure, or injected fault. A genuine existing test may satisfy this when its assertions cover the changed behavior; do not create token duplicates just to increase counts.
- Every active FC needs locatable test coverage, and each invariant needs a test that detects its violation. Link tests to the relevant FC/IR or requirement. Parameterized tests and shared evidence may cover multiple IDs when assertions are explicit.
- Derive expected results from D1, approved D2 contracts, independent calculations, or sourced fixtures. Do not call the implementation under test to generate its own oracle or accept its self-reported counters as independent evidence.
- External model/vendor substitutes are acceptable for offline tests. Preserve the real internal boundary being verified; do not mock away the core logic and call the result an integration pass. Offline results do not establish live model quality.
- Verification must not modify the application under test to make a check pass. Return implementation defects to the implementation phase, then rerun the relevant checks and required regression. Do not delete tests, weaken assertions, zero-fill missing measurements, or relax thresholds to hide failures.
- Follow D4 for structural, regression, and behavioral checks. Each round runs prior applicable suites; regressions block merge. The default `pytest -q` from the project root excludes integration tests and is not evidence of a live/full offline-and-live pass.
- Verification aids such as watchdogs, sentinels, and static scans may use equivalent methods. They do not create production deadlines, monitoring services, custom AST frameworks, or additional business requirements.
- Report actual commands, versions, results, skips, and environment blocks. Unrun, skipped, or blocked checks are not passes. No test or acceptance result is established by this document.

## 5. Safety-critical changes

- Changes to formal recommendation authority, fail-closed behavior, risk applicability/calculation, trusted availability inputs, output/memory decision consistency, credential handling, path confinement, or agent permission enforcement require safety-impact review. Use the affected D1/D2 contract to determine the actual scope rather than declaring every file safety-critical.
- Before implementing safety-critical changes, identify the corresponding ADR and obtain human approval for the specific change and tests. If an existing ADR already covers the change, cite it; do not create a new ADR for every local edit. If the change alters an architecture decision or boundary, update/reopen the affected decision through an authorized task before dependent implementation.
- Passing tests or an ordinary PR verdict does not replace required architecture and human approval. Conversely, approval does not prove behavior: retain independent negative and boundary assertions under D4.
- Preserve the limited D1 safety scope. Do not add broker verification, trade execution, generic secret detection, all-platform race guarantees, or recovery protocols as hidden acceptance conditions.

## 6. Context freshness and rule maintenance

- At the start of each round, check the current applicable requirements, architecture, verification rules, plan version, and relevant OQs. Historical descriptions and baseline observations do not override current requirement objects.
- After an approved requirements change, identify affected architecture, rules, tests, permissions, and trace links. Update affected rules within one sprint of that change, using the team's actual sprint boundary; do not invent a fixed day count or fictitious sprint record.
- The one-sprint limit is a maintenance deadline, not permission to implement against known contradictory rules. Resolve a conflict before dependent work or defer only that affected work. Continue independent authorized work where possible.
- Only update artifacts affected by the change. Do not require a wholesale D1/D2/D3/D4 rewrite for an internal refactor that preserves contracts. If maintenance lies outside the current authorization, report the exact gap for a scoped task rather than silently editing protected files.
- Do not claim a rule or permission file is automatically loaded or enforced without checking the actual tool mechanism. In particular, the course-named permission file documents its explicit-loading requirement; this covenant does not activate it or grant commands. Missing launch/configuration controls remain reported prerequisites.

## 7. Evidence and handoff

Preserve real raw sessions and human interventions. Maintain AI-use, review, significant-bug, and debt records through authorized paths as actual work occurs; do not fabricate entries or approvals. A delivery states changed files, covered FC/IR IDs, actual checks/evidence, and unresolved limitations. Use the existing D4 review verdicts and applicable CI/branch-protection requirements; do not treat push, merge, or a documentation self-check as application acceptance.

This covenant has been authored as a governance artifact. It does not approve an implementation round, resolve pending entry/D3 decisions, activate deferred scope, or certify machine enforcement.
