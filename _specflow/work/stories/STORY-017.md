---
id: STORY-017
title: Implement CI integration job with two-pass validation
type: story
status: verified
priority: medium
tags:
- team
- ci
- validation
- P7
suspect: false
links:
- target: REQ-004
  role: implements
- target: ARCH-001
  role: guided_by
- target: UT-007
  role: verified_by
- target: IT-001
  role: verified_by
- target: QT-006
  role: verified_by
created: '2026-04-11'
checklists_applied:
- checklist: check-STORY-017
  timestamp: '2026-04-11T13:45:49Z'
- checklist: check-STORY-017
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-04-22'
fingerprint: sha256:802ee56ce791
version: 1
---

# Implement CI integration job with two-pass validation

## Description

Implement a CI pipeline job template that runs SpecFlow validation as part of the build. Uses a two-pass approach: programmatic checks (zero tokens) run first, LLM-judged checks run only if programmatic checks pass. Provides an informational status badge by default, optionally blocking via branch protection.

## Acceptance Criteria

1. Given specflow init is run with CI integration enabled, then a CI job template is generated (GitHub Actions YAML) that runs specflow validate as a build step with zero-token checks only by default

2. Given the CI job runs on a PR with a broken link in an artifact, then the programmatic validation fails, the LLM-judged checks are skipped (saving tokens), and the PR check shows a failing status with the specific error

3. Given the CI job runs on a PR with all programmatic checks passing, when LLM-judged mode is enabled (opt-in config), then LLM-judged checks execute and results are posted as a PR comment summarizing findings

## Out of Scope

- Test execution record integration (separate concern)
- GitLab CI / other CI platforms (GitHub Actions only for MVP)

## Dependencies

- None
