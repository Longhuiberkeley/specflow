---
id: STORY-075
title: Validate the autoresearch pack end-to-end in a real research project
type: story
status: implemented
priority: high
tags:
- autoresearch
- wave-4
- test
- pilot
suspect: false
links:
- target: REQ-028
  role: implements
- target: REQ-029
  role: implements
- target: REQ-030
  role: implements
- target: REQ-032
  role: implements
created: '2026-05-15'
fingerprint: sha256:96ff3242dc57
modified: '2026-08-30'
version: 2
---

# Validate the autoresearch pack end-to-end in a real research project

## Outcome

The autoresearch pack is validated through automated tests and a real research project.

## Test scope

| Test | What it covers |
|---|---|
| Schema lifecycle test | Create COMP/LOOP/EXPT/FIND with valid + invalid statuses |
| Pack install integration test | `specflow init --with-pack autoresearch` produces a complete install (schemas, directories, skill) |
| EXPT terminal-status test | Verify all 4 EXPT statuses (kept/discarded/crashed/no_op) permit direct creation |
| End-to-end chain test | Create COMP → LOOP → 3 EXPTs → 1 FIND; `specflow trace COMP-NNN` walks all of them |
| Skill no-overwrite test | Reinstall pack does not clobber edited skill files |

## Validation scope

Install the autoresearch pack into a real research project:

1. Run `specflow init --with-pack autoresearch` (or apply to existing init)
2. Create COMP-001 for the first research campaign (single split) and COMP-002 for the second (walk-forward)
3. Migrate any existing upstream research-fork state into the artifact model (best-effort)
4. Run one LOOP end-to-end and confirm:
   - EXPT artifacts populate as expected
   - Loop reaches plateau or budget cleanly
   - FIND can be authored from the LOOP's EXPTs
5. Confirm `specflow status` shows a Research row
6. Confirm `specflow trace COMP-001` renders the hierarchy

## Acceptance Criteria

1. All 5 tests pass in CI
2. Validation produces at least one COMP, one LOOP, ≥10 EXPTs, and one FIND
3. User confirms the workflow feels natural for their research use case
