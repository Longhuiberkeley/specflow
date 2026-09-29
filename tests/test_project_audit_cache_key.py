"""STORY-684: the findings cache key covers non-artifact inputs.

Pre-STORY-684 ``_project_fingerprint`` hashed artifact signatures only, so an
edit to docs/, installed standards, baselines, schemas or the source tree
(orphan-code's input) replayed stale cross-cutting findings. Generation 6
folds a signature of each of those inputs (and the run mode) into the key.
"""

from __future__ import annotations

from pathlib import Path

from specflow.commands import project_audit as audit_cmd
from specflow.lib import artifacts as art_lib


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    req_dir = root / "_specflow" / "specs" / "requirements"
    req_dir.mkdir(parents=True)
    (req_dir / "REQ-001.md").write_text(
        "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: draft\n"
        "tags: []\nsuspect: false\nlinks: []\n---\n\n# T\n",
        encoding="utf-8",
    )
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("# Guide\n\nCites REQ-001.\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    return root


def _key(root: Path, **kw) -> str:
    arts = art_lib.discover_artifacts(root)
    return audit_cmd._project_fingerprint(arts, root, **kw)


class TestCacheKeyInputs:
    def test_generation_is_6(self):
        assert audit_cmd._CACHE_GENERATION == 6

    def test_unchanged_repo_reuses_key(self, tmp_path):
        root = _project(tmp_path)
        assert _key(root) == _key(root)

    def test_docs_edit_changes_key(self, tmp_path):
        root = _project(tmp_path)
        before = _key(root)
        (root / "docs" / "guide.md").write_text("# Guide\n\nNow cites REQ-002.\n", encoding="utf-8")
        assert _key(root) != before

    def test_new_doc_changes_key(self, tmp_path):
        root = _project(tmp_path)
        before = _key(root)
        (root / "docs" / "more.md").write_text("# More\n", encoding="utf-8")
        assert _key(root) != before

    def test_standards_change_changes_key(self, tmp_path):
        root = _project(tmp_path)
        before = _key(root)
        std = root / ".specflow" / "standards"
        std.mkdir(parents=True)
        (std / "iso.yaml").write_text("title: ISO\nclauses: []\n", encoding="utf-8")
        assert _key(root) != before

    def test_baselines_change_changes_key(self, tmp_path):
        root = _project(tmp_path)
        before = _key(root)
        bl = root / ".specflow" / "baselines"
        bl.mkdir(parents=True)
        (bl / "v1.0.yaml").write_text("name: v1.0\nartifacts: {}\n", encoding="utf-8")
        assert _key(root) != before

    def test_schema_change_changes_key(self, tmp_path):
        root = _project(tmp_path)
        before = _key(root)
        sd = root / ".specflow" / "schema"
        sd.mkdir(parents=True)
        (sd / "requirement.yaml").write_text("type: requirement\nprefix: REQ\n", encoding="utf-8")
        assert _key(root) != before

    def test_new_source_file_changes_key(self, tmp_path):
        root = _project(tmp_path)
        before = _key(root)
        (root / "src" / "new_mod.py").write_text("x = 1\n", encoding="utf-8")
        assert _key(root) != before

    def test_run_mode_is_part_of_key(self, tmp_path):
        root = _project(tmp_path)
        assert _key(root, mode="quick") != _key(root, mode="full")

    def test_artifact_only_call_still_supported(self):
        # Backward-compatible artifact-only form (no root): pure function.
        a = art_lib.Artifact(path=Path("a.md"), frontmatter={"id": "REQ-001", "type": "requirement"},
                             body="", links=[])
        assert audit_cmd._project_fingerprint([a]) == audit_cmd._project_fingerprint([a])


class TestCacheReuseEndToEnd:
    @staticmethod
    def _stub(monkeypatch):
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

    def test_docs_edit_invalidates_and_unchanged_reuses(self, tmp_path, monkeypatch, capsys):
        root = _project(tmp_path)
        self._stub(monkeypatch)
        audit_cmd.run(root, {})
        out1 = capsys.readouterr().out
        assert "reusing previous findings" not in out1

        audit_cmd.run(root, {})
        out2 = capsys.readouterr().out
        assert "reusing previous findings" in out2  # unchanged repo → reuse

        (root / "docs" / "guide.md").write_text("# Guide\n\nEdited.\n", encoding="utf-8")
        audit_cmd.run(root, {})
        out3 = capsys.readouterr().out
        assert "reusing previous findings" not in out3  # docs edit → recompute

    def test_quick_run_cache_not_replayed_by_full_run(self, tmp_path, monkeypatch, capsys):
        root = _project(tmp_path)
        self._stub(monkeypatch)
        audit_cmd.run(root, {"quick": True})
        capsys.readouterr()
        audit_cmd.run(root, {})
        out = capsys.readouterr().out
        assert "reusing previous findings" not in out
        assert "Running cross-cutting analysis" in out


class TestCacheKeyCli:
    def test_cli_docs_edit_recomputes(self, tmp_path, monkeypatch, capsys):
        from specflow import cli

        root = _project(tmp_path)
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])
        monkeypatch.chdir(root)
        cli.main(["project-audit"])
        capsys.readouterr()
        cli.main(["project-audit"])
        assert "reusing previous findings" in capsys.readouterr().out
        (root / "docs" / "guide.md").write_text("# Guide\n\nChanged.\n", encoding="utf-8")
        cli.main(["project-audit"])
        assert "reusing previous findings" not in capsys.readouterr().out
