---
id: STORY-688
title: 'Guard tests: prose-to-CLI surface, reference lint, aggregate always-on budget'
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- guards
suspect: false
links:
- target: REQ-056
  role: implements
created: '2026-09-30'
fingerprint: sha256:d118b999d3cc
modified: '2026-09-30'
output_files:
- tests/test_prose_cli_surface.py
- tests/test_reference_lint.py
- tests/test_context_budget.py
- tests/test_v124_ergonomics.py
- docs/cli-reference.md
- docs/lifecycle.md
- src/specflow/templates/skills/shared/specflow-change-impact-review/SKILL.md
- src/specflow/templates/skills/shared/specflow-doc/references/citation-syntax.md
---

# Guard tests: prose-to-CLI surface, reference lint, aggregate always-on budget

## Acceptance Criteria
1. tests/test_prose_cli_surface.py extracts every specflow invocation from shipped templates, packs and docs and parses it with the real parser, failing on argparse errors, deprecated aliases, uv-run outside the allowlist, non-entry create statuses without --sanctioned, and missing required fields.
2. A reference-lint test forbids repository-internal path literals and legacy D-numbered ids in shipped templates and packs.
3. One aggregate test bounds agent-context.md plus every pack context_snippet to 375 words and rejects sentence overlap, replacing the 40-line cap.
4. All three tests pass on the fixed corpus and each has a negative fixture proving it fails on a seeded violation.
