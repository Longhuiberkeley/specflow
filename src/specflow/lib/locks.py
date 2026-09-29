"""Filesystem locks: the repo-wide mutation lock and per-artifact locks.

The mutation lock (DEC-093, DDD-034 I6) serialises every writer of
``_index.yaml``, ``state.yaml``, learned PREV patterns, baselines and
impact-log files. Those writers go through :func:`atomic_write` /
:func:`exclusive_write`, which raise :class:`MutationLockNotHeld` unless the
calling thread holds the lock for an enclosing project root;
tests/test_single_index_writer.py bans any other writer of those files.

Mechanism and honest limits:

- POSIX: ``fcntl.flock`` on ``.specflow/locks/mutation.flock``. The kernel
  releases the lock when the holder dies, so there is no stale-lock break
  and no window in which two processes both hold it
  (tests/formal/test_index_store_barriers.py::test_I6_*). The file is never
  unlinked (unlinking a flock file lets two processes lock two different
  inodes); the holder's payload is written into it for ``specflow locks``
  and truncated on release.
- Windows (no ``fcntl``): ``msvcrt.locking`` on one byte of the same
  ``mutation.flock`` file, far past the payload so readers of the payload are
  not blocked. The OS releases it when the holder's handle closes or the
  process dies, so there is no stale break here either
  (DEF-015, test_I6_no_flock_fallback_stale_break_vs_second_acquirer_single_holder,
  which runs this protocol on POSIX through a ``lockf`` stand-in).
- Neither ``fcntl`` nor ``msvcrt``: the file-lock path below — unique temp
  file plus ``os.link`` for acquisition and a payload-verified stale break. A
  residual window remains between the stale break's re-read and its unlink
  in which a second acquirer's fresh lock can be removed (DEF-010); no
  supported platform takes this path for the mutation lock.
- The lock is advisory: code that writes those files without the primitive
  is not stopped at runtime by the kernel, only by the lock-held assertion
  and the writer-ban test.
- Reentrant per thread: nested ``mutation_lock`` calls in one thread share
  one acquisition.

Per-artifact locks (``acquire_lock``) keep the file-lock path on every
platform, with the DEF-010 window: they are advisory wave-deferral markers,
not the mutation lock, and no DDD-034 invariant rests on them.
``release_lock`` is ownership-checked and live locks are never broken
(``specflow unlock`` refuses them).
"""

from __future__ import annotations

import contextlib
import errno
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import yaml

try:  # POSIX
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows
    _fcntl = None  # type: ignore[assignment]

try:  # Windows
    import msvcrt as _msvcrt  # type: ignore[import-not-found]
except ImportError:
    _msvcrt = None  # type: ignore[assignment]

#: True when the kernel flock path is used for the mutation lock.
HAVE_FLOCK = _fcntl is not None

# Create locks are type-scoped: the artifact ID does not exist yet at
# acquisition time, so the lock key namespaces on the artifact type. The
# "__create__" prefix cannot collide with real artifact IDs (PREFIX-NNN).
CREATE_LOCK_PREFIX = "__create__"

_CREATE_LOCK_POLL_S = 0.05


def _lock_path(root: Path, artifact_id: str) -> Path:
    return root / ".specflow" / "locks" / f"{artifact_id}.lock"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_pid_running(pid: int) -> bool:
    """Check if a process with the given PID is still running.

    ``PermissionError`` means the process EXISTS but is owned by another
    user — that is a live holder, not a stale one.
    """
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (OSError, ProcessLookupError):
        return False


def _env_float(name: str, default: float) -> float:
    """Read a float env override at call time (monkeypatch/test friendly)."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def create_lock_key(artifact_type: str) -> str:
    """Lock key for the type-scoped create lock of an artifact type."""
    return f"{CREATE_LOCK_PREFIX}{artifact_type}"


def _read_lock(lock_file: Path) -> dict[str, Any] | None:
    """Parse a lock file; None when missing or malformed."""
    if not lock_file.exists():
        return None
    try:
        data = yaml.safe_load(lock_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _lock_age_s(info: dict[str, Any]) -> float | None:
    """Age of a lock in seconds; None when the timestamp is unparsable."""
    ts = info.get("timestamp")
    try:
        held = datetime.strptime(str(ts), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        return None
    return (datetime.now(timezone.utc) - held).total_seconds()


def _lock_is_stale(info: dict[str, Any], max_age_s: float | None = None) -> bool:
    """Stale when the holder PID is gone, the payload is malformed, or (when
    ``max_age_s`` is given) the lock is older than the bound — create locks
    are short-lived, so an old lock held by a live PID reads as PID reuse."""
    if not _is_pid_running(int(info.get("pid", 0) or 0)):
        return True
    age = _lock_age_s(info)
    if age is None:
        return True
    if max_age_s is not None and age > max_age_s:
        return True
    return False


def _safe_unlink(lock_file: Path) -> None:
    try:
        lock_file.unlink()
    except FileNotFoundError:
        pass


def _try_exclusive_create(lock_file: Path, lock_data: dict[str, Any]) -> bool:
    """Atomically create+claim the lock file.

    The payload is written to a unique temp file and linked into place with
    ``os.link`` (atomic on POSIX): the lock file either appears fully formed
    or not at all. ``O_CREAT|O_EXCL`` alone would expose an empty-file window
    where a concurrent reader misreads the lock as malformed, unlinks it, and
    steals it — two holders, the exact bug this module exists to prevent.
    """
    payload = yaml.dump(lock_data, default_flow_style=False, sort_keys=False)
    tmp = lock_file.with_name(
        f"{lock_file.name}.{os.getpid()}.{time.monotonic_ns()}.tmp"
    )
    try:
        tmp.write_text(payload, encoding="utf-8")
        try:
            os.link(tmp, lock_file)
        except FileExistsError:
            return False
        return True
    finally:
        _safe_unlink(tmp)


def _acquire_exclusive(
    lock_file: Path,
    lock_data: dict[str, Any],
    max_wait_s: float = 0.0,
    max_age_s: float | None = None,
) -> dict[str, Any]:
    """Acquire ``lock_file`` exclusively.

    Fresh creation is atomic (unique temp file + ``os.link``): the lock file
    appears fully formed or not at all. Contention within ``max_wait_s`` is
    retried with a short poll; beyond it the holder wins.

    Stale locks (dead/unparsable PID, optionally age-bound) are broken via
    :func:`_break_stale_verified`: the unlink is guarded by a re-inspection
    of the exact payload judged stale, which closes the YAML-parse gap but
    not the re-read→unlink gap: a breaker paused there removes a fresh lock
    and two processes hold it (DEF-010,
    tests/formal/test_index_store_barriers.py::test_I6_stale_break_unlink_vs_second_acquirer_single_holder).
    That is why the mutation lock uses a kernel lock (``fcntl.flock`` on
    POSIX, ``msvcrt.locking`` on Windows, DEF-015); this path remains for
    per-artifact locks and for a platform with neither.
    """
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + max(0.0, max_wait_s)
    while True:
        info = _read_lock(lock_file)
        if info is not None and not _lock_is_stale(info, max_age_s):
            if time.monotonic() >= deadline:
                return {
                    "ok": False,
                    "held_by": str(info.get("story_id", "unknown")),
                    "pid": int(info.get("pid", 0) or 0),
                }
            time.sleep(_CREATE_LOCK_POLL_S)
            continue
        # Missing, malformed, or stale: verified break, then race for it.
        if info is not None:
            if not _break_stale_verified(lock_file, info):
                # Payload changed under us (someone else broke/acquired) —
                # re-inspect rather than unlink blind.
                continue
        elif lock_file.exists():
            # Unparsable payload: verified break against the raw bytes.
            if not _break_stale_verified(lock_file, None):
                continue
        if _try_exclusive_create(lock_file, lock_data):
            return {"ok": True, "lock_path": str(lock_file)}
        # Lost the race to another breaker/creator — loop and re-inspect.


def _break_stale_verified(lock_file: Path, inspected: dict[str, Any] | None) -> bool:
    """Unlink ``lock_file`` only if it still holds the payload we judged stale.

    Re-reads and compares against ``inspected`` (or, for an unparsable
    payload, the raw bytes) immediately before unlinking, so the common
    check-then-act race — two breakers, one winner, the loser deleting the
    winner's freshly linked lock — cannot fire across the YAML-parse gap.
    Returns True when this call performed the unlink.
    """
    try:
        current_bytes = lock_file.read_bytes()
    except FileNotFoundError:
        return False  # someone else broke it first
    if inspected is not None:
        try:
            current = yaml.safe_load(current_bytes.decode("utf-8"))
        except Exception:
            current = None
        if not isinstance(current, dict) or current != inspected:
            return False  # file changed under us — do not unlink
    else:
        # Unparsable-inspection path: caller saw garbage; only unlink if it
        # is STILL garbage. A fresh lock parses as a mapping — empty files
        # and non-dict payloads (yaml.safe_load(b"") → None, no exception)
        # are garbage and MUST be broken, or the acquire loop spins forever
        # (NEW-1 from review pass 2).
        try:
            parsed = yaml.safe_load(current_bytes.decode("utf-8"))
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            return False  # a fresh lock replaced the garbage
        # else: still non-dict garbage — fall through to unlink.
    try:
        os.unlink(lock_file)
    except FileNotFoundError:
        return False
    # Post-unlink audit: if the file re-appeared with a DIFFERENT payload,
    # our unlink removed the stale one and an acquirer followed — correct.
    return True


def acquire_lock(root: Path, artifact_id: str, story_id: str) -> dict[str, Any]:
    """Acquire a filesystem lock for an artifact.

    Returns {"ok": True, "lock_path": str} on success,
    or {"ok": False, "held_by": str, "pid": int} if already locked.

    Fresh acquisition is atomic (unique temp file + ``os.link``) and stale
    breaking is payload-reverified; the stale break still has a re-read→unlink
    window in which two callers can both end up holding the lock (see
    :func:`_acquire_exclusive` and DEF-010). Per-artifact locks are advisory
    markers for wave deferral, not the mutation lock.
    """
    lock_data = {
        "pid": os.getpid(),
        "story_id": story_id,
        "timestamp": _now_iso(),
    }
    return _acquire_exclusive(_lock_path(root, artifact_id), lock_data)


# Raw (non-reentrant) holds taken through the compatibility API below.
_RAW_HOLDS: dict[tuple[str, str], tuple] = {}


def acquire_create_lock(root: Path, artifact_type: str) -> dict[str, Any]:
    """Compatibility alias: hold the repo-wide mutation lock.

    Per-type create locks were replaced by one mutation lock (DEC-093); the
    ``create-lock:<type>`` surface (``specflow unlock``, ``specflow locks``)
    now addresses it. This takes a raw hold that is NOT registered as held
    by the calling thread, so a ``create_artifact`` in the same thread
    contends with it exactly as another process would. Waits up to
    SPECFLOW_CREATE_LOCK_WAIT seconds (default 10).
    """
    key = (_root_key(root), artifact_type)
    try:
        handle = _acquire_raw(
            Path(key[0]), f"create:{artifact_type}",
            _env_float("SPECFLOW_CREATE_LOCK_WAIT", 10.0),
        )
    except MutationLockTimeout as exc:
        return {"ok": False, "held_by": exc.holder, "pid": exc.pid}
    _RAW_HOLDS[key] = handle
    return {"ok": True, "lock_path": str(handle[2])}


def release_create_lock(root: Path, artifact_type: str) -> bool:
    """Release a hold taken by :func:`acquire_create_lock`. True if released.

    Without such a hold, falls back to removing a legacy per-type lock file
    this process owns.
    """
    handle = _RAW_HOLDS.pop((_root_key(root), artifact_type), None)
    if handle is not None:
        _release_raw(Path(_root_key(root)), handle)
        return True
    return release_lock(root, create_lock_key(artifact_type))


def release_lock(root: Path, artifact_id: str, expect_pid: int | None = None) -> bool:
    """Release a filesystem lock. True if deleted, False if not found.

    With ``expect_pid`` (or, by default, our own PID), the unlink is
    ownership-checked: a holder whose lock was dispossessed mid-flight must
    not delete the lock a subsequent acquirer legitimately holds.
    """
    lock_file = _lock_path(root, artifact_id)
    info = _read_lock(lock_file)
    if info is None:
        if lock_file.exists() and expect_pid is None:
            _safe_unlink(lock_file)
            return True
        return False
    pid = int(info.get("pid", 0) or 0)
    want = os.getpid() if expect_pid is None else expect_pid
    if pid != want:
        return False  # not ours anymore — leave the current holder's lock
    _safe_unlink(lock_file)
    return True


def check_lock(root: Path, artifact_id: str) -> dict[str, Any] | None:
    """Check if an artifact is locked. Returns lock info dict or None.

    A ``create-lock:<type>`` key (``__create__<type>``) or the mutation key
    reports a legacy lock file when one exists, else the mutation lock's
    holder while it is held.
    """
    lock_file = _lock_path(root, artifact_id)
    if not lock_file.exists():
        if artifact_id.startswith(CREATE_LOCK_PREFIX) or artifact_id == MUTATION_LOCK_KEY:
            return mutation_lock_holder(root)
        return None

    try:
        data = yaml.safe_load(lock_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def break_stale_lock(root: Path, artifact_id: str) -> bool:
    """Break a lock if the holding PID is no longer running.

    Returns True if the lock was stale and broken, False otherwise.
    """
    lock_file = _lock_path(root, artifact_id)
    info = _read_lock(lock_file)
    if info is None:
        if lock_file.exists():
            # Malformed — treat as stale
            _safe_unlink(lock_file)
            return True
        return False

    if not _is_pid_running(int(info.get("pid", 0) or 0)):
        _safe_unlink(lock_file)
        return True

    return False


def list_locks(root: Path) -> list[dict[str, Any]]:
    """List all current locks."""
    locks_dir = root / ".specflow" / "locks"
    if not locks_dir.exists():
        return []

    result: list[dict[str, Any]] = []
    holder = mutation_lock_holder(root)
    if holder is not None:
        result.append({**holder, "artifact_id": "mutation", "stale": False})
    for lock_file in sorted(locks_dir.glob("*.lock")):
        artifact_id = lock_file.stem
        info = _read_lock(lock_file)
        if info is None:
            result.append({"artifact_id": artifact_id, "error": "malformed lock file"})
            continue
        info["artifact_id"] = artifact_id
        info["stale"] = not _is_pid_running(int(info.get("pid", 0) or 0))
        info.setdefault("holder", info.get("story_id", "?"))
        info.setdefault("acquired_at", info.get("timestamp", "?"))
        result.append(info)

    return result


# ---------------------------------------------------------------------------
# The repo-wide mutation lock (DEC-093) and the single write primitive.

#: Lock key of the mutation lock on the file-lock (Windows) fallback path.
MUTATION_LOCK_KEY = "__mutation__"
_FLOCK_NAME = "mutation.flock"
_POLL_S = 0.01


class MutationLockTimeout(RuntimeError):
    """The mutation lock stayed held by another process past the wait."""

    def __init__(self, info: dict[str, Any] | None) -> None:
        info = info or {}
        self.holder = str(info.get("story_id", info.get("held_by", "unknown")))
        self.pid = int(info.get("pid", 0) or 0)
        super().__init__(
            f"the mutation lock is held by PID {self.pid or '?'} ({self.holder})"
        )


class MutationLockNotHeld(RuntimeError):
    """A guarded file was written without holding the mutation lock."""


_local = threading.local()


def _root_key(root: Path | str) -> str:
    return str(Path(root).resolve())


def _held() -> dict[str, dict[str, Any]]:
    held = getattr(_local, "held", None)
    if held is None:
        held = _local.held = {}
    return held


def _locks_dir(root: Path) -> Path:
    d = root / ".specflow" / "locks"
    d.mkdir(parents=True, exist_ok=True)
    ignore = d / ".gitignore"
    if not ignore.exists():
        # Lock files are machine state; keep them out of consumers' git.
        try:
            fd = os.open(ignore, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            pass
        else:
            try:
                os.write(fd, b"*\n")
            finally:
                os.close(fd)
    return d


def _lock_wait_s() -> float:
    if os.environ.get("SPECFLOW_MUTATION_LOCK_WAIT") is not None:
        return _env_float("SPECFLOW_MUTATION_LOCK_WAIT", 30.0)
    return _env_float("SPECFLOW_CREATE_LOCK_WAIT", 30.0)


def _acquire_raw(root: Path, holder: str, wait_s: float) -> tuple:
    """Acquire the mutation lock for ``root``; raise MutationLockTimeout."""
    lock_data = {"pid": os.getpid(), "story_id": holder, "timestamp": _now_iso()}
    d = _locks_dir(root)
    if _fcntl is None and _msvcrt is not None:
        return _acquire_msvcrt(d / _FLOCK_NAME, lock_data, wait_s)
    if _fcntl is None:  # pragma: no cover - no kernel lock available
        res = _acquire_exclusive(
            _lock_path(root, MUTATION_LOCK_KEY), lock_data,
            max_wait_s=wait_s,
            max_age_s=_env_float("SPECFLOW_CREATE_LOCK_MAX_AGE", 300.0),
        )
        if not res.get("ok"):
            raise MutationLockTimeout(res)
        return ("file", None, _lock_path(root, MUTATION_LOCK_KEY))
    path = d / _FLOCK_NAME
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    deadline = time.monotonic() + max(0.0, wait_s)
    while True:
        try:
            _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
            break
        except OSError as exc:
            if exc.errno not in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES):
                os.close(fd)
                raise
            if time.monotonic() >= deadline:
                os.close(fd)
                raise MutationLockTimeout(_read_lock(path)) from None
            time.sleep(_POLL_S)
    payload = yaml.dump(lock_data, default_flow_style=False, sort_keys=False).encode()
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, payload)
    return ("flock", fd, path)


#: Offset of the byte ``msvcrt.locking`` locks: past any payload, so reading
#: the holder's payload is never blocked by the byte-range lock.
_MSVCRT_LOCK_OFFSET = 1 << 30


def _msvcrt_try_lock(fd: int) -> bool:
    os.lseek(fd, _MSVCRT_LOCK_OFFSET, os.SEEK_SET)
    try:
        _msvcrt.locking(fd, _msvcrt.LK_NBLCK, 1)
    except OSError:
        return False
    return True


def _msvcrt_unlock(fd: int) -> None:
    os.lseek(fd, _MSVCRT_LOCK_OFFSET, os.SEEK_SET)
    _msvcrt.locking(fd, _msvcrt.LK_UNLCK, 1)


def _acquire_msvcrt(path: Path, lock_data: dict[str, Any], wait_s: float) -> tuple:
    """Kernel byte-range lock for the no-``fcntl`` path (DEF-015)."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    deadline = time.monotonic() + max(0.0, wait_s)
    while not _msvcrt_try_lock(fd):
        if time.monotonic() >= deadline:
            os.close(fd)
            raise MutationLockTimeout(_read_lock(path))
        time.sleep(_POLL_S)
    payload = yaml.dump(lock_data, default_flow_style=False, sort_keys=False).encode()
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, payload)
    return ("msvcrt", fd, path)


def _release_raw(root: Path, handle: tuple) -> None:
    kind, fd, _path = handle
    if kind == "msvcrt":
        try:
            os.ftruncate(fd, 0)
        finally:
            _msvcrt_unlock(fd)
            os.close(fd)
        return
    if kind == "flock":
        try:
            os.ftruncate(fd, 0)
        finally:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
            os.close(fd)
    else:  # pragma: no cover - Windows fallback
        release_lock(root, MUTATION_LOCK_KEY)


def mutation_lock_holder(root: Path) -> dict[str, Any] | None:
    """The current mutation-lock holder's payload, or None when free."""
    if _fcntl is None and _msvcrt is not None:
        path = root / ".specflow" / "locks" / _FLOCK_NAME
        if not path.exists():
            return None
        fd = os.open(path, os.O_RDWR)
        try:
            if _msvcrt_try_lock(fd):
                _msvcrt_unlock(fd)
                return None
            info = _read_lock(path) or {}
            return {**info, "holder": info.get("story_id", "?"),
                    "acquired_at": info.get("timestamp", "?")}
        finally:
            os.close(fd)
    if _fcntl is None:  # pragma: no cover - no kernel lock available
        return _read_lock(_lock_path(root, MUTATION_LOCK_KEY))
    path = root / ".specflow" / "locks" / _FLOCK_NAME
    if not path.exists():
        return None
    fd = os.open(path, os.O_RDONLY)
    try:
        try:
            _fcntl.flock(fd, _fcntl.LOCK_SH | _fcntl.LOCK_NB)
        except OSError:
            info = _read_lock(path) or {}
            return {**info, "holder": info.get("story_id", "?"),
                    "acquired_at": info.get("timestamp", "?")}
        _fcntl.flock(fd, _fcntl.LOCK_UN)
        return None
    finally:
        os.close(fd)


def lock_held(root: Path) -> bool:
    """True when the calling thread holds the mutation lock for ``root``."""
    ent = _held().get(_root_key(root))
    return bool(ent) and ent["pid"] == os.getpid()


@contextlib.contextmanager
def mutation_lock(
    root: Path, holder: str = "mutation", wait_s: float | None = None
) -> Iterator[None]:
    """Hold the repo-wide mutation lock for ``root`` (reentrant per thread).

    Raises :class:`MutationLockTimeout` when another process keeps it past
    ``wait_s`` (default SPECFLOW_MUTATION_LOCK_WAIT, else
    SPECFLOW_CREATE_LOCK_WAIT, else 30 s).
    """
    key = _root_key(root)
    ent = _held().get(key)
    if ent is not None and ent["pid"] == os.getpid():
        ent["depth"] += 1
        try:
            yield
        finally:
            ent["depth"] -= 1
        return
    handle = _acquire_raw(Path(key), holder, _lock_wait_s() if wait_s is None else wait_s)
    _held()[key] = {"depth": 1, "pid": os.getpid(), "handle": handle}
    try:
        yield
    finally:
        _held().pop(key, None)
        _release_raw(Path(key), handle)


def _assert_held_for(path: Path) -> None:
    target = Path(path).resolve()
    pid = os.getpid()
    for key, ent in _held().items():
        if ent["pid"] != pid:
            continue
        held_root = Path(key)
        if target == held_root or held_root in target.parents:
            return
    raise MutationLockNotHeld(
        f"write to {path} without the mutation lock; wrap the caller in "
        "locks.mutation_lock(root)"
    )


def _tmp_for(path: Path) -> Path:
    return path.with_name(f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")


def atomic_write(path: Path, text: str | bytes, *, encoding: str = "utf-8") -> None:
    """Replace ``path`` with ``text`` atomically (temp file + ``os.replace``).

    THE write primitive for index, state, PREV, baseline and impact-log files
    and for artifact rewrites under the lock: readers and a crash at any
    point see the whole old or the whole new file, never a torn prefix
    (tests/formal/test_index_store_crash.py). Raises
    :class:`MutationLockNotHeld` unless the calling thread holds the
    mutation lock for an enclosing project root.
    """
    path = Path(path)
    _assert_held_for(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_for(path)
    try:
        if isinstance(text, bytes):
            tmp.write_bytes(text)
        else:
            tmp.write_text(text, encoding=encoding)
        os.replace(tmp, path)
    finally:
        _safe_unlink(tmp)


def exclusive_write(path: Path, text: str, *, encoding: str = "utf-8") -> bool:
    """Create ``path`` with ``text`` only if it does not exist; True if created.

    The linearisation point of every allocator (DEC-093): the content goes
    to a temp file that is hard-linked into place, so the file appears whole
    or not at all and an existing file is never replaced. File systems
    without hard links fall back to ``O_CREAT|O_EXCL`` (exclusive, but a
    crash mid-write can leave a partial file). Requires the mutation lock.
    """
    path = Path(path)
    _assert_held_for(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_for(path)
    try:
        tmp.write_text(text, encoding=encoding)
        try:
            os.link(tmp, path)
            return True
        except FileExistsError:
            return False
        except OSError:
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except FileExistsError:
                return False
            with os.fdopen(fd, "w", encoding=encoding) as fh:
                fh.write(text)
            return True
    finally:
        _safe_unlink(tmp)


def locked_write(root: Path, path: Path, text: str | bytes, *, encoding: str = "utf-8") -> None:
    """:func:`atomic_write` under the mutation lock for ``root``."""
    with mutation_lock(root):
        atomic_write(path, text, encoding=encoding)


def locked_exclusive_write(root: Path, path: Path, text: str) -> bool:
    """:func:`exclusive_write` under the mutation lock for ``root``."""
    with mutation_lock(root):
        return exclusive_write(path, text)
