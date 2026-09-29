---
id: STORY-694
title: 'Autoresearch CLI: no fabricated metrics, no count-based kill drafts, null-safe
  sorting'
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- autoresearch
suspect: false
links:
- target: REQ-056
  role: implements
- target: REQ-043
  role: implements
created: '2026-09-30'
fingerprint: sha256:6a4416958b2a
modified: '2026-09-30'
output_files:
- src/specflow/commands/autoresearch.py
- src/specflow/cli.py
- tests/test_autoresearch_cli.py
- ROADMAP.md
---

# Autoresearch CLI: no fabricated metrics, no count-based kill drafts, null-safe sorting

## Acceptance Criteria
1. autoresearch log refuses --status kept without --metric-value and writes a null metric for crashed, discarded and no-op runs.
2. Crashed experiments are excluded from measured-experiment jump and guard advisories.
3. suggest-finds emits neutral outcome accounting drawn from hypothesis_outcome and failure_analysis with confidence defaulting to low, and no avoid or exploit directive.
4. The five bare float sort keys use the numeric helper and sort None last; regression tests cover each behaviour.
