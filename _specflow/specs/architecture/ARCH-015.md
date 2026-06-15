---
id: ARCH-015
title: Deprecation Cleanup
type: architecture
status: implemented
suspect: false
links:
- target: REQ-014
  role: derives_from
created: '2026-04-22'
modified: '2026-06-15'
fingerprint: sha256:8bd625c65830
thinking_techniques: [assumption-surfacing]
---

# Deprecation Cleanup

## Component

Removes eight deprecated CLI aliases from `cli.py` and fixes a schema inconsistency in the requirement schema definition.

## Structure

- **Deprecated aliases removed**: `validate` → `artifact-lint`, `check` → `checklist-run`, `impact` → `change-impact`, `tweak` → `fingerprint-refresh`, `sequence` → `renumber-drafts`, `verify` → `artifact-review`, `audit` → `project-audit`, `compliance` → `project-audit`. These were hidden from help but still functional; removing them reduces the command surface to the canonical set.
- **Schema fix**: `reqif_metadata` added to `.specflow/schema/requirement.yaml` optional_fields list, resolving a mismatch between the schema definition and actual artifact frontmatter.

## Responsibility

- Eliminates maintenance burden of shadow aliases that could confuse users about the canonical command names.
- Ensures `specflow artifact-lint` passes cleanly after cleanup by fixing the schema field mismatch.
- All existing tests continue to pass — this is a removal-only change with no new behavior.

## Dependencies

- `cli.py` for alias definitions (Click command registration).
- `.specflow/schema/requirement.yaml` for the schema fix.
- `lib/lint.py` for post-cleanup validation.
