---
id: STORY-707
title: 'Wave P-1: artifact writers use the locked path; artifact-review stops rewriting
  and pre-stamping'
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-002
  role: implements
- target: REQ-060
  role: implements
created: '2026-10-08'
fingerprint: sha256:004719cc130a
modified: '2026-10-08'
output_files:
- src/specflow/commands/artifact_review.py
- src/specflow/commands/checklist_run.py
- src/specflow/lib/challenge.py
- src/specflow/lib/checklists.py
- src/specflow/lib/frontmatter_patch.py
- src/specflow/lib/orphans.py
- tests/formal/test_index_store_crash.py
- tests/test_artifact_review_cli.py
---

# Wave P-1: artifact writers use the locked path; artifact-review stops rewriting and pre-stamping

# Wave P-1

Findings F-019, F-131, F-132, F-137, F-138, F-139 of the 2026-10 audit (see the SPIKE).
## Acceptance Criteria

- [ ] AC1: Given checklist-run --all on an unchanged repo, when it finishes, then no artifact file outside the reviewed set changes a byte and both checklist/orphan writers go through write_artifact_text under the mutation lock.
- [ ] AC2: Given artifact-review --depth deep on one artifact, when prompts are printed, then thinking_techniques on the artifact is unchanged and no dead-code/similarity scan runs.
- [ ] AC3: Given checklist-run --proactive, when an item has an llm_prompt hint, then the hint line is printed under the item.
- [ ] AC4: Given a project outside this checkout, when artifact-review bootstraps the challenge schema, then it copies from the installed package path.
