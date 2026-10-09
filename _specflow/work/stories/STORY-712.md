---
id: STORY-712
title: 'Wave P-6: docs, README, ROADMAP, CHANGELOG, AGENTS.md and pack-reference consistency
  with guard tests'
type: story
status: verified
tags:
- v1.17.2
suspect: false
links:
- target: REQ-021
  role: implements
- target: REQ-046
  role: implements
created: '2026-10-08'
fingerprint: sha256:6f6c17dd3eef
modified: '2026-10-09'
output_files:
- .claude/skills/specflow-adapter/SKILL.md
- .claude/skills/specflow-artifact-review/SKILL.md
- .claude/skills/specflow-artifact-review/references/challenge-engine.md
- .claude/skills/specflow-artifact-review/references/checklist-assembly.md
- .claude/skills/specflow-discover/references/thinking-techniques.md
- .claude/skills/specflow-execute/references/thinking-techniques.md
- .claude/skills/specflow-pack-author/SKILL.md
- .claude/skills/specflow-pack-author/references/example-packs.md
- .claude/skills/specflow-pack-author/references/large-documents.md
- .claude/skills/specflow-pack-author/references/pack-structure.md
- .claude/skills/specflow-plan/references/thinking-techniques.md
- .claude/skills/specflow-references/references/adversarial-lenses.md
- .github/workflows/specflow.yml
- AGENTS.md
- CHANGELOG.md
- README.md
- ROADMAP.md
- docs/cli-reference.md
- docs/commands.md
- docs/decisions.md
- docs/lifecycle.md
- docs/skill-standards.md
- src/specflow/commands/autoresearch.py
- src/specflow/commands/change_impact.py
- src/specflow/lib/git_utils.py
- src/specflow/lib/learning.py
- src/specflow/lib/scaffold.py
- src/specflow/packs/adoption/README.md
- src/specflow/packs/adoption/skills/specflow-adopt/SKILL.md
- src/specflow/packs/adoption/skills/specflow-adopt/references/as-built-baseline-protocol.md
- src/specflow/packs/adoption/skills/specflow-adopt/references/conflict-resolution-protocol.md
- src/specflow/packs/autoresearch/schemas/competition.yaml
- src/specflow/packs/autoresearch/skills/specflow-autoresearch/SKILL.md
- src/specflow/templates/skills/shared/specflow-adapter/SKILL.md
- src/specflow/templates/skills/shared/specflow-artifact-review/SKILL.md
- src/specflow/templates/skills/shared/specflow-artifact-review/references/challenge-engine.md
- src/specflow/templates/skills/shared/specflow-artifact-review/references/checklist-assembly.md
- src/specflow/templates/skills/shared/specflow-discover/references/thinking-techniques.md
- src/specflow/templates/skills/shared/specflow-execute/references/thinking-techniques.md
- src/specflow/templates/skills/shared/specflow-pack-author/SKILL.md
- src/specflow/templates/skills/shared/specflow-pack-author/references/example-packs.md
- src/specflow/templates/skills/shared/specflow-pack-author/references/large-documents.md
- src/specflow/templates/skills/shared/specflow-pack-author/references/pack-structure.md
- src/specflow/templates/skills/shared/specflow-plan/references/thinking-techniques.md
- src/specflow/templates/skills/shared/specflow-references/references/adversarial-lenses.md
- tests/test_adoption_pack.py
- tests/test_autoresearch_cli.py
- tests/test_autoresearch_pack.py
- tests/test_checklist_corpus.py
- tests/test_cli_reference_coverage.py
- tests/test_git_commit_timestamp.py
- tests/test_iso26262_demo_pack.py
- tests/test_learning_lenses.py
- tests/test_readme_pin.py
- tests/test_scaffold_scratch_gitignore.py
- tests/test_review_skill_doc_parity.py
---

# Wave P-6: docs, README, ROADMAP, CHANGELOG, AGENTS.md and pack-reference consistency with guard tests

# Wave P-6

Findings F-049, F-093, F-106, F-108, F-133, F-134, F-128, F-136, F-144, F-145, F-107, F-111, F-112, F-089, F-090, F-011, F-050, F-051, F-052, F-053, F-087, F-094, F-095, F-086, F-065, F-028, F-078, release-step additions.
## Acceptance Criteria

- [ ] AC1: Given docs/cli-reference.md, when compared against argparse, then every subcommand has a heading, pinned by a test.
- [ ] AC2: Given README.md, when compared against specflow.__version__, then the git+ pin matches, pinned by a test.
- [ ] AC3: Given AGENTS.md, when read, then step 10 says do not publish to PyPI, the CHANGELOG template says DEC-NNN and the SKILL budget line matches DEC-083.
- [ ] AC4: Given the pack-author references, when read, then the iso26262-demo section matches the real pack tree.
- [ ] AC5: Given autoresearch, when plan --inherit on a plateaued LOOP and status with no COMP, then inherit succeeds and status exits 0 with a neutral line.
