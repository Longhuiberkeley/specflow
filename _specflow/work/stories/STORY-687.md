---
id: STORY-687
title: 'Shipped checklists: story-writing rewrite, per-artifact scope, dead surfaces,
  corpus test'
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- checklists
suspect: false
links:
- target: REQ-056
  role: implements
created: '2026-09-30'
fingerprint: sha256:7b64ff801e55
modified: '2026-10-09'
output_files:
- src/specflow/lib/checklists.py
- src/specflow/lib/lint.py
- src/specflow/templates/checklists/in-process/story-writing.yaml
- src/specflow/templates/checklists/in-process/requirement-writing.yaml
- src/specflow/templates/checklists/domain/embedded.yaml
- src/specflow/templates/checklists/domain/cli-tool.yaml
- src/specflow/templates/checklists/phase-gates/executing-to-verifying.yaml
- src/specflow/templates/checklists/phase-gates/verifying-to-complete.yaml
- tests/test_checklist_corpus.py
- tests/test_checklist_run_integration.py
- src/specflow/lib/scaffold.py
- src/specflow/commands/refresh.py
- src/specflow/cli.py
- tests/test_refresh_checklists.py
- tests/test_init_checklist_categories.py
---

# Shipped checklists: story-writing rewrite, per-artifact scope, dead surfaces, corpus test

## Acceptance Criteria
1. story-writing.yaml parses and its spec-link check is a grep over frontmatter with no python3 or PyYAML dependency.
2. Per-artifact items that ran project-wide lint (requirement-writing, embedded) are agent-judged with an llm_prompt; the embedded item is warning severity.
3. readiness/ is deleted from templates and scaffold; unit, integration and qualification tests map to implementation-review; phase-gate items that only lint status legality are agent-judged; the duplicate sub-lint item is removed; the dead parallel runner in lint.py is deleted.
4. tests/test_checklist_corpus.py enforces parse, non-empty items, script presence, per-artifact argument reference and loader reachability for every shipped checklist.
