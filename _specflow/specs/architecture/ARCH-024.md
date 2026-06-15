---
id: ARCH-024
title: Dynamic status dashboard for research categories
type: architecture
status: implemented
priority: medium
rationale: The status dashboard groups artifacts by category. When packs add new artifact
  types (e.g., research), the dashboard must display them without code changes.
tags:
- autoresearch
- status
- dashboard
suspect: false
links:
- target: REQ-033
  role: derives_from
created: '2026-06-07'
modified: '2026-06-15'
fingerprint: sha256:5eedd44d4af3
thinking_techniques: [assumption-surfacing]
---

# Dynamic status dashboard for research categories

## Component

The `specflow status` command reads each schema YAML's optional `category:` field to group artifact rows dynamically. The research pack sets `category: research` on COMP/LOOP/EXPT/FIND schemas, enabling automatic display without hardcoded prefix lists.

## Structure

- **Schema-driven grouping**: No hardcoded category lists — each schema declares its category, and the dashboard renders whatever categories have artifacts present.
- **Default category**: Schemas without `category:` default to `spec`.
- **Category ordering**: research appears last in the dashboard (spec → work → review → research), keeping the familiar layout unchanged when no research artifacts exist.

## Responsibility

- Eliminates the need to edit `status.py` when packs add new artifact types. Pack authors declare a category in their schema YAML and the dashboard picks it up automatically.
- Maintains backward compatibility: existing projects without research artifacts see no change in their status output.
- Groups artifacts logically so users can quickly assess progress across specification, work, review, and research dimensions.
