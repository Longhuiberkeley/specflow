---
id: STORY-636
title: Autoresearch CLI writes traceable link edges (plan/log/suggest-finds)
type: story
status: implemented
tags:
- autoresearch
suspect: false
links:
- target: REQ-034
  role: implements
- target: REQ-035
  role: implements
created: '2026-08-26'
fingerprint: sha256:e62fc2d27768
modified: '2026-08-26'
output_files:
- src/specflow/commands/autoresearch.py
- src/specflow/commands/artifact_lint.py
- tests/test_autoresearch_cli.py
---

# Autoresearch CLI writes traceable link edges (plan/log/suggest-finds)

## Goal

autoresearch plan/log/suggest-finds populate parent IDs in frontmatter but never write the link edges specflow trace needs, so CLI-created LOOP/EXPT/FIND artifacts vanish from the trace graph. Tests masked this by pre-seeding links.

## Acceptance Criteria

1. plan writes LOOP operates_on→COMP; log writes EXPT belongs_to→LOOP; suggest-finds --write writes FIND belongs_to→COMP + condenses→LOOP (in addition to existing frontmatter).
2. Update paths merge edges idempotently without clobbering unrelated links.
3. New CLI-path tests create artifacts without pre-seeded links and then assert specflow trace renders the hierarchy; FIND trace renders its COMP/LOOP.
4. artifact-lint surfaces missing links on existing (legacy) pack artifacts as a warning with a repair hint (forward-only writes + deterministic detection).

## Authorization note
Pre-authorized by the owner via scheduled autonomous task (oc-later 2026-08-26).
