"""Tests for specflow.lib.rbac — role resolution, authorization, independence."""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import rbac as rbac_lib


def _write_config(root: Path, team: dict) -> None:
    config_dir = root / ".specflow"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = {"team": team}
    (config_dir / "config.yaml").write_text(
        yaml.dump(config, default_flow_style=False), encoding="utf-8"
    )


def _solo_config(root: Path) -> None:
    _write_config(root, {"roles": {"reviewer": [], "approver": []}})


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


class TestResolveAuthorRoles:
    def test_solo_dev_no_roles(self, tmp_path: Path):
        _solo_config(tmp_path)
        roles = rbac_lib.resolve_author_roles(tmp_path, "alice@company.com")
        assert roles == []

    def test_assigned_role(self, tmp_path: Path):
        _team_config(tmp_path)
        roles = rbac_lib.resolve_author_roles(tmp_path, "carol@company.com")
        assert "approver" in roles

    def test_case_insensitive(self, tmp_path: Path):
        _team_config(tmp_path)
        roles = rbac_lib.resolve_author_roles(tmp_path, "Carol@Company.COM")
        assert "approver" in roles

    def test_no_role_assigned(self, tmp_path: Path):
        _team_config(tmp_path)
        roles = rbac_lib.resolve_author_roles(tmp_path, "eve@company.com")
        assert roles == []


class TestAuthorizeStatusTransition:
    def test_solo_dev_allowed(self, tmp_path: Path):
        _solo_config(tmp_path)
        ok, _ = rbac_lib.authorize_status_transition(
            tmp_path, "REQ-001", "approved", "alice@company.com"
        )
        assert ok

    def test_authorized_user(self, tmp_path: Path):
        _team_config(tmp_path)
        ok, _ = rbac_lib.authorize_status_transition(
            tmp_path, "REQ-001", "approved", "carol@company.com"
        )
        assert ok

    def test_unauthorized_user(self, tmp_path: Path):
        _team_config(tmp_path)
        ok, reason = rbac_lib.authorize_status_transition(
            tmp_path, "REQ-001", "approved", "bob@company.com"
        )
        assert not ok
        assert "approver" in reason

    def test_no_policy_for_status(self, tmp_path: Path):
        _team_config(tmp_path)
        ok, _ = rbac_lib.authorize_status_transition(
            tmp_path, "REQ-001", "draft", "bob@company.com"
        )
        assert ok


class TestCheckIndependence:
    def test_solo_dev_skipped(self, tmp_path: Path):
        _solo_config(tmp_path)
        ok, _ = rbac_lib.check_independence(
            tmp_path, "_specflow/specs/requirements/REQ-001.md",
            "verified", "alice@company.com",
        )
        assert ok

    def test_non_verification_status(self, tmp_path: Path):
        _team_config(tmp_path)
        ok, _ = rbac_lib.check_independence(
            tmp_path, "_specflow/specs/requirements/REQ-001.md",
            "approved", "bob@company.com",
        )
        assert ok
