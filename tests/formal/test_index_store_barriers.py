"""Subprocess barrier tests and environment fixtures for the index store
(STORY-696, DDD-034 I1-I4 and I6; SPIKE-003 part 1).

Each race runs real processes released together by a file barrier (the
pattern of tests/test_create_locking.py). Where the unprotected window is
narrow, the worker widens it with an injected sleep in a function that exists
in both the old and the fixed code (``_read_index``, ``_plan_id_map``,
``os.unlink``): on the fixed code the sleep happens while the mutation lock is
held, so it only slows the run down.

The environment fixtures cover the states the index meets outside a single
process: git conflict markers, a deleted highest id, a nested artifact file,
a detached HEAD and a feature branch.
"""

from __future__ import annotations

import ast
import collections
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest
import yaml

from specflow.lib import artifacts as art_lib

from index_store_support import (
    index_of,
    invariant_names,
    invariant_violations,
    scaffold,
    type_dir,
)

HERE = Path(__file__).resolve().parent

_WORKER = textwrap.dedent(
    r"""
    import json, os, sys, time
    from pathlib import Path

    root = Path(sys.argv[1]); mode = sys.argv[2]; n = int(sys.argv[3])
    barrier = Path(sys.argv[4]); delay = float(sys.argv[5]); tag = sys.argv[6]

    from specflow.lib import artifacts as art_lib

    if delay:
        _orig_read = art_lib._read_index
        def _slow_read(path, *a, **kw):
            data = _orig_read(path, *a, **kw)
            time.sleep(delay)
            return data
        art_lib._read_index = _slow_read
        art_lib.read_index = _slow_read

    while not barrier.exists():
        time.sleep(0.002)

    out = {"created": [], "errors": []}
    if mode == "create":
        for i in range(n):
            title = f"{tag} {i}"
            r = art_lib.create_artifact(root, sys.argv[7], title=title, body=title)
            if r.get("ok"):
                out["created"].append([r["id"], title])
            else:
                out["errors"].append(r.get("error"))
    elif mode == "update":
        for i in range(n):
            r = art_lib.update_artifact(root, sys.argv[7], tags=[f"t{i}"])
            if not r.get("ok"):
                out["errors"].append(r.get("error"))
    elif mode == "rebuild":
        for i in range(n):
            art_lib.rebuild_index(root)
    elif mode == "renumber":
        import contextlib, io
        from specflow.commands import renumber_drafts
        if delay:
            _orig_plan = renumber_drafts._plan_id_map
            def _slow_plan(*a, **kw):
                res = _orig_plan(*a, **kw)
                time.sleep(delay * 20)
                return res
            renumber_drafts._plan_id_map = _slow_plan
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            out["rc"] = renumber_drafts.run(root, {})
        out["stdout"] = buf.getvalue()
    print("RESULT " + json.dumps(out))
    """
)


def _spawn(tmp: Path, root: Path, mode: str, n: int, barrier: Path, delay: float,
           tag: str, arg: str = "") -> subprocess.Popen:
    script = tmp / "worker.py"
    if not script.exists():
        script.write_text(_WORKER, encoding="utf-8")
    return subprocess.Popen(
        [sys.executable, str(script), str(root), mode, str(n), str(barrier),
         str(delay), tag, arg],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def _collect(procs: list[subprocess.Popen]) -> list[dict]:
    results = []
    for p in procs:
        out, err = p.communicate(timeout=180)
        assert p.returncode == 0, f"worker crashed: {err[-2000:]}"
        line = [ln for ln in out.splitlines() if ln.startswith("RESULT ")][-1]
        results.append(json.loads(line[len("RESULT "):]))
    return results


def _titles_intact(root: Path, created: list[list[str]]) -> list[str]:
    """I2: every create that reported success still owns its id's file."""
    lost = []
    for art_id, title in created:
        path = art_lib.resolve_link_target(root, art_id)
        art = art_lib.parse_artifact(path) if path else None
        if art is None or art.title != title:
            lost.append(f"{art_id} ({title!r} -> {art.title if art else None!r})")
    return lost


# ---------------------------------------------------------------------------
# Races (subprocess barriers)


def test_I4_update_rmw_vs_create_loses_no_create(tmp_path: Path):
    """Same-type update read-modify-write racing create (defect C)."""
    root = scaffold(tmp_path)
    art_lib.create_artifact(root, "requirement", title="seed", body="s")
    barrier = tmp_path / "go"
    procs = [
        _spawn(tmp_path, root, "create", 25, barrier, 0.0, "C", "requirement"),
        _spawn(tmp_path, root, "update", 25, barrier, 0.01, "U", "REQ-001"),
    ]
    barrier.write_text("go")
    created, updated = _collect(procs)
    assert not created["errors"] and not updated["errors"], (created, updated)
    ids = [i for i, _t in created["created"]]
    assert len(set(ids)) == 25
    assert not _titles_intact(root, created["created"])
    assert invariant_violations(root) == []


def test_I4_parallel_verify_vs_generate_tests_create(tmp_path: Path):
    """verify's status/field writes on a UT racing generate-tests creating UTs."""
    root = scaffold(tmp_path)
    art_lib.create_artifact(root, "unit-test", title="seed UT", body="s")
    barrier = tmp_path / "go"
    procs = [
        _spawn(tmp_path, root, "create", 20, barrier, 0.0, "G", "unit-test"),
        _spawn(tmp_path, root, "update", 20, barrier, 0.01, "V", "UT-001"),
    ]
    barrier.write_text("go")
    created, updated = _collect(procs)
    assert not created["errors"] and not updated["errors"], (created, updated)
    assert not _titles_intact(root, created["created"])
    assert invariant_violations(root) == []


def test_I2_rebuild_vs_create_never_overwrites(tmp_path: Path):
    root = scaffold(tmp_path)
    art_lib.create_artifact(root, "requirement", title="seed", body="s")
    barrier = tmp_path / "go"
    procs = [
        _spawn(tmp_path, root, "create", 20, barrier, 0.0, "C", "requirement"),
        _spawn(tmp_path, root, "rebuild", 20, barrier, 0.01, "R"),
    ]
    barrier.write_text("go")
    created, _rebuilt = _collect(procs)
    assert not created["errors"], created
    assert not _titles_intact(root, created["created"]), "a create was overwritten"
    assert invariant_violations(root) == []


def test_I2_renumber_vs_create_never_overwrites(tmp_path: Path):
    root = scaffold(tmp_path)
    art_lib.create_artifact(root, "requirement", title="Base", body="b")
    for slug, title in (("ALPHAFEA-aaaa", "Alpha feature"), ("BETAFEAT-bbbb", "Beta feature")):
        art_lib.create_artifact(root, "requirement", title=title, body=title,
                                artifact_id=f"REQ-{slug}")
    barrier = tmp_path / "go"
    procs = [
        _spawn(tmp_path, root, "renumber", 1, barrier, 0.02, "N"),
        _spawn(tmp_path, root, "create", 4, barrier, 0.0, "C", "requirement"),
    ]
    barrier.write_text("go")
    renum, created = _collect(procs)
    assert renum["rc"] == 0, renum
    assert not created["errors"], created
    assert not _titles_intact(root, created["created"]), "renumber replaced a created file"
    titles = collections.Counter(a.title for a in art_lib.discover_artifacts(root, "requirement"))
    assert titles["Alpha feature"] == 1 and titles["Beta feature"] == 1, titles
    assert invariant_violations(root) == []


_LOCK_WORKER = textwrap.dedent(
    r"""
    import json, os, sys, time
    from pathlib import Path

    root = Path(sys.argv[1]); role = sys.argv[2]; sig = Path(sys.argv[3])
    os.environ["SPECFLOW_CREATE_LOCK_WAIT"] = "20"
    from specflow.lib import locks as locks_lib

    def wait_for(*names, timeout=4.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if any((sig / n).exists() for n in names):
                return True
            time.sleep(0.005)
        return False

    if role == "B":
        # The breaker: pause between the payload re-verification and the
        # unlink of the stale lock until A holds a fresh lock.
        real_unlink = os.unlink
        fired = {"done": False}
        def paused_unlink(path, *a, **kw):
            if str(path).endswith("__create__story.lock") and not fired["done"]:
                fired["done"] = True
                (sig / "B-verified").write_text("1")
                wait_for("A-holding")
            return real_unlink(path, *a, **kw)
        os.unlink = paused_unlink
        (sig / "B-ready").write_text("1")
    else:
        wait_for("B-verified", "B-holding", timeout=6.0)

    got = locks_lib.acquire_create_lock(root, "story")
    t0 = time.time()
    if got.get("ok"):
        (sig / f"{role}-holding").write_text("1")
        time.sleep(0.8)
    t1 = time.time()
    if got.get("ok"):
        locks_lib.release_create_lock(root, "story")
    print("RESULT " + json.dumps({"role": role, "ok": bool(got.get("ok")), "t0": t0, "t1": t1}))
    """
)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock path")
def test_I6_stale_break_unlink_vs_second_acquirer_single_holder(tmp_path: Path):
    """Two processes race to break the same stale lock; the breaker that
    verified the stale payload is paused before its unlink until the other
    holds a fresh lock. At most one process may believe it holds the lock."""
    root = scaffold(tmp_path)
    lock_file = root / ".specflow" / "locks" / "__create__story.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(yaml.dump({"pid": 999_999_999, "story_id": "create:story",
                                    "timestamp": "2026-01-01T00:00:00Z"}))
    sig = tmp_path / "sig"
    sig.mkdir()
    script = tmp_path / "lockworker.py"
    script.write_text(_LOCK_WORKER, encoding="utf-8")
    procs = [
        subprocess.Popen([sys.executable, str(script), str(root), role, str(sig)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for role in ("B", "A")
    ]
    results = _collect(procs)
    holders = [r for r in results if r["ok"]]
    assert holders, results
    holders.sort(key=lambda r: r["t0"])
    for first, second in zip(holders, holders[1:]):
        assert second["t0"] >= first["t1"] - 0.01, f"two holders at once: {results}"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock path")
def test_I6_killed_holder_releases_the_mutation_lock(tmp_path: Path):
    """A holder killed with SIGKILL leaves no lock behind (kernel release)."""
    from specflow.lib import locks as locks_lib

    root = scaffold(tmp_path)
    holder = subprocess.Popen(
        [sys.executable, "-c", textwrap.dedent(f"""
            import time
            from pathlib import Path
            from specflow.lib import locks as locks_lib
            assert locks_lib.acquire_create_lock(Path({str(root)!r}), "story")["ok"]
            print("HELD", flush=True)
            time.sleep(60)
        """)],
        stdout=subprocess.PIPE, text=True,
    )
    assert holder.stdout.readline().strip() == "HELD"
    holder.kill()
    holder.wait(timeout=10)
    start = time.monotonic()
    res = art_lib.create_artifact(root, "story", title="after kill", body="b")
    assert res["ok"], res
    assert time.monotonic() - start < 5
    assert locks_lib.check_lock(root, locks_lib.create_lock_key("story")) is None


# The no-flock (Windows) path of the mutation lock, exercised on POSIX: the
# worker removes ``fcntl`` from locks.py and supplies an ``msvcrt`` stand-in
# whose ``locking`` is a POSIX record lock, so the byte-range kernel-lock
# protocol the Windows path uses runs for real. On a locks.py without that
# protocol the stand-in is ignored and the stale-file break runs instead.
_FALLBACK_LOCK_WORKER = _LOCK_WORKER.replace(
    "from specflow.lib import locks as locks_lib\n",
    textwrap.dedent(
        """\
        from specflow.lib import locks as locks_lib
        import fcntl as _posix_fcntl

        class _Msvcrt:
            LK_UNLCK, LK_LOCK, LK_NBLCK = 0, 1, 2

            def locking(self, fd, mode, nbytes):
                pos = os.lseek(fd, 0, os.SEEK_CUR)
                if mode == self.LK_UNLCK:
                    _posix_fcntl.lockf(fd, _posix_fcntl.LOCK_UN, nbytes, pos, 0)
                else:
                    _posix_fcntl.lockf(fd, _posix_fcntl.LOCK_EX | _posix_fcntl.LOCK_NB,
                                       nbytes, pos, 0)

        locks_lib._fcntl = None
        locks_lib._msvcrt = _Msvcrt()
        """
    ),
).replace("__create__story.lock", "__mutation__.lock")


@pytest.mark.skipif(sys.platform == "win32", reason="stand-in msvcrt is built on POSIX lockf")
def test_I6_no_flock_fallback_stale_break_vs_second_acquirer_single_holder(tmp_path: Path):
    """I6 on the path used where ``fcntl`` is missing (Windows).

    A stale ``__mutation__.lock`` from a dead process sits in the locks dir;
    breaker B is paused between verifying it stale and unlinking it until A
    holds the lock. At most one process may believe it holds the lock.
    """
    assert "locks_lib._fcntl = None" in _FALLBACK_LOCK_WORKER
    assert "__mutation__.lock" in _FALLBACK_LOCK_WORKER
    root = scaffold(tmp_path)
    lock_file = root / ".specflow" / "locks" / "__mutation__.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(yaml.dump({"pid": 999_999_999, "story_id": "create:story",
                                    "timestamp": "2026-01-01T00:00:00Z"}))
    sig = tmp_path / "sig"
    sig.mkdir()
    script = tmp_path / "lockworker_fallback.py"
    script.write_text(_FALLBACK_LOCK_WORKER, encoding="utf-8")
    procs = [
        subprocess.Popen([sys.executable, str(script), str(root), role, str(sig)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for role in ("B", "A")
    ]
    results = _collect(procs)
    holders = [r for r in results if r["ok"]]
    assert holders, results
    holders.sort(key=lambda r: r["t0"])
    for first, second in zip(holders, holders[1:]):
        assert second["t0"] >= first["t1"] - 0.01, f"two holders at once: {results}"


# ---------------------------------------------------------------------------
# Environment fixtures


def test_I2_create_with_conflict_marked_index_never_overwrites(tmp_path: Path):
    """Defect A: git left conflict markers in _index.yaml."""
    root = scaffold(tmp_path)
    art_lib.create_artifact(root, "requirement", title="Original one", body="ORIGINAL BODY 1")
    art_lib.create_artifact(root, "requirement", title="Two", body="b2")
    idx = type_dir(root, "requirement") / "_index.yaml"
    idx.write_text(idx.read_text().replace(
        "next_id: 3", "<<<<<<< HEAD\nnext_id: 3\n=======\nnext_id: 4\n>>>>>>> branch"))
    before = (type_dir(root, "requirement") / "REQ-001.md").read_bytes()
    res = art_lib.create_artifact(root, "requirement", title="New unrelated", body="NEW BODY")
    assert res["ok"], res
    assert res["id"] not in ("REQ-001", "REQ-002"), res["id"]
    assert (type_dir(root, "requirement") / "REQ-001.md").read_bytes() == before
    assert "<<<<<<<" not in idx.read_text()
    assert invariant_violations(root) == []


def test_I3_deleted_highest_id_never_reused_after_rebuild(tmp_path: Path):
    """Defect B: delete the highest id, rebuild, create -> must not reuse it."""
    root = scaffold(tmp_path)
    for i in range(3):
        art_lib.create_artifact(root, "requirement", title=f"R{i}", body=f"b{i}")
    art_lib.create_artifact(root, "story", title="S", body="s",
                            links=[{"target": "REQ-003", "role": "implements"}])
    (type_dir(root, "requirement") / "REQ-003.md").unlink()
    art_lib.rebuild_index(root)
    res = art_lib.create_artifact(root, "requirement", title="Totally different", body="x")
    assert res["ok"], res
    assert res["id"] != "REQ-003", "deleted id re-allocated; STORY-001's link re-binds"
    assert art_lib.resolve_link_target(root, "REQ-003") is None
    assert invariant_violations(root, {"requirement": {"REQ-003"}}) == []


def test_I3_deleted_highest_id_never_reused_without_rebuild(tmp_path: Path):
    root = scaffold(tmp_path)
    for i in range(2):
        art_lib.create_artifact(root, "requirement", title=f"R{i}", body=f"b{i}")
    (type_dir(root, "requirement") / "REQ-002.md").unlink()
    res = art_lib.create_artifact(root, "requirement", title="New", body="x")
    assert res["id"] == "REQ-003", res


def test_I1_nested_file_id_not_reallocated(tmp_path: Path):
    """A hand-placed artifact in a subdirectory that the index never saw."""
    root = scaffold(tmp_path)
    art_lib.create_artifact(root, "requirement", title="R1", body="b")
    art_lib.create_artifact(root, "requirement", title="R2", body="b")
    nested = type_dir(root, "requirement") / "area" / "REQ-003.md"
    nested.parent.mkdir()
    nested.write_text("---\nid: REQ-003\ntitle: Nested\ntype: requirement\nstatus: draft\n"
                      "created: '2026-01-01'\n---\n\n# Nested\n", encoding="utf-8")
    res = art_lib.create_artifact(root, "requirement", title="R new", body="b")
    assert res["ok"], res
    assert res["id"] == "REQ-004", res
    assert invariant_violations(root) == []


def test_I1_explicit_id_that_exists_on_disk_is_refused(tmp_path: Path):
    root = scaffold(tmp_path)
    art_lib.create_artifact(root, "requirement", title="R1", body="ORIGINAL")
    (type_dir(root, "requirement") / "_index.yaml").unlink()
    before = (type_dir(root, "requirement") / "REQ-001.md").read_bytes()
    res = art_lib.create_artifact(root, "requirement", title="X", body="b", artifact_id="REQ-001")
    assert res["ok"] is False and "already exists" in res["error"]
    assert (type_dir(root, "requirement") / "REQ-001.md").read_bytes() == before


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})


def test_I1_detached_head_allocates_sequential_ids(tmp_path: Path):
    root = scaffold(tmp_path)
    _git(root, "init", "-q", "-b", "main")
    art_lib.create_artifact(root, "requirement", title="R1", body="b")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    _git(root, "checkout", "-q", "--detach")
    res = art_lib.create_artifact(root, "requirement", title="R2", body="b")
    assert res["id"] == "REQ-002", res
    assert invariant_violations(root) == []


def test_renumber_refuses_on_feature_branch(tmp_path: Path, capsys):
    from specflow.commands import renumber_drafts

    root = scaffold(tmp_path)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "commit", "-q", "--allow-empty", "-m", "init")
    _git(root, "checkout", "-q", "-b", "feature/x")
    res = art_lib.create_artifact(root, "requirement", title="Draft one", body="b")
    assert not res["id"].endswith("-001"), res  # a draft id on a feature branch
    before = sorted(p.name for p in type_dir(root, "requirement").iterdir())
    rc = renumber_drafts.run(root, {})
    assert rc != 0
    assert "feature branch" in capsys.readouterr().out
    assert sorted(p.name for p in type_dir(root, "requirement").iterdir()) == before


def test_renumber_refuses_a_target_collision(tmp_path: Path, capsys, monkeypatch):
    """If the planned target already exists, nothing is renamed or rewritten."""
    from specflow.commands import renumber_drafts

    root = scaffold(tmp_path)
    art_lib.create_artifact(root, "requirement", title="Base", body="b")
    art_lib.create_artifact(root, "requirement", title="Draft", body="d",
                            artifact_id="REQ-DRAFTONE-aaaa")
    # A file that collides with the plan's first target, written behind the
    # allocator's back and hidden from it (models a racing writer).
    target = type_dir(root, "requirement") / "REQ-002.md"
    orig = renumber_drafts._plan_id_map

    def plan_then_collide(*a, **kw):
        res = orig(*a, **kw)
        target.write_text("---\nid: REQ-002\ntitle: Other\ntype: requirement\n"
                          "status: draft\ncreated: '2026-01-01'\n---\n\n# Other\n")
        return res

    monkeypatch.setattr(renumber_drafts, "_plan_id_map", plan_then_collide)
    rc = renumber_drafts.run(root, {})
    assert rc != 0
    assert "already exists" in capsys.readouterr().out
    assert (type_dir(root, "requirement") / "REQ-DRAFTONE-aaaa.md").exists()
    assert art_lib.parse_artifact(target).title == "Other"


def test_I4_index_is_rebuildable_cache_after_mixed_sequence(tmp_path: Path):
    root = scaffold(tmp_path)
    allocated: set[str] = set()
    for i in range(4):
        allocated.add(art_lib.create_artifact(root, "requirement", title=f"R{i}", body="b")["id"])
    art_lib.update_artifact(root, "REQ-002", status="approved")
    (type_dir(root, "requirement") / "REQ-004.md").unlink()
    art_lib.rebuild_index(root)
    allocated.add(art_lib.create_artifact(root, "requirement", title="R5", body="b")["id"])
    assert invariant_violations(root, {"requirement": allocated}) == []
    assert index_of(root, "requirement")["next_id"] == 6


# ---------------------------------------------------------------------------
# Pin: every DDD-034 invariant has a test_I<n>_* in tests/formal/


def test_invariant_names_are_pinned_to_tests():
    names = invariant_names()
    assert [n for n, _ in names] == [f"I{i}" for i in range(1, 7)], names
    defined = {
        node.name
        for path in HERE.glob("test_*.py")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.FunctionDef)
    }
    missing = [n for n, _ in names if not any(d.startswith(f"test_{n}_") for d in defined)]
    assert not missing, f"DDD-034 invariants without a test_I<n>_* test: {missing}"


@pytest.mark.parametrize("op", ["close_phase", "set_phase"])
def test_I4_phase_state_read_modify_write_holds_the_mutation_lock(tmp_path: Path, monkeypatch, op):
    """STORY-696 AC2: close_phase / set_phase read state.yaml under the lock.

    The write alone going through atomic_write under the lock is not enough:
    a read outside it lets a concurrent state writer's update be lost.
    """
    from specflow.lib import learning
    from specflow.lib import locks as locks_lib

    root = scaffold(tmp_path)
    real = learning.read_state
    seen: list[bool] = []

    def spy(r):
        seen.append(locks_lib.lock_held(r))
        return real(r)

    monkeypatch.setattr(learning, "read_state", spy)
    res = learning.close_phase(root) if op == "close_phase" else learning.set_phase(root, "verifying")
    assert res["ok"], res
    assert seen and all(seen), f"{op} read state.yaml without the mutation lock"
