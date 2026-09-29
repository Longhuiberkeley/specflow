"""Shared fixtures for the index-store formal harness (STORY-696, DDD-034).

Scaffolds a throwaway project from the shipped schemas, snapshots its state
for convergence comparison (I5), and checks the quiescent invariants I1-I4 on
real files. Not a test module (no ``test_`` prefix).
"""

from __future__ import annotations

import collections
import re
import shutil
from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "src" / "specflow" / "templates" / "schemas"
DDD_034 = REPO / "_specflow" / "specs" / "detailed-design" / "DDD-034.md"

TYPES = ("requirement", "story", "unit-test", "best-practice")

_TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}[:-]\d{2}[:-]\d{2}Z")


def scaffold(base: Path, name: str = "p") -> Path:
    """A minimal project: shipped schemas for TYPES, config, state, dirs."""
    root = base / name
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True)
    for t in TYPES:
        shutil.copy(SCHEMAS / f"{t}.yaml", schema_dir / f"{t}.yaml")
        (root / "_specflow" / art_lib.TYPE_TO_DIR[t]).mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "formal"}, "active_packs": []}), encoding="utf-8"
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "executing", "history": []}), encoding="utf-8"
    )
    return root


def type_dir(root: Path, artifact_type: str) -> Path:
    return root / "_specflow" / art_lib.TYPE_TO_DIR[artifact_type]


def index_of(root: Path, artifact_type: str) -> dict:
    path = type_dir(root, artifact_type) / "_index.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def snapshot(root: Path) -> dict[str, str]:
    """Normalised file state: relative path -> text.

    Excludes lock files and temp debris; timestamps (impact-log names and
    fields, quarantine stamps) are normalised so two uncrashed runs compare
    equal.
    """
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith(".specflow/locks/") or ".tmp" in p.name:
            continue
        if rel == ".specflow/renumber-journal.yaml":
            # A journal left behind is itself a divergence; keep it visible.
            pass
        text = p.read_text(encoding="utf-8", errors="replace")
        out[_TS.sub("<TS>", rel)] = _TS.sub("<TS>", text)
    return out


def ids_on_disk(root: Path) -> collections.Counter:
    """Frontmatter ids of every artifact file under _specflow/ (nested too)."""
    ids: collections.Counter = collections.Counter()
    for md in (root / "_specflow").rglob("*.md"):
        if md.name.startswith("_"):
            continue
        art = art_lib.parse_artifact(md)
        if art is not None and art.id:
            ids[art.id] += 1
    return ids


def _canonical_num(art_id: str, prefix: str) -> int | None:
    m = re.fullmatch(rf"{re.escape(prefix)}-(\d+)", art_lib.get_base_id(art_id))
    return int(m.group(1)) if m else None


def invariant_violations(root: Path, allocated: dict[str, set[str]] | None = None) -> list[str]:
    """Quiescent checks: I1 (no duplicate id) and I4 (index is a faithful
    cache: keys == ids on disk; next_id above every allocated id, including
    quarantined ones). ``allocated`` optionally adds ids known to have been
    handed out (I3 history variable)."""
    problems: list[str] = []
    dupes = [i for i, c in ids_on_disk(root).items() if c > 1]
    if dupes:
        problems.append(f"I1 duplicate ids on disk: {sorted(dupes)}")
    for t in TYPES:
        d = type_dir(root, t)
        prefix = art_lib.TYPE_TO_PREFIX[t]
        disk = set()
        for md in d.rglob("*.md"):
            if md.name.startswith("_"):
                continue
            art = art_lib.parse_artifact(md)
            if art is not None and art.id:
                disk.add(art.id)
        idx_path = d / "_index.yaml"
        if not idx_path.exists():
            if disk:
                problems.append(f"I4 {t}: files on disk but no index")
            continue
        try:
            idx = yaml.safe_load(idx_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            problems.append(f"I4 {t}: index unparsable ({exc.__class__.__name__})")
            continue
        keys = set((idx.get("artifacts") or {}).keys())
        if keys != disk:
            problems.append(
                f"I4 {t}: index keys != disk ids (missing {sorted(disk - keys)}, "
                f"extra {sorted(keys - disk)})"
            )
        q_path = d / "_index.quarantine.yaml"
        quarantined = set()
        if q_path.exists():
            quarantined = set((yaml.safe_load(q_path.read_text(encoding="utf-8")) or {}).keys())
        seen = disk | quarantined | set((allocated or {}).get(t, set()))
        nums = [n for n in (_canonical_num(i, prefix) for i in seen) if n is not None]
        if nums and int(idx.get("next_id", 0) or 0) <= max(nums):
            problems.append(f"I4 {t}: next_id {idx.get('next_id')} <= max allocated {max(nums)}")
    return problems


def invariant_names() -> list[tuple[str, str]]:
    """(I<n>, Name) pairs parsed from DDD-034's '## Invariants' section."""
    text = DDD_034.read_text(encoding="utf-8")
    section = text.split("## Invariants", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"^- (I\d+) (\w+):", section, flags=re.M)
