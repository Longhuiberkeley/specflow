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


# ---------------------------------------------------------------------------
# STORY-698: rename-proof independence and per-commit (upto) evaluation.
# ---------------------------------------------------------------------------

import os  # noqa: E402
import subprocess  # noqa: E402

from specflow.lib import git_utils  # noqa: E402


def _git(root: Path, *args: str, author: str = "alice@company.com") -> str:
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "x", "GIT_AUTHOR_EMAIL": author,
        "GIT_COMMITTER_NAME": "x", "GIT_COMMITTER_EMAIL": author,
    })
    return subprocess.run(
        ["git", *args], cwd=str(root), env=env,
        capture_output=True, text=True, check=True,
    ).stdout


def _req(root: Path, rel: str, rid: str, status: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"---\nid: {rid}\ntype: requirement\nstatus: {status}\n---\n\n"
        "# Lockout\n\nThe system shall lock an account after five failed logins\n"
        "within ten minutes and notify the owner by email when it engages.\n",
        encoding="utf-8",
    )


def _renamed_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "commit.gpgsign", "false")
    _team_config(root)
    draft = "_specflow/specs/requirements/REQ-FOO-ab12.md"
    _req(root, draft, "REQ-FOO-ab12", "implemented")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "draft", author="alice@company.com")
    final = "_specflow/specs/requirements/REQ-001.md"
    _git(root, "mv", draft, final)
    _req(root, final, "REQ-001", "implemented")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "renumber", author="bot@company.com")
    return root, final


class TestFileHistory:
    def test_follows_rename_oldest_first(self, tmp_path: Path):
        root, final = _renamed_repo(tmp_path)
        hist = git_utils.file_history(root, final, "HEAD")
        assert [h["author_email"] for h in hist] == ["alice@company.com", "bot@company.com"]
        assert hist[0]["change"] == "A" and hist[0]["old_path"] == ""
        assert hist[1]["change"] == "R"
        assert hist[1]["old_path"].endswith("REQ-FOO-ab12.md")
        assert hist[1]["new_path"] == final

    def test_without_follow_loses_pre_rename_history(self, tmp_path: Path):
        root, final = _renamed_repo(tmp_path)
        hist = git_utils.file_history(root, final, "HEAD", follow=False)
        assert [h["author_email"] for h in hist] == ["bot@company.com"]

    def test_unknown_ref_returns_none(self, tmp_path: Path):
        root, final = _renamed_repo(tmp_path)
        assert git_utils.file_history(root, final, "no-such-ref") is None


class TestCheckIndependenceHistory:
    def test_implementer_seen_across_rename(self, tmp_path: Path):
        root, final = _renamed_repo(tmp_path)
        ok, reason = rbac_lib.check_independence(root, final, "verified", "Alice@Company.com")
        assert not ok
        assert "Independence violation" in reason

    def test_upto_excludes_the_transition_commit_itself(self, tmp_path: Path):
        root, final = _renamed_repo(tmp_path)
        _req(root, final, "REQ-001", "verified")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "verify", author="bob@company.com")
        head = _git(root, "rev-parse", "HEAD").strip()
        ok, _ = rbac_lib.check_independence(root, final, "verified", "bob@company.com", upto=head)
        assert ok
        # A ref name resolves to the same commit.
        ok, _ = rbac_lib.check_independence(root, final, "verified", "bob@company.com", upto="HEAD")
        assert ok
        # Without upto, HEAD history includes bob's commit (pre-commit semantics).
        ok, _ = rbac_lib.check_independence(root, final, "verified", "bob@company.com")
        assert not ok
