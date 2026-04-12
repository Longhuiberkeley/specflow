"""specflow sequence — Renumber draft IDs to sequential integers.

Run after merging feature branches to main: every `PREFIX-SLUG-hash4` ID is
replaced with `PREFIX-NNN` (continuing from each type's `_index.yaml.next_id`),
and every reference to those IDs across the repo is rewritten in place.
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


def _build_id_map(root: Path, drafts: list[Path]) -> dict[str, str]:
    """Allocate sequential IDs for every draft, grouped by artifact type."""
    by_prefix: dict[str, list[tuple[Path, dict]]] = {}
    for path in drafts:
        fm = draft_lib._read_frontmatter(path) or {}
        draft_id = fm.get("id", "")
        if not draft_id:
            continue
        prefix = art_lib.get_prefix_from_id(draft_id)
        by_prefix.setdefault(prefix, []).append((path, fm))

    id_map: dict[str, str] = {}
    for prefix, entries in by_prefix.items():
        type_name = art_lib.PREFIX_TO_TYPE.get(prefix)
        if not type_name:
            continue
        rel_dir = art_lib.TYPE_TO_DIR.get(type_name)
        if not rel_dir:
            continue
        index_path = root / "_specflow" / rel_dir / "_index.yaml"
        index = art_lib._read_index(index_path)
        next_num = index.get("next_id", 1)

        # Stable ordering so two runs yield identical IDs.
        for path, fm in sorted(entries, key=lambda e: e[1].get("id", "")):
            draft_id = fm["id"]
            new_id = f"{prefix}-{next_num:03d}"
            id_map[draft_id] = new_id
            next_num += 1

        index["next_id"] = next_num
        art_lib._write_index(index_path, index)

    return id_map


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

    # Build the plan first (mutates indexes only when dry-run is False).
    if dry_run:
        # Show a preview without writing; rebuild an ephemeral plan.
        plan: dict[str, str] = {}
        counters: dict[str, int] = {}
        for path in drafts:
            fm = draft_lib._read_frontmatter(path) or {}
            draft_id = fm.get("id", "")
            prefix = art_lib.get_prefix_from_id(draft_id)
            type_name = art_lib.PREFIX_TO_TYPE.get(prefix)
            rel_dir = art_lib.TYPE_TO_DIR.get(type_name or "")
            if not rel_dir:
                continue
            idx_path = root / "_specflow" / rel_dir / "_index.yaml"
            counter = counters.get(prefix)
            if counter is None:
                counter = art_lib._read_index(idx_path).get("next_id", 1)
            plan[draft_id] = f"{prefix}-{counter:03d}"
            counters[prefix] = counter + 1

        print(f"{CYAN}Dry-run: would renumber {len(plan)} draft ID(s){NC}")
        for draft_id, new_id in sorted(plan.items()):
            print(f"  {draft_id} → {new_id}")
        return 0

    id_map = _build_id_map(root, drafts)
    replacements = draft_lib.rewrite_references(root, id_map)
    renamed = _rename_files(root, id_map)
    _refresh_indexes(root)

    print(f"{GREEN}✓ Renumbered {len(id_map)} artifact(s){NC}")
    print(f"  {renamed} file(s) renamed")
    print(f"  {replacements} reference(s) rewritten")
    for draft_id, new_id in sorted(id_map.items()):
        print(f"  {draft_id} → {new_id}")
    return 0
