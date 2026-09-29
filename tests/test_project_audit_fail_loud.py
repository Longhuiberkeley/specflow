"""STORY-683: project-audit lenses fail loud.

Pre-STORY-683 lens bodies were wrapped in ``try/except Exception: pass``: a
lens that crashed contributed NOTHING and the audit read as clean. Now every
cross-cutting lens runs through ``_run_lens``; an exception becomes ONE
blocking ``lens-error`` finding naming the lens (severity ``error`` → exit 3)
and the remaining lenses still run.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from specflow.commands import project_audit as audit_cmd
from specflow.lib import artifacts as art_lib


def _req(aid: str = "REQ-001") -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"{aid}.md"),
        frontmatter={"id": aid, "type": "requirement", "status": "approved"},
        body="",
        links=[],
    )


def _boom(*_a, **_k):
    raise RuntimeError("injected lens failure")


class TestLensErrorFinding:
    def test_raising_helper_lens_emits_lens_error_and_others_run(self, tmp_path, monkeypatch):
        monkeypatch.setattr(audit_cmd, "_verification_lens", _boom)
        results = audit_cmd._cross_cutting_analysis([_req()], tmp_path, drift_pair=[])
        errs = results["lens-error"]
        assert len(errs) == 1
        assert errs[0]["severity"] == "error"
        assert "verification" in errs[0]["message"]
        assert "RuntimeError" in errs[0]["message"]
        assert "injected lens failure" in errs[0]["message"]
        # Remaining lenses still ran.
        assert "nfr-coverage" in results
        assert "completeness" in results

    def test_raising_inline_lens_emits_lens_error(self, tmp_path, monkeypatch):
        import specflow.lib.orphans as orphans

        monkeypatch.setattr(orphans, "find_orphan_code", _boom)
        results = audit_cmd._cross_cutting_analysis([_req()], tmp_path, drift_pair=[])
        msgs = [f["message"] for f in results["lens-error"]]
        assert any("orphan-code" in m for m in msgs)
        assert "orphan-code" not in results

    def test_two_raising_lenses_each_reported(self, tmp_path, monkeypatch):
        monkeypatch.setattr(audit_cmd, "_ac_coverage_lens", _boom)
        monkeypatch.setattr(audit_cmd, "_ac_observability_lens", _boom)
        results = audit_cmd._cross_cutting_analysis([_req()], tmp_path, drift_pair=[])
        msgs = " ".join(f["message"] for f in results["lens-error"])
        assert "'ac-coverage'" in msgs
        assert "'ac-observability'" in msgs

    def test_lens_error_is_never_accounting(self):
        assert "lens-error" not in audit_cmd._ACCOUNTING_CONCERNS

    def test_run_exits_3_and_does_not_cache_lens_error(self, tmp_path, monkeypatch, capsys):
        root = tmp_path / "project"
        req_dir = root / "_specflow" / "specs" / "requirements"
        req_dir.mkdir(parents=True)
        (req_dir / "REQ-001.md").write_text(
            "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: draft\n"
            "tags: []\nsuspect: false\nlinks: []\n---\n\n# T\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(audit_cmd, "_nfr_coverage_lens", _boom)
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])
        rc = audit_cmd.run(root, {})
        out = capsys.readouterr().out
        assert rc == 3
        assert "ERRORS FOUND" in out
        # A crashed lens must not poison the findings cache.
        cache_dir = root / ".specflow" / "audits" / ".cache"
        assert list(cache_dir.glob("*.md")) == []


class TestNoSwallowingWrappers:
    def test_no_try_except_pass_around_lens_bodies(self):
        # AC3: no lens body keeps a try/except-pass wrapper.
        for fn in (
            audit_cmd._cross_cutting_analysis,
            audit_cmd._verification_lens,
            audit_cmd._ac_coverage_lens,
            audit_cmd._ac_observability_lens,
            audit_cmd._nfr_coverage_lens,
            audit_cmd._backfilled_exemption_lens,
        ):
            src = inspect.getsource(fn)
            assert "except Exception" not in src, fn.__name__


class TestFailLoudCli:
    @staticmethod
    def _project(root: Path) -> None:
        req_dir = root / "_specflow" / "specs" / "requirements"
        req_dir.mkdir(parents=True)
        (req_dir / "REQ-001.md").write_text(
            "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: draft\n"
            "tags: []\nsuspect: false\nlinks: []\n---\n\n# T\n",
            encoding="utf-8",
        )

    def test_cli_audit_raising_lens_exits_3_naming_lens(self, tmp_path, monkeypatch, capsys):
        from specflow import cli

        root = tmp_path / "proj"
        self._project(root)
        monkeypatch.setattr(audit_cmd, "_ac_coverage_lens", _boom)
        monkeypatch.chdir(root)
        rc = cli.main(["project-audit", "--dry-run"])
        out = capsys.readouterr().out
        assert rc == 3
        assert "ERRORS FOUND" in out

    def test_cli_lint_malformed_schema_exits_nonzero(self, tmp_path, monkeypatch, capsys):
        from specflow import cli

        root = tmp_path / "proj"
        self._project(root)
        schema_dir = root / ".specflow" / "schema"
        schema_dir.mkdir(parents=True)
        (schema_dir / "bad.yaml").write_text("type: x\nprefix: [X\n", encoding="utf-8")
        monkeypatch.chdir(root)
        rc = cli.main(["artifact-lint", "--type", "schema"])
        out = capsys.readouterr().out
        assert rc != 0
        assert "schema-error" in out and "bad.yaml" in out


class TestCacheKeyIsTotal:
    """Fix pass (STORY-683/684): the gen-6 cache key reads the source tree
    and docs surface before any lens runs. A config that makes those scans
    raise must become a named lens-error (exit 3), never a raw traceback."""

    @staticmethod
    def _project(root: Path, config: str) -> None:
        TestFailLoudCli._project(root)
        (root / ".specflow").mkdir(parents=True, exist_ok=True)
        (root / ".specflow" / "config.yaml").write_text(config, encoding="utf-8")

    def test_absolute_source_scope_exclude_is_lens_error(self, tmp_path, monkeypatch, capsys):
        from specflow import cli

        root = tmp_path / "proj"
        self._project(root, "source_scope:\n  exclude: ['/tmp/ignored/**']\n")
        monkeypatch.chdir(root)
        rc = cli.main(["project-audit", "--dry-run"])
        out = capsys.readouterr().out
        assert rc == 3
        assert "ERRORS FOUND" in out
        results = audit_cmd._cross_cutting_analysis([_req()], root, drift_pair=[])
        assert any("orphan-code" in f["message"] for f in results["lens-error"])

    def test_malformed_docs_block_is_lens_error(self, tmp_path, monkeypatch, capsys):
        from specflow import cli

        root = tmp_path / "proj"
        self._project(root, "docs: [docs/]\n")
        monkeypatch.chdir(root)
        rc = cli.main(["project-audit", "--dry-run"])
        out = capsys.readouterr().out
        assert rc == 3
        assert "ERRORS FOUND" in out
        results = audit_cmd._cross_cutting_analysis([_req()], root, drift_pair=[])
        assert any("docs-staleness" in f["message"] for f in results["lens-error"])

    def test_signature_marks_unavailable_inputs(self, tmp_path):
        root = tmp_path / "proj"
        self._project(root, "source_scope:\n  exclude: ['/tmp/ignored/**']\n")
        sig = audit_cmd._non_artifact_inputs_signature(root)
        assert "source=unavailable:" in sig
