"""STORY-698 / SPIKE-004: the CI gate evaluates a PR's history, not its net diff.

Each test builds a throwaway git repository with distinct commit authors and
runs the real ``run_ci_gate`` / ``check_independence`` against it.

H1 PerStepLegality   — every consecutive status pair is legal in its schema.
H2 PerStepAuthority  — each transition is authorised for the commit that made it.
H3 IndependenceAcrossRename — renumber-drafts cannot erase implementer authorship.

DEF-002 (H1/H2) and DEF-003 (H3) were reproduced by these tests on the
pre-fix code.

A commit is a snapshot, not a CLI step: one commit may record several legal
steps (``cascade-status`` walks approved -> implemented -> verified in one
run). A commit's step is legal when a chain of single legal transitions
reaches it, and every policy-gated status on that chain is charged to the
commit's author.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

from specflow.commands import hook as hook_cmd
from specflow.lib import rbac as rbac_lib

ALICE = "alice@company.com"  # implementer / developer (no role)
BOB = "bob@company.com"  # reviewer
CAROL = "carol@company.com"  # approver
RENUMBER_BOT = "bot@company.com"

REQ_DIR = "_specflow/specs/requirements"

_REQ_SCHEMA = {
    "type": "requirement",
    "prefix": "REQ",
    "allowed_status": {
        "draft": [],
        "approved": ["draft"],
        "implemented": ["approved"],
        "verified": ["implemented"],
        "cancelled": ["draft", "approved", "implemented", "verified"],
    },
}


def _git(root: Path, *args: str, author: str | None = None) -> str:
    env = dict(os.environ)
    if author:
        name = author.split("@", 1)[0]
        env.update({
            "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": author,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": author,
        })
    res = subprocess.run(
        ["git", *args], cwd=str(root), env=env,
        capture_output=True, text=True, check=True,
    )
    return res.stdout


def _artifact_text(artifact_id: str, status: str, body: str = "") -> str:
    fm = {
        "id": artifact_id, "title": "Login must lock after five failures",
        "type": "requirement", "status": status, "created": "2026-09-30",
    }
    text = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n"
    text += f"# {fm['title']}\n\n"
    text += body or (
        "The system shall lock an account after five consecutive failed login\n"
        "attempts within ten minutes, and shall notify the account owner by\n"
        "email when the lock engages. Unlock requires either a password reset\n"
        "or thirty minutes elapsing without further failed attempts.\n"
    )
    return text


def _write(root: Path, rel: str, artifact_id: str, status: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_artifact_text(artifact_id, status), encoding="utf-8")


def _commit(root: Path, author: str, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message, author=author)
    return _git(root, "rev-parse", "HEAD").strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo with team RBAC configured and a requirement schema."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", ALICE)
    _git(root, "config", "user.name", "alice")
    _git(root, "config", "commit.gpgsign", "false")
    spec = root / ".specflow"
    (spec / "schema").mkdir(parents=True)
    (spec / "config.yaml").write_text(yaml.safe_dump({
        "team": {
            "roles": {"reviewer": [BOB], "approver": [CAROL]},
            "policy": {
                "transitions": {"approved": ["approver"], "verified": ["reviewer"]},
                "verification_statuses": ["verified"],
            },
        },
    }), encoding="utf-8")
    (spec / "schema" / "requirement.yaml").write_text(
        yaml.safe_dump(_REQ_SCHEMA, sort_keys=False), encoding="utf-8"
    )
    return root


def _gate(root: Path, base: str = "main", head: str = "HEAD") -> int:
    return hook_cmd.run_ci_gate(root, {"base": base, "head": head})


def _start_pr(root: Path, status: str = "draft") -> str:
    """Commit REQ-001 at ``status`` on main (by alice) and branch off."""
    _write(root, f"{REQ_DIR}/REQ-001.md", "REQ-001", status)
    _commit(root, ALICE, "spec: REQ-001")
    _git(root, "checkout", "-q", "-b", "feature")
    return f"{REQ_DIR}/REQ-001.md"


# ---------------------------------------------------------------------------
# H2 — per-commit authority
# ---------------------------------------------------------------------------


def test_h2_unauthorised_intermediate_approval_is_flagged(repo, capsys):
    """draft -> approved (by alice, no approver role) -> implemented -> verified
    (by bob). The net diff is draft -> verified by a reviewer; only the walk sees
    that alice approved her own requirement."""
    rel = _start_pr(repo)
    _write(repo, rel, "REQ-001", "approved")
    _commit(repo, ALICE, "approve")
    _write(repo, rel, "REQ-001", "implemented")
    _commit(repo, ALICE, "implement")
    _write(repo, rel, "REQ-001", "verified")
    _commit(repo, BOB, "verify")

    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 1
    assert f"author '{ALICE}' lacks required role for 'approved'" in out
    # The legitimate verification by bob is not blamed.
    assert f"'{BOB}' lacks" not in out
    assert "Independence violation" not in out


def test_h2_legitimate_multi_commit_pr_passes(repo, capsys):
    """Every step legal, each made by an authorised author, verifier never
    touched the file before: the gate passes. Pre-fix, the gate charged every
    transition to the OLDEST author (carol) and counted bob's own verifying
    commit as prior implementation."""
    rel = _start_pr(repo)
    _write(repo, rel, "REQ-001", "approved")
    _commit(repo, CAROL, "approve")
    _write(repo, rel, "REQ-001", "implemented")
    _commit(repo, ALICE, "implement")
    _write(repo, rel, "REQ-001", "verified")
    _commit(repo, BOB, "verify")

    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "All artifact status transitions pass RBAC checks" in out


def test_h2_newest_author_is_charged_not_oldest(repo, capsys):
    """An unrelated older commit by carol must not lend her approver role to
    alice's later approval."""
    _start_pr(repo)
    (repo / "notes.txt").write_text("unrelated\n", encoding="utf-8")
    _commit(repo, CAROL, "unrelated")
    _write(repo, f"{REQ_DIR}/REQ-001.md", "REQ-001", "approved")
    _commit(repo, ALICE, "approve")

    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 1
    assert f"author '{ALICE}' lacks required role for 'approved'" in out


# ---------------------------------------------------------------------------
# H1 — per-step legality
# ---------------------------------------------------------------------------


def test_h1_single_commit_jump_charges_the_skipped_approval(repo, capsys):
    """draft -> implemented in one commit by alice passes through 'approved';
    no RBAC policy covers 'implemented', so only the walk of the legal chain
    finds that alice, who lacks the approver role, approved it."""
    rel = _start_pr(repo)
    _write(repo, rel, "REQ-001", "implemented")
    _commit(repo, ALICE, "jump")

    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 1
    assert f"author '{ALICE}' lacks required role for 'approved'" in out
    assert "passed through in one commit on 'draft' -> 'implemented'" in out


def test_h1_unreachable_status_in_one_commit_is_flagged(repo, capsys):
    """verified -> approved cannot be reached by any chain of legal steps."""
    rel = _start_pr(repo, status="verified")
    _write(repo, rel, "REQ-001", "approved")
    _commit(repo, CAROL, "reopen")

    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 1
    assert "REQ-001: illegal transition 'verified' -> 'approved'" in out


def test_h1_cascade_multi_step_commit_by_authorised_reviewer_passes(repo, capsys):
    """Regression: cascade-status (or two `update` calls) records approved ->
    implemented -> verified in ONE commit. bob holds the reviewer role, and
    'implemented' is not policy-gated, so the gate must pass."""
    rel = _start_pr(repo, status="approved")
    _write(repo, rel, "REQ-001", "verified")
    _commit(repo, BOB, "cascade-status: approved -> implemented -> verified")

    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "illegal transition" not in out


def test_h2_multi_step_commit_by_non_approver_through_approval_is_flagged(repo, capsys):
    """draft -> verified in one commit by bob (reviewer, not approver): the
    chain passes 'approved', which bob may not set."""
    rel = _start_pr(repo)
    _write(repo, rel, "REQ-001", "verified")
    _commit(repo, BOB, "one-shot")

    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 1
    assert f"author '{BOB}' lacks required role for 'approved'" in out


def test_h1_stuttering_illegal_intermediate_step_is_flagged(repo, capsys):
    """approved -> cancelled -> implemented: the net pair approved ->
    implemented is legal, the hidden cancelled -> implemented step is not."""
    rel = _start_pr(repo, status="approved")
    _write(repo, rel, "REQ-001", "cancelled")
    _commit(repo, ALICE, "cancel")
    _write(repo, rel, "REQ-001", "implemented")
    _commit(repo, ALICE, "resurrect")

    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 1
    assert "REQ-001: illegal transition 'cancelled' -> 'implemented'" in out
    assert "'approved' -> 'cancelled'" not in out


def test_solo_mode_stays_a_no_op(repo, capsys):
    """No roles configured: the gate passes even an illegal jump (solo-dev
    fast path is unchanged; artifact-lint / update own solo legality)."""
    (repo / ".specflow" / "config.yaml").write_text(
        yaml.safe_dump({"team": {"roles": {"reviewer": [], "approver": []}}}),
        encoding="utf-8",
    )
    _commit(repo, ALICE, "solo config")
    rel = _start_pr(repo)
    _write(repo, rel, "REQ-001", "verified")
    _commit(repo, ALICE, "jump")
    assert _gate(repo) == 0


def test_no_artifact_changes_message_is_stable(repo, capsys):
    _start_pr(repo)
    (repo / "notes.txt").write_text("x\n", encoding="utf-8")
    _commit(repo, ALICE, "notes")
    assert _gate(repo) == 0
    assert "No artifact status changes in this diff" in capsys.readouterr().out


def test_missing_refs_exit_code_is_stable(repo, capsys):
    assert hook_cmd.run_ci_gate(repo, {"base": "", "head": "HEAD"}) == 1
    assert "--base and --head refs are required" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# H3 — independence across renumber-drafts renames
# ---------------------------------------------------------------------------


def _renumbered_history(repo: Path) -> str:
    """alice authors and implements REQ-FOO-ab12.md; a bot renumbers it to
    REQ-001.md (git mv + id rewrite, as renumber-drafts does)."""
    draft_rel = f"{REQ_DIR}/REQ-FOO-ab12.md"
    _write(repo, draft_rel, "REQ-FOO-ab12", "draft")
    _commit(repo, ALICE, "draft")
    _write(repo, draft_rel, "REQ-FOO-ab12", "approved")
    _commit(repo, CAROL, "approve")
    _write(repo, draft_rel, "REQ-FOO-ab12", "implemented")
    _commit(repo, ALICE, "implement")
    final_rel = f"{REQ_DIR}/REQ-001.md"
    _git(repo, "mv", draft_rel, final_rel)
    _write(repo, final_rel, "REQ-001", "implemented")
    _commit(repo, RENUMBER_BOT, "renumber-drafts")
    return final_rel


def test_h3_check_independence_follows_renumber_rename(repo):
    final_rel = _renumbered_history(repo)
    ok, reason = rbac_lib.check_independence(repo, final_rel, "verified", ALICE)
    assert not ok
    assert "Independence violation" in reason
    # A genuine outsider is still allowed.
    ok, _ = rbac_lib.check_independence(repo, final_rel, "verified", BOB)
    assert ok


def test_h3_ci_gate_flags_implementer_verifying_renamed_artifact(repo, capsys):
    """alice also holds the reviewer role here, so only independence can stop
    her verifying the requirement she implemented under its draft id."""
    cfg_path = repo / ".specflow" / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cfg["team"]["roles"]["reviewer"] = [BOB, ALICE]
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    final_rel = _renumbered_history(repo)
    _git(repo, "checkout", "-q", "-b", "feature")
    _write(repo, final_rel, "REQ-001", "verified")
    _commit(repo, ALICE, "verify")

    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 1
    assert "Independence violation" in out
    assert ALICE in out


def test_h3_ci_gate_allows_outsider_verifying_renamed_artifact(repo, capsys):
    final_rel = _renumbered_history(repo)
    _git(repo, "checkout", "-q", "-b", "feature")
    _write(repo, final_rel, "REQ-001", "verified")
    _commit(repo, BOB, "verify")
    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 0, out


def test_rename_inside_pr_is_walked_across(repo, capsys):
    """A PR that renumbers and then (illegally) approves by a non-approver is
    still walked through the rename."""
    draft_rel = f"{REQ_DIR}/REQ-FOO-ab12.md"
    _write(repo, draft_rel, "REQ-FOO-ab12", "draft")
    _commit(repo, ALICE, "draft")
    _git(repo, "checkout", "-q", "-b", "feature")
    final_rel = f"{REQ_DIR}/REQ-001.md"
    _git(repo, "mv", draft_rel, final_rel)
    _write(repo, final_rel, "REQ-001", "draft")
    _commit(repo, RENUMBER_BOT, "renumber-drafts")
    _write(repo, final_rel, "REQ-001", "approved")
    _commit(repo, ALICE, "approve")

    rc = _gate(repo)
    out = capsys.readouterr().out
    assert rc == 1
    assert f"author '{ALICE}' lacks required role for 'approved'" in out


# ---------------------------------------------------------------------------
# CLI level — `specflow ci-gate` as a CI job runs it.
# ---------------------------------------------------------------------------


def _cli_gate(root: Path) -> subprocess.CompletedProcess[str]:
    import sys

    return subprocess.run(
        [sys.executable, "-m", "specflow", "ci-gate", "--base", "main", "--head", "HEAD"],
        cwd=str(root), capture_output=True, text=True, check=False,
    )


def test_cli_ci_gate_flags_hidden_approval_and_passes_clean_pr(repo):
    rel = _start_pr(repo)
    _write(repo, rel, "REQ-001", "approved")
    _commit(repo, ALICE, "approve")
    _write(repo, rel, "REQ-001", "implemented")
    _commit(repo, ALICE, "implement")
    _write(repo, rel, "REQ-001", "verified")
    _commit(repo, BOB, "verify")
    res = _cli_gate(repo)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "specflow ci-gate: RBAC check failed" in res.stdout
    assert f"author '{ALICE}' lacks required role for 'approved'" in res.stdout

    # Rewrite the PR so an approver approves: the same CLI run passes.
    _git(repo, "reset", "-q", "--hard", "main")
    _write(repo, rel, "REQ-001", "approved")
    _commit(repo, CAROL, "approve")
    _write(repo, rel, "REQ-001", "implemented")
    _commit(repo, ALICE, "implement")
    _write(repo, rel, "REQ-001", "verified")
    _commit(repo, BOB, "verify")
    res = _cli_gate(repo)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "All artifact status transitions pass RBAC checks" in res.stdout
