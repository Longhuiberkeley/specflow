---
id: SPIKE-BPSURFAC-710b
title: 'BP surface gaps: inert applies_to field + no wildcard; no promote-PREV/CHL
  to BP command'
type: spike
status: completed
tags:
- best-practice
- checklist
- doctrine
- ux
suspect: false
links:
- target: DEC-CHANGERE-066b
  role: derives_from
created: '2026-08-09'
fingerprint: sha256:5b732f9be3f9
modified: '2026-08-10'
rationale: Investigation complete; remaining BP wildcard/promotion enhancements are
  explicitly deferred on the roadmap.
---

## Goal

Investigate and propose fixes for two BP-surface gaps found while auditing SpecFlow usage in a downstream project. Both make the BP surface weaker than its "strong planning / error-catching" billing.

## Gap 1 — inert `applies_to` field + no wildcard

The BP/checklist matching logic (`lib/ci.py:load_active_best_practices`, ~line 33-36) loads a BP for an artifact iff the BP has a `links[]` entry with `role: applies_to` targeting the artifact OR `bp.tags ∩ artifact.tags`. There is NO `applies_to: all` wildcard — a grep of `lib/` + `commands/` finds no `"all"` special-case. Yet users naturally write `applies_to: all` in BP frontmatter (observed in a downstream `BP-001`), expecting it to mean "applies everywhere." It is silently inert: `applies_to` is an allowed LINK ROLE, not a frontmatter field on the BP schema, so the scalar is never read. Repro: a BP with `applies_to: all`, no intersecting tags, and no applies_to links loads for nothing.

Proposed: either (a) support a first-class `applies_to: all` (or empty-tags-means-all) rule so domain doctrine can apply broadly without per-artifact linking, or (b) make `specflow schema best-practice` reject/warn on a frontmatter `applies_to` scalar so the misleading field cannot be authored. Recommend (a) — proactive domain doctrine often SHOULD apply broadly.

## Gap 2 — no promote-PREV/CHL -> BP command

Adversarial-lens and review findings produce `CHL` and `PREV` artifacts but never a `BP`. Grep finds no code path that creates a `best-practice` from findings; BPs are only authored when the discover/plan skills tell the agent to run `specflow create --type best-practice`. So recurring incident patterns (PREVs) and review challenges never graduate into proactive doctrine — the system never learns new BPs from its own findings.

Proposed: a `specflow promote-to-bp <PREV-or-CHL-id>` command (or a `--promote` flag on review/done) that scaffolds a BP draft from a finding for the agent to generalize. Closes the doctrine-learning loop.

## Notes

Together these mean: doctrine only fires if hand-authored with exactly the right tags, and the system never auto-promotes a hard-won lesson into reusable doctrine.
