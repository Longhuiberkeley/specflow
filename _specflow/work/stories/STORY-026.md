---
id: STORY-026
title: Build the unified adapter framework
type: story
status: draft
priority: high
tags:
- architecture
- adapters
- M2-extensible
suspect: false
created: '2026-04-14'
checklists_applied:
- checklist: check-STORY-026
  timestamp: '2026-04-14T17:03:23Z'
---

# Build the unified adapter framework

## Description

Build the unified adapter framework from retrospective §11 to replace the three hardcoded integration paths (CI/CD, exchange formats, standards ingestion) with a single config-driven dispatch system. Turns N×M integration into N+M. Ship with two working adapters: GitHub Actions (CI) and ReqIF (exchange).

### Deliverables

1. **`lib/adapters/base.py`** — Adapter interface with `name`, `supported_operations`, and methods: `generate_ci_workflow()`, `import_artifacts()`, `export_artifacts()`, `ingest_standard()`

2. **`lib/adapters/github_actions.py`** — Generates CI workflows for declared operations (artifact-lint, change-impact, project-audit, release-gate). Replaces the hand-maintained `.github/workflows/specflow.yml` with generated output.

3. **`lib/adapters/reqif.py`** — Bidirectional exchange adapter. Ports existing P7 `lib/reqif.py` code behind the adapter interface.

4. **`.specflow/adapters.yaml`** — Config shape for CI provider, exchange formats, and standards sources (see retrospective §11 for schema)

5. **`specflow ci generate` CLI** — Reads adapters.yaml, picks CI adapter, writes workflow files

6. **`specflow import/export --adapter <name>` CLI** — Explicit adapter selection replacing per-format subcommands

7. **`specflow hook install`** — Asks the CI adapter for the appropriate hook script (Bash or PowerShell), closing the Windows shell-wrapper gap

8. **`docs/authoring-an-adapter.md`** — Covers all three axes with a worked example

### Explicitly NOT shipped

No GitLab/Bitbucket/Jenkins adapters. No Jira/Linear/GitHub Issues exchange adapters. No PowerShell hook adapter. No "coming soon" roadmap promises — the framework IS the invitation for contributions.

## Acceptance Criteria

1. `specflow ci generate` reads `.specflow/adapters.yaml` and produces a working GitHub Actions workflow file without hardcoded templates

2. `specflow import --adapter reqif path.reqif` imports artifacts via the adapter interface; `specflow export --adapter reqif out.reqif` exports via the same interface

3. The existing ReqIF import/export functionality is fully preserved behind the new adapter interface with no behavioral regressions

4. `specflow hook install` delegates hook script generation to the CI adapter, enabling future PowerShell support without codebase changes

5. `docs/authoring-an-adapter.md` exists and contains a worked example showing how to create a new adapter

6. No hardcoded provider branching in command code — all dispatch goes through the adapter interface

7. The old `.github/workflows/specflow.yml` can be deleted and regenerated via `specflow ci generate`

## Out of Scope

- Additional CI/exchange adapters (community contribution territory)
- `/specflow-pack-author` (STORY-028, uses the standards-ingestion axis)
- Scheduled audit, RBAC doctor, compliance dashboard (enterprise features)

## Dependencies

- STORY-022 (command rename — import/export CLI refactoring)
