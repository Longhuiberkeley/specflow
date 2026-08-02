---
id: ARCH-028
title: "Deferred lifecycle capabilities \u2014 accounting-based command surfaces"
type: architecture
status: implemented
priority: medium
rationale: "Refines REQ-DEFERRED-5cea: the six deferred lifecycle capabilities (phase-set\
  \ accounting, RTM, RBAC check, supersession, AC/NFR gates, multi-host) are unified\
  \ by being accounting/recording surfaces over the existing artifact graph \u2014\
  \ none becomes a gate. Retroactive design record of v1.12.0 shipped capability;\
  \ no new types or link roles."
tags:
- lifecycle
- architecture
- accounting-not-policing
- v1.12
suspect: false
links:
- target: REQ-DEFERRED-5cea
  role: derives_from
created: '2026-08-03'
fingerprint: sha256:174bed332720
version: 1
---

# Deferred lifecycle capabilities — accounting-based command surfaces

Refines REQ-DEFERRED-5cea: the six capabilities deferred from the 2026-07 UX
gap analysis and shipped in v1.12.0. Retroactive design record of shipped
capability. The unifying architectural property is that every one of the six
is an ACCOUNTING surface — it records, queries, or warns — and none becomes a
gate. No new artifact types and no new link roles were introduced (the
`supersedes` role and `superseded` status were already in the D-18 frozen
vocabulary); each command composes the existing artifact graph.

## Context

The 2026-07 conversational-UX gap analysis identified six deferred lifecycle
capabilities. Each was scoped as a read/recording surface over the existing
artifact model rather than a new enforcement layer, preserving the
accounting-not-policing doctrine (BP-006).

## The six capabilities

1. **Reverse-lifecycle phase accounting** (`commands/phase_set.py`).
   `specflow phase-set <phase> --reason` records BOTH forward and rewind
   transitions in state history. It never gates a transition; execution state
   clears when leaving the `executing` phase. Accounting: the history is the
   evidence, the operator is the authority.

2. **Bidirectional requirements-traceability matrix** (`commands/rtm.py`).
   `specflow rtm` walks REQ→ARCH→DDD→STORY→tests in both directions and prints
   a matrix with per-column gap markers, `--gaps` filter, table/markdown/csv
   formats, and an orphan-test footer. Pure read; never writes.

3. **User-facing RBAC check** (`commands/rbac_check.py`).
   `specflow rbac check` resolves the current git author's roles
   (`CODEOWNERS`-driven) and can verify a status-transition authorization.
   Single-user projects get a clear not-active message and exit 0 — never a
   blocker for a solo maintainer.

4. **Spec supersession** (link role `supersedes` + status `superseded`).
   REQ/ARCH/DDD may move to `superseded` (from approved/implemented/verified).
   The new artifact links `supersedes` → the old one first; docs-staleness then
   warns on any doc citing the superseded artifact. The role/status already
   existed in D-18; this capability exercised them end-to-end.

5. **Acceptance-criteria / NFR quality gates** (`commands/artifact_lint.py`).
   artifact-lint flags an empty Acceptance Criteria section as a blocking
   error and an NFR REQ without a numeric threshold as a non-blocking
   scope-honest warning (`functional` category exempt). Lint, not a runtime
   gate — the release gate calls lint, lint does not become the gate.

6. **Multi-host skill-install awareness** (`commands/init.py`, `commands/refresh.py`).
   `specflow init` warns when multiple AI-host platforms are detected;
   `specflow refresh --all-platforms` refreshes every detected host's skills.
   Awareness + convenience, never a hard choice forced on the user.

## Components

All six reuse the existing artifact graph, link vocabulary, status-transition
model, and config. They add COMMANDS, not mechanisms:

```
existing artifact graph (REQ/ARCH/DDD/STORY/tests + links + status)
        │
        ├── phase-set    → writes execution-state history (accounting)
        ├── rtm          → reads the graph into a matrix (read-only)
        ├── rbac check   → reads CODEOWNERS + transition rules (read-only)
        ├── supersedes   → existing link role + status, exercised end-to-end
        ├── artifact-lint→ existing lint engine, two new checks
        └── init/refresh → existing skill-sync path, multi-host detection
```

## Keystone invariant

None of the six escalates a release-gate exit code on its own. The structural
exit-code drivers (missing ARCH, missing STORY, orphan code) live in
`project-audit` / `artifact-lint.check_coverage`, unchanged by these
capabilities. Supersession and phase-rewind are recorded honestly; the human
decides what they mean.

## Verification

- `tests/test_phase_set.py`, `tests/test_rtm.py`, `tests/test_rbac.py`,
  supersession, AC/NFR lint, and multi-host detection each have dedicated
  coverage (the v1.12.0 wave).
