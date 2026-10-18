---
id: STORY-752
title: Promote or close the 56 draft UT/IT/QT specs and repair stale test-file citations
type: story
status: verified
tags:
- consistency
- v1.17.8
suspect: false
links:
- target: REQ-071
  role: implements
- target: SPIKE-008
  role: derives_from
created: '2026-10-18'
fingerprint: sha256:555e51de503b
modified: '2026-10-18'
output_files:
- tests/test_spec_promotion_state.py
---

# Promote or close the 56 draft UT/IT/QT specs and repair stale test-file citations

## Scope
Practice-spine specs UT-089..102 / IT-055..070 / QT-054..073 (parents STORY-666..677, ARCH-035..038, DDD-031/032, REQ-044..051), UT-153/154, IT-113/114, QT-114/115 (verify_command present). For each: locate the real test(s), set `--set verify_command` and `--output-files`, approve, `specflow verify`, implemented; parents deprecated (REQ-048..051) → legal terminal status with a reason. Repair `tests/*.py` citations in all UT/IT/QT bodies that point at files that no longer exist.

## Acceptance criteria
- AC1: Given the three test-spec lists after the change, when filtered to draft, then no spec with an implemented or verified parent remains (REQ AC2).
- AC2: Given every promoted spec, when its frontmatter is read, then verify_run_exit_code is 0 and output_files name existing test files.
- AC3: Given every UT/IT/QT body, when each cited tests/*.py path is checked, then it exists on disk (REQ AC3).
