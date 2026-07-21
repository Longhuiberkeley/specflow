"""Tests for robust source scoping (lib.files.scan_source_files).

Covers the orphan-meter denominator fix:
  - .gitignore is respected automatically inside a git work tree
  - source_scope.include is an authoritative allowlist (bypasses extensions)
  - source_scope.exclude is a denylist subtracted last (committed non-code)
  - source_scope.extensions additively extends the code-extension heuristic
  - no config + no git falls back to the historical rglob walk
  - find_orphan_code keeps numerator/denominator on the same scope
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml
import pytest

from specflow.lib import artifacts as art_lib
from specflow.lib import files as files_lib
from specflow.lib import orphans as orphans_lib


def _write(root: Path, rel: str, content: str = "x") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _write_config(root: Path, source_scope: dict) -> None:
    cfg_dir = root / ".specflow"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.yaml").write_text(
        yaml.dump({"source_scope": source_scope}), encoding="utf-8"
    )


def _rel_names(root: Path, files: list[Path]) -> set[str]:
    return {str(f.resolve().relative_to(root.resolve())) for f in files}


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)


git_only = pytest.mark.skipif(shutil.which("git") is None, reason="git not available")


class TestScanSourceFiles:
    def test_no_config_no_git_uses_rglob(self, tmp_path: Path):
        """Outside a git repo with no config, behavior matches the historical walk:
        data-ish extensions (.json) still count as source."""
        _write(tmp_path, "src/app.py")
        _write(tmp_path, "data/raw/x.json")
        found = _rel_names(tmp_path, files_lib.scan_source_files(tmp_path))
        assert "src/app.py" in found
        assert "data/raw/x.json" in found  # historical (naive) behavior preserved

    @git_only
    def test_gitignore_is_respected(self, tmp_path: Path):
        _git_init(tmp_path)
        _write(tmp_path, "src/app.py")
        _write(tmp_path, "data/raw/x.json")
        _write(tmp_path, "data/raw/y.json")
        _write(tmp_path, ".gitignore", "data/\n")
        found = _rel_names(tmp_path, files_lib.scan_source_files(tmp_path))
        assert "src/app.py" in found
        assert not any(f.startswith("data/") for f in found)

    @git_only
    def test_untracked_uncommitted_code_still_counts(self, tmp_path: Path):
        """Brand-new, never-committed source must remain in scope (it is not
        ignored), so adoption work isn't hidden."""
        _git_init(tmp_path)
        _write(tmp_path, "src/brand_new.py")
        found = _rel_names(tmp_path, files_lib.scan_source_files(tmp_path))
        assert "src/brand_new.py" in found

    @git_only
    def test_include_allowlist_bypasses_extension_heuristic(self, tmp_path: Path):
        _git_init(tmp_path)
        _write(tmp_path, "src/app.py")
        _write(tmp_path, "weird/thing.foo")  # not a default source extension
        _write_config(tmp_path, {"include": ["weird/**/*.foo"]})
        found = _rel_names(tmp_path, files_lib.scan_source_files(tmp_path))
        assert found == {"weird/thing.foo"}  # only allowlisted; .foo honored

    @git_only
    def test_exclude_denylist_drops_committed_non_code(self, tmp_path: Path):
        _git_init(tmp_path)
        _write(tmp_path, "src/app.py")
        _write(tmp_path, "data/raw/x.json")  # committed (no .gitignore)
        _write_config(tmp_path, {"exclude": ["data/**"]})
        found = _rel_names(tmp_path, files_lib.scan_source_files(tmp_path))
        assert "src/app.py" in found
        assert not any(f.startswith("data/") for f in found)

    @git_only
    def test_extensions_additive(self, tmp_path: Path):
        _git_init(tmp_path)
        _write(tmp_path, "src/app.py")
        _write(tmp_path, "notebooks/explore.ipynb")  # not a default extension
        _write_config(tmp_path, {"extensions": [".ipynb"]})
        found = _rel_names(tmp_path, files_lib.scan_source_files(tmp_path))
        assert "src/app.py" in found
        assert "notebooks/explore.ipynb" in found

    @git_only
    def test_excluded_dirs_backstop_even_when_tracked(self, tmp_path: Path):
        """A committed node_modules/ must never count, regardless of git/config."""
        _git_init(tmp_path)
        _write(tmp_path, "src/app.py")
        _write(tmp_path, "node_modules/pkg/index.js")
        found = _rel_names(tmp_path, files_lib.scan_source_files(tmp_path))
        assert "src/app.py" in found
        assert not any(f.startswith("node_modules/") for f in found)


class TestDescribeSourceScope:
    @git_only
    def test_reports_configured_scope(self, tmp_path: Path):
        _git_init(tmp_path)
        _write_config(tmp_path, {"include": ["src/**/*.py"], "exclude": ["data/**"]})
        desc = files_lib.describe_source_scope(tmp_path)
        assert desc["include"] == ["src/**/*.py"]
        assert desc["exclude"] == ["data/**"]
        assert desc["gitignore_respected"] is True


class TestOrphanScopeConsistency:
    @git_only
    def test_denominator_excludes_gitignored_data(self, tmp_path: Path):
        _git_init(tmp_path)
        _write(tmp_path, "src/app.py")
        for i in range(20):
            _write(tmp_path, f"data/raw/{i}.json")
        _write(tmp_path, ".gitignore", "data/\n")
        result = orphans_lib.find_orphan_code(tmp_path)
        # Only src/app.py is in scope; the 20 data files are gone.
        assert result["total_count"] == 1

    def test_referenced_count_clamped_to_scope(self, tmp_path: Path, monkeypatch):
        """A declared output_file outside the scanned scope must not inflate the
        numerator past the denominator (coverage stays <= 100%)."""
        in_scope = _write(tmp_path, "src/app.py").resolve()
        out_of_scope = (tmp_path / "phantom.py").resolve()  # never scanned

        monkeypatch.setattr(
            orphans_lib, "_collect_referenced_files",
            lambda artifacts, root: {in_scope, out_of_scope},
        )
        result = orphans_lib.find_orphan_code(tmp_path)
        assert result["total_count"] == 1
        assert result["referenced_count"] == 1  # clamped: out_of_scope dropped
        assert result["referenced_count"] <= result["total_count"]


class TestCollectReferencedFilesBodyHeuristic:
    def test_inline_backtick_path_collected(self, tmp_path: Path):
        # Inline-prose citation "Code: `src/foo.py`" must count as a reference.
        # Previously only line-start backticks matched, so genuinely-traced
        # files were reported as orphans on real projects.
        src = _write(tmp_path, "src/foo.py").resolve()
        art = art_lib.Artifact(
            path=tmp_path / "_specflow/work/stories/STORY-001.md",
            frontmatter={"id": "STORY-001", "type": "story", "status": "approved"},
            body="Implementation lives in Code: `src/foo.py` — see there.",
        )
        referenced = orphans_lib._collect_referenced_files([art], tmp_path)
        assert src in referenced

    def test_nonexistent_backtick_token_ignored(self, tmp_path: Path):
        # A backtick token that is not a real file path is filtered by the
        # exists()+is_file() guard.
        _write(tmp_path, "src/real.py")
        art = art_lib.Artifact(
            path=tmp_path / "_specflow/work/stories/STORY-001.md",
            frontmatter={"id": "STORY-001", "type": "story", "status": "approved"},
            body="Set the `flag` then call `do_thing()`.",
        )
        referenced = orphans_lib._collect_referenced_files([art], tmp_path)
        assert referenced == set()
