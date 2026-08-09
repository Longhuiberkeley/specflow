---
id: SPIKE-CHECKLIS-1a12
title: 'Checklist/review behavior gaps: starved review to PREV capture; empty checklist
  results read as success'
type: spike
status: draft
tags:
- checklist
- review
- learning
- observability
suspect: false
links: []
created: '2026-08-09'
fingerprint: sha256:ee1fdea97a1c
modified: '2026-08-09'
---

## Goal

Investigate and propose fixes for two checklist-run / review behavior gaps that obscure real signal.

## Gap 3 — review -> PREV capture is starved

`commands/artifact_review.py:_create_learned_patterns` (~line 200-228) is gated by `learnable_techniques` (which, when empty, correctly defaults to ALL techniques — `lib/learning.py:learnable_techniques`), but it is effectively starved: `artifact_review.run()` only ever feeds info-severity hygiene findings into capture; the deep-review technique prompts are PRINTED for the host agent (~line 346-358) but the CLI never turns the agent's output back into `TechniqueFinding` objects. So review-driven PREV capture rarely fires; PREVs arrive via `specflow done` and defect-closure instead, and the `learnable_techniques` config is mostly cosmetic.

Proposed: let the host agent write review findings back (e.g. ingest a JSON file of findings into `_create_learned_patterns`), OR document explicitly that review-driven PREV capture currently only covers the hygiene lens so users do not over-trust the config knob.

## Gap 4 — checklist-run empty results read as success

`lib/checklists.py:persist_results` (~line 472-474) sets `overall = "passed"` when `all(r.result == "passed" for r in results)`, and `all([])` is `True`. Since the CLI only runs items with `automated: true` AND a `script`, most checklists (whose value is the agent-judged `llm_prompt` items) produce `results: [] -> overall: passed`, `blocking_failures: 0`. Technically correct ("nothing machine-checkable failed") but indistinguishable from a genuine all-green to any automation reading the log. A downstream project's entire checklist-log history shows `results: [] / overall: passed`.

Proposed: write `overall: skipped` (or an explicit `automated_count: 0` field) when the automated pass is empty, so "nothing ran" is not mistaken for "everything passed". Side note: dead code at ~line 454-460 computes a `blocking_failures` local via `for i in []` (comment "Will be passed in real usage") that is discarded; the real key is recomputed at ~473 — worth removing.

## Notes

Both gaps make SpecFlow's review output read as healthier/more complete than it is: capture looks configured but does not fire, and runs look like passes when nothing was evaluated.
