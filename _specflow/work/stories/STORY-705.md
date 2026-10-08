---
id: STORY-705
title: Committed findings-baseline ratchet replaces run-count escalation
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
fingerprint: sha256:87df847d1ee6
modified: '2026-09-30'
output_files:
- src/specflow/core/findings_baseline.py
- src/specflow/commands/findings_baseline.py
- src/specflow/commands/brief.py
- src/specflow/templates/skills/shared/specflow-artifact-review/references/severity-levels.md
- tests/test_findings_baseline_cmd.py
- tests/test_findings_policy.py
- tests/test_single_index_writer.py
---

# Committed findings-baseline ratchet replaces run-count escalation

## Acceptance Criteria

1. On a full artifact-lint run an escalating warning whose (rule_id, subjects) key is absent from .specflow/findings-baseline.yaml exits 1; known keys, accounting findings and type-filtered runs never escalate; an absent baseline prints the ratchet-off hint on every full run and fails on blocking findings only.
2. Two consecutive lint runs on an unchanged repository print identical output and exit codes.
3. findings-baseline update seeds an absent baseline, drops resolved keys, refuses new keys unless accept-new is given (writes nothing, lists them, exit 1), prints every key added under accept-new, and is byte-idempotent; findings-baseline diff is read-only.
4. The only code path that writes the baseline is the findings-baseline command module, under the mutation lock; a writer-ban test enforces it; init writes an empty baseline through that routine.
5. refresh deletes .specflow/lint-warning-history.yaml and tells the user to run findings-baseline update once; brief nags when no baseline exists; severity-levels.md states the baseline semantics and prose-CLI guard tests pass.
