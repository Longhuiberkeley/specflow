---
id: STORY-661
title: 'handbook.py: drop generic practice bodies; index-only default stdout'
type: story
status: implemented
suspect: false
links:
- target: REQ-042
  role: implements
created: '2026-09-13'
fingerprint: sha256:07d4f9866811
modified: '2026-09-13'
---

# handbook.py: drop generic practice bodies; index-only default stdout

Per SPIKE-002 STORY-6 section.

## Acceptance Criteria

1. Default `specflow handbook` stdout prints domain, count, and the title+tag index only.
2. GENERIC_PRACTICES bodies are no longer appended to every listing.
3. Full practice bodies are available on `--verbose`/`--create`.
4. tests/test_handbook.py pins the index-only default.
