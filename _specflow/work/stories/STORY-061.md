---
id: STORY-061
title: Add inter-REQ dependency prompting to discover skill
type: story
status: implemented
priority: low
tags:
- discover
- dependencies
suspect: false
links:
- target: REQ-027
  role: implements
- target: ARCH-021
  role: guided_by
- target: DDD-021
  role: specified_by
created: '2026-05-04'
modified: '2026-05-05'
fingerprint: sha256:6bae276e1383
---

# Add inter-REQ dependency prompting to discover skill

Update the discover skill to explicitly prompt for inter-REQ dependencies and record them as derives_from links between requirement artifacts.

## Acceptance Criteria

1. Given a discovery session with multiple REQs, when Step 4 (summary) is presented, then the skill asks whether any requirements depend on others being implemented first.
2. Given the user identifies REQ-005 depends on REQ-002, when the dependency is recorded, then REQ-005 receives a `derives_from` link to REQ-002.
3. Given the user says no dependencies exist, when Step 4 completes, then no inter-REQ links are created and the skill proceeds to Step 5.
4. Given the plan skill reads REQs with inter-REQ links, when computing story waves, then the dependency ordering can influence wave sequencing.
