# MCP and Tool-Manifest for AI Coding Agents

- Document status: Design-time tool inventory and role-use policy; not an approval, active permission configuration, MCP connection, execution record, or security certification.
- Requirements basis: [`docs/req/requirements.yaml`](../req/requirements.yaml) v1.48.0, independently counted as 13 requirements and 55 fit criteria: 9 active requirements with 40 FCs and 4 deferred requirements with 15 FCs.
- Architecture basis: [`architecture-blueprint.md`](../../architecture-blueprint.md) and [`ADR 001`](../architecture/adr/001-graph-internal-final-check.md).
- Governance basis: [`permission-model.md`](../architecture/permission-model.md) and [`verification-constraints.md`](verification-constraints.md).
- Project instruction basis: [`AGENTS.md`](../../AGENTS.md).
- Build/test basis: [`pyproject.toml`](../../pyproject.toml) and the [`CI workflow`](../../.github/workflows/ci.yml).
- Structural basis: [`structural-constraints.md`](structural-constraints.md); proposed module allocations do not constitute implementation approval.

## 1. Purpose, Scope, and Status

This file lists the tools/capabilities exposed to the current AI coding-agent session and the role-level use boundaries derived from D2. It is a coding-agent inventory, not the TradingAgents runtime business model. Plan, Architecture, Implementation, and Verification are design responsibilities; they are not configured agent identities, MCP servers, or application roles.

The course requirement is limited to listing which tools an AI coding agent can call and which roles may use them. This document therefore does not require or create an MCP server, a tool count, a role deployment, a fixed table format, or a new implementation platform.

Status terms:

| Status | Meaning |
|---|---|
| Observed in this session | The capability is directly exposed in the current OpenCode session. Its project-level source, version, and global configuration are not verified. |
| Project-configured | A project file specifies the capability. The permission configuration now exists; effective loading and enforcement remain unverified. |
| MCP tool | A tool supplied by an MCP server. None was observed in this session. |
| Role maximum | A design boundary in this document/D2; not a task grant and not proof of enforcement. |
| Task-authorized | The current human task explicitly permits the exact use; this is narrower than both tool availability and role maximum. |
| Planned / unverified | Proposed for a later task or dependent on configuration/version not confirmed here. |

Tool availability is not authorization. A role allowlist is not a task grant. A task grant does not authorize arbitrary paths, commands, network access, credentials, or remote operations.

## 2. Observed Tools and Capabilities

The following tools were observed in the session in which this document was written. This is a session snapshot, not a guarantee that the same names or capabilities will be present in a future session or another installation. Check the actual session before use; unknown source/version and execution behavior remain unverified. These entries are not claims of permanent installation. No service was connected and no global configuration was inspected to prove availability. No MCP server or MCP tool was observed. The project now contains `.opencode/permissions.jsonc`, targeting OpenCode 1.19.3 V1 syntax with explicit loading instructions. It does not establish the source or effective enforcement of the tools observed in the earlier session.

| Tool / Capability | Kind | Availability | Purpose | Side Effects | Evidence / Limitation |
|---|---|---|---|---|---|
| `read` | Native file-read tool | Observed in this session | Read a project file or directory; returns contents with line numbers | No file write; content enters session context | Cannot establish a project-enforced path sandbox; task must constrain paths to the project root |
| `glob` | Native file-pattern tool | Observed in this session | Find files by path pattern | Read-only directory traversal | Pattern scope must be project-relative and task-approved |
| `grep` | Native content-search tool | Observed in this session | Search file contents using regular expressions | Read-only traversal/read | Does not itself enforce project confinement; task scope required |
| `edit` | Native file-edit tool | Observed in this session | Replace an exact string in a previously read file | Modifies one file | Requires prior read; only approved exact files; no source-of-truth validation built in |
| `write` | Native file-write tool | Observed in this session | Create or overwrite a file | Creates or overwrites file content | Overwrite protection is not an OS guarantee; a task may authorize only an exact path |
| `bash` | Native command-execution capability | Observed in this session | Run shell commands, including read-only inspection, project commands, and potentially network/process/file operations | Arbitrary command side effects are possible | Not a sandbox; the task must define command purpose/class, cwd, path scope, side effects, and output boundary. Ordinary approved operations need no literal command pre-enumeration; high-impact/ambiguous operations may require it |
| `webfetch` | Native network-fetch tool | Observed in this session | Retrieve a URL and return its content | Outbound network request; external content enters context | Not authorized by tool availability alone; no live vendor/model call was made here |
| `task` | Native subagent-delegation tool | Observed in this session | Launch an isolated agent for research or multi-step work | Subagent may use its own tools and consume context; writes are possible if delegated with permissions | Delegation, parallel agents, and background work are not authorized by default |
| `question` | Native user-interaction tool | Observed in this session | Ask the user to choose or clarify | Requests human input | For clarification/decisions, not a path or security bypass |
| `todowrite` | Native session-state tool | Observed in this session | Maintain a task checklist in the current session | Session-only task state | Does not create a project plan file or approve work |
| `skill` | Native instruction loader | Observed in this session | Load specialized instructions/resources for a matching task | Adds instructions/context to the session | May load only instruction resources allowed by current permissions and task scope; availability does not authorize external resource reads. If resource location/access legality is unclear, leave it unverified and do not load it to probe. A skill cannot grant filesystem, command, network, or role permissions |
| MCP server/tool | MCP capability | None observed | Would supply external tools through an MCP server | Unknown/unavailable until configured | Do not claim any MCP server is installed, connected, or usable; no connection was attempted |

The current session exposes no distinct tool for Git hosting, CI queries, PRs, deployment, dependency installation, or package publication. Those operations would require explicit task authorization and appropriate existing commands/credentials; no such authorization is provided here.

## 3. Role Capability Matrix

The four roles are the logical responsibilities in the D2 permission model. OQ-07 still leaves their configured names and whitelists pending human confirmation. This matrix does not approve a role deployment or expand a path allowlist.

| Capability | Plan | Architecture | Implementation | Verification | Conditions |
|---|---|---|---|---|---|
| Read project files, enumerate directories, search content (`read`, `glob`, `grep`) | Yes | Yes | Yes | Yes | Only task-relevant project-relative paths; no `.env*`, credentials, outside root, or unrelated baseline raw logs |
| Read D1/D2/D3/D4 inputs and `AGENTS.md` | Yes | Yes | Yes | Yes | Read-only unless a separately authorized maintenance task names the file; this is design intent, not a machine allowlist |
| Write D2 architecture artifacts (`write`, `edit`) | No | Conditional | No | No | Only exact `architecture-blueprint.md` or declared `docs/architecture/**` files named in an approved Architecture task; permission model itself remains human-controlled |
| Write application files | No | No | Conditional | No | Only exact application files in the approved task and D2 role maximum |
| Write tests | No | No | Conditional | Conditional | Only exact approved test files; Verification must not modify implementation; test-first approval applies |
| Maintain this tool manifest or another governance/permission file | No | No standing grant | No | No | Human-authorized governance maintenance only; no role may self-expand access |
| Session checklist/user questions (`todowrite`, `question`) | Yes | Yes | Yes | Yes | No file/network/approval effect; cannot replace a plan or human approval |
| Load a skill (`skill`) | Yes | Yes | Yes | Yes | Only matching instruction resources allowed by current permissions/task scope; do not load an uncertain or out-of-scope resource to test it; a skill grants no extra capability |
| Read-only project commands (`bash`) | Conditional | Conditional | Conditional | Conditional | Approve the purpose, cwd, path scope, and side-effect boundary; ordinary read/search/check commands need no pre-enumerated literal string. Project root/`TradingAgents` only for task files; no hidden writes, out-of-scope reads, credentials, or background process |
| Run approved tests/lint/type checks (`bash`) | No | No | Conditional | Conditional | Approve command class/purpose and output boundary; high-impact/complex commands may require the exact command. Run from the project root; no live/network or dependency install by default |
| Dependency installation or environment mutation (`bash`) | No | No | No | No | Requires separate explicit human authorization; not granted by this manifest |
| Local Git read-only inspection (`bash`, if authorized) | Conditional | Conditional | Conditional | Conditional | Current permission model does not grant `.git/**` access; a future human task/model update must authorize any local Git inspection |
| Local Git write operations, such as commit (`bash`) | No | No | No | No | Requires explicit local task authorization; this is not a remote-operation grant; tool availability is not permission |
| Remote Git operations: push, PR, remote CI query, merge (`bash`/network equivalents) | No | No | No | No | Each requires explicit remote-operation authorization and applicable environment; no remote Git operation is authorized by this manifest |
| Network or live model/data access (`webfetch`, `bash`, future clients) | No | No | No | Conditional | Only with explicit task/live authorization and environment; no credentials; offline substitutes cannot prove live quality |
| Delegate to a subagent (`task`) | No | No | No | No | Explicit human task authorization is required; no parallel/background expansion by default |
| MCP tools | No | No | No | No | No MCP server/tool observed; creating or connecting one is out of scope |

“Conditional” means the role maximum may allow the capability only inside an exact human-approved task and path/command list. It is not a standing authorization.

## 4. Round-Specific Authorization

Each round derives its authorization from the actual human task and the selected round plan. The round, not this manifest, selects the allowed files, tool capabilities, command purpose/work directory/path/side-effect range, and output locations. This manifest does not replace that authorization and does not establish a standing file-write limit.

A prior creation task does not grant permission for later development, tests, network access, installation, MCP connection, or remote Git operations. It also does not permanently restrict every future task to editing this manifest; each future round may select a different approved scope through its own authorization.

Without a plan or recorded approval, no development or test work is represented as approved. A documentation-only round must not be treated as application-test approval.

## 5. Usage Conditions and Boundaries

### 5.1 Path and Task Conditions

- All task files that are actively read or modified must resolve inside the project root. A symlink, alias, `..`, absolute path, home path, or external target does not inherit project access.
- Exact task paths narrow the role maximum. A directory present in a role maximum does not authorize edits to arbitrary files in that directory.
- Unlisted task paths and future task files are denied by default.
- Plan does not invent a plan file. Architecture writes only task-named D2 artifacts. Implementation writes only task-named application/test files. Verification writes only approved tests and does not change the code under test.
- Temporary files, caches, and test outputs follow the round plan and actual tool configuration. An unclaimed write outside the project is not authorized merely because a runtime environment is located outside it.
- A task cannot expand role permissions. A task-file path outside the role maximum requires a human permission-model change first.

### 5.2 Command Conditions

- `bash` is not a general “allow shell” grant. A round authorizes the command purpose/class, working directory, resource path scope, and side-effect boundary. Ordinary authorized reads, searches, and checks need no pre-enumerated literal command string; high-impact, complex, or specially scoped commands may require the exact command in the task.
- Task files actively read or modified by a command must be inside the project root. A future approved test or check command may use an existing interpreter, executable, standard library, or installed dependency that resides outside the project. That runtime use does not authorize browsing outside files, reading credentials, installing dependencies, changing global environment, or writing outside the project.
- Temporary files, caches, and test outputs remain limited by the task plan and actual configuration. An undeclared write outside the project is not granted by the fact that the runtime environment is external.
- Within an explicitly approved purpose/path/side-effect scope, ordinary reads, searches, and checks do not require repeated approval. Approval is not refreshed merely because the same ordinary operation is repeated.
- After execution, evidence records the actual command used. The ex-ante authorization scope and the ex-post command record remain distinct.
- Test/lint/type commands use the existing `src/` and `test/` layout from the project root. The default test command is `pytest -q`, whose configuration excludes `integration`; this does not establish a live pass.
- No install, dependency upgrade, live test, model/vendor call, background process, or network action is implied by command availability. Nested shell commands, redirection to undeclared paths, and arbitrary command construction remain prohibited outside the authorized scope.
- Long-running or autonomous background work is not authorized by default. No such command was executed for this revision.

### 5.3 Protected Inputs

- `docs/req/**`, `goal.md`, `D2.md`, `baseline/**`, `.github/**`, governance/permission files, `.env*`, and credentials are read-only or forbidden as specified by the permission model.
- Requirements and design guidance may be read as task inputs; they are not writable by an implementation or verification agent.
- Do not read `.env*` or credential values, and do not use real credentials as fixtures. SR-01's limited runtime protection does not grant coding-agent secret access.
- Baseline evidence is read selectively; it must not be regenerated, formatted, cleaned, or rewritten.
- Version-control metadata is not a normal write target. Local Git write operations require explicit local task authorization; push, PR, remote CI query, and merge require separate remote-operation authorization.

### 5.4 Non-Authorization Rules

- Tool availability does not imply permission to write, execute, install, fetch, delegate, or connect to a service.
- A skill may load only instruction resources allowed by current permissions and task scope. If its source/location/access legality cannot be confirmed, leave it unverified and do not load it as a probe. A skill cannot grant extra file, command, network, or role permissions.
- An MCP server is not added or connected by this document.
- The list does not grant parallel agents, background tasks, deployment, publication, messaging, or trade execution.
- Test approval is separate. Passing tests is not PR approval or acceptance.
- A role must not modify governance, permission, rules, AGENTS, or CI files to expand its own access.

## 6. Enforcement Limitations and Open Items

| Mechanism | Current Evidence | Limitation / Status |
|---|---|---|
| This manifest | Documentation only | Natural-language inventory does not enforce tool access or paths |
| `AGENTS.md` | Exists at project root and was read as guidance | Natural-language instructions are not an OS sandbox; it does not itself grant tools |
| D2 permission model | Exists as a Proposed design artifact | Role maxima are not active enforcement; its older “no AGENTS.md found” and “no D3 files” metadata is stale relative to the current checkout |
| Project OpenCode permissions | `.opencode/permissions.jsonc` exists with default-deny and per-role rules | Explicit loading is required; effective merged policy and enforcement have not been tested. Commands/discovery remain denied pending round configuration |
| Project rules | `.agent/rules.md` exists; human-only `.opencode/rules.md` remains missing | Document presence is not proof of automatic loading or enforcement |
| Structural constraints | `docs/code-governance/structural-constraints.md` exists | Proposed allocations and checks are not implementation or execution evidence |
| MCP configuration | No project-local MCP configuration or MCP tool observed | No server, endpoint, credential, or connection is claimed; global OpenCode config was not inspected |
| CI | CI runs install, `pytest -q`, ruff, and clean-install smoke checks | CI is retrospective and contains no verified path/tool-permission gate; it cannot prevent local reads or writes |
| Branch protection | Not verifiable from repository files | Do not claim it is enabled |
| OpenCode/tool provenance | Tool names and availability observed in this session | Version, package source, and execution isolation are unverified |
| OS/container sandbox | Not established by project evidence | Tool rules are not a substitute for OS isolation |

Open items:

1. **OQ-07 remains pending.** The four role names are design labels, not approved configured identities or machine whitelists.
2. The intent that roles may read D3/D4 inputs and `AGENTS.md` is a design boundary, not proof that a machine allowlist exists. Actual permission enforcement remains for authorized D3 configuration work; this document supplies no new role or enforcement mechanism.
3. The current MCP server inventory is empty/unverified. No MCP capability is granted.
4. The current round-plan inventory is absent; no implementation/test authorization exists.
5. Local Git writes, remote Git operations, network/live API use, and dependency installation remain separate human authorizations.
6. The permission model's AGENTS/D3 file-presence metadata and role/tool synchronization require future human-maintained updates; this task may not edit that file.

No application implementation, test execution, MCP connection, network call, dependency installation, or acceptance claim is made by this manifest.

## Current Configuration Relationship

The role matrix is a design maximum, not the effective tool grant. The current permission file deliberately denies command execution, search/discovery, delegation, skills, and network tools. Conditional capabilities in this manifest remain unavailable until a human approves and configures the relevant round. Reading the first round plan does not authorize its creation, editing, tests, or implementation. The pending D2 role decision remains pending.
