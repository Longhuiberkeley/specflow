---
id: STORY-704
title: Typed Finding records for every lint check and audit lens; byte-identical rendering
type: story
status: verified
tags:
- v1.17.1
- engine
- p3
- lint
suspect: false
links:
- target: REQ-053
  role: implements
- target: DEC-FINDINGS-79d8
  role: guided_by
created: '2026-09-30'
fingerprint: sha256:b272d39a77dd
modified: '2026-09-30'
output_files:
- src/specflow/core/findings.py
- src/specflow/core/policy.py
- src/specflow/lib/ac_quality.py
- src/specflow/lib/role_targets.py
- src/specflow/lib/waves.py
- tests/test_findings_model.py
---

# Typed Finding records for every lint check and audit lens; byte-identical rendering

Implements REQ-053 AC3 and AC4 as the P3 step of the ARCH-039 migration order (named, not linked: ARCH-039 is draft).

## Acceptance Criteria

1. Every artifact-lint check returns typed findings (rule_id per finding kind, subjects with a discriminator, severity, class, args) alongside its rendered detail; a test asserts for every check on the fixture corpus that finding counts equal the check blocking and warning counts.
2. Two different problems on one artifact produce two distinct baseline keys (tested on links and output-files).
3. Every check rendered detail is byte-identical to v1.17.0 on the golden corpora, except source-drift and wave-cycles lines, whose order becomes deterministic.
4. project-audit findings map to typed records through one adapter, and class comes from the same policy table lint uses.
5. Source-drift and wave-cycle output no longer depends on PYTHONHASHSEED.
