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
| `description` | Yes | One-line summary. This appears in `specflow init` output. |
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

You can add additional fields to clause objects if your standard requires them (e.g., `asil_level`, `severity`, `verification_method`). The compliance engine will include all fields in audit reports.

## Step 3: Define New Artifact Types (Optional)

If your standard requires tracking artifact types beyond the built-in ones (`requirement`, `story`, `test`, `hazard`, `decision`, `spike`, `defect`, `audit`, `challenge`), create a schema for each.

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
| `allowed_status` | Yes | Map of valid statuses to their allowed next statuses. |
| `directory` | Yes | `_specflow/specs/` subdirectory for this type's artifacts. |
| `optional_fields` | No | Additional fields that may appear. |
| `allowed_link_roles` | No | Valid link roles for `links:` entries. |

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

For a single project, manually copy the pack's content into the project's `.specflow/` internals:

```bash
# Copy standards
cp .specflow/packs/{name}/standards/*.yaml .specflow/standards/

# Copy schemas (if any)
cp .specflow/packs/{name}/schemas/*.yaml .specflow/schema/

# Create directories (if any)
mkdir -p _specflow/specs/{new-type}/
touch _specflow/specs/{new-type}/_index.yaml
echo "artifacts: {}" > _specflow/specs/{new-type}/_index.yaml
echo "next_id: 1" >> _specflow/specs/{new-type}/_index.yaml
```

Then update `.specflow/config.yaml` to register the new artifact types:

```yaml
active_packs:
  - {name}
artifact_types:
  - security-finding    # add your new types
```

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
