# Permission Model — Report Archive

## Runtime authority

The runtime model can produce report text but cannot choose archive paths, generate commit markers, overwrite committed runs, invoke recovery or run shell commands. The analysis adapter selects fields; ArchiveContracts validates them; ArchiveService and FileArchiveStore own writes. A historical report is data and cannot alter the host's instructions or file permissions.

| Operation | Allowed resources | Denied resources/actions |
|---|---|---|
| New archive | Own pending/staging paths and absent final run directory under fixed archive root | Other committed runs; arbitrary path from report prose |
| Query | Final run metadata and fixed manifest-declared report files | Pending/staging as successful content; arbitrary files |
| Recovery | Valid pending snapshot and corresponding fresh staging/final paths | Model/data-provider/graph/memory calls; changed run identity |
| Cleanup | Own redundant temporary artifacts after verified commit | Committed archives and legacy report files |
| Additional export | Explicitly supplied empty destination, exclusively reserved | Canonical-root overlap, existing non-empty destination or legacy file overwrite |

Reject traversal, absolute section paths, drive/UNC injection, alternate data streams, and symlink/junction escapes. Root containment is checked on resolved paths; unlisted filenames cannot be introduced by the snapshot text.

## File-level software-engineering role matrix

Default is no read and no write. All paths below are repository-relative; a write grant includes reading that file. Global denials override every wildcard. These rights describe the archive design's implementation boundary.

| Role | Read allowlist | Write allowlist |
|---|---|---|
| Requirements editor | docs/req/**; docs/architecture/**; architecture-blueprint.md; TradingAgents/cli/run.py; TradingAgents/tradingagents/graph/trading_graph.py; TradingAgents/tradingagents/reporting.py | docs/req/requirements.yaml; docs/req/req-schema.json |
| Architecture editor | docs/req/**; docs/architecture/**; architecture-blueprint.md; TradingAgents/cli/*.py; TradingAgents/tradingagents/**/*.py | architecture-blueprint.md; docs/architecture/**/*.md |
| Archive implementation role | docs/req/**; docs/architecture/**; architecture-blueprint.md; TradingAgents/cli/*.py; TradingAgents/tradingagents/**/*.py; TradingAgents/tests/** | TradingAgents/tradingagents/archive/*.py; TradingAgents/tradingagents/reporting.py; TradingAgents/tradingagents/graph/trading_graph.py; TradingAgents/tradingagents/default_config.py; TradingAgents/cli/run.py; TradingAgents/cli/archive.py; TradingAgents/tests/test_archive*.py |
| Verification role | docs/req/**; docs/architecture/**; architecture-blueprint.md; TradingAgents/cli/*.py; TradingAgents/tradingagents/**/*.py; TradingAgents/tests/** | TradingAgents/tests/test_archive*.py; TradingAgents/tests/fixtures/archive/**; baseline/archive-verification/** |
| Documentation reviewer | docs/req/**; docs/architecture/**; architecture-blueprint.md; TradingAgents/cli/*.py; TradingAgents/tradingagents/**/*.py; TradingAgents/tests/**; baseline/archive-verification/** | None |

No role may read/write .git/**, **/.env, **/.env.*, **/secrets/**, **/credentials/**, **/*.pem, **/*.key, **/*.p12 or **/*.pfx, OS credential stores, shell history or real user archives. Tests use synthetic fixtures. This matrix grants no repository publication, arbitrary network or package installation rights. Access through a link to a denied target remains denied.

## Verification and fallback

Use positive and negative role/path fixtures and global-deny precedence checks. T-RAR-09 tests secret sentinels and excluded fields; T-RAR-11 tests path escapes; T-RAR-07 installs failing spies on forbidden recovery calls. Stop an invalid operation before writes and return a safe diagnostic code. The model cannot grant itself access through generated report text.
