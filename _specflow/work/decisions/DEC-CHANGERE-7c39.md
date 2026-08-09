---
id: DEC-CHANGERE-7c39
title: 'Change Record: chore: trace v1.13.3 AC boundary patch'
type: decision
status: approved
rationale: 'chore: trace v1.13.3 AC boundary patch. Changed: STORY-FIXACCEP-f941.'
tags:
- change-record
- auto-generated
suspect: false
links:
- target: STORY-FIXACCEP-f941
  role: addresses
created: '2026-08-04'
review_status: reviewed
risk_profile:
  tier: 2
  reversibility: irreversible
  blast_radius_count: 0
  confidence: high
  confidence_reason: ''
fingerprint: sha256:6938a165bdf3
modified: '2026-08-10'
thinking_techniques:
- temporal_drift
- premortem
dec_kind: change_record
---

# Change Record: v1.13.3 AC mutation boundary patch

## Commits

- `4278177` — fix: preserve AC section boundaries. Recognizes no-space sibling headings and skips fenced headings during section-end selection; adds exact regressions.
- `ff60f28` — chore: trace v1.13.3 AC boundary patch. Adds STORY-FIXACCEP-f941 against the existing REQ/ARCH/DDD chain.

## Changed Artifacts

- STORY-FIXACCEP-f941 — implemented patch trace and output-file ownership.

## Release rationale

v1.13.2 is immutable and remains published. v1.13.3 supersedes it because the two late temporal-drift findings reproduced as silent body corruption, which violates the release doctrine. No v1.13.2 tag rewriting.
