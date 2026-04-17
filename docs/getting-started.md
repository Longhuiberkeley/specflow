# Getting Started with SpecFlow

A transcript-style walkthrough from cold install to a complete discover→plan→execute cycle.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## 1. Install

```bash
uv tool install specflow
```

Verify:

```bash
$ specflow --help
```

You should see the command list grouped by workflow phase: Discover, Plan, Execute, Review, Release, CI, Recovery.

## 2. Initialize a project

In your project repository:

```bash
$ cd my-project
$ specflow init
```

This creates:

```
_specflow/
├── specs/
│   ├── requirements/    # REQ artifacts
│   ├── architecture/    # ARCH artifacts
│   ├── detailed-design/ # DDD artifacts
│   ├── unit-tests/      # UT artifacts
│   ├── integration-tests/  # IT artifacts
│   └── qualification-tests/ # QT artifacts
└── work/
    ├── stories/         # STORY artifacts
    ├── spikes/          # SPIKE artifacts
    └── decisions/       # DEC artifacts
.specflow/
├── schema/              # YAML schemas per artifact type
├── checklists/          # Phase-gate and review checklists
└── config.yaml          # Project configuration
```

## 3. Discover requirements

Use the `/specflow-discover` conversational skill to capture your first requirement. In your AI coding assistant (Claude, Cursor, etc.):

```
/specflow-discover
```

The skill will guide you through a progressive disclosure conversation to extract requirements and create REQ artifacts. Alternatively, create one manually:

```bash
$ specflow create --type requirement --title "User authentication via OAuth 2.0" --priority high
✓ Created REQ-001
  Path: _specflow/specs/requirements/REQ-001.md
```

For non-functional requirements, specify a category:

```bash
$ specflow create --type requirement \
    --title "Login response under 200ms" \
    --nfr-category performance \
    --priority high
```

## 4. Plan the work

Use the `/specflow-plan` conversational skill once requirements are approved:

```
/specflow-plan
```

This breaks approved REQs into architecture (ARCH), detailed design (DDD), and story (STORY) artifacts. The skill creates the V-model traceability links automatically.

To approve a requirement first:

```bash
$ specflow update REQ-001 --status approved
```

## 5. Execute stories

With stories planned and approved, run execution:

```bash
# See what will execute (dry run)
$ specflow go --dry-run

# Execute all approved stories
$ specflow go
```

The `/specflow-execute` conversational skill orchestrates this with subagents:

```
/specflow-execute
```

Stories are executed in dependency waves — independent stories run in parallel.

## 6. Verify and review

After implementation, run validation:

```bash
# Deterministic checks (zero tokens)
$ specflow artifact-lint

# Run a specific check
$ specflow artifact-lint --type coverage
$ specflow artifact-lint --type conflicts
$ specflow artifact-lint --type story-size

# Full review with LLM judgement
$ specflow artifact-review --all --depth normal
```

Available lint checks:

| Check | What it validates |
|-------|-------------------|
| `schema` | Required fields, ID format, status values |
| `links` | Link integrity, orphan detection, V-model pairs |
| `status` | Status lifecycle consistency |
| `ids` | ID uniqueness, format, dot-notation depth |
| `fingerprints` | Content fingerprint staleness |
| `acceptance` | REQs have acceptance criteria |
| `conflicts` | Cross-REQ constraint contradictions |
| `coverage` | REQ→STORY→test completeness |
| `story-size` | Story decomposition heuristics |

## 7. Check project status

At any point, see the current project state:

```bash
$ specflow status
```

This shows the current phase, artifact counts by status, and any flagged issues.

## 8. Finish a phase

When all stories in a phase are implemented:

```bash
$ specflow done
```

This closes the current phase and extracts prevention patterns for future work.

## Next steps

- Read the [lifecycle overview](lifecycle.md) to understand the full workflow
- Read the [command reference](commands.md) for all available commands and skills
- Run `specflow artifact-lint` regularly to keep artifacts healthy
- Use `specflow baseline create` to snapshot project state before major changes
