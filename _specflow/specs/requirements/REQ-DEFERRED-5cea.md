---
id: REQ-DEFERRED-5cea
title: 'Deferred lifecycle capabilities: rewind accounting, RTM, RBAC check, supersession,
  quality gates, multi-host'
type: requirement
status: implemented
priority: medium
rationale: Batch implementation of the six capabilities deferred from the 2026-07
  conversational-UX gap analysis; scoped and approved by the maintainer for v1.12.0.
suspect: false
links: []
created: '2026-07-10'
fingerprint: sha256:d512b2374ca6
modified: '2026-07-10'
---

# Deferred lifecycle capabilities: rewind accounting, RTM, RBAC check, supersession, quality gates, multi-host

## Description
Close the six deferred gaps from the 2026-07 UX analysis: reverse-lifecycle phase accounting, a bidirectional requirements-traceability matrix, a user-facing RBAC check, spec supersession for REQ/ARCH/DDD, acceptance-criteria/NFR quality gates, and multi-host skill-install awareness.

## Acceptance Criteria
1. `specflow phase-set <phase> --reason` records forward and rewind transitions in state history without gating (accounting-not-policing); execution state clears when leaving executing.
2. `specflow rtm` prints a REQ→ARCH→STORY→tests matrix with per-column gap markers, --gaps filter, table/markdown/csv formats, and an orphan-test footer.
3. `specflow rbac check` resolves the current git author's roles and can verify a status-transition authorization; single-user projects get a clear not-active message with exit 0.
4. REQ/ARCH/DDD support status 'superseded' (from approved/implemented/verified only) and link role 'supersedes'; docs-staleness continues to warn on superseded citations.
5. artifact-lint flags an empty Acceptance Criteria section as a blocking error and an NFR REQ without a numeric threshold as a non-blocking scope-honest warning ('functional' category exempt).
6. `specflow init` warns when multiple AI-host platforms are detected; `specflow refresh --all-platforms` refreshes every detected host.
