---
id: CHL-NONSEMVE-c16b
title: Non-semver baseline names can outrank release baselines
type: challenge
status: open
suspect: false
links:
- target: STORY-627
  role: refers_to
- target: STORY-630
  role: refers_to
created: '2026-08-05'
severity: info
technique: premortem
thinking_techniques:
- premortem
fingerprint: sha256:dfca327579e0
modified: '2026-08-05'
---

# Non-semver baseline names can outrank release baselines

## Finding

Semver-parseable baselines sort before freeform names, while newest/predecessor callers select the final entries. External projects mixing release tags with names such as `snapshot` can therefore compare the freeform baseline instead of the newest release. This repository uses version-shaped baseline names and is unaffected.

## Follow-up

Choose and document a policy: enforce semver baseline names, or have newest/predecessor callers prefer semver names and fall back only when none parse.

## Resolution Evidence

Resolved by STORY-630 (verified via UT-067 / IT-036 / QT-043), which implemented BOTH halves of the policy plus the dead-flag wiring:

- Enforcement: `baseline create` now rejects non-semver names with a loud, clear error (pattern `^v?\d+(\.\d+)*(-[0-9A-Za-z.-]+)?$` — accepts `v1.2`, `v1.13.5`, `v1.13.5-rc1`; rejects `snapshot`, `a`). Freeform baselines already on disk are grandfathered: baselines are write-once, no migration runs, and `list_baselines` still globs them unchecked.
- Selection: `select_release_pair` (src/specflow/lib/baselines.py) makes drift callers prefer semver-parseable releases and fall back to the raw tail only when fewer than two names parse. Wired into the project-audit drift diff, the audit scope line, and the evidence predecessor selection. Byte-identical behavior for pure-semver and pure-freeform lists; only mixed lists change.
- `project-audit --baseline NAME` is wired: drift anchors as NAME → newest semver release; an unknown name warns and auto-falls back to the auto pair (accounting-not-policing); anchored runs bypass the findings cache so anchors are never shadowed and never poison cached auto-pair findings. `--dry-run` parity and exit-code semantics are unchanged (exit code remains a pure function of findings).

Status stays open: the orchestrator closes this CHL after the release that ships STORY-630.
