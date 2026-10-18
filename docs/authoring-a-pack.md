# Authoring a Standards Pack (Manual)

This guide walks through creating a standards compliance pack without LLM assistance. If you prefer LLM-assisted authoring, use `/specflow-pack-author` instead.

## When to Author a Pack

Create a pack when you need SpecFlow to track compliance against an external standard — an industry regulation (ISO 26262, DO-178C), an internal policy, or a contractual requirement.

## Directory Structure

A pack is a self-contained directory:

```
{name}/
├── pack.yaml              # Pack manifest (required)
├── standards/
│   └── {name}.yaml        # Standard clauses (required)
├── schemas/               # Only if pack adds new artifact types
│   └── {type}.yaml
├── checklists/            # Optional: pack-specific checklists
│   └── {category}/*.yaml
└── README.md              # Human-readable description (recommended)
```

For bundled packs (shipped with SpecFlow), place this under `src/specflow/packs/{name}/`. For project-local packs, use `.specflow/packs/{name}/`.

## Step 1: Create pack.yaml

The pack manifest declares what the pack adds to a project.

```yaml
name: my-standard
version: "1.0.0"
description: "My internal security compliance standard"
adds_artifact_types:
  - security-finding
adds_directories:
  - specs/security-findings
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Pack identifier. Use lowercase with hyphens (e.g., `iso26262`, `soc2-type2`). |
| `version` | Yes | Version string. Follow semantic versioning or use a label like `"0.1-draft"`. |
| `description` | Yes | One-line human summary. `specflow pack-validate` requires it; `specflow init` does not print it. |
| `adds_artifact_types` | No | List of artifact type IDs that this pack introduces. Each must have a matching schema file in `schemas/`. |
| `adds_directories` | No | List of `_specflow/` relative paths to create when the pack is installed. One per new artifact type, matching the `directory` field in each schema. |

If your pack only adds standard clauses (no new artifact types), omit `adds_artifact_types` and `adds_directories`.

## Step 2: Write the Standards YAML

Create `standards/{name}.yaml` with the clauses from your standard.

```yaml
standard: my-standard
title: "My Internal Security Compliance Standard"
version: "1.0.0"
clauses:
  - id: "SEC-1"
    title: "Access Control"
    description: "All systems shall enforce role-based access control. Users must be authenticated before accessing protected resources."
  - id: "SEC-2"
    title: "Audit Logging"
    description: "All authentication and authorization events shall be logged with timestamp, user ID, source IP, and outcome."
  - id: "SEC-3"
    title: "Data Encryption"
    description: "Sensitive data at rest shall be encrypted using AES-256 or equivalent. Keys shall be rotated at least annually."
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `standard` | Yes | Identifier matching the pack `name`. |
| `title` | Yes | Full title of the standard. |
| `version` | Yes | Version of the source standard. |
| `clauses` | Yes | List of clause objects. |

### Clause Object

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Clause identifier from the source. Preserve the original ID format. |
| `title` | Yes | Short clause title. |
| `description` | Yes | Clause text or summary. Use normative language ("shall", "should", "may"). |

Clause objects may carry `severity` (`high` / `medium` / `low`, default `medium`), `category` and `priority`; these three sort and label gaps in `specflow standards gaps`. Other fields (e.g. `asil_level`, `verification_method`) are tolerated and stay in the YAML, but no command reports them.

## Step 3: Define New Artifact Types (Optional)

If your standard requires tracking artifact types beyond the built-in ones (`requirement`, `architecture`, `detailed-design`, `unit-test`, `integration-test`, `qualification-test`, `story`, `spike`, `decision`, `defect`, `audit`, `challenge`, `review`, `best-practice`; plus the optional core types `hazard`, `control` and `risk` enabled by `init --with-types`), create a schema for each. Do not name a pack type after a core type.

Create `schemas/{type}.yaml`:

```yaml
type: security-finding
prefix: SEC
id_format: "^SEC-\\d{3}(\\.\\d{1,3})?$"
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
  - cvss_score
  - affected_systems
allowed_status:
  draft: []
  approved:
    - draft
  remediated:
    - approved
  accepted:
    - approved
allowed_link_roles:
  - refined_by
  - derives_from
  - complies_with
  - verified_by
directory: _specflow/specs/security-findings/
```

### Schema Fields

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Lowercase artifact type identifier. Singular form. |
| `prefix` | Yes | Uppercase prefix for artifact IDs (2-4 letters). |
| `id_format` | Yes | Regex pattern for valid IDs. Escape backslashes in YAML (`\\d`). |
| `required_fields` | Yes | Frontmatter fields that must be present on every artifact. |
| `allowed_status` | Yes | Map of each status to the statuses it may be entered *from* (target → predecessors). An empty list is a computed creation root. |
| `directory` | Yes | `_specflow/specs/` subdirectory for this type's artifacts. |
| `optional_fields` | No | Additional fields that may appear. |
| `allowed_link_roles` | No | Valid link roles for `links:` entries. |
| `initial_statuses` | No | Creation entry point(s). When present, overrides computed empty-predecessor roots for default `--status` resolution and the create sanction gate. When absent, behavior is unchanged (computed roots). Use this for reversible cycles — e.g. `active: [paused]` so paused→active is legal, plus `initial_statuses: [active]` so create still defaults to / sanction-freely accepts `active`. A multi-entry list is ambiguous for implicit create (explicit `--status` required); each listed status is sanction-free at creation. Unknown names in the list are ignored; if none remain, SpecFlow falls back to computed roots. |

### Registering the Type

Add the type name to `adds_artifact_types` in `pack.yaml`, and add the directory to `adds_directories`:

```yaml
adds_artifact_types:
  - security-finding
adds_directories:
  - specs/security-findings
```

The `directory` field in the schema and the entry in `adds_directories` must match.

## Step 4: Add Checklists (Optional)

If your standard defines review checklists, add them under `checklists/`. The directory structure mirrors `.specflow/checklists/`:

```
checklists/
├── phase-gates/
│   └── my-standard-gate.yaml
└── review/
    └── my-standard-review.yaml
```

Each checklist YAML follows the standard checklist format used by `specflow checklist-run`.

## Step 5: Write README.md

A brief description of the pack:

```markdown
# My Standard Pack

Covers compliance tracking against [Standard Name] version [X.Y].

## Coverage

- [N] clauses from [source standard]
- [M] new artifact types: [list types]

## Source

[Link or reference to the original standard document]

## Notes

[Any limitations, scope restrictions, or disclaimers]
```

## Step 6: Validate the Pack

Run the validation script (if using `/specflow-pack-author`, this runs automatically):

```bash
.claude/skills/specflow-pack-author/scripts/validate-pack.sh src/specflow/packs/{name}/
```

Or manually check:
1. `pack.yaml` exists with `name`, `version`, `description`
2. `standards/{name}.yaml` exists with `standard`, `title`, `clauses` (at least 1 clause)
3. If `adds_artifact_types` is set, each type has a matching `schemas/{type}.yaml`
4. If `adds_directories` is set, each directory corresponds to a schema's `directory` field

## Step 7: Install the Pack

### Option A: Bundled Pack (Development)

Copy the pack directory to `src/specflow/packs/` in the SpecFlow source tree, then users can install it with:

```bash
specflow init --preset {name}
```

### Option B: Project-Local Pack

For a single project, put the pack directory at `.specflow/packs/{name}/` and install it:

```bash
specflow init --preset {name}
```

`init` resolves the pack from `.specflow/packs/{name}/`. On an initialized project it runs in merge mode, keeps your config, installs the standards, schemas, directories, checklists, skills and context block, and registers the pack in `active_packs`. After editing an installed pack, run `specflow refresh --packs --force` to sync it. Do not copy pack files into `.specflow/` or edit `config.yaml` by hand: the pack would not be registered, so its skills, context block and later syncs would be missing.

## Step 8: Declare Coverage in Artifacts

Installing a pack makes its clauses available, but coverage is only recorded when artifacts explicitly link to them. Use the `complies_with` link role in any artifact's frontmatter:

```yaml
---
id: REQ-001
title: Access Control
type: requirement
status: approved
links:
  - target: "SEC-1"
    role: complies_with
  - target: "SEC-2"
    role: complies_with
---
```

`target` must match a clause `id` exactly as written in your `standards/{name}.yaml`.

You can link any artifact type — requirements, architecture specs, stories, test records — to clause IDs. Multiple artifacts can cover the same clause; a clause counts as covered once any artifact links to it, and the reports list the clauses that remain uncovered.

## Step 9: Check Coverage with `specflow standards gaps`

Once at least one artifact has a `complies_with` link, list the uncovered clauses. The command is read-only:

```bash
specflow standards gaps
```

If you have multiple standards installed, specify which one:

```bash
specflow standards gaps --standard my-standard
```

**Example output:**

```
Standard: My Internal Security Compliance Standard
  Total: 3 clauses | Covered: 2 (66.7%) | Uncovered: 1

  Uncovered (sorted by severity):
    [MED ]  SEC-3 — Data Encryption
           → Consider creating a requirement or detailed-design
           run: specflow create --from-standard SEC-3
```

Each uncovered clause is a gap — add a `complies_with` link from an existing artifact, or create a new one. Re-run `specflow standards gaps` after each change to track progress. `specflow project-audit` reports the same coverage as one finding (`N/M clauses uncovered in <standard>`) as part of the full audit, and writes AUD/CHL artifacts unless run with `--dry-run`.

## Complete Example: Minimal Pack

A pack that adds clauses but no new artifact types — the simplest valid pack:

```
internal-policy/
├── pack.yaml
├── standards/internal-policy.yaml
└── README.md
```

**pack.yaml:**
```yaml
name: internal-policy
version: "1.0.0"
description: "Internal security policy — access control and audit requirements"
```

**standards/internal-policy.yaml:**
```yaml
standard: internal-policy
title: "Internal Security Policy"
version: "1.0.0"
clauses:
  - id: "POL-1"
    title: "Password Policy"
    description: "All user accounts shall enforce a minimum password length of 12 characters."
  - id: "POL-2"
    title: "Session Timeout"
    description: "Interactive sessions shall terminate after 15 minutes of inactivity."
  - id: "POL-3"
    title: "Access Review"
    description: "User access rights shall be reviewed quarterly by the account owner's manager."
```

**README.md:**
```markdown
# Internal Security Policy Pack

3 clauses covering password policy, session management, and access review.
Derived from the company security policy v1.0 (2024-01).
```

**After installing, link an artifact and audit:**
```yaml
# _specflow/specs/requirements/REQ-001.md
---
id: REQ-001
title: Authentication
type: requirement
status: approved
links:
  - target: "POL-1"
    role: complies_with
---
```

```bash
specflow standards gaps
# Standard: Internal Security Policy
#   Total: 3 clauses | Covered: 1 (33.3%) | Uncovered: 2
#   Uncovered (sorted by severity):
#     [MED ]  POL-2 — Session Timeout
#     [MED ]  POL-3 — Access Review
```
