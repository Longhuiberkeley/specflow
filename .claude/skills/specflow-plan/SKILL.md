---
name: specflow-plan
description: "Decompose approved REQs into ARCH/DDD/STORY, or revisit architecture after execute."
---

Extra text narrows scope — still run the deterministic core first.

# SpecFlow Plan

Decompose approved REQs into ARCH/DDD/STORY.

## Workflow

1. **Orient & gate:** `specflow brief`; read the approved REQs — if any are still `draft`, name them and stop here. Rewind handling: revising ARCH/DDDs in place or re-decomposing → `specflow phase-set planning --reason "<why>"`; back to requirements → route to `/specflow-discover`. Then run the deterministic gate:
   ```
   specflow artifact-lint --type gate --gate specifying-to-planning
   ```
   Exit 1 → report blockers and stop.
2. **Read context:** every approved REQ in full; `project.domain` and `project.domain_tags` from `.specflow/config.yaml`; the concept→artifact map in `../specflow-discover/references/domain-checklists/<domain>.md` when it has one (not every concept becomes a STORY — decompose into the artifact type the map names). Load the DECs the discover skill's challenge step created (`_specflow/work/decisions/`) — assumptions, risks, and drops inform the architecture. Best practices: `specflow handbook generate --create` if none exist yet; audit your draft against them before presenting.
3. **ARCH per component** — responsibility, public interface, dependencies, data flow — discussed with the user, then `specflow create --type architecture --links '[{"target":"<REQ-ID>","role":"derives_from"}]' ...`.
4. **DDD only where needed:** decide with `references/ddd-selection.md` (6-question checklist); `--type detailed-design`, linked `refined_by` its ARCH.
5. **STORYs:** decompose per `references/spidr-decomposition.md`, write per `references/story-writing.md` (vertical slices, ≥3 Given/When/Then acceptance criteria). Link every applicable role: `implements` → REQ, `guided_by` → ARCH, `specified_by` → DDD (`references/link-roles.md`).
6. **Stress-test** the result with `references/thinking-techniques.md` (premortem, dependency shock, …) and record what you applied: `specflow update <ID> --thinking-techniques <...>`.
7. **Validate:** `specflow artifact-lint`.

## Approval gate (I1)

Present per `../specflow-references/references/approval-presentation.md` — TLDR, the proposed system behavior in plain terms, every ARCH/DDD/STORY inline, key decisions (fold in: every approved REQ covered by ≥1 STORY? any STORY that should be a SPIKE? any ARCH interface needing a DDD?), risk profile from `specflow risk-tier <IDs>`. **You must NOT self-approve** — artifacts stay `draft` until the user explicitly approves; only then `specflow update <ID> --status approved`. Iterate on requested changes and re-present.

**Exit message:** `specflow approve --type STORY` (and ARCH/DDD as needed), then `/specflow-execute`; record the phase with `specflow phase-set planning --reason "<why>"`.

## Rules

- Gate severity: `blocking` → stop and report · `warning` → present, don't proceed silently · `info` → note and proceed. If the user says "skip" or "proceed anyway", do it and name the risk.
- ARCH answers how the system is structured; DDD how a part works internally; STORYs reference specs, never replace them. Boundaries: `../specflow-discover/references/level-boundaries.md`.

## References

- `references/spidr-decomposition.md` — SPIDR story decomposition checklist.
- `references/story-writing.md` — story template, title formula, ≥3 GWT acceptance criteria.
- `references/ddd-selection.md` — which ARCH components need a DDD.
- `references/link-roles.md` — complete link role vocabulary.
- `references/thinking-techniques.md` — planning-stage techniques (points to `../specflow-references/references/adversarial-lenses.md`).
- `../specflow-discover/references/level-boundaries.md` — REQ vs ARCH vs DDD boundary rules (shared copy).
