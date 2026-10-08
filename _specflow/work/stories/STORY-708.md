---
id: STORY-708
title: 'Wave P-2: pre-commit hook PATH guard, worktree hooks dir, staged deletions,
  foreign-hook safety; CI and adapter skill truth'
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-057
  role: implements
- target: REQ-061
  role: implements
created: '2026-10-08'
fingerprint: sha256:88490474d57d
modified: '2026-10-08'
output_files:
- .claude/skills/specflow-adapter/SKILL.md
- .claude/skills/specflow-adapter/references/team-setup.md
- .github/workflows/specflow.yml
- docs/commands.md
- docs/team-setup.md
- src/specflow/commands/ci.py
- src/specflow/commands/hook.py
- src/specflow/commands/init.py
- src/specflow/lib/adapters/github_actions.py
- src/specflow/lib/git_utils.py
- src/specflow/lib/rbac.py
- src/specflow/templates/skills/shared/specflow-adapter/SKILL.md
- src/specflow/templates/skills/shared/specflow-adapter/references/team-setup.md
- tests/test_ci_generation.py
- tests/test_hook.py
---

# Wave P-2: pre-commit hook PATH guard, worktree hooks dir, staged deletions, foreign-hook safety; CI and adapter skill truth

# Wave P-2

Findings F-120, F-121, F-122, F-124, F-129, F-085, F-044, F-045, F-048, F-058 (CI step), F-062 (adapter half).
## Acceptance Criteria

- [ ] AC1: Given specflow is not on PATH, when the installed pre-commit hook runs, then it prints an install hint and exits non-zero instead of exit 127 before Python.
- [ ] AC2: Given a linked git worktree, when init or hook install runs, then the hook lands in the directory git rev-parse --git-path hooks reports.
- [ ] AC3: Given the only staged change is an artifact deletion, when the hook runs, then links and schema lint still run.
- [ ] AC4: Given a foreign pre-commit hook exists, when hook install runs without --force, then it refuses with the exact --force hint and never overwrites.
- [ ] AC5: Given the adapter skill text, when read by an agent, then it says the hook blocks on RBAC/links/schema and that init writes CODEOWNERS only when absent.
