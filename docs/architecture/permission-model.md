# Coding-Agent Permission Model

- Document status: Proposed permission design; not an active permission configuration, security certification, or claim that enforcement exists.
- Requirements basis: [`docs/req/requirements.yaml`](../req/requirements.yaml) version 1.48.0, independently counted as 13 requirements and 55 fit criteria: 9 active requirements with 40 FCs and 4 deferred requirements with 15 FCs.
- Architecture basis: [`architecture-blueprint.md`](../../architecture-blueprint.md), especially §9.3 and §11, and [`ADR 001`](adr/001-graph-internal-final-check.md).
- Cross-check basis: [`invariants.md`](invariants.md), [`trace-matrix.md`](trace-matrix.md), [`memory-design.md`](memory-design.md), [`runtime-policy-catalog.md`](runtime-policy-catalog.md), and [`evaluation-table.md`](evaluation-table.md).
- Project guidance checked: `goal.md` and `D2.md`.
- Secret handling: no `.env*`, credential, or secret content was read. Only project paths and non-secret governance files were inspected.

This document describes file-level permissions for AI coding agents. It is not the TradingAgents runtime business model. Analyst, researcher, Trader, Portfolio Manager, SB-01, and other application roles are not file-access roles. Conversely, Plan/Architecture/Implementation/Verification are coding responsibilities, not application authorities.

## 1. Role model

The project does not contain an `AGENTS.md`, `.opencode/` permissions configuration, `.opencode/rules.md`, `.agent/rules.md`, or D3 machine-permission file. The following four roles are design responsibilities derived from the blueprint's four-role proposal and the project guidance. They do not imply that four agent processes, tools, or configured identities exist.

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
| Plan | `goal.md`, `D2.md` | Yes | No | Read project goals and authoring guidance | Blueprint §9.3; project guidance |
| Plan | `docs/req/**` | Yes | No | Read current requirements/FCs; no requirement edits | Human-maintained boundary |
| Plan | `architecture-blueprint.md`, `docs/architecture/**` | Yes | No | Read selected architecture and D2 artifacts | Architecture inputs |
| Plan | `TradingAgents/tradingagents/**`, `TradingAgents/cli/**`, `TradingAgents/tests/**`, `TradingAgents/pyproject.toml`, `TradingAgents/requirements.txt`, `scripts/**` | Yes | No | Read-only inspection needed to plan a task; no execution or modification | Actual project paths; least-read extension |
| Plan | `baseline/**/summary.md`, `baseline/**/metrics*.json`, `baseline/**/report-consistency.json`, `baseline/**/data-availability.csv`, `baseline/**/source-integrity.json`, `baseline/**/probe-manifest.json`, `baseline/**/README.md` | Yes | No | Only baseline files relevant to the task; not all raw logs | Blueprint evidence boundary; actual baseline files |
| Plan | No file | — | — | Produce the plan in conversation; no plan-file path is created or implied | Project guidance |
| Architecture | `goal.md`, `D2.md`, `docs/req/**` | Yes | No | Read requirements and guidance; requirements remain human-maintained | Blueprint §9.3 |
| Architecture | `architecture-blueprint.md`, `docs/architecture/**` except `docs/architecture/permission-model.md` | Yes | Yes | Only D2 artifacts named in an approved architecture task; exact file list required | Blueprint §9.3 |
| Architecture | `TradingAgents/tradingagents/**`, `TradingAgents/cli/**`, `TradingAgents/tests/**`, `TradingAgents/pyproject.toml`, `TradingAgents/requirements.txt`, `scripts/**` | Yes | No | Inspect actual implementation and tests; never edit application code | Blueprint: no application code for Architecture |
| Architecture | `baseline/**/summary.md`, `baseline/**/metrics*.json`, `baseline/**/report-consistency.json`, `baseline/**/data-availability.csv`, `baseline/**/source-integrity.json`, `baseline/**/probe-manifest.json`, `baseline/**/README.md` | Yes | No | Selected baseline evidence only; no regeneration/formatting/cleanup | Blueprint §9.3 and baseline boundary |
| Architecture | `TradingAgents/.github/**` | Yes | No | Read CI/governance context; no modification | Human-maintained boundary |
| Architecture | `docs/architecture/permission-model.md`, `docs/req/**`, `goal.md`, `D2.md`, `baseline/**`, `TradingAgents/.github/**` | No write | No | Permission, requirements, guidance, baseline, and CI remain human-maintained | Blueprint §9.3, §11 |
| Implementation | `goal.md`, `D2.md`, `docs/req/**`, `architecture-blueprint.md`, `docs/architecture/**` | Yes | No | Read the governing requirements and architecture for the approved task | Blueprint §9.3 |
| Implementation | `TradingAgents/tradingagents/**`, `TradingAgents/cli/**`, `TradingAgents/main.py`, `TradingAgents/assets/**`, `TradingAgents/cli/static/**` | Yes | Yes | Only exact application files named in an approved task; no blanket directory write | Blueprint: approved application paths |
| Implementation | `TradingAgents/tests/**` | Yes | Yes | Only exact test files named in an approved task and under test-first/approval rules | Blueprint: approved test paths |
| Implementation | `TradingAgents/pyproject.toml`, `TradingAgents/requirements.txt`, `TradingAgents/docker-compose.yml`, `TradingAgents/Dockerfile`, `scripts/**` | Yes | No | Build/dependency/evidence scripts are read-only unless a future human-approved task explicitly expands the model | User instruction on build/dependency/output boundaries |
| Implementation | `baseline/**/summary.md`, `baseline/**/metrics*.json`, `baseline/**/report-consistency.json`, `baseline/**/data-availability.csv`, `baseline/**/source-integrity.json`, `baseline/**/probe-manifest.json`, `baseline/**/README.md` | Yes | No | Read only task-relevant evidence; no baseline regeneration or cleanup | Human-maintained baseline boundary |
| Verification | `goal.md`, `D2.md`, `docs/req/**`, `architecture-blueprint.md`, `docs/architecture/**` | Yes | No | Read acceptance basis and architecture | Verification inputs |
| Verification | `TradingAgents/tradingagents/**`, `TradingAgents/cli/**`, `TradingAgents/main.py`, `TradingAgents/assets/**`, `TradingAgents/cli/static/**`, `TradingAgents/tests/**`, `TradingAgents/pyproject.toml`, `TradingAgents/requirements.txt` | Yes | No direct application write | Inspect implementation/tests; verification must not modify the code under test | Blueprint: read-only repository for Verification |
| Verification | `TradingAgents/tests/<approved-test-file>` | Yes | Yes | Only the exact test files declared in an approved verification task; test-first/human approval applies | Blueprint: declared test paths |
| Verification | `TradingAgents/.github/**` | Yes | No | Inspect CI/gate configuration; no edits | Human-maintained boundary |
| Verification | `baseline/**/summary.md`, `baseline/**/metrics*.json`, `baseline/**/report-consistency.json`, `baseline/**/data-availability.csv`, `baseline/**/source-integrity.json`, `baseline/**/probe-manifest.json`, `baseline/**/README.md` | Yes | No | Task-relevant evidence only; no regeneration or cleanup | Baseline boundary |
| Verification | Verification-report path | No path is currently declared | No | If a future project report location is established, a human must first update the permission model; this document does not pre-authorize one | User instruction; no D4 report path exists |
| All roles | Unlisted project path | No | No | Default deny; no “necessary” or “any project file” exception | Blueprint default no read/write |

## 3. Human-maintained and protected content

Human-maintained does not mean unreadable. It means agents cannot modify it without a human-owned governance decision.

| Path/content | Read | Write | Protection and rationale |
|---|---|---|---|
| `docs/req/**` | Plan, Architecture, Implementation, Verification may read for their task | No agent write | Requirements and FCs are human-maintained. No reformatting or regeneration by an implementation agent. |
| `goal.md`, `D2.md` | Roles may read as project guidance | No agent write | Human-maintained course/project guidance. |
| `baseline/**` | Selected safe evidence patterns only, as listed above | No agent write | Human-maintained evidence. Do not regenerate, format, clean, or read all raw logs by default. The `home-*`, `outside-*`, `environment*`, and reproduction artifacts are not included unless a human task explicitly selects them. |
| `TradingAgents/.github/**` | Architecture and Verification may read; Plan and Implementation are not granted access | No agent write | Human-maintained CI and repository governance. The actual nested path is `TradingAgents/.github/**`; no root `.github/` exists in this checkout. |
| `.env*` and credential files | No agent read | No agent write | Default deny. This document was prepared without reading their contents. SR-01's application-level limited protection does not grant coding agents secret access. |
| `.git/**` | No agent read | No agent write | Version-control metadata is not a normal implementation input or write target. A human can provide a diff/status excerpt instead of granting metadata access. |
| `docs/architecture/permission-model.md` | All roles may read | No role may self-edit | This permission boundary is human-controlled. The current creation is a user-authorized task, not a standing agent grant. |
| `.opencode/**`, `.agent/**`, `AGENTS*`, future rules/permission files | None currently exist; if introduced, read only by an explicit human task | No agent write | No machine governance configuration exists in this checkout. Future governance files are human-maintained. |
| `docs/code-governance/**` D3 files | None currently exist; future files are human-maintained | No agent write | D3 machine permissions, rules, and tool manifests are not present here. Do not create or infer them from this document. |
| D4 verification reports and review/debt/bug records | None currently exist as declared project paths | No standing write | Verification reports require a future declared path and human update to this model. Do not invent D4 files. |
| `TradingAgents/pyproject.toml`, `requirements.txt`, build/dependency manifests | Read by Plan/Architecture/Implementation/Verification as applicable | No standing write | A future task may explicitly propose a scoped dependency/build change, but this document pre-authorizes none. |
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
| Project-level OpenCode permissions | No `.opencode/permissions.jsonc` or `.opencode/` directory found | Default agent/tool behavior is not established by this document; no machine allowlist is configured here. |
| AGENTS / rules | No `AGENTS.md`, `.opencode/rules.md`, or `.agent/rules.md` found in the project | No persistent agent-specific rule file currently enforces these boundaries. |
| D3 machine governance | No `docs/code-governance/**` files found | Structural constraints and MCP/tool permissions remain unconfigured in this checkout. |
| CI | `TradingAgents/.github/workflows/ci.yml` runs install, pytest, ruff, and clean-install smoke jobs; `release-assets.yml` builds release assets | These are test/lint/build checks. No path-permission check is present. CI is post-hoc and cannot prevent arbitrary reads or local edits. |
| Branch protection | Not verifiable from repository files | No claim is made that branch protection is enabled. |
| Human task approval/review | Required by project guidance and blueprint change policy | Human review is an operational control, not an OS boundary. |
| OS/container permissions | Not configured by this model | Tool-level rules are not an OS security sandbox. |

Planned mechanisms, not current enforcement:

- a machine-readable per-role permission file matching the actual OpenCode version;
- a path allow/deny check covering reads and writes, including exact task file lists;
- human-approved test-first and security-critical change gates with recorded evidence;
- verification that protected requirements, baseline, CI, and governance files were not modified.

No planned mechanism is claimed to be implemented. This document does not grant command execution, network access, messaging, deployment, release, package publication, secrets access, or trade execution. Those require separate human authorization and are outside file permissions.

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
| P-V01 | Each role can read every required input for its normal task and can write only the listed task outputs. | Planned; no permission test or enforcement configuration exists. |
| P-V02 | Unlisted paths, `..`, absolute paths, aliases, links, and out-of-project targets are denied. | Planned; resolution rules must be implemented before testing. |
| P-V03 | No role writes `docs/req/**`, `goal.md`, `D2.md`, `baseline/**`, `TradingAgents/.github/**`, `.env*`, `.git/**`, or governance files. | Planned; static diff-based verification only. |
| P-V04 | Architecture cannot modify application code or requirements; Verification cannot modify the code under test in a pure-review task. | Planned; human review/static checks. |
| P-V05 | A task can narrow a role allowlist and cannot widen it; exact file lists are required for conditional writes. | Planned; process rule, not automated. |
| P-V06 | No current document or CI check is represented as an active OS/security enforcement boundary. | Planned; documentation/review check. |

Open items that affect implementation:

1. OQ-07 still leaves coding-agent role names and whitelists pending human review. The role names here are design labels, not configured identities.
2. No machine-readable permission file, rules file, AGENTS file, path check, or D3 machine governance currently exists.
3. No verification-report path is currently declared, so Verification has no standing report-write path.
4. Branch protection and CI path checks are not evidenced in the checkout; they must not be claimed as active.

No source conflict changes the file boundaries above. The main limitation is enforcement: the current project has design guidance and ordinary CI, not a verified file-permission engine.
