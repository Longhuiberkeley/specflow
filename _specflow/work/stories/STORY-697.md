---
id: STORY-697
title: cascade-status and merge write only legal statuses and fail loudly
type: story
status: verified
tags:
- v1.17.0
- engine
- p1c
- cascade
suspect: false
links:
- target: REQ-003
  role: implements
- target: REQ-053
  role: implements
- target: DEC-093
  role: guided_by
- target: DEF-011
  role: derives_from
- target: DEF-012
  role: derives_from
- target: DEF-018
  role: derives_from
- target: DEF-019
  role: derives_from
created: '2026-09-30'
fingerprint: sha256:43102866b8a5
modified: '2026-09-30'
output_files:
- src/specflow/commands/cascade_status.py
- src/specflow/commands/artifact_lint.py
- src/specflow/commands/reconcile.py
- src/specflow/lib/impact.py
- tests/test_cascade_status.py
- tests/test_cascade_legality_table.py
- tests/test_cascade_status_cli.py
- tests/test_cascade_support.py
- tests/test_cascade_reconcile.py
- tests/test_status_write_ban.py
- tests/test_merge_split_status.py
---

# cascade-status and merge write only legal statuses and fail loudly

## Acceptance Criteria

1. cascade-status proposes only transitions legal in the target schema, walking approved to implemented to verified when needed, or refuses with the reason.
2. cascade-status exits non-zero when any proposed transition fails, and reconcile, which runs the cascade, exits non-zero too.
3. cascade-status and the status-cascade lint share one decision of which links cascade (cascade_targets over CASCADE_ROLES), pinned by an exhaustive table test over the real schemas that also runs the lint and requires it to nudge exactly what the cascade moves.
4. A REQ is never promoted to verified while a sibling STORY implementing it is unverified.
5. merge and split write only legal statuses: the source ends superseded with a supersedes link from the target, or cancelled or deprecated (or unchanged) with no supersedes link; a grep test bans status writes outside update_artifact across src/specflow.
6. DEF-011 (cascade illegal transitions, planned label DEF-006), DEF-018 (reconcile exit 0 on a failed cascade) and DEF-019 (merge dangling supersedes link) are filed from failing tests and closed by this story. DEF-012 (merge wrote the non-schema merged_into status, planned label DEF-007) was fixed by the STORY-696 package; this story adds the repo-wide status-write ban that keeps it fixed.
