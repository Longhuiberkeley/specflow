---
id: STORY-744
title: Framing reference, discover step 0 and description, start-router clause, positioning
  docs, pins
type: story
status: verified
tags:
- core
- skills
suspect: false
links:
- target: REQ-069
  role: implements
created: '2026-10-18'
fingerprint: sha256:19cd0e4dbe2b
modified: '2026-10-18'
output_files:
- src/specflow/templates/skills/shared/specflow-discover/references/framing.md
- .claude/skills/specflow-discover/references/framing.md
- src/specflow/templates/skills/shared/specflow-discover/SKILL.md
- .claude/skills/specflow-discover/SKILL.md
- src/specflow/templates/skills/shared/specflow-discover/references/readiness-assessment.md
- .claude/skills/specflow-discover/references/readiness-assessment.md
- src/specflow/templates/skills/shared/specflow-start/SKILL.md
- .claude/skills/specflow-start/SKILL.md
- docs/comparison.md
- README.md
- docs/lifecycle.md
- tests/test_core_skill_text.py
- src/specflow/commands/artifact_lint.py
- tests/test_framing_dec_orphan.py
- docs/commands.md
thinking_techniques:
- worst_case_user
- composition
---

# Framing reference, discover step 0 and description, start-router clause, positioning docs, pins

## Summary

Implement REQ-069 under DEC-104, prose only, both skill trees byte-identical. (1) Add `specflow-discover/references/framing.md` (≤60 lines, RFC 2119, attribution header; the drafted text is supplied by the parent). (2) `specflow-discover/SKILL.md`: rewrite the description to "Shape a fuzzy idea, or author/revise REQs when the requested change has no approved requirements yet, or rewind to requirements."; add a step 0 "Frame (only when readiness is near zero)" of two or three lines pointing at `references/framing.md` and naming the go/clarify/kill verdict and the exchange-count restart; add one References line; stay ≤120 lines. (3) `references/readiness-assessment.md`: add a "## Framing trigger" paragraph (≤1 required dimension met, or uncertainty language → framing first) and, under "Lean vs Full Decision", the restart rule ("a go verdict restarts the exchange count"). (4) `specflow-start/SKILL.md` step 4: add the clause "fuzzy idea / not sure it's worth building → `/specflow-discover` (it frames first)". (5) docs/comparison.md "What SpecFlow expects you to bring": narrow to framing-yes / market-validation-no and keep the pointer to other tools for market validation only; README line 31 and docs/lifecycle.md's discover row gain "(frames a fuzzy idea first)". (6) Pin the central framing sentences and the discover description in `tests/test_core_skill_text.py` with `# DEC-104` provenance, in one edit, then `specflow verify IT-109` once. (7) One code change found in review: exempt DECs tagged `framing` from the `links/orphan` row in `artifact_lint.py` (REQ-069 OBL-7) with a positive and negative test; rule id unchanged. (8) `specflow generate-tests` for the V-model pair and `specflow verify` before anything moves to verified (parent runs the approval).

## Acceptance Criteria

1. Given specflow-discover/SKILL.md, when read, then the description claims fuzzy ideas, step 0 cites references/framing.md once, and `wc -l` ≤ 120.
2. Given framing.md, when the pin tests run, then the trigger, five-question cap, hard stop, verdict, restart and `guided_by` sentences are present.
3. Given specflow-start/SKILL.md, when read, then the fuzzy-idea route to /specflow-discover is present exactly once.
4. Given docs/comparison.md, README.md and docs/lifecycle.md, when grepped, then "SpecFlow does not have this" is gone from comparison.md and each file carries the narrowed positioning.
5. Given both skill trees, when `diff -rq` runs, then it prints nothing, and the full suite is green.
