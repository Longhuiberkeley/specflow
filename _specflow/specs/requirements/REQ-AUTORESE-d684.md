---
id: REQ-AUTORESE-d684
title: 'Autoresearch pack v0.2.0: multi-criteria support, CLI subcommand, and harness-agnosticism'
type: requirement
status: approved
suspect: false
links: []
created: '2026-05-16'
modified: '2026-06-19'
fingerprint: sha256:0fc93b56a8e8
---

# Autoresearch pack v0.2.0: multi-criteria support, CLI subcommand, and harness-agnosticism

## Acceptance Criteria

1. EXPT schema accepts `auxiliary_metrics` optional field (freeform YAML dict) and artifacts with this field pass lint
2. `competition-setup-protocol.md` documents multi-criteria competitions (primary metric + guards + auxiliary logging) with a worked quant example
3. `competition-setup-protocol.md` documents leakage and gaming patterns (read-only eval, one-number verify, robustness-adjusted primaries) as recommendations, not mandates
4. `autonomous-loop-protocol.md` includes anti-gaming pointer and auxiliary_metrics logging in Phase 7
5. `specflow autoresearch plan|run|review|leaderboard` CLI subcommand works with multi-COMP repos (`--competition`, `--all`)
6. SKILL.md references CLI backends for all subcommands instead of inlining full protocol
7. Pack `context_snippet` is defined in pack.yaml and `inject_pack_context()` injects it into instruction files with idempotent sentinel markers
8. `platforms.yaml` has `instruction_file` field for each platform
9. All existing tests pass (372 tests) and new tests cover auxiliary_metrics, CLI subcommands, and context injection
