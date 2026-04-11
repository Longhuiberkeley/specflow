---
id: STORY-008
title: Assemble context-specific review criteria for specflow check
type: story
status: implemented
priority: high
tags:
- review
- checklists
- P5
suspect: false
links:
- target: REQ-004
  role: implements
- target: REQ-001
  role: implements
- target: ARCH-002
  role: guided_by
- target: DDD-003
  role: specified_by
created: '2026-04-11'
modified: '2026-04-11'
fingerprint: sha256:bde4ab3a1b2eb0bd5b4f339b910f9799b866147b39bf46be1e1d4ff7e433206e
checklists_applied:
- checklist: check-STORY-008
  timestamp: '2026-04-11T13:45:49Z'
---


# Assemble context-specific review criteria for specflow check

## Description

Implement the specflow check command that assembles unique review criteria per artifact by combining artifact-type checklists, domain-tag checklists, shared checklists, and learned prevention patterns. Runs automated checks first (zero tokens), then LLM-judged checks. Review is never generic.

## Acceptance Criteria

1. Given REQ-001 tagged [security, auth], when specflow check REQ-001 runs, then the review loads requirement-writing.yaml (type checklist) + authentication.yaml (shared checklist matching auth tag) + any PREV-*.yaml matching security/auth tags, and presents the combined unique criteria set

2. Given the assembled checklist has 3 automated items and 4 LLM-judged items, when a blocking automated item fails, then only the automated results are shown, LLM-judged items are NOT executed (saving tokens), and the user is told to fix the blocking issue first

3. Given no checklists match the artifact's type or tags (e.g., a SPIKE with unusual tags), when specflow check runs, then a warning is shown that no domain-specific criteria were found and only the base artifact-type checklist is applied

4. Given the review completes, then results are persisted to .specflow/checklist-log/ as a timestamped YAML file and the artifact's checklists_applied frontmatter is updated with the checklist ID and timestamp

## Out of Scope

- Proactive challenge engine (STORY-009)
- Reactive/learned patterns extraction (STORY-010)

## Dependencies

- None (can be developed independently)
