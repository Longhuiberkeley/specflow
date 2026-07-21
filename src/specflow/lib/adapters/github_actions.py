"""GitHub Actions CI adapter.

Generates CI workflows for declared operations:
  - artifact-lint (always included as base validation)
  - change-impact
  - project-audit
  - release-gate
  - ci-gate (RBAC)
  - pytest

SpecFlow is bootstrapped from its Git source on each run via ``uvx`` — the
consuming project does NOT need to declare specflow as a dependency, and
specflow is never resolved from PyPI (the public ``specflow`` name belongs to
an unrelated JSON-Schema library). The validation checks themselves remain
self-contained and deterministic: zero external API calls, zero tokens.

Also provides the default Bash hook script via ``get_hook_script()``.
"""

from __future__ import annotations

from pathlib import Path

from specflow.lib.adapters.base import Adapter, register_adapter


# Canonical Git source for SpecFlow (GitHub-only distribution; not on PyPI).
_SPECFLOW_REPO = "https://github.com/Longhuiberkeley/specflow"


def _specflow_source() -> str:
    """Git source ref used to bootstrap specflow in generated CI.

    Pinned to the running version (``git+<repo>@v<ver>``) so a consuming
    project's CI is reproducible; falls back to unpinned ``git+<repo>`` only if
    the version can't be determined. Uses ``specflow.__version__`` (the same
    source ``specflow --version`` uses) rather than ``importlib.metadata``,
    which can return ``None`` on a partially-installed checkout.
    """
    try:
        from specflow import __version__ as _ver

        if _ver:
            return f"git+{_SPECFLOW_REPO}@v{_ver}"
    except Exception:
        pass
    return f"git+{_SPECFLOW_REPO}"


# Canonical default hook script — Bash wrapper to the CLI. THIS IS THE SINGLE
# SOURCE OF TRUTH: ``get_hook_script()`` returns it, ``specflow hook install``'s
# fallback uses it, and ``specflow init`` writes it. It invokes bare ``specflow``
# (not ``uv run specflow``) so it works in a consuming project, where specflow is
# installed as a tool on PATH (``uv tool install git+...``) and is NOT a declared
# project dependency — the same reason generated CI uses ``uvx --from git+...``.
_DEFAULT_HOOK_SCRIPT = (
    "#!/usr/bin/env bash\n"
    "# specflow pre-commit hook — installed by `specflow hook install` or `specflow init`\n"
    "# Delegates to the Python CLI so the logic stays version-controlled.\n"
    "exec specflow hook pre-commit \"$@\"\n"
)

# YAML blocks for each job.  Using string templates to preserve
# the `${{ ... }}` GitHub Actions expressions that yaml.dump would quote.
#
# SpecFlow-only jobs bootstrap the tool from its Git source via `uvx`
# (`__SPECFLOW_SOURCE__` is substituted at generation time). They deliberately
# do NOT call `uv sync` / `uv run specflow`, because a consuming project does
# not declare specflow as a dependency and specflow is not installable from
# PyPI under that name. The `pytest` job is the exception: it needs the
# consuming project's own dependencies, so it keeps `uv sync`.

_PASS1 = """\
  specflow-pass-1:
    name: Pass 1 — programmatic validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Validate artifacts (deterministic, zero tokens)
        run: uvx --from __SPECFLOW_SOURCE__ specflow artifact-lint --method programmatic
"""

_CHANGE_IMPACT = """\
  specflow-change-impact:
    name: Change-impact review
    runs-on: ubuntu-latest
    needs: specflow-pass-1
    if: ${{ github.event_name == 'pull_request' }}
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Change-impact review
        run: uvx --from __SPECFLOW_SOURCE__ specflow change-impact || true
"""

_PROJECT_AUDIT = """\
  specflow-project-audit:
    name: Project audit
    runs-on: ubuntu-latest
    if: ${{ github.event_name == 'push' }}
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Project audit
        run: uvx --from __SPECFLOW_SOURCE__ specflow project-audit 2>&1 | tee audit-report.txt
      - name: Upload audit report
        uses: actions/upload-artifact@v4
        with:
          name: audit-report
          path: audit-report.txt
"""

_RELEASE_GATE = """\
  specflow-release-gate:
    name: Release gate
    runs-on: ubuntu-latest
    if: ${{ startsWith(github.ref, 'refs/tags/') }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Release gate check
        run: uvx --from __SPECFLOW_SOURCE__ specflow project-audit && echo "Release gate passed"
"""

_CI_GATE = """\
  specflow-ci-gate:
    name: CI gate (RBAC)
    runs-on: ubuntu-latest
    needs: specflow-pass-1
    if: ${{ github.event_name == 'pull_request' }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: RBAC gate check
        run: uvx --from __SPECFLOW_SOURCE__ specflow ci-gate --base ${{ github.base_ref }} --head ${{ github.head_ref }}
"""

_PYTEST = """\
  pytest:
    name: Run tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync
      - name: Run pytest
        run: uv run pytest tests/ -v
"""

_HEADER = """\
name: SpecFlow

on:
  pull_request:
  push:
    branches: [main, master]
    tags: ['v*']

# All SpecFlow CI checks are self-contained and deterministic — zero external API calls.
# SpecFlow is bootstrapped from its Git source (uvx --from git+...); the consuming
# project does not need to declare specflow as a dependency.

jobs:
"""

# Map of operation → YAML job block.
_OP_JOBS: dict[str, str] = {
    "change-impact": _CHANGE_IMPACT,
    "project-audit": _PROJECT_AUDIT,
    "release-gate": _RELEASE_GATE,
    "ci-gate": _CI_GATE,
    "pytest": _PYTEST,
}


@register_adapter
class GitHubActionsAdapter(Adapter):
    """Generate GitHub Actions CI workflows from config."""

    name = "github-actions"
    supported_operations = {"generate_ci_workflow", "get_hook_script"}

    def generate_ci_workflow(self, ops: list[str]) -> dict[Path, str]:
        """Generate a complete GitHub Actions workflow.

        Pass 1 (artifact-lint) is always included as the base validation layer.
        Additional operation jobs are appended based on the *ops* list.
        All checks are deterministic — no external API calls.

        SpecFlow-only jobs bootstrap the tool from its Git source via ``uvx``
        (substituted into each ``__SPECFLOW_SOURCE__`` sentinel), so the
        consuming project never has to declare specflow as a dependency.
        """
        ops_set = set(ops)
        parts = [_HEADER, _PASS1]

        for op in ops_set:
            if op == "artifact-lint":
                continue  # already in pass-1
            block = _OP_JOBS.get(op)
            if block:
                parts.append(block)

        rendered = "".join(parts).replace("__SPECFLOW_SOURCE__", _specflow_source())
        return {Path(".github/workflows/specflow.yml"): rendered}

    def get_hook_script(self) -> str:
        return _DEFAULT_HOOK_SCRIPT
