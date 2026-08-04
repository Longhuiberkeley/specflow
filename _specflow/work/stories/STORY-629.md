---
id: STORY-629
title: Add dec_kind discriminator to DEC artifacts
type: story
status: verified
rationale: Addresses CHL-342 DEC type conflation
suspect: false
links:
- target: UT-047
  role: verified_by
- target: REQ-035
  role: implements
created: '2026-08-04'
fingerprint: sha256:a657f806a0a2
modified: '2026-08-04'
output_files:
- src/specflow/commands/document_changes.py
- .specflow/schema/decision.yaml
- tests/test_risk.py
---

# Add dec_kind discriminator to DEC artifacts

49 of 62 DEC artifacts are auto-generated change records; the DEC type conflates design decisions with per-commit bookkeeping. Add a dec_kind discriminator (adr | change_record): schema optional field in .specflow/schema/decision.yaml, document_changes generator stamps change_record, and backfill-stamp all 62 existing DECs. See CHL-342.
