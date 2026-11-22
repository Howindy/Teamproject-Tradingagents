# Permission Path Changes for Human Application

- Status: Historical proposed human-maintained changes, not a current edit request. No permission control was edited by this task.
- Historical reference only: the old `TradingAgents/` paths and line numbers below describe a prior permission-file state. They are retained for traceability and must not be reapplied merely because a line number or JSONC syntax appears valid. File presence or valid syntax is not proof of effective enforcement.
- No permission migration was applied by this documentation task, and no current permission is changed.
- Files requiring human application:
  - `.opencode/permissions.jsonc`
  - `docs/architecture/permission-model.md`
- Do not modify `.opencode/rules.md`.
- Preserve the existing permission levels. Do not grant blanket write access to
  `src/**` or `test/**`.

## 1. `.opencode/permissions.jsonc`

The file uses absolute project paths. Replace only the listed rules; keep the
same role profile, action and permission value. Line numbers are historical and
may not match the current file; treat them as descriptive references only. This
migration must not be re-applied from this document.

### Plan read

| Current line | Old path | New path | Keep |
|---|---|---|---|
| 104 | `TradingAgents/tradingagents/*` | `src/tradingagents/*` | `allow` |
| 105 | `TradingAgents/cli/*` | `src/cli/*` | `allow` |
| 106 | `TradingAgents/tests/*` | `test/*` | `allow` |
| 107 | `TradingAgents/pyproject.toml` | `pyproject.toml` | `allow` |
| 108 | `TradingAgents/requirements.txt` | `requirements.txt` | `allow` |

### Architecture read

| Current line | Old path | New path | Keep |
|---|---|---|---|
| 152 | `TradingAgents/tradingagents/*` | `src/tradingagents/*` | `allow` |
| 153 | `TradingAgents/cli/*` | `src/cli/*` | `allow` |
| 154 | `TradingAgents/tests/*` | `test/*` | `allow` |
| 155 | `TradingAgents/pyproject.toml` | `pyproject.toml` | `allow` |
| 156 | `TradingAgents/requirements.txt` | `requirements.txt` | `allow` |
| 165 | `TradingAgents/.github/*` | `.github/*` | `allow` |

### Architecture edit

| Current line | Old path | New path | Keep |
|---|---|---|---|
| 197 | `TradingAgents/.github/*` | `.github/*` | `deny` |

### Implementation read

| Current line | Old path | New path | Keep |
|---|---|---|---|
| 223 | `TradingAgents/tradingagents/*` | `src/tradingagents/*` | `allow` |
| 224 | `TradingAgents/cli/*` | `src/cli/*` | `allow` |
| 225 | `TradingAgents/tests/*` | `test/*` | `allow` |
| 226 | `TradingAgents/pyproject.toml` | `pyproject.toml` | `allow` |
| 227 | `TradingAgents/requirements.txt` | `requirements.txt` | `allow` |
| 235 | `TradingAgents/main.py` | Remove entry | Deleted file |
| 236 | `TradingAgents/assets/*` | Remove entry | Deleted root assets |
| 237 | `TradingAgents/cli/static/*` | `src/cli/static/*` | `allow` |

### Implementation edit

| Current line | Old path | New path | Keep |
|---|---|---|---|
| 250 | `TradingAgents/tradingagents/*` | `src/tradingagents/*` | `ask` |
| 251 | `TradingAgents/cli/*` | `src/cli/*` | `ask` |
| 252 | `TradingAgents/main.py` | Remove entry | Deleted file |
| 253 | `TradingAgents/assets/*` | Remove entry | Deleted root assets |
| 254 | `TradingAgents/tests/*` | `test/*` | `ask` |
| 272 | `TradingAgents/.github/*` | `.github/*` | `deny` |

### Verification read

| Current line | Old path | New path | Keep |
|---|---|---|---|
| 298 | `TradingAgents/tradingagents/*` | `src/tradingagents/*` | `allow` |
| 299 | `TradingAgents/cli/*` | `src/cli/*` | `allow` |
| 300 | `TradingAgents/tests/*` | `test/*` | `allow` |
| 301 | `TradingAgents/pyproject.toml` | `pyproject.toml` | `allow` |
| 302 | `TradingAgents/requirements.txt` | `requirements.txt` | `allow` |
| 310 | `TradingAgents/main.py` | Remove entry | Deleted file |
| 311 | `TradingAgents/assets/*` | Remove entry | Deleted root assets |
| 312 | `TradingAgents/cli/static/*` | `src/cli/static/*` | `allow` |
| 313 | `TradingAgents/.github/*` | `.github/*` | `allow` |

### Verification edit

| Current line | Old path | New path | Keep |
|---|---|---|---|
| 326 | `TradingAgents/tests/*` | `test/*` | `ask` |
| 344 | `TradingAgents/.github/*` | `.github/*` | `deny` |

### Resulting path coverage

- `src/tradingagents/**` remains read-only for Plan/Architecture and
  read/write-ask for Implementation only within exact approved files.
- `src/cli/**` follows the same rule; `src/cli/static/**` remains read-only
  except where the broader approved `src/cli/*` task scope already applies.
- `test/**` is read-only for Plan/Architecture, writable only under approved
  Implementation/Verification tasks, with Verification test edits using `ask`.
- Root `pyproject.toml` and `requirements.txt` remain read-only.
- Root `.github/**` remains read-only for Architecture/Verification and denied
  for edit.
- `main.py` and root `assets/**` permissions are removed because those paths
  were deleted.

This documentation task did not apply the migration and does not claim any
permission is currently in effect. If a human ever re-checks the historical
migration, verify the effective merged policy and that the old paths are gone.
File presence or JSONC validity is not proof of enforcement.

## 2. `docs/architecture/permission-model.md`

This human-maintained document still contains migration-era paths and stale
file-presence statements. The corrections below are a historical reference, not
a current edit request. Apply them only under a separate authorized task and
without changing role authority or write boundaries.

### Path replacements

| Current location | Old text/path | New text/path |
|---|---|---|
| Role tables, Plan read | `TradingAgents/tradingagents/**` | `src/tradingagents/**` |
| Role tables, Plan read | `TradingAgents/cli/**` | `src/cli/**` |
| Role tables, Plan read | `TradingAgents/tests/**` | `test/offline/**`, `test/live/**` |
| Role tables, Plan read | `TradingAgents/pyproject.toml` | `pyproject.toml` |
| Role tables, Plan read | `TradingAgents/requirements.txt` | `requirements.txt` |
| Role tables, Architecture read | same source/CLI/test/config paths as Plan | new root/src/test paths |
| Role tables, Architecture `.github` | `TradingAgents/.github/**` | `.github/**` |
| Role tables, Implementation app paths | `TradingAgents/tradingagents/**`, `TradingAgents/cli/**` | `src/tradingagents/**`, `src/cli/**` |
| Role tables, Implementation deleted paths | `TradingAgents/main.py`, `TradingAgents/assets/**` | Remove; no replacement |
| Role tables, Implementation CLI resource | `TradingAgents/cli/static/**` | `src/cli/static/**` |
| Role tables, Implementation test paths | `TradingAgents/tests/**` | `test/offline/**`, `test/live/**`, `test/conftest.py` |
| Role tables, Verification app paths | `TradingAgents/tradingagents/**`, `TradingAgents/cli/**` | `src/tradingagents/**`, `src/cli/**` |
| Role tables, Verification deleted paths | `TradingAgents/main.py`, `TradingAgents/assets/**` | Remove; no replacement |
| Role tables, Verification CLI resource | `TradingAgents/cli/static/**` | `src/cli/static/**` |
| Role tables, Verification test paths | `TradingAgents/tests/**` | `test/offline/**`, `test/live/**`, `test/conftest.py` |
| Role tables, Verification `.github` | `TradingAgents/.github/**` | `.github/**` |
| Protected content table | `TradingAgents/.github/**` | `.github/**` |
| Protected content table | `TradingAgents/.github/**` nested-path sentence | `The current CI/governance path is the root ``.github/**``; the old nested path was removed by the approved layout migration.` |
| Build/dependency row | `TradingAgents/pyproject.toml`, `requirements.txt` | root `pyproject.toml`, `requirements.txt` |
| CI row | `TradingAgents/.github/workflows/ci.yml` and `release-assets.yml` | root `.github/workflows/ci.yml`; release-assets was not migrated |
| P-V03 | `TradingAgents/.github/**` | `.github/**` |

### Stale factual corrections

| Current location | Old statement | Corrected statement |
|---|---|---|
| Section 1 introduction (line 14) | Project does not contain `AGENTS.md`, `.opencode/` permissions, `.opencode/rules.md`, `.agent/rules.md`, or D3 machine-permission files | These files now exist; their presence does not prove effective enforcement |
| Protected-content table (around lines 69-71) | `.opencode/**`, `AGENTS*`, D3 files, D4 reports, review/debt/bug records do not exist | They exist or have current project paths; human-maintained write restrictions still apply |
| Enforcement table (around lines 99-101) | No `.opencode/permissions.jsonc`, no AGENTS/rules, no D3 files | They exist; explicit loading and effective enforcement remain unverified |
| Enforcement table CI row | Nested `TradingAgents/.github/workflows/ci.yml` runs install/test/lint/smoke; release-assets builds assets | Root `.github/workflows/ci.yml` contains the baseline install/test/lint/smoke jobs; release-assets was not migrated |
| Section 7 P-V03 | No role writes `TradingAgents/.github/**` | No role writes `.github/**` |

Preserve the existing distinction that coding-agent file permissions are not
the application runtime business authority. Do not convert role maxima into
blanket `src/**` or `test/**` write grants.
