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
fingerprint: sha256:7638ec09a640
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

- Existing projects (no research artifacts) render the three core rows in spec → work → review order (the Reviews and Work rows are intentionally swapped vs. pre-066 output to match DDD-024's render-order rule)
- A project with zero artifacts in a category renders no row for that category (no "always show core categories" exception — matches DDD-024 §rendering rule)
- A project with a COMP/LOOP/EXPT/FIND shows a fourth "Research:" row
- Removing the autoresearch pack (deleting research schemas) hides the Research row again
- Status tests still pass
