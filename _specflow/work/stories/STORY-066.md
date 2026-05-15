---
id: STORY-066
title: Make specflow status dashboard dynamic via category
type: story
status: implemented
priority: medium
tags:
- autoresearch
- wave-1
- status
suspect: false
links:
- target: REQ-033
  role: implements
- target: DDD-024
  role: specified_by
created: '2026-05-15'
modified: '2026-05-15'
fingerprint: sha256:e325091f42c4
---

# Make specflow status dashboard dynamic via category

## Outcome

`specflow status` groups dashboard rows by the `category:` field on each schema, replacing the hardcoded prefix lists.

## Scope

- `src/specflow/commands/status.py:209-256` — introduce `_load_categories(root)` helper that reads `.specflow/schema/*.yaml` and groups prefixes by category
- Replace the three hardcoded blocks (Specs, Reviews, Work) with iteration over loaded categories
- Render order: spec, work, review, research
- Render a row only if at least one artifact in that category has count > 0

## Acceptance

- Existing projects (no research artifacts) show identical output to today
- A project with a COMP/LOOP/EXPT/FIND shows a fourth "Research:" row
- Removing the autoresearch pack (deleting research schemas) hides the Research row again
- Status tests still pass
