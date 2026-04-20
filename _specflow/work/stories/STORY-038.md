---
id: STORY-038
title: Add provider-agnostic CI gate command and GitHub Actions template
type: story
status: approved
priority: high
tags:
- rbac
- ci
- adapters
suspect: false
links:
- target: REQ-008
  role: implements
created: '2026-04-20'
modified: '2026-04-20'
---

# Add provider-agnostic CI gate command and GitHub Actions template

## Description

Add a `specflow ci-gate --base <ref> --head <ref>` CLI command that runs RBAC checks against a git diff between two refs. Update the GitHub Actions adapter to include a ci-gate job template. Update the `/specflow-adapter` skill to recommend ci-gate when RBAC roles are configured.

## Acceptance Criteria

1. Given a branch where an artifact transitions from `draft` to `approved` by an unauthorized author, when running `specflow ci-gate --base main --head feature-branch`, then the command detects the RBAC violation, prints a failure message, and exits with code 1

2. Given the `run_ci_gate` function in `hook.py`, when the git diff and log operations are examined, then only git CLI commands are used with no provider-specific API calls

3. Given the GitHub Actions adapter `_OP_JOBS` dictionary, when "ci-gate" is requested, then a job template is generated with `github.base_ref` and `github.head_ref` variables and `fetch-depth: 0`

4. Given the `/specflow-adapter` SKILL.md, when the CI Setup section is read, then ci-gate is recommended as an operation when team roles are configured

## Out of Scope

- GitLab CI or Bitbucket Pipelines adapters
- Auto-installing the gate into an existing workflow
- PR comment posting or status check API calls

## Dependencies

- REQ-008 must be approved
- `lib/rbac.py` authorize_status_transition and check_independence must exist
- Git must be available in the CI environment
