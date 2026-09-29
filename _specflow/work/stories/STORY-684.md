---
id: STORY-684
title: Audit findings cache key covers non-artifact inputs
type: story
status: verified
tags:
- v1.17.0
- engine
- p1
- determinism
suspect: false
links:
- target: REQ-053
  role: implements
created: '2026-09-30'
fingerprint: sha256:b1cc3def8264
modified: '2026-09-30'
output_files:
- src/specflow/commands/project_audit.py
- tests/test_project_audit_cache_key.py
- tests/test_project_audit_fail_loud.py
---

# Audit findings cache key covers non-artifact inputs

## Acceptance Criteria
1. The cache key incorporates hashes of the standards directory, baselines, docs tree and source-tree signature used by cross-cutting lenses.
2. Changing any of those inputs without touching artifacts invalidates the cache.
3. The cache generation constant is bumped and old cache files are ignored.
4. A test proves a docs edit changes the key and an unchanged repo reuses it.
