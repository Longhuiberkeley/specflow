---
id: STORY-031
title: "Install UX \u2014 one-line install path and getting-started tutorial"
type: story
status: verified
priority: high
tags:
- UX
- documentation
- M3-depth
suspect: false
created: '2026-04-14'
links:
- target: STORY-022
  role: depends_on
- target: STORY-023
  role: depends_on
- target: STORY-026
  role: depends_on
- target: REQ-018
  role: implements
- target: ARCH-010
  role: guided_by
- target: DDD-007
  role: specified_by
- target: QT-019
  role: verified_by
- target: IT-012
  role: verified_by
- target: UT-013
  role: verified_by
checklists_applied:
- checklist: check-STORY-031
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-10-18'
fingerprint: sha256:6caf80005302
version: 2
---

# Install UX — one-line install path and getting-started tutorial

## Description

Public-launch prerequisite: establish a one-line install path, populate README.md install section, and write the getting-started tutorial. This is the final M3 item because the API must be stable (post-rename, post-adapter-framework) before documenting it. Per retrospective §13.11 and §6.

### Deliverables

1. **One-line install** — `uv tool install git+https://github.com/Longhuiberkeley/specflow` or equivalent `uvx` path works end-to-end. Verify package metadata in `pyproject.toml` is complete (description, classifiers, URLs, entry points).

2. **README.md install section** — Install command, quick-verify (`specflow --help`), link to `docs/getting-started.md`.

3. **`docs/getting-started.md`** — Tutorial-shaped, transcript-style walkthrough. Covers: install → `specflow init` → `/specflow-discover` a simple REQ → `/specflow-plan` → `/specflow-execute` → verify results. Written against the stable post-rename API.

4. **Package metadata** — `pyproject.toml` has correct `description`, `classifiers` (Development Status, Topic, etc.), `project.urls` (Homepage, Documentation, Repository), and `[project.scripts]` entry point.

## Acceptance Criteria

1. `uv tool install git+https://github.com/Longhuiberkeley/specflow` (or the documented equivalent) installs the CLI and `specflow --help` works with no additional setup

> Amended 2026-10-18 (SPIKE-008 R1-133): the PyPI `specflow` name is an unrelated package. SpecFlow installs from Git only (AGENTS.md section 6), and the install commands above now say so.

2. `pyproject.toml` contains complete package metadata: description, version, classifiers, project URLs, and entry point

3. `README.md` has an install section with the one-liner, a quick-verify command, and links to docs

4. `docs/getting-started.md` exists as a transcript-style tutorial that walks a new user from cold install through a complete discover→plan→execute cycle

5. All command names in docs/getting-started.md use post-rename names (artifact-lint, artifact-review, change-impact, etc.)

## Out of Scope

- Publishing to PyPI (separate release step)
- GitHub Actions release workflow
- Logo, branding, landing page

## Dependencies

- STORY-022 (command rename — docs must reference final command names)
- STORY-023 (docs restructure — getting-started.md goes in the restructured docs/)
- STORY-026 (adapter framework — API surface must be stable)
