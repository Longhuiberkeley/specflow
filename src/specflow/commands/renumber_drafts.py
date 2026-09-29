"""specflow renumber-drafts — Renumber draft IDs to sequential integers.

Run on main after merging feature branches: every `PREFIX-SLUG-hash4` ID is
replaced with `PREFIX-NNN` and every reference to those IDs across the repo
is rewritten in place.

Protocol (DEC-093, DDD-034 I5):

1. Refuse on a feature branch (drafts are renumbered once, on main).
2. Under the repo-wide mutation lock, plan from disk and the indexes: each
   type continues from max(ids on disk, quarantined ids, index next_id) + 1.
   Refuse, changing nothing, if any planned target id already exists.
3. Write the plan to ``.specflow/renumber-journal.yaml`` before the first
   change.
4. Rewrite references (each file atomically), rename files without ever
   replacing an existing one, rebuild the touched indexes, delete the
   journal.

A run that crashes at any write resumes from the journal when re-run and
ends in the same state as an uncrashed run
(tests/formal/test_index_store_crash.py, renumber-drafts cases). While the
journal exists, ``create`` treats its planned targets as allocated, so a
create between the crash and the re-run cannot take one (DEF-013,
tests/formal/test_index_store_model_traces.py). The resumed run re-checks
the targets before its first write and refuses, changing nothing, if another
artifact holds one.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import draft_ids as draft_lib
from specflow.lib import locks as locks_lib
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, NC

JOURNAL = Path(".specflow") / "renumber-journal.yaml"


class _Collision(Exception):
    pass


def _plan_id_map(
    root: Path,
    drafts: list[Path],
) -> tuple[dict[str, str], dict[str, tuple[Path, int]]]:
    """Compute the draft-ID → sequential-ID mapping without touching disk.

    Returns (id_map, per_prefix_counters) where per_prefix_counters[prefix]
    is (index_path, next_id after the plan).
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
        target_dir = root / "_specflow" / rel_dir
        index_path = target_dir / "_index.yaml"
        index = art_lib.read_index(index_path)
        next_num = art_lib._highest_allocated(target_dir, prefix, index) + 1

        # Stable ordering so two runs yield identical IDs.
        for path, fm in sorted(entries, key=lambda e: e[1].get("id", "")):
            id_map[fm["id"]] = f"{prefix}-{next_num:03d}"
            next_num += 1

        counters[prefix] = (index_path, next_num)

    return id_map, counters


def _collisions(root: Path, id_map: dict[str, str]) -> list[str]:
    """Planned targets that already exist as a file stem or artifact id."""
    targets = set(id_map.values())
    taken = {md.stem for md in (root / "_specflow").rglob("*.md")} & targets
    taken |= {a.id for a in art_lib.discover_artifacts(root) if a.id in targets}
    inverse = {v: k for k, v in id_map.items()}
    return [f"{t} (planned for {inverse[t]})" for t in sorted(taken)]


def _resume_collisions(root: Path, id_map: dict[str, str]) -> list[str]:
    """Collisions for a resumed run (DEF-013).

    The crashed run may already have rewritten a draft file's frontmatter id
    to its target, or hard-linked/renamed it to ``TARGET.md``; that file is
    the draft's own and is not a collision. Any other file whose stem or
    frontmatter id is a planned target is one: rewriting references to that
    id would re-bind links to an unrelated artifact.
    """
    spec = root / "_specflow"
    inverse = {v: k for k, v in id_map.items()}
    draft_files: dict[str, Path] = {}
    for md in spec.rglob("*.md"):
        if md.stem in id_map:
            draft_files[id_map[md.stem]] = md

    def owned(target: str, path: Path) -> bool:
        own = draft_files.get(target)
        if own is None:
            # rename finished: TARGET.md is the draft's file
            return path.stem == target
        try:
            return os.path.samefile(own, path)
        except OSError:
            return False

    taken: set[str] = set()
    for md in spec.rglob("*.md"):
        if md.name.startswith(("_", ".")):
            continue
        if md.stem in inverse and not owned(md.stem, md):
            taken.add(md.stem)
    for art in art_lib.discover_artifacts(root):
        if art.id in inverse and not owned(art.id, art.path):
            taken.add(art.id)
    return [f"{t} (planned for {inverse[t]})" for t in sorted(taken)]


def _rename_files(root: Path, id_map: dict[str, str]) -> int:
    """Rename draft-named files; never replace an existing file.

    Link-then-unlink: a crash in between leaves both names on one inode,
    which the resumed run recognises and finishes.
    """
    renamed = 0
    for md in sorted((root / "_specflow").rglob("*.md")):
        if md.stem not in id_map:
            continue
        new_path = md.with_name(f"{id_map[md.stem]}.md")
        if new_path.exists():
            if os.path.samefile(md, new_path) or new_path.read_bytes() == md.read_bytes():
                md.unlink()  # resumed: the link already happened
                renamed += 1
                continue
            raise _Collision(f"{new_path.relative_to(root)} already exists")
        try:
            os.link(md, new_path)
        except FileExistsError:
            raise _Collision(f"{new_path.relative_to(root)} already exists") from None
        except OSError:
            os.rename(md, new_path)  # no hard links here; existence checked above
        else:
            md.unlink()
        renamed += 1
    return renamed


def _types_of(root: Path, paths: list[Path]) -> set[str]:
    types: set[str] = set()
    for path in paths:
        rel = path.relative_to(root / "_specflow").as_posix() if (root / "_specflow") in path.parents else ""
        for type_name, rel_dir in art_lib.TYPE_TO_DIR.items():
            if rel.startswith(rel_dir.rstrip("/") + "/"):
                types.add(type_name)
    return types


def _apply(root: Path, id_map: dict[str, str], journal_path: Path) -> tuple[int, int]:
    touched: list[Path] = []
    replacements = draft_lib.rewrite_references(root, id_map, touched=touched)
    renamed = _rename_files(root, id_map)
    types = _types_of(root, touched)
    for new_id in id_map.values():
        type_name = art_lib.PREFIX_TO_TYPE.get(art_lib.get_prefix_from_id(new_id))
        if type_name:
            types.add(type_name)
    for type_name in sorted(types):
        art_lib.rebuild_index(root, type_name)
    journal_path.unlink()
    return replacements, renamed


def _run_locked(root: Path, dry_run: bool) -> int:
    journal_path = root / JOURNAL
    resumed = False
    if journal_path.exists():
        journal = yaml.safe_load(journal_path.read_text(encoding="utf-8")) or {}
        id_map = dict(journal.get("id_map") or {})
        resumed = True
    else:
        drafts = draft_lib.enumerate_draft_artifacts(root)
        if not drafts:
            print(f"{GREEN}✓ No draft IDs found — nothing to renumber.{NC}")
            return 0
        id_map, _counters = _plan_id_map(root, drafts)
        collisions = _collisions(root, id_map)
        if collisions:
            print(f"{RED}✗ Refusing to renumber: target ID already exists: "
                  f"{', '.join(collisions)}. Nothing was changed.{NC}")
            return 1

    if dry_run:
        verb = "resume" if resumed else "renumber"
        print(f"{CYAN}Dry-run: would {verb} {len(id_map)} draft ID(s){NC}")
        for draft_id, new_id in sorted(id_map.items()):
            print(f"  {draft_id} → {new_id}")
        return 0

    if not resumed:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        locks_lib.atomic_write(
            journal_path,
            yaml.dump({"started": stamp, "id_map": id_map},
                      default_flow_style=False, sort_keys=True),
        )
    else:
        collisions = _resume_collisions(root, id_map)
        if collisions:
            print(f"{RED}✗ Refusing to resume the renumber: target ID already taken by "
                  f"another artifact: {', '.join(collisions)}. Nothing was changed; the "
                  f"journal {JOURNAL.as_posix()} is kept. Renumber or remove the other "
                  f"artifact, then re-run.{NC}")
            return 1
        print(f"{YELLOW}Resuming an interrupted renumber from {JOURNAL.as_posix()}{NC}")

    try:
        replacements, renamed = _apply(root, id_map, journal_path)
    except _Collision as exc:
        print(f"{RED}✗ Renumber stopped: {exc}. The journal {JOURNAL.as_posix()} is kept; "
              f"resolve the collision and re-run.{NC}")
        return 1

    print(f"{GREEN}✓ Renumbered {len(id_map)} artifact(s){NC}")
    print(f"  {renamed} file(s) renamed")
    print(f"  {replacements} reference(s) rewritten")
    for draft_id, new_id in sorted(id_map.items()):
        print(f"  {draft_id} → {new_id}")
    return 0


def run(root: Path, args: dict) -> int:
    root = root.resolve()
    dry_run = bool(args.get("dry_run"))

    if not dry_run and draft_lib.is_feature_branch(root):
        branch = draft_lib.current_branch(root)
        print(f"{RED}✗ renumber-drafts runs on main after the merge; '{branch}' is a "
              f"feature branch, where draft IDs are expected. Nothing was changed.{NC}")
        return 1

    try:
        with locks_lib.mutation_lock(root, holder="renumber-drafts"):
            return _run_locked(root, dry_run)
    except locks_lib.MutationLockTimeout as exc:
        print(f"{RED}✗ {exc}; retry when it finishes ('specflow locks' shows it).{NC}")
        return 1
