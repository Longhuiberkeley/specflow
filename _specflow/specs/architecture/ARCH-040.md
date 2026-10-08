---
id: ARCH-040
title: Shipped-surface guards, pack resolution and format versioning
type: architecture
status: approved
tags:
- guards
- packs
- format-version
suspect: false
links:
- target: REQ-055
  role: derives_from
- target: REQ-056
  role: derives_from
- target: REQ-057
  role: derives_from
- target: DEC-090
  role: guided_by
created: '2026-09-30'
thinking_techniques:
- assumption_surfacing
- premortem
- devils_advocate
fingerprint: sha256:6f851214ea4b
modified: '2026-10-08'
---

# Shipped-surface guards, pack resolution and format versioning

## Responsibility
Keep what SpecFlow ships (skill text, checklists, pack text, always-on snippets, docs) executable against the CLI it ships with, resolve project-local packs before bundled ones, and version the on-disk format so consumer hooks and future migrations can refuse or upgrade safely.

## Public interface
- config.yaml format_version (integer) stamped by init and refresh; SUPPORTED_FORMAT_VERSION in lib/config; a once-per-process warning on mismatch; hook pre-commit refusal on mismatch.
- Pack resolution order: .specflow/packs/<name>/ then bundled packs, for init --preset and refresh --packs.
- Guard tests: prose-to-CLI surface (every specflow invocation in shipped text parses against build_parser), checklist corpus (parse, script presence, per-artifact argument, loader reachability), platform install safety (every platforms.yaml entry survives init plus refresh), aggregate always-on budget (base block plus pack snippets at most 375 words), reference lint (no repository-internal pointers), per-pack healthy fixtures (documented sequences yield zero warnings).

## Constraints
- Shipped text uses bare specflow; only this repository's dogfood files may use uv run.
- Skill templates and the .claude/skills mirror stay byte-identical.
- Guard tests run in the normal pytest suite; no CI-only or Java-dependent jobs.
- Consumer checklists are repaired by refresh --checklists only when the local copy fails to parse or --force is given; user-added checklists are never touched.
