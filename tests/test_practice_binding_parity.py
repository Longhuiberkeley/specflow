"""One applicability predicate for ``artifact-lint`` bp-application and ``brief``.

``practices.in_scope_bindings`` owns scope, the provenance-stamp skip (DEC-089),
the DEC-authorized tailoring drop, and the backfill grace. Both renderers must
derive their counts from it so they can never disagree on what "in-scope" means.
Fixture-based (stamped BP, unstamped BP, grace-exempt pair, bound legacy pair),
never the live corpus.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import practices as practices_lib

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_TYPES = ("requirement", "architecture", "story", "best-practice", "decision")

_BP_BODY = (
    "## Practice\nDo the thing.\n\n## Applies when\nAlways.\n\n"
    "## Work products\nThe artifact.\n\n## Verification\nInspect.\n\n## Rationale\nIt helps."
)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True)
    for art_type in _SCHEMA_TYPES:
        source = _REPO_ROOT / "src/specflow/templates/schemas" / f"{art_type}.yaml"
        (schema_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (root / ".specflow/config.yaml").write_text(
        yaml.safe_dump({"project": {"name": "parity"}, "active_packs": []}), encoding="utf-8"
    )
    for art_type in _SCHEMA_TYPES:
        (root / "_specflow" / art_lib.TYPE_TO_DIR[art_type]).mkdir(parents=True, exist_ok=True)
    return root


def _write(root: Path, artifact_id: str, art_type: str, *, status="approved",
           links=None, body="Body.", **extra) -> Path:
    path = root / "_specflow" / art_lib.TYPE_TO_DIR[art_type] / f"{artifact_id}.md"
    fm = {"id": artifact_id, "title": artifact_id, "type": art_type, "status": status,
          "created": "2026-01-01", "links": links or []}
    fm.update(extra)
    path.write_text(f"---\n{yaml.safe_dump(fm, sort_keys=False)}---\n\n{body}\n", encoding="utf-8")
    return path


def _bp(root: Path, bp_id: str, **extra) -> Path:
    fields = {"provenance": "learned", "applicability": {"always": True},
              "strength": "recommended", "verification_method": "inspection",
              "modified": "2025-12-01"}
    fields.update(extra)
    return _write(root, bp_id, "best-practice", body=_BP_BODY, **fields)


def _counts_from_helper(root: Path, artifacts):
    counts = {t: {"bound": 0, "unbound": 0, "exempt": 0}
              for t in practices_lib.BINDING_TARGET_TYPES}
    for target, _bp_art, bound, exempt in practices_lib.in_scope_bindings(root, artifacts):
        bucket = "exempt" if exempt else ("bound" if bound else "unbound")
        counts[target.type][bucket] += 1
    return counts


def _seed_fixture(root: Path) -> None:
    _bp(root, "BP-001")                                      # stamped, in scope
    _bp(root, "BP-002", provenance=None)                     # unstamped → exempt
    _bp(root, "BP-003", modified="2026-06-01")               # newer than legacy targets
    _write(root, "DEC-001", "decision")
    _bp(root, "BP-004", tailoring={"status": "dropped", "rationale": "n/a", "dec": "DEC-001"})
    # REQ-001: created after every BP → in scope for BP-001 and BP-003; bound to BP-001.
    _write(root, "REQ-001", "requirement", created="2026-07-01",
           links=[{"target": "BP-001", "role": "guided_by"}])
    # REQ-002: legacy (created before BP-003) → grace for BP-003, unbound for BP-001.
    _write(root, "REQ-002", "requirement", created="2026-01-01", modified="2026-09-30")
    # ARCH-001: legacy but explicitly bound to BP-003 → counted, not graced.
    _write(root, "ARCH-001", "architecture", created="2026-01-01",
           links=[{"target": "BP-003", "role": "guided_by"}])
    # STORY-001: in scope for both stamped BPs, bound to neither.
    _write(root, "STORY-001", "story", created="2026-07-01")


def test_in_scope_bindings_classifies_every_pair(project_root: Path):
    _seed_fixture(project_root)
    artifacts = art_lib.discover_artifacts(project_root)

    rows = {(t.id, b.id): (bound, exempt)
            for t, b, bound, exempt in practices_lib.in_scope_bindings(project_root, artifacts)}

    assert not any(bp == "BP-004" for _, bp in rows), "DEC-dropped BP produces no rows"
    assert rows[("REQ-001", "BP-002")] == (False, practices_lib.EXEMPT_UNSTAMPED)
    assert rows[("REQ-001", "BP-001")] == (True, None)
    assert rows[("REQ-001", "BP-003")] == (False, None)
    assert rows[("REQ-002", "BP-001")] == (False, None)
    assert rows[("REQ-002", "BP-003")] == (False, practices_lib.EXEMPT_GRACE)
    assert rows[("ARCH-001", "BP-003")] == (True, None), "bound pairs are never graced"
    assert rows[("ARCH-001", "BP-001")] == (False, None)
    assert rows[("STORY-001", "BP-001")] == (False, None)
    assert rows[("STORY-001", "BP-003")] == (False, None)


def test_lint_coverage_lines_equal_helper_counts(project_root: Path):
    _seed_fixture(project_root)
    artifacts = art_lib.discover_artifacts(project_root)
    counts = _counts_from_helper(project_root, artifacts)

    result = lint_cmd._run_check(artifacts, project_root, "bp-application")

    assert counts["requirement"] == {"bound": 1, "unbound": 2, "exempt": 3}
    for art_type, c in counts.items():
        total = c["bound"] + c["unbound"]
        assert (f"{art_type}: {c['bound']}/{total} in-scope BP binding(s) bound; "
                f"{c['unbound']} unbound") in result["detail"]
    assert result["warning_count"] == sum(c["unbound"] for c in counts.values())
    assert "BP-002" not in result["detail"] and "BP-004" not in result["detail"]
    assert "[REQ-002] in-scope BP BP-003" not in result["detail"]


def test_helper_matches_per_target_loader_semantics(project_root: Path):
    """The batched filter is the loader's semantics, one parse instead of N."""
    _seed_fixture(project_root)
    artifacts = art_lib.discover_artifacts(project_root)
    by_target: dict[str, set[str]] = {}
    for target, bp, _bound, _exempt in practices_lib.in_scope_bindings(project_root, artifacts):
        by_target.setdefault(target.id, set()).add(bp.id)
    for target in artifacts:
        if target.type not in practices_lib.BINDING_TARGET_TYPES:
            continue
        loaded = {bp.id for bp in practices_lib.load_active_best_practices(project_root, target)}
        assert by_target.get(target.id, set()) == loaded - {"BP-004"}


def test_lifecycle_date_accepts_quoted_and_bare_yaml_dates(tmp_path: Path):
    quoted = art_lib.Artifact.__new__(art_lib.Artifact)
    quoted.frontmatter = {"created": "2026-04-10", "modified": "2026-10-08"}
    bare = art_lib.Artifact.__new__(art_lib.Artifact)
    bare.frontmatter = {"created": yaml.safe_load("2026-04-10")}
    junk = art_lib.Artifact.__new__(art_lib.Artifact)
    junk.frontmatter = {"created": "soon", "modified": ""}

    assert practices_lib.lifecycle_date(quoted) == practices_lib.lifecycle_date(bare)
    assert practices_lib.lifecycle_date(quoted, ("modified", "created")).isoformat() == "2026-10-08"
    assert practices_lib.lifecycle_date(junk) is None
