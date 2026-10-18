---
id: STORY-737
title: Evidence-labels reference, skill pointers, and sentence pins
type: story
status: verified
suspect: false
links:
- target: REQ-066
  role: implements
created: '2026-10-17'
fingerprint: sha256:19ac50f7b7b2
modified: '2026-10-17'
---

# Evidence-labels reference, skill pointers, and sentence pins

## Summary

Prose + pins change implementing the linked REQ: an evidence-label reply contract for lifecycle skills.

1. New shared reference `specflow-references/references/evidence-labels.md` (~40-60 lines): every claim carries its evidence or its label (measured / inferred / guess) in the same sentence; never fabricate — cite only artifact IDs, file:line, commands, and output produced or read this session (verify IDs with `specflow trace` / `specflow list` before citing); frame impact for the consumer and the maintainer before implementation detail; never hand the user a check you could run yourself.
2. One-line pointers from specflow-execute/SKILL.md and specflow-artifact-review/SKILL.md to the new reference (and specflow-ship/SKILL.md only if its <50-line pin survives; otherwise note why it was skipped).
3. Byte-identical mirror sync of the new reference and edited SKILL.md files into `.claude/skills/` so `diff -rq` comes back clean.
4. Phrase pins for the new normative sentences with DEC provenance comments in tests/test_core_skill_text.py.

## Acceptance Criteria

1. Given the new reference exists, when lifecycle skills compose replies, then claims are labeled measured/inferred/guess in the same sentence and cite only session-verified IDs.
2. Given the skill files gain pointers, when tests/test_reference_lint.py and tests/test_core_skill_text.py run, then line budgets (120 core / 300 pack, <50-line ship pin) hold and the new phrases are pinned.
3. Given both skill trees after the change, when `diff -rq .claude/skills src/specflow/templates/skills/shared` runs, then there is no output.
