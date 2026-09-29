# Adapter Framework Reference

## Architecture

SpecFlow's adapters are configured in `.specflow/adapters.yaml`. Each names a provider and the operations it runs.

## Two Axes

| Axis | Methods | Purpose |
|------|---------|---------|
| **CI generation** | `generate_ci_workflow(ops)`, `get_hook_script()` | Generate CI workflow files and pre-commit hooks |
| **Artifact exchange** | `import_artifacts(source)`, `export_artifacts(dest)` | Import/export from external formats |

The built-in GitHub Actions adapter only does CI; the built-in ReqIF adapter only does exchange.

## Built-in Adapters

### github-actions

- **Axis:** CI generation
- **Generates:** `.github/workflows/specflow.yml`
- **Operations:**
  - `artifact-lint` — blocking (always included; fully deterministic, zero external API calls)
  - `ci-gate` — blocking (RBAC check on PRs)
  - `release-gate` — blocking (project-audit on tag pushes)
  - `change-impact` — advisory (blast-radius review on PRs; never fails the run)
  - `project-audit` — advisory (full audit on push to main; never fails the run)
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

```

### CI Section

| Field | Description |
|-------|-------------|
| `provider` | Adapter name (`github-actions`) |
| `operations` | List of CI operations to generate workflows for |

### Exchange Section

| Field | Description |
|-------|-------------|
| `name` | User-friendly name for this exchange configuration |
| `provider` | Adapter name (`reqif`) |
| `direction` | `import`, `export`, or `bidirectional` |

## CLI Commands

| Command | What it does |
|---------|-------------|
| `specflow ci generate` | Reads adapters.yaml, generates CI workflow files |
| `specflow import --adapter <name> <file>` | Import via exchange adapter |
| `specflow export --adapter <name> --output <file>` | Export via exchange adapter |
| `specflow hook install` | Install pre-commit hook via CI adapter |

## CI Coexistence

SpecFlow generates its own dedicated workflow file (`.github/workflows/specflow.yml`) and does not modify any existing CI files. Multiple workflows coexist in the same repository. The generated workflow uses distinct job names (`specflow-pass-1`, etc.) to avoid collisions.
