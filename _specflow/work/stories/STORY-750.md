---
id: STORY-750
title: Baseline diff pairs renumbered artifacts (same type, equal fingerprint or title)
  and reports them as renumbered, not removed
type: story
status: verified
tags:
- consistency
- v1.17.7
suspect: false
links:
- target: REQ-005
  role: implements
- target: DEF-024
  role: derives_from
created: '2026-10-18'
fingerprint: sha256:983e9ca9aae5
modified: '2026-10-18'
output_files:
- src/specflow/lib/baselines.py
- src/specflow/commands/project_audit.py
- src/specflow/commands/baseline.py
- tests/test_baselines.py
---

# Baseline diff pairs renumbered artifacts (same type, equal fingerprint or title) and reports them as renumbered, not removed

## Scope
`lib/baselines.py` gains `_pair_renumbered` and a `renumbered` key in the diff; `project-audit` baseline-drift emits info 'renumbered to' rows instead of warn for pairs; `baseline diff` prints a Renumbered section and count.

## Acceptance criteria
- AC1: Given baseline A with STORY-ADDCLI-0e15 and baseline B with STORY-722 carrying the same fingerprint, when `diff_baselines` runs, then the pair is in `renumbered` with matched_by fingerprint and neither `added` nor `removed` lists them.
- AC2: Given the same shape with different fingerprints but equal titles, when it runs, then the pair is matched by title.
- AC3: Given a removed id with no same-type match, when it runs, then it stays in `removed` and a cross-type title match is never paired.
- AC4: Given this repository, when `specflow project-audit --dry-run` runs with baselines v1.17.1 and v1.17.7, then the baseline-drift lens emits no escalating warning for renumbered drafts.
