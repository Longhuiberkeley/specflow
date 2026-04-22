"""Immutable baseline snapshots of project artifact state.

A baseline captures every artifact's ID, status, fingerprint, title, and type
at a point in time, plus a git ref if available. Baselines are write-once:
attempting to overwrite an existing baseline returns an immutability error.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import git_utils

_BASELINE_NAME_RE = re.compile(r"^[\w.\-]+$")


def baseline_dir(root: Path) -> Path:
    return root / ".specflow" / "baselines"


def _baseline_path(root: Path, name: str) -> Path:
    return baseline_dir(root) / f"{name}.yaml"


def _validate_name(name: str) -> str | None:
    """Return an error message if the name is invalid, else None."""
    if not name:
        return "Baseline name cannot be empty"
    if not _BASELINE_NAME_RE.match(name):
        return (
            f"Invalid baseline name '{name}'. "
            "Use alphanumerics, '.', '-', and '_' only (no slashes or spaces)."
        )
    return None


def _resolve_git_ref(root: Path, name: str) -> str:
    """Resolve a git ref for the baseline: tag matching name, else HEAD SHA."""
    if not git_utils.is_git_repo(root):
        return ""
    tag_sha = git_utils.resolve_ref(root, name)
    if tag_sha:
        return tag_sha
    return git_utils.get_current_sha(root)


def create_baseline(root: Path, name: str) -> dict[str, Any]:
    """Create an immutable baseline snapshot at .specflow/baselines/<name>.yaml.

    Returns {"ok": True, "path": str, "artifact_count": int, "git_ref": str}
    or {"ok": False, "error": str} on failure.
    """
    err = _validate_name(name)
    if err:
        return {"ok": False, "error": err}

    path = _baseline_path(root, name)
    if path.exists():
        return {
            "ok": False,
            "error": (
                f"Baseline '{name}' already exists and cannot be overwritten "
                "(baselines are immutable)."
            ),
        }

    artifacts = art_lib.discover_artifacts(root)
    snapshot: dict[str, Any] = {}
    for art in artifacts:
        if not art.id:
            continue
        snapshot[art.id] = {
            "status": art.status,
            "fingerprint": art.fingerprint,
            "title": art.title,
            "type": art.type,
        }

    git_ref = _resolve_git_ref(root, name)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    data = {
        "name": name,
        "created_at": created_at,
        "git_ref": git_ref,
        "artifacts": snapshot,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "path": str(path),
        "artifact_count": len(snapshot),
        "git_ref": git_ref,
    }


def load_baseline(root: Path, name: str) -> dict[str, Any] | None:
    """Load a baseline by name, or None if not found."""
    path = _baseline_path(root, name)
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def list_baselines(root: Path) -> list[str]:
    """Return sorted list of existing baseline names."""
    d = baseline_dir(root)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.yaml"))


def diff_baselines(root: Path, name_a: str, name_b: str) -> dict[str, Any]:
    """Compare two baselines and report changes from A to B.

    Returns dict with:
      - ok: bool
      - added: artifacts in B but not A
      - removed: artifacts in A but not B
      - status_changed: same ID, different status
      - fingerprint_changed: same ID, same status, different fingerprint
      - (on error) error: str
    """
    baseline_a = load_baseline(root, name_a)
    if baseline_a is None:
        return {"ok": False, "error": f"Baseline '{name_a}' not found"}
    baseline_b = load_baseline(root, name_b)
    if baseline_b is None:
        return {"ok": False, "error": f"Baseline '{name_b}' not found"}

    arts_a = baseline_a.get("artifacts", {}) or {}
    arts_b = baseline_b.get("artifacts", {}) or {}

    added: list[dict[str, str]] = []
    removed: list[dict[str, str]] = []
    status_changed: list[dict[str, str]] = []
    fingerprint_changed: list[dict[str, str]] = []

    for art_id in sorted(set(arts_b) - set(arts_a)):
        entry = arts_b[art_id]
        added.append(
            {
                "id": art_id,
                "status": entry.get("status", ""),
                "title": entry.get("title", ""),
            }
        )

    for art_id in sorted(set(arts_a) - set(arts_b)):
        entry = arts_a[art_id]
        removed.append(
            {
                "id": art_id,
                "status": entry.get("status", ""),
                "title": entry.get("title", ""),
            }
        )

    for art_id in sorted(set(arts_a) & set(arts_b)):
        a = arts_a[art_id]
        b = arts_b[art_id]
        status_a = a.get("status", "")
        status_b = b.get("status", "")
        fp_a = a.get("fingerprint", "")
        fp_b = b.get("fingerprint", "")
        title = b.get("title", a.get("title", ""))

        if status_a != status_b:
            status_changed.append(
                {
                    "id": art_id,
                    "old": status_a,
                    "new": status_b,
                    "title": title,
                }
            )
        elif fp_a != fp_b:
            fingerprint_changed.append(
                {
                    "id": art_id,
                    "status": status_b,
                    "title": title,
                }
            )

    return {
        "ok": True,
        "name_a": name_a,
        "name_b": name_b,
        "added": added,
        "removed": removed,
        "status_changed": status_changed,
        "fingerprint_changed": fingerprint_changed,
    }
