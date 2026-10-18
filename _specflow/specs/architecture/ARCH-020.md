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
modified: '2026-10-08'
fingerprint: sha256:75c8167aecc6
thinking_techniques:
- assumption_surfacing
- devils_advocate
rationale: 'Fully implemented: SPIDR, wave-cycle, DDD selection, decision guidance,
  and the bundled no-API handbook fallback now ship with executable evidence.'
version: 2
---

# Decomposition Guidance System

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-034); earlier text described a `best_practices.py` / `templates/best-practices/` API-key fallback and plan Step 3 creating DEC artifacts (the plan skill now reads discover's DECs and writes option briefs before a contested ARCH).

Provides deterministic validation and reference guidance for decomposition completeness. Includes SPIDR dimension coverage checks, story dependency cycle detection, a bundled best-practice seed catalogue, DDD selection guidance, and plan-skill decision guidance.

## Package Structure

```
src/specflow/commands/artifact_lint.py       — checks spidr-coverage (_check_spidr_coverage) and wave-cycles (_check_wave_cycles)
src/specflow/lib/practices_seed.py           — bundled generic + domain best-practice seed catalogue (no external API)
src/specflow/commands/practices.py           — `specflow practices seed [--create] [--verbose]`
src/specflow/commands/handbook.py            — deprecated `handbook generate` alias delegating to `practices seed`
.claude/skills/specflow-plan/references/     — ddd-selection.md (6-question DDD checklist)
.claude/skills/specflow-plan/SKILL.md        — Step 2 loads discover's DECs and seeds BPs; Step 3 option briefs; Step 4 DDD selection
```

## Component Responsibilities

1. **SPIDR Coverage Checker**: Scans story tags for `spidr-*` prefixes. Reports which of the 5 dimensions (spike, path, interface, data, rules) have zero stories, as warning `spidr-coverage/dimension`; with fewer stories than dimensions the gaps are informational only. Never blocking.

2. **Wave Cycle Detector**: Imports `compute_waves()` from `lib/waves.py`. Runs with every `artifact-lint` and alone via `artifact-lint --type wave-cycles`. Reports circular dependencies (`wave-cycles/cycle`) and stories with excessive (>3) dependencies (`wave-cycles/fan-in`), as warnings.

3. **Bundled Practice Seeds**: `lib/practices_seed.py` is the single source of truth for the bundled catalogue: universal generic practices plus domain practices selected by `project.domain` (`generate_handbook(root)` returns them with `source: "bundled"`). `specflow practices seed` lists them and `--create` drafts BP artifacts for the user to approve; no API key is involved. `specflow handbook generate` remains as a stderr-warned deprecated alias for `practices seed`.

4. **DDD Selection Guide**: Reference document with a 6-question decision checklist. Not enforced by lint — used by the plan skill during Step 4 to decide which ARCHs need DDD artifacts.

5. **Plan Decision Guidance**: Skill instruction. In Step 2 the plan skill loads the DECs that discover's challenge step created; in Step 3, when a component's structure is a real choice (irreversible, a new external dependency, or two plausible approaches), it writes 2-3 one-paragraph option briefs with the user before the ARCH, and it surfaces key decisions in the approval presentation.

## Interfaces

- `_check_spidr_coverage(artifacts) -> dict` — the `spidr-coverage` lint check (shared check-result dict)
- `_check_wave_cycles(artifacts, root) -> dict` — the `wave-cycles` lint check
- `practices_seed.generate_handbook(root) -> dict` and `practices_seed.get_practices(domain) -> list[Practice]` — the bundled catalogue
- CLI: `specflow practices seed [--create] [--verbose]`; `specflow handbook generate` (deprecated alias)
- Reference: `references/ddd-selection.md`

## Dependencies

- Existing `lib/waves.py` for cycle detection
- `lib/practices_seed.py` and `lib/config.get_domain` for the bundled practice catalogue
- Existing DEC artifact type (DECs created by discover's challenge step)
- Story tag convention (`tags:` field in frontmatter)

## Data Flow

1. `artifact-lint` runs spidr-coverage and wave-cycles alongside the other checks
2. `specflow practices seed` (or the deprecated `handbook generate`) reads the project domain and lists or drafts the bundled practices, with no API key
3. Plan skill loads discover's DECs and seeds BPs in Step 2, writes option briefs for contested components in Step 3, and reads ddd-selection.md in Step 4
