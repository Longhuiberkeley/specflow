"""CLI-level test for 'specflow change-impact' report — QT-026 AC5.

Proves that the "Source File Impact" section renders in the report output
when a git commit modifies files that match an artifact's output_files entries
(reverse impact lookup).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml
import pytest

from specflow.commands import change_impact as change_impact_cmd


_SCHEMA_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"),
    ("defect", "DEF"),
]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"],
}


def _git_available() -> bool:
    return shutil.which("git") is not None


pytestmark = pytest.mark.skipif(not _git_available(), reason="git not installed")


def _run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command inside root and return the completed process."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(root),
        check=False,
    )


def _git_init(root: Path) -> None:
    _run_git(root, ["init"])
    _run_git(root, ["config", "user.email", "test@example.com"])
    _run_git(root, ["config", "user.name", "Test User"])
    # Disable any hooks or signing that could interfere
    _run_git(root, ["config", "commit.gpgsign", "false"])


def _git_commit_all(root: Path, msg: str) -> None:
    _run_git(root, ["add", "-A"])
    _run_git(root, ["commit", "-m", msg])


@pytest.fixture
def git_project_root(tmp_path: Path) -> Path:
    """A git repo with schemas, config, and artifact directories."""
    root = tmp_path / "project"
    root.mkdir(parents=True, exist_ok=True)

    _git_init(root)

    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "cache" / "backups").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "impact-log").mkdir(parents=True, exist_ok=True)

    for art_type, prefix in _SCHEMA_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(_STATUS_FLOW),
            "optional_fields": ["output_files"],
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    config = {
        "project": {"name": "test-project", "created": "2026-01-01", "domain": "", "domain_tags": []},
        "artifact_types": [t for t, _ in _SCHEMA_TYPES],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8"
    )

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/specs/detailed-design", "_specflow/specs/unit-tests",
        "_specflow/specs/integration-tests", "_specflow/specs/qualification-tests",
        "_specflow/work/stories", "_specflow/work/spikes",
        "_specflow/work/decisions", "_specflow/work/defects",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    # Initial commit so we have a HEAD
    _git_commit_all(root, "initial")

    return root


def _write_artifact(
    root: Path,
    artifact_id: str,
    art_type: str,
    title: str,
    extra_fm: dict | None = None,
) -> Path:
    """Write a minimal artifact file."""
    from specflow.lib import artifacts as art_lib

    rel_dir = art_lib.TYPE_TO_DIR.get(art_type, "")
    target_dir = root / "_specflow" / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    fm: dict = {
        "id": artifact_id,
        "title": title,
        "type": art_type,
        "status": "approved",
        "tags": [],
        "suspect": False,
        "links": [],
    }
    if extra_fm:
        fm.update(extra_fm)

    fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    content = f"---\n{fm_yaml}---\n\n# {title}\n\nBody text.\n"
    file_path = target_dir / f"{artifact_id}.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


class TestChangeImpactSourceFileReport:
    """QT-026 AC5: the report shall include a section listing source file
    changes and their associated spec artifacts."""

    def test_source_file_impact_renders_for_literal_match(self, git_project_root: Path, capsys):
        """When a commit modifies a file listed in an artifact's output_files,
        the 'Source File Impact' section renders with the artifact ID."""
        root = git_project_root

        # Create an ARCH with output_files
        _write_artifact(
            root, "ARCH-050", "architecture", "Impact Arch",
            extra_fm={"output_files": ["src/lib/feature.py"]},
        )
        _git_commit_all(root, "add arch artifact")

        # Now create the source file and commit it
        src_file = root / "src" / "lib" / "feature.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("def feature():\n    pass\n", encoding="utf-8")
        _git_commit_all(root, "add source file")

        # Run change-impact — should detect the source file change and match it
        rc = change_impact_cmd.run(root, {"artifact_id": None, "resolve": None, "flag": False})
        assert rc == 0

        out = capsys.readouterr().out
        assert "Source File Impact" in out
        assert "ARCH-050" in out
        assert "src/lib/feature.py" in out
        # The hint to flag should appear (we didn't pass --flag)
        assert "specflow change-impact --flag" in out

    def test_source_file_impact_with_flag_flags_suspect(self, git_project_root: Path, capsys):
        """With --flag, the Source File Impact section flags matched artifacts as suspect."""
        root = git_project_root

        _write_artifact(
            root, "ARCH-051", "architecture", "Flag Arch",
            extra_fm={"output_files": ["src/core/engine.py"]},
        )
        _git_commit_all(root, "add arch")

        src_file = root / "src" / "core" / "engine.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("class Engine: pass\n", encoding="utf-8")
        _git_commit_all(root, "add engine")

        rc = change_impact_cmd.run(root, {"artifact_id": None, "resolve": None, "flag": True})
        assert rc == 0

        out = capsys.readouterr().out
        assert "Source File Impact" in out
        assert "ARCH-051" in out
        assert "flagged" in out.lower()

        # Verify the artifact was actually flagged
        from specflow.lib import artifacts as art_lib
        art = art_lib.parse_artifact(
            root / "_specflow" / "specs" / "architecture" / "ARCH-051.md"
        )
        assert art is not None
        assert art.suspect is True

    def test_source_file_impact_multiple_artifacts(self, git_project_root: Path, capsys):
        """When a commit modifies files governed by different artifacts,
        each affected artifact appears in the report."""
        root = git_project_root

        _write_artifact(
            root, "ARCH-060", "architecture", "Arch A",
            extra_fm={"output_files": ["src/module_a.py"]},
        )
        _write_artifact(
            root, "DDD-060", "detailed-design", "DDD A",
            extra_fm={"output_files": ["src/module_b.py"]},
        )
        _git_commit_all(root, "add artifacts")

        # Modify both files in one commit
        for path in ["src/module_a.py", "src/module_b.py"]:
            f = root / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"# {path}\n", encoding="utf-8")
        _git_commit_all(root, "modify both modules")

        rc = change_impact_cmd.run(root, {"artifact_id": None, "resolve": None, "flag": False})
        assert rc == 0

        out = capsys.readouterr().out
        assert "Source File Impact" in out
        assert "ARCH-060" in out
        assert "DDD-060" in out

    def test_no_source_file_impact_when_no_match(self, git_project_root: Path, capsys):
        """When a commit modifies files not in any artifact's output_files,
        no Source File Impact section appears."""
        root = git_project_root

        _write_artifact(
            root, "ARCH-070", "architecture", "Safe Arch",
            extra_fm={"output_files": ["src/specific.py"]},
        )
        _git_commit_all(root, "add arch")

        # Modify a file that is NOT in any output_files
        other = root / "docs" / "unrelated.md"
        other.parent.mkdir(parents=True, exist_ok=True)
        other.write_text("# Unrelated\n", encoding="utf-8")
        _git_commit_all(root, "modify unrelated doc")

        rc = change_impact_cmd.run(root, {"artifact_id": None, "resolve": None, "flag": False})
        assert rc == 0

        out = capsys.readouterr().out
        # "Source File Impact" should NOT appear (no matches)
        assert "Source File Impact" not in out

    def test_source_file_impact_glob_match(self, git_project_root: Path, capsys):
        """When output_files has a glob pattern and a matching file is changed,
        the artifact appears in the report."""
        root = git_project_root

        _write_artifact(
            root, "ARCH-080", "architecture", "Glob Arch",
            extra_fm={"output_files": ["output/*_report.json"]},
        )
        _git_commit_all(root, "add glob arch")

        # Create a file matching the glob
        out_file = root / "output" / "2026_report.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text('{"data": 1}', encoding="utf-8")
        _git_commit_all(root, "add report")

        rc = change_impact_cmd.run(root, {"artifact_id": None, "resolve": None, "flag": False})
        assert rc == 0

        out = capsys.readouterr().out
        assert "Source File Impact" in out
        assert "ARCH-080" in out
        # The match type should indicate it was a glob match
        assert "glob" in out.lower()
