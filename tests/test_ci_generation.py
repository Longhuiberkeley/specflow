"""Tests for GitHub Actions CI workflow generation.

Locks in the fixes for the CI bootstrap bug (cs2_bet-class failure): generated
specflow-only jobs must bootstrap specflow from its Git source
(``uvx --from git+...``) and must NOT use ``uv run specflow`` — which fails in a
clean CI runner because a consuming project does not declare specflow as a
dependency and specflow is not on PyPI. Also guards the ``change-impact --all``
regression and the ``pytest`` job's legitimate use of ``uv sync``.
"""

from __future__ import annotations

import yaml

from specflow import __version__
from specflow.lib.adapters.github_actions import (
    GitHubActionsAdapter,
    _DEFAULT_HOOK_SCRIPT,
    _specflow_source,
)

REPO = "https://github.com/Longhuiberkeley/specflow"


def _generate(ops):
    """Render the workflow for the given ops and return its text."""
    return list(GitHubActionsAdapter().generate_ci_workflow(ops).values())[0]


def _job_runs(text):
    """Return {job_name: [run-command strings]} from rendered workflow text."""
    parsed = yaml.safe_load(text)
    out = {}
    for name, job in parsed["jobs"].items():
        out[name] = [step["run"] for step in job.get("steps", []) if "run" in step]
    return out


def test_specflow_source_is_version_pinned_git():
    # The bootstrap source must point at the Git repo, pinned to the running
    # version (reproducible CI). Not PyPI (the `specflow` name is unrelated).
    assert _specflow_source() == f"git+{REPO}@v{__version__}"


def test_no_sentinel_leftover():
    text = _generate(["artifact-lint", "change-impact", "project-audit"])
    assert "__SPECFLOW_SOURCE__" not in text


def test_specflow_only_jobs_never_use_uv_run():
    text = _generate(["artifact-lint", "change-impact", "project-audit"])
    runs = _job_runs(text)
    flat = "\n".join(r for run_list in runs.values() for r in run_list)
    # The consuming-project killer: no specflow invocation may rely on uv run.
    assert "uv run specflow" not in flat
    # Instead, every specflow command bootstraps from the Git source.
    assert f"uvx --from git+{REPO}@v{__version__}" in flat
    assert "specflow artifact-lint --method programmatic" in flat


def test_change_impact_has_no_all_flag():
    # The CLI has no `--all` for change-impact; it errored silently before.
    text = _generate(["change-impact"])
    assert "change-impact --all" not in text
    assert "specflow change-impact" in text  # bare form, matches dogfood workflow


def test_pytest_job_keeps_uv_sync():
    # pytest legitimately needs the consuming project's own deps.
    text = _generate(["pytest"])
    runs = _job_runs(text)
    assert "pytest" in runs
    pytest_runs = "\n".join(runs["pytest"])
    assert "uv sync" in pytest_runs
    assert "uv run pytest" in pytest_runs


def test_ci_gate_preserves_github_expressions():
    # The ${{ }} expressions must survive substitution (string replace, not
    # str.format) and the job must still bootstrap from git.
    text = _generate(["ci-gate"])
    assert "${{ github.base_ref }}" in text
    assert "${{ github.head_ref }}" in text
    assert "uvx --from git+" in text


def test_default_ops_produce_expected_jobs():
    text = _generate(["artifact-lint", "change-impact", "project-audit"])
    assert set(_job_runs(text)) == {
        "specflow-pass-1",
        "specflow-change-impact",
        "specflow-project-audit",
    }


def test_pass1_always_present():
    # Pass 1 (the hard gate) is included regardless of requested ops.
    text = _generate([])
    assert "specflow-pass-1" in _job_runs(text)


def test_hook_script_uses_bare_specflow():
    # The pre-commit hook installed into consuming projects must invoke bare
    # `specflow` (on PATH via `uv tool install git+...`), NOT `uv run specflow`
    # (which fails where specflow isn't a declared dependency — the cs2_bet bug
    # class). `_DEFAULT_HOOK_SCRIPT` is the single source of truth shared by
    # get_hook_script(), `specflow hook install`, and `specflow init`.
    script = GitHubActionsAdapter().get_hook_script()
    assert script == _DEFAULT_HOOK_SCRIPT
    assert "uv run specflow" not in script
    assert "exec specflow hook pre-commit" in script


def test_release_gate_fires_on_tags():
    # The release-gate job guards on `refs/tags/*`; the workflow MUST trigger on
    # tag pushes (a `tags:` filter), otherwise the job is unreachable dead code.
    text = _generate(["release-gate"])
    assert "tags: ['v*']" in text
    assert "specflow-release-gate" in _job_runs(text)
