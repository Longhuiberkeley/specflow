# P0: Foundation

## Goal

Ship a Python package (managed by uv) that provides the `specflow` CLI command to scaffold a valid SpecFlow project structure. No LLM-driven features yet — just the programmatic, filesystem foundation that everything else builds on.

## Deliverables

### 1. Python package structure

```
specflow/
├── pyproject.toml            # project metadata, dependencies, scripts
├── src/
│   └── specflow/
│       ├── __init__.py
│       ├── cli.py            # CLI entry point (typer or argparse)
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── init.py       # specflow init
│       │   └── status.py     # specflow status
│       ├── lib/
│       │   ├── __init__.py
│       │   ├── platform.py   # Platform detection logic
│       │   ├── scaffold.py   # Directory/file creation
│       │   └── config.py     # Config reading/writing
│       └── templates/
│           ├── config.yaml       # Default config template
│           ├── state.yaml        # Initial state template
│           ├── agents-section.md # SpecFlow section for AGENTS.md
│           ├── skills/           # Platform-specific skill facades
│           │   ├── gemini/
│           │   ├── claude/
│           │   └── opencode/
│           ├── schemas/          # All artifact type schemas
│           │   ├── requirement.yaml
│           │   ├── architecture.yaml
│           │   ├── detailed-design.yaml
│           │   ├── unit-test.yaml
│           │   ├── integration-test.yaml
│           │   ├── qualification-test.yaml
│           │   ├── story.yaml
│           │   ├── spike.yaml
│           │   ├── decision.yaml
│           │   └── defect.yaml
│           └── checklists/       # Checklist definitions (copied to .specflow/checklists/)
│               ├── phase-gates/  # Empty stubs, populated in P2
│               ├── in-process/   # Empty stubs, populated in P2
│               ├── review/       # Empty stubs, populated in P5
│               └── readiness/    # Empty stubs, populated in P2
├── scripts/                  # Validation & CRUD shell scripts (called by CLI, not copied to projects)
│   └── validate-schema.sh    # Minimal: validate YAML frontmatter
└── README.md
```

### 2. `specflow init` command

Programmatic setup command that runs once to initialize a project:
1. Detects platform (`.claude/` = Claude Code, `.opencode/` = OpenCode, `.gemini/` = Gemini CLI)
2. If no platform detected, asks user to select one
3. Asks which instruction file to append SpecFlow section to (AGENTS.md, CLAUDE.md, or other)
4. Creates `.specflow/` with config.yaml, state.yaml, schema/, checklists/ (from templates), empty impact-log/, empty checklist-log/, empty baselines/, empty locks/
5. Creates `_specflow/` with specs/ (6 directories, each with `_index.yaml` stub) and work/ (4 directories, each with `_index.yaml` stub)
6. Appends SpecFlow section to chosen instruction file
7. Copies platform-specific skill files from `src/specflow/templates/skills/` into the detected platform's skills directory
8. Installs standard Git `pre-commit` hooks to enforce link validation and impact analysis locally.

### 3. `.specflow/config.yaml` defaults

```yaml
project:
  name: ""                    # Set during init
  created: ""                 # Set during init

impact_analysis:
  auto_flag: true
  auto_resolve: false
  remind_after: 7d

artifact_types:
  - requirement
  - architecture
  - detailed-design
  - unit-test
  - integration-test
  - qualification-test
  - story
  - spike
  - decision
  - defect

active_packs: []              # Populated by --preset installs
```

### 4. `.specflow/state.yaml` initial state

```yaml
current: idle
history: []
created: ""                   # Set during init
```

### 5. Artifact schema definitions

Each schema in `.specflow/schema/` defines:
- Required frontmatter fields
- Optional frontmatter fields
- Allowed status values and transitions
- Allowed link roles
- ID prefix and format

Example (`requirement.yaml`):

```yaml
type: requirement
prefix: REQ
id_format: "REQ-\\d{3}(\\.\\d{1,3})?$"
required_fields: [id, title, type, status, created]
optional_fields: [priority, version, rationale, tags, suspect, fingerprint, links, upstream, checklists_applied, modified]
allowed_status:
  draft: []
  approved: [draft]
  implemented: [approved]
  verified: [implemented]
allowed_link_roles: [refined_by, verified_by, derives_from, complies_with]
```

### 6. `_index.yaml` stubs

Each artifact directory gets an `_index.yaml`:

```yaml
artifacts: {}
next_id: 1
```

### 7. AGENTS.md section content

The appended section explains:
- This project uses SpecFlow
- Where artifacts live (`_specflow/`)
- How to check status (`specflow status`)
- Brief command reference
- Not to manually edit `.specflow/` internals

## Acceptance Criteria

- [ ] `uv run specflow init` runs without error
- [ ] Platform is correctly detected or user is prompted
- [ ] `.specflow/` directory structure matches architecture.md
- [ ] `_specflow/` directory structure matches architecture.md (6 spec dirs + 4 work dirs)
- [ ] All 10 schema files are valid YAML
- [ ] AGENTS.md (or chosen file) has SpecFlow section appended without destroying existing content
- [ ] `specflow status` outputs: "Phase: idle | Artifacts: 0 | No issues"
- [ ] Running `specflow init` again prompts about overwriting the existing section
- [ ] `specflow validate` (or `validate-schema.sh`) passes on freshly scaffolded empty project

## Dependencies

None. This is the foundation phase.

## Verification Gate

Dogfooding Initialization:
- We immediately run `uv run specflow init` on the SpecFlow repository itself to initialize its own `.specflow/` and `_specflow/` directories.

## Estimated Effort

Small-medium. Mostly boilerplate and scaffolding logic. No LLM integration yet.