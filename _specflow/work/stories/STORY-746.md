---
id: STORY-746
title: 'W-1b pack prose: adoption baseline name v0.0.0-adoption.<n>, merge via specflow
  merge, fingerprint seeding, autoresearch/ops recipe fixes, baseline-name guard test'
type: story
status: verified
tags:
- consistency
- v1.17.7
suspect: false
links:
- target: REQ-070
  role: implements
- target: SPIKE-008
  role: derives_from
created: '2026-10-18'
fingerprint: sha256:bb83b250f03a
modified: '2026-10-18'
output_files:
- docs/decisions.md
- docs/lifecycle.md
- src/specflow/commands/adopt.py
- src/specflow/commands/brief.py
- src/specflow/packs/adoption/README.md
- src/specflow/packs/adoption/skills/specflow-adopt/SKILL.md
- src/specflow/packs/adoption/skills/specflow-adopt/references/as-built-baseline-protocol.md
- src/specflow/packs/adoption/skills/specflow-adopt/references/incremental-adoption-protocol.md
- src/specflow/packs/autoresearch/skills/specflow-autoresearch/SKILL.md
- src/specflow/packs/autoresearch/skills/specflow-autoresearch/references/autonomous-loop-protocol.md
- src/specflow/packs/autoresearch/skills/specflow-autoresearch/references/finding-generation-protocol.md
- src/specflow/packs/autoresearch/skills/specflow-autoresearch/references/rolling-evaluation.md
- src/specflow/packs/ops/README.md
- src/specflow/packs/ops/skills/specflow-ops/SKILL.md
- tests/test_adopt_depth_unified.py
- tests/test_prose_baseline_names.py
---

# W-1b pack prose: adoption baseline name v0.0.0-adoption.<n>, merge via specflow merge, fingerprint seeding, autoresearch/ops recipe fixes, baseline-name guard test

## Scope
`src/specflow/packs/adoption/**` (README, SKILL.md, as-built-baseline-protocol.md, incremental-adoption-protocol.md), `src/specflow/packs/autoresearch/**` recipe lines, `src/specflow/packs/ops/README.md` + SKILL recall bullet, `docs/decisions.md` D-19/D-22 lines and `docs/lifecycle.md` adoption lines. New `tests/test_prose_baseline_names.py`.

## Acceptance criteria
- AC1: Given the adoption pack after the change, when every `baseline create <name>` it prescribes is run through `lib.baselines._validate_name`, then each returns None (valid), and the prose names `v0.0.0-adoption.<n>` with the highest n as headline and tells legacy repos to keep `adoption-v0.yaml`.
- AC2: Given incremental-adoption-protocol.md, when the merge recipe is read, then it uses `specflow merge <loser> <survivor>` and `update --output-files`, and no longer uses `update --links` or a hand-moved archive directory.
- AC3: Given Phase 4 of the adopt SKILL.md, when read, then it runs `specflow fingerprint-refresh --source` after the baseline and no longer claims the baseline rationale registers the docs surface.
- AC4: Given the new test, when a shipped prose file prescribes a non-semver baseline name, then the test fails; on the current tree it passes.
- AC5: Given the autoresearch FIND/LOOP manual recipes and the condensation-brief invariant, when read, then they carry the `belongs_to`/`condenses` links and the `condensation_briefs.<n>` form.
