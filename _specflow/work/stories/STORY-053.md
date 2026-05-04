---
id: STORY-053
title: Implement config merge and version stamp for init upgrade
type: story
status: implemented
priority: high
tags:
- init
- upgrade
- config
suspect: false
links:
- target: REQ-022
  role: implements
- target: ARCH-016
  role: guided_by
- target: DDD-017
  role: specified_by
created: '2026-05-04'
modified: '2026-05-04'
fingerprint: sha256:3138c854d574
---

# Implement config merge and version stamp for init upgrade

Modify `specflow init` to detect existing projects and merge configuration instead of overwriting. Add version stamp to config.yaml.

## Acceptance Criteria

1. Given an initialized project with user-modified config (domain, tags, packs), when `specflow init` is re-run, then the user's modified values are preserved while new default fields are added.
2. Given a fresh project with no `.specflow/` directory, when `specflow init` runs, then behavior is identical to the current implementation (no regression).
3. Given a newly initialized project, when init completes, then `config.yaml` contains a `version` field matching the current framework version.
4. Given a project initialized with an earlier version, when `specflow init` is re-run, then the version is updated and the delta is reported to the user.
5. Given an initialized project, when `specflow init` is re-run, then `state.yaml` is not overwritten.
6. Given an initialized project with pack-installed schemas, when `specflow init` is re-run, then existing schema files are preserved and only new framework schemas are added.
