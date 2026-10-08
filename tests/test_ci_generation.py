"""Tests for GitHub Actions CI workflow generation.

Locks in the fixes for the CI bootstrap bug (example_bets-class failure): generated
specflow-only jobs must bootstrap specflow from its Git source
(``uvx --from git+...``) and must NOT use ``uv run specflow`` — which fails in a
clean CI runner because a consuming project does not declare specflow as a
dependency and specflow is not on PyPI. Also guards the ``change-impact --all``
regression and the ``pytest`` job's legitimate use of ``uv sync``.
"""

from __future__ import annotations

from pathlib import Path

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
    assert "specflow artifact-lint" in flat
    # F-085: `--method` is a no-op kept only for already-generated consumer CI.
    assert "--method" not in text


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
    assert "uvx --from git+" in text


def test_ci_gate_diffs_origin_base_against_pr_head_sha():
    # STORY-686 AC3: bare base_ref/head_ref are branch names that do not exist
    # as local refs in a PR checkout; the gate must diff origin/<base> against
    # the pull-request head sha (replaces the old head_ref assertion).
    text = _generate(["ci-gate"])
    runs = "\n".join(_job_runs(text)["specflow-ci-gate"])
    assert "--base origin/${{ github.base_ref }}" in runs
    assert "--head ${{ github.event.pull_request.head.sha }}" in runs
    assert "github.head_ref" not in text
    job = yaml.safe_load(text)["jobs"]["specflow-ci-gate"]
    assert "pull_request" in job["if"]


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
    # (which fails where specflow isn't a declared dependency — the example_bets bug
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


# ── Repo's own dogfood workflow (.github/workflows/specflow.yml) ──────────────
# The generator emits consumer jobs (uvx --from git+...). The repo itself is the
# specflow project, so it bootstraps with `uv sync` + `uv run specflow` instead.
# These tests pin the two dogfood jobs the generator emits for consumers
# (ci-gate, release-gate), adapted to the repo's own bootstrap.

_REPO_WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "specflow.yml"


def test_repo_workflow_has_ci_and_release_gates():
    assert _REPO_WORKFLOW.exists(), f"missing {_REPO_WORKFLOW}"
    data = yaml.safe_load(_REPO_WORKFLOW.read_text(encoding="utf-8"))
    jobs = data["jobs"]
    assert "specflow-ci-gate" in jobs
    assert "specflow-release-gate" in jobs


def test_repo_workflow_triggers_on_tags():
    data = yaml.safe_load(_REPO_WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML 1.1 parses the bare `on:` key as boolean True.
    triggers = data.get("on", data.get(True))
    push_cfg = triggers["push"]
    assert "v*" in push_cfg.get("tags", [])


def test_repo_ci_gate_pr_only_and_uses_github_refs():
    data = yaml.safe_load(_REPO_WORKFLOW.read_text(encoding="utf-8"))
    job = data["jobs"]["specflow-ci-gate"]
    assert "pull_request" in job["if"]
    runs = [s["run"] for s in job["steps"] if "run" in s]
    flat = "\n".join(runs)
    # Bootstraps from the repo itself (uv sync), not uvx.
    assert "uv sync" in flat
    assert "uv run specflow ci-gate" in flat
    # STORY-686 AC3: same ref form as the generated gate (was bare head_ref).
    assert "--base origin/${{ github.base_ref }}" in flat
    assert "--head ${{ github.event.pull_request.head.sha }}" in flat
    assert "github.head_ref" not in flat


def test_repo_release_gate_no_continue_on_error():
    # The release gate is the authoritative gate on tags — it must NOT carry
    # continue-on-error (safe now that accounting warns are excluded from exit 2).
    data = yaml.safe_load(_REPO_WORKFLOW.read_text(encoding="utf-8"))
    job = data["jobs"]["specflow-release-gate"]
    assert "refs/tags/" in job["if"]
    assert not job.get("continue-on-error", False)
    runs = [s["run"] for s in job["steps"] if "run" in s]
    flat = "\n".join(runs)
    assert "uv run specflow project-audit" in flat


def test_repo_workflow_release_gate_checks_tag_against_package_version():
    # F-058: a tag push must fail the release gate when the tag is not
    # `v<specflow --version>`.
    data = yaml.safe_load(_REPO_WORKFLOW.read_text(encoding="utf-8"))
    job = data["jobs"]["specflow-release-gate"]
    runs = "\n".join(s["run"] for s in job["steps"] if "run" in s)
    assert "GITHUB_REF_NAME" in runs
    assert "specflow --version" in runs
    # The version check precedes the audit so a mis-tagged push fails fast.
    names = [s.get("name", "") for s in job["steps"]]
    assert names.index("Tag matches package version") < names.index("Release gate check")


def test_repo_workflow_does_not_pass_method_flag():
    # F-085: `--method` is a no-op; neither the repo workflow nor the generator
    # should advertise it.
    assert "--method" not in _REPO_WORKFLOW.read_text(encoding="utf-8")


# ── `specflow ci generate` write safety (F-129) ──────────────────────────────

from specflow.commands import ci as ci_cmd  # noqa: E402


def _ci_project(tmp_path):
    root = tmp_path / "proj"
    (root / ".specflow").mkdir(parents=True)
    (root / ".specflow" / "adapters.yaml").write_text(
        "ci:\n  provider: github-actions\n  operations: [artifact-lint]\n", encoding="utf-8"
    )
    return root


def test_ci_generate_writes_new_file_then_reports_unchanged(tmp_path, capsys):
    root = _ci_project(tmp_path)
    assert ci_cmd.run(root, {"ci_subcommand": "generate"}) == 0
    wf = root / ".github" / "workflows" / "specflow.yml"
    assert wf.exists()
    assert "Wrote" in capsys.readouterr().out
    assert ci_cmd.run(root, {"ci_subcommand": "generate"}) == 0
    out = capsys.readouterr().out
    assert "unchanged" in out and "Wrote" not in out


def test_ci_generate_preserves_hand_edited_workflow_and_names_the_flags(tmp_path, capsys):
    root = _ci_project(tmp_path)
    wf = root / ".github" / "workflows" / "specflow.yml"
    wf.parent.mkdir(parents=True)
    wf.write_text("name: mine\n", encoding="utf-8")
    assert ci_cmd.run(root, {"ci_subcommand": "generate"}) == 0
    out = capsys.readouterr().out
    assert wf.read_text(encoding="utf-8") == "name: mine\n"
    assert "left as-is" in out
    assert "specflow ci generate --force" in out and "--dry-run" in out
    assert not (root / ".specflow" / "cache" / "backups").exists()


def test_ci_generate_dry_run_writes_nothing(tmp_path, capsys):
    root = _ci_project(tmp_path)
    assert ci_cmd.run(root, {"ci_subcommand": "generate", "dry_run": True}) == 0
    assert not (root / ".github").exists()
    assert "would be written" in capsys.readouterr().out
    wf = root / ".github" / "workflows" / "specflow.yml"
    wf.parent.mkdir(parents=True)
    wf.write_text("name: mine\n", encoding="utf-8")
    assert ci_cmd.run(root, {"ci_subcommand": "generate", "dry_run": True, "force": True}) == 0
    assert wf.read_text(encoding="utf-8") == "name: mine\n"
    out = capsys.readouterr().out
    assert "differs" in out
    # The warning promises a preview, so dry-run shows the unified diff.
    assert "--- .github/workflows/specflow.yml (existing)" in out
    assert "+++ .github/workflows/specflow.yml (generated)" in out
    assert "-name: mine" in out and "+name: SpecFlow" in out


def test_bounded_diff_caps_long_output():
    a = "\n".join(f"a{i}" for i in range(200))
    b = "\n".join(f"b{i}" for i in range(200))
    lines = ci_cmd._bounded_diff(a, b, "x.yml")
    assert len(lines) == ci_cmd._DIFF_LINE_LIMIT + 1
    assert lines[-1].startswith("... (") and lines[-1].endswith("more diff lines)")


def test_cli_ci_generate_accepts_dry_run_and_force(tmp_path, monkeypatch, capsys):
    """Parser wiring for the flags the preserve warning advertises (cli.py)."""
    from specflow import cli
    root = _ci_project(tmp_path)
    monkeypatch.chdir(root)
    assert cli.main(["ci", "generate", "--dry-run"]) == 0
    assert not (root / ".github").exists()
    wf = root / ".github" / "workflows" / "specflow.yml"
    wf.parent.mkdir(parents=True)
    wf.write_text("name: mine\n", encoding="utf-8")
    assert cli.main(["ci", "generate"]) == 0
    assert wf.read_text(encoding="utf-8") == "name: mine\n"
    assert cli.main(["ci", "generate", "--force"]) == 0
    assert wf.read_text(encoding="utf-8") != "name: mine\n"
    capsys.readouterr()


def test_ci_generate_force_backs_up_then_overwrites(tmp_path, capsys):
    root = _ci_project(tmp_path)
    wf = root / ".github" / "workflows" / "specflow.yml"
    wf.parent.mkdir(parents=True)
    wf.write_text("name: mine\n", encoding="utf-8")
    assert ci_cmd.run(root, {"ci_subcommand": "generate", "force": True}) == 0
    assert "specflow-pass-1" in wf.read_text(encoding="utf-8")
    backups = list((root / ".specflow" / "cache" / "backups").glob("*/ci/specflow.yml"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == "name: mine\n"
    assert "Backed up" in capsys.readouterr().out
