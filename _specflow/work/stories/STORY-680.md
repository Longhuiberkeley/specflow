---
id: STORY-680
title: find_missing_v_pairs requires the paired test type and returns the test prefix
type: story
status: verified
tags:
- v1.17.0
- engine
- p1
- coverage
suspect: false
links:
- target: REQ-013
  role: implements
- target: REQ-012
  role: implements
created: '2026-09-30'
fingerprint: sha256:a13aad4d1b06
modified: '2026-09-30'
output_files:
- src/specflow/lib/artifacts.py
- src/specflow/commands/artifact_lint.py
- tests/test_coverage_semantics.py
---

# find_missing_v_pairs requires the paired test type and returns the test prefix

## Acceptance Criteria
1. A spec whose only verified_by comes from a non-test artifact is reported as missing its V-pair.
2. A spec's own outgoing verified_by to the paired test type counts as paired.
3. The returned tuple carries the paired test prefix, matching the function docstring.
4. A DEC records the change against the do-not-fix note and cites REQ-012 and REQ-013.
