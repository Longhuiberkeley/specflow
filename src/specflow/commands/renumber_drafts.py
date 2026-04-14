"""specflow renumber-drafts — Renumber draft IDs to sequential integers.

Run after merging feature branches to main: every `PREFIX-SLUG-hash4` ID is
replaced with `PREFIX-NNN` (continuing from each type's `_index.yaml.next_id`),
and every reference to those IDs across the repo is rewritten in place.

Operation is atomic with respect to on-disk state: the planning phase is
read-only, then file content rewrites happen, then file renames, and only
after all of that do the per-type indexes advance. A crash in any earlier
step leaves indexes pointing at their pre-run values so re-running is safe.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import draft_ids as draft_lib

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"


def _plan_id_map(
    root: Path,
    drafts: list[Path],
) -> tuple[dict[str, str], dict[str, tuple[Path, int]]]:
    """Compute the draft-ID → sequential-ID mapping without touching disk.

    Returns (id_map, per_prefix_counters) where per_prefix_counters[prefix]
    is (index_path, new_next_id) — fed to _commit_indexes after all file
    operations succeed.
    """
    by_prefix: dict[str, list[tuple[Path, dict]]] = {}
    for path in drafts:
        fm = draft_lib.read_frontmatter(path) or {}
        draft_id = fm.get("id", "")
        if not draft_id:
            continue
        prefix = art_lib.get_prefix_from_id(draft_id)
        by_prefix.setdefault(prefix, []).append((path, fm))

    id_map: dict[str, str] = {}
    counters: dict[str, tuple[Path, int]] = {}
    for prefix, entries in by_prefix.items():
        type_name = art_lib.PREFIX_TO_TYPE.get(prefix)
        if not type_name:
            continue
        rel_dir = art_lib.TYPE_TO_DIR.get(type_name)
        if not rel_dir:
            continue
        index_path = root / "_specflow" / rel_dir / "_index.yaml"
        index = art_lib.read_index(index_path)
        next_num = index.get("next_id", 1)

        # Stable ordering so two runs yield identical IDs.
        for path, fm in sorted(entries, key=lambda e: e[1].get("id", "")):
            draft_id = fm["id"]
            new_id = f"{prefix}-{next_num:03d}"
            id_map[draft_id] = new_id
            next_num += 1

        counters[prefix] = (index_path, next_num)

    return id_map, counters


def _commit_indexes(counters: dict[str, tuple[Path, int]]) -> None:
    """Advance each touched index's next_id. Called last so a crash earlier
    leaves indexes at their original values."""
    for _prefix, (index_path, next_num) in counters.items():
        index = art_lib.read_index(index_path)
        index["next_id"] = next_num
        art_lib.write_index(index_path, index)


def _rename_files(root: Path, id_map: dict[str, str]) -> int:
    renamed = 0
    specflow_dir = root / "_specflow"
    for md in list(specflow_dir.rglob("*.md")):
        stem = md.stem
        if stem in id_map:
            new_path = md.with_name(f"{id_map[stem]}.md")
            md.rename(new_path)
            renamed += 1
    return renamed


def _refresh_indexes(root: Path) -> None:
    specflow_dir = root / "_specflow"
    for index_path in specflow_dir.rglob("_index.yaml"):
        try:
            data = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        artifacts = data.get("artifacts") or {}
        rebuilt: dict[str, dict] = {}
        for key, meta in artifacts.items():
            if not isinstance(meta, dict):
                continue
            meta_id = meta.get("id") or key
            rebuilt[meta_id] = {**meta, "id": meta_id}
        data["artifacts"] = rebuilt
        index_path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )


def run(root: Path, args: dict) -> int:
    root = root.resolve()
    dry_run = bool(args.get("dry_run"))

    drafts = draft_lib.enumerate_draft_artifacts(root)
    if not drafts:
        print(f"{GREEN}✓ No draft IDs found — nothing to renumber.{NC}")
        return 0

    id_map, counters = _plan_id_map(root, drafts)

    if dry_run:
        print(f"{CYAN}Dry-run: would renumber {len(id_map)} draft ID(s){NC}")
        for draft_id, new_id in sorted(id_map.items()):
            print(f"  {draft_id} → {new_id}")
        return 0

    replacements = draft_lib.rewrite_references(root, id_map)
    renamed = _rename_files(root, id_map)
    _commit_indexes(counters)
    _refresh_indexes(root)

    print(f"{GREEN}✓ Renumbered {len(id_map)} artifact(s){NC}")
    print(f"  {renamed} file(s) renamed")
    print(f"  {replacements} reference(s) rewritten")
    for draft_id, new_id in sorted(id_map.items()):
        print(f"  {draft_id} → {new_id}")
    return 0
