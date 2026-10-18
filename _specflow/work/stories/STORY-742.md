---
id: STORY-742
title: 'Test-only: skill-catalog backstop pins (description shape, references and
  routes resolve)'
type: story
status: verified
tags:
- core
- skills
suspect: false
links:
- target: REQ-067
  role: implements
created: '2026-10-18'
fingerprint: sha256:2b06856e5fde
modified: '2026-10-18'
output_files:
- tests/test_reference_lint.py
- src/specflow/templates/skills/shared/specflow-execute/references/escalation-and-promotion.md
- .claude/skills/specflow-execute/references/escalation-and-promotion.md
- src/specflow/templates/skills/shared/specflow-references/references/adversarial-lenses.md
- .claude/skills/specflow-references/references/adversarial-lenses.md
thinking_techniques:
- worst_case_user
- composition
---

# Test-only: skill-catalog backstop pins (description shape, references and routes resolve)

## Summary

Test-only backstop for the skill-catalog rules (REQ-042 R2/R4 hole). Extend tests/test_reference_lint.py with: every shipped SKILL.md frontmatter `description` is a single line of at most 160 characters and contains no "NOT for" negation; every relative `references/...` or `../specflow-references/references/...` path cited in a shipped SKILL.md or reference file resolves to an existing file; every `/specflow-<name>` route named in a shipped SKILL.md resolves to a shipped skill directory (core or pack); and the total number of core skill descriptions is pinned at 13 so a 14th skill is a conscious change. Fix any violations the new tests surface (report them on this STORY).

## Acceptance Criteria

1. Given a shipped SKILL.md with a multi-line or over-length description, when the test runs, then it fails naming the skill.
2. Given a SKILL.md citing a references/ path that does not exist, when the test runs, then it fails naming the file and the path.
3. Given a SKILL.md naming `/specflow-nonexistent`, when the test runs, then it fails naming the route.
4. Given the current shipped tree, when the suite runs, then all new tests pass.
