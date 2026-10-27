# FR-04 Permission Contribution

Status: **personal draft / pending team review**
Implementation status: **design only; no permissions are enforced by this file**

## Runtime AI

Runtime AI may produce a proposal but may not:

- supply or modify authoritative portfolio values or policy limits;
- invoke or override the deterministic evaluator or shared gate;
- read files, environment variables, credentials, or arbitrary URLs;
- write formal artifacts or memory directly;
- convert rendered Markdown into authoritative numeric state.

Runtime AI receives only assembled context and registered tools. Deterministic
application code owns authoritative risk inputs, policies, finalization, and
publication.

## D1/D2 drafting agent

The FR-04 documentation agent is default-deny.

Allowed writes:

- `architecture-blueprint.md`;
- `docs/req/requirements.yaml`;
- `docs/architecture/adr/002-deterministic-portfolio-risk.md`;
- `docs/architecture/invariants.md`;
- `docs/architecture/trace-matrix.md`;
- `docs/architecture/memory-design.md`;
- `docs/architecture/permission-model.md`;
- `docs/architecture/runtime-policy-catalog.md`;
- `docs/architecture/evaluation-table.md`;
- `docs/architecture/open-decisions.md`;
- its own new entry in `docs/ai-use-log.yaml`.

Allowed reads:

- `docs/req/req-schema.json`;
- canonical team D1/D2 documents;
- `TradingAgents/**`;
- sanitized `baseline/**` evidence.

Denied:

- writes to `TradingAgents/**`, tests, frozen baseline evidence, credentials,
  `.env`, runtime state, or another member's approved requirement;
- commit, push, merge, reset, deletion, dependency installation, or arbitrary
  network access without explicit human approval.

## Future implementation roles

| Role | Allowed writes | Allowed reads | Explicitly denied |
|---|---|---|---|
| Builder | Human-approved FR-04 source paths only | Approved D1/D2/D3/D4, relevant source | Requirements, approved tests, baseline evidence, secrets, Git history |
| Verifier | New FR-04 test/evidence paths only | Source, requirements, architecture, prior tests | Product-code repair, requirement changes, secrets |
| Reviewer | None | Repository, diff, sanitized evidence | All writes and merge approval on behalf of humans |

The exact implementation allowlist must be approved in D3 before coding begins.
This Markdown document is descriptive; enforcement belongs in
`.opencode/permissions.jsonc`, CI, and branch protection.

## Human authority

Only humans approve D1/D2, close blocking decisions, authorize safety-critical
code changes, approve tests before implementation, and merge the pull request.
