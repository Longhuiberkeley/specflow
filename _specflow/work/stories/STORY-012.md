---
id: STORY-012
title: Implement standards pack architecture and compliance gap analysis
type: story
status: implemented
priority: high
tags:
- compliance
- standards
- gap-analysis
- P6
suspect: false
links:
- target: REQ-005
  role: implements
- target: ARCH-002
  role: guided_by
created: '2026-04-11'
checklists_applied:
- checklist: check-STORY-012
  timestamp: '2026-04-11T13:45:49Z'
modified: '2026-04-12'
fingerprint: sha256:61abebf22c956f48a124c82e3174d10892c124c95e155d0864431b6f34e4f23a
---

# Implement standards pack architecture and compliance gap analysis

## Description

Implement the standards pack system (specflow init --preset) that adds industry-specific artifact types, schemas, and checklists, and the specflow compliance command that maps artifacts to standard clauses and reports coverage gaps.

## Acceptance Criteria

1. Given specflow init --preset iso26262 is run, then the ISO 26262 pack is loaded from packs/iso26262/, additional schemas (HAZ, SG, SR) are copied to .specflow/schema/, additional checklists are copied to .specflow/checklists/, and standard clauses are imported into .specflow/standards/ as YAML files

2. Given a project with 45 artifacts mapped to standard clauses via complies_with links and 50 total standard clauses, when specflow compliance --standard iso26262 runs, then the output shows 45 covered clauses with their linked artifact IDs and 5 uncovered clauses listed as compliance gaps

3. Given a project with no standards imported, when specflow compliance runs, then a clear error message explains that no standards are installed and suggests using --preset during init

## Out of Scope

- Specific ISO 26262 HARA/FMEA templates (future pack content)
- Cross-repo traceability (P8)

## Dependencies

- None (can be developed independently)
