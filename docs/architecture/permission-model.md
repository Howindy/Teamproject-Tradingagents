# Coding-Agent Permission Model

> **FR-10 feature-integration planning exception (2026-11-24):** The human explicitly authorizes the Plan responsibility, for this round only, to read the relevant FR-10, current CI/semantic-suite and Round 3 materials; create and edit `docs/plans/financial-metrics-feature-integration.md`; append the actual planning and permission-maintenance record to `docs/ai-use-log.yaml`; and perform status inspection, fetch, plan commit, push and Draft PR creation. This is an exact, temporary role-maximum exception to §§2–4 below, not implementation, test, live-evaluation, merge, or general governance authorization. Existing protections and other role boundaries remain. Actual configured tool permissions are separately enforced; no tool denial may be bypassed. This human-authorized exception does not establish automatic loading or OS isolation.

> **FR-10 checkpoint A exception (2026-11-24):** The human authorizes implementation and verification of the six named `src/tradingagents/financials/` modules, `src/tradingagents/dataflows/vendors/sec_edgar.py`, `src/tradingagents/dataflows/vendors/yahoo/market.py`, `test/offline/test_financial_metrics.py`, `test/offline/test_sec_financial_provider.py`, and actual A records in `docs/ai-use-log.yaml`. Independent test-environment installation, targeted offline tests, Ruff, scoped commit/push and PR body updates are authorized. This narrow exception does not authorize B graph/CLI/prompt wiring, live calls, trusted workflow maintenance, merge, or editing the frozen plan. Actual enforcement remains separately determined; no tool denial may be bypassed.

- Document status: Proposed role-permission design. A machine-readable project permission file exists and CI includes a static configuration check, but effective OpenCode loading, merged policy, runtime access restriction, and enforcement are not verified; this is not a security certification.
- Requirements basis: [D1 registry](../req/requirements.yaml), v1.51.0 (14 requirements, 65 fit criteria).
- Architecture basis: [`architecture-blueprint.md`](../../architecture-blueprint.md), especially §9.3 and §11, and [`ADR 001`](adr/001-graph-internal-final-check.md).
- Cross-check basis: [`invariants.md`](invariants.md), [`trace-matrix.md`](trace-matrix.md), [`memory-design.md`](memory-design.md), [`runtime-policy-catalog.md`](runtime-policy-catalog.md), and [`evaluation-table.md`](evaluation-table.md).
- Project guidance checked: `goal.md`. `D2.md` was a deleted copy of course instructions, not a required project deliverable; the course D2 delivery basis is the course PDF (pages 5 and 9), and project architecture is read through the existing blueprint and `docs/architecture/` artifacts.
- Secret handling: no `.env*`, credential, or secret content was read. Only project paths and non-secret governance files were inspected.

This document describes file-level permissions for AI coding agents. It is not the TradingAgents runtime business model. Analyst, researcher, Trader, Portfolio Manager, SB-01, and other application roles are not file-access roles. Conversely, Plan/Architecture/Implementation/Verification are coding responsibilities, not application authorities.

## 1. Role model

The project contains `AGENTS.md`, `.opencode/permissions.jsonc`, `.opencode/rules.md`, `.agent/rules.md`, and D3 governance files under `docs/code-governance/`. Their presence does not establish automatic loading, effective permissions, or enforcement. The following four roles are design responsibilities derived from the blueprint's four-role proposal and the project guidance. They do not imply that four agent processes, tools, or configured identities exist.

| Role | Responsibility | Default posture | Write boundary |
|---|---|---|---|
| Plan | Read requirements, architecture, relevant source/tests, and selected baseline evidence; produce a plan or review in conversation | No read or write unless explicitly listed | No standing write path. Do not invent a plan file or output path. |
| Architecture | Maintain the selected D2 architecture and decisions | No read or write unless explicitly listed | `architecture-blueprint.md` and declared `docs/architecture/**` artifacts, excluding the permission model itself, under a narrowed human-approved task list |
| Implementation | Implement approved application/test changes | No read or write unless explicitly listed | Only the exact application/test files named in an approved task and permitted by this model |
| Verification | Inspect requirements, architecture, application, tests, and selected evidence; run or design verification when separately authorized | No read or write unless explicitly listed | Only exact approved test files; if the task is pure review, no write. No verification-report path is currently pre-authorized. |

No role may change this file or another governance/permission rule to expand its own access. A proposed permission change is a human-maintained, security-critical governance change under the blueprint's change policy.

## 2. Role path allowlists

All paths are project-relative and are denied unless listed. A path pattern in this table is a role-wide maximum, not a task grant. The human-approved task must narrow the scope to exact files; a directory pattern never authorizes arbitrary files in that directory.

| Role | Project-relative path or restricted pattern | Read | Write | Task/condition | Basis |
|---|---|---|---|---|---|
| Plan | `goal.md` | Yes | No | Read project goals and authoring guidance | Blueprint §9.3; project guidance |
| Plan | `docs/req/**` | Yes | No | Read current requirements/FCs; no requirement edits | Human-maintained boundary |
| Plan | `architecture-blueprint.md`, `docs/architecture/**` | Yes | No | Read selected architecture and D2 artifacts | Architecture inputs |
| Plan | `src/tradingagents/**`, `src/cli/**`, `test/conftest.py`, `test/offline/**`, `test/live/**`, `pyproject.toml`, `requirements.txt`, `scripts/**` | Yes | No | Read-only inspection needed to plan a task; no execution or modification | Actual project paths; least-read extension |
| Plan | `baseline/**/summary.md`, `baseline/**/metrics*.json`, `baseline/**/report-consistency.json`, `baseline/**/data-availability.csv`, `baseline/**/source-integrity.json`, `baseline/**/probe-manifest.json`, `baseline/**/README.md` | Yes | No | Only baseline files relevant to the task; not all raw logs | Blueprint evidence boundary; actual baseline files |
| Plan | No file | — | — | Produce the plan in conversation; no plan-file path is created or implied | Project guidance |
| Architecture | `goal.md`, `docs/req/**` | Yes | No | Read requirements and guidance; requirements remain human-maintained | Blueprint §9.3 |
| Architecture | `architecture-blueprint.md`, `docs/architecture/**` except `docs/architecture/permission-model.md` | Yes | Yes | Only D2 artifacts named in an approved architecture task; exact file list required | Blueprint §9.3 |
| Architecture | `src/tradingagents/**`, `src/cli/**`, `test/conftest.py`, `test/offline/**`, `test/live/**`, `pyproject.toml`, `requirements.txt`, `scripts/**` | Yes | No | Inspect actual implementation and tests; never edit application code | Blueprint: no application code for Architecture |
| Architecture | `baseline/**/summary.md`, `baseline/**/metrics*.json`, `baseline/**/report-consistency.json`, `baseline/**/data-availability.csv`, `baseline/**/source-integrity.json`, `baseline/**/probe-manifest.json`, `baseline/**/README.md` | Yes | No | Selected baseline evidence only; no regeneration/formatting/cleanup | Blueprint §9.3 and baseline boundary |
| Architecture | `.github/**` | Yes | No | Read CI/governance context; no modification | Human-maintained boundary |
| Architecture | `docs/architecture/permission-model.md`, `docs/req/**`, `goal.md`, `baseline/**`, `.github/**` | No write | No | Permission, requirements, guidance, baseline, and CI remain human-maintained | Blueprint §9.3, §11 |
| Implementation | `goal.md`, `docs/req/**`, `architecture-blueprint.md`, `docs/architecture/**` | Yes | No | Read the governing requirements and architecture for the approved task | Blueprint §9.3 |
| Implementation | `src/tradingagents/**`, `src/cli/**`, `src/cli/static/**` | Yes | Yes | Only exact application files named in an approved task; no blanket directory write | Blueprint: approved application paths |
| Implementation | `test/conftest.py`, `test/offline/**`, `test/live/**` | Yes | Yes | Only exact test files named in an approved task and under test-first/approval rules | Blueprint: approved test paths |
| Implementation | `pyproject.toml`, `requirements.txt`, `docker-compose.yml`, `Dockerfile`, `scripts/**` | Yes | No | Build/dependency/evidence scripts are read-only unless a future human-approved task explicitly expands the model | User instruction on build/dependency/output boundaries |
| Implementation | `baseline/**/summary.md`, `baseline/**/metrics*.json`, `baseline/**/report-consistency.json`, `baseline/**/data-availability.csv`, `baseline/**/source-integrity.json`, `baseline/**/probe-manifest.json`, `baseline/**/README.md` | Yes | No | Read only task-relevant evidence; no baseline regeneration or cleanup | Human-maintained baseline boundary |
| Verification | `goal.md`, `docs/req/**`, `architecture-blueprint.md`, `docs/architecture/**` | Yes | No | Read acceptance basis and architecture | Verification inputs |
| Verification | `src/tradingagents/**`, `src/cli/**`, `src/cli/static/**`, `test/conftest.py`, `test/offline/**`, `test/live/**`, `pyproject.toml`, `requirements.txt` | Yes | No direct application write | Inspect implementation/tests; verification must not modify the code under test | Blueprint: read-only repository for Verification |
| Verification | `test/<approved-test-file>` | Yes | Yes | Only the exact test files declared in an approved verification task; test-first/human approval applies | Blueprint: declared test paths |
| Verification | `.github/**` | Yes | No | Inspect CI/gate configuration; no edits | Human-maintained boundary |
| Verification | `baseline/**/summary.md`, `baseline/**/metrics*.json`, `baseline/**/report-consistency.json`, `baseline/**/data-availability.csv`, `baseline/**/source-integrity.json`, `baseline/**/probe-manifest.json`, `baseline/**/README.md` | Yes | No | Task-relevant evidence only; no regeneration or cleanup | Baseline boundary |
| Verification | Verification-report path | No path is currently declared | No | If a future project report location is established, a human must first update the permission model; this document does not pre-authorize one | User instruction; no D4 report path exists |
| All roles | Unlisted project path | No | No | Default deny; no “necessary” or “any project file” exception | Blueprint default no read/write |

## 3. Human-maintained and protected content

Human-maintained does not mean unreadable. It means agents cannot modify it without a human-owned governance decision.

| Path/content | Read | Write | Protection and rationale |
|---|---|---|---|
| `docs/req/**` | Plan, Architecture, Implementation, Verification may read for their task | No agent write | Requirements and FCs are human-maintained. No reformatting or regeneration by an implementation agent. |
| `goal.md` | Roles may read as project guidance | No agent write | Human-maintained course/project guidance. |
| `baseline/**` | Selected safe evidence patterns only, as listed above | No agent write | Human-maintained evidence. Do not regenerate, format, clean, or read all raw logs by default. The `home-*`, `outside-*`, `environment*`, and reproduction artifacts are not included unless a human task explicitly selects them. |
| `.github/**` | Architecture and Verification may read; Plan and Implementation are not granted access | No agent write | Human-maintained CI and repository governance. The current CI/governance path is the root `.github/**`; the old nested path was removed by the approved layout migration. |
| `.env*` and credential files | No agent read | No agent write | Default deny. This document was prepared without reading their contents. SR-01's application-level limited protection does not grant coding agents secret access. |
| `.git/**` | No agent read | No agent write | Version-control metadata is not a normal implementation input or write target. A human can provide a diff/status excerpt instead of granting metadata access. |
| `docs/architecture/permission-model.md` | All roles may read | No role may self-edit | This permission boundary is human-controlled. The current creation is a user-authorized task, not a standing agent grant. |
| `.opencode/**`, `.agent/**`, `AGENTS*`, future rules/permission files | Existing governance files are readable only by an explicit human task | No agent write | Machine governance files exist in this checkout, but their automatic loading and effective enforcement are unverified. Future governance files remain human-maintained. |
| `docs/code-governance/**` D3 files | Existing D3 governance files are human-maintained | No agent write | D3 structural, verification, and tool-manifest documents exist; this does not establish active machine enforcement. Do not create or infer additional controls from this document. |
| D4 verification reports and review/debt/bug records | `docs/review-memo.md`, `docs/debt-register.md`, and `docs/bug-diary.md` exist as templates; no actual records are registered. Selected migration validation evidence exists under `docs/migration/validation/`. | No standing write | Template or evidence-file existence does not grant Verification write access or create a new record-write path; a future task must declare and approve any report path. Do not invent D4 records. |
| `pyproject.toml`, `requirements.txt`, build/dependency manifests | Read by Plan/Architecture/Implementation/Verification as applicable | No standing write | A future task may explicitly propose a scoped dependency/build change, but this document pre-authorizes none. |
| Dependency, build, temporary, and test output directories | Read only if a task names a relevant existing file | No standing write | No broad write grant for generated or transient files. A future task must name a project-relative path and obtain approval. |

## 4. From role maximum to task permission

A task is allowed only at the intersection of:

1. the role's maximum allowlist above;
2. the exact project-relative file list approved by the human for that task;
3. the requirements/architecture scope of that task.

Rules:

- Architecture may be permitted to write `docs/architecture/**`, but a task may narrow it to one exact file such as `docs/architecture/invariants.md`.
- Implementation may be permitted to write application/test paths, but a task must name exact files; it cannot modify the whole application tree merely because the directory is in the role maximum.
- Verification may be permitted to write exact approved tests, but a pure review has no write permission and cannot modify the implementation under test.
- Plan has no standing file output. If a task requires a plan document, a human must first name its exact path and add it to this model.
- A task cannot expand a role maximum. A path outside the role maximum is denied even if the task asks for it; the permission model must be reopened by a human first.
- A symlink, path alias, `..` component, absolute path, home path, or path that resolves outside the project does not inherit project access. All accepted paths must resolve inside the project root.
- New files are denied by default. A task may authorize a new file only when its exact project-relative path is already within the role maximum and the human names it in the task.
- No repeated approval gate is added for ordinary reversible changes already within an approved exact file list. Human approval remains required for test-first gates, security-critical changes, governance/permission changes, deferred-scope activation, or any path outside the maximum.

## 5. Actual enforcement state and limitations

| Mechanism | Verified current state | Limitation |
|---|---|---|
| This permission model | Design document only | Natural-language rules do not enforce file access. |
| Project-level OpenCode permissions | `.opencode/permissions.jsonc` exists | Explicit loading, effective merged policy, and enforcement are unverified; this document does not establish machine permission behavior. |
| AGENTS / rules | `AGENTS.md`, `.opencode/rules.md`, and `.agent/rules.md` exist in the project | Their automatic loading and actual enforcement of these boundaries are unverified. |
| D3 machine governance | `docs/code-governance/**` governance files exist | They remain design/verification records; active machine enforcement is unverified. |
| CI | Root `.github/workflows/ci.yml` runs push/PR schema, Ruff, mypy-baseline, dependency/import, regression, and clean-install jobs; PR gates add test approval, contract tests, security-path/ADR, permission-configuration, API-signature, AI-use-log, trusted semantic evidence, and aggregate checks | CI includes a static `.opencode/permissions.jsonc` check and classification-based gates, not a runtime path-permission engine. CI is retrospective, cannot prevent arbitrary reads or local edits, and remote execution is unverified. |
| Branch protection | Not verifiable from repository files | No claim is made that branch protection is enabled. |
| Human task approval/review | Required by project guidance and blueprint change policy | Human review is an operational control, not an OS boundary. |
| OS/container permissions | Not configured by this model | Tool-level rules are not an OS security sandbox. |

Partially evidenced mechanisms:

- `.opencode/permissions.jsonc` exists and CI runs a static configuration check for it;
- CI has PR gates for test approval, contract tests, security paths/ADR references, permission configuration, API signatures, AI-use log, and the aggregate result.

Still planned or unverified:

- actual OpenCode loading, merged policy, and runtime read/write restriction matching this design;
- a precedence-tested path allow/deny engine covering reads and writes, including exact task file lists;
- automated proof that protected requirements, baseline, CI, and governance files were not modified beyond classification, static checks, and human review;
- remote branch protection and human-review enforcement.

The existing file and CI gates are not proof of runtime permission enforcement. This document does not grant command execution, network access, messaging, deployment, release, package publication, secrets access, or trade execution. Those require separate human authorization and are outside file permissions.

## 6. Application runtime boundary

File permissions do not change application business authority:

- The Portfolio Manager produces an advisory `model_proposal`.
- FR-04 evaluates only the caller-supplied stock purchase scenario and returns a risk result; it does not write the formal rating.
- SB-01 forms the formal recommendation from the check-time availability summary, applicable risk result, and model rating.
- No role or application component receives trade-execution authority.
- SR-01 and SR-02 are limited application runtime protections, not coding-agent file permissions.

FR-06, FR-07, PR-01, CR-01, and context budgeting/compression/reinjection remain deferred. No write path, implementation task, interface, or acceptance is reserved for them.

## 7. Verification intents and open items

| ID | Verification intent | Evidence state |
|---|---|---|
| P-V01 | Each role can read every required input for its normal task and can write only the listed task outputs. | Planned for runtime enforcement; a project permission file exists and CI statically checks its configuration, but no effective loading/merged-policy test or runtime access test exists. |
| P-V02 | Unlisted paths, `..`, absolute paths, aliases, links, and out-of-project targets are denied. | Planned; resolution rules must be implemented before testing. |
| P-V03 | No role writes `docs/req/**`, `goal.md`, `baseline/**`, `.github/**`, `.env*`, `.git/**`, or governance files. | Planned; static diff-based verification only. |
| P-V04 | Architecture cannot modify application code or requirements; Verification cannot modify the code under test in a pure-review task. | Planned; human review/static checks. |
| P-V05 | A task can narrow a role allowlist and cannot widen it; exact file lists are required for conditional writes. | Planned; process rule, not automated. |
| P-V06 | No current document or CI check is represented as an active OS/security enforcement boundary. | Planned; documentation/review check. |

Open items that affect implementation:

1. OQ-07 still leaves coding-agent role names and whitelists pending human review. The role names here are design labels, not configured identities.
2. The machine-readable permission file, rules, AGENTS file, and D3 governance files exist, but their effective loading and path-check enforcement are not verified.
3. No verification-report path is currently declared, so Verification has no standing report-write path.
4. CI has local classification, permission-configuration, and security-path checks, but no runtime path-permission enforcement is verified. Remote branch protection and required-check enforcement are not evidenced in the checkout and must not be claimed as active.

No source conflict changes the file boundaries above. The main limitation is enforcement: the project has design guidance, a machine-readable permission file, and CI static checks, not a verified runtime file-permission engine.
