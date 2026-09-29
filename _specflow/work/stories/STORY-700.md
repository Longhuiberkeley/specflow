---
id: STORY-700
title: Baseline ordering follows SemVer 2.0 section 11
type: story
status: verified
tags:
- v1.17.0
- engine
- p1c
- semver
suspect: false
links:
- target: REQ-035
  role: implements
- target: DEF-001
  role: derives_from
created: '2026-09-30'
fingerprint: sha256:cacb862383e2
modified: '2026-09-30'
output_files:
- src/specflow/lib/baselines.py
- tests/test_baseline_ordering.py
- src/specflow/templates/skills/shared/specflow-ship/references/baseline-naming.md
- src/specflow/templates/skills/shared/specflow-ship/SKILL.md
---

# Baseline ordering follows SemVer 2.0 section 11

## Acceptance Criteria

1. Prerelease identifiers compare per SemVer 2.0 section 11 (numeric identifiers as integers, numeric before alphanumeric) and build metadata is ignored for ordering.
2. A parametrized table drawn from the specification's own examples passes, including rc.10 after rc.9.
3. Post-release suffixes such as -spec-sync sort as prereleases and the policy is documented in the baseline naming reference.
4. DEF-001 (planned label DEF-011) is filed from a failing test and closed by this story.
