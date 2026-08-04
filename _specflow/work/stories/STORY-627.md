---
id: STORY-627
title: Fix project-audit baseline selection to semver ordering
type: story
status: verified
rationale: Fixes CHL-343 (audit compares v1.9.0->v1.9.2 despite newer baselines)
suspect: false
links:
- target: UT-045
  role: verified_by
- target: REQ-035
  role: implements
created: '2026-08-04'
fingerprint: sha256:b76debaf06ec
modified: '2026-08-04'
output_files:
- src/specflow/lib/baselines.py
- tests/test_baselines.py
---

# Fix project-audit baseline selection to semver ordering

project-audit picks its comparison baseline pair via lexicographic sort (list_baselines), so with baselines v0.2.0..v1.13.3 on disk it compares v1.9.0 -> v1.9.2 instead of v1.13.2 -> v1.13.3. Both the report header and the actual drift analysis use the wrong pair. Fix: semver-aware ascending ordering in src/specflow/lib/baselines.py list_baselines, plus regression tests in tests/test_baselines.py (semver order, lex-trap regression, non-semver fallback, empty dir). See CHL-343.
