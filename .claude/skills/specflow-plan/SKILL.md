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
2. **Read context:** every approved REQ in full; `project.domain` and `project.domain_tags` from `.specflow/config.yaml`; the concept→artifact map in `../specflow-discover/references/domain-checklists/<domain>.md` when it has one (not every concept becomes a STORY — decompose into the artifact type the map names). Load the DECs the discover skill's challenge step created (`_specflow/work/decisions/`) — assumptions, risks, and drops inform the architecture. Best practices: `specflow practices seed --create` if none exist yet (drafts the user approves; guide: `../specflow-references/references/bp-authoring.md`); audit your draft against the approved ones before presenting. Reuse any `draft` STORY that already `implements` an in-scope REQ (the discover lean path creates one) — refine it rather than creating a duplicate.
3. **ARCH per component** — responsibility, public interface, dependencies, data flow — discussed with the user, then `specflow create --type architecture --title "<component>" ...` and hang it under the REQ: `specflow update <REQ-ID> --add-link <ARCH-ID>:refined_by` (the REQ holds the link — canonical; `ARCH derives_from REQ` is the legacy shape lint reports as accounting only). Add `--add-link <BP-ID>:guided_by` on the ARCH for each in-scope approved best practice that shapes the component.
4. **DDD only where needed:** decide with `references/ddd-selection.md` (6-question checklist); `--type detailed-design`, then `specflow update <ARCH-ID> --add-link <DDD-ID>:refined_by` (the ARCH holds the link, same direction as REQ → ARCH).
5. **STORYs:** decompose per `references/spidr-decomposition.md`, write per `references/story-writing.md` (vertical slices, ≥3 Given/When/Then acceptance criteria). Link every applicable role: `implements` → REQ, `guided_by` → ARCH, `specified_by` → DDD (`references/link-roles.md`), plus `guided_by` → each in-scope approved BP.
6. **Stress-test** the result with `references/thinking-techniques.md` (premortem, dependency shock, …) and record what you applied: `specflow update <ID> --thinking-techniques <...>`.
7. **Validate:** `specflow artifact-lint` and `specflow practices validate`.

## Approval gate (I1)

Present per `../specflow-references/references/approval-presentation.md` — TLDR, the proposed system behavior in plain terms, every ARCH/DDD/STORY inline, key decisions (fold in: every approved REQ covered by ≥1 STORY? any STORY that should be a SPIKE? any ARCH interface needing a DDD?), risk profile from `specflow risk-tier <IDs>`. **You must NOT self-approve** — artifacts stay `draft` until the user explicitly approves; only then `specflow update <ID> --status approved`. Iterate on requested changes and re-present.

**Exit message:** `specflow approve --type STORY` (and ARCH/DDD as needed), then `/specflow-execute`; record the phase with `specflow phase-set planning --reason "<why>"`.

## Delegating to subagents

When you fan work out to subagents, each brief carries: the skill to follow (name it — `/specflow-execute`, `/specflow-plan` — so the subagent reads that SKILL.md first), the current `specflow brief --next` output, and the exact STORY/REQ IDs in scope — never "the next story". Allocate IDs serially in the parent before fan-out (`specflow create ...` once per artifact, then pass the IDs); parallel creates race the index. Tell subagents to read skill references with a bounded read (`sed -n 1,80p <file>`, or the host's file-read tool with a line range), never `cat <file> | head` — a closed pipe aborts the command. Subagents report back the IDs they changed and the exact `specflow update ...` commands they ran; the parent runs `specflow artifact-lint` once after the wave.

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
