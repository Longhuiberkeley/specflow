---
id: STORY-703
title: artifact-lint is read-only with explicit environment inputs
type: story
status: verified
tags:
- v1.17.1
- engine
- p3
- lint
suspect: false
links:
- target: REQ-053
  role: implements
- target: DEC-099
  role: guided_by
created: '2026-09-30'
fingerprint: sha256:cba96df20853
modified: '2026-10-09'
output_files:
- src/specflow/lib/source_drift.py
- src/specflow/commands/fingerprint_refresh.py
- src/specflow/commands/artifact_lint.py
- tests/test_lint_readonly.py
---

# artifact-lint is read-only with explicit environment inputs

## Acceptance Criteria

1. A full artifact-lint run (without --fix) leaves every file under .specflow/ byte-identical, whether or not a source-drift store exists.
2. Source-drift seeding moves out of lint: init and refresh seed .specflow/source-fingerprints.yaml when absent, under the mutation lock, and specflow fingerprint-refresh --source re-accepts drift for named artifacts or all; lint reports unseeded artifacts as info.
3. artifact-lint --as-of YYYY-MM-DD (default today, UTC) drives spike staleness; spike staleness is accounting while zombie and repeated-topic findings stay escalating.
4. Full runs print an Inputs line recording the as-of date and the source-drift store state.
