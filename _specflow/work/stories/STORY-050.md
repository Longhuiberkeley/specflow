---
id: STORY-050
title: Add REQ-to-ARCH coverage and story minimum AC checks
type: story
status: implemented
priority: high
tags:
- lint
- coverage
suspect: false
links:
- target: REQ-023
  role: implements
- target: ARCH-017
  role: guided_by
- target: DDD-018
  role: specified_by
created: '2026-05-04'
modified: '2026-05-04'
fingerprint: sha256:67dac14c2536
---

# Add REQ-to-ARCH coverage and story minimum AC checks

Extend artifact-lint coverage and story-size checks to verify REQ-to-ARCH traceability and minimum story acceptance criteria.

## Acceptance Criteria

1. Given an approved REQ with at least one ARCH artifact linking to it via `derives_from`, when `artifact-lint` runs, then no coverage warning is produced for that REQ.
2. Given an approved REQ with no ARCH artifact linking to it via `derives_from`, when `artifact-lint` runs, then a warning reports that the REQ lacks architectural decomposition.
3. Given a story with 2 or more acceptance criteria, when `artifact-lint` runs, then no minimum-AC warning is produced.
4. Given a story with 0 or 1 acceptance criteria, when `artifact-lint` runs, then a warning reports the count and the minimum of 2.
5. Given a story with no Acceptance Criteria section at all, when `artifact-lint` runs, then a warning reports the missing section.
