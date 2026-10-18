---
id: STORY-749
title: W-4/W-5 ledger amendments (command renames, go auto-commit notes, REQ-044/047
  cascade, PREV-003 tags) and the AGENTS.md release ledger step; release v1.17.7
type: story
status: verified
tags:
- consistency
- v1.17.7
suspect: false
links:
- target: REQ-070
  role: implements
- target: SPIKE-008
  role: derives_from
created: '2026-10-18'
fingerprint: sha256:1e371cd38cff
modified: '2026-10-18'
output_files:
- AGENTS.md
- tests/test_release_ledger_step.py
---

# W-4/W-5 ledger amendments (command renames, go auto-commit notes, REQ-044/047 cascade, PREV-003 tags) and the AGENTS.md release ledger step; release v1.17.7

## Scope
Dated amendment notes in the REQ/STORY bodies listed in SPIKE-008 'Stale ledger' (REQ-001/002/003/005/011/014/015/017/024/026/032/037/046/057/062/067; STORY-002/008/012/015/017/019/022/024/030/031/046/048/059/063/064/083/623/638/651/663/675/712/718/735) followed by `specflow fingerprint-refresh`; `cascade-status --include-req` for REQ-044/047; `patterns update PREV-003 --tags`; AGENTS.md release process gains document-changes / baseline create --evidence / phase-set complete before the release commit; CHANGELOG 1.17.7, version bump, README pin, ROADMAP.

## Acceptance criteria
- AC1: Given each listed artifact, when read, then it carries an 'Amended 2026-10-18 (SPIKE-008 …)' note naming the real command/flag or the DEC that changed the behaviour, and `specflow artifact-lint` reports no fingerprints/stale finding for it.
- AC2: Given REQ-044 and REQ-047, when `specflow list --type requirement` runs, then both read implemented.
- AC3: Given AGENTS.md Release Process, when read, then a step before Commit runs `specflow document-changes --since <prev-tag>`, `specflow baseline create v1.x.x --evidence` and `specflow phase-set complete`.
- AC4: Given the v1.17.7 release, when `.specflow/baselines/` is listed after it, then `v1.17.7.yaml` exists and `state.yaml` reads complete; CHANGELOG notes the v1.17.2..v1.17.6 baseline gap.
