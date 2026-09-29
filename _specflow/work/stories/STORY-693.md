---
id: STORY-693
title: 'Autoresearch pack text matches the CLI: commands, flags, noise shape, plan
  and frontier'
type: story
status: verified
tags:
- v1.17.0
- sweep
- p1b
- autoresearch
suspect: false
links:
- target: REQ-056
  role: implements
created: '2026-09-30'
fingerprint: sha256:efaa3993b44e
modified: '2026-09-30'
output_files:
- src/specflow/packs/autoresearch/README.md
- src/specflow/packs/autoresearch/schemas/competition.yaml
- src/specflow/packs/autoresearch/schemas/experiment.yaml
- src/specflow/packs/autoresearch/schemas/loop.yaml
- src/specflow/packs/autoresearch/skills/specflow-autoresearch/SKILL.md
- src/specflow/packs/autoresearch/skills/specflow-autoresearch/references/
- tests/test_autoresearch_skill_text.py
- tests/test_autoresearch_pack.py
---

# Autoresearch pack text matches the CLI: commands, flags, noise shape, plan and frontier

## Acceptance Criteria
1. No shipped autoresearch text names a command or flag that argparse rejects; landscape-resurvey uses specflow list, the log example carries its required flags, --no-profile is gone, and the all-commands-accept-competition claim is corrected.
2. frontier accepts --competition as an alias of --comp.
3. competition.yaml documents the noise_characterization shape once (samples, strategy, optional jump and guard parameters) and the protocol tells the agent to record three verify samples via update --set.
4. Step 3 leads with autoresearch plan; a frontier row is added; the backend-less delegate-review row is removed; the review-pass rule appears once; stale step annotations and repository-internal ids are removed.
