"""v1.14.3 integration contracts — real CLI / real repo boundaries.

IT-043 (STORY-639): the role-target check runs clean on the REAL dogfood
repo via the actual CLI (exit 0, PASS, zero warnings) — the dogfood corpus
is a live regression fixture for the matrix.

IT-044 (STORY-640): the creation-status gate works through the full CLI
boundary (argparse → command → lib): rejected without --sanctioned (no
partial artifact), created-with-record with it.

IT-045 (STORY-641): the LIVE installed skill tree (.claude/skills) matches
the shipped templates byte-for-byte AND carries the approval gate — the
hardened guardrail assertions hold on the surface agents actually read.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(*argv: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "specflow", *argv],
        capture_output=True,
        text=True,
        cwd=str(cwd or _REPO_ROOT),
        timeout=120,
    )


class TestRoleTargetRealRepo:
    def test_dogfood_repo_runs_clean_via_cli(self):
        proc = _run_cli("artifact-lint", "--type", "role-target")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "PASS" in proc.stdout
        # Zero warnings: every direction-bearing link in the real corpus
        # points at an allowed target type.
        assert "warning" not in proc.stdout.lower().split("result:")[-1].split("(")[0].lower() or "0 warning" in proc.stdout


class TestCreationGateCliBoundary:
    def _project(self, tmp: Path) -> Path:
        root = tmp / "cli-proj"
        schema_dir = root / ".specflow" / "schema"
        schema_dir.mkdir(parents=True, exist_ok=True)
        (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
        (schema_dir / "story.yaml").write_text(
            yaml.dump(
                {
                    "type": "story",
                    "prefix": "STORY",
                    "directory": "_specflow/work/stories",
                    "allowed_status": {
                        "draft": [], "approved": ["draft"],
                        "implemented": ["approved"], "verified": ["implemented"],
                    },
                    "allowed_link_roles": ["implements"],
                }
            ),
            encoding="utf-8",
        )
        (root / ".specflow" / "config.yaml").write_text(
            yaml.dump(
                {
                    "project": {"name": "cli-gate", "created": "2026-01-01"},
                    "artifact_types": ["story"],
                    "active_packs": [],
                }
            ),
            encoding="utf-8",
        )
        (root / ".specflow" / "state.yaml").write_text(
            yaml.dump({"current": "idle", "history": []}), encoding="utf-8"
        )
        (root / "_specflow" / "work" / "stories").mkdir(parents=True, exist_ok=True)
        return root

    def test_rejected_without_sanction_no_partial_artifact(self, tmp_path: Path):
        root = self._project(tmp_path)
        proc = _run_cli(
            "create", "--type", "story", "--title", "T", "--status", "approved",
            "--skip-dedup-check",
            cwd=root,
        )
        assert proc.returncode == 1
        assert "--sanctioned" in proc.stdout
        assert not list((root / "_specflow" / "work" / "stories").glob("*.md"))

    def test_created_with_record_with_sanction(self, tmp_path: Path):
        root = self._project(tmp_path)
        proc = _run_cli(
            "create", "--type", "story", "--title", "T", "--status", "approved",
            "--sanctioned", "CLI integration contract run",
            "--skip-dedup-check",
            cwd=root,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        files = list((root / "_specflow" / "work" / "stories").glob("STORY-*.md"))
        assert len(files) == 1
        fm = yaml.safe_load(files[0].read_text(encoding="utf-8").split("---")[1])
        assert fm["status"] == "approved"
        assert fm["sanctioned_justification"] == "CLI integration contract run"


class TestLiveSkillTreeCarriesGate:
    def test_live_mirror_matches_templates(self):
        shared = _REPO_ROOT / "src/specflow/templates/skills/shared"
        live = _REPO_ROOT / ".claude/skills"
        for template in shared.rglob("*.md"):
            mirror = live / template.relative_to(shared)
            assert mirror.exists(), f"missing live mirror for {template.name}"
            assert template.read_bytes() == mirror.read_bytes(), (
                f"live mirror drifted from template: {mirror}"
            )

    def test_live_mutating_skills_state_the_rule(self):
        import re

        sys.path.insert(0, str(_REPO_ROOT))
        from tests.test_approval_guardrail import (
            TestSkillsCarryGuardrail,
            _has_approval_gate,
        )

        live = _REPO_ROOT / ".claude/skills"
        for skill in TestSkillsCarryGuardrail._MUTATING_SKILLS:
            text = (live / skill / "SKILL.md").read_text(encoding="utf-8").lower()
            assert _has_approval_gate(text), (
                f"live {skill}/SKILL.md lost the no-self-approval gate"
            )
        # re module import kept for clarity of the assertion surface
        assert re is not None
