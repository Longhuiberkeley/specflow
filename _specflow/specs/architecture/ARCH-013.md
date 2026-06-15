---
id: ARCH-013
title: Structure Checklists & Doc Lifecycle
type: architecture
status: implemented
suspect: false
links:
- target: REQ-021
  role: derives_from
- target: IT-015
  role: verified_by
created: '2026-04-22'
fingerprint: sha256:eaee17cccf0b
thinking_techniques: [assumption-surfacing, devil's-advocate]
version: 1
modified: '2026-06-15'
---

# Structure Checklists & Doc Lifecycle

## Component

The checklist and document lifecycle system enforces structural conventions on artifacts through automated validation:

- **Checklist engine** (`lib/checklists.py`): Loads checklist YAML definitions from packs or `.specflow/checklists/`, evaluates each clause against artifact content, and produces pass/fail/skip verdicts.
- **Lint engine** (`lib/lint.py`): Validates artifact frontmatter schemas, enforces status hierarchies, detects acceptance criteria, and flags structural warnings (missing headers, short bodies, broken links).
- **Lifecycle enforcement**: Artifacts progress through `draft → approved → implemented → verified`. Transitions are validated against role-based authorization rules in `lib/rbac.py`.

## Structure

Checklist YAML files define a sequence of clauses, each with an `id`, `description`, and optional `severity` (blocking vs. advisory). The `checklist-run` command evaluates these against a target artifact directory, producing a verdict report.

Doc lifecycle is driven by YAML frontmatter `status` field mutations. The `specflow update` command is the only sanctioned path for status changes, ensuring audit trail integrity via fingerprint updates.

## Data Flow

Artifact file → frontmatter parsing → schema validation → checklist evaluation → verdict report. Status changes flow through `specflow update` → `lib/artifacts.py` (frontmatter rewrite) → fingerprint recomputation → optional cascade to linked artifacts.

## Dependencies

- `lib/lint.py` for schema validation and structural checks.
- `lib/checklists.py` for checklist loading and clause evaluation.
- `lib/rbac.py` for role-based transition authorization.
- Pack system for shipping domain-specific checklists (e.g., ISO 26262 compliance packs).
