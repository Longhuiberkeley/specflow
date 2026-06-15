---
id: STORY-075
title: Test autoresearch pack end-to-end and pilot with quant_trade_rnd
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
---

# Test autoresearch pack end-to-end and pilot with quant_trade_rnd

## Outcome

The autoresearch pack is validated through automated tests and a real pilot.

## Test scope

| Test | What it covers |
|---|---|
| Schema lifecycle test | Create COMP/LOOP/EXPT/FIND with valid + invalid statuses |
| Pack install integration test | `specflow init --with-pack autoresearch` produces a complete install (schemas, directories, skill) |
| EXPT terminal-status test | Verify all 4 EXPT statuses (kept/discarded/crashed/no_op) permit direct creation |
| End-to-end chain test | Create COMP → LOOP → 3 EXPTs → 1 FIND; `specflow trace COMP-NNN` walks all of them |
| Skill no-overwrite test | Reinstall pack does not clobber edited skill files |

## Pilot scope

Install the autoresearch pack into the user's `quant_trade_rnd` project:

1. Run `specflow init --with-pack autoresearch` (or apply to existing init)
2. Create COMP-001 for Track A (single split) and COMP-002 for Track B (walk-forward)
3. Migrate any existing autoresearch_fork state into the artifact model (best-effort)
4. Run one LOOP end-to-end and confirm:
   - EXPT artifacts populate as expected
   - Loop reaches plateau or budget cleanly
   - FIND can be authored from the LOOP's EXPTs
5. Confirm `specflow status` shows a Research row
6. Confirm `specflow trace COMP-001` renders the hierarchy

## Acceptance Criteria

1. All 5 tests pass in CI
2. Pilot produces at least one COMP, one LOOP, ≥10 EXPTs, and one FIND
3. User confirms the workflow feels natural for their backtesting use case (CS2 / HKJC / crypto)
