"""Tests for ``specflow done`` — output_files auto-capture on phase closure.

Covers Task-1 of the v1.13.0 orphan-code adoption arc:
  - ``capture_phase_output_files`` links phase source files to the right STORY
    via wave-commit message attribution.
  - Unattributable files (touched by non-wave commits in the phase window) are
    reported in the summary, never fatal.
  - ``done`` still exits 0 when git history is empty/absent or a STORY cannot
    be resolved (accounting-not-policing defensiveness).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml
import pytest

from specflow.commands import done as done_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib.orphans import (
    adopt_orphan_cluster,
    capture_phase_output_files,
    find_orphan_code,
    parse_wave_commit_stories,
)


# ── helpers ──────────────────────────────────────────────────────────────

def _bootstrap(tmp_path: Path) -> Path:
    """Minimal specflow project with a story schema + index, ready for git."""
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)

    pkg_schemas = (
        Path(__file__).parent.parent / "src" / "specflow" / "templates" / "schemas"
    )
    # story + requirement cover the existing done/capture tests; architecture
    # is included so STORY-624 adoption tests can create ARCH targets and run
    # create_artifact for the backfilled STORY through the real schema path.
    for name in ("story.yaml", "requirement.yaml", "architecture.yaml"):
        src = pkg_schemas / name
        assert src.exists(), f"missing template schema: {src}"
        (schema_dir / name).write_text(src.read_text(), encoding="utf-8")

    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "test", "created": "2026-01-01"}}),
        encoding="utf-8",
    )
    # state.yaml: current phase = executing, entered today so the since-window
    # covers the wave commits the tests create below.
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({
            "current": "executing",
            "history": [{"phase": "executing", "entered": "2026-01-02"}],
        }),
        encoding="utf-8",
    )

    stories_dir = root / "_specflow" / "work" / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    (stories_dir / "_index.yaml").write_text(
        "artifacts: {}\nnext_id: 1\n", encoding="utf-8"
    )
    # Architecture dir for STORY-624 adoption tests (ARCH targets are written
    # here; resolve_link_target finds them via rglob, so no index is required).
    (root / "_specflow" / "specs" / "architecture").mkdir(parents=True, exist_ok=True)
    return root


def _make_story(root: Path, sid: str, title: str = "Test story") -> Path:
    """Write a minimal discoverable STORY artifact."""
    path = root / "_specflow" / "work" / "stories" / f"{sid}.md"
    path.write_text(
        f"---\nid: {sid}\ntitle: {title}\ntype: story\nstatus: implemented\n"
        f"created: '2026-01-01'\nlinks: []\n---\n\n# {title}\n",
        encoding="utf-8",
    )
    return path


def _make_arch(root: Path, aid: str, title: str = "Adoption target") -> Path:
    """Write a minimal discoverable ARCH artifact (STORY-624 adoption target)."""
    path = root / "_specflow" / "specs" / "architecture" / f"{aid}.md"
    path.write_text(
        f"---\nid: {aid}\ntitle: {title}\ntype: architecture\nstatus: approved\n"
        f"created: '2026-01-01'\nlinks: []\n---\n\n# {title}\n",
        encoding="utf-8",
    )
    return path


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)


def _commit(root: Path, message: str, files: list[str]) -> None:
    """Stage the given relative files and commit with `message`."""
    for rel in files:
        subprocess.run(["git", "add", rel], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)


def _write(root: Path, rel: str, content: str = "x = 1\n") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


git_only = pytest.mark.skipif(shutil.which("git") is None, reason="git not available")


# ── pure unit: wave-commit subject parsing ───────────────────────────────

class TestParseWaveCommitStories:
    def test_parses_single_and_multiple(self):
        assert parse_wave_commit_stories(
            "specflow: wave 1 prepared [STORY-001]"
        ) == ["STORY-001"]
        assert parse_wave_commit_stories(
            "specflow: wave 2 prepared [STORY-001, STORY-002, STORY-003]"
        ) == ["STORY-001", "STORY-002", "STORY-003"]

    def test_ignores_non_wave_subjects(self):
        assert parse_wave_commit_stories("feat: add login") == []
        assert parse_wave_commit_stories("") == []
        assert parse_wave_commit_stories("specflow: wave 1") == []


# ── capture_phase_output_files ───────────────────────────────────────────

@git_only
class TestCapturePhaseOutputFiles:
    def test_links_files_to_owning_story_via_wave_commit(self, tmp_path: Path):
        """A source file touched by a wave commit is retro_linked to that
        commit's STORY id."""
        root = _bootstrap(tmp_path)
        _git_init(root)
        _make_story(root, "STORY-001")
        # initial commit so HEAD exists before the wave commit
        _write(root, "README.md", "# proj\n")
        _commit(root, "init", ["README.md"])

        src = _write(root, "src/app.py", "x = 1\n")
        _commit(
            root,
            "specflow: wave 1 prepared [STORY-001]",
            ["src/app.py"],
        )

        summary = capture_phase_output_files(root)
        assert summary["captured"] == 1
        assert summary["stories"] == 1
        assert summary["unattributed"] == 0

        # The STORY now lists the file in output_files.
        art = art_lib.parse_artifact(root / "_specflow" / "work" / "stories" / "STORY-001.md")
        assert "src/app.py" in (art.frontmatter.get("output_files") or [])

    def test_unattributable_files_reported_not_fatal(self, tmp_path: Path):
        """A source file touched by a NON-wave commit in the phase window is
        reported as unattributed; the call still succeeds and does not raise."""
        root = _bootstrap(tmp_path)
        _git_init(root)
        _make_story(root, "STORY-001")
        _write(root, "README.md", "# proj\n")
        _commit(root, "init", ["README.md"])

        _write(root, "src/linked.py", "x = 1\n")
        _commit(root, "specflow: wave 1 prepared [STORY-001]", ["src/linked.py"])
        _write(root, "src/manual.py", "y = 2\n")
        _commit(root, "chore: manual edit", ["src/manual.py"])

        summary = capture_phase_output_files(root)
        assert summary["captured"] == 1          # src/linked.py
        assert "src/manual.py" in summary["unattributed_files"]
        assert summary["unattributed"] == 1

    def test_no_git_repo_returns_zero_summary(self, tmp_path: Path):
        """Outside a git repo the capture is a no-op (never raises)."""
        root = _bootstrap(tmp_path)
        summary = capture_phase_output_files(root)
        assert summary["captured"] == 0
        assert summary["stories"] == 0
        assert summary["unattributed"] == 0

    def test_empty_history_returns_zero(self, tmp_path: Path):
        """A git repo with no commits in the phase window captures nothing."""
        root = _bootstrap(tmp_path)
        _git_init(root)
        _make_story(root, "STORY-001")
        summary = capture_phase_output_files(root)
        assert summary["captured"] == 0

    def test_unresolvable_story_does_not_raise(self, tmp_path: Path):
        """A wave commit naming a STORY that does not exist is skipped silently
        (the file is not captured, but the call exits cleanly)."""
        root = _bootstrap(tmp_path)
        _git_init(root)
        _write(root, "README.md", "# proj\n")
        _commit(root, "init", ["README.md"])
        _write(root, "src/app.py", "x = 1\n")
        # STORY-999 does not exist as an artifact.
        _commit(root, "specflow: wave 1 prepared [STORY-999]", ["src/app.py"])

        summary = capture_phase_output_files(root)  # must not raise
        assert summary["captured"] == 0

    def test_already_referenced_file_not_recounted(self, tmp_path: Path):
        """A file already in a STORY's output_files is not counted as a new capture."""
        root = _bootstrap(tmp_path)
        _git_init(root)
        path = _make_story(root, "STORY-001")
        # pre-link the file
        art = art_lib.parse_artifact(path)
        fm = art.frontmatter
        fm["output_files"] = ["src/app.py"]
        path.write_text(
            f"---\n{yaml.dump(fm, sort_keys=False)}---\n\n# body\n", encoding="utf-8"
        )
        _write(root, "README.md", "# proj\n")
        _commit(root, "init", ["README.md"])
        _write(root, "src/app.py", "x = 1\n")
        _commit(root, "specflow: wave 1 prepared [STORY-001]", ["src/app.py"])

        summary = capture_phase_output_files(root)
        assert summary["captured"] == 0  # already referenced


# ── done command integration ─────────────────────────────────────────────

@git_only
class TestDoneCommandCapture:
    def test_done_exits_0_without_git(self, tmp_path: Path, capsys):
        """`specflow done` exits 0 when there is no git history at all."""
        root = _bootstrap(tmp_path)
        # no git init, no commits
        rc = done_cmd.run(root, {"auto": True, "no_patterns": True})
        assert rc == 0

    def test_done_prints_capture_summary(self, tmp_path: Path, capsys):
        """When phase files are captured, done prints the summary line and
        still exits 0."""
        root = _bootstrap(tmp_path)
        _git_init(root)
        _make_story(root, "STORY-001", "Impl story")
        _write(root, "README.md", "# proj\n")
        _commit(root, "init", ["README.md"])
        _write(root, "src/app.py", "x = 1\n")
        _commit(root, "specflow: wave 1 prepared [STORY-001]", ["src/app.py"])

        rc = done_cmd.run(root, {"auto": False, "no_patterns": True})
        out = capsys.readouterr().out
        assert rc == 0
        assert "captured 1 output_file link(s)" in out


# ── STORY-624: orphan-code adoption closure ──────────────────────────────


class TestAdoptOrphanCluster:
    """STORY-624 Part 1: one-step adopt lands an un-adopted cluster under an
    ARCH with a backfilled STORY (tagged ``backfilled``), and coverage rises."""

    def test_adopts_cluster_into_arch_and_creates_backfilled_story(self, tmp_path: Path):
        root = _bootstrap(tmp_path)
        _make_arch(root, "ARCH-007")
        # Two orphan source files in one cluster.
        pkg = root / "src" / "legacy"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "a.py").write_text("x = 1\n", encoding="utf-8")
        (pkg / "b.py").write_text("y = 2\n", encoding="utf-8")

        summary = adopt_orphan_cluster(root, "ARCH-007")

        assert summary["ok"] is True
        assert summary["linked"] == 2
        assert summary["total_orphans"] == 2
        # Backfilled STORY created and traces to the ARCH.
        assert summary["story_id"] is not None
        assert summary["story_path"] is not None
        story = art_lib.parse_artifact(Path(summary["story_path"]))
        assert story is not None
        assert "backfilled" in (story.tags or [])
        assert story.status == "approved"
        links = story.links or []
        assert any(
            l.target == "ARCH-007" and l.role == "derives_from"
            for l in links
        )
        # The ARCH now carries both files in output_files.
        arch = art_lib.parse_artifact(
            root / "_specflow" / "specs" / "architecture" / "ARCH-007.md"
        )
        of = arch.frontmatter.get("output_files") or []
        assert "src/legacy/a.py" in of
        assert "src/legacy/b.py" in of

    def test_coverage_rises_after_adoption(self, tmp_path: Path):
        root = _bootstrap(tmp_path)
        _make_arch(root, "ARCH-001")
        pkg = root / "src" / "orphan"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "one.py").write_text("x = 1\n", encoding="utf-8")

        # Before adoption: the file is orphaned → 0% coverage.
        before = find_orphan_code(root)
        assert before["referenced_count"] == 0
        assert before["orphan_files"]

        summary = adopt_orphan_cluster(root, "ARCH-001")

        assert summary["ok"] is True
        assert summary["coverage_before"] == 0.0
        assert summary["coverage_after"] == 100.0
        # After adoption: no orphans remain.
        after = find_orphan_code(root)
        assert after["orphan_files"] == []
        assert after["referenced_count"] == 1

    def test_unknown_arch_target_returns_not_ok(self, tmp_path: Path):
        root = _bootstrap(tmp_path)
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "src" / "x.py").write_text("x = 1\n", encoding="utf-8")

        summary = adopt_orphan_cluster(root, "ARCH-999")

        assert summary["ok"] is False
        assert "not found" in summary.get("error", "").lower()
        assert summary["linked"] == 0
        # Coverage unchanged.
        assert summary["coverage_before"] == summary["coverage_after"]
        assert summary["story_id"] is None

    def test_no_orphans_still_succeeds_and_creates_story(self, tmp_path: Path):
        """When there is nothing to adopt, the call still succeeds; the ARCH
        gets no new output_files but the backfilled STORY is still created
        (accounting-not-policing: never raises)."""
        root = _bootstrap(tmp_path)
        _make_arch(root, "ARCH-010")

        summary = adopt_orphan_cluster(root, "ARCH-010")

        assert summary["ok"] is True
        assert summary["linked"] == 0
        assert summary["total_orphans"] == 0
        assert summary["story_id"] is not None

    def test_custom_story_title_used(self, tmp_path: Path):
        root = _bootstrap(tmp_path)
        _make_arch(root, "ARCH-002")
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "src" / "f.py").write_text("x = 1\n", encoding="utf-8")

        summary = adopt_orphan_cluster(
            root, "ARCH-002", story_title="Legacy payments adoption"
        )
        assert summary["ok"] is True
        story = art_lib.parse_artifact(Path(summary["story_path"]))
        assert story.title == "Legacy payments adoption"


class TestDetectAdoptCommand:
    """STORY-624 Part 1: the `detect orphan-code --adopt <ARCH>` command path
    prints the one-step summary and reports the coverage delta."""

    def test_adopt_command_path_prints_summary(self, tmp_path: Path, capsys):
        from specflow.commands import detect as detect_cmd

        root = _bootstrap(tmp_path)
        _make_arch(root, "ARCH-007")
        pkg = root / "src" / "legacy"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "a.py").write_text("x = 1\n", encoding="utf-8")

        rc = detect_cmd._run_orphan_code(root, {"adopt_target": "ARCH-007"})

        out = capsys.readouterr().out
        assert rc == 0
        assert "Adopting orphan cluster into ARCH-007" in out
        assert "Linked 1/1 orphan files to ARCH-007" in out
        assert "backfilled STORY" in out
        assert "derives_from ARCH-007" in out
        assert "Coverage:" in out
        assert "0.0%" in out  # before
        assert "100.0%" in out  # after

    def test_adopt_command_unknown_target_exits_nonzero(self, tmp_path: Path, capsys):
        from specflow.commands import detect as detect_cmd

        root = _bootstrap(tmp_path)
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "src" / "x.py").write_text("x = 1\n", encoding="utf-8")

        rc = detect_cmd._run_orphan_code(root, {"adopt_target": "ARCH-999"})
        out = capsys.readouterr().out
        assert rc == 1
        assert "not found" in out.lower()


class TestAdoptionArtifactLintClean:
    """STORY-624 AC: `artifact-lint --method programmatic` adds 0 blocking
    issues in a scaffolded project after adoption."""

    def test_lint_clean_after_adoption(self, tmp_path: Path, capsys):
        from specflow.commands import artifact_lint as lint_cmd

        root = _bootstrap(tmp_path)
        _make_arch(root, "ARCH-007")
        pkg = root / "src" / "legacy"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "a.py").write_text("x = 1\n", encoding="utf-8")

        adopt_orphan_cluster(root, "ARCH-007")

        rc = lint_cmd.run(root, {"method": "programmatic"})
        out = capsys.readouterr().out
        # 0 blocking issues → exit 0 and a PASS summary (warnings are allowed;
        # the AC gates on *blocking* issues only).
        assert rc == 0, f"artifact-lint reported blocking issues:\n{out}"
        assert "FAIL" not in out
        assert "PASS" in out
