# 项目全部文件只读分析

**Session ID:** ses_e390ffa8fffe7rjDa0NgzQnqi4
**Created:** 11/11/2026, 3:29:41 AM
**Updated:** 11/11/2026, 6:15:30 AM

---

## Assistant (Build · DeepSeek Flash · 3.8s)

_Thinking:_

Also update §14.3 "Protected critical section" maybe already says short. Add explicit "long prep outside lock" bullet. Search current. It has "run.lock used only short", "waiting..." good. Maybe add "lock-external prepared content revalidated". Let's add a bullet.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"- **Protected critical section**: for every protected write (risk/metric/permanent-snapshot promotion, terminal commit, ordered memory write, post-commit diagnostic), acquire the run file lock, re-read the lease owner/fencing token, compare with the caller token, perform the write, then release. The check and write are in the same critical section; a pre-check outside the write is insufficient.\",\n\"- **Protected critical section**: for every protected write (risk/metric/permanent-snapshot promotion, terminal commit, ordered memory write, post-commit diagnostic), acquire the run file lock, re-read the lease owner/fencing token and current publication state, compare with the caller token, verify lock-external prepared content still applies, perform the write, then release. The check and write are in the same critical section; a pre-check outside the write is insufficient.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 7.5s)

_Thinking:_

Need ensure runtime POL-LOCK similarly mentions staged content revalidation. Add maybe. Later.

### Step 3: Memory version formula/high water mark
Update blueprint §9.6.3, §12.4, memory design §7/§14, runtime POL-MEM, invariants INV-A-08/39, open decisions ARCH-OD-20, trace scenario T-SCEN-15, evaluation. Let's do blueprint first.

§9.6.3: change next version formula; add durable high-water mark incl failed, ledger replay/repair, commit projection. Let's replace bullets.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"\"\"- `memory/reservations.jsonl` (or an equivalent sidecar under the memory lock) is authoritative for **version allocation**, not for decision content. Each record: `{ticker, trade_date, decision_id, entry_version, owner_run_id, status: reserved|committed|failed, fencing_token, created_at, committed_at, failure_reason}`.\n- The next version is `max(committed, reserved-uncommitted) + 1` under the memory lock. A retry/recovery reuses the reservation keyed by the original `run_id` and `decision_id`.\n- Effective version remains the highest `entry_version` whose source terminal manifest is `completed` and binds the entry. A reservation without a committed manifest is not effective and is never reused as success.\n- Recovery of an uncommitted reservation uses the original `run_id`, original `entry_version`, and original recovery snapshot. The reservation is never transferred to another run.\n- A failed reservation stays `failed` and leaves a version gap. A binding conflict (same decision_id, different entry_digest, or inconsistent owner/version) is never overwritten.\"\"\",\n\"\"\"- `memory/reservations.jsonl` (or an equivalent sidecar under the memory lock) is an append-only allocation history authoritative for **version allocation**, not for decision content. Each record: `{ticker, trade_date, decision_id, entry_version, owner_run_id, status: reserved|committed|failed, fencing_token, created_at, committed_at, failure_reason}`.\n- The allocator keeps a persistent, lock-protected **high-water mark over every historical allocation, including failed reservations**. The next version is `high_water + 1`. A failed reservation permanently occupies its version; it never leaves the high-water mark and is never reissued.\n- A retry/recovery reuses its own reservation keyed by the original `run_id` and `decision_id`; a different run must receive a higher version. Effective version remains the highest `entry_version` whose source terminal manifest is `completed` and binds the entry.\n- `committed` is a derived projection: it is true only when the terminal manifest is `completed` and read-time `INV-01` passes. A ledger commit mark is an audit/cache aid, not a second commit condition; if missing, it is rebuilt from the terminal manifest.\n- Ledger replay/repair: replay the append-only allocation records to reconstruct the high-water mark including failed versions; rebuild `committed` projections from terminal manifests. Do not derive allocation history solely from committed manifests (that would lose failed reservations). If the allocation history is missing or corrupt, stop new allocation, restore from a durable backup or operator-approved reconstruction, and never silently reset the watermark or reissue a failed version.\n- Recovery of an uncommitted reservation uses the original `run_id`, original `entry_version`, and original recovery snapshot. The reservation is never transferred to another run. A binding conflict is never overwritten.\"\"\")\ns=s.replace(\"\"\"- `MemoryReservationStore` is a persistent, lock-protected monotonic reservation ledger. The next version is greater than the highest of (a) committed versions and (b) reserved-but-uncommitted versions. Concurrent runs therefore cannot receive the same version.\n- The reservation records the ticker/date, decision_id, entry_version, owner `run_id`, and status (`reserved`, `committed`, `failed`). It is written under the memory lock and is included in the recovery snapshot.\n- Retries and recovery reuse the original reservation; they do not allocate a second version. A failed publication may leave a version gap, but it does not make the version effective and does not remove an older committed version.\"\"\",\n\"\"\"- `MemoryReservationStore` is a persistent, append-only, lock-protected allocation history with a monotonic high-water mark over **all** historical allocations, including failed reservations. The next version is `high_water + 1`; concurrent runs cannot receive the same version.\n- The reservation records the ticker/date, decision_id, entry_version, owner `run_id`, status (`reserved`, `committed`, `failed`), and fencing token. It is written under the memory lock and is included in the recovery snapshot.\n- Retries and recovery reuse their own reservation; they do not allocate a second version. A failed publication permanently occupies its version and leaves a gap; the version does not become effective and the older committed version remains effective.\n- `committed` is a derived projection from the terminal manifest plus read-time `INV-01`, not a second commit condition. The ledger's allocation history (including failed reservations) must be durable; repair replays it and must never reissue a failed version.\"\"\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.7s)

_Thinking:_

Now update memory design §7 formula and add state transitions/replay. Replace §7.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/memory-design.md')\ns=p.read_text()\ns=s.replace(\"\"\"1. `MemoryReservationStore` is a persistent, lock-protected, monotonic reservation ledger. It records ticker/date, decision_id, entry_version, owner run_id, and status (`reserved`, `committed`, `failed`).\n2. Before the recovery snapshot is written, `MemoryService` determines the plan: reuse a committed entry, reuse an uncommitted reservation owned by the same publication, or reserve a new version. A new version is greater than the highest of committed and reserved-uncommitted versions, so concurrent runs cannot receive the same version.\n3. The reserved version and the planned decision identity are recorded in the recovery snapshot, the permanent snapshot binding, and the terminal manifest.\n4. Retries and recovery reuse the original reservation; they do not allocate a second version. A failed publication may leave a version gap but no effective change and does not remove the old effective version.\n5. Effective version = the highest `entry_version` whose source terminal manifest is `completed` and binds the entry.\n6. No post-commit write to an older entry is required; superseded entries remain for audit but are excluded from lessons/statistics.\n7. Legal rotation of resolved entries removes them under policy and records `retention_status=rotated` or `not_available`, not a binding mismatch.\n8. The order is fixed: plan/reservation -> recovery snapshot containing the plan -> idempotent memory write -> permanent snapshot -> terminal candidate -> commit. Recovery follows the recorded plan.\"\"\",\n\"\"\"1. `MemoryReservationStore` is a persistent, append-only, lock-protected allocation history. It records ticker/date, decision_id, entry_version, owner run_id, status (`reserved`, `committed`, `failed`), and fencing token.\n2. The allocator keeps a persistent high-water mark over **every historical allocation, including failed reservations**. The next version is `high_water + 1`; a failed reservation permanently occupies its version and is never reissued.\n3. Before the recovery snapshot is written, `MemoryService` determines the plan: reuse a committed entry, reuse its own uncommitted reservation, or reserve a new version. A retry/recovery reuses its own reservation; a different run gets a higher version.\n4. The reserved version and the planned decision identity are recorded in the recovery snapshot, the permanent snapshot binding, and the terminal manifest.\n5. State transitions:\n   - `reserved`: before the recovery snapshot; durable and version-occupying.\n   - `failed`: publish/memory write aborts before a completed terminal manifest; the version remains occupied forever.\n   - `committed`: a derived projection, true only when the terminal manifest is `completed` and read-time `INV-01` passes. A ledger commit mark is an audit/cache aid, not a second commit condition; if missing, rebuild it from the terminal manifest.\n6. Effective version = the highest `entry_version` whose source terminal manifest is `completed` and binds the entry.\n7. Ledger replay/repair replays the append-only allocation records to reconstruct the high-water mark including failed versions, and rebuilds `committed` projections from terminal manifests. Do not derive allocation history solely from committed manifests. If the allocation history is missing/corrupt, stop new allocation, restore from a durable backup or operator-approved reconstruction, and never silently reset the watermark or reissue a failed version.\n8. No post-commit write to an older entry is required; superseded entries remain for audit but are excluded from lessons/statistics.\n9. Legal rotation of resolved entries removes them under policy and records `retention_status=rotated` or `not_available`, not a binding mismatch.\n10. The order is fixed: plan/reservation -> recovery snapshot containing the plan -> idempotent memory write -> permanent snapshot -> terminal candidate -> commit. Recovery follows the recorded plan.\"\"\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.2s)

_Thinking:_

Update memory design §14 bullet "considering committed and reserved-uncommitted" -> all historical including failed. Also add state update timing to publish/recovery. Let's edit.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/memory-design.md')\ns=p.read_text()\ns=s.replace(\"- `MemoryReservationStore` allocates versions under the same lock, considering committed and reserved-uncommitted versions. Two concurrent runs cannot receive the same version.\",\n\"- `MemoryReservationStore` allocates versions under the same lock from a persistent high-water mark over every historical allocation, including failed reservations. Two concurrent runs cannot receive the same version; a failed version is never reissued.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.8s)

_Thinking:_

Update runtime POL-MEM and runtime concrete?

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/runtime-policy-catalog.md')\ns=p.read_text()\ns=s.replace(\"- `MemoryReservationStore` is a persistent, lock-protected monotonic ledger; the next version is greater than the highest of committed and reserved-uncommitted versions; retries/recovery reuse the reservation; failure may leave a gap;\",\n\"- `MemoryReservationStore` is a persistent, append-only allocation history; the next version is `high_water + 1` over **all** historical allocations, including failed reservations; a failed version is never reissued; retries/recovery reuse their own reservation; `committed` is a derived projection from the terminal manifest, not a second commit condition;\")\ns=s.replace(\"- **Related decision**: D2-OD-06 (storage shape).\",\n\"- **Related decision**: D2-OD-06 (storage shape), ARCH-OD-20 (allocation authority/replay).\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.0s)

_Thinking:_

Update invariants INV-A-08 and INV-A-39 formula.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/invariants.md')\ns=p.read_text()\ns=s.replace(\"Version allocation is persistent and lock-protected, and the next version is greater than the highest of committed and reserved-uncommitted versions. Retries and recovery reuse the original reservation; failure may leave a gap.\",\n\"Version allocation is persistent and lock-protected, and the next version is `high_water + 1` over every historical allocation, including failed reservations. Retries and recovery reuse their own reservation; a failed version permanently occupies the high-water mark and is never reissued. `committed` is a derived projection from the terminal manifest plus read-time INV-01, not a second commit condition.\")\ns=s.replace(\"| INV-A-39 | A same-decision uncommitted entry is never reused or ownership-transferred; B waits bounded or triggers recovery under A's original run_id/reservation/snapshot; missing snapshot/failure/conflict are typed.\",\n\"| INV-A-39 | A same-decision uncommitted entry is never reused or ownership-transferred; B waits bounded or triggers recovery under A's original run_id/reservation/snapshot; missing snapshot/failure/conflict are typed. Failed reservations permanently occupy their versions.\")\ns=s.replace(\"- **Statement**: A same-decision entry with no committed terminal manifest is not reusable success. Run B never takes ownership. If A is active, B waits bounded without holding run/memory locks and returns `MEMORY_PENDING_RETRYABLE` on timeout. If A is invalid with a valid recovery snapshot, recovery runs under A's original `run_id`, original reservation, and original snapshot; ownership is never transferred. Missing snapshot -> `MEMORY_RECOVERY_UNAVAILABLE`; recovery failure -> `MEMORY_RECOVERY_FAILED`; binding conflict -> `MEMORY_CONFLICT`. B may reuse A only after A commits and validates, through `reused_decision_ref`.\",\n\"- **Statement**: A same-decision entry with no committed terminal manifest is not reusable success. Run B never takes ownership. If A is active, B waits bounded without holding run/memory locks and returns `MEMORY_PENDING_RETRYABLE` on timeout. If A is invalid with a valid recovery snapshot, recovery runs under A's original `run_id`, original reservation, and original snapshot; ownership is never transferred. Missing snapshot -> `MEMORY_RECOVERY_UNAVAILABLE`; recovery failure -> `MEMORY_RECOVERY_FAILED`; binding conflict -> `MEMORY_CONFLICT`. B may reuse A only after A commits and validates, through `reused_decision_ref`. A failed reservation permanently occupies its version; a retry/recovery of A reuses it, while any new run receives a higher version.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.4s)

_Thinking:_

Check the INV-A-39 replacement worked; likely. Now open decisions ARCH-OD-20 formula.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/open-decisions.md')\ns=p.read_text()\ns=s.replace(\"The next version is `max(committed, reserved-uncommitted) + 1`; retries/recovery reuse the reservation; recovery uses the original run_id/version/snapshot; failure leaves a gap; uncommitted reservations are never effective.\",\n\"The next version is `high_water + 1` over every historical allocation, including failed reservations; a failed version is never reissued; retries/recovery reuse their own reservation; recovery uses the original run_id/version/snapshot; `committed` is a derived projection from the terminal manifest, not a second commit condition. Repair replays the append-only allocation history and never resets the watermark or reissues failed versions.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 10.3s)

_Thinking:_

### Step 4: Hash DAG
Fix §9.6.1 `publication_ref` and binding description. Add a new subsection §9.6.5 "Digest and hash DAG" with table. Need ensure no cycle.

Replace:
- `binding.json # artifact_binding + record/manifest hashes` -> `binding.json # artifact_binding + record_hash; no terminal manifest hash`
- `publication_ref = ... record_hash, terminal_manifest_hash` -> remove terminal_manifest_hash; add `files` incl binding.json hash, record.json hash, etc.
- Add §9.6.5 after 9.6.4 with table:
  - `record_hash`: canonical FinalizedRunRecord projection excluding run-level timestamps, paths, cache counters, manifest/recovery fields.
  - `binding.json` digest: `artifact_binding` fields + record_hash; excludes terminal manifest hash, own file hash, recovery digest.
  - `section_manifest` digests: section files + complete report; excludes terminal manifest.
  - `metric_evidence_bundle` digests: facts/formula/block; excludes terminal manifest.
  - `recovery_snapshot` digest: self-contained inputs + formal decision/binding + memory plan; excludes final terminal manifest hash (candidate identity only).
  - `terminal_manifest`: includes `publication_ref.files` hashes (including binding.json), formal decision, security, section manifest, metric bundle, memory binding, `recovery_snapshot_summary` audit-only; excludes its own hash and excludes commit_evidence hash.
  - `commit_evidence.json` (optional): terminal manifest hash + read-time validation result; outside permanent hashed set; audit-only, not commit authority; never hashed by terminal manifest.
  - Computation order: record_hash -> binding.json -> section manifest/report -> final-state/risk/metrics/memory binding -> recovery snapshot -> terminal manifest -> external manifest hash/read token -> optional commit_evidence.
  - No file hashed by terminal manifest contains terminal manifest hash. binding.json never contains terminal manifest hash. Terminal manifest never hashes itself. Recovery snapshot never contains final terminal manifest hash if terminal manifest includes recovery digest; it may contain candidate identity (run_id, decision_id, record_hash, reservation).
- Update §12.5 step 9 "hashes of permanent snapshot and recovery snapshot" to "publication_ref hashes of permanent files and a `recovery_snapshot_summary` audit-only; no terminal manifest hash inside binding". Step 10 "INV-01 against candidate and every referenced file" split scopes.
- Update INV-01? Add new invariant INV-A-40 "Acyclic hash DAG". Add to inventory/verification summary.
- Runtime POL-PUB/POL-SNAP mention.
- ADR 002 mention.
- Open decisions ARCH-OD-23 update with DAG.
- Trace T-ARCH-39.

Let's edit.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"    binding.json                     # artifact_binding + record/manifest hashes\", \"    binding.json                     # artifact_binding + record_hash; no terminal-manifest hash\")\ns=s.replace(\"- `publication_ref` = `{root: \\\"publication\\\", files: [{relative_path, sha256, hash_scope: \\\"file\\\"}], record_hash, terminal_manifest_hash}`. All paths are relative and confined.\",\n\"- `publication_ref` = `{root: \\\"publication\\\", files: [{relative_path, sha256, hash_scope: \\\"file\\\"}], record_hash}`; it contains no terminal-manifest hash. All paths are relative and confined.\")\ns=s.replace(\"\"\"- The existing `get_income_statement`, `get_balance_sheet`, and `get_cashflow` tools use the same query path, run cache, counters, and provenance. `FinancialFactService` performs period/fact identity normalization; the adapter does not decide metric semantics.\n\n---\n\n## 10. Entry points and adaptation\"\"\",\n\"\"\"- The existing `get_income_statement`, `get_balance_sheet`, and `get_cashflow` tools use the same query path, run cache, counters, and provenance. `FinancialFactService` performs period/fact identity normalization; the adapter does not decide metric semantics.\n\n#### 9.6.5 Digest and hash DAG\n\nThe permanent artifacts form a directed acyclic hash graph. A file that is hashed by the terminal manifest must not contain the terminal manifest hash.\n\n| Artifact | Digest covers | Explicitly excludes | Order |\n|---|---|---|---|\n| `record.json` | Canonical `FinalizedRunRecord` content and `artifact_binding` fields | Run-level generated/evaluated/finished timestamps, local paths, cache counters, terminal-manifest hash, recovery-snapshot hash | 1 |\n| `binding.json` | `artifact_binding` fields plus `record_hash` | Terminal-manifest hash, its own file hash, recovery-snapshot digest, commit-evidence hash | 2 |\n| `report/section_manifest.json` | Section paths, fields, byte sizes, SHA-256, complete-report digest | Terminal-manifest hash, binding file hash, recovery digest | 3 |\n| `final_state.json`, `risk/*`, `metrics/*`, `memory/entry_binding.json` | Their own canonical content and referenced evidence digests | Terminal-manifest hash, binding file hash, recovery digest | 3 |\n| `recovery/recovery_snapshot.json` | Self-contained inputs, formal decision/binding, memory plan/reservation, versions | Final terminal-manifest hash; it may carry terminal-candidate identity (`run_id`, `decision_id`, `record_hash`, reservation) | 4 |\n| terminal `run_manifest.json` | `publication_ref.files` hashes (including `binding.json`), formal decision, security scans, section manifest, metric bundle, memory binding, and `recovery_snapshot_summary` (audit-only) | Its own hash; any file that contains its hash; optional commit-evidence hash | 5 |\n| `diagnostics/commit_evidence.json` (optional) | Terminal-manifest hash and read-time validation result | Never hashed by the terminal manifest; never a commit condition | 6 (after commit) |\n\n- `binding.json` never stores a terminal-manifest hash or a full terminal-manifest file hash.\n- The terminal manifest never hashes itself. Readers compute its hash from the manifest bytes and use it as a read-time token.\n- If an audit summary of the terminal manifest is needed, use `diagnostics/commit_evidence.json`; it is outside the permanent hashed set and is not a second commit authority.\n- A `recovery_snapshot_summary` inside the terminal manifest may record status/digest/created-at as audit information. It does not make `recovery/` a required verification dependency.\n- Computation order is fixed as above; a later artifact may hash an earlier one, never the reverse.\n\n---\n\n## 10. Entry points and adaptation\"\"\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.0s)

_Thinking:_

Need update §12.5 step 9/10 to align. Replace step 9 "hashes of permanent snapshot and recovery snapshot" with publication_ref and audit summary. Step 10 split scopes. Let's edit.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"9. Build the terminal manifest candidate with binding, formal decision, security scans, section manifest, metric bundle, risk evidence, memory binding, and hashes of the permanent snapshot and recovery snapshot.\\n10. Run `INV-01` against the candidate and every referenced file; the on-disk manifest is still the running manifest.\",\n\"9. Build the terminal manifest candidate with binding, formal decision, security scans, section manifest, metric bundle, risk evidence, memory binding, and `publication_ref` hashes. If desired, include a `recovery_snapshot_summary` (status/digest/created-at) as audit-only; no terminal-manifest hash is written into `binding.json` or any file hashed by the manifest.\\n10. Validate the permanent candidate with `INV-01`; separately verify the self-contained recovery snapshot for recoverability. The recovery snapshot is not part of the formal `INV-01`/history/export scope. The on-disk manifest is still the running manifest.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.8s)

_Thinking:_

Add invariant INV-A-40 hash DAG. Also maybe update INV-A-37? Add new row and detailed section, verification summary.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/invariants.md')\ns=p.read_text()\ns=s.replace(\"| INV-A-39 | A same-decision uncommitted entry is never reused or ownership-transferred; B waits bounded or triggers recovery under A's original run_id/reservation/snapshot; missing snapshot/failure/conflict are typed. Failed reservations permanently occupy their versions.\",\n\"| INV-A-39 | A same-decision uncommitted entry is never reused or ownership-transferred; B waits bounded or triggers recovery under A's original run_id/reservation/snapshot; missing snapshot/failure/conflict are typed. Failed reservations permanently occupy their versions. | `INV-01`, `FR-06`, `INV-02` | `MemoryRecoveryCoordinator`, `MemoryService`, `RecoveryService` | Active/expired/missing-snapshot/failed/conflict tests | Retryable/unavailable/failed/conflict; no duplicate | Design only |\\n| INV-A-40 | Permanent artifacts form an acyclic hash DAG; `binding.json` never contains the terminal-manifest hash, and no file hashed by the terminal manifest contains that hash. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService` | Hash-DAG ordering/cycle tests | Reject cyclic candidate; no commit | Design only |\")\n# Add detailed section before section 4\ns=s.replace(\"\"\"---\n\n## 4. Planned verification summary\"\"\",\n\"\"\"### INV-A-40 — Acyclic permanent hash DAG\n\n- **Statement**: Permanent artifacts form a directed acyclic hash graph. `record_hash` is computed first; `binding.json` covers `artifact_binding` plus `record_hash` but excludes the terminal-manifest hash, its own file hash, the recovery digest, and commit-evidence hash. Section/final-state/risk/metric/memory files are hashed next. The recovery snapshot may carry terminal-candidate identity but not the final terminal-manifest hash. The terminal manifest covers `publication_ref` hashes (including `binding.json`) and may hold a `recovery_snapshot_summary` as audit-only; it never hashes itself. An optional `diagnostics/commit_evidence.json` may record the terminal-manifest hash after commit but is outside the permanent hashed set and is not a commit authority.\n- **Source**: `FR-02`, `INV-01`, `FR-05`.\n- **Enforcement**: `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService`.\n- **Verification**: compute in the declared order; assert no cycle and no file hashed by the terminal manifest contains its hash; assert binding has no terminal-manifest hash.\n- **Fallback**: reject cyclic candidate; do not commit; no post-commit rewrite.\n- **Status**: design only.\n\n---\n\n## 4. Planned verification summary\"\"\")\n# verification summary\ns=s.replace(\"| Uncommitted same-decision coordination | INV-A-39 |\",\"| Uncommitted same-decision coordination | INV-A-39 |\\n| Permanent hash DAG | INV-A-40 |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 6.4s)

_Thinking:_

Check inventory row insertion didn't duplicate columns. Table consistency later.

### Step 5: SEC per-fact contract
Replace §9.6.4 output contract with per-fact records including filing/subject/period/unit/currency/restatement. Also update §12.2 adapter boundary and invariants INV-A-30, ADR 002, runtime POL-FIN, open decisions ARCH-OD-19, trace T-ARCH-35.

Let's edit §9.6.4.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"\"\"- **Output** (returned by `SecEdgarAdapter`, normalized by `FinancialFactService`):\n  ```text\n  {subject_id, source: \"SEC EDGAR\",\n   filings: [{accession_no, filing_ref, form, filed_at, period_end, fiscal_year, fiscal_quarter}],\n   statements: [{statement: income|balance|cashflow, rows: [{concept, value, unit, currency, period_start, period_end, span, cumulative_duration_days, sign}]}],\n   provenance: {...}}\n  ```\n- **Errors**: `VendorUnavailableError`, `NoMarketDataError`, `VendorNotConfiguredError`, `FactAmbiguousError`, `FactUnavailableError`, mapped by `DataAccessService`; no raw vendor call outside the adapter.\n- The existing `get_income_statement`, `get_balance_sheet`, and `get_cashflow` tools use the same query path, run cache, counters, and provenance. `FinancialFactService` performs period/fact identity normalization; the adapter does not decide metric semantics.\"\"\",\n\"\"\"- **Output** (returned by `SecEdgarAdapter`, normalized by `FinancialFactService`): each fact is a self-describing record, not an unlinked row plus a separate filing list.\n  ```text\n  {subject_id, source: \"SEC EDGAR\", source_retrieved_at,\n   facts: [{\n     fact_id,\n     subject_id,                       # CIK or equivalent issuer identity\n     accession_no,                     # disclosure identifier\n     filing_ref,                       # locatable filing reference\n     filed_at,                         # disclosure time\n     form,                             # 10-K, 10-Q, ...\n     concept, value, unit, currency,\n     period_start, period_end,\n     fiscal_year, fiscal_quarter,\n     span: annual|quarter|ytd|instant,\n     cumulative_duration_days,\n     sign,\n     restates_fact_id?,                # explicit restatement/alternative lineage\n     supersedes?,\n     source_fact_ref?                  # raw SEC fact/table reference\n   }],\n   provenance: {...}}\n  ```\n- **Source-field ownership**: `subject_id`, `accession_no`, `filing_ref`, `filed_at`, `form`, `concept`, `period_*`, `fiscal_*`, `span`, `unit`, `currency`, `value`, `sign`, and any restatement/supersession link are preserved from the raw SEC filing/fact data. `FinancialFactService` may validate, canonicalize, or derive `fact_id`, `cumulative_duration_days`, and normalized comparisons, but must preserve the source linkage. If any required source field is missing, or more than one fact remains a plausible source, return `FactUnavailableError`/`FactAmbiguousError`; never infer a link from date proximity or equal value.\n- **Errors**: `VendorUnavailableError`, `NoMarketDataError`, `VendorNotConfiguredError`, `FactAmbiguousError`, `FactUnavailableError`, mapped by `DataAccessService`; no raw vendor call outside the adapter.\n- The existing `get_income_statement`, `get_balance_sheet`, and `get_cashflow` tools use the same query path, run cache, counters, and provenance. `FinancialFactService` performs period/fact identity validation/normalization; the adapter does not decide metric semantics.\"\"\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.4s)

_Thinking:_

Update §12.2 adapter boundary bullet with per-fact source contract.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"- `FinancialFactService.fetch(ticker, as_of)` issues a structured-fact query through `DataAccessService`; the adapter returns raw statements/JSON plus filing metadata; `FinancialFactService` normalizes that payload into `financial_fact`s. It never imports or calls a vendor module directly.\",\n\"- `FinancialFactService.fetch(ticker, as_of)` issues a structured-fact query through `DataAccessService`; the adapter returns per-fact records that preserve `subject_id`, `accession_no`, `filing_ref`, `filed_at`, `form`, `concept`, period/fiscal identity, `span`, `unit`, `currency`, `value`, `sign`, and restatement/supersession lineage. `FinancialFactService` validates/normalizes these records into `financial_fact`s; it never imports or calls a vendor module directly, and it never guesses a filing/fact link from date proximity or equal value.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.9s)

_Thinking:_

Update invariants INV-A-30 statement with per-fact source contract.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/invariants.md')\ns=p.read_text()\ns=s.replace(\"- **Statement**: Derived metrics use structured facts with subject, accession, filing reference, concept, period identity, fiscal position, span, filed-at, source, sign, and restatement lineage. The fact fetch, metric computation, block append, and conflict check occur after the fundamentals report exists and before research debate consumes it; final publication only persists the existing result.\",\n\"- **Statement**: Derived metrics use per-fact structured records that each carry subject, accession/disclosure identifier, filing reference, filed-at, form, concept, period identity, fiscal position, span, unit, currency, sign, and restatement/supersession lineage. Source linkage is preserved from raw SEC data or explicitly derived by normalization; missing or multiple plausible sources return unavailable/ambiguous and are never guessed from date proximity or equal value. The fact fetch, metric computation, block append, and conflict check occur after the fundamentals report exists and before research debate consumes it; final publication only persists the existing result.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.3s)

_Thinking:_

Update ADR 002 §2.3 with per-fact provenance.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/adr/002-full-scope-add-r.md')\ns=p.read_text()\ns=s.replace(\"- Facts carry subject, accession, filing reference, concept, periods, fiscal position, span, filed-at, source, sign, and restatement lineage.\",\n\"- Each fact carries subject, accession/disclosure identifier, filing reference, filed-at, form, concept, periods, fiscal position, span, unit, currency, source, sign, and restatement/supersession lineage. Missing or multiple plausible sources return unavailable/ambiguous; the normalizer never guesses a link from date proximity or equal value.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.0s)

_Thinking:_

Update runtime POL-FIN-01 with per-fact contract.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/runtime-policy-catalog.md')\ns=p.read_text()\ns=s.replace(\"- **Facts**: subject/accession/filing_ref/concept/period/fiscal position/span/cumulative duration/filed_at/source/sign/restatement lineage; CIK never substitutes for accession/filing_ref.\",\n\"- **Facts**: each fact carries subject/accession/filing_ref/filed_at/form/concept/period/fiscal position/span/cumulative duration/unit/currency/source/sign/restatement lineage; CIK never substitutes for accession/filing_ref. Source linkage is preserved from raw SEC data or explicitly derived; missing/multiple plausible sources return unavailable/ambiguous and are never guessed from date proximity or equal value.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.6s)

_Thinking:_

Update open decisions ARCH-OD-19 with per-fact contract.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/open-decisions.md')\ns=p.read_text()\ns=s.replace(\"- **Recommendation (not approved)**: after the fundamentals report exists and before Bull/Bear; a `get_structured_financial_facts`-style query through `DataAccessService` returns raw statements/JSON plus filing metadata; `FinancialFactService` normalizes it; the existing statement tools use the same adapter/cache/counters.\",\n\"- **Recommendation (not approved)**: after the fundamentals report exists and before Bull/Bear; a `get_structured_financial_facts`-style query through `DataAccessService` returns per-fact records with subject/accession/filing_ref/filed_at/form/concept/period/span/unit/currency/sign and restatement lineage; `FinancialFactService` validates/normalizes them; the existing statement tools use the same adapter/cache/counters. Missing or multiple plausible sources return unavailable/ambiguous; never guess from date proximity or equal value.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.3s)

_Thinking:_

Update trace T-ARCH-35 description with per-fact provenance.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/trace-matrix.md')\ns=p.read_text()\ns=s.replace(\"| `T-ARCH-35` | SEC structured query input/output contract; adapter boundary and normalization | not started |\",\n\"| `T-ARCH-35` | SEC structured query input/output contract; per-fact filing/subject/period/unit/currency/lineage; unavailable/ambiguous, no guessing | not started |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.8s)

_Thinking:_

### Step 6: Temporary recovery/permanent verification boundary
We already updated §12.5 step 9/10 and §12.6. Need check §11.3/§12.6 "recovery snapshot hash" wording. Search "hashes of the permanent snapshot and recovery snapshot" gone. Search "every referenced file". Also add verification scope table maybe already. §12.5 has scope bullets. Good.

Need update ADR 001/002 maybe "recovery snapshot hash" wording. Search.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"recovery snapshot hash\\|hashes of the permanent snapshot and recovery\\|every referenced file\\|verify every referenced\" architecture-blueprint.md docs/architecture || echo none; grep -rn \"recovery_snapshot_summary\" architecture-blueprint.md docs/architecture | head -20"
}
```

**Output:**
```
none
architecture-blueprint.md:461:- The terminal manifest may retain `recovery_snapshot_summary` (status, digest, created_at) as **audit information only**. It is not a verification dependency; after cleanup, `get_run`, memory binding validation, and `verified_package` MUST still work from `publication/`.
architecture-blueprint.md:529:| terminal `run_manifest.json` | `publication_ref.files` hashes (including `binding.json`), formal decision, security scans, section manifest, metric bundle, memory binding, and `recovery_snapshot_summary` (audit-only) | Its own hash; any file that contains its hash; optional commit-evidence hash | 5 |
architecture-blueprint.md:535:- A `recovery_snapshot_summary` inside the terminal manifest may record status/digest/created-at as audit information. It does not make `recovery/` a required verification dependency.
architecture-blueprint.md:909:9. Build the terminal manifest candidate with binding, formal decision, security scans, section manifest, metric bundle, risk evidence, memory binding, and `publication_ref` hashes. If desired, include a `recovery_snapshot_summary` (status/digest/created-at) as audit-only; no terminal-manifest hash is written into `binding.json` or any file hashed by the manifest.
architecture-blueprint.md:928:- If the terminal manifest retains a `recovery_snapshot_summary`, it is audit metadata only. Readers must not require the temporary recovery file or re-read it to verify the formal record.
docs/architecture/adr/002-full-scope-add-r.md:61:- After successful commit and post-commit validation, temporary `recovery/` material may be cleaned. Formal report reads, history `get_run`, memory binding validation, and `verified_package` export depend only on the permanent `publication/` snapshot; a terminal `recovery_snapshot_summary` is audit-only, not a re-read dependency. A cleanup failure after commit is a warning, not a committed-identity change.
docs/architecture/invariants.md:402:- **Statement**: Temporary recovery material may be cleaned after successful commit and post-commit validation. Formal report reads, history `get_run`, memory binding validation, and `verified_package` export depend only on the permanent publication snapshot and terminal manifest. A terminal `recovery_snapshot_summary` is audit-only; readers must not require the temporary recovery file.
docs/architecture/invariants.md:429:- **Statement**: Permanent artifacts form a directed acyclic hash graph. `record_hash` is computed first; `binding.json` covers `artifact_binding` plus `record_hash` but excludes the terminal-manifest hash, its own file hash, the recovery digest, and commit-evidence hash. Section/final-state/risk/metric/memory files are hashed next. The recovery snapshot may carry terminal-candidate identity but not the final terminal-manifest hash. The terminal manifest covers `publication_ref` hashes (including `binding.json`) and may hold a `recovery_snapshot_summary` as audit-only; it never hashes itself. An optional `diagnostics/commit_evidence.json` may record the terminal-manifest hash after commit but is outside the permanent hashed set and is not a commit authority.
docs/architecture/trace-matrix.md:308:| `T-ARCH-31` | recovery snapshot cleanup vs permanent publication read dependency; `recovery_snapshot_summary` audit-only | not started |
docs/architecture/runtime-policy-catalog.md:231:- **Cleanup**: after commit and post-commit validation, `recovery/`, claim, and staging may be cleaned. A terminal `recovery_snapshot_summary` is audit-only.
docs/architecture/memory-design.md:249:- The recovery snapshot is temporary. After successful commit and post-commit validation, `recovery/` may be cleaned; history reads, memory binding validation, and export rely on the permanent `publication/` snapshot, not the temporary file. A terminal `recovery_snapshot_summary` is audit-only.
docs/architecture/open-decisions.md:406:- **Recommendation (not approved)**: use the `publication/`, `recovery/`, `locks/`, `diagnostics/` layout in blueprint §9.6.1. Formal report/history/export/memory binding validation depend only on `publication/` + terminal manifest; `recovery/` is temporary and may be cleaned; a terminal `recovery_snapshot_summary` is audit-only.

```

---

## Assistant (Build · DeepSeek Flash · 7.3s)

_Thinking:_

Good.

### Step 7: Ledger state transitions in publish/recovery protocol
Need add to blueprint §12.5/§12.6 explicit reservation state updates and commit projection. Current §12.5 step 5 reserve; step 7 memory write; no ledger committed update. Add:
- Step 5 reserve (state reserved).
- On failure before commit, ledger append failed (version remains).
- After terminal commit + read validation, append derived commit event/projection; if ledger update fails, terminal manifest remains authority; rebuild later.
- Retry/recovery reuse reservation.
- Add in §12.6 identity bullets.

Let's edit §12.5 steps 5/7/12/13 and add a "Memory ledger integration" paragraph. Also §12.6 "Snapshot boundary and order" maybe.

Find current §12.5 steps. We'll patch.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"5. Determine the memory plan and reserve the required `entry_version` under the memory lock.\",\n\"5. Determine the memory plan and reserve the required `entry_version` under the memory lock; append a `reserved` allocation record.\")\ns=s.replace(\"\"\"12. Post-commit read validation under the same ownership rules. If it succeeds, history becomes visible. If it fails, **do not overwrite the committed terminal manifest**: keep it as immutable commit evidence, record an independent corruption diagnostic, reject the record as success, and exclude it from history/export until repaired.\n13. Clean temporary recovery material only after successful post-commit validation; a cleanup failure is a warning and does not change the committed identity.\n14. History visibility begins only after steps 11-12 succeed. The permanent snapshot is never created after cleanup.\"\"\",\n\"\"\"12. Post-commit read validation under the same ownership rules. If it succeeds, history becomes visible; append/refresh the ledger's `committed` projection (audit/cache only, not a commit condition). If it fails, **do not overwrite the committed terminal manifest**: keep it as immutable commit evidence, record an independent corruption diagnostic, reject the record as success, and exclude it from history/export until repaired.\n13. Clean temporary recovery material only after successful post-commit validation; a cleanup failure is a warning and does not change the committed identity.\n14. History visibility begins only after steps 11-12 succeed. The permanent snapshot is never created after cleanup.\n\n**Memory ledger integration**\n\n- Before the recovery snapshot: append `reserved` with the allocated version; this is durable allocation history.\n- On abort before a completed terminal manifest: append `failed`; the version remains permanently occupied and is never reissued.\n- On retry/recovery: reuse the same reservation; do not allocate a new version.\n- After terminal commit plus read-time `INV-01`: the `committed` projection may be appended, but it is derived/rebuildable. If the ledger update fails, the terminal manifest remains authoritative and the projection is repaired from it.\n- A ledger `committed` entry without a completed terminal manifest is not a commit. The ledger never becomes a second commit condition.\"\"\")\ns=s.replace(\"\"\"- Before claiming/publishing, recovery inspects the existing terminal manifest and content identity.\n- A legal completed publication with matching identity is already complete: do not republish and do not repeat memory; snapshot residue alone must not trigger publication.\n- Same `run_id` with the same immutable content is a no-op; different content is `RUN_ID_CONFLICT`.\"\"\",\n\"\"\"- Before claiming/publishing, recovery inspects the existing terminal manifest and content identity.\n- A legal completed publication with matching identity is already complete: do not republish and do not repeat memory; snapshot residue alone must not trigger publication. The ledger's `committed` projection may be rebuilt from that manifest.\n- Same `run_id` with the same immutable content is a no-op; different content is `RUN_ID_CONFLICT`.\n- Recovery reuses its recorded `reserved` allocation. If the original publication failed, the ledger keeps a `failed` allocation; recovery does not allocate a new version. If recovery fails again, the version remains occupied.\"\"\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.3s)

_Thinking:_

Need update §9.6.3 state transitions with commit timing. It has bullet "committed is derived projection...". Add explicit timing maybe enough. Let's add a line:
- reserved append before snapshot; failed append on abort; committed projection after terminal commit+INV-01; ledger update failure does not block commit; repair from manifest.
We already have a bullet but not timing. Add.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"- `committed` is a derived projection: it is true only when the terminal manifest is `completed` and read-time `INV-01` passes. A ledger commit mark is an audit/cache aid, not a second commit condition; if missing, it is rebuilt from the terminal manifest.\",\n\"- `committed` is a derived projection: it is true only when the terminal manifest is `completed` and read-time `INV-01` passes. A ledger commit mark is an audit/cache aid, not a second commit condition; if missing or if the ledger write fails after commit, it is rebuilt from the terminal manifest. Append `reserved` before the recovery snapshot, `failed` on abort before a completed manifest, and the `committed` projection only after commit plus read verification.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.9s)

_Thinking:_

Update memory design §8 retry with state update. Add bullet in §8.2.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/memory-design.md')\ns=p.read_text()\ns=s.replace(\"- after memory succeeds and INV-01 passes on the candidate, the publisher commits the terminal manifest;\\n- if memory remains unavailable, operator action is required.\",\n\"- if memory remains unavailable, the ledger records `failed` (the version stays occupied) and operator action is required;\\n- after memory succeeds and INV-01 passes on the candidate, the publisher commits the terminal manifest; the ledger `committed` projection may be appended after commit+read verification, but it is derived and rebuildable.\\n- if the process is interrupted between terminal commit and ledger projection update, the terminal manifest remains authoritative; repair rebuilds `committed` without changing the allocation high-water mark or reissuing a failed version.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.6s)

_Thinking:_

Check the replacement order: it replaced "after memory succeeds..." line and inserted new. Good.

Update runtime POL-PUB/POL-MEM with ledger timing.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/runtime-policy-catalog.md')\ns=p.read_text()\ns=s.replace(\"  - memory remains pending/unreadable until commit;\",\n\"  - memory remains pending/unreadable until commit; the allocation ledger appends `reserved` before the recovery snapshot, `failed` on abort before a completed manifest, and a rebuildable `committed` projection only after commit plus read verification; ledger write failure after commit does not block the manifest authority;\")\ns=s.replace(\"  - memory-disabled runs require no memory artifact;\",\n\"  - memory-disabled runs require no memory artifact; the ledger's `committed` projection is derived from terminal manifests, not a second commit condition;\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.7s)

_Thinking:_

Update invariants INV-A-08 maybe add ledger state timing; INV-A-39 maybe. Add to INV-A-08 statement.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/invariants.md')\ns=p.read_text()\ns=s.replace(\"Version allocation is persistent and lock-protected, and the next version is `high_water + 1` over every historical allocation, including failed reservations. Retries and recovery reuse their own reservation; a failed version permanently occupies the high-water mark and is never reissued. `committed` is a derived projection from the terminal manifest plus read-time INV-01, not a second commit condition.\",\n\"Version allocation is persistent and lock-protected, and the next version is `high_water + 1` over every historical allocation, including failed reservations. Retries and recovery reuse their own reservation; a failed version permanently occupies the high-water mark and is never reissued. `reserved` is appended before the recovery snapshot, `failed` on abort before a completed manifest, and `committed` is a derived projection appended only after terminal commit plus read-time INV-01; a missing/failed projection write is rebuilt from the terminal manifest and is not a second commit condition.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 8.9s)

_Thinking:_

Need add test scenario "highest version failed, new run allocates, old run retries" T-SCEN-15 and "interruption between commit and ledger update" T-SCEN-16. Add to blueprint §13.2, trace inventory, evaluation. Also T-ARCH-38 ledger watermark, T-ARCH-39 hash DAG, T-ARCH-40 ledger commit projection/repair. Let's add.

Blueprint §13.2 add rows before Portfolio Manager? Add after T-SCEN-14:
- Failed version/new allocation/old retry.
- Interruption between commit and ledger update.
Also update §19 reference 01..16.
Trace T-SCEN-15/16, T-ARCH-38/39/40, counts 16/40.
Evaluation scenario row 01..16 and measurement rows.

Let's edit.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"| Portfolio Manager proposal source | PM consumes full reports/plans/risk debate/memory; model_proposal source=portfolio_manager; Trader/risk-debater output never final proposal | `T-SCEN-14`: normal PM output, missing/parsing failure, and attempted Trader/risk-debater promotion; assert source fields and gate input |\",\n\"\"\"| Portfolio Manager proposal source | PM consumes full reports/plans/risk debate/memory; model_proposal source=portfolio_manager; Trader/risk-debater output never final proposal | `T-SCEN-14`: normal PM output, missing/parsing failure, and attempted Trader/risk-debater promotion; assert source fields and gate input |\n| Failed version, new run, old retry | Highest version fails and remains in the high-water mark; a new run gets a higher version; the old run retries its own reservation and never reuses the new version | `T-SCEN-15`: fail version N, allocate N+1 to a new run, retry the old run; assert no version reuse, no duplicate entry, effective versions correct |\n| Commit/ledger-update interruption | Terminal manifest commit succeeds but ledger `committed` projection is missing/fails; manifest remains authority; repair rebuilds projection without losing failed allocations or reissuing versions | `T-SCEN-16`: crash between commit and ledger update; assert history reads, ledger repair, high-water preservation, no second commit condition |\"\"\")\ns=s.replace(\"The end-to-end scenario tests `T-SCEN-01`..`T-SCEN-14` in §13.2 cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, and Portfolio Manager proposal sourcing.\",\n\"The end-to-end scenario tests `T-SCEN-01`..`T-SCEN-16` in §13.2 cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, and commit/ledger-update interruption.\")\np.write_text(s)\np=Path('docs/architecture/trace-matrix.md')\ns=p.read_text()\ns=s.replace(\"| `T-SCEN-14` | Portfolio Manager proposal source; Trader/risk-debater output not promoted | not started |\",\n\"\"\"| `T-SCEN-14` | Portfolio Manager proposal source; Trader/risk-debater output not promoted | not started |\n| `T-SCEN-15` | Highest version failed, new run allocates, old run retries own reservation; no version reuse | not started |\n| `T-SCEN-16` | Commit/ledger-update interruption; manifest authority; ledger projection repair; failed allocations preserved | not started |\"\"\")\ns=s.replace(\"Additional scenario tests: `T-SCEN-01`..`T-SCEN-14` (14 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-37`, not started.\",\n\"Additional scenario tests: `T-SCEN-01`..`T-SCEN-16` (16 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-40`, not started.\")\ns=s.replace(\"| `T-ARCH-37` | lock/lease record state transitions and run/memory lock order | not started |\",\n\"\"\"| `T-ARCH-37` | lock/lease record state transitions and run/memory lock order | not started |\n| `T-ARCH-38` | memory allocation high-water mark includes failed reservations; new/retry version behavior | not started |\n| `T-ARCH-39` | permanent hash DAG: binding no terminal hash, no cycles, declared computation order | not started |\n| `T-ARCH-40` | ledger reserved/failed/committed timing and commit-projection repair | not started |\"\"\")\ns=s.replace(\"- The scenario tests `T-SCEN-01`..`T-SCEN-14` cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, and Portfolio Manager proposal sourcing. They are planned, not executed.\",\n\"- The scenario tests `T-SCEN-01`..`T-SCEN-16` cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, and commit/ledger-update interruption. They are planned, not executed.\")\np.write_text(s)\np=Path('docs/architecture/evaluation-table.md')\ns=p.read_text()\ns=s.replace(\"| Scenario matrix T-SCEN-01..14 | Normal, business block, system error, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export, cleanup-after-read, brief failure, uncommitted-memory coordination, old-process lock/lease, PM proposal source | not started |\",\n\"| Scenario matrix T-SCEN-01..16 | Normal, business block, system error, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export, cleanup-after-read, brief failure, uncommitted-memory coordination, old-process lock/lease, PM proposal source, failed-version retry, commit/ledger-update interruption | not started |\")\ns=s.replace(\"| Memory reservation | Concurrent reservations, committed vs reserved-uncommitted, retry reuse, failure gap | not started |\",\n\"| Memory reservation | Concurrent reservations, high-water including failed, retry reuse, failed-version gap, new-run higher version | not started |\\n| Ledger commit projection | Commit/ledger interruption, rebuild from manifest, failed allocation preservation | not started |\\n| Permanent hash DAG | binding no terminal hash; no cycles; declared order | not started |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.0s)

_Thinking:_

Need add evaluation scenario row maybe replace didn't match because actual row was 01..16? Let's check.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -n \"Scenario matrix\\|Memory reservation\\|Ledger commit\\|Permanent hash\" docs/architecture/evaluation-table.md; grep -n \"T-SCEN-1[5-6]\\|T-ARCH-3[8-9]\\|T-ARCH-40\" docs/architecture/trace-matrix.md"
}
```

**Output:**
```
252:| Scenario matrix T-SCEN-01..16 | Normal, business block, system error, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export, cleanup-after-read, brief failure, uncommitted-memory coordination, old-process lock/lease, PM proposal source, failed-version retry, commit/ledger-update interruption | not started |
254:| Memory reservation | Concurrent reservations, high-water including failed, retry reuse, failed-version gap, new-run higher version | not started |
255:| Ledger commit projection | Commit/ledger interruption, rebuild from manifest, failed allocation preservation | not started |
256:| Permanent hash DAG | binding no terminal hash; no cycles; declared order | not started |
253:Additional scenario tests: `T-SCEN-01`..`T-SCEN-16` (16 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-40`, not started.
273:| `T-SCEN-15` | Highest version failed, new run allocates, old run retries own reservation; no version reuse | not started |
274:| `T-SCEN-16` | Commit/ledger-update interruption; manifest authority; ledger projection repair; failed allocations preserved | not started |
317:| `T-ARCH-38` | memory allocation high-water mark includes failed reservations; new/retry version behavior | not started |
318:| `T-ARCH-39` | permanent hash DAG: binding no terminal hash, no cycles, declared computation order | not started |
319:| `T-ARCH-40` | ledger reserved/failed/committed timing and commit-projection repair | not started |
354:- The scenario tests `T-SCEN-01`..`T-SCEN-16` cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, and commit/ledger-update interruption. They are planned, not executed.

```

---

## Assistant (Build · DeepSeek Flash · 3.7s)

_Thinking:_

Good.

Now update trace matrix FR-07-AC3 maybe per-fact source. Also FR-07-AC7. Let's add per-fact provenance wording.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/trace-matrix.md')\ns=p.read_text()\ns=s.replace(\"| `FR-07-AC3` | `FinancialFactService` | `T-FR07-03` near-date/accession/restatement/as-of | `MON-FR07-03` silent merge/look-ahead | design only; not started |\",\n\"| `FR-07-AC3` | `FinancialFactService`, `SecEdgarAdapter` | `T-FR07-03` per-fact subject/accession/filing_ref/filed_at; near-date/restatement/as-of; unavailable/ambiguous, no guessing | `MON-FR07-03` silent merge/look-ahead/guessed link | design only; not started |\")\ns=s.replace(\"| `FR-07-AC7` | `FinancialFactService`, `DataAccessService` | `T-FR07-07` unified data access/counters | `MON-FR07-07` direct vendor call | design only; not started |\",\n\"| `FR-07-AC7` | `FinancialFactService`, `DataAccessService`, `SecEdgarAdapter` | `T-FR07-07` unified data access/counters/per-fact provenance | `MON-FR07-07` direct vendor call/lost provenance | design only; not started |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.0s)

_Thinking:_

Now update runtime POL-FIN with per-fact contract maybe already. Good.

Need update `docs/architecture/adr/002` §2.3 per-fact; done.

Need update `docs/architecture/open-decisions.md` ARCH-OD-19 per-fact; done.

Now update `docs/architecture/memory-design.md` §7 with state transitions and high water; done. But need update §8.1 retry ledger failure and §8.2 commit projection; done. Need add §7 note that `committed` projection not second authority; done.

Need update `docs/architecture/invariants.md` INV-A-40 hash DAG and inventory; done. Need ensure INV-A-40 detailed section inserted before §4 and inventory row. Check table consistency later.

Need update `docs/architecture/runtime-policy-catalog.md` POL-SNAP/POL-PUB with hash DAG? Add mention. Also POL-PUB step currently "permanent-snapshot files ... authoritative only after commit" but not hash DAG. Add bullet "binding.json contains no terminal-manifest hash; terminal manifest hashes permanent files; no cycle." Let's edit.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/runtime-policy-catalog.md')\ns=p.read_text()\ns=s.replace(\"  - permanent-snapshot files are written/validated before commit and are authoritative only after commit; the permanent snapshot is never created after cleanup;\",\n\"  - permanent-snapshot files are written/validated before commit and are authoritative only after commit; the permanent snapshot is never created after cleanup;\\n  - permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; an optional `diagnostics/commit_evidence.json` is audit-only;\")\ns=s.replace(\"- **Dependency**: report, history, export, and memory binding validation depend on `publication/` and the terminal manifest. They do not depend on `recovery/`.\",\n\"- **Dependency**: report, history, export, and memory binding validation depend on `publication/` and the terminal manifest. They do not depend on `recovery/`. The hash DAG is acyclic: `binding.json` has no terminal-manifest hash; the terminal manifest hashes permanent files; no hashed file contains the manifest hash.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.1s)

_Thinking:_

Now update ADR 002 §2.2 with hash DAG/cleanup maybe. Add bullet.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/adr/002-full-scope-add-r.md')\ns=p.read_text()\ns=s.replace(\"- After successful commit and post-commit validation, temporary `recovery/` material may be cleaned. Formal report reads, history `get_run`, memory binding validation, and `verified_package` export depend only on the permanent `publication/` snapshot; a terminal `recovery_snapshot_summary` is audit-only, not a re-read dependency. A cleanup failure after commit is a warning, not a committed-identity change.\",\n\"- After successful commit and post-commit validation, temporary `recovery/` material may be cleaned. Formal report reads, history `get_run`, memory binding validation, and `verified_package` export depend only on the permanent `publication/` snapshot; a terminal `recovery_snapshot_summary` is audit-only, not a re-read dependency. A cleanup failure after commit is a warning, not a committed-identity change.\\n- Permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; optional `diagnostics/commit_evidence.json` is audit-only.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.6s)

_Thinking:_

Update ADR 001 maybe hash DAG? Add bullet maybe.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/adr/001-run-governance.md')\ns=p.read_text()\ns=s.replace(\"- `PublicationSnapshotStore` holds permanent committed records. `RecoverySnapshotStore` holds temporary pending envelopes. History and export read the permanent snapshot and revalidate on every read.\",\n\"- `PublicationSnapshotStore` holds permanent committed records. `RecoverySnapshotStore` holds temporary pending envelopes. History and export read the permanent snapshot and revalidate on every read. Permanent artifacts form an acyclic hash DAG: `binding.json` has no terminal-manifest hash; the manifest hashes permanent files; no hashed file contains the manifest hash.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.8s)

_Thinking:_

Update open decisions ARCH-OD-23 with hash DAG and binding exclusion.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/open-decisions.md')\ns=p.read_text()\ns=s.replace(\"- **Recommendation (not approved)**: use the `publication/`, `recovery/`, `locks/`, `diagnostics/` layout in blueprint §9.6.1. Formal report/history/export/memory binding validation depend only on `publication/` + terminal manifest; `recovery/` is temporary and may be cleaned; a terminal `recovery_snapshot_summary` is audit-only.\",\n\"- **Recommendation (not approved)**: use the `publication/`, `recovery/`, `locks/`, `diagnostics/` layout in blueprint §9.6.1. Formal report/history/export/memory binding validation depend only on `publication/` + terminal manifest; `recovery/` is temporary and may be cleaned; a terminal `recovery_snapshot_summary` is audit-only. The hash DAG is acyclic: `binding.json` contains no terminal-manifest hash; the manifest hashes permanent files including binding; no hashed file contains the manifest hash; optional `commit_evidence.json` is audit-only.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.3s)

_Thinking:_

Now update permission-model maybe no hash. Fine.

Need update memory design open decisions ARCH-OD-20 formula maybe already; check.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -n \"high_water\\|high-water\\|reserved-uncommitted\" architecture-blueprint.md docs/architecture/memory-design.md docs/architecture/runtime-policy-catalog.md docs/architecture/invariants.md docs/architecture/open-decisions.md | head -60"
}
```

**Output:**
```
architecture-blueprint.md:312:| `MemoryReservationStore` | `run/memory_reservation.py` | Persistent, lock-protected monotonic entry-version reservation over committed and reserved-uncommitted versions; reuse on retry/recovery; failure gaps | ticker/date, decision_id, owner/lease | `MemoryReservation` | `ReservationError`, `ReservationConflict` | Reservation ledger | MemoryLock, Canonicalizer | 1/2 |
architecture-blueprint.md:407:| Memory version reservation | `MemoryReservationStore` | Persistent, lock-protected monotonic reservation over committed and reserved-uncommitted versions; retries/recovery reuse; failure gaps. |
architecture-blueprint.md:475:- The allocator keeps a persistent, lock-protected **high-water mark over every historical allocation, including failed reservations**. The next version is `high_water + 1`. A failed reservation permanently occupies its version; it never leaves the high-water mark and is never reissued.
architecture-blueprint.md:478:- Ledger replay/repair: replay the append-only allocation records to reconstruct the high-water mark including failed versions; rebuild `committed` projections from terminal manifests. Do not derive allocation history solely from committed manifests (that would lose failed reservations). If the allocation history is missing or corrupt, stop new allocation, restore from a durable backup or operator-approved reconstruction, and never silently reset the watermark or reissue a failed version.
architecture-blueprint.md:870:- `MemoryReservationStore` is a persistent, append-only, lock-protected allocation history with a monotonic high-water mark over **all** historical allocations, including failed reservations. The next version is `high_water + 1`; concurrent runs cannot receive the same version.
architecture-blueprint.md:1058:| Failed version, new run, old retry | Highest version fails and remains in the high-water mark; a new run gets a higher version; the old run retries its own reservation and never reuses the new version | `T-SCEN-15`: fail version N, allocate N+1 to a new run, retry the old run; assert no version reuse, no duplicate entry, effective versions correct |
architecture-blueprint.md:1059:| Commit/ledger-update interruption | Terminal manifest commit succeeds but ledger `committed` projection is missing/fails; manifest remains authority; repair rebuilds projection without losing failed allocations or reissuing versions | `T-SCEN-16`: crash between commit and ledger update; assert history reads, ledger repair, high-water preservation, no second commit condition |
architecture-blueprint.md:1290:| Memory version collision | Two runs receive the same version | Persistent lock-protected monotonic reservation over committed and reserved-uncommitted versions; retries/recovery reuse the reservation. |
docs/architecture/memory-design.md:130:| Same trade_date/ticker with different decision_id | Reserve a pre-commit `entry_version` greater than the highest of committed and reserved-uncommitted versions; write `supersedes`; effective version is the highest committed |
docs/architecture/memory-design.md:149:2. The allocator keeps a persistent high-water mark over **every historical allocation, including failed reservations**. The next version is `high_water + 1`; a failed reservation permanently occupies its version and is never reissued.
docs/architecture/memory-design.md:157:7. Ledger replay/repair replays the append-only allocation records to reconstruct the high-water mark including failed versions, and rebuilds `committed` projections from terminal manifests. Do not derive allocation history solely from committed manifests. If the allocation history is missing/corrupt, stop new allocation, restore from a durable backup or operator-approved reconstruction, and never silently reset the watermark or reissue a failed version.
docs/architecture/memory-design.md:184:- if the process is interrupted between terminal commit and ledger projection update, the terminal manifest remains authoritative; repair rebuilds `committed` without changing the allocation high-water mark or reissuing a failed version.
docs/architecture/memory-design.md:268:- `MemoryReservationStore` allocates versions under the same lock from a persistent high-water mark over every historical allocation, including failed reservations. Two concurrent runs cannot receive the same version; a failed version is never reissued.
docs/architecture/runtime-policy-catalog.md:289:  - `MemoryReservationStore` is a persistent, append-only allocation history; the next version is `high_water + 1` over **all** historical allocations, including failed reservations; a failed version is never reissued; retries/recovery reuse their own reservation; `committed` is a derived projection from the terminal manifest, not a second commit condition;
docs/architecture/invariants.md:38:| INV-A-08 | Memory writes are idempotent, versioned, and conflict-safe; version allocation is persistent, lock-protected, monotonic over committed and reserved-uncommitted versions. | `INV-01`, `FR-06` | `MemoryService`, `MemoryReservationStore` | Duplicate/version/conflict/reservation tests | No-op for same key; new reserved version for changed decision; reuse reservation on retry; conflict on same decision_id/different digest | Design only |
docs/architecture/invariants.md:141:- **Statement**: Memory append is keyed by `(decision_id, entry_digest)` plus the existing `(trade_date, ticker)` guard. The readable criterion is the completed terminal manifest plus read-time INV-01. Same key is a no-op; a different decision_id creates a new committed version; only same decision_id with a different entry_digest is a conflict. Reused historical entries use `reused_decision_ref` and keep the current artifact run_id. Version allocation is persistent and lock-protected, and the next version is `high_water + 1` over every historical allocation, including failed reservations. Retries and recovery reuse their own reservation; a failed version permanently occupies the high-water mark and is never reissued. `reserved` is appended before the recovery snapshot, `failed` on abort before a completed manifest, and `committed` is a derived projection appended only after terminal commit plus read-time INV-01; a missing/failed projection write is rebuilt from the terminal manifest and is not a second commit condition. An uncommitted entry is never treated as reusable success; `MemoryRecoveryCoordinator` applies bounded wait/`MEMORY_PENDING_RETRYABLE`, recovery under the original run identity/reservation/snapshot, and typed unavailable/failed/conflict statuses; it never transfers ownership. Settlement/reflection is append-only; legal rotation is recorded as `not_available`, not a binding mismatch.
docs/architecture/open-decisions.md:377:- **Question**: where is the persistent reservation ledger stored, and how does it atomically track committed and reserved-uncommitted versions?
docs/architecture/open-decisions.md:379:- **Recommendation (not approved)**: a lock-protected `memory/reservations.jsonl` ledger keyed by ticker/date/decision_id, recording entry_version, owner run_id, status reserved/committed/failed, and fencing token. It is authoritative for version allocation, not for decision content. The next version is `high_water + 1` over every historical allocation, including failed reservations; a failed version is never reissued; retries/recovery reuse their own reservation; recovery uses the original run_id/version/snapshot; `committed` is a derived projection from the terminal manifest, not a second commit condition. Repair replays the append-only allocation history and never resets the watermark or reissues failed versions. If a structured sidecar is rejected, the same fields must live in a structured Markdown metadata line under the same lock.

```

---

## Assistant (Build · DeepSeek Flash · 5.6s)

_Thinking:_

There are stale rows in blueprint component catalog and state ownership and risk table and memory design table/invariant inventory still say "committed and reserved-uncommitted". Need update to high-water all allocations. Specifically:
- blueprint line 312 component row.
- blueprint line 407 state ownership.
- blueprint line 1290 risk table.
- memory design line 130 table row.
- invariants line 38 inventory.
- open decisions line 377 question.
Let's fix all.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"| `MemoryReservationStore` | `run/memory_reservation.py` | Persistent, lock-protected monotonic entry-version reservation over committed and reserved-uncommitted versions; reuse on retry/recovery; failure gaps | ticker/date, decision_id, owner/lease | `MemoryReservation` | `ReservationError`, `ReservationConflict` | Reservation ledger | MemoryLock, Canonicalizer | 1/2 |\",\n\"| `MemoryReservationStore` | `run/memory_reservation.py` | Persistent, append-only allocation history with a monotonic high-water mark over all historical allocations, including failed; retry/recovery reuse; new runs get higher versions | ticker/date, decision_id, owner/lease | `MemoryReservation` | `ReservationError`, `ReservationConflict` | Reservation ledger | MemoryLock, Canonicalizer | 1/2 |\")\ns=s.replace(\"| Memory version reservation | `MemoryReservationStore` | Persistent, lock-protected monotonic reservation over committed and reserved-uncommitted versions; retries/recovery reuse; failure gaps. |\",\n\"| Memory version reservation | `MemoryReservationStore` | Persistent, append-only allocation history; next version is `high_water + 1` over all historical allocations including failed; retries/recovery reuse; failed versions never reissued. |\")\ns=s.replace(\"| Memory version collision | Two runs receive the same version | Persistent lock-protected monotonic reservation over committed and reserved-uncommitted versions; retries/recovery reuse the reservation. |\",\n\"| Memory version collision | Two runs receive the same version, or a failed version is reissued | Persistent append-only allocation history with a high-water mark over all allocations including failed; retries/recovery reuse their own reservation. |\")\np.write_text(s)\np=Path('docs/architecture/memory-design.md')\ns=p.read_text()\ns=s.replace(\"| Same trade_date/ticker with different decision_id | Reserve a pre-commit `entry_version` greater than the highest of committed and reserved-uncommitted versions; write `supersedes`; effective version is the highest committed |\",\n\"| Same trade_date/ticker with different decision_id | Reserve a pre-commit `entry_version` greater than the persistent high-water mark over all historical allocations, including failed; write `supersedes`; effective version is the highest committed |\")\np.write_text(s)\np=Path('docs/architecture/invariants.md')\ns=p.read_text()\ns=s.replace(\"| INV-A-08 | Memory writes are idempotent, versioned, and conflict-safe; version allocation is persistent, lock-protected, monotonic over committed and reserved-uncommitted versions. |\",\n\"| INV-A-08 | Memory writes are idempotent, versioned, and conflict-safe; version allocation is persistent, lock-protected, and monotonic over every historical allocation, including failed reservations. |\")\np.write_text(s)\np=Path('docs/architecture/open-decisions.md')\ns=p.read_text()\ns=s.replace(\"- **Question**: where is the persistent reservation ledger stored, and how does it atomically track committed and reserved-uncommitted versions?\",\n\"- **Question**: where is the persistent reservation history stored, and how does it atomically track the allocation high-water mark (including failed reservations) and derived commit projections?\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.2s)

_Thinking:_

Search again for reserved-uncommitted.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"reserved-uncommitted\\|highest of committed and reserved\" architecture-blueprint.md docs/architecture || echo none"
}
```

**Output:**
```
docs/architecture/adr/001-run-governance.md:51:- `MemoryService` remains the only memory writer. `MemoryReservationStore` provides a persistent, lock-protected monotonic reservation over committed and reserved-uncommitted versions; retries/recovery reuse the reservation and failure may leave a gap. The reuse/new plan is fixed before the recovery snapshot.
docs/architecture/adr/002-full-scope-add-r.md:170:| Memory versions collide | Persistent lock-protected monotonic reservation over committed and reserved-uncommitted versions. |
docs/architecture/trace-matrix.md:303:| `T-ARCH-24` | memory reservation over committed and reserved-uncommitted versions; retry reuse; failure gap | not started |

```

---

## Assistant (Build · DeepSeek Flash · 4.2s)

_Thinking:_

Fix these.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/adr/001-run-governance.md')\ns=p.read_text()\ns=s.replace(\"- `MemoryService` remains the only memory writer. `MemoryReservationStore` provides a persistent, lock-protected monotonic reservation over committed and reserved-uncommitted versions; retries/recovery reuse the reservation and failure may leave a gap. The reuse/new plan is fixed before the recovery snapshot.\",\n\"- `MemoryService` remains the only memory writer. `MemoryReservationStore` provides a persistent, append-only allocation history with a high-water mark over all historical allocations, including failed; a failed version is never reissued; retries/recovery reuse their own reservation; `committed` is a derived projection, not a second commit condition. The reuse/new plan is fixed before the recovery snapshot.\")\np.write_text(s)\np=Path('docs/architecture/adr/002-full-scope-add-r.md')\ns=p.read_text()\ns=s.replace(\"| Memory versions collide | Persistent lock-protected monotonic reservation over committed and reserved-uncommitted versions. |\",\n\"| Memory versions collide or failed versions are reissued | Persistent append-only allocation history with a high-water mark over all allocations including failed; retries/recovery reuse their own reservation. |\")\np.write_text(s)\np=Path('docs/architecture/trace-matrix.md')\ns=p.read_text()\ns=s.replace(\"| `T-ARCH-24` | memory reservation over committed and reserved-uncommitted versions; retry reuse; failure gap | not started |\",\n\"| `T-ARCH-24` | memory allocation high-water over all historical allocations including failed; retry reuse; failed-version gap; new-run higher version | not started |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.2s)

_Thinking:_

Good.

### Step 8: Hash DAG consistency in trace/eval/invariants
Need update trace T-ARCH-39 description already. Add binding no terminal hash maybe. Good.
Need update §9.6.1 binding comment and publication_ref. Done.
Need ensure no other doc says binding includes terminal manifest hash. Search.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"terminal_manifest_hash\\|terminal-manifest hash\\|manifest hashes\" architecture-blueprint.md docs/architecture | head -50"
}
```

**Output:**
```
architecture-blueprint.md:437:    binding.json                     # artifact_binding + record_hash; no terminal-manifest hash
architecture-blueprint.md:459:- `publication_ref` = `{root: "publication", files: [{relative_path, sha256, hash_scope: "file"}], record_hash}`; it contains no terminal-manifest hash. All paths are relative and confined.
architecture-blueprint.md:524:| `record.json` | Canonical `FinalizedRunRecord` content and `artifact_binding` fields | Run-level generated/evaluated/finished timestamps, local paths, cache counters, terminal-manifest hash, recovery-snapshot hash | 1 |
architecture-blueprint.md:528:| `recovery/recovery_snapshot.json` | Self-contained inputs, formal decision/binding, memory plan/reservation, versions | Final terminal-manifest hash; it may carry terminal-candidate identity (`run_id`, `decision_id`, `record_hash`, reservation) | 4 |
architecture-blueprint.md:532:- `binding.json` never stores a terminal-manifest hash or a full terminal-manifest file hash.
architecture-blueprint.md:909:9. Build the terminal manifest candidate with binding, formal decision, security scans, section manifest, metric bundle, risk evidence, memory binding, and `publication_ref` hashes. If desired, include a `recovery_snapshot_summary` (status/digest/created-at) as audit-only; no terminal-manifest hash is written into `binding.json` or any file hashed by the manifest.
docs/architecture/adr/001-run-governance.md:48:- `PublicationSnapshotStore` holds permanent committed records. `RecoverySnapshotStore` holds temporary pending envelopes. History and export read the permanent snapshot and revalidate on every read. Permanent artifacts form an acyclic hash DAG: `binding.json` has no terminal-manifest hash; the manifest hashes permanent files; no hashed file contains the manifest hash.
docs/architecture/adr/002-full-scope-add-r.md:62:- Permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; optional `diagnostics/commit_evidence.json` is audit-only.
docs/architecture/invariants.md:70:| INV-A-40 | Permanent artifacts form an acyclic hash DAG; `binding.json` never contains the terminal-manifest hash, and no file hashed by the terminal manifest contains that hash. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService` | Hash-DAG ordering/cycle tests | Reject cyclic candidate; no commit | Design only | | `INV-01`, `FR-06`, `INV-02` | `MemoryRecoveryCoordinator`, `MemoryService`, `RecoveryService` | Active/expired/missing-snapshot/failed/conflict tests | Retryable/unavailable/failed/conflict; no duplicate | Design only |
docs/architecture/invariants.md:429:- **Statement**: Permanent artifacts form a directed acyclic hash graph. `record_hash` is computed first; `binding.json` covers `artifact_binding` plus `record_hash` but excludes the terminal-manifest hash, its own file hash, the recovery digest, and commit-evidence hash. Section/final-state/risk/metric/memory files are hashed next. The recovery snapshot may carry terminal-candidate identity but not the final terminal-manifest hash. The terminal manifest covers `publication_ref` hashes (including `binding.json`) and may hold a `recovery_snapshot_summary` as audit-only; it never hashes itself. An optional `diagnostics/commit_evidence.json` may record the terminal-manifest hash after commit but is outside the permanent hashed set and is not a commit authority.
docs/architecture/invariants.md:432:- **Verification**: compute in the declared order; assert no cycle and no file hashed by the terminal manifest contains its hash; assert binding has no terminal-manifest hash.
docs/architecture/runtime-policy-catalog.md:210:  - permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; an optional `diagnostics/commit_evidence.json` is audit-only;
docs/architecture/runtime-policy-catalog.md:231:- **Dependency**: report, history, export, and memory binding validation depend on `publication/` and the terminal manifest. They do not depend on `recovery/`. The hash DAG is acyclic: `binding.json` has no terminal-manifest hash; the terminal manifest hashes permanent files; no hashed file contains the manifest hash.
docs/architecture/open-decisions.md:406:- **Recommendation (not approved)**: use the `publication/`, `recovery/`, `locks/`, `diagnostics/` layout in blueprint §9.6.1. Formal report/history/export/memory binding validation depend only on `publication/` + terminal manifest; `recovery/` is temporary and may be cleaned; a terminal `recovery_snapshot_summary` is audit-only. The hash DAG is acyclic: `binding.json` contains no terminal-manifest hash; the manifest hashes permanent files including binding; no hashed file contains the manifest hash; optional `commit_evidence.json` is audit-only.

```

---

## Assistant (Build · DeepSeek Flash · 3.1s)

_Thinking:_

There is a table corruption in invariants line 70: INV-A-40 row has appended INV-A-39 cells because our replacement for INV-A-39 inventory row likely inserted incorrectly. Need fix table row. Let's inspect inventory around 60-72.

**Tool: bash**

**Input:**
```json
{
  "command": "sed -n '58,72p' docs/architecture/invariants.md"
}
```

**Output:**
```
| INV-A-28 | Publication recovery uses saved records only, preserves the original run_id, and yields at most one committed publication. | `FR-06` | `RecoveryService`, `ArtifactPublisher` | Model-free/duplicate/retry tests | Quarantine; no publish; bounded retry | Design only |
| INV-A-29 | A recovery snapshot is complete, durable, read-back-verified, internally referenced, and versioned before recovery guarantees begin. | `FR-06` | `RecoverySnapshotStore` | Snapshot reference/digest/fault tests | Quarantine; retain valid material | Design only |
| INV-A-30 | Financial facts and metrics use structured identity and as-of visibility; the metric block is the numeric authority. | `FR-07` | `FinancialFactService`, `FinancialMetricService`, `MetricConflictDetector` | Fact/period/formula/conflict tests | n/a with typed reason; disclose conflict | Design only |
| INV-A-31 | Mandatory brief content is never truncated; the brief is generated before the five roles, uses a versioned program view, replaces the four full reports for those roles, and never mutates full/formal/history/recovery artifacts. | `FR-08` | `DownstreamBriefBuilder`, `ContextAssembler` | Budget/replacement/view-version/non-mutation tests | `BRIEF_REJECTED`; fail closed; no bypass | Design only |
| INV-A-32 | The final model request obeys the token budget; characters/bytes are auxiliary. | `FR-08`, D2 context design | `TokenCounter`, `ContextAssembler` | Tokenizer fixture | Reject/compress; fail closed | Design only |
| INV-A-33 | A `verified_package` export either proves every followed history reference or is labeled `historical_reference_unverified`; a non-empty target is never overwritten. | `FR-05`, `SR-01` | `ExportService` | Closure/conflict tests | Label limitation; return EXPORT_CONFLICT | Design only |
| INV-A-34 | A post-commit read failure never overwrites the committed terminal manifest; the record is rejected as success and an independent diagnostic records the corruption. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationStatusReader`, `HistoryService` | Post-commit tamper tests | Keep immutable manifest; `CORRUPT_RECORD`; no second publication | Design only |
| INV-A-35 | Normal publication and recovery share one per-run ownership lock/fencing token; ownership is checked in the same critical section as the protected write; OS file lock and logical lease are distinct. | `FR-02`, `FR-06` | `RunOwnershipLock`, `ArtifactPublisher`, `RecoveryService` | Concurrent publisher/recovery, stale takeover, lost-owner, paused-lock tests | Reject lost owner; one winner; no duplicate write; `LOCK_BUSY` when file lock held | Design only |
| INV-A-36 | The final model proposal is produced by the Portfolio Manager adapter, not by the Trader or a risk debater; it carries source and unapproved status. | `SB-01`, `INV-01` | `PortfolioManagerAdapter`, `SafetyGate` | Source-field/source-promotion audit | Reject proposal; no formal decision | Design only |
| INV-A-37 | Temporary recovery material may be cleaned after commit/validation; formal reads and export depend only on the permanent publication snapshot; a terminal recovery summary is audit-only. | `FR-02`, `FR-05`, `FR-06`, `INV-01` | `ArtifactPublisher`, `PublicationSnapshotStore`, `HistoryService`, `ExportService` | Cleanup-then-read/memory/export tests | Reject temporary-file dependency; keep permanent records | Design only |
| INV-A-38 | Brief failure states are distinct: disabled uses normal full input; full-report fallback requires explicit policy permission and hard-cap compliance; final `BRIEF_REJECTED` is terminal and cannot re-enter normal input or generic compression. | `FR-08` | `DownstreamBriefBuilder`, `ContextAssembler` | Disabled/fallback/rejection/bypass tests | Fail closed at context stage; no bypass | Design only |
| INV-A-39 | A same-decision uncommitted entry is never reused or ownership-transferred; B waits bounded or triggers recovery under A's original run_id/reservation/snapshot; missing snapshot/failure/conflict are typed. Failed reservations permanently occupy their versions. | `INV-01`, `FR-06`, `INV-02` | `MemoryRecoveryCoordinator`, `MemoryService`, `RecoveryService` | Active/expired/missing-snapshot/failed/conflict tests | Retryable/unavailable/failed/conflict; no duplicate | Design only |
| INV-A-40 | Permanent artifacts form an acyclic hash DAG; `binding.json` never contains the terminal-manifest hash, and no file hashed by the terminal manifest contains that hash. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService` | Hash-DAG ordering/cycle tests | Reject cyclic candidate; no commit | Design only | | `INV-01`, `FR-06`, `INV-02` | `MemoryRecoveryCoordinator`, `MemoryService`, `RecoveryService` | Active/expired/missing-snapshot/failed/conflict tests | Retryable/unavailable/failed/conflict; no duplicate | Design only |

---

```

---

## Assistant (Build · DeepSeek Flash · 4.2s)

_Thinking:_

INV-A-40 row has extra leftover columns. Fix row to end after "Design only |".

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/invariants.md')\ns=p.read_text()\nold=\"| INV-A-40 | Permanent artifacts form an acyclic hash DAG; `binding.json` never contains the terminal-manifest hash, and no file hashed by the terminal manifest contains that hash. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService` | Hash-DAG ordering/cycle tests | Reject cyclic candidate; no commit | Design only | | `INV-01`, `FR-06`, `INV-02` | `MemoryRecoveryCoordinator`, `MemoryService`, `RecoveryService` | Active/expired/missing-snapshot/failed/conflict tests | Retryable/unavailable/failed/conflict; no duplicate | Design only |\"\nnew=\"| INV-A-40 | Permanent artifacts form an acyclic hash DAG; `binding.json` never contains the terminal-manifest hash, and no file hashed by the terminal manifest contains that hash. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService` | Hash-DAG ordering/cycle tests | Reject cyclic candidate; no commit | Design only |\"\ns=s.replace(old,new)\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.5s)

_Thinking:_

Now table consistency check.

**Tool: bash**

**Input:**
```json
{
  "command": "ruby -e '\nfiles = Dir[\"architecture-blueprint.md\"] + Dir[\"docs/architecture/**/*.md\"]\nfiles.each do |f|\n lines=File.readlines(f,chomp:true); i=0\n while i<lines.length\n  if lines[i].start_with?(\"|\")\n   block=[]; j=i\n   while j<lines.length && lines[j].start_with?(\"|\"); block<<[j+1,lines[j]]; j+=1; end\n   data=block.reject{|ln,l| l.gsub(/[|\\-: ]/,\"\").empty?}\n   if data.length>1\n    exp=data.first[1].split(\"|\",-1).length\n    data.each{|ln,l| c=l.split(\"|\",-1).length; puts \"#{f}:#{ln} cells=#{c} exp=#{exp}\" if c!=exp}\n   end\n   i=j\n  else; i+=1; end\n end\nend\n' | head -20; echo \"table check done\""
}
```

**Output:**
```
table check done

```

---

## Assistant (Build · DeepSeek Flash · 4.6s)

_Thinking:_

Good.

### Step 9: Recovery flow and locks – check no `RunOwnershipLock.protect` whole recovery remains. Search.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"RunOwnershipLock.protect\\|protect(run_id\" architecture-blueprint.md docs/architecture | head -20; echo \"=== whole recovery lock wording ===\"; grep -rn \"under RunOwnershipLock\\|under the RunOwnershipLock\\|entire recovery\\|whole recovery\" architecture-blueprint.md docs/architecture | head -30"
}
```

**Output:**
```
architecture-blueprint.md:238:- **Interfaces**: `publish(record) -> PublishResult`; `list_publications(filters) -> HistoryPage`; `get_run(run_id) -> VerifiedPublication`; `export(run_id, mode, target) -> ExportResult`; `scan_and_recover(startup) -> RecoveryReport`; `claim(run_id, owner) -> Claim`; `assert_owner(claim)`; `RunOwnershipLock.protect(run_id, owner, write_fn)`.
architecture-blueprint.md:362:RunOwnershipLock.protect(run_id, owner, write_fn) -> ProtectedWriteResult
architecture-blueprint.md:638:  -> RunOwnershipLock.protect(run_id, terminal commit)
=== whole recovery lock wording ===
architecture-blueprint.md:466:- `run.lock` is an OS advisory lock used only for short critical sections: read lease, update owner/token/expiry, and perform the protected write. It is never held for the whole recovery, never held while waiting for another run's memory, and never held across a model call.
architecture-blueprint.md:1085:- `run.lock` is an OS advisory file lock used only for short critical sections: read the lease, update owner/token/expiry, and perform the protected write. It is never held for the whole recovery, across model calls, or while waiting for another run.
docs/architecture/invariants.md:384:- **Statement**: Normal publication and recovery use one per-run OS file lock (`run.lock`), a logical lease record (`lease.json`), owner identity, and fencing token. The file lock is held only for short ownership/token update/protected writes, never for the whole recovery or while waiting. Lease expiry does not release the OS file lock. A paused old process holding the file lock can only be waited on or reported as `LOCK_BUSY`; the lock file is never deleted. Takeover acquires the file lock, increments the fencing token, and the old owner rechecks the token on every protected write. Lock order is run lock then memory lock; a lost owner cannot write publication, memory, cleanup, or owner diagnostics.
docs/architecture/runtime-policy-catalog.md:271:- **OS file lock vs logical lease**: `run.lock` is an OS advisory file lock held only for short critical sections (read lease, update owner/token/expiry, protected write); it is never held for the whole recovery or while waiting. `lease.json` is the logical lease (`owner_id`, `fencing_token`, `lease_expires_at`, status). Lease expiry does not release the OS file lock.

```

---

## Assistant (Build · DeepSeek Flash · 3.9s)

_Thinking:_

`RunOwnershipLock.protect` remains in interfaces and normal publication flow line 638 (terminal commit), which is fine (short critical section). The recovery flow no longer uses it. Good.

Need update interface maybe `protect` name implies whole function; but it's used for short write. Fine.

Need ensure normal publication flow uses `protect` only terminal commit, not whole. It does. Good.

### Step 10: Brief state branch – check no generic normal path fallback remains. Search "otherwise use the role's normal input path" gone. Check `BRIEF_REJECTED` docs all consistent. Search "if a valid brief exists" etc.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"otherwise use the role's normal\\|if a valid brief exists\\|no valid brief\\|brief unavailable\" architecture-blueprint.md docs/architecture || echo none; grep -rn \"BRIEF_REJECTED\" architecture-blueprint.md docs/architecture | grep -i \"normal\\|full\\|bypass\\|completed\""
}
```

**Output:**
```
none
architecture-blueprint.md:58:12. Brief failure states are explicit: disabled uses normal full input; full-report fallback requires explicit policy permission, complete mandatory content, and hard-cap compliance; final `BRIEF_REJECTED` is terminal and cannot re-enter normal input or generic compression.
architecture-blueprint.md:267:- **Review**: the brief is generated before the five target roles receive context and reused across Bull, Bear, and the three risk debaters with the same recorded `coverage_view_version` unless the program view changes, in which case a new versioned brief replaces it. It uses the program coverage view at that time; the final gate still uses the final coverage snapshot. For the five roles it replaces the four full analyst reports (no duplicate full+brief injection); other roles keep full inputs. Mandatory content is canonical `FR-03` gaps, the `FR-07` metric block and sources, and safety constraints; mandatory budget is reserved first; protected markers prevent any generic compression from truncating them; ordered resolution expansion -> reference -> full report -> `BRIEF_REJECTED`; token measurement uses the selected model/tokenizer; character limits are auxiliary; full reports/formal records/history/recovery are byte-identical; audit metadata is stored separately; quality is judged only against the approved `quality_loss_max`; no saving is claimed before acceptance. No brief is generated after the final decision.
architecture-blueprint.md:849:| `BRIEF_REJECTED` | Mandatory content exceeds hard cap, no resolvable reference, full-report fallback not allowed or does not fit, tokenizer unavailable, or invalid markers | Terminal for the five-role context: fail closed with `error.stage=context`; no ordinary input path, no generic compression, and no full-report injection may be used to bypass the rejection. |
architecture-blueprint.md:851:- Full-report fallback is allowed only when the versioned policy explicitly permits it, all mandatory content is preserved, and the final request is within the context hard cap. It is never a recovery from `BRIEF_REJECTED`.
architecture-blueprint.md:852:- After `BRIEF_REJECTED`, the five-role stage does not fall back to normal full input or generic compression; the run fails closed with a typed brief rejection record. Other formal artifacts already computed may be retained as evidence, but no tradeable formal decision is produced.
architecture-blueprint.md:1020:| Brief mandatory exceeds hard cap or all safe fallbacks fail | n/a | n/a | Full artifacts may remain as evidence; no formal decision | Recovery unaffected | Unchanged | `BRIEF_REJECTED`; no re-entry to normal input/generic compression | `failed` at context stage |
architecture-blueprint.md:1021:| Brief tokenizer missing | n/a | n/a | Full artifacts may remain as evidence | Unaffected | Unchanged | `BRIEF_REJECTED` | `failed` at context stage |
architecture-blueprint.md:1051:| Context overflow | No oversized model request; mandatory brief content preserved; safe compression/reference/rejection; all fallbacks obey hard cap | `T-SCEN-08`: over-budget context and brief cases; assert `ContextBudgetError`/`BRIEF_REJECTED`, protected blocks intact, no full+brief duplication |
architecture-blueprint.md:1160:| Brief rejected | No brief or full reports injected for the five roles; run fails closed at context stage | `BRIEF_REJECTED` | No bypass via normal input or generic compression |
architecture-blueprint.md:1169:2. Add L3/L4. For the five target roles, branch on the brief state: `BRIEF_DISABLED` uses the role's normal full-report path; `BRIEF_OK`/`BRIEF_FULL_REPORT` use the selected brief/full-report replacement; `BRIEF_REJECTED` fails closed at the context stage and does not use normal full input or generic compression.
architecture-blueprint.md:1220:| 5. Brief and context | `FR-08`; brief before five-role context; replacement mapping; protected markers; token counter; budget policy; audit metadata; compression | Mandatory preservation; budget/reference/rejection; role replacement; non-mutation; quality/safety evaluation; over-budget failure | Brief disabled -> full reports to five roles (existing behavior); tokenizer missing or all safe fallbacks fail -> `BRIEF_REJECTED` and run failed at context stage; compression disabled -> over-budget fails closed |
docs/architecture/adr/002-full-scope-add-r.md:91:- A versioned budget policy defines the ordered resolution: expansion -> resolvable reference -> full report within the context hard cap -> `BRIEF_REJECTED`. Every branch obeys the context hard cap.
docs/architecture/adr/002-full-scope-add-r.md:92:- Failure states are distinct: `BRIEF_DISABLED` uses the normal full-input path; `BRIEF_FULL_REPORT` is allowed only when the policy explicitly permits it, mandatory content is complete, and the full report fits the hard cap; `BRIEF_REJECTED` is terminal for the five-role context and cannot re-enter normal input or generic compression. The run fails closed at the context stage.
docs/architecture/invariants.md:61:| INV-A-31 | Mandatory brief content is never truncated; the brief is generated before the five roles, uses a versioned program view, replaces the four full reports for those roles, and never mutates full/formal/history/recovery artifacts. | `FR-08` | `DownstreamBriefBuilder`, `ContextAssembler` | Budget/replacement/view-version/non-mutation tests | `BRIEF_REJECTED`; fail closed; no bypass | Design only |
docs/architecture/invariants.md:68:| INV-A-38 | Brief failure states are distinct: disabled uses normal full input; full-report fallback requires explicit policy permission and hard-cap compliance; final `BRIEF_REJECTED` is terminal and cannot re-enter normal input or generic compression. | `FR-08` | `DownstreamBriefBuilder`, `ContextAssembler` | Disabled/fallback/rejection/bypass tests | Fail closed at context stage; no bypass | Design only |
docs/architecture/invariants.md:352:- **Fallback**: `BRIEF_REJECTED`; fail closed at context stage; full reports remain formal artifacts but are not injected into the rejected five-role context; no bypass via normal input or generic compression.
docs/architecture/invariants.md:411:- **Statement**: `BRIEF_DISABLED` uses the normal full-input path and is not a fallback/rejection. `BRIEF_FULL_REPORT` is allowed only when the versioned policy explicitly permits it, mandatory content is complete, and the full report fits the context hard cap. `BRIEF_REJECTED` is terminal for the five-role context; the run fails closed at the context stage and must not re-enter the ordinary full-input path or generic compression to bypass the rejection.
docs/architecture/trace-matrix.md:311:| `T-ARCH-32` | brief failure state machine: `BRIEF_DISABLED`/`BRIEF_FULL_REPORT`/`BRIEF_REJECTED`; no post-rejection bypass | not started |
docs/architecture/runtime-policy-catalog.md:319:- **Ordered resolution**: mandatory above hard cap -> reject; otherwise expand to hard cap if allowed; otherwise downstream-resolvable reference whose payload counts against the context hard cap; otherwise full report only if the policy explicitly allows it, mandatory content is complete, and it fits the context hard cap; otherwise `BRIEF_REJECTED`. Every branch obeys the context hard cap; no branch combines full report and brief for the same role.
docs/architecture/runtime-policy-catalog.md:320:- **Failure states**: `BRIEF_DISABLED` uses the normal full-input path; `BRIEF_FULL_REPORT` is an allowed fallback only under the stated conditions; `BRIEF_REJECTED` is terminal for the five-role context and fails closed at the context stage. No re-entry to normal input or generic compression after `BRIEF_REJECTED`.
docs/architecture/runtime-policy-catalog.md:321:- **Run status**: `BRIEF_REJECTED` -> `failed` at context stage; full artifacts may remain as evidence but no tradeable formal decision is produced.
docs/architecture/permission-model.md:108:- `BRIEF_DISABLED` uses the normal full-input path; `BRIEF_FULL_REPORT` is allowed only with explicit policy permission and hard-cap compliance; `BRIEF_REJECTED` is terminal and cannot re-enter normal input or generic compression.

```

---

## Assistant (Build · DeepSeek Flash · 6.5s)

_Thinking:_

Looks consistent. `BRIEF_DISABLED uses normal full input` is correct feature-disabled path, not a fallback from invalid brief. Good.

### Step 11: Hash DAG check for table corruption and binding. Good. But need ensure `publication_ref` no `terminal_manifest_hash`; done. Need check `record.json` digest excludes recovery hash; okay.

Need update `docs/architecture/invariants.md` INV-A-40 inventory and summary. Table consistency check passed. Good.

Need update `docs/architecture/evaluation-table.md` maybe hash DAG row; added permanent hash DAG measurement. Good.

### Step 12: Ledger state transitions in runtime/memory/invariants. Check for explicit state transition table. We added bullets, maybe enough. Could add a small table in memory design §7 for states. The user asks "明确reserved、committed、failed的转换时机，以及写入失败、中断和重试后的处理方式". We have bullets. Maybe make a table for clarity. Let's add a table after §7 list:
| State | When written | If interrupted | Retry/recovery |
- reserved before recovery snapshot; durable; if interrupted, reservation persists; retry reuses.
- failed on abort before completed manifest; persists; never reissued.
- committed projection after terminal commit + INV-01; if ledger write fails, manifest authority; repair rebuilds; if mark exists without manifest, not commit.
Let's add.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/memory-design.md')\ns=p.read_text()\ns=s.replace(\"\"\"10. The order is fixed: plan/reservation -> recovery snapshot containing the plan -> idempotent memory write -> permanent snapshot -> terminal candidate -> commit. Recovery follows the recorded plan.\n\n---\n\n## 8. Retry protocol\"\"\",\n\"\"\"10. The order is fixed: plan/reservation -> recovery snapshot containing the plan -> idempotent memory write -> permanent snapshot -> terminal candidate -> commit. Recovery follows the recorded plan.\n\n| Ledger state | Written when | Interruption behavior | Retry/recovery |\n|---|---|---|---|\n| `reserved` | Before the recovery snapshot; durable allocation history | Remains reserved; version stays occupied | Original run/retry reuses it; no new version |\n| `failed` | Publish aborts before a completed terminal manifest, or memory write fails | Remains failed; version stays occupied forever | Original run/retry may reuse the same reservation; other runs get higher versions |\n| `committed` projection | After terminal commit plus read-time `INV-01`; audit/cache aid only | Missing/failed ledger write does not change the manifest authority; rebuild from manifest | Repair rebuilds projection; never changes allocation high-water mark |\n\n---\n\n## 8. Retry protocol\"\"\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.6s)

_Thinking:_

### Step 13: Recovery flow consistency in ADR/runtime
Check ADR 001/002 maybe say "recovery uses same lock" but not whole. ADR 002 says "RecoveryClaimStore and RunOwnershipLock provide one per-run owner/lease/fencing protocol"; okay. ADR 001 bullet "ownership checked in same critical section"; okay. Runtime POL-REC says "claim/fencing same RunOwnershipLock; ownership checked same critical section"; okay. But does any doc still imply whole recovery under lock? Search "recovery critical section", "protect" in runtime.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"recovery critical section\\|recovery.*lock.*entire\\|held.*recovery\\|protect(run_id\" architecture-blueprint.md docs/architecture | head -30"
}
```

**Output:**
```
architecture-blueprint.md:238:- **Interfaces**: `publish(record) -> PublishResult`; `list_publications(filters) -> HistoryPage`; `get_run(run_id) -> VerifiedPublication`; `export(run_id, mode, target) -> ExportResult`; `scan_and_recover(startup) -> RecoveryReport`; `claim(run_id, owner) -> Claim`; `assert_owner(claim)`; `RunOwnershipLock.protect(run_id, owner, write_fn)`.
architecture-blueprint.md:362:RunOwnershipLock.protect(run_id, owner, write_fn) -> ProtectedWriteResult
architecture-blueprint.md:466:- `run.lock` is an OS advisory lock used only for short critical sections: read lease, update owner/token/expiry, and perform the protected write. It is never held for the whole recovery, never held while waiting for another run's memory, and never held across a model call.
architecture-blueprint.md:638:  -> RunOwnershipLock.protect(run_id, terminal commit)
architecture-blueprint.md:1085:- `run.lock` is an OS advisory file lock used only for short critical sections: read the lease, update owner/token/expiry, and perform the protected write. It is never held for the whole recovery, across model calls, or while waiting for another run.
docs/architecture/invariants.md:384:- **Statement**: Normal publication and recovery use one per-run OS file lock (`run.lock`), a logical lease record (`lease.json`), owner identity, and fencing token. The file lock is held only for short ownership/token update/protected writes, never for the whole recovery or while waiting. Lease expiry does not release the OS file lock. A paused old process holding the file lock can only be waited on or reported as `LOCK_BUSY`; the lock file is never deleted. Takeover acquires the file lock, increments the fencing token, and the old owner rechecks the token on every protected write. Lock order is run lock then memory lock; a lost owner cannot write publication, memory, cleanup, or owner diagnostics.
docs/architecture/runtime-policy-catalog.md:271:- **OS file lock vs logical lease**: `run.lock` is an OS advisory file lock held only for short critical sections (read lease, update owner/token/expiry, protected write); it is never held for the whole recovery or while waiting. `lease.json` is the logical lease (`owner_id`, `fencing_token`, `lease_expires_at`, status). Lease expiry does not release the OS file lock.
docs/architecture/open-decisions.md:343:- **Recommendation (not approved)**: `run.lock` is a short-lived OS advisory file lock; `lease.json` is the logical lease (`owner_id`, `fencing_token`, `lease_expires_at`, status). File lock is held only for ownership check/token update/protected write, never across recovery or waiting. Takeover acquires the file lock first; lease expiry alone does not release the file lock; a paused old process holding the file lock can only be waited on or reported as `LOCK_BUSY`; never delete the lock file. Once acquired, takeover increments the fencing token; the old owner rechecks on every write and is rejected with `LostOwnership`. Lock order run lock -> memory lock; retry reacquires and rechecks; cleanup releases only its own lock. No second commit marker or transaction.

```

---

## Assistant (Build · DeepSeek Flash · 4.5s)

_Thinking:_

`RunOwnershipLock.protect` interface maybe implies wrapping function; but it's a generic protected write helper, not whole recovery. Could rename to `with_ownership` or clarify. The user says delete `RunOwnershipLock.protect` covering entire recovery. It's gone from recovery flow; interface remains for protected write. Fine. But to avoid confusion, rename to `RunOwnershipLock.protected_write(run_id, owner, write_fn)`? Could be clearer. Not necessary, but maybe update interface name to `owned_write` or `critical_section`. The user specifically says "删除覆盖整个恢复过程的 RunOwnershipLock.protect" — we deleted the flow usage. The interface name still might be interpreted. Could rename to `RunOwnershipLock.critical_section(run_id, owner, write_fn)` to emphasize short. Let's do rename in blueprint interfaces/flow and ADR? Only blueprint uses `protect`. Rename to `critical_section`. Also §11.1 normal flow line 638 `RunOwnershipLock.protect(run_id, terminal commit)` -> `RunOwnershipLock.critical_section(...)`. This avoids residual implication. Let's do.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"`RunOwnershipLock.protect(run_id, owner, write_fn)`\", \"`RunOwnershipLock.critical_section(run_id, owner, write_fn)`\")\ns=s.replace(\"RunOwnershipLock.protect(run_id, owner, write_fn) -> ProtectedWriteResult\", \"RunOwnershipLock.critical_section(run_id, owner, write_fn) -> ProtectedWriteResult\")\ns=s.replace(\"  -> RunOwnershipLock.protect(run_id, terminal commit)\", \"  -> RunOwnershipLock.critical_section(run_id, terminal commit)\")\np.write_text(s)\nPY\ngrep -rn \"RunOwnershipLock.protect\" architecture-blueprint.md docs/architecture || echo none"
}
```

**Output:**
```
none

```

---

## Assistant (Build · DeepSeek Flash · 3.5s)

_Thinking:_

Now check runtime POL-REC "claim/fencing" maybe says "Recovery claims atomically per run_id" fine.

### Step 14: Check SEC per-fact contract in all docs
Search for old output pattern "filings: [" or "statements: [".

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"filings:\\|statements:\\|rows: \\[{concept\" architecture-blueprint.md docs/architecture || echo none; grep -rn \"per-fact\\|per fact\\|fact_id\" architecture-blueprint.md docs/architecture/adr/002-full-scope-add-r.md docs/architecture/runtime-policy-catalog.md docs/architecture/open-decisions.md | head -30"
}
```

**Output:**
```
none
architecture-blueprint.md:496:     fact_id,
architecture-blueprint.md:508:     restates_fact_id?,                # explicit restatement/alternative lineage
architecture-blueprint.md:514:- **Source-field ownership**: `subject_id`, `accession_no`, `filing_ref`, `filed_at`, `form`, `concept`, `period_*`, `fiscal_*`, `span`, `unit`, `currency`, `value`, `sign`, and any restatement/supersession link are preserved from the raw SEC filing/fact data. `FinancialFactService` may validate, canonicalize, or derive `fact_id`, `cumulative_duration_days`, and normalized comparisons, but must preserve the source linkage. If any required source field is missing, or more than one fact remains a plausible source, return `FactUnavailableError`/`FactAmbiguousError`; never infer a link from date proximity or equal value.
architecture-blueprint.md:779:- `FinancialFactService.fetch(ticker, as_of)` issues a structured-fact query through `DataAccessService`; the adapter returns per-fact records that preserve `subject_id`, `accession_no`, `filing_ref`, `filed_at`, `form`, `concept`, period/fiscal identity, `span`, `unit`, `currency`, `value`, `sign`, and restatement/supersession lineage. `FinancialFactService` validates/normalizes these records into `financial_fact`s; it never imports or calls a vendor module directly, and it never guesses a filing/fact link from date proximity or equal value.
architecture-blueprint.md:784:- A `financial_fact` records `fact_id`, `subject_id` (CIK or equivalent), `accession_no`, locatable `filing_ref`, concept, value, unit, currency, periods, fiscal year/quarter, span (annual/quarter/ytd/instant), cumulative duration, `filed_at`, source, sign convention, and restatement lineage.
docs/architecture/open-decisions.md:370:- **Recommendation (not approved)**: after the fundamentals report exists and before Bull/Bear; a `get_structured_financial_facts`-style query through `DataAccessService` returns per-fact records with subject/accession/filing_ref/filed_at/form/concept/period/span/unit/currency/sign and restatement lineage; `FinancialFactService` validates/normalizes them; the existing statement tools use the same adapter/cache/counters. Missing or multiple plausible sources return unavailable/ambiguous; never guess from date proximity or equal value.

```

---

## Assistant (Build · DeepSeek Flash · 4.3s)

_Thinking:_

Good.

### Step 15: Check recovery/permanent verification boundary in ADR/runtime/invariants
Search "recovery snapshot hash" none. Good. But runtime POL-PUB step 9 "recovery_snapshot summary" okay.

Need update ADR 001/002 maybe "recovery snapshot hash" not present. Good.

### Step 16: Check memory ledger state timing in all docs
Search "committed projection" etc. Good.

Need update `docs/architecture/invariants.md` INV-A-08 inventory row now high-water; good. Need add ledger state table? Not necessary.

Need update `docs/architecture/trace-matrix.md` T-ARCH-40 ledger timing. Good.

### Step 17: Check no stale "highest committed" formula for allocation. Search "highest of committed". We fixed most; search.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"highest of committed\\|greater than the highest committed\\|greater than the current highest committed\\|max(committed\" architecture-blueprint.md docs/architecture || echo none; echo \"=== hash cycle wording ===\"; grep -rn \"terminal_manifest_hash\" architecture-blueprint.md docs/architecture || echo none; echo \"=== whole recovery lock ===\"; grep -rn \"RunOwnershipLock.protect\\|recovery critical section\" architecture-blueprint.md docs/architecture || echo none"
}
```

**Output:**
```
none
=== hash cycle wording ===
none
=== whole recovery lock ===
none

```

---

## Assistant (Build · DeepSeek Flash · 5.5s)

_Thinking:_

Good.

### Step 18: Final consistency checks
Need table consistency after all edits, refs, trace AC count, status, docs/req untouched. Also check all T-SCEN references 01..16, T-ARCH 01..40. Check no duplicate scenario IDs. Check ADR 002 component table includes PM/MemoryRecoveryCoordinator. Check runtime index includes new policies. Check open decisions blocking table includes 21-23. Check invariants inventory has 40 rows and no corruption.

Let's run.

**Tool: bash**

**Input:**
```json
{
  "command": "ruby -e '\nfiles = Dir[\"architecture-blueprint.md\"] + Dir[\"docs/architecture/**/*.md\"]\nfiles.each do |f|\n lines=File.readlines(f,chomp:true); i=0\n while i<lines.length\n  if lines[i].start_with?(\"|\")\n   block=[]; j=i\n   while j<lines.length && lines[j].start_with?(\"|\"); block<<[j+1,lines[j]]; j+=1; end\n   data=block.reject{|ln,l| l.gsub(/[|\\-: ]/,\"\").empty?}\n   if data.length>1\n    exp=data.first[1].split(\"|\",-1).length\n    data.each{|ln,l| c=l.split(\"|\",-1).length; puts \"#{f}:#{ln} cells=#{c} exp=#{exp}\" if c!=exp}\n   end\n   i=j\n  else; i+=1; end\n end\nend\n' | head -20; echo \"tables ok\"; echo \"=== refs ===\"; defined=$(grep -oE \"(ARCH|D2)-OD-[0-9]+\" docs/architecture/open-decisions.md | sort -u); for ref in $(grep -rhoE \"(ARCH|D2)-OD-[0-9]+\" architecture-blueprint.md docs/architecture | sort -u); do echo \"$defined\" | grep -qx \"$ref\" || echo \"UNDEFINED $ref\"; done; echo \"refs ok\"; echo \"=== trace ===\"; grep -cE '^\\| `(FR|INV|SB|SR|QR)-[0-9]+-AC[0-9]+`' docs/architecture/trace-matrix.md; echo \"=== no conflicts ===\"; grep -rn \"<<<<<<<\\|>>>>>>>\" architecture-blueprint.md docs/architecture || echo none"
}
```

**Output:**
```
tables ok
=== refs ===
refs ok
=== trace ===
111
=== no conflicts ===
none

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== scenario/arch ids ===\"; grep -oE \"T-SCEN-[0-9]+\" architecture-blueprint.md docs/architecture/trace-matrix.md docs/architecture/evaluation-table.md | sed 's/.*://' | sort -u | tr '\\n' ' '; echo; grep -oE \"T-ARCH-[0-9]+\" docs/architecture/trace-matrix.md | sort -u | tail -8; echo \"=== policy ids ===\"; grep -oE \"POL-[A-Z]+-[0-9]+\" docs/architecture/runtime-policy-catalog.md | sort -u | tail -15; echo \"=== open ids ===\"; grep -oE \"ARCH-OD-[0-9]+\" docs/architecture/open-decisions.md | sort -u | tail -8"
}
```

**Output:**
```
=== scenario/arch ids ===
T-SCEN-01 T-SCEN-02 T-SCEN-03 T-SCEN-04 T-SCEN-05 T-SCEN-06 T-SCEN-07 T-SCEN-08 T-SCEN-09 T-SCEN-10 T-SCEN-11 T-SCEN-12 T-SCEN-13 T-SCEN-14 T-SCEN-15 T-SCEN-16 
T-ARCH-33
T-ARCH-34
T-ARCH-35
T-ARCH-36
T-ARCH-37
T-ARCH-38
T-ARCH-39
T-ARCH-40
=== policy ids ===
POL-LOCK-01
POL-MEM-01
POL-PERF-01
POL-PERM-01
POL-PERM-02
POL-PRE-01
POL-PROPOSAL-01
POL-PUB-01
POL-PUB-02
POL-REC-01
POL-RED-01
POL-RISK-01
POL-RISK-02
POL-RISK-03
POL-SNAP-01
=== open ids ===
ARCH-OD-16
ARCH-OD-17
ARCH-OD-18
ARCH-OD-19
ARCH-OD-20
ARCH-OD-21
ARCH-OD-22
ARCH-OD-23

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== status ===\"; git status --short architecture-blueprint.md docs/architecture; echo \"=== req mtime ===\"; ls -la docs/req/requirements.yaml; echo \"=== headers ===\"; for f in architecture-blueprint.md docs/architecture/*.md docs/architecture/adr/*.md; do printf \"%-55s \" \"$f\"; sed -n '3p' \"$f\"; done"
}
```

**Output:**
```
=== status ===
 M architecture-blueprint.md
 M docs/architecture/adr/001-run-governance.md
 M docs/architecture/evaluation-table.md
 M docs/architecture/invariants.md
 M docs/architecture/memory-design.md
 M docs/architecture/open-decisions.md
 M docs/architecture/permission-model.md
 M docs/architecture/runtime-policy-catalog.md
 M docs/architecture/trace-matrix.md
?? docs/architecture/adr/002-full-scope-add-r.md
=== req mtime ===
-rw-r--r--@ 1 ichihann  staff  365262 11月 11 03:32 docs/req/requirements.yaml
=== headers ===
architecture-blueprint.md                               Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/evaluation-table.md                   Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/invariants.md                         Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/memory-design.md                      Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/open-decisions.md                     Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/permission-model.md                   Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/runtime-policy-catalog.md             Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/trace-matrix.md                       Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/adr/001-run-governance.md             Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/adr/002-full-scope-add-r.md           Status: **v0.2 — ADD-R round 2 draft / pending human review**  

```

---

## Assistant (Build · DeepSeek Flash · 3.3s)

_Thinking:_

Good. But need check policy IDs full list maybe POL-GATE etc missing from tail but likely present. Fine.

Need verify `T-ARCH-01..40` all present. We can check count.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -c \"^| \\`T-ARCH-\" docs/architecture/trace-matrix.md; grep -c \"^| \\`T-SCEN-\" docs/architecture/trace-matrix.md; echo \"=== invariants count ===\"; grep -c \"^| INV-A-\" docs/architecture/invariants.md; echo \"=== component rows ===\"; grep -c \"^| \\`.*\\` | \\`run/\" architecture-blueprint.md"
}
```

**Output:**
```
40
16
=== invariants count ===
40
=== component rows ===
40

```

---

## Assistant (Build · DeepSeek Flash · 3.4s)

_Thinking:_

Good.

Need check `docs/architecture/evaluation-table.md` scenario row 01..16 and measurement rows. Fine.

Potential issue: Open decisions ARCH-OD-23 recommendation mentions "binding contains no terminal-manifest hash..." good. But ARCH-OD-15 maybe still says "terminal candidate with binding, hashes of permanent snapshot and recovery snapshot"? Let's check.

**Tool: bash**

**Input:**
```json
{
  "command": "sed -n '/### ARCH-OD-15/,/### ARCH-OD-16/p' docs/architecture/open-decisions.md; sed -n '/### ARCH-OD-20/,/### ARCH-OD-21/p' docs/architecture/open-decisions.md"
}
```

**Output:**
```
### ARCH-OD-15 — Permanent snapshot staging, hashing, and post-commit diagnostics

- **Status**: open; **blocking before publication implementation**.
- **Question**: where are permanent-snapshot files staged before the terminal commit, how are their hashes bound into the terminal manifest, and where is the independent post-commit corruption diagnostic stored?
- **Impact**: `ArtifactPublisher`, `PublicationSnapshotStore`, `PublicationStatusReader`, history/export.
- **Recommendation (not approved)**: write all permanent-snapshot files under a per-run staging/publication directory, fsync/validate them, bind their hashes into the terminal candidate, and atomically commit the terminal manifest last. The snapshot is authoritative only after commit. A post-commit validation failure keeps the committed manifest immutable and writes a separate diagnostic record outside the formal decision/commit path.
- **Blocking phase**: before publication implementation.
- **Related**: FR-02, INV-01, FR-05.

### ARCH-OD-16 — Shared run lock, lease, takeover, and lock order
### ARCH-OD-20 — Memory reservation storage and format

- **Status**: open; **blocking before memory/recovery implementation**.
- **Question**: where is the persistent reservation history stored, and how does it atomically track the allocation high-water mark (including failed reservations) and derived commit projections?
- **Impact**: `MemoryReservationStore`, `MemoryService`, `RecoveryService`, `INV-01`, `INV-02`.
- **Recommendation (not approved)**: a lock-protected `memory/reservations.jsonl` ledger keyed by ticker/date/decision_id, recording entry_version, owner run_id, status reserved/committed/failed, and fencing token. It is authoritative for version allocation, not for decision content. The next version is `high_water + 1` over every historical allocation, including failed reservations; a failed version is never reissued; retries/recovery reuse their own reservation; recovery uses the original run_id/version/snapshot; `committed` is a derived projection from the terminal manifest, not a second commit condition. Repair replays the append-only allocation history and never resets the watermark or reissues failed versions. If a structured sidecar is rejected, the same fields must live in a structured Markdown metadata line under the same lock.
- **Blocking phase**: before memory/recovery implementation.
- **Related**: INV-01, FR-06, D2-OD-06.

### ARCH-OD-21 — Portfolio Manager adapter and model-proposal source

```

---

## Assistant (Build · DeepSeek Flash · 3.6s)

_Thinking:_

ARCH-OD-15 recommendation doesn't explicitly hash DAG. Could add "no terminal-manifest hash inside binding; DAG per blueprint §9.6.5." Let's add.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/open-decisions.md')\ns=p.read_text()\ns=s.replace(\"- **Recommendation (not approved)**: write all permanent-snapshot files under a per-run staging/publication directory, fsync/validate them, bind their hashes into the terminal candidate, and atomically commit the terminal manifest last. The snapshot is authoritative only after commit. A post-commit validation failure keeps the committed manifest immutable and writes a separate diagnostic record outside the formal decision/commit path.\",\n\"- **Recommendation (not approved)**: write all permanent-snapshot files under a per-run staging/publication directory, fsync/validate them, bind their hashes into the terminal candidate, and atomically commit the terminal manifest last. The snapshot is authoritative only after commit. The hash DAG in blueprint §9.6.5 is acyclic: `binding.json` has no terminal-manifest hash; the manifest hashes permanent files; no hashed file contains the manifest hash. A post-commit validation failure keeps the committed manifest immutable and writes a separate diagnostic record outside the formal decision/commit path.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.0s)

_Thinking:_

Need update runtime POL-SNAP maybe hash DAG already. Good.

Need update `docs/architecture/evaluation-table.md` measurement row "Permanent hash DAG" perhaps already added. Check.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -n \"Permanent hash DAG\\|Ledger commit\\|Failed version\\|Commit/ledger\" docs/architecture/evaluation-table.md"
}
```

**Output:**
```
255:| Ledger commit projection | Commit/ledger interruption, rebuild from manifest, failed allocation preservation | not started |
256:| Permanent hash DAG | binding no terminal hash; no cycles; declared order | not started |

```

---

## Assistant (Build · DeepSeek Flash · 3.6s)

_Thinking:_

Good.

Need update `docs/architecture/trace-matrix.md` FR-02/FR-06/FR-07/FR-08 rows for new things? T-SCEN/T-ARCH cover. Fine.

Potential issue: `docs/architecture/invariants.md` INV-A-40 inventory row now correct; table check passed. Good.

Potential issue: `docs/architecture/memory-design.md` §7 table has "committed projection" okay.

Potential issue: `docs/architecture/runtime-policy-catalog.md` POL-MEM says "committed projection is derived" but state timing? It says "the allocation ledger appends reserved before... failed... committed projection only after..."? We added to POL-PUB not POL-MEM? Let's check POL-PUB.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -n \"reserved.*recovery snapshot\\|failed.*completed\\|committed.*projection\" docs/architecture/runtime-policy-catalog.md | head -20"
}
```

**Output:**
```
212:  - memory remains pending/unreadable until commit; the allocation ledger appends `reserved` before the recovery snapshot, `failed` on abort before a completed manifest, and a rebuildable `committed` projection only after commit plus read verification; ledger write failure after commit does not block the manifest authority;
289:  - `MemoryReservationStore` is a persistent, append-only allocation history; the next version is `high_water + 1` over **all** historical allocations, including failed reservations; a failed version is never reissued; retries/recovery reuse their own reservation; `committed` is a derived projection from the terminal manifest, not a second commit condition;
292:  - memory-disabled runs require no memory artifact; the ledger's `committed` projection is derived from terminal manifests, not a second commit condition;

```

---

## Assistant (Build · DeepSeek Flash · 4.0s)

_Thinking:_

Good.

Need update `docs/architecture/adr/002` memory section with high-water/ledger state? ADR 002 §2.6 is uncommitted same-decision, not ledger formula. Add a bullet in §2.2 or 2.6 about ledger high-water/commit projection? ADR 001 bullet updated. ADR 002 risk table has high-water. Maybe add to §2.2 or 2.6:
- "MemoryReservationStore allocation history includes failed; committed projection derived." Let's add in §2.6.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/adr/002-full-scope-add-r.md')\ns=p.read_text()\ns=s.replace(\"- B may reuse A only after A commits and validates, through `reused_decision_ref`; B never writes a duplicate entry or takes A's version.\",\n\"- B may reuse A only after A commits and validates, through `reused_decision_ref`; B never writes a duplicate entry or takes A's version.\\n- `MemoryReservationStore` keeps a persistent high-water mark over all historical allocations, including failed reservations; a failed version is never reissued. `committed` is a derived projection from the terminal manifest, not a second commit condition.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.5s)

_Thinking:_

Need update ADR 001 maybe PM/ledger/hash. Already PM, lock, cleanup, brief, uncommitted. Ledger high-water? It says "persistent, append-only allocation history..." yes we updated earlier. Good.

Need check ADR 001 hash DAG bullet. Yes.

### Step 19: Check recovery flow scenario consistency after changes
- §11.3 recovery now reads/renders outside lock, then short lock; T-SCEN-04/13/15/16 cover.
- §12.6 "Shared claim, lock, fencing" still says "Recovery claims atomically per run_id" and "stale claim/lock may be taken over after lease expiry"; fine.
- Runtime POL-REC says "claim/fencing" but not lock-external prep. Could add bullet. Let's add to POL-REC: "long reads/parsing/render outside lock; protected writes short".

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/runtime-policy-catalog.md')\ns=p.read_text()\ns=s.replace(\"- **Claim/fencing**: uses the same `RunOwnershipLock` as normal publication; atomic per `run_id`; owner + fencing token; one active worker; stale lease reclaim increments the token; ownership/fencing is checked in the same critical section as each protected write; lost-lease writes rejected; failure isolated; retries bounded; at most one committed publication. Lock order is run lock then memory lock.\",\n\"- **Claim/fencing**: uses the same `RunOwnershipLock` as normal publication; atomic per `run_id`; owner + fencing token; one active worker; stale lease reclaim increments the token; ownership/fencing is checked in the same critical section as each protected write; lost-lease writes rejected; failure isolated; retries bounded; at most one committed publication. Lock order is run lock then memory lock.\\n- **Lock-external preparation**: reads, parsing, rendering, and hashing run outside the locks; staged content is revalidated against current ownership/publication state inside the short critical section before use.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.1s)

_Thinking:_

Need update invariant INV-A-28 maybe "recovery uses saved records only" fine. Add lock-external prep? INV-A-35 covers.

### Step 20: Check brief state branch in §16.3 and all docs
We fixed. Search "otherwise use the role's normal" none. Good.

### Step 21: Check hash DAG in trace/ADR/open.
Need add T-ARCH-39 to verification summary? It's in trace. Good.

### Step 22: Check memory ledger state table and scenario T-SCEN-15/16 in trace/eval/blueprint. Good.

### Step 23: Check all docs use same scenario count 16. Search T-SCEN-01..16.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"T-SCEN-01\\.\\.\\|T-SCEN-01`\\.\\.\\|T-SCEN-01\\`\\.\\.\" architecture-blueprint.md docs/architecture | head -20; grep -rn \"T-ARCH-01\\.\\.\" architecture-blueprint.md docs/architecture | head -10"
}
```

**Output:**
```
zsh:1: unmatched "

```

---

## Assistant (Build · DeepSeek Flash · 3.0s)

_Thinking:_

Quote issue. Use grep simpler.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"T-SCEN-01\" architecture-blueprint.md docs/architecture | tail -10; grep -rn \"T-ARCH-01\" docs/architecture | tail -10"
}
```

**Output:**
```
architecture-blueprint.md:1044:| Normal pass | Complete coverage, stock Buy/Overweight risk passes; formal rating unchanged; publication commits once; history visible after post-commit validation | `T-SCEN-01`: end-to-end fixture with fixed replay, query counters, risk boundary pass, manifest/INV-01, permanent snapshot, recovery snapshot, memory idempotency, read-back |
architecture-blueprint.md:1251:The end-to-end scenario tests `T-SCEN-01`..`T-SCEN-16` in §13.2 cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, and commit/ledger-update interruption.
docs/architecture/evaluation-table.md:252:| Scenario matrix T-SCEN-01..16 | Normal, business block, system error, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export, cleanup-after-read, brief failure, uncommitted-memory coordination, old-process lock/lease, PM proposal source, failed-version retry, commit/ledger-update interruption | not started |
docs/architecture/trace-matrix.md:253:Additional scenario tests: `T-SCEN-01`..`T-SCEN-16` (16 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-40`, not started.
docs/architecture/trace-matrix.md:259:| `T-SCEN-01` | Normal pass: coverage complete, risk passes, one commit, snapshots, memory idempotency, post-commit read | not started |
docs/architecture/trace-matrix.md:354:- The scenario tests `T-SCEN-01`..`T-SCEN-16` cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, and commit/ledger-update interruption. They are planned, not executed.
docs/architecture/trace-matrix.md:253:Additional scenario tests: `T-SCEN-01`..`T-SCEN-16` (16 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-40`, not started.
docs/architecture/trace-matrix.md:280:| `T-ARCH-01` | writer bypass audit | not started |

```

---

## Assistant (Build · DeepSeek Flash · 4.8s)

_Thinking:_

Good.

### Step 24: Check table consistency and refs final, docs/req untouched.

**Tool: bash**

**Input:**
```json
{
  "command": "ruby -e '\nfiles = Dir[\"architecture-blueprint.md\"] + Dir[\"docs/architecture/**/*.md\"]\nfiles.each do |f|\n lines=File.readlines(f,chomp:true); i=0\n while i<lines.length\n  if lines[i].start_with?(\"|\")\n   block=[]; j=i\n   while j<lines.length && lines[j].start_with?(\"|\"); block<<[j+1,lines[j]]; j+=1; end\n   data=block.reject{|ln,l| l.gsub(/[|\\-: ]/,\"\").empty?}\n   if data.length>1\n    exp=data.first[1].split(\"|\",-1).length\n    data.each{|ln,l| c=l.split(\"|\",-1).length; puts \"#{f}:#{ln} cells=#{c} exp=#{exp}\" if c!=exp}\n   end\n   i=j\n  else; i+=1; end\n end\nend\n' | head -20; echo \"tables ok\"; echo \"=== refs ===\"; defined=$(grep -oE \"(ARCH|D2)-OD-[0-9]+\" docs/architecture/open-decisions.md | sort -u); for ref in $(grep -rhoE \"(ARCH|D2)-OD-[0-9]+\" architecture-blueprint.md docs/architecture | sort -u); do echo \"$defined\" | grep -qx \"$ref\" || echo \"UNDEFINED $ref\"; done; echo \"refs ok\"; echo \"=== trace ===\"; grep -cE '^\\| `(FR|INV|SB|SR|QR)-[0-9]+-AC[0-9]+`' docs/architecture/trace-matrix.md; echo \"=== no conflict ===\"; grep -rn \"<<<<<<<\\|>>>>>>>\" architecture-blueprint.md docs/architecture || echo none"
}
```

**Output:**
```
tables ok
=== refs ===
refs ok
=== trace ===
111
=== no conflict ===
none

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== stale formulas/phrases ===\"; grep -rn \"reserved-uncommitted\\|highest of committed and reserved\\|RunOwnershipLock.protect\\|recovery critical section\\|terminal_manifest_hash\\|completed (analysis)\\|wait.*takes over\" architecture-blueprint.md docs/architecture || echo none; echo \"=== status ===\"; git status --short architecture-blueprint.md docs/architecture; echo \"=== req mtime ===\"; ls -la docs/req/requirements.yaml"
}
```

**Output:**
```
=== stale formulas/phrases ===
none
=== status ===
 M architecture-blueprint.md
 M docs/architecture/adr/001-run-governance.md
 M docs/architecture/evaluation-table.md
 M docs/architecture/invariants.md
 M docs/architecture/memory-design.md
 M docs/architecture/open-decisions.md
 M docs/architecture/permission-model.md
 M docs/architecture/runtime-policy-catalog.md
 M docs/architecture/trace-matrix.md
?? docs/architecture/adr/002-full-scope-add-r.md
=== req mtime ===
-rw-r--r--@ 1 ichihann  staff  365262 11月 11 03:32 docs/req/requirements.yaml

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== key terms ===\"; for t in \"high_water\" \"BRIEF_DISABLED\" \"BRIEF_FULL_REPORT\" \"BRIEF_REJECTED\" \"MemoryRecoveryCoordinator\" \"commit_evidence.json\" \"restates_fact_id\" \"LOCK_BUSY\"; do printf \"%-26s %s\\n\" \"$t\" \"$(grep -rl \"$t\" architecture-blueprint.md docs/architecture | wc -l | tr -d ' ') files\"; done"
}
```

**Output:**
```
=== key terms ===
high_water                 5 files
BRIEF_DISABLED             6 files
BRIEF_FULL_REPORT          6 files
BRIEF_REJECTED             7 files
MemoryRecoveryCoordinator  8 files
commit_evidence.json       5 files
restates_fact_id           1 files
LOCK_BUSY                  7 files

```

---

## Assistant (Build · DeepSeek Flash · 4.7s)

_Thinking:_

`restates_fact_id` only blueprint; should be in ADR/runtime/invariants maybe "restatement lineage" wording covers. Fine.

### Step 25: Verify recovery flow and §12.5/12.6 consistency
Potential issue: §11.3 says "promote staged permanent files; write terminal manifest; atomically commit" in short lock; §12.5 step 8 says "Write and validate all permanent publication snapshot files before terminal commit"; step 11 "Enter RunOwnershipLock ... atomically replace". It doesn't mention staging outside lock, but okay. Could add "staged outside lock, promoted inside short lock" to §12.5 step 8/11. The user wants explicit. Let's add:
- Step 8: "stage under owner-specific directory; validate; promotion happens in the commit critical section."
- Step 11: "re-check ownership and staged content still applies; promote staged files and atomically commit."
Let's edit.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"8. Write and validate all permanent publication snapshot files **before the terminal commit**: complete report, section manifest, final-state, risk evidence/policy references, metric bundle when applicable, memory entry/binding, versions, and hashes. The snapshot is not authoritative until the terminal manifest commits.\",\n\"8. Stage and validate all permanent publication snapshot files **before the terminal commit** in an owner-specific staging directory: complete report, section manifest, final-state, risk evidence/policy references, metric bundle when applicable, memory entry/binding, versions, and hashes. The snapshot is not authoritative until the terminal manifest commits; promotion happens in the commit critical section.\")\ns=s.replace(\"11. Enter `RunOwnershipLock` for the `run_id`; re-check owner/fencing inside the same critical section; atomically replace the running manifest with the terminal manifest. This is the only commit point.\",\n\"11. Enter `RunOwnershipLock.critical_section` for the `run_id`; re-check owner/fencing and that the staged content still applies to the current publication state; promote staged permanent files; atomically replace the running manifest with the terminal manifest. This is the only commit point.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.1s)

_Thinking:_

Update runtime POL-PUB step order maybe "sections -> memory plan..." doesn't mention staging. Add "stage outside lock; promote in short commit".

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/runtime-policy-catalog.md')\ns=p.read_text()\ns=s.replace(\"  - permanent-snapshot files are written/validated before commit and are authoritative only after commit; the permanent snapshot is never created after cleanup;\",\n\"  - permanent-snapshot files are staged/validated outside the lock before commit, then promoted in the short commit critical section; they are authoritative only after commit; the permanent snapshot is never created after cleanup;\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.1s)

_Thinking:_

Update ADR 002/001 maybe "recovery long prep outside lock". ADR 001 bullet says ownership checked; not explicit. Add to ADR 001? Maybe not necessary, but cross-doc consistency. Add a bullet to ADR 001:
- "Recovery does long reads/parsing/rendering outside locks; short lock only for claim/state/protected writes; staged content revalidated." Let's add.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/adr/001-run-governance.md')\ns=p.read_text()\ns=s.replace(\"- Normal publication and recovery share one `RunOwnershipLock`, owner identity, and fencing token. The OS file lock is short-lived; the logical lease records activity. Ownership is checked in the same critical section as the protected write; takeover acquires the file lock and increments fencing; lease expiry does not release the file lock. The lock order is run lock then memory lock.\",\n\"- Normal publication and recovery share one `RunOwnershipLock`, owner identity, and fencing token. The OS file lock is short-lived; the logical lease records activity. Ownership is checked in the same critical section as the protected write; takeover acquires the file lock and increments fencing; lease expiry does not release the file lock. The lock order is run lock then memory lock. Recovery reads/parses/renders outside the locks; staged content is revalidated against current ownership/publication state before use.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.4s)

_Thinking:_

### Step 26: Check invariants INV-A-35 says "file lock short"; good.
Need maybe update INV-A-28/29 recovery to mention lock-external prep? INV-A-35 enough.

### Step 27: Check no duplicate "recovery snapshot hash" in terminal manifest. Search "recovery.*hash".

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"recovery snapshot hash\\|recovery-snapshot hash\\|hashes of.*recovery\\|every referenced file\" architecture-blueprint.md docs/architecture || echo none; grep -rn \"publication_ref\" architecture-blueprint.md docs/architecture | head -20"
}
```

**Output:**
```
architecture-blueprint.md:524:| `record.json` | Canonical `FinalizedRunRecord` content and `artifact_binding` fields | Run-level generated/evaluated/finished timestamps, local paths, cache counters, terminal-manifest hash, recovery-snapshot hash | 1 |
architecture-blueprint.md:459:- `publication_ref` = `{root: "publication", files: [{relative_path, sha256, hash_scope: "file"}], record_hash}`; it contains no terminal-manifest hash. All paths are relative and confined.
architecture-blueprint.md:529:| terminal `run_manifest.json` | `publication_ref.files` hashes (including `binding.json`), formal decision, security scans, section manifest, metric bundle, memory binding, and `recovery_snapshot_summary` (audit-only) | Its own hash; any file that contains its hash; optional commit-evidence hash | 5 |
architecture-blueprint.md:909:9. Build the terminal manifest candidate with binding, formal decision, security scans, section manifest, metric bundle, risk evidence, memory binding, and `publication_ref` hashes. If desired, include a `recovery_snapshot_summary` (status/digest/created-at) as audit-only; no terminal-manifest hash is written into `binding.json` or any file hashed by the manifest.
docs/architecture/adr/002-full-scope-add-r.md:62:- Permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; optional `diagnostics/commit_evidence.json` is audit-only.
docs/architecture/invariants.md:429:- **Statement**: Permanent artifacts form a directed acyclic hash graph. `record_hash` is computed first; `binding.json` covers `artifact_binding` plus `record_hash` but excludes the terminal-manifest hash, its own file hash, the recovery digest, and commit-evidence hash. Section/final-state/risk/metric/memory files are hashed next. The recovery snapshot may carry terminal-candidate identity but not the final terminal-manifest hash. The terminal manifest covers `publication_ref` hashes (including `binding.json`) and may hold a `recovery_snapshot_summary` as audit-only; it never hashes itself. An optional `diagnostics/commit_evidence.json` may record the terminal-manifest hash after commit but is outside the permanent hashed set and is not a commit authority.
docs/architecture/runtime-policy-catalog.md:210:  - permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; an optional `diagnostics/commit_evidence.json` is audit-only;

```

---

## Assistant (Build · DeepSeek Flash · 6.5s)

_Thinking:_

Good; "recovery-snapshot hash" only as excluded field in record.json, fine.

### Step 28: Check `binding.json` comment no manifest hash. Good.

### Step 29: Check SEC per-fact contract with source ownership in runtime ADR. Good.

### Step 30: Check brief state branch no generic fallback. Good.

### Step 31: Check memory ledger state transitions and scenario T-SCEN-15/16. Good.

### Step 32: Check all docs use same scenario count and trace count. Good.

### Step 33: Check "approved obligations" boundary still consistent after new edits. Good.

### Step 34: Potential issue: `docs/architecture/adr/002` §2.6 says "MemoryReservationStore keeps high-water..." good.

### Step 35: Update evaluation table maybe "Memory reservation" row now high-water; yes. "Ledger commit projection" row. Good.

### Step 36: Update trace T-ARCH-24/38 high-water; done.

### Step 37: Update `docs/architecture/runtime-policy-catalog.md` §6 implementation blockers includes ARCH-OD-21/22; good.

### Step 38: Check open decisions blocking summary includes ARCH-OD-23 etc; yes.

### Step 39: Check table consistency after latest edits.

**Tool: bash**

**Input:**
```json
{
  "command": "ruby -e '\nfiles = Dir[\"architecture-blueprint.md\"] + Dir[\"docs/architecture/**/*.md\"]\nfiles.each do |f|\n lines=File.readlines(f,chomp:true); i=0\n while i<lines.length\n  if lines[i].start_with?(\"|\")\n   block=[]; j=i\n   while j<lines.length && lines[j].start_with?(\"|\"); block<<[j+1,lines[j]]; j+=1; end\n   data=block.reject{|ln,l| l.gsub(/[|\\-: ]/,\"\").empty?}\n   if data.length>1\n    exp=data.first[1].split(\"|\",-1).length\n    data.each{|ln,l| c=l.split(\"|\",-1).length; puts \"#{f}:#{ln} cells=#{c} exp=#{exp}\" if c!=exp}\n   end\n   i=j\n  else; i+=1; end\n end\nend\n' | head -20; echo \"tables ok\"; echo \"=== refs ===\"; defined=$(grep -oE \"(ARCH|D2)-OD-[0-9]+\" docs/architecture/open-decisions.md | sort -u); for ref in $(grep -rhoE \"(ARCH|D2)-OD-[0-9]+\" architecture-blueprint.md docs/architecture | sort -u); do echo \"$defined\" | grep -qx \"$ref\" || echo \"UNDEFINED $ref\"; done; echo \"refs ok\"; echo \"=== trace ===\"; grep -cE '^\\| `(FR|INV|SB|SR|QR)-[0-9]+-AC[0-9]+`' docs/architecture/trace-matrix.md; echo \"=== no conflict ===\"; grep -rn \"<<<<<<<\\|>>>>>>>\" architecture-blueprint.md docs/architecture || echo none"
}
```

**Output:**
```
tables ok
=== refs ===
refs ok
=== trace ===
111
=== no conflict ===
none

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== stale ===\"; grep -rn \"reserved-uncommitted\\|highest of committed and reserved\\|RunOwnershipLock.protect\\|recovery critical section\\|terminal_manifest_hash\\|completed (analysis)\\|wait.*takes over\\|otherwise use the role's normal\" architecture-blueprint.md docs/architecture || echo none; echo \"=== status ===\"; git status --short architecture-blueprint.md docs/architecture; echo \"=== req mtime ===\"; ls -la docs/req/requirements.yaml"
}
```

**Output:**
```
=== stale ===
none
=== status ===
 M architecture-blueprint.md
 M docs/architecture/adr/001-run-governance.md
 M docs/architecture/evaluation-table.md
 M docs/architecture/invariants.md
 M docs/architecture/memory-design.md
 M docs/architecture/open-decisions.md
 M docs/architecture/permission-model.md
 M docs/architecture/runtime-policy-catalog.md
 M docs/architecture/trace-matrix.md
?? docs/architecture/adr/002-full-scope-add-r.md
=== req mtime ===
-rw-r--r--@ 1 ichihann  staff  365262 11月 11 03:32 docs/req/requirements.yaml

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== counts ===\"; printf \"AC rows: \"; grep -cE '^\\| `(FR|INV|SB|SR|QR)-[0-9]+-AC[0-9]+`' docs/architecture/trace-matrix.md; printf \"invariants: \"; grep -c \"^| INV-A-\" docs/architecture/invariants.md; printf \"arch tests: \"; grep -c \"^| \\`T-ARCH-\" docs/architecture/trace-matrix.md; printf \"scenario tests: \"; grep -c \"^| \\`T-SCEN-\" docs/architecture/trace-matrix.md; echo \"=== headers ===\"; for f in architecture-blueprint.md docs/architecture/*.md docs/architecture/adr/*.md; do printf \"%-55s \" \"$f\"; sed -n '3p' \"$f\"; done"
}
```

**Output:**
```
=== counts ===
AC rows: 111
invariants: 40
arch tests: 40
scenario tests: 16
=== headers ===
architecture-blueprint.md                               Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/evaluation-table.md                   Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/invariants.md                         Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/memory-design.md                      Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/open-decisions.md                     Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/permission-model.md                   Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/runtime-policy-catalog.md             Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/trace-matrix.md                       Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/adr/001-run-governance.md             Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/adr/002-full-scope-add-r.md           Status: **v0.2 — ADD-R round 2 draft / pending human review**  

```

---

## Assistant (Build · DeepSeek Flash · 4.5s)

_Thinking:_

All good.

Need maybe update `docs/architecture/adr/002` §2.5/2.6 and component table references to new hash DAG etc. It has hash DAG bullet. Good.

Need update `docs/architecture/invariants.md` INV-A-40 inventory row; done.

Need check `docs/architecture/open-decisions.md` ARCH-OD-23 etc. Good.

Potential issue: `docs/architecture/evaluation-table.md` "Scenario matrix T-SCEN-01..16" row; good.

Potential issue: `docs/architecture/trace-matrix.md` T-ARCH-35 description per-fact; good.

Potential issue: `docs/architecture/runtime-policy-catalog.md` index has POL-SNAP-01/POL-PROPOSAL-01; check sections. Good.

Potential issue: `docs/architecture/permission-model.md` may still say "Brief unavailable/rejected" no; fine.

Potential issue: The user asked "不要只在文档开头添加已修复说明" — we did substantial edits throughout, plus §1.3. Fine.

Now, maybe need update blueprint §1.3 item 16 "concrete implementation-start proposals" to include hash DAG? It says snapshot layout/lock/lease/reservation/SEC query; add hash DAG. Let's update item 16.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"16. Concrete implementation-start proposals are recorded for snapshot layout, lock/lease records, memory reservation authority, and the SEC structured query contract; they are proposals pending review, not approvals.\",\n\"16. Concrete implementation-start proposals are recorded for snapshot layout, the acyclic hash DAG, lock/lease records and state transitions, memory reservation authority/replay, and the per-fact SEC structured query contract; they are proposals pending review, not approvals.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 14.7s)

_Thinking:_

Need update §9.6 intro maybe "These are reviewable proposals" good.

Potential issue: `docs/architecture/memory-design.md` §7 table uses `reserved`, `failed`, `committed`; good.

Potential issue: `docs/architecture/runtime-policy-catalog.md` POL-MEM state timing maybe okay.

Potential issue: `docs/architecture/invariants.md` INV-A-08 statement now says "high_water + 1" but not "committed projection derived"; it includes. Good.

Potential issue: `docs/architecture/trace-matrix.md` FR-06-AC1 etc may not mention ledger state; T-SCEN-16 covers. Fine.

Potential issue: `docs/architecture/evaluation-table.md` "Memory reservation" row high-water; good.

Potential issue: `docs/architecture/open-decisions.md` ARCH-OD-20 question high-water; good.

Now final report. But before, maybe run one final `git diff --stat` and no docs/req changes. Also maybe check no accidental `A`/`D` status for docs/architecture. Good.

Let me also check `docs/architecture/adr/002` status and content for "binding no terminal hash". Good.

Need mention no tests/implementation run.

Final answer in Chinese:
- 修复内容 (brief branches, recovery flow/lock, memory high-water/ledger, hash DAG, SEC per-fact, temporary/permanent boundary, approved boundary, scenario/verification).
- 修改文件.
- 静态核对.
- 仍需人工决定 (implementation blockers vs acceptance-only, approval coupling, evidence/CI).
Be concise but complete. No claim of tests. Mention docs/req untouched.

Let's craft.

本轮仅修改 `architecture-blueprint.md` 与 `docs/architecture/`，未改 `docs/req/`、`TradingAgents/`、`baseline/` 或其他目录；`docs/req/requirements.yaml` mtime 未变。

## 修复内容

1. **摘要上下文状态分支**
   - 删除“没有有效摘要就进入普通输入路径”的笼统规则。
   - 统一为四态：`BRIEF_DISABLED` 使用原有完整输入；`BRIEF_OK` 使用摘要；`BRIEF_FULL_REPORT` 仅在策略明确允许、mandatory 内容完整且符合上下文硬上限时使用；`BRIEF_REJECTED` 终止五角色上下文阶段。
   - `BRIEF_REJECTED` 后禁止重新进入普通输入或通用压缩绕过拒绝；运行在 context 阶段 fail closed。
   - 同步修正上下文组装步骤、行为表、错误契约、运行策略、不变量、验证场景 `T-SCEN-11`。

2. **恢复流程图与锁范围**
   - 删除覆盖整个恢复过程的 `RunOwnershipLock.protect` 表述。
   - 恢复流程改为：短锁内 claim/读取 lease 与当前发布状态 → 锁外读取/解析/渲染/哈希/暂存 → 短锁内重查 owner/fencing 与暂存内容适用性 → 幂等记忆写入、永久文件提升、终态提交 → 锁外 post-commit 读取验证 → 短锁内清理自己的临时材料。
   - 明确锁外准备内容在使用前必须重新校验当前所有权与发布状态；旧所有者接管后无法继续写入。
   - 保持 run lock → memory lock 顺序；等待其他运行时不得持锁。
   - 接口从 `RunOwnershipLock.protect` 改为 `RunOwnershipLock.critical_section`，避免被理解为覆盖整个恢复过程。

3. **记忆版本分配与账本**
   - 改为持久化 **high-water mark over all historical allocations**，失败预留永久占用版本，不因 `failed` 退出高水位。
   - 新运行只能获得更高版本；原运行重试/恢复只能复用自己的预留。
   - 明确 `reserved`、`failed`、`committed` 的写入时机：
     - `reserved`：恢复快照前；
     - `failed`：未形成 completed 终态前中止；
     - `committed`：终态提交并通过 read-time `INV-01` 后追加的派生投影。
   - 终态清单仍是唯一发布权威；账本 `committed` 只是可核对、可重建的投影，不是第二提交条件。
   - 增加账本重放/修复规则：不得只从已提交 manifest 重建分配历史，不得丢失失败预留或重新发号。
   - 增加 `T-SCEN-15`（最高版本失败、新运行分配、旧运行重试）和 `T-SCEN-16`（提交与账本更新之间中断）。

4. **永久快照、binding 与终态清单的无环哈希**
   - 修正 `publication_ref`，不再包含 `terminal_manifest_hash`。
   - `binding.json` 只覆盖 `artifact_binding` 与 `record_hash`，明确排除终态清单哈希、自身文件哈希、恢复快照摘要和 commit-evidence 哈希。
   - 新增 §9.6.5 哈希 DAG 表，列出每个摘要覆盖/排除的字段与计算顺序。
   - 终态清单单向绑定提交前固定的永久产物；如需终态清单摘要，放入 `diagnostics/commit_evidence.json` 作为 audit-only，不形成第二提交权威，也不要求提交后改写正式文件。
   - 新增 `INV-A-40`、`T-ARCH-39`。

5. **SEC 逐事实来源契约**
   - `SecEdgarAdapter` 输出改为逐事实记录，每个 fact 自带 `subject_id`、`accession_no`、`filing_ref`、`filed_at`、`form`、`concept`、period/fiscal identity、`span`、`unit`、`currency`、`value`、`sign`、`restates_fact_id`/`supersedes`、`source_fact_ref`。
   - 明确原始 SEC 数据与规范化服务的字段责任；缺失或多个合理来源返回 `FactUnavailableError`/`FactAmbiguousError`。
   - 禁止按日期接近或数值相同猜测 filing/fact 关联。
   - 同步 `INV-A-30`、运行策略 `POL-FIN-01`、ADR 002、ARCH-OD-19、追踪矩阵 `T-ARCH-35`。

6. **临时恢复材料与永久验证依赖**
   - 提交前只验证自包含恢复材料与永久候选；正式 `INV-01`、历史读取、记忆绑定、`verified_package` 只依赖永久 `publication/` 与终态 manifest。
   - 终态清单如保留 `recovery_snapshot_summary`，明确为 audit-only。
   - 清理 `recovery/` 后，历史读取、记忆绑定验证和导出仍必须成功；`T-SCEN-10`/`INV-A-37` 已覆盖。

7. **批准义务与草案边界**
   - 明确 `FR-02` 的 recovery-snapshot 生成、section manifest、终态 manifest、binding 属于批准义务，不能因 `FR-05/FR-06` 是草案而设为可选。
   - `FR-06` 启动扫描仍为后续能力；`FR-02` 恢复快照生成与启动扫描分开。
   - `INV-01` binding/read-time 验证、`SB-01` 风险分支行为保持必需。
   - 草案状态只限制完成/验收声明，不降低批准行为，也不宣布草案获批。

8. **实施设计具体化**
   - 蓝图 §9.6 已给出 `publication/`、`recovery/`、`locks/`、`diagnostics/` 布局、`run.lock`/`lease.json` 状态转换、`memory/reservations.jsonl` 权威性与修复规则、SEC 查询输入输出契约、哈希 DAG。
   - 区分实现启动阻塞项、验收-only 阈值、证据/CI 阻塞项。

## 修改文件

修改：
- `architecture-blueprint.md`
- `docs/architecture/adr/001-run-governance.md`
- `docs/architecture/evaluation-table.md`
- `docs/architecture/invariants.md`
- `docs/architecture/memory-design.md`
- `docs/architecture/open-decisions.md`
- `docs/architecture/permission-model.md`
- `docs/architecture/runtime-policy-catalog.md`
- `docs/architecture/trace-matrix.md`

新增：
- `docs/architecture/adr/002-full-scope-add-r.md`

## 场景推演与验证计划

已统一覆盖：

- 正常发布：`T-SCEN-01`
- 摘要最终拒绝：`T-SCEN-11`
- 恢复接管：`T-SCEN-13`
- 失败版本重试：`T-SCEN-15`
- 提交与账本更新之间中断：`T-SCEN-16`
- 临时材料清理后读取：`T-SCEN-10`
- 并发同决策/未提交记忆：`T-SCEN-12`
- 旧进程暂停：`T-SCEN-13`

新增架构测试 `T-ARCH-38..40`，覆盖高水位/失败版本、哈希 DAG、账本提交投影修复。

## 静态核对结果

- `trace-matrix.md` 仍覆盖 **111/111** 条验收条件。
- 不变量 40 条；架构测试 40 条；场景测试 16 条。
- 所有 `ARCH-OD-*` / `D2-OD-*` 引用均有定义。
- 所有 Markdown 表格列数一致；无冲突标记。
- 所有架构文档保持 `v0.2 — ADD-R round 2 draft / pending human review`。
- 未修改 `docs/req/`、应用代码或 `baseline/`；未声称实现、测试或批准结果。

## 仍需人工决定

**实现启动阻塞项：**
- `OQ-09` 风险输入来源
- `ARCH-OD-03` 风险 policy 定位/审批记录
- `ARCH-OD-16` 锁/租约格式、TTL、接管条件
- `ARCH-OD-15/23` 永久/恢复快照布局与哈希边界
- `ARCH-OD-20` 记忆预留历史格式/权威性
- `ARCH-OD-19` SEC 逐事实查询契约
- `ARCH-OD-21` Portfolio Manager 适配器/model_proposal 来源
- `ARCH-OD-22` 未提交记忆协调超时/状态
- `ARCH-OD-04` tokenizer/model
- `OQ-14` 非 NVDA 参考 manifest（FR-07 实现）

**仅影响验收：**
- `OQ-10` 风险阈值/policy 的 approved 声明（有效 provisional 路径可用）
- `OQ-13` QR-02 目标/平台
- `OQ-16` 摘要预算/质量阈值
- `D2-OD-09` 行为评估快照/人工批准
- `OQ-05` manifest overhead

**证据/CI 阻塞：**
- `ARCH-OD-01` `yhx/requirements.yaml` 缺失
- `ARCH-OD-02` validator 依赖未声明

**审批范围：**
- `ARCH-OD-13/14`：approved `SB-01`/`FR-02`/`INV-01` 与 draft 细节的耦合仍需人工决定；当前文档只限制完成/验收声明，不降低批准义务，也不宣布草案获批。

---

## User

请只修改 `/Users/ichihann/Desktop/CS5351/Teamproject-tradingagents/architecture-blueprint.md` 和 `docs/architecture/` 下的相关架构文档，修复以下三个问题，不要修改需求文件、TradingAgents原版代码、baseline或其他目录。先核对当前内容，保留已经正确的设计，同步所有受影响的流程、接口、不变量、运行策略和验证计划，不要仅添加“已修复”的说明。

首先调整恢复流程的检查顺序。恢复时先读取终态清单并验证永久发布：已提交、验证通过且内容身份匹配时直接返回幂等成功，不再要求临时恢复快照存在；已提交但身份冲突或永久产物损坏时，分别返回明确的冲突或损坏结果，不能覆盖终态清单或自动重新发布。只有尚未提交、确实需要继续发布的记录才读取并验证恢复快照。同步修正流程图和配套说明，增加“成功发布并清理恢复目录后再次调用恢复”及“已提交产物损坏”的计划验证场景。

其次明确record_hash的字段级计算投影。在计算前显式排除artifact_binding.record_hash以及其他承载该计算结果的字段，禁止通过序列化已填入自身摘要的完整记录计算record_hash。明确区分规范内容摘要与文件字节哈希，按“构建规范内容、计算record_hash、填入绑定、序列化文件、计算文件哈希、生成终态清单”的顺序处理，检查所有摘要引用仍构成无环依赖。时间戳排除规则应逐项与当前需求对齐，只排除需求规定的易变运行字段，保留风险评估和来源证据中必须保留的时间信息；增加自身摘要排除、重试稳定性、风险证据时间变化及实际文件哈希验证的计划场景。

最后统一SEC事实字段的来源与派生权限。将字段分为必须保留原始证据的披露字段和允许按版本化规则确定的规范字段，逐项说明由适配器保留、规范化服务校验或派生的职责；保留原始值，派生结果另外记录规则版本、输入证据和来源引用。不能假定原始SEC数据已经直接提供所有规范字段，也不能直接把披露文件所属财年季度当成每条历史事实的期间身份。允许从明确证据按确定性规则规范化期间类型、符号约定等信息，但禁止用日期接近、数值相同或缺省猜测替代来源关联；证据不足或无法唯一确定时返回明确的不可用或歧义结果。

完成后交叉检查蓝图、ADR、不变量、运行策略、追踪矩阵和验证计划，确保三项规则只有一套一致表述。最终简要列出修改文件、解决的冲突、静态核对结果及仍需人工决定的事项，不得虚构批准、应用实现或运行测试结果。 

---

## Assistant (Build · DeepSeek Flash · 7.0s)

_Thinking:_

We need modify only architecture docs. Three fixes:

1. Recovery check order: On recovery, first read terminal manifest and verify permanent publication: if committed, validated, identity matches -> idempotent success, no need for recovery snapshot. If committed but identity conflict or permanent artifacts corrupt -> return explicit conflict/corrupt, do not overwrite manifest or auto-republish. Only for not committed records requiring continuation read/verify recovery snapshot. Update flow diagram and explanations. Add planned scenarios: "successful publish + cleanup recovery dir, then call recovery again" and "committed artifacts corrupt". Current docs say recovery inspects existing terminal manifest before claiming/publishing, but flow currently reads recovery snapshot first. Need reorder.

2. record_hash field-level projection: explicitly exclude artifact_binding.record_hash and other fields carrying the computed result before calculation; never serialize full record with self-digest. Distinguish canonical content digest vs file byte hash; order: build canonical content -> compute record_hash -> fill binding -> serialize file -> compute file hash -> generate terminal manifest. Check all digest references acyclic. Timestamp exclusion rules align with requirements: only exclude volatile run fields specified; preserve risk evaluation and provenance evidence timestamps. Add scenarios: self-digest exclusion, retry stability, risk evidence timestamp change, actual file hash verification.

3. SEC fact field provenance/derivation: classify fields into disclosure fields that must preserve raw evidence vs canonical fields allowed to be derived by versioned rules. Per-field responsibility: adapter preserves, normalizer validates/derives. Preserve raw values; derived results record rule version, input evidence, source refs. Cannot assume raw SEC provides all canonical fields; cannot treat filing's fiscal year/quarter as each historical fact's period identity. Allowed to normalize period type, sign convention from explicit evidence via deterministic rules; forbidden date proximity/value equality/default guessing. Insufficient/ambiguous -> typed unavailable/ambiguous. Update blueprint §9.6.4, §12.2, ADR 002, invariants INV-A-30, runtime POL-FIN, open decisions ARCH-OD-19, trace tests, evaluation. Add test scenarios for field provenance/derivation.

Need verify current docs. Let's inspect relevant sections.

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== recovery flow and checks ===\"; sed -n '/### 11.3 Recovery path/,/### 11.4/p' architecture-blueprint.md; sed -n '/### 12.6 Recovery snapshot/,/### 12.7/p' architecture-blueprint.md | head -80"
}
```

**Output:**
```
=== recovery flow and checks ===
### 11.3 Recovery path

```text
startup
  -> RecoveryService.scan pending run_ids
  -> short lock: claim/read lease, read current terminal identity,
     update owner/token/expiry; release
  -> outside lock (no run/memory lock held):
       -> read and verify recovery_snapshot (references, digests, versions)
       -> if a completed terminal manifest with matching identity exists: prepare no-op
       -> if different immutable content exists: prepare RUN_ID_CONFLICT
       -> read the recorded memory plan/reservation
       -> render fixed sections; compute hashes; assemble permanent files
       -> stage permanent files under an owner-specific staging directory
       -> stage the original memory entry payload
  -> short lock (run lock -> memory lock):
       -> re-read lease/fencing and current terminal identity
       -> verify the staged content still belongs to the current owner,
          run_id, decision_id, reservation, snapshot, and versions
       -> no-op/conflict exits without writing
       -> complete the one original planned memory entry idempotently
       -> promote staged permanent files; write terminal manifest;
          atomically commit; release
  -> outside lock: post-commit read validation
       -> success: short lock: cleanup own staging/recovery material; release
       -> failure: keep committed manifest; independent corruption diagnostic;
          reject as success/history/export
```

- Long reads, parsing, rendering, and hashing happen outside the run/memory locks.
- Ownership/fencing and the current publication state are re-checked inside each short critical section, and staged content is rejected if it no longer matches the current owner/publication state.
- Recovery uses no LLM, external data, analysis graph, settlement, or reflection. It reuses the original run identity and the recorded reservation; a failed retry leaves a version gap but does not create a second publication.

### 11.4 Read path
### 12.6 Recovery snapshot, lease fencing, and idempotent completion (FR-06/QR-02)

**Snapshot boundary and order**

- Recovery guarantee begins only at `snapshot_ready`: a complete, durably written, read-back-verified, self-contained, redacted snapshot.
- The recovery snapshot is a temporary pending envelope. After commit and post-commit validation, it may be cleaned; formal reads and export do not depend on it.
- The memory reuse/new plan and reserved version are determined **before** the snapshot is written. The snapshot records that plan.
- After the snapshot is ready, recovery performs the idempotent memory write, then writes/validates the permanent publication snapshot candidate, then builds and validates the terminal candidate, then commits, then reads back, then cleans temporary material.
- The snapshot includes the formal decision and binding, terminal-manifest candidate identity, section manifest and fixed rendering inputs, risk input/policy references, the original required memory decision identity and reserved version, the metric bundle when `FR-07` applies, and schema/renderer versions.
- Every reference resolves inside the snapshot with a validated digest; recovery does not depend on a separately lost external file.
- Missing, corrupt, unsupported, or reference-broken snapshots are quarantined and not published as success; valid source material is retained across persistent faults.

**Shared claim, lock, and fencing**

- Normal publication and recovery use the **same** per-run `RunOwnershipLock` and owner/fencing records. There is no second lock or commit marker.
- Long recovery reads, parsing, rendering, and hashing run outside the run/memory locks. The run lock is acquired only for claim/lease state changes and protected writes; the memory lock is acquired after it only for the memory write.
- Recovery claims atomically per `run_id`; one worker is active per `run_id`; duplicate startup/claim does not create a second publication.
- A stale claim/lock may be taken over after lease expiry; takeover increments the fencing token. The old owner is rejected on its next protected write.
- The ownership/fencing check is performed inside the same critical section as the protected write (and memory write when the order requires it), not once before it.
- Lock order is fixed: run lock before memory lock; never acquire the run lock while holding the memory lock.
- Interruption/retry: process exit releases the OS file lock if the OS does so; the logical lease may remain active until expiry. Retry reacquires the file lock, re-reads the lease/reservation/terminal identity, and either reuses the original reservation or completes the same entry idempotently. Cleanup releases only its own lock and never deletes another owner's claim.
- Every publication and memory write checks current ownership/fencing at commit; a worker that lost its lease is rejected without writing.
- Failure is isolated per task; retries are bounded; at most one successful formal publication exists per `run_id` and decision identity.

**Identity and idempotency**

- Before claiming/publishing, recovery inspects the existing terminal manifest and content identity.
- A legal completed publication with matching identity is already complete: do not republish and do not repeat memory; snapshot residue alone must not trigger publication. The ledger's `committed` projection may be rebuilt from that manifest.
- Same `run_id` with the same immutable content is a no-op; different content is `RUN_ID_CONFLICT`.
- Recovery reuses its recorded `reserved` allocation. If the original publication failed, the ledger keeps a `failed` allocation; recovery does not allocate a new version. If recovery fails again, the version remains occupied.
- A post-commit read failure keeps the committed terminal manifest immutable, records an independent corruption diagnostic, and rejects the record as success/history/export; it does not republish a second terminal manifest.
- `analysis_complete`, `snapshot_ready`, `publication_committed`, `failed`, `quarantined`, and `corrupt` are distinct states; only committed plus read-time `INV-01` is visible as successful history.

**Performance**

- QR-02 uses 100 committed publications and 10 pending valid snapshots, fixed 12-section report maps, one risk evidence object, one required memory write, rendered output and snapshot each at most 1,048,576 bytes, 30 independently reset trials, and nearest-rank p95 at most 2.000 s **provisional**.
- Timing starts immediately before claim/scan and ends after final read-time validation of every recovered run, including rendering, risk evidence handling, publication, memory, and cleanup attempts.
- Correctness and model-free behavior are zero-tolerance; failures/timeouts are retained and the target is never met by skipping validation.

### 12.7 History retrieval and independent export (FR-05/SR-01)

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== record_hash mentions ===\"; grep -rn \"record_hash\\|record-hash\\|record hash\" architecture-blueprint.md docs/architecture | head -80; echo \"=== hash DAG ===\"; sed -n '/#### 9.6.5 Digest and hash DAG/,/## 10. Entry points/p' architecture-blueprint.md"
}
```

**Output:**
```
=== record_hash mentions ===
architecture-blueprint.md:437:    binding.json                     # artifact_binding + record_hash; no terminal-manifest hash
architecture-blueprint.md:459:- `publication_ref` = `{root: "publication", files: [{relative_path, sha256, hash_scope: "file"}], record_hash}`; it contains no terminal-manifest hash. All paths are relative and confined.
architecture-blueprint.md:525:| `binding.json` | `artifact_binding` fields plus `record_hash` | Terminal-manifest hash, its own file hash, recovery-snapshot digest, commit-evidence hash | 2 |
architecture-blueprint.md:528:| `recovery/recovery_snapshot.json` | Self-contained inputs, formal decision/binding, memory plan/reservation, versions | Final terminal-manifest hash; it may carry terminal-candidate identity (`run_id`, `decision_id`, `record_hash`, reservation) | 4 |
docs/architecture/invariants.md:44:| INV-A-14 | A finalized record hash cannot change during publish or recovery retries. | `INV-01`, `FR-06` | `ArtifactPublisher` | Hash assertion | Abort; quarantine; manual review | Design only |
docs/architecture/invariants.md:51:| INV-A-21 | Immutable decision timing ends at the gate; publish/risk/metrics timestamps have defined scopes and do not mutate the record hash. | `FR-02`, `INV-01`, `FR-04` | `SafetyGate`, `ArtifactPublisher` | Timing-field audit | Reject mismatch; recompute publish metrics | Design only |
docs/architecture/invariants.md:195:- **Statement**: `record_hash` is stable across publish and recovery retries; retries must not mutate the record. Only the highest committed version is effective.
docs/architecture/invariants.md:258:- **Statement**: `FinalizedRunRecord` contains decision-time timing only through the gate. Publish, manifest-write, terminal-manifest write, and end-to-end durations are measured after the decision is frozen and stored in the terminal manifest, not in the immutable record hash. Risk `evaluated_at` and metric computation time are retained in their own evidence fields; they do not mutate the formal decision.
docs/architecture/invariants.md:261:- **Verification**: timing-field audit; record-hash stability across retry; risk evidence timestamp retention.
docs/architecture/invariants.md:429:- **Statement**: Permanent artifacts form a directed acyclic hash graph. `record_hash` is computed first; `binding.json` covers `artifact_binding` plus `record_hash` but excludes the terminal-manifest hash, its own file hash, the recovery digest, and commit-evidence hash. Section/final-state/risk/metric/memory files are hashed next. The recovery snapshot may carry terminal-candidate identity but not the final terminal-manifest hash. The terminal manifest covers `publication_ref` hashes (including `binding.json`) and may hold a `recovery_snapshot_summary` as audit-only; it never hashes itself. An optional `diagnostics/commit_evidence.json` may record the terminal-manifest hash after commit but is outside the permanent hashed set and is not a commit authority.
docs/architecture/runtime-policy-catalog.md:215:  - 3 publish attempts with bounded backoff; no model calls; same `run_id`/`record_version`/`record_hash`; no duplicate memory;
docs/architecture/memory-design.md:89:RUN_META: <record_hash> <run_id> <decision_id> <entry_version> <entry_digest> <evidence_digest> <profile_hash> <gate_status>
docs/architecture/memory-design.md:178:- same `run_id`, `record_version`, and `record_hash`.
docs/architecture/memory-design.md:225:- a compact record hash, gate status, and optional risk summary as metadata.
=== hash DAG ===
#### 9.6.5 Digest and hash DAG

The permanent artifacts form a directed acyclic hash graph. A file that is hashed by the terminal manifest must not contain the terminal manifest hash.

| Artifact | Digest covers | Explicitly excludes | Order |
|---|---|---|---|
| `record.json` | Canonical `FinalizedRunRecord` content and `artifact_binding` fields | Run-level generated/evaluated/finished timestamps, local paths, cache counters, terminal-manifest hash, recovery-snapshot hash | 1 |
| `binding.json` | `artifact_binding` fields plus `record_hash` | Terminal-manifest hash, its own file hash, recovery-snapshot digest, commit-evidence hash | 2 |
| `report/section_manifest.json` | Section paths, fields, byte sizes, SHA-256, complete-report digest | Terminal-manifest hash, binding file hash, recovery digest | 3 |
| `final_state.json`, `risk/*`, `metrics/*`, `memory/entry_binding.json` | Their own canonical content and referenced evidence digests | Terminal-manifest hash, binding file hash, recovery digest | 3 |
| `recovery/recovery_snapshot.json` | Self-contained inputs, formal decision/binding, memory plan/reservation, versions | Final terminal-manifest hash; it may carry terminal-candidate identity (`run_id`, `decision_id`, `record_hash`, reservation) | 4 |
| terminal `run_manifest.json` | `publication_ref.files` hashes (including `binding.json`), formal decision, security scans, section manifest, metric bundle, memory binding, and `recovery_snapshot_summary` (audit-only) | Its own hash; any file that contains its hash; optional commit-evidence hash | 5 |
| `diagnostics/commit_evidence.json` (optional) | Terminal-manifest hash and read-time validation result | Never hashed by the terminal manifest; never a commit condition | 6 (after commit) |

- `binding.json` never stores a terminal-manifest hash or a full terminal-manifest file hash.
- The terminal manifest never hashes itself. Readers compute its hash from the manifest bytes and use it as a read-time token.
- If an audit summary of the terminal manifest is needed, use `diagnostics/commit_evidence.json`; it is outside the permanent hashed set and is not a second commit authority.
- A `recovery_snapshot_summary` inside the terminal manifest may record status/digest/created-at as audit information. It does not make `recovery/` a required verification dependency.
- Computation order is fixed as above; a later artifact may hash an earlier one, never the reverse.

---

## 10. Entry points and adaptation

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== SEC contract ===\"; sed -n '/#### 9.6.4 SEC structured query/,/#### 9.6.5/p' architecture-blueprint.md; echo \"=== SEC other docs ===\"; grep -rn \"Source-field\\|source-field\\|fiscal_year\\|fiscal_quarter\\|period identity\\|field ownership\\|derived\" docs/architecture/invariants.md docs/architecture/runtime-policy-catalog.md docs/architecture/adr/002-full-scope-add-r.md docs/architecture/open-decisions.md | head -60"
}
```

**Output:**
```
=== SEC contract ===
#### 9.6.4 SEC structured query input/output contract

`DataAccessService.query("sec_structured_facts", request) -> StructuredFactPayload`

- **Input**:
  ```text
  {ticker, subject_id? (CIK), as_of_date,
   forms? ["10-K", "10-Q"], concepts? [...],
   periods? {annual: n, quarterly: n, ytd: n},
   filing_ref_required: true}
  ```
- **Output** (returned by `SecEdgarAdapter`, normalized by `FinancialFactService`): each fact is a self-describing record, not an unlinked row plus a separate filing list.
  ```text
  {subject_id, source: "SEC EDGAR", source_retrieved_at,
   facts: [{
     fact_id,
     subject_id,                       # CIK or equivalent issuer identity
     accession_no,                     # disclosure identifier
     filing_ref,                       # locatable filing reference
     filed_at,                         # disclosure time
     form,                             # 10-K, 10-Q, ...
     concept, value, unit, currency,
     period_start, period_end,
     fiscal_year, fiscal_quarter,
     span: annual|quarter|ytd|instant,
     cumulative_duration_days,
     sign,
     restates_fact_id?,                # explicit restatement/alternative lineage
     supersedes?,
     source_fact_ref?                  # raw SEC fact/table reference
   }],
   provenance: {...}}
  ```
- **Source-field ownership**: `subject_id`, `accession_no`, `filing_ref`, `filed_at`, `form`, `concept`, `period_*`, `fiscal_*`, `span`, `unit`, `currency`, `value`, `sign`, and any restatement/supersession link are preserved from the raw SEC filing/fact data. `FinancialFactService` may validate, canonicalize, or derive `fact_id`, `cumulative_duration_days`, and normalized comparisons, but must preserve the source linkage. If any required source field is missing, or more than one fact remains a plausible source, return `FactUnavailableError`/`FactAmbiguousError`; never infer a link from date proximity or equal value.
- **Errors**: `VendorUnavailableError`, `NoMarketDataError`, `VendorNotConfiguredError`, `FactAmbiguousError`, `FactUnavailableError`, mapped by `DataAccessService`; no raw vendor call outside the adapter.
- The existing `get_income_statement`, `get_balance_sheet`, and `get_cashflow` tools use the same query path, run cache, counters, and provenance. `FinancialFactService` performs period/fact identity validation/normalization; the adapter does not decide metric semantics.

#### 9.6.5 Digest and hash DAG
=== SEC other docs ===
docs/architecture/invariants.md:66:| INV-A-36 | The final model proposal is produced by the Portfolio Manager adapter, not by the Trader or a risk debater; it carries source and unapproved status. | `SB-01`, `INV-01` | `PortfolioManagerAdapter`, `SafetyGate` | Source-field/source-promotion audit | Reject proposal; no formal decision | Design only |
docs/architecture/invariants.md:141:- **Statement**: Memory append is keyed by `(decision_id, entry_digest)` plus the existing `(trade_date, ticker)` guard. The readable criterion is the completed terminal manifest plus read-time INV-01. Same key is a no-op; a different decision_id creates a new committed version; only same decision_id with a different entry_digest is a conflict. Reused historical entries use `reused_decision_ref` and keep the current artifact run_id. Version allocation is persistent and lock-protected, and the next version is `high_water + 1` over every historical allocation, including failed reservations. Retries and recovery reuse their own reservation; a failed version permanently occupies the high-water mark and is never reissued. `reserved` is appended before the recovery snapshot, `failed` on abort before a completed manifest, and `committed` is a derived projection appended only after terminal commit plus read-time INV-01; a missing/failed projection write is rebuilt from the terminal manifest and is not a second commit condition. An uncommitted entry is never treated as reusable success; `MemoryRecoveryCoordinator` applies bounded wait/`MEMORY_PENDING_RETRYABLE`, recovery under the original run identity/reservation/snapshot, and typed unavailable/failed/conflict statuses; it never transfers ownership. Settlement/reflection is append-only; legal rotation is recorded as `not_available`, not a binding mismatch.
docs/architecture/invariants.md:150:- **Statement**: No known secret and no unredacted versioned-pattern match appears in an in-scope app-controlled boundary, including manifest, final-state, risk input/diagnostic, policy snapshot, memory entry, report metadata/content, section manifest, archive, history responses, recovery snapshot/diagnostics, export diagnostics, logs, preferences, error/gate/availability records, and formal API return. Audit endpoints are scheme/host/path only; restore endpoints may keep non-sensitive query parameters and secret references, never inline sensitive values. Paths derived from prose, filters, run_id, or export target remain within the configured root; traversal, absolute-path injection, symlink/junction escape, and out-of-root writes are forbidden. A non-empty export target returns `EXPORT_CONFLICT` and is not modified.
docs/architecture/invariants.md:213:- **Statement**: `decision_id` is derived from stable decision content and is independent of `run_id`. Memory reuse/conflict is decided by `decision_id`/`entry_digest`. `entry_digest` covers stable decision content only; `evidence_digest` covers per-run evidence and may differ. A reused historical entry is referenced through `reused_decision_ref`; current artifacts keep the current run_id.
docs/architecture/invariants.md:222:- **Statement**: When multiple reasons occur, `primary_reason_code` is the first in the fixed priority list; `review_class` is derived from that primary reason; all reason codes remain as secondary reasons. A system error (`gate_internal_error` or `portfolio_risk_evaluator_error`) takes the higher-priority error path over a coverage gap.
docs/architecture/invariants.md:339:- **Statement**: Derived metrics use per-fact structured records that each carry subject, accession/disclosure identifier, filing reference, filed-at, form, concept, period identity, fiscal position, span, unit, currency, sign, and restatement/supersession lineage. Source linkage is preserved from raw SEC data or explicitly derived by normalization; missing or multiple plausible sources return unavailable/ambiguous and are never guessed from date proximity or equal value. The fact fetch, metric computation, block append, and conflict check occur after the fundamentals report exists and before research debate consumes it; final publication only persists the existing result. Only facts filed on or before as-of are visible. Near dates, equal values, and same-day multiple accessions are never merged without explicit lineage; ambiguity produces a typed n/a. Formulas are explicit and versioned; TTM uses annual + current YTD - prior matching YTD and never derives a quarter by subtraction. The program-appended metric block is the numeric authority; conflicts with structured claims are disclosed and the contradicted claim is labeled unverified.
docs/architecture/invariants.md:396:- **Verification**: source-field assertions; attempted Trader/risk-debater promotion; unparseable PM output; formal-consumer audit.
docs/architecture/runtime-policy-catalog.md:137:- **Rule**: historical/current mode is derived once from the fixed clock, never from a later call to today. Resume/replay inherits the original clock unless a `clock_override` is recorded.
docs/architecture/runtime-policy-catalog.md:287:  - entries physically `pending`; `commit_status` derived from the completed manifest, not stored in the entry;
docs/architecture/runtime-policy-catalog.md:290:  - `MemoryReservationStore` is a persistent, append-only allocation history; the next version is `high_water + 1` over **all** historical allocations, including failed reservations; a failed version is never reissued; retries/recovery reuse their own reservation; `committed` is a derived projection from the terminal manifest, not a second commit condition;
docs/architecture/runtime-policy-catalog.md:293:  - memory-disabled runs require no memory artifact; the ledger's `committed` projection is derived from terminal manifests, not a second commit condition;
docs/architecture/runtime-policy-catalog.md:304:- **Facts**: each fact carries subject/accession/filing_ref/filed_at/form/concept/period/fiscal position/span/cumulative duration/unit/currency/source/sign/restatement lineage; CIK never substitutes for accession/filing_ref. Source linkage is preserved from raw SEC data or explicitly derived; missing/multiple plausible sources return unavailable/ambiguous and are never guessed from date proximity or equal value.
docs/architecture/adr/002-full-scope-add-r.md:20:- `FR-07`: deterministic derived financial metrics from structured facts.
docs/architecture/adr/002-full-scope-add-r.md:74:- `FinancialMetricService` is pure and computes the listed metrics with exact formulas and typed n/a reasons; no quarter is derived by subtraction.
docs/architecture/adr/002-full-scope-add-r.md:81:Rejected alternatives: model arithmetic (baseline error, unverifiable); a direct SEC client (duplicate data path/counters); subtraction-derived quarters (prohibited).
docs/architecture/adr/002-full-scope-add-r.md:114:- `MemoryReservationStore` keeps a persistent high-water mark over all historical allocations, including failed reservations; a failed version is never reissued. `committed` is a derived projection from the terminal manifest, not a second commit condition.
docs/architecture/open-decisions.md:248:- **Question**: scan committed publication roots on demand, or maintain a derived index?
docs/architecture/open-decisions.md:250:- **Recommendation (not approved)**: scan committed publication roots and optionally maintain a **non-authoritative** derived index that can be rebuilt; never let the index decide commitment or override read-time validation.
docs/architecture/open-decisions.md:377:- **Question**: where is the persistent reservation history stored, and how does it atomically track the allocation high-water mark (including failed reservations) and derived commit projections?
docs/architecture/open-decisions.md:379:- **Recommendation (not approved)**: a lock-protected `memory/reservations.jsonl` ledger keyed by ticker/date/decision_id, recording entry_version, owner run_id, status reserved/committed/failed, and fencing token. It is authoritative for version allocation, not for decision content. The next version is `high_water + 1` over every historical allocation, including failed reservations; a failed version is never reissued; retries/recovery reuse their own reservation; recovery uses the original run_id/version/snapshot; `committed` is a derived projection from the terminal manifest, not a second commit condition. Repair replays the append-only allocation history and never resets the watermark or reissues failed versions. If a structured sidecar is rejected, the same fields must live in a structured Markdown metadata line under the same lock.

```

---

## Assistant (Build · DeepSeek Flash · 21.8s)

_Thinking:_

Need implement three fixes.

### Fix 1: Recovery check order
Rewrite §11.3 flow: after scan, short lock read lease + terminal manifest? We need "first read terminal manifest and verify permanent publication". Could be outside lock? Reading terminal manifest is read-only; can read outside lock. But to decide idempotent success, need validate permanent artifacts and identity. We can do outside lock initially; then if not committed, claim/lease. However user says "恢复时先读取终态清单并验证永久发布". We can do:
```
startup
 -> scan pending run_ids
 -> read terminal manifest (if present) and verify permanent publication outside lock:
    - committed + validated + identity match -> return idempotent success (no recovery snapshot)
    - committed + identity conflict -> RUN_ID_CONFLICT
    - committed + permanent artifacts corrupt -> CORRUPT_RECORD / committed_unavailable (no overwrite/republish)
    - not committed/absent -> continue
 -> short lock claim/read lease...
 -> outside lock read/verify recovery snapshot only for continuation
...
```
But "committed + corrupt" could be a race with another writer? The manifest is immutable; okay. If committed but corrupt, return explicit result. If not committed, claim then continue. Need also handle terminal manifest appears after initial read: short lock recheck before committing; if a completed matching manifest appears, no-op; if conflict, conflict. Good.

Also §12.6 "Identity and idempotency" currently says "Before claiming/publishing, recovery inspects existing terminal manifest..." but flow reads snapshot first. Update to explicitly order and outcomes:
1. Read terminal manifest first.
2. If completed + INV-01 + identity match -> idempotent success, no snapshot required.
3. If completed + identity conflict -> `RUN_ID_CONFLICT`, no overwrite/republish.
4. If completed but permanent artifact corrupt -> `CORRUPT_RECORD`/`COMMITTED_CORRUPT`, no overwrite/republish.
5. Only uncommitted/absent continues to claim/read recovery snapshot.
6. If snapshot missing/invalid -> quarantine/failed, no publication.
Need define status names. Use `RUN_ID_CONFLICT`, `CORRUPT_RECORD` maybe `PERMANENT_RECORD_CORRUPT`. The docs use `CORRUPT_RECORD` for history. For recovery, return `COMMITTED_CORRUPT`? Let's define `PERMANENT_RECORD_CORRUPT` or reuse `CORRUPT_RECORD`. To be consistent with existing, use `CORRUPT_RECORD` with context, and `RUN_ID_CONFLICT`. The user says "分别返回明确的冲突或损坏结果" — use `RUN_ID_CONFLICT` and `CORRUPT_RECORD`. Fine.

Add scenarios: T-SCEN-17 "successful publish + cleanup recovery dir, then recovery called again -> idempotent success without recovery snapshot"; T-SCEN-18 "committed artifacts corrupt -> CORRUPT_RECORD, no overwrite/republish". Add T-ARCH-41/42 maybe. Update trace/eval counts 18/42.

Also update §11.3 text bullets. §12.6 "Snapshot boundary and order" says recovery guarantee begins at snapshot; but if already committed, no snapshot needed. Clarify: recovery snapshot is required only for continuation of uncommitted publication; already committed returns idempotent success without it. Update.

### Fix 2: record_hash field-level projection
Need add explicit §? in §9.6.5 or new §9.6.6. Current hash DAG table says record.json covers canonical record and artifact_binding fields, excludes timestamps etc. But record_hash computation not explicit. Add subsection "record_hash projection and file hash order" with:
- `record_hash` is a canonical content digest, not a file byte hash.
- Build projection excluding:
  - `artifact_binding.record_hash` and any field carrying record_hash or computed from it (e.g., `publication_ref.record_hash`, binder self-hash)
  - terminal manifest hash, commit evidence hash, artifact file hashes
  - only volatile run-level fields required to be excluded by D1: `generated_at`, `evaluated_at`, `finished_at`, `run_clock.now_utc`? Requirements INV-01 canonicalization says excludes run-level generated_at/evaluated_at/finished_at and local absolute paths; `record_hash` definition says excludes volatile run-level timestamps including run_clock.now_utc, artifact paths, cache counters, computed snapshot timestamps. Need align "只排除需求规定的易变运行字段，保留风险评估和来源证据中必须保留的时间信息". So list:
    - Exclude: `generated_at`, `evaluated_at` (run-level gate? careful risk evaluated_at must be preserved in risk evidence), `finished_at`, `run_clock.now_utc`, local absolute paths, cache counters, computed snapshot timestamps, manifest/file hashes, record_hash itself.
    - Preserve: risk `evaluated_at` inside `portfolio_risk_result` (immutable risk evidence timestamp), provenance/attempt/evidence timestamps, `filed_at`, `valuation_time`, `valuation_cutoff`, metric computation timestamps? Requirement says risk `evaluated_at` retained. "来源证据中必须保留的时间信息" includes attempts timestamps, evidence timestamps, filed_at. Need say:
      - Preserve risk policy/input/result timestamps and provenance evidence timestamps.
      - Exclude only run-level volatile timestamps, not risk/e evidence timestamps.
- Order:
  1. Build canonical content projection with `artifact_binding.record_hash` removed and all fields that carry the computed result/hash removed.
  2. Compute `record_hash` = SHA-256 canonical projection.
  3. Fill `artifact_binding.record_hash`.
  4. Serialize `record.json`/`binding.json` (file bytes).
  5. Compute file byte SHA-256 for publication_ref.
  6. Build terminal manifest with file hashes.
- Distinguish canonical content digest vs file hash: `record_hash` is not `sha256(record.json bytes)`; `binding.json` file hash is `sha256(binding.json bytes)`.
- `decision_digest` etc are content digests; file hashes separate.
- Add invariant INV-A-41 "record_hash projection" or fold into INV-A-40? Add new INV-A-41. Add scenarios T-SCEN-17? Wait we used 17/18 for recovery. Add T-SCEN-19 record_hash self-exclusion, T-SCEN-20 retry stability/risk timestamp/file hash? The user asks "增加自身摘要排除、重试稳定性、风险证据时间变化及实际文件哈希验证的计划场景." Could add T-ARCH-41..44 instead of scenarios. Better add T-SCEN-19 "record_hash self-exclusion/retry stability/risk timestamp preservation/file hash verification" or split into T-ARCH-41..44. We already will use T-ARCH-41/42 for recovery maybe. Let's plan:
  - T-SCEN-17: cleanup recovery then recovery idempotent success.
  - T-SCEN-18: committed permanent corrupt.
  - T-ARCH-41: record_hash projection self-exclusion and canonical digest vs file hash.
  - T-ARCH-42: retry stability and risk evidence timestamp preservation.
  - T-ARCH-43: recovery first checks terminal manifest, no snapshot requirement on committed.
  - T-ARCH-44: committed corrupt no overwrite/republish.
Maybe T-SCEN-17/18 plus T-ARCH-41..44.
- Update trace counts 18 scenarios, 44 arch.
- Update evaluation measurement rows.

### Fix 3: SEC field provenance/derivation
Need rewrite §9.6.4 with two field classes:
A. Disclosure/raw evidence fields that must be preserved:
   - subject_id (issuer CIK), accession_no, filing_ref, filed_at, form, source_fact_ref, raw concept/tag, raw value, raw unit, raw currency, raw period start/end (if present), raw fiscal metadata (if present), raw sign/capex presentation, restatement/supersession links.
B. Canonical/derived fields allowed by versioned rules:
   - canonical concept mapping, canonical period identity (period_start/end, fiscal_year/quarter, span, cumulative_duration_days), normalized sign convention, normalized unit/currency (only if explicit conversion? No FX allowed), `fact_id`, `supersedes` linkage if explicit; `calculation_status`.
- Responsibilities:
  - Adapter preserves raw fields and source refs; does not infer canonical period/quarter.
  - Normalizer validates presence/types; may derive canonical period/span/duration/sign only from explicit raw evidence and versioned rules; records `normalization_rule_version`, `input_evidence_refs`, `source_refs`; retains raw values.
  - Cannot assume raw SEC provides all canonical fields; cannot use filing's fiscal year/quarter as each historical fact's period identity. The filing's fiscal metadata is filing-level, not fact-level; each fact must have its own period identity or explicit derivation evidence.
  - If evidence insufficient or multiple plausible sources -> `FactUnavailableError`/`FactAmbiguousError`.
  - No date proximity/value equality/default guessing.
- Update output schema with `raw_*` fields and `derived_*`/`normalization` metadata, e.g.:
  ```
  fact_id,
  subject_id, accession_no, filing_ref, filed_at, form, source_fact_ref,
  raw: {concept, value, unit, currency, period_start, period_end, fiscal_year, fiscal_quarter, span, sign, restates_fact_id?, supersedes?},
  canonical: {concept, value, unit, currency, period_start, period_end, fiscal_year, fiscal_quarter, span, cumulative_duration_days, sign, restates_fact_id?, supersedes?},
  derivation: {rule_version, derived_fields: [...], input_evidence_refs: [...], source_refs: [...]}
  ```
  But this may be too verbose. Use clear structure.
- Update §12.2 bullet; invariants INV-A-30; ADR 002; runtime POL-FIN; open decisions ARCH-OD-19; trace FR-07-AC3/AC7/T-ARCH-35; evaluation.
- Add tests T-ARCH-45 "SEC field provenance/derivation matrix" or extend T-ARCH-35. Maybe T-ARCH-35 enough, but add T-ARCH-45 for raw vs derived fields and filing-level vs fact-level fiscal identity. Update counts.

Let's implement.

#### Recovery order edits
Rewrite §11.3 flow and §12.6 identity.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\nold=\"\"\"```text\nstartup\n  -> RecoveryService.scan pending run_ids\n  -> short lock: claim/read lease, read current terminal identity,\n     update owner/token/expiry; release\n  -> outside lock (no run/memory lock held):\n       -> read and verify recovery_snapshot (references, digests, versions)\n       -> if a completed terminal manifest with matching identity exists: prepare no-op\n       -> if different immutable content exists: prepare RUN_ID_CONFLICT\n       -> read the recorded memory plan/reservation\n       -> render fixed sections; compute hashes; assemble permanent files\n       -> stage permanent files under an owner-specific staging directory\n       -> stage the original memory entry payload\n  -> short lock (run lock -> memory lock):\n       -> re-read lease/fencing and current terminal identity\n       -> verify the staged content still belongs to the current owner,\n          run_id, decision_id, reservation, snapshot, and versions\n       -> no-op/conflict exits without writing\n       -> complete the one original planned memory entry idempotently\n       -> promote staged permanent files; write terminal manifest;\n          atomically commit; release\n  -> outside lock: post-commit read validation\n       -> success: short lock: cleanup own staging/recovery material; release\n       -> failure: keep committed manifest; independent corruption diagnostic;\n          reject as success/history/export\n```\n\n- Long reads, parsing, rendering, and hashing happen outside the run/memory locks.\n- Ownership/fencing and the current publication state are re-checked inside each short critical section, and staged content is rejected if it no longer matches the current owner/publication state.\n- Recovery uses no LLM, external data, analysis graph, settlement, or reflection. It reuses the original run identity and the recorded reservation; a failed retry leaves a version gap but does not create a second publication.\"\"\"\nnew=\"\"\"```text\nstartup\n  -> RecoveryService.scan pending run_ids\n  -> FIRST: read the terminal manifest, if present, outside the locks\n       -> completed + read-time INV-01 passes + identity matches:\n            return idempotent success; do NOT require recovery_snapshot\n       -> completed + identity conflict:\n            return RUN_ID_CONFLICT; do not overwrite or republish\n       -> completed + permanent artifacts corrupt:\n            return CORRUPT_RECORD; do not overwrite or republish\n       -> not completed or absent: continue as a pending publication\n  -> short lock: claim/read lease, read current terminal identity,\n     update owner/token/expiry; release\n  -> outside lock (no run/memory lock held):\n       -> only now read and verify recovery_snapshot (references, digests, versions)\n       -> re-check terminal identity; a completed matching run becomes no-op,\n          a completed conflicting/corrupt run returns the typed result\n       -> read the recorded memory plan/reservation\n       -> render fixed sections; compute hashes; assemble permanent files\n       -> stage permanent files under an owner-specific staging directory\n       -> stage the original memory entry payload\n  -> short lock (run lock -> memory lock):\n       -> re-read lease/fencing and current terminal identity\n       -> verify the staged content still belongs to the current owner,\n          run_id, decision_id, reservation, snapshot, and versions\n       -> no-op/conflict/corrupt exits without writing\n       -> complete the one original planned memory entry idempotently\n       -> promote staged permanent files; write terminal manifest;\n          atomically commit; release\n  -> outside lock: post-commit read validation\n       -> success: short lock: cleanup own staging/recovery material; release\n       -> failure: keep committed manifest; independent corruption diagnostic;\n          reject as success/history/export\n```\n\n- The terminal manifest is checked first. A committed, verified, identity-matching publication is an idempotent success even if `recovery/` no longer exists.\n- A committed identity conflict returns `RUN_ID_CONFLICT`; committed-but-corrupt permanent artifacts return `CORRUPT_RECORD`. Neither path overwrites the terminal manifest or auto-republishes.\n- The recovery snapshot is read and verified only for a record that is not yet committed and still needs publication continuation.\n- Long reads, parsing, rendering, and hashing happen outside the run/memory locks.\n- Ownership/fencing and the current publication state are re-checked inside each short critical section, and staged content is rejected if it no longer matches the current owner/publication state.\n- Recovery uses no LLM, external data, analysis graph, settlement, or reflection. It reuses the original run identity and the recorded reservation; a failed retry leaves a version gap but does not create a second publication.\"\"\"\ns=s.replace(old,new)\n# Update §12.6 identity and snapshot order\ns=s.replace(\"\"\"**Snapshot boundary and order**\n\n- Recovery guarantee begins only at `snapshot_ready`: a complete, durably written, read-back-verified, self-contained, redacted snapshot.\n- The recovery snapshot is a temporary pending envelope. After commit and post-commit validation, it may be cleaned; formal reads and export do not depend on it.\n- The memory reuse/new plan and reserved version are determined **before** the snapshot is written. The snapshot records that plan.\n- After the snapshot is ready, recovery performs the idempotent memory write, then writes/validates the permanent publication snapshot candidate, then builds and validates the terminal candidate, then commits, then reads back, then cleans temporary material.\n- The snapshot includes the formal decision and binding, terminal-manifest candidate identity, section manifest and fixed rendering inputs, risk input/policy references, the original required memory decision identity and reserved version, the metric bundle when `FR-07` applies, and schema/renderer versions.\n- Every reference resolves inside the snapshot with a validated digest; recovery does not depend on a separately lost external file.\n- Missing, corrupt, unsupported, or reference-broken snapshots are quarantined and not published as success; valid source material is retained across persistent faults.\"\"\",\n\"\"\"**Snapshot boundary and order**\n\n- Recovery **first** reads the terminal manifest and verifies the permanent publication. A committed, INV-01-valid, identity-matching publication returns idempotent success and does not require `recovery/`.\n- A committed identity conflict returns `RUN_ID_CONFLICT`; a committed publication with corrupt permanent artifacts returns `CORRUPT_RECORD`. Neither overwrites the terminal manifest or auto-republishes.\n- Only a record that is not committed and still needs publication continuation reads and verifies the recovery snapshot.\n- For that continuation, recovery guarantee begins only at `snapshot_ready`: a complete, durably written, read-back-verified, self-contained, redacted snapshot.\n- The recovery snapshot is a temporary pending envelope. After commit and post-commit validation, it may be cleaned; formal reads and export do not depend on it.\n- The memory reuse/new plan and reserved version are determined **before** the snapshot is written. The snapshot records that plan.\n- After the snapshot is ready, recovery performs the idempotent memory write, then writes/validates the permanent publication snapshot candidate, then builds and validates the terminal candidate, then commits, then reads back, then cleans temporary material.\n- The snapshot includes the formal decision and binding, terminal-manifest candidate identity, section manifest and fixed rendering inputs, risk input/policy references, the original required memory decision identity and reserved version, the metric bundle when `FR-07` applies, and schema/renderer versions.\n- Every reference resolves inside the snapshot with a validated digest; recovery does not depend on a separately lost external file.\n- Missing, corrupt, unsupported, or reference-broken snapshots for a still-uncommitted record are quarantined and not published as success; valid source material is retained across persistent faults.\"\"\")\ns=s.replace(\"\"\"**Identity and idempotency**\n\n- Before claiming/publishing, recovery inspects the existing terminal manifest and content identity.\n- A legal completed publication with matching identity is already complete: do not republish and do not repeat memory; snapshot residue alone must not trigger publication. The ledger's `committed` projection may be rebuilt from that manifest.\n- Same `run_id` with the same immutable content is a no-op; different content is `RUN_ID_CONFLICT`.\"\"\",\n\"\"\"**Identity and idempotency**\n\n- Recovery checks the terminal manifest **before** reading the recovery snapshot.\n- A legal completed publication with matching identity is already complete: return idempotent success, do not republish, do not repeat memory, and do not require `recovery/`. The ledger's `committed` projection may be rebuilt from that manifest.\n- A completed publication with a different identity returns `RUN_ID_CONFLICT`; a completed publication whose permanent artifacts fail verification returns `CORRUPT_RECORD`. Neither overwrites the terminal manifest or auto-republishes.\n- Only an uncommitted/absent record continues to claim and read the recovery snapshot. Same `run_id` with the same immutable content is a no-op; different content is `RUN_ID_CONFLICT`.\"\"\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.2s)

_Thinking:_

Need update runtime POL-REC and ADR 002 to first terminal check. Add bullet.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/runtime-policy-catalog.md')\ns=p.read_text()\ns=s.replace(\"- **Order**: determine the memory reuse/new plan and reserve the version -> write the recovery snapshot containing the plan -> idempotent memory write -> permanent snapshot write/validate -> terminal candidate + INV-01 -> commit -> post-commit read -> cleanup.\",\n\"- **First check**: read the terminal manifest and verify the permanent publication before reading `recovery/`. Committed + INV-01 + identity match -> idempotent success (no snapshot required); committed + identity conflict -> `RUN_ID_CONFLICT`; committed + corrupt permanent artifacts -> `CORRUPT_RECORD`; neither overwrites the manifest or auto-republishes.\\n- **Continuation order**: only for an uncommitted record, determine the memory reuse/new plan and reserve the version -> write the recovery snapshot containing the plan -> idempotent memory write -> permanent snapshot write/validate -> terminal candidate + INV-01 -> commit -> post-commit read -> cleanup.\")\ns=s.replace(\"- **Identity**: existing completed matching identity -> no-op; different content -> `RUN_ID_CONFLICT`; same content no-op.\",\n\"- **Identity**: terminal manifest first. Completed + matching identity -> idempotent success without `recovery/`; different content -> `RUN_ID_CONFLICT`; committed but permanent artifacts corrupt -> `CORRUPT_RECORD`; only uncommitted/absent continues with the recovery snapshot.\")\np.write_text(s)\np=Path('docs/architecture/adr/002-full-scope-add-r.md')\ns=p.read_text()\ns=s.replace(\"- The memory plan/reservation is fixed before the recovery snapshot; after it, recovery performs the idempotent memory write, writes/validates the permanent snapshot candidate, validates the terminal candidate, commits, reads back, and cleans last.\",\n\"- Recovery first reads the terminal manifest and verifies the permanent publication. Committed + INV-01 + identity match is idempotent success without `recovery/`; committed + identity conflict -> `RUN_ID_CONFLICT`; committed + corrupt permanent artifacts -> `CORRUPT_RECORD`; neither overwrites or auto-republishes. Only an uncommitted record continues: memory plan/reservation -> recovery snapshot -> idempotent memory write -> permanent snapshot -> terminal candidate -> commit -> read-back -> cleanup.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.9s)

_Thinking:_

Update invariant INV-A-28/29? Add to INV-A-28 statement "terminal manifest first; committed matching no snapshot; conflict/corrupt typed; no republish." Let's edit inventory and detailed.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/invariants.md')\ns=p.read_text()\ns=s.replace(\"| INV-A-28 | Publication recovery uses saved records only, preserves the original run_id, and yields at most one committed publication. | `FR-06` | `RecoveryService`, `ArtifactPublisher` | Model-free/duplicate/retry tests | Quarantine; no publish; bounded retry | Design only |\",\n\"| INV-A-28 | Publication recovery checks the terminal manifest first: committed+verified+identity match is idempotent success without `recovery/`; conflict/corrupt are typed; only uncommitted records use saved recovery records; at most one committed publication. | `FR-06` | `RecoveryService`, `ArtifactPublisher` | Terminal-first/model-free/duplicate/retry/corrupt tests | Quarantine; no publish; no overwrite; bounded retry | Design only |\")\ns=s.replace(\"- **Statement**: Recovery continues the existing publication process using saved, verified, redacted formal records and fixed render inputs. It does not re-run analysis or create a separate archive transaction. It preserves the original `run_id`, makes no LLM/external/graph/settlement/reflection calls, and yields at most one committed publication per `run_id` and decision identity. An existing completed publication with matching identity is a no-op; different content is `RUN_ID_CONFLICT`.\",\n\"- **Statement**: Recovery first reads the terminal manifest and verifies the permanent publication. A committed, INV-01-valid, identity-matching publication is an idempotent success without requiring `recovery/`; a committed identity conflict is `RUN_ID_CONFLICT`; committed permanent-artifact corruption is `CORRUPT_RECORD`; neither overwrites the terminal manifest or auto-republishes. Only an uncommitted/absent record continues with saved, verified, redacted formal records and fixed render inputs. Recovery does not re-run analysis or create a separate archive transaction. It preserves the original `run_id`, makes no LLM/external/graph/settlement/reflection calls, and yields at most one committed publication per `run_id` and decision identity.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.4s)

_Thinking:_

Check detailed replacement worked. Fine.

Update memory design §12 first check.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/memory-design.md')\ns=p.read_text()\ns=s.replace(\"- Recovery first checks for an existing completed publication with matching identity; if found, it does not repeat memory.\",\n\"- Recovery first reads the terminal manifest and verifies the permanent publication. A committed, verified, identity-matching publication is idempotent success without requiring `recovery/`; a committed identity conflict is `RUN_ID_CONFLICT`; committed permanent-artifact corruption is `CORRUPT_RECORD`; neither overwrites the manifest or auto-republishes. Only an uncommitted record continues with the recovery snapshot.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.3s)

_Thinking:_

Update blueprint §1.3 corrections item 11 maybe includes first check. Add item? Existing 11 says cleanup/permanent. Add item 17? We can add to §1.3 a line about recovery first check. Not strictly necessary but good. Add item 17.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"16. Concrete implementation-start proposals are recorded for snapshot layout, the acyclic hash DAG, lock/lease records and state transitions, memory reservation authority/replay, and the per-fact SEC structured query contract; they are proposals pending review, not approvals.\",\n\"16. Concrete implementation-start proposals are recorded for snapshot layout, the acyclic hash DAG, lock/lease records and state transitions, memory reservation authority/replay, and the per-fact SEC structured query contract; they are proposals pending review, not approvals.\\n17. Recovery checks the terminal manifest first: committed+verified+identity match is idempotent success without requiring `recovery/`; committed identity conflict or permanent-artifact corruption returns a typed conflict/corrupt result and never overwrites or auto-republishes. Only uncommitted records read the recovery snapshot.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 9.0s)

_Thinking:_

Now add scenarios T-SCEN-17/18 and T-ARCH-41.. etc. We planned T-SCEN-17 cleanup recovery idempotent, T-SCEN-18 committed corrupt. Add to §13.2, trace, eval. Also add T-ARCH-41 record_hash projection, T-ARCH-42 retry/timestamps/file hash, T-ARCH-43 recovery terminal-first, T-ARCH-44 committed corrupt no overwrite. Update counts 18 scenarios, 44 arch.

Let's edit.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"| Commit/ledger-update interruption | Terminal manifest commit succeeds but ledger `committed` projection is missing/fails; manifest remains authority; repair rebuilds projection without losing failed allocations or reissuing versions | `T-SCEN-16`: crash between commit and ledger update; assert history reads, ledger repair, high-water preservation, no second commit condition |\",\n\"\"\"| Commit/ledger-update interruption | Terminal manifest commit succeeds but ledger `committed` projection is missing/fails; manifest remains authority; repair rebuilds projection without losing failed allocations or reissuing versions | `T-SCEN-16`: crash between commit and ledger update; assert history reads, ledger repair, high-water preservation, no second commit condition |\n| Recovery after cleanup | Successful publication and recovery-directory cleanup, then recovery is called again; terminal manifest first gives idempotent success without `recovery/` | `T-SCEN-17`: commit, validate, cleanup `recovery/`, run recovery again; assert idempotent success and no snapshot requirement |\n| Committed publication corrupt | Terminal manifest committed but a permanent artifact fails verification; recovery returns `CORRUPT_RECORD`, does not overwrite the manifest, and does not auto-republish | `T-SCEN-18`: tamper a permanent file after commit, run recovery; assert immutable manifest, typed corruption, no second publication |\"\"\")\ns=s.replace(\"The end-to-end scenario tests `T-SCEN-01`..`T-SCEN-16` in §13.2 cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, and commit/ledger-update interruption.\",\n\"The end-to-end scenario tests `T-SCEN-01`..`T-SCEN-18` in §13.2 cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, and committed-publication corruption.\")\np.write_text(s)\np=Path('docs/architecture/trace-matrix.md')\ns=p.read_text()\ns=s.replace(\"| `T-SCEN-16` | Commit/ledger-update interruption; manifest authority; ledger projection repair; failed allocations preserved | not started |\",\n\"\"\"| `T-SCEN-16` | Commit/ledger-update interruption; manifest authority; ledger projection repair; failed allocations preserved | not started |\n| `T-SCEN-17` | Recovery after cleanup: terminal-first idempotent success without recovery directory | not started |\n| `T-SCEN-18` | Committed permanent artifact corrupt: `CORRUPT_RECORD`, no overwrite/republish | not started |\"\"\")\ns=s.replace(\"Additional scenario tests: `T-SCEN-01`..`T-SCEN-16` (16 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-40`, not started.\",\n\"Additional scenario tests: `T-SCEN-01`..`T-SCEN-18` (18 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-44`, not started.\")\ns=s.replace(\"| `T-ARCH-40` | ledger reserved/failed/committed timing and commit-projection repair | not started |\",\n\"\"\"| `T-ARCH-40` | ledger reserved/failed/committed timing and commit-projection repair | not started |\n| `T-ARCH-41` | `record_hash` field-level projection excludes `artifact_binding.record_hash` and other result-carrying fields | not started |\n| `T-ARCH-42` | canonical digest vs file-byte hash; retry stability; risk/provenance timestamps preserved; actual file hash verified | not started |\n| `T-ARCH-43` | recovery terminal-first check: committed+verified+identity match -> idempotent success without `recovery/` | not started |\n| `T-ARCH-44` | committed identity conflict/corrupt permanent artifacts -> typed result; no overwrite/republish | not started |\"\"\")\ns=s.replace(\"- The scenario tests `T-SCEN-01`..`T-SCEN-16` cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, and commit/ledger-update interruption. They are planned, not executed.\",\n\"- The scenario tests `T-SCEN-01`..`T-SCEN-18` cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, and committed-publication corruption. They are planned, not executed.\")\np.write_text(s)\np=Path('docs/architecture/evaluation-table.md')\ns=p.read_text()\ns=s.replace(\"| Scenario matrix T-SCEN-01..16 | Normal, business block, system error, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export, cleanup-after-read, brief failure, uncommitted-memory coordination, old-process lock/lease, PM proposal source, failed-version retry, commit/ledger-update interruption | not started |\",\n\"| Scenario matrix T-SCEN-01..18 | Normal, business block, system error, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export, cleanup-after-read, brief failure, uncommitted-memory coordination, old-process lock/lease, PM proposal source, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, committed-publication corruption | not started |\")\ns=s.replace(\"| Permanent hash DAG | binding no terminal hash; no cycles; declared order | not started |\",\n\"| Permanent hash DAG | binding no terminal hash; no cycles; declared order; `record_hash` self-exclusion | not started |\\n| record_hash projection | field-level exclusion, canonical digest vs file hash, retry/risk-timestamp stability | not started |\\n| Recovery terminal-first | committed+verified -> idempotent without `recovery/`; conflict/corrupt typed; no overwrite | not started |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.6s)

_Thinking:_

Now record_hash projection section. Add §9.6.6 after hash DAG? We have §9.6.5 hash DAG. Add "#### 9.6.6 record_hash projection and file hashes" with details. Need align timestamps. Let's add.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"\"\"- Computation order is fixed as above; a later artifact may hash an earlier one, never the reverse.\n\n---\n\n## 10. Entry points and adaptation\"\"\",\n\"\"\"- Computation order is fixed as above; a later artifact may hash an earlier one, never the reverse.\n\n#### 9.6.6 record_hash projection and file-byte hashes\n\n`record_hash` is a **canonical content digest**, not `sha256(record.json bytes)`.\n\n1. Build the canonical content projection.\n2. **Exclude** `artifact_binding.record_hash` and every other field that carries the computed result or a derivative of it (including `publication_ref.record_hash`, binding self-hash, terminal-manifest hash, file hashes, commit-evidence hash).\n3. Compute `record_hash = SHA-256(canonical projection)`.\n4. Fill `artifact_binding.record_hash`.\n5. Serialize `record.json` and `binding.json` to bytes.\n6. Compute each file's byte-level SHA-256 for `publication_ref`.\n7. Build the terminal manifest from the file hashes.\n\n**Excluded volatile run fields** (only those allowed by the requirement): run-level `generated_at`, `evaluated_at`, `finished_at`, `run_clock.now_utc`, local absolute paths, cache counters, computed snapshot timestamps, and any terminal/file/self hash.\n\n**Preserved evidence timestamps**: risk `evaluated_at`, valuation time/cutoff, attempt/evidence timestamps, provenance timestamps, filing `filed_at`, and other source-evidence timestamps are retained in their own evidence fields and are not treated as run-level volatile fields. A change in risk evidence timestamp must change the risk evidence digest/record projection where required, not be silently dropped by the record-hash exclusion.\n\nA retry must produce the same `record_hash` for the same canonical decision content. The file-byte hash may differ only if serialization bytes change; the two hash kinds must not be conflated.\n\n---\n\n## 10. Entry points and adaptation\"\"\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.2s)

_Thinking:_

Update hash DAG record.json row to reference §9.6.6 and self-exclusion. Also binding row.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"| `record.json` | Canonical `FinalizedRunRecord` content and `artifact_binding` fields | Run-level generated/evaluated/finished timestamps, local paths, cache counters, terminal-manifest hash, recovery-snapshot hash | 1 |\",\n\"| `record.json` | Canonical `FinalizedRunRecord` content and `artifact_binding` fields, using the §9.6.6 projection with `artifact_binding.record_hash` and all result-carrying hashes removed | Run-level generated/evaluated/finished timestamps, `run_clock.now_utc`, local paths, cache counters, terminal-manifest hash, recovery-snapshot hash, record/self/file hashes | 1 |\")\ns=s.replace(\"| `binding.json` | `artifact_binding` fields plus `record_hash` | Terminal-manifest hash, its own file hash, recovery-snapshot digest, commit-evidence hash | 2 |\",\n\"| `binding.json` | `artifact_binding` fields plus the already-computed `record_hash` | Terminal-manifest hash, its own file hash, recovery-snapshot digest, commit-evidence hash, any field that would feed back into `record_hash` | 2 |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.5s)

_Thinking:_

Add invariant INV-A-41 record_hash projection. Update inventory and detailed section/verification summary.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/invariants.md')\ns=p.read_text()\ns=s.replace(\"| INV-A-40 | Permanent artifacts form an acyclic hash DAG; `binding.json` never contains the terminal-manifest hash, and no file hashed by the terminal manifest contains that hash. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService` | Hash-DAG ordering/cycle tests | Reject cyclic candidate; no commit | Design only |\",\n\"| INV-A-40 | Permanent artifacts form an acyclic hash DAG; `binding.json` never contains the terminal-manifest hash, and no file hashed by the terminal manifest contains that hash. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationSnapshotStore`, `MemoryService` | Hash-DAG ordering/cycle tests | Reject cyclic candidate; no commit | Design only |\\n| INV-A-41 | `record_hash` is computed from a canonical content projection that excludes `artifact_binding.record_hash` and every result-carrying hash; content digest and file-byte hash are separate; only specified volatile run fields are excluded and risk/provenance timestamps are preserved. | `INV-01`, `FR-02`, `FR-04` | `SafetyGate`, `ArtifactPublisher`, `Canonicalizer` | Self-exclusion/retry/timestamp/file-hash tests | Reject self-referential or unstable record hash | Design only |\")\ns=s.replace(\"\"\"---\n\n## 4. Planned verification summary\"\"\",\n\"\"\"### INV-A-41 — record_hash content projection\n\n- **Statement**: `record_hash` is computed from a canonical content projection with `artifact_binding.record_hash` and all derivative/result-carrying hashes removed; the full record with a populated self-hash is never serialized as the hash input. The order is canonical content -> `record_hash` -> fill binding -> serialize -> file-byte SHA-256 -> terminal manifest. `record_hash` (content digest) and file-byte hashes are distinct. Only the requirement's volatile run-level timestamps are excluded; risk and provenance evidence timestamps are preserved.\n- **Source**: `INV-01`, `FR-02`, `FR-04`.\n- **Enforcement**: `SafetyGate`, `ArtifactPublisher`, `Canonicalizer`.\n- **Verification**: self-digest exclusion; retry stability; risk evidence timestamp change; actual file byte hash verification; no field feedback cycle.\n- **Fallback**: reject record; no commit; manual review.\n- **Status**: design only.\n\n---\n\n## 4. Planned verification summary\"\"\")\ns=s.replace(\"| Permanent hash DAG | INV-A-40 |\",\"| Permanent hash DAG | INV-A-40 |\\n| record_hash projection | INV-A-41 |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.0s)

_Thinking:_

Update runtime POL-PUB / POL-SNAP with record_hash projection. Add bullet.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/runtime-policy-catalog.md')\ns=p.read_text()\ns=s.replace(\"  - permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; an optional `diagnostics/commit_evidence.json` is audit-only;\",\n\"  - permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; an optional `diagnostics/commit_evidence.json` is audit-only;\\n  - `record_hash` uses the §9.6.6 field-level projection with `artifact_binding.record_hash` and all result-carrying hashes removed; content digest and file-byte hash are distinct; only specified volatile run timestamps are excluded and risk/provenance evidence timestamps are preserved;\")\np.write_text(s)\np=Path('docs/architecture/adr/002-full-scope-add-r.md')\ns=p.read_text()\ns=s.replace(\"- Permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; optional `diagnostics/commit_evidence.json` is audit-only.\",\n\"- Permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; optional `diagnostics/commit_evidence.json` is audit-only. `record_hash` uses the field-level projection in blueprint §9.6.6: build canonical content, exclude `artifact_binding.record_hash` and all result-carrying hashes, compute the content digest, fill binding, serialize, compute file-byte hashes, then build the terminal manifest.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.7s)

_Thinking:_

Update ADR 001 maybe record_hash. Add bullet.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/adr/001-run-governance.md')\ns=p.read_text()\ns=s.replace(\"- `PublicationSnapshotStore` holds permanent committed records. `RecoverySnapshotStore` holds temporary pending envelopes. History and export read the permanent snapshot and revalidate on every read. Permanent artifacts form an acyclic hash DAG: `binding.json` has no terminal-manifest hash; the manifest hashes permanent files; no hashed file contains the manifest hash.\",\n\"- `PublicationSnapshotStore` holds permanent committed records. `RecoverySnapshotStore` holds temporary pending envelopes. History and export read the permanent snapshot and revalidate on every read. Permanent artifacts form an acyclic hash DAG: `binding.json` has no terminal-manifest hash; the manifest hashes permanent files; no hashed file contains the manifest hash. `record_hash` is a canonical content digest with `artifact_binding.record_hash` and result-carrying hashes excluded; file-byte hashes are separate.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.0s)

_Thinking:_

Update open decisions ARCH-OD-23 with record_hash projection maybe. Add.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/open-decisions.md')\ns=p.read_text()\ns=s.replace(\"- **Recommendation (not approved)**: use the `publication/`, `recovery/`, `locks/`, `diagnostics/` layout in blueprint §9.6.1. Formal report/history/export/memory binding validation depend only on `publication/` + terminal manifest; `recovery/` is temporary and may be cleaned; a terminal `recovery_snapshot_summary` is audit-only. The hash DAG is acyclic: `binding.json` contains no terminal-manifest hash; the manifest hashes permanent files including binding; no hashed file contains the manifest hash; optional `commit_evidence.json` is audit-only.\",\n\"- **Recommendation (not approved)**: use the `publication/`, `recovery/`, `locks/`, `diagnostics/` layout in blueprint §9.6.1. Formal report/history/export/memory binding validation depend only on `publication/` + terminal manifest; `recovery/` is temporary and may be cleaned; a terminal `recovery_snapshot_summary` is audit-only. The hash DAG is acyclic: `binding.json` contains no terminal-manifest hash; the manifest hashes permanent files including binding; no hashed file contains the manifest hash; optional `commit_evidence.json` is audit-only. `record_hash` uses the §9.6.6 projection excluding `artifact_binding.record_hash` and result-carrying hashes; content digest and file-byte hash are distinct.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.8s)

_Thinking:_

Update trace T-ARCH-41/42 descriptions already. T-ARCH-43/44 recovery. Need add T-SCEN-17/18 and T-ARCH-41..44 to trace. Done. Update counts 18/44. Done.

Update evaluation scenario row 01..18 and measurement rows. Done partly; check counts.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -n \"T-SCEN-01\\.\\.18\\|record_hash\\|Recovery terminal\\|Scenario matrix\" docs/architecture/evaluation-table.md; grep -n \"T-SCEN-17\\|T-SCEN-18\\|T-ARCH-4[1-4]\" docs/architecture/trace-matrix.md"
}
```

**Output:**
```
252:| Scenario matrix T-SCEN-01..18 | Normal, business block, system error, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export, cleanup-after-read, brief failure, uncommitted-memory coordination, old-process lock/lease, PM proposal source, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, committed-publication corruption | not started |
256:| Permanent hash DAG | binding no terminal hash; no cycles; declared order; `record_hash` self-exclusion | not started |
257:| record_hash projection | field-level exclusion, canonical digest vs file hash, retry/risk-timestamp stability | not started |
258:| Recovery terminal-first | committed+verified -> idempotent without `recovery/`; conflict/corrupt typed; no overwrite | not started |
253:Additional scenario tests: `T-SCEN-01`..`T-SCEN-18` (18 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-44`, not started.
275:| `T-SCEN-17` | Recovery after cleanup: terminal-first idempotent success without recovery directory | not started |
276:| `T-SCEN-18` | Committed permanent artifact corrupt: `CORRUPT_RECORD`, no overwrite/republish | not started |
322:| `T-ARCH-41` | `record_hash` field-level projection excludes `artifact_binding.record_hash` and other result-carrying fields | not started |
323:| `T-ARCH-42` | canonical digest vs file-byte hash; retry stability; risk/provenance timestamps preserved; actual file hash verified | not started |
324:| `T-ARCH-43` | recovery terminal-first check: committed+verified+identity match -> idempotent success without `recovery/` | not started |
325:| `T-ARCH-44` | committed identity conflict/corrupt permanent artifacts -> typed result; no overwrite/republish | not started |
360:- The scenario tests `T-SCEN-01`..`T-SCEN-18` cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, and committed-publication corruption. They are planned, not executed.

```

---

## Assistant (Build · DeepSeek Flash · 10.6s)

_Thinking:_

Good.

### SEC field provenance/derivation deeper
Need update §9.6.4 with explicit field classes and derivation rules. Current has "Source-field ownership" but not two classes and "filing fiscal year/quarter not each fact's period identity". Need rewrite that bullet into a structured classification.

Let's replace the output schema and source-field ownership with a more explicit contract:

- `disclosure_fields` (preserve raw evidence):
  - `subject_id/issuer_cik`, `accession_no`, `filing_ref`, `filed_at`, `form`, `source_fact_ref`, raw `concept`/tag, raw `value`, raw `unit`, raw `currency`, raw period fields if present, raw fiscal fields if present, raw sign/capex presentation, explicit restatement/supersession identifiers.
- `canonical_fields` (validated or derived by versioned rules):
  - `fact_id` (derived stable identity), `canonical_concept`, `canonical_period_start/end`, `fiscal_year/quarter` (per fact, derived only from explicit fact period evidence; not copied from filing-level), `span`, `cumulative_duration_days`, `canonical_sign`, `canonical_unit/currency` (no FX conversion), `restates_fact_id/supersedes` (only explicit).
- `derivation` metadata: `normalization_rule_version`, `derived_fields[]`, `input_evidence_refs[]`, `source_refs[]`, `status: original|normalized|derived|ambiguous|unavailable`, `reason`.
- Responsibilities:
  - Adapter preserves disclosure fields and source refs; does not infer canonical period/fiscal/quarter/sign.
  - Normalizer validates, canonicalizes, derives using explicit evidence/versioned rules; retains raw values alongside canonical; records derivation.
  - Filing-level fiscal year/quarter is metadata of the filing, not each fact's period identity. Each fact must have its own period identity or explicit derivation evidence.
  - Missing/ambiguous -> `FactUnavailableError`/`FactAmbiguousError`.
  - No date proximity/value equality/default guessing.

Update output schema to show `raw` and `canonical` subobjects maybe. Let's rewrite the contract section entirely. Use python replace from `- **Output**...` through `- **Errors**` maybe. Let's do careful.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\nold=\"\"\"- **Output** (returned by `SecEdgarAdapter`, normalized by `FinancialFactService`): each fact is a self-describing record, not an unlinked row plus a separate filing list.\n  ```text\n  {subject_id, source: \"SEC EDGAR\", source_retrieved_at,\n   facts: [{\n     fact_id,\n     subject_id,                       # CIK or equivalent issuer identity\n     accession_no,                     # disclosure identifier\n     filing_ref,                       # locatable filing reference\n     filed_at,                         # disclosure time\n     form,                             # 10-K, 10-Q, ...\n     concept, value, unit, currency,\n     period_start, period_end,\n     fiscal_year, fiscal_quarter,\n     span: annual|quarter|ytd|instant,\n     cumulative_duration_days,\n     sign,\n     restates_fact_id?,                # explicit restatement/alternative lineage\n     supersedes?,\n     source_fact_ref?                  # raw SEC fact/table reference\n   }],\n   provenance: {...}}\n  ```\n- **Source-field ownership**: `subject_id`, `accession_no`, `filing_ref`, `filed_at`, `form`, `concept`, `period_*`, `fiscal_*`, `span`, `unit`, `currency`, `value`, `sign`, and any restatement/supersession link are preserved from the raw SEC filing/fact data. `FinancialFactService` may validate, canonicalize, or derive `fact_id`, `cumulative_duration_days`, and normalized comparisons, but must preserve the source linkage. If any required source field is missing, or more than one fact remains a plausible source, return `FactUnavailableError`/`FactAmbiguousError`; never infer a link from date proximity or equal value.\n- **Errors**: `VendorUnavailableError`, `NoMarketDataError`, `VendorNotConfiguredError`, `FactAmbiguousError`, `FactUnavailableError`, mapped by `DataAccessService`; no raw vendor call outside the adapter.\n- The existing `get_income_statement`, `get_balance_sheet`, and `get_cashflow` tools use the same query path, run cache, counters, and provenance. `FinancialFactService` performs period/fact identity validation/normalization; the adapter does not decide metric semantics.\"\"\"\nnew=\"\"\"- **Output** (returned by `SecEdgarAdapter`, normalized by `FinancialFactService`): each fact is a self-describing record, not an unlinked row plus a separate filing list.\n\n  ```text\n  {subject_id, source: \"SEC EDGAR\", source_retrieved_at,\n   facts: [{\n     fact_id,                          # canonical stable id (derived)\n     disclosure: {                     # original evidence, preserved\n       subject_id, accession_no, filing_ref, filed_at, form,\n       source_fact_ref, raw_concept, raw_value, raw_unit, raw_currency,\n       raw_period_start?, raw_period_end?, raw_fiscal_year?, raw_fiscal_quarter?,\n       raw_span?, raw_sign?, restates_fact_id?, supersedes?\n     },\n     canonical: {                      # validated/derived, versioned rules\n       concept, value, unit, currency,\n       period_start, period_end, fiscal_year, fiscal_quarter,\n       span: annual|quarter|ytd|instant,\n       cumulative_duration_days, sign,\n       restates_fact_id?, supersedes?\n     },\n     derivation: {\n       normalization_rule_version, derived_fields[], input_evidence_refs[],\n       source_refs[], status: original|normalized|derived|ambiguous|unavailable, reason?\n     }\n   }],\n   provenance: {...}}\n  ```\n\n- **Disclosure fields (must preserve raw evidence)**: `subject_id`, `accession_no`, `filing_ref`, `filed_at`, `form`, `source_fact_ref`, raw concept/tag, raw value, raw unit, raw currency, raw period fields when present, raw fiscal fields when present, raw sign/capex presentation, and explicit restatement/supersession identifiers. The adapter preserves these; the normalizer may copy/attach them but must not overwrite them.\n- **Canonical fields (validated or derived by versioned rules)**: `fact_id`, canonical concept, canonical period start/end, per-fact fiscal year/quarter, span, cumulative duration, canonical sign, canonical unit/currency (no FX conversion), and explicit restatement/supersession links. The normalizer may derive these only from explicit evidence and a recorded `normalization_rule_version`; each derived field records its input evidence and source references.\n- **Filing-level versus fact-level identity**: a filing's fiscal year/quarter is filing metadata and MUST NOT be copied as every historical fact's period identity. Each fact needs its own period/fiscal identity or explicit derivation evidence. A missing/ambiguous period identity returns `FactUnavailableError`/`FactAmbiguousError`.\n- **Prohibited inference**: never connect a fact to a filing/period by date proximity, equal value, column order, or a default. If more than one fact remains a plausible source, return ambiguity; if required evidence is absent, return unavailable.\n- **Errors**: `VendorUnavailableError`, `NoMarketDataError`, `VendorNotConfiguredError`, `FactAmbiguousError`, `FactUnavailableError`, mapped by `DataAccessService`; no raw vendor call outside the adapter.\n- The existing `get_income_statement`, `get_balance_sheet`, and `get_cashflow` tools use the same query path, run cache, counters, and provenance. `FinancialFactService` performs validation/normalization and records derivation metadata; the adapter does not decide metric semantics.\"\"\"\ns=s.replace(old,new)\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.4s)

_Thinking:_

Update invariants INV-A-30 statement with field classes and no filing-level fiscal copy. Currently says source linkage preserved or explicitly derived; add raw/canonical distinction and no filing-level fiscal copy.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/invariants.md')\ns=p.read_text()\ns=s.replace(\"- **Statement**: Derived metrics use per-fact structured records that each carry subject, accession/disclosure identifier, filing reference, filed-at, form, concept, period identity, fiscal position, span, unit, currency, sign, and restatement/supersession lineage. Source linkage is preserved from raw SEC data or explicitly derived by normalization; missing or multiple plausible sources return unavailable/ambiguous and are never guessed from date proximity or equal value. The fact fetch, metric computation, block append, and conflict check occur after the fundamentals report exists and before research debate consumes it; final publication only persists the existing result. Only facts filed on or before as-of are visible. Near dates, equal values, and same-day multiple accessions are never merged without explicit lineage; ambiguity produces a typed n/a. Formulas are explicit and versioned; TTM uses annual + current YTD - prior matching YTD and never derives a quarter by subtraction. The program-appended metric block is the numeric authority; conflicts with structured claims are disclosed and the contradicted claim is labeled unverified.\",\n\"- **Statement**: Derived metrics use per-fact structured records. **Disclosure fields** (subject, accession/disclosure identifier, filing reference, filed-at, form, source fact reference, raw concept/value/unit/currency/period/fiscal/sign, explicit restatement/supersession identifiers) preserve original evidence. **Canonical fields** (fact_id, canonical concept/period/fiscal identity, span, cumulative duration, canonical sign/unit/currency, explicit lineage) may be validated or derived only by a recorded versioned rule, with input evidence and source references retained. A filing's fiscal year/quarter is not each historical fact's period identity. Missing or multiple plausible sources return unavailable/ambiguous; never use date proximity, equal value, column order, or a default. The fact fetch, metric computation, block append, and conflict check occur after the fundamentals report exists and before research debate consumes it; final publication only persists the existing result. Only facts filed on or before as-of are visible. Formulas are explicit and versioned; TTM uses annual + current YTD - prior matching YTD and never derives a quarter by subtraction. The program-appended metric block is the numeric authority; conflicts with structured claims are disclosed and the contradicted claim is labeled unverified.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.9s)

_Thinking:_

Update runtime POL-FIN with field classes.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/runtime-policy-catalog.md')\ns=p.read_text()\ns=s.replace(\"- **Facts**: each fact carries subject/accession/filing_ref/filed_at/form/concept/period/fiscal position/span/cumulative duration/unit/currency/source/sign/restatement lineage; CIK never substitutes for accession/filing_ref. Source linkage is preserved from raw SEC data or explicitly derived; missing/multiple plausible sources return unavailable/ambiguous and are never guessed from date proximity or equal value.\",\n\"- **Facts**: each fact separates **disclosure fields** (subject/accession/filing_ref/filed_at/form/source_fact_ref and raw concept/value/unit/currency/period/fiscal/sign) that preserve original evidence from **canonical fields** (fact_id/concept/period/fiscal identity/span/cumulative duration/sign/unit/currency/lineage) that may be validated or derived only by a recorded versioned rule with input evidence and source refs. A filing's fiscal year/quarter is not each historical fact's period identity. Missing/multiple plausible sources return unavailable/ambiguous; never use date proximity, equal value, column order, or a default. CIK never substitutes for accession/filing_ref.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.3s)

_Thinking:_

Update ADR 002 §2.3 with disclosure/canonical field classes and no filing-level fiscal copy.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/adr/002-full-scope-add-r.md')\ns=p.read_text()\ns=s.replace(\"- Each fact carries subject, accession/disclosure identifier, filing reference, filed-at, form, concept, periods, fiscal position, span, unit, currency, source, sign, and restatement/supersession lineage. Missing or multiple plausible sources return unavailable/ambiguous; the normalizer never guesses a link from date proximity or equal value.\",\n\"- Each fact separates **disclosure fields** (subject/accession/filing_ref/filed_at/form/source_fact_ref and raw concept/value/unit/currency/period/fiscal/sign) preserved from the source from **canonical fields** (fact_id/concept/per-fact period and fiscal identity/span/cumulative duration/sign/unit/currency/lineage) validated or derived only by a recorded versioned rule with input evidence and source refs. A filing's fiscal year/quarter is not copied as each historical fact's period identity. Missing or multiple plausible sources return unavailable/ambiguous; the normalizer never guesses from date proximity, equal value, column order, or a default.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.8s)

_Thinking:_

Update open decisions ARCH-OD-19 with field classes.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/open-decisions.md')\ns=p.read_text()\ns=s.replace(\"- **Recommendation (not approved)**: after the fundamentals report exists and before Bull/Bear; a `get_structured_financial_facts`-style query through `DataAccessService` returns per-fact records with subject/accession/filing_ref/filed_at/form/concept/period/span/unit/currency/sign and restatement lineage; `FinancialFactService` validates/normalizes them; the existing statement tools use the same adapter/cache/counters. Missing or multiple plausible sources return unavailable/ambiguous; never guess from date proximity or equal value.\",\n\"- **Recommendation (not approved)**: after the fundamentals report exists and before Bull/Bear; a `get_structured_financial_facts`-style query through `DataAccessService` returns per-fact records with separate disclosure fields (subject/accession/filing_ref/filed_at/form/source_fact_ref and raw concept/value/unit/currency/period/fiscal/sign) and canonical fields (fact_id/concept/per-fact period/fiscal identity/span/cumulative duration/sign/unit/currency/lineage). `FinancialFactService` validates/normalizes canonical fields only via recorded versioned rules with input evidence and source refs; a filing's fiscal year/quarter is not copied as each historical fact's period identity. Missing or multiple plausible sources return unavailable/ambiguous; never guess from date proximity, equal value, column order, or a default. The existing statement tools use the same adapter/cache/counters.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.3s)

_Thinking:_

Update trace FR-07 rows to mention disclosure/canonical split and no filing-level fiscal copy. T-ARCH-35 already; update FR-07-AC3 perhaps.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/trace-matrix.md')\ns=p.read_text()\ns=s.replace(\"| `FR-07-AC3` | `FinancialFactService`, `SecEdgarAdapter` | `T-FR07-03` per-fact subject/accession/filing_ref/filed_at; near-date/restatement/as-of; unavailable/ambiguous, no guessing | `MON-FR07-03` silent merge/look-ahead/guessed link | design only; not started |\",\n\"| `FR-07-AC3` | `FinancialFactService`, `SecEdgarAdapter` | `T-FR07-03` disclosure vs canonical fields; per-fact period/fiscal identity; near-date/restatement/as-of; unavailable/ambiguous, no guessing | `MON-FR07-03` filing-level fiscal copy/silent merge/look-ahead/guessed link | design only; not started |\")\ns=s.replace(\"| `T-ARCH-35` | SEC structured query input/output contract; per-fact filing/subject/period/unit/currency/lineage; unavailable/ambiguous, no guessing | not started |\",\n\"| `T-ARCH-35` | SEC structured query contract; disclosure fields preserved; canonical fields derived with rule/version/evidence; per-fact period identity; unavailable/ambiguous, no guessing | not started |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.5s)

_Thinking:_

### Recovery first-check trace/validation
Need update T-SCEN-17/18 counts in trace/eval; done. Add T-ARCH-43/44 descriptions. done.

Need update recovery §11.3 says "read terminal manifest outside locks" and "if completed corrupt return CORRUPT_RECORD". Good. But it says "if completed + identity conflict" before "corrupt". Fine. Need ensure "committed + corrupt" if identity matches but permanent artifacts corrupt: return CORRUPT_RECORD. Good.

Need update runtime POL-REC first check; done.

Need update memory design §12; done.

Need update ADR 001 recovery bullet maybe "first check terminal manifest". Search.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"first.*terminal\\|terminal manifest first\\|committed.*idempotent\\|without requiring \\`recovery/\\`\\|CORRUPT_RECORD\" architecture-blueprint.md docs/architecture/adr/001-run-governance.md docs/architecture/adr/002-full-scope-add-r.md docs/architecture/invariants.md docs/architecture/memory-design.md docs/architecture/runtime-policy-catalog.md | head -40"
}
```

**Output:**
```
architecture-blueprint.md:63:17. Recovery checks the terminal manifest first: committed+verified+identity match is idempotent success without requiring `recovery/`; committed identity conflict or permanent-artifact corruption returns a typed conflict/corrupt result and never overwrites or auto-republishes. Only uncommitted records read the recovery snapshot.
architecture-blueprint.md:699:            return CORRUPT_RECORD; do not overwrite or republish
architecture-blueprint.md:725:- The terminal manifest is checked first. A committed, verified, identity-matching publication is an idempotent success even if `recovery/` no longer exists.
architecture-blueprint.md:726:- A committed identity conflict returns `RUN_ID_CONFLICT`; committed-but-corrupt permanent artifacts return `CORRUPT_RECORD`. Neither path overwrites the terminal manifest or auto-republishes.
architecture-blueprint.md:745:  -> return verified publication or NOT_FOUND/CORRUPT_RECORD
architecture-blueprint.md:966:- A post-commit read failure MUST NOT replace the committed terminal manifest with `failed` or any other status. The terminal manifest is immutable commit evidence. A separate diagnostic record identifies the corrupt run; `HistoryService`/`ExportService` return `CORRUPT_RECORD` and do not return partial content.
architecture-blueprint.md:981:- Recovery **first** reads the terminal manifest and verifies the permanent publication. A committed, INV-01-valid, identity-matching publication returns idempotent success and does not require `recovery/`.
architecture-blueprint.md:982:- A committed identity conflict returns `RUN_ID_CONFLICT`; a committed publication with corrupt permanent artifacts returns `CORRUPT_RECORD`. Neither overwrites the terminal manifest or auto-republishes.
architecture-blueprint.md:1008:- A completed publication with a different identity returns `RUN_ID_CONFLICT`; a completed publication whose permanent artifacts fail verification returns `CORRUPT_RECORD`. Neither overwrites the terminal manifest or auto-republishes.
architecture-blueprint.md:1035:- A post-commit validation failure returns `CORRUPT_RECORD`, leaves the committed terminal manifest untouched, and records an independent diagnostic. It is never converted into a new `failed` terminal state or a second publication.
architecture-blueprint.md:1066:| Post-commit read validation fails | Unchanged; committed formal result | Committed formal decision remains immutable | Committed terminal manifest is not overwritten; independent corruption diagnostic | Does not republish; record is quarantined/corrupt | `CORRUPT_RECORD`; no partial content | Unchanged | `completed` commit evidence, marked corrupt for readers |
architecture-blueprint.md:1072:| History corrupt record | Unchanged | n/a | n/a | n/a | `CORRUPT_RECORD`; no partial content | n/a | n/a |
architecture-blueprint.md:1090:| Post-commit corruption | Committed terminal manifest is preserved; record rejected as success; independent corruption diagnostic; history/export return `CORRUPT_RECORD`; no compensating `failed` manifest | `T-SCEN-05`: tamper one bound artifact after commit; assert immutable manifest bytes, diagnostic record, history/export rejection, no second publication |
architecture-blueprint.md:1102:| Recovery after cleanup | Successful publication and recovery-directory cleanup, then recovery is called again; terminal manifest first gives idempotent success without `recovery/` | `T-SCEN-17`: commit, validate, cleanup `recovery/`, run recovery again; assert idempotent success and no snapshot requirement |
architecture-blueprint.md:1103:| Committed publication corrupt | Terminal manifest committed but a permanent artifact fails verification; recovery returns `CORRUPT_RECORD`, does not overwrite the manifest, and does not auto-republish | `T-SCEN-18`: tamper a permanent file after commit, run recovery; assert immutable manifest, typed corruption, no second publication |
architecture-blueprint.md:1176:| Post-commit corruption | Not applicable | Keep committed terminal manifest immutable; independent diagnostic; reject as `CORRUPT_RECORD` |
docs/architecture/adr/002-full-scope-add-r.md:57:- Recovery first reads the terminal manifest and verifies the permanent publication. Committed + INV-01 + identity match is idempotent success without `recovery/`; committed + identity conflict -> `RUN_ID_CONFLICT`; committed + corrupt permanent artifacts -> `CORRUPT_RECORD`; neither overwrites or auto-republishes. Only an uncommitted record continues: memory plan/reservation -> recovery snapshot -> idempotent memory write -> permanent snapshot -> terminal candidate -> commit -> read-back -> cleanup.
docs/architecture/invariants.md:56:| INV-A-26 | History returns only committed publications that pass read-time INV-01; pending/failed/quarantined are not successful history. | `FR-05`, `FR-06`, `INV-01` | `HistoryService`, `PublicationSnapshotStore` | Status/history visibility tests | Exclude; return NOT_FOUND/CORRUPT_RECORD | Design only |
docs/architecture/invariants.md:57:| INV-A-27 | Committed report sections come only from the permanent publication snapshot and recorded capability set; no foreign/stale/mixed sections. | `FR-05`, `INV-01` | `ReportSectionManifestBuilder`, `PublicationSnapshotStore` | Section isolation/tamper tests | Fail read as CORRUPT_RECORD | Design only |
docs/architecture/invariants.md:58:| INV-A-28 | Publication recovery checks the terminal manifest first: committed+verified+identity match is idempotent success without `recovery/`; conflict/corrupt are typed; only uncommitted records use saved recovery records; at most one committed publication. | `FR-06` | `RecoveryService`, `ArtifactPublisher` | Terminal-first/model-free/duplicate/retry/corrupt tests | Quarantine; no publish; no overwrite; bounded retry | Design only |
docs/architecture/invariants.md:64:| INV-A-34 | A post-commit read failure never overwrites the committed terminal manifest; the record is rejected as success and an independent diagnostic records the corruption. | `FR-02`, `INV-01`, `FR-05` | `ArtifactPublisher`, `PublicationStatusReader`, `HistoryService` | Post-commit tamper tests | Keep immutable manifest; `CORRUPT_RECORD`; no second publication | Design only |
docs/architecture/invariants.md:137:- **Fallback**: pre-commit: keep the last running manifest and write `failed`; post-commit: immutable manifest, `CORRUPT_RECORD`, independent diagnostic; retry without model re-run.
docs/architecture/invariants.md:304:- **Statement**: History visibility is exactly the committed state: terminal manifest `run_status=completed` plus successful read-time INV-01. Analysis completion, pending recovery, failed publication, and quarantined records are not successful history. Listing excludes non-committed/corrupt records; `get_run` returns `NOT_FOUND` or `CORRUPT_RECORD` without partial content.
docs/architecture/invariants.md:317:- **Fallback**: fail read as `CORRUPT_RECORD`; do not return complete.
docs/architecture/invariants.md:322:- **Statement**: Recovery first reads the terminal manifest and verifies the permanent publication. A committed, INV-01-valid, identity-matching publication is an idempotent success without requiring `recovery/`; a committed identity conflict is `RUN_ID_CONFLICT`; committed permanent-artifact corruption is `CORRUPT_RECORD`; neither overwrites the terminal manifest or auto-republishes. Only an uncommitted/absent record continues with saved, verified, redacted formal records and fixed render inputs. Recovery does not re-run analysis or create a separate archive transaction. It preserves the original `run_id`, makes no LLM/external/graph/settlement/reflection calls, and yields at most one committed publication per `run_id` and decision identity.
docs/architecture/invariants.md:376:- **Statement**: A failure during post-commit read validation never overwrites the committed terminal manifest with `failed` or any other status. The committed manifest remains immutable evidence. The record is rejected as a successful formal result, history/export return `CORRUPT_RECORD`, and an independent diagnostic records the anomaly. No second publication or compensating terminal state is created.
docs/architecture/invariants.md:430:- **Statement**: Permanent artifacts form a directed acyclic hash graph. `record_hash` is computed first; `binding.json` covers `artifact_binding` plus `record_hash` but excludes the terminal-manifest hash, its own file hash, the recovery digest, and commit-evidence hash. Section/final-state/risk/metric/memory files are hashed next. The recovery snapshot may carry terminal-candidate identity but not the final terminal-manifest hash. The terminal manifest covers `publication_ref` hashes (including `binding.json`) and may hold a `recovery_snapshot_summary` as audit-only; it never hashes itself. An optional `diagnostics/commit_evidence.json` may record the terminal-manifest hash after commit but is outside the permanent hashed set and is not a commit authority.
docs/architecture/memory-design.md:254:- Recovery first reads the terminal manifest and verifies the permanent publication. A committed, verified, identity-matching publication is idempotent success without requiring `recovery/`; a committed identity conflict is `RUN_ID_CONFLICT`; committed permanent-artifact corruption is `CORRUPT_RECORD`; neither overwrites the manifest or auto-republishes. Only an uncommitted record continues with the recovery snapshot.
docs/architecture/runtime-policy-catalog.md:224:- **Handling**: the record is rejected as successful formal output; history/export return `CORRUPT_RECORD` without partial content; an independent diagnostic records the corrupt run, failed check, and artifact references. Manual repair is required.
docs/architecture/runtime-policy-catalog.md:241:- **Retrieval**: `get_run` revalidates terminal manifest, binding, complete report, section manifest, and permanent references; unknown -> `NOT_FOUND`; corrupt -> `CORRUPT_RECORD`; no partial content.
docs/architecture/runtime-policy-catalog.md:250:- **First check**: read the terminal manifest and verify the permanent publication before reading `recovery/`. Committed + INV-01 + identity match -> idempotent success (no snapshot required); committed + identity conflict -> `RUN_ID_CONFLICT`; committed + corrupt permanent artifacts -> `CORRUPT_RECORD`; neither overwrites the manifest or auto-republishes.
docs/architecture/runtime-policy-catalog.md:251:- **Continuation order**: only for an uncommitted record, determine the memory reuse/new plan and reserve the version -> write the recovery snapshot containing the plan -> idempotent memory write -> permanent snapshot write/validate -> terminal candidate + INV-01 -> commit -> post-commit read -> cleanup.
docs/architecture/runtime-policy-catalog.md:256:- **Identity**: terminal manifest first. Completed + matching identity -> idempotent success without `recovery/`; different content -> `RUN_ID_CONFLICT`; committed but permanent artifacts corrupt -> `CORRUPT_RECORD`; only uncommitted/absent continues with the recovery snapshot.
docs/architecture/runtime-policy-catalog.md:265:- **Workload**: 100 committed publications + 10 pending valid snapshots; fixed 12-section report map; one risk evidence object with policy reference; one required memory idempotent write; rendered output and snapshot each <= 1,048,576 bytes; local supported filesystem; no competing writer.

```

---

## Assistant (Build · DeepSeek Flash · 3.4s)

_Thinking:_

Recovery consistency good. Need update ADR 001 maybe first check? Search "recovery first" in ADR001.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -n \"Recovery\\|recovery\" docs/architecture/adr/001-run-governance.md | head -20"
}
```

**Output:**
```
21:- No native lifecycle manifest, no unified coverage state, no coverage-aware safety gate, no deterministic portfolio-risk check, no history/recovery interface, no structured metric block, and no bounded downstream brief.
28:- `FR-06`: model-free startup recovery of pending publication.
29:- `QR-02`: bounded recovery performance.
46:- `ArtifactPublisher` is the only formal publication writer. It determines the memory plan/reservation, writes/verifies the recovery snapshot before promising recovery, writes the original memory entry idempotently, persists/validates the permanent-snapshot files before the terminal commit, validates the terminal candidate, atomically commits, reads back, and cleans temporary material last. Recovery drives the same publisher and commit; it has no separate transaction or marker.
48:- `PublicationSnapshotStore` holds permanent committed records. `RecoverySnapshotStore` holds temporary pending envelopes. History and export read the permanent snapshot and revalidate on every read. Permanent artifacts form an acyclic hash DAG: `binding.json` has no terminal-manifest hash; the manifest hashes permanent files; no hashed file contains the manifest hash. `record_hash` is a canonical content digest with `artifact_binding.record_hash` and result-carrying hashes excluded; file-byte hashes are separate.
50:- `ContextAssembler` remains the only context entry. `DownstreamBriefBuilder` generates/reuses the five-role brief before context delivery, using the program coverage view and its version; for those roles the brief replaces the four full analyst reports. It does not mutate full/formal/history/recovery artifacts.
51:- `MemoryService` remains the only memory writer. `MemoryReservationStore` provides a persistent, append-only allocation history with a high-water mark over all historical allocations, including failed; a failed version is never reissued; retries/recovery reuse their own reservation; `committed` is a derived projection, not a second commit condition. The reuse/new plan is fixed before the recovery snapshot.
52:- Normal publication and recovery share one `RunOwnershipLock`, owner identity, and fencing token. The OS file lock is short-lived; the logical lease records activity. Ownership is checked in the same critical section as the protected write; takeover acquires the file lock and increments fencing; lease expiry does not release the file lock. The lock order is run lock then memory lock. Recovery reads/parses/renders outside the locks; staged content is revalidated against current ownership/publication state before use.
56:- Implementation is phased: foundations; core closed loop + Portfolio Manager/model proposal + minimum memory identity/idempotency + FR-02-required section manifest/permanent snapshot/recovery snapshot; memory enhancements; financial metrics; history/startup scan/export/benchmark; brief/context; behavior evaluation. Approved FR-02/INV-01/SB-01 obligations are not downgraded by draft dependencies.
58:- Approved `FR-02` recovery-snapshot generation, section manifest, terminal manifest, and binding; approved `INV-01` binding/read-time verification; and approved `SB-01` risk-branch behavior remain obligations even though related draft requirements exist. Draft status limits completion/acceptance claims, not approved behavior.
64:3. Publication lifecycle: extend the publisher with permanent/recovery snapshots and claim/fencing (chosen over a separate archive transaction, graph re-run, or directory-scan history).
86:- Explicit permanent/temporary record split for history and recovery.
90:- Cross-cutting integration across CLI, graph, tools, reporting, memory, history, export, and recovery.
93:- Risk and recovery add new failure modes that must be proven.
111:Every run fact is appended to a ledger; reducers produce availability, metrics, gate input, risk result, publication, and recovery.
134:- Under the same required coverage (CLI, programmatic, backtest, checkpoint, recovery), the change surface becomes high.
155:All candidates are compared under the same gate, binding, redaction, and history/recovery contract. No candidate has been implemented. All ratings except baseline facts are design expectations.
164:4. The permanent/temporary publication split gives history and recovery a clear source of truth without a second commit marker.
177:- one recovery snapshot, claim/fencing, and model-free completion;
194:- Recovery completes the existing publication without model/data/graph calls and without a second commit authority.

```

---

## Assistant (Build · DeepSeek Flash · 4.0s)

_Thinking:_

ADR001 line 46 says "writes/verifies recovery snapshot before promising recovery" but first check terminal manifest not mentioned. Add a sentence to that bullet.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/adr/001-run-governance.md')\ns=p.read_text()\ns=s.replace(\"- `ArtifactPublisher` is the only formal publication writer. It determines the memory plan/reservation, writes/verifies the recovery snapshot before promising recovery, writes the original memory entry idempotently, persists/validates the permanent-snapshot files before the terminal commit, validates the terminal candidate, atomically commits, reads back, and cleans temporary material last. Recovery drives the same publisher and commit; it has no separate transaction or marker.\",\n\"- `ArtifactPublisher` is the only formal publication writer. It determines the memory plan/reservation, writes/verifies the recovery snapshot before promising recovery, writes the original memory entry idempotently, persists/validates the permanent-snapshot files before the terminal commit, validates the terminal candidate, atomically commits, reads back, and cleans temporary material last. Recovery first checks the terminal manifest: committed+verified+identity match is idempotent success without `recovery/`; committed conflict/corruption returns a typed result without overwrite or republish; only uncommitted records proceed with the recovery snapshot. Recovery drives the same publisher and commit; it has no separate transaction or marker.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 5.5s)

_Thinking:_

Now check record_hash projection in ADR 002 maybe only hash DAG; added. ADR 001 added. Invariants added. Runtime added. Open decisions added. Trace added. Evaluation added. Good.

Need add record_hash scenarios to trace T-ARCH-41/42, counts. Done.

Need update trace T-SCEN-17/18 and counts 18. Done.

Need update evaluation scenario row 01..18. Done.

Need update §13.2 scenario table includes T-SCEN-17/18. Done.

Need update blueprint §1.3 item 17 for recovery first; done. Maybe add item 18 for record_hash projection? §1.3 has 17 items; record_hash not explicitly. Add item 18? Let's add to §1.3:
18. record_hash field-level projection...; 19 SEC field classes... Actually §1.3 is a changelog, not necessary but good. Add.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"17. Recovery checks the terminal manifest first: committed+verified+identity match is idempotent success without requiring `recovery/`; committed identity conflict or permanent-artifact corruption returns a typed conflict/corrupt result and never overwrites or auto-republishes. Only uncommitted records read the recovery snapshot.\",\n\"17. Recovery checks the terminal manifest first: committed+verified+identity match is idempotent success without requiring `recovery/`; committed identity conflict or permanent-artifact corruption returns a typed conflict/corrupt result and never overwrites or auto-republishes. Only uncommitted records read the recovery snapshot.\\n18. `record_hash` uses a field-level canonical projection that excludes `artifact_binding.record_hash` and all result-carrying hashes; content digest and file-byte hash are separate, and only specified volatile run fields are excluded while risk/provenance timestamps are preserved.\\n19. SEC facts separate preserved disclosure fields from versioned canonical derivations; a filing's fiscal year/quarter is not copied as each historical fact's period identity, and missing/ambiguous evidence is never guessed.\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.2s)

_Thinking:_

Now check final consistency. Also need update trace matrix total counts: 18 scenarios, 44 arch. Done. Check T-ARCH-41..44 descriptions. Good.

Need update `docs/architecture/evaluation-table.md` scenario row 01..18 and measurement rows. Done.

Need update `docs/architecture/invariants.md` INV-A-41 inventory and verification summary. Done.

Need check table consistency after §9.6.4 schema text? It's code block, not table. Fine.

Need check no stale "filing-level fiscal" or "Source-field ownership" that implies all fields raw. Search.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -rn \"Source-field ownership\\|filing's fiscal\\|filing-level\\|raw SEC data.*all\\|derive.*fiscal\" architecture-blueprint.md docs/architecture | head -30; echo \"=== record hash projection ===\"; grep -rn \"artifact_binding.record_hash\\|canonical content digest\\|file-byte\" architecture-blueprint.md docs/architecture | head -30"
}
```

**Output:**
```
architecture-blueprint.md:65:19. SEC facts separate preserved disclosure fields from versioned canonical derivations; a filing's fiscal year/quarter is not copied as each historical fact's period identity, and missing/ambiguous evidence is never guessed.
architecture-blueprint.md:523:- **Canonical fields (validated or derived by versioned rules)**: `fact_id`, canonical concept, canonical period start/end, per-fact fiscal year/quarter, span, cumulative duration, canonical sign, canonical unit/currency (no FX conversion), and explicit restatement/supersession links. The normalizer may derive these only from explicit evidence and a recorded `normalization_rule_version`; each derived field records its input evidence and source references.
architecture-blueprint.md:524:- **Filing-level versus fact-level identity**: a filing's fiscal year/quarter is filing metadata and MUST NOT be copied as every historical fact's period identity. Each fact needs its own period/fiscal identity or explicit derivation evidence. A missing/ambiguous period identity returns `FactUnavailableError`/`FactAmbiguousError`.
architecture-blueprint.md:834:- No single quarter is derived by subtraction. Zero denominators, non-positive growth bases, zero/negative EPS, missing fields, currency mismatch, unit mismatch, or fiscal-period mismatch produce typed n/a reasons.
docs/architecture/adr/002-full-scope-add-r.md:73:- Each fact separates **disclosure fields** (subject/accession/filing_ref/filed_at/form/source_fact_ref and raw concept/value/unit/currency/period/fiscal/sign) preserved from the source from **canonical fields** (fact_id/concept/per-fact period and fiscal identity/span/cumulative duration/sign/unit/currency/lineage) validated or derived only by a recorded versioned rule with input evidence and source refs. A filing's fiscal year/quarter is not copied as each historical fact's period identity. Missing or multiple plausible sources return unavailable/ambiguous; the normalizer never guesses from date proximity, equal value, column order, or a default.
docs/architecture/invariants.md:340:- **Statement**: Derived metrics use per-fact structured records. **Disclosure fields** (subject, accession/disclosure identifier, filing reference, filed-at, form, source fact reference, raw concept/value/unit/currency/period/fiscal/sign, explicit restatement/supersession identifiers) preserve original evidence. **Canonical fields** (fact_id, canonical concept/period/fiscal identity, span, cumulative duration, canonical sign/unit/currency, explicit lineage) may be validated or derived only by a recorded versioned rule, with input evidence and source references retained. A filing's fiscal year/quarter is not each historical fact's period identity. Missing or multiple plausible sources return unavailable/ambiguous; never use date proximity, equal value, column order, or a default. The fact fetch, metric computation, block append, and conflict check occur after the fundamentals report exists and before research debate consumes it; final publication only persists the existing result. Only facts filed on or before as-of are visible. Formulas are explicit and versioned; TTM uses annual + current YTD - prior matching YTD and never derives a quarter by subtraction. The program-appended metric block is the numeric authority; conflicts with structured claims are disclosed and the contradicted claim is labeled unverified.
docs/architecture/trace-matrix.md:145:| `FR-07-AC3` | `FinancialFactService`, `SecEdgarAdapter` | `T-FR07-03` disclosure vs canonical fields; per-fact period/fiscal identity; near-date/restatement/as-of; unavailable/ambiguous, no guessing | `MON-FR07-03` filing-level fiscal copy/silent merge/look-ahead/guessed link | design only; not started |
docs/architecture/runtime-policy-catalog.md:306:- **Facts**: each fact separates **disclosure fields** (subject/accession/filing_ref/filed_at/form/source_fact_ref and raw concept/value/unit/currency/period/fiscal/sign) that preserve original evidence from **canonical fields** (fact_id/concept/period/fiscal identity/span/cumulative duration/sign/unit/currency/lineage) that may be validated or derived only by a recorded versioned rule with input evidence and source refs. A filing's fiscal year/quarter is not each historical fact's period identity. Missing/multiple plausible sources return unavailable/ambiguous; never use date proximity, equal value, column order, or a default. CIK never substitutes for accession/filing_ref.
docs/architecture/open-decisions.md:370:- **Recommendation (not approved)**: after the fundamentals report exists and before Bull/Bear; a `get_structured_financial_facts`-style query through `DataAccessService` returns per-fact records with separate disclosure fields (subject/accession/filing_ref/filed_at/form/source_fact_ref and raw concept/value/unit/currency/period/fiscal/sign) and canonical fields (fact_id/concept/per-fact period/fiscal identity/span/cumulative duration/sign/unit/currency/lineage). `FinancialFactService` validates/normalizes canonical fields only via recorded versioned rules with input evidence and source refs; a filing's fiscal year/quarter is not copied as each historical fact's period identity. Missing or multiple plausible sources return unavailable/ambiguous; never guess from date proximity, equal value, column order, or a default. The existing statement tools use the same adapter/cache/counters.
=== record hash projection ===
architecture-blueprint.md:64:18. `record_hash` uses a field-level canonical projection that excludes `artifact_binding.record_hash` and all result-carrying hashes; content digest and file-byte hash are separate, and only specified volatile run fields are excluded while risk/provenance timestamps are preserved.
architecture-blueprint.md:535:| `record.json` | Canonical `FinalizedRunRecord` content and `artifact_binding` fields, using the §9.6.6 projection with `artifact_binding.record_hash` and all result-carrying hashes removed | Run-level generated/evaluated/finished timestamps, `run_clock.now_utc`, local paths, cache counters, terminal-manifest hash, recovery-snapshot hash, record/self/file hashes | 1 |
architecture-blueprint.md:549:#### 9.6.6 record_hash projection and file-byte hashes
architecture-blueprint.md:551:`record_hash` is a **canonical content digest**, not `sha256(record.json bytes)`.
architecture-blueprint.md:554:2. **Exclude** `artifact_binding.record_hash` and every other field that carries the computed result or a derivative of it (including `publication_ref.record_hash`, binding self-hash, terminal-manifest hash, file hashes, commit-evidence hash).
architecture-blueprint.md:556:4. Fill `artifact_binding.record_hash`.
architecture-blueprint.md:565:A retry must produce the same `record_hash` for the same canonical decision content. The file-byte hash may differ only if serialization bytes change; the two hash kinds must not be conflated.
docs/architecture/adr/001-run-governance.md:48:- `PublicationSnapshotStore` holds permanent committed records. `RecoverySnapshotStore` holds temporary pending envelopes. History and export read the permanent snapshot and revalidate on every read. Permanent artifacts form an acyclic hash DAG: `binding.json` has no terminal-manifest hash; the manifest hashes permanent files; no hashed file contains the manifest hash. `record_hash` is a canonical content digest with `artifact_binding.record_hash` and result-carrying hashes excluded; file-byte hashes are separate.
docs/architecture/adr/002-full-scope-add-r.md:62:- Permanent artifacts form an acyclic hash DAG: `binding.json` contains no terminal-manifest hash; the terminal manifest hashes `publication_ref` files including binding; no file hashed by the manifest contains the manifest hash; optional `diagnostics/commit_evidence.json` is audit-only. `record_hash` uses the field-level projection in blueprint §9.6.6: build canonical content, exclude `artifact_binding.record_hash` and all result-carrying hashes, compute the content digest, fill binding, serialize, compute file-byte hashes, then build the terminal manifest.
docs/architecture/invariants.md:71:| INV-A-41 | `record_hash` is computed from a canonical content projection that excludes `artifact_binding.record_hash` and every result-carrying hash; content digest and file-byte hash are separate; only specified volatile run fields are excluded and risk/provenance timestamps are preserved. | `INV-01`, `FR-02`, `FR-04` | `SafetyGate`, `ArtifactPublisher`, `Canonicalizer` | Self-exclusion/retry/timestamp/file-hash tests | Reject self-referential or unstable record hash | Design only |
docs/architecture/invariants.md:439:- **Statement**: `record_hash` is computed from a canonical content projection with `artifact_binding.record_hash` and all derivative/result-carrying hashes removed; the full record with a populated self-hash is never serialized as the hash input. The order is canonical content -> `record_hash` -> fill binding -> serialize -> file-byte SHA-256 -> terminal manifest. `record_hash` (content digest) and file-byte hashes are distinct. Only the requirement's volatile run-level timestamps are excluded; risk and provenance evidence timestamps are preserved.
docs/architecture/trace-matrix.md:322:| `T-ARCH-41` | `record_hash` field-level projection excludes `artifact_binding.record_hash` and other result-carrying fields | not started |
docs/architecture/trace-matrix.md:323:| `T-ARCH-42` | canonical digest vs file-byte hash; retry stability; risk/provenance timestamps preserved; actual file hash verified | not started |
docs/architecture/runtime-policy-catalog.md:211:  - `record_hash` uses the §9.6.6 field-level projection with `artifact_binding.record_hash` and all result-carrying hashes removed; content digest and file-byte hash are distinct; only specified volatile run timestamps are excluded and risk/provenance evidence timestamps are preserved;
docs/architecture/open-decisions.md:406:- **Recommendation (not approved)**: use the `publication/`, `recovery/`, `locks/`, `diagnostics/` layout in blueprint §9.6.1. Formal report/history/export/memory binding validation depend only on `publication/` + terminal manifest; `recovery/` is temporary and may be cleaned; a terminal `recovery_snapshot_summary` is audit-only. The hash DAG is acyclic: `binding.json` contains no terminal-manifest hash; the manifest hashes permanent files including binding; no hashed file contains the manifest hash; optional `commit_evidence.json` is audit-only. `record_hash` uses the §9.6.6 projection excluding `artifact_binding.record_hash` and result-carrying hashes; content digest and file-byte hash are distinct.

```

---

## Assistant (Build · DeepSeek Flash · 6.4s)

_Thinking:_

Good.

Need update trace FR-07-AC3 monitor "filing-level fiscal copy" good.

### Check timestamp exclusion vs requirements
Current §9.6.6 excludes `run_clock.now_utc` etc and preserves risk/provenance timestamps. Good. But `record_hash` requirement says excludes `generated_at`, `evaluated_at`, `finished_at` run-level, local paths, cache counters, computed snapshot timestamps. We include those. Good.

Potential concern: `evaluated_at` appears in gate_result (run-level) and risk result (immutable). We say run-level evaluated_at excluded, risk `evaluated_at` preserved. Good.

### Check recovery first check in scenarios and trace
T-SCEN-17/18 added. Good. Need update evaluation scenario row 01..18; yes. Need update trace count; yes.

### Check T-ARCH count 44, T-SCEN 18. Good.

### Check table consistency final
Run again.

**Tool: bash**

**Input:**
```json
{
  "command": "ruby -e '\nfiles = Dir[\"architecture-blueprint.md\"] + Dir[\"docs/architecture/**/*.md\"]\nfiles.each do |f|\n lines=File.readlines(f,chomp:true); i=0\n while i<lines.length\n  if lines[i].start_with?(\"|\")\n   block=[]; j=i\n   while j<lines.length && lines[j].start_with?(\"|\"); block<<[j+1,lines[j]]; j+=1; end\n   data=block.reject{|ln,l| l.gsub(/[|\\-: ]/,\"\").empty?}\n   if data.length>1\n    exp=data.first[1].split(\"|\",-1).length\n    data.each{|ln,l| c=l.split(\"|\",-1).length; puts \"#{f}:#{ln} cells=#{c} exp=#{exp}\" if c!=exp}\n   end\n   i=j\n  else; i+=1; end\n end\nend\n' | head -20; echo \"tables ok\"; echo \"=== refs ===\"; defined=$(grep -oE \"(ARCH|D2)-OD-[0-9]+\" docs/architecture/open-decisions.md | sort -u); for ref in $(grep -rhoE \"(ARCH|D2)-OD-[0-9]+\" architecture-blueprint.md docs/architecture | sort -u); do echo \"$defined\" | grep -qx \"$ref\" || echo \"UNDEFINED $ref\"; done; echo \"refs ok\"; echo \"=== counts ===\"; printf \"AC \"; grep -cE '^\\| `(FR|INV|SB|SR|QR)-[0-9]+-AC[0-9]+`' docs/architecture/trace-matrix.md; printf \"INV \"; grep -c \"^| INV-A-\" docs/architecture/invariants.md; printf \"ARCH \"; grep -c \"^| \\`T-ARCH-\" docs/architecture/trace-matrix.md; printf \"SCEN \"; grep -c \"^| \\`T-SCEN-\" docs/architecture/trace-matrix.md"
}
```

**Output:**
```
tables ok
=== refs ===
refs ok
=== counts ===
AC 111
INV 41
ARCH 44
SCEN 18

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== stale phrases ===\"; grep -rn \"reserved-uncommitted\\|highest of committed and reserved\\|RunOwnershipLock.protect\\|recovery critical section\\|terminal_manifest_hash\\|completed (analysis)\\|otherwise use the role's normal\\|Source-field ownership\" architecture-blueprint.md docs/architecture || echo none; echo \"=== status ===\"; git status --short architecture-blueprint.md docs/architecture; echo \"=== req mtime ===\"; ls -la docs/req/requirements.yaml"
}
```

**Output:**
```
=== stale phrases ===
none
=== status ===
 M architecture-blueprint.md
 M docs/architecture/adr/001-run-governance.md
 M docs/architecture/evaluation-table.md
 M docs/architecture/invariants.md
 M docs/architecture/memory-design.md
 M docs/architecture/open-decisions.md
 M docs/architecture/permission-model.md
 M docs/architecture/runtime-policy-catalog.md
 M docs/architecture/trace-matrix.md
?? docs/architecture/adr/002-full-scope-add-r.md
=== req mtime ===
-rw-r--r--@ 1 ichihann  staff  365262 11月 11 03:32 docs/req/requirements.yaml

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== headers ===\"; for f in architecture-blueprint.md docs/architecture/*.md docs/architecture/adr/*.md; do printf \"%-55s \" \"$f\"; sed -n '3p' \"$f\"; done; echo \"=== no conflict ===\"; grep -rn \"<<<<<<<\\|>>>>>>>\" architecture-blueprint.md docs/architecture || echo none"
}
```

**Output:**
```
=== headers ===
architecture-blueprint.md                               Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/evaluation-table.md                   Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/invariants.md                         Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/memory-design.md                      Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/open-decisions.md                     Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/permission-model.md                   Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/runtime-policy-catalog.md             Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/trace-matrix.md                       Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/adr/001-run-governance.md             Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/adr/002-full-scope-add-r.md           Status: **v0.2 — ADD-R round 2 draft / pending human review**  
=== no conflict ===
none

```

---

## Assistant (Build · DeepSeek Flash · 4.1s)

_Thinking:_

Good. Need verify evaluation-table scenario count and measurement rows. Check.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -n \"Scenario matrix\\|record_hash\\|Recovery terminal\\|T-SCEN-01\" docs/architecture/evaluation-table.md | head -20; echo \"=== trace T-ARCH tail ===\"; grep -n \"T-ARCH-4[1-4]\\|T-SCEN-1[7-8]\" docs/architecture/trace-matrix.md"
}
```

**Output:**
```
252:| Scenario matrix T-SCEN-01..18 | Normal, business block, system error, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export, cleanup-after-read, brief failure, uncommitted-memory coordination, old-process lock/lease, PM proposal source, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, committed-publication corruption | not started |
256:| Permanent hash DAG | binding no terminal hash; no cycles; declared order; `record_hash` self-exclusion | not started |
257:| record_hash projection | field-level exclusion, canonical digest vs file hash, retry/risk-timestamp stability | not started |
258:| Recovery terminal-first | committed+verified -> idempotent without `recovery/`; conflict/corrupt typed; no overwrite | not started |
=== trace T-ARCH tail ===
253:Additional scenario tests: `T-SCEN-01`..`T-SCEN-18` (18 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-44`, not started.
275:| `T-SCEN-17` | Recovery after cleanup: terminal-first idempotent success without recovery directory | not started |
276:| `T-SCEN-18` | Committed permanent artifact corrupt: `CORRUPT_RECORD`, no overwrite/republish | not started |
322:| `T-ARCH-41` | `record_hash` field-level projection excludes `artifact_binding.record_hash` and other result-carrying fields | not started |
323:| `T-ARCH-42` | canonical digest vs file-byte hash; retry stability; risk/provenance timestamps preserved; actual file hash verified | not started |
324:| `T-ARCH-43` | recovery terminal-first check: committed+verified+identity match -> idempotent success without `recovery/` | not started |
325:| `T-ARCH-44` | committed identity conflict/corrupt permanent artifacts -> typed result; no overwrite/republish | not started |
360:- The scenario tests `T-SCEN-01`..`T-SCEN-18` cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, and committed-publication corruption. They are planned, not executed.

```

---

## Assistant (Build · DeepSeek Flash · 13.9s)

_Thinking:_

Good.

Need update `docs/architecture/runtime-policy-catalog.md` §6 implementation blockers maybe no new items; okay.

Need update open decisions ARCH-OD-23 maybe record_hash projection; done. Could add ARCH-OD-24 for record_hash projection? Not necessary; INV-A-41 and trace. But user asks "仍需人工决定的事项" — record_hash projection is a design proposal; maybe no open decision needed. Could add a non-blocking proposed decision `ARCH-OD-24 — record_hash projection acceptance` but not necessary. However, the user asks "最终...仍需人工决定的事项". We can mention record_hash projection is a proposed design pending review, but not necessarily an open decision. Maybe add to open decisions as "ARCH-OD-24 — record_hash projection and timestamp exclusion" to make it reviewable. But the architecture already specifies it; adding an open decision could imply unresolved. The user said "将相应模块开始实施所必需的设计选择具体化...可以提出明确的待评审方案". So a reviewable proposal is good. Add ARCH-OD-24 with status proposed/pending review, non-blocking? It is needed for implementation but concrete proposal exists. Could mark "proposed; blocking before implementation" or "non-blocking if accepted". Maybe add as `ARCH-OD-24 — record_hash projection acceptance` with status open/proposed, blocking before publication implementation. But that adds another blocker. Alternatively note in ADR/open decisions that §9.6.6 is the concrete proposal pending review. The user wants list of manual decisions. I can mention "§9.6.6 record_hash projection is a proposed design pending review" in final report without new ID. But for traceability, add `ARCH-OD-24` maybe. Hmm.

Similarly SEC field classes are a proposed design in ARCH-OD-19. Good.
Recovery first-check is now design; no open decision. Could add `ARCH-OD-25 — recovery terminal-first behavior` but it's clearly derived from FR-06. Not needed.

Let's add a short "review status" note in blueprint §9.6 intro: "These proposals, including §9.6.5 hash DAG and §9.6.6 record_hash projection, require human review; they are not approvals." Already says. Good.

Need update ADR 002 maybe record_hash projection bullet; done.

Need update ADR 001 maybe SEC field classes? Not necessary; ADR 002 covers.

Need update memory design maybe no SEC. Fine.

Need update permission model maybe record_hash? no.

Need update `docs/architecture/invariants.md` INV-A-41 inventory count 41; table check passed. Good.

Need check `docs/architecture/evaluation-table.md` requirement coverage FR-07 residual risk maybe mention source field classes? Not necessary; measurement rows.

Need check `docs/architecture/open-decisions.md` ARCH-OD-19 no "Source-field ownership"; good.

### Potential residual issue: §9.6.5 table `record.json` digest covers `artifact_binding` fields and uses §9.6.6 projection, but `record_hash` is computed over canonical content excluding record_hash. Good.
But `record.json` file includes `artifact_binding.record_hash`; file-byte hash covers it. `binding.json` file includes record_hash. Terminal manifest hashes both. No cycle. Good.

### Potential residual issue: `publication_ref` is in terminal manifest and includes `record_hash`; `record.json` includes `artifact_binding.record_hash` (same). No cycle. Good.

### Potential residual issue: `recovery_snapshot` includes `record_hash` and terminal-candidate identity; terminal manifest includes recovery summary digest; no cycle because recovery doesn't include terminal manifest hash. Good.

### Potential residual issue: `binding.json` includes `artifact_binding` fields; does `artifact_binding` include `record_hash`? Yes, and binding excludes terminal manifest hash. Fine.

### Potential residual issue: `record_hash` computation excludes `artifact_binding.record_hash` but what about `artifact_binding` fields that include coverage_snapshot_hash etc? Those are content-derived hashes, not result-carrying of record_hash; they are allowed. The user said exclude "其他承载该计算结果的字段" — only record_hash and derivatives. We exclude all result-carrying hashes including publication_ref.record_hash, binding self-hash, terminal manifest hash, file hashes, commit evidence. Good.

### Potential residual issue: `record_hash` exclusion of `run_clock.now_utc`—requirement says exclude volatile run-level timestamps including run_clock.now_utc. Good. Preserve risk evaluated_at. Good.

### Potential residual issue: `evaluated_at` is both gate_result (run-level) and risk result (preserved). We mention run-level evaluated_at excluded; risk evaluated_at preserved. Good.

### Potential residual issue: SEC "source_fact_ref" and disclosure fields; normalizer may derive `fiscal_year/quarter`; we say only from explicit evidence, not filing-level. Good.

### Potential residual issue: "不能假定原始SEC数据已经直接提供所有规范字段" — we say disclosure vs canonical, canonical may be derived. Good.

### Potential residual issue: "允许从明确证据按确定性规则规范化期间类型、符号约定等信息" — we say canonical sign/span can be derived with rule version/evidence. Good.

### Potential residual issue: "禁止用日期接近、数值相同或缺省猜测替代来源关联" — we state. Good.

### Potential residual issue: Recovery first check "committed + identity conflict or permanent corrupt" — what if both? We return conflict first in flow; okay. Maybe say "identity conflict takes precedence; otherwise corruption". Fine, not necessary.

### Potential residual issue: "已提交、验证通过且内容身份匹配时直接返回幂等成功，不再要求临时恢复快照存在" — flow says. Good.
"已提交但身份冲突或永久产物损坏时，分别返回明确的冲突或损坏结果" — flow says. Good.
"不能覆盖终态清单或自动重新发布" — says. Good.
"只有尚未提交...才读取并验证恢复快照" — says. Good.
"增加成功发布并清理恢复目录后再次调用恢复" — T-SCEN-17. Good.
"已提交产物损坏" — T-SCEN-18. Good.

### Potential residual issue: "调整恢复流程的检查顺序" — flow now terminal first. Good.

### Potential residual issue: "检查所有摘要引用仍构成无环依赖" — §9.6.5. Good.
"时间戳排除规则应逐项与当前需求对齐" — §9.6.6 lists. Good.
"增加自身摘要排除、重试稳定性、风险证据时间变化及实际文件哈希验证的计划场景" — T-ARCH-41/42, T-SCEN? T-ARCH covers. Good.

Need maybe add explicit T-SCEN for record_hash? The user says "计划场景", T-ARCH tests count. Fine.

### Potential residual issue: "统一SEC事实字段的来源与派生权限" — §9.6.4, §12.2, INV-A-30, POL-FIN, ADR 002, ARCH-OD-19, trace. Good.

Now final static checks and report. But before final, check no docs/req modifications and mtime. Already. Check no duplicate T-ARCH/T-SCEN. Counts 44/18. Check no duplicate table rows issues. Fine.

Need maybe update `docs/architecture/adr/002` §2.3 "no direct vendor" still. Good.

Need maybe update `docs/architecture/runtime-policy-catalog.md` §6 blockers includes record_hash? Not necessary; it's a design proposal not an open decision. But the final report should mention §9.6.6 pending review.

Need maybe update open decisions `ARCH-OD-24` for record_hash projection. Let's decide. The user asks "仍需人工决定的事项" and "不得虚构批准". §9.6.6 is a concrete proposal for review; we can list it as pending review without new ID. But to be explicit, add `ARCH-OD-24 — record_hash projection and timestamp exclusion` with status open/proposed, blocking before publication implementation. That makes it a human decision. Also `ARCH-OD-25 — SEC field provenance/derivation contract`? ARCH-OD-19 already covers SEC query; we can update it to include field classes (done). So only record_hash maybe. Add ARCH-OD-24. Update blocking summary and runtime §6. Let's add.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/open-decisions.md')\ns=p.read_text()\ns=s.replace(\"\"\"### ARCH-OD-23 — Permanent/recovery snapshot layout and cleanup dependency\"\"\",\n\"\"\"### ARCH-OD-24 — record_hash projection and timestamp exclusion\n\n- **Status**: open; **blocking before publication implementation**.\n- **Question**: accept the §9.6.6 field-level projection, including exclusion of `artifact_binding.record_hash` and all result-carrying hashes, the content-digest vs file-byte-hash split, and the exact volatile-timestamp list?\n- **Impact**: `SafetyGate`, `ArtifactPublisher`, `Canonicalizer`, `INV-01`, `INV-A-41`.\n- **Recommendation (not approved)**: canonical content -> exclude self/result hashes and specified volatile run timestamps (`generated_at`, run-level `evaluated_at`, `finished_at`, `run_clock.now_utc`, paths, cache counters, computed snapshot timestamps) -> compute `record_hash` -> fill binding -> serialize -> file-byte SHA-256 -> terminal manifest. Preserve risk `evaluated_at` and provenance/evidence/filed-at timestamps.\n- **Blocking phase**: before publication implementation.\n- **Related**: INV-01, FR-02, FR-04.\n\n### ARCH-OD-23 — Permanent/recovery snapshot layout and cleanup dependency\"\"\")\n# Add blocking row\ns=s.replace(\"| ARCH-OD-23 permanent/recovery layout/cleanup dependency | Before publication implementation | FR-02, FR-05, FR-06, INV-01 |\",\n\"| ARCH-OD-23 permanent/recovery layout/cleanup dependency | Before publication implementation | FR-02, FR-05, FR-06, INV-01 |\\n| ARCH-OD-24 record_hash projection/timestamp exclusion | Before publication implementation | INV-01, FR-02, FR-04 |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.6s)

_Thinking:_

Ordering: ARCH-OD-24 inserted before ARCH-OD-23. Reorder again for ascending. Let's use the reorder script on ARCH-OD sections.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\nimport re\np=Path('docs/architecture/open-decisions.md')\ns=p.read_text()\nstart=s.index('### ARCH-OD-01')\nend=s.index('---\\n\\n## 5. Blocking summary', start)\nprefix=s[:start]; suffix=s[end:]; body=s[start:end]\nparts=[x for x in re.split(r'(?=^### ARCH-OD-\\d+ — )', body, flags=re.M) if x.strip()]\nparts.sort(key=lambda x:int(re.match(r'### ARCH-OD-(\\d+)',x).group(1)))\ns=prefix+''.join(parts).rstrip()+'\\n\\n'+suffix\np.write_text(s)\nPY\ngrep -n \"^### ARCH-OD-\" docs/architecture/open-decisions.md | tail -8"
}
```

**Output:**
```
347:### ARCH-OD-17 — Brief replacement mapping and protected-marker format
356:### ARCH-OD-18 — Brief timing versus the final coverage snapshot
365:### ARCH-OD-19 — Financial-fact graph placement and SEC query shape
374:### ARCH-OD-20 — Memory reservation storage and format
383:### ARCH-OD-21 — Portfolio Manager adapter and model-proposal source
392:### ARCH-OD-22 — Uncommitted same-decision memory coordination
401:### ARCH-OD-23 — Permanent/recovery snapshot layout and cleanup dependency
410:### ARCH-OD-24 — record_hash projection and timestamp exclusion

```

---

## Assistant (Build · DeepSeek Flash · 3.6s)

_Thinking:_

Update runtime §6 implementation blockers includes record_hash projection? Add ARCH-OD-24.

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/architecture/runtime-policy-catalog.md')\ns=p.read_text()\ns=s.replace(\"permanent/recovery layout (ARCH-OD-15/23), memory reservation format/authority (ARCH-OD-20), SEC query contract (ARCH-OD-19), PM adapter/model-proposal source (ARCH-OD-21), uncommitted-memory status protocol (ARCH-OD-22), tokenizer/model (ARCH-OD-04)\",\n\"permanent/recovery layout (ARCH-OD-15/23), record_hash projection (ARCH-OD-24), memory reservation format/authority (ARCH-OD-20), SEC query contract (ARCH-OD-19), PM adapter/model-proposal source (ARCH-OD-21), uncommitted-memory status protocol (ARCH-OD-22), tokenizer/model (ARCH-OD-04)\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 3.3s)

_Thinking:_

Need update blueprint §21.3 implementation blockers list maybe add record_hash projection; currently lists items. Let's inspect/update.

**Tool: bash**

**Input:**
```json
{
  "command": "sed -n '/### 21.3 Implementation blockers/,/## 22./p' architecture-blueprint.md | head -20"
}
```

**Output:**
```
### 21.3 Implementation blockers versus acceptance-only

| Class | Items | Effect |
|---|---|---|
| Implementation-start | OQ-09 risk input source; ARCH-OD-03 risk policy locator; ARCH-OD-16 lock/lease format; ARCH-OD-15/23 snapshot layout; ARCH-OD-20 reservation format; ARCH-OD-19 SEC query contract; ARCH-OD-21 PM adapter; ARCH-OD-22 uncommitted-memory protocol; ARCH-OD-04 tokenizer/model | Decide before the affected module starts. Not an approval claim. |
| Acceptance-only | OQ-10 approved risk thresholds; OQ-13 QR-02 target/platform; OQ-16 brief budgets/quality; D2-OD-09 behavior snapshots; OQ-05 manifest overhead | Do not block starting implementation; block completion/acceptance claims. |
| Evidence/CI | ARCH-OD-01 missing `yhx` evidence; ARCH-OD-02 validator dependencies | Block reproducible D1 validation/CI, not module design. |

---

## 22. Document index and status

```

---

## Assistant (Build · DeepSeek Flash · 3.7s)

**Tool: bash**

**Input:**
```json
{
  "command": "python3 - <<'PY'\nfrom pathlib import Path\np=Path('architecture-blueprint.md')\ns=p.read_text()\ns=s.replace(\"| Implementation-start | OQ-09 risk input source; ARCH-OD-03 risk policy locator; ARCH-OD-16 lock/lease format; ARCH-OD-15/23 snapshot layout; ARCH-OD-20 reservation format; ARCH-OD-19 SEC query contract; ARCH-OD-21 PM adapter; ARCH-OD-22 uncommitted-memory protocol; ARCH-OD-04 tokenizer/model | Decide before the affected module starts. Not an approval claim. |\",\n\"| Implementation-start | OQ-09 risk input source; ARCH-OD-03 risk policy locator; ARCH-OD-16 lock/lease format; ARCH-OD-15/23 snapshot layout; ARCH-OD-24 record_hash projection; ARCH-OD-20 reservation format; ARCH-OD-19 SEC query contract; ARCH-OD-21 PM adapter; ARCH-OD-22 uncommitted-memory protocol; ARCH-OD-04 tokenizer/model | Decide before the affected module starts. Not an approval claim. |\")\np.write_text(s)\nPY"
}
```

**Output:**
```
(no output)
```

---

## Assistant (Build · DeepSeek Flash · 4.8s)

_Thinking:_

Now final consistency checks again.

**Tool: bash**

**Input:**
```json
{
  "command": "ruby -e '\nfiles = Dir[\"architecture-blueprint.md\"] + Dir[\"docs/architecture/**/*.md\"]\nfiles.each do |f|\n lines=File.readlines(f,chomp:true); i=0\n while i<lines.length\n  if lines[i].start_with?(\"|\")\n   block=[]; j=i\n   while j<lines.length && lines[j].start_with?(\"|\"); block<<[j+1,lines[j]]; j+=1; end\n   data=block.reject{|ln,l| l.gsub(/[|\\-: ]/,\"\").empty?}\n   if data.length>1\n    exp=data.first[1].split(\"|\",-1).length\n    data.each{|ln,l| c=l.split(\"|\",-1).length; puts \"#{f}:#{ln} cells=#{c} exp=#{exp}\" if c!=exp}\n   end\n   i=j\n  else; i+=1; end\n end\nend\n' | head -20; echo \"tables ok\"; echo \"=== refs ===\"; defined=$(grep -oE \"(ARCH|D2)-OD-[0-9]+\" docs/architecture/open-decisions.md | sort -u); for ref in $(grep -rhoE \"(ARCH|D2)-OD-[0-9]+\" architecture-blueprint.md docs/architecture | sort -u); do echo \"$defined\" | grep -qx \"$ref\" || echo \"UNDEFINED $ref\"; done; echo \"refs ok\"; echo \"=== counts ===\"; printf \"AC \"; grep -cE '^\\| `(FR|INV|SB|SR|QR)-[0-9]+-AC[0-9]+`' docs/architecture/trace-matrix.md; printf \"INV \"; grep -c \"^| INV-A-\" docs/architecture/invariants.md; printf \"ARCH \"; grep -c \"^| \\`T-ARCH-\" docs/architecture/trace-matrix.md; printf \"SCEN \"; grep -c \"^| \\`T-SCEN-\" docs/architecture/trace-matrix.md"
}
```

**Output:**
```
tables ok
=== refs ===
refs ok
=== counts ===
AC 111
INV 41
ARCH 44
SCEN 18

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== stale ===\"; grep -rn \"reserved-uncommitted\\|highest of committed and reserved\\|RunOwnershipLock.protect\\|terminal_manifest_hash\\|completed (analysis)\\|otherwise use the role's normal\\|Source-field ownership\" architecture-blueprint.md docs/architecture || echo none; echo \"=== status ===\"; git status --short architecture-blueprint.md docs/architecture; echo \"=== req mtime ===\"; ls -la docs/req/requirements.yaml; echo \"=== conflicts ===\"; grep -rn \"<<<<<<<\\|>>>>>>>\" architecture-blueprint.md docs/architecture || echo none"
}
```

**Output:**
```
=== stale ===
none
=== status ===
 M architecture-blueprint.md
 M docs/architecture/adr/001-run-governance.md
 M docs/architecture/evaluation-table.md
 M docs/architecture/invariants.md
 M docs/architecture/memory-design.md
 M docs/architecture/open-decisions.md
 M docs/architecture/permission-model.md
 M docs/architecture/runtime-policy-catalog.md
 M docs/architecture/trace-matrix.md
?? docs/architecture/adr/002-full-scope-add-r.md
=== req mtime ===
-rw-r--r--@ 1 ichihann  staff  365262 11月 11 03:32 docs/req/requirements.yaml
=== conflicts ===
none

```

**Tool: bash**

**Input:**
```json
{
  "command": "echo \"=== headers ===\"; for f in architecture-blueprint.md docs/architecture/*.md docs/architecture/adr/*.md; do printf \"%-55s \" \"$f\"; sed -n '3p' \"$f\"; done"
}
```

**Output:**
```
=== headers ===
architecture-blueprint.md                               Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/evaluation-table.md                   Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/invariants.md                         Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/memory-design.md                      Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/open-decisions.md                     Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/permission-model.md                   Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/runtime-policy-catalog.md             Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/trace-matrix.md                       Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/adr/001-run-governance.md             Status: **v0.2 — ADD-R round 2 draft / pending human review**  
docs/architecture/adr/002-full-scope-add-r.md           Status: **v0.2 — ADD-R round 2 draft / pending human review**  

```

---

## Assistant (Build · DeepSeek Flash · 4.0s)

_Thinking:_

Good.

Need check `docs/architecture/evaluation-table.md` scenario row 01..18. Done.
Need check `docs/architecture/trace-matrix.md` T-SCEN-17/18 and T-ARCH-41..44. Done.
Need check `docs/architecture/invariants.md` INV-A-41 inventory row and detailed. Table consistency passed.

Potential issue: `docs/architecture/runtime-policy-catalog.md` §6 blocking list now includes ARCH-OD-24 but not ARCH-OD-15/23? It says permanent/recovery layout (ARCH-OD-15/23), record_hash (24), memory reservation (20), SEC (19), PM (21), uncommitted (22), tokenizer (04). Good.

Potential issue: `docs/architecture/open-decisions.md` blocking table row for ARCH-OD-24. Check.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -n \"ARCH-OD-24\" docs/architecture/open-decisions.md docs/architecture/runtime-policy-catalog.md architecture-blueprint.md | head -20; echo \"=== T-SCEN-17/18 and T-ARCH-41..44 ===\"; grep -n \"T-SCEN-17\\|T-SCEN-18\\|T-ARCH-41\\|T-ARCH-42\\|T-ARCH-43\\|T-ARCH-44\" docs/architecture/trace-matrix.md"
}
```

**Output:**
```
docs/architecture/open-decisions.md:410:### ARCH-OD-24 — record_hash projection and timestamp exclusion
docs/architecture/open-decisions.md:448:| ARCH-OD-24 record_hash projection/timestamp exclusion | Before publication implementation | INV-01, FR-02, FR-04 |
docs/architecture/runtime-policy-catalog.md:441:| Implementation-start blockers | Risk input source (OQ-09), risk policy locator/approval record (ARCH-OD-03), shared lock/lease format (ARCH-OD-16), permanent/recovery layout (ARCH-OD-15/23), record_hash projection (ARCH-OD-24), memory reservation format/authority (ARCH-OD-20), SEC query contract (ARCH-OD-19), PM adapter/model-proposal source (ARCH-OD-21), uncommitted-memory status protocol (ARCH-OD-22), tokenizer/model (ARCH-OD-04) | Must be decided before the affected module starts; not a claim of approval. |
architecture-blueprint.md:1376:| Implementation-start | OQ-09 risk input source; ARCH-OD-03 risk policy locator; ARCH-OD-16 lock/lease format; ARCH-OD-15/23 snapshot layout; ARCH-OD-24 record_hash projection; ARCH-OD-20 reservation format; ARCH-OD-19 SEC query contract; ARCH-OD-21 PM adapter; ARCH-OD-22 uncommitted-memory protocol; ARCH-OD-04 tokenizer/model | Decide before the affected module starts. Not an approval claim. |
=== T-SCEN-17/18 and T-ARCH-41..44 ===
253:Additional scenario tests: `T-SCEN-01`..`T-SCEN-18` (18 scenarios), not started. Additional architecture tests: `T-ARCH-01`..`T-ARCH-44`, not started.
275:| `T-SCEN-17` | Recovery after cleanup: terminal-first idempotent success without recovery directory | not started |
276:| `T-SCEN-18` | Committed permanent artifact corrupt: `CORRUPT_RECORD`, no overwrite/republish | not started |
322:| `T-ARCH-41` | `record_hash` field-level projection excludes `artifact_binding.record_hash` and other result-carrying fields | not started |
323:| `T-ARCH-42` | canonical digest vs file-byte hash; retry stability; risk/provenance timestamps preserved; actual file hash verified | not started |
324:| `T-ARCH-43` | recovery terminal-first check: committed+verified+identity match -> idempotent success without `recovery/` | not started |
325:| `T-ARCH-44` | committed identity conflict/corrupt permanent artifacts -> typed result; no overwrite/republish | not started |
360:- The scenario tests `T-SCEN-01`..`T-SCEN-18` cover normal pass, business block, system exception, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export edge cases, cleanup-after-read, brief failure modes, uncommitted-memory coordination, old-process lock/lease takeover, Portfolio Manager proposal sourcing, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, and committed-publication corruption. They are planned, not executed.

```

---

## Assistant (Build · DeepSeek Flash · 3.1s)

_Thinking:_

Need update evaluation table scenario row mentions T-SCEN-01..18 and maybe record_hash measurement. Done. Check.

**Tool: bash**

**Input:**
```json
{
  "command": "grep -n \"Scenario matrix\\|record_hash projection\\|Recovery terminal-first\" docs/architecture/evaluation-table.md"
}
```

**Output:**
```
252:| Scenario matrix T-SCEN-01..18 | Normal, business block, system error, pre-commit interruption, post-commit corruption, duplicate recovery, concurrent publication, context overflow, history/export, cleanup-after-read, brief failure, uncommitted-memory coordination, old-process lock/lease, PM proposal source, failed-version retry, commit/ledger-update interruption, recovery-after-cleanup, committed-publication corruption | not started |
257:| record_hash projection | field-level exclusion, canonical digest vs file hash, retry/risk-timestamp stability | not started |
258:| Recovery terminal-first | committed+verified -> idempotent without `recovery/`; conflict/corrupt typed; no overwrite | not started |

```

---

## Assistant (Build · DeepSeek Flash · 12.8s)

_Thinking:_

Good.

Potential issue: `docs/architecture/adr/002` might not mention recovery first-check in §2.2? It does. Good.

Potential issue: `docs/architecture/adr/001` line 46 updated. Good.

Potential issue: `docs/architecture/memory-design.md` §12 updated. Good.

Potential issue: `docs/architecture/invariants.md` INV-A-28 inventory and detailed updated; INV-A-41 added. Good.

Potential issue: `docs/architecture/runtime-policy-catalog.md` POL-REC first check and POL-PUB record_hash. Good.

Potential issue: `docs/architecture/trace-matrix.md` FR-06 ACs don't explicitly mention terminal-first; T-SCEN-17/T-ARCH-43 cover. Could add FR-06-AC1/AC5 component/test mention? Maybe not necessary. But "同步 ... 追踪矩阵和验证计划" — scenario/arch tests suffice. Maybe update FR-06-AC5 row to mention terminal-first? Let's check FR-06-AC5 description. It covers identity/no-op/conflict. It likely mentions existing completed publication. Good. Could add T-SCEN-17/18 in row? Not necessary.

Potential issue: `docs/architecture/evaluation-table.md` "FR-06 residual risk" maybe no terminal-first. Not necessary.

Potential issue: SEC field classes in trace T-ARCH-35; good.

Potential issue: hash DAG in trace T-ARCH-39; good.

Potential issue: record_hash projection in trace T-ARCH-41/42; good.

Potential issue: "时间戳排除规则应逐项与当前需求对齐，只排除需求规定的易变运行字段，保留风险评估和来源证据中必须保留的时间信息" — §9.6.6 lists. But does it align with requirement exactly? Requirement says exclude `generated_at`, `evaluated_at`, `finished_at` run-level, local paths, cache counters, computed snapshot timestamps; `run_clock.now_utc` specifically in record_hash definition. We include. Risk `evaluated_at` preserved. Good. Maybe `run_clock.now_utc` is a timestamp but requirement record_hash says exclude volatile run-level timestamps (including run_clock.now_utc). Good.

Potential issue: "禁止通过序列化已填入自身摘要的完整记录计算 record_hash" — §9.6.6 says full record with populated self-hash never serialized as hash input. Good.

Potential issue: "明确区分规范内容摘要与文件字节哈希" — yes.

Potential issue: "按构建规范内容、计算record_hash、填入绑定、序列化文件、计算文件哈希、生成终态清单的顺序处理" — yes exact order.

Potential issue: "检查所有摘要引用仍构成无环依赖" — yes hash DAG table.

Potential issue: "SEC...保留原始值，派生结果另外记录规则版本、输入证据和来源引用" — yes disclosure/canonical/derivation.

Potential issue: "不能假定原始SEC数据已经直接提供所有规范字段" — yes canonical may be derived.

Potential issue: "不能直接把披露文件所属财年季度当成每条历史事实的期间身份" — yes.

Potential issue: "允许从明确证据按确定性规则规范化期间类型、符号约定等信息" — yes canonical fields derive with rules.

Potential issue: "禁止用日期接近、数值相同或缺省猜测替代来源关联" — yes.

Potential issue: "证据不足或无法唯一确定时返回明确的不可用或歧义结果" — yes.

Now final answer. Need mention modified files, conflicts resolved, static checks, manual decisions. No claim of tests. Keep concise but comprehensive.

Also note `docs/req/` untouched mtime. Mention no app implementation/tests.

Let's formulate in Chinese. Maybe 40-60 lines.

Key sections:
- 修复1 recovery order
- 修复2 record_hash projection
- 修复3 SEC fields
- 修改文件
- 静态核对
- 仍需人工决定

Include scenario tests T-SCEN-17/18, T-ARCH-41..44.

Let's ensure no claim that docs were approved. State proposals pending review.

Final.

本轮仅修改 `architecture-blueprint.md` 与 `docs/architecture/`，未改 `docs/req/`、`TradingAgents/`、`baseline/` 或其他目录；`docs/req/requirements.yaml` mtime 未变。

## 修复内容

### 1. 恢复流程检查顺序

- 恢复现在**先读取终态清单并验证永久发布**：
  - `completed` + read-time `INV-01` 通过 + 内容身份匹配：直接返回幂等成功，不要求 `recovery/` 存在。
  - `completed` + 身份冲突：返回 `RUN_ID_CONFLICT`。
  - `completed` + 永久产物损坏：返回 `CORRUPT_RECORD`。
  - 以上已提交路径均不覆盖终态清单、不自动重新发布。
- 只有**尚未提交、确实需要继续发布**的记录才 claim/读取并验证恢复快照。
- 恢复流程、§12.6、ADR、记忆设计、运行策略、不变量均已同步。
- 新增验证场景：
  - `T-SCEN-17`：成功发布并清理恢复目录后再次调用恢复，仍返回幂等成功。
  - `T-SCEN-18`：已提交永久产物损坏，返回 `CORRUPT_RECORD` 且不覆盖/不重发。
  - `T-ARCH-43/44`：terminal-first 检查与冲突/损坏结果。

### 2. `record_hash` 字段级投影

- 明确 `record_hash` 是**规范内容摘要**，不是 `sha256(record.json bytes)`。
- 计算前显式排除：
  - `artifact_binding.record_hash`；
  - 所有承载/派生该结果的字段与哈希，包括 `publication_ref.record_hash`、binding 自身哈希、终态清单哈希、文件哈希、commit-evidence 哈希。
- 固定顺序：
  1. 构建规范内容；
  2. 计算 `record_hash`；
  3. 填入 binding；
  4. 序列化文件；
  5. 计算文件字节 SHA-256；
  6. 生成终态清单。
- 明确区分内容摘要与文件字节哈希；禁止序列化已填入自身摘要的完整记录再计算 `record_hash`。
- 时间戳排除规则对齐需求：只排除规定的易变运行字段；风险 `evaluated_at`、估值时间/截止时间、attempt/evidence/provenance 时间、`filed_at` 等来源证据时间保留。
- 新增 `INV-A-41`，并补充 `T-ARCH-41/42`：
  - 自身摘要排除；
  - 重试稳定性；
  - 风险证据时间变化；
  - 实际文件字节哈希验证。

### 3. SEC 事实字段来源与派生权限

- `SecEdgarAdapter` 输出改为逐事实记录，并区分：
  - **disclosure 字段**：subject、accession、filing_ref、filed_at、form、source_fact_ref、raw concept/value/unit/currency/period/fiscal/sign、显式 restatement/supersession 等，必须保留原始证据；
  - **canonical 字段**：fact_id、canonical concept/period/fiscal identity、span、cumulative duration、canonical sign/unit/currency、显式 lineage，可由 `FinancialFactService` 按版本化规则校验或派生。
- 派生结果必须记录 `normalization_rule_version`、`derived_fields`、`input_evidence_refs`、`source_refs`。
- 明确：披露文件的财年/季度不能直接当作每条历史事实的期间身份；每条事实需要自身期间/财年身份或明确派生证据。
- 允许从明确证据确定性规范化期间类型、符号约定等；禁止用日期接近、数值相同、列顺序或缺省猜测来源关联。
- 缺失或无法唯一确定时返回 `FactUnavailableError`/`FactAmbiguousError`。
- 同步 `INV-A-30`、`POL-FIN-01`、ADR 002、`ARCH-OD-19`、`T-ARCH-35`。

## 修改文件

修改：
- `architecture-blueprint.md`
- `docs/architecture/adr/001-run-governance.md`
- `docs/architecture/evaluation-table.md`
- `docs/architecture/invariants.md`
- `docs/architecture/memory-design.md`
- `docs/architecture/open-decisions.md`
- `docs/architecture/permission-model.md`
- `docs/architecture/runtime-policy-catalog.md`
- `docs/architecture/trace-matrix.md`

新增：
- `docs/architecture/adr/002-full-scope-add-r.md`

## 静态核对结果

- `trace-matrix.md` 仍覆盖 **111/111** 条验收条件。
- 不变量 **41** 条，架构测试 **44** 条，场景测试 **18** 条。
- 所有 `ARCH-OD-*` / `D2-OD-*` 引用均有定义。
- 所有 Markdown 表格列数一致；无冲突标记。
- 所有架构文档保持 `v0.2 — ADD-R round 2 draft / pending human review`。
- 未修改 `docs/req/`、应用代码或 `baseline/`；未声称实现、运行测试或批准结果。

## 仍需人工决定

**实现启动阻塞项：**
- `OQ-09` 风险输入来源
- `ARCH-OD-03` 风险 policy 定位/审批记录
- `ARCH-OD-16` 锁/租约格式、TTL、接管条件
- `ARCH-OD-15/23` 永久/恢复快照布局与清理边界
- `ARCH-OD-24` `record_hash` 字段级投影与时间戳排除
- `ARCH-OD-20` 记忆预留历史格式/权威性
- `ARCH-OD-19` SEC 逐事实查询与字段派生契约
- `ARCH-OD-21` Portfolio Manager 适配器/model_proposal 来源
- `ARCH-OD-22` 未提交记忆协调超时/状态
- `ARCH-OD-04` tokenizer/model
- `OQ-14` 非 NVDA 参考 manifest

**仅影响验收：**
- `OQ-10` 风险阈值/policy 的 approved 声明（有效 provisional 路径可用）
- `OQ-13` QR-02 目标/平台
- `OQ-16` 摘要预算/质量阈值
- `D2-OD-09` 行为评估快照/人工批准
- `OQ-05` manifest overhead

**证据/CI 阻塞：**
- `ARCH-OD-01` `yhx/requirements.yaml` 缺失
- `ARCH-OD-02` validator 依赖未声明

**审批范围：**
- `ARCH-OD-13/14`：approved `SB-01`/`FR-02`/`INV-01` 与 draft 细节的耦合仍需人工决定；当前文档只限制完成/验收声明，不降低批准义务，也不宣布草案获批。

---

