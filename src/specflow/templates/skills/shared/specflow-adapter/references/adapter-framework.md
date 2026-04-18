# Adapter Framework Reference

## Architecture

SpecFlow's adapter framework uses a registry-based plugin system. Adapters are Python classes that inherit from `specflow.lib.adapters.base.Adapter` and declare which operations they support via `supported_operations`.

## Three Axes

| Axis | Methods | Purpose |
|------|---------|---------|
| **CI generation** | `generate_ci_workflow(ops)`, `get_hook_script()` | Generate CI workflow files and pre-commit hooks |
| **Artifact exchange** | `import_artifacts(source)`, `export_artifacts(dest)` | Import/export from external formats |
| **Standards ingestion** | `ingest_standard(source)` | Parse standards documents into pack format |

An adapter can implement any combination of these. The built-in GitHub Actions adapter only does CI; the built-in ReqIF adapter only does exchange.

## Built-in Adapters

### github-actions

- **Axis:** CI generation
- **Generates:** `.github/workflows/specflow.yml`
- **Operations:**
  - `artifact-lint` (always included — Pass 1: programmatic, Pass 2: LLM-judged opt-in)
  - `change-impact` (blast-radius review on PRs)
  - `project-audit` (full audit on push to main)
  - `release-gate` (gate check on tag pushes)
- **Hook:** Generates `.git/hooks/pre-commit` that delegates to `specflow hook pre-commit`

### reqif

- **Axis:** Artifact exchange
- **Direction:** Bidirectional (import and export)
- **Format:** ReqIF 1.2 XML
- **Round-trip:** Preserves DOORS/Polarion tool-specific attributes in `reqif_metadata` frontmatter field
- **Use case:** Interchange with DOORS, Polarion, and other ReqIF-compliant tools

## Configuration

All adapter configuration lives in `.specflow/adapters.yaml`:

```yaml
ci:
  provider: github-actions
  operations:
    - artifact-lint
    - change-impact
    - project-audit

exchange:
  - name: reqif
    provider: reqif
    direction: bidirectional

standards: []
```

### CI Section

| Field | Description |
|-------|-------------|
| `provider` | Adapter name from the registry |
| `operations` | List of CI operations to generate workflows for |

### Exchange Section

| Field | Description |
|-------|-------------|
| `name` | User-friendly name for this exchange configuration |
| `provider` | Adapter name from the registry |
| `direction` | `import`, `export`, or `bidirectional` |

### Standards Section

List of standards ingestion sources. Each entry has `name`, `source` (file path), and `provider` (adapter name).

## CLI Commands

| Command | What it does |
|---------|-------------|
| `specflow ci generate` | Reads adapters.yaml, generates CI workflow files |
| `specflow import --adapter <name> <file>` | Import via exchange adapter |
| `specflow export --adapter <name> --output <file>` | Export via exchange adapter |
| `specflow hook install` | Install pre-commit hook via CI adapter |

## Creating Custom Adapters

See `docs/authoring-an-adapter.md` for the full guide. Quick summary:

1. Create a Python class inheriting from `Adapter`
2. Set `name` and `supported_operations`
3. Override the methods you need
4. Decorate with `@register_adapter`
5. Import in `lib/adapters/__init__.py` to auto-register
6. Configure in `.specflow/adapters.yaml`

## CI Coexistence

SpecFlow generates its own dedicated workflow file (`.github/workflows/specflow.yml`) and does not modify any existing CI files. Multiple workflows coexist in the same repository. The generated workflow uses distinct job names (`specflow-pass-1`, `specflow-pass-2`, etc.) to avoid collisions.
