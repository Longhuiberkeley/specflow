---
id: STORY-630
title: Enforce semver baseline naming and prefer releases in drift selection
type: story
status: verified
rationale: Addresses CHL-NONSEMVE-c16b (non-semver baseline names can outrank release
  baselines; --baseline audit flag dead).
tags:
- baselines
- semver
- CHL-NONSEMVE-c16b
- REQ-035
suspect: false
links:
- target: REQ-035
  role: implements
- target: UT-067
  role: verified_by
- target: IT-036
  role: verified_by
- target: QT-043
  role: verified_by
created: '2026-08-05'
fingerprint: sha256:6fc057fe0db5
output_files:
- src/specflow/lib/baselines.py
- src/specflow/commands/project_audit.py
- src/specflow/lib/evidence.py
- src/specflow/cli.py
- tests/test_baselines.py
- tests/test_project_audit.py
- tests/test_evidence.py
- docs/cli-reference.md
- tests/test_nfr_category.py
- tests/test_backfilled_guard.py
modified: '2026-08-05'
---

# Enforce semver baseline naming and prefer releases in drift selection

## Context

Semver-parseable baselines sort before freeform names, while newest/predecessor selection callers take the tail of the list. A project mixing release tags with names such as `snapshot` can therefore diff the freeform baseline instead of the newest release, and the documented `project-audit --baseline` flag was never consumed (CHL-NONSEMVE-c16b).

## Acceptance Criteria

1. `create_baseline` rejects non-semver names with a loud, clear error (accepts `v1.2`, `v1.2.3`, `v1.2.3-rc1`); existing freeform baselines on disk are grandfathered (no migration — baselines are write-once).
2. Drift selection (`select_release_pair`) prefers semver-parseable releases and falls back to the raw tail only when fewer than two names parse; byte-identical to the old behavior for pure-semver and pure-freeform lists.
3. `project-audit --baseline NAME` anchors drift as NAME → newest release; unknown names warn and auto-fallback to the auto pair; --dry-run parity and exit-code semantics unchanged.
4. The evidence report's predecessor selection follows the same semver-prefer policy.
5. The full test suite passes.

## Implementation

- src/specflow/lib/baselines.py — shared `_semver_parts` predicate, `select_release_pair`, `newest_release`, semver-shaped `_validate_name`.
- src/specflow/commands/project_audit.py — `_resolve_drift_pair`; `--baseline` wired through run() (warn + fallback; anchored runs bypass the findings cache both ways).
- src/specflow/lib/evidence.py — semver-prefer predecessor selection.
- docs/cli-reference.md — baseline naming policy; create-time enforcement is a consumer-visible breaking change for freeform-naming automation.
