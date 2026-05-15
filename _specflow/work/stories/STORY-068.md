---
id: STORY-068
title: Create autoresearch pack directory and pack.yaml manifest
type: story
status: draft
priority: high
tags:
- autoresearch
- wave-2
- pack
suspect: false
links:
- target: REQ-028
  role: implements
- target: ARCH-022
  role: guided_by
created: '2026-05-15'
---

# Create autoresearch pack directory and pack.yaml manifest

## Outcome

`src/specflow/packs/autoresearch/` exists with a complete `pack.yaml` manifest declaring artifact types, directories, and skills.

## Scope

Create:

```
src/specflow/packs/autoresearch/
├── pack.yaml
├── README.md
└── (subdirectories created by Wave 2 STORY-069 and Wave 3 stories)
```

`pack.yaml` contents:

```yaml
name: autoresearch
version: "0.1.0"
description: >
  Autonomous research loop for SpecFlow. Adds competition-scoped
  experimentation with knowledge condensation. Adapted from
  https://github.com/Longhuiberkeley/autoresearch_fork.
adds_artifact_types:
  - competition
  - loop
  - experiment
  - finding
adds_directories:
  - specs/competitions
  - work/loops
  - work/experiments
  - specs/findings
adds_skills:
  - specflow-autoresearch
```

## Acceptance

- `specflow init --with-pack autoresearch` in a fresh test project creates all four `_specflow/specs/<...>` directories
- The 4 schemas (from STORY-069) are copied into `.specflow/schema/`
- The skill (from Wave 3) is copied into the platform's skills directory
- README.md briefly explains pack purpose and references the autoresearch_fork attribution
