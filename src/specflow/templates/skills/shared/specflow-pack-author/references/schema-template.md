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

## Status Transitions

The `allowed_status` dict maps each status to a list of valid next statuses:

```yaml
allowed_status:
  draft: []              # draft can transition to nothing (terminal) or to approved
  approved:
    - draft              # approved can go back to draft for rework
  mitigated:
    - approved           # mitigated can revert to approved
```

An empty list means the status is a valid terminal state (no further transition required from this status alone — transitions are validated by the artifact update logic).

## Example: Hazard Schema

```yaml
type: hazard
prefix: HAZ
id_format: "^HAZ-\\d{3}(\\.\\d{1,3})?$"
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
- ID format: `^{PREFIX}-\\d{3}(\\.\\d{1,3})?$` for parent.child numbering
