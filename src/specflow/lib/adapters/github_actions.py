"""GitHub Actions CI adapter.

Generates CI workflows for declared operations:
  - artifact-lint
  - change-impact
  - project-audit
  - release-gate

Also provides the default Bash hook script via `get_hook_script()`.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from specflow.lib.adapters.base import Adapter, register_adapter


# Default hook script — Bash wrapper to the CLI.
_DEFAULT_HOOK_SCRIPT = (
    "#!/usr/bin/env bash\n"
    "# specflow pre-commit hook — installed by `specflow hook install`\n"
    "# Delegates to the Python CLI so the logic stays version-controlled.\n"
    "exec uv run specflow hook pre-commit \"$@\"\n"
)

# YAML blocks for each job.  Using string templates to preserve
# the `${{ ... }}` GitHub Actions expressions that yaml.dump would quote.

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
      - name: Install SpecFlow
        run: uv sync
      - name: Validate artifacts (zero tokens)
        run: uv run specflow artifact-lint --method programmatic
"""

_PASS2 = """\
  specflow-pass-2:
    name: Pass 2 — LLM-judged review (opt-in)
    runs-on: ubuntu-latest
    needs: specflow-pass-1
    if: ${{ vars.SPECFLOW_LLM_CHECKS == 'true' }}
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Install SpecFlow
        run: uv sync
      - name: LLM-judged review
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: uv run specflow artifact-lint --method llm | tee llm-report.txt
      - name: Post PR comment
        if: ${{ github.event_name == 'pull_request' }}
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('llm-report.txt', 'utf8');
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '### SpecFlow Pass 2 (LLM-judged)\\n\\n```\\n' + body + '\\n```',
            });
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
      - name: Install SpecFlow
        run: uv sync
      - name: Change-impact review
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: uv run specflow change-impact --all || true
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
      - name: Install SpecFlow
        run: uv sync
      - name: Project audit
        run: uv run specflow project-audit 2>&1 | tee audit-report.txt
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
      - name: Install SpecFlow
        run: uv sync
      - name: Release gate check
        run: uv run specflow project-audit && echo "Release gate passed"
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
      - name: Install SpecFlow
        run: uv sync
      - name: RBAC gate check
        run: uv run specflow ci-gate --base ${{ github.base_ref }} --head ${{ github.head_ref }}
"""

_HEADER = """\
name: SpecFlow

on:
  pull_request:
  push:
    branches: [main, master]

jobs:
"""

# Map of operation → YAML job block.
_OP_JOBS: dict[str, str] = {
    "change-impact": _CHANGE_IMPACT,
    "project-audit": _PROJECT_AUDIT,
    "release-gate": _RELEASE_GATE,
    "ci-gate": _CI_GATE,
}


@register_adapter
class GitHubActionsAdapter(Adapter):
    """Generate GitHub Actions CI workflows from config."""

    name = "github-actions"
    supported_operations = {"generate_ci_workflow", "get_hook_script"}

    def generate_ci_workflow(self, ops: list[str]) -> dict[Path, str]:
        """Generate a complete GitHub Actions workflow.

        Pass 1 (artifact-lint) and Pass 2 (LLM review) are always included
        as the base validation layer. Additional operation jobs are appended
        based on the *ops* list.
        """
        ops_set = set(ops)
        parts = [_HEADER, _PASS1, _PASS2]

        for op in ops_set:
            if op == "artifact-lint":
                continue  # already in pass-1 / pass-2
            block = _OP_JOBS.get(op)
            if block:
                parts.append(block)

        rendered = "".join(parts)
        return {Path(".github/workflows/specflow.yml"): rendered}

    def get_hook_script(self) -> str:
        return _DEFAULT_HOOK_SCRIPT
