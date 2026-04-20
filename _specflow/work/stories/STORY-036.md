---
id: STORY-036
title: Improve pack-author extraction protocol with verification layer
type: story
status: implemented
priority: high
tags:
- skills
- packs
- quality
suspect: false
links:
- target: REQ-006
  role: implements
created: '2026-04-20'
modified: '2026-04-21'
fingerprint: sha256:6a7a4f1483c8
---

# Improve pack-author extraction protocol with verification layer

## Description

Rewrite the "Large Document Strategy" section of the `/specflow-pack-author` SKILL.md to use a TOC-first extraction protocol with a verification layer. The prompt-only change instructs the AI agent to extract the table of contents first, scope extraction to selected sections, chunk by section boundaries, run a dedup pass, and spot-check 2-3 random sections for completeness.

## Acceptance Criteria

1. Given the `/specflow-pack-author` SKILL.md, when the agent reads the "Large Document Strategy" section, then it finds a TOC-first extraction protocol that instructs extracting the table of contents before any clause extraction, and presenting it as a user selection menu

2. Given the SKILL.md with the new protocol, when the agent processes a large document, then a dedup pass is described for merging overlapping clause fragments before the verification step

3. Given the SKILL.md with the new protocol, when the agent completes clause extraction, then a verification step exists that spot-checks 2-3 source sections and reports discrepancies to the user

4. Given both the installed copy (`.claude/skills/`) and the template copy (`src/specflow/templates/skills/shared/`), when the files are compared, then they are byte-for-byte identical

## Out of Scope

- Changes to the pack-author Python code or CLI
- Changes to small-document extraction path
- Schema changes for pack.yaml

## Dependencies

- REQ-006 must be approved
- Existing `/specflow-pack-author` skill must be installed
