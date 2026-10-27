# D2 Permission Model

Status: **v0.1 — draft / pending human review**  
Date: 2026-10-27  
D1 baseline: `docs/req/requirements.yaml` (working baseline; not finally approved)  
Implementation status: **design only; no application code changed**

---

## 1. Two separate permission domains

This document separates:

1. **Runtime AI permissions** — what the in-product LLM agents may do during an analysis run.
2. **Coding-agent permissions** — what software-engineering agents may read/write in the repository and workspace.

They are not interchangeable. A coding agent may edit documentation or, after approval, application code. A runtime AI agent may not edit files, read environment variables, or access arbitrary networks.

---

## 2. Runtime AI permissions

### 2.1 Default

Runtime AI is **default-deny** outside the registered tool boundary.

| Resource / action | Runtime AI | Enforcement |
|---|---|---|
| Read provided context/evidence | Allowed | Prompt/context assembler |
| Call registered data tools | Allowed | Tool registry |
| Produce reports/proposals | Allowed | Agent state |
| Read `.env`, environment variables, secrets | Denied | No tool; no file access |
| Read arbitrary files | Denied | No file tool |
| Write files/artifacts/memory | Denied | Publisher/MemoryService only |
| Run shell commands | Denied | No shell tool |
| Access arbitrary URLs/network | Denied | Fixed vendor tools only |
| Modify code or configuration | Denied | No file/write tool |
| Invoke SafetyGate or ArtifactPublisher | Denied | Deterministic code only |
| Override gate result | Denied | Gate not model-callable |
| Read other runs' memory/cache | Denied | Run-scoped context |
| Write raw model output to final decision | Denied | Final decision is gate output |

### 2.2 Tool boundary

Allowed tools are only the registered data tools, for example:

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

The tool layer enforces:

- ticker normalization and path safety;
- date clamping;
- fixed vendor endpoints;
- no arbitrary URL parameter;
- no credentials in tool output;
- run-scoped cache and evidence.

The model cannot add tools at runtime.

---

## 3. Coding-agent permissions

### 3.1 Default

Coding agents are **default-deny**. A role receives only the paths/actions listed in its whitelist. Anything not listed is denied.

### 3.2 Roles and path whitelists

| Role | Active in D2 | Allowed writes | Allowed reads | Denied |
|---|---|---|---|---|
| `architect_d2` | Yes | `architecture-blueprint.md`, `docs/architecture/**` | `docs/req/**`, `TradingAgents/**`, `baseline/**`, `docs/architecture/**` | `TradingAgents/**` writes, `scripts/**` writes, `baseline/**` writes, `docs/req/**` writes, `.env`, secrets, Git history changes |
| `reviewer` | Yes | None | Everything in repository and baseline | All writes |
| `baseline_operator` | Future | `scripts/**`, `baseline/**` (new run/check directories only) | `TradingAgents/**`, `docs/**`, `baseline/**` | `TradingAgents/**` writes, `docs/req/**` writes, `.env`, secrets |
| `implementation_agent` | Future, after approval | `TradingAgents/tradingagents/**`, `TradingAgents/cli/**`, `TradingAgents/tests/**`, `scripts/**` | `TradingAgents/**`, `docs/**`, `baseline/**` | `docs/req/**` writes, `baseline/**` writes except evidence output, `.env`, secrets, Git history changes |
| `test_agent` | Future, after approval | `scripts/**`, `baseline/**` (new run/check directories only) | `TradingAgents/**`, `docs/**`, `baseline/**` | `TradingAgents/**` writes, `docs/req/**` writes, `.env`, secrets |
| `d1_editor` | Future, after approval | `docs/req/**` | All docs, read-only repository | `TradingAgents/**` writes, `scripts/**` writes, `baseline/**` writes, `.env`, secrets |
| `release_agent` | Future, after approval | None by default; explicit release manifest only | All | Git commit/push, secrets, app code unless separately approved |

### 3.3 Path deny list

The following paths are denied to all coding agents unless a future explicit exception is approved:

- `.env`, `.env.*`, `.env.enterprise`
- `**/*.pem`, `**/*.key`, `**/*.p12`, `**/*.pfx`
- `**/secrets/**`, `**/credentials/**`
- `~/.tradingagents/**` (runtime state)
- `.git/**`
- OS keychain / shell history

### 3.4 Command policy

For coding agents, file permissions are not the only boundary. Commands are also default-deny.

| Command class | Default | Notes |
|---|---|---|
| `git status`, `git diff`, `git log`, `git show` | Allowed | Read-only |
| `git commit`, `git push`, `git reset`, `git clean`, force operations | Denied unless explicitly approved | Never used to hide failures |
| Test/lint commands | Allowed for test roles | Must not modify app source |
| Package install/upgrade | Denied unless explicitly approved | Protects environment reproducibility |
| Network downloads | Denied unless explicitly approved | No arbitrary vendor/tool acquisition |
| File deletion outside allowed output dirs | Denied | No cleanup that hides evidence |

D2 architecture work itself only writes `architecture-blueprint.md` and `docs/architecture/**`.

---

## 4. Desensitization output boundaries

Every boundary below must use `SecretRedactor` or an equivalent allowlist.

| Boundary | Data that may appear | Rule |
|---|---|---|
| CLI stdout/stderr | Reports, status, errors | No secrets; endpoint sanitized |
| Application logs | Warnings, errors, vendor failures | No raw URLs with query; no keys |
| Error messages/tracebacks | Exception text | Scrub keys/tokens/userinfo/query |
| Run manifest | Config, counts, status, gate | Allowlisted config; no secrets |
| Final-state JSON | Reports, debate, decision | No keys; no raw endpoint credentials |
| Report Markdown | Reports, news links | No keys; preserve source labels |
| Report HTML | Rendered report | Existing CSP/no-script/no-image posture; escape external text |
| Memory log | Final decision, rating, provenance | Final record only; no raw proposal as final; no secrets |
| Preferences | Provider, models, backend URL | Remove userinfo/query/fragment |
| Run evidence journal | Query/status/metrics | No secrets; endpoint sanitized |
| Checkpoint SQLite | Graph state | No keys; treat as sensitive local state |
| Publish staging/manifest | Artifact hashes/paths | No secrets; no raw env |
| Telemetry/monitoring | Counts/status/latency | No prompts, no secrets |
| Coding-agent transcripts | Commands, file edits | Separate from app runtime; redact secrets if exported |

Rules:

- endpoint record = scheme + host + path;
- remove userinfo, query, and fragment;
- never record full environment variables;
- never record API keys, tokens, passwords, or secret-like values;
- prefer hashes/digests and allowlisted metadata over raw values;
- secret scanning is a planned test, not a completed result.

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
| Can publish artifacts? | No; publisher only | No; only via code changes after approval |
| Can approve D1/D2? | No | No; humans only |

---

## 6. Status

- Runtime permission enforcement: **design only**.
- Coding-agent permission enforcement: **design only**.
- Permission tests: **not started**.
- D2 coding agents currently allowed to write only `architecture-blueprint.md` and `docs/architecture/**`.
- No application code changed.
