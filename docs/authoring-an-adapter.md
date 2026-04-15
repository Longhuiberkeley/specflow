# Authoring a SpecFlow Adapter

SpecFlow's adapter framework replaces hardcoded integration paths with a single
config-driven dispatch system. An adapter is a Python class that inherits from
`specflow.lib.adapters.base.Adapter` and declares which operations it supports.

## The three axes

| Axis | Methods | Example adapters |
|------|---------|------------------|
| **CI generation** | `generate_ci_workflow()`, `get_hook_script()` | GitHub Actions, GitLab CI |
| **Artifact exchange** | `import_artifacts()`, `export_artifacts()` | ReqIF, Jira CSV |
| **Standards ingestion** | `ingest_standard()` | PDF parser, YAML importer |

An adapter can implement any combination of these. The built-in GitHub Actions
adapter only does CI; the built-in ReqIF adapter only does exchange.

## Minimal adapter

```python
# src/specflow/lib/adapters/my_adapter.py

from pathlib import Path
from typing import Any

from specflow.lib.adapters.base import Adapter, register_adapter


@register_adapter
class MyAdapter(Adapter):
    name = "my-adapter"
    supported_operations = {"generate_ci_workflow"}

    def generate_ci_workflow(self, ops: list[str]) -> dict[Path, str]:
        workflow = "# my CI workflow\n..."
        return {Path(".github/workflows/specflow.yml"): workflow}
```

The `@register_adapter` decorator adds the class to the global registry keyed
by `name`. Import your module in `lib/adapters/__init__.py` to auto-register it:

```python
import specflow.lib.adapters.my_adapter  # noqa: F401
```

## Adapter base class API

| Method | Default | Override when |
|--------|---------|---------------|
| `generate_ci_workflow(ops)` | raises `NotImplementedError` | Adapter can produce CI workflow files |
| `import_artifacts(source)` | raises `NotImplementedError` | Adapter can read an external format |
| `export_artifacts(dest)` | raises `NotImplementedError` | Adapter can write an external format |
| `ingest_standard(source)` | raises `NotImplementedError` | Adapter can parse a standards document |
| `get_hook_script()` | raises `NotImplementedError` | Adapter can provide a pre-commit hook script |

Only override the methods you declare in `supported_operations`. Callers check
`supported_operations` before invoking a method.

## Configuration

Adapters are configured via `.specflow/adapters.yaml`:

```yaml
ci:
  provider: my-adapter
  operations: [artifact-lint, change-impact]

exchange:
  - name: my-exchange
    provider: my-adapter
    direction: bidirectional

standards: []
```

Call `load_adapters_config(root)` to read this file. It falls back to sensible
defaults when the file is absent.

## CLI integration

Three CLI commands dispatch through adapters:

| Command | What it does |
|---------|-------------|
| `specflow ci generate` | Reads `adapters.yaml`, calls CI adapter's `generate_ci_workflow()` |
| `specflow import --adapter <name> <file>` | Calls exchange adapter's `import_artifacts()` |
| `specflow export --adapter <name> --output <file>` | Calls exchange adapter's `export_artifacts()` |
| `specflow hook install` | Calls CI adapter's `get_hook_script()` for the hook content |

## Worked example: GitLab CI adapter

```python
# src/specflow/lib/adapters/gitlab_ci.py

from pathlib import Path
from typing import Any

from specflow.lib.adapters.base import Adapter, register_adapter

_GITLAB_WORKFLOW = """\
stages:
  - validate
  - review

specflow-validate:
  stage: validate
  image: python:3.11
  script:
    - pip install uv
    - uv sync
    - uv run specflow artifact-lint --method programmatic
"""

_GITLAB_HOOK = """\
#!/usr/bin/env bash
# specflow pre-commit hook (GitLab variant)
exec uv run specflow hook pre-commit "$@"
"""


@register_adapter
class GitLabCIAdapter(Adapter):
    name = "gitlab-ci"
    supported_operations = {"generate_ci_workflow", "get_hook_script"}

    def generate_ci_workflow(self, ops: list[str]) -> dict[Path, str]:
        return {Path(".gitlab-ci.yml"): _GITLAB_WORKFLOW}

    def get_hook_script(self) -> str:
        return _GITLAB_HOOK
```

After adding this file and importing it in `__init__.py`, users switch providers
by editing `.specflow/adapters.yaml`:

```yaml
ci:
  provider: gitlab-ci
```

Running `specflow ci generate` then writes `.gitlab-ci.yml` instead of
`.github/workflows/specflow.yml`.

## Registry API

```python
from specflow.lib.adapters import get_adapter, ADAPTER_REGISTRY

# List all registered adapters
for name in ADAPTER_REGISTRY:
    print(name)

# Instantiate by name
adapter = get_adapter("github-actions")
```

## Testing your adapter

```python
from specflow.lib.adapters import get_adapter

adapter = get_adapter("my-adapter")

# Verify operations
assert "generate_ci_workflow" in adapter.supported_operations

# Generate workflow
files = adapter.generate_ci_workflow(["artifact-lint"])
for path, content in files.items():
    print(f"Would write {path}:\n{content}")
```

## Deferred: unified `/specflow-adapter` skill

A future Tier 1 conversational skill (`/specflow-adapter`) will wrap all
adapter operations behind a single interactive prompt. Tracked as a follow-up
to STORY-026.
