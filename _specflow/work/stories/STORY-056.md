---
id: STORY-056
title: Add SPIDR dimension coverage lint check
type: story
status: implemented
priority: low
tags:
- lint
- spidr
- plan
suspect: false
links:
- target: REQ-026
  role: implements
- target: ARCH-020
  role: guided_by
- target: DDD-020
  role: specified_by
created: '2026-05-04'
modified: '2026-05-05'
fingerprint: sha256:aa12a11098e3
output_files:
- tests/test_spidr_coverage.py
---

# Add SPIDR dimension coverage lint check

Add a deterministic lint check that reports when SPIDR dimensions have no stories, ensuring decomposition coverage across all five sources.

## Acceptance Criteria

1. Given stories tagged with all five SPIDR dimensions (spidr-spike, spidr-path, spidr-interface, spidr-data, spidr-rules), when `artifact-lint` runs the `spidr-coverage` check, then no warnings are produced.
2. Given stories where the spidr-spike dimension has no stories, when `artifact-lint` runs, then a warning reports the uncovered dimension.
3. Given zero stories with any spidr-* tag, when `artifact-lint` runs, then an informational note suggests tagging stories during plan Step 5.
4. Given stories with only spidr-path tags, when `artifact-lint` runs, then warnings report the 4 missing dimensions.
