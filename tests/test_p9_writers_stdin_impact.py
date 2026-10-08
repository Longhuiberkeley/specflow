"""v1.17.2 wave P-9 — writers, stdin and impact-log honesty (STORY-714).

Regression coverage, one class per finding:

  F-001  EOF-only stdin (</dev/null, empty closed pipe, agent harness) is not
         piped data: no "Stdin data ignored" warning, no hang on an idle pipe.
  F-017  ``update --set`` cannot rewrite identity/system keys (id, type,
         created, suspect); ``KEY=null`` removes the key; a no-op update says
         "No changes to apply" instead of "Updated".
  F-018  ``update --title`` / ``--set title=`` propagate to ``_index.yaml``.
  F-015  ``fingerprint-refresh`` on a current artifact writes nothing (no
         version bump, no impact-log event); non-integer versions tolerated.
  F-014  Events that flagged nothing never count as unresolved.
  F-021  Source File Impact is labelled with its commit and age, the --flag
         nudge only fires for a commit newer than the impact log, and long
         match lists are summarised.
  F-020  ``create`` dedup honours type aliases and proceeds non-interactively.
  F-097  ``create`` of a REQ/STORY without an AC section prints one hint.
  F-069  ``change-impact --resolve`` on a non-suspect is an advisory, exit 0.
  F-110  ``create --from-standard`` lists unreadable standards on a miss.
"""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from specflow.commands import change_impact as change_impact_cmd
from specflow.commands import create as create_cmd
from specflow.commands import fingerprint_refresh as fp_cmd
from specflow.commands import update as update_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import impact as impact_lib
from specflow.lib.stdin_probe import stdin_has_data

# ── fixtures ────────────────────────────────────────────────────────────

_SCHEMAS = {
    "requirement": {
        "prefix": "REQ",
        "allowed_status": {"draft": [], "approved": ["draft"],
                           "implemented": ["approved"]},
        "directory": "_specflow/specs/requirements",
        "required_fields": ["id", "title", "type", "status", "created"],
        "optional_fields": ["priority", "rationale", "tags", "suspect",
                            "owner", "notes", "output_files"],
    },
    "story": {
        "prefix": "STORY",
        "allowed_status": {"draft": [], "approved": ["draft"]},
        "directory": "_specflow/work/stories",
        "required_fields": ["id", "title", "type", "status", "created"],
        "optional_fields": ["tags", "output_files"],
    },
    "architecture": {
        "prefix": "ARCH",
        "allowed_status": {"draft": [], "approved": ["draft"]},
        "directory": "_specflow/specs/architecture",
        "required_fields": ["id", "title", "type", "status", "created"],
        "optional_fields": ["tags", "output_files"],
    },
}


def _scaffold(root: Path) -> Path:
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "impact-log").mkdir(parents=True, exist_ok=True)
    for art_type, spec in _SCHEMAS.items():
        (schema_dir / f"{art_type}.yaml").write_text(
            yaml.dump({"type": art_type, **spec}), encoding="utf-8",
        )
        (root / spec["directory"]).mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({
            "project": {"name": "t", "created": "2026-01-01"},
            "artifact_types": list(_SCHEMAS),
            "active_packs": [],
        }),
        encoding="utf-8",
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8",
    )
    return root


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    return _scaffold(tmp_path / "project")


def _create_args(**overrides) -> dict:
    args = {
        "type": "requirement", "title": "T", "status": None,
        "priority": None, "rationale": None, "tags": None, "links": None,
        "body": "b", "from_standard": None, "force": False,
        "skip_dedup_check": True, "nfr_category": None, "set_fields": None,
    }
    args.update(overrides)
    return args


def _make(root: Path, *, art_type: str = "requirement", title: str = "T",
          body: str = "b", **extra) -> art_lib.Artifact:
    rc = create_cmd.run(root, _create_args(type=art_type, title=title,
                                           body=body, **extra))
    assert rc == 0
    arts = art_lib.discover_artifacts(root, artifact_type=art_type)
    return [a for a in arts if a.title == title][-1]


def _reload(root: Path, art_id: str) -> art_lib.Artifact:
    art = art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))
    assert art is not None
    return art


def _index_entry(root: Path, art: art_lib.Artifact) -> dict:
    index = yaml.safe_load(
        (Path(art.path).parent / "_index.yaml").read_text(encoding="utf-8")
    )
    return index["artifacts"][art.id]


def _impact_events(root: Path) -> list[Path]:
    return sorted((root / ".specflow" / "impact-log").glob("*.yaml"))


# ── F-001: EOF-only stdin is not data ───────────────────────────────────

class TestStdinProbe:
    def test_closed_empty_pipe_is_not_data(self):
        read_fd, write_fd = os.pipe()
        os.close(write_fd)
        with os.fdopen(read_fd, "r") as stream:
            assert stdin_has_data(stream) is False

    def test_devnull_is_not_data(self):
        with open(os.devnull, "r") as stream:
            assert stdin_has_data(stream) is False

    def test_idle_open_pipe_does_not_block(self):
        read_fd, write_fd = os.pipe()
        stream = os.fdopen(read_fd, "r")
        try:
            assert stdin_has_data(stream) is False
        finally:
            os.close(write_fd)
            stream.close()

    def test_pipe_with_bytes_is_data_and_not_consumed(self):
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"BODY")
        os.close(write_fd)
        with os.fdopen(read_fd, "r") as stream:
            assert stdin_has_data(stream) is True
            assert stream.read() == "BODY"

    def test_stringio_fallback(self):
        assert stdin_has_data(io.StringIO("x")) is True
        assert stdin_has_data(io.StringIO("")) is False

    def test_none_and_closed_streams(self):
        assert stdin_has_data(io.StringIO("x").__class__()) is False
        closed = io.StringIO("x")
        closed.close()
        assert stdin_has_data(closed) is False


class TestUpdateStdinEof:
    def test_closed_empty_pipe_no_warning(self, project_root, capsys, monkeypatch):
        req = _make(project_root, body="precious")
        read_fd, write_fd = os.pipe()
        os.close(write_fd)
        with os.fdopen(read_fd, "r") as stream:
            monkeypatch.setattr(sys, "stdin", stream)
            rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                               "status": "approved"})
        out = capsys.readouterr().out
        assert rc == 0
        assert "Stdin data ignored" not in out
        assert _reload(project_root, req.id).status == "approved"

    def test_devnull_no_warning(self, project_root, capsys, monkeypatch):
        req = _make(project_root, body="precious")
        with open(os.devnull, "r") as stream:
            monkeypatch.setattr(sys, "stdin", stream)
            rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                               "title": "Renamed"})
        out = capsys.readouterr().out
        assert rc == 0
        assert "Stdin data ignored" not in out
        assert _reload(project_root, req.id).title == "Renamed"

    def test_idle_open_pipe_does_not_hang_or_warn(self, project_root, capsys, monkeypatch):
        req = _make(project_root, body="precious")
        read_fd, write_fd = os.pipe()
        stream = os.fdopen(read_fd, "r")
        monkeypatch.setattr(sys, "stdin", stream)
        try:
            rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                               "status": "approved"})
        finally:
            os.close(write_fd)
            stream.close()
        assert rc == 0
        assert "Stdin data ignored" not in capsys.readouterr().out

    def test_real_piped_body_with_flags_still_warns(self, project_root, capsys, monkeypatch):
        req = _make(project_root, body="precious")
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"PIPED BODY")
        os.close(write_fd)
        with os.fdopen(read_fd, "r") as stream:
            monkeypatch.setattr(sys, "stdin", stream)
            rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                               "status": "approved"})
        assert rc == 0
        assert "Stdin data ignored" in capsys.readouterr().out
        art = _reload(project_root, req.id)
        assert "precious" in art.body and "PIPED BODY" not in art.body

    def test_real_piped_body_only_replaces_body(self, project_root, monkeypatch):
        req = _make(project_root, body="old body")
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"NEW BODY")
        os.close(write_fd)
        with os.fdopen(read_fd, "r") as stream:
            monkeypatch.setattr(sys, "stdin", stream)
            rc = update_cmd.run(project_root, {"artifact_id": req.id})
        assert rc == 0
        assert "NEW BODY" in _reload(project_root, req.id).body

    def test_eof_only_and_no_fields_is_the_usage_error(self, project_root, capsys, monkeypatch):
        req = _make(project_root, body="old body")
        with open(os.devnull, "r") as stream:
            monkeypatch.setattr(sys, "stdin", stream)
            rc = update_cmd.run(project_root, {"artifact_id": req.id})
        assert rc == 1
        assert "No fields to update" in capsys.readouterr().out
        assert "old body" in _reload(project_root, req.id).body


class TestCreateStdinEof:
    def test_devnull_leaves_body_empty_without_crash(self, project_root, monkeypatch):
        with open(os.devnull, "r") as stream:
            monkeypatch.setattr(sys, "stdin", stream)
            rc = create_cmd.run(project_root, _create_args(title="Empty", body=""))
        assert rc == 0
        art = [a for a in art_lib.discover_artifacts(project_root) if a.title == "Empty"][0]
        assert art.body.strip() in ("", "# Empty")

    def test_real_piped_body_is_read(self, project_root, monkeypatch):
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"PIPED CREATE BODY")
        os.close(write_fd)
        with os.fdopen(read_fd, "r") as stream:
            monkeypatch.setattr(sys, "stdin", stream)
            rc = create_cmd.run(project_root, _create_args(title="Piped", body=""))
        assert rc == 0
        art = [a for a in art_lib.discover_artifacts(project_root) if a.title == "Piped"][0]
        assert "PIPED CREATE BODY" in art.body


# ── F-017: --set identity keys, null semantics, no-op honesty ────────────

class TestUpdateSetReservedKeys:
    @pytest.mark.parametrize("key,pointer", [
        ("id", "renumber-drafts"),
        ("type", "merge"),
        ("created", "create"),
        ("suspect", "change-impact --resolve"),
    ])
    def test_identity_and_system_keys_rejected(self, project_root, capsys, key, pointer):
        req = _make(project_root)
        before = Path(req.path).read_text(encoding="utf-8")
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": [f"{key}=X"]})
        out = capsys.readouterr().out
        assert rc == 1
        assert f"--set {key} is reserved" in out
        assert pointer in out
        assert Path(req.path).read_text(encoding="utf-8") == before

    def test_shared_identity_set_is_the_single_source(self):
        from specflow.commands import autoresearch as ar_cmd
        assert set(art_lib.IDENTITY_SET_KEYS) == {"id", "type", "created"}
        for key in art_lib.IDENTITY_SET_KEYS:
            assert key in update_cmd._RESERVED_SET_KEYS
            assert key in create_cmd._RESERVED_SET_KEYS
            assert key in ar_cmd._RESERVED_SET_HINTS

    def test_create_set_identity_keys_rejected(self, project_root, capsys):
        for key in ("id", "created"):
            rc = create_cmd.run(project_root, _create_args(
                title=f"bad {key}", set_fields=[f"{key}=X"]))
            assert rc == 1
            assert "reserved" in capsys.readouterr().out
        assert art_lib.discover_artifacts(project_root) == []


class TestUpdateSetNull:
    def test_null_removes_optional_key(self, project_root, capsys):
        req = _make(project_root, set_fields=["owner=alice"])
        assert _reload(project_root, req.id).frontmatter.get("owner") == "alice"
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": ["owner=null"]})
        assert rc == 0
        assert "✓ Updated" in capsys.readouterr().out
        assert "owner" not in _reload(project_root, req.id).frontmatter

    def test_null_on_absent_key_is_no_change(self, project_root, capsys):
        req = _make(project_root)
        before = Path(req.path).read_text(encoding="utf-8")
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": ["owner=null"]})
        out = capsys.readouterr().out
        assert rc == 0
        assert "No changes to apply" in out
        assert "✓ Updated" not in out
        assert Path(req.path).read_text(encoding="utf-8") == before

    @pytest.mark.parametrize("key", ["status", "title", "created"])
    def test_null_on_required_or_identity_key_rejected(self, project_root, capsys, key):
        req = _make(project_root)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": [f"{key}=null"]})
        out = capsys.readouterr().out
        assert rc == 1
        assert key in out
        assert _reload(project_root, req.id).frontmatter.get(key)

    def test_body_null_is_the_empty_body_noop(self, project_root):
        req = _make(project_root, body="precious")
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": ["body=null"],
                                           "status": "approved"})
        assert rc == 0
        art = _reload(project_root, req.id)
        assert "precious" in art.body and art.status == "approved"


class TestUpdateNoOpHonesty:
    def test_same_status_reapplied_reports_no_changes(self, project_root, capsys):
        req = _make(project_root)
        update_cmd.run(project_root, {"artifact_id": req.id, "status": "approved"})
        capsys.readouterr()
        text_before = Path(req.path).read_text(encoding="utf-8")
        rc = update_cmd.run(project_root, {"artifact_id": req.id, "status": "approved"})
        out = capsys.readouterr().out
        assert rc == 0
        assert "No changes to apply" in out
        assert "✓ Updated" not in out
        assert Path(req.path).read_text(encoding="utf-8") == text_before

    def test_stale_fingerprint_still_repaired(self, project_root, capsys):
        req = _make(project_root)
        path = Path(req.path)
        path.write_text(path.read_text(encoding="utf-8").replace(
            "fingerprint: sha256:", "fingerprint: sha256:deadbeef00"), encoding="utf-8")
        rc = update_cmd.run(project_root, {"artifact_id": req.id, "status": "draft"})
        assert rc == 0
        assert "✓ Updated" in capsys.readouterr().out
        from specflow.lib import lint as lint_lib
        assert lint_lib.validate_fingerprint(_reload(project_root, req.id))["match"]

    def test_library_none_kwarg_still_means_untouched(self, project_root):
        req = _make(project_root, set_fields=["owner=alice"])
        result = art_lib.update_artifact(project_root, req.id, owner=None, status="approved")
        assert result["ok"] and result.get("changed") is not False
        fm = _reload(project_root, req.id).frontmatter
        assert fm["owner"] == "alice" and fm["status"] == "approved"


# ── F-018: title propagates to _index.yaml ──────────────────────────────

class TestIndexTitleSync:
    def test_title_flag_updates_index(self, project_root):
        req = _make(project_root, title="Old title")
        assert _index_entry(project_root, req)["title"] == "Old title"
        rc = update_cmd.run(project_root, {"artifact_id": req.id, "title": "New title"})
        assert rc == 0
        assert _index_entry(project_root, req)["title"] == "New title"

    def test_set_title_updates_index(self, project_root):
        req = _make(project_root, title="Old title")
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": ["title=Set title"]})
        assert rc == 0
        assert _index_entry(project_root, req)["title"] == "Set title"
        assert _reload(project_root, req.id).title == "Set title"


# ── F-015: fingerprint-refresh on a current artifact is a no-op ─────────

class TestFingerprintRefreshNoOp:
    def test_current_artifact_untouched(self, project_root, capsys):
        req = _make(project_root)
        fm_before = _reload(project_root, req.id).frontmatter
        text_before = Path(req.path).read_text(encoding="utf-8")
        assert _impact_events(project_root) == []

        rc = fp_cmd.run(project_root, {"targets": [req.id]})
        out = capsys.readouterr().out
        assert rc == 0
        assert "already current" in out
        assert "Tweaked" not in out
        assert Path(req.path).read_text(encoding="utf-8") == text_before
        assert _reload(project_root, req.id).frontmatter.get("version") == fm_before.get("version")
        assert _impact_events(project_root) == []

    def test_stale_fingerprint_refresh_writes_minor_event_born_resolved(self, project_root, capsys):
        req = _make(project_root)
        path = Path(req.path)
        path.write_text(path.read_text(encoding="utf-8").replace(
            "fingerprint: sha256:", "fingerprint: sha256:deadbeef00"), encoding="utf-8")
        rc = fp_cmd.run(project_root, {"targets": [req.id]})
        assert rc == 0
        assert "Tweaked" in capsys.readouterr().out
        events = _impact_events(project_root)
        assert len(events) == 1
        data = yaml.safe_load(events[0].read_text(encoding="utf-8"))
        assert data["update_type"] == "minor"
        assert data["flagged_suspects"] == []
        assert data["resolved"] is True
        assert data["resolved_by"] == "system"

    def test_non_integer_version_tolerated(self, project_root):
        req = _make(project_root)
        path = Path(req.path)
        text = path.read_text(encoding="utf-8").replace(
            "fingerprint: sha256:", "version: '1.0'\nfingerprint: sha256:deadbeef00")
        path.write_text(text, encoding="utf-8")
        result = impact_lib.propagate_suspects(project_root, req.id, force_minor=True)
        assert result["ok"] and result["changed"]
        assert _reload(project_root, req.id).frontmatter["version"] == 1


# ── F-014: empty-flag events are never "unresolved" ─────────────────────

class TestChangeImpactUnresolvedFilter:
    def _run(self, root, capsys, **extra) -> str:
        rc = change_impact_cmd.run(root, {"artifact_id": None, "resolve": None,
                                          "flag": False, **extra})
        assert rc == 0
        return capsys.readouterr().out

    def test_minor_update_leaves_report_clean(self, project_root, capsys):
        req = _make(project_root)
        path = Path(req.path)
        path.write_text(path.read_text(encoding="utf-8").replace(
            "fingerprint: sha256:", "fingerprint: sha256:deadbeef00"), encoding="utf-8")
        assert fp_cmd.run(project_root, {"targets": [req.id]}) == 0
        capsys.readouterr()
        out = self._run(project_root, capsys)
        assert "No unresolved suspect flags" in out
        assert "Oldest unresolved flag" not in out

    def test_legacy_empty_flag_event_ignored_on_read(self, project_root, capsys):
        _make(project_root)
        (project_root / ".specflow" / "impact-log" / "2026-04-01T00-00-00Z_REQ-001.yaml").write_text(
            yaml.dump({
                "changed": "REQ-001", "change_type": "content_modified",
                "fingerprint_old": "a", "fingerprint_new": "b",
                "update_type": "minor", "flagged_suspects": [],
                "resolved": False, "timestamp": "2026-04-01T00:00:00Z",
            }), encoding="utf-8")
        out = self._run(project_root, capsys)
        assert "No unresolved suspect flags" in out
        assert "Oldest unresolved flag" not in out

    def test_real_flag_still_reported(self, project_root, capsys):
        req = _make(project_root, title="Upstream")
        arch = _make(project_root, art_type="architecture", title="Downstream",
                     links=f"{req.id}:refines")
        # Semantic change on the REQ: body edit + propagate.
        path = Path(req.path)
        path.write_text(path.read_text(encoding="utf-8").replace("\nb\n", "\nchanged\n"),
                        encoding="utf-8")
        result = impact_lib.propagate_suspects(project_root, req.id)
        assert result["ok"] and result["flagged_count"] == 1
        out = self._run(project_root, capsys)
        assert "Unresolved Suspect Flags" in out
        assert arch.id in out
        assert "Oldest unresolved flag" in out


# ── F-069: --resolve on a non-suspect is advisory ───────────────────────

class TestResolveNonSuspect:
    def test_advisory_exit_zero(self, project_root, capsys):
        req = _make(project_root)
        rc = change_impact_cmd.run(project_root, {"artifact_id": None,
                                                  "resolve": req.id, "flag": False})
        out = capsys.readouterr().out
        assert rc == 0
        assert "is not suspect" in out
        assert "Resolved suspect flag" not in out


# ── F-021: Source File Impact labelling, nudge and summary ──────────────

_git = shutil.which("git") is not None


def _run_git(root: Path, args: list[str]) -> None:
    subprocess.run(["git", *args], cwd=str(root), check=False, capture_output=True, text=True)


def _git_project(tmp_path: Path) -> Path:
    root = _scaffold(tmp_path / "gitproject")
    _run_git(root, ["init"])
    _run_git(root, ["config", "user.email", "t@example.com"])
    _run_git(root, ["config", "user.name", "T"])
    _run_git(root, ["config", "commit.gpgsign", "false"])
    _run_git(root, ["add", "-A"])
    _run_git(root, ["commit", "-m", "initial"])
    return root


def _write_arch_with_output(root: Path, art_id: str, src: str) -> None:
    path = root / "_specflow" / "specs" / "architecture" / f"{art_id}.md"
    path.write_text(
        "---\n" + yaml.dump({
            "id": art_id, "title": art_id, "type": "architecture",
            "status": "approved", "created": "2026-01-01", "tags": [],
            "suspect": False, "links": [], "output_files": [src],
        }, sort_keys=False) + "---\n\n# A\n\nBody.\n", encoding="utf-8")


@pytest.mark.skipif(not _git, reason="git not installed")
class TestSourceFileImpactLabel:
    def _report(self, root, capsys) -> str:
        rc = change_impact_cmd.run(root, {"artifact_id": None, "resolve": None, "flag": False})
        assert rc == 0
        return capsys.readouterr().out

    def _commit_source(self, root: Path, rel: str, msg: str) -> None:
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# {rel}\n", encoding="utf-8")
        _run_git(root, ["add", "-A"])
        _run_git(root, ["commit", "-m", msg])

    def test_header_names_commit_age_and_informational(self, tmp_path, capsys):
        root = _git_project(tmp_path)
        _write_arch_with_output(root, "ARCH-001", "src/a.py")
        _run_git(root, ["add", "-A"]); _run_git(root, ["commit", "-m", "arch"])
        self._commit_source(root, "src/a.py", "src")
        out = self._report(root, capsys)
        assert "Source File Impact" in out
        assert "(1 match(es)) — from last commit " in out
        assert "ago), informational" in out
        # Empty impact log: the commit is the newest thing, so the nudge fires.
        assert "specflow change-impact --flag" in out

    def test_nudge_suppressed_when_commit_predates_log(self, tmp_path, capsys):
        root = _git_project(tmp_path)
        _write_arch_with_output(root, "ARCH-001", "src/a.py")
        _run_git(root, ["add", "-A"]); _run_git(root, ["commit", "-m", "arch"])
        self._commit_source(root, "src/a.py", "src")
        # Later spec activity: an impact-log event newer than HEAD.
        (root / ".specflow" / "impact-log" / "2099-01-01T00-00-00Z_REQ-001.yaml").write_text(
            yaml.dump({
                "changed": "REQ-001", "change_type": "content_modified",
                "fingerprint_old": "a", "fingerprint_new": "b",
                "update_type": "minor", "flagged_suspects": [],
                "resolved": True, "resolved_by": "system",
                "timestamp": "2099-01-01T00:00:00Z",
            }), encoding="utf-8")
        out = self._report(root, capsys)
        assert "Source File Impact" in out
        assert "specflow change-impact --flag" not in out
        assert "predates the newest impact-log entry" in out

    def test_long_match_list_is_summarised(self, tmp_path, capsys):
        root = _git_project(tmp_path)
        n = change_impact_cmd._SOURCE_IMPACT_MAX_ARTIFACTS + 5
        for i in range(1, n + 1):
            _write_arch_with_output(root, f"ARCH-{i:03d}", f"src/m{i}.py")
        _run_git(root, ["add", "-A"]); _run_git(root, ["commit", "-m", "arch"])
        for i in range(1, n + 1):
            f = root / "src" / f"m{i}.py"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x\n", encoding="utf-8")
        _run_git(root, ["add", "-A"]); _run_git(root, ["commit", "-m", "src"])
        out = self._report(root, capsys)
        assert f"({n} match(es))" in out
        assert "… and 5 more artifact(s) (5 file match(es)) not listed" in out
        assert out.count("Artifact: ") == change_impact_cmd._SOURCE_IMPACT_MAX_ARTIFACTS


# ── F-020: dedup honours aliases and proceeds non-interactively ─────────

class TestCreateDedup:
    def _seed(self, root: Path) -> None:
        for title, tags in (("User login flow", "auth, login"),
                            ("Payment gateway integration", "billing")):
            assert create_cmd.run(root, _create_args(title=title, tags=tags)) == 0

    def test_alias_type_still_screened(self, project_root, capsys, monkeypatch):
        self._seed(project_root)
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        rc = create_cmd.run(project_root, _create_args(
            type="REQ", title="User login flow", tags="auth, login",
            skip_dedup_check=False))
        out = capsys.readouterr().out
        assert rc == 0
        assert "Possible duplicate" in out
        assert "REQ-001" in out

    def test_non_interactive_proceeds_exit_zero(self, project_root, capsys, monkeypatch):
        self._seed(project_root)
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        rc = create_cmd.run(project_root, _create_args(
            title="User login flow", tags="auth, login", skip_dedup_check=False))
        out = capsys.readouterr().out
        assert rc == 0
        assert "Possible duplicate" in out
        assert "non-interactive: proceeding" in out
        assert "Non-interactive mode cannot prompt" not in out
        assert "✓ Created REQ-003" in out

    def test_alias_type_creates_canonical_artifact(self, project_root):
        rc = create_cmd.run(project_root, _create_args(type="req", title="Alias"))
        assert rc == 0
        art = art_lib.discover_artifacts(project_root)[0]
        assert art.type == "requirement" and art.id == "REQ-001"

    def test_ops_skill_no_longer_teaches_skip_dedup(self):
        import specflow
        skill = (Path(specflow.__file__).parent / "packs" / "ops" / "skills"
                 / "specflow-ops" / "SKILL.md").read_text(encoding="utf-8")
        assert "--skip-dedup-check" not in skill


# ── F-097: AC convention stated at create time ──────────────────────────

class TestCreateAcHint:
    _AC = "Intro.\n\n## Acceptance Criteria\n\n1. Given x, when y, then z.\n"

    @pytest.mark.parametrize("art_type", ["requirement", "story"])
    def test_hint_when_ac_missing(self, project_root, capsys, art_type):
        rc = create_cmd.run(project_root, _create_args(type=art_type, title="No AC",
                                                       body="Just prose."))
        out = capsys.readouterr().out
        assert rc == 0
        assert "no '## Acceptance Criteria' section" in out
        assert "specflow update " in out and "--ac" in out
        assert out.count("Acceptance Criteria") == 1

    def test_no_hint_when_ac_present(self, project_root, capsys):
        rc = create_cmd.run(project_root, _create_args(title="With AC", body=self._AC))
        assert rc == 0
        assert "no '## Acceptance Criteria'" not in capsys.readouterr().out

    def test_no_hint_for_other_types(self, project_root, capsys):
        rc = create_cmd.run(project_root, _create_args(type="architecture", title="Arch",
                                                       body="Just prose."))
        assert rc == 0
        assert "Acceptance Criteria" not in capsys.readouterr().out


# ── F-110: unreadable standards surfaced on a --from-standard miss ──────

class TestCreateFromStandardUnreadable:
    def test_malformed_standard_listed(self, project_root, capsys):
        std_dir = project_root / ".specflow" / "standards"
        (std_dir / "broken.yaml").write_text("clauses: [unclosed", encoding="utf-8")
        rc = create_cmd.run(project_root, _create_args(type=None, title=None,
                                                       from_standard="C1"))
        out = capsys.readouterr().out
        assert rc == 1
        assert "Standard clause 'C1' not found" in out
        assert "standard 'broken' could not be read" in out


# ── F-017 fix pass: list-valued KEY=null removes the key (real CLI) ──────

def _cli(root: Path, monkeypatch, *argv: str) -> tuple[int, str]:
    from specflow import cli

    monkeypatch.chdir(root)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(list(argv))
    return code, buf.getvalue()


class TestUpdateSetNullListKeys:
    def test_tags_null_removes_key_from_file_and_index(self, project_root, monkeypatch):
        req = _make(project_root, tags="alpha,beta")
        assert _reload(project_root, req.id).tags == ["alpha", "beta"]
        assert _index_entry(project_root, req)["tags"] == ["alpha", "beta"]
        code, out = _cli(project_root, monkeypatch, "update", req.id, "--set", "tags=null")
        assert code == 0, out
        assert "✓ Updated" in out
        fm = _reload(project_root, req.id).frontmatter
        assert "tags" not in fm
        text = Path(req.path).read_text(encoding="utf-8")
        assert "tags:" not in text.split("---")[1]
        # The index mirrors the file (rebuild-index writes `tags: []` for an
        # untagged artifact): no stale tag values survive the removal.
        assert _index_entry(project_root, req)["tags"] == []

    def test_output_files_null_on_absent_key_is_no_change(self, project_root, monkeypatch):
        req = _make(project_root)
        assert "output_files" not in _reload(project_root, req.id).frontmatter
        before = Path(req.path).read_text(encoding="utf-8")
        code, out = _cli(project_root, monkeypatch, "update", req.id,
                         "--set", "output_files=null")
        assert code == 0, out
        assert "No changes to apply" in out
        assert "✓ Updated" not in out
        assert Path(req.path).read_text(encoding="utf-8") == before
        assert "output_files" not in _reload(project_root, req.id).frontmatter

    def test_output_files_null_removes_existing_key(self, project_root, capsys):
        req = _make(project_root, set_fields=['output_files=["src/a.py"]'])
        assert _reload(project_root, req.id).output_files == ["src/a.py"]
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": ["output_files=null"]})
        assert rc == 0
        assert "✓ Updated" in capsys.readouterr().out
        assert "output_files" not in _reload(project_root, req.id).frontmatter

    def test_links_null_names_the_dedicated_flags(self, project_root, capsys):
        req = _make(project_root)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": ["links=null"]})
        out = capsys.readouterr().out
        assert rc == 1
        assert "cannot be removed with --set" in out
        assert "--remove-link" in out
        assert "is required on this artifact" not in out

    @pytest.mark.parametrize("key,flag", [("status", "--status"), ("title", "--title")])
    def test_status_title_null_point_at_their_flag(self, project_root, capsys, key, flag):
        req = _make(project_root)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": [f"{key}=null"]})
        out = capsys.readouterr().out
        assert rc == 1
        assert flag in out


# ── F-014 fix pass: split/merge events are born resolved ────────────────

class TestSplitMergeEventsBornResolved:
    def _events(self, root: Path) -> list[dict]:
        return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in _impact_events(root)]

    def test_split_event_resolved_by_system(self, project_root):
        src = _make(project_root, title="Source")
        new = _make(project_root, title="New")
        arch = _make(project_root, art_type="architecture", title="Down",
                     links=f"{src.id}:refines")
        result = impact_lib.split_artifact(project_root, src.id, new.id, [arch.id])
        assert result["ok"] and result["rewritten"] == [arch.id]
        events = [e for e in self._events(project_root) if e["change_type"] == "split"]
        assert len(events) == 1
        assert events[0]["resolved"] is True
        assert events[0]["resolved_by"] == "system"
        assert events[0]["flagged_suspects"] == []

    def test_merge_event_resolved_by_system(self, project_root):
        src = _make(project_root, title="Source")
        tgt = _make(project_root, title="Target")
        result = impact_lib.merge_artifact(project_root, src.id, tgt.id)
        assert result["ok"], result
        events = [e for e in self._events(project_root) if e["change_type"] == "merged"]
        assert len(events) == 1
        assert events[0]["resolved"] is True
        assert events[0]["resolved_by"] == "system"


# ── fix pass: a hand-cleared flag never prints "(0 artifacts)" ──────────

class TestLegacyClearedFlag:
    def _flag_then_hand_clear(self, root: Path) -> tuple[art_lib.Artifact, art_lib.Artifact]:
        req = _make(root, title="Upstream")
        arch = _make(root, art_type="architecture", title="Downstream",
                     links=f"{req.id}:refines")
        path = Path(req.path)
        path.write_text(path.read_text(encoding="utf-8").replace("\nb\n", "\nchanged\n"),
                        encoding="utf-8")
        result = impact_lib.propagate_suspects(root, req.id)
        assert result["ok"] and result["flagged_count"] == 1
        assert _reload(root, arch.id).suspect
        # Legacy bypass: the flag is cleared without going through --resolve.
        apath = Path(arch.path)
        apath.write_text(apath.read_text(encoding="utf-8").replace("suspect: true", "suspect: false"),
                         encoding="utf-8")
        assert not _reload(root, arch.id).suspect
        return req, arch

    def test_report_ignores_cleared_flag(self, project_root, capsys):
        self._flag_then_hand_clear(project_root)
        rc = change_impact_cmd.run(project_root, {"artifact_id": None, "resolve": None,
                                                  "flag": False})
        out = capsys.readouterr().out
        assert rc == 0
        assert "(0 artifacts)" not in out
        assert "Oldest unresolved flag" not in out
        assert "No unresolved suspect flags" in out

    def test_resolve_closes_the_stale_event(self, project_root, capsys):
        _, arch = self._flag_then_hand_clear(project_root)
        open_before = [p for p in _impact_events(project_root)
                       if not yaml.safe_load(p.read_text(encoding="utf-8")).get("resolved")]
        assert len(open_before) == 1
        rc = change_impact_cmd.run(project_root, {"artifact_id": None,
                                                  "resolve": arch.id, "flag": False})
        out = capsys.readouterr().out
        assert rc == 0
        assert "is not suspect" in out
        assert "closed 1 stale impact-log event" in out
        assert "Resolved suspect flag" not in out
        data = yaml.safe_load(open_before[0].read_text(encoding="utf-8"))
        assert data["resolved"] is True
        assert data["resolved_by"] == "user"
        # Second call: nothing left to close.
        rc = change_impact_cmd.run(project_root, {"artifact_id": None,
                                                  "resolve": arch.id, "flag": False})
        assert rc == 0
        assert "nothing to resolve" in capsys.readouterr().out
