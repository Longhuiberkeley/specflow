---
id: ARCH-020
title: Decomposition Guidance System
type: architecture
status: implemented
suspect: false
links:
- target: REQ-026
  role: derives_from
created: '2026-05-04'
modified: '2026-05-05'
fingerprint: sha256:a1e55914cd09
---

# Decomposition Guidance System

Provides deterministic validation and reference guidance for decomposition completeness. Includes SPIDR dimension coverage checks, story dependency cycle detection, bundled generic best practices, DDD selection guidance, and plan-skill decision artifact creation.

## Package Structure

```
src/specflow/commands/artifact_lint.py       — New checks: spidr-coverage, wave-cycles
src/specflow/lib/best_practices.py           — Bundled generic BP fallback
src/specflow/templates/best-practices/       — Generic phase BP YAML files
.claude/skills/specflow-plan/references/     — ddd-selection.md (new reference doc)
.claude/skills/specflow-plan/SKILL.md        — Updated: DEC creation in Step 3
```

## Component Responsibilities

1. **SPIDR Coverage Checker**: Scans story tags for `spidr-*` prefixes. Reports which of the 5 dimensions (spike, path, interface, data, rules) have zero stories. Warning-only, not blocking.

2. **Wave Cycle Detector**: Imports `compute_waves()` from `waves.py`. Runs during `artifact-lint --type wave-cycles`. Reports circular dependencies and stories with excessive (>3) dependencies.

3. **Generic BP Bundler**: Ships 3-5 universal best-practice YAML files in `templates/best-practices/`. When `handbook generate` is called without an API key, copies these as fallback instead of failing.

4. **DDD Selection Guide**: Reference document with a 6-question decision checklist. Not enforced by lint — used by the plan skill during Step 4 to decide which ARCHs need DDD artifacts.

5. **Plan Decision Recorder**: Skill instruction update. During Step 3, when significant architectural choices are made, the plan skill creates DEC artifacts to make choices traceable and feed back into the handbook system.

## Interfaces

- `_check_spidr_coverage(artifacts) -> (blocking, warnings, details)` — new lint check
- `_check_wave_cycles(root) -> (blocking, warnings, details)` — new lint check
- `best_practices.copy_generic_fallback(cache_path, phase)` — fallback copy
- New reference: `references/ddd-selection.md`

## Dependencies

- Existing `waves.py` for cycle detection
- Existing `best_practices.py` for handbook generation
- Existing DEC artifact type and create command
- Story tag convention (`tags:` field in frontmatter)

## Data Flow

1. `artifact-lint` runs spidr-coverage and wave-cycles alongside existing checks
2. `handbook generate` falls back to bundled generic BPs when no API key
3. Plan skill reads ddd-selection.md during Step 4, creates DEC artifacts in Step 3
