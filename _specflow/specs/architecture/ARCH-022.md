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
modified: '2026-06-15'
fingerprint: sha256:13275b1aa6fc
thinking_techniques: [assumption-surfacing, devil's-advocate]
---

# Pack-as-integration-boundary for autoresearch

## Component

Autoresearch is delivered as a SpecFlow pack at `src/specflow/packs/autoresearch/`, applied opt-in via `specflow init --with-pack autoresearch`. The pack contains a `pack.yaml` manifest, four schema YAMLs (competition, loop, experiment, finding), and a skill directory with `SKILL.md` plus protocol reference documents.

## Structure

```
src/specflow/packs/autoresearch/
├── pack.yaml              # manifest: adds_artifact_types, adds_directories, adds_skills
├── schemas/               # competition.yaml, loop.yaml, experiment.yaml, finding.yaml
└── skills/
    └── specflow-autoresearch/
        ├── SKILL.md
        └── references/    # 4 protocol .md files
```

## Responsibility

- **Isolation**: COMP/LOOP/EXPT/FIND directories are not created in projects that do not opt in, keeping the default SpecFlow experience unchanged for non-research projects.
- **Reusability**: the `adds_skills` pack-manifest field is generic — any future pack can ship skills via the same mechanism.
- **Parity**: shares the same install mechanism and no-overwrite policy as the existing iso26262-demo pack.

## Dependencies

The category-based status grouping (REQ-033) and the research-chain trace (REQ-034) are implemented in core SpecFlow, not in the pack, so any future research-style pack inherits both capabilities for free. The pack depends on `lib/scaffold.py` for directory creation and `lib/platform.py` for skills directory resolution.
