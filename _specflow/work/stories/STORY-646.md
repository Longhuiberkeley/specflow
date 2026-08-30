---
id: STORY-646
title: 'v1.14.5: privacy scrub of personal fingerprints + autoresearch/ops wiring
  fixes'
type: story
status: implemented
suspect: false
links:
- target: REQ-038
  role: implements
created: '2026-08-30'
summary: 'Pack-wide fingerprint sweep with domain-neutral example rewrites (tabular-ML
  churn / A-B test); test fixture renames + baseline regen; doc scrubs (DEC-059, STORY-075,
  SPIKE-001, archived plan doc); untrack .antigravitycli/.gemini; seven wiring one-liners:
  experiment.yaml += competition, competition.yaml += custom_categories, lint condensation_brief_\d+
  acceptance, ops SKILL.md informs->derives_from, quant.md add role, loop.yaml +=
  derives_from, brief.py MON-escalation accounting + test.'
fingerprint: sha256:f87f81bbc5b2
modified: '2026-08-30'
version: 1
---

# v1.14.5: privacy scrub of personal fingerprints + autoresearch/ops wiring fixes

## Acceptance Criteria

- Pack-wide fingerprint sweep complete across the 5 autoresearch skill files; denylist grep clean; protocol shape preserved (verified by reviewer).
- Fixture/baseline renames landed: tests/test_ci_generation.py, tests/test_baselines.py, 12 baseline YAMLs — targeted tests green.
- Seven wiring one-liners landed (experiment.yaml competition; competition.yaml custom_categories; loop.yaml derives_from; lint condensation_brief_N; ops informs->derives_from; quant.md role added; brief.py MON-escalation credit + test) — 1429 tests green.
- Docs scrubs + .antigravitycli/.gemini untracked + stale branch/worktree hygiene done; lint PASS, audit warnings-only, QT-049 stamped exit 0.
