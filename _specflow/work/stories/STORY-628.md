---
id: STORY-628
title: 'De-noise brief --next: rewind-evidence gate and auto-DEC filter'
type: story
status: verified
rationale: Kill two cry-wolf advisories; de-noise doctrine
suspect: false
links:
- target: UT-046
  role: verified_by
- target: REQ-035
  role: implements
created: '2026-08-04'
fingerprint: sha256:513b978adf4c
modified: '2026-09-13'
output_files:
- src/specflow/commands/brief.py
- tests/test_brief.py
---

# De-noise brief --next: rewind-evidence gate and auto-DEC filter

brief --next fires two false positives on healthy state: the "90 stories remain implemented after rewind" note (no rewind ever happened; template wording) and "47 unreviewed DEC(s)" inflated by ~49 auto-generated change-record DECs. Fix: gate the rewind note on recorded rewind: true entries in state history; filter change-record/auto-generated/project-audit tagged DECs out of the unreviewed count and blast-radius cone; de-pollute the Recent decisions section of auto change records. Follows the de-noise doctrine (dogfood retrospective A1-A5). See CHL-344 context.

## Acceptance Criteria

1. The rewind note in `brief --next` prints only when a recorded `rewind: true` entry exists in state history.
2. The unreviewed-DEC count excludes change-record / auto-generated / project-audit DECs.
3. The DEC blast-radius cone excludes auto change records the same way.
4. The Recent decisions section no longer lists auto change records.
5. tests/test_brief.py pins the gate and the filter.
