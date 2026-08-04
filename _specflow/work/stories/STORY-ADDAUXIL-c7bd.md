---
id: STORY-ADDAUXIL-c7bd
title: Add auxiliary_metrics field to EXPT schema and update test coverage
type: story
status: verified
suspect: false
links:
- target: REQ-AUTORESE-d684
  role: implements
- target: UT-041
  role: verified_by
created: '2026-05-16'
fingerprint: sha256:c73031c9d86f
modified: '2026-08-04'
output_files:
- src/specflow/packs/autoresearch/schemas/experiment.yaml
- tests/test_autoresearch_schema.py
---

# Add auxiliary_metrics field to EXPT schema and update test coverage

## Acceptance Criteria

1. EXPT schema YAML accepts an optional `auxiliary_metrics` field (freeform YAML dict)
2. Artifacts with `auxiliary_metrics` pass `specflow artifact-lint` without warnings
3. Test coverage includes creation and round-trip of EXPT artifacts with auxiliary_metrics populated
