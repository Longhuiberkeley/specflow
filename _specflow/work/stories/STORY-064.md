---
id: STORY-064
title: Extend apply_pack with skill installation step
type: story
status: implemented
priority: high
tags:
- autoresearch
- wave-1
- scaffold
- pack
suspect: false
links:
- target: REQ-032
  role: implements
- target: DDD-023
  role: specified_by
- target: ARCH-022
  role: guided_by
created: '2026-05-15'
modified: '2026-06-15'
fingerprint: sha256:4f5d8d729f6c
---

# Extend apply_pack with skill installation step

## Outcome

`apply_pack(root, pack_name, packs_dir)` installs pack-bundled skills as Step 5, following the no-overwrite policy.

## Scope

- `src/specflow/lib/scaffold.py:116-192` — add Step 5 inside `apply_pack`
- Use `platform.detect_platform()` + `platform.get_skills_dir()` (no changes needed there)
- Extend return dict with `skills_added: [<name>...]`

## Acceptance Criteria

1. Pack manifest with `adds_skills: [foo]` and a `skills/foo/` directory results in `<platform_skills_dir>/foo/` being created on first install
2. Reinstalling the pack does not overwrite an existing skill directory
3. A pack declaring skills but installed in a project with no detected platform produces a warning, not an error
4. Return value includes `skills_added`
