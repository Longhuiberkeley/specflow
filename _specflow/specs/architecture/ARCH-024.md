---
id: ARCH-024
title: Dynamic status dashboard for research categories
type: architecture
status: implemented
priority: medium
rationale: The status dashboard groups artifacts by category. When packs add new
  artifact types (e.g., research), the dashboard must display them without code changes.
tags:
- autoresearch
- status
- dashboard
suspect: false
links:
- target: REQ-033
  role: derives_from
created: '2026-06-07'
---

# Dynamic status dashboard for research categories

## Design

The `specflow status` command reads each schema YAML's optional `category:` field to group artifact rows. The research pack sets `category: research` on COMP/LOOP/EXPT/FIND schemas.

## Key decisions

- **Schema-driven grouping**: No hardcoded category lists — each schema declares its category, and the dashboard renders whatever categories have artifacts.
- **Default category**: Schemas without `category:` default to `spec`.
- **Category ordering**: research appears last in the dashboard (spec → work → review → research), keeping the familiar layout unchanged when no research artifacts exist.
