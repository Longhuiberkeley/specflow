---
id: SPIKE-002
title: "2026-09 frontier-model context audit \u2014 handoff"
type: spike
status: draft
rationale: Durable record of the two ultracode context audits (specflow + opencode-ultracode)
  so the remaining STORY 3-9 work and the plugin rewrite can resume in a fresh session.
tags:
- context-audit
- handoff
suspect: false
links: []
created: '2026-09-13'
fingerprint: sha256:0ec50ff5c587
modified: '2026-09-13'
---

# 2026-09 frontier-model context audit — handoff

Two ultracode audits (2026-09-13, runs `run_lsrfgboue3jw` specflow / `run_30rsl5rkgun4` plugin,
previews in `.opencode/workflows/runs/`; full results retrievable via `/ultracode result` in the
original session) compared SpecFlow's shipped model-facing context against GPT-6 Astra and Claude
Fable 5.1 prompting guidance. Stance: aggressive — smarter models need less instruction.

Rubric (reuse for consistency): O0 earned-lines · O1 narrow one-line triggers, no NOT-for walls ·
O2 minimal router + references · O3 no recipe itineraries · O4 contextual pointers · O5 no forced
re-verification · O6 permission over prohibition · O7 defined completion · O8 multi-model audience ·
O9 prune rot · F1 don't ban narration · F2 conditional formatting · F3 don't block on requested work ·
F4 scoped changes · F5 targeted edits · F6 compaction-resistant digests.
Invariants: I1 seek-and-proceed consent · I2 never hand-edit .specflow/ · I3 enforcement in CLI, not prompts.

## Done (don't redo)

- STORY-656: agent-context.md (26→12 content lines), 4 pack snippets (routing + STORY-reservation
  only), guardrail test re-anchored. Commit 39ab7de.
- STORY-657: 15 skill descriptions → one-line narrow triggers.
- DEC-082 approved: docs/ is derived rendering only; knowledge lives in artifacts.
- Plugin repo (opencode-ultracode): ctrl+G pin-drop TUI fix, commit afe1101, 640/640 tests.

## STORY 3 — collapse lifecycle skill bodies into lean routers

Per skill, keep/cut (from audit findings):
- specflow-discover (326 lines): keep lean-vs-full decision + I1 gate + create/phase-set pointers;
  cut weighted table, six scripted questions + never-batch, domain/BP cookbook.
- specflow-init: delete copy-pasted Freeform block (also on adapter/pack-author/lifecycle — one
  shared line "extra text narrows scope" replaces it).
- specflow-execute: F3 revision — proceed on reversible impl; stop only for approval-gated status,
  unapproved linked specs, scope change. Keep: gate command, trivial-change-still-gets-STORY (Step 1L),
  STORY→implemented + cascade-status, baseline-then-delta. Blocking "does this look correct" confirm goes.
- specflow-plan/start/doc/review-triad: same router treatment; doc skill premise shifts per DEC-082.
- specflow-pack-author/scripts/validate-pack.sh uses `uv run python3` — broken in consuming
  projects; stdlib-only python3 or defer to `specflow pack-validate` (STORY 8).

## STORY 4 — trim on-demand references

- normative-language.md (175): keep RFC 2119 + ambiguity list + one-shall; cut EARS tutorial/essays.
- story-writing.md (130): keep ≥3 GWT AC, vertical slice, title formula; cut CLI-written YAML.
- spidr-decomposition.md (106): collapse to 5-row checklist.
- level-boundaries.md (plan copy, 71): byte-identical duplicate — delete, one shared pointer.
- wave-computation.md: keep 3-row hard/soft/none dependency table; cut Kahn re-teach.
- status-lifecycle.md (execute): keep terminal statuses + DEF cycle + `transitions <ID>`; cut the
  universal draft→approved→implemented map (contradicts type-specific maps).
- team-setup.md (adapter): keep enforcement-layers table + troubleshooting.
- checklist-assembly.md (artifact-review): delete assembly algorithm — `checklist-run` owns it.
- severity-levels.md: keep 3 severity definitions + user override; delete report-template duplicate.

## STORY 5 — brief.py consent + digest fixes

- `--next` core + IDs hoisted to top of output (currently buried under inventory).
- Digest must list exact draft IDs + one-line impact for `approve --type` (currently count-only →
  cannot serve as I1 consent vehicle). `approve --type REQ` stays a valid consent vehicle only
  after IDs shown; never auto `--yes`.
- Surface DEC id/title/review_status/constraint.
- Conditional chrome: print suspects/stale/drill-down only when non-empty; cut V-model re-teach,
  point at `/specflow-artifact-review` / `change-impact` / `defect-from-suspect <ID>`.

## STORY 6 — handbook.py

- Delete GENERIC_PRACTICES sermon bodies (always appended today).
- Default stdout: domain, count, title+tag index only; full bodies on `--verbose`/`--create`.

## STORY 7 — hook.py

- Link/schema failures: name `specflow artifact-lint --type links|schema` and stop (today's text
  teaches `--no-verify` while comments forbid teaching it).
- RBAC failure: "local hook blocked this transition; durable enforcement is hosting-side" (do not
  call it advisory). Suspect warning stays as-is (already conditional + ID-exact).

## STORY 8 — CLI backstops (gates STORY 9; unblocks HIGH-risk cuts)

- artifact-lint: warnings persisting ≥3 validation runs escalate to blocking (or delete the claim
  in severity-levels — never leave prompt-only false security).
- `specflow pack-validate` command (never `uv run` in shipped skill scripts).
- `specflow autoresearch status` fail/warn codes: Phase 0 git checks (rev-parse, dirty tree,
  index.lock, detached HEAD, COMP exists, LOOP draft), discard streak, category-run length,
  missing research_agenda, diversity/stuck. Prompt rule becomes: if status fails, stop.

## STORY 9 — autoresearch invariant sheets + skill-standards (gated on 8)

- autonomous-loop-protocol.md (1143 lines) → invariant sheet: budget, one LOOP/COMP, one atomic
  EXPT, commit-before-verify, no `git add -A`, persist condensation_brief (F6), stop on
  goals-met/budget.
- competition-setup-protocol.md (602): keep stdout-is-one-number, dry-run-before-first-LOOP,
  freeze exam fields, eval-data off-limits, human gate on COMP completed (I1).
- finding-generation-protocol.md: keep create-vs-update/supersede/falsify map; FIND draft→confirmed
  is an I1 user gate; CLI `suggest-finds` exists.
- crash-recovery, explore-exploit, domain-research, methodology-handbook, protocol-integrations:
  dedupe to invariants + consult-when pointers (details in original report).
- docs/skill-standards.md → DEC/ARCH per DEC-082 (minimal router, O1 triggers, O4 pointers,
  `specflow <cmd>` never `uv run`); human page at most derived rendering.

## Plugin repo (opencode-ultracode) — NOT started

Audit: hot path ~9,080 tok → ~1,220 (−87%); run tool description ~1,114 → ~270; skill 361 lines →
65-line router + references/. Implementation order (strict):
1. Runtime guards first: compile-error on fanout missing `max`; warn on schema-less
   merge/gate/branch outputs; warn on parallel write agents; wall-clock estimate warn; refuse
   inline script digest-matching an untrusted saved workflow.
2. Always-on strings: src/command.ts TOOL_DESCRIPTION + BACKGROUND_RUN_HINT + resultHint;
   src/index.ts tool/field descriptions (keep: identity, CALL DIRECTLY, WHEN, trust/no-inline U1,
   kinds + max-on-fanout, global names, caps 8/200/60m/512KB/64KB, background-default, settle →
   poll status, omit-runID-iff-one). src/catalog.ts hint.
3. Skill split: write references/{graph-authoring,named-workflows,script-patterns,sizing,
   running-and-steering}.md from current skill slices; replace skills/ultracode.md with the
   65-line router; update src/skill-content.ts; new SKILL_DESCRIPTION (no NOT-for wall).
4. Slash help inspect-only; docs/AUTHORING.md → short index.
5. Samples/templates: trim catalog blurbs; keep grep/ranged/no-echo read-discipline in template
   child prompts (only read-discipline backstop), cut numbers + skeptic pedagogy.
6. E2E: catalog → graph-before-trust → refuse-untrusted-run → trust → run → settle/poll/page →
   steer/control → guard assertions. Fail if always-on descriptions > ~600 tok or skill root > ~900.
Working drafts for all of the above are in the original session's run record.

## Cross-cutting (not started)

- Live eval (~30 min): fresh consuming project with the new context — vague prompt → routing;
  "implement this" → execute without blocking confirm; approval gate → present/suggest/impact/proceed;
  brownfield → adopt + no STORY backfill.
- Release when ready: CHANGELOG entry, version bump (pyproject + __init__), pytest, self-audit,
  commit, tag, push --follow-tags, GitHub release.

## Sequencing (user-directed, 2026-09-13)

Upgrade thoroughly first: STORY-658..664 in order (663 CLI backstops gates 664), then ONE live eval of the finished context in a fresh consuming session, then release. No intermediate evals, no release before the eval.
