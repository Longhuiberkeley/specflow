"""Replays of the TLC traces found on the FIXED protocol model (SPIKE-003 part 2).

formal/tla/IdAllocation.tla models the protocol shipped by STORY-696 (DEC-093).
TLC found two families of traces that break DDD-034 invariants. Each is
replayed here on the real code, following the recipe in SPIKE-003: a trace
becomes a DEF only once a pytest on the shipped code reproduces it.

M1 (formal/tla/IdAllocation_NoTheirs.cfg): renumber-drafts crashes after it has
journalled its plan, then a create runs before the documented re-run. The
allocators floor on file stems, index keys, the quarantine and next_id, but
not on the journal's targets, and ``_heal_index`` skips a file whose stem is
already an index key, so a frontmatter id rewritten by the crashed run is
invisible. The create takes a journalled target (I3), or an id another file
already carries (I1), and the resumed renumber stops on a collision (I5).

M2 (formal/tla/IdAllocation_NoCrash.cfg): an artifact file is deleted by hand
or by git, and a merge conflict on ``_index.yaml`` is resolved with the other
branch's side, which forked before the id was allocated. No working-tree
state remembers the id, so create hands it out again (I3) and existing links
to it re-bind silently.

M1 is DEF-013, fixed: the allocators floor on the renumber journal's planned
targets, ``_heal_index`` compares frontmatter ids while a journal exists, and
a resumed renumber re-checks its targets before the first write. The M1 tests
are plain regression tests now.

M2 (DEF-014) is open; its test is a strict xfail that names the DEF. Run with
``--runxfail`` to see the failure on the shipped code. When a fix lands, the
strict xfail turns into a failure and the mark must be removed.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import pytest
import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import draft_ids as draft_lib
from specflow.lib import locks as locks_lib

from index_store_support import ids_on_disk, scaffold, type_dir

JOURNAL = Path(".specflow") / "renumber-journal.yaml"

M2 = pytest.mark.xfail(
    strict=True,
    reason="DEF-014 open: an id erased from every working-tree record is reallocated",
)


class Crash(BaseException):
    """Simulated process death (not swallowed by ``except Exception``)."""


def _setup_drafts(root: Path) -> None:
    """REQ-001 plus two merged drafts; the second links the first, a story links it."""
    assert art_lib.create_artifact(root, "requirement", title="Base", body="b")["ok"]
    assert art_lib.create_artifact(root, "requirement", title="Alpha feature", body="a",
                                   artifact_id="REQ-ALPHAFEA-aaaa")["ok"]
    assert art_lib.create_artifact(
        root, "requirement", title="Beta feature", body="b", artifact_id="REQ-BETAFEAT-bbbb",
        links=[{"target": "REQ-ALPHAFEA-aaaa", "role": "derives_from"}],
    )["ok"]
    assert art_lib.create_artifact(
        root, "story", title="S", body="s",
        links=[{"target": "REQ-BETAFEAT-bbbb", "role": "implements"}],
    )["ok"]


def _renumber(root: Path) -> int:
    from specflow.commands import renumber_drafts

    with contextlib.redirect_stdout(io.StringIO()):
        return renumber_drafts.run(root, {})


def _crash_renumber_after_journal(root: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Model states 3-5: RnStart, RnJournal, Crash before the first rewrite."""
    def boom(*_a, **_kw):
        raise Crash("killed after the journal write")

    with monkeypatch.context() as m:
        m.setattr(draft_lib, "rewrite_references", boom)
        with pytest.raises(Crash):
            _renumber(root)
    journal = yaml.safe_load((root / JOURNAL).read_text(encoding="utf-8"))
    return dict(journal["id_map"])


def _crash_renumber_before_index_rewrite(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Model states 3-6: every *.md rewritten, crash at the _index.yaml rewrite."""
    real = locks_lib.atomic_write

    def guarded(path, text, *a, **kw):
        if Path(path).name == "_index.yaml" and (root / JOURNAL).exists():
            raise Crash(f"killed at {path}")
        return real(path, text, *a, **kw)

    with monkeypatch.context() as m:
        m.setattr(locks_lib, "atomic_write", guarded)
        with pytest.raises(Crash):
            _renumber(root)


def test_I3_create_after_renumber_crash_never_takes_a_journalled_target(tmp_path, monkeypatch):
    root = scaffold(tmp_path)
    _setup_drafts(root)
    id_map = _crash_renumber_after_journal(root, monkeypatch)

    res = art_lib.create_artifact(root, "requirement", title="Created before the re-run", body="n")

    assert res["ok"], res
    assert res["id"] not in set(id_map.values()), (
        f"create allocated {res['id']}, which the crashed renumber journalled for "
        f"{ {v: k for k, v in id_map.items()}[res['id']] }"
    )


def test_I1_create_after_renumber_crash_mid_rewrite_never_duplicates_an_id(tmp_path, monkeypatch):
    root = scaffold(tmp_path)
    _setup_drafts(root)
    _crash_renumber_before_index_rewrite(root, monkeypatch)

    res = art_lib.create_artifact(root, "requirement", title="Created before the re-run", body="n")

    assert res["ok"], res
    dupes = sorted(i for i, c in ids_on_disk(root).items() if c > 1)
    assert not dupes, f"create allocated {res['id']}; duplicate frontmatter ids on disk: {dupes}"


def test_I5_renumber_resume_after_interleaved_create_converges(tmp_path, monkeypatch):
    root = scaffold(tmp_path)
    _setup_drafts(root)
    _crash_renumber_after_journal(root, monkeypatch)
    assert art_lib.create_artifact(root, "requirement", title="Created before the re-run",
                                   body="n")["ok"]

    rc = _renumber(root)  # the documented recovery

    dupes = sorted(i for i, c in ids_on_disk(root).items() if c > 1)
    assert rc == 0 and not (root / JOURNAL).exists() and not dupes, (
        f"re-run exit {rc}, journal kept: {(root / JOURNAL).exists()}, duplicate ids: {dupes}"
    )


@M2
def test_I3_theirs_resolved_index_after_deleting_an_id_never_reuses_it(tmp_path):
    root = scaffold(tmp_path)
    reqs = type_dir(root, "requirement")
    assert art_lib.create_artifact(root, "requirement", title="One", body="1")["ok"]
    theirs = (reqs / "_index.yaml").read_text(encoding="utf-8")  # the other branch forks here
    assert art_lib.create_artifact(root, "requirement", title="Two", body="2")["id"] == "REQ-002"
    assert art_lib.create_artifact(
        root, "story", title="S", body="s", links=[{"target": "REQ-002", "role": "implements"}],
    )["ok"]
    (reqs / "REQ-002.md").unlink()  # git rm / hand delete, no rebuild
    (reqs / "_index.yaml").write_text(theirs, encoding="utf-8")  # conflict resolved --theirs

    res = art_lib.create_artifact(root, "requirement", title="Unrelated", body="u")

    assert res["ok"], res
    assert res["id"] != "REQ-002", "REQ-002 reallocated; STORY-001's implements link re-binds to it"


def test_I5_resume_refuses_before_rewriting_when_another_file_holds_a_target(tmp_path, monkeypatch):
    """DEF-013: a resumed renumber re-checks targets before its first write.

    An id can still reach the tree behind the allocator's back (a pull, a hand
    copy). The resumed run must stop before rewriting references, or links to
    the draft re-bind to the unrelated artifact.
    """
    from index_store_support import snapshot

    root = scaffold(tmp_path)
    _setup_drafts(root)
    id_map = _crash_renumber_after_journal(root, monkeypatch)
    target = sorted(id_map.values())[0]
    reqs = type_dir(root, "requirement")
    (reqs / f"{target}.md").write_text(
        f"---\nid: {target}\ntitle: Pulled in\ntype: requirement\nstatus: draft\n---\n\nx\n",
        encoding="utf-8",
    )
    before = snapshot(root)

    rc = _renumber(root)

    assert rc == 1
    assert (root / JOURNAL).exists()
    assert snapshot(root) == before, "the refused resume changed files"
