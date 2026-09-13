---
id: STORY-649
title: Audit-report privacy redaction at generation time + single-source denylist
  pattern
type: story
status: implemented
rationale: 'The v1.14.6 pre-release review found the project-audit GENERATOR re-leaking
  REQ-038''s denylist into every new report (reports quote spec ACs; REQ-038''s AC
  enumerates the denylist). Fix: lib/privacy.py holds the pattern (single source,
  shipped in wheel); the gate script imports it; every audit-report write site (report.md,
  3 subagent files, findings cache) redacts at write time. Tests: tests/test_privacy_redaction.py
  (token classes, idempotence, cache choke point, pattern-object sharing).'
suspect: false
links:
- target: REQ-038
  role: implements
created: '2026-08-30'
fingerprint: sha256:9cbdb0c07756
modified: '2026-09-13'
output_files:
- src/specflow/lib/privacy.py
- tests/test_privacy_redaction.py
---

# Audit-report privacy redaction at generation time + single-source denylist pattern

## Acceptance Criteria

1. Every project-audit report/cache write passes through `privacy.redact_text`, so quoting REQ-038's AC cannot re-leak the denylist enumeration.
2. src/specflow/lib/privacy.py is the single source of truth for the denylist pattern; scripts/denylist_gate.py imports it rather than embedding a copy.
3. tests/test_privacy_redaction.py pins token classes, idempotence, and prose-safety.
