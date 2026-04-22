---
id: STORY-029
title: Add deterministic analytical passes to the V-model
type: story
status: verified
priority: medium
tags:
- analysis
- V-model
- M3-depth
suspect: false
created: '2026-04-14'
links:
- target: STORY-022
  role: depends_on
- target: STORY-024
  role: depends_on
- target: REQ-020
  role: implements
- target: ARCH-012
  role: guided_by
- target: DDD-009
  role: specified_by
- target: QT-021
  role: verified_by
- target: IT-014
  role: verified_by
- target: UT-015
  role: verified_by
checklists_applied:
- checklist: check-STORY-029
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-04-22'
fingerprint: sha256:e2e291118dad
version: 1
---

# Add deterministic analytical passes to the V-model

## Description

Add deterministic (zero-token) analytical passes to strengthen the V-model specification layer, as described in retrospective §13.9. These feeds into the quality/review layer (STORY-024) and project-audit (STORY-030).

### Capabilities

1. **Conflict detection across REQs** — Detect contradictions between requirements (not just duplicates). Flag REQs that specify conflicting constraints on the same system element (e.g., REQ-003 says "response time < 200ms" and REQ-009 says "batch processing may take up to 5 minutes" for the same endpoint).

2. **Non-functional taxonomy as a first-class REQ field** — Add `non_functional_category` optional field to REQ schema (performance, security, reliability, usability, maintainability, scalability, compliance). Enables structured NFR coverage analysis.

3. **Coverage-completeness check** — Verify REQ→STORY→test coverage at all three test levels (UT/IT/QT). Report gaps where approved REQs lack linked stories, or approved stories lack linked tests of all required levels.

4. **Story-too-big warnings** — Flag stories with excessive acceptance criteria count, body length, or estimated complexity. Heuristic-based: warn when a STORY has >8 acceptance criteria or references >5 distinct subsystems.

## Acceptance Criteria

1. `specflow artifact-lint` detects and reports conflicting constraints between REQs (e.g., same system element with contradictory performance/behavior specifications) — zero-token AST/pattern matching

2. REQ schema includes optional `non_functional_category` field; `specflow create requirement` accepts `--nfr-category` flag

3. `specflow artifact-lint --type coverage` reports REQ→STORY→test gaps: REQs with no stories, stories with no UT, stories missing IT or QT where required by the V-model

4. `specflow artifact-lint` warns on stories exceeding size heuristics (>8 acceptance criteria or >5 subsystem references)

5. All checks are deterministic (zero LLM tokens) and run in the programmatic lint pass

## Out of Scope

- LLM-driven conflict resolution (human decides)
- Automated story splitting (human decides)
- Industry-specific NFR taxonomies (BYOC territory)

## Dependencies

- STORY-022 (command rename — lint runs under new name)
- STORY-024 (artifact-review composes these passes)
