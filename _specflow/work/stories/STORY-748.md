---
id: STORY-748
title: 'W-3 engine: deterministic ci generate job order + ci-gate default, brief complete-phase
  routing, open status categories, hook staged-rename RBAC, role-matrix DDD guided_by,
  severity rank, help texts'
type: story
status: verified
tags:
- consistency
- v1.17.7
suspect: false
links:
- target: REQ-070
  role: implements
- target: SPIKE-008
  role: derives_from
- target: DEF-021
  role: derives_from
- target: DEF-022
  role: derives_from
- target: DEF-023
  role: derives_from
created: '2026-10-18'
fingerprint: sha256:255beba861ab
modified: '2026-10-18'
output_files:
- src/specflow/cli.py
- src/specflow/commands/brief.py
- src/specflow/commands/hook.py
- src/specflow/commands/patterns.py
- src/specflow/commands/project_audit.py
- src/specflow/commands/status.py
- src/specflow/lib/adapters/github_actions.py
- src/specflow/lib/rbac.py
- src/specflow/lib/role_targets.py
- src/specflow/templates/adapters.yaml
- tests/test_engine_consistency_story748.py
- tests/test_status_categories.py
---

# W-3 engine: deterministic ci generate job order + ci-gate default, brief complete-phase routing, open status categories, hook staged-rename RBAC, role-matrix DDD guided_by, severity rank, help texts

## Scope
`lib/adapters/github_actions.py` (ordered ops), `templates/adapters.yaml` (+ci-gate), `commands/brief.py` (:864 split; :23 open categories), `commands/status.py` (open categories), `lib/rbac.py` staged_artifact_changes (name-status -M AMR), `commands/patterns.py:30`, `lib/role_targets.py:77`, `commands/project_audit.py` _severity_rank, orphan-code/export help text; `_CACHE_GENERATION` 9 if audit output changes. Resolves DEF-021 and DEF-022 (and DEF-023 once linked).

## Acceptance criteria
- AC1: Given the same ci config, when `ci generate --dry-run` runs under PYTHONHASHSEED=1 and =2, then the output is byte-identical and the job names are unchanged; a fresh `init` + `ci generate` contains the `specflow-ci-gate` job.
- AC2: Given phase `complete`, when `brief --next` runs, then the first line names /specflow-discover; in `verifying` it still names /specflow-ship.
- AC3: Given a project with one RUN artifact (category ops), when `specflow status` runs, then an Ops: row appears after the four core rows; without extra categories the output is unchanged.
- AC4: Given a staged `git mv` of an artifact whose status also changes and team roles configured, when the hook's RBAC check runs, then the transition is evaluated (author checked) instead of skipped.
- AC5: Given the role-target matrix, when compared with every schema's allowed_link_roles, then every matrix (type, role) pair is allowed by that schema (test added).
- AC6: Given `uv run pytest tests/`, when run, then it is green with new tests for each change.
