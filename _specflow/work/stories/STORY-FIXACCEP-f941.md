---
id: STORY-FIXACCEP-f941
title: Fix Acceptance Criteria mutation boundaries (v1.13.3)
type: story
status: implemented
priority: high
rationale: 'Patch two v1.13.2 body-corruption cases without rewriting the published
  tag: preserve no-space sibling headings and ignore fenced headings during boundary
  selection.'
tags:
- v1.13.3
- bugfix
- ac-mutation
suspect: false
links:
- target: REQ-TRANSCRI-24b7
  role: implements
- target: ARCH-LOUDFAIL-d87a
  role: derives_from
- target: DDD-LOUDFAIL-3e02
  role: specified_by
created: '2026-08-04'
fingerprint: sha256:0090ff56379c
output_files:
- src/specflow/lib/lint.py
- tests/test_v132_ergonomics.py
- CHANGELOG.md
modified: '2026-08-04'
---

# Fix Acceptance Criteria mutation boundaries (v1.13.3)

## Scope

Make AC mutation start/end recognition symmetric for no-space ATX headings and fence-aware for both section starts and boundaries.

## Acceptance Criteria

1. `##Notes` following an h2 AC section survives `update --ac` unchanged.
2. Headings inside fenced code examples never terminate replacement or leave orphan fences.
3. Same-or-higher-level real headings still end the section; h2 AC sections retain ownership of nested h3 children.
4. Full suite and structural audit remain green.

## Verification

Focused v1.13.2 ergonomics suite: 36 passed. Full suite: 1026 passed.
