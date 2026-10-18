"""REQ-071 AC2/AC3 / STORY-752: test specs are not left in draft under a parent
that already claims done-ness, every promoted spec carries passing verify
evidence, and every ``tests/*.py`` path a spec body cites exists on disk.

Known exemption: a spec whose only parents are deprecated requirements
(QT-058..061 under REQ-048..051) stays ``draft`` because the test-spec status
map has no terminal status (recorded in SPIKE-008 / ROADMAP as an engine gap).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SPECS = REPO / "_specflow" / "specs"
WORK = REPO / "_specflow" / "work"
TEST_DIRS = {"UT": "unit-tests", "IT": "integration-tests", "QT": "qualification-tests"}
CLAIMED = {"implemented", "verified"}

# Promoted on 2026-10-18 (STORY-752): practice spine + the v1.17.4 pstack specs.
PROMOTED = (
    [f"UT-{n:03d}" for n in range(89, 103)] + ["UT-153", "UT-154"]
    + [f"IT-{n:03d}" for n in range(55, 71)] + ["IT-113", "IT-114"]
    + [f"QT-{n:03d}" for n in range(54, 58)] + [f"QT-{n:03d}" for n in range(62, 74)]
    + ["QT-114", "QT-115"]
)
DEPRECATED_PARENT_EXEMPT = {"QT-058", "QT-059", "QT-060", "QT-061"}


def _frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1]) or {}


def _index() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for base in (SPECS, WORK):
        for p in base.rglob("*.md"):
            if p.name.startswith("_"):
                continue
            try:
                fm = _frontmatter(p)
            except Exception:  # pragma: no cover - malformed fixture
                continue
            if fm.get("id"):
                out[fm["id"]] = {"status": fm.get("status", ""), "path": p, "fm": fm}
    return out


def _specs(index: dict[str, dict]) -> list[dict]:
    return [v for k, v in index.items() if k.split("-")[0] in TEST_DIRS]


def test_no_draft_spec_under_a_claimed_parent() -> None:
    index = _index()
    offenders = []
    for spec in _specs(index):
        fm = spec["fm"]
        if fm.get("status") != "draft" or fm["id"] in DEPRECATED_PARENT_EXEMPT:
            continue
        parents = [l["target"] for l in fm.get("links", []) if l.get("role") == "verified_by"]
        claimed = [p for p in parents if index.get(p, {}).get("status") in CLAIMED]
        if claimed:
            offenders.append((fm["id"], claimed))
    assert not offenders, f"draft specs under implemented/verified parents: {offenders}"


def test_deprecated_parent_exemption_is_still_true() -> None:
    index = _index()
    for spec_id in DEPRECATED_PARENT_EXEMPT:
        fm = index[spec_id]["fm"]
        parents = [l["target"] for l in fm.get("links", []) if l.get("role") == "verified_by"]
        assert parents, spec_id
        assert all(index[p]["status"] == "deprecated" for p in parents), (spec_id, parents)


def test_promoted_specs_carry_passing_evidence() -> None:
    index = _index()
    bad = []
    for spec_id in PROMOTED:
        fm = index[spec_id]["fm"]
        if fm.get("status") not in CLAIMED:
            bad.append((spec_id, "status", fm.get("status")))
            continue
        if not fm.get("verify_command"):
            bad.append((spec_id, "no verify_command", None))
        if fm.get("verify_run_exit_code") != 0:
            bad.append((spec_id, "verify_run_exit_code", fm.get("verify_run_exit_code")))
        for f in fm.get("output_files") or []:
            if not (REPO / f).exists():
                bad.append((spec_id, "missing output file", f))
    assert not bad, bad


def test_every_cited_test_path_exists() -> None:
    index = _index()
    pattern = re.compile(r"tests/[A-Za-z0-9_/]+\.py")
    missing = []
    for spec in _specs(index):
        text = spec["path"].read_text(encoding="utf-8")
        for m in sorted(set(pattern.findall(text))):
            if not (REPO / m).exists():
                missing.append((spec["fm"]["id"], m))
    assert not missing, f"spec bodies cite test files that do not exist: {missing}"
