"""Tests for `specflow rbac check` — RBAC introspection command.

Follows the config shape established in tests/test_rbac.py
(`.specflow/config.yaml` -> `team.roles` / `team.policy.transitions`).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml
import pytest

from specflow.commands import rbac_check as rbac_check_cmd


def _write_config(root: Path, team: dict) -> None:
    config_dir = root / ".specflow"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yaml").write_text(
        yaml.dump({"team": team}, default_flow_style=False), encoding="utf-8"
    )


def _team_config(root: Path) -> None:
    _write_config(root, {
        "roles": {
            "reviewer": ["bob@company.com"],
            "approver": ["carol@company.com"],
        },
        "policy": {
            "transitions": {
                "approved": ["approver"],
                "verified": ["reviewer"],
            },
            "verification_statuses": ["verified"],
        },
    })


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".specflow").mkdir(parents=True, exist_ok=True)
    return root


# The git-fallback test shells out to real git; skip cleanly when git is absent
# instead of erroring on FileNotFoundError. Mirrors test_source_scope.py /
# test_done.py, which guard every git-dependent test the same way.
git_only = pytest.mark.skipif(shutil.which("git") is None, reason="git not available")


class TestNoTeamConfig:
    def test_no_config_file_at_all(self, project_root: Path, capsys):
        rc = rbac_check_cmd.run(project_root, {})
        assert rc == 0
        out = capsys.readouterr().out
        assert "not active" in out.lower()
        assert "single-user mode" in out.lower()

    def test_empty_roles_is_solo_mode(self, project_root: Path, capsys):
        _write_config(project_root, {"roles": {"reviewer": [], "approver": []}})
        rc = rbac_check_cmd.run(project_root, {})
        assert rc == 0
        out = capsys.readouterr().out
        assert "not active" in out.lower()


class TestWithTeamConfig:
    def test_resolves_roles_from_explicit_email(self, project_root: Path, capsys):
        _team_config(project_root)
        rc = rbac_check_cmd.run(project_root, {"email": "carol@company.com"})
        assert rc == 0
        out = capsys.readouterr().out
        assert "carol@company.com" in out
        assert "approver" in out

    def test_no_roles_assigned_still_reports(self, project_root: Path, capsys):
        _team_config(project_root)
        rc = rbac_check_cmd.run(project_root, {"email": "eve@company.com"})
        assert rc == 0
        out = capsys.readouterr().out
        assert "eve@company.com" in out

    def test_allowed_transition_exits_zero(self, project_root: Path, capsys):
        _team_config(project_root)
        rc = rbac_check_cmd.run(
            project_root,
            {"email": "carol@company.com", "type": "REQ", "to_status": "approved"},
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "Allowed" in out

    def test_denied_transition_exits_nonzero(self, project_root: Path, capsys):
        _team_config(project_root)
        rc = rbac_check_cmd.run(
            project_root,
            {"email": "bob@company.com", "type": "REQ", "to_status": "approved"},
        )
        assert rc == 1
        out = capsys.readouterr().out
        assert "Denied" in out
        assert "approver" in out

    @git_only
    def test_falls_back_to_git_author_email(self, project_root: Path, capsys, monkeypatch):
        _team_config(project_root)
        subprocess.run(["git", "init"], cwd=project_root, capture_output=True, check=False)
        subprocess.run(
            ["git", "config", "user.email", "carol@company.com"],
            cwd=project_root, capture_output=True, check=False,
        )
        rc = rbac_check_cmd.run(project_root, {})
        assert rc == 0
        out = capsys.readouterr().out
        assert "carol@company.com" in out
        assert "approver" in out
