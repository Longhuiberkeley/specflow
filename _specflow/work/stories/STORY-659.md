---
id: STORY-659
title: Trim on-demand reference files to consult-when pointers
type: story
status: implemented
suspect: false
links:
- target: REQ-042
  role: implements
created: '2026-09-13'
fingerprint: sha256:88597a4209ef
modified: '2026-09-13'
---

# Trim on-demand reference files to consult-when pointers

Per SPIKE-002 STORY-4 section: normative-language, story-writing, spidr, level-boundaries duplicate, wave-computation, status-lifecycle, team-setup, checklist-assembly, severity-levels.

## Acceptance Criteria

1. normative-language.md keeps RFC 2119 + the ambiguity list + one-shall; story-writing.md keeps ≥3 GWT ACs, vertical slice, and the title formula; wave-computation.md keeps the hard/soft/none dependency table; status-lifecycle.md keeps terminal statuses + the DEF cycle + `transitions <ID>`.
2. The byte-identical level-boundaries.md duplicate is deleted in favor of one shared pointer.
3. checklist-assembly.md no longer restates the assembly algorithm (`checklist-run` owns it); severity-levels.md keeps the 3 severity definitions + user override.
4. Template and live `.claude` mirrors stay byte-identical (tests/test_v1143_integration.py).
