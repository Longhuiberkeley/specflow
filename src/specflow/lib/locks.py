"""PID-based filesystem locking for concurrent artifact modification.

Guarantees and honest limits:

- Fresh acquisition is atomic (unique temp file + ``os.link``): the lock
  file appears fully formed or not at all; there is no empty-file window.
- Live-holder contention is exclusive: a second acquirer fails or waits,
  never steals.
- Stale breaking (dead/unparsable PID; age-bound PID-reuse for create
  locks) re-verifies the exact payload immediately before unlinking, so a
  breaker cannot delete a lock a concurrent acquirer just placed across the
  YAML-parse gap. A residual nanosecond-scale window remains between the
  re-read and the unlink itself; ``fcntl.flock`` (kernel-released on holder
  death, making stale detection unnecessary) is the airtight primitive if
  that window ever matters — deliberately not adopted here to keep the
  module portable (no fcntl on Windows).
- Release is ownership-checked: a dispossessed holder cannot delete a
  subsequent acquirer's lock.
- Age-based breaking (``SPECFLOW_CREATE_LOCK_MAX_AGE``, default 300 s)
  intentionally trades a pathological >300 s create critical section for
  liveness after PID reuse; a live-but-hung holder must be killed by PID —
  ``specflow unlock`` refuses live locks by design.

Advisory locks (these) are sufficient because every artifact mutation goes
through this module's callers, never raw file writes.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

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
    of the exact payload judged stale, so a breaker cannot delete a lock a
    concurrent acquirer just placed. A residual nanosecond-scale
    stat→unlink window is documented in the module docstring.
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
    breaking is payload-reverified, so two concurrent callers cannot both
    believe they hold the same lock except across a residual nanosecond-scale
    window in the stat→unlink gap of a stale break (see the module docstring;
    ``fcntl.flock`` is the airtight long-term primitive if that window ever
    matters in practice).
    """
    lock_data = {
        "pid": os.getpid(),
        "story_id": story_id,
        "timestamp": _now_iso(),
    }
    return _acquire_exclusive(_lock_path(root, artifact_id), lock_data)


def acquire_create_lock(root: Path, artifact_type: str) -> dict[str, Any]:
    """Acquire the type-scoped create lock guarding ID allocation.

    ``create_artifact`` holds this across the read-duplicate-write-index
    sequence so concurrent creates of the same type cannot allocate the same
    ID, overwrite each other's file, or lose the ``next_id`` bump. Contention
    waits briefly (creates are short); overridable for tests via
    SPECFLOW_CREATE_LOCK_WAIT / SPECFLOW_CREATE_LOCK_MAX_AGE (seconds).
    """
    lock_data = {
        "pid": os.getpid(),
        "story_id": f"create:{artifact_type}",
        "timestamp": _now_iso(),
    }
    return _acquire_exclusive(
        _lock_path(root, create_lock_key(artifact_type)),
        lock_data,
        max_wait_s=_env_float("SPECFLOW_CREATE_LOCK_WAIT", 10.0),
        max_age_s=_env_float("SPECFLOW_CREATE_LOCK_MAX_AGE", 300.0),
    )


def release_create_lock(root: Path, artifact_type: str) -> bool:
    """Release the type-scoped create lock. True if deleted."""
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
    """Check if an artifact is locked. Returns lock info dict or None."""
    lock_file = _lock_path(root, artifact_id)
    if not lock_file.exists():
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
    for lock_file in sorted(locks_dir.glob("*.lock")):
        artifact_id = lock_file.stem
        info = _read_lock(lock_file)
        if info is None:
            result.append({"artifact_id": artifact_id, "error": "malformed lock file"})
            continue
        info["artifact_id"] = artifact_id
        info["stale"] = not _is_pid_running(int(info.get("pid", 0) or 0))
        result.append(info)

    return result
