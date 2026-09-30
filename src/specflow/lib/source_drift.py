"""Source-drift fingerprint store (``.specflow/source-fingerprints.yaml``).

artifact-lint only READS this store (REQ-053 AC2). It is written by
``init``/``refresh`` when absent and by ``specflow fingerprint-refresh
--source`` (the explicit seed/re-accept command, REQ-053 AC9), always
through the mutation-lock write primitive.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import files as files_lib
from specflow.lib import locks

Store = dict[str, dict[str, str]]


def hash_file(path: Path) -> str:
    """First 16 hex chars of the SHA-256 of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def store_path(root: Path) -> Path:
    return root / files_lib.SOURCE_FP_FILE


def load_store(root: Path) -> Store:
    path = store_path(root)
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def current_hashes(root: Path, art: art_lib.Artifact) -> dict[str, str]:
    """``{relative path: hash}`` for an artifact's output_files, in sorted
    path order (independent of set iteration / PYTHONHASHSEED)."""
    output_files = art.frontmatter.get("output_files")
    if not output_files or not isinstance(output_files, list):
        return {}
    resolved_root = root.resolve()
    hashes: dict[str, str] = {}
    for resolved in files_lib.expand_output_files(root, output_files):
        try:
            rel = str(resolved.relative_to(resolved_root))
        except ValueError:
            rel = str(resolved)
        hashes[rel] = hash_file(resolved)
    return dict(sorted(hashes.items()))


def seed(
    root: Path,
    artifacts: list[art_lib.Artifact] | None = None,
    *,
    ids: list[str] | None = None,
    all_: bool = False,
) -> list[str]:
    """Record current output_files hashes; return the artifact ids written.

    Default: add entries only for artifacts missing from the store (never
    overwrite an accepted hash). ``ids``: re-accept current hashes for those
    artifacts. ``all_``: re-seed every artifact.
    """
    if artifacts is None:
        artifacts = art_lib.discover_artifacts(root)
    with locks.mutation_lock(root):
        stored = load_store(root)
        wanted = set(ids or [])
        written: list[str] = []
        for art in sorted(artifacts, key=lambda a: a.id):
            if ids is not None and art.id not in wanted:
                continue
            if ids is None and not all_ and art.id in stored:
                continue
            hashes = current_hashes(root, art)
            if not hashes:
                continue
            stored[art.id] = hashes
            written.append(art.id)
        if written:
            locks.atomic_write(
                store_path(root),
                yaml.dump(stored, default_flow_style=False, sort_keys=True),
            )
    return written
