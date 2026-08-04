---
id: STORY-SHIPV1-cbb2
title: Ship v1.13.2 transcript-mined CLI ergonomics
type: story
status: implemented
priority: high
rationale: Implements the three-wave v1.13.2 ergonomics cycle and adversarial-review
  hardening; accounting-not-policing, no cry-wolf.
tags:
- v1.13.2
- ergonomics
- dogfood
suspect: false
links:
- target: REQ-TRANSCRI-24b7
  role: implements
- target: ARCH-LOUDFAIL-d87a
  role: derives_from
- target: UT-055
  role: verified_by
created: '2026-08-04'
fingerprint: sha256:2a64bb3f9eef
output_files:
- src/specflow/cli.py
- src/specflow/lib/artifacts.py
- src/specflow/lib/lint.py
- src/specflow/lib/impact.py
- src/specflow/commands/update.py
- src/specflow/commands/create.py
- src/specflow/commands/brief.py
- src/specflow/commands/artifact_lint.py
- src/specflow/commands/fingerprint_refresh.py
- tests/test_v132_ergonomics.py
- tests/test_artifacts.py
- tests/test_create_set_fields.py
- tests/test_v124_ergonomics.py
- docs/cli-reference.md
- CHANGELOG.md
modified: '2026-08-04'
---

# Ship v1.13.2 transcript-mined CLI ergonomics

## Scope

Deliver the transcript-mined ergonomics wave: body and AC editing, status validation, nested-map merges, deterministic repair hints, create-link parity, report-only fingerprint discovery, and fast unique DEC blast-radius accounting.

## Acceptance Criteria

1. All behavior is loud-failure-or-advisory; no new blocking gate or mode toggle.
2. AC mutation never clobbers prose, fenced examples, sibling headings, or ambiguous duplicate sections.
3. Every emitted fix command succeeds for the state that triggered it.
4. Full test suite, dry-run project audit, and live↔shipped skill mirror gates are green.

## Verification

Adversarial ultracode review: 70 opus/fable agents, 16 confirmed raw findings (12 distinct after dedup), all fixed and covered. Pre-dogfood suite: 1023/1023. `brief --next`: 1.51s and 5 unique downstream artifacts (from ~58s and double-counted 116).
