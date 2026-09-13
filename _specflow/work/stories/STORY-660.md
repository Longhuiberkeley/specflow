---
id: STORY-660
title: 'brief.py: hoist --next + IDs; approve lists exact draft IDs and impact'
type: story
status: implemented
suspect: false
links:
- target: REQ-042
  role: implements
created: '2026-09-13'
fingerprint: sha256:ef5902486a13
modified: '2026-09-13'
---

# brief.py: hoist --next + IDs; approve lists exact draft IDs and impact

Per SPIKE-002 STORY-5 section: consent-vehicle fix for approve --type; conditional chrome; DEC surfacing.

## Acceptance Criteria

1. `brief --next` prints the next action and hoists artifact IDs to the top of the output.
2. The approve digest lists the exact draft IDs with one-line impact before any approval, and never auto-approves.
3. DEC id/title/review_status/constraint are surfaced in the digest.
4. Suspect/stale/drill-down chrome prints only when non-empty.
5. tests/test_brief.py pins each behavior.
