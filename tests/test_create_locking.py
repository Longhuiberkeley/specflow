"""STORY-638 — atomic create locking: race-safe ID allocation.

Covers the lock primitives (atomic O_EXCL acquisition, stale/malformed
breaking, age-bound create guards) and the end-to-end guarantee: concurrent
`create_artifact` calls of the same type must produce distinct IDs and an
intact index (no lost `next_id` bumps, no overwritten files).
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import locks as locks_lib


def _scaffold(tmp: Path) -> Path:
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)

    schema = {
        "type": "story",
        "prefix": "STORY",
        "allowed_status": {
            "draft": [],
            "approved": ["draft"],
            "implemented": ["approved"],
            "verified": ["implemented"],
        },
        "allowed_link_roles": ["implements", "verified_by"],
    }
    (schema_dir / "story.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    config = {
        "project": {"name": "lock-test", "created": "2026-01-01"},
        "artifact_types": ["story"],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / "_specflow" / "work" / "stories").mkdir(parents=True, exist_ok=True)
    return root


class TestLockPrimitives:
    def test_second_acquire_fails_when_live_holder(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        first = locks_lib.acquire_lock(root, "STORY-001", "S1")
        second = locks_lib.acquire_lock(root, "STORY-001", "S2")
        assert first["ok"] is True
        assert second["ok"] is False
        assert second["pid"] == os.getpid()
        assert locks_lib.release_lock(root, "STORY-001") is True

    def test_dead_pid_lock_is_broken(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        lock_file = root / ".specflow" / "locks" / "STORY-001.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(
            yaml.dump({"pid": 999_999_999, "story_id": "ghost", "timestamp": "2026-01-01T00:00:00Z"}),
            encoding="utf-8",
        )
        result = locks_lib.acquire_lock(root, "STORY-001", "S1")
        assert result["ok"] is True

    def test_malformed_lock_is_broken(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        lock_file = root / ".specflow" / "locks" / "STORY-001.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text("::: not yaml @@@ [", encoding="utf-8")
        result = locks_lib.acquire_lock(root, "STORY-001", "S1")
        assert result["ok"] is True

    def test_create_lock_key_is_namespaced(self):
        # Cannot collide with real artifact IDs (PREFIX-NNN shape).
        assert locks_lib.create_lock_key("story") == "__create__story"
        assert locks_lib.create_lock_key("story").startswith(locks_lib.CREATE_LOCK_PREFIX)

    def test_stale_create_lock_broken_by_age_with_live_pid(self, tmp_path, monkeypatch):
        # PID reuse guard: a create lock older than the age bound is stale
        # even when the recorded PID is alive (here: our own PID).
        root = _scaffold(tmp_path)
        monkeypatch.setenv("SPECFLOW_CREATE_LOCK_MAX_AGE", "0")
        lock_file = root / ".specflow" / "locks" / "__create__story.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(
            yaml.dump(
                {
                    "pid": os.getpid(),
                    "story_id": "create:story",
                    "timestamp": "2020-01-01T00:00:00Z",
                }
            ),
            encoding="utf-8",
        )
        result = locks_lib.acquire_create_lock(root, "story")
        assert result["ok"] is True
        assert locks_lib.release_create_lock(root, "story") is True

    def test_live_fresh_create_lock_is_respected(self, tmp_path, monkeypatch):
        root = _scaffold(tmp_path)
        monkeypatch.setenv("SPECFLOW_CREATE_LOCK_WAIT", "0")
        first = locks_lib.acquire_create_lock(root, "story")
        second = locks_lib.acquire_create_lock(root, "story")
        assert first["ok"] is True
        assert second["ok"] is False
        assert second["pid"] == os.getpid()
        locks_lib.release_create_lock(root, "story")

    def test_permissionerror_means_alive_pid(self, tmp_path, monkeypatch):
        # Another user's live process: os.kill(0) raises PermissionError —
        # that is a LIVE holder, never stale. Fresh timestamp isolates the
        # liveness path from the age-based PID-reuse rule.
        root = _scaffold(tmp_path)
        lock_file = root / ".specflow" / "locks" / "__create__story.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(
            yaml.dump({"pid": 1, "story_id": "create:story",
                       "timestamp": locks_lib._now_iso()}),
            encoding="utf-8",
        )
        monkeypatch.setattr(
            locks_lib.os, "kill",
            lambda pid, sig: (_ for _ in ()).throw(PermissionError()),
        )
        monkeypatch.setenv("SPECFLOW_CREATE_LOCK_WAIT", "0")
        result = locks_lib.acquire_create_lock(root, "story")
        assert result["ok"] is False

    def test_break_does_not_unlink_changed_payload(self, tmp_path):
        # The verified-break guard: if the lock file's payload changes
        # between inspection and break (another acquirer replaced it), the
        # break must NOT unlink the fresh lock.
        root = _scaffold(tmp_path)
        lock_file = root / ".specflow" / "locks" / "__create__story.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        stale = {"pid": 999_999_999, "story_id": "create:story",
                 "timestamp": "2026-01-01T00:00:00Z"}
        lock_file.write_text(yaml.dump(stale), encoding="utf-8")
        # A fresh lock replaces the stale one before the break runs:
        fresh = {"pid": os.getpid(), "story_id": "create:story",
                 "timestamp": "2026-08-27T00:00:00Z"}
        lock_file.write_text(yaml.dump(fresh), encoding="utf-8")
        broke = locks_lib._break_stale_verified(lock_file, stale)
        assert broke is False
        assert yaml.safe_load(lock_file.read_text()) == fresh  # untouched

    def test_empty_lock_file_is_broken_not_hung(self, tmp_path, monkeypatch):
        # NEW-1 regression: yaml.safe_load(b"") returns None WITHOUT raising,
        # so an empty (or scalar) lock file must still be broken — otherwise
        # the acquire loop spins forever. Bounded wait proves termination.
        root = _scaffold(tmp_path)
        monkeypatch.setenv("SPECFLOW_CREATE_LOCK_WAIT", "0.2")
        lock_file = root / ".specflow" / "locks" / "__create__story.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text("", encoding="utf-8")
        result = locks_lib.acquire_create_lock(root, "story")
        assert result["ok"] is True

    def test_scalar_lock_file_is_broken_not_hung(self, tmp_path, monkeypatch):
        root = _scaffold(tmp_path)
        monkeypatch.setenv("SPECFLOW_CREATE_LOCK_WAIT", "0.2")
        lock_file = root / ".specflow" / "locks" / "__create__story.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text("pid", encoding="utf-8")  # parses as a string
        result = locks_lib.acquire_create_lock(root, "story")
        assert result["ok"] is True

    def test_release_is_ownership_checked(self, tmp_path):
        # A dispossessed holder's finally-release must not delete the lock
        # a subsequent acquirer holds.
        root = _scaffold(tmp_path)
        lock_file = root / ".specflow" / "locks" / "__create__story.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        other = {"pid": 4242, "story_id": "create:story",
                 "timestamp": "2026-08-27T00:00:00Z"}
        lock_file.write_text(yaml.dump(other), encoding="utf-8")
        assert locks_lib.release_lock(root, locks_lib.create_lock_key("story")) is False
        assert yaml.safe_load(lock_file.read_text()) == other  # untouched


class TestCreateArtifactLocking:
    def test_lock_released_after_failed_create(self, tmp_path: Path):
        # A failing create (duplicate explicit ID) must still release the
        # create guard — the next create succeeds without waiting.
        root = _scaffold(tmp_path)
        first = art_lib.create_artifact(root, "story", title="A", body="b")
        assert first["ok"] is True
        dup = art_lib.create_artifact(root, "story", title="A2", artifact_id="STORY-001", body="b")
        assert dup["ok"] is False
        assert "already exists" in dup["error"]
        # Guard is free again:
        assert locks_lib.check_lock(root, locks_lib.create_lock_key("story")) is None
        third = art_lib.create_artifact(root, "story", title="C", body="b")
        assert third["ok"] is True
        assert third["id"] == "STORY-002"

    def test_no_lock_left_behind_after_success(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        result = art_lib.create_artifact(root, "story", title="A", body="b")
        assert result["ok"] is True
        locks_dir = root / ".specflow" / "locks"
        leftovers = list(locks_dir.glob("*.lock")) if locks_dir.exists() else []
        assert leftovers == []

    def test_blocked_create_reports_actionable_error(self, tmp_path, monkeypatch):
        root = _scaffold(tmp_path)
        monkeypatch.setenv("SPECFLOW_CREATE_LOCK_WAIT", "0")
        held = locks_lib.acquire_create_lock(root, "story")
        assert held["ok"] is True
        try:
            result = art_lib.create_artifact(root, "story", title="blocked", body="b")
            assert result["ok"] is False
            assert "specflow unlock create-lock:story" in result["error"]
        finally:
            locks_lib.release_create_lock(root, "story")

    def test_unlock_cli_breaks_stale_create_lock(self, tmp_path: Path, capsys):
        from specflow.commands import unlock as unlock_cmd

        root = _scaffold(tmp_path)
        lock_file = root / ".specflow" / "locks" / "__create__story.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(
            yaml.dump(
                {
                    "pid": 999_999_999,
                    "story_id": "create:story",
                    "timestamp": "2026-01-01T00:00:00Z",
                }
            ),
            encoding="utf-8",
        )
        code = unlock_cmd.run(root, {"artifact_id": "create-lock:story"})
        out = capsys.readouterr().out
        assert code == 0
        assert "Broke stale lock" in out
        assert not lock_file.exists()

    def test_unlock_cli_recognizes_type_alias(self, tmp_path: Path, capsys):
        from specflow.commands import unlock as unlock_cmd

        root = _scaffold(tmp_path)
        code = unlock_cmd.run(root, {"artifact_id": "create-lock:story"})
        out = capsys.readouterr().out
        assert code == 0
        assert "No lock exists on create-lock:story" in out


_WORKER_SCRIPT = textwrap.dedent(
    """
    import sys, time
    from pathlib import Path

    root = Path(sys.argv[1])
    worker = sys.argv[2]
    count = int(sys.argv[3])
    barrier = Path(sys.argv[4])

    from specflow.lib import artifacts as art_lib

    while not barrier.exists():
        time.sleep(0.005)

    ok = 0
    ids = []
    for i in range(count):
        r = art_lib.create_artifact(
            root, "story", title=f"W{worker} story {i}", body="concurrency probe"
        )
        if r.get("ok"):
            ok += 1
            ids.append(r["id"])
    print("RESULT", ok, ",".join(ids))
    """
)


class TestConcurrentCreate:
    def test_parallel_creates_distinct_ids_intact_index(self, tmp_path: Path):
        """Subprocess-based race: 8 workers, 2 creates each, synchronized on
        a file barrier — all 16 must succeed with distinct IDs and the index
        must reflect every artifact plus the correct next_id."""
        root = _scaffold(tmp_path)
        script = tmp_path / "worker.py"
        script.write_text(_WORKER_SCRIPT, encoding="utf-8")
        barrier = tmp_path / "go"

        workers = 8
        per_worker = 2
        procs = [
            subprocess.Popen(
                [sys.executable, str(script), str(root), str(w), str(per_worker), str(barrier)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for w in range(workers)
        ]
        barrier.write_text("go", encoding="utf-8")

        all_ids: list[str] = []
        total_ok = 0
        errors: list[str] = []
        for p in procs:
            out, err = p.communicate(timeout=120)
            for line in out.splitlines():
                if line.startswith("RESULT"):
                    _, ok, ids = line.split(maxsplit=2)
                    total_ok += int(ok)
                    all_ids.extend(i for i in ids.split(",") if i)
            if err.strip():
                errors.append(err.strip()[-500:])
            assert p.returncode == 0, f"worker failed: {err}"

        expected = workers * per_worker
        lock_state = list((root / ".specflow" / "locks").glob("*")) if (root / ".specflow" / "locks").exists() else []
        index_raw = (root / "_specflow" / "work" / "stories" / "_index.yaml")
        diag = f"\nerrors={errors}\nlocks={lock_state}\nindex={index_raw.read_text() if index_raw.exists() else 'MISSING'}"
        assert total_ok == expected, f"only {total_ok}/{expected} creates succeeded{diag}"
        assert len(set(all_ids)) == expected, f"duplicate IDs allocated under concurrency{diag}"

        index = yaml.safe_load(
            (root / "_specflow" / "work" / "stories" / "_index.yaml").read_text(encoding="utf-8")
        )
        indexed = index.get("artifacts", {})
        assert len(indexed) == expected, f"index lost updates{diag}"
        assert set(indexed.keys()) == set(all_ids), f"index/content mismatch{diag}"
        assert index.get("next_id") == expected + 1, f"next_id drifted{diag}"

        files = list((root / "_specflow" / "work" / "stories").glob("STORY-*.md"))
        assert len(files) == expected
