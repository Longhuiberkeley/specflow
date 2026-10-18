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
modified: '2026-10-08'
fingerprint: sha256:0c98f70db67a
thinking_techniques:
- assumption_surfacing
version: 2
---

# Deprecation Cleanup

> Rewritten 2026-10-18 against the engine as built (SPIKE-008 R1-031); earlier text described Click command registration.

## Component

Removes eight deprecated CLI aliases from `cli.py` and fixes a schema inconsistency in the requirement schema definition.

## Structure

- **Deprecated aliases removed**: `validate` → `artifact-lint`, `check` → `checklist-run`, `impact` → `change-impact`, `tweak` → `fingerprint-refresh`, `sequence` → `renumber-drafts`, `verify` → `artifact-review`, `audit` → `project-audit`, `compliance` → `project-audit`. These were hidden from help but still functional; removing them reduces the command surface to the canonical set. None of the other seven names is a top-level command today. The name `verify` was later reused for an unrelated top-level command (`specflow verify`, `commands/verify.py`, which runs verification contracts); it is not an alias of `artifact-review`.
- **Schema fix**: `reqif_metadata` added to the requirement schema's `optional_fields` list (shipped as `src/specflow/templates/schemas/requirement.yaml`, installed as `.specflow/schema/requirement.yaml`), resolving a mismatch between the schema definition and actual artifact frontmatter.

## Responsibility

- Eliminates maintenance burden of shadow aliases that could confuse users about the canonical command names.
- Ensures `specflow artifact-lint` passes cleanly after cleanup by fixing the schema field mismatch.
- All existing tests continue to pass — this is a removal-only change with no new behavior.

## Dependencies

- `cli.py` for command registration: argparse subparsers added by the `_add_<name>_parser()` helpers, and the `main()` dispatch dict that maps command names to handlers.
- The requirement schema (`templates/schemas/requirement.yaml` and its installed copy `.specflow/schema/requirement.yaml`) for the schema fix.
- `specflow artifact-lint` (`commands/artifact_lint.py`, which validates schemas through `lib/lint.py`) for post-cleanup validation.
