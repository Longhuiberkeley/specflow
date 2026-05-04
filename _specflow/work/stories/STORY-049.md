---
id: STORY-049
title: Add ARCH and DDD body quality lint checks
type: story
status: implemented
priority: high
tags:
- lint
- quality
suspect: false
links:
- target: REQ-023
  role: implements
- target: ARCH-017
  role: guided_by
- target: DDD-018
  role: specified_by
created: '2026-05-04'
modified: '2026-05-04'
fingerprint: sha256:1fb053d274f4
---

# Add ARCH and DDD body quality lint checks

Add deterministic body-content quality validation for ARCH and DDD artifacts to artifact_lint.py.

## Acceptance Criteria

1. Given an ARCH artifact with structural section headers and 50+ words, when `artifact-lint` runs the `spec-body` check, then no warnings are produced for that artifact.
2. Given an ARCH artifact body under 50 words, when `artifact-lint` runs, then a warning is reported identifying the artifact as a potential placeholder with the word count.
3. Given an ARCH artifact with no structural section headers (Interface, Component, Responsibility, Data Flow, Structure, Package, Module, Dependencies), when `artifact-lint` runs, then a warning lists the expected header categories.
4. Given a DDD artifact with design section headers and 100+ words, when `artifact-lint` runs the `spec-body` check, then no warnings are produced.
5. Given a DDD artifact body under 100 words, when `artifact-lint` runs, then a warning is reported with the word count.
6. Given a DDD artifact with no design section headers (Function, Data Structure, Algorithm, Error Handling, Invariant, Precondition, Signature, Implementation), when `artifact-lint` runs, then a warning lists the expected header categories.
