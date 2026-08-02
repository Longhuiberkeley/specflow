---
id: STORY-069
title: Author 4 schema YAMLs for COMP / LOOP / EXPT / FIND
type: story
status: implemented
priority: high
tags:
- autoresearch
- wave-2
- schemas
suspect: false
links:
- target: REQ-029
  role: implements
- target: REQ-030
  role: implements
- target: DDD-022
  role: specified_by
created: '2026-05-15'
fingerprint: sha256:c1629f868976
---

# Author 4 schema YAMLs for COMP / LOOP / EXPT / FIND

## Outcome

Four schema files exist at `src/specflow/packs/autoresearch/schemas/`, ready to be copied by `apply_pack` into projects.

## Files

- `competition.yaml` — prefix COMP, category research
- `loop.yaml` — prefix LOOP, category research
- `experiment.yaml` — prefix EXPT, category research, id_format \\d{4,5}
- `finding.yaml` — prefix FIND, category research

Full schema content is in DDD-022.

## Acceptance Criteria

1. All 4 schemas pass `yaml.safe_load` and contain required SpecFlow schema fields
2. After `specflow init --with-pack autoresearch`, all 4 are present in `.specflow/schema/` of the target project
3. `specflow create --type competition --title 'Test' --verify-command 'echo 1' --metric-name 'Test' --metric-direction higher_is_better` succeeds
4. Same for loop, experiment, finding (each with their required fields)
5. EXPT can be created directly with status `kept`, `discarded`, `crashed`, or `no_op` (terminal-status design from DEC-047)
