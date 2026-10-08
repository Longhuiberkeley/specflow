"""Corpus test for every shipped checklist (STORY-687).

Every checklist SpecFlow ships — core templates and pack-provided checklists —
must parse, carry at least one item, give every automated item a script, scope
per-artifact automated scripts to the artifact under review (``"$1"``), and be
reachable by a loader. A checklist that fails any of these silently drops its
items (story-writing.yaml was unparseable for several releases), so the corpus
is enforced deterministically here.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from specflow.lib import checklists as ckl
from specflow.lib import lint as lint_lib
from specflow.lib.artifacts import Artifact

_SRC = Path(__file__).resolve().parent.parent / "src" / "specflow"
_TEMPLATES = _SRC / "templates" / "checklists"


def _shipped_files() -> list[Path]:
    files = sorted(_TEMPLATES.rglob("*.yaml"))
    for pack_dir in sorted((_SRC / "packs").glob("*/")):
        for ck_dir in pack_dir.rglob("checklists"):
            if ck_dir.is_dir():
                files.extend(sorted(ck_dir.rglob("*.yaml")))
    return files


_FILES = _shipped_files()
_IDS = [str(p.relative_to(_SRC)) for p in _FILES]

# Categories whose automated scripts run once per artifact under review and so
# must reference the artifact path ("$1"). Phase gates are project-wide by design.
_PER_ARTIFACT_CATEGORIES = {"in-process", "review", "domain"}


def _category(path: Path) -> str:
    return path.parent.name


def test_corpus_is_nonempty():
    assert len(_FILES) >= 20


@pytest.mark.parametrize("path", _FILES, ids=_IDS)
def test_checklist_parses_with_items(path: Path):
    errors: list[str] = []
    items = ckl.parse_checklist_file(path, errors)
    assert errors == [], f"{path} failed to parse: {errors}"
    assert len(items) >= 1, f"{path} has no items"
    for item in items:
        assert item.id, f"{path}: item without id"
        assert item.check, f"{path}: {item.id} has no check text"
        assert item.severity in {"blocking", "warning", "info"}, f"{path}: {item.id} bad severity"


@pytest.mark.parametrize("path", _FILES, ids=_IDS)
def test_automated_items_have_scripts(path: Path):
    for item in ckl.parse_checklist_file(path):
        if item.automated:
            assert item.script and item.script.strip(), f"{path}: {item.id} is automated but has no script"
        else:
            assert item.llm_prompt or item.check, f"{path}: {item.id} agent-judged without guidance"


@pytest.mark.parametrize("path", _FILES, ids=_IDS)
def test_per_artifact_scripts_reference_the_artifact(path: Path):
    if _category(path) not in _PER_ARTIFACT_CATEGORIES:
        pytest.skip("project-wide category")
    for item in ckl.parse_checklist_file(path):
        if item.automated:
            assert '"$1"' in (item.script or ""), (
                f"{path}: {item.id} is a per-artifact automated item but its script does not "
                f'reference "$1" — make it artifact-scoped or automated: false'
            )


def _reachable(path: Path) -> bool:
    category = _category(path)
    stem = path.stem
    if category == "in-process":
        return stem in ckl.TYPE_CHECKLIST_TYPE_MAP.values()
    if category == "review":
        return stem in ckl.REVIEW_CHECKLIST_TYPE_MAP.values()
    if category == "learned":
        return stem.startswith("PREV-")
    # phase-gates are loaded by transition name (checklist-run --gate,
    # artifact-lint --type gate --gate); domain/ by the configured domain name;
    # shared/ by glob with tag/type matching.
    return category in {"phase-gates", "domain", "shared"}


@pytest.mark.parametrize("path", _FILES, ids=_IDS)
def test_checklist_is_reachable_by_a_loader(path: Path):
    assert _reachable(path), f"{path} is not read by any checklist loader"


@pytest.mark.parametrize("path", _FILES, ids=_IDS)
def test_declared_types_route_to_this_checklist(path: Path):
    """A type-scoped in-process/review checklist is what the loader picks for each declared type."""
    category = _category(path)
    type_map = {
        "in-process": ckl.TYPE_CHECKLIST_TYPE_MAP,
        "review": ckl.REVIEW_CHECKLIST_TYPE_MAP,
    }.get(category)
    if type_map is None:
        pytest.skip("not type-routed")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for art_type in (data.get("applies_to") or {}).get("types") or []:
        assert type_map.get(art_type) == path.stem, f"{path}: type {art_type} does not route here"


def test_item_ids_unique_across_corpus():
    seen: dict[str, Path] = {}
    for path in _FILES:
        for item in ckl.parse_checklist_file(path):
            assert item.id not in seen, f"duplicate item id {item.id} in {path} and {seen[item.id]}"
            seen[item.id] = path


# ---------------------------------------------------------------------------
# Targeted content assertions (STORY-687 AC1-AC3)
# ---------------------------------------------------------------------------

def _items(rel: str) -> dict[str, ckl.ChecklistItem]:
    return {i.id: i for i in ckl.parse_checklist_file(_TEMPLATES / rel)}


def _story_writing_script() -> str:
    item = _items("in-process/story-writing.yaml")["CKL-IP-004-01"]
    assert item.automated
    return item.script or ""


def test_story_writing_spec_link_check_has_no_python():
    script = _story_writing_script()
    assert "python" not in script
    assert "yaml" not in script.lower()
    assert "grep" in script


def _run_story_script(tmp_path: Path, text: str) -> int:
    f = tmp_path / "STORY-001.md"
    f.write_text(text, encoding="utf-8")
    return subprocess.run(
        ["bash", "-c", _story_writing_script(), "--", str(f)],
        capture_output=True, text=True, timeout=30,
    ).returncode


@pytest.mark.parametrize("role", ["implements", "guided_by", "specified_by"])
def test_story_writing_passes_with_spec_link(tmp_path: Path, role: str):
    text = (
        "---\nid: STORY-001\ntype: story\nstatus: draft\nlinks:\n"
        f"- target: REQ-001\n  role: {role}\ncreated: '2026-01-01'\n---\n\n# S\n"
    )
    assert _run_story_script(tmp_path, text) == 0


def test_story_writing_passes_with_indented_and_quoted_links(tmp_path: Path):
    text = (
        "---\nid: STORY-001\nlinks:\n  - target: REQ-001\n    role: 'implements'\n"
        "status: draft\n---\n\n# S\n"
    )
    assert _run_story_script(tmp_path, text) == 0


def test_story_writing_passes_with_flow_style_links(tmp_path: Path):
    text = "---\nid: STORY-001\nlinks: [{target: REQ-001, role: implements}]\n---\n\n# S\n"
    assert _run_story_script(tmp_path, text) == 0


def test_story_writing_fails_without_spec_link(tmp_path: Path):
    text = (
        "---\nid: STORY-001\ntype: story\nlinks:\n- target: STORY-002\n  role: depends_on\n"
        "status: draft\n---\n\n# S\n"
    )
    assert _run_story_script(tmp_path, text) == 1


def test_story_writing_fails_with_no_links(tmp_path: Path):
    text = "---\nid: STORY-001\ntype: story\nlinks: []\n---\n\n# S\n"
    assert _run_story_script(tmp_path, text) == 1


def test_story_writing_ignores_roles_outside_links_block(tmp_path: Path):
    # A spec role mentioned in another frontmatter key or the body is not a link.
    text = (
        "---\nid: STORY-001\nlinks: []\nnotes:\n  role: implements\n---\n\n"
        "links:\n- target: REQ-001\n  role: implements\n"
    )
    assert _run_story_script(tmp_path, text) == 1


def test_story_writing_near_miss_role_does_not_count(tmp_path: Path):
    text = "---\nid: STORY-001\nlinks:\n- target: REQ-001\n  role: implements_partially\n---\n"
    assert _run_story_script(tmp_path, text) == 1


def test_requirement_acceptance_item_is_agent_judged():
    item = _items("in-process/requirement-writing.yaml")["CKL-IP-001-03"]
    assert item.automated is False
    assert item.llm_prompt
    assert item.script is None


def test_embedded_safety_linkage_is_agent_judged_warning():
    item = _items("domain/embedded.yaml")["CKL-DOM-EMB-01"]
    assert item.automated is False
    assert item.llm_prompt
    assert item.severity == "warning"


def test_status_legality_gate_items_are_agent_judged():
    gate5 = _items("phase-gates/executing-to-verifying.yaml")
    gate6 = _items("phase-gates/verifying-to-complete.yaml")
    for item in (gate5["CKL-GATE-005-01"], gate5["CKL-GATE-005-03"], gate6["CKL-GATE-006-01"]):
        assert item.automated is False, item.id
        assert item.llm_prompt, item.id


def test_duplicate_full_lint_gate_item_removed():
    assert "CKL-GATE-006-05" not in _items("phase-gates/verifying-to-complete.yaml")


def test_readiness_templates_removed():
    assert not (_TEMPLATES / "readiness").exists()


# ---------------------------------------------------------------------------
# Loader behaviour: test types reach implementation-review (STORY-687 AC3)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("art_type", ["unit-test", "integration-test", "qualification-test"])
def test_test_types_load_implementation_review(tmp_path: Path, art_type: str):
    review_dir = tmp_path / ".specflow" / "checklists" / "review"
    review_dir.mkdir(parents=True)
    shutil.copy(_TEMPLATES / "review" / "implementation-review.yaml", review_dir)
    art = Artifact(
        path=tmp_path / "UT-001.md",
        frontmatter={"id": "UT-001", "type": art_type, "status": "draft", "title": "t"},
        body="",
        links=[],
    )
    assembled = ckl.assemble_checklist(tmp_path, art)
    assert f"review/{art_type}" in assembled.sources
    assert any(i.id == "CKL-REV-IMPL-01" for i in assembled.items)


def test_dead_parallel_checklist_runner_removed_from_lint():
    assert not hasattr(lint_lib, "discover_checklists")
    assert not hasattr(lint_lib, "run_automated_checklist")
    assert "discover_checklists" not in lint_lib.__all__
    assert "run_automated_checklist" not in lint_lib.__all__


# ── Live dogfood dirs are routable (STORY-712 / F-128) ──────────────────────

_REPO_ROOT = _SRC.parent.parent
_LIVE_CHECKLISTS = _REPO_ROOT / ".specflow" / "checklists"
# Every category a loader in lib/checklists.py reads. A directory outside this
# set silently drops its items (readiness/ sat unread from v1.1.0 to v1.17.1).
_ROUTABLE_CATEGORIES = {"in-process", "review", "shared", "phase-gates", "domain", "learned"}


@pytest.mark.skipif(not _LIVE_CHECKLISTS.is_dir(), reason="no live .specflow/checklists in this checkout")
def test_live_checklist_dirs_are_routable():
    live = {p.name for p in _LIVE_CHECKLISTS.iterdir() if p.is_dir()}
    unroutable = live - _ROUTABLE_CATEGORIES
    assert not unroutable, f"no loader reads .specflow/checklists/{sorted(unroutable)}; move or delete them"


def test_routable_categories_cover_shipped_templates():
    shipped = {p.name for p in _TEMPLATES.iterdir() if p.is_dir()}
    assert shipped <= _ROUTABLE_CATEGORIES, shipped - _ROUTABLE_CATEGORIES
