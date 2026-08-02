---
id: STORY-624
title: Orphan-code adoption + outcome feedback loop (upcoming wave)
type: story
status: draft
priority: medium
rationale: 'Planned follow-on to REQ-037/ARCH-026. Two coupled gaps surfaced by the
  v1.13 audit pass: (1) detect orphan-code still reports un-adopted source clusters
  that have no owning STORY/ARCH even after the accounting lenses landed, and (2)
  recorded verify_run evidence is written but not yet fed back into the execute/review
  outcome (a failed contract should inform the next wave''s prevention pattern, not
  just sit on disk). Both stay accounting-not-policing.'
tags:
- v1.13
- orphan-code
- adoption
- outcome-feedback
- upcoming
suspect: false
links:
- target: REQ-037
  role: implements
- target: ARCH-026
  role: derives_from
created: '2026-08-03'
fingerprint: sha256:0c60189f291d
---

# Orphan-code adoption + outcome feedback loop (upcoming wave)

Planned follow-on within the REQ-037 / ARCH-026 theme. Not yet started — this is
the next wave's scope, recorded now so the chain is complete and the work is
queueable.

## Scope (proposed)

1. **Orphan-code adoption closure.** `specflow detect orphan-code` still flags
   source clusters with no owning STORY/ARCH/DDD even after the v1.13 accounting
   pass. Provide a low-friction retro-link path (extend the existing
   `--retro-link` flow) so an un-adopted cluster can be adopted into an ARCH's
   `output_files` with a backfilled STORY in one step, tagged `backfilled`.
2. **Outcome feedback loop.** Recorded `verify_run_*` evidence (from
   `specflow verify`) is written but not yet consumed downstream. When a contract
   records a divergent exit code, offer to feed it into a PREV prevention pattern
   (the existing learnings surface) so a repeated failure mode informs the next
   wave — accounting, never blocking. No new artifact type (PREV already exists).

## Acceptance criteria (to be met when implemented)

- A one-step adopt-orphan path lands an un-adopted cluster under an ARCH with a
  backfilled STORY, and the orphan meter coverage % rises accordingly.
- A recorded divergent `verify_run_exit_code` can seed a PREV prevention pattern
  via the existing learnings path; the loop is opt-in and never blocks.
- `specflow artifact-lint --method programmatic` adds 0 blocking issues.
- No new artifact types, no new link roles (D-18 respected), zero external API
  calls.

## Out of scope

- Auto-capturing output_files from execute/done (deferred per the deferred
  output_files autocatch memory — this wave makes detection fire; auto-capture
  stays deferred to avoid noise).
- Blocking on orphan clusters or divergent contracts — accounting only.
