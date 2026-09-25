---
id: STORY-665
title: 'Autoresearch evidence-sensitive reassessment (REQ-043): CLI, schema, skill
  references'
type: story
status: implemented
tags:
- autoresearch
- v1.16.0
suspect: false
links:
- target: REQ-043
  role: implements
created: '2026-09-21'
fingerprint: sha256:e399616ba8ef
modified: '2026-09-21'
---

# Autoresearch evidence-sensitive reassessment (REQ-043): CLI, schema, skill references

Implements REQ-043. Protocol/review redline: replace count-driven continuation gates with evidence-sensitive reassessment across the CLI and every skill reference, separate evidence from priority fields, and reconcile one-investigator flow with optional boundary review.

Follow-up within the same story: reassessment is bounded to the last three attempts and reads an optional EXPT `research_progress` claim (`evidence_ref` anchored to that EXPT, a distinct finding, a next decision) or a measured keep (new best primary metric / non-zero `delta`). Outcome labels alone, repeated claims or refs across history, malformed/absent records, and repeat keeps no longer count; an older keep cannot mask a stagnant tail. `autoresearch log --research-progress '<json>'` is the validated producer (schema, lint, docs, tests agree). SKILL.md setup now reasons about formulation width before the baseline dry-run, the quick tier keeps its validity checks without a blanket rerun mandate, and the progress advisory / `sensitive` FIND-tag doc defects are corrected.

## Acceptance Criteria

1. `specflow autoresearch status` no longer warns on a direction-count quota or a same-category streak by itself: missing/empty agenda still warns; a sustained same-category or consecutive non-kept run warns only when its last three experiments produced no meaningful progress (a distinct, anchored `research_progress` record or a measured improvement) — never from outcome labels, repeated claims/refs, malformed/absent records, or an older keep; the reassessment warn stays exit 3 and never structural (tests/test_autoresearch_cli.py).
2. Agenda directions accept optional `priority` (`pursue`/`deprioritize`/`blocked`/`revisit`) and `progress` (new evidence + next decision); status's open-directions view excludes `deprioritize`/`blocked` and keeps `revisit` open; EXPT `hypothesis_outcome` accepts `invalid`; EXPT `research_progress` ({evidence_ref, finding, next_decision}, all non-empty) is written by `autoresearch log --research-progress` and malformed input fails the log; schema docs, lint (malformed shape), and the log path agree (tests/test_autoresearch_pack.py).
3. SKILL.md, the reference sheets, and the CLI-printed 8-phase protocol agree on: decomposition as a hypothesis with formulation width and no quota (reasoned before the baseline dry-run in Setup), one coherent hypothesis per EXPT (coordinated component changes allowed), evidence vs priority, recent-window progress accounting, optional boundary review with sequential fallback, runtime-loop vs research-LOOP vs project-cycle terminology, and SPIKE/FIND for nonmetric exploration. No old contradictory rule (3+ consecutive block, 5-discard switch, 3-failure exhaustion, mandatory delegate-review, progress-as-warn, `sensitive` as an EXPT outcome) remains (tests/test_autoresearch_pack.py).
4. `pytest tests/test_autoresearch_cli.py tests/test_autoresearch_pack.py tests/test_autoresearch_schema.py`, `specflow artifact-lint`, `specflow project-audit`, and `specflow pack-validate` are run; unrelated baseline failures are reported, not hidden.
