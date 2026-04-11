"""PID-based filesystem locking for concurrent artifact modification."""

from __future__ import annotations

import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _lock_path(root: Path, artifact_id: str) -> Path:
    return root / ".specflow" / "locks" / f"{artifact_id}.lock"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_pid_running(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def acquire_lock(root: Path, artifact_id: str, story_id: str) -> dict[str, Any]:
    """Acquire a filesystem lock for an artifact.

    Returns {"ok": True, "lock_path": str} on success,
    or {"ok": False, "held_by": str, "pid": int} if already locked.
    """
    lock_file = _lock_path(root, artifact_id)
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if already locked
    if lock_file.exists():
        try:
            data = yaml.safe_load(lock_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                held_pid = data.get("pid", 0)
                held_by = data.get("story_id", "unknown")

                if _is_pid_running(held_pid):
                    return {"ok": False, "held_by": held_by, "pid": held_pid}

                # Stale lock — break it
                lock_file.unlink()
        except Exception:
            # Malformed lock file — remove and proceed
            lock_file.unlink()

    # Create new lock
    lock_data = {
        "pid": os.getpid(),
        "story_id": story_id,
        "timestamp": _now_iso(),
    }
    lock_file.write_text(
        yaml.dump(lock_data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return {"ok": True, "lock_path": str(lock_file)}


def release_lock(root: Path, artifact_id: str) -> bool:
    """Release a filesystem lock. Returns True if deleted, False if not found."""
    lock_file = _lock_path(root, artifact_id)
    if lock_file.exists():
        lock_file.unlink()
        return True
    return False


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
    if not lock_file.exists():
        return False

    try:
        data = yaml.safe_load(lock_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            pid = data.get("pid", 0)
            if not _is_pid_running(pid):
                lock_file.unlink()
                return True
    except Exception:
        # Malformed — treat as stale
        lock_file.unlink()
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
        try:
            data = yaml.safe_load(lock_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data["artifact_id"] = artifact_id
                data["stale"] = not _is_pid_running(data.get("pid", 0))
                result.append(data)
        except Exception:
            result.append({"artifact_id": artifact_id, "error": "malformed lock file"})

    return result
