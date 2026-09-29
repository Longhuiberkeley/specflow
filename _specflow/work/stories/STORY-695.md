---
id: STORY-695
title: TLDR pack rewrite, iso26262-demo relabel, per-pack healthy-fixture tests
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- packs
suspect: false
links:
- target: REQ-056
  role: implements
created: '2026-09-30'
fingerprint: sha256:9dcc3833db5f
modified: '2026-09-30'
output_files:
- src/specflow/packs/tldr-communication/pack.yaml
- src/specflow/packs/tldr-communication/README.md
- src/specflow/packs/iso26262-demo/pack.yaml
- src/specflow/packs/iso26262-demo/README.md
- src/specflow/packs/iso26262-demo/standards/iso26262-demo.yaml
- tests/test_tldr_pack.py
- tests/test_iso26262_demo_pack.py
- tests/test_pack_healthy_fixtures.py
- src/specflow/commands/artifact_lint.py
- tests/test_spidr_coverage.py
- src/specflow/templates/skills/shared/specflow-init/SKILL.md
- tests/test_core_skill_text.py
---

# TLDR pack rewrite, iso26262-demo relabel, per-pack healthy-fixture tests

## Acceptance Criteria
1. The tldr-communication snippet carries only the delta to the base block (compaction recap plus one plain-language gloss clause); its description, README line and init menu line match; the pack test requires eli5 in the body.
2. iso26262-demo is removed from the init preset menu and --preset help, its duplicate hazard schema is deleted, and its clauses are renamed DEMO-1 to DEMO-5.
3. Healthy-fixture tests drive the documented adoption, ops, autoresearch and core lifecycle sequences through the CLI and assert zero warnings from artifact-lint, brief --next and autoresearch status.
4. The aggregate always-on budget test passes with the rewritten snippet.
