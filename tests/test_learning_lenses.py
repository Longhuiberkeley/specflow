"""STORY-712 (F-133/F-134): the lens catalog, its documentation and the
learnable-technique defaults stay in step, and the artifact-review skill does
not promise PREV auto-creation the CLI cannot deliver.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specflow.lib import learning as learn_lib
from specflow.lib.techniques import ARTIFACT_LEVEL_DEFAULT_LENSES, LENS_CATALOG

_SHARED = Path(__file__).resolve().parent.parent / "src" / "specflow" / "templates" / "skills" / "shared"
_LENS_DOC = _SHARED / "specflow-references" / "references" / "adversarial-lenses.md"
_REVIEW_SKILL = _SHARED / "specflow-artifact-review" / "SKILL.md"
_COUNT_FILES = [
    _LENS_DOC,
    _REVIEW_SKILL,
    *(_SHARED / f"specflow-{s}" / "references" / "thinking-techniques.md" for s in ("discover", "plan", "execute")),
]

# Catalog lenses deliberately kept out of DEFAULT_LEARNABLE_TECHNIQUES. Empty
# on purpose: every lens can seed a PREV unless a decision says otherwise.
NOT_LEARNABLE_BY_DEFAULT: set[str] = set()


@pytest.mark.parametrize("lens", sorted(LENS_CATALOG))
def test_every_catalog_lens_is_documented(lens: str):
    assert f"(`{lens}`)" in _LENS_DOC.read_text(encoding="utf-8"), f"{lens} missing from adversarial-lenses.md"


@pytest.mark.parametrize("lens", sorted(LENS_CATALOG))
def test_every_catalog_lens_is_learnable_or_excluded(lens: str):
    assert (lens in learn_lib.DEFAULT_LEARNABLE_TECHNIQUES) != (lens in NOT_LEARNABLE_BY_DEFAULT)


def test_learnable_defaults_name_only_real_lenses_or_passes():
    non_lens = {t for t in learn_lib.DEFAULT_LEARNABLE_TECHNIQUES if "_" in t}
    assert non_lens <= set(LENS_CATALOG), non_lens - set(LENS_CATALOG)


def test_research_default_sets_are_documented():
    doc = _LENS_DOC.read_text(encoding="utf-8")
    for art_type, lenses in ARTIFACT_LEVEL_DEFAULT_LENSES.items():
        for lens in lenses:
            assert f"`{lens}`" in doc, f"{art_type} default {lens} not in the research table"


@pytest.mark.parametrize("path", _COUNT_FILES, ids=[str(p.relative_to(_SHARED)) for p in _COUNT_FILES])
def test_documented_lens_count_matches_catalog(path: Path):
    text = path.read_text(encoding="utf-8")
    counts = {int(n) for n in re.findall(r"\b(\d+)-lens catalog\b", text)}
    counts |= {int(n) for n in re.findall(r"\bAll (\d+) available\b", text)}
    assert counts, f"{path.name} no longer states the lens count"
    assert counts == {len(LENS_CATALOG)}, f"{path.name} says {counts}, catalog has {len(LENS_CATALOG)}"


def test_review_skill_does_not_promise_prev_auto_creation():
    text = _REVIEW_SKILL.read_text(encoding="utf-8")
    assert "auto-create" not in text
    assert "creates no PREV" in text
    assert "specflow verify --seed-prev" in text
