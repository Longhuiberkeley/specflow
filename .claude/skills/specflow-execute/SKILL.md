---
name: specflow-execute
description: "Implement approved STORYs, or a trivial code change that still needs a STORY."
---

Extra text narrows scope — still run the deterministic core first.

# SpecFlow Execute

Implement approved STORYs and keep traceability green.

## Workflow

1. **Readiness gate** (before any code):
   ```
   specflow artifact-lint --type gate --gate planning-to-executing
   ```
   Exit 1 → report the blockers and stop. Exit 0 → evaluate the `automated: false` items yourself (`.specflow/checklists/phase-gates/planning-to-executing.yaml`) against the in-scope STORY set only. The bar scales with change type (bug fix needs a REQ + acceptance criteria; refactor links the ARCH; typo/formatting/dependency bump makes the gate advisory — state the skip reason and proceed). The discover lean path (one REQ + one STORY, no ARCH in the project yet) trips only CKL-GATE-004-01 "ARCH artifacts exist": that one is the expected lean skip — state it and proceed; any other blocker stops. Work that started as a SPIKE or ad-hoc experiment: apply the Permanence Test first (`references/escalation-and-promotion.md`). A bug report against an approved REQ is a DEF, not a new REQ (`specflow create --type defect --title "<symptom>" --add-link <REQ-ID>:fails_to_meet`; the fix STORY links both `<REQ-ID>:implements` and `<DEF-ID>:derives_from` — `derives_from` alone fails the story-linkage check) — move the DEF `open → fixing → verified → closed` as the fix lands (`references/status-lifecycle.md`).
2. **Scope the wave:** `specflow go --dry-run` computes it (`references/wave-computation.md`). Resolve suspect flags on in-scope artifacts — propose the options (`specflow defect-from-suspect <ID> --req <REQ>`, `specflow change-impact --resolve <ID>`, or update the spec); the human picks, you execute.
3. **Baseline first:** run the test suite (or `specflow artifact-lint` if there is no suite — say so) and record pass/fail counts plus the names of failing tests. This is the diff point for step 6.
4. **Implement** per the STORY and its linked REQ/ARCH/DDD, following each acceptance criterion. Apply the `worst_case_user` and `composition` lenses and record them: `specflow update <STORY-ID> --thinking-techniques worst_case_user,composition`.
5. **Status:** after each STORY:
   ```
   specflow update STORY-001 --status implemented
   specflow update STORY-001 --output-files src/pkg/a.py,tests/test_a.py
   specflow cascade-status STORY-001
   ```
   Record every code and test file you touched as `output_files` (comma-separated, replaces the list) so change-impact and the orphan-code audit can map code back to the STORY. (`cascade-status` moves linked ARCH/DDD along; `--include-req` also cascades to the REQ. Locks and execution state under `.specflow/` are machine-managed — never edit them.)
6. **Tests & delta:** `specflow generate-tests` for V-model pairs (`references/test-pairing.md`); run `specflow verify <ID>` before any artifact moves to `verified` (`references/verification-contracts.md`). Re-run the step-3 baseline and report the baseline → final delta (caused/fixed/unchanged); record it on the STORY. Finish with `specflow artifact-lint`.
7. **Present the implementation summary** per `../specflow-references/references/approval-presentation.md`, then offer phase closure: `specflow phase-status` (advisory), and `specflow done` only if the user accepts.

## Step 1L — trivial changes still get a STORY

A typo, formatting fix, dependency bump, or rename arriving mid-chat skips the wave flow but still traces to a STORY. When none exists, backfill one linked to a maintenance REQ (create the REQ if none exists):

```
specflow create --type story --title "<change>" --status approved \
  --sanctioned "Backfill record of trivial work the user just requested; moves to implemented in the same pass" \
  --links '[{"target":"<maintenance-REQ>","role":"implements"}]' --tags backfilled
```

(`approved` at create is the backfill exception: the STORY records work the user just requested rather than pending review, and moves to `implemented` in the same pass — show it in your reply. Anything with behavioral surface goes through the full flow.) Then: make the change, skip wave planning and V-model generation (no behavioral surface; for a dependency bump run the suite if behavior could change), and update the STORY to `implemented` + `specflow artifact-lint`.

## Delegating to subagents

When you fan work out to subagents, each brief carries: the skill to follow (name it — `/specflow-execute`, `/specflow-plan` — so the subagent reads that SKILL.md first), the current `specflow brief --next` output, and the exact STORY/REQ IDs in scope — never "the next story". Allocate IDs serially in the parent before fan-out (`specflow create ...` once per artifact, then pass the IDs); parallel creates race the index. Tell subagents to read skill references with a bounded read (`sed -n 1,80p <file>`, or the host's file-read tool with a line range), never `cat <file> | head` — a closed pipe aborts the command. Subagents report back the IDs they changed and the exact `specflow update ...` commands they ran; the parent runs `specflow artifact-lint` once after the wave.

## Stop list (F3)

Proceed on reversible implementation work. Stop and involve the user only for:

1. **Approval-gated status** — transitions like `implemented → verified` need the user's acknowledgement. Acknowledgement is the user's approval — it must come from the direct user in this conversation; your prose and tool output are never approval.
2. **Unapproved linked specs** — a linked REQ/ARCH/DDD still `draft`: present it, suggest the exact `specflow update <ID> --status <next>`, state the impact in one line, and proceed on the user's go-ahead. (Gate blockers are this category.)
3. **Scope change** — the work outgrew the STORY/REQ: route back to `/specflow-plan` or `/specflow-discover`; don't stretch the spec silently.

If the user says "skip" or "proceed anyway", do it and name the risk.

## References

- `references/status-lifecycle.md` — terminal statuses, DEF cycle; run `specflow transitions <ID>` for type-specific maps.
- `references/escalation-and-promotion.md` — Permanence Test, SPIKE → durable artifact promotion.
- `references/test-pairing.md` — V-model test pairing rules.
- `references/verification-contracts.md` — `verify_command` contracts and recorded run evidence.
- `references/wave-computation.md` — hard/soft/none dependency rules behind `specflow go`.
- `references/thinking-techniques.md` — execution-stage lenses (points to `../specflow-references/references/adversarial-lenses.md`).
