---
id: STORY-019
title: Implement tiered duplicate detection pipeline for artifacts
type: story
status: draft
priority: medium
tags:
- intelligence
- dedup
- P8
suspect: false
links:
- target: REQ-004
  role: implements
- target: ARCH-002
  role: guided_by
created: '2026-04-11'
checklists_applied:
- checklist: check-STORY-019
  timestamp: '2026-04-11T13:45:49Z'
---

# Implement tiered duplicate detection pipeline for artifacts

## Description

Implement a 4-tier duplicate detection pipeline: tag overlap -> TF-IDF keyword similarity -> local embeddings -> LLM confirmation. Results are stored in .specflow/dedup-candidates.yaml as suggestions. The pipeline runs on-demand (specflow check --dedup) and also as search-before-create during artifact creation.

## Acceptance Criteria

1. Given 20 artifacts where REQ-003 and REQ-007 have 80% overlapping tags and similar titles, when specflow check --dedup runs, then the tag overlap tier flags them as potential duplicates, the TF-IDF tier confirms high keyword similarity, and the pair appears in .specflow/dedup-candidates.yaml with a confidence score

2. Given a user runs specflow create to add a new REQ with title 'User Authentication', when the search-before-create check runs and finds existing REQ-005 with title 'Implement User Auth Flow', then the user is warned about the potential duplicate before the artifact is created and can choose to proceed or cancel

3. Given 50 artifacts with no genuine duplicates, when specflow check --dedup runs, then no false positives appear in dedup-candidates.yaml (or fewer than 5% false positive rate at default threshold)

## Out of Scope

- Automatic dedup resolution (human decides)
- Pre-cached embeddings storage

## Dependencies

- None
