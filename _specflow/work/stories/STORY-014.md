---
id: STORY-014
title: Enforce role-based access control via git hooks and CODEOWNERS
type: story
status: implemented
priority: medium
tags:
- team
- rbac
- security
- P7
suspect: false
links:
- target: REQ-005
  role: implements
- target: ARCH-002
  role: guided_by
created: '2026-04-11'
checklists_applied:
- checklist: check-STORY-014
  timestamp: '2026-04-11T13:45:49Z'
- checklist: check-STORY-014
  timestamp: '2026-04-14T17:03:23Z'
modified: '2026-04-14'
fingerprint: sha256:91ea8b11001c
---

# Enforce role-based access control via git hooks and CODEOWNERS

## Description

Implement RBAC using git-native mechanisms: CODEOWNERS for directory-level ownership, pre-commit hooks that check git author roles from .specflow/config.yaml, and GPG-signed commits for verified status transitions. Ensures implementer != verifier.

## Acceptance Criteria

1. Given roles configured in .specflow/config.yaml (verifiers: [alice], approvers: [bob]), when user 'charlie' (not in verifiers) attempts to commit a status change to 'verified' on any artifact, then the pre-commit hook rejects the commit with a message listing authorized verifiers

2. Given specflow init is run on a project configured for team use, then a CODEOWNERS file is generated mapping _specflow/specs/ directories to configured role groups

3. Given user 'alice' (a verifier) changes STORY-001's status to verified and signs the commit with GPG, when the commit is pushed, then the verification is recorded with the GPG signature as the electronic signature in the artifact's checklists_applied

4. Given a user who implemented STORY-001 attempts to also verify it, then the pre-commit hook rejects the verification with a message about independence enforcement (implementer != verifier)

## Out of Scope

- Cross-repo RBAC
- OAuth/SSO integration

## Dependencies

- None
