---
id: STORY-048
title: Add optional artifact type schemas and init integration
type: story
status: draft
priority: medium
tags:
- artifact-types
- init
- packs
- flexibility
suspect: false
links:
- target: REQ-017
  role: implements
- target: ARCH-004
  role: guided_by
- target: ARCH-006
  role: guided_by
created: '2026-04-22'
---

# Add optional artifact type schemas and init integration

Ship optional artifact type schemas (hazard, risk, control) and integrate them into `specflow init` so users can enable domain-specific types without needing to author packs.

## Description

The 12 built-in artifact types cover most use cases, but regulated industries sometimes need genuinely different schemas (different status lifecycles, required fields, or link roles). This story adds three optional schema files under `src/specflow/schemas/optional/` and updates `specflow init` to offer them as opt-in choices. No standard content ships — users create their own via `/specflow-pack-author`.

## Acceptance Criteria

1. Given `src/specflow/schemas/optional/`, when the directory is inspected, then `hazard.yaml`, `risk.yaml`, and `control.yaml` schema files exist with valid type, prefix, id_format, required_fields, allowed_status, and allowed_link_roles
2. Given `specflow init`, when run interactively, then optional artifact types are offered as selections
3. Given a user who selects the hazard type, when init completes, then `.specflow/schema/hazard.yaml` exists and `_specflow/specs/hazards/` directory is created
4. Given the hazard schema installed, when `specflow create --type hazard --title "Identify brake failure" --status draft` is run, then a HAZ-001 artifact is created in `_specflow/specs/hazards/`
5. Given optional types installed, when `specflow artifact-lint` is run, then HAZ/RISK/CTRL artifacts are validated against their schemas
6. Given optional types installed, when `specflow trace HAZ-001` is run, then traceability chains work correctly
7. Given `specflow init` run a second time, when optional types are already installed, then schemas are not duplicated
8. Given the full test suite, when `uv run pytest` is run, then all existing plus new tests pass

## Out of Scope

- Shipping any industry-standard content or clauses
- AI-assisted schema generation
- Changes to the 12 built-in artifact types
- Checklists or templates for optional types (users create via pack-author)

## Dependencies

- REQ-017 approved
- `specflow init` command exists
- `lib/scaffold.py` apply_pack() exists
