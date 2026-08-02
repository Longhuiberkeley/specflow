---
id: STORY-SMALLFIX-621b
title: Small fixes - concurrent-LOOP gate, noise probe, test cleanup
type: story
status: draft
suspect: false
links:
- target: REQ-035
  role: implements
created: '2026-05-16'
fingerprint: sha256:6ef30b99260e
---

# Small fixes - concurrent-LOOP gate, noise probe, test cleanup

## Acceptance Criteria

1. Concurrent-LOOP gate prevents starting a second LOOP on the same COMP while one is active
2. Noise probe test verifies metric variance below a configurable threshold before trusting results
3. Flaky or obsolete tests are removed or stabilized without reducing coverage
