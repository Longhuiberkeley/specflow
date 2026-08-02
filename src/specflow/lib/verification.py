"""Verification contract runner — records deterministic evidence, never blocks.

A ``verify_command`` that exits non-zero is RECORDED (``verify_run_exit_code`` =
that code) and the caller still treats it as a successful recording. This is the
accounting-not-policing keystone invariant: we surface evidence, we do not gate
on it. The CLI reserves non-zero exit for *runner* failures only (timeout,
subprocess spawn failure) — never for a non-zero verify_command.

Result fields are written via ``update_artifact`` so they land in frontmatter.
Recording is fingerprint-EXEMPT by design: ``compute_fingerprint`` hashes the
body only, so adding these fields never changes the artifact fingerprint and
never sets ``suspect``.
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib


# ── Small deterministic helpers ───────────────────────────────────


def hash_text(text: str) -> str:
    """Return ``sha256:<12hex>`` of the given UTF-8 text."""
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]}"


def hash_file(path: Path) -> str:
    """Return ``sha256:<12hex>`` of the given file's bytes."""
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()[:12]}"


def now_iso_utc() -> str:
    """Current time as ISO-8601 UTC, e.g. ``2026-08-02T14:03:00Z``."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mtime_iso_utc(path: Path) -> str:
    """A file's mtime as ISO-8601 UTC."""
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head_ref(root: Path) -> str:
    """Best-effort ``git rev-parse HEAD``. Empty string if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def resolve_evidence_file(root: Path, globs: Any) -> Path | None:
    """Return the first file matching any glob pattern (relative to root), else None.

    A bare string is treated as a single pattern. Non-string/None input yields
    no match.
    """
    if isinstance(globs, str):
        globs = [globs]
    if not isinstance(globs, list):
        return None
    for pattern in globs:
        if not isinstance(pattern, str) or not pattern:
            continue
        for match in sorted(root.glob(pattern)):
            if match.is_file():
                return match
    return None


# ── Core runner ───────────────────────────────────────────────────


def run_one(
    root: Path,
    artifact: art_lib.Artifact,
    *,
    timeout: int = 600,
    evidence_file: bool = False,
) -> dict[str, Any]:
    """Run a single artifact's ``verify_command`` and gather pinned result fields.

    Returns a dict with:
      ok: True if the subprocess completed (regardless of its exit code);
          False on timeout or spawn failure.
      exit_code: the subprocess exit code (None when the run failed).
      out_hash: ``sha256:<12hex>`` of stdout+stderr ("" on failure).
      run_at: ISO-8601 UTC timestamp of the attempt.
      git_ref: best-effort ``git rev-parse HEAD`` ("" if not a repo).
      command_hash: ``sha256:<12hex>`` of the verify_command string.
      evidence_hash / evidence_mtime: only meaningful when evidence_file=True.
      error: human-readable message on failure ("").

    This never raises for a non-zero verify_command exit — that exit code is
    recorded, not treated as a runner failure.
    """
    fm = artifact.frontmatter
    command = fm.get("verify_command", "")
    if not isinstance(command, str):
        command = str(command)

    started = now_iso_utc()
    start_clock = datetime.now(timezone.utc)
    result: dict[str, Any] = {
        "ok": True,
        "exit_code": None,
        "command": command,
        "command_hash": hash_text(command),
        "run_at": started,
        "git_ref": git_head_ref(root),
        "out_hash": "",
        "evidence_hash": "",
        "evidence_mtime": "",
        "error": "",
        "elapsed": 0.0,
    }

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result["exit_code"] = proc.returncode
        result["out_hash"] = hash_text((proc.stdout or "") + (proc.stderr or ""))
        result["ok"] = True
    except subprocess.TimeoutExpired:
        result["ok"] = False
        result["error"] = f"verify_command timed out after {timeout}s"
        result["elapsed"] = (datetime.now(timezone.utc) - start_clock).total_seconds()
        return result
    except Exception as exc:  # spawn failure (command malformed, OOM, ...)
        result["ok"] = False
        result["error"] = f"failed to spawn verify_command: {exc}"
        result["elapsed"] = (datetime.now(timezone.utc) - start_clock).total_seconds()
        return result

    result["elapsed"] = (datetime.now(timezone.utc) - start_clock).total_seconds()

    if evidence_file:
        match = resolve_evidence_file(root, fm.get("verify_evidence"))
        if match is not None:
            result["evidence_hash"] = hash_file(match)
            result["evidence_mtime"] = mtime_iso_utc(match)
        # else: leave empty — caller surfaces a warning

    return result


def build_updates(run_result: dict[str, Any], *, evidence_file: bool) -> dict[str, Any]:
    """Build the frontmatter update dict from a ``run_one`` result.

    Only the pinned result field names are emitted. Evidence fields are included
    only when ``evidence_file`` was requested (so non-evidence runs don't write
    empty placeholders).
    """
    updates: dict[str, Any] = {
        "verify_run_exit_code": run_result["exit_code"],
        "verify_run_out_hash": run_result["out_hash"],
        "verify_run_at": run_result["run_at"],
        "verify_run_git_ref": run_result["git_ref"],
        "verify_run_command_hash": run_result["command_hash"],
    }
    if evidence_file:
        updates["verify_run_evidence_hash"] = run_result["evidence_hash"]
        updates["verify_run_evidence_mtime"] = run_result["evidence_mtime"]
    return updates
