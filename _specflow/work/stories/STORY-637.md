---
id: STORY-637
title: 'v1.14.2 review fixes: typed refined_by direction, --set guard, IT-038 truthfulness,
  lint crash guard'
type: story
status: implemented
tags:
- review-fix
suspect: false
links:
- target: REQ-003
  role: implements
- target: REQ-034
  role: implements
- target: REQ-009
  role: implements
created: '2026-08-26'
fingerprint: sha256:c4ce6f80b91a
modified: '2026-08-26'
output_files:
- src/specflow/lib/artifacts.py
- src/specflow/commands/autoresearch.py
- src/specflow/commands/artifact_lint.py
- tests/test_artifacts.py
- tests/test_autoresearch_cli.py
- tests/test_trace_integration.py
---

# v1.14.2 review fixes: typed refined_by direction, --set guard, IT-038 truthfulness, lint crash guard

## Goal

Post-implementation review of v1.14.1 found four defects; fix them as v1.14.2.

## Acceptance Criteria

1. refined_by direction is type-pair aware: REQ refined_by→ARCH (canonical, target refines source) is NOT upstream and renders downstream; legacy DDD refined_by→ARCH remains upstream. RUN implements→REQ/ARCH traces upstream (ops run schema allows implements). Spec-owned verified_by→QT/IT/UT edges render downstream for REQ/ARCH/DDD sources.
2. autoresearch log/plan reject --set overrides of reserved keys (links, loop, competition, status) with a clear error; regression test.
3. IT-038 becomes truthful: an assertion-bearing integration test renders STORY-632's real trace output (REQ-005/REQ-001 upstream, DEC-077 guided_by, UT-069/IT-037/QT-044 downstream) and the contract references it; verify stamp refreshed.
4. autoresearch-logging lint guards non-string parent fields (isinstance str) instead of crashing on malformed frontmatter; comment corrected.

## Authorization note
Pre-authorized by the owner (scheduled autonomous task, oc-later 2026-08-26): fix-and-improve after review was the standing instruction.
