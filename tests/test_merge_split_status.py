"""merge and split write only schema-legal statuses (STORY-697 AC5, DEC-093).

Before the fix ``merge_artifact`` wrote ``status: merged_into`` (in no
schema's ``allowed_status``) straight into the file, left the index entry
stale, and recorded the pairing in an ad-hoc ``merged_target`` field. Now
the target gains a ``supersedes`` link to the source and the source moves to
``superseded`` through ``update_artifact`` — or to ``cancelled`` /
``deprecated`` where ``superseded`` is not legal from its current status, and
then the target gets no ``supersedes`` link (DEF-019). split writes no status
at all.
"""

from __future__ import annotations

import contextlib
import io
import re
import shutil
from pathlib import Path

import pytest
import yaml

from specflow import cli
from specflow.lib import artifacts as art_lib

REPO = Path(__file__).resolve().parents[1]
SCHEMAS = REPO / "src" / "specflow" / "templates" / "schemas"


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "p"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True)
    for t in ("requirement", "story"):
        shutil.copy(SCHEMAS / f"{t}.yaml", schema_dir / f"{t}.yaml")
        (root / "_specflow" / art_lib.TYPE_TO_DIR[t]).mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "t"}, "active_packs": []}), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "executing", "history": []}), encoding="utf-8")
    return root


def _cli(root: Path, monkeypatch, *argv: str) -> tuple[int, str]:
    monkeypatch.chdir(root)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(list(argv))
    return code, buf.getvalue()


def _legal(root: Path, art_type: str, status: str) -> bool:
    schema = yaml.safe_load((root / ".specflow" / "schema" / f"{art_type}.yaml").read_text())
    return status in (schema.get("allowed_status") or {})


def _index_status(root: Path, art_id: str) -> str:
    idx = yaml.safe_load(
        (root / "_specflow" / art_lib.TYPE_TO_DIR["requirement"] / "_index.yaml").read_text())
    return idx["artifacts"][art_id]["status"]


def test_merge_cli_supersedes_an_approved_source(tmp_path: Path, monkeypatch):
    root = _project(tmp_path)
    art_lib.create_artifact(root, "requirement", title="Old", body="old", status="approved")
    art_lib.create_artifact(root, "requirement", title="New", body="new", status="approved")
    art_lib.create_artifact(root, "story", title="S", body="s",
                            links=[{"target": "REQ-001", "role": "implements"}])

    code, out = _cli(root, monkeypatch, "merge", "REQ-001", "REQ-002")

    assert code == 0, out
    src = art_lib.parse_artifact(art_lib.resolve_link_target(root, "REQ-001"))
    tgt = art_lib.parse_artifact(art_lib.resolve_link_target(root, "REQ-002"))
    story = art_lib.parse_artifact(art_lib.resolve_link_target(root, "STORY-001"))
    assert src.status == "superseded" and _legal(root, "requirement", src.status)
    assert "merged_target" not in src.frontmatter
    assert ("REQ-001", "supersedes") in [(ln.target, ln.role) for ln in tgt.links]
    assert [(ln.target, ln.role) for ln in story.links] == [("REQ-002", "implements")]
    assert _index_status(root, "REQ-001") == "superseded"  # index stays a faithful cache
    assert "REQ-001 status: superseded" in out


def test_merge_of_a_draft_source_uses_the_legal_cancelled(tmp_path: Path, monkeypatch):
    # superseded is not legal from draft in the shipped requirement schema.
    root = _project(tmp_path)
    art_lib.create_artifact(root, "requirement", title="Draft", body="d")
    art_lib.create_artifact(root, "requirement", title="Keep", body="k", status="approved")

    code, out = _cli(root, monkeypatch, "merge", "REQ-001", "REQ-002")

    assert code == 0, out
    src = art_lib.parse_artifact(art_lib.resolve_link_target(root, "REQ-001"))
    assert src.status == "cancelled" and _legal(root, "requirement", src.status)
    assert _index_status(root, "REQ-001") == "cancelled"


def test_merge_never_writes_a_status_outside_the_schema(tmp_path: Path, monkeypatch):
    root = _project(tmp_path)
    for status in ("draft", "approved", "implemented", "verified"):
        a = art_lib.create_artifact(root, "requirement", title=f"S {status}", body=status)
        art_lib.create_artifact(root, "requirement", title=f"T {status}", body=status)
        if status != "draft":
            path = Path(a["path"])
            path.write_text(path.read_text().replace("status: draft", f"status: {status}"))
    art_lib.rebuild_index(root)
    for n in (1, 3, 5, 7):
        code, out = _cli(root, monkeypatch, "merge", f"REQ-{n:03d}", f"REQ-{n + 1:03d}")
        assert code == 0, out
        src = art_lib.parse_artifact(art_lib.resolve_link_target(root, f"REQ-{n:03d}"))
        assert _legal(root, "requirement", src.status), (n, src.status)


@pytest.mark.parametrize("source_status", ["draft", "approved", "implemented", "verified"])
def test_supersedes_link_iff_source_superseded(tmp_path: Path, monkeypatch, source_status):
    """AC5: the pairing is 'superseded plus a supersedes link'. A source that
    ends cancelled, deprecated or unchanged must not leave the target with a
    supersedes link to it (a dangling supersession claim)."""
    root = _project(tmp_path)
    a = art_lib.create_artifact(root, "requirement", title="Src", body="s")
    art_lib.create_artifact(root, "requirement", title="Tgt", body="t", status="approved")
    if source_status != "draft":
        path = Path(a["path"])
        path.write_text(path.read_text().replace("status: draft", f"status: {source_status}"))
        art_lib.rebuild_index(root)

    code, out = _cli(root, monkeypatch, "merge", "REQ-001", "REQ-002")

    assert code == 0, out
    src = art_lib.parse_artifact(art_lib.resolve_link_target(root, "REQ-001"))
    tgt = art_lib.parse_artifact(art_lib.resolve_link_target(root, "REQ-002"))
    has_link = ("REQ-001", "supersedes") in [(ln.target, ln.role) for ln in tgt.links]
    assert has_link == (src.status == "superseded"), (source_status, src.status, has_link)


def test_split_writes_no_status(tmp_path: Path, monkeypatch):
    root = _project(tmp_path)
    art_lib.create_artifact(root, "requirement", title="Big", body="b", status="approved")
    art_lib.create_artifact(root, "requirement", title="Half", body="h")
    art_lib.create_artifact(root, "story", title="S", body="s",
                            links=[{"target": "REQ-001", "role": "implements"}])

    code, out = _cli(root, monkeypatch, "split", "REQ-001", "REQ-002", "--reassign", "STORY-001")

    assert code == 0, out
    src = art_lib.parse_artifact(art_lib.resolve_link_target(root, "REQ-001"))
    story = art_lib.parse_artifact(art_lib.resolve_link_target(root, "STORY-001"))
    assert src.status == "approved"
    assert [(ln.target, ln.role) for ln in story.links] == [("REQ-002", "implements")]


@pytest.mark.parametrize("module", ["lib/impact.py", "commands/merge.py", "commands/split.py"])
def test_merge_and_split_never_write_status_directly(module: str):
    text = (REPO / "src" / "specflow" / module).read_text(encoding="utf-8")
    assert "merged_into" not in text
    assert not re.search(r"_update_frontmatter_field\([^)]*[\"']status[\"']", text)
