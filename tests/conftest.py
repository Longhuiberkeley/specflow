"""Shared test helpers (STORY-718).

Importable from any test module as ``from conftest import ...`` (pytest puts
``tests/`` on ``sys.path`` because the directory has no ``__init__.py``).

Two things live here:

* ``DOGFOOD_SEED_BP_IDS`` / ``shipped_dogfood_seed_bps()`` — the shipped dogfood
  best-practices that were generated from the seed catalogue (BP-002..BP-007).
  Learned practices such as BP-008 are deliberately excluded: they carry extra
  sections and are not seed-equivalent, and a glob-then-exact-set check made
  four tests skip silently from the day BP-008 landed.
* ``write_artifact`` — scaffolds a fixture artifact through the production
  writer (``art_lib.create_artifact``) so the directory index, fingerprint and
  frontmatter shape are exactly what the CLI would produce. Fixtures that must
  be *invalid* on purpose (a status the schema rejects) write their file by
  hand in the test that needs them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib

REPO_ROOT = Path(__file__).resolve().parents[1]

# The seed-generated dogfood practices (DEC-058). Keep in lockstep with
# ``practices_seed.GENERIC_PRACTICES`` when a seed is added or retired.
DOGFOOD_SEED_BP_IDS: frozenset[str] = frozenset(f"BP-{index:03}" for index in range(2, 8))


def shipped_dogfood_seed_bps(root: Path = REPO_ROOT) -> list[art_lib.Artifact]:
    """Parse the shipped seed-generated dogfood BPs, asserting each one exists."""
    bp_dir = root / "_specflow" / "specs" / "best-practices"
    practices: list[art_lib.Artifact] = []
    for bp_id in sorted(DOGFOOD_SEED_BP_IDS):
        path = bp_dir / f"{bp_id}.md"
        assert path.exists(), f"shipped dogfood practice missing: {path}"
        practice = art_lib.parse_artifact(path)
        assert practice is not None, f"shipped dogfood practice unparseable: {path}"
        practices.append(practice)
    return practices


def write_artifact(
    root: Path,
    artifact_id: str,
    art_type: str,
    title: str,
    status: str = "draft",
    body: str = "",
    links: list[dict] | None = None,
    extra_fm: dict | None = None,
    tags: list[str] | None = None,
) -> Path:
    """Create a fixture artifact with the production writer and return its path.

    Extra frontmatter keys go through ``create_artifact``'s ``**kwargs`` path —
    the same path ``specflow create --set KEY=VALUE`` uses — so a value the
    writer would refuse is refused here too. Raises when the writer reports an
    error (unknown type, status outside the schema, duplicate id).
    """
    _forget_artifact(root, art_type, artifact_id)
    extra: dict[str, Any] = dict(extra_fm or {})
    if tags is None:
        tags = extra.pop("tags", None)
    else:
        extra.pop("tags", None)
    for reserved in ("id", "type", "title", "status"):
        extra.pop(reserved, None)
    result = art_lib.create_artifact(
        root,
        art_type,
        title,
        status=status,
        tags=tags,
        links=links or [],
        body=body,
        artifact_id=artifact_id,
        **extra,
    )
    assert result.get("ok"), f"write_artifact({artifact_id}): {result.get('error')}"
    return Path(result["path"])


def _forget_artifact(root: Path, art_type: str, artifact_id: str) -> None:
    """Drop a fixture artifact (file + index entry) so it can be re-written.

    Fixtures sometimes re-create an artifact with new fields; the production
    writer refuses duplicate ids, so an upsert needs the old one gone first.
    Runs under the repo-wide mutation lock like every production index writer.
    """
    from specflow.lib import locks as locks_lib

    rel_dir = art_lib.TYPE_TO_DIR.get(art_lib.normalize_type(art_type), "")
    if not rel_dir:
        return
    target_dir = root / "_specflow" / rel_dir
    file_path = target_dir / f"{artifact_id}.md"
    index_path = target_dir / "_index.yaml"
    if not file_path.exists() and not index_path.exists():
        return
    with locks_lib.mutation_lock(root, holder=f"test-forget:{artifact_id}"):
        if file_path.exists():
            file_path.unlink()
        if index_path.exists():
            index_data = art_lib._read_index(index_path)
            if artifact_id in index_data.get("artifacts", {}):
                del index_data["artifacts"][artifact_id]
                art_lib._write_index(index_path, index_data)
