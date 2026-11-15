# D2 Permission Model

Status: **v0.3 — ADD-R round 3 draft / pending human review**
Date: 2026-11-15
Amended by: `docs/architecture/adr/003-add-r-round-3.md`
D1 basis: `docs/req/requirements.yaml` v1.24.0
Status basis: 17 active requirements are approved as a requirement-design baseline; `QR-02` is deferred and outside current acceptance; approval does not assert implementation or measured results
Implementation status: **design only; no application code changed**

---

## 1. Two separate permission domains

1. **Runtime AI permissions** — what the in-product LLM agents may do during an analysis run.
2. **Coding-agent permissions** — what software-engineering agents may read/write in the repository and workspace.

They are not interchangeable. A coding agent may edit documentation or, after approval, application code. A runtime AI agent may not edit files, read environment variables, or access arbitrary networks.

The ADD-R round adds deterministic services (risk, metrics, history, recovery) that are **not runtime AI tools** and must not be callable by the model to change a formal outcome. Export is deferred. `RunCoordinator` and `RunContext` are control objects, not model tools.

---

## 2. Runtime AI permissions

### 2.1 Default

Runtime AI is **default-deny** outside the registered tool boundary.

| Resource / action | Runtime AI | Enforcement |
|---|---|---|
| Read provided context/evidence | Allowed | Context assembler |
| Call registered data tools | Allowed | Tool registry |
| Produce reports/proposals | Allowed | Agent state |
| Read `.env`, environment variables, secrets | Denied | No tool; no file access |
| Read arbitrary files | Denied | No file tool |
| Write files/artifacts/memory | Denied | Publisher/MemoryService only |
| Run shell commands | Denied | No shell tool |
| Access arbitrary URLs/network | Denied | Fixed vendor tools only |
| Modify code or configuration | Denied | No file/write tool |
| Invoke `SafetyGate`/`ArtifactPublisher` | Denied | Deterministic code only |
| Override gate result | Denied | Gate not model-callable |
| Read other runs' memory/cache directly | Denied | Run-scoped context; no file tool |
| Receive historical lessons through `MemoryService` | Allowed with filtering | Authorized, ticker/date/retention-filtered, committed entries only |
| Supply authoritative portfolio/order risk input | Denied | Caller/application supplies validated decimals |
| Change or bypass the risk result | Denied | Pure evaluator inside the gate |
| Call the metric calculator or edit the metric block | Denied | Program-appended block |
| Call history/recovery (export deferred) | Denied | CLI/application only |
| Receive the downstream brief | Allowed for five debate roles only | `ContextAssembler` delivers a view |
| Write raw model output to final decision | Denied | Final decision is gate output |

### 2.2 Tool boundary

Allowed tools are the registered data tools, for example:

- `get_stock_data`
- `get_indicators`
- `get_verified_market_snapshot`
- `get_fundamentals`
- `get_balance_sheet`
- `get_cashflow`
- `get_income_statement`
- `get_insider_transactions`
- `get_news`
- `get_global_news`
- `get_macro_indicators`
- `get_prediction_markets`

New `FR-07` may expose a `get_derived_metrics`-style tool, but the deterministic metric block is appended by code regardless of whether the model calls it. The tool is an aid, not the correctness mechanism.

The tool layer enforces:

- ticker normalization and path safety;
- date clamping and as-of visibility;
- fixed vendor endpoints;
- no arbitrary URL parameter;
- no credentials in tool output;
- run-scoped cache and evidence;
- no direct vendor bypass.

The model cannot add tools at runtime.

### 2.3 Deterministic service boundary

| Service | Model-callable | May read | May write | Must not |
|---|---|---|---|---|
| `RiskInputValidator` | No; called only by `SafetyGate` | Caller envelope | None | LLM, network, UI, second applicability caller |
| `PortfolioRiskEvaluator` | No; called only by `SafetyGate` | Validated input, policy snapshot | None | LLM, network, vendor, persistence, UI, second gate |
| `RiskPolicyResolver` | No | Policy catalog/source | None | Model, network |
| `RiskEvidenceStore` | No | Validated input/diagnostic | Via publisher only | Raw invalid values, secrets |
| `FinancialFactService` | Through the unified data tool path only | Structured fact payload via `DataAccessService` | Evidence records | Direct vendor calls, direct `sec_edgar.py` import/call |
| `FinancialMetricService` | No | Fact set, price, as-of | None | Model, network, vendor |
| `MetricConflictDetector` | No | Block, structured claims | None | Free-form number claims as verified |
| `DownstreamBriefBuilder` | No | Reports, program coverage view/version, metric block, policy, tokenizer | None | Mutating full/formal artifacts, injecting full+brief for the same role |
| `HistoryService` | No | Committed publication snapshots | None | Listing pending/failed as success |
| `ExportService` (deferred) | No | Verified publication | Future empty export target only | Overwriting a non-empty target or escaping root; not current |
| `RunCoordinator` | No | Stage inputs and service handles | Stage order/handoff only | Formal decision, gate bypass, direct vendor/formal write |
| `RunContext` | No | Config/request, policy handles | Identity, clock, versions, paths, dependency refs | Business policy, gate/risk/metric/context decisions, formal write |
| `DataAccessService` | No; called by tools/prefetch/preflight | Query request, run context | Run cache, evidence, counters | Direct model call, arbitrary URL, hidden retry outside budget |
| `RecoveryService` | No | Saved recovery/formal records | Through publisher/memory only, under `StartupRecoveryGuard` | LLM, external data, graph, settlement, reflection, second commit marker |
| `StartupRecoveryGuard` | No | Startup/guard state | Single-process guard state | Model, vendor, second publication authority; deleting another guard; claiming lease/fencing |
| `RunOwnershipLock` (deferred) | No | Future multi-worker ownership state | Future lock/lease state | Not current; no current code may claim it |
| `PortfolioManagerAdapter` | PM is a runtime AI role; adapter itself is deterministic | Full reports/plans/risk debate/past memory | `ModelProposal` only | Formal decision, gate override, promoting Trader/risk-debater output |
| `MemoryRecoveryCoordinator` | No | Pending entry/guard/reservation status | Coordination status only | Ownership transfer, duplicate entry, holding locks while waiting |

### 2.4 Brief delivery boundary

- Only Bull Researcher, Bear Researcher, and the three risk debaters receive the downstream brief.
- For those five roles, the brief replaces the four full analyst reports; the same role never receives both.
- All other roles, formal records, history, recovery, and the permanent publication snapshot keep full inputs.
- The brief is generated/reused before the five roles receive context, uses the program coverage view and its version, and is not generated after the final decision.
- The brief is a view, not a formal artifact or a second context authority.
- Mandatory content (program gaps, metric block/sources, safety constraints) is never truncated; protected markers prevent generic compression from shortening it.
- `BRIEF_DISABLED` uses the normal full-input path; `BRIEF_FULL_REPORT` is allowed only with explicit policy permission and hard-cap compliance; `BRIEF_REJECTED` is terminal and cannot re-enter normal input or generic compression.

---

## 3. Coding-agent permissions

### 3.1 Default

Coding agents are **default-deny**. A role receives only the paths/actions in its whitelist. Anything not listed is denied.

### 3.2 Roles and path whitelists

| Role | Active in ADD-R round 2 | Allowed writes | Allowed reads | Denied |
|---|---|---|---|---|
| `architect_add_r` | Yes (Round 3) | `architecture-blueprint.md`, `docs/architecture/**` | `docs/req/**`, `TradingAgents/**`, `baseline/**`, `docs/architecture/**` | `TradingAgents/**` writes, `scripts/**` writes, `baseline/**` writes, `docs/req/**` writes, `.env`, secrets, Git history changes |
| `reviewer` | Yes | None | Everything in repository and baseline | All writes |
| `baseline_operator` | Future | `scripts/**`, `baseline/**` (new run/check directories only) | `TradingAgents/**`, `docs/**`, `baseline/**` | `TradingAgents/**` writes, `docs/req/**` writes, `.env`, secrets |
| `implementation_agent` | Future, after approval | `TradingAgents/tradingagents/**`, `TradingAgents/cli/**`, `TradingAgents/tests/**`, `scripts/**` | `TradingAgents/**`, `docs/**`, `baseline/**` | `docs/req/**` writes, `baseline/**` writes except evidence output, `.env`, secrets, Git history changes |
| `test_agent` | Future, after approval | `scripts/**`, `baseline/**` (new run/check directories only) | `TradingAgents/**`, `docs/**`, `baseline/**` | `TradingAgents/**` writes, `docs/req/**` writes, `.env`, secrets |
| `d1_editor` | Future, after approval | `docs/req/**` | All docs, read-only repository | `TradingAgents/**` writes, `scripts/**` writes, `baseline/**` writes, `.env`, secrets |
| `release_agent` | Future, after approval | None by default; explicit release manifest only | All | Git commit/push, secrets, app code unless separately approved |

The Round 3 architecture round only writes `architecture-blueprint.md`, `docs/architecture/**`, and the new ADR 003. It does not write requirements, application code, tests, baseline evidence, governance rules, permissions, or secrets.

### 3.3 Path deny list

Denied to all coding agents unless a future explicit exception is approved:

- `.env`, `.env.*`, `.env.enterprise`
- `**/*.pem`, `**/*.key`, `**/*.p12`, `**/*.pfx`
- `**/secrets/**`, `**/credentials/**`
- `~/.tradingagents/**` (runtime state)
- `.git/**`
- OS keychain / shell history

### 3.4 Command policy

File permissions are not the only boundary. Commands are also default-deny.

| Command class | Default | Notes |
|---|---|---|
| `git status`, `git diff`, `git log`, `git show` | Allowed | Read-only |
| `git commit`, `git push`, `git reset`, `git clean`, force operations | Denied unless explicitly approved | Never used to hide failures |
| Test/lint commands | Allowed for test roles | Must not modify app source |
| Package install/upgrade | Denied unless explicitly approved | Protects environment reproducibility |
| Network downloads | Denied unless explicitly approved | No arbitrary vendor/tool acquisition |
| File deletion outside allowed output dirs | Denied | No cleanup that hides evidence |

---

## 4. Desensitization output boundaries

Every boundary below must use `SecretRedactor` or an equivalent allowlist.

| Boundary | Data that may appear | Rule |
|---|---|---|
| CLI stdout/stderr | Reports, status, errors | No secrets; endpoint sanitized |
| Application logs | Warnings, errors, vendor failures | No raw URLs with query; no keys |
| Error messages/tracebacks | Exception text | Scrub keys/tokens/userinfo/query |
| Run manifest | Config, counts, status, gate, risk, metric binding, section manifest | Allowlisted config; no secrets |
| Final-state JSON | Reports, debate, decision, risk evidence | No keys; no raw endpoint credentials |
| Risk input artifact | Validated decimal input and provenance | Only validated input; no raw invalid value; no secret |
| Risk diagnostic artifact | Failure outcome and reason code | No raw invalid value; no secret |
| Risk policy snapshot | Thresholds, digests, approval reference | No secret; provisional labeled |
| Report Markdown | Reports, news links, metric block, risk summary | No keys; preserve source labels |
| Report HTML | Rendered report | Existing CSP/no-script/no-image posture; escape external text |
| Report section manifest | Paths, fields, sizes, hashes | Relative paths only; no secret |
| Metric evidence bundle | Facts, formulas, versions, digests | No secret; no raw credentials |
| Memory log | Final decision, rating, binding, risk summary | Final record only; no raw proposal as final; no secrets |
| Preferences | Provider, models, audit endpoint, restore endpoint, secret refs | Audit endpoint = scheme/host/path; restore endpoint keeps only non-sensitive query parameters and secret_ref names; no inline sensitive values |
| Run evidence journal | Query/status/metrics | No secrets; endpoint sanitized |
| Checkpoint SQLite | Graph state | No keys; treat as sensitive local state |
| Publish staging/manifest | Artifact hashes/paths | No secrets; no raw env |
| Archive/history/recovery diagnostics (future export) | Publication metadata, paths, hashes | No secrets; in-root relative paths |
| API return | Status, formal decision, verified publication | No secrets; no unapproved proposal as final; typed errors |
| Streaming/debug output | Intermediate messages/proposals | Marked unapproved/intermediate; scanned; no formal decision claim |
| Telemetry/monitoring | Counts/status/latency | No prompts, no secrets |
| Coding-agent transcripts | Commands, file edits | Separate from app runtime; redact secrets if exported |

Rules:

- audit endpoint = scheme + host + path only;
- restore endpoint = scheme + host + path + allowlisted non-sensitive query parameters + `secret_ref` names; no inline sensitive values;
- every write records `write_scan_status`; the terminal manifest records final `run_scan_status`; completed requires both clean/redacted;
- preferences remain the original global file; concurrent local runs use atomic replace and last-writer-wins;
- never record full environment variables;
- never record API keys, tokens, passwords, or secret-like values;
- empty secret values are never treated as matches; too-short values follow the requirement's short-secret rule rather than a blanket scan; scanner/rule-version failure fails closed;
- prefer hashes/digests and allowlisted metadata over raw values;
- paths derived from report prose, filters, or `run_id` are confined to the configured root;
- if export is reactivated, paths from an export target are confined and a non-empty target returns `EXPORT_CONFLICT`;
- secret scanning is a planned test, not a completed result; a clean scan proves only the defined scope/rules/fixtures.

---

## 5. Runtime vs coding-agent summary

| Question | Runtime AI | Coding agent |
|---|---|---|
| Can read repo files? | No | Role-dependent |
| Can write repo files? | No | Role-dependent, default deny |
| Can read env/secrets? | No | Denied |
| Can run shell? | No | Role/command policy |
| Can access network? | Only fixed tools | Denied unless approved |
| Can change final rating? | No; gate only | No |
| Can supply portfolio/order risk input? | No; caller/application | No |
| Can bypass risk or metrics? | No | No |
| Can publish artifacts? | No; publisher only | No; only via code changes after approval |
| Can query history (export deferred)? | No | No runtime authority |
| Can approve requirements/architecture? | No | No; humans only |

---

## 6. Status

- Runtime permission enforcement: **design only**.
- Coding-agent permission enforcement: **design only**.
- Permission tests: **not started**.
- Round 3 coding agents currently allowed to write only `architecture-blueprint.md`, `docs/architecture/**`, and `docs/architecture/adr/003-add-r-round-3.md`.
- Current recovery is single-process; `RunOwnershipLock` lease/fencing/takeover is deferred.
- No application code changed.
- D1 v1.24.0; 17 active requirements are approved as a requirement-design baseline; QR-02 is deferred; approval does not assert implementation or measured results.
