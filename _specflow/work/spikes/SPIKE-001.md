---
id: SPIKE-001
title: "autoresearch_fork inventory \u2014 diff list before Wave 3"
type: spike
status: draft
priority: high
rationale: The fork contains ~1670 lines of battle-tested protocol. Adapting blindly
  risks losing crash-recovery and stuck-detection specifics. A scoped read-through
  with a diff list de-risks Wave 3.
tags:
- autoresearch
- spike
- research
suspect: false
links:
- target: REQ-028
  role: derives_from
created: '2026-05-15'
---

# autoresearch_fork inventory — diff list before Wave 3

## Goal

Produce a concrete, file-by-file diff list specifying exactly what changes when adapting each autoresearch_fork document to SpecFlow.

## Inputs

`/Volumes/ExternalDrive/Documents_external/githubcode/autoresearch_fork/.claude/skills/autoresearch/`

| Source file | Lines | Adaptation target |
|---|---|---|
| `SKILL.md` | 313 | `specflow-autoresearch/SKILL.md` |
| `references/autonomous-loop-protocol.md` | 1030 | `references/autonomous-loop-protocol.md` (Phases 1, 7, 8 changed) |
| `references/core-principles.md` | 207 | merge into SKILL.md |
| `references/results-logging.md` | 194 | merge into loop protocol (TSV → EXPT) |
| `references/common-setup.md` | 82 | merge into SKILL.md |
| `references/plan-workflow.md` | 117 | adapt → `competition-setup-protocol.md` |
| `references/context-rotation-protocol.md` | 247 | **deferred (v2)** — fresh-mode |
| `agents/autoresearch-worker.md` | 41 | **deferred (v2)** — fresh-mode worker |

## Deliverable

A diff plan (~1 page) listing per source file:

1. **Preserve verbatim**: which sections stay
2. **Modify**: which sections change and how (specific edits like "replace TSV append with `specflow create --type experiment`")
3. **Delete**: which sections do not apply to SpecFlow
4. **Add**: new sections SpecFlow needs (e.g., "reading FINDs via `specflow trace COMP-NNN`")

## Timebox

Half a day. The output unblocks Stories 8-11 (the four protocol docs).

## Acceptance

Spike is complete when the diff plan is committed to `docs/autoresearch-fork-adaptation.md` and reviewed by the user.
