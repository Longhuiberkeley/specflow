---
id: STORY-045
title: Add specflow generate-tests command and update execute skill
type: story
status: verified
priority: high
tags:
- testing
- vmodel
- scaffolding
suspect: false
links:
- target: REQ-013
  role: implements
- target: ARCH-001
  role: guided_by
- target: ARCH-002
  role: guided_by
- target: UT-007
  role: verified_by
- target: IT-001
  role: verified_by
- target: QT-012
  role: verified_by
created: '2026-04-21'
modified: '2026-04-22'
fingerprint: sha256:d0d41ed8b5f6
version: 1
---

# Add specflow generate-tests command and update execute skill

Create the specflow generate-tests CLI command for deterministic test stub scaffolding and update the /specflow-execute skill to call it.

## Description

Given implemented REQ/ARCH/DDD artifacts, the test stubs (UT/IT/QT with correct links, titles, and section headers) can be derived 100% deterministically. This story creates a new CLI command that generates these stubs and updates the execute skill to use it.

## Acceptance Criteria

1. Given an implemented DDD-001 artifact, when `specflow generate-tests --from DDD-001` is run, then a UT stub is created with type unit-test, title "Test \<DDD title\>", and verified_by link to DDD-001
2. Given an implemented REQ-001 artifact, when `specflow generate-tests --from REQ-001` is run, then a QT stub is created with acceptance criteria copied as test case placeholders
3. Given multiple specs missing verification pairs, when `specflow generate-tests` is run with no args, then stubs are created for all missing pairs
4. Given `specflow generate-tests --dry-run`, when run, then no files are written but a summary of what would be created is printed
5. Given an existing UT linked to DDD-001, when `specflow generate-tests --from DDD-001` is run again, then no duplicate UT is created
6. Given the /specflow-execute SKILL.md, when reviewed, then Step 5 references `specflow generate-tests` as the stub creation mechanism
7. Given the full test suite, when `uv run pytest` is run, then all existing plus new tests pass

## Out of Scope

- AI-generated test case content (stub bodies are placeholders only)
- Running the generated tests (they are spec artifacts, not executable test files)
- Test execution framework integration

## Dependencies

- None — the command operates on existing artifact data
