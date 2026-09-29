---
id: STORY-690
title: 'Setup skills and docs: pack-author install message and schema docs, adapter
  cleanup, no uv run in docs'
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- skills
suspect: false
links:
- target: REQ-056
  role: implements
created: '2026-09-30'
fingerprint: sha256:a443102a0573
modified: '2026-09-30'
output_files:
- src/specflow/templates/skills/shared/specflow-pack-author/SKILL.md
- src/specflow/templates/skills/shared/specflow-pack-author/references/pack-structure.md
- src/specflow/templates/skills/shared/specflow-pack-author/references/schema-template.md
- src/specflow/templates/skills/shared/specflow-pack-author/references/large-documents.md
- src/specflow/templates/skills/shared/specflow-pack-author/references/example-packs.md
- src/specflow/templates/skills/shared/specflow-pack-author/scripts/validate-pack.sh
- src/specflow/templates/skills/shared/specflow-adapter/SKILL.md
- src/specflow/templates/skills/shared/specflow-adapter/references/adapter-framework.md
- src/specflow/templates/adapters.yaml
- docs/architecture.md
- docs/lifecycle.md
- docs/authoring-an-adapter.md
- docs/authoring-a-pack.md
- docs/commands.md
- docs/getting-started.md
- docs/skill-standards.md
- README.md
- tests/test_core_skill_text.py
- tests/test_prose_cli_surface.py
---

# Setup skills and docs: pack-author install message and schema docs, adapter cleanup, no uv run in docs

## Acceptance Criteria
1. The pack-author exit message describes the working install path; pack-structure.md and schema-template.md document adds_skills, context_snippet with its budget, category, allowed_review_status and clause category, with forward-worded transition comments and a pointer to specflow schema for the type list.
2. The adapter skill drops repository-only paths, the no-op status and standards sections and the custom-adapter lines, and states which generated jobs are advisory versus blocking.
3. docs/ no longer teaches uv run specflow outside decisions.md; CI examples bootstrap with uvx from git.
4. The prose-surface test passes over docs/.
