---
id: ARCH-022
title: Pack-as-integration-boundary for autoresearch
type: architecture
status: implemented
priority: high
rationale: Shipping autoresearch as a pack (not core) keeps the default SpecFlow experience
  unchanged for non-research projects and establishes a reusable pattern for future
  capability extensions
tags:
- autoresearch
- architecture
- pack
suspect: false
links:
- target: REQ-028
  role: derives_from
- target: REQ-032
  role: derives_from
created: '2026-05-15'
modified: '2026-06-07'
fingerprint: sha256:0b506123054f
---

# Pack-as-integration-boundary for autoresearch

Autoresearch is delivered as a SpecFlow pack at `src/specflow/packs/autoresearch/`, applied opt-in via `specflow init --with-pack autoresearch`.

## Pack contents

```
src/specflow/packs/autoresearch/
├── pack.yaml              # manifest: adds_artifact_types, adds_directories, adds_skills
├── schemas/               # competition.yaml, loop.yaml, experiment.yaml, finding.yaml
└── skills/
    └── specflow-autoresearch/
        ├── SKILL.md
        └── references/    # 4 protocol .md files
```

## Why a pack

- **Isolation**: COMP/LOOP/EXPT/FIND directories aren't created in projects that don't opt in
- **Reusability**: the `adds_skills` pack-manifest field becomes generic — any future pack can ship skills
- **Parity with existing iso26262-demo pack**: same install mechanism, same no-overwrite policy

## Forward compatibility

The category-based status grouping (REQ-033) and the research-chain trace (REQ-034) are implemented in core SpecFlow, not in the pack — so any future research-style pack inherits both for free.
