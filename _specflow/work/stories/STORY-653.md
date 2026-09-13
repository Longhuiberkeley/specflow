---
id: STORY-653
title: Rolling-evaluation recipe, churn rule, window_end registration
type: story
status: implemented
rationale: 'Ship the v1.15.0 rolling-evaluation design per DEC-079: references/rolling-evaluation.md
  (fixed vs rolling choice, split configs as researchable object, window sizing +
  historical-to-live tracks, churn rule, window advance = successor COMP), SKILL.md
  wiring, window_end registered in competition.yaml optional_fields with a locking
  test.'
suspect: false
links:
- target: REQ-040
  role: implements
- target: DEC-079
  role: guided_by
created: '2026-09-11'
fingerprint: sha256:423bc885e9df
modified: '2026-09-13'
---

# Rolling-evaluation recipe, churn rule, window_end registration

## Acceptance Criteria

1. references/rolling-evaluation.md ships the fixed-split vs rolling evaluation recipe in the autoresearch pack.
2. DEC-079 records the COMP churn rule (frozen competitions, successor chains, window advance).
3. `window_end` is a registered COMP schema field (tests/test_v1145_locks.py) and the recipe/churn references are pinned by tests/test_autoresearch_pack.py.
