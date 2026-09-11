# Schema Template

Each schema YAML file defines a new artifact type that SpecFlow can create, validate, and track.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Lowercase artifact type identifier (e.g., `hazard`, `threat`, `control`) |
| `prefix` | string | Uppercase prefix for artifact IDs (e.g., `HAZ`, `THR`, `CTL`) |
| `id_format` | regex | Regex pattern for valid artifact IDs |
| `required_fields` | list | YAML frontmatter fields that must be present |
| `allowed_status` | dict | Valid statuses and their allowed transitions |
| `directory` | string | `_specflow/specs/` subdirectory for artifacts of this type |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `optional_fields` | list | YAML frontmatter fields that may be present |
| `allowed_link_roles` | list | Valid link roles for `links:` frontmatter entries |
| `initial_statuses` | list | Creation entry point(s). Overrides computed empty-predecessor roots when present; omitted → today's computed-root behavior |

## Status Transitions

The `allowed_status` dict maps each status to the statuses it may be entered *from* (target → predecessors):

```yaml
allowed_status:
  draft: []              # draft can transition to nothing (terminal) or to approved
  approved:
    - draft              # approved can go back to draft for rework
  mitigated:
    - approved           # mitigated can revert to approved
```

An empty predecessor list marks a computed creation root (the default `--status` when exactly one such status exists).

### `initial_statuses`

When a status must both be a creation default *and* have a predecessor — for example a reversible pause — declare `initial_statuses` so create still lands on that entry point:

```yaml
initial_statuses: [active]
allowed_status:
  active: [paused]       # paused → active is legal
  paused: [active]
  completed: [active]
```

Without `initial_statuses`, `active: [paused]` has no empty-predecessor root, so implicit create would require `--status`. A multi-entry list behaves like today's multi-root schemas (explicit `--status` required; each listed status is sanction-free at creation). Unknown names in the list are ignored; if none remain, SpecFlow falls back to computed roots.

## Example: Hazard Schema

```yaml
type: hazard
prefix: HAZ
id_format: "^HAZ-\\d{3,5}(\\.\\d{1,3})?$"
required_fields:
  - id
  - title
  - type
  - status
  - created
optional_fields:
  - priority
  - version
  - rationale
  - tags
  - suspect
  - fingerprint
  - links
  - modified
  - severity
  - controllability
  - exposure
  - asil_level
allowed_status:
  draft: []
  approved:
    - draft
  mitigated:
    - approved
allowed_link_roles:
  - refined_by
  - derives_from
  - complies_with
  - verified_by
directory: _specflow/specs/hazards/
```

## Naming Conventions

- `type`: lowercase, singular (e.g., `hazard` not `hazards`)
- `prefix`: uppercase, 2-4 letters (e.g., `HAZ`, `THR`, `CTRL`)
- `directory`: `_specflow/specs/{plural-type}/` (e.g., `_specflow/specs/hazards/`)
- ID format: `^{PREFIX}-\\d{3,5}(\\.\\d{1,3})?$` for parent.child numbering
