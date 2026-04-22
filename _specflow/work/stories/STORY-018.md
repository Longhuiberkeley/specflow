---
id: STORY-018
title: Implement ReqIF import and export for DOORS/Polarion interchange
type: story
status: verified
priority: low
tags:
- team
- reqif
- interchange
- P7
suspect: false
links:
- target: REQ-005
  role: implements
- target: ARCH-001
  role: guided_by
- target: UT-007
  role: verified_by
- target: IT-001
  role: verified_by
- target: QT-007
  role: verified_by
created: '2026-04-11'
checklists_applied:
- checklist: check-STORY-018
  timestamp: '2026-04-11T13:45:49Z'
- checklist: check-STORY-018
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-04-22'
fingerprint: sha256:2cfa543fa94c
---

# Implement ReqIF import and export for DOORS/Polarion interchange

## Description

Implement specflow import reqif and specflow export reqif CLI subcommands that perform mechanical transformation between SpecFlow's YAML-frontmatter Markdown format and ReqIF XML. Enables interchange with DOORS, Polarion, and other requirements management tools.

## Acceptance Criteria

1. Given a ReqIF XML file containing 10 requirements with attributes (ID, title, description, status), when specflow import reqif requirements.reqif runs, then 10 REQ-*.md files are created in _specflow/specs/requirements/ with mapped frontmatter fields and Markdown body content extracted from the ReqIF rich text

2. Given 5 SpecFlow REQ artifacts with frontmatter and Markdown body, when specflow export reqif --output requirements.reqif runs, then a valid ReqIF XML file is produced with all artifacts represented as SpecObjects with mapped attributes

3. Given a ReqIF file with attributes that have no SpecFlow equivalent, when import runs, then unmapped attributes are preserved in a reqif_metadata field in the artifact's frontmatter so round-trip fidelity is maintained

## Out of Scope

- Real-time DOORS/Polarion synchronization
- ReqIF exchange documents with multiple SpecRelationGroups

## Dependencies

- None
