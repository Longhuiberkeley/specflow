"""Crash-at-k harness for the index store (STORY-696, DDD-034 I5; SPIKE-003 part 1).

Every mutating command is run once cleanly while counting calls to the write
primitives (``Path.write_text``, ``Path.write_bytes``, ``os.replace``, ``os.rename`` — which
``Path.rename`` delegates to — and ``os.link``). ``_write_index`` is covered
through the primitives it calls. Then, for every k, the command is re-run on
a fresh scaffold with the k-th write made to crash, in two variants:

* ``raise`` — the write raises before it happens;
* ``torn``  — ``write_text``/``write_bytes`` writes the first half of its payload, then raises
  (the atomic ``os.replace``/``os.rename``/``os.link`` cannot tear, so they
  raise).

The crash is a ``BaseException`` so ``except Exception`` handlers in the code
under test cannot swallow it (it models a kill, not an error). The same
command is then re-run without a crash and the normalised end state must
equal a state reached by an uncrashed history: the command run once (the
crashed attempt left no trace) or run twice (it had fully committed). The
quiescent invariants I1 and I4 must also hold.
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
from pathlib import Path
from typing import Callable

import pytest

from specflow.lib import artifacts as art_lib
from specflow.lib import impact as impact_lib

from index_store_support import invariant_violations, scaffold, snapshot, type_dir


class Crash(BaseException):
    """Simulated process death at a write."""


@contextlib.contextmanager
def write_counter(crash_at: int | None = None, mode: str = "raise"):
    """Count (and optionally crash at) calls to the write primitives."""
    state = {"n": 0}
    orig_write_text = pathlib.Path.write_text
    orig_write_bytes = pathlib.Path.write_bytes
    orig_replace, orig_rename, orig_link = os.replace, os.rename, os.link

    def tick() -> bool:
        state["n"] += 1
        return crash_at is not None and state["n"] == crash_at

    def write_text(self, data, *a, **kw):
        if tick():
            if mode == "torn":
                orig_write_text(self, data[: len(data) // 2], *a, **kw)
            raise Crash(f"write_text {self}")
        return orig_write_text(self, data, *a, **kw)

    def write_bytes(self, data):
        if tick():
            if mode == "torn":
                orig_write_bytes(self, data[: len(data) // 2])
            raise Crash(f"write_bytes {self}")
        return orig_write_bytes(self, data)

    def wrap(fn, name):
        def inner(*a, **kw):
            if tick():
                raise Crash(f"{name} {a[:2]}")
            return fn(*a, **kw)
        return inner

    pathlib.Path.write_text = write_text
    pathlib.Path.write_bytes = write_bytes
    os.replace = wrap(orig_replace, "replace")
    os.rename = wrap(orig_rename, "rename")
    os.link = wrap(orig_link, "link")
    try:
        yield state
    finally:
        pathlib.Path.write_text = orig_write_text
        pathlib.Path.write_bytes = orig_write_bytes
        os.replace, os.rename, os.link = orig_replace, orig_rename, orig_link


# ---------------------------------------------------------------------------
# Operations: (setup(root), op(root)). Setup runs uncrashed.


def _body(root: Path, artifact_id: str, text: str) -> None:
    path = art_lib.resolve_link_target(root, artifact_id)
    raw = path.read_text(encoding="utf-8")
    head, _sep, _old = raw.partition("\n---\n")
    path.write_text(head + "\n---\n\n" + text + "\n", encoding="utf-8")


def _setup_basic(root: Path) -> None:
    art_lib.create_artifact(root, "requirement", title="R one", body="one")
    art_lib.create_artifact(root, "requirement", title="R two", body="two")
    art_lib.create_artifact(
        root, "story", title="S one", body="s",
        links=[{"target": "REQ-001", "role": "implements"}],
    )


def _op_create(root: Path) -> None:
    assert art_lib.create_artifact(root, "requirement", title="R new", body="new")["ok"]


def _op_update(root: Path) -> None:
    res = art_lib.update_artifact(root, "REQ-001", status="approved", tags=["x", "y"])
    assert res["ok"], res


def _setup_rebuild(root: Path) -> None:
    _setup_basic(root)
    art_lib.create_artifact(root, "requirement", title="R three", body="three")
    (type_dir(root, "requirement") / "REQ-002.md").unlink()
    # Empty fingerprint -> rebuild repairs it (one more write site).
    p = type_dir(root, "requirement") / "REQ-001.md"
    p.write_text(p.read_text(encoding="utf-8").replace("fingerprint: sha256", "fingerprint: ''\nx_old: sha256"), encoding="utf-8")


def _op_rebuild(root: Path) -> None:
    art_lib.rebuild_index(root)


def _setup_renumber(root: Path) -> None:
    art_lib.create_artifact(root, "requirement", title="Base", body="b")
    art_lib.create_artifact(root, "requirement", title="Alpha feature", body="a",
                            artifact_id="REQ-ALPHAFEA-aaaa")
    art_lib.create_artifact(root, "requirement", title="Beta feature", body="b",
                            artifact_id="REQ-BETAFEAT-bbbb",
                            links=[{"target": "REQ-ALPHAFEA-aaaa", "role": "derives_from"}])
    art_lib.create_artifact(root, "story", title="S", body="s",
                            links=[{"target": "REQ-BETAFEAT-bbbb", "role": "implements"}])


def _op_renumber(root: Path) -> None:
    from specflow.commands import renumber_drafts

    with contextlib.redirect_stdout(io.StringIO()):
        assert renumber_drafts.run(root, {}) == 0


def _setup_lint_fix(root: Path) -> None:
    _setup_basic(root)
    _body(root, "REQ-002", "# R two\n\nedited body makes the fingerprint stale")


def _op_lint_fix(root: Path) -> None:
    from specflow.commands import artifact_lint

    with contextlib.redirect_stdout(io.StringIO()):
        artifact_lint._auto_fix(root)


def _setup_merge(root: Path) -> None:
    _setup_basic(root)
    for rid in ("REQ-001", "REQ-002"):
        assert art_lib.update_artifact(root, rid, status="approved")["ok"]


def _op_merge(root: Path) -> None:
    res = impact_lib.merge_artifact(root, "REQ-001", "REQ-002")
    assert res["ok"], res


def _setup_split(root: Path) -> None:
    _setup_basic(root)
    art_lib.create_artifact(root, "story", title="S two", body="s2",
                            links=[{"target": "REQ-001", "role": "implements"}])


def _op_split(root: Path) -> None:
    res = impact_lib.split_artifact(root, "REQ-001", "REQ-002", ["STORY-002"])
    assert res["ok"], res


def _setup_migrate(root: Path) -> None:
    from specflow.lib import practices

    for i, title in ((1, "Separation"), (2, "Hand authored")):
        art_lib.create_artifact(
            root, "best-practice", title=title, status="draft",
            body=practices.render_practice_body(
                "Do the practice.", "For relevant work.", "A decision record.",
                "Inspect the record.", "It avoids ambiguity.",
            ),
        )


def _op_migrate(root: Path) -> None:
    from specflow.lib import practices

    res = practices.migrate_practices(root)
    assert not res["errors"], res["errors"]


OPS: dict[str, tuple[Callable[[Path], None], Callable[[Path], None]]] = {
    "create": (_setup_basic, _op_create),
    "update": (_setup_basic, _op_update),
    "rebuild-index": (_setup_rebuild, _op_rebuild),
    "renumber-drafts": (_setup_renumber, _op_renumber),
    "artifact-lint--fix": (_setup_lint_fix, _op_lint_fix),
    "merge": (_setup_merge, _op_merge),
    "split": (_setup_split, _op_split),
    "practices-migrate": (_setup_migrate, _op_migrate),
}


def _clean_states(tmp: Path, name: str) -> tuple[dict, dict, int]:
    setup, op = OPS[name]
    once = scaffold(tmp, "clean1")
    setup(once)
    with write_counter() as counter:
        op(once)
    twice = scaffold(tmp, "clean2")
    setup(twice)
    op(twice)
    op(twice)
    return snapshot(once), snapshot(twice), counter["n"]


@pytest.mark.parametrize("mode", ["raise", "torn"])
@pytest.mark.parametrize("name", list(OPS))
def test_I5_crash_at_every_write_then_rerun_converges(tmp_path: Path, name: str, mode: str):
    setup, op = OPS[name]
    once, twice, n_writes = _clean_states(tmp_path, name)
    assert n_writes > 0, f"{name} performed no writes"
    failures: list[str] = []
    for k in range(1, n_writes + 1):
        root = scaffold(tmp_path, f"crash-{k}")
        setup(root)
        with write_counter(crash_at=k, mode=mode):
            try:
                op(root)
            except Crash:
                pass
        try:
            op(root)  # the documented recovery: run the same command again
        except Exception as exc:  # noqa: BLE001 - recorded as a divergence
            failures.append(f"k={k}: re-run raised {exc!r}")
            continue
        state = snapshot(root)
        if state not in (once, twice):
            diff = sorted(
                p for p in set(state) | set(once)
                if state.get(p) != once.get(p)
            )
            failures.append(f"k={k}: diverged from the clean run in {diff[:6]}")
        problems = invariant_violations(root)
        if problems:
            failures.append(f"k={k}: {problems}")
    assert not failures, f"{name}/{mode} over {n_writes} writes:\n" + "\n".join(failures)


def test_I5_harness_counts_every_write_primitive(tmp_path: Path):
    """Fidelity canary: the counter sees each primitive the harness patches."""
    p = tmp_path / "f"
    with write_counter() as counter:
        p.write_text("a")
        p.write_bytes(b"b")
        os.replace(p, tmp_path / "g")
        (tmp_path / "g").rename(tmp_path / "h")
        os.link(tmp_path / "h", tmp_path / "i")
    assert counter["n"] == 5
    with pytest.raises(Crash):
        with write_counter(crash_at=1, mode="torn"):
            (tmp_path / "t").write_text("abcdef")
    assert (tmp_path / "t").read_text() == "abc"
